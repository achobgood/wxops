"""The pipeline-stage state machine (`wxcli.migration.stages`) and its gate.

Pins three things that used to be spread across `commands/cucm.py`:

1. The rules as data — every gated command has a prerequisite, the order is
   one tuple, invalidation and "what runs next" are pure functions.
2. One gate for every gated command. `report`, `user-diff` and `user-notice`
   each had a hand-rolled copy with its own wording; they now go through
   `_check_prerequisite`, still on stderr so a refusal never reaches a JSON
   stdout.
3. Every refusal and `status` name the literal next command, derived from
   `completed_stages` (authoritative) rather than the forward-only State line.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app
from wxcli.migration.stages import (
    STAGE_ORDER,
    STAGE_PREREQUISITES,
    STATE_IMPLIES_STAGE,
    command_for,
    downstream_of,
    missing_prerequisite,
    next_stage,
    stage_divergence,
)
from wxcli.migration.state import ProjectState

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr(
        "wxcli.commands.cucm.CURRENT_PROJECT_FILE", tmp_path / "current_project"
    )
    return migrations_dir


def _project(migrations_dir: Path, stages: list[str], state: str | None = None) -> Path:
    res = runner.invoke(app, ["init", "test-project"])
    assert res.exit_code == 0, res.output
    project_dir = migrations_dir / "test-project"
    data = json.loads((project_dir / "state.json").read_text())
    data["completed_stages"] = stages
    if state is not None:
        data["state"] = state
    (project_dir / "state.json").write_text(json.dumps(data, indent=2))
    return project_dir


def _flat(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# The rules as data
# ---------------------------------------------------------------------------


class TestRules:
    def test_every_stage_but_init_has_its_predecessor_as_prerequisite(self):
        for prev, stage in zip(STAGE_ORDER, STAGE_ORDER[1:]):
            assert STAGE_PREREQUISITES[stage] == prev

    def test_init_is_never_gated(self):
        assert "init" not in STAGE_PREREQUISITES

    def test_every_prerequisite_is_a_real_stage(self):
        assert set(STAGE_PREREQUISITES.values()) <= set(STAGE_ORDER)

    @pytest.mark.parametrize("cmd", ["report", "user-diff", "user-notice"])
    def test_post_analyze_deliverables_need_analyze(self, cmd):
        assert STAGE_PREREQUISITES[cmd] == "analyze"

    def test_execute_needs_preflight(self):
        assert STAGE_PREREQUISITES["execute"] == "preflight"

    def test_every_project_state_maps_to_a_real_stage(self):
        assert {s.value for s in ProjectState} <= set(STATE_IMPLIES_STAGE)
        assert set(STATE_IMPLIES_STAGE.values()) <= set(STAGE_ORDER)

    def test_every_gated_command_is_a_registered_cli_command(self):
        import typer.main

        click_app = typer.main.get_command(app)
        registered = set(click_app.commands)
        assert set(STAGE_PREREQUISITES) <= registered


class TestPureFunctions:
    def test_missing_prerequisite(self):
        assert missing_prerequisite("plan", ["init", "discover"]) == "analyze"
        assert missing_prerequisite("plan", list(STAGE_ORDER[:5])) is None
        assert missing_prerequisite("status", []) is None
        assert missing_prerequisite("init", []) is None

    def test_downstream_of(self):
        assert downstream_of("analyze") == ["plan", "preflight"]
        assert downstream_of("preflight") == []
        assert downstream_of("report") == []  # not a stage: invalidates nothing

    def test_next_stage(self):
        assert next_stage([]) == "init"
        assert next_stage(["init", "discover", "normalize"]) == "map"
        assert next_stage(list(STAGE_ORDER)) is None

    def test_command_for(self):
        assert command_for("analyze") == "wxcli cucm analyze"
        assert command_for("init").startswith("wxcli cucm init ")
        assert "--from-file" in command_for("discover")

    def test_stage_divergence(self):
        assert stage_divergence("planned", ["init", "discover"]) == "plan"
        assert stage_divergence("planned", list(STAGE_ORDER[:6])) is None
        assert stage_divergence("some-future-state", []) is None


# ---------------------------------------------------------------------------
# One gate, naming the next command
# ---------------------------------------------------------------------------


class TestGate:
    def test_refusal_names_the_literal_next_command(self, tmp_migrations_dir):
        _project(tmp_migrations_dir, ["init", "discover", "normalize"])
        res = runner.invoke(app, ["plan"])
        assert res.exit_code == 1
        text = _flat(res.output)
        assert "prerequisite 'analyze'" in text
        assert "Run next: wxcli cucm map" in text

    @pytest.mark.parametrize("cmd,args", [
        ("report", ["--brand", "Acme", "--prepared-by", "SE"]),
        ("user-diff", []),
        ("user-notice", ["--brand", "Acme", "--migration-date", "May 1",
                         "--helpdesk", "x100"]),
    ])
    def test_deliverables_use_the_shared_gate_on_stderr(
        self, tmp_migrations_dir, cmd, args
    ):
        _project(tmp_migrations_dir, ["init", "discover", "normalize", "map"])
        res = runner.invoke(app, [cmd, *args])
        assert res.exit_code == 1
        assert res.stdout == "", "a refusal must never land on a JSON stdout"
        text = _flat(res.stderr)
        assert f"Cannot run '{cmd}'" in text
        assert "prerequisite 'analyze'" in text
        assert "Run next: wxcli cucm analyze" in text


# ---------------------------------------------------------------------------
# status prints the next step
# ---------------------------------------------------------------------------


class TestStatusNextLine:
    def test_status_names_the_next_stage(self, tmp_migrations_dir):
        _project(tmp_migrations_dir, ["init", "discover", "normalize", "map"],
                 state="discovered")
        res = runner.invoke(app, ["status"])
        assert res.exit_code == 0, res.output
        assert "Next: wxcli cucm analyze" in _flat(res.output)

    def test_status_when_every_stage_is_complete(self, tmp_migrations_dir):
        _project(tmp_migrations_dir, list(STAGE_ORDER), state="preflight")
        res = runner.invoke(app, ["status"])
        assert res.exit_code == 0, res.output
        assert "Next: wxcli cucm export, then /cucm-migrate" in _flat(res.output)

    def test_divergent_status_keeps_its_own_next_line_only(self, tmp_migrations_dir):
        _project(tmp_migrations_dir, ["init", "discover", "normalize", "map"],
                 state="planned")
        text = _flat(runner.invoke(app, ["status"]).output)
        assert "Next stage to run: analyze" in text
        assert "Next: wxcli" not in text
