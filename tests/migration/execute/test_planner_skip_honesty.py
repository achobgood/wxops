"""F16 + the skip-summary over-report.

Two findings in the same output.

F16: `plan` emitted 1366 lines / 267KB for a 300-user environment. Fixing F09
did not shrink it — 769 "Planner anomaly:" WARN lines simply replaced 766
"Planner skip:" ones (measured on director-demo-2026-04-15: 1153 stderr lines
before and after). The per-entity anomaly line is redundant with
`_log_anomaly_summary` and describes entities that ARE in the plan.

The over-report: `Planner skipped 1384 entities:` where 1248 of them (90%) need
no operation by design — 687 `line` objects consumed by `user:create`, 314
softphone users moving to the Webex App, 224 line key templates no phone
references, 12 report-only softkey templates, 10 CTI ports, 1 forwarding object
with every type disabled. This is the fourth instance of the split-the-population
defect, in the one output built to make silent skips loud.

The 224 were first classified as gaps pending measurement, on the worry that
phones_using=0 might mean a failed cross-ref rather than an unused template.
Measured since — see TestDeadTemplateIsByDesignAtTheCallSite — and they are by
design.
"""

from __future__ import annotations

import logging

from wxcli.migration.execute.planner import (
    PlannerSkipReport,
    _log_skip_summary,
    _warn_anomaly,
    _warn_skip,
)

PLANNER_LOGGER = "wxcli.migration.execute.planner"


def _messages(caplog) -> str:
    return "\n".join(r.getMessage() for r in caplog.records)


def _director_demo_shaped_report() -> PlannerSkipReport:
    """The measured director-demo-2026-04-15 population: 1248 by design, 136 gaps."""
    report = PlannerSkipReport()
    by_design = [
        ("data_only_type", 687, "line"),
        ("compatibility_tier=webex_app", 314, "device"),
        # Measured by design, not assumed — see test_dead_template_is_by_design.
        ("dead_template_zero_phones", 224, "line_key_template"),
        ("template_level_report_only", 12, "softkey_config"),
        ("compatibility_tier=infrastructure", 10, "device"),
        ("all_forwarding_disabled", 1, "call_forwarding"),
    ]
    gaps = [
        ("no_layout_content", 70, "device_layout"),
        ("missing_mac", 60, "device"),
        ("no_expander_registered", 6, "call_park_ext"),
    ]
    for reason, count, etype in by_design:
        for i in range(count):
            report.record(
                canonical_id=f"{etype}:{reason}:{i}", entity_type=etype,
                reason=reason, consequence="c", by_design=True,
            )
    for reason, count, etype in gaps:
        for i in range(count):
            report.record(
                canonical_id=f"{etype}:{reason}:{i}", entity_type=etype,
                reason=reason, consequence="c",
            )
    return report


class TestPopulationIsSplit:
    def test_measured_split_is_1248_by_design_and_136_gaps(self):
        report = _director_demo_shaped_report()
        assert len(report.entries) == 1384
        assert len(report.by_design_entries) == 1248
        assert len(report.gap_entries) == 136

    def test_headline_states_the_split(self, caplog):
        report = _director_demo_shaped_report()
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _log_skip_summary(report)
        text = _messages(caplog)

        assert "Planner skipped 1384 entities (1248 by design, 136 gaps)" in text
        assert "1248 need no operation by design — nothing is missing" in text
        assert "136 are gaps — an entity that should have been built was not" in text

    def test_each_reason_lands_in_the_right_block(self, caplog):
        report = _director_demo_shaped_report()
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _log_skip_summary(report)
        lines = _messages(caplog).splitlines()

        design_at = next(i for i, l in enumerate(lines) if "by design" in l and "need no" in l)
        gaps_at = next(i for i, l in enumerate(lines) if "are gaps" in l)

        def block(reason: str) -> str:
            idx = next(i for i, l in enumerate(lines) if l.strip().startswith(reason + ":"))
            return "design" if design_at < idx < gaps_at else "gaps"

        assert block("data_only_type") == "design"
        assert block("compatibility_tier=webex_app") == "design"
        assert block("dead_template_zero_phones") == "design"
        assert block("template_level_report_only") == "design"
        assert block("compatibility_tier=infrastructure") == "design"
        assert block("all_forwarding_disabled") == "design"
        assert block("no_layout_content") == "gaps"
        assert block("missing_mac") == "gaps"
        assert block("no_expander_registered") == "gaps"

    def test_no_python_enum_repr_in_operator_text(self, caplog):
        report = _director_demo_shaped_report()
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _log_skip_summary(report)
        assert "DeviceCompatibilityTier." not in _messages(caplog)


class TestAdviceLineIsEarned:
    def test_no_decision_review_advice_when_no_skip_has_a_decision(self, caplog):
        """Every director-demo group printed "expander short-circuit"."""
        report = _director_demo_shaped_report()
        report.stranded_counts = {"user": 23}  # a different population entirely

        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _log_skip_summary(report)
        text = _messages(caplog)

        assert report.has_unresolved_skips is True  # stranded, not skips
        assert "Review unresolved decisions" not in text

    def test_advice_appears_when_a_skip_really_is_decision_gated(self, caplog):
        report = PlannerSkipReport()
        report.record(
            canonical_id="user:u1", entity_type="user", reason="stale_decision",
            decision_type="EXTENSION_CONFLICT", decision_state="stale",
            consequence="c",
        )
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _log_skip_summary(report)
        text = _messages(caplog)

        assert "Review unresolved decisions" in text
        assert "EXTENSION_CONFLICT" in text


