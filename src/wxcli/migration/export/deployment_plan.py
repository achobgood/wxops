"""Generate a summary-only deployment plan in markdown format.

Reads the SQLite plan (operations, edges, batches) and produces a markdown
summary for admin review. No CLI commands or placeholders are included —
execution is handled by skill delegation at runtime.

Sections:
1. Objective
2. Prerequisites
3. Resource Summary
4. Decisions Made
5. Batch Execution Order
6. Estimated Impact
7. Rollback Strategy
8. Approval

(Phase 09 → Phase 12b refactored to summary-only)
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.store import MigrationStore

logger = logging.getLogger(__name__)


# Webex resource types to include in the summary.
# Excludes CUCM-only source types (partition, css, device_pool, etc.)
WEBEX_RESOURCE_TYPES = {
    "location", "user", "workspace", "device",
    "hunt_group", "call_queue", "auto_attendant",
    "call_park", "pickup_group", "paging_group",
    "operating_mode", "trunk", "route_group",
    "dial_plan", "translation_pattern", "schedule",
    "virtual_line", "shared_line", "calling_permission",
}

# CUCM-only types to exclude from the resource summary
CUCM_ONLY_TYPES = {
    "partition", "css", "device_pool", "cucm_location",
    "line", "voicemail_profile", "line_group", "hunt_list",
    "cti_route_point", "gateway", "sip_trunk",
}

TYPE_LABELS = {
    "location": "Location",
    "user": "Person",
    "device": "Device",
    "workspace": "Workspace",
    "trunk": "Trunk",
    "route_group": "Route Group",
    "dial_plan": "Dial Plan",
    "translation_pattern": "Translation Pattern",
    "hunt_group": "Hunt Group",
    "call_queue": "Call Queue",
    "auto_attendant": "Auto Attendant",
    "call_park": "Call Park",
    "pickup_group": "Pickup Group",
    "paging_group": "Paging Group",
    "operating_mode": "Operating Mode",
    "virtual_line": "Virtual Line",
    "shared_line": "Shared Line",
    "calling_permission": "Calling Permission",
    "schedule": "Location Schedule",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_by_type(store: MigrationStore) -> dict[str, int]:
    """Count objects by type from the store."""
    rows = store.conn.execute(
        "SELECT object_type, COUNT(*) as cnt FROM objects GROUP BY object_type ORDER BY cnt DESC"
    ).fetchall()
    return {r["object_type"]: r["cnt"] for r in rows}


def _pending_decision_count(store: MigrationStore) -> int:
    """Count unresolved, non-stale decisions."""
    all_decisions = store.get_all_decisions()
    return sum(
        1 for d in all_decisions
        if d.get("chosen_option") is None
    )


def _get_resolved_decisions(store: MigrationStore) -> list[dict[str, Any]]:
    """Get all resolved, non-stale decisions."""
    all_decisions = store.get_all_decisions()
    return [
        d for d in all_decisions
        if d.get("chosen_option") is not None
        and d.get("chosen_option") != "__stale__"
    ]


def _get_plan_ops(store: MigrationStore) -> list[dict[str, Any]]:
    """Get all plan operations from the DB."""
    rows = store.conn.execute(
        """SELECT node_id, canonical_id, op_type, resource_type,
                  tier, batch, api_calls, description, status
           FROM plan_operations
           ORDER BY tier, batch, node_id"""
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------

def _section_objective(
    type_counts: dict[str, int],
    project_id: str,
) -> list[str]:
    """Section 1: Objective."""
    lines = ["## 1. Objective", ""]

    parts = []
    user_count = type_counts.get("user", 0)
    if user_count:
        parts.append(f"{user_count} users")
    device_count = type_counts.get("device", 0)
    if device_count:
        parts.append(f"{device_count} devices")
    workspace_count = type_counts.get("workspace", 0)
    if workspace_count:
        parts.append(f"{workspace_count} workspaces")

    feature_types = ["hunt_group", "call_queue", "auto_attendant", "call_park",
                     "pickup_group", "paging_group"]
    feature_count = sum(type_counts.get(ft, 0) for ft in feature_types)
    if feature_count:
        parts.append(f"{feature_count} call features")

    infra_parts = []
    for itype in ("location", "trunk", "dial_plan"):
        cnt = type_counts.get(itype, 0)
        if cnt:
            label = TYPE_LABELS.get(itype, itype)
            infra_parts.append(f"{cnt} {label.lower()}s")

    obj_summary = ", ".join(parts) if parts else "migration objects"
    lines.append(
        f"Migrate {obj_summary} from CUCM to Webex Calling (project: {project_id})."
    )
    if infra_parts:
        lines.append(f"{', '.join(infra_parts)} as routing infrastructure.")
    lines.append("")
    return lines


def _section_prerequisites(
    type_counts: dict[str, int],
    pending_decisions: int,
) -> list[str]:
    """Section 2: Prerequisites."""
    lines = ["## 2. Prerequisites", ""]
    lines.append("| # | Prerequisite | Verification Method | Status |")
    lines.append("|---|---|---|---|")
    lines.append("| 1 | Webex org accessible | `wxcli whoami` | [ ] |")

    user_count = type_counts.get("user", 0)
    if user_count:
        lines.append(
            f"| 2 | Calling licenses available ({user_count} Professional) "
            f"| `wxcli licenses list` | [ ] |"
        )

    location_count = type_counts.get("location", 0)
    if location_count:
        lines.append(
            f"| 3 | Number inventory for {location_count} location(s) "
            f"| `wxcli numbers list --location-id ...` | [ ] |"
        )

    lines.append(
        f"| 4 | All decisions resolved ({pending_decisions} pending) "
        f"| `wxcli cucm decisions --status pending` | "
        f"{'[x]' if pending_decisions == 0 else '[ ]'} |"
    )
    lines.append("")
    if pending_decisions > 0:
        lines.append(
            f"**Blockers found:** {pending_decisions} pending decision(s) "
            f"must be resolved before execution."
        )
    else:
        lines.append("**Blockers found:** None")
    lines.append("")
    return lines


def _section_resource_summary(
    type_counts: dict[str, int],
) -> list[str]:
    """Section 3: Resource Summary — Webex resource types only."""
    lines = ["## 3. Resource Summary", ""]
    lines.append("| Resource Type | Count | Action |")
    lines.append("|--------------|-------|--------|")

    for obj_type, count in type_counts.items():
        if obj_type not in WEBEX_RESOURCE_TYPES:
            continue
        label = TYPE_LABELS.get(obj_type, obj_type)
        lines.append(f"| {label} | {count} | Create |")

    lines.append("")
    return lines


def _section_decisions(
    resolved: list[dict[str, Any]],
) -> list[str]:
    """Section 4: Decisions Made."""
    lines = ["## 4. Decisions Made", ""]

    if not resolved:
        lines.append("No decisions were required for this migration.")
        lines.append("")
        return lines

    lines.append("| ID | Type | Summary | Chosen Option |")
    lines.append("|---|------|---------|---------------|")

    for d in resolved:
        did = d.get("decision_id", "?")
        dtype = d.get("type", "?")
        summary = d.get("summary", "").replace("|", "\\|")
        chosen = d.get("chosen_option", "?")
        # Try to find the label for the chosen option
        options = d.get("options", [])
        chosen_label = chosen
        for opt in options:
            if isinstance(opt, dict) and opt.get("id") == chosen:
                chosen_label = opt.get("label", chosen)
                break
        lines.append(f"| {did} | {dtype} | {summary} | {chosen_label} |")

    lines.append("")
    return lines


def _section_batch_order(
    ops: list[dict[str, Any]],
) -> list[str]:
    """Section 5: Batch Execution Order."""
    lines = ["## 5. Batch Execution Order", ""]

    # Group by (tier, batch) and count
    groups: dict[tuple[int, str], int] = defaultdict(int)
    tier_types: dict[tuple[int, str], set[str]] = defaultdict(set)
    for op in ops:
        key = (op["tier"], op.get("batch") or "org-wide")
        groups[key] += 1
        tier_types[key].add(op["resource_type"])

    if not groups:
        lines.append("No operations planned.")
        lines.append("")
        return lines

    lines.append("| Tier | Batch | Operations | Resource Types |")
    lines.append("|------|-------|------------|----------------|")

    for (tier, batch) in sorted(groups.keys()):
        count = groups[(tier, batch)]
        rtypes = ", ".join(
            TYPE_LABELS.get(rt, rt)
            for rt in sorted(tier_types[(tier, batch)])
        )
        lines.append(f"| {tier} | {batch} | {count} | {rtypes} |")

    lines.append("")
    return lines


def _section_impact(
    type_counts: dict[str, int],
    total_ops: int,
    total_api_calls: int,
) -> list[str]:
    """Section 6: Estimated Impact."""
    lines = ["## 6. Estimated Impact", ""]
    lines.append("| What Changes | Details |")
    lines.append("|-------------|---------|")

    user_count = type_counts.get("user", 0)
    if user_count:
        lines.append(f"| Users added | {user_count} new Webex Calling users |")

    workspace_count = type_counts.get("workspace", 0)
    if workspace_count:
        lines.append(f"| Workspaces added | {workspace_count} new workspaces |")

    device_count = type_counts.get("device", 0)
    if device_count:
        lines.append(f"| Devices provisioned | {device_count} devices |")

    license_count = user_count + workspace_count
    if license_count:
        parts = []
        if user_count:
            parts.append(f"{user_count} user")
        if workspace_count:
            parts.append(f"{workspace_count} workspace")
        lines.append(
            f"| Licenses consumed | {license_count} Webex Calling Professional "
            f"({' + '.join(parts)}) |"
        )

    location_count = type_counts.get("location", 0)
    if location_count:
        lines.append(f"| Locations created | {location_count} new locations |")

    lines.append(f"| Total operations | {total_ops} |")

    est_minutes = math.ceil(total_api_calls / 100) if total_api_calls else 0
    lines.append(
        f"| Estimated API calls | {total_api_calls} calls (~{est_minutes} min at 100 req/min) |"
    )

    lines.append("")
    return lines


def _section_activation_codes(
    store: MigrationStore,
) -> list[str]:
    """Section: Activation Codes (only shown when convertible devices are present).

    Lists every device:create_activation_code op with device, owner, model,
    code, and status. Pre-execution the code column shows '(pending)';
    post-execution it shows the 16-digit activation code formatted in groups
    of 4 for readability (e.g., 5414-0112-5617-3816).
    """
    rows = store.conn.execute(
        """SELECT canonical_id, webex_id, status, batch
           FROM plan_operations
           WHERE op_type = 'create_activation_code'
           ORDER BY canonical_id"""
    ).fetchall()

    if not rows:
        return []

    lines = [
        "## Activation Codes",
        "",
        "The following firmware-convertible phones require an activation code",
        "after their firmware is converted to MPP. Distribute the codes below",
        "to on-site IT staff before the conversion window. Codes are generated",
        "by `POST /v1/devices/activationCode` during execution.",
        "",
        "| Device | Owner | Model | Code | Status |",
        "|--------|-------|-------|------|--------|",
    ]

    for row in rows:
        device_data = store.get_object(row["canonical_id"]) or {}
        device_name = device_data.get("display_name") or row["canonical_id"].split(":", 1)[-1]
        model = device_data.get("model", "")

        owner_cid = device_data.get("owner_canonical_id")
        owner_label = "—"
        if owner_cid:
            owner_data = store.get_object(owner_cid) or {}
            owner_label = (
                owner_data.get("display_name")
                or owner_data.get("name")
                or owner_cid
            )

        raw_code = row["webex_id"] or ""
        if raw_code and len(raw_code) == 16 and raw_code.isdigit():
            code_display = "-".join(
                raw_code[i:i + 4] for i in range(0, 16, 4)
            )
        elif raw_code:
            code_display = raw_code
        else:
            code_display = "(pending)"

        status_label = row["status"] or "pending"
        lines.append(
            f"| {device_name} | {owner_label} | {model} | {code_display} | {status_label} |"
        )

    lines.append("")
    return lines


def _section_rollback_strategy() -> list[str]:
    """Section 7: Rollback Strategy."""
    return [
        "## 7. Rollback Strategy",
        "",
        "Execution is tracked per-operation in the migration database. "
        "Rollback deletes created resources in reverse dependency order. "
        "Use `wxcli cucm rollback` to initiate.",
        "",
    ]


def _section_approval() -> list[str]:
    """Section 8: Approval."""
    return [
        "## 8. Approval",
        "",
        "Review the plan above. The migration skill will not execute until you confirm.",
        "",
        "- [ ] **I approve this deployment plan.** Proceed with execution.",
        "- [ ] **I need changes.** [Describe what to modify]",
        "- [ ] **Cancel.** Do not execute.",
        "",
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_plan_summary(
    store: MigrationStore,
    project_id: str,
) -> str:
    """Generate a summary-only deployment plan markdown document.

    This is the Phase 12b replacement for generate_deployment_plan().
    No CLI commands, no placeholders, no command_builder dependency.
    The cucm-migrate skill uses DB-driven execution with domain skill delegation.

    Args:
        store: MigrationStore with canonical objects, decisions, and plan ops.
        project_id: Migration project identifier.

    Returns:
        Complete markdown string with 8 sections for admin review.
    """
    type_counts = _count_by_type(store)
    pending_decisions = _pending_decision_count(store)
    resolved_decisions = _get_resolved_decisions(store)
    ops = _get_plan_ops(store)

    total_ops = len(ops)
    total_api_calls = sum(op.get("api_calls", 1) or 1 for op in ops)

    # Assemble the document
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# Deployment Plan: CUCM Migration — {project_id}",
        "",
        f"Created: {now}",
        "Agent: wxc-calling-builder",
        "",
        "---",
        "",
    ]

    lines.extend(_section_objective(type_counts, project_id))
    lines.extend(_section_prerequisites(type_counts, pending_decisions))
    lines.extend(_section_resource_summary(type_counts))
    lines.extend(_section_decisions(resolved_decisions))
    lines.extend(_section_batch_order(ops))
    lines.extend(_section_activation_codes(store))
    lines.extend(_section_impact(type_counts, total_ops, total_api_calls))
    lines.extend(_section_rollback_strategy())
    lines.extend(_section_approval())

    return "\n".join(lines)
