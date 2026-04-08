"""Decision model helpers for querying, summarizing, and formatting decisions.

Complements the Mapper._fingerprint() method with higher-level helpers
for CLI reporting and programmatic queries.

(from 03b-transform-mappers.md, shared patterns)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from wxcli.migration.store import MigrationStore


def summarize_decisions(decisions: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Group decisions by type and severity.

    Returns a nested dict: {type: {severity: count}}.

    Args:
        decisions: list of decision dicts (from store.get_all_decisions() or similar).

    Example return::

        {
            "DEVICE_INCOMPATIBLE": {"HIGH": 3, "MEDIUM": 1},
            "MISSING_DATA": {"MEDIUM": 5, "LOW": 2},
        }
    """
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for dec in decisions:
        dec_type = dec.get("type", "UNKNOWN")
        severity = dec.get("severity", "UNKNOWN")
        summary[dec_type][severity] += 1
    # Convert defaultdicts to regular dicts for clean serialization
    return {k: dict(v) for k, v in summary.items()}


def format_decision_report(decisions: list[dict[str, Any]]) -> str:
    """Human-readable decision summary for CLI output.

    Produces a compact multi-line report grouped by type with counts
    and resolution status.

    Args:
        decisions: list of decision dicts.

    Returns:
        Multi-line string suitable for console display.
    """
    if not decisions:
        return "No decisions to report."

    summary = summarize_decisions(decisions)

    # Count resolved vs pending
    total = len(decisions)
    resolved = sum(1 for d in decisions if d.get("chosen_option") is not None)
    pending = total - resolved

    lines: list[str] = [
        f"Decision Report: {total} total ({resolved} resolved, {pending} pending)",
        "-" * 60,
    ]

    # Sort types by total count descending
    type_totals = {
        dec_type: sum(sev_counts.values())
        for dec_type, sev_counts in summary.items()
    }
    for dec_type in sorted(type_totals, key=type_totals.get, reverse=True):  # type: ignore[arg-type]
        sev_counts = summary[dec_type]
        sev_parts = ", ".join(
            f"{sev}: {count}" for sev, count in sorted(sev_counts.items())
        )
        lines.append(f"  {dec_type}: {type_totals[dec_type]} ({sev_parts})")

    # Pending breakdown
    if pending > 0:
        lines.append("")
        lines.append(f"Pending decisions requiring resolution: {pending}")
        pending_by_severity: dict[str, int] = defaultdict(int)
        for d in decisions:
            if d.get("chosen_option") is None:
                pending_by_severity[d.get("severity", "UNKNOWN")] += 1
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            count = pending_by_severity.get(sev, 0)
            if count:
                lines.append(f"    {sev}: {count}")

    return "\n".join(lines)


def decisions_by_type(
    store: MigrationStore, decision_type: str
) -> list[dict[str, Any]]:
    """Query all decisions of a given type from the store.

    Args:
        store: MigrationStore instance.
        decision_type: DecisionType value string (e.g., "DEVICE_INCOMPATIBLE").

    Returns:
        List of decision dicts matching the given type.
    """
    all_decisions = store.get_all_decisions()
    return [d for d in all_decisions if d.get("type") == decision_type]


def pending_decisions(store: MigrationStore) -> list[dict[str, Any]]:
    """Query all unresolved decisions from the store.

    Returns:
        List of decision dicts where chosen_option is None.
    """
    all_decisions = store.get_all_decisions()
    return [d for d in all_decisions if d.get("chosen_option") is None]


def resolved_decisions(store: MigrationStore) -> list[dict[str, Any]]:
    """Query all resolved decisions from the store.

    Returns:
        List of decision dicts where chosen_option is not None.
    """
    all_decisions = store.get_all_decisions()
    return [d for d in all_decisions if d.get("chosen_option") is not None]


# ---------------------------------------------------------------------------
# Auto-apply / needs-input classification
# ---------------------------------------------------------------------------

