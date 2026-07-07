"""Tests for cascading failure behavior and retry recovery.

Validates two critical properties:
1. Independent branches proceed when one branch fails
2. Fixing a failed operation unblocks the full downstream chain

These tests simulate the multi-round execute pattern:
  execute → some failures → fix → execute again → downstream proceeds
"""

import json
import pytest
from datetime import datetime, timezone

import networkx as nx

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.runtime import (
    get_execution_progress,
    get_next_batch,
    update_op_status,
)
from wxcli.migration.models import (
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


# ---------------------------------------------------------------------------
# Two-location DAG builder
# ---------------------------------------------------------------------------

def _setup_two_location_plan(store):
    """Build a realistic two-location migration plan.

    DAG structure:
        location:hq:create → location:hq:enable_calling → user:alice:create → hunt_group:sales:create
                                                         → user:bob:create   ↗ (SOFT dep)

        location:branch:create → location:branch:enable_calling → user:carol:create → call_queue:support:create
                                                                 → user:dave:create  ↗ (SOFT dep)

    The two location branches are completely independent.
    """
    # Objects
    loc_hq = CanonicalLocation(
        canonical_id="location:hq", provenance=_prov(),
        name="HQ Office", time_zone="America/New_York",
        preferred_language="en_US", announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    )
    loc_branch = CanonicalLocation(
        canonical_id="location:branch", provenance=_prov(),
        name="Branch Office", time_zone="America/Chicago",
        preferred_language="en_US", announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    )
    alice = CanonicalUser(
        canonical_id="user:alice", provenance=_prov(),
        emails=["alice@acme.com"], first_name="Alice", last_name="Smith",
        location_id="location:hq", extension="1001",
        status=MigrationStatus.ANALYZED,
    )
    bob = CanonicalUser(
        canonical_id="user:bob", provenance=_prov(),
        emails=["bob@acme.com"], first_name="Bob", last_name="Jones",
        location_id="location:hq", extension="1002",
        status=MigrationStatus.ANALYZED,
    )
    carol = CanonicalUser(
        canonical_id="user:carol", provenance=_prov(),
        emails=["carol@acme.com"], first_name="Carol", last_name="Davis",
        location_id="location:branch", extension="2001",
        status=MigrationStatus.ANALYZED,
    )
    dave = CanonicalUser(
        canonical_id="user:dave", provenance=_prov(),
        emails=["dave@acme.com"], first_name="Dave", last_name="Wilson",
        location_id="location:branch", extension="2002",
        status=MigrationStatus.ANALYZED,
    )
    sales_hg = CanonicalHuntGroup(
        canonical_id="hunt_group:sales", provenance=_prov(),
        name="Sales HG", extension="3001",
        location_id="location:hq",
        status=MigrationStatus.ANALYZED,
    )
    support_cq = CanonicalHuntGroup(
        canonical_id="call_queue:support", provenance=_prov(),
        name="Support Queue", extension="3002",
        location_id="location:branch",
        status=MigrationStatus.ANALYZED,
    )

    for obj in [loc_hq, loc_branch, alice, bob, carol, dave, sales_hg, support_cq]:
        store.upsert_object(obj)

    G = nx.DiGraph()

    # HQ branch
    G.add_node("location:hq:create", canonical_id="location:hq",
               op_type="create", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ Office")
    G.add_node("location:hq:enable_calling", canonical_id="location:hq",
               op_type="enable_calling", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Enable Webex Calling on HQ Office")
    G.add_node("user:alice:create", canonical_id="user:alice",
               op_type="create", resource_type="user",
               tier=2, batch="location:hq", api_calls=1,
               description="Create user alice@acme.com")
    G.add_node("user:bob:create", canonical_id="user:bob",
               op_type="create", resource_type="user",
               tier=2, batch="location:hq", api_calls=1,
               description="Create user bob@acme.com")
    G.add_node("hunt_group:sales:create", canonical_id="hunt_group:sales",
               op_type="create", resource_type="hunt_group",
               tier=4, batch="location:hq", api_calls=1,
               description="Create hunt group Sales HG")

    # Branch
    G.add_node("location:branch:create", canonical_id="location:branch",
               op_type="create", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Create location Branch Office")
    G.add_node("location:branch:enable_calling", canonical_id="location:branch",
               op_type="enable_calling", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Enable Webex Calling on Branch Office")
    G.add_node("user:carol:create", canonical_id="user:carol",
               op_type="create", resource_type="user",
               tier=2, batch="location:branch", api_calls=1,
               description="Create user carol@acme.com")
    G.add_node("user:dave:create", canonical_id="user:dave",
               op_type="create", resource_type="user",
               tier=2, batch="location:branch", api_calls=1,
               description="Create user dave@acme.com")
    G.add_node("call_queue:support:create", canonical_id="call_queue:support",
               op_type="create", resource_type="call_queue",
               tier=4, batch="location:branch", api_calls=1,
               description="Create call queue Support Queue")

    # Edges — HQ branch
    G.add_edge("location:hq:create", "location:hq:enable_calling",
               type=DependencyType.CONFIGURES)
    G.add_edge("location:hq:enable_calling", "user:alice:create",
               type=DependencyType.REQUIRES)
    G.add_edge("location:hq:enable_calling", "user:bob:create",
               type=DependencyType.REQUIRES)
    G.add_edge("user:alice:create", "hunt_group:sales:create",
               type=DependencyType.SOFT)
    G.add_edge("user:bob:create", "hunt_group:sales:create",
               type=DependencyType.SOFT)
    # HG also requires the location
    G.add_edge("location:hq:enable_calling", "hunt_group:sales:create",
               type=DependencyType.REQUIRES)

    # Edges — Branch
    G.add_edge("location:branch:create", "location:branch:enable_calling",
               type=DependencyType.CONFIGURES)
    G.add_edge("location:branch:enable_calling", "user:carol:create",
               type=DependencyType.REQUIRES)
    G.add_edge("location:branch:enable_calling", "user:dave:create",
               type=DependencyType.REQUIRES)
    G.add_edge("user:carol:create", "call_queue:support:create",
               type=DependencyType.SOFT)
    G.add_edge("user:dave:create", "call_queue:support:create",
               type=DependencyType.SOFT)
    G.add_edge("location:branch:enable_calling", "call_queue:support:create",
               type=DependencyType.REQUIRES)

    save_plan_to_store(G, store)
    return G


# ===========================================================================
# SCENARIO 1: Independent branches — fail one, other proceeds
# ===========================================================================

class TestIndependentBranches:
    """When Location A fails, Location B's entire branch must still proceed."""

    def test_both_locations_ready_initially(self, store):
        """Both location creates should appear in the first batch."""
        _setup_two_location_plan(store)
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "location:hq:create" in node_ids
        assert "location:branch:create" in node_ids

    def test_fail_hq_branch_proceeds(self, store):
        """Fail HQ location — branch users should still become ready."""
        _setup_two_location_plan(store)

        # Round 1: Both locations are ready. HQ fails, Branch succeeds.
        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address validation failed")
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-loc-branch")

        # Branch's enable_calling should be ready
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "location:branch:enable_calling" in node_ids
        # HQ's enable_calling should NOT be ready (dependency failed)
        assert "location:hq:enable_calling" not in node_ids

    def test_fail_hq_branch_users_proceed(self, store):
        """Full branch chain: HQ fails, branch users and features succeed."""
        _setup_two_location_plan(store)

        # Tier 0: HQ fails, Branch succeeds
        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address validation failed")
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-loc-branch")
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-loc-branch-calling")

        # Tier 2: Only branch users should be ready
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "user:carol:create" in node_ids
        assert "user:dave:create" in node_ids
        # HQ users must NOT be ready
        assert "user:alice:create" not in node_ids
        assert "user:bob:create" not in node_ids

    def test_fail_hq_branch_features_proceed(self, store):
        """Entire branch completes while HQ is blocked at tier 0."""
        _setup_two_location_plan(store)

        # HQ fails at create
        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address validation failed")

        # Branch runs to completion
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-loc-branch")
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-loc-branch-calling")
        update_op_status(store, "user:carol:create", "completed",
                         webex_id="wx-carol")
        update_op_status(store, "user:dave:create", "completed",
                         webex_id="wx-dave")

        # Call queue should be ready (SOFT deps on carol/dave are completed)
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "call_queue:support:create" in node_ids
        # HQ hunt group must NOT be ready
        assert "hunt_group:sales:create" not in node_ids

    def test_hq_ops_cascade_skipped_on_failure(self, store):
        """Failed location must cascade-skip its hard dependents."""
        _setup_two_location_plan(store)

        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address validation failed")

        # Verify HQ downstream ops are skipped (cascade from failure)
        for node_id in ("location:hq:enable_calling", "user:alice:create",
                        "user:bob:create", "hunt_group:sales:create"):
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "skipped", \
                f"{node_id} should be 'skipped' but is '{row['status']}'"

    def test_progress_shows_correct_counts(self, store):
        """Progress should show 1 failed + 5 completed + 4 skipped."""
        _setup_two_location_plan(store)

        # HQ fails, branch completes through features
        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address")
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-b")
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-b-c")
        update_op_status(store, "user:carol:create", "completed",
                         webex_id="wx-carol")
        update_op_status(store, "user:dave:create", "completed",
                         webex_id="wx-dave")
        update_op_status(store, "call_queue:support:create", "completed",
                         webex_id="wx-cq")

        progress = get_execution_progress(store)
        assert progress["completed"] == 5
        assert progress["failed"] == 1
        assert progress["pending"] == 0
        assert progress["skipped"] == 4  # HQ's enable_calling + alice + bob + sales HG


# ===========================================================================
# SCENARIO 2: Fix a failure, downstream chain unblocks
# ===========================================================================

class TestRetryUnblocksChain:
    """After fixing a failed op, running get_next_batch again must return
    the full downstream chain — nothing permanently blocked."""

    def test_fix_location_unblocks_enable_calling(self, store):
        """Fix failed location:create → cascade-skipped ops reset → enable_calling becomes ready."""
        _setup_two_location_plan(store)

        # Location fails — downstream cascade-skipped
        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address validation failed")

        # Verify cascade-skipped
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("location:hq:enable_calling",),
        ).fetchone()
        assert row["status"] == "skipped"

        # Nothing in HQ chain is ready
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-b")
        batch = get_next_batch(store)
        hq_nodes = {op["node_id"] for op in batch if "hq" in op["node_id"]}
        assert len(hq_nodes) == 0

        # FIX: mark location:hq:create as completed (admin fixed the address)
        # This should undo the cascade-skip on dependents
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-hq")

        # Now enable_calling should be ready (reset from skipped to pending)
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "location:hq:enable_calling" in node_ids

    def test_fix_location_full_chain_completes(self, store):
        """Simulate full multi-round recovery: fail → cascade-skip → fix → undo-skip → complete."""
        _setup_two_location_plan(store)

        # === ROUND 1: Both locations created, HQ fails ===
        update_op_status(store, "location:hq:create", "failed",
                         error_message="400: Address validation failed")
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-b")

        # Complete branch fully
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-b-c")
        update_op_status(store, "user:carol:create", "completed",
                         webex_id="wx-carol")
        update_op_status(store, "user:dave:create", "completed",
                         webex_id="wx-dave")
        update_op_status(store, "call_queue:support:create", "completed",
                         webex_id="wx-cq")

        # Verify: HQ chain cascade-skipped
        progress = get_execution_progress(store)
        assert progress["skipped"] == 4  # enable_calling + alice + bob + sales HG

        # === ROUND 2: Fix HQ location — undo cascade-skip, re-run ===
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-loc-hq")

        # enable_calling should be ready
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "location:hq:enable_calling"
        update_op_status(store, "location:hq:enable_calling", "completed",
                         webex_id="wx-hq-calling")

        # === ROUND 3: Users become ready ===
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "user:alice:create" in node_ids
        assert "user:bob:create" in node_ids

        update_op_status(store, "user:alice:create", "completed",
                         webex_id="wx-alice")
        update_op_status(store, "user:bob:create", "completed",
                         webex_id="wx-bob")

        # === ROUND 4: Hunt group ready ===
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "hunt_group:sales:create"
        # Verify resolved_deps includes location and both users.
        # Note: location:hq has two ops (create + enable_calling) sharing the
        # same canonical_id. The resolved_deps dict uses canonical_id as key,
        # so the last one written wins — enable_calling's webex_id.
        deps = batch[0]["resolved_deps"]
        assert "location:hq" in deps
        assert deps["user:alice"] == "wx-alice"
        assert deps["user:bob"] == "wx-bob"

        update_op_status(store, "hunt_group:sales:create", "completed",
                         webex_id="wx-sales-hg")

        # === DONE: Everything completed ===
        progress = get_execution_progress(store)
        assert progress["completed"] == 10
        assert progress["pending"] == 0
        assert progress["failed"] == 0
        assert progress["skipped"] == 0

    def test_fix_user_unblocks_settings(self, store):
        """Fail a user create, fix it, verify configure_settings becomes ready."""
        # Simpler DAG: location → user → user:configure_settings
        loc = CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(),
            name="HQ", time_zone="America/New_York",
            preferred_language="en_US", announcement_language="en_us",
            status=MigrationStatus.ANALYZED,
        )
        user = CanonicalUser(
            canonical_id="user:alice", provenance=_prov(),
            emails=["alice@acme.com"], first_name="Alice", last_name="Smith",
            location_id="location:hq", extension="1001",
            call_settings={"callForwarding": {"enabled": True}},
            status=MigrationStatus.ANALYZED,
        )
        store.upsert_object(loc)
        store.upsert_object(user)

        G = nx.DiGraph()
        G.add_node("location:hq:create", canonical_id="location:hq",
                    op_type="create", resource_type="location",
                    tier=0, batch="org-wide", api_calls=1,
                    description="Create location HQ")
        G.add_node("user:alice:create", canonical_id="user:alice",
                    op_type="create", resource_type="user",
                    tier=2, batch="location:hq", api_calls=1,
                    description="Create user alice@acme.com")
        G.add_node("user:alice:configure_settings", canonical_id="user:alice",
                    op_type="configure_settings", resource_type="user",
                    tier=5, batch="location:hq", api_calls=5,
                    description="Configure call settings for alice")

        G.add_edge("location:hq:create", "user:alice:create",
                    type=DependencyType.REQUIRES)
        G.add_edge("user:alice:create", "user:alice:configure_settings",
                    type=DependencyType.CONFIGURES)

        save_plan_to_store(G, store)

        # Location succeeds
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")

        # User fails
        update_op_status(store, "user:alice:create", "failed",
                         error_message="409: User already exists")

        # Settings should NOT be ready — cascade-skipped from user failure
        batch = get_next_batch(store)
        assert len(batch) == 0

        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("user:alice:configure_settings",),
        ).fetchone()
        assert row["status"] == "skipped"

        # FIX: mark user as completed (found existing user by email)
        # This should undo the cascade-skip on configure_settings
        update_op_status(store, "user:alice:create", "completed",
                         webex_id="wx-alice-existing")

        # Now settings should be ready (reset from skipped to pending)
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "user:alice:configure_settings"
        assert batch[0]["resolved_deps"]["user:alice"] == "wx-alice-existing"


# ===========================================================================
# SCENARIO 3: Failed vs Skipped — the critical distinction
# ===========================================================================

class TestFailedVsSkipped:
    """Both failed and skipped cascade to dependents.

    The key difference: failed cascade is REVERSIBLE — fixing the parent
    (marking it completed) undoes the cascade-skip on dependents. Skipped
    cascade is permanent (admin decision).
    """

    def test_failed_cascades_but_is_reversible(self, store):
        """Mark location as failed — downstream cascade-skipped, but fixable."""
        _setup_two_location_plan(store)

        update_op_status(store, "location:hq:create", "failed",
                         error_message="500: Internal server error")

        # All HQ downstream ops should be cascade-skipped
        hq_downstream = [
            "location:hq:enable_calling",
            "user:alice:create",
            "user:bob:create",
            "hunt_group:sales:create",
        ]
        for node_id in hq_downstream:
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "skipped", \
                f"FAILED must cascade: {node_id} is '{row['status']}' not 'skipped'"

        # FIX: mark parent as completed → dependents reset to pending
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq-fixed")
        for node_id in hq_downstream:
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "pending", \
                f"Undo cascade: {node_id} is '{row['status']}' not 'pending'"

    def test_skipped_does_cascade(self, store):
        """Mark location as skipped — downstream must cascade to skipped."""
        _setup_two_location_plan(store)

        update_op_status(store, "location:hq:create", "skipped",
                         error_message="Admin chose to skip this location")

        # ALL HQ downstream ops should be skipped
        hq_downstream = [
            "location:hq:enable_calling",
            "user:alice:create",
            "user:bob:create",
            "hunt_group:sales:create",
        ]
        for node_id in hq_downstream:
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "skipped", \
                f"SKIPPED must cascade: {node_id} is '{row['status']}' not 'skipped'"

    def test_skipped_branch_does_not_affect_other_branch(self, store):
        """Skip HQ entirely — branch must be unaffected."""
        _setup_two_location_plan(store)

        update_op_status(store, "location:hq:create", "skipped",
                         error_message="Admin chose to skip")

        # Branch ops should all be pending still
        branch_ops = [
            "location:branch:create",
            "location:branch:enable_calling",
            "user:carol:create",
            "user:dave:create",
            "call_queue:support:create",
        ]
        for node_id in branch_ops:
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "pending", \
                f"Skip cascade leaked: {node_id} is '{row['status']}' not 'pending'"

    def test_skipped_is_permanent_cannot_unblock(self, store):
        """Once skipped, downstream ops are permanently skipped —
        even if we later mark the parent as completed."""
        _setup_two_location_plan(store)

        # Skip location
        update_op_status(store, "location:hq:create", "skipped",
                         error_message="Admin skip")

        # Verify cascade happened
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("user:alice:create",),
        ).fetchone()
        assert row["status"] == "skipped"

        # Now "un-skip" the location by marking it completed
        # (This is an unusual recovery path but tests the permanence)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")

        # The downstream is STILL skipped — cascade was permanent
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("user:alice:create",),
        ).fetchone()
        assert row["status"] == "skipped", \
            "Skipped ops should stay skipped even after parent is completed"


