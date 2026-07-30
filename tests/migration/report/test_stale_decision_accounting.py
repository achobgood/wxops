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
    STALE,
    DecisionCounts,
    count_decisions,
    is_pending,
    is_resolved,
    is_stale,
    live,
    stale_only,
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

    def test_live_and_stale_only_partition_the_population(self):
        decisions = [
            {"chosen_option": None},
            {"chosen_option": STALE},
            {"chosen_option": STALE},
            {"chosen_option": "accept"},
        ]
        assert len(live(decisions)) == 2
        assert len(stale_only(decisions)) == 2
        assert len(live(decisions)) + len(stale_only(decisions)) == len(decisions)

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
    assert counts == DecisionCounts(total=8, resolved=2, pending=1, stale=5)
    assert counts.live_total == 3


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
