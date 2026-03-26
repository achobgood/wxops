"""CSV export of migration decisions for stakeholder review.

Exports all non-stale decisions with type, severity, summary, options,
chosen_option, and resolved_by columns.

(Phase 09 — csv_export.py)
"""

from __future__ import annotations

import csv
import io
from typing import Any

from wxcli.migration.store import MigrationStore


def generate_csv_decisions(
    store: MigrationStore,
) -> str:
    """Generate CSV content for all non-stale decisions.

    Returns:
        CSV string with header row and one row per decision.
    """
    all_decisions = store.get_all_decisions()
    non_stale = [d for d in all_decisions if d.get("chosen_option") != "__stale__"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "decision_id", "type", "severity", "summary",
        "options", "chosen_option", "resolved_by",
    ])
    for d in non_stale:
        options_str = "; ".join(
            opt.get("id", str(opt)) if isinstance(opt, dict) else str(opt)
            for opt in d.get("options", [])
        )
        writer.writerow([
            d.get("decision_id", ""),
            d.get("type", ""),
            d.get("severity", ""),
            d.get("summary", ""),
            options_str,
            d.get("chosen_option", ""),
            d.get("resolved_by", ""),
        ])

    return output.getvalue()


def has_decisions(store: MigrationStore) -> bool:
    """Check if there are any non-stale decisions to export."""
    all_decisions = store.get_all_decisions()
    return any(d.get("chosen_option") != "__stale__" for d in all_decisions)
