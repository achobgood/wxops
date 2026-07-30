"""F13 — `ProjectState` and `completed_stages` diverge permanently.

Re-running an earlier stage calls `_invalidate_downstream`, which rolls
`completed_stages` back. `ProjectState` cannot follow: `VALID_TRANSITIONS` has
no backwards edges. `status` then printed the stale `ProjectState` *first*, and
the `cucm-migrate` skill's first checkpoint tells an agent to read exactly that
line to confirm the stage is ANALYZED or later.

Adam's F07 precedent applies: flag on read, never rewrite. These tests pin both
halves — the divergence is disclosed, and `state.json` is left byte-identical.

The two fixtures below are the shapes measured on disk in ~/.wxcli/migrations:
  dcloud-demo   state=planned    stages end at map
  vidcast-demo  state=preflight  stages end at analyze
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import (
    STAGE_ORDER,
    STATE_IMPLIES_STAGE,
    _stage_divergence,
    app,
)

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


def _project(migrations_dir: Path, state: str, stages: list[str]) -> Path:
    runner.invoke(app, ["init", "test-project"])
    project_dir = migrations_dir / "test-project"
    data = json.loads((project_dir / "state.json").read_text())
    data["state"] = state
    data["completed_stages"] = stages
    (project_dir / "state.json").write_text(json.dumps(data, indent=2))
    return project_dir


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _flat(text: str) -> str:
    return " ".join(text.split())


class TestDivergenceDetection:
    def test_agreement_returns_none(self):
        assert _stage_divergence(
            "preflight",
            ["init", "discover", "normalize", "map", "analyze", "plan", "preflight"],
        ) is None

    def test_dcloud_demo_shape(self):
        """state=planned over stages ending at map."""
        assert _stage_divergence(
            "planned", ["init", "discover", "normalize", "map"]
        ) == "plan"

    def test_vidcast_demo_shape(self):
        """state=preflight over stages ending at analyze."""
        assert _stage_divergence(
            "preflight", ["init", "discover", "normalize", "map", "analyze"]
        ) == "preflight"

    def test_ready_and_blocked_only_require_analyze(self):
        stages = ["init", "discover", "normalize", "map", "analyze"]
        assert _stage_divergence("ready", stages) is None
        assert _stage_divergence("blocked", stages) is None

    def test_unknown_state_does_not_raise_a_false_alarm(self):
        assert _stage_divergence("some-future-state", ["init"]) is None

    def test_every_project_state_has_a_mapping(self):
        """A new ProjectState with no mapping would silently never flag."""
        from wxcli.migration.state import ProjectState

        missing = [s.value for s in ProjectState if s.value not in STATE_IMPLIES_STAGE]
        assert missing == []

    def test_every_mapped_stage_is_a_real_stage(self):
        assert set(STATE_IMPLIES_STAGE.values()) <= set(STAGE_ORDER)


class TestStatusDisclosesIt:
    def test_status_flags_the_divergence_and_names_the_next_stage(
        self, tmp_migrations_dir
    ):
        _project(tmp_migrations_dir, "planned", ["init", "discover", "normalize", "map"])

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        text = _flat(result.output)

        assert "STALE" in text
        assert "State and stages disagree" in text
        assert "`state` is `planned`, which requires the `plan` stage" in text
        assert "`Stages` is authoritative" in text
        assert "Next stage to run: analyze" in text

    def test_status_says_nothing_when_they_agree(self, tmp_migrations_dir):
        _project(
            tmp_migrations_dir,
            "analyzed",
            ["init", "discover", "normalize", "map", "analyze"],
        )

        result = runner.invoke(app, ["status"])
        text = _flat(result.output)
        assert "STALE" not in text
        assert "State and stages disagree" not in text

    def test_status_does_not_rewrite_state_json(self, tmp_migrations_dir):
        """Flag on read, never rewrite — the F07 precedent."""
        project_dir = _project(
            tmp_migrations_dir,
            "preflight",
            ["init", "discover", "normalize", "map", "analyze"],
        )
        state_path = project_dir / "state.json"
        before = _md5(state_path)

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "State and stages disagree" in _flat(result.output)

        assert _md5(state_path) == before
        data = json.loads(state_path.read_text())
        assert data["state"] == "preflight"
        assert data["completed_stages"] == [
            "init", "discover", "normalize", "map", "analyze",
        ]
