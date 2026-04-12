"""Batch partitioning — split the DAG into executable batches.

Two-level partitioning:
1. Org-wide vs site-specific (based on batch assignment on each node)
2. Within each group, split by tier

Batch ordering:
1. org-wide tiers 0-1 (locations, trunks, schedules, route groups)
2. org-wide tier 2 (dial plans, calling permissions)
3. Per-site tiers 2-6 (users, devices, features, settings)
4. Fixups tier 7 (broken cycle fixups)

(from 05-dependency-graph.md lines 202-261)
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict

import networkx as nx

from wxcli.migration.execute import Batch, DependencyType

logger = logging.getLogger(__name__)


def partition_into_batches(
    G: nx.DiGraph,
    rate_limit_per_minute: int = 100,
) -> list[Batch]:
    """Partition the DAG into executable batches.

    Batches are ordered: org-wide first, then per-site, then fixups.
    Within each group, split by tier. Returns a list of Batch objects
    with estimated API call counts and timing.

    (from 05-dependency-graph.md lines 221-258)
    """
    # Separate nodes by batch assignment
    org_wide_nodes: list[str] = []
    fixup_nodes: list[str] = []
    site_nodes: dict[str, list[str]] = defaultdict(list)

    for node in nx.topological_sort(G):
        batch = G.nodes[node].get("batch")
        tier = G.nodes[node].get("tier", 0)

        if batch == "fixups":
            fixup_nodes.append(node)
        elif batch is None or batch == "org-wide":
            org_wide_nodes.append(node)
        else:
            site_nodes[batch].append(node)

    batches: list[Batch] = []

    # 1. Org-wide batches first, split by tier
    batches.extend(_split_by_tier(org_wide_nodes, G, "org-wide"))

    # 2. Per-site batches, sorted by site name for determinism
    for site in sorted(site_nodes.keys()):
        batches.extend(_split_by_tier(site_nodes[site], G, site))

    # 3. Fixup batch last
    if fixup_nodes:
        batches.extend(_split_by_tier(fixup_nodes, G, "fixups"))

    # Log summary
    total_ops = sum(len(b.operations) for b in batches)
    total_api = sum(b.estimated_api_calls for b in batches)
    logger.info(
        "Partitioned %d operations into %d batches "
        "(estimated %d API calls, ~%d min at %d req/min)",
        total_ops,
        len(batches),
        total_api,
        math.ceil(total_api / rate_limit_per_minute) if total_api else 0,
        rate_limit_per_minute,
    )

    return batches


def _split_by_tier(
    nodes: list[str],
    G: nx.DiGraph,
    site: str,
) -> list[Batch]:
    """Split a set of nodes into one batch per tier.

    (from 05-dependency-graph.md lines 244-258)
    """
    by_tier: dict[int, list[str]] = defaultdict(list)
    for n in nodes:
        tier = G.nodes[n].get("tier", 0)
        by_tier[tier].append(n)

    batches = []
    for tier in sorted(by_tier.keys()):
        tier_nodes = by_tier[tier]
        api_calls = sum(G.nodes[n].get("api_calls", 1) for n in tier_nodes)
        batches.append(Batch(
            site=site,
            tier=tier,
            operations=tier_nodes,
            estimated_api_calls=api_calls,
        ))

    return batches


def format_batch_plan(
    batches: list[Batch],
    rate_limit_per_minute: int = 100,
) -> str:
    """Format a human-readable execution plan from batches.

    (from 05-dependency-graph.md lines 285-295 — plan output format)
    """
    if not batches:
        return "No batches to execute."

    lines: list[str] = ["Execution Plan", "=" * 60]

    total_api = 0
    for batch in batches:
        total_api += batch.estimated_api_calls
        est_minutes = math.ceil(batch.estimated_api_calls / rate_limit_per_minute) if batch.estimated_api_calls else 0

        # Count operations by type
        op_counts: dict[str, int] = defaultdict(int)
        for node_id in batch.operations:
            # node_id format: "canonical_id:op_type"
            parts = node_id.rsplit(":", 1)
            if len(parts) == 2:
                op_counts[parts[1]] += 1
            else:
                op_counts["unknown"] += 1

        op_summary = ", ".join(
            f"{count} {op_type}" for op_type, count in sorted(op_counts.items())
        )

        lines.append(f"\nBatch: {batch.site} / tier {batch.tier}")
        lines.append(f"  Operations: {op_summary}")
        lines.append(f"  Estimated API calls: {batch.estimated_api_calls}")
        if est_minutes > 0:
            lines.append(f"  Estimated time at {rate_limit_per_minute} req/min: ~{est_minutes} minutes")

    total_minutes = math.ceil(total_api / rate_limit_per_minute) if total_api else 0
    lines.append(f"\n{'=' * 60}")
    lines.append(f"Total: {sum(len(b.operations) for b in batches)} operations, "
                 f"{total_api} API calls, ~{total_minutes} minutes")

    return "\n".join(lines)


def save_plan_to_store(
    G: nx.DiGraph,
    store: "MigrationStore",
) -> None:
    """Persist the execution plan (operations + edges) to SQLite.

    Writes to plan_operations and plan_edges tables. Clears any
    existing plan data first (idempotent re-planning).

    (from 05-dependency-graph.md lines 300-327 — plan_operations + plan_edges tables)
    """
    conn = store.conn

    # Clear existing plan (edges first — FK constraint)
    conn.execute("DELETE FROM plan_edges")
    conn.execute("DELETE FROM plan_operations")

    # Write operations
    for node_id in G.nodes():
        node = G.nodes[node_id]
        conn.execute(
            """INSERT INTO plan_operations
               (node_id, canonical_id, op_type, resource_type, tier, batch,
                api_calls, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node_id,
                node.get("canonical_id", ""),
                node.get("op_type", ""),
                node.get("resource_type", ""),
                node.get("tier", 0),
                node.get("batch"),
                node.get("api_calls", 1),
                node.get("description", ""),
                "pending",
            ),
        )

    # Write edges
    for u, v, data in G.edges(data=True):
        dep_type = data.get("type", DependencyType.CONFIGURES)
        dep_type_str = dep_type.value if hasattr(dep_type, "value") else str(dep_type)
        conn.execute(
            """INSERT OR IGNORE INTO plan_edges (from_node, to_node, dep_type, broken)
               VALUES (?, ?, ?, ?)""",
            (u, v, dep_type_str, 0),
        )

    conn.commit()

    total_ops = G.number_of_nodes()
    total_edges = G.number_of_edges()
    logger.info("Saved plan to SQLite: %d operations, %d edges", total_ops, total_edges)


