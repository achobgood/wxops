"""Full JSON export of migration state.

Exports all objects (by type), decisions, cross-references, and plan operations
as a single JSON document for external tooling or archive.

(Phase 09 — json_export.py)
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.store import MigrationStore


def generate_json_export(
    store: MigrationStore,
    project_id: str,
) -> dict[str, Any]:
    """Build the full JSON export dict.

    Args:
        store: MigrationStore with all migration data.
        project_id: Migration project identifier.

    Returns:
        Dict ready for json.dump().
    """
    data: dict[str, Any] = {
        "project": project_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    # Objects by type
    rows = store.conn.execute("SELECT object_type, data FROM objects").fetchall()
    objects_by_type: dict[str, list] = defaultdict(list)
    for r in rows:
        objects_by_type[r["object_type"]].append(json.loads(r["data"]))
    data["objects"] = dict(objects_by_type)

    # Decisions (exclude stale)
    all_decisions = store.get_all_decisions()
    data["decisions"] = [d for d in all_decisions if d.get("chosen_option") != "__stale__"]

    # Cross-refs
    xrefs = store.conn.execute("SELECT * FROM cross_refs").fetchall()
    data["cross_refs"] = [dict(r) for r in xrefs]

    # Plan operations
    ops = store.conn.execute("SELECT * FROM plan_operations").fetchall()
    data["plan_operations"] = [dict(r) for r in ops]

    # Plan edges
    edges = store.conn.execute("SELECT * FROM plan_edges").fetchall()
    data["plan_edges"] = [dict(r) for r in edges]

    return data
