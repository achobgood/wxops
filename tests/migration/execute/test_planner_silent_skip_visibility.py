"""Tests for planner silent-skip visibility (2026-04-15).

Every short-circuit path in ``expand_to_operations`` and the per-type
expanders must emit a ``logger.warning`` AND record into ``PlannerSkipReport``.
This prevents the ``DEVICE_FIRMWARE_CONVERTIBLE`` bug class where 611
convertible phones were silently dropped from the plan.

Tests organized by site:
- Stale decisions on analyzed objects
- Pending decisions on analyzed objects
- Generic decision-skip (_SKIP_DECISION_TYPES)
- Per-expander short-circuits (line_key_template, monitoring_list, device_layout, etc.)
- Aggregate summary formatting
- ``fail_on_unresolved`` loud-fail gate
- Data-only types
- Unknown expander
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.execute.planner import (
    PlannerSkipReport,
    PlannerUnresolvedError,
    _log_skip_summary,
    expand_to_operations,
)
from wxcli.migration.models import (
    CanonicalCallForwarding,
    CanonicalCallingPermission,
    CanonicalDevice,
    CanonicalDeviceLayout,
    CanonicalLineKeyTemplate,
    CanonicalMonitoringList,
    CanonicalSharedLine,
    CanonicalSoftkeyConfig,
    CanonicalUser,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _analyzed(obj):
    obj.status = MigrationStatus.ANALYZED
    return obj


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "silent-skip.db")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Stale-decision visibility (the DEVICE_FIRMWARE_CONVERTIBLE bug pattern)
# ---------------------------------------------------------------------------

class TestStaleDecisionWarnsAndRecords:
    """A stale decision attached to an analyzed object must produce a WARN.

    **Expectation revised 2026-07-30 (finding F09).** The WARN is unchanged — it
    is what stopped 611 convertible phones being hidden. What changed is where it
    is recorded: ``report.anomalies``, not ``report.entries``. The entity is still
    expanded, so calling it a "skip" made the skip report untrustworthy. Measured
    on director-demo-2026-04-15: 766 of 1129 "Planner skip:" lines described
    entities that were all present in ``plan_operations``.
    """

    def test_stale_decision_emits_warn_and_anomaly_entry(self, store, caplog):
        """Stale decision on an analyzed device → WARN + anomaly (not a skip)."""
        device = _analyzed(CanonicalDevice(
            canonical_id="device:stale_test",
            provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.upsert_object(device)

        store.save_decision({
            "decision_id": "D_stale_1",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "stale",
            "context": {"_affected_objects": ["device:stale_test"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
            "chosen_option": "__stale__",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "stale",
            "fingerprint": "fp-stale-1",
            "run_id": "r",
        })

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            ops = expand_to_operations(store, report=report)

        # Device still gets ops — stale decision is a WARN, not a skip
        assert len([o for o in ops if o.resource_type == "device"]) == 2

        # WARN + anomaly entry are present
        stale_anomalies = [a for a in report.anomalies if a.decision_state == "stale"]
        assert len(stale_anomalies) == 1
        assert stale_anomalies[0].canonical_id == "device:stale_test"
        assert stale_anomalies[0].decision_type == "DEVICE_INCOMPATIBLE"
        assert "stale" in " ".join(r.message for r in caplog.records).lower()

        # ...and it is NOT in the skip report, because it was not skipped.
        assert not any(e.canonical_id == "device:stale_test" for e in report.entries)


class TestPendingDecisionWarnsAndRecords:
    """A pending (unresolved) decision attached to an analyzed object must WARN."""

    def test_pending_decision_on_analyzed_emits_warn(self, store, caplog):
        """A pending decision on an ANALYZED object is a status-drift bug.

        The object should be at ``needs_decision`` — if it's at ``analyzed``
        with a pending decision, the planner loudly flags it.
        """
        user = _analyzed(CanonicalUser(
            canonical_id="user:pending_test",
            provenance=_prov(),
            emails=["x@y.com"],
        ))
        store.upsert_object(user)

        store.save_decision({
            "decision_id": "D_pending_1",
            "type": "EXTENSION_CONFLICT",
            "severity": "HIGH",
            "summary": "pending",
            "context": {"_affected_objects": ["user:pending_test"]},
            "options": [{"id": "skip", "label": "skip", "impact": "none"}],
            "chosen_option": None,  # pending
            "fingerprint": "fp-pending-1",
            "run_id": "r",
        })

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        # Recorded as an anomaly, not a skip — the user is still planned.
        # Same revision as the stale case above (finding F09).
        pending = [a for a in report.anomalies if a.decision_state == "pending"]
        assert len(pending) == 1
        assert pending[0].canonical_id == "user:pending_test"
        assert not any(e.canonical_id == "user:pending_test" for e in report.entries)


# ---------------------------------------------------------------------------
# Generic decision-skip visibility
# ---------------------------------------------------------------------------

class TestDecisionSkipWarns:
    """_SKIP_DECISION_TYPES resolved as 'skip' must WARN + record."""

    def test_extension_conflict_skip_warns(self, store, caplog):
        user = _analyzed(CanonicalUser(
            canonical_id="user:skipme",
            provenance=_prov(),
            emails=["skip@x.com"],
        ))
        store.upsert_object(user)
        store.save_decision({
            "decision_id": "D_skip_1",
            "type": "EXTENSION_CONFLICT",
            "severity": "HIGH",
            "summary": "skip",
            "context": {"_affected_objects": ["user:skipme"]},
            "options": [{"id": "skip", "label": "skip", "impact": "user dropped"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-skip-1",
            "run_id": "r",
        })

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            ops = expand_to_operations(store, report=report)

        user_ops = [o for o in ops if o.canonical_id == "user:skipme"]
        assert len(user_ops) == 0

        skip_entries = [e for e in report.entries if e.reason == "decision_skip"]
        assert len(skip_entries) == 1
        assert skip_entries[0].decision_type == "EXTENSION_CONFLICT"
        assert skip_entries[0].decision_state == "skip"
        # WARN is in the log
        assert any("user:skipme" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Per-expander short-circuit visibility
# ---------------------------------------------------------------------------

class TestPerExpanderShortCircuitsWarn:
    """Every per-expander skip path must WARN + record."""

    def test_line_key_template_zero_phones_warns(self, store, caplog):
        tmpl = _analyzed(CanonicalLineKeyTemplate(
            canonical_id="line_key_template:dead",
            provenance=_prov(),
            name="Dead",
            device_model="Cisco 9861",
            phones_using=0,
            line_keys=[],
        ))
        store.upsert_object(tmpl)

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        entries = [e for e in report.entries if e.entity_type == "line_key_template"]
        assert len(entries) == 1
        assert entries[0].reason == "dead_template_zero_phones"

    def test_monitoring_list_no_members_warns(self, store, caplog):
        ml = _analyzed(CanonicalMonitoringList(
            canonical_id="monitoring_list:m1",
            provenance=_prov(),
            user_canonical_id="user:mgr",
            monitored_members=[],
        ))
        store.upsert_object(ml)

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        assert any(
            e.entity_type == "monitoring_list" and e.reason == "no_monitored_members"
            for e in report.entries
        )

    def test_device_layout_no_content_warns(self, store, caplog):
        layout = _analyzed(CanonicalDeviceLayout(
            canonical_id="device_layout:empty",
            provenance=_prov(),
            device_canonical_id="device:x",
            resolved_line_keys=[],
            template_canonical_id=None,
        ))
        store.upsert_object(layout)

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        assert any(
            e.entity_type == "device_layout" and e.reason == "no_layout_content"
            for e in report.entries
        )

    def test_softkey_config_missing_device_warns(self, store, caplog):
        sk = _analyzed(CanonicalSoftkeyConfig(
            canonical_id="softkey_config:orphan",
            provenance=_prov(),
            is_psk_target=True,
            device_canonical_id=None,
        ))
        store.upsert_object(sk)

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        assert any(
            e.entity_type == "softkey_config" and e.reason == "no_device_canonical_id"
            for e in report.entries
        )

    def test_calling_permission_no_users_warns(self, store, caplog):
        perm = _analyzed(CanonicalCallingPermission(
            canonical_id="calling_permission:unused",
            provenance=_prov(),
            name="Unused",
            assigned_users=[],
        ))
        store.upsert_object(perm)

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        assert any(
            e.entity_type == "calling_permission" and e.reason == "no_assigned_users"
            for e in report.entries
        )

    def test_call_forwarding_all_disabled_records_info(self, store):
        """call_forwarding with all types disabled records in report but
        is INFO-level (expected no-op, not WARN)."""
        cf = _analyzed(CanonicalCallForwarding(
            canonical_id="call_forwarding:u1",
            provenance=_prov(),
            user_canonical_id="user:u1",
            always_enabled=False,
            busy_enabled=False,
            no_answer_enabled=False,
        ))
        store.upsert_object(cf)

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)
        assert any(
            e.reason == "all_forwarding_disabled"
            for e in report.entries
        )

    def test_shared_line_skip_decision_warns(self, store, caplog):
        sl = _analyzed(CanonicalSharedLine(
            canonical_id="shared_line:s1",
            provenance=_prov(),
            owner_canonical_ids=["user:a", "user:b"],
            extension="1001",
        ))
        store.upsert_object(sl)
        store.save_decision({
            "decision_id": "D_sl_1",
            "type": "SHARED_LINE_COMPLEX",
            "severity": "MEDIUM",
            "summary": "skip shared",
            "context": {"_affected_objects": ["shared_line:s1"]},
            "options": [{"id": "skip", "label": "skip", "impact": "none"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-sl-1",
            "run_id": "r",
        })

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        assert any(
            e.entity_type == "shared_line"
            and e.decision_type == "SHARED_LINE_COMPLEX"
            and e.decision_state == "skip"
            for e in report.entries
        )

    def test_non_webex_device_model_records_info(self, store):
        """Non-Webex device models are expected skips (INFO) but still
        recorded in the report so the summary shows the full roster."""
        dev = _analyzed(CanonicalDevice(
            canonical_id="device:ata",
            provenance=_prov(),
            mac="001122334455",
            model="Cisco ATA 191",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.upsert_object(dev)

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)

        assert any(
            e.entity_type == "device" and e.canonical_id == "device:ata"
            for e in report.entries
        )


# ---------------------------------------------------------------------------
# Aggregate summary
# ---------------------------------------------------------------------------

class TestAggregateSummary:
    """The aggregate summary should group counts by reason / decision type."""

    def test_summary_groups_by_decision_type(self, caplog):
        report = PlannerSkipReport()
        report.record(
            canonical_id="device:d1", entity_type="device",
            reason="decision_skip", decision_type="DEVICE_INCOMPATIBLE",
            decision_state="skip", consequence="c",
        )
        report.record(
            canonical_id="device:d2", entity_type="device",
            reason="decision_skip", decision_type="DEVICE_INCOMPATIBLE",
            decision_state="skip", consequence="c",
        )
        report.record(
            canonical_id="user:u1", entity_type="user",
            reason="stale_decision_attached", decision_type="EXTENSION_CONFLICT",
            decision_state="stale", consequence="c",
        )

        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            _log_skip_summary(report)

        joined = "\n".join(r.message for r in caplog.records)
        assert "Planner skipped 3 entities" in joined
        assert "DEVICE_INCOMPATIBLE" in joined
        assert "EXTENSION_CONFLICT" in joined
        # Unresolved review line is present
        assert "wxcli cucm decisions" in joined

    def test_has_unresolved_skips_flag(self):
        report = PlannerSkipReport()
        report.record(
            canonical_id="x", entity_type="x", reason="decision_skip",
            decision_type="FOO", decision_state="skip", consequence="c",
        )
        assert not report.has_unresolved_skips

        report.record(
            canonical_id="y", entity_type="y", reason="stale",
            decision_type="BAR", decision_state="stale", consequence="c",
        )
        assert report.has_unresolved_skips

    def test_counts_groups_by_decision_or_reason(self):
        report = PlannerSkipReport()
        report.record(
            canonical_id="a", entity_type="a", reason="decision_skip",
            decision_type="FOO", decision_state="skip", consequence="c",
        )
        report.record(
            canonical_id="b", entity_type="b", reason="no_members",
            consequence="c",
        )
        counts = report.counts
        assert counts["FOO"] == 1  # uses decision_type when present
        assert counts["no_members"] == 1  # falls back to reason


# ---------------------------------------------------------------------------
# Loud-fail gate
# ---------------------------------------------------------------------------

class TestFailOnUnresolved:
    """--fail-on-unresolved / WXCLI_PLAN_FAIL_ON_UNRESOLVED loud-fail gate.

    **Contract revised 2026-07-30 (finding F09).** The gate no longer fires on a
    stale decision attached to an entity that was still expanded. Rationale, in
    order of weight:

    1. ``PlannerUnresolvedError``'s own message says "entities **skipped** due to
       unresolved decisions". Measured on director-demo-2026-04-15, 766 of the
       entities it would cite are present in ``plan_operations``. The message was
       false.
    2. Firing on them aborts correct plans. Every one of the 300 users on that
       project carries a stale MISSING_DATA decision, so the gate could never be
       used on a real migration.
    3. The gate was simultaneously **blind** to the entities genuinely missing —
       the 23 users stranded at ``status='normalized'`` (finding F08) produce no
       skip entry at all. Those now trip it, which is what it was for.

    The WARN and the aggregate roll-up are unchanged; see
    ``test_planner_skip_report_truth.py`` for the positive cases.
    """

    def test_does_not_raise_when_entity_was_planned_despite_stale_decision(self, store):
        device = _analyzed(CanonicalDevice(
            canonical_id="device:stale_for_fail",
            provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.upsert_object(device)
        store.save_decision({
            "decision_id": "D_stale_fail_1",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "stale",
            "context": {"_affected_objects": ["device:stale_for_fail"]},
            "options": [{"id": "skip", "label": "skip", "impact": "none"}],
            "chosen_option": "__stale__",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "stale",
            "fingerprint": "fp-stale-fail-1",
            "run_id": "r",
        })

        report = PlannerSkipReport()
        ops = expand_to_operations(
            store, report=report, fail_on_unresolved=True
        )
        assert [o for o in ops if o.canonical_id == "device:stale_for_fail"], (
            "the device is planned, so the gate must not abort"
        )
        assert not report.has_unresolved_skips
        assert len(report.anomalies) == 1

    def test_does_not_raise_when_flag_unset(self, store):
        """Default behaviour: WARN + continue, no exception."""
        device = _analyzed(CanonicalDevice(
            canonical_id="device:stale_nofail",
            provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.upsert_object(device)
        store.save_decision({
            "decision_id": "D_stale_nofail_1",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "stale",
            "context": {"_affected_objects": ["device:stale_nofail"]},
            "options": [{"id": "skip", "label": "skip", "impact": "none"}],
            "chosen_option": "__stale__",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "stale",
            "fingerprint": "fp-stale-nofail-1",
            "run_id": "r",
        })

        # Should NOT raise
        report = PlannerSkipReport()
        ops = expand_to_operations(store, report=report, fail_on_unresolved=False)
        assert len([o for o in ops if o.resource_type == "device"]) == 2
        # Nothing is missing from the plan, so has_unresolved_skips is False —
        # the observation lives in anomalies instead (finding F09).
        assert not report.has_unresolved_skips
        assert len(report.anomalies) == 1

    def test_does_not_raise_when_only_expected_skips(self, store):
        """Skips without unresolved decisions (e.g., dead template) should
        NOT trigger the loud-fail gate."""
        tmpl = _analyzed(CanonicalLineKeyTemplate(
            canonical_id="line_key_template:dead2",
            provenance=_prov(),
            name="Dead",
            device_model="Cisco 9861",
            phones_using=0,
            line_keys=[],
        ))
        store.upsert_object(tmpl)

        report = PlannerSkipReport()
        # Should not raise even though an entity was skipped
        ops = expand_to_operations(store, report=report, fail_on_unresolved=True)
        assert ops == []  # nothing to plan
        assert not report.has_unresolved_skips
        # But the entry is still in the report
        assert len(report.entries) == 1

    def test_env_var_enables_gate(self, store, monkeypatch):
        """WXCLI_PLAN_FAIL_ON_UNRESOLVED=1 environment variable enables gate.

        Trigger switched to a stranded object — an entity genuinely absent from
        the plan. The env var plumbing is what this test covers; the stale-but-
        expanded case no longer trips the gate (see the class docstring).
        """
        user = CanonicalUser(
            canonical_id="user:env_stranded",
            provenance=_prov(),
            emails=["env@x.com"],
        )
        user.status = MigrationStatus.NORMALIZED
        store.upsert_object(user)

        monkeypatch.setenv("WXCLI_PLAN_FAIL_ON_UNRESOLVED", "1")
        with pytest.raises(PlannerUnresolvedError) as exc:
            expand_to_operations(store)
        assert "never reached the planner" in str(exc.value)


# ---------------------------------------------------------------------------
# Unknown expander
# ---------------------------------------------------------------------------

class TestUnknownExpanderWarnsAndRecords:
    def test_unknown_type_warns_and_records(self, store, caplog):
        """An analyzed object whose prefix has no expander must WARN + record.

        We fabricate such an object via a MigrationObject since no canonical
        model uses an unregistered prefix.
        """
        from wxcli.migration.models import MigrationObject

        obj = MigrationObject(
            canonical_id="made_up_type:abc",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
        )
        store.upsert_object(obj)

        report = PlannerSkipReport()
        with caplog.at_level("WARNING", logger="wxcli.migration.execute.planner"):
            expand_to_operations(store, report=report)

        assert any(
            e.reason == "no_expander_registered" and e.entity_type == "made_up_type"
            for e in report.entries
        )
