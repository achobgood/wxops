"""Tests for dependency graph construction, tier validation, and cycle detection.

Acceptance criteria (from phase-07-planning.md):
- Graph with no cycles → topological_sort succeeds
- Graph with SOFT cycle → cycle broken, fixup op created at tier 7
- Graph with all-REQUIRES cycle → error raised
- Tier validation catches a tier 3 op depending on tier 4 op
"""

import pytest
import networkx as nx
from datetime import datetime, timezone

from wxcli.migration.execute import (
    BrokenCycle,
    DependencyType,
    MigrationOp,
)
from wxcli.migration.execute.dependency import (
    build_dependency_graph,
    create_fixup_operations,
    detect_and_break_cycles,
    validate_tiers,
)
from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalUser,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _op(cid, op_type, resource_type, tier, depends_on=None, batch=None):
    return MigrationOp(
        canonical_id=cid,
        op_type=op_type,
        resource_type=resource_type,
        tier=tier,
        batch=batch,
        description=f"{op_type} {cid}",
        depends_on=depends_on or [],
    )


class TestBuildDependencyGraph:
    """Test graph construction from MigrationOp nodes."""

    def test_simple_graph(self):
        """Linear chain: location → user → device."""
        ops = [
            _op("location:hq", "create", "location", 0),
            _op("user:jsmith", "create", "user", 2,
                depends_on=["location:hq:create"]),
            _op("device:phone1", "create", "device", 3,
                depends_on=["user:jsmith:create"]),
        ]
        G = build_dependency_graph(ops)
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2
        assert G.has_edge("location:hq:create", "user:jsmith:create")
        assert G.has_edge("user:jsmith:create", "device:phone1:create")

    def test_user_expansion_chain(self):
        """User 5-op chain produces 4 intra-object edges."""
        ops = [
            _op("user:u1", "create", "user", 2),
            _op("user:u1", "assign_license", "user", 3,
                depends_on=["user:u1:create"]),
            _op("user:u1", "assign_number", "user", 3,
                depends_on=["user:u1:assign_license"]),
            _op("user:u1", "configure_settings", "user", 5,
                depends_on=["user:u1:assign_number"]),
            _op("user:u1", "configure_voicemail", "user", 5,
                depends_on=["user:u1:assign_number"]),
        ]
        G = build_dependency_graph(ops)
        assert G.number_of_nodes() == 5
        assert G.number_of_edges() == 4

    def test_no_cycles_topological_sort(self):
        """DAG with no cycles → topological_sort succeeds."""
        ops = [
            _op("location:hq", "create", "location", 0),
            _op("trunk:t1", "create", "trunk", 1),
            _op("user:u1", "create", "user", 2),
            _op("device:d1", "create", "device", 3,
                depends_on=["user:u1:create"]),
        ]
        G = build_dependency_graph(ops)
        order = list(nx.topological_sort(G))
        assert len(order) == 4
        # Location and trunk have no dependency, so they can be in any order
        # But device must come after user
        assert order.index("user:u1:create") < order.index("device:d1:create")

    def test_missing_dependency_ignored(self):
        """depends_on referencing a non-existent node is silently skipped."""
        ops = [
            _op("user:u1", "create", "user", 2,
                depends_on=["location:nonexistent:create"]),
        ]
        G = build_dependency_graph(ops)
        assert G.number_of_nodes() == 1
        assert G.number_of_edges() == 0

    def test_node_attributes_preserved(self):
        """Node attributes from MigrationOp are stored on the graph."""
        ops = [
            _op("user:u1", "create", "user", 2, batch="location:hq"),
        ]
        G = build_dependency_graph(ops)
        node_data = G.nodes["user:u1:create"]
        assert node_data["canonical_id"] == "user:u1"
        assert node_data["op_type"] == "create"
        assert node_data["resource_type"] == "user"
        assert node_data["tier"] == 2
        assert node_data["batch"] == "location:hq"


class TestValidateTiers:
    """Tier validation catches backward dependencies."""

    def test_valid_tiers(self):
        """All edges go from lower to higher tier → no violations."""
        G = nx.DiGraph()
        G.add_node("a", tier=0)
        G.add_node("b", tier=2)
        G.add_node("c", tier=3)
        G.add_edge("a", "b")
        G.add_edge("b", "c")

        violations = validate_tiers(G)
        assert violations == []

    def test_same_tier_valid(self):
        """Edges within the same tier are valid."""
        G = nx.DiGraph()
        G.add_node("a", tier=4)
        G.add_node("b", tier=4)
        G.add_edge("a", "b")

        violations = validate_tiers(G)
        assert violations == []

    def test_tier_violation_detected(self):
        """Tier 3 op depending on tier 4 op → violation."""
        G = nx.DiGraph()
        G.add_node("high_tier", tier=4)
        G.add_node("low_tier", tier=3)
        # Edge means: high_tier must happen before low_tier
        # So low_tier depends on high_tier — but low_tier has lower tier!
        G.add_edge("high_tier", "low_tier")

        violations = validate_tiers(G)
        assert len(violations) == 1
        assert "tier 4" in violations[0]
        assert "tier 3" in violations[0]

    def test_multiple_violations(self):
        """Multiple tier violations all reported."""
        G = nx.DiGraph()
        G.add_node("a", tier=5)
        G.add_node("b", tier=3)
        G.add_node("c", tier=4)
        G.add_node("d", tier=2)
        G.add_edge("a", "b")  # 5 → 3 violation
        G.add_edge("c", "d")  # 4 → 2 violation

        violations = validate_tiers(G)
        assert len(violations) == 2