class TestLogLevelFollowsClassification:
    """The pairing used to be convention only, and that is how 224 templates
    ended up warning about work that was never owed."""

    def test_a_gap_warns(self, caplog):
        report = PlannerSkipReport()
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _warn_skip(
                report, canonical_id="device:d1", entity_type="device",
                reason="missing_mac", consequence="c",
            )
        assert "Planner skip: device device:d1" in _messages(caplog)
        assert report.entries[0].by_design is False

    def test_a_by_design_skip_does_not_warn(self, caplog):
        report = PlannerSkipReport()
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            _warn_skip(
                report, canonical_id="line_key_template:t1",
                entity_type="line_key_template",
                reason="dead_template_zero_phones", consequence="c",
                by_design=True,
            )
        assert _messages(caplog) == ""
        assert report.entries[0].by_design is True

    def test_a_by_design_skip_is_still_recoverable_at_info(self, caplog):
        report = PlannerSkipReport()
        with caplog.at_level(logging.INFO, logger=PLANNER_LOGGER):
            _warn_skip(
                report, canonical_id="line_key_template:t1",
                entity_type="line_key_template",
                reason="dead_template_zero_phones", consequence="c",
                by_design=True,
            )
        assert "Planner skip (expected): line_key_template" in _messages(caplog)


class TestDeadTemplateIsByDesignAtTheCallSite:
    """Measured on director-demo-2026-04-15, not assumed.

    227 of 1100 phones carry a non-null phoneTemplateName; those name 18
    distinct templates; exactly 18 templates have phones_using > 0 and their
    counts sum to 227, which is also the phone_uses_button_template cross-ref
    count. So phones_using=0 means genuinely unreferenced, not a broken
    cross-ref.
    """

    def test_unreferenced_template_records_by_design(self):
        from wxcli.migration.execute.planner import (
            _CURRENT_REPORT, _expand_line_key_template, _set_current_report,
        )

        report = PlannerSkipReport()
        token = _set_current_report(report)
        try:
            ops = _expand_line_key_template({
                "canonical_id": "line_key_template:Standard 8851 SIP",
                "phones_using": 0,
            })
        finally:
            _CURRENT_REPORT.reset(token)

        assert ops == []
        assert len(report.entries) == 1
        assert report.entries[0].reason == "dead_template_zero_phones"
        assert report.entries[0].by_design is True
        assert report.gap_entries == []

    def test_referenced_template_still_expands(self):
        from wxcli.migration.execute.planner import (
            _CURRENT_REPORT, _expand_line_key_template, _set_current_report,
        )

        report = PlannerSkipReport()
        token = _set_current_report(report)
        try:
            ops = _expand_line_key_template({
                "canonical_id": "line_key_template:Standard 8851 SIP",
                "phones_using": 49,
            })
        finally:
            _CURRENT_REPORT.reset(token)

        assert ops
        assert report.entries == []

    def test_device_settings_template_splits_its_two_reasons(self):
        """zero_phones_using is the same structural condition; no_settings is not."""
        from wxcli.migration.execute.planner import (
            _CURRENT_REPORT, _expand_device_settings_template,
            _set_current_report,
        )

        report = PlannerSkipReport()
        token = _set_current_report(report)
        try:
            _expand_device_settings_template(
                {"canonical_id": "device_settings_template:a",
                 "settings": {"x": 1}, "phones_using": 0}, [],
            )
            _expand_device_settings_template(
                {"canonical_id": "device_settings_template:b",
                 "settings": {}, "phones_using": 5}, [],
            )
        finally:
            _CURRENT_REPORT.reset(token)

        by_reason = {e.reason: e.by_design for e in report.entries}
        assert by_reason == {"zero_phones_using": True, "no_settings": False}


class TestAnomalyVolume:
    def test_per_entity_anomaly_is_debug_not_warning(self, caplog):
        """769 of these were the whole of F16's unshrunk output."""
        report = PlannerSkipReport()
        with caplog.at_level(logging.WARNING, logger=PLANNER_LOGGER):
            for i in range(769):
                _warn_anomaly(
                    report, canonical_id=f"user:{i}", entity_type="user",
                    reason="MISSING_DATA", consequence="c",
                    decision_type="MISSING_DATA", decision_state="stale",
                )
        assert _messages(caplog) == ""

    def test_the_record_itself_is_still_kept_in_full(self, caplog):
        """Quieter, not blinder — the report and its gate are unaffected."""
        report = PlannerSkipReport()
        for i in range(769):
            _warn_anomaly(
                report, canonical_id=f"user:{i}", entity_type="user",
                reason="MISSING_DATA", consequence="c",
                decision_type="MISSING_DATA", decision_state="stale",
            )
        assert len(report.anomalies) == 769
        assert report.anomaly_counts == {"MISSING_DATA": 769}
        # Anomalies are planned entities, so they must not trip the gate.
        assert report.has_unresolved_skips is False

    def test_verbose_recovers_the_per_entity_lines(self, caplog):
        report = PlannerSkipReport()
        with caplog.at_level(logging.DEBUG, logger=PLANNER_LOGGER):
            _warn_anomaly(
                report, canonical_id="user:1", entity_type="user",
                reason="MISSING_DATA", consequence="c",
                decision_type="MISSING_DATA", decision_state="stale",
            )
        assert "Planner anomaly: user user:1" in _messages(caplog)
