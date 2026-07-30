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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.decision_state import is_resolved
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
    # Types the plan acts on that Section 3 used to omit — 615 entities on
    # director-demo-2026-04-15, about a third of the plan.
    "ecbn_config": "Emergency Callback Number",
    "device_layout": "Device Line Key Layout",
    "call_forwarding": "Call Forwarding",
    "line_key_template": "Line Key Template",
    "route_list": "Route List",
    "bulk_line_key_template": "Line Key Template (bulk job)",
    "bulk_device_settings": "Device Settings (bulk job)",
    "bulk_rebuild_phones": "Phone Rebuild (bulk job)",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_by_type(store: MigrationStore) -> dict[str, int]:
    """Count objects by type from the store — the CUCM-side inventory.

    This is what was discovered, NOT what will be built. Use
    :func:`_count_planned_by_type` for anything the reader will act on.
    """
    rows = store.conn.execute(
        "SELECT object_type, COUNT(*) as cnt FROM objects GROUP BY object_type ORDER BY cnt DESC"
    ).fetchall()
    return {r["object_type"]: r["cnt"] for r in rows}


def _count_planned_by_type(store: MigrationStore) -> dict[str, int]:
    """Count distinct resources per type that this plan actually acts on.

    Read from ``plan_operations``, not ``objects``. The inventory is what CUCM
    had; the plan is what will be built, and on director-demo-2026-04-15 those
    differ by 388 devices, 23 users, 17 translation patterns and 12 call parks
    (finding F03). This document is what ``cucm-migrate`` presents at the
    "Ready to execute? (yes/no)" gate, so every number in it has to describe
    the plan.

    ``COUNT(DISTINCT canonical_id)`` rather than a create-only count:
    ``shared_line`` and ``call_forwarding`` are never created, only configured
    (275 and 51 operations on the real projects), so counting creates would
    report 0 for work that definitely happens.
    """
    rows = store.conn.execute(
        """SELECT resource_type, COUNT(DISTINCT canonical_id) AS cnt
           FROM plan_operations
           GROUP BY resource_type ORDER BY cnt DESC"""
    ).fetchall()
    return {r["resource_type"]: r["cnt"] for r in rows}


def _planned_actions_by_type(store: MigrationStore) -> dict[str, list[str]]:
    """The distinct op_types the plan uses, per resource type.

    Derived from the data rather than a hand-written label map, so a new op_type
    cannot silently render as the wrong action (the F17 failure mode).
    """
    rows = store.conn.execute(
        """SELECT resource_type, op_type FROM plan_operations
           GROUP BY resource_type, op_type
           ORDER BY resource_type, op_type"""
    ).fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["resource_type"], []).append(r["op_type"])
    return out


#: Object shapes that legitimately produce no plan operation, keyed by
#: object_type — ``(data field, values that need no operation)``.
#:
#: Measured on director-demo-2026-04-15: of the 328 devices with no operation,
#: **314 are `webex_app`** (softphones moving to the Webex App, so there is no
#: device to provision) and **13 are `infrastructure`** (CTI ports, route points
#: — no Webex device equivalent). Only 4 had genuinely stopped advancing.
#: Reporting all 328 as "excluded because a decision resolved to skip, the object
#: is incompatible, or its decision was invalidated" would put a false claim in a
#: customer-facing document — the same class of defect as F03 itself.
NO_OP_EXPECTED: dict[str, tuple[str, set[str]]] = {
    "device": ("compatibility_tier", {"webex_app", "infrastructure"}),
}

#: Reasons an object produced no operation that ARE knowable from its own data,
#: keyed by object_type — ``(field that must be empty, operator-facing reason)``.
#:
#: The planner computes these too and prints them in the `plan` stage output
#: (``missing_mac: 60 skipped``), but its skip report is in-memory and not
#: persisted, so ``export`` cannot read it. Where the object itself carries the
#: evidence, say so; do not label it "no known reason" when the reason is sitting
#: in the row. Verified on director-demo: all 60 unplanned incompatible-tier
#: devices have ``mac: null`` and model "CTI Port".
NO_OP_KNOWN_GAP: dict[str, tuple[str, str]] = {
    "device": ("mac", "no MAC address was extracted from CUCM"),
}


@dataclass(frozen=True)
class UnplannedObjects:
    """Objects with no plan operation, split by *why* — counts keyed by type.

    Only ``stranded`` and ``unexplained`` warrant an operator's attention.
    ``no_op_expected`` is stated so the arithmetic reconciles, never as a warning.
    """

    stranded: dict[str, int]
    no_op_expected: dict[str, int]
    unexplained: dict[str, int]
    #: ``{object_type: {reason: count}}`` — gaps the object's own data explains.
    known_gaps: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def needs_attention(self) -> bool:
        return bool(self.stranded or self.unexplained or self.known_gaps)


