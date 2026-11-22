"""`models.OP_STATUS_TRANSITIONS` is the whole operation-status machine.

The writers are set-based SQL in three modules. These tests drive each real
writer — no hand-written UPDATEs — record every (before, after) status pair,
and fail if one is missing from the table. Add the edge to the table when you
add a writer; the table is what agents and maintainers read.

Also pins two CLI fixes to the operator overrides:

* `mark-complete` on an already-completed op without `--webex-id` is a no-op.
  It used to overwrite the recorded webex_id with NULL, which dependents and
  rollback-ops both read.
* `mark-failed` reports the cascade of *this* op, not every cascade in the
  plan.
"""

from __future__ import annotations

from datetime import datetime, timezone

import networkx as nx
import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app
from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.engine import reset_in_progress
from wxcli.migration.execute.runtime import mark_ops_in_progress, update_op_status
from wxcli.migration.models import (
    OP_STATUS_TRANSITIONS,
    CanonicalLocation,
    MigrationStatus,
    OpStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore

runner = CliRunner()

A, B, C, D = (
    "location:a:create", "location:b:create", "location:c:create", "location:d:create",
)


def _plan(store: MigrationStore) -> None:
    """A → B → C (hard chain) and an independent D."""
    prov = Provenance(source_system="cucm", source_id="pk", source_name="t",
                      extracted_at=datetime.now(timezone.utc))
    for node in (A, B, C, D):
        cid = node.rsplit(":", 1)[0]
        store.upsert_object(CanonicalLocation(
            canonical_id=cid, provenance=prov, name=cid,
            time_zone="America/New_York", preferred_language="en_US",
            announcement_language="en_us", status=MigrationStatus.ANALYZED,
        ))
    G = nx.DiGraph()
    for tier, node in enumerate((A, B, C, D)):
        G.add_node(node, canonical_id=node.rsplit(":", 1)[0], op_type="create",
                   resource_type="location", tier=tier, batch="org-wide",
                   api_calls=1, description=node)
    G.add_edge(A, B, type=DependencyType.REQUIRES)
    G.add_edge(B, C, type=DependencyType.REQUIRES)
    save_plan_to_store(G, store)


def _statuses(store: MigrationStore) -> dict[str, str]:
    rows = store.conn.execute("SELECT node_id, status FROM plan_operations")
    return {r["node_id"]: r["status"] for r in rows}


class _Recorder:
    """Snapshot statuses around each writer call and collect the edges."""

    def __init__(self, store: MigrationStore):
        self.store = store
        self.edges: set[tuple[str, str]] = set()

    def __call__(self, fn, *args, **kwargs):
        before = _statuses(self.store)
        fn(*args, **kwargs)
        after = _statuses(self.store)
        for node, old in before.items():
            if after[node] != old:
                self.edges.add((old, after[node]))


def _assert_in_table(edges: set[tuple[str, str]]) -> None:
    illegal = sorted(
        (a, b) for a, b in edges
        if OpStatus(b) not in OP_STATUS_TRANSITIONS[OpStatus(a)]
    )
    assert illegal == [], (
        f"writers produced edges missing from OP_STATUS_TRANSITIONS: {illegal}"
    )


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "t.db")
    _plan(s)
    yield s
    s.close()


def _retry_failed(store: MigrationStore) -> None:
    """The exact statement `wxcli cucm retry-failed` runs."""
    store.conn.execute(
        "UPDATE plan_operations SET status = 'pending', error_message = NULL "
        "WHERE status = 'failed'"
    )
    store.conn.commit()