class TestDetectAndBreakCycles:
    """Cycle detection and breaking with safety rails."""

    def test_no_cycles(self):
        """Acyclic graph → no cycles found."""
        G = nx.DiGraph()
        G.add_node("a", tier=0)
        G.add_node("b", tier=2)
        G.add_edge("a", "b", type=DependencyType.REQUIRES)

        broken, errors = detect_and_break_cycles(G)
        assert broken == []
        assert errors == []

    def test_soft_cycle_broken(self):
        """SOFT cycle → broken, one BrokenCycle returned."""
        G = nx.DiGraph()
        G.add_node("a", tier=4)
        G.add_node("b", tier=4)
        G.add_edge("a", "b", type=DependencyType.SOFT)
        G.add_edge("b", "a", type=DependencyType.SOFT)

        broken, errors = detect_and_break_cycles(G)
        assert len(broken) == 1
        assert errors == []
        assert broken[0].dep_type == "soft"
        assert "tier 7" in broken[0].reason

    def test_configures_cycle_broken(self):
        """CONFIGURES cycle → broken at the CONFIGURES edge."""
        G = nx.DiGraph()
        G.add_node("a", tier=4)
        G.add_node("b", tier=4)
        G.add_edge("a", "b", type=DependencyType.REQUIRES)
        G.add_edge("b", "a", type=DependencyType.CONFIGURES)

        broken, errors = detect_and_break_cycles(G)
        assert len(broken) == 1
        assert errors == []
        # Should break the CONFIGURES edge, not the REQUIRES one
        assert broken[0].dep_type == "configures"

    def test_all_requires_cycle_error(self):
        """All-REQUIRES cycle → hard error, not silently broken."""
        G = nx.DiGraph()
        G.add_node("a", tier=4)
        G.add_node("b", tier=4)
        G.add_edge("a", "b", type=DependencyType.REQUIRES)
        G.add_edge("b", "a", type=DependencyType.REQUIRES)

        broken, errors = detect_and_break_cycles(G)
        assert len(errors) == 1
        assert "Unbreakable" in errors[0]
        assert "REQUIRES" in errors[0]

    def test_mixed_cycle_breaks_weakest(self):
        """Cycle with REQUIRES + SOFT → breaks SOFT edge."""
        G = nx.DiGraph()
        G.add_node("a", tier=4)
        G.add_node("b", tier=4)
        G.add_node("c", tier=4)
        G.add_edge("a", "b", type=DependencyType.REQUIRES)
        G.add_edge("b", "c", type=DependencyType.REQUIRES)
        G.add_edge("c", "a", type=DependencyType.SOFT)

        broken, errors = detect_and_break_cycles(G)
        assert len(broken) == 1
        assert errors == []
        assert broken[0].dep_type == "soft"

    def test_multiple_cycles(self):
        """Multiple independent cycles all detected and handled."""
        G = nx.DiGraph()
        # Cycle 1: soft
        G.add_node("a1", tier=4)
        G.add_node("b1", tier=4)
        G.add_edge("a1", "b1", type=DependencyType.SOFT)
        G.add_edge("b1", "a1", type=DependencyType.SOFT)
        # Cycle 2: requires (error)
        G.add_node("a2", tier=4)
        G.add_node("b2", tier=4)
        G.add_edge("a2", "b2", type=DependencyType.REQUIRES)
        G.add_edge("b2", "a2", type=DependencyType.REQUIRES)

        broken, errors = detect_and_break_cycles(G)
        assert len(broken) == 1  # soft cycle broken
        assert len(errors) == 1  # requires cycle errored

    def test_graph_acyclic_after_breaking(self):
        """After breaking cycles, graph is a valid DAG."""
        G = nx.DiGraph()
        G.add_node("a", tier=4)
        G.add_node("b", tier=4)
        G.add_node("c", tier=4)
        G.add_edge("a", "b", type=DependencyType.SOFT)
        G.add_edge("b", "c", type=DependencyType.CONFIGURES)
        G.add_edge("c", "a", type=DependencyType.SOFT)

        broken, errors = detect_and_break_cycles(G)
        assert errors == []
        # Graph should now be acyclic
        assert nx.is_directed_acyclic_graph(G)


