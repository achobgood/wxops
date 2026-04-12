"""Tests for DECT network planner expansion.

Spec §5d: _expand_dect_network() requirements.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.execute import API_CALL_ESTIMATES, TIER_ASSIGNMENTS
from wxcli.migration.execute.planner import _EXPANDERS, _expand_dect_network
from wxcli.migration.models import CanonicalDECTNetwork, MigrationStatus, Provenance


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk-dect",
        source_name="DECT-TEST",
        extracted_at=datetime.now(timezone.utc),
    )


def _analyzed_dect(cid: str, **kwargs) -> dict:
    """Build a minimal analyzed CanonicalDECTNetwork dict."""
    network = CanonicalDECTNetwork(
        canonical_id=cid,
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        **kwargs,
    )
    return network.model_dump()


class TestExpandDECTNetworkDependencyOrder:
    """test_expand_dect_network_dependency_order"""

    def test_produces_three_ops(self):
        obj = _analyzed_dect(
            "dect_network:POOL-HQ",
            display_name="HQ DECT",
            location_canonical_id="location:hq",
            base_stations=[{"mac": "AABB001122CC", "display_name": "BS-1"}],
            handset_assignments=[],
        )
        ops = _expand_dect_network(obj)
        assert len(ops) == 3

    def test_op_types_in_order(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        assert [op.op_type for op in ops] == ["create", "create_base_stations", "assign_handsets"]

    def test_create_depends_on_location(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        create_op = ops[0]
        assert "location:hq:create" in create_op.depends_on

    def test_create_base_stations_depends_on_create(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        bs_op = ops[1]
        assert "dect_network:POOL-HQ:create" in bs_op.depends_on

    def test_assign_handsets_depends_on_base_stations(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        assert "dect_network:POOL-HQ:create_base_stations" in hs_op.depends_on

    def test_assign_handsets_depends_on_user_owners(self):
        obj = _analyzed_dect(
            "dect_network:POOL-HQ",
            location_canonical_id="location:hq",
            handset_assignments=[
                {"index": 1, "user_canonical_id": "user:jsmith", "display_name": "J Smith"},
                {"index": 2, "user_canonical_id": "user:jdoe", "display_name": "J Doe"},
            ],
        )
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        assert "user:jsmith:create" in hs_op.depends_on
        assert "user:jdoe:create" in hs_op.depends_on

    def test_assign_handsets_depends_on_workspace_owners(self):
        obj = _analyzed_dect(
            "dect_network:POOL-HQ",
            location_canonical_id="location:hq",
            handset_assignments=[
                {"index": 1, "user_canonical_id": "workspace:lobby", "display_name": "Lobby"},
            ],
        )
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        assert "workspace:lobby:create" in hs_op.depends_on

    def test_no_location_no_create_dep(self):
        obj = _analyzed_dect("dect_network:POOL-ORPHAN", location_canonical_id=None)
        ops = _expand_dect_network(obj)
        create_op = ops[0]
        assert create_op.depends_on == []

    def test_no_location_batch_is_none(self):
        obj = _analyzed_dect("dect_network:POOL-ORPHAN", location_canonical_id=None)
        ops = _expand_dect_network(obj)
        for op in ops:
            assert op.batch is None

    def test_batch_set_to_location_cid(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        for op in ops:
            assert op.batch == "location:hq"

    def test_all_ops_have_dect_network_resource_type(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        for op in ops:
            assert op.resource_type == "dect_network"

    def test_all_ops_have_correct_canonical_id(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        for op in ops:
            assert op.canonical_id == "dect_network:POOL-HQ"

    def test_tier_assignments(self):
        obj = _analyzed_dect("dect_network:POOL-HQ", location_canonical_id="location:hq")
        ops = _expand_dect_network(obj)
        create_op, bs_op, hs_op = ops
        assert create_op.tier == 2
        assert bs_op.tier == 2
        assert hs_op.tier == 3

    def test_no_handsets_assign_depends_only_on_base_stations(self):
        obj = _analyzed_dect(
            "dect_network:POOL-HQ",
            location_canonical_id="location:hq",
            handset_assignments=[],
        )
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        assert hs_op.depends_on == ["dect_network:POOL-HQ:create_base_stations"]

    def test_duplicate_owner_deps_are_deduplicated(self):
        """Same user as owner for multiple handsets → single dep entry."""
        obj = _analyzed_dect(
            "dect_network:POOL-HQ",
            location_canonical_id="location:hq",
            handset_assignments=[
                {"index": 1, "user_canonical_id": "user:jsmith"},
                {"index": 2, "user_canonical_id": "user:jsmith"},
            ],
        )
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        user_create_deps = [d for d in hs_op.depends_on if d == "user:jsmith:create"]
        assert len(user_create_deps) == 1


class TestExpandDECTNetworkHandsetBatching:
    """test_expand_dect_network_handset_batching

    The planner emits one assign_handsets op per DECT network. The handler
    is responsible for batching API calls (e.g., groups of 50). Here we verify
    the op captures all handset_assignments and the op data passes them through.
    """

    def test_many_handsets_produce_single_assign_op(self):
        """60 handsets → still 3 ops (batching is handler responsibility)."""
        handsets = [
            {"index": i, "user_canonical_id": f"user:u{i}", "display_name": f"User {i}"}
            for i in range(60)
        ]
        obj = _analyzed_dect(
            "dect_network:POOL-LARGE",
            location_canonical_id="location:campus",
            handset_assignments=handsets,
        )
        ops = _expand_dect_network(obj)
        # Always 3 ops regardless of handset count
        assert len(ops) == 3
        assign_op = ops[2]
        assert assign_op.op_type == "assign_handsets"

    def test_many_handsets_all_owners_in_deps(self):
        """All unique user owners appear in assign_handsets depends_on."""
        handsets = [
            {"index": i, "user_canonical_id": f"user:u{i}"}
            for i in range(10)
        ]
        obj = _analyzed_dect(
            "dect_network:POOL-LARGE",
            location_canonical_id="location:campus",
            handset_assignments=handsets,
        )
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        for i in range(10):
            assert f"user:u{i}:create" in hs_op.depends_on

    def test_handsets_without_owner_do_not_add_deps(self):
        """Handsets with no user_canonical_id don't add spurious deps."""
        handsets = [
            {"index": 1, "display_name": "Unassigned HS"},  # no user_canonical_id
            {"index": 2, "user_canonical_id": None},         # explicit None
        ]
        obj = _analyzed_dect(
            "dect_network:POOL-HQ",
            location_canonical_id="location:hq",
            handset_assignments=handsets,
        )
        ops = _expand_dect_network(obj)
        hs_op = ops[2]
        # Only the base_stations dep, no user deps
        assert hs_op.depends_on == ["dect_network:POOL-HQ:create_base_stations"]


class TestDECTNetworkRegistry:
    def test_in_expanders(self):
        assert "dect_network" in _EXPANDERS

    def test_tier_create(self):
        assert TIER_ASSIGNMENTS.get(("dect_network", "create")) == 2

    def test_tier_create_base_stations(self):
        assert TIER_ASSIGNMENTS.get(("dect_network", "create_base_stations")) == 2

    def test_tier_assign_handsets(self):
        assert TIER_ASSIGNMENTS.get(("dect_network", "assign_handsets")) == 3

    def test_api_call_estimates_present(self):
        assert "dect_network:create" in API_CALL_ESTIMATES
        assert "dect_network:create_base_stations" in API_CALL_ESTIMATES
        assert "dect_network:assign_handsets" in API_CALL_ESTIMATES
