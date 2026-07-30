"""Stale decisions must never be reported as resolved (round-3 finding F04/F15).

``store.merge_decisions`` invalidates a decision by writing
``chosen_option = '__stale__'``. That string is truthy, so
``if d.get("chosen_option")`` counted invalidated decisions as auto-resolved —
live at nine call sites across three report modules. On the dcloud-fresh
dataset that rendered ``Incompatible Devices (405) — 405/405 resolved`` with
every row labelled "Auto-resolved" while nothing had decided anything, and
inflated the decision denominator 5.4x.

The fixture here is that dataset in miniature: every DEVICE_INCOMPATIBLE
decision stale, one genuinely resolved decision, one genuinely pending.
"""

import pytest

from wxcli.migration.decision_state import (
    RETIRED_DECISION_TYPES,
    STALE,
    DecisionCounts,
    count_decisions,
    is_pending,
    is_resolved,
    is_retired,
    is_stale,
)
from wxcli.migration.models import DecisionType
from wxcli.migration.store import MigrationStore


# ---------------------------------------------------------------------------
# The predicate itself
# ---------------------------------------------------------------------------

class TestPredicate:
    def test_stale_is_not_resolved(self):
        """The whole bug in one assertion: the sentinel is truthy."""
        d = {"chosen_option": STALE}
        assert bool(d["chosen_option"]) is True, "sentinel must be truthy or this test is moot"
        assert is_resolved(d) is False
        assert is_stale(d) is True
        assert is_pending(d) is False

    def test_chosen_option_is_resolved(self):
        d = {"chosen_option": "replace"}
        assert is_resolved(d) is True
        assert is_stale(d) is False
        assert is_pending(d) is False

    def test_none_is_pending(self):
        d = {"chosen_option": None}
        assert is_pending(d) is True
        assert is_resolved(d) is False
        assert is_stale(d) is False

    def test_missing_key_is_pending(self):
        assert is_pending({}) is True
        assert is_resolved({}) is False

    def test_only_none_and_the_sentinel_are_special(self):
        """Pinning the boundary: any other value counts as a real choice.

        The store writes exactly three things into ``chosen_option`` — ``None``,
        an option id, or the sentinel — so no fourth case needs handling. This
        test exists so a future "treat empty as pending" change is a deliberate
        edit here rather than a silent behaviour shift.
        """
        assert is_resolved({"chosen_option": ""}) is True
        assert is_stale({"chosen_option": ""}) is False
        assert is_resolved({"chosen_option": "__STALE__"}) is True, "sentinel is case-sensitive"

    def test_states_are_exhaustive_and_exclusive(self):
        decisions = [
            {"chosen_option": None},
            {"chosen_option": STALE},
            {"chosen_option": "accept"},
        ]
        counts = count_decisions(decisions)
        assert counts == DecisionCounts(total=3, resolved=1, pending=1, stale=1)
        assert counts.resolved + counts.pending + counts.stale == counts.total
        assert counts.live_total == 2

    def test_retired_stale_rows_are_counted_apart_from_active_ones(self):
        """611 of dcloud-fresh's 1399 stale rows are a retired decision type.

        Telling the operator all 1399 "need review" is wrong in the alarming
        direction, the same way counting them as resolved was wrong in the
        flattering direction.
        """
        retired_type = next(iter(RETIRED_DECISION_TYPES))
        decisions = [
            {"chosen_option": STALE, "type": retired_type},
            {"chosen_option": STALE, "type": retired_type},
            {"chosen_option": STALE, "type": "DEVICE_INCOMPATIBLE"},
            {"chosen_option": "accept", "type": "FEATURE_APPROXIMATION"},
        ]
        counts = count_decisions(decisions)
        assert counts.stale == 3
        assert counts.stale_retired == 2
        assert counts.stale_active == 1, "only the live-type stale row needs review"

    def test_is_retired_only_matches_the_declared_set(self):
        assert is_retired({"type": "DEVICE_FIRMWARE_CONVERTIBLE"}) is True
        assert is_retired({"type": "DEVICE_INCOMPATIBLE"}) is False
        assert is_retired({}) is False

    def test_retired_set_members_are_real_decision_types(self):
        """A typo here would silently classify nothing, hiding the split."""
        from wxcli.migration.models import DecisionType

        valid = {d.value for d in DecisionType}
        assert RETIRED_DECISION_TYPES <= valid, (
            f"unknown decision types in RETIRED_DECISION_TYPES: "
            f"{RETIRED_DECISION_TYPES - valid}"
        )

    def test_resolved_pct_is_over_the_live_population_not_the_total(self):
        """1399 of 1579 stale must not drag the resolution percentage down."""
        counts = DecisionCounts(total=100, resolved=18, pending=2, stale=80)
        assert counts.live_total == 20
        assert counts.resolved_pct == 90

    def test_resolved_pct_is_zero_when_nothing_is_live(self):
        assert DecisionCounts(total=5, stale=5).resolved_pct == 0


