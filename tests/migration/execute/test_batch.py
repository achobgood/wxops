"""Tests for batch partitioning.

Acceptance criteria (from phase-07-planning.md):
- 3 locations → org-wide batch first, then 3 site batches
- Rate limit estimate shown per batch
"""

import pytest
import networkx as nx
from datetime import datetime, timezone

from wxcli.migration.execute import Batch, DependencyType, MigrationOp
from wxcli.migration.execute.batch import (
    format_batch_plan,
    load_plan_from_store,
    partition_into_batches,
    save_plan_to_store,
)
from wxcli.migration.execute.dependency import build_dependency_graph
from wxcli.migration.models import CanonicalUser, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm", source_id="pk", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _insert_user(store, cid):
    """Insert a minimal user object so FK constraints are satisfied."""
    user = CanonicalUser(
        canonical_id=cid, provenance=_prov(), emails=[f"{cid}@test.com"],
        status=MigrationStatus.ANALYZED,
    )
    store.upsert_object(user)


def _op(cid, op_type, resource_type, tier, batch=None, api_calls=1, depends_on=None):
    return MigrationOp(
        canonical_id=cid,
        op_type=op_type,
        resource_type=resource_type,
        tier=tier,
        batch=batch,
        api_calls=api_calls,
        description=f"{op_type} {cid}",
        depends_on=depends_on or [],
    )


class TestPartitionIntoBatches:
    """Two-level partitioning: org-wide → per-site → fixups."""

    def test_three_locations_org_wide_first(self):
        """3 locations + users → org-wide batch first, then 3 site batches."""
        ops = [
            # Org-wide: 3 locations
            _op("location:hq", "create", "location", 0, batch="org-wide"),
            _op("location:branch1", "create", "location", 0, batch="org-wide"),
            _op("location:branch2", "create", "location", 0, batch="org-wide"),
            # Org-wide: 1 trunk
            _op("trunk:main", "create", "trunk", 1, batch="org-wide"),
            # HQ users
            _op("user:u1", "create", "user", 2, batch="location:hq"),
            _op("user:u1", "assign_license", "user", 3, batch="location:hq",
                depends_on=["user:u1:create"]),
            # Branch 1 users
            _op("user:u2", "create", "user", 2, batch="location:branch1"),
            _op("user:u2", "assign_license", "user", 3, batch="location:branch1",
                depends_on=["user:u2:create"]),
            # Branch 2 users
            _op("user:u3", "create", "user", 2, batch="location:branch2"),
            _op("user:u3", "assign_license", "user", 3, batch="location:branch2",
                depends_on=["user:u3:create"]),
        ]
        G = build_dependency_graph(ops)
        batches = partition_into_batches(G)

        # First batches should be org-wide
        assert batches[0].site == "org-wide"
        assert batches[0].tier == 0  # locations

        # Should have org-wide tier 1 (trunk)
        assert batches[1].site == "org-wide"
        assert batches[1].tier == 1

        # Then 3 site batches (sorted alphabetically)
        site_batches = [b for b in batches if b.site != "org-wide"]
        site_names = [b.site for b in site_batches]
        # Each site has tier 2 and tier 3
        assert "location:branch1" in site_names
        assert "location:branch2" in site_names
        assert "location:hq" in site_names

    def test_org_wide_always_first(self):
        """Even with no sites, org-wide comes first."""
        ops = [
            _op("location:l1", "create", "location", 0, batch="org-wide"),
            _op("trunk:t1", "create", "trunk", 1, batch="org-wide"),
        ]
        G = build_dependency_graph(ops)
        batches = partition_into_batches(G)
        assert len(batches) == 2
        assert all(b.site == "org-wide" for b in batches)

    def test_fixups_last(self):
        """Fixup operations always come in the last batch."""
        ops = [
            _op("location:l1", "create", "location", 0, batch="org-wide"),
            _op("user:u1", "create", "user", 2, batch="location:l1"),
        ]
        G = build_dependency_graph(ops)
        # Manually add a fixup node
        G.add_node("fixup:0:a->b", canonical_id="fixup:0", op_type="fixup",
                    resource_type="fixup", tier=7, batch="fixups",
                    api_calls=1, description="fixup")

        batches = partition_into_batches(G)
        assert batches[-1].site == "fixups"
        assert batches[-1].tier == 7

    def test_rate_limit_estimation(self):
        """API call estimates aggregate correctly per batch."""
        ops = [
            _op("user:u1", "create", "user", 2, batch="site-a", api_calls=1),
            _op("user:u2", "create", "user", 2, batch="site-a", api_calls=1),
            _op("user:u3", "create", "user", 2, batch="site-a", api_calls=1),
            _op("user:u1", "configure_settings", "user", 5,
                batch="site-a", api_calls=5),
        ]
        G = build_dependency_graph(ops)
        batches = partition_into_batches(G)

        # Tier 2 batch: 3 creates × 1 call = 3
        tier2_batch = [b for b in batches if b.tier == 2][0]
        assert tier2_batch.estimated_api_calls == 3

        # Tier 5 batch: 1 configure × 5 calls = 5
        tier5_batch = [b for b in batches if b.tier == 5][0]
        assert tier5_batch.estimated_api_calls == 5

    def test_empty_graph(self):
        """Empty graph → no batches."""
        G = nx.DiGraph()
        batches = partition_into_batches(G)
        assert batches == []

    def test_site_with_zero_users(self):
        """Location with no users → org-wide batch only, no site batch."""
        ops = [
            _op("location:empty", "create", "location", 0, batch="org-wide"),
        ]
        G = build_dependency_graph(ops)
        batches = partition_into_batches(G)
        assert len(batches) == 1
        assert batches[0].site == "org-wide"

    def test_none_batch_treated_as_org_wide(self):
        """Ops with batch=None go into the org-wide group."""
        ops = [
            _op("thing:t1", "create", "thing", 2, batch=None),
        ]
        G = build_dependency_graph(ops)
        batches = partition_into_batches(G)
        assert batches[0].site == "org-wide"