class TestEveryWriterStaysInsideTheTable:
    def test_crash_recovery_path(self, store):
        rec = _Recorder(store)
        rec(mark_ops_in_progress, store, [A, D])
        rec(reset_in_progress, store)
        assert rec.edges == {("pending", "in_progress"), ("in_progress", "pending")}
        _assert_in_table(rec.edges)

    def test_fail_cascade_retry_recover_path(self, store):
        rec = _Recorder(store)
        rec(mark_ops_in_progress, store, [A])
        rec(update_op_status, store, A, "failed", error_message="500")
        assert _statuses(store)[C] == "skipped"  # cascade reached the leaf
        rec(_retry_failed, store)
        rec(update_op_status, store, A, "completed", webex_id="loc-1")
        assert _statuses(store)[B] == "pending"  # cascade undone
        assert _statuses(store)[C] == "pending"
        assert ("pending", "skipped") in rec.edges
        assert ("skipped", "pending") in rec.edges
        assert ("failed", "pending") in rec.edges
        _assert_in_table(rec.edges)

    def test_explicit_skip_and_operator_overrides(self, store):
        rec = _Recorder(store)
        rec(update_op_status, store, D, "skipped", error_message="not needed")
        rec(update_op_status, store, A, "failed", error_message="x")
        rec(update_op_status, store, A, "completed", webex_id="found")  # mark-complete
        rec(update_op_status, store, B, "in_progress")
        rec(update_op_status, store, B, "failed", error_message="y")
        rec(update_op_status, store, B, "skipped", error_message="give up")  # --skip
        _assert_in_table(rec.edges)

    def test_completed_is_terminal_for_the_engine(self):
        assert OP_STATUS_TRANSITIONS[OpStatus.COMPLETED] == frozenset()

    def test_every_status_has_a_row(self):
        assert set(OP_STATUS_TRANSITIONS) == set(OpStatus)


# ---------------------------------------------------------------------------
# CLI operator overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_project(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr(
        "wxcli.commands.cucm.CURRENT_PROJECT_FILE", tmp_path / "current_project"
    )
    res = runner.invoke(app, ["init", "test-project"])
    assert res.exit_code == 0, res.output
    project_dir = migrations_dir / "test-project"
    s = MigrationStore(project_dir / "migration.db")
    _plan(s)
    s.close()
    return project_dir


def _row(project_dir, node):
    s = MigrationStore(project_dir / "migration.db")
    try:
        r = s.conn.execute(
            "SELECT status, webex_id FROM plan_operations WHERE node_id = ?", (node,)
        ).fetchone()
        return dict(r)
    finally:
        s.close()


class TestMarkComplete:
    def test_remark_without_webex_id_keeps_the_recorded_id(self, cli_project):
        assert runner.invoke(app, ["mark-complete", A, "--webex-id", "loc-1"]).exit_code == 0
        res = runner.invoke(app, ["mark-complete", A])
        assert res.exit_code == 0, res.output
        assert "Already completed" in res.output
        assert _row(cli_project, A) == {"status": "completed", "webex_id": "loc-1"}

    def test_remark_with_webex_id_still_corrects_it(self, cli_project):
        runner.invoke(app, ["mark-complete", A, "--webex-id", "loc-1"])
        res = runner.invoke(app, ["mark-complete", A, "--webex-id", "loc-2"])
        assert res.exit_code == 0, res.output
        assert _row(cli_project, A)["webex_id"] == "loc-2"

    def test_node_id_prints_verbatim(self, cli_project):
        """`location:a:create` used to print as `location🅰create` (Rich emoji)."""
        res = runner.invoke(app, ["mark-complete", A, "--webex-id", "loc-1"])
        assert A in res.output


class TestMarkFailedCascadeCount:
    def test_count_is_this_ops_cascade_only(self, cli_project):
        # An unrelated cascade already in the plan: B fails, C is skipped.
        runner.invoke(app, ["mark-failed", B, "--error", "first"])
        # D has no dependents, so it cascades to nothing.
        res = runner.invoke(app, ["mark-failed", D, "--error", "x", "--skip"])
        assert res.exit_code == 0, res.output
        assert "Cascaded to" not in res.output

    def test_failed_reports_its_cascade(self, cli_project):
        res = runner.invoke(app, ["mark-failed", A, "--error", "x"])
        assert res.exit_code == 0, res.output
        assert "Cascaded to 2 dependent operation(s)" in res.output
