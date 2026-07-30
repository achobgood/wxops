"""F10 + F11 — `analyze`'s headline must agree with its own itemisation.

F10: the headline was `len(result.decisions)`, collected before the advisor
runs, while the itemisation iterates `result.stats`, into which the advisor
inserts its row afterwards. The headline was short by exactly the advisor's
count.

F11: the itemisation printed only `count > 0`, so an analyzer that ran clean
and an analyzer that never ran looked identical.

The itemisation sum is recomputed from the rendered text in these tests rather
than asserted against a constant, so agreement is proven rather than restated.
"""

from __future__ import annotations

import re

from wxcli.commands import cucm as cucm_cli
from wxcli.migration.transform.analyzers import AnalysisResult


def _render(result: AnalysisResult) -> str:
    """Render the summary and collapse Rich's terminal-width wrapping."""
    with cucm_cli.console.capture() as cap:
        cucm_cli._print_analysis_summary(result)
    return " ".join(cap.get().split())


def _itemised_total(text: str) -> int:
    return sum(int(n) for n in re.findall(r"(\d+) decisions", text))


def _headline(text: str) -> int:
    match = re.search(r"Decisions raised: (\d+)", text)
    assert match, f"no headline in output: {text!r}"
    return int(match.group(1))


class TestHeadlineAgreesWithItemisation:
    def test_advisor_row_is_included_in_the_headline(self):
        """The exact F10 shape: 70 printed over a list summing to 85."""
        result = AnalysisResult(
            # Deliberately empty — this is the field the old headline read, and
            # it never contains the advisor's decisions.
            decisions=[],
            stats={
                "missing_data": 66,
                "selective_call_handling": 3,
                "workspace_license": 1,
                "architecture_advisor": 15,
            },
        )
        text = _render(result)
        assert _headline(text) == _itemised_total(text) == 85

    def test_empty_run_does_not_print_zero_over_a_nonzero_row(self):
        """`Decisions produced: 0` directly above `architecture_advisor 1`."""
        result = AnalysisResult(
            decisions=[],
            stats={"missing_data": 0, "architecture_advisor": 1},
        )
        text = _render(result)
        assert _headline(text) == _itemised_total(text) == 1

    def test_zero_everywhere_stays_zero(self):
        result = AnalysisResult(stats={"missing_data": 0, "architecture_advisor": 0})
        text = _render(result)
        assert _headline(text) == _itemised_total(text) == 0


class TestEveryAnalyzerIsAccountedFor:
    def test_clean_analyzer_still_prints_a_line(self):
        """F11 — a clean analyzer must not be silent."""
        result = AnalysisResult(stats={"device_compatibility": 0, "missing_data": 4})
        text = _render(result)
        assert "device_compatibility 0 decisions" in text
        assert "missing_data 4 decisions" in text

    def test_all_analyzers_appear_even_when_all_are_clean(self):
        names = [f"analyzer_{i:02d}" for i in range(15)]
        result = AnalysisResult(stats=dict.fromkeys(names, 0))
        text = _render(result)
        for name in names:
            assert f"{name} 0 decisions" in text

    def test_failed_analyzer_marks_the_headline_incomplete(self):
        """A count that could not be produced must not read as a clean total."""
        result = AnalysisResult(stats={"missing_data": 4, "cross_site": -1})
        text = _render(result)
        assert _headline(text) == 4
        assert "incomplete" in text
        assert "1 of 2 analyzers FAILED" in text
        assert "cross_site FAILED" in text

    def test_no_failures_means_no_incomplete_caveat(self):
        result = AnalysisResult(stats={"missing_data": 4})
        text = _render(result)
        assert "incomplete" not in text
        assert "FAILED" not in text


class TestMergeOutcomeIsSeparateFromWhatWasRaised:
    def test_raised_and_stored_are_reported_as_different_questions(self):
        result = AnalysisResult(
            stats={"missing_data": 100},
            merge_counts={
                "new": 12, "updated": 28, "kept": 15,
                "stale": 500, "invalidated": 111,
            },
        )
        text = _render(result)
        # 100 were raised; only 12 of them were new to the store.
        assert _headline(text) == 100
        assert "Store: 12 new, 28 updated, 15 already resolved and still current" in text

    def test_invalidated_population_is_split_by_whether_it_was_answered(self):
        result = AnalysisResult(
            stats={"missing_data": 100},
            merge_counts={
                "new": 12, "updated": 28, "kept": 15,
                "stale": 500, "invalidated": 111,
            },
        )
        text = _render(result)
        assert "Invalidated by this run: 611 no longer detected" in text
        assert "111 of them had already been answered" in text
        assert "decisions --status stale" in text

    def test_no_invalidated_line_when_nothing_was_invalidated(self):
        result = AnalysisResult(
            stats={"missing_data": 4},
            merge_counts={"new": 4, "updated": 0, "kept": 0, "stale": 0, "invalidated": 0},
        )
        text = _render(result)
        assert "Invalidated by this run" not in text
        assert "--status stale" not in text

    def test_no_store_line_when_merge_counts_absent(self):
        result = AnalysisResult(stats={"missing_data": 4})
        text = _render(result)
        assert "Store:" not in text