def classify_decisions(
    store: MigrationStore,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split pending decisions into auto-apply and needs-input groups.

    Auto-apply = pending decisions that the project's ``config["auto_rules"]``
    would resolve. Each item is augmented with ``auto_choice`` and
    ``auto_reason`` keys (from ``preview_auto_rules``).

    Needs-input = pending decisions that no rule matches.

    Both groups exclude already-resolved decisions and ``__stale__``
    decisions.
    """
    from wxcli.migration.transform.rules import preview_auto_rules

    auto_apply = preview_auto_rules(store, config)
    auto_apply_ids = {d["decision_id"] for d in auto_apply}

    all_decisions = store.get_all_decisions()
    needs_input = [
        d for d in all_decisions
        if d.get("chosen_option") is None
        and d.get("chosen_option") != "__stale__"
        and d["decision_id"] not in auto_apply_ids
    ]

    return auto_apply, needs_input


# ---------------------------------------------------------------------------
# Decision review export (markdown)
# ---------------------------------------------------------------------------

# Group labels for the needs-input section
_DECISION_CATEGORY: dict[str, str] = {
    "LOCATION_AMBIGUOUS": "Location",
    "DEVICE_FIRMWARE_CONVERTIBLE": "Device",
    "DEVICE_INCOMPATIBLE": "Device",
    "WORKSPACE_LICENSE_TIER": "Workspace",
    "WORKSPACE_TYPE_UNCERTAIN": "Workspace",
    "HOTDESK_DN_CONFLICT": "Workspace",
    "EXTENSION_CONFLICT": "User",
    "DN_AMBIGUOUS": "User",
    "DUPLICATE_USER": "User",
    "SHARED_LINE_COMPLEX": "User",
    "MISSING_DATA": "Data Quality",
    "CSS_ROUTING_MISMATCH": "Routing",
    "CALLING_PERMISSION_MISMATCH": "Permissions",
    "VOICEMAIL_INCOMPATIBLE": "Voicemail",
    "FEATURE_APPROXIMATION": "Feature",
    "NUMBER_CONFLICT": "Number",
}


def generate_decision_review(
    store: MigrationStore,
    project_id: str,
    config: dict[str, Any],
) -> str:
    """Generate a markdown decision review file with auto-apply and needs-input sections."""
    auto_apply, needs_input = classify_decisions(store, config)

    lines: list[str] = []
    lines.append(f"# Migration Decision Review — {project_id}")
    lines.append(f"Generated: {_now_date()}")
    lines.append("")

    # --- Section 1: Auto-apply ---
    lines.append(f"## Auto-Apply ({len(auto_apply)} decisions)")
    lines.append("")
    if auto_apply:
        lines.append("These have only one sensible resolution and will be applied when you run")
        lines.append("`wxcli cucm decide --apply-auto`. Review and raise any concerns before applying.")
        lines.append("")
        lines.append("| ID | Type | Object | Resolution | Reason |")
        lines.append("|----|------|--------|------------|--------|")
        for d in auto_apply:
            did = d.get("decision_id", "")
            dtype = d.get("type", "")
            obj_name = _object_name(d)
            choice = d.get("auto_choice", "")
            reason = d.get("auto_reason", "")
            lines.append(f"| {did} | {dtype} | {obj_name} | {choice} | {reason} |")
    else:
        lines.append("No auto-apply decisions.")
    lines.append("")

    # --- Section 2: Needs input ---
    lines.append(f"## Needs Your Input ({len(needs_input)} decisions)")
    lines.append("")
    if needs_input:
        lines.append("Each decision requires admin judgment. Options are listed — discuss with")
        lines.append("your migration team if needed. Resolve via `wxcli cucm decide <ID> <choice>`")
        lines.append("or tell the migration agent your choices.")
        lines.append("")

        # Group by category
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for d in needs_input:
            cat = _DECISION_CATEGORY.get(d.get("type", ""), "Other")
            grouped[cat].append(d)

        for category in sorted(grouped.keys()):
            decs = grouped[category]
            lines.append(f"### {category} Decisions ({len(decs)})")
            lines.append("")
            lines.append("| ID | Severity | Summary | Options |")
            lines.append("|----|----------|---------|---------|")
            for d in decs:
                did = d.get("decision_id", "")
                sev = d.get("severity", "")
                summary = d.get("summary", "").replace("|", "/")
                opts = _format_options_short(d.get("options", []))
                lines.append(f"| {did} | {sev} | {summary} | {opts} |")

            # Detail section: show context for each decision
            lines.append("")
            for d in decs:
                did = d.get("decision_id", "")
                lines.append(f"**{did}** — {d.get('summary', '')}")
                lines.append("")
                for i, opt in enumerate(d.get("options", [])):
                    letter = chr(ord("a") + i)
                    opt_id = opt.get("id", "") if isinstance(opt, dict) else str(opt)
                    label = opt.get("label", opt_id) if isinstance(opt, dict) else str(opt)
                    impact = opt.get("impact", "") if isinstance(opt, dict) else ""
                    lines.append(f"  {letter}) **{label}** (`{opt_id}`) — {impact}")
                lines.append("")
    else:
        lines.append("No decisions require input — all are auto-apply.")
    lines.append("")

    return "\n".join(lines)


def _object_name(decision: dict[str, Any]) -> str:
    """Extract a readable object name from a decision's context or affected_objects."""
    ctx = decision.get("context", {})
    for key in ("device_name", "name", "canonical_id", "object_name"):
        val = ctx.get(key)
        if val:
            return str(val)
    affected = ctx.get("_affected_objects", [])
    if affected:
        return str(affected[0])
    return "unknown"


def _format_options_short(options: list) -> str:
    """Format options as a compact lettered list for table cells."""
    parts = []
    for i, opt in enumerate(options):
        letter = chr(ord("a") + i)
        if isinstance(opt, dict):
            opt_id = opt.get("id", "")
            label = opt.get("label", opt_id)
        else:
            label = str(opt)
        parts.append(f"**{letter}**) {label}")
    return " ".join(parts)


def _now_date() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