# ===========================================================================
# SCENARIO 3b: Skip cascade must NOT leak through SOFT deps
# ===========================================================================

class TestSkipCascadeSoftDeps:
    """Skipping a user should NOT cascade-skip a hunt group
    connected via a SOFT dependency edge."""

    def test_skip_agent_does_not_skip_hunt_group(self, store):
        """Skip bob (agent) — hunt group with SOFT dep on bob stays pending."""
        _setup_two_location_plan(store)

        # Complete HQ location chain
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")
        update_op_status(store, "location:hq:enable_calling", "completed",
                         webex_id="wx-hq-c")

        # Skip bob — SOFT dep to hunt_group:sales should NOT cascade
        update_op_status(store, "user:bob:create", "skipped",
                         error_message="Admin chose to skip bob")

        # Hunt group must still be pending (not skipped)
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("hunt_group:sales:create",),
        ).fetchone()
        assert row["status"] == "pending", \
            f"Skip cascade leaked through SOFT dep: hunt_group is '{row['status']}' not 'pending'"


# ===========================================================================
# SCENARIO 4: SOFT dependencies — features proceed with partial agents
# ===========================================================================

class TestSoftDependencies:
    """Hunt groups and call queues have SOFT deps on their agents.
    If an agent user fails, the feature should still proceed."""

    def test_hg_proceeds_when_one_agent_fails(self, store):
        """Hunt group with 2 agents: 1 fails, HG still becomes ready."""
        _setup_two_location_plan(store)

        # Complete HQ location chain
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")
        update_op_status(store, "location:hq:enable_calling", "completed",
                         webex_id="wx-hq-c")

        # Complete branch location chain too (so tier 0 is clear)
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-branch")
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-branch-c")

        # Alice succeeds, Bob fails
        update_op_status(store, "user:alice:create", "completed",
                         webex_id="wx-alice")
        update_op_status(store, "user:bob:create", "failed",
                         error_message="409: Duplicate email")

        # Complete branch users too (clear tier 2)
        update_op_status(store, "user:carol:create", "completed",
                         webex_id="wx-carol")
        update_op_status(store, "user:dave:create", "completed",
                         webex_id="wx-dave")

        # Both features are tier 4 but in different batches.
        # get_next_batch returns one (tier, batch) group at a time.
        # Consume batches until we find the HG.
        found_hg = False
        for _ in range(3):  # safety limit
            batch = get_next_batch(store)
            if not batch:
                break
            node_ids = {op["node_id"] for op in batch}
            if "hunt_group:sales:create" in node_ids:
                found_hg = True
                # resolved_deps should include Alice but not Bob
                hg_op = [op for op in batch
                         if op["node_id"] == "hunt_group:sales:create"][0]
                assert hg_op["resolved_deps"].get("user:alice") == "wx-alice"
                # Bob is failed, so his webex_id is None
                assert "user:bob" not in hg_op["resolved_deps"]
                break
            # Complete this batch and move on
            for op in batch:
                update_op_status(store, op["node_id"], "completed",
                                 webex_id=f"wx-{op['node_id']}")

        assert found_hg, "Hunt group never became ready despite SOFT dep fix"

    def test_cq_proceeds_when_all_agents_fail(self, store):
        """Even if ALL agents fail, the feature with only SOFT deps proceeds."""
        _setup_two_location_plan(store)

        # Complete both locations first (clear tier 0)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")
        update_op_status(store, "location:hq:enable_calling", "completed",
                         webex_id="wx-hq-c")
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-b")
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-b-c")

        # Complete HQ users (clear tier 2 for HQ batch)
        update_op_status(store, "user:alice:create", "completed",
                         webex_id="wx-alice")
        update_op_status(store, "user:bob:create", "completed",
                         webex_id="wx-bob")

        # Both branch users fail
        update_op_status(store, "user:carol:create", "failed",
                         error_message="409: Duplicate")
        update_op_status(store, "user:dave:create", "failed",
                         error_message="409: Duplicate")

        # Call queue should still be ready (REQUIRES dep on location is met,
        # SOFT deps on carol/dave don't block even though they failed)
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert "call_queue:support:create" in node_ids


