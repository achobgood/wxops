"""Wave 3B of silent-failure-hardening — runtime cascade labeling (#13).

Covers Group 4 / Issue #13 of the silent-failure hardening spec:

* Cascade-skip error_message format now names the ROOT failed/skipped op
  (``"Cascade skip: dependency <root> FAILED|SKIPPED"``), so downstream
  consumers can group cascade-skipped ops under a single root cause.
* Multi-level cascades (A → B → C) name A in every descendant's
  error_message, not the intermediate B. This enables cleaner grouping.
* ``get_execution_progress()`` now returns a ``cascade_groups`` dict
  mapping root_node_id → {root_status, descendants} for the execution
  report.
* The ``_undo_cascade_skip`` path continues to work with the new marker
  format — succeeding on retry resets ALL descendants (at every depth),
  not just direct children.
"""

from __future__ import annotations

from datetime import datetime, timezone

import networkx as nx
import pytest

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.runtime import (
    get_execution_progress,
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


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "wave3b.db")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Plan fixtures
# ---------------------------------------------------------------------------

def _setup_linear_chain(store: MigrationStore) -> None:
    """3-level linear chain: location → user → hunt_group.

    location:hq:create → user:alice:create → hunt_group:sales:create
    """
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
        status=MigrationStatus.ANALYZED,
    )
    hg = CanonicalHuntGroup(
        canonical_id="hunt_group:sales", provenance=_prov(),
        name="Sales HG", extension="3001",
        location_id="location:hq",
        status=MigrationStatus.ANALYZED,
    )
    for obj in (loc, user, hg):
        store.upsert_object(obj)

    G = nx.DiGraph()
    G.add_node("location:hq:create", canonical_id="location:hq",
               op_type="create", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ")
    G.add_node("user:alice:create", canonical_id="user:alice",
               op_type="create", resource_type="user",
               tier=2, batch="location:hq", api_calls=1,
               description="Create user alice@acme.com")
    G.add_node("hunt_group:sales:create", canonical_id="hunt_group:sales",
               op_type="create", resource_type="hunt_group",
               tier=4, batch="location:hq", api_calls=1,
               description="Create hunt group Sales")

    G.add_edge("location:hq:create", "user:alice:create",
               type=DependencyType.REQUIRES)
    G.add_edge("user:alice:create", "hunt_group:sales:create",
               type=DependencyType.REQUIRES)

    save_plan_to_store(G, store)


def _setup_fanout(store: MigrationStore) -> None:
    """Root + 3 direct dependents (no further nesting).

    location:hq:create → user:alice:create
                     → user:bob:create
                     → user:carol:create
    """
    loc = CanonicalLocation(
        canonical_id="location:hq", provenance=_prov(),
        name="HQ", time_zone="America/New_York",
        preferred_language="en_US", announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    )
    store.upsert_object(loc)
    for nm, ext in (("alice", "1001"), ("bob", "1002"), ("carol", "1003")):
        u = CanonicalUser(
            canonical_id=f"user:{nm}", provenance=_prov(),
            emails=[f"{nm}@acme.com"], first_name=nm.title(), last_name="X",
            location_id="location:hq", extension=ext,
            status=MigrationStatus.ANALYZED,
        )
        store.upsert_object(u)

    G = nx.DiGraph()
    G.add_node("location:hq:create", canonical_id="location:hq",
               op_type="create", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ")
    for nm in ("alice", "bob", "carol"):
        G.add_node(f"user:{nm}:create", canonical_id=f"user:{nm}",
                   op_type="create", resource_type="user",
                   tier=2, batch="location:hq", api_calls=1,
                   description=f"Create user {nm}")
        G.add_edge("location:hq:create", f"user:{nm}:create",
                   type=DependencyType.REQUIRES)

    save_plan_to_store(G, store)


# ---------------------------------------------------------------------------
# Error-message format
# ---------------------------------------------------------------------------

class TestCascadeErrorMessageFormat:
    """After Wave 3B the error_message on every cascade-skipped op is
    ``"Cascade skip: dependency <root> FAILED"`` (or SKIPPED).

    No intermediate id appears — every descendant at every depth names
    the ROOT. No double-prefix (the old code appended the dep's own id).
    """

    def test_failed_root_produces_failed_marker(self, store):
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="API 500")

        for node_id in ("user:alice:create", "hunt_group:sales:create"):
            row = store.conn.execute(
                "SELECT error_message FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["error_message"] == (
                "Cascade skip: dependency location:hq:create FAILED"
            ), f"{node_id} has {row['error_message']!r}"

    def test_skipped_root_produces_skipped_marker(self, store):
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "skipped",
                         error_message="Admin elected to skip")

        for node_id in ("user:alice:create", "hunt_group:sales:create"):
            row = store.conn.execute(
                "SELECT error_message FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["error_message"] == (
                "Cascade skip: dependency location:hq:create SKIPPED"
            ), f"{node_id} has {row['error_message']!r}"

    def test_no_double_prefix(self, store):
        """Old code wrote ``"Dependency failed: <root>: <dep>"`` (double-
        prefix). New format has no extra node_id appended."""
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="boom")

        msgs = [
            r["error_message"] for r in store.conn.execute(
                "SELECT error_message FROM plan_operations "
                "WHERE status = 'skipped'"
            ).fetchall()
        ]
        # No message should contain the intermediate dep's own id after the root.
        # The new format is a single fixed-format string; ``: `` appears only
        # once (between "skip" and "dependency").
        for msg in msgs:
            # Exactly two spaces-after-colons in the format:
            #   "Cascade skip: dependency <root> FAILED"
            assert msg.count(": ") == 1, f"double-prefix leaked: {msg!r}"