# ---------------------------------------------------------------------------
# Fixture: the dcloud-fresh shape in miniature
# ---------------------------------------------------------------------------

@pytest.fixture()
def stale_heavy_store(tmp_path):
    """A store whose DEVICE_INCOMPATIBLE decisions were all invalidated.

    Mirrors dcloud-fresh: the DeviceCompatibilityAnalyzer produced nothing on
    a re-run, so every device decision the mapper had raised got stale-marked.
    """
    store = MigrationStore(tmp_path / "migration.db")
    run_id = "20260729T120000-stale-fixture"

    # 5 invalidated device decisions — the population that was mislabelled.
    for i in range(5):
        store.save_decision({
            "decision_id": store.next_decision_id(),
            "type": DecisionType.DEVICE_INCOMPATIBLE.value,
            "severity": "HIGH",
            "summary": f"CP-7962G device {i} is incompatible",
            "context": {"model": "CP-7962G"},
            "options": [{"id": "replace", "label": "Replace hardware", "impact": "1 new phone"}],
            "fingerprint": f"dev-incompat-{i}",
            "run_id": run_id,
            "chosen_option": STALE,
            "resolved_by": "stale",
        })

    # 2 genuinely auto-resolved decisions. Two of the same type on purpose:
    # the appendix only renders a per-row status table when a type has more
    # than one decision, so a single resolved decision would never produce an
    # "Auto-resolved" row label to compare against.
    for i in range(2):
        store.save_decision({
            "decision_id": store.next_decision_id(),
            "type": DecisionType.FEATURE_APPROXIMATION.value,
            "severity": "MEDIUM",
            "summary": f"Hunt group 'Sales HG {i}' uses Top Down which maps to REGULAR",
            "context": {"cucm_algorithm": "Top Down"},
            "options": [{"id": "accept", "label": "Accept approximation", "impact": "Minor"}],
            "fingerprint": f"fa-hg-{i}",
            "run_id": run_id,
            "chosen_option": "accept",
            "resolved_by": "auto_rule",
        })

    # 1 genuinely pending decision.
    store.save_decision({
        "decision_id": store.next_decision_id(),
        "type": DecisionType.CSS_ROUTING_MISMATCH.value,
        "severity": "MEDIUM",
        "summary": "CSS-International has 4 partitions — complex routing scope",
        "context": {"partition_count": 4},
        "options": [{"id": "map_dial_plan", "label": "Map to dial plan", "impact": "1 dial plan"}],
        "fingerprint": "css-intl-1",
        "run_id": run_id,
    })

    yield store
    store.close()


def test_fixture_really_is_stale_heavy(stale_heavy_store):
    """Guard the guard: a fixture with no stale rows would pass everything."""
    counts = count_decisions(stale_heavy_store.get_all_decisions())
    assert counts == DecisionCounts(
        total=8, resolved=2, pending=1, stale=5, stale_retired=0
    )
    assert counts.live_total == 3
    assert counts.stale_active == 5