class TestCreateFixupOperations:
    """Broken cycles produce tier 7 fixup nodes."""

    def test_fixup_created(self):
        G = nx.DiGraph()
        G.add_node("a", tier=4, canonical_id="aa:1", op_type="create",
                    resource_type="auto_attendant")
        G.add_node("b", tier=4, canonical_id="aa:2", op_type="create",
                    resource_type="auto_attendant")

        broken_cycles = [
            BrokenCycle(
                from_node="a", to_node="b",
                dep_type="soft",
                reason="Circular dependency broken",
            ),
        ]

        create_fixup_operations(broken_cycles, G)

        fixup_nodes = [n for n in G.nodes() if "fixup" in n]
        assert len(fixup_nodes) == 1
        fixup = G.nodes[fixup_nodes[0]]
        assert fixup["tier"] == 7
        assert fixup["batch"] == "fixups"

    def test_fixup_depends_on_both_nodes(self):
        G = nx.DiGraph()
        G.add_node("x", tier=4)
        G.add_node("y", tier=4)

        broken_cycles = [
            BrokenCycle(from_node="x", to_node="y", dep_type="soft", reason="test"),
        ]
        create_fixup_operations(broken_cycles, G)

        fixup_nodes = [n for n in G.nodes() if "fixup" in n]
        assert len(fixup_nodes) == 1
        # Fixup should have edges FROM both x and y
        predecessors = list(G.predecessors(fixup_nodes[0]))
        assert "x" in predecessors
        assert "y" in predecessors