# ---------------------------------------------------------------------------
# Multi-level cascade: every descendant names the ROOT, not intermediates
# ---------------------------------------------------------------------------

class TestMultiLevelCascadeNamesRoot:
    """For a chain A → B → C, when A fails, both B and C's error_message
    must reference A (the root), not B (the immediate cause). This is the
    key design decision — cleaner grouping in the execution report.
    """

    def test_three_level_chain_all_name_root(self, store):
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="address validation failed")

        # Both intermediate (user:alice) and leaf (hunt_group:sales)
        # reference the root (location:hq:create).
        for node_id in ("user:alice:create", "hunt_group:sales:create"):
            row = store.conn.execute(
                "SELECT error_message FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert "location:hq:create" in row["error_message"]
            # Neither should reference the intermediate user id.
            # (The leaf "hunt_group:sales:create" specifically must NOT
            # be labeled with "user:alice:create" as the root.)
            if node_id != "user:alice:create":
                assert "user:alice:create" not in row["error_message"], (
                    f"Leaf {node_id} should reference ROOT (location:hq:create), "
                    f"not intermediate ancestor — got: {row['error_message']!r}"
                )


# ---------------------------------------------------------------------------
# cascade_groups in get_execution_progress()
# ---------------------------------------------------------------------------

class TestCascadeGroupsProgressSection:
    def test_cascade_groups_empty_when_no_cascades(self, store):
        _setup_linear_chain(store)
        progress = get_execution_progress(store)
        assert progress["cascade_groups"] == {}

    def test_cascade_groups_after_root_failure(self, store):
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="boom")

        progress = get_execution_progress(store)
        groups = progress["cascade_groups"]
        assert "location:hq:create" in groups
        group = groups["location:hq:create"]
        assert group["root_status"] == "failed"
        assert set(group["descendants"]) == {
            "user:alice:create",
            "hunt_group:sales:create",
        }

    def test_cascade_groups_after_root_skip(self, store):
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "skipped",
                         error_message="admin skip")

        progress = get_execution_progress(store)
        groups = progress["cascade_groups"]
        assert "location:hq:create" in groups
        assert groups["location:hq:create"]["root_status"] == "skipped"
        assert set(groups["location:hq:create"]["descendants"]) == {
            "user:alice:create",
            "hunt_group:sales:create",
        }

    def test_cascade_groups_fanout_all_descendants(self, store):
        """Root fans out to 3 siblings — all 3 land under the same root."""
        _setup_fanout(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="boom")

        progress = get_execution_progress(store)
        groups = progress["cascade_groups"]
        assert list(groups.keys()) == ["location:hq:create"]
        assert groups["location:hq:create"]["root_status"] == "failed"
        assert set(groups["location:hq:create"]["descendants"]) == {
            "user:alice:create",
            "user:bob:create",
            "user:carol:create",
        }

    def test_cascade_groups_excludes_direct_skips(self, store):
        """A handler-returned SkippedResult writes a handler-supplied reason,
        not the cascade marker. Those ops should NOT appear in cascade_groups.
        Only cascade-labeled ops are grouped.
        """
        _setup_linear_chain(store)
        # Directly skip the user — handler-style reason, no cascade marker.
        update_op_status(store, "user:alice:create", "skipped",
                         error_message="missing dependency: CALLING_LICENSE_ID")

        progress = get_execution_progress(store)
        groups = progress["cascade_groups"]
        # The user itself carries a handler reason, so it's not a cascade
        # descendant. But it DID cascade to hunt_group:sales:create — that
        # descendant IS cascade-labeled with user:alice:create as the root.
        assert "user:alice:create" in groups
        assert groups["user:alice:create"]["root_status"] == "skipped"
        assert groups["user:alice:create"]["descendants"] == [
            "hunt_group:sales:create",
        ]
        # The directly-skipped user itself is NOT in any group's descendants —
        # it's a root, not a cascade-labeled descendant.
        for info in groups.values():
            assert "user:alice:create" not in info["descendants"]