@pytest.fixture()
def mixed_stale_store(tmp_path):
    """Stale rows of both kinds: 4 of a retired type, 2 of a live type.

    dcloud-fresh in miniature — 611 of its 1399 invalidated decisions are
    DEVICE_FIRMWARE_CONVERTIBLE, retired 2026-04-15.
    """
    store = MigrationStore(tmp_path / "migration.db")
    run_id = "20260729T120000-mixed"

    for i in range(4):
        store.save_decision({
            "decision_id": store.next_decision_id(),
            "type": DecisionType.DEVICE_FIRMWARE_CONVERTIBLE.value,
            "severity": "MEDIUM",
            "summary": f"CP-7841 device {i} can be converted",
            "context": {},
            "options": [{"id": "convert", "label": "Convert", "impact": "Reflash"}],
            "fingerprint": f"conv-{i}",
            "run_id": run_id,
            "chosen_option": STALE,
            "resolved_by": "stale",
        })
    for i in range(2):
        store.save_decision({
            "decision_id": store.next_decision_id(),
            "type": DecisionType.DEVICE_INCOMPATIBLE.value,
            "severity": "HIGH",
            "summary": f"CP-7962G device {i} is incompatible",
            "context": {},
            "options": [{"id": "replace", "label": "Replace", "impact": "1 phone"}],
            "fingerprint": f"incompat-{i}",
            "run_id": run_id,
            "chosen_option": STALE,
            "resolved_by": "stale",
        })
    store.save_decision({
        "decision_id": store.next_decision_id(),
        "type": DecisionType.FEATURE_APPROXIMATION.value,
        "severity": "LOW",
        "summary": "Hunt group maps to REGULAR",
        "context": {},
        "options": [{"id": "accept", "label": "Accept", "impact": "Minor"}],
        "fingerprint": "fa-live",
        "run_id": run_id,
        "chosen_option": "accept",
        "resolved_by": "auto_rule",
    })
    yield store
    store.close()


class TestRetiredStaleRowsAreNotReportedAsProblems:
    def test_fixture_has_both_kinds(self, mixed_stale_store):
        counts = count_decisions(mixed_stale_store.get_all_decisions())
        assert counts.stale == 6
        assert counts.stale_retired == 4
        assert counts.stale_active == 2

    def test_executive_page_reports_only_the_active_stale_as_needing_review(
        self, mixed_stale_store
    ):
        from wxcli.migration.report.executive import _page_scope

        html_out = _page_scope(mixed_stale_store)
        assert '<div class="stat-number">2</div>' in html_out, (
            "the Invalidated card must show 2 active, not all 6"
        )
        assert '<div class="stat-number">6</div>' not in html_out

    def test_executive_page_accounts_for_retired_rows_separately(
        self, mixed_stale_store
    ):
        from wxcli.migration.report.executive import _page_scope

        html_out = _page_scope(mixed_stale_store).lower()
        assert "retired" in html_out or "no longer" in html_out, (
            "the 4 retired rows must be explained, not silently dropped"
        )

    def test_verdict_does_not_demand_review_of_retired_rows(self, mixed_stale_store):
        from wxcli.migration.report.explainer import generate_verdict
        from wxcli.migration.report.score import compute_complexity_score

        score = compute_complexity_score(mixed_stale_store)
        verdict = generate_verdict(score, mixed_stale_store)
        assert "6 decisions were invalidated" not in verdict
        assert "A further 6" not in verdict

    def test_key_findings_flag_only_the_active_stale(self, mixed_stale_store):
        from wxcli.migration.report.explainer import generate_key_findings

        texts = " ".join(f["text"] for f in generate_key_findings(mixed_stale_store))
        assert "6 decisions were invalidated" not in texts
        if "invalidated" in texts:
            assert "2 decisions were invalidated" in texts

    def test_appendix_separates_the_two_kinds(self, mixed_stale_store):
        from wxcli.migration.report.appendix import _decisions_group

        html_out = _decisions_group(mixed_stale_store)
        assert "6 invalidated by re-analysis" not in html_out
        assert "retired" in html_out.lower()

    def test_all_retired_means_nothing_needs_review(self, tmp_path):
        """A project whose only stale rows are retired must not raise an alarm."""
        from wxcli.migration.report.executive import _page_scope

        store = MigrationStore(tmp_path / "retired_only.db")
        for i in range(3):
            store.save_decision({
                "decision_id": store.next_decision_id(),
                "type": DecisionType.DEVICE_FIRMWARE_CONVERTIBLE.value,
                "severity": "MEDIUM",
                "summary": f"convertible {i}",
                "context": {},
                "options": [{"id": "convert", "label": "Convert", "impact": "Reflash"}],
                "fingerprint": f"c-{i}",
                "run_id": "r",
                "chosen_option": STALE,
                "resolved_by": "stale",
            })
        html_out = _page_scope(store)
        store.close()
        assert "need review" not in html_out.lower()
        assert '<div class="stat-number">3</div>' not in html_out


# ---------------------------------------------------------------------------
# Appendix B — Decision Detail
# ---------------------------------------------------------------------------

