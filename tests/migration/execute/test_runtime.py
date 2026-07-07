"""Tests for runtime execution module (Phase 12b).

Acceptance criteria:
- get_next_batch returns operation metadata with data and resolved_deps
- update_op_status updates plan_operations AND objects table webex_id
- Skip cascade works
- get_completed_ops_for_rollback returns reverse dependency order with location_webex_id
- get_execution_progress counts all statuses correctly
"""

import json
import pytest
from datetime import datetime, timezone

import networkx as nx

from wxcli.migration.execute import DependencyType, MigrationOp
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.runtime import (
    dry_run_all_batches,
    get_completed_ops_for_rollback,
    get_execution_progress,
    get_next_batch,
    update_op_status,
)
from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalHuntGroup,
    CanonicalLocation,
    CanonicalUser,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm", source_id="pk", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _setup_basic_plan(store):
    """Create location → user → hunt_group plan with objects in store."""
    loc = CanonicalLocation(
        canonical_id="location:hq", provenance=_prov(),
        name="HQ", time_zone="America/New_York",
        preferred_language="en_US", announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    )
    user = CanonicalUser(
        canonical_id="user:jsmith", provenance=_prov(),
        emails=["jsmith@acme.com"], first_name="John", last_name="Smith",
        location_id="location:hq", extension="1001",
        status=MigrationStatus.ANALYZED,
    )
    hg = CanonicalHuntGroup(
        canonical_id="hunt_group:hg1", provenance=_prov(),
        name="Sales HG", extension="2001",
        location_id="location:hq",
        status=MigrationStatus.ANALYZED,
    )
    store.upsert_object(loc)
    store.upsert_object(user)
    store.upsert_object(hg)

    G = nx.DiGraph()
    G.add_node("location:hq:create", canonical_id="location:hq", op_type="create",
               resource_type="location", tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ")
    G.add_node("user:jsmith:create", canonical_id="user:jsmith", op_type="create",
               resource_type="user", tier=2, batch="site:hq", api_calls=1,
               description="Create user jsmith@acme.com")
    G.add_node("hunt_group:hg1:create", canonical_id="hunt_group:hg1",
               op_type="create", resource_type="hunt_group", tier=4,
               batch="site:hq", api_calls=1,
               description="Create hunt group Sales HG")

    G.add_edge("location:hq:create", "user:jsmith:create",
               type=DependencyType.REQUIRES)
    G.add_edge("location:hq:create", "hunt_group:hg1:create",
               type=DependencyType.REQUIRES)
    G.add_edge("user:jsmith:create", "hunt_group:hg1:create",
               type=DependencyType.REQUIRES)

    save_plan_to_store(G, store)
    return G


# ---------------------------------------------------------------------------
# get_next_batch tests
# ---------------------------------------------------------------------------

class TestGetNextBatch:
    def test_no_ops_returns_empty(self, store):
        assert get_next_batch(store) == []

    def test_all_completed_returns_empty(self, store):
        _setup_basic_plan(store)
        # Mark all as completed
        for nid in ("location:hq:create", "user:jsmith:create", "hunt_group:hg1:create"):
            update_op_status(store, nid, "completed", webex_id=f"wx-{nid}")
        assert get_next_batch(store) == []

    def test_tier_0_no_deps_returned(self, store):
        _setup_basic_plan(store)
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "location:hq:create"
        assert batch[0]["resource_type"] == "location"
        assert batch[0]["op_type"] == "create"

    def test_respects_dependency_ordering(self, store):
        _setup_basic_plan(store)
        # user:jsmith:create depends on location:hq:create
        batch = get_next_batch(store)
        node_ids = [op["node_id"] for op in batch]
        assert "user:jsmith:create" not in node_ids
        assert "hunt_group:hg1:create" not in node_ids

    def test_returns_ops_grouped_by_batch(self, store):
        _setup_basic_plan(store)
        # Complete location
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-123")
        batch = get_next_batch(store)
        # user:jsmith:create should be in the next batch (site:hq, tier 2)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "user:jsmith:create"

    def test_includes_data_field(self, store):
        _setup_basic_plan(store)
        batch = get_next_batch(store)
        data = batch[0]["data"]
        assert data["name"] == "HQ"
        assert data["time_zone"] == "America/New_York"

    def test_includes_resolved_deps(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-123")
        batch = get_next_batch(store)
        assert batch[0]["node_id"] == "user:jsmith:create"
        assert batch[0]["resolved_deps"]["location:hq"] == "wx-loc-123"

    def test_empty_batch_after_partial_completion(self, store):
        _setup_basic_plan(store)
        # Complete location and user
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-123")
        update_op_status(store, "user:jsmith:create", "completed",
                         webex_id="wx-user-456")
        batch = get_next_batch(store)
        # Should get hunt_group (tier 4, site:hq)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "hunt_group:hg1:create"
        # resolved_deps should include both location and user
        deps = batch[0]["resolved_deps"]
        assert "location:hq" in deps
        assert "user:jsmith" in deps


# ---------------------------------------------------------------------------
# update_op_status tests
# ---------------------------------------------------------------------------

class TestUpdateOpStatus:
    def test_completed_updates_webex_id_in_plan_ops(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-abc")
        row = store.conn.execute(
            "SELECT status, webex_id, completed_at FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == "completed"
        assert row["webex_id"] == "wx-loc-abc"
        assert row["completed_at"] is not None

    def test_completed_updates_objects_table(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-abc")
        obj = store.get_object("location:hq")
        assert obj["webex_id"] == "wx-loc-abc"

    def test_failed_increments_attempts(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="API error 500")
        row = store.conn.execute(
            "SELECT status, error_message, attempts FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == "failed"
        assert row["error_message"] == "API error 500"
        assert row["attempts"] == 1

    def test_skipped_cascades_to_dependents(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "skipped",
                         error_message="Location already exists")

        # user and hunt_group should also be skipped
        user_row = store.conn.execute(
            "SELECT status, error_message FROM plan_operations WHERE node_id = ?",
            ("user:jsmith:create",),
        ).fetchone()
        assert user_row["status"] == "skipped"
        assert "location:hq:create" in user_row["error_message"]

        hg_row = store.conn.execute(
            "SELECT status, error_message FROM plan_operations WHERE node_id = ?",
            ("hunt_group:hg1:create",),
        ).fetchone()
        assert hg_row["status"] == "skipped"

    def test_in_progress_status(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "in_progress")
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == "in_progress"

    def test_invalid_status_raises(self, store):
        _setup_basic_plan(store)
        with pytest.raises(ValueError, match="Invalid status"):
            update_op_status(store, "location:hq:create", "unknown")


# ---------------------------------------------------------------------------
# get_completed_ops_for_rollback tests
# ---------------------------------------------------------------------------

class TestGetCompletedOpsForRollback:
    def test_scope_all_reverse_order(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc")
        update_op_status(store, "user:jsmith:create", "completed",
                         webex_id="wx-user")
        update_op_status(store, "hunt_group:hg1:create", "completed",
                         webex_id="wx-hg")

        ops = get_completed_ops_for_rollback(store, scope="all")
        # Should be reverse tier order: hunt_group (4), user (2), location (0)
        types = [op["resource_type"] for op in ops]
        assert types == ["hunt_group", "user", "location"]

    def test_scope_batch(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc")
        update_op_status(store, "user:jsmith:create", "completed",
                         webex_id="wx-user")

        ops = get_completed_ops_for_rollback(store, scope="batch",
                                              batch_name="site:hq")
        # Only site:hq ops, not org-wide
        node_ids = [op["node_id"] for op in ops]
        assert "location:hq:create" not in node_ids
        assert "user:jsmith:create" in node_ids

    def test_includes_location_webex_id_for_features(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-999")
        update_op_status(store, "user:jsmith:create", "completed",
                         webex_id="wx-user")
        update_op_status(store, "hunt_group:hg1:create", "completed",
                         webex_id="wx-hg")

        ops = get_completed_ops_for_rollback(store, scope="all")
        hg_op = [op for op in ops if op["resource_type"] == "hunt_group"][0]
        assert hg_op["location_webex_id"] == "wx-loc-999"

    def test_includes_data(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc")
        ops = get_completed_ops_for_rollback(store)
        assert ops[0]["data"]["name"] == "HQ"


# ---------------------------------------------------------------------------
# get_execution_progress tests
# ---------------------------------------------------------------------------

class TestGetExecutionProgress:
    def test_all_pending(self, store):
        _setup_basic_plan(store)
        progress = get_execution_progress(store)
        assert progress["total"] == 3
        assert progress["pending"] == 3
        assert progress["completed"] == 0
        assert progress["failed"] == 0

    def test_mixed_statuses(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc")
        update_op_status(store, "user:jsmith:create", "failed",
                         error_message="API error")
        progress = get_execution_progress(store)
        assert progress["completed"] == 1
        assert progress["failed"] == 1
        assert progress["skipped"] == 1  # hunt_group cascade-skipped from user failure

    def test_by_resource_type(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc")
        progress = get_execution_progress(store)
        by_rt = progress["by_resource_type"]
        assert by_rt["location"]["completed"] == 1
        assert by_rt["user"]["pending"] == 1

    def test_last_error(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="Connection refused")
        progress = get_execution_progress(store)
        assert progress["last_error"]["error"] == "Connection refused"

    def test_last_completed(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc")
        progress = get_execution_progress(store)
        assert progress["last_completed"]["node_id"] == "location:hq:create"

    def test_empty_store(self, store):
        progress = get_execution_progress(store)
        assert progress["total"] == 0
        assert progress["last_error"] is None
        assert progress["last_completed"] is None


# ---------------------------------------------------------------------------
# Schema migration tests
# ---------------------------------------------------------------------------

class TestSchemaMigration:
    def test_new_database_has_all_columns(self, tmp_path):
        s = MigrationStore(tmp_path / "new.db")
        try:
            cols = s.conn.execute("PRAGMA table_info(plan_operations)").fetchall()
            col_names = {c["name"] for c in cols}
            assert "webex_id" in col_names
            assert "error_message" in col_names
            assert "completed_at" in col_names
            assert "attempts" in col_names
        finally:
            s.close()

    def test_existing_database_gets_columns(self, tmp_path):
        # Create a DB without the new columns (simulating pre-12b)
        import sqlite3
        db_path = tmp_path / "old.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""CREATE TABLE plan_operations (
            node_id TEXT PRIMARY KEY,
            canonical_id TEXT NOT NULL,
            op_type TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            tier INTEGER NOT NULL,
            batch TEXT,
            api_calls INTEGER DEFAULT 1,
            description TEXT,
            status TEXT DEFAULT 'pending'
        )""")
        # Also create other required tables minimally
        conn.execute("""CREATE TABLE objects (
            canonical_id TEXT PRIMARY KEY,
            object_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'discovered',
            location_id TEXT, webex_id TEXT, batch TEXT,
            tier INTEGER, data TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE cross_refs (
            from_id TEXT, to_id TEXT, relationship TEXT,
            ordinal INTEGER, PRIMARY KEY (from_id, to_id, relationship)
        )""")
        conn.execute("""CREATE TABLE decisions (
            decision_id TEXT PRIMARY KEY, type TEXT NOT NULL,
            severity TEXT NOT NULL, summary TEXT NOT NULL,
            context TEXT NOT NULL, options TEXT NOT NULL,
            chosen_option TEXT, resolved_at TEXT, resolved_by TEXT,
            fingerprint TEXT NOT NULL, run_id TEXT NOT NULL,
            UNIQUE(fingerprint)
        )""")
        conn.execute("""CREATE TABLE journal (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, entry_type TEXT, canonical_id TEXT,
            resource_type TEXT, request TEXT, response TEXT, pre_state TEXT
        )""")
        conn.execute("""CREATE TABLE merge_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, stage TEXT, run_id TEXT,
            action TEXT, target_type TEXT, target_id TEXT, details TEXT
        )""")
        conn.execute("""CREATE TABLE plan_edges (
            from_node TEXT, to_node TEXT, dep_type TEXT,
            broken INTEGER DEFAULT 0, PRIMARY KEY (from_node, to_node)
        )""")
        conn.commit()
        conn.close()

        # Opening with MigrationStore should add columns via migration
        s = MigrationStore(db_path)
        try:
            cols = s.conn.execute("PRAGMA table_info(plan_operations)").fetchall()
            col_names = {c["name"] for c in cols}
            assert "webex_id" in col_names
            assert "error_message" in col_names
            assert "completed_at" in col_names
            assert "attempts" in col_names
        finally:
            s.close()


# ---------------------------------------------------------------------------
# dry_run_all_batches tests
# ---------------------------------------------------------------------------

class TestDryRunAllBatches:
    def test_empty_store(self, store):
        result = dry_run_all_batches(store)
        assert result["total_operations"] == 0
        assert result["total_batches"] == 0
        assert result["batches"] == []

    def test_walks_all_batches_in_order(self, store):
        _setup_basic_plan(store)
        result = dry_run_all_batches(store)

        assert result["total_operations"] == 3
        assert result["total_batches"] == 3
        batches = result["batches"]

        # Batch 0: location (org-wide, tier 0)
        assert batches[0]["tier"] == 0
        assert len(batches[0]["operations"]) == 1
        assert batches[0]["operations"][0]["resource_type"] == "location"

        # Batch 1: user (site:hq, tier 2)
        assert batches[1]["tier"] == 2
        assert len(batches[1]["operations"]) == 1
        assert batches[1]["operations"][0]["resource_type"] == "user"

        # Batch 2: hunt_group (site:hq, tier 4)
        assert batches[2]["tier"] == 4
        assert len(batches[2]["operations"]) == 1
        assert batches[2]["operations"][0]["resource_type"] == "hunt_group"

    def test_does_not_modify_database(self, store):
        _setup_basic_plan(store)

        # Snapshot statuses before
        before = store.conn.execute(
            "SELECT node_id, status, webex_id FROM plan_operations ORDER BY node_id"
        ).fetchall()
        before = [(r["node_id"], r["status"], r["webex_id"]) for r in before]

        dry_run_all_batches(store)

        # Snapshot statuses after
        after = store.conn.execute(
            "SELECT node_id, status, webex_id FROM plan_operations ORDER BY node_id"
        ).fetchall()
        after = [(r["node_id"], r["status"], r["webex_id"]) for r in after]

        assert before == after

    def test_resolved_deps_populated(self, store):
        _setup_basic_plan(store)
        result = dry_run_all_batches(store)

        # user should have location in resolved_deps
        user_op = result["batches"][1]["operations"][0]
        assert "location:hq" in user_op["resolved_deps"]

        # hunt_group should have both location and user
        hg_op = result["batches"][2]["operations"][0]
        assert "location:hq" in hg_op["resolved_deps"]
        assert "user:jsmith" in hg_op["resolved_deps"]

    def test_skips_already_completed(self, store):
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-existing")

        result = dry_run_all_batches(store)
        # Location already completed, so only 2 remaining
        assert result["total_operations"] == 2
        assert result["total_batches"] == 2

    def test_api_calls_counted(self, store):
        _setup_basic_plan(store)
        result = dry_run_all_batches(store)
        assert result["total_api_calls"] >= 3  # At least 1 per op

    def test_failed_op_blocks_dependents(self, store):
        """Dry run from a state where one op failed — dependents are unreachable."""
        _setup_basic_plan(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="API error")

        result = dry_run_all_batches(store)
        # Location is failed (not pending), user/HG depend on it → nothing ready
        assert result["total_operations"] == 0
        assert result["total_batches"] == 0

    def test_parallel_ops_in_same_batch(self, store):
        """Two ops in the same (batch, tier) both appear in one batch."""
        loc = CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(),
            name="HQ", time_zone="America/New_York",
            preferred_language="en_US", announcement_language="en_us",
            status=MigrationStatus.ANALYZED,
        )
        u1 = CanonicalUser(
            canonical_id="user:a", provenance=_prov(),
            emails=["a@acme.com"], first_name="A", last_name="User",
            location_id="location:hq", extension="1001",
            status=MigrationStatus.ANALYZED,
        )
        u2 = CanonicalUser(
            canonical_id="user:b", provenance=_prov(),
            emails=["b@acme.com"], first_name="B", last_name="User",
            location_id="location:hq", extension="1002",
            status=MigrationStatus.ANALYZED,
        )
        store.upsert_object(loc)
        store.upsert_object(u1)
        store.upsert_object(u2)

        G = nx.DiGraph()
        G.add_node("location:hq:create", canonical_id="location:hq", op_type="create",
                    resource_type="location", tier=0, batch="org-wide", api_calls=1,
                    description="Create location HQ")
        G.add_node("user:a:create", canonical_id="user:a", op_type="create",
                    resource_type="user", tier=2, batch="site:hq", api_calls=1,
                    description="Create user a@acme.com")
        G.add_node("user:b:create", canonical_id="user:b", op_type="create",
                    resource_type="user", tier=2, batch="site:hq", api_calls=1,
                    description="Create user b@acme.com")
        G.add_edge("location:hq:create", "user:a:create",
                    type=DependencyType.REQUIRES)
        G.add_edge("location:hq:create", "user:b:create",
                    type=DependencyType.REQUIRES)
        save_plan_to_store(G, store)

        result = dry_run_all_batches(store)
        assert result["total_operations"] == 3
        assert result["total_batches"] == 2

        # Batch 1: location; Batch 2: both users together
        user_batch = result["batches"][1]
        assert len(user_batch["operations"]) == 2
        user_types = {op["resource_type"] for op in user_batch["operations"]}
        assert user_types == {"user"}
