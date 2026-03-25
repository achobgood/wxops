"""Technical appendix HTML generator for the CUCM assessment report.

Generates variable-length appendix with collapsible ``<details>/<summary>``
sections.  Each section is only emitted when relevant data exists in the
store — an empty environment produces an empty appendix.

One public function: ``generate_appendix(store) -> str``.
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

from wxcli.migration.store import MigrationStore


# ---------------------------------------------------------------------------
# Device compatibility tier labels and guidance
# ---------------------------------------------------------------------------

_TIER_LABELS = {
    "native_mpp": "Native MPP",
    "convertible": "Convertible",
    "incompatible": "Incompatible",
}

_TIER_GUIDANCE = {
    "native_mpp": "Direct migration — no hardware changes required.",
    "convertible": "Firmware flash required to convert to MPP firmware.",
    "incompatible": "Hardware replacement required — not supported on Webex Calling.",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_appendix(store: MigrationStore) -> str:
    """Generate the full technical appendix HTML from a migration store."""
    sections: list[str] = []

    for generator in [
        _object_inventory,
        _decision_detail,
        _css_partition_analysis,
        _device_inventory,
        _dn_analysis,
        _user_device_line_map,
        _routing_topology,
        _voicemail_analysis,
        _call_forwarding_summary,
        _speed_dials_monitoring,
        _data_coverage,
    ]:
        fragment = generator(store)
        if fragment:
            sections.append(fragment)

    if not sections:
        return '<section class="appendix"><p>No appendix data available.</p></section>'

    return (
        '<section class="appendix">\n'
        '<h2>Technical Appendix</h2>\n'
        + "\n".join(sections)
        + "\n</section>"
    )


# ---------------------------------------------------------------------------
# 1. Object Inventory
# ---------------------------------------------------------------------------

_INVENTORY_TYPES = [
    ("location", "Locations"),
    ("user", "Users"),
    ("device", "Devices"),
    ("hunt_group", "Hunt Groups"),
    ("auto_attendant", "Auto Attendants"),
    ("call_queue", "Call Queues"),
    ("call_park", "Call Park"),
    ("pickup_group", "Pickup Groups"),
    ("trunk", "Trunks"),
    ("route_group", "Route Groups"),
    ("dial_plan", "Dial Plans"),
    ("translation_pattern", "Translation Patterns"),
    ("operating_mode", "Operating Modes"),
    ("paging_group", "Paging Groups"),
    ("voicemail_profile", "Voicemail Profiles"),
    ("shared_line", "Shared Lines"),
    ("virtual_line", "Virtual Lines"),
    ("workspace", "Workspaces"),
    ("calling_permission", "Calling Permissions"),
    ("schedule", "Schedules"),
]


def _object_inventory(store: MigrationStore) -> str:
    """Tables grouped by object type and by location."""
    rows: list[tuple[str, int]] = []
    for type_key, label in _INVENTORY_TYPES:
        count = store.count_by_type(type_key)
        if count > 0:
            rows.append((label, count))

    css_count = store.count_by_type("css")
    if css_count > 0:
        rows.append(("Calling Search Spaces", css_count))
    pt_count = store.count_by_type("partition")
    if pt_count > 0:
        rows.append(("Partitions", pt_count))

    if not rows:
        return ""

    lines = [
        '<details open id="objects">',
        '  <summary>Object Inventory</summary>',
        '  <table>',
        '    <thead><tr><th>Object Type</th><th>Count</th></tr></thead>',
        '    <tbody>',
    ]
    for label, count in rows:
        lines.append(f'      <tr><td>{_esc(label)}</td><td>{count}</td></tr>')
    lines.append('    </tbody>')
    lines.append('  </table>')

    location_breakdown = _location_breakdown(store)
    if location_breakdown:
        lines.append('  <h4>By Location</h4>')
        lines.append('  <table>')
        lines.append('    <thead><tr><th>Location</th><th>Users</th><th>Devices</th></tr></thead>')
        lines.append('    <tbody>')
        for loc_name, user_ct, device_ct in location_breakdown:
            lines.append(
                f'      <tr><td>{_esc(loc_name)}</td>'
                f'<td>{user_ct}</td><td>{device_ct}</td></tr>'
            )
        lines.append('    </tbody>')
        lines.append('  </table>')

    lines.append('</details>')
    return "\n".join(lines)


def _location_breakdown(store: MigrationStore) -> list[tuple[str, int, int]]:
    """Return (location_name, user_count, device_count) per location."""
    locations = store.get_objects("location")
    if not locations:
        return []

    all_users = store.get_objects("user")
    user_locations: dict[str, str] = {
        u.get("canonical_id", ""): u.get("location_id", "")
        for u in all_users
    }

    user_counts: dict[str, int] = defaultdict(int)
    for loc_id in user_locations.values():
        if loc_id:
            user_counts[loc_id] += 1

    all_devices = store.get_objects("device")
    device_counts: dict[str, int] = defaultdict(int)
    for d in all_devices:
        owner = d.get("owner_canonical_id", "")
        if owner:
            owner_loc = user_locations.get(owner, "")
            if owner_loc:
                device_counts[owner_loc] += 1

    result: list[tuple[str, int, int]] = []
    for loc in locations:
        loc_id = loc.get("canonical_id", "")
        loc_name = loc.get("name", loc_id)
        result.append((loc_name, user_counts.get(loc_id, 0), device_counts.get(loc_id, 0)))

    return result


# ---------------------------------------------------------------------------
# 2. Decision Detail
# ---------------------------------------------------------------------------

def _decision_detail(store: MigrationStore) -> str:
    """Every decision grouped by DecisionType, with context and severity."""
    decisions = store.get_all_decisions()
    if not decisions:
        return ""

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in decisions:
        by_type[d["type"]].append(d)

    lines = [
        '<details open id="decision-detail">',
        '  <summary>Decision Detail</summary>',
    ]

    for dtype, dlist in sorted(by_type.items()):
        lines.append(f'  <h4>{_esc(dtype)}</h4>')
        lines.append('  <table>')
        lines.append(
            '    <thead><tr>'
            '<th>ID</th><th>Severity</th><th>Summary</th>'
            '<th>Status</th>'
            '</tr></thead>'
        )
        lines.append('    <tbody>')
        for d in dlist:
            status = "Resolved" if d.get("chosen_option") else "Pending"
            if d.get("resolved_by") == "auto_rule":
                status = "Auto-resolved"

            severity_lower = d.get("severity", "low").lower()
            status_badge = f'<span class="badge badge-auto">{_esc(status)}</span>'
            if status == "Pending":
                status_badge = f'<span class="badge badge-decision">{_esc(status)}</span>'

            lines.append(
                f'      <tr>'
                f'<td>{_esc(d.get("decision_id", ""))}</td>'
                f'<td><span class="badge badge-{severity_lower}">{_esc(d.get("severity", ""))}</span></td>'
                f'<td>{_esc(d.get("summary", ""))}</td>'
                f'<td>{status_badge}</td>'
                f'</tr>'
            )
        lines.append('    </tbody>')
        lines.append('  </table>')

        for d in dlist:
            options = d.get("options", [])
            if options:
                lines.append(
                    f'  <div class="callout info">'
                    f'<p><strong>{_esc(d.get("decision_id", ""))}</strong> options:</p>'
                )
                lines.append('  <ul style="margin:0.25rem 0 0 1.25rem;">')
                for opt in options:
                    if isinstance(opt, dict):
                        opt_label = opt.get("label", opt.get("id", ""))
                        opt_impact = opt.get("impact", "")
                        lines.append(f'    <li>{_esc(opt_label)}: {_esc(opt_impact)}</li>')
                lines.append('  </ul></div>')

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. CSS / Partition Analysis
# ---------------------------------------------------------------------------

def _css_partition_analysis(store: MigrationStore) -> str:
    """Indented list topology: CSS -> partitions via cross-refs."""
    css_refs = store.get_cross_refs(relationship="css_contains_partition")
    if not css_refs:
        return ""

    css_map: dict[str, list[tuple[int | None, str]]] = defaultdict(list)
    for ref in css_refs:
        css_map[ref["from_id"]].append((ref.get("ordinal"), ref["to_id"]))

    for css_id in css_map:
        css_map[css_id].sort(key=lambda x: (x[0] if x[0] is not None else 999))

    lines = [
        '<details open id="css-analysis">',
        '  <summary>CSS / Partition Analysis</summary>',
        '  <p>Calling Search Spaces define the dialing scope for users and devices. '
        'Each CSS contains an ordered list of partitions that determine which '
        'patterns a caller can reach.</p>',
        '  <div class="css-topology">',
        '  <ul>',
    ]

    for css_id in sorted(css_map.keys()):
        css_name = css_id.replace("css:", "")
        partitions = css_map[css_id]
        pt_names = [pt_id.replace("partition:", "") for _, pt_id in partitions]
        lines.append(f'    <li><span class="css-name">{_esc(css_name)}</span>')
        lines.append('      <ul class="pt-list">')
        for pt_name in pt_names:
            lines.append(f'        <li>{_esc(pt_name)}</li>')
        lines.append('      </ul>')
        lines.append('    </li>')

    lines.append('  </ul>')
    lines.append('  </div>')

    total_css = len(css_map)
    all_partitions = set()
    for pts in css_map.values():
        for _, pt_id in pts:
            all_partitions.add(pt_id)
    lines.append(
        f'  <p class="muted small">{total_css} CSS(es) referencing {len(all_partitions)} '
        f'unique partition(s).</p>'
    )

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Device Inventory
# ---------------------------------------------------------------------------

def _device_inventory(store: MigrationStore) -> str:
    """Full phone model list grouped by compatibility tier."""
    devices = store.get_objects("device")
    if not devices:
        return ""

    by_tier: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for d in devices:
        tier = d.get("compatibility_tier", "unknown")
        model = d.get("model", "Unknown")
        by_tier[tier][model] += 1

    tier_order = ["native_mpp", "convertible", "incompatible"]
    ordered_tiers = [t for t in tier_order if t in by_tier]
    for t in sorted(by_tier.keys()):
        if t not in ordered_tiers:
            ordered_tiers.append(t)

    lines = [
        '<details open id="device-detail">',
        '  <summary>Device Inventory</summary>',
        '  <table>',
        '    <thead><tr>'
        '<th>Compatibility</th><th>Model</th><th>Count</th><th>Action</th>'
        '</tr></thead>',
        '    <tbody>',
    ]

    for tier in ordered_tiers:
        tier_label = _TIER_LABELS.get(tier, tier.replace("_", " ").title())
        guidance = _TIER_GUIDANCE.get(tier, "Review required.")

        badge_class = "badge-direct"
        if tier == "convertible":
            badge_class = "badge-approx"
        elif tier == "incompatible":
            badge_class = "badge-decision"

        models = by_tier[tier]
        for model, count in sorted(models.items()):
            lines.append(
                f'      <tr>'
                f'<td><span class="badge {badge_class}">{_esc(tier_label)}</span></td>'
                f'<td>{_esc(model)}</td>'
                f'<td>{count}</td>'
                f'<td>{_esc(guidance)}</td>'
                f'</tr>'
            )

    lines.append('    </tbody>')
    lines.append('  </table>')

    total = sum(sum(m.values()) for m in by_tier.values())
    lines.append(f'  <p class="muted small">{total} total device(s).</p>')

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. DN Analysis
# ---------------------------------------------------------------------------

def _dn_analysis(store: MigrationStore) -> str:
    """E.164 classification breakdown from line objects."""
    lines_data = store.get_objects("line")
    if not lines_data:
        return ""

    by_class: dict[str, int] = defaultdict(int)
    for ln in lines_data:
        classification = ln.get("classification", "UNKNOWN")
        by_class[classification] += 1

    lines = [
        '<details open id="dn-analysis">',
        '  <summary>DN Analysis</summary>',
        '  <table>',
        '    <thead><tr><th>Classification</th><th>Count</th></tr></thead>',
        '    <tbody>',
    ]
    for cls_name, count in sorted(by_class.items()):
        lines.append(f'      <tr><td>{_esc(cls_name)}</td><td>{count}</td></tr>')
    lines.append('    </tbody>')
    lines.append('  </table>')
    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. User-Device-Line Map
# ---------------------------------------------------------------------------

def _user_device_line_map(store: MigrationStore) -> str:
    """Cross-ref chains: user -> device -> DN -> partition."""
    user_device_refs = store.get_cross_refs(relationship="user_has_device")
    if not user_device_refs:
        return ""

    lines = [
        '<details open id="user-device-map">',
        '  <summary>User / Device / Line Map</summary>',
        '  <table>',
        '    <thead><tr><th>User</th><th>Device</th><th>DN</th><th>Partition</th></tr></thead>',
        '    <tbody>',
    ]

    for ref in user_device_refs:
        user_id = ref["from_id"]
        device_id = ref["to_id"]

        user_obj = store.get_object(user_id)
        user_label = user_id
        if user_obj:
            first = user_obj.get("first_name", "")
            last = user_obj.get("last_name", "")
            user_label = f"{first} {last}".strip() or user_id

        device_obj = store.get_object(device_id)
        device_label = device_id
        if device_obj:
            device_label = device_obj.get("model", device_id)

        dn_refs = store.get_cross_refs(from_id=device_id, relationship="device_has_dn")
        if dn_refs:
            for dn_ref in dn_refs:
                dn_id = dn_ref["to_id"]
                dn_obj = store.get_object(dn_id)
                dn_label = dn_id
                if dn_obj:
                    dn_label = dn_obj.get("cucm_pattern", dn_obj.get("extension", dn_id))

                pt_refs = store.get_cross_refs(from_id=dn_id, relationship="dn_in_partition")
                pt_label = ""
                if pt_refs:
                    pt_id = pt_refs[0]["to_id"]
                    pt_label = pt_id.replace("partition:", "")

                lines.append(
                    f'      <tr>'
                    f'<td>{_esc(user_label)}</td>'
                    f'<td>{_esc(device_label)}</td>'
                    f'<td>{_esc(dn_label)}</td>'
                    f'<td>{_esc(pt_label)}</td>'
                    f'</tr>'
                )
        else:
            lines.append(
                f'      <tr>'
                f'<td>{_esc(user_label)}</td>'
                f'<td>{_esc(device_label)}</td>'
                f'<td>-</td><td>-</td>'
                f'</tr>'
            )

    lines.append('    </tbody>')
    lines.append('  </table>')
    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. Routing Topology
# ---------------------------------------------------------------------------

def _routing_topology(store: MigrationStore) -> str:
    """Trunk, route group, and dial plan inventory tables."""
    trunks = store.get_objects("trunk")
    route_groups = store.get_objects("route_group")
    dial_plans = store.get_objects("dial_plan")

    if not trunks and not route_groups and not dial_plans:
        return ""

    lines = [
        '<details open id="routing">',
        '  <summary>Routing Topology</summary>',
    ]

    if trunks:
        lines.append('  <h4>Trunks</h4>')
        lines.append('  <table>')
        lines.append(
            '    <thead><tr><th>Name</th><th>Type</th><th>Security</th>'
            '<th>Early Offer</th><th>Location</th></tr></thead>'
        )
        lines.append('    <tbody>')
        for t in trunks:
            name = t.get("name", t.get("canonical_id", ""))
            trunk_type = t.get("trunk_type", "")
            loc_id = t.get("location_id", "")
            loc_name = _resolve_location_name(store, loc_id) if loc_id else ""
            security = t.get("security_mode", "")
            early_offer = "Yes" if t.get("sip_profile_early_offer") else ""
            lines.append(
                f'      <tr><td>{_esc(name)}</td>'
                f'<td>{_esc(trunk_type)}</td>'
                f'<td>{_esc(security)}</td>'
                f'<td>{_esc(early_offer)}</td>'
                f'<td>{_esc(loc_name)}</td></tr>'
            )
        lines.append('    </tbody>')
        lines.append('  </table>')

    if route_groups:
        lines.append('  <h4>Route Groups</h4>')
        lines.append('  <table>')
        lines.append('    <thead><tr><th>Name</th></tr></thead>')
        lines.append('    <tbody>')
        for rg in route_groups:
            name = rg.get("name", rg.get("canonical_id", ""))
            lines.append(f'      <tr><td>{_esc(name)}</td></tr>')
        lines.append('    </tbody>')
        lines.append('  </table>')

    if dial_plans:
        lines.append('  <h4>Dial Plans</h4>')
        lines.append('  <table>')
        lines.append(
            '    <thead><tr><th>Name</th><th>Patterns</th></tr></thead>'
        )
        lines.append('    <tbody>')
        for dp in dial_plans:
            name = dp.get("name", dp.get("canonical_id", ""))
            patterns = dp.get("dial_patterns", [])
            pattern_str = ", ".join(str(p) for p in patterns) if patterns else "-"
            lines.append(
                f'      <tr><td>{_esc(name)}</td>'
                f'<td>{_esc(pattern_str)}</td></tr>'
            )
        lines.append('    </tbody>')
        lines.append('  </table>')

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. Voicemail Analysis
# ---------------------------------------------------------------------------

def _voicemail_analysis(store: MigrationStore) -> str:
    """Voicemail profile mapping and incompatibility decisions."""
    vm_profiles = store.get_objects("voicemail_profile")
    decisions = store.get_all_decisions()
    vm_decisions = [d for d in decisions if d.get("type") == "VOICEMAIL_INCOMPATIBLE"]

    if not vm_profiles and not vm_decisions:
        return ""

    lines = [
        '<details open id="voicemail">',
        '  <summary>Voicemail Analysis</summary>',
    ]

    if vm_profiles:
        lines.append('  <h4>Voicemail Profiles</h4>')
        lines.append('  <table>')
        lines.append('    <thead><tr><th>Name</th></tr></thead>')
        lines.append('    <tbody>')
        for vp in vm_profiles:
            name = vp.get("name", vp.get("canonical_id", ""))
            lines.append(f'      <tr><td>{_esc(name)}</td></tr>')
        lines.append('    </tbody>')
        lines.append('  </table>')

    if vm_decisions:
        lines.append('  <h4>Voicemail Incompatibilities</h4>')
        for d in vm_decisions:
            lines.append(
                f'  <div class="callout critical">'
                f'<p>{_esc(d.get("summary", ""))}</p>'
                f'  </div>'
            )

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 9. Call Forwarding Summary
# ---------------------------------------------------------------------------

def _call_forwarding_summary(store: MigrationStore) -> str:
    """Call forwarding configuration summary."""
    cf_objects = store.get_objects("call_forwarding")
    if not cf_objects:
        return ""

    total = len(cf_objects)
    cfa_active = sum(1 for cf in cf_objects if cf.get("always_enabled"))
    cfb_active = sum(1 for cf in cf_objects if cf.get("busy_enabled"))
    cfna_active = sum(1 for cf in cf_objects if cf.get("no_answer_enabled"))

    # CUCM-only lossy variants
    lossy_fields = [
        "busy_internal_enabled", "no_answer_internal_enabled",
        "no_coverage_enabled", "on_failure_enabled", "not_registered_enabled",
    ]
    lossy_count = sum(
        1 for cf in cf_objects
        if any(cf.get(f) for f in lossy_fields)
    )

    lines = [
        '<details open id="call-forwarding">',
        '  <summary>Call Forwarding</summary>',
        '  <table>',
        '    <thead><tr><th>Setting</th><th>Active Users</th></tr></thead>',
        '    <tbody>',
        f'      <tr><td>Call Forward All (CFA)</td><td>{cfa_active}</td></tr>',
        f'      <tr><td>Call Forward Busy (CFB)</td><td>{cfb_active}</td></tr>',
        f'      <tr><td>Call Forward No Answer (CFNA)</td><td>{cfna_active}</td></tr>',
        f'      <tr><td>CUCM-only variants (lossy)</td><td>{lossy_count}</td></tr>',
        '    </tbody>',
        '  </table>',
        f'  <p>Total users with call forwarding configured: {total}</p>',
    ]

    if lossy_count > 0:
        lines.append(
            '  <div class="callout info"><p>'
            f'{lossy_count} user(s) use CUCM-only forwarding variants '
            '(BusyInt, NoAnswerInt, NoCoverage, OnFailure, NotRegistered) '
            'that have no Webex equivalent. These are captured as '
            'FORWARDING_LOSSY decisions.'
            '</p></div>'
        )

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 10. Speed Dials & Monitoring
# ---------------------------------------------------------------------------

def _speed_dials_monitoring(store: MigrationStore) -> str:
    """BLF monitoring lists and speed dial summary."""
    ml_objects = store.get_objects("monitoring_list")
    # Speed dials are in phone metadata, not a separate type
    phones = store.get_objects("phone")

    phones_with_sd = 0
    total_sd = 0
    for phone in phones:
        state = phone.get("pre_migration_state") or {}
        sd = state.get("speeddials")
        if sd:
            entries = sd.get("speeddial", []) if isinstance(sd, dict) else sd
            if isinstance(entries, list) and entries:
                phones_with_sd += 1
                total_sd += len(entries)

    if not ml_objects and phones_with_sd == 0:
        return ""

    lines = [
        '<details open id="monitoring">',
        '  <summary>Speed Dials &amp; Monitoring</summary>',
    ]

    if ml_objects:
        total_members = sum(len(ml.get("monitored_members", [])) for ml in ml_objects)
        unresolved = sum(
            1 for ml in ml_objects
            for m in ml.get("monitored_members", [])
            if m.get("target_canonical_id") is None
        )
        lines.extend([
            '  <h4>BLF / Monitoring Lists</h4>',
            '  <table>',
            '    <thead><tr><th>Metric</th><th>Count</th></tr></thead>',
            '    <tbody>',
            f'      <tr><td>Users with monitoring list</td><td>{len(ml_objects)}</td></tr>',
            f'      <tr><td>Total monitored members</td><td>{total_members}</td></tr>',
            f'      <tr><td>Unresolvable BLF targets</td><td>{unresolved}</td></tr>',
            '    </tbody>',
            '  </table>',
        ])

    if phones_with_sd > 0:
        lines.extend([
            '  <h4>Speed Dials</h4>',
            f'  <p>{phones_with_sd} phone(s) with {total_sd} speed dial entries total. '
            'Speed dials are not migrated automatically — users configure these in Webex.</p>',
        ])

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 11. Data Coverage
# ---------------------------------------------------------------------------

def _data_coverage(store: MigrationStore) -> str:
    """Report on data collection coverage from the journal table."""
    journal_count = store.get_journal_count()

    error_count = 0
    if journal_count > 0:
        error_count = store.get_journal_count(entry_type="error")

    lines = [
        '<details open id="coverage">',
        '  <summary>Data Coverage</summary>',
    ]

    if journal_count == 0:
        lines.append(
            '  <div class="callout success">'
            '<p>Data collected via live AXL extraction. '
            'No collection errors recorded.</p></div>'
        )
    else:
        lines.append(f'  <p>{journal_count} journal entries recorded.</p>')
        if error_count > 0:
            lines.append(
                f'  <div class="callout critical">'
                f'<p><strong>{error_count} error(s)</strong> during collection:</p>'
            )
            error_entries = store.get_journal_entries(entry_type="error", limit=50)
            lines.append('  <ul style="margin:0.25rem 0 0 1.25rem;">')
            for entry in error_entries:
                lines.append(
                    f'    <li>{_esc(entry["resource_type"])}: '
                    f'{_esc(entry["canonical_id"])} — '
                    f'{_esc(entry.get("response") or "no details")}</li>'
                )
            lines.append('  </ul></div>')
        else:
            lines.append(
                '  <div class="callout success">'
                '<p>No collection errors recorded.</p></div>'
            )

    lines.append('</details>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text)) if text else ""


def _resolve_location_name(store: MigrationStore, location_id: str) -> str:
    """Look up a location name by canonical_id."""
    obj = store.get_object(location_id)
    if obj:
        return obj.get("name", location_id)
    return location_id