def _classify_unplanned(store: MigrationStore) -> UnplannedObjects:
    """Split the objects this plan does not act on by the reason it does not.

    The words "skip", "excluded", "incompatible" and "stale" appeared nowhere in
    the 811-line document (finding F03), so a reader had no way to tell that 23
    of 300 users were absent from it. But a flat "excluded" count is its own
    misstatement — see :data:`NO_OP_EXPECTED`. Three buckets:

    * ``stranded`` — never reached ``status='analyzed'``, so ``expand_to_operations``
      never saw them. This is the 23-user population from finding F08.
    * ``no_op_expected`` — analyzed, and the object's own shape says no operation
      is required.
    * ``unexplained`` — analyzed, no operation, and no known reason. The bucket
      that should be empty and is worth chasing when it is not.

    Scoped to :data:`WEBEX_RESOURCE_TYPES`, and unlike the Section 3 table
    above it this filter is load-bearing: it reads the ``objects`` inventory,
    which is full of CUCM-only types (``partition``, ``css``, ``line``,
    ``phone``, ``button_template``) that were never going to become Webex
    resources. Reporting those as "absent from this plan" is the 2005-vs-67
    over-report from finding F08. The Section 3 table reads
    ``plan_operations``, where nothing needs excluding — the two are no longer
    scoped alike and should not be made to match.
    """
    rows = store.conn.execute(
        """SELECT object_type, status, data FROM objects
           WHERE canonical_id NOT IN (SELECT canonical_id FROM plan_operations)"""
    ).fetchall()

    stranded: dict[str, int] = {}
    expected: dict[str, int] = {}
    unexplained: dict[str, int] = {}

    known_gaps: dict[str, dict[str, int]] = {}

    for r in rows:
        obj_type = r["object_type"]
        if obj_type not in WEBEX_RESOURCE_TYPES:
            continue
        try:
            data = json.loads(r["data"]) or {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        # By-design is checked BEFORE status, deliberately. An adversarial
        # verification run caught the other order misfiling 4 devices as
        # "stopped advancing — investigate" when they were `infrastructure` and
        # `webex_app`, i.e. identical in kind to the 324 the same document said
        # need no action. A type that produces no operation by design produces
        # none at any status, so the shape of the object outranks how far it got.
        rule = NO_OP_EXPECTED.get(obj_type)
        if rule is not None:
            tier_field, values = rule
            if data.get(tier_field) in values:
                expected[obj_type] = expected.get(obj_type, 0) + 1
                continue

        if r["status"] != "analyzed":
            stranded[obj_type] = stranded.get(obj_type, 0) + 1
            continue

        gap = NO_OP_KNOWN_GAP.get(obj_type)
        if gap is not None:
            gap_field, reason = gap
            if not data.get(gap_field):
                bucket = known_gaps.setdefault(obj_type, {})
                bucket[reason] = bucket.get(reason, 0) + 1
                continue

        unexplained[obj_type] = unexplained.get(obj_type, 0) + 1

    return UnplannedObjects(
        stranded=stranded,
        no_op_expected=expected,
        unexplained=unexplained,
        known_gaps=known_gaps,
    )


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
        if is_resolved(d)
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
    actions: dict[str, list[str]] | None = None,
    unplanned: UnplannedObjects | None = None,
) -> list[str]:
    """Section 3: Resource Summary — Webex resource types only.

    ``type_counts`` must be plan-derived (see :func:`_count_planned_by_type`).
    ``actions`` supplies the real op_types per type; without it every row falls
    back to "Create", which is what made the old table claim creates for
    translation patterns and call parks the plan never touches.
    ``unplanned`` adds the "Not in this plan" disclosure — see
    :func:`_classify_unplanned` for why it is three buckets and not one.
    """
    lines = ["## 3. Resource Summary", ""]
    lines.append(
        "Distinct resources this plan acts on. One resource can carry several "
        "operations, so these counts are lower than the operation total in "
        "Section 6."
    )
    lines.append("")
    lines.append("| Resource Type | Count | Action |")
    lines.append("|--------------|-------|--------|")

    # Deliberately NOT filtered to WEBEX_RESOURCE_TYPES. That allowlist was
    # correct when this table was built from the `objects` inventory, which
    # holds CUCM-only types (partition, css, line) that were never going to
    # become Webex resources. F03 repointed the table at `plan_operations`,
    # where every row is by definition something this plan builds — and the
    # filter was left behind, silently subtracting real work. It hid 8 types /
    # 615 entities on director-demo-2026-04-15: 304 emergency callback numbers,
    # 215 device layouts, 51 call forwarding configs and five smaller types,
    # roughly a third of the plan. They were counted in the operation totals
    # and listed in Section 5's batch order, so the document was not wrong —
    # but the one table an approver reads as "what this builds" was.
    #
    # An allowlist here would also have to be extended by hand every time a new
    # op type lands, and would fail silently by omission when it wasn't.
    for obj_type, count in type_counts.items():
        label = TYPE_LABELS.get(obj_type, obj_type)
        op_types = (actions or {}).get(obj_type)
        if op_types:
            action = ", ".join(
                op.replace("_", " ").capitalize() for op in op_types
            )
        else:
            action = "Create"
        lines.append(f"| {label} | {count} | {action} |")

    lines.append("")

    if unplanned is not None and unplanned.needs_attention:
        lines.append("### Not in this plan")
        lines.append("")
        lines.append(
            "Discovered in CUCM but absent from the operations above. Reconcile these "
            "before approving:"
        )
        lines.append("")
        lines.append("| Resource Type | Count | Why |")
        lines.append("|--------------|-------|-----|")
        for obj_type, n in sorted(
            unplanned.stranded.items(), key=lambda kv: kv[1], reverse=True
        ):
            label = TYPE_LABELS.get(obj_type, obj_type)
            lines.append(
                f"| {label} | {n} | Stopped advancing before the planner ran |"
            )
        for obj_type, reasons in sorted(
            unplanned.known_gaps.items(),
            key=lambda kv: sum(kv[1].values()),
            reverse=True,
        ):
            label = TYPE_LABELS.get(obj_type, obj_type)
            for reason, n in sorted(
                reasons.items(), key=lambda kv: kv[1], reverse=True
            ):
                lines.append(f"| {label} | {n} | {reason[0].upper()}{reason[1:]} |")
        for obj_type, n in sorted(
            unplanned.unexplained.items(), key=lambda kv: kv[1], reverse=True
        ):
            label = TYPE_LABELS.get(obj_type, obj_type)
            # Deliberately not "no known reason". The planner may well know it —
            # it prints per-type skip reasons — but that report is in-memory and
            # this stage cannot read it, so claiming no reason exists would be
            # asserting something unverified.
            lines.append(
                f"| {label} | {n} | Analyzed, but produced no operation "
                f"(see the `plan` stage output for the per-type reason) |"
            )
        lines.append("")
        lines.append(
            "The `wxcli cucm plan` output breaks these down by reason. For the "
            "decision-related ones, `wxcli cucm decisions --status stale` and "
            "`--status pending` show what is unresolved."
        )
        lines.append("")

    if unplanned is not None and unplanned.no_op_expected:
        # Deliberately not a warning and deliberately not in the table above:
        # these need no operation by design, and calling them "excluded" was a
        # false claim in a customer-facing document.
        total = sum(unplanned.no_op_expected.values())
        detail = ", ".join(
            f"{n} {TYPE_LABELS.get(t, t).lower()}"
            for t, n in sorted(
                unplanned.no_op_expected.items(), key=lambda kv: kv[1], reverse=True
            )
        )
        lines.append(
            f"A further {total} discovered objects ({detail}) require no operation: "
            "softphone users move to the Webex App, and infrastructure endpoints such "
            "as CTI ports have no Webex device equivalent. No action needed."
        )
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
    # Every count a reader acts on is plan-derived. `_count_by_type` (the CUCM
    # inventory) now feeds only the excluded-population diff, where the gap
    # between what was discovered and what will be built is the whole point.
    planned_counts = _count_planned_by_type(store)
    planned_actions = _planned_actions_by_type(store)
    unplanned = _classify_unplanned(store)
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

    lines.extend(_section_objective(planned_counts, project_id))
    lines.extend(_section_prerequisites(planned_counts, pending_decisions))
    lines.extend(_section_resource_summary(
        planned_counts, planned_actions, unplanned
    ))
    lines.extend(_section_decisions(resolved_decisions))
    lines.extend(_section_batch_order(ops))
    lines.extend(_section_activation_codes(store))
    lines.extend(_section_impact(planned_counts, total_ops, total_api_calls))
    lines.extend(_section_rollback_strategy())
    lines.extend(_section_approval())

    return "\n".join(lines)