class TestFormatBatchPlan:
    """Human-readable batch plan output."""

    def test_format_includes_summary(self):
        batches = [
            Batch(site="org-wide", tier=0, operations=["loc:hq:create"],
                  estimated_api_calls=1),
            Batch(site="location:hq", tier=2,
                  operations=["user:u1:create", "user:u2:create"],
                  estimated_api_calls=2),
        ]
        output = format_batch_plan(batches)
        assert "Execution Plan" in output
        assert "org-wide" in output
        assert "location:hq" in output
        assert "Total:" in output
        assert "3 API calls" in output

    def test_format_empty(self):
        assert format_batch_plan([]) == "No batches to execute."


class TestSavePlanToStore:
    """Persist plan to SQLite plan_operations + plan_edges tables."""

    def test_save_and_query(self, tmp_path):
        store = MigrationStore(tmp_path / "test.db")
        try:
            _insert_user(store, "user:u1")
            ops = [
                _op("user:u1", "create", "user", 2),
                _op("user:u1", "assign_license", "user", 3,
                    depends_on=["user:u1:create"]),
            ]
            G = build_dependency_graph(ops)
            batches = partition_into_batches(G)

            save_plan_to_store(G, store)

            # Verify plan_operations
            rows = store.conn.execute(
                "SELECT * FROM plan_operations ORDER BY tier"
            ).fetchall()
            assert len(rows) == 2
            assert rows[0]["node_id"] == "user:u1:create"
            assert rows[0]["tier"] == 2
            assert rows[1]["node_id"] == "user:u1:assign_license"
            assert rows[1]["tier"] == 3

            # Verify plan_edges
            edge_rows = store.conn.execute("SELECT * FROM plan_edges").fetchall()
            assert len(edge_rows) == 1
            assert edge_rows[0]["from_node"] == "user:u1:create"
            assert edge_rows[0]["to_node"] == "user:u1:assign_license"
        finally:
            store.close()

    def test_save_idempotent(self, tmp_path):
        """Re-saving plan replaces previous data."""
        store = MigrationStore(tmp_path / "test.db")
        try:
            _insert_user(store, "user:u1")
            _insert_user(store, "user:u2")
            _insert_user(store, "user:u3")
            ops1 = [_op("user:u1", "create", "user", 2)]
            G1 = build_dependency_graph(ops1)
            save_plan_to_store(G1, store)

            # Save again with different data
            ops2 = [
                _op("user:u2", "create", "user", 2),
                _op("user:u3", "create", "user", 2),
            ]
            G2 = build_dependency_graph(ops2)
            save_plan_to_store(G2, store)

            rows = store.conn.execute("SELECT * FROM plan_operations").fetchall()
            assert len(rows) == 2  # replaced, not appended
            node_ids = {r["node_id"] for r in rows}
            assert "user:u2:create" in node_ids
            assert "user:u3:create" in node_ids
        finally:
            store.close()

    def test_save_and_load_round_trip(self, tmp_path):
        """Save plan → load plan → graph matches original."""
        store = MigrationStore(tmp_path / "test.db")
        try:
            _insert_user(store, "user:u1")
            ops = [
                _op("user:u1", "create", "user", 2, batch="location:hq"),
                _op("user:u1", "assign_license", "user", 3, batch="location:hq",
                    depends_on=["user:u1:create"]),
            ]
            G = build_dependency_graph(ops)
            save_plan_to_store(G, store)

            # Reconstruct
            G2 = load_plan_from_store(store)
            assert G2.number_of_nodes() == 2
            assert G2.number_of_edges() == 1
            assert G2.nodes["user:u1:create"]["tier"] == 2
            assert G2.nodes["user:u1:create"]["batch"] == "location:hq"
            assert G2.nodes["user:u1:assign_license"]["tier"] == 3
            assert G2.has_edge("user:u1:create", "user:u1:assign_license")
            # Edge type should be reconstructed as DependencyType enum, not raw string
            edge_data = G2.edges["user:u1:create", "user:u1:assign_license"]
            assert edge_data["type"] == DependencyType.CONFIGURES
        finally:
            store.close()

    def test_edge_dep_type_persisted(self, tmp_path):
        """Edge dep_type column is correctly serialized."""
        store = MigrationStore(tmp_path / "test.db")
        try:
            _insert_user(store, "user:u1")
            ops = [
                _op("user:u1", "create", "user", 2),
                _op("user:u1", "assign_license", "user", 3,
                    depends_on=["user:u1:create"]),
            ]
            G = build_dependency_graph(ops)
            save_plan_to_store(G, store)

            edge_rows = store.conn.execute("SELECT * FROM plan_edges").fetchall()
            assert edge_rows[0]["dep_type"] == "configures"
            assert edge_rows[0]["broken"] == 0
        finally:
            store.close()
