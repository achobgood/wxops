"""The invalidated decision population must be visible from the CLI (F15).

``wxcli cucm status`` reported ``Decisions: 180 total (180 resolved, 0 pending)``
on a project whose decisions table held 1579 rows, 1399 of them stale. An
operator could not see that 89% of the project's decisions had been invalidated,
and ``wxcli cucm decisions`` hard-excluded stale rows with no filter to reach
them — so there was nothing to look at even after being told to look.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from wxcli.migration.decision_state import STALE
from wxcli.migration.models import DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.commands.cucm import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    current_file = tmp_path / "current_project"
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr("wxcli.commands.cucm.CURRENT_PROJECT_FILE", current_file)
    return migrations_dir


@pytest.fixture()
def stale_heavy_project(tmp_migrations_dir):
    """A project in the dcloud-fresh shape: mostly-invalidated decisions."""
    runner.invoke(app, ["init", "stale-proj"])
    store = MigrationStore(tmp_migrations_dir / "stale-proj" / "migration.db")
    run_id = "20260729T120000-fixture"

    for i in range(9):
        store.save_decision({
            "decision_id": store.next_decision_id(),
            "type": DecisionType.DEVICE_INCOMPATIBLE.value,
            "severity": "HIGH",
            "summary": f"CP-7962G device {i} is incompatible",
            "context": {"model": "CP-7962G"},
            "options": [{"id": "replace", "label": "Replace", "impact": "1 phone"}],
            "fingerprint": f"dev-{i}",
            "run_id": run_id,
            "chosen_option": STALE,
            "resolved_by": "stale",
        })
    store.save_decision({
        "decision_id": store.next_decision_id(),
        "type": DecisionType.FEATURE_APPROXIMATION.value,
        "severity": "MEDIUM",
        "summary": "Hunt group maps to REGULAR",
        "context": {},
        "options": [{"id": "accept", "label": "Accept", "impact": "Minor"}],
        "fingerprint": "fa-1",
        "run_id": run_id,
        "chosen_option": "accept",
        "resolved_by": "auto_rule",
    })
    store.close()
    return tmp_migrations_dir


class TestStatusReportsInvalidated:
    def test_status_names_the_invalidated_population(self, stale_heavy_project):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "nvalidated" in result.output, (
            "status must disclose that 9 of 10 decisions were invalidated"
        )
        assert "9" in result.output

    def test_status_does_not_call_stale_decisions_resolved(self, stale_heavy_project):
        result = runner.invoke(app, ["status"])
        assert "10 resolved" not in result.output
        assert "(1 resolved, 0 pending)" in result.output

    def test_status_points_at_a_command_that_can_show_them(self, stale_heavy_project):
        """A prompt to inspect is only useful if the command it names works."""
        result = runner.invoke(app, ["status"])
        assert "--status stale" in result.output

    def test_decision_block_prints_even_when_everything_is_stale(
        self, tmp_migrations_dir
    ):
        """`if non_stale:` suppressed the whole block when nothing was live."""
        runner.invoke(app, ["init", "all-stale"])
        store = MigrationStore(tmp_migrations_dir / "all-stale" / "migration.db")
        store.save_decision({
            "decision_id": store.next_decision_id(),
            "type": DecisionType.DEVICE_INCOMPATIBLE.value,
            "severity": "HIGH",
            "summary": "Only decision, invalidated",
            "context": {},
            "options": [{"id": "replace", "label": "Replace", "impact": "1 phone"}],
            "fingerprint": "only-1",
            "run_id": "r1",
            "chosen_option": STALE,
            "resolved_by": "stale",
        })
        store.close()

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Decisions:" in result.output, (
            "a project whose every decision is invalidated said nothing at all"
        )
        assert "nvalidated" in result.output


class TestDecisionsCanShowStale:
    def test_status_stale_filter_returns_the_invalidated_rows(self, stale_heavy_project):
        result = runner.invoke(app, ["decisions", "--status", "stale"])
        assert result.exit_code == 0
        assert "No decisions found" not in result.output
        assert "CP-7962G" in result.output

    def test_stale_rows_stay_out_of_the_default_listing(self, stale_heavy_project):
        result = runner.invoke(app, ["decisions"])
        assert result.exit_code == 0
        assert "CP-7962G" not in result.output, (
            "default listing must still exclude invalidated decisions"
        )

    def test_stale_rows_stay_out_of_pending_and_resolved(self, stale_heavy_project):
        pending = runner.invoke(app, ["decisions", "--status", "pending"])
        resolved = runner.invoke(app, ["decisions", "--status", "resolved"])
        assert "CP-7962G" not in pending.output
        assert "CP-7962G" not in resolved.output

    def test_stale_filter_is_documented_in_help(self):
        result = runner.invoke(app, ["decisions", "--help"])
        assert "stale" in result.output.lower(), (
            "a filter value the operator is told to use must appear in --help"
        )

    def test_stale_listing_does_not_call_them_resolved(self, stale_heavy_project):
        """The F04 truthiness bug must not reappear in the listing it feeds.

        ``chosen_option='__stale__'`` is not None, so the summary line's
        ``resolved = len(decs) - pending`` would report "0 pending, 9 resolved".
        """
        result = runner.invoke(app, ["decisions", "--status", "stale"])
        assert "9 resolved" not in result.output
        assert "9 invalidated" in result.output

    def test_stale_rows_render_a_readable_status(self, stale_heavy_project):
        """The raw sentinel is an internal token, not an operator-facing word."""
        result = runner.invoke(app, ["decisions", "--status", "stale"])
        assert "__stale__" not in result.output
        assert "invalidated" in result.output.lower()


class TestRetiredTypesAreNotReportedAsProblems:
    """Retired decision types must not be counted as needing review."""

    @pytest.fixture()
    def retired_stale_project(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "retired-proj"])
        store = MigrationStore(tmp_migrations_dir / "retired-proj" / "migration.db")
        for i in range(6):
            store.save_decision({
                "decision_id": store.next_decision_id(),
                "type": DecisionType.DEVICE_FIRMWARE_CONVERTIBLE.value,
                "severity": "MEDIUM",
                "summary": f"CP-7841 {i} can be converted",
                "context": {},
                "options": [{"id": "convert", "label": "Convert", "impact": "Reflash"}],
                "fingerprint": f"conv-{i}",
                "run_id": "r1",
                "chosen_option": STALE,
                "resolved_by": "stale",
            })
        for i in range(2):
            store.save_decision({
                "decision_id": store.next_decision_id(),
                "type": DecisionType.DEVICE_INCOMPATIBLE.value,
                "severity": "HIGH",
                "summary": f"CP-7962G {i} is incompatible",
                "context": {},
                "options": [{"id": "replace", "label": "Replace", "impact": "1 phone"}],
                "fingerprint": f"inc-{i}",
                "run_id": "r1",
                "chosen_option": STALE,
                "resolved_by": "stale",
            })
        store.close()
        return tmp_migrations_dir

    def test_status_reports_active_and_retired_separately(self, retired_stale_project):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "2 invalidated" in result.output, "only the live-type rows need review"
        assert "8 invalidated" not in result.output
        assert "6 retired" in result.output

    def test_status_does_not_ask_for_action_on_retired_rows(self, retired_stale_project):
        """The inspect prompt is tied to the population that needs inspecting."""
        result = runner.invoke(app, ["status"])
        assert "No action needed" in result.output