# ---------------------------------------------------------------------------
# Undo cascade: succeeding on retry resets ALL descendants (every depth)
# ---------------------------------------------------------------------------

class TestUndoCascadeResetsAllDescendants:
    def test_retry_success_resets_entire_subtree(self, store):
        """A fails → B, C cascade-skipped with A in error_message.
        A succeeds on retry → both B and C reset to pending.
        """
        _setup_linear_chain(store)

        # Round 1: root fails, descendants cascade-skipped
        update_op_status(store, "location:hq:create", "failed",
                         error_message="boom")
        for node_id in ("user:alice:create", "hunt_group:sales:create"):
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "skipped"

        # Round 2: root succeeds — ALL descendants reset (not just direct)
        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq-fixed")
        for node_id in ("user:alice:create", "hunt_group:sales:create"):
            row = store.conn.execute(
                "SELECT status, error_message FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            assert row["status"] == "pending", (
                f"{node_id} should be 'pending' after root retry, "
                f"got {row['status']!r}"
            )
            assert row["error_message"] is None

    def test_retry_success_fanout(self, store):
        """Root with 3 direct siblings — all 3 reset on root success."""
        _setup_fanout(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="boom")

        update_op_status(store, "location:hq:create", "completed",
                         webex_id="wx-hq")

        for nm in ("alice", "bob", "carol"):
            row = store.conn.execute(
                "SELECT status FROM plan_operations WHERE node_id = ?",
                (f"user:{nm}:create",),
            ).fetchone()
            assert row["status"] == "pending"


# ---------------------------------------------------------------------------
# Regression: skipped status summary still counts cascade-skipped ops
# ---------------------------------------------------------------------------

class TestCascadeDoesNotBreakExistingProgressCounts:
    """The top-level ``skipped`` count in the progress summary must
    continue to include cascade-skipped ops (i.e. the new
    cascade_groups section is additive, not a replacement)."""

    def test_skipped_count_includes_cascade(self, store):
        _setup_linear_chain(store)
        update_op_status(store, "location:hq:create", "failed",
                         error_message="boom")

        progress = get_execution_progress(store)
        assert progress["failed"] == 1
        # user + hunt_group = 2 cascade-skipped
        assert progress["skipped"] == 2
