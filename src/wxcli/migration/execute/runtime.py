"""Runtime execution support — operation metadata, status tracking, rollback.

Returns operation metadata (resource type, canonical data, resolved
dependency IDs) instead of pre-built CLI command strings. The cucm-migrate
skill uses this metadata to delegate to domain skills, which build and
execute the actual commands.

(Phase 12b — runtime.py)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.store import MigrationStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_next_batch(store: MigrationStore) -> list[dict[str, Any]]:
    """Return all pending ops whose dependencies are all completed.

    Algorithm:
    1. Query plan_operations WHERE status = 'pending'
    2. For each pending op, check plan_edges: all predecessors must be
       status = 'completed' or 'skipped'
    3. Group qualifying ops by (batch, tier), return the lowest group
    4. For each op, include the canonical object data and resolved
       dependency IDs (webex_ids from completed predecessor ops)

    Returns list of dicts:
    {
        "node_id": str,
        "resource_type": str,
        "op_type": str,
        "canonical_id": str,
        "description": str,
        "batch": str | None,
        "tier": int,
        "data": dict,
        "resolved_deps": dict,
    }
    """
    conn = store.conn

    # Find pending ops whose HARD dependencies are all completed or skipped.
    # SOFT deps (e.g., agent membership in hunt groups) do NOT block —
    # a failed SOFT dep means the feature proceeds without that agent.
    # Only REQUIRES and CONFIGURES edges block execution.
    ready_rows = conn.execute(
        """SELECT po.node_id, po.canonical_id, po.op_type, po.resource_type,
                  po.tier, po.batch, po.description, po.data_json
           FROM plan_operations po
           WHERE po.status = 'pending'
             AND NOT EXISTS (
                 SELECT 1 FROM plan_edges pe
                 JOIN plan_operations dep ON dep.node_id = pe.from_node
                 WHERE pe.to_node = po.node_id
                   AND pe.broken = 0
                   AND pe.dep_type != 'soft'
                   AND dep.status NOT IN ('completed', 'skipped')
             )
           ORDER BY po.tier, po.batch"""
    ).fetchall()

    if not ready_rows:
        return []

    # Group by (tier, batch) and return the lowest group
    first_tier = ready_rows[0]["tier"]
    first_batch = ready_rows[0]["batch"]
    batch_ops = [
        r for r in ready_rows
        if r["tier"] == first_tier and r["batch"] == first_batch
    ]

    result = []
    for row in batch_ops:
        node_id = row["node_id"]
        canonical_id = row["canonical_id"]

        # Prefer inline payload (bulk ops) over canonical object lookup.
        raw_payload = row["data_json"] if row["data_json"] else None
        if raw_payload:
            data = json.loads(raw_payload)
        else:
            obj_data = store.get_object(canonical_id)
            data = obj_data if obj_data else {}

        # Get resolved dependency IDs (explicit edges)
        deps = conn.execute(
            """SELECT dep.canonical_id, dep.webex_id
               FROM plan_edges pe
               JOIN plan_operations dep ON dep.node_id = pe.from_node
               WHERE pe.to_node = ? AND dep.status = 'completed'""",
            (node_id,),
        ).fetchall()
        resolved_deps = {
            r["canonical_id"]: r["webex_id"]
            for r in deps
            if r["webex_id"]
        }

        # Also inject all completed location ops into resolved_deps so that
        # handlers can resolve location_id even when no explicit edge exists.
        # This covers CUCM resources (AA, HG, pickup, trunk) that have no
        # location in their canonical form — the handler falls back to
        # _resolve_location() which looks up location_id from data in deps.
        loc_ops = conn.execute(
            """SELECT canonical_id, webex_id
               FROM plan_operations
               WHERE resource_type = 'location'
                 AND op_type = 'create'
                 AND status = 'completed'
                 AND webex_id IS NOT NULL""",
        ).fetchall()
        for loc in loc_ops:
            # Only inject if not already present from explicit edges
            if loc["canonical_id"] not in resolved_deps:
                resolved_deps[loc["canonical_id"]] = loc["webex_id"]

        result.append({
            "node_id": node_id,
            "resource_type": row["resource_type"],
            "op_type": row["op_type"],
            "canonical_id": canonical_id,
            "description": row["description"] or "",
            "batch": row["batch"],
            "tier": row["tier"],
            "data": data,
            "resolved_deps": resolved_deps,
        })

    return result


def update_op_status(
    store: MigrationStore,
    node_id: str,
    status: str,
    webex_id: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update operation status in the DB.

    Accepted ``status`` values mirror ``models.OpStatus``:
    ``pending`` / ``in_progress`` / ``completed`` / ``skipped`` / ``failed``.

    On completion: sets webex_id, completed_at, clears error_message. Also
    updates the canonical object's webex_id field in the objects table, and
    undoes any prior cascade-skip from this node (so dependents that were
    skipped because THIS op previously failed can now run on retry).
    On failure: sets error_message, increments attempts, cascade-skips
    dependents via hard edges.
    On skip: sets status to 'skipped', stores the reason in error_message,
    and cascade-skips dependents via hard edges (same as failure). Engines
    should pass ``error_message=<reason>`` so the execution report can
    explain why each op was skipped. The ``SkippedResult`` sentinel
    returned by handlers is the canonical producer of this path.
    On in_progress: just flips the status (no error/timestamp updates).
    """
    conn = store.conn

    if status == "completed":
        conn.execute(
            """UPDATE plan_operations
               SET status = ?, webex_id = ?, completed_at = ?,
                   error_message = NULL, attempts = attempts + 1
               WHERE node_id = ?""",
            (status, webex_id, _now(), node_id),
        )
        # Also update the canonical object's webex_id
        if webex_id:
            row = conn.execute(
                "SELECT canonical_id FROM plan_operations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if row:
                canonical_id = row["canonical_id"]
                conn.execute(
                    "UPDATE objects SET data = json_set(data, '$.webex_id', ?) WHERE canonical_id = ?",
                    (webex_id, canonical_id),
                )
        # Undo cascade-skip: if this op was previously failed and had cascade-
        # skipped its dependents, reset them back to pending so they can execute.
        _undo_cascade_skip(conn, node_id)
    elif status == "failed":
        conn.execute(
            """UPDATE plan_operations
               SET status = ?, error_message = ?, completed_at = ?,
                   attempts = attempts + 1
               WHERE node_id = ?""",
            (status, error_message, _now(), node_id),
        )
        # Cascade: skip all hard dependents since this op failed
        _cascade_skip(conn, node_id, reason_prefix="Dependency failed")
    elif status == "skipped":
        conn.execute(
            """UPDATE plan_operations
               SET status = ?, error_message = ?, attempts = attempts + 1
               WHERE node_id = ?""",
            (status, error_message, node_id),
        )
        # Cascade: mark all dependent ops as skipped
        _cascade_skip(conn, node_id, reason_prefix="Dependency skipped")
    elif status == "in_progress":
        conn.execute(
            "UPDATE plan_operations SET status = ? WHERE node_id = ?",
            (status, node_id),
        )
    else:
        raise ValueError(f"Invalid status: {status}")

    conn.commit()


def _cascade_skip(conn, node_id: str, reason_prefix: str = "Dependency skipped") -> None:
    """Recursively skip all ops that depend on the given node via hard edges.

    SOFT deps are excluded — skipping a user should NOT cascade-skip
    a hunt group that has the user as a SOFT agent dependency.
    """
    dependents = conn.execute(
        """SELECT pe.to_node FROM plan_edges pe
           JOIN plan_operations po ON po.node_id = pe.to_node
           WHERE pe.from_node = ?
             AND po.status IN ('pending', 'in_progress')
             AND pe.dep_type != 'soft'""",
        (node_id,),
    ).fetchall()

    for dep in dependents:
        dep_node = dep["to_node"]
        conn.execute(
            """UPDATE plan_operations
               SET status = 'skipped',
                   error_message = ?
               WHERE node_id = ? AND status IN ('pending', 'in_progress')""",
            (f"{reason_prefix}: {node_id}", dep_node),
        )
        # Recurse
        _cascade_skip(conn, dep_node, reason_prefix=reason_prefix)


def _undo_cascade_skip(conn, node_id: str) -> None:
    """Reset ops that were cascade-skipped due to this node's failure.

    When a failed op is retried and succeeds, its cascade-skipped dependents
    should be reset to pending so they can execute in the next batch.
    """
    skipped = conn.execute(
        """SELECT po.node_id FROM plan_operations po
           WHERE po.status = 'skipped'
             AND po.error_message LIKE ?""",
        (f"Dependency failed: {node_id}",),
    ).fetchall()

    for row in skipped:
        dep_node = row["node_id"]
        conn.execute(
            """UPDATE plan_operations
               SET status = 'pending', error_message = NULL
               WHERE node_id = ? AND status = 'skipped'""",
            (dep_node,),
        )
        # Recurse: this dep might have cascade-skipped its own dependents
        _undo_cascade_skip(conn, dep_node)


def get_completed_ops_for_rollback(
    store: MigrationStore,
    scope: str = "all",
    batch_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return completed CREATE ops in reverse dependency order for rollback.

    Each dict includes:
    - node_id, resource_type, op_type, webex_id, canonical_id
    - data: canonical object data (for name/description in rollback report)
    - location_webex_id: for feature deletes that need LOCATION_ID
    """
    conn = store.conn

    if scope == "batch" and batch_name:
        rows = conn.execute(
            """SELECT node_id, canonical_id, op_type, resource_type,
                      webex_id, tier, batch
               FROM plan_operations
               WHERE status = 'completed' AND op_type = 'create'
                 AND batch = ?
               ORDER BY tier DESC, node_id DESC""",
            (batch_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT node_id, canonical_id, op_type, resource_type,
                      webex_id, tier, batch
               FROM plan_operations
               WHERE status = 'completed' AND op_type = 'create'
               ORDER BY tier DESC, node_id DESC"""
        ).fetchall()

    result = []
    for row in rows:
        node_id = row["node_id"]
        canonical_id = row["canonical_id"]

        obj_data = store.get_object(canonical_id)
        data = obj_data if obj_data else {}

        # For features, resolve location webex_id from dependencies
        location_webex_id = None
        feature_types = {
            "hunt_group", "call_queue", "auto_attendant",
            "call_park", "pickup_group", "paging_group",
        }
        if row["resource_type"] in feature_types:
            loc_dep = conn.execute(
                """SELECT dep.webex_id FROM plan_edges pe
                   JOIN plan_operations dep ON dep.node_id = pe.from_node
                   WHERE pe.to_node = ?
                     AND dep.resource_type = 'location'
                     AND dep.status = 'completed'""",
                (node_id,),
            ).fetchone()
            if loc_dep:
                location_webex_id = loc_dep["webex_id"]

        result.append({
            "node_id": node_id,
            "resource_type": row["resource_type"],
            "op_type": row["op_type"],
            "webex_id": row["webex_id"],
            "canonical_id": canonical_id,
            "data": data,
            "location_webex_id": location_webex_id,
        })

    return result


def dry_run_all_batches(store: MigrationStore) -> dict[str, Any]:
    """Walk all batches in execution order without changing state.

    For each batch:
    1. Find all ready ops (same logic as get_next_batch)
    2. Simulate completion (mark as 'completed' in a SAVEPOINT)
    3. Move to next batch
    4. ROLLBACK the savepoint — no state changes persist

    Returns the full execution sequence as a list of batch dicts:
    [{
        "batch": str,
        "tier": int,
        "operations": [
            {"node_id": str, "resource_type": str, "op_type": str,
             "description": str, "resolved_deps": dict}
        ]
    }]
    """
    conn = store.conn
    batches: list[dict[str, Any]] = []
    total_api_calls = 0

    conn.execute("SAVEPOINT dry_run")
    try:
        while True:
            batch_ops = get_next_batch(store)
            if not batch_ops:
                break

            batch_name = batch_ops[0]["batch"] or "org-wide"
            tier = batch_ops[0]["tier"]

            operations = []
            for op in batch_ops:
                api_calls = conn.execute(
                    "SELECT api_calls FROM plan_operations WHERE node_id = ?",
                    (op["node_id"],),
                ).fetchone()
                op_api_calls = api_calls["api_calls"] if api_calls else 1
                total_api_calls += op_api_calls

                operations.append({
                    "node_id": op["node_id"],
                    "resource_type": op["resource_type"],
                    "op_type": op["op_type"],
                    "description": op["description"],
                    "resolved_deps": op["resolved_deps"],
                })

                # Simulate completion so next iteration can resolve deps
                conn.execute(
                    """UPDATE plan_operations
                       SET status = 'completed', webex_id = ?
                       WHERE node_id = ?""",
                    (f"dry-run-{op['node_id']}", op["node_id"]),
                )

            batches.append({
                "batch": batch_name,
                "tier": tier,
                "operations": operations,
            })
    finally:
        conn.execute("ROLLBACK TO dry_run")
        conn.execute("RELEASE dry_run")

    # Attach summary
    total_ops = sum(len(b["operations"]) for b in batches)
    return {
        "batches": batches,
        "total_operations": total_ops,
        "total_batches": len(batches),
        "total_api_calls": total_api_calls,
    }


def get_execution_progress(store: MigrationStore) -> dict[str, Any]:
    """Return execution progress summary.

    Returns: {
        "total": int,
        "pending": int,
        "in_progress": int,
        "completed": int,
        "failed": int,
        "skipped": int,
        "by_resource_type": {"location": {"completed": N, "pending": M, ...}, ...},
        "last_error": {"node_id": str, "error": str} | None,
        "last_completed": {"node_id": str, "description": str} | None,
    }
    """
    conn = store.conn

    # Overall counts
    status_rows = conn.execute(
        """SELECT status, COUNT(*) as cnt
           FROM plan_operations GROUP BY status"""
    ).fetchall()
    counts = {r["status"]: r["cnt"] for r in status_rows}

    total = sum(counts.values())
    progress = {
        "total": total,
        "pending": counts.get("pending", 0),
        "in_progress": counts.get("in_progress", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "skipped": counts.get("skipped", 0),
    }

    # Per-resource-type breakdown
    rt_rows = conn.execute(
        """SELECT resource_type, status, COUNT(*) as cnt
           FROM plan_operations GROUP BY resource_type, status"""
    ).fetchall()
    by_rt: dict[str, dict[str, int]] = {}
    for r in rt_rows:
        rt = r["resource_type"]
        if rt not in by_rt:
            by_rt[rt] = {}
        by_rt[rt][r["status"]] = r["cnt"]
    progress["by_resource_type"] = by_rt

    # Last error
    err_row = conn.execute(
        """SELECT node_id, error_message
           FROM plan_operations
           WHERE status = 'failed' AND error_message IS NOT NULL
           ORDER BY completed_at DESC, node_id DESC
           LIMIT 1"""
    ).fetchone()
    progress["last_error"] = (
        {"node_id": err_row["node_id"], "error": err_row["error_message"]}
        if err_row
        else None
    )

    # Last completed
    comp_row = conn.execute(
        """SELECT node_id, description
           FROM plan_operations
           WHERE status = 'completed'
           ORDER BY completed_at DESC
           LIMIT 1"""
    ).fetchone()
    progress["last_completed"] = (
        {"node_id": comp_row["node_id"], "description": comp_row["description"]}
        if comp_row
        else None
    )

    return progress