def load_plan_from_store(store: "MigrationStore") -> nx.DiGraph:
    """Reconstruct the NetworkX DiGraph from SQLite plan tables.

    The tables are the source of truth; the in-memory graph is a working view.

    (from 05-dependency-graph.md line 328)
    """
    G = nx.DiGraph()
    conn = store.conn

    # Load nodes
    rows = conn.execute(
        """SELECT node_id, canonical_id, op_type, resource_type, tier, batch,
                  api_calls, description, status
           FROM plan_operations"""
    ).fetchall()
    for row in rows:
        G.add_node(
            row["node_id"],
            canonical_id=row["canonical_id"],
            op_type=row["op_type"],
            resource_type=row["resource_type"],
            tier=row["tier"],
            batch=row["batch"],
            api_calls=row["api_calls"],
            description=row["description"],
            status=row["status"],
        )

    # Load edges
    edge_rows = conn.execute(
        "SELECT from_node, to_node, dep_type, broken FROM plan_edges"
    ).fetchall()
    for row in edge_rows:
        _valid_values = {e.value for e in DependencyType}
        dep_type = DependencyType(row["dep_type"]) if row["dep_type"] in _valid_values else row["dep_type"]
        G.add_edge(
            row["from_node"],
            row["to_node"],
            type=dep_type,
            broken=bool(row["broken"]),
        )

    logger.info(
        "Loaded plan from SQLite: %d operations, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G
