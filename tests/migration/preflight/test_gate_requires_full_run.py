"""`--check <one>` must not satisfy the mandatory preflight gate (finding F07).

`cucm.py` marked the preflight stage complete and advanced ProjectState whenever
`overall != FAIL`. So `wxcli cucm preflight --check rate-limit` ran one check that
needs no Webex data, yielded PASS, and left a state.json indistinguishable at a
glance from a full 10-check pass.

Three saved projects in the user's own migration directory are in exactly that
state. Per Adam's decision (2026-07-30) those files are **not rewritten** — the
fix makes an existing partial pass legible on read, and stops new ones counting.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app
from wxcli.migration.preflight import PreflightError

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr(
        "wxcli.commands.cucm.CURRENT_PROJECT_FILE", tmp_path / "current"
    )
    return migrations_dir


def _state(migrations_dir, name="p1") -> dict:
    return json.loads((migrations_dir / name / "state.json").read_text())


def _seed_up_to_plan(migrations_dir, name="p1") -> None:
    """`preflight` refuses to run until `plan` is complete — satisfy that."""
    path = migrations_dir / name / "state.json"
    data = json.loads(path.read_text())
    data["completed_stages"] = [
        "init", "discover", "normalize", "map", "analyze", "plan",
    ]
    path.write_text(json.dumps(data))


class TestPartialRunDoesNotSatisfyTheGate:
    def test_single_check_does_not_mark_the_stage_complete(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "p1"])
        _seed_up_to_plan(tmp_migrations_dir)
        result = runner.invoke(app, ["preflight", "--check", "rate-limit"])
        assert result.exit_code == 0, result.output

        state = _state(tmp_migrations_dir)
        assert "preflight" not in state.get("completed_stages", []), (
            "one check must not complete a gate the skill calls NOT SKIPPABLE"
        )

    def test_single_check_says_the_gate_is_not_satisfied(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "p1"])
        _seed_up_to_plan(tmp_migrations_dir)
        result = runner.invoke(app, ["preflight", "--check", "rate-limit"])
        assert "NOT satisfied" in result.output
        assert "of 10 checks" in result.output

    def test_the_recorded_total_is_written_so_partial_is_legible(
        self, tmp_migrations_dir
    ):
        runner.invoke(app, ["init", "p1"])
        _seed_up_to_plan(tmp_migrations_dir)
        runner.invoke(app, ["preflight", "--check", "rate-limit"])
        state = _state(tmp_migrations_dir)
        assert state["preflight_checks_total"] == 10
        assert len(state["preflight_checks"]) == 1


class TestStatusDisclosesAPartialPass:
    def test_status_reports_coverage_not_just_the_verdict(self, tmp_migrations_dir):
        """The three existing projects are read, never rewritten."""
        runner.invoke(app, ["init", "p1"])
        # Hand-write the exact shape found on disk: PASS over one check, and no
        # preflight_checks_total (those files predate the field).
        path = tmp_migrations_dir / "p1" / "state.json"
        data = json.loads(path.read_text())
        data["completed_stages"] = [
            "init", "discover", "normalize", "map", "analyze", "plan", "preflight",
        ]
        data["preflight_result"] = "PASS"
        data["preflight_checks"] = [
            {"name": "Rate limit budget", "status": "PASS", "detail": "ok"}
        ]
        path.write_text(json.dumps(data))

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "PARTIAL" in result.output
        assert "1 of 10 checks" in result.output
        assert "gate is NOT satisfied" in result.output
        assert "Rate limit budget" in result.output

    def test_status_does_not_rewrite_the_state_file(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "p1"])
        path = tmp_migrations_dir / "p1" / "state.json"
        data = json.loads(path.read_text())
        data["preflight_result"] = "PASS"
        data["preflight_checks"] = [
            {"name": "Rate limit budget", "status": "PASS", "detail": "ok"}
        ]
        path.write_text(json.dumps(data))
        before = path.read_text()

        runner.invoke(app, ["status"])
        assert path.read_text() == before, "status must be read-only on state.json"

    def test_full_pass_reads_as_a_full_pass(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "p1"])
        path = tmp_migrations_dir / "p1" / "state.json"
        data = json.loads(path.read_text())
        data["preflight_result"] = "PASS"
        data["preflight_checks_total"] = 10
        data["preflight_checks"] = [
            {"name": f"c{i}", "status": "PASS", "detail": "ok"} for i in range(10)
        ]
        path.write_text(json.dumps(data))

        result = runner.invoke(app, ["status"])
        assert "PARTIAL" not in result.output
        assert "all 10 checks" in result.output


class TestIncompleteDoesNotSatisfyTheGate:
    def test_incomplete_overall_leaves_the_stage_incomplete(self, tmp_migrations_dir):
        """A full run whose fetches all failed must not complete the gate either."""
        runner.invoke(app, ["init", "p1"])
        _seed_up_to_plan(tmp_migrations_dir)
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = runner.invoke(app, ["preflight"])

        state = _state(tmp_migrations_dir)
        assert state.get("preflight_result") in ("INCOMPLETE", "FAIL"), result.output
        assert "preflight" not in state.get("completed_stages", [])