# ===========================================================================
# SCENARIO 5: Multi-round execute simulation
# ===========================================================================

class TestMultiRoundExecution:
    """Simulates the full execute → review → fix → execute cycle."""

    def test_three_round_recovery(self, store):
        """Round 1: partial success. Round 2: fix + more success. Round 3: complete."""
        _setup_two_location_plan(store)

        # === ROUND 1 ===
        # get_next_batch returns tier 0 (both locations)
        batch = get_next_batch(store)
        assert len(batch) == 2  # both locations
        tier_0_ids = {op["node_id"] for op in batch}
        assert tier_0_ids == {"location:hq:create", "location:branch:create"}

        # HQ succeeds, Branch fails
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")
        update_op_status(store, "location:branch:create", "failed",
                         error_message="400: Invalid timezone")

        # Next batch: HQ's enable_calling (branch blocked)
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "location:hq:enable_calling"
        update_op_status(store, "location:hq:enable_calling", "completed",
                         webex_id="wx-hq-c")

        # Next batch: HQ users
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert node_ids == {"user:alice:create", "user:bob:create"}

        # Alice succeeds, Bob fails
        update_op_status(store, "user:alice:create", "completed",
                         webex_id="wx-alice")
        update_op_status(store, "user:bob:create", "failed",
                         error_message="Extension conflict")

        # HG is ready — SOFT deps (bob) don't block, REQUIRES (location) is met.
        # But get_next_batch returns lowest (tier, batch) first. HG is tier 4.
        # No lower-tier pending ops in HQ branch, but branch:create (tier 0)
        # is still pending in the other branch. get_next_batch groups by
        # (tier, batch), and tier 0 ops come before tier 4.
        # So we need to check that HG shows up once we account for batching.
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        # Tier 0 has no more ready ops (branch:create is failed, hq done)
        # Actually branch:create is failed, not pending, and hq:create is
        # completed. So no tier 0 ops are ready.
        # Tier 2: no pending HQ users. Branch users blocked (branch failed).
        # Tier 4: HG should be the only ready op.
        assert "hunt_group:sales:create" in node_ids
        update_op_status(store, "hunt_group:sales:create", "completed",
                         webex_id="wx-hg")

        # Round 1 done — check progress
        progress = get_execution_progress(store)
        assert progress["completed"] == 4   # hq create, enable, alice, HG
        assert progress["failed"] == 2      # branch create, bob
        assert progress["skipped"] == 4     # branch enable, carol, dave, CQ (cascade-skipped)

        # === ROUND 2: Fix both failures ===
        update_op_status(store, "location:branch:create", "completed",
                         webex_id="wx-branch")
        update_op_status(store, "user:bob:create", "completed",
                         webex_id="wx-bob")

        # Branch enable_calling becomes ready
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "location:branch:enable_calling"
        update_op_status(store, "location:branch:enable_calling", "completed",
                         webex_id="wx-branch-c")

        # Branch users ready
        batch = get_next_batch(store)
        node_ids = {op["node_id"] for op in batch}
        assert node_ids == {"user:carol:create", "user:dave:create"}
        update_op_status(store, "user:carol:create", "completed",
                         webex_id="wx-carol")
        update_op_status(store, "user:dave:create", "completed",
                         webex_id="wx-dave")

        # Call queue ready
        batch = get_next_batch(store)
        assert len(batch) == 1
        assert batch[0]["node_id"] == "call_queue:support:create"
        update_op_status(store, "call_queue:support:create", "completed",
                         webex_id="wx-cq")

        # === ROUND 3: Done ===
        batch = get_next_batch(store)
        assert len(batch) == 0

        progress = get_execution_progress(store)
        assert progress["completed"] == 10
        assert progress["failed"] == 0  # failures were overwritten by completed
        assert progress["pending"] == 0
        assert progress["skipped"] == 0

    def test_get_next_batch_never_returns_blocked_ops(self, store):
        """Exhaustive check: at no point does get_next_batch return an op
        whose REQUIRES dependency is not completed or skipped."""
        _setup_two_location_plan(store)

        # Run through the plan checking every batch
        completed = set()
        max_iterations = 20  # safety valve

        for _ in range(max_iterations):
            batch = get_next_batch(store)
            if not batch:
                break

            for op in batch:
                node_id = op["node_id"]
                # Check that all REQUIRES deps are completed/skipped
                deps = store.conn.execute(
                    """SELECT pe.from_node, dep.status, pe.dep_type
                       FROM plan_edges pe
                       JOIN plan_operations dep ON dep.node_id = pe.from_node
                       WHERE pe.to_node = ? AND pe.broken = 0""",
                    (node_id,),
                ).fetchall()

                for dep in deps:
                    assert dep["status"] in ("completed", "skipped"), \
                        f"{node_id} returned in batch but dep {dep['from_node']} " \
                        f"is '{dep['status']}'"

                update_op_status(store, node_id, "completed",
                                 webex_id=f"wx-{node_id}")
                completed.add(node_id)

        # All 10 ops should have been completed
        assert len(completed) == 10
