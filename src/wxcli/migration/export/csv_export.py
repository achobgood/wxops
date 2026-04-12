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


def has_activation_codes(store: MigrationStore) -> bool:
    """Check if the plan contains any create_activation_code operations."""
    row = store.conn.execute(
        "SELECT COUNT(*) AS cnt FROM plan_operations "
        "WHERE op_type = 'create_activation_code'"
    ).fetchone()
    return bool(row and row["cnt"] > 0)


def generate_csv_activation_codes(store: MigrationStore) -> str:
    """Generate CSV content listing activation codes for convertible devices.

    One row per device:create_activation_code operation. Joins back to the
    canonical device (for display_name, model, location) and the owner
    (user or workspace, for name and email). The activation code itself
    comes from plan_operations.webex_id, populated by the engine after the
    POST /devices/activationCode call succeeds. Pre-execution the code is
    blank and status is 'pending'; post-execution the code is the 16-digit
    string returned by the API.

    Columns: device_name, owner_name, owner_email, model, activation_code,
    status, location.
    """
    rows = store.conn.execute(
        """SELECT po.canonical_id, po.webex_id, po.status, po.batch
           FROM plan_operations po
           WHERE po.op_type = 'create_activation_code'
           ORDER BY po.canonical_id"""
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "device_name", "owner_name", "owner_email",
        "model", "activation_code", "status", "location",
    ])

    for row in rows:
        device_data = store.get_object(row["canonical_id"]) or {}
        device_name = (
            device_data.get("display_name")
            or row["canonical_id"].split(":", 1)[-1]
        )
        model = device_data.get("model", "")

        owner_cid = device_data.get("owner_canonical_id")
        owner_name = ""
        owner_email = ""
        if owner_cid:
            owner_data = store.get_object(owner_cid) or {}
            owner_name = (
                owner_data.get("display_name") or owner_data.get("name") or ""
            )
            emails = owner_data.get("emails") or []
            if emails:
                owner_email = emails[0]

        writer.writerow([
            device_name,
            owner_name,
            owner_email,
            model,
            row["webex_id"] or "",
            row["status"] or "",
            row["batch"] or "",
        ])

    return output.getvalue()