def _prov():
    return Provenance(
        source_system="cucm", source_id="pk", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


class TestCrossObjectEdges:
    """Cross-object edges via store cross_refs."""

    def test_device_owner_edge(self, tmp_path):
        """Device depends on its owner user via cross_refs."""
        store = MigrationStore(tmp_path / "test.db")
        try:
            # Insert objects
            user = CanonicalUser(
                canonical_id="user:jsmith", provenance=_prov(),
                emails=["jsmith@acme.com"],
                status=MigrationStatus.ANALYZED,
            )
            device = CanonicalDevice(
                canonical_id="device:phone1", provenance=_prov(),
                mac="AABB", compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
                status=MigrationStatus.ANALYZED,
            )
            store.upsert_object(user)
            store.upsert_object(device)
            store.add_cross_ref("device:phone1", "user:jsmith", "device_owner")

            ops = [
                _op("user:jsmith", "create", "user", 2),
                _op("device:phone1", "create", "device", 3),
            ]
            G = build_dependency_graph(ops, store=store)

            # Device create should depend on user create
            assert G.has_edge("user:jsmith:create", "device:phone1:create")
            edge_data = G.edges["user:jsmith:create", "device:phone1:create"]
            assert edge_data["type"] == DependencyType.REQUIRES
        finally:
            store.close()

    def test_user_location_edge(self, tmp_path):
        """User depends on its location's enable_calling via cross_refs (Fix 13)."""
        store = MigrationStore(tmp_path / "test.db")
        try:
            from wxcli.migration.models import CanonicalLocation
            loc = CanonicalLocation(
                canonical_id="location:hq", provenance=_prov(),
                name="HQ", status=MigrationStatus.ANALYZED,
            )
            user = CanonicalUser(
                canonical_id="user:u1", provenance=_prov(),
                emails=["u1@acme.com"],
                status=MigrationStatus.ANALYZED,
            )
            store.upsert_object(loc)
            store.upsert_object(user)
            store.add_cross_ref("user:u1", "location:hq", "user_in_location")

            ops = [
                _op("location:hq", "create", "location", 0),
                _op("location:hq", "enable_calling", "location", 0,
                    depends_on=["location:hq:create"]),
                _op("user:u1", "create", "user", 2),
            ]
            G = build_dependency_graph(ops, store=store)

            # Fix 13: user depends on enable_calling, not create
            assert G.has_edge("location:hq:enable_calling", "user:u1:create")
        finally:
            store.close()

    def test_missing_cross_ref_target_ignored(self, tmp_path):
        """Cross-ref target exists in store but has no op in the graph → no edge."""
        store = MigrationStore(tmp_path / "test.db")
        try:
            device = CanonicalDevice(
                canonical_id="device:orphan", provenance=_prov(),
                mac="FFFF", status=MigrationStatus.ANALYZED,
            )
            # User exists in store but will NOT have ops in the graph
            user = CanonicalUser(
                canonical_id="user:no_ops", provenance=_prov(),
                emails=["noops@acme.com"],
                status=MigrationStatus.NEEDS_DECISION,  # not analyzed
            )
            store.upsert_object(device)
            store.upsert_object(user)
            store.add_cross_ref("device:orphan", "user:no_ops", "device_owner")

            # Only device op in graph, no user op
            ops = [_op("device:orphan", "create", "device", 3)]
            G = build_dependency_graph(ops, store=store)

            # No edge added — target op not in graph
            assert G.number_of_edges() == 0
        finally:
            store.close()


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _set_analyzed(obj):
    obj.status = MigrationStatus.ANALYZED
    return obj


class TestPhase3CrossObjectRules:
    """Cross-object edge rules for Phase 3 types."""

    def test_call_forwarding_depends_on_user(self, store):
        """call_forwarding:configure must come after user:create."""
        from wxcli.migration.models import CanonicalCallForwarding, CanonicalUser
        from wxcli.migration.execute.dependency import build_dependency_graph
        from wxcli.migration.execute.planner import expand_to_operations

        user = _set_analyzed(CanonicalUser(
            canonical_id="user:jsmith",
            provenance=_prov(),
            emails=["jsmith@example.com"],
        ))
        cf = _set_analyzed(CanonicalCallForwarding(
            canonical_id="call_forwarding:user:jsmith",
            provenance=_prov(),
            user_canonical_id="user:jsmith",
            always_enabled=True,
            always_destination="+12223334444",
        ))
        store.upsert_object(user)
        store.upsert_object(cf)
        store.add_cross_ref("call_forwarding:user:jsmith", "user:jsmith", "user_has_call_forwarding")

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        assert G.has_edge("user:jsmith:create", "call_forwarding:user:jsmith:configure")

    def test_monitoring_list_depends_on_user(self, store):
        """monitoring_list:configure must come after user:create."""
        from wxcli.migration.models import CanonicalMonitoringList, CanonicalUser
        from wxcli.migration.execute.dependency import build_dependency_graph
        from wxcli.migration.execute.planner import expand_to_operations

        user = _set_analyzed(CanonicalUser(
            canonical_id="user:jsmith",
            provenance=_prov(),
            emails=["jsmith@example.com"],
        ))
        ml = _set_analyzed(CanonicalMonitoringList(
            canonical_id="monitoring_list:user:jsmith",
            provenance=_prov(),
            user_canonical_id="user:jsmith",
            monitored_members=[{"target_canonical_id": "user:alice"}],
        ))
        store.upsert_object(user)
        store.upsert_object(ml)
        store.add_cross_ref("monitoring_list:user:jsmith", "user:jsmith", "user_has_monitoring_list")

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        assert G.has_edge("user:jsmith:create", "monitoring_list:user:jsmith:configure")

    def test_device_layout_depends_on_device(self, store):
        """device_layout:configure must come after device:create."""
        from wxcli.migration.models import CanonicalDevice, CanonicalDeviceLayout
        from wxcli.migration.execute.dependency import build_dependency_graph
        from wxcli.migration.execute.planner import expand_to_operations
        from wxcli.migration.models import DeviceCompatibilityTier

        device = _set_analyzed(CanonicalDevice(
            canonical_id="device:SEPAA112233",
            provenance=_prov(),
            mac="AA112233",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        layout = _set_analyzed(CanonicalDeviceLayout(
            canonical_id="device_layout:SEPAA112233",
            provenance=_prov(),
            device_canonical_id="device:SEPAA112233",
            resolved_line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
        ))
        store.upsert_object(device)
        store.upsert_object(layout)
        store.add_cross_ref("device_layout:SEPAA112233", "device:SEPAA112233", "device_has_layout")

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        assert G.has_edge("device:SEPAA112233:create", "device_layout:SEPAA112233:configure")

    def test_device_layout_depends_on_template(self, store):
        """device_layout:configure must come after line_key_template:create."""
        from wxcli.migration.models import CanonicalDeviceLayout, CanonicalLineKeyTemplate
        from wxcli.migration.execute.dependency import build_dependency_graph
        from wxcli.migration.execute.planner import expand_to_operations

        tmpl = _set_analyzed(CanonicalLineKeyTemplate(
            canonical_id="line_key_template:Standard 8845",
            provenance=_prov(),
            name="Standard 8845",
            device_model="DMS Cisco 8845",
            line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
            phones_using=1,
        ))
        layout = _set_analyzed(CanonicalDeviceLayout(
            canonical_id="device_layout:SEPAA112233",
            provenance=_prov(),
            device_canonical_id="device:SEPAA112233",
            template_canonical_id="line_key_template:Standard 8845",
            resolved_line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
        ))
        store.upsert_object(tmpl)
        store.upsert_object(layout)
        store.add_cross_ref(
            "device_layout:SEPAA112233",
            "line_key_template:Standard 8845",
            "layout_uses_template",
        )

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        assert G.has_edge(
            "line_key_template:Standard 8845:create",
            "device_layout:SEPAA112233:configure",
        )
