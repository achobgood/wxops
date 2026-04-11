"""Per-user CUCM-vs-Webex migration diff report.

Joins 10+ object types from the post-analyze SQLite store to produce
a side-by-side comparison of what each user has in CUCM vs. what they'll
have in Webex Calling. Outputs self-contained HTML or flat CSV.
"""
from __future__ import annotations

import csv
import html
import io
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ForwardingRuleDiff:
    """Single forwarding rule comparison."""
    rule_type: str  # "always", "busy", "no_answer", "busy_internal", etc.
    cucm_enabled: bool
    cucm_destination: str | None
    webex_enabled: bool
    webex_destination: str | None
    status: str  # "mapped", "lossy", "not_mapped"


@dataclass
class ForwardingDiff:
    """Detailed call forwarding comparison."""
    rules: list[ForwardingRuleDiff] = field(default_factory=list)


@dataclass
class UserDecisionSummary:
    """Compact decision summary for the diff table."""
    decision_id: str
    type: str
    severity: str
    summary: str
    resolution: str  # "auto-resolved: {option}" or "pending"


@dataclass
class UserDiffRecord:
    """Complete CUCM-vs-Webex diff for a single user."""
    # Identity
    canonical_id: str
    display_name: str
    email: str | None = None
    cucm_userid: str | None = None

    # Extension & Numbers
    extension: str | None = None
    did: str | None = None
    extension_change: str = "unchanged"

    # Location
    cucm_location: str | None = None
    webex_location: str | None = None

    # Device
    cucm_device_model: str | None = None
    cucm_device_protocol: str | None = None
    webex_device_model: str | None = None
    device_tier: str | None = None
    device_action: str = "no_change"

    # Call Forwarding
    forwarding: ForwardingDiff | None = None

    # Voicemail
    cucm_voicemail: str | None = None
    webex_voicemail: str | None = None
    voicemail_greeting_action: str = "not_applicable"

    # BLF / Monitoring
    blf_count_cucm: int = 0
    blf_count_webex: int = 0
    blf_mapped: int = 0
    blf_unmapped: int = 0

    # Speed Dials
    speed_dial_count_cucm: int = 0
    speed_dial_count_webex: int = 0

    # Shared Lines
    shared_line_dns: list[str] = field(default_factory=list)
    shared_line_action: str = "none"

    # Button Layout
    total_buttons_cucm: int = 0
    mapped_buttons_webex: int = 0
    unmapped_buttons: list[str] = field(default_factory=list)

    # Calling Permissions
    cucm_css: str | None = None
    webex_permissions: str | None = None

    # Decisions
    decisions: list[UserDecisionSummary] = field(default_factory=list)

    # Summary flags
    has_changes: bool = False
    change_categories: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Index helpers — build O(1) lookup maps from bulk store queries
# ---------------------------------------------------------------------------

def _index_by_field(
    objects: list[dict[str, Any]], key_field: str,
) -> dict[str, list[dict[str, Any]]]:
    """Group objects by a field value. Returns {field_value: [obj, ...]}."""
    index: dict[str, list[dict[str, Any]]] = {}
    for obj in objects:
        key = obj.get(key_field)
        if key:
            index.setdefault(key, []).append(obj)
    return index


