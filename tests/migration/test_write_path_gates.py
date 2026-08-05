"""The two guards protecting the one path that writes to a customer's live org.

Both added 2026-08-05, both closing gaps this repository had already built the
machinery for and applied everywhere except here.

**1. `execute` had no prerequisite at all.** Every read stage
(`discover`→`normalize`→`map`→`analyze`→`plan`→`preflight`) refuses to run until
its predecessor completes, via `_check_prerequisite`. So does `report`, which
merely writes an HTML file. `execute` — 20-way concurrent, unattended, writing to
a live org — checked nothing, while the cucm-migrate skill called preflight
"MANDATORY. No override or bypass" in a prompt file.

**2. `normalize` silently erased the execution record.** It calls
`store.clear_all()`, which empties every table including `plan_operations` (every
`webex_id`) and `decisions` (every resolved approval). No prompt, no warning, and
`--help` said only "Run pass 1 normalizers + pass 2 cross-reference builder."
Unlike `plan` — which now carries the record forward — `normalize` rebuilds
`objects` from raw_data and every other table hangs off it by foreign key, so it
cannot preserve. Refusing is the only honest option.

Tracked deliberately — `tests/migration/**` is re-included at `.gitignore:56-57`.
A guard pinned by an untracked test is a guard pinned by nothing.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app
from wxcli.migration.store import MigrationStore

runner = CliRunner()

ALL_READ_STAGES = ["init", "discover", "normalize", "map", "analyze", "plan"]


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr(
        "wxcli.commands.cucm.CURRENT_PROJECT_FILE", tmp_path / "current"
    )
    return migrations_dir


def _project(migrations_dir, stages, name="p1"):
    res = runner.invoke(app, ["init", name])
    assert res.exit_code == 0, res.output
    path = migrations_dir / name / "state.json"
    data = json.loads(path.read_text())
    data["completed_stages"] = list(stages)
    path.write_text(json.dumps(data))
    return migrations_dir / name


def _seed_completed_op(project_dir, webex_id="wx-loc-1"):
    """One executed operation, as a real `execute` run would have left it."""
    store = MigrationStore(project_dir / "migration.db")
    store.conn.execute("PRAGMA foreign_keys=OFF")
    store.conn.execute(
        "INSERT INTO plan_operations (node_id, canonical_id, op_type, "
        "resource_type, tier, batch, status, webex_id) "
        "VALUES ('location:hq:create','location:hq','create','location',0,"
        "'org-wide','completed',?)", (webex_id,),
    )
    store.conn.commit()
    store.close()


class TestExecuteRequiresPreflight:
    def test_execute_refuses_without_a_passing_preflight(self, tmp_migrations_dir):
        _project(tmp_migrations_dir, ALL_READ_STAGES)   # no "preflight"

        res = runner.invoke(app, ["execute", "-p", "p1"])

        assert res.exit_code == 1, res.output
        assert "preflight" in res.output
        assert "prerequisite" in res.output.lower()

    def test_the_gate_runs_before_anything_opens_the_store_or_a_socket(
        self, tmp_migrations_dir
    ):
        """Order matters: refusing after resolving a token would still have
        reached the network for the licence lookup."""
        _project(tmp_migrations_dir, ALL_READ_STAGES)

        res = runner.invoke(app, ["execute", "-p", "p1"])

        assert "Starting migration execution" not in res.output
        assert "No token" not in res.output

    def test_a_passing_preflight_gets_past_the_gate(self, tmp_migrations_dir):
        """Positive case: the gate opens and the command reaches the next check.

        `resolve_token` is forced to None so this stops at `execute`'s own
        no-token guard. That is deliberate and load-bearing, not convenience:
        without it this test reaches `get_api()` and issues a real
        `GET /v1/licenses` against whatever org the developer's (or CI's) token
        points at. A test in `tests/migration/**` runs on every PR, so a live
        call here would be a live call for everyone.
        """
        _project(tmp_migrations_dir, ALL_READ_STAGES + ["preflight"])

        with patch("wxcli.auth.resolve_token", return_value=None):
            res = runner.invoke(app, ["execute", "-p", "p1"])

        assert "prerequisite" not in res.output.lower(), res.output
        assert "No token" in res.output, (
            "expected to reach the no-token guard, which sits immediately after "
            "the prerequisite check — that is what proves the gate opened"
        )

    def test_a_partial_preflight_does_not_open_the_gate(self, tmp_migrations_dir):
        """`preflight --check <one>` never marks the stage (finding F07), so the
        two guards compose: a partial run cannot satisfy this one either."""
        _project(tmp_migrations_dir, ALL_READ_STAGES)   # partial run marked nothing

        res = runner.invoke(app, ["execute", "-p", "p1"])
        assert res.exit_code == 1


class TestNormalizeRefusesToEraseTheRecord:
    def _ready_to_normalize(self, migrations_dir):
        project_dir = _project(migrations_dir, ["init", "discover"])
        (project_dir / "raw_data.json").write_text("{}")
        return project_dir

    def test_it_refuses_once_operations_have_been_executed(self, tmp_migrations_dir):
        project_dir = self._ready_to_normalize(tmp_migrations_dir)
        _seed_completed_op(project_dir)

        res = runner.invoke(app, ["normalize", "-p", "p1"])

        assert res.exit_code == 1, res.output
        assert "Refusing to re-normalize" in res.output

    def test_the_refusal_names_the_count_and_the_way_out(self, tmp_migrations_dir):
        project_dir = self._ready_to_normalize(tmp_migrations_dir)
        _seed_completed_op(project_dir)

        res = runner.invoke(app, ["normalize", "-p", "p1"])

        assert "1 operation(s) have already been executed" in res.output
        assert "rollback-ops" in res.output      # how to see what exists
        assert "wxcli cucm plan" in res.output   # the non-destructive alternative
        assert "--force" in res.output

    def test_the_record_is_still_there_after_the_refusal(self, tmp_migrations_dir):
        """A guard that aborts after clear_all() would be worse than none."""
        project_dir = self._ready_to_normalize(tmp_migrations_dir)
        _seed_completed_op(project_dir, webex_id="wx-survives")

        runner.invoke(app, ["normalize", "-p", "p1"])

        store = MigrationStore(project_dir / "migration.db")
        row = store.conn.execute(
            "SELECT status, webex_id FROM plan_operations"
        ).fetchone()
        store.close()
        assert row["status"] == "completed"
        assert row["webex_id"] == "wx-survives"

    def test_it_does_not_refuse_when_nothing_has_been_executed(
        self, tmp_migrations_dir
    ):
        """The common case must stay unblocked — re-normalizing after a config
        change is an ordinary operation the pipeline expects."""
        self._ready_to_normalize(tmp_migrations_dir)

        res = runner.invoke(app, ["normalize", "-p", "p1"])

        assert "Refusing to re-normalize" not in res.output

    def test_force_is_the_documented_way_through(self, tmp_migrations_dir):
        project_dir = self._ready_to_normalize(tmp_migrations_dir)
        _seed_completed_op(project_dir)

        res = runner.invoke(app, ["normalize", "-p", "p1", "--force"])

        assert "Refusing to re-normalize" not in res.output

    def test_force_help_states_what_it_destroys(self):
        """`--force` on the 202 generated commands says only "Skip confirmation".
        This one has to do better — it is erasing the record of remote writes."""
        res = runner.invoke(app, ["normalize", "--help"])
        assert "ERASES" in res.output
        assert "webexId" in res.output
