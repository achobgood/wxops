"""Re-planning must not erase what the migration already built in Webex.

`plan_operations` is the only durable record of what this tool created in a
customer's org: the status, and the `webex_id` Webex handed back. `execute/`
issues no DELETE anywhere, so an id lost here cannot be cleaned up by this tool —
`rollback-ops` reads these same rows.

Until 2026-08-05 `save_plan_to_store` opened with an unconditional
`DELETE FROM plan_operations`, documented as "idempotent re-planning". It is
idempotent with respect to the *plan* and destructive with respect to the
*execution record*. Measured before the fix: after one successful op,
`wxcli cucm plan` took `status=completed, webex_id=Y2lzY29z…` to
`status=pending, webex_id=None`, and `rollback-ops` went from 1 row to 0. The
next `execute` would then re-issue the whole plan against an org that already
had it — a duplicate for the 13 of 21 create-capable resource types
`_try_find_existing` does not cover, a hard 409 for the rest.

Neither `plan` nor `normalize` prompted, warned, or was gated, and neither
mentions deletion in `--help`. Meanwhile `wxcli cleanup run`, which deletes real
remote objects, asks `Delete {total} resources? This cannot be undone`.

Tracked deliberately — `tests/migration/**` is re-included at `.gitignore:56-57`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import networkx as nx
import pytest

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.runtime import (
    get_completed_ops_for_rollback,
    update_op_status,
)
from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore

WEBEX_ID = "Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzEyMw"


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm", source_id="pk", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture()
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    s.upsert_object(CanonicalLocation(
        canonical_id="location:hq", provenance=_prov(), name="HQ",
        time_zone="America/New_York", preferred_language="en_US",
        announcement_language="en_us", status=MigrationStatus.ANALYZED,
    ))
    s.upsert_object(CanonicalUser(
        canonical_id="user:alice", provenance=_prov(), emails=["alice@acme.com"],
        first_name="Alice", last_name="Smith", location_id="location:hq",
        extension="1001", status=MigrationStatus.ANALYZED,
    ))
    yield s
    s.close()


def _graph(*, with_user: bool = True) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_node(
        "location:hq:create", canonical_id="location:hq", op_type="create",
        resource_type="location", tier=0, batch="org-wide", api_calls=1,
        description="Create location HQ",
    )
    if with_user:
        G.add_node(
            "user:alice:create", canonical_id="user:alice", op_type="create",
            resource_type="user", tier=2, batch="location:hq", api_calls=1,
            description="Create user alice@acme.com",
        )
        G.add_edge("location:hq:create", "user:alice:create",
                   type=DependencyType.REQUIRES)
    return G


def _row(store, node_id="location:hq:create"):
    return store.conn.execute(
        "SELECT status, webex_id, error_message, attempts FROM plan_operations "
        "WHERE node_id = ?", (node_id,),
    ).fetchone()


class TestReplanCarriesTheRecordForward:
    def test_a_completed_op_survives_a_re_plan(self, store):
        """The whole finding in one assertion."""
        save_plan_to_store(_graph(), store)
        update_op_status(store, "location:hq:create", "completed", webex_id=WEBEX_ID)
        assert len(get_completed_ops_for_rollback(store)) == 1

        result = save_plan_to_store(_graph(), store)   # `wxcli cucm plan` again

        row = _row(store)
        assert row["status"] == "completed", (
            "a re-plan reset an already-executed operation to pending; the next "
            "execute would re-issue it against an org that already has it"
        )
        assert row["webex_id"] == WEBEX_ID, (
            "the webexId is the only handle this tool has on the remote object, "
            "and execute/ issues no DELETE to clean up what it forgets"
        )
        assert result["preserved"] == 1
        assert result["orphaned"] == []
        assert len(get_completed_ops_for_rollback(store)) == 1, (
            "rollback-ops reads plan_operations — losing the row silently "
            "reports 'nothing to roll back'"
        )

    def test_a_failed_op_keeps_its_error_and_attempt_count(self, store):
        save_plan_to_store(_graph(), store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="409: already exists")
        before = _row(store)

        save_plan_to_store(_graph(), store)

        after = _row(store)
        assert after["status"] == "failed"
        assert after["error_message"] == "409: already exists"
        assert after["attempts"] == before["attempts"]

    def test_pending_ops_are_not_counted_as_preserved(self, store):
        """Carrying nothing forward must report nothing, not a false positive."""
        save_plan_to_store(_graph(), store)
        result = save_plan_to_store(_graph(), store)
        assert result["preserved"] == 0
        assert result["orphaned"] == []

    def test_the_plan_shape_still_rebuilds_from_the_graph(self, store):
        """Preserving execution state must not freeze tier/batch/deps.

        The graph stays the source of truth for everything the planner decides;
        only the columns recording what happened remotely are carried over.
        """
        save_plan_to_store(_graph(), store)
        update_op_status(store, "location:hq:create", "completed", webex_id=WEBEX_ID)

        G = _graph()
        G.nodes["location:hq:create"]["tier"] = 3
        G.nodes["location:hq:create"]["batch"] = "moved"
        G.nodes["location:hq:create"]["description"] = "Create location HQ (renamed)"
        save_plan_to_store(G, store)

        row = store.conn.execute(
            "SELECT tier, batch, description, status, webex_id FROM plan_operations "
            "WHERE node_id = 'location:hq:create'"
        ).fetchone()
        assert row["tier"] == 3
        assert row["batch"] == "moved"
        assert row["description"] == "Create location HQ (renamed)"
        assert row["status"] == "completed"      # execution record survives
        assert row["webex_id"] == WEBEX_ID


class TestOrphansAreReportedNotSwallowed:
    def test_a_completed_op_dropped_from_the_plan_is_returned(self, store):
        """The one case a human still has to resolve.

        A completed op with a webexId whose node is gone from the new graph names
        a real object in the customer's org that the new plan no longer knows
        about. Nothing in this tool can delete it, so it must not vanish quietly.
        """
        save_plan_to_store(_graph(with_user=True), store)
        update_op_status(store, "user:alice:create", "completed", webex_id="wx-alice")

        result = save_plan_to_store(_graph(with_user=False), store)

        assert len(result["orphaned"]) == 1
        orphan = result["orphaned"][0]
        assert orphan["node_id"] == "user:alice:create"
        assert orphan["webex_id"] == "wx-alice"
        assert orphan["resource_type"] == "user"
        assert orphan["description"]

    def test_a_dropped_op_that_never_ran_is_not_an_orphan(self, store):
        save_plan_to_store(_graph(with_user=True), store)
        result = save_plan_to_store(_graph(with_user=False), store)
        assert result["orphaned"] == []

    def test_a_fresh_store_reports_neither(self, store):
        result = save_plan_to_store(_graph(), store)
        assert result == {"preserved": 0, "orphaned": []}