def _index_decisions_by_user(
    decisions: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index decisions by affected user canonical_id.

    Checks context dict for: user_canonical_id, affected_user,
    owner_canonical_id, and affected_objects (list).
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for dec in decisions:
        ctx = dec.get("context") or {}
        user_ids: set[str] = set()
        for key in ("user_canonical_id", "affected_user", "owner_canonical_id"):
            val = ctx.get(key)
            if val and isinstance(val, str) and val.startswith("user:"):
                user_ids.add(val)
        affected = ctx.get("affected_objects")
        if isinstance(affected, list):
            for item in affected:
                if isinstance(item, str) and item.startswith("user:"):
                    user_ids.add(item)
        for uid in user_ids:
            index.setdefault(uid, []).append(dec)
    return index


def _index_shared_lines_by_user(
    shared_lines: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index shared lines by member user canonical_id."""
    index: dict[str, list[dict[str, Any]]] = {}
    for sl in shared_lines:
        owners = sl.get("owner_canonical_ids") or []
        for uid in owners:
            index.setdefault(uid, []).append(sl)
    return index


def _index_permissions_by_user(
    permissions: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index calling permissions by assigned user canonical_id."""
    index: dict[str, list[dict[str, Any]]] = {}
    for perm in permissions:
        users = perm.get("assigned_users") or []
        for uid in users:
            index.setdefault(uid, []).append(perm)
    return index


# ---------------------------------------------------------------------------
# Per-field diff builders
# ---------------------------------------------------------------------------

# Forwarding rule types that Webex Calling supports (map 1:1)
_WEBEX_FORWARDING_TYPES = {"always", "busy", "no_answer"}


def _build_forwarding_diff(
    fwd: dict[str, Any] | None,
) -> ForwardingDiff | None:
    """Build forwarding diff from a call_forwarding store dict."""
    if fwd is None:
        return None

    rules: list[ForwardingRuleDiff] = []

    all_types = [
        ("always", "always_enabled", "always_destination"),
        ("busy", "busy_enabled", "busy_destination"),
        ("no_answer", "no_answer_enabled", "no_answer_destination"),
        ("busy_internal", "busy_internal_enabled", "busy_internal_destination"),
        ("no_answer_internal", "no_answer_internal_enabled", "no_answer_internal_destination"),
        ("no_coverage", "no_coverage_enabled", "no_coverage_destination"),
        ("on_failure", "on_failure_enabled", "on_failure_destination"),
        ("not_registered", "not_registered_enabled", "not_registered_destination"),
    ]

    has_any = False
    for rule_type, enabled_key, dest_key in all_types:
        enabled = fwd.get(enabled_key, False)
        dest = fwd.get(dest_key)
        if not enabled and not dest:
            continue
        has_any = True

        if rule_type in _WEBEX_FORWARDING_TYPES:
            to_vm_key = f"{rule_type}_to_voicemail"
            to_vm = fwd.get(to_vm_key, False)
            webex_dest = "Voicemail" if to_vm else dest
            ring_count = fwd.get("no_answer_ring_count") if rule_type == "no_answer" else None
            if ring_count and webex_dest:
                webex_dest = f"{webex_dest} ({ring_count} rings)"
            rules.append(ForwardingRuleDiff(
                rule_type=rule_type,
                cucm_enabled=enabled,
                cucm_destination=dest,
                webex_enabled=enabled,
                webex_destination=webex_dest,
                status="mapped",
            ))
        else:
            rules.append(ForwardingRuleDiff(
                rule_type=rule_type,
                cucm_enabled=enabled,
                cucm_destination=dest,
                webex_enabled=False,
                webex_destination=None,
                status="not_mapped",
            ))

    return ForwardingDiff(rules=rules) if has_any else None


def _determine_device_action(tier: str | None) -> str:
    """Map compatibility tier to a human-readable action."""
    return {
        "native_mpp": "no_change",
        "convertible": "firmware_upgrade",
        "webex_app": "webex_app",
        "incompatible": "replace",
    }.get(tier or "", "no_change")


def _determine_webex_device_model(
    cucm_model: str | None, tier: str | None,
) -> str | None:
    """Determine what device model the user will have in Webex."""
    if not cucm_model:
        return None
    if tier in ("native_mpp", "convertible"):
        return cucm_model
    if tier == "webex_app":
        return "Webex App"
    if tier == "incompatible":
        return "New device TBD"
    return cucm_model


def _format_perm_summary(perm: dict[str, Any]) -> str:
    """Format calling permissions into a short summary string."""
    entries = perm.get("calling_permissions") or []
    allowed = []
    for e in entries:
        if isinstance(e, dict) and e.get("action") == "ALLOW":
            allowed.append(e["call_type"].replace("_", " ").title())
    if not allowed:
        return "All blocked"
    return " + ".join(allowed[:4])


# ---------------------------------------------------------------------------
# Core join logic
# ---------------------------------------------------------------------------

def _build_single_user_diff(
    user: dict[str, Any],
    device_by_owner: dict[str, list[dict[str, Any]]],
    fwd_by_user: dict[str, list[dict[str, Any]]],
    vm_by_user: dict[str, list[dict[str, Any]]],
    monitor_by_user: dict[str, list[dict[str, Any]]],
    layout_by_owner: dict[str, list[dict[str, Any]]],
    location_by_id: dict[str, dict[str, Any]],
    decisions_by_user: dict[str, list[dict[str, Any]]],
    shared_by_user: dict[str, list[dict[str, Any]]],
    perms_by_user: dict[str, list[dict[str, Any]]],
    css_by_user: dict[str, str],
) -> UserDiffRecord:
    """Build a UserDiffRecord for a single user."""
    uid = user["canonical_id"]
    changes: list[str] = []

    # --- Identity ---
    emails = user.get("emails") or []
    email = emails[0] if emails else None
    first = user.get("first_name") or ""
    last = user.get("last_name") or ""
    display_name = user.get("display_name") or f"{first} {last}".strip() or uid

    # --- Location ---
    loc_id = user.get("location_id")
    loc = location_by_id.get(loc_id) if loc_id else None
    cucm_loc = None
    webex_loc = None
    if loc:
        webex_loc = loc.get("name")
        pools = loc.get("cucm_device_pool_names") or []
        cucm_loc = pools[0] if pools else loc.get("cucm_location_name")

    # --- Device ---
    devices = device_by_owner.get(uid, [])
    dev = devices[0] if devices else None
    cucm_model = dev.get("model") if dev else None
    cucm_protocol = dev.get("cucm_protocol") if dev else None
    tier = dev.get("compatibility_tier") if dev else None
    webex_model = _determine_webex_device_model(cucm_model, tier)
    device_action = _determine_device_action(tier)
    if device_action != "no_change" and cucm_model:
        changes.append("device")

    # --- Call Forwarding ---
    fwd_list = fwd_by_user.get(uid, [])
    fwd = fwd_list[0] if fwd_list else None
    forwarding = _build_forwarding_diff(fwd)
    if forwarding and any(r.status == "not_mapped" for r in forwarding.rules):
        changes.append("forwarding")

    # --- Voicemail ---
    vm_list = vm_by_user.get(uid, [])
    vm = vm_list[0] if vm_list else None
    cucm_vm = None
    webex_vm = None
    greeting_action = "not_applicable"
    if vm:
        enabled = vm.get("enabled", True)
        profile_name = vm.get("cucm_voicemail_profile_name") or "Unity"
        cucm_vm = f"Enabled ({profile_name})" if enabled else "Disabled"
        webex_vm = "Enabled (Webex VM)" if enabled else "Disabled"
        if enabled:
            greeting_action = "re-record"
            changes.append("voicemail")

    # --- Monitoring / BLF ---
    mon_list = monitor_by_user.get(uid, [])
    mon = mon_list[0] if mon_list else None
    blf_cucm = 0
    blf_mapped = 0
    blf_unmapped = 0
    if mon:
        members = mon.get("monitored_members") or []
        blf_cucm = len(members)
        blf_mapped = sum(1 for m in members if m.get("mapped", False))
        blf_unmapped = blf_cucm - blf_mapped
        if blf_unmapped > 0:
            changes.append("monitoring")

    # --- Device Layout ---
    layouts = layout_by_owner.get(uid, [])
    layout = layouts[0] if layouts else None
    total_buttons = 0
    mapped_buttons = 0
    speed_cucm = 0
    speed_webex = 0
    unmapped_descs: list[str] = []
    if layout:
        keys = layout.get("resolved_line_keys") or []
        total_buttons = len(keys)
        mapped_buttons = total_buttons
        sds = layout.get("speed_dials") or []
        speed_cucm = len(sds)
        speed_webex = speed_cucm
        um = layout.get("unmapped_buttons") or []
        unmapped_descs = [b.get("label") or b.get("type", "Unknown") for b in um]
        total_buttons += len(um)
        if unmapped_descs:
            changes.append("buttons")

    # --- Shared Lines ---
    shared_list = shared_by_user.get(uid, [])
    shared_dns: list[str] = []
    shared_action = "none"
    for sl in shared_list:
        dn_id = sl.get("dn_canonical_id") or ""
        shared_dns.append(dn_id)
    if shared_dns:
        shared_action = "virtual_line"
        changes.append("shared_lines")

    # --- Calling Permissions ---
    perm_list = perms_by_user.get(uid, [])
    perm = perm_list[0] if perm_list else None
    cucm_css = css_by_user.get(uid)
    webex_perms = _format_perm_summary(perm) if perm else None
    if cucm_css and webex_perms:
        changes.append("permissions")

    # --- Decisions ---
    user_decs = decisions_by_user.get(uid, [])
    dec_summaries: list[UserDecisionSummary] = []
    for d in user_decs:
        chosen = d.get("chosen_option")
        resolution = f"auto-resolved: {chosen}" if chosen else "pending"
        dec_summaries.append(UserDecisionSummary(
            decision_id=d.get("decision_id", ""),
            type=d.get("type", ""),
            severity=d.get("severity", ""),
            summary=d.get("summary", ""),
            resolution=resolution,
        ))
    if any(ds.resolution == "pending" for ds in dec_summaries):
        changes.append("decisions")

    return UserDiffRecord(
        canonical_id=uid,
        display_name=display_name,
        email=email,
        cucm_userid=user.get("cucm_userid"),
        extension=user.get("extension"),
        did=None,
        extension_change="unchanged",
        cucm_location=cucm_loc,
        webex_location=webex_loc,
        cucm_device_model=cucm_model,
        cucm_device_protocol=cucm_protocol,
        webex_device_model=webex_model,
        device_tier=tier,
        device_action=device_action,
        forwarding=forwarding,
        cucm_voicemail=cucm_vm,
        webex_voicemail=webex_vm,
        voicemail_greeting_action=greeting_action,
        blf_count_cucm=blf_cucm,
        blf_count_webex=blf_mapped,
        blf_mapped=blf_mapped,
        blf_unmapped=blf_unmapped,
        speed_dial_count_cucm=speed_cucm,
        speed_dial_count_webex=speed_webex,
        shared_line_dns=shared_dns,
        shared_line_action=shared_action,
        total_buttons_cucm=total_buttons,
        mapped_buttons_webex=mapped_buttons,
        unmapped_buttons=unmapped_descs,
        cucm_css=cucm_css,
        webex_permissions=webex_perms,
        decisions=dec_summaries,
        has_changes=len(changes) > 0,
        change_categories=changes,
    )


def build_user_diffs(
    store: Any,
    user_filter: str | None = None,
    location_filter: str | None = None,
) -> list[UserDiffRecord]:
    """Build per-user diff records from the migration store.

    Args:
        store: MigrationStore instance (post-analyze state).
        user_filter: If set, only return this single user's canonical_id.
        location_filter: If set, only return users in this location canonical_id.

    Returns:
        List of UserDiffRecord sorted by display_name.
    """
    # 1. Bulk load all relevant object types
    users = store.get_objects("user")
    devices = store.get_objects("device")
    call_fwds = store.get_objects("call_forwarding")
    vm_profiles = store.get_objects("voicemail_profile")
    monitoring = store.get_objects("monitoring_list")
    layouts = store.get_objects("device_layout")
    shared_lines = store.get_objects("shared_line")
    permissions = store.get_objects("calling_permission")
    decisions = store.get_all_decisions()
    locations = store.get_objects("location")

    # 2. Build index maps for O(1) lookups
    device_by_owner = _index_by_field(devices, "owner_canonical_id")
    fwd_by_user = _index_by_field(call_fwds, "user_canonical_id")
    monitor_by_user = _index_by_field(monitoring, "user_canonical_id")
    layout_by_owner = _index_by_field(layouts, "owner_canonical_id")
    location_by_id = {loc["canonical_id"]: loc for loc in locations}

    # Voicemail profiles may be indexed by user_canonical_id field OR
    # wired via user_has_voicemail cross-refs — support both patterns.
    vm_profile_by_id = {p["canonical_id"]: p for p in vm_profiles}
    vm_by_user: dict[str, list[dict[str, Any]]] = _index_by_field(
        vm_profiles, "user_canonical_id"
    )
    try:
        vm_refs = store.get_cross_refs(relationship="user_has_voicemail")
        for ref in vm_refs:
            uid_ref = ref["from_id"]
            profile = vm_profile_by_id.get(ref["to_id"])
            if profile:
                vm_by_user.setdefault(uid_ref, []).append(profile)
    except Exception:
        pass

    # 3. Index decisions, shared lines, permissions by user
    decisions_by_user = _index_decisions_by_user(decisions)
    shared_by_user = _index_shared_lines_by_user(shared_lines)
    perms_by_user = _index_permissions_by_user(permissions)

    # 4. Build CSS-by-user map from cross-refs
    css_by_user: dict[str, str] = {}
    try:
        css_refs = store.get_cross_refs(relationship="user_has_css")
        for ref in css_refs:
            css_by_user[ref["from_id"]] = ref["to_id"].split(":", 1)[-1]
    except Exception:
        pass  # cross-ref may not exist

    # 5. Apply filters
    if user_filter:
        users = [u for u in users if u["canonical_id"] == user_filter]
    if location_filter:
        users = [u for u in users if u.get("location_id") == location_filter]

    # 6. Build diff record for each user
    results: list[UserDiffRecord] = []
    for user in users:
        record = _build_single_user_diff(
            user, device_by_owner, fwd_by_user, vm_by_user,
            monitor_by_user, layout_by_owner, location_by_id,
            decisions_by_user, shared_by_user, perms_by_user,
            css_by_user,
        )
        results.append(record)

    # 7. Sort by display name
    results.sort(key=lambda r: (r.display_name or "").lower())
    return results


# ---------------------------------------------------------------------------
# CSV Renderer
# ---------------------------------------------------------------------------

def _diff_status(cucm_val: str | None, webex_val: str | None) -> str:
    """Determine diff status between CUCM and Webex values."""
    if not cucm_val and not webex_val:
        return "unchanged"
    if not cucm_val and webex_val:
        return "new"
    if cucm_val and not webex_val:
        return "removed"
    if cucm_val == webex_val:
        return "unchanged"
    return "changed"


def render_csv(records: list[UserDiffRecord]) -> str:
    """Render diff records as CSV with UTF-8 BOM.

    One row per user per setting category.
    """
    output = io.StringIO()
    output.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "User", "Email", "Extension", "Category",
        "CUCM_Value", "Webex_Value", "Status", "Decision_ID",
    ])

    for r in records:
        base = [r.display_name, r.email or "", r.extension or ""]

        # Device
        cucm_dev = (f"{r.cucm_device_model} ({r.cucm_device_protocol})"
                    if r.cucm_device_model else "")
        webex_dev = r.webex_device_model or ""
        writer.writerow(base + [
            "Phone Model", cucm_dev, webex_dev,
            _diff_status(r.cucm_device_model, r.webex_device_model), "",
        ])

        if r.device_tier:
            tier_display = r.device_tier.replace("_", " ").title()
            writer.writerow(base + [
                "Compatibility", "--", f"{tier_display} ({r.device_action})",
                "new", "",
            ])

        # Extension
        writer.writerow(base + [
            "Extension", r.extension or "", r.extension or "",
            r.extension_change, "",
        ])

        # DID
        if r.did:
            writer.writerow(base + [
                "DID", r.did, r.did, "unchanged", "",
            ])

        # Location
        writer.writerow(base + [
            "Location", r.cucm_location or "", r.webex_location or "",
            _diff_status(r.cucm_location, r.webex_location), "",
        ])

        # Voicemail
        if r.cucm_voicemail or r.webex_voicemail:
            writer.writerow(base + [
                "Voicemail", r.cucm_voicemail or "Disabled",
                r.webex_voicemail or "Disabled",
                _diff_status(r.cucm_voicemail, r.webex_voicemail), "",
            ])
            if r.voicemail_greeting_action == "re-record":
                writer.writerow(base + [
                    "Voicemail Greeting", "--", "RE-RECORD",
                    "action_required", "",
                ])

        # Forwarding rules
        if r.forwarding:
            for rule in r.forwarding.rules:
                cucm_dest = rule.cucm_destination or (
                    "Enabled" if rule.cucm_enabled else "Off")
                if rule.status == "not_mapped":
                    webex_dest = "NOT MAPPED"
                else:
                    webex_dest = rule.webex_destination or (
                        "Enabled" if rule.webex_enabled else "Off")
                label = f"Fwd {rule.rule_type.replace('_', ' ').title()}"
                writer.writerow(base + [
                    label, cucm_dest, webex_dest, rule.status, "",
                ])

        # BLF
        if r.blf_count_cucm > 0:
            writer.writerow(base + [
                "BLF Keys", str(r.blf_count_cucm), str(r.blf_mapped),
                "unchanged" if r.blf_unmapped == 0 else "changed", "",
            ])

        # Speed Dials
        if r.speed_dial_count_cucm > 0:
            writer.writerow(base + [
                "Speed Dials", str(r.speed_dial_count_cucm),
                str(r.speed_dial_count_webex), "unchanged", "",
            ])

        # Shared Lines
        if r.shared_line_dns:
            writer.writerow(base + [
                "Shared Lines", str(len(r.shared_line_dns)),
                r.shared_line_action, "changed", "",
            ])

        # Unmapped Buttons
        if r.unmapped_buttons:
            writer.writerow(base + [
                "Unmapped Buttons", str(len(r.unmapped_buttons)),
                "; ".join(r.unmapped_buttons), "action_required", "",
            ])

        # Calling Permissions
        if r.cucm_css or r.webex_permissions:
            writer.writerow(base + [
                "Calling Permissions", r.cucm_css or "",
                r.webex_permissions or "",
                _diff_status(r.cucm_css, r.webex_permissions), "",
            ])

        # Decisions
        for dec in r.decisions:
            writer.writerow(base + [
                f"Decision: {dec.type}", dec.summary,
                dec.resolution, dec.severity.lower(), dec.decision_id,
            ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# HTML Renderer
# ---------------------------------------------------------------------------

def _css_class_for_status(status: str) -> str:
    """Map diff status to CSS class name."""
    return {
        "unchanged": "unchanged",
        "changed": "changed",
        "not_mapped": "not-mapped",
        "new": "new",
        "action_required": "action-required",
        "mapped": "unchanged",
        "lossy": "changed",
    }.get(status, "")


def _render_diff_row(
    setting: str, cucm: str, webex: str, status: str = "",
) -> str:
    """Render a single <tr> for the diff table."""
    cls = _css_class_for_status(status)
    cucm_e = html.escape(cucm)
    webex_e = html.escape(webex)
    return (
        f'<tr><td>{html.escape(setting)}</td>'
        f'<td class="{cls}">{cucm_e}</td>'
        f'<td class="{cls}">{webex_e}</td></tr>\n'
    )


def _render_user_section(r: UserDiffRecord) -> str:
    """Render a single <details> section for one user."""
    ext_display = f" &mdash; ext. {html.escape(r.extension)}" if r.extension else ""
    email_display = f" ({html.escape(r.email)})" if r.email else ""
    change_count = len(r.change_categories)
    badge = ""
    if change_count > 0:
        badge = f' <span class="badge warning">{change_count} change{"s" if change_count != 1 else ""}</span>'
    elif r.decisions:
        badge = f' <span class="badge info">{len(r.decisions)} decision{"s" if len(r.decisions) != 1 else ""}</span>'

    categories = ",".join(r.change_categories) if r.change_categories else "none"
    has_decisions = "true" if r.decisions else "false"

    lines: list[str] = []
    lines.append(
        f'<details class="user-diff" data-categories="{categories}" '
        f'data-decisions="{has_decisions}">'
    )
    lines.append(
        f'<summary><strong>{html.escape(r.display_name)}</strong>'
        f'{email_display}{ext_display}{badge}</summary>'
    )
    lines.append('<table class="diff-table"><thead><tr>')
    lines.append('<th>Setting</th><th>CUCM (Current)</th><th>Webex (Planned)</th>')
    lines.append('</tr></thead><tbody>')

    # Device
    if r.cucm_device_model:
        cucm_dev = f"{r.cucm_device_model} ({r.cucm_device_protocol or 'SIP'})"
        webex_dev = r.webex_device_model or ""
        lines.append(_render_diff_row(
            "Phone Model", cucm_dev, webex_dev,
            "changed" if cucm_dev != webex_dev else "unchanged",
        ))
        if r.device_tier:
            tier_d = r.device_tier.replace("_", " ").title()
            lines.append(_render_diff_row(
                "Compatibility", "--", f"{tier_d}", "new",
            ))

    # Extension
    if r.extension:
        lines.append(_render_diff_row(
            "Extension", r.extension, r.extension, r.extension_change,
        ))

    # DID
    if r.did:
        lines.append(_render_diff_row("DID", r.did, r.did, "unchanged"))

    # Location
    if r.cucm_location or r.webex_location:
        lines.append(_render_diff_row(
            "Location", r.cucm_location or "--", r.webex_location or "--",
            _diff_status(r.cucm_location, r.webex_location),
        ))

    # Voicemail
    if r.cucm_voicemail or r.webex_voicemail:
        lines.append(_render_diff_row(
            "Voicemail", r.cucm_voicemail or "Disabled",
            r.webex_voicemail or "Disabled",
            _diff_status(r.cucm_voicemail, r.webex_voicemail),
        ))
        if r.voicemail_greeting_action == "re-record":
            lines.append(_render_diff_row(
                "", "", "Greeting: RE-RECORD", "action_required",
            ))

    # Forwarding
    if r.forwarding:
        for rule in r.forwarding.rules:
            cucm_dest = rule.cucm_destination or (
                "Enabled" if rule.cucm_enabled else "Off")
            if rule.status == "not_mapped":
                webex_dest = "NOT MAPPED"
            else:
                webex_dest = rule.webex_destination or (
                    "Enabled" if rule.webex_enabled else "Off")
            label = f"Fwd {rule.rule_type.replace('_', ' ').title()}"
            lines.append(_render_diff_row(label, cucm_dest, webex_dest, rule.status))

    # Shared Lines
    if r.shared_line_dns:
        lines.append(_render_diff_row(
            "Shared Lines", str(len(r.shared_line_dns)),
            r.shared_line_action.replace("_", " ").title(), "changed",
        ))

    # BLF
    if r.blf_count_cucm > 0:
        blf_status = "unchanged" if r.blf_unmapped == 0 else "changed"
        detail = f"{r.blf_mapped} mapped"
        if r.blf_unmapped:
            detail += f", {r.blf_unmapped} unmapped"
        lines.append(_render_diff_row(
            "BLF Keys", str(r.blf_count_cucm), detail, blf_status,
        ))

    # Speed Dials
    if r.speed_dial_count_cucm > 0:
        lines.append(_render_diff_row(
            "Speed Dials", str(r.speed_dial_count_cucm),
            str(r.speed_dial_count_webex), "unchanged",
        ))

    # Unmapped Buttons
    if r.unmapped_buttons:
        lines.append(_render_diff_row(
            "Unmapped Buttons", str(len(r.unmapped_buttons)),
            "; ".join(r.unmapped_buttons), "action_required",
        ))

    # Calling Permissions
    if r.cucm_css or r.webex_permissions:
        lines.append(_render_diff_row(
            "Calling Permissions", r.cucm_css or "--",
            r.webex_permissions or "--",
            _diff_status(r.cucm_css, r.webex_permissions),
        ))

    lines.append('</tbody></table>')

    # Decisions section
    if r.decisions:
        lines.append('<div class="decisions-section"><h4>Decisions</h4><ul>')
        for d in r.decisions:
            sev_cls = d.severity.lower()
            lines.append(
                f'<li><span class="badge {sev_cls}">{html.escape(d.severity)}</span> '
                f'{html.escape(d.decision_id)}: {html.escape(d.type)} &mdash; '
                f'{html.escape(d.resolution)}</li>'
            )
        lines.append('</ul></div>')

    lines.append('</details>')
    return "\n".join(lines)


_USER_DIFF_CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
    --warm-50: #fdf8f3; --warm-100: #f9efe4; --warm-200: #f0dcc6;
    --slate-400: #8e97a5; --slate-500: #636e7e; --slate-700: #353d4a;
    --slate-800: #242a33; --slate-900: #181c22;
    --primary: #00897B; --primary-light: #E0F2F1;
    --success: #2E7D32; --warning: #EF6C00; --critical: #C62828;
    --font-display: 'Lora', Georgia, serif;
    --font-body: 'Source Sans 3', system-ui, sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;
}
body { font-family: var(--font-body); background: var(--warm-50);
       color: var(--slate-800); line-height: 1.5; padding: 0; }
.page-header { background: var(--slate-900); color: #fff; padding: 32px 40px; }
.page-header h1 { font-family: var(--font-display); font-size: 1.75rem;
                   font-weight: 600; margin-bottom: 4px; }
.page-header p { color: var(--slate-400); font-size: 0.9rem; }
.summary-bar { display: flex; gap: 24px; padding: 20px 40px;
               background: #fff; border-bottom: 1px solid var(--warm-200); }
.summary-bar .stat { font-size: 0.95rem; color: var(--slate-700); }
.summary-bar .stat strong { font-size: 1.3rem; display: block;
                            color: var(--slate-800); }
.controls { display: flex; gap: 12px; padding: 16px 40px;
            align-items: center; flex-wrap: wrap; }
.controls input { flex: 1; min-width: 200px; padding: 8px 12px;
                  border: 1px solid var(--warm-200); border-radius: 4px;
                  font-family: var(--font-body); font-size: 0.9rem; }
.controls select { padding: 8px 12px; border: 1px solid var(--warm-200);
                   border-radius: 4px; font-family: var(--font-body);
                   font-size: 0.9rem; background: #fff; }
.controls button { padding: 8px 16px; border: 1px solid var(--warm-200);
                   border-radius: 4px; background: #fff; cursor: pointer;
                   font-family: var(--font-body); font-size: 0.9rem; }
.controls button:hover { background: var(--warm-100); }
.user-list { padding: 16px 40px; }
.user-diff { border: 1px solid var(--warm-200); border-radius: 4px;
             margin: 8px 0; background: #fff; }
.user-diff summary { padding: 12px 16px; cursor: pointer; display: flex;
                     align-items: center; gap: 12px; font-size: 0.95rem;
                     list-style: none; }
.user-diff summary::-webkit-details-marker { display: none; }
.user-diff summary::before { content: '\\25b6'; font-size: 0.7rem;
                             color: var(--slate-400); transition: transform 0.15s; }
.user-diff[open] summary::before { transform: rotate(90deg); }
.user-diff[open] summary { border-bottom: 1px solid var(--warm-200);
                           background: var(--warm-50); }
.diff-table { width: 100%; border-collapse: collapse; }
.diff-table th { text-align: left; text-transform: uppercase; font-size: 0.75rem;
                 letter-spacing: 0.05em; color: var(--slate-500);
                 padding: 8px 12px; border-bottom: 2px solid var(--warm-200); }
.diff-table td { padding: 6px 12px; border-bottom: 1px solid var(--warm-100);
                 font-size: 0.9rem; }
.diff-table .not-mapped { color: var(--critical); font-style: italic; }
.diff-table .unchanged { color: var(--slate-400); }
.diff-table .changed { color: var(--warning); font-weight: 600; }
.diff-table .new { color: var(--success); }
.diff-table .action-required { color: var(--primary); font-weight: 600; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
         font-size: 0.75rem; font-weight: 600; }
.badge.warning { background: #FFF3E0; color: var(--warning); }
.badge.info { background: var(--primary-light); color: var(--primary); }
.badge.high, .badge.critical { background: #FFEBEE; color: var(--critical); }
.badge.medium { background: #FFF3E0; color: var(--warning); }
.badge.low { background: #E8F5E9; color: var(--success); }
.decisions-section { padding: 12px 16px; background: var(--warm-50);
                     border-top: 1px solid var(--warm-200); }
.decisions-section h4 { font-family: var(--font-display); font-size: 0.9rem;
                        margin-bottom: 8px; }
.decisions-section ul { list-style: none; }
.decisions-section li { padding: 4px 0; font-size: 0.85rem; }
.empty-state { text-align: center; padding: 60px; color: var(--slate-500);
               font-size: 1.1rem; }
footer { padding: 24px 40px; text-align: center; color: var(--slate-400);
         font-size: 0.8rem; border-top: 1px solid var(--warm-200);
         margin-top: 32px; }
.hidden { display: none !important; }
@media print {
    .controls, .page-header, footer { display: none; }
    .user-diff[open] summary { background: transparent; }
    .user-diff { break-inside: avoid; }
    details[open] { display: block; }
}
"""

_USER_DIFF_JS = """\
(function() {
    var search = document.getElementById('search');
    var filter = document.getElementById('filter-category');
    var expandBtn = document.getElementById('expand-all');
    var details = document.querySelectorAll('.user-diff');

    function applyFilters() {
        var q = search.value.toLowerCase();
        var cat = filter.value;
        details.forEach(function(el) {
            var text = el.querySelector('summary').textContent.toLowerCase();
            var cats = el.dataset.categories || '';
            var hasDec = el.dataset.decisions === 'true';
            var matchSearch = !q || text.indexOf(q) >= 0;
            var matchCat = cat === 'all'
                || (cat === 'no-change' && cats === 'none')
                || (cat === 'decisions' && hasDec)
                || cats.indexOf(cat) >= 0;
            if (matchSearch && matchCat) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        });
    }

    search.addEventListener('input', applyFilters);
    filter.addEventListener('change', applyFilters);

    var expanded = false;
    expandBtn.addEventListener('click', function() {
        expanded = !expanded;
        details.forEach(function(el) {
            if (!el.classList.contains('hidden')) el.open = expanded;
        });
        expandBtn.textContent = expanded ? 'Collapse All' : 'Expand All';
    });
})();
"""


def render_html(
    records: list[UserDiffRecord],
    brand: str = "",
) -> str:
    """Render diff records as a self-contained HTML document."""
    change_count = sum(1 for r in records if r.has_changes)
    no_change_count = len(records) - change_count
    pending_count = sum(
        1 for r in records
        for d in r.decisions if d.resolution == "pending"
    )
    date_str = __import__("datetime").date.today().isoformat()

    user_sections = "\n".join(_render_user_section(r) for r in records)
    if not records:
        user_sections = '<p class="empty-state">No users found in the migration store.</p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Per-User Migration Diff &mdash; {html.escape(brand)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Source+Sans+3:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{_USER_DIFF_CSS}
</style>
</head>
<body>
<header class="page-header">
<h1>Per-User Migration Diff</h1>
<p>Generated {date_str} | {len(records)} users | {html.escape(brand)}</p>
</header>

<div class="summary-bar">
<div class="stat"><strong>{len(records)}</strong> Total Users</div>
<div class="stat"><strong>{change_count}</strong> With Changes</div>
<div class="stat"><strong>{no_change_count}</strong> No Changes</div>
<div class="stat"><strong>{pending_count}</strong> Pending Decisions</div>
</div>

<div class="controls">
<input type="text" id="search" placeholder="Search by name, email, or extension...">
<select id="filter-category">
<option value="all">All Users</option>
<option value="device">Device Changes</option>
<option value="forwarding">Forwarding Changes</option>
<option value="voicemail">Voicemail Changes</option>
<option value="decisions">Has Decisions</option>
<option value="no-change">No Changes</option>
</select>
<button id="expand-all" type="button">Expand All</button>
</div>

<div class="user-list">
{user_sections}
</div>

<footer>
<p>Generated by wxcli cucm user-diff</p>
</footer>

<script>
{_USER_DIFF_JS}
</script>
</body>
</html>'''
