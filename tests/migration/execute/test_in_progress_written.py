"""An op that was dispatched must be distinguishable from one never attempted.

Phase 6 finding D13. `plan_operations` carries an `in_progress` status,
`OpStatus.IN_PROGRESS` is declared, `update_op_status` implements the
transition, `reset_in_progress` exists to recover from it and
`commands/cucm.py` calls it at the top of every run — and **nothing ever wrote
it**. `execute_all_batches` set only `completed`, `failed` and `skipped`.

Two consequences, both closed here:

1. `reset_in_progress` could only ever return 0, so the
   `Reset N in-progress ops to pending` line was unreachable. Dead defensive
   code that reads, to anyone auditing the file, like crash recovery is handled.
2. An operation killed after its POST reached Webex but before the `completed`
   commit landed stayed `pending` — byte-for-byte identical to an operation
   that was never attempted. The next `wxcli cucm execute` re-issued the write.
   `execute/` issues no DELETE, so a duplicate it creates cannot be cleaned up
   by this tool.

These tests pin the write itself, not the recovery policy. They are tracked
(`tests/migration/**` is re-included at `.gitignore:56-57`) because an untracked
test cannot report its own decay — three files in this repo are red for exactly
that reason (`07-testability.md` §3.4).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import networkx as nx
import pytest

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.engine import (
    OpResult,
    execute_all_batches,
    reset_in_progress,
)
from wxcli.migration.execute.runtime import get_next_batch, mark_ops_in_progress
from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture()
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _two_op_plan(store: MigrationStore) -> None:
    """location:hq:create (tier 0) -> user:alice:create (tier 2)."""
    store.upsert_object(
        CanonicalLocation(
            canonical_id="location:hq",
            provenance=_prov(),
            name="HQ",
            time_zone="America/New_York",
            preferred_language="en_US",
            announcement_language="en_us",
            status=MigrationStatus.ANALYZED,
        )
    )
    store.upsert_object(
        CanonicalUser(
            canonical_id="user:alice",
            provenance=_prov(),
            emails=["alice@acme.com"],
            first_name="Alice",
            last_name="Smith",
            location_id="location:hq",
            extension="1001",
            status=MigrationStatus.ANALYZED,
        )
    )
    G = nx.DiGraph()
    G.add_node(
        "location:hq:create", canonical_id="location:hq", op_type="create",
        resource_type="location", tier=0, batch="org-wide", api_calls=1,
        description="Create location HQ",
    )
    G.add_node(
        "user:alice:create", canonical_id="user:alice", op_type="create",
        resource_type="user", tier=2, batch="location:hq", api_calls=1,
        description="Create user alice@acme.com",
    )
    G.add_edge("location:hq:create", "user:alice:create",
               type=DependencyType.REQUIRES)
    save_plan_to_store(G, store)


def _status(store: MigrationStore, node_id: str) -> str:
    row = store.conn.execute(
        "SELECT status FROM plan_operations WHERE node_id = ?", (node_id,)
    ).fetchone()
    return row["status"]


class TestInProgressIsWrittenBeforeDispatch:
    def test_status_is_in_progress_while_the_batch_is_in_flight(self, store):
        """The whole finding in one assertion.

        `run_batch_ops` is the first thing that can put a request on the wire.
        Read the DB from inside it: if the status is still `pending` there, a
        kill at that instant is indistinguishable from never having started.
        """
        _two_op_plan(store)
        observed: list[str] = []

        async def _spy(session, tasks, semaphore, ctx=None, **kwargs):
            for t in tasks:
                observed.append(_status(store, t["op"]["node_id"]))
            return [
                OpResult(node_id=t["op"]["node_id"], status=200,
                         webex_id=f"wx-{i}", body={"id": f"wx-{i}"})
                for i, t in enumerate(tasks)
            ]

        with patch("wxcli.migration.execute.engine.run_batch_ops", _spy):
            asyncio.run(execute_all_batches(store=store, token="t", concurrency=2))

        assert observed == ["in_progress", "in_progress"], (
            "every dispatched op must be in_progress before its first request "
            f"leaves the process; observed {observed}"
        )

    def test_terminal_statuses_still_land(self, store):
        """The in_progress write must not strand ops in it."""
        _two_op_plan(store)

        async def _ok(session, tasks, semaphore, ctx=None, **kwargs):
            return [
                OpResult(node_id=t["op"]["node_id"], status=200,
                         webex_id="wx-1", body={"id": "wx-1"})
                for t in tasks
            ]

        with patch("wxcli.migration.execute.engine.run_batch_ops", _ok):
            summary = asyncio.run(
                execute_all_batches(store=store, token="t", concurrency=2)
            )

        assert summary["completed"] == 2
        assert _status(store, "location:hq:create") == "completed"
        assert _status(store, "user:alice:create") == "completed"
        assert reset_in_progress(store) == 0

    def test_a_killed_run_leaves_recoverable_state(self, store):
        """The crash-recovery path becomes reachable, which was consequence 1.

        Simulate the kill by raising out of `run_batch_ops` after dispatch —
        the same window in which a real SIGKILL lands. Before this fix the op
        was left `pending` and `reset_in_progress` returned 0, so the operator
        saw nothing at all.
        """
        _two_op_plan(store)

        async def _die(session, tasks, semaphore, ctx=None, **kwargs):
            raise KeyboardInterrupt("operator killed the run")

        with patch("wxcli.migration.execute.engine.run_batch_ops", _die):
            with pytest.raises(KeyboardInterrupt):
                asyncio.run(execute_all_batches(store=store, token="t"))

        assert _status(store, "location:hq:create") == "in_progress"
        assert reset_in_progress(store) == 1, (
            "the next run's reset must find the killed op — this is the only "
            "signal the operator gets that a prior run died mid-flight"
        )
        assert _status(store, "location:hq:create") == "pending"


class TestMarkOpsInProgress:
    def test_only_pending_ops_are_moved(self, store):
        """Guarded on `pending` so a re-entrant call cannot resurrect an op."""
        _two_op_plan(store)
        store.conn.execute(
            "UPDATE plan_operations SET status = 'completed' "
            "WHERE node_id = 'location:hq:create'"
        )
        store.conn.commit()

        moved = mark_ops_in_progress(
            store, ["location:hq:create", "user:alice:create"]
        )

        assert moved == 1
        assert _status(store, "location:hq:create") == "completed"
        assert _status(store, "user:alice:create") == "in_progress"

    def test_empty_list_is_a_no_op(self, store):
        _two_op_plan(store)
        assert mark_ops_in_progress(store, []) == 0

    def test_in_progress_ops_are_not_re_dispatched(self, store):
        """`get_next_batch` selects `status = 'pending'` only.

        If it ever widened to include `in_progress`, a batch could be issued
        twice inside one run. Pinned here because the in_progress write is what
        makes that reachable.
        """
        _two_op_plan(store)
        mark_ops_in_progress(store, ["location:hq:create"])
        assert get_next_batch(store) == []