class TestAppendixDecisionDetail:
    def test_stale_rows_are_not_labelled_auto_resolved(self, stale_heavy_store):
        """The headline symptom: 5 stale rows rendered as "Auto-resolved"."""
        from wxcli.migration.report.appendix import _decisions_group

        html_out = _decisions_group(stale_heavy_store)
        assert html_out.count("<td>Auto-resolved</td>") == 2, (
            "only the 2 genuinely resolved decisions may be labelled Auto-resolved"
        )
        assert html_out.count("<td>Invalidated</td>") == 5, (
            "the 5 stale device decisions must be labelled as invalidated"
        )

    def test_stale_population_is_visible(self, stale_heavy_store):
        from wxcli.migration.report.appendix import _decisions_group

        html_out = _decisions_group(stale_heavy_store)
        assert "nvalidated" in html_out, "the invalidated population must be named"
        assert "5 invalidated" in html_out

    def test_per_type_resolution_excludes_stale(self, stale_heavy_store):
        """DEVICE_INCOMPATIBLE read 5/5 resolved; nothing resolved any of them."""
        from wxcli.migration.report.appendix import _decisions_group

        html_out = _decisions_group(stale_heavy_store)
        assert "5/5 resolved" not in html_out

    def test_incompatible_devices_still_appear(self, stale_heavy_store):
        """Excluding stale from the *counts* must not hide the hardware facts.

        The 91 HIGH-severity incompatible devices in the real dataset are the
        reason this report exists — suppressing the section would trade one
        misstatement for a worse omission.
        """
        from wxcli.migration.report.appendix import _decisions_group

        html_out = _decisions_group(stale_heavy_store)
        assert "CP-7962G" in html_out


# ---------------------------------------------------------------------------
# Executive summary — effort bands and stat grid
# ---------------------------------------------------------------------------

class TestExecutiveEffortBands:
    def test_stale_decisions_do_not_migrate_automatically(self, stale_heavy_store):
        """A stale DEVICE_INCOMPATIBLE is manual work, not an auto-resolution."""
        from wxcli.migration.report.executive import _classify_decisions

        auto, planning, manual = _classify_decisions(stale_heavy_store.get_all_decisions())
        assert len(auto) == 2, "only genuinely resolved decisions migrate automatically"
        assert len(manual) == 5, "the 5 invalidated device decisions are manual work"

    def test_stat_grid_does_not_overstate_auto_resolved(self, stale_heavy_store):
        from wxcli.migration.report.executive import _page_scope

        html_out = _page_scope(stale_heavy_store)
        assert '<div class="stat-number">7</div>' not in html_out, (
            "7 = 2 genuinely resolved + 5 stale counted as resolved"
        )
        assert '<div class="stat-number">2</div>' in html_out

    def test_resolution_bar_excludes_stale(self, stale_heavy_store):
        from wxcli.migration.report.executive import _page_scope

        html_out = _page_scope(stale_heavy_store)
        assert "7 of 8" not in html_out

    def test_invalidated_population_is_surfaced(self, stale_heavy_store):
        """An operator reading page 3 must be able to see the 5 invalidated rows."""
        from wxcli.migration.report.executive import _page_scope

        html_out = _page_scope(stale_heavy_store)
        assert "nvalidated" in html_out


# ---------------------------------------------------------------------------
# Explainer — verdict and key findings
# ---------------------------------------------------------------------------

class TestExplainerNarrative:
    def test_verdict_does_not_claim_stale_decisions_were_resolved(self, stale_heavy_store):
        from wxcli.migration.report.explainer import generate_verdict
        from wxcli.migration.report.score import compute_complexity_score

        score = compute_complexity_score(stale_heavy_store)
        verdict = generate_verdict(score, stale_heavy_store)
        assert "of 8 decisions" not in verdict, (
            "denominator must be the live population (3), not the total (8)"
        )
        assert "All 8 decisions" not in verdict

    def test_key_findings_do_not_claim_stale_decisions_were_resolved(self, stale_heavy_store):
        from wxcli.migration.report.explainer import generate_key_findings

        texts = " ".join(f["text"] for f in generate_key_findings(stale_heavy_store))
        # 8 is the inflated denominator — 5 of those rows are invalidated.
        assert "of 8 decisions" not in texts, (
            "denominator must be the live population (3), not the total (8)"
        )
