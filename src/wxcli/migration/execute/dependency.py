"""Dependency graph construction, validation, and cycle breaking.

Builds a NetworkX DiGraph from MigrationOp nodes. Edges come from two sources:
1. Intra-object edges: from the ``depends_on`` field set during expansion
2. Cross-object edges: from cross_refs in the SQLite store

After construction, validates that all edges respect the tier ordering and
detects/breaks cycles with safety rails.

(from 05-dependency-graph.md — build_dependency_graph, validate_tiers,
 detect_and_break_cycles)
"""

from __future__ import annotations

import logging

import networkx as nx

from wxcli.migration.execute import (
    BrokenCycle,
    DependencyType,
    MigrationOp,
    TIER_ASSIGNMENTS,
)
from wxcli.migration.store import MigrationStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cross-object edge rules
# (from 05-dependency-graph.md lines 136-145 — device depends on owner user)
# ---------------------------------------------------------------------------

_CROSS_OBJECT_RULES: list[dict] = [
    # Device depends on its owner user being created
    {
        "source_type": "device",
        "source_op": "create",
        "relationship": "device_owner",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Device depends on its location existing
    {
        "source_type": "device",
        "source_op": "create",
        "relationship": "device_in_location",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # User depends on their location having Calling enabled (Fix 13)
    {
        "source_type": "user",
        "source_op": "create",
        "relationship": "user_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Schedule depends on location having Calling enabled
    {
        "source_type": "schedule",
        "source_op": "create",
        "relationship": "schedule_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Workspace depends on location having Calling enabled
    {
        "source_type": "workspace",
        "source_op": "create",
        "relationship": "workspace_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Trunk depends on location having Calling enabled
    {
        "source_type": "trunk",
        "source_op": "create",
        "relationship": "trunk_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Virtual line depends on location having Calling enabled
    {
        "source_type": "virtual_line",
        "source_op": "create",
        "relationship": "virtual_line_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Hunt group depends on location having Calling enabled
    {
        "source_type": "hunt_group",
        "source_op": "create",
        "relationship": "hunt_group_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Hunt group member users should exist (soft — can break if circular)
    {
        "source_type": "hunt_group",
        "source_op": "create",
        "relationship": "feature_has_agent",
        "target_op": "create",
        "dep_type": DependencyType.SOFT,
    },
    # Call queue depends on location having Calling enabled
    {
        "source_type": "call_queue",
        "source_op": "create",
        "relationship": "call_queue_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Call queue member users should exist
    {
        "source_type": "call_queue",
        "source_op": "create",
        "relationship": "feature_has_agent",
        "target_op": "create",
        "dep_type": DependencyType.SOFT,
    },
    # Call park depends on location having Calling enabled
    {
        "source_type": "call_park",
        "source_op": "create",
        "relationship": "call_park_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Pickup group depends on location having Calling enabled
    {
        "source_type": "pickup_group",
        "source_op": "create",
        "relationship": "pickup_group_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Pickup group member users should exist
    {
        "source_type": "pickup_group",
        "source_op": "create",
        "relationship": "feature_has_agent",
        "target_op": "create",
        "dep_type": DependencyType.SOFT,
    },
    # Paging group depends on location having Calling enabled
    {
        "source_type": "paging_group",
        "source_op": "create",
        "relationship": "paging_group_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Auto attendant depends on location having Calling enabled
    {
        "source_type": "auto_attendant",
        "source_op": "create",
        "relationship": "aa_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Auto attendant depends on its business schedule existing
    {
        "source_type": "auto_attendant",
        "source_op": "create",
        "relationship": "aa_has_schedule",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Call forwarding depends on owner user being created
    {
        "source_type": "call_forwarding",
        "source_op": "configure",
        "relationship": "user_has_call_forwarding",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Monitoring list depends on owner user being created
    {
        "source_type": "monitoring_list",
        "source_op": "configure",
        "relationship": "user_has_monitoring_list",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Monitoring list depends on each monitored target existing (SOFT — partial OK)
    {
        "source_type": "monitoring_list",
        "source_op": "configure",
        "relationship": "monitoring_watches",
        "target_op": "create",
        "dep_type": DependencyType.SOFT,
    },
    # Device layout depends on its device being created
    {
        "source_type": "device_layout",
        "source_op": "configure",
        "relationship": "device_has_layout",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Device layout depends on referenced line key template existing
    {
        "source_type": "device_layout",
        "source_op": "configure",
        "relationship": "layout_uses_template",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Device settings template location settings depends on location having Calling enabled
    {
        "source_type": "device_settings_template",
        "source_op": "apply_location_settings",
        "relationship": "device_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # Device settings template per-device override depends on the device being created
    {
        "source_type": "device_settings_template",
        "source_op": "apply_device_override",
        "relationship": "device_owner",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Advisory-to-execution bridge: Phase A no-ops, but rules are pre-wired for Phase B.
    # These produce no edges in Phase A because the mappers don't set location_canonical_id
    # (no moh_in_location / announcement_in_location cross-refs exist yet). When Phase B
    # adds location resolution to MOHMapper and AnnouncementMapper, these rules will
    # automatically enforce correct execution ordering.
    {
        "source_type": "music_on_hold",
        "source_op": "configure",
        "relationship": "moh_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    {
        "source_type": "announcement",
        "source_op": "upload",
        "relationship": "announcement_in_location",
        "target_op": "enable_calling",
        "dep_type": DependencyType.REQUIRES,
    },
    # device_profile hoteling depends on the owner user being created.
    # Cross-ref user_has_device_profile is already written by DeviceProfileMapper.
    {
        "source_type": "device_profile",
        "source_op": "enable_hoteling_guest",
        "relationship": "user_has_device_profile",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Hunt group forwarding must wait for voicemail group to be created
    # so the VM group extension exists as a valid destination.
    # Cross-ref feature_forwards_to_voicemail_group written by FeatureMapper.
    {
        "source_type": "hunt_group",
        "source_op": "configure_forwarding",
        "relationship": "feature_forwards_to_voicemail_group",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Call queue forwarding must wait for voicemail group to be created.
    {
        "source_type": "call_queue",
        "source_op": "configure_forwarding",
        "relationship": "feature_forwards_to_voicemail_group",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
    # Call queue stranded calls must wait for voicemail group to be created.
    {
        "source_type": "call_queue",
        "source_op": "configure_stranded_calls",
        "relationship": "feature_forwards_to_voicemail_group",
        "target_op": "create",
        "dep_type": DependencyType.REQUIRES,
    },
]


def build_dependency_graph(
    ops: list[MigrationOp],
    store: MigrationStore | None = None,
) -> nx.DiGraph:
    """Build the DAG from all planned migration operations.

    Two sources of edges:
    1. Intra-object: from ``depends_on`` field (set during expansion)
    2. Cross-object: from cross_refs in SQLite (requires store)

    (from 05-dependency-graph.md lines 118-145)
    """
    G = nx.DiGraph()

    # Add all nodes
    for op in ops:
        node_id = f"{op.canonical_id}:{op.op_type}"
        G.add_node(node_id, **op.model_dump())

    # Add intra-object edges (from depends_on field set during expansion)
    for op in ops:
        node_id = f"{op.canonical_id}:{op.op_type}"
        for dep_node_id in op.depends_on:
            if dep_node_id in G:
                G.add_edge(dep_node_id, node_id, type=DependencyType.CONFIGURES)

    # Add cross-object edges from store cross_refs
    if store is not None:
        _add_cross_object_edges(G, ops, store)

    logger.info(
        "Built dependency graph: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def _add_cross_object_edges(
    G: nx.DiGraph,
    ops: list[MigrationOp],
    store: MigrationStore,
) -> None:
    """Add cross-object edges using cross_refs from the store."""
    # Index ops by (canonical_id, op_type) for fast lookup
    op_index: dict[tuple[str, str], str] = {}
    for op in ops:
        node_id = f"{op.canonical_id}:{op.op_type}"
        op_index[(op.canonical_id, op.op_type)] = node_id

    for rule in _CROSS_OBJECT_RULES:
        # Find all ops matching this rule's source
        source_ops = [
            op for op in ops
            if op.resource_type == rule["source_type"]
            and op.op_type == rule["source_op"]
        ]
        for op in source_ops:
            # Query cross_refs for this object + relationship
            targets = store.find_cross_refs(op.canonical_id, rule["relationship"])
            for target_cid in targets:
                target_node = op_index.get((target_cid, rule["target_op"]))
                if target_node is not None:
                    source_node = f"{op.canonical_id}:{op.op_type}"
                    # Edge direction: target must happen before source
                    if target_node != source_node:
                        G.add_edge(
                            target_node,
                            source_node,
                            type=rule["dep_type"],
                        )


def validate_tiers(G: nx.DiGraph) -> list[str]:
    """Check that no operation depends on a higher-tier operation.

    An edge from node U to node V means U must happen before V.
    Therefore V depends on U. If V's tier < U's tier, that's a violation
    (a lower-tier operation depends on a higher-tier one).

    (from 05-dependency-graph.md lines 89-99)
    """
    violations = []
    for u, v in G.edges():
        u_tier = G.nodes[u]["tier"]
        v_tier = G.nodes[v]["tier"]
        if v_tier < u_tier:
            violations.append(
                f"Tier violation: {u} (tier {u_tier}) -> {v} (tier {v_tier})"
            )
    return violations


def detect_and_break_cycles(
    G: nx.DiGraph,
) -> tuple[list[BrokenCycle], list[str]]:
    """Find cycles and break them. Returns broken cycles and hard errors.

    Safety rails:
    - All-REQUIRES cycle → hard error (unbreakable, needs human decision)
    - Mixed or SOFT/CONFIGURES cycle → break weakest edge, create tier 7 fixup

    WARNING: This function mutates G. For all-REQUIRES cycles, one edge is
    removed to unblock further cycle detection — the removed edge is NOT
    tracked in the return value (only in the errors list). Callers should
    treat the graph as potentially incomplete after errors are reported.

    (from 05-dependency-graph.md lines 157-196)
    """
    broken: list[BrokenCycle] = []
    errors: list[str] = []

    while True:
        try:
            cycle = nx.find_cycle(G, orientation="original")
        except nx.NetworkXNoCycle:
            break

        # Collect edge types in the cycle
        edge_types = []
        for edge in cycle:
            u, v = edge[0], edge[1]
            etype = G.edges[u, v].get("type", DependencyType.REQUIRES)
            edge_types.append(etype)

        # All-REQUIRES cycle is a real error
        if all(t == DependencyType.REQUIRES for t in edge_types):
            cycle_desc = " -> ".join(e[0] for e in cycle)
            errors.append(
                f"Unbreakable circular dependency (all REQUIRES edges): "
                f"{cycle_desc}. This requires a human decision to resolve."
            )
            # Remove one edge to unblock further cycle detection
            G.remove_edge(cycle[0][0], cycle[0][1])
            continue

        # Find the weakest edge (prefer breaking SOFT, then CONFIGURES)
        priority = {
            DependencyType.SOFT: 0,
            DependencyType.CONFIGURES: 1,
            DependencyType.REQUIRES: 2,
        }
        weakest_idx = min(
            range(len(cycle)),
            key=lambda i: priority.get(edge_types[i], 2),
        )
        weakest_edge = cycle[weakest_idx]
        u, v = weakest_edge[0], weakest_edge[1]

        # Record the broken edge info before removing
        dep_type_str = str(edge_types[weakest_idx].value) if hasattr(edge_types[weakest_idx], 'value') else str(edge_types[weakest_idx])
        G.remove_edge(u, v)

        broken.append(BrokenCycle(
            from_node=u,
            to_node=v,
            dep_type=dep_type_str,
            reason="Circular dependency broken — this configuration will be "
                   "applied in a post-creation fixup pass (tier 7)",
        ))

    if broken:
        logger.info("Broke %d cycle(s) — fixup operations will be created at tier 7", len(broken))
    if errors:
        logger.error("Found %d unbreakable cycle(s) requiring human resolution", len(errors))

    return broken, errors


def create_fixup_operations(
    broken_cycles: list[BrokenCycle],
    G: nx.DiGraph,
) -> None:
    """Create tier 7 fixup operations for broken cycle edges.

    For each broken edge, creates a new node in the graph that re-applies
    the deferred configuration after all normal tiers complete.

    (from 05-dependency-graph.md line 200 — broken cycles become tier 7 fixups)
    """
    for i, bc in enumerate(broken_cycles):
        fixup_id = f"fixup:{i}:{bc.from_node}->{bc.to_node}"
        G.add_node(
            fixup_id,
            canonical_id=f"fixup:{i}",
            op_type="fixup",
            resource_type="fixup",
            tier=7,
            batch="fixups",
            api_calls=1,
            description=f"Fixup: re-apply {bc.from_node} -> {bc.to_node} ({bc.reason})",
            depends_on=[],
        )
        # Fixup depends on both nodes in the broken edge
        if bc.from_node in G:
            G.add_edge(bc.from_node, fixup_id, type=DependencyType.CONFIGURES)
        if bc.to_node in G:
            G.add_edge(bc.to_node, fixup_id, type=DependencyType.CONFIGURES)
