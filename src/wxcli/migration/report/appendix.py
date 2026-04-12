"""Technical appendix HTML generator for CUCM assessment reports (v4).

Generates 30 lettered sections (A-AE), each as a collapsed <details> element:
A. Object Inventory, B. Decision Detail, C. CSS/Partitions, D. Device Inventory,
E. DN Analysis, F. User/Device Map, G. Routing Topology, H. Voicemail Analysis,
I. Audio Assets, J. Data Coverage, K. Gateways, L. Call Features,
M. Button Templates, N. Device Layouts, O. Softkey Migration,
P. Cloud-Managed Resources, Q. Feature Gaps, R. Manual Reconfiguration,
S. Planning Inputs, T. Call Recording, U. Single Number Reach,
V. Caller ID Transformations, W. Extension Mobility, X. DECT Networks,
Y. Intercept Candidates, Z. Executive/Assistant Pairings, AA. Receptionist Users,
AB. Selective Call Handling, AC. Device Settings Coverage,
AD. Feature Forwarding Status, AE. Workspace Settings Coverage.

One public function: generate_appendix().
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any


def _axl_str(value: Any) -> str:
    """Coerce an AXL field value to a plain string.

    AXL returns some reference fields (e.g. routePartitionName) as a dict
    with a ``_value_1`` key and a ``uuid`` key rather than a bare string.
    Extract the human-readable value; fall back to empty string for None/missing.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("_value_1", ""))
    return str(value)

from wxcli.migration.report.charts import stacked_bar_chart
from wxcli.migration.report.explainer import (
    DECISION_TYPE_DISPLAY_NAMES,
    explain_decision,
)
from wxcli.migration.report.helpers import friendly_site_name, strip_canonical_id
from wxcli.migration.store import MigrationStore
from wxcli.migration.cucm.extractors.informational import (
    DISPLAY_NAMES,
    NOT_MIGRATABLE_WORKAROUNDS,
    WEBEX_EQUIVALENTS,
)


def generate_appendix(store: MigrationStore) -> str:
    """Generate the technical appendix HTML with lettered A-X sections."""
    sections = [
        ("A", _object_inventory(store)),
        ("B", _decisions_group(store)),
        ("E911", _e911_readiness(store)),
        ("C", _css_partitions(store)),
        ("D", _device_inventory(store)),
        ("E", _dn_analysis(store)),
        ("F", _user_device_map(store)),
        ("G", _routing_group(store)),
        ("H", _voicemail_analysis(store)),
        ("I", _audio_assets(store)),
        ("J", _data_quality_group(store)),
        ("K", _gateways_group(store)),
        ("L", _features_group(store)),
        ("M", _button_template_group(store)),
        ("N", _device_layout_group(store)),
        ("O", _softkey_group(store)),
        ("P", _cloud_managed_group(store)),
        ("Q", _feature_gaps_group(store)),
        ("R", _manual_reconfig_group(store)),
        ("S", _planning_inputs_group(store)),
        ("T", _recording_inventory(store)),
        ("U", _snr_inventory(store)),
        ("V", _caller_id_xforms(store)),
        ("W", _extension_mobility_group(store)),
        ("X", _dect_networks_group(store)),
        ("Y", _intercept_candidates(store)),
        ("Z", _executive_assistant_group(store)),
        ("AA", _receptionist_group(store)),
        ("AB", _selective_call_handling(store)),
        ("AC", _device_settings_coverage(store)),
        ("AD", _feature_forwarding_status(store)),
        ("AE", _workspace_settings_coverage(store)),
    ]
    # Filter out empty sections
    sections = [(letter, section_html) for letter, section_html in sections if section_html]
    if not sections:
        return '<section id="appendix"></section>'

    return (
        '<section id="appendix">\n'
        + "\n".join(section_html for _, section_html in sections)
        + "\n</section>"
    )


# ---------------------------------------------------------------------------
# A. Object Inventory
# ---------------------------------------------------------------------------

def _object_inventory(store: MigrationStore) -> str:
    """A. Object Inventory — total counts by type."""
    object_types = [
        "user", "device", "line", "shared_line", "location",
        "hunt_group", "call_queue", "auto_attendant", "call_park",
        "pickup_group", "paging_group", "trunk", "route_group",
        "css", "partition", "translation_pattern", "voicemail_profile",
        "schedule", "gateway", "workspace", "virtual_line",
        "line_key_template", "device_layout", "softkey_config",
    ]
    rows = []
    total = 0
    for ot in object_types:
        count = store.count_by_type(ot)
        if count > 0:
            display = ot.replace("_", " ").title()
            rows.append((display, count))
            total += count

    if not rows:
        return ""

    parts = [
        f'<details id="objects">',
        f'<summary>A. Object Inventory <span class="summary-count">— {total} objects across {len(rows)} types</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Object Type</th><th class="num">Count</th></tr></thead>',
        '<tbody>',
    ]
    for display, count in rows:
        parts.append(f'<tr><td>{html.escape(display)}</td><td class="num">{count}</td></tr>')
    parts.append('</tbody></table>')

    # By-location breakdown
    locations = store.get_objects("location")
    if locations:
        parts.append('<h4>By Location</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Location</th><th class="num">Users</th><th class="num">Devices</th></tr></thead>')
        parts.append('<tbody>')
        all_users = store.get_objects("user")
        all_devices = store.get_objects("device")
        for loc in locations:
            loc_id = loc.get("canonical_id", "")
            loc_name = loc.get("name", "")
            if not loc_name:
                loc_name = strip_canonical_id(loc_id)
            friendly = friendly_site_name(loc_name) if loc_name.startswith("DP-") else loc_name
            u_count = sum(1 for u in all_users if u.get("location_id") == loc_id)
            loc_user_ids = {u.get("canonical_id") for u in all_users if u.get("location_id") == loc_id}
            d_count = sum(1 for d in all_devices if d.get("owner_canonical_id") in loc_user_ids)
            parts.append(f'<tr><td>{html.escape(friendly)}</td><td class="num">{u_count}</td><td class="num">{d_count}</td></tr>')
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# B. Decision Detail
# ---------------------------------------------------------------------------

def _decisions_group(store: MigrationStore) -> str:
    """B. Decisions grouped by type with aggregated counts."""
    decisions = store.get_all_decisions()
    if not decisions:
        return ""

    total = len(decisions)
    resolved = sum(1 for d in decisions if d.get("chosen_option"))

    # Group by type
    by_type: dict[str, list[dict]] = defaultdict(list)
    for d in decisions:
        by_type[d.get("type", "UNKNOWN")].append(d)

    parts = [
        f'<details id="decision-detail">',
        f'<summary>B. Decision Detail <span class="summary-count">— {total} total, {resolved} auto-resolved</span></summary>',
        '<div class="details-content">',
    ]

    for dtype in sorted(by_type.keys()):
        type_decisions = by_type[dtype]
        display_name = DECISION_TYPE_DISPLAY_NAMES.get(dtype, dtype.replace("_", " ").title())
        type_resolved = sum(1 for d in type_decisions if d.get("chosen_option"))
        resolution = f"{type_resolved}/{len(type_decisions)} resolved"

        parts.append(f'<div class="explanation">')
        parts.append(f'<h4>{html.escape(display_name)} ({len(type_decisions)}) <span class="muted small">— {resolution}</span></h4>')

        # Show explainer for the type
        sample = type_decisions[0]
        explained = explain_decision(
            decision_type=sample["type"],
            severity=sample.get("severity", "MEDIUM"),
            summary=sample.get("summary", ""),
            context=sample.get("context", {}),
        )
        parts.append(f'<p>{explained["explanation"]}</p>')
        parts.append(f'<p class="reassurance">{explained["reassurance"]}</p>')

        # Summary table if more than 1
        if len(type_decisions) > 1:
            parts.append('<table>')
            parts.append('<thead><tr><th>Summary</th><th>Severity</th><th>Status</th></tr></thead>')
            parts.append('<tbody>')
            for d in type_decisions:
                severity = d.get("severity", "MEDIUM")
                status = "Auto-resolved" if d.get("chosen_option") else "Pending"
                parts.append(
                    f'<tr><td>{html.escape(d.get("summary", ""))}</td>'
                    f'<td><span class="badge badge-{severity.lower()}">{html.escape(severity)}</span></td>'
                    f'<td>{status}</td></tr>'
                )
            parts.append('</tbody></table>')

        parts.append('</div>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# E911 Readiness (appendix placement after Decision Detail)
# ---------------------------------------------------------------------------

def _e911_readiness(store: MigrationStore) -> str:
    """E911 Readiness appendix section — ECBN auto-config counts + decision counts."""
    ecbn_configs = store.get_objects("ecbn_config")
    direct_line = [c for c in ecbn_configs if c.get("ecbn_selection") == "DIRECT_LINE"]
    location_ecbn = [c for c in ecbn_configs if c.get("ecbn_selection") == "LOCATION_ECBN"]

    ambiguous = 0
    mismatch = 0
    for d in store.get_all_decisions():
        if d.get("chosen_option") == "__stale__":
            continue
        t = d.get("type", "")
        if t == "E911_ECBN_AMBIGUOUS":
            ambiguous += 1
        elif t == "E911_LOCATION_MISMATCH":
            mismatch += 1

    # Skip section entirely when there is nothing to report.
    if not ecbn_configs and ambiguous == 0 and mismatch == 0:
        return ""

    if not ecbn_configs:
        status_label = "SKIP"
        status_class = "badge-info"
    elif ambiguous == 0 and mismatch == 0 and len(location_ecbn) == 0:
        status_label = "PASS"
        status_class = "badge-success"
    elif ambiguous == 0 and mismatch == 0:
        status_label = "WARN"
        status_class = "badge-warning"
    else:
        status_label = "REVIEW"
        status_class = "badge-warning"

    rows = [
        ("Users with DID (auto-ECBN / DIRECT_LINE)", len(direct_line)),
        ("Extension-only users (LOCATION_ECBN)", len(location_ecbn)),
        ("Ambiguous ECBN (multi-DID) decisions", ambiguous),
        ("Location-mismatch decisions", mismatch),
    ]

    row_html = "\n".join(
        f"<tr><td>{label}</td><td>{count}</td></tr>"
        for label, count in rows
    )

    return f"""
<details id="appendix-e911-readiness">
  <summary><strong>E911 Readiness</strong> <span class="badge {status_class}">{status_label}</span></summary>
  <p>Emergency Callback Number (ECBN) breakdown. Kari's Law and RAY BAUM's Act require that every user has a valid ECBN before dialing 911.</p>
  <table class="data-table">
    <thead>
      <tr><th>Metric</th><th>Count</th></tr>
    </thead>
    <tbody>
      {row_html}
    </tbody>
  </table>
</details>
"""


# ---------------------------------------------------------------------------
# C. CSS / Partitions
# ---------------------------------------------------------------------------

def _css_partitions(store: MigrationStore) -> str:
    """C. CSS / Partition topology."""
    css_count = store.count_by_type("css")
    pt_count = store.count_by_type("partition")
    if css_count == 0 and pt_count == 0:
        return ""

    parts = [
        f'<details id="css-partitions">',
        f'<summary>C. CSS / Partitions <span class="summary-count">— {css_count} CSSes, {pt_count} partitions</span></summary>',
        '<div class="details-content">',
    ]

    css_objects = store.get_objects("css")
    if css_objects:
        parts.append('<ul class="css-topology">')
        for css in css_objects:
            css_id = css.get("canonical_id", "")
            css_name = strip_canonical_id(css_id)
            parts.append(f'<li>{html.escape(css_name)}')
            css_pt_refs = store.get_cross_refs(
                relationship="css_contains_partition",
                from_id=css_id,
            )
            if css_pt_refs:
                for ref in sorted(css_pt_refs, key=lambda r: r.get("ordinal", 0)):
                    pt_name = strip_canonical_id(ref.get("to_id", ""))
                    parts.append(f'<li class="partition">{html.escape(pt_name)}</li>')
            parts.append('</li>')
        parts.append('</ul>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# D. Device Inventory
# ---------------------------------------------------------------------------

def _device_inventory(store: MigrationStore) -> str:
    """D. Device Inventory — by model with stacked bar chart."""
    devices = store.get_objects("device")
    if not devices:
        return ""

    total = len(devices)

    # Count by model
    model_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for d in devices:
        model = d.get("model", "Unknown")
        tier = d.get("compatibility_tier", "unknown")
        if hasattr(tier, "value"):
            tier = tier.value
        model_counts[model][str(tier)] += 1

    native = sum(1 for d in devices if d.get("compatibility_tier") == "native_mpp")
    convertible = sum(1 for d in devices if d.get("compatibility_tier") == "convertible")
    webex_app = sum(1 for d in devices if d.get("compatibility_tier") == "webex_app")
    infrastructure = sum(1 for d in devices if d.get("compatibility_tier") == "infrastructure")
    incompatible = sum(1 for d in devices if d.get("compatibility_tier") == "incompatible")
    dect = sum(1 for d in devices if d.get("compatibility_tier") == "dect")

    summary_parts = [f"{total} phones"]
    if native:
        summary_parts.append(f"{native} native")
    if convertible:
        summary_parts.append(f"{convertible} convertible")
    if webex_app:
        summary_parts.append(f"{webex_app} Webex App")
    if infrastructure:
        summary_parts.append(f"{infrastructure} infrastructure")
    if incompatible:
        summary_parts.append(f"{incompatible} incompatible")
    if dect:
        summary_parts.append(f"{dect} DECT")
    summary = " — ".join(summary_parts[:1]) + " — " + ", ".join(summary_parts[1:])

    parts = [
        f'<details id="device-detail">',
        f'<summary>D. Device Inventory <span class="summary-count">— {summary}</span></summary>',
        '<div class="details-content">',
        '<h4>Device Inventory by Model</h4>',
        '<table>',
        '<thead><tr><th>Model</th><th class="num">Count</th><th>Compatibility</th></tr></thead>',
        '<tbody>',
    ]

    for model in sorted(model_counts.keys()):
        tiers = model_counts[model]
        total_model = sum(tiers.values())
        tier_list = []
        _TIER_DISPLAY = {
            "native_mpp": "Native MPP",
            "convertible": "Convertible",
            "webex_app": "Webex App",
            "infrastructure": "Infrastructure (not migrated)",
            "incompatible": "Incompatible",
            "dect": "DECT (wireless)",
        }
        for tier_name in ["native_mpp", "convertible", "webex_app", "infrastructure", "incompatible", "dect"]:
            if tiers.get(tier_name, 0) > 0:
                tier_list.append(f'{_TIER_DISPLAY.get(tier_name, tier_name)}: {tiers[tier_name]}')
        tier_str = ", ".join(tier_list) if tier_list else "Unknown"

        parts.append(
            f'<tr><td>{html.escape(model)}</td>'
            f'<td class="num">{total_model}</td>'
            f'<td>{html.escape(tier_str)}</td></tr>'
        )

    parts.append('</tbody></table>')

    # Stacked bar chart for device compatibility
    segments = [
        {"label": "Native MPP", "value": native, "color": "#2E7D32"},
        {"label": "Convertible", "value": convertible, "color": "#EF6C00"},
        {"label": "Incompatible", "value": incompatible, "color": "#C62828"},
    ]
    if dect:
        segments.append({"label": "DECT", "value": dect, "color": "#42A5F5"})
    bar_html = stacked_bar_chart(segments)
    if bar_html:
        parts.append(bar_html)

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# E. DN Analysis
# ---------------------------------------------------------------------------

def _dn_analysis(store: MigrationStore) -> str:
    """E. DN Analysis — extension classification breakdown."""
    lines = store.get_objects("line")
    if not lines:
        return ""

    classification_counts: dict[str, int] = defaultdict(int)
    for line in lines:
        cls = line.get("classification", "UNKNOWN")
        if hasattr(cls, "value"):
            cls = cls.value
        classification_counts[str(cls)] += 1

    parts = [
        f'<details id="dn-analysis">',
        f'<summary>E. DN Analysis <span class="summary-count">— {len(lines)} extensions</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Classification</th><th class="num">Count</th></tr></thead>',
        '<tbody>',
    ]
    for cls, count in sorted(classification_counts.items(), key=lambda x: -x[1]):
        parts.append(f'<tr><td>{html.escape(cls)}</td><td class="num">{count}</td></tr>')
    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# F. User/Device Map
# ---------------------------------------------------------------------------

def _user_device_map(store: MigrationStore) -> str:
    """F. User/Device Map — user-device-line assignments."""
    user_device_refs = store.get_cross_refs(relationship="user_has_device")
    if not user_device_refs:
        return ""

    parts = [
        f'<details id="user-device-map">',
        f'<summary>F. User/Device Map <span class="summary-count">— {len(user_device_refs)} assignments</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>User</th><th>Device</th><th>Model</th><th>Line</th><th>Partition</th></tr></thead>',
        '<tbody>',
    ]

    for ref in user_device_refs:
        user_id = ref.get("from_id", "")
        device_id = ref.get("to_id", "")

        user_obj = store.get_object(user_id)
        device_obj = store.get_object(device_id)

        user_name = ""
        if user_obj:
            first = user_obj.get("first_name", "")
            last = user_obj.get("last_name", "")
            user_name = f"{first} {last}".strip() or strip_canonical_id(user_id)
        else:
            user_name = strip_canonical_id(user_id)

        model = device_obj.get("model", "") if device_obj else ""

        device_line_refs = store.get_cross_refs(
            relationship="device_has_dn", from_id=device_id,
        )

        if device_line_refs:
            for dl_ref in device_line_refs:
                line_id = dl_ref.get("to_id", "")
                line_obj = store.get_object(line_id)
                line_ext = ""
                partition = ""
                if line_obj:
                    line_ext = line_obj.get("extension", "") or line_obj.get("cucm_pattern", "")
                    partition = line_obj.get("route_partition_name", "")
                if not partition:
                    dn_pt_refs = store.get_cross_refs(
                        relationship="dn_in_partition", from_id=line_id,
                    )
                    if dn_pt_refs:
                        partition = strip_canonical_id(dn_pt_refs[0].get("to_id", ""))
                parts.append(
                    f'<tr><td>{html.escape(user_name)}</td>'
                    f'<td>{html.escape(strip_canonical_id(device_id))}</td>'
                    f'<td>{html.escape(model)}</td>'
                    f'<td>{html.escape(line_ext)}</td>'
                    f'<td>{html.escape(partition)}</td></tr>'
                )
        else:
            parts.append(
                f'<tr><td>{html.escape(user_name)}</td>'
                f'<td>{html.escape(strip_canonical_id(device_id))}</td>'
                f'<td>{html.escape(model)}</td>'
                f'<td>—</td><td>—</td></tr>'
            )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# G. Routing Topology
# ---------------------------------------------------------------------------

def _routing_group(store: MigrationStore) -> str:
    """G. Routing — trunks and route groups (CSS/partition topology in Section C)."""
    trunk_count = store.count_by_type("trunk")
    rg_count = store.count_by_type("route_group")
    dp_count = store.count_by_type("dial_plan")
    tp_count = store.count_by_type("translation_pattern")

    total = trunk_count + rg_count + dp_count + tp_count
    if total == 0:
        return ""

    summary_parts = []
    if trunk_count:
        summary_parts.append(f"{trunk_count} trunks")
    if rg_count:
        summary_parts.append(f"{rg_count} route groups")
    if dp_count:
        summary_parts.append(f"{dp_count} dial plans")
    if tp_count:
        summary_parts.append(f"{tp_count} translation patterns")

    parts = [
        f'<details id="routing">',
        f'<summary>G. Routing Topology <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
        '<div class="details-content">',
    ]

    # Trunks
    trunks = store.get_objects("trunk")
    if trunks:
        parts.append('<h4>Trunks</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Name</th><th>Type</th><th>Location</th></tr></thead>')
        parts.append('<tbody>')
        for t in trunks:
            name = t.get("name", strip_canonical_id(t.get("canonical_id", "")))
            trunk_type = t.get("trunk_type", "—")
            loc_id = t.get("location_id", "")
            loc_obj = store.get_object(loc_id) if loc_id else None
            loc_name = loc_obj.get("name", strip_canonical_id(loc_id)) if loc_obj else "—"
            parts.append(
                f'<tr><td>{html.escape(name)}</td>'
                f'<td>{html.escape(str(trunk_type))}</td>'
                f'<td>{html.escape(loc_name)}</td></tr>'
            )
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# H. Voicemail Analysis
# ---------------------------------------------------------------------------

def _voicemail_analysis(store: MigrationStore) -> str:
    """H. Voicemail Analysis — voicemail profiles + custom greeting count."""
    profiles = store.get_objects("voicemail_profile")
    if not profiles:
        return ""

    # Count custom greeting decisions
    decisions = store.get_all_decisions()
    greeting_count = 0
    for d in decisions:
        if d.get("type") != "MISSING_DATA":
            continue
        ctx = d.get("context", {})
        if ctx.get("reason") == "custom_greeting_not_extractable":
            greeting_count += 1

    parts = [
        '<details id="voicemail">',
        f'<summary>H. Voicemail Analysis <span class="summary-count">— {len(profiles)} profiles</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Profile</th><th>Description</th></tr></thead>',
        '<tbody>',
    ]
    for p in profiles:
        name = p.get("name", strip_canonical_id(p.get("canonical_id", "")))
        desc = p.get("description", "—")
        parts.append(f'<tr><td>{html.escape(name)}</td><td>{html.escape(str(desc))}</td></tr>')
    parts.append('</tbody></table>')

    if greeting_count > 0:
        parts.append(
            f'<div class="callout warning">'
            f'<p><strong>Custom Greetings: {greeting_count} users</strong> have personalized '
            f'voicemail greetings that will revert to the system default after migration. '
            f'Each user must re-record their greeting.</p>'
            f'</div>'
        )
        parts.append(
            '<h4>User Action Required — Voicemail Greeting Re-Recording</h4>'
            '<p>Send the following communication to affected users at least 1 week before migration:</p>'
            '<blockquote>'
            '<p><strong>Subject: Action Required — Re-record Your Voicemail Greeting After Migration</strong></p>'
            '<p>As part of our phone system migration to Webex Calling, your voicemail '
            'greeting will reset to the system default. After the migration is complete, '
            'please re-record your personalized greeting:</p>'
            '<ul>'
            '<li>Open the Webex App</li>'
            '<li>Go to Settings &gt; Calling &gt; Voicemail</li>'
            '<li>Select &quot;Greeting&quot; and record your new greeting</li>'
            '</ul>'
            '<p>Alternatively, dial the voicemail access number from your desk phone and '
            'follow the prompts to record a new greeting.</p>'
            '<p>If you have a script for your greeting, please have it ready before '
            're-recording. We recommend completing this within the first day after migration.</p>'
            '</blockquote>'
        )

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# I. Audio Assets (MoH + Announcements)
# ---------------------------------------------------------------------------

def _audio_assets(store: MigrationStore) -> str:
    """I. Audio Assets — custom MoH sources and announcements."""
    moh_sources = store.get_objects("music_on_hold")
    announcements = store.get_objects("announcement")

    custom_moh = [m for m in moh_sources if not m.get("is_default", False)]

    if not custom_moh and not announcements:
        return ""

    total = len(custom_moh) + len(announcements)
    parts = [
        '<details id="audio-assets">',
        f'<summary>I. Audio Assets <span class="summary-count">— {total} custom audio assets</span></summary>',
        '<div class="details-content">',
        '<div class="callout warning">'
        '<p><strong>Action Required:</strong> Download these files from CUCM '
        'before migration day. MoH and AA greetings are customer-facing — '
        'losing them on cutover is a P1 experience issue.</p>'
        '</div>',
    ]

    if custom_moh:
        parts.append('<h4>Music on Hold Sources</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Source Name</th><th>File Name</th><th>Features Using</th></tr></thead>')
        parts.append('<tbody>')
        for m in custom_moh:
            name = m.get("source_name") or strip_canonical_id(m.get("canonical_id", ""))
            fname = m.get("source_file_name", "\u2014")
            mid = m.get("canonical_id", "")
            refs = store.get_cross_refs(to_id=mid, relationship="feature_uses_moh_source")
            if refs:
                feature_names = [strip_canonical_id(r["from_id"]) for r in refs]
                loc_text = ", ".join(feature_names)
            else:
                loc_text = "\u2014"
            parts.append(
                f'<tr><td>{html.escape(str(name))}</td>'
                f'<td>{html.escape(str(fname))}</td>'
                f'<td>{html.escape(loc_text)}</td></tr>'
            )
        parts.append('</tbody></table>')

    if announcements:
        parts.append('<h4>Announcements</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Name</th><th>File Name</th><th>Type</th></tr></thead>')
        parts.append('<tbody>')
        for a in announcements:
            name = a.get("name") or strip_canonical_id(a.get("canonical_id", ""))
            fname = a.get("file_name", "\u2014")
            media_type = a.get("media_type", "\u2014")
            parts.append(
                f'<tr><td>{html.escape(str(name))}</td>'
                f'<td>{html.escape(str(fname))}</td>'
                f'<td>{html.escape(str(media_type))}</td></tr>'
            )
        parts.append('</tbody></table>')

    parts.append(f'<p><strong>{total} custom audio asset(s)</strong> requiring manual migration.</p>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# J. Data Coverage
# ---------------------------------------------------------------------------

def _data_quality_group(store: MigrationStore) -> str:
    """J. Data coverage and completeness."""
    check_types = [
        "user", "device", "line", "location",
        "hunt_group", "call_queue", "auto_attendant",
        "trunk", "css", "partition",
        "voicemail_profile", "schedule",
    ]

    total_types_checked = len(check_types)
    types_with_data = sum(1 for t in check_types if store.count_by_type(t) > 0)

    if types_with_data == 0:
        return ""

    parts = [
        f'<details id="coverage">',
        f'<summary>J. Data Coverage <span class="summary-count">— {types_with_data}/{total_types_checked} object types populated</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Object Type</th><th class="num">Count</th><th>Status</th></tr></thead>',
        '<tbody>',
    ]

    for t in check_types:
        count = store.count_by_type(t)
        status = "✓" if count > 0 else "—"
        display = t.replace("_", " ").title()
        parts.append(
            f'<tr><td>{html.escape(display)}</td>'
            f'<td class="num">{count}</td>'
            f'<td>{status}</td></tr>'
        )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# K. Gateways & Analog Ports
# ---------------------------------------------------------------------------

# Product model → estimated FXS port count
_ANALOG_PORT_ESTIMATES: dict[str, int] = {
    "ATA 191": 2,
    "ATA 192": 2,
    "VG202": 2,
    "VG204": 4,
    "VG310": 24,
    "VG320": 48,
    "VG350": 48,
    "VG400": 8,
    "VG450": 200,
}

# Products or keywords that indicate analog-capable gateways
_ANALOG_KEYWORDS = ("VG", "ATA", "ISR", "FXS", "FXO", "analog")

# Protocols that need conversion warnings
_UNSUPPORTED_PROTOCOLS = ("MGCP", "H.323", "H323")


def _is_analog_capable(product: str, protocol: str) -> bool:
    """Check if a gateway is analog-capable based on product or protocol."""
    product_upper = (product or "").upper()
    protocol_upper = (protocol or "").upper()
    if protocol_upper in ("MGCP", "H.323", "H323"):
        return True
    return any(kw.upper() in product_upper for kw in _ANALOG_KEYWORDS)


def _estimate_ports(product: str) -> int | None:
    """Estimate FXS port count from product model name."""
    if not product:
        return None
    for model, ports in _ANALOG_PORT_ESTIMATES.items():
        if model.upper() in product.upper():
            return ports
    if "ISR" in product.upper():
        return None
    return None


def _gateways_group(store: MigrationStore) -> str:
    """K. Gateway & analog port review."""
    gateways = store.get_objects("gateway")
    if not gateways:
        return ""

    analog_gws = []
    sip_gws = []
    total_estimated_ports = 0

    for gw in gateways:
        state = gw.get("pre_migration_state", {})
        product = state.get("product", "")
        protocol = state.get("protocol", "")

        if _is_analog_capable(product, protocol):
            ports = _estimate_ports(product)
            if ports:
                total_estimated_ports += ports
            analog_gws.append((gw, ports))
        else:
            sip_gws.append(gw)

    if not analog_gws:
        summary = f"{len(gateways)} gateways — all SIP, no analog review needed"
        parts = [
            f'<details id="gateways">',
            f'<summary>K. Gateways <span class="summary-count">— {summary}</span></summary>',
            '<div class="details-content">',
            f'<p>{len(sip_gws)} SIP gateways detected. No analog ports requiring manual review.</p>',
            '</div></details>',
        ]
        return "\n".join(parts)

    port_note = f", ~{total_estimated_ports} estimated analog ports" if total_estimated_ports else ""
    summary = f"{len(gateways)} gateways — {len(analog_gws)} analog-capable{port_note}"

    parts = [
        f'<details id="gateways">',
        f'<summary>K. Gateways & Analog Ports <span class="summary-count">— {summary}</span></summary>',
        '<div class="details-content">',
    ]

    # Warning callout
    parts.append(
        '<div class="callout warning">'
        '<p><strong>Analog ports require manual review.</strong> Each FXS/FXO port must be mapped to a '
        'Webex workspace with an ATA device. Analog ports commonly serve fax machines, elevator phones, '
        'alarm panels, overhead paging, and door entry systems — these are often undocumented and cause '
        'day-one outages when missed.</p>'
        '</div>'
    )

    # Analog gateway table
    parts.append('<h4>Analog-Capable Gateways</h4>')
    parts.append('<table>')
    parts.append('<thead><tr><th>Gateway</th><th>Product</th><th>Protocol</th>'
                 '<th class="num">Est. Ports</th><th>Location</th><th>Notes</th></tr></thead>')
    parts.append('<tbody>')

    for gw, ports in analog_gws:
        state = gw.get("pre_migration_state", {})
        name = state.get("gateway_name", strip_canonical_id(gw.get("canonical_id", "")))
        product = state.get("product", "—")
        protocol = state.get("protocol", "—")
        device_pool = state.get("cucm_device_pool", "")
        location = friendly_site_name(device_pool) if device_pool else "—"
        port_str = str(ports) if ports else "Unknown"

        notes = []
        if (protocol or "").upper() in _UNSUPPORTED_PROTOCOLS:
            notes.append(f"{protocol} not supported in Webex — convert to SIP LGW or replace with ATA")
        if not ports:
            notes.append("Port count varies by NIM configuration — manual review needed")
        note_str = "; ".join(notes) if notes else "Map each port to a Webex workspace"

        parts.append(
            f'<tr><td>{html.escape(name)}</td>'
            f'<td>{html.escape(product)}</td>'
            f'<td>{html.escape(protocol)}</td>'
            f'<td class="num">{html.escape(port_str)}</td>'
            f'<td>{html.escape(location)}</td>'
            f'<td>{html.escape(note_str)}</td></tr>'
        )

    parts.append('</tbody></table>')

    # MGCP-specific warning if applicable
    mgcp_gws = [gw for gw, _ in analog_gws if (gw.get("pre_migration_state", {}).get("protocol", "")).upper() == "MGCP"]
    if mgcp_gws:
        parts.append(
            '<div class="callout critical">'
            f'<p><strong>{len(mgcp_gws)} MGCP gateway{"s" if len(mgcp_gws) != 1 else ""} detected.</strong> '
            'MGCP protocol is not supported in Webex Calling. These must be converted to SIP Local Gateway '
            'or replaced with Cisco ATA devices before migration.</p>'
            '</div>'
        )

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# L. Call Features
# ---------------------------------------------------------------------------

def _features_group(store: MigrationStore) -> str:
    """L. Feature inventory with counts."""
    feature_types = [
        ("hunt_group", "Hunt Groups"),
        ("call_queue", "Call Queues"),
        ("auto_attendant", "Auto Attendants"),
        ("call_park", "Call Parks"),
        ("pickup_group", "Pickup Groups"),
        ("paging_group", "Paging Groups"),
        ("call_forwarding", "Call Forwarding Rules"),
        ("monitoring_list", "Monitoring Lists"),
    ]

    feature_rows = []
    total = 0
    for type_key, display_name in feature_types:
        count = store.count_by_type(type_key)
        if count > 0:
            feature_rows.append((type_key, display_name, count))
            total += count

    if not feature_rows:
        return ""

    parts = [
        f'<details id="call-features">',
        f'<summary>L. Call Features <span class="summary-count">— {total} features across {len(feature_rows)} types</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Feature Type</th><th class="num">Count</th></tr></thead>',
        '<tbody>',
    ]

    for type_key, display_name, count in feature_rows:
        parts.append(f'<tr><td>{html.escape(display_name)}</td><td class="num">{count}</td></tr>')

    parts.append('</tbody></table>')

    # Feature detail tables for specific types
    for type_key, display_name, _ in feature_rows:
        objects = store.get_objects(type_key)
        if not objects:
            continue

        parts.append(f'<h4>{html.escape(display_name)}</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Name</th><th>Extension</th><th>Location</th></tr></thead>')
        parts.append('<tbody>')
        for obj in objects:
            name = obj.get("name", strip_canonical_id(obj.get("canonical_id", "")))
            ext = obj.get("extension", "—")
            loc_id = obj.get("location_id", "")
            loc_obj = store.get_object(loc_id) if loc_id else None
            loc_name = loc_obj.get("name", strip_canonical_id(loc_id)) if loc_obj else strip_canonical_id(loc_id) if loc_id else "—"
            parts.append(
                f'<tr><td>{html.escape(name)}</td>'
                f'<td>{html.escape(str(ext))}</td>'
                f'<td>{html.escape(loc_name)}</td></tr>'
            )
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# M. Button Templates
# ---------------------------------------------------------------------------

def _button_template_group(store: MigrationStore) -> str:
    """M. Phone button template inventory — template names, button types, usage counts."""
    templates = store.get_objects("line_key_template")
    if not templates:
        return ""

    total_templates = len(templates)
    total_phones = sum(t.get("phones_using", 0) for t in templates)
    total_unmapped = sum(len(t.get("unmapped_buttons", [])) for t in templates)

    summary_parts = [f"{total_templates} templates"]
    if total_phones:
        summary_parts.append(f"{total_phones} phones")
    if total_unmapped:
        summary_parts.append(f"{total_unmapped} unmapped buttons")

    parts = [
        f'<details id="button-templates">',
        f'<summary>M. Button Templates <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Template</th><th>Base</th><th class="num">Buttons</th>'
        '<th class="num">Phones</th><th>Key Type Breakdown</th><th>Unmapped</th></tr></thead>',
        '<tbody>',
    ]

    for t in sorted(templates, key=lambda x: -(x.get("phones_using", 0))):
        name = t.get("name") or strip_canonical_id(t.get("canonical_id", ""))
        base = t.get("cucm_template_name") or "—"
        line_keys = t.get("line_keys", [])
        phones = t.get("phones_using", 0)
        unmapped = t.get("unmapped_buttons", [])

        # Key type breakdown
        type_counts: dict[str, int] = defaultdict(int)
        for key in line_keys:
            kt = key.get("key_type", "UNKNOWN")
            type_counts[kt] += 1
        breakdown = ", ".join(f"{v} {k}" for k, v in sorted(type_counts.items()))
        if not breakdown:
            breakdown = "—"

        unmapped_str = ", ".join(
            html.escape(b.get("feature", b.get("key_type", "?")))
            for b in unmapped
        ) if unmapped else "—"

        parts.append(
            f'<tr>'
            f'<td>{html.escape(name)}</td>'
            f'<td>{html.escape(base)}</td>'
            f'<td class="num">{len(line_keys)}</td>'
            f'<td class="num">{phones}</td>'
            f'<td>{html.escape(breakdown)}</td>'
            f'<td>{unmapped_str}</td>'
            f'</tr>'
        )

    parts.append('</tbody></table>')

    # Unmapped button types summary
    all_unmapped_features: dict[str, int] = defaultdict(int)
    for t in templates:
        for b in t.get("unmapped_buttons", []):
            feature = b.get("feature", b.get("key_type", "Unknown"))
            all_unmapped_features[feature] += t.get("phones_using", 0)

    if all_unmapped_features:
        parts.append('<h4>Unmapped Button Types</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>CUCM Button Type</th><th class="num">Affected Phones</th></tr></thead>')
        parts.append('<tbody>')
        for feature, count in sorted(all_unmapped_features.items(), key=lambda x: -x[1]):
            parts.append(
                f'<tr><td>{html.escape(feature)}</td>'
                f'<td class="num">{count}</td></tr>'
            )
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# N. Device Layouts
# ---------------------------------------------------------------------------

def _device_layout_group(store: MigrationStore) -> str:
    """N. Per-device layout summary — shared lines, speed dials, BLF, KEM stats."""
    layouts = store.get_objects("device_layout")
    if not layouts:
        return ""

    total = len(layouts)
    shared_count = 0
    speed_dial_count = 0
    blf_count = 0
    kem_count = 0
    total_speed_dials = 0

    for layout in layouts:
        keys = layout.get("resolved_line_keys", [])
        kem_keys = layout.get("resolved_kem_keys", [])
        speed_dials = layout.get("speed_dials", [])

        has_shared = any(k.get("key_type") == "SHARED_LINE" for k in keys)
        has_blf = any(k.get("key_type") == "MONITOR" for k in keys)
        has_kem = len(kem_keys) > 0
        has_speed_dials = len(speed_dials) > 0

        if has_shared:
            shared_count += 1
        if has_blf:
            blf_count += 1
        if has_kem:
            kem_count += 1
        if has_speed_dials:
            speed_dial_count += 1
            total_speed_dials += len(speed_dials)

    summary_parts = [f"{total} device layouts"]
    if shared_count:
        summary_parts.append(f"{shared_count} with shared lines")
    if blf_count:
        summary_parts.append(f"{blf_count} with BLF")

    parts = [
        f'<details id="device-layouts">',
        f'<summary>N. Device Layouts <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Metric</th><th class="num">Count</th></tr></thead>',
        '<tbody>',
        f'<tr><td>Total device layouts</td><td class="num">{total}</td></tr>',
        f'<tr><td>Phones with shared line appearances</td><td class="num">{shared_count}</td></tr>',
        f'<tr><td>Phones with speed dials</td><td class="num">{speed_dial_count}</td></tr>',
    ]

    if speed_dial_count > 0:
        avg = total_speed_dials / speed_dial_count
        parts.append(
            f'<tr><td>Average speed dials per phone</td><td class="num">{avg:.1f}</td></tr>'
        )

    parts.extend([
        f'<tr><td>Phones with BLF/monitoring keys</td><td class="num">{blf_count}</td></tr>',
        f'<tr><td>Phones with KEM modules</td><td class="num">{kem_count}</td></tr>',
    ])

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# O. Softkey Migration
# ---------------------------------------------------------------------------

def _softkey_group(store: MigrationStore) -> str:
    """O. Softkey template migration status — PSK mapping, classic MPP flags."""
    configs = store.get_objects("softkey_config")
    if not configs:
        return ""

    total = len(configs)
    psk_count = sum(1 for c in configs if c.get("is_psk_target"))
    classic_count = total - psk_count

    summary_parts = [f"{total} softkey templates"]
    if psk_count:
        summary_parts.append(f"{psk_count} PSK-capable")
    if classic_count:
        summary_parts.append(f"{classic_count} classic MPP")

    parts = [
        f'<details id="softkeys">',
        f'<summary>O. Softkey Migration <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Template</th><th class="num">Phones</th>'
        '<th>PSK Target</th><th class="num">PSK Mappings</th>'
        '<th class="num">Unmapped</th></tr></thead>',
        '<tbody>',
    ]

    for c in sorted(configs, key=lambda x: -(x.get("phones_using", 0))):
        name = c.get("cucm_template_name") or strip_canonical_id(c.get("canonical_id", ""))
        phones = c.get("phones_using", 0)
        is_psk = c.get("is_psk_target", False)
        psk_mappings = c.get("psk_mappings", [])
        unmapped = c.get("unmapped_softkeys", [])

        psk_str = "Yes (9800/8875)" if is_psk else "No (classic MPP)"

        parts.append(
            f'<tr>'
            f'<td>{html.escape(name)}</td>'
            f'<td class="num">{phones}</td>'
            f'<td>{html.escape(psk_str)}</td>'
            f'<td class="num">{len(psk_mappings)}</td>'
            f'<td class="num">{len(unmapped)}</td>'
            f'</tr>'
        )

    parts.append('</tbody></table>')

    # Classic MPP warning
    classic_phones = sum(
        c.get("phones_using", 0) for c in configs if not c.get("is_psk_target")
    )
    if classic_phones > 0:
        parts.append(
            '<div class="callout warning">'
            f'<p><strong>{classic_phones} phones with custom softkey templates on classic MPP.</strong> '
            'Classic MPP phones (non-9800/8875) do not support Programmable Softkeys. '
            'These phones will use Webex default softkey behavior after migration — '
            'custom softkey layouts will not be preserved.</p>'
            '</div>'
        )

    # Unmapped softkeys summary
    all_unmapped: dict[str, int] = defaultdict(int)
    for c in configs:
        for sk in c.get("unmapped_softkeys", []):
            cucm_name = sk.get("cucm_name", "Unknown")
            all_unmapped[cucm_name] += 1

    if all_unmapped:
        parts.append('<h4>Unmapped CUCM Softkeys</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>CUCM Softkey</th><th class="num">Templates Using</th></tr></thead>')
        parts.append('<tbody>')
        for sk_name, count in sorted(all_unmapped.items(), key=lambda x: -x[1]):
            parts.append(
                f'<tr><td>{html.escape(sk_name)}</td>'
                f'<td class="num">{count}</td></tr>'
            )
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# P. Cloud-Managed Resources (Tier 3)
# ---------------------------------------------------------------------------

_CLOUD_MANAGED_TYPES = [
    "info_region", "info_srst", "info_media_resource_group",
    "info_media_resource_list", "info_aar_group",
    "info_device_mobility_group", "info_conference_bridge",
]


def _cloud_managed_group(store: MigrationStore) -> str:
    """P. Cloud-Managed Resources — CUCM objects handled automatically by Webex."""
    rows = []
    total = 0
    for ot in _CLOUD_MANAGED_TYPES:
        count = store.count_by_type(ot)
        if count > 0:
            suffix = ot.replace("info_", "")
            display = DISPLAY_NAMES.get(suffix, suffix.replace("_", " ").title())
            rows.append((display, count))
            total += count

    if not rows:
        return ""

    parts = [
        '<details id="cloud-managed">',
        f'<summary>P. Cloud-Managed Resources <span class="summary-count">'
        f'— {total} objects across {len(rows)} types</span></summary>',
        '<div class="details-content">',
        '<p>These CUCM resources are managed automatically by the Webex cloud. '
        'No migration action is needed.</p>',
        '<table>',
        '<thead><tr><th>Resource Type</th><th class="num">Count</th><th>Note</th></tr></thead>',
        '<tbody>',
    ]
    for display, count in rows:
        parts.append(
            f'<tr><td>{html.escape(display)}</td>'
            f'<td class="num">{count}</td>'
            f'<td>Webex manages this automatically</td></tr>'
        )
    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Q. Feature Gaps (Tier 3)
# ---------------------------------------------------------------------------

_NOT_MIGRATABLE_TYPES = [
    "info_softkey_template", "info_ip_phone_service", "info_intercom",
]


def _feature_gaps_group(store: MigrationStore) -> str:
    """Q. Feature Gaps — CUCM features with no Webex equivalent."""
    rows = []
    total = 0
    for ot in _NOT_MIGRATABLE_TYPES:
        count = store.count_by_type(ot)
        if count > 0:
            suffix = ot.replace("info_", "")
            display = DISPLAY_NAMES.get(suffix, suffix.replace("_", " ").title())
            workaround = NOT_MIGRATABLE_WORKAROUNDS.get(suffix, "None")
            rows.append((display, count, workaround))
            total += count

    if not rows:
        return ""

    parts = [
        '<details id="feature-gaps">',
        f'<summary>Q. Feature Gaps <span class="summary-count">'
        f'— {total} objects across {len(rows)} types</span></summary>',
        '<div class="details-content">',
        '<div class="callout warning">'
        '<p>These CUCM features have no direct Webex equivalent. '
        'Functionality may be lost or require workarounds.</p></div>',
        '<table>',
        '<thead><tr><th>Feature</th><th class="num">Count</th>'
        '<th>Impact</th><th>Workaround</th></tr></thead>',
        '<tbody>',
    ]
    for display, count, workaround in rows:
        parts.append(
            f'<tr><td>{html.escape(display)}</td>'
            f'<td class="num">{count}</td>'
            f'<td>No Webex equivalent</td>'
            f'<td>{html.escape(workaround)}</td></tr>'
        )
    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# R. Manual Reconfiguration (Tier 3)
# ---------------------------------------------------------------------------

_DIFFERENT_ARCH_TYPES = [
    "info_common_phone_config", "info_phone_button_template",
    "info_feature_control_policy", "info_credential_policy",
    "info_recording_profile", "info_ldap_directory",
]


def _manual_reconfig_group(store: MigrationStore) -> str:
    """R. Manual Reconfiguration — features that must be reconfigured in Webex."""
    rows = []
    total = 0
    for ot in _DIFFERENT_ARCH_TYPES:
        count = store.count_by_type(ot)
        if count > 0:
            suffix = ot.replace("info_", "")
            display = DISPLAY_NAMES.get(suffix, suffix.replace("_", " ").title())
            webex_eq = WEBEX_EQUIVALENTS.get(suffix, "Manual configuration required")
            rows.append((display, count, webex_eq))
            total += count

    if not rows:
        return ""

    parts = [
        '<details id="manual-reconfig">',
        f'<summary>R. Manual Reconfiguration <span class="summary-count">'
        f'— {total} objects across {len(rows)} types</span></summary>',
        '<div class="details-content">',
        '<p>These CUCM features have Webex equivalents but are configured differently. '
        'They must be set up manually in Webex Control Hub.</p>',
        '<table>',
        '<thead><tr><th>CUCM Feature</th><th class="num">Count</th>'
        '<th>Webex Equivalent</th></tr></thead>',
        '<tbody>',
    ]
    for display, count, webex_eq in rows:
        parts.append(
            f'<tr><td>{html.escape(display)}</td>'
            f'<td class="num">{count}</td>'
            f'<td>{html.escape(webex_eq)}</td></tr>'
        )
    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# S. Planning Inputs (Tier 3)
# ---------------------------------------------------------------------------

_INTEGRATION_KEYWORDS = ("jtapi", "tapi", "cer", "recording", "finesse", "uccx", "cuic")


def _planning_inputs_group(store: MigrationStore) -> str:
    """S. Planning Inputs — data for migration planning decisions."""
    app_users = store.get_objects("info_app_user")
    h323_gws = store.get_objects("info_h323_gateway")
    enterprise = store.get_objects("info_enterprise_params")
    service_params = store.get_objects("info_service_params")

    total = len(app_users) + len(h323_gws) + len(enterprise) + len(service_params)
    if total == 0:
        return ""

    parts = [
        '<details id="planning-inputs">',
        f'<summary>S. Planning Inputs <span class="summary-count">'
        f'— {total} items</span></summary>',
        '<div class="details-content">',
    ]

    if app_users:
        integration_users = []
        other_users = []
        for u in app_users:
            state = u.get("pre_migration_state", {})
            uid = state.get("userid", "")
            desc = (state.get("description") or "").lower()
            is_integration = any(
                kw in uid.lower() or kw in desc for kw in _INTEGRATION_KEYWORDS
            )
            if is_integration:
                integration_users.append(u)
            else:
                other_users.append(u)

        parts.append(f'<h4>Application Users ({len(app_users)})</h4>')
        if integration_users:
            parts.append(
                '<div class="callout warning">'
                f'<p><strong>{len(integration_users)} integration-related application user'
                f'{"s" if len(integration_users) != 1 else ""} detected.</strong> '
                'JTAPI/TAPI apps, CER, and recording integrations must be reviewed '
                'for Webex compatibility.</p></div>'
            )
        parts.append('<table>')
        parts.append(
            '<thead><tr><th>User ID</th><th>Description</th>'
            '<th>Devices</th><th>Integration?</th></tr></thead>'
        )
        parts.append('<tbody>')
        for u in app_users:
            state = u.get("pre_migration_state", {})
            uid = state.get("userid", "")
            desc = state.get("description", "")
            devices = state.get("associatedDevices", "")
            is_int = u in integration_users
            flag = "Yes" if is_int else ""
            parts.append(
                f'<tr><td>{html.escape(uid)}</td>'
                f'<td>{html.escape(desc)}</td>'
                f'<td>{html.escape(str(devices))}</td>'
                f'<td>{flag}</td></tr>'
            )
        parts.append('</tbody></table>')

    if h323_gws:
        parts.append(f'<h4>H.323 Gateways ({len(h323_gws)})</h4>')
        parts.append(
            '<div class="callout warning">'
            '<p><strong>H.323 gateways require protocol conversion.</strong> '
            'Webex Calling uses SIP only — these gateways must be replaced or '
            'converted to SIP Local Gateway.</p></div>'
        )
        parts.append('<table>')
        parts.append('<thead><tr><th>Name</th><th>Product</th><th>Description</th></tr></thead>')
        parts.append('<tbody>')
        for gw in h323_gws:
            state = gw.get("pre_migration_state", {})
            parts.append(
                f'<tr><td>{html.escape(state.get("name", ""))}</td>'
                f'<td>{html.escape(state.get("product", ""))}</td>'
                f'<td>{html.escape(state.get("description", ""))}</td></tr>'
            )
        parts.append('</tbody></table>')

    if enterprise:
        parts.append('<h4>Enterprise Parameters</h4>')
        parts.append('<p>Enterprise parameter baseline captured for reference. '
                     'Review cluster-wide settings during migration planning.</p>')

    if service_params:
        parts.append(f'<h4>Service Parameters ({len(service_params)})</h4>')
        parts.append('<p>Telephony-related service parameters captured. '
                     'Key parameters may need equivalent Webex configuration.</p>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Parameter</th><th>Service</th><th>Value</th></tr></thead>')
        parts.append('<tbody>')
        for sp in service_params[:20]:
            state = sp.get("pre_migration_state", {})
            parts.append(
                f'<tr><td>{html.escape(state.get("name", ""))}</td>'
                f'<td>{html.escape(state.get("service", ""))}</td>'
                f'<td>{html.escape(str(state.get("value", "")))}</td></tr>'
            )
        parts.append('</tbody></table>')
        if len(service_params) > 20:
            parts.append(f'<p class="muted">{len(service_params) - 20} additional parameters not shown.</p>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# T. Call Recording Inventory (Tier 4 Item 1)
# ---------------------------------------------------------------------------

def _recording_inventory(store: MigrationStore) -> str:
    """T. Users with call recording enabled -- from phone line data."""
    phones = store.get_objects("phone")
    if not phones:
        return ""

    recording_entries: list[tuple[str, str, str, str, str]] = []  # (user, phone, dn, flag, profile)

    for phone in phones:
        pre = phone.get("pre_migration_state", {}) or {}
        owner_raw = pre.get("ownerUserName", "")
        if isinstance(owner_raw, dict):
            owner = owner_raw.get("_value_1", "") or ""
        else:
            owner = owner_raw or ""
        phone_name = pre.get("name", strip_canonical_id(phone.get("canonical_id", "")))
        for line in (pre.get("lines") or []):
            if not isinstance(line, dict):
                continue
            flag = line.get("recordingFlag", "Call Recording Disabled")
            if flag and flag != "Call Recording Disabled":
                dirn = line.get("dirn", {})
                pattern = dirn.get("pattern", "") if isinstance(dirn, dict) else ""
                profile_ref = line.get("recordingProfileName")
                profile = ""
                if isinstance(profile_ref, dict):
                    profile = profile_ref.get("_value_1", "")
                elif isinstance(profile_ref, str):
                    profile = profile_ref
                recording_entries.append((owner or "\u2014", phone_name, pattern, flag, profile))

    if not recording_entries:
        return ""

    users = set(e[0] for e in recording_entries if e[0] != "\u2014")
    summary = f"{len(recording_entries)} lines with recording enabled across {len(users)} users"

    parts = [
        '<details id="recording-inventory">',
        f'<summary>T. Call Recording Inventory <span class="summary-count">'
        f'\u2014 {summary}</span></summary>',
        '<div class="details-content">',
        '<div class="callout warning">',
        '<p><strong>Call recording requires separate Webex configuration.</strong> '
        'Each recording-enabled user needs: (1) Webex Call Recording license, '
        '(2) location-level recording vendor configuration, and '
        '(3) person-level recording settings enabled.</p>',
        '</div>',
        '<table>',
        '<thead><tr><th>User</th><th>Phone</th><th>DN</th><th>Recording Mode</th><th>Recording Profile</th></tr></thead>',
        '<tbody>',
    ]

    em_dash = "\u2014"
    for owner, phone_name, pattern, flag, profile in sorted(recording_entries):
        mode = flag.replace("Call Recording ", "").replace(" Enabled", "")
        profile_display = html.escape(profile) if profile else em_dash
        parts.append(
            f'<tr><td>{html.escape(owner)}</td>'
            f'<td>{html.escape(phone_name)}</td>'
            f'<td>{html.escape(pattern)}</td>'
            f'<td>{html.escape(mode)}</td>'
            f'<td>{profile_display}</td></tr>'
        )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# U. Single Number Reach Inventory (Tier 4 Item 2)
# ---------------------------------------------------------------------------

def _snr_inventory(store: MigrationStore) -> str:
    """U. Remote destination profiles -- Single Number Reach."""
    rdps = store.get_objects("remote_destination")
    if not rdps:
        return ""

    owners: dict[str, list[dict]] = defaultdict(list)
    for rdp in rdps:
        pre = rdp.get("pre_migration_state", {}) or {}
        owner = pre.get("ownerUserId", "") or "\u2014"
        owners[owner].append(pre)

    summary = f"{len(rdps)} remote destinations for {len(owners)} users"

    parts = [
        '<details id="snr-inventory">',
        f'<summary>U. Single Number Reach <span class="summary-count">'
        f'\u2014 {summary}</span></summary>',
        '<div class="details-content">',
        '<div class="callout">',
        '<p><strong>Webex SNR is simpler than CUCM.</strong> '
        'CUCM timer controls (answer-too-soon, answer-too-late thresholds) '
        'do not have Webex equivalents. Manual setup required per user.</p>',
        '</div>',
        '<table>',
        '<thead><tr><th>User</th><th>Profile Name</th><th>Destination</th></tr></thead>',
        '<tbody>',
    ]

    for owner in sorted(owners):
        for rdp in owners[owner]:
            name = rdp.get("name", "\u2014")
            dest = rdp.get("destination", "\u2014")
            parts.append(
                f'<tr><td>{html.escape(owner)}</td>'
                f'<td>{html.escape(name)}</td>'
                f'<td>{html.escape(dest)}</td></tr>'
            )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# V. Caller ID Transformation Patterns (Tier 4 Item 4)
# ---------------------------------------------------------------------------

def _caller_id_xforms(store: MigrationStore) -> str:
    """V. Calling/Called party transformation patterns."""
    calling = store.get_objects("info_calling_xform")
    called = store.get_objects("info_called_xform")
    total = len(calling) + len(called)

    if total == 0:
        return ""

    summary = f"{len(calling)} calling party, {len(called)} called party"

    parts = [
        '<details id="caller-id-xforms">',
        f'<summary>V. Caller ID Transformations <span class="summary-count">'
        f'\u2014 {summary}</span></summary>',
        '<div class="details-content">',
        '<div class="callout">',
        '<p><strong>CUCM caller ID transformations &rarr; Webex location-level outbound caller ID.</strong> '
        'Each pattern requires manual review to determine the equivalent Webex configuration.</p>',
        '</div>',
    ]

    if calling:
        parts.append('<h4>Calling Party Transformations</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Pattern</th><th>Partition</th><th>Mask</th><th>Description</th></tr></thead>')
        parts.append('<tbody>')
        for obj in calling:
            pre = obj.get("pre_migration_state", {}) or {}
            parts.append(
                f'<tr><td>{html.escape(_axl_str(pre.get("pattern", "")))}</td>'
                f'<td>{html.escape(_axl_str(pre.get("routePartitionName", "")))}</td>'
                f'<td>{html.escape(_axl_str(pre.get("callingPartyTransformationMask", "")))}</td>'
                f'<td>{html.escape(_axl_str(pre.get("description", "")))}</td></tr>'
            )
        parts.append('</tbody></table>')

    if called:
        parts.append('<h4>Called Party Transformations</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Pattern</th><th>Partition</th><th>Mask</th><th>Description</th></tr></thead>')
        parts.append('<tbody>')
        for obj in called:
            pre = obj.get("pre_migration_state", {}) or {}
            parts.append(
                f'<tr><td>{html.escape(_axl_str(pre.get("pattern", "")))}</td>'
                f'<td>{html.escape(_axl_str(pre.get("routePartitionName", "")))}</td>'
                f'<td>{html.escape(_axl_str(pre.get("calledPartyTransformationMask", "")))}</td>'
                f'<td>{html.escape(_axl_str(pre.get("description", "")))}</td></tr>'
            )
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# W. Extension Mobility Usage (Tier 4 Item 6)
# ---------------------------------------------------------------------------

def _extension_mobility_group(store: MigrationStore) -> str:
    """W. Extension Mobility device profiles -- hot desking with feature loss detail."""
    profiles = store.get_objects("info_device_profile")
    if not profiles:
        return ""

    summary = f"{len(profiles)} device profiles"

    parts = [
        '<details id="extension-mobility">',
        f'<summary>W. Extension Mobility <span class="summary-count">'
        f'\u2014 {summary}</span></summary>',
        '<div class="details-content">',
        '<div class="callout">',
        '<p><strong>Extension Mobility &rarr; Webex hot desking.</strong> '
        'CUCM device profile switching does not carry over. Webex hot desking provides '
        'user login/logout with primary line on shared workspaces. '
        'Multi-line profiles, speed dials, and BLF entries are not available during '
        'hot desk sessions.</p>',
        '</div>',
        '<table>',
        '<thead><tr>'
        '<th>Profile Name</th><th>Product</th><th>Lines</th>'
        '<th>Speed Dials</th><th>BLF</th><th>Feature Loss</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for p in profiles:
        pre = p.get("pre_migration_state", {}) or {}
        name = pre.get("name", strip_canonical_id(p.get("canonical_id", "")))
        product = pre.get("product", "\u2014")
        lines = pre.get("lines") or []
        line_count = len(lines) if lines else pre.get("line_count", 0)
        sd_count = pre.get("speed_dial_count", 0)
        blf_count_val = pre.get("blf_count", 0)

        if line_count > 1 or blf_count_val > 0:
            loss = "Medium"
            loss_class = "badge-warning"
        elif sd_count > 0:
            loss = "Low"
            loss_class = "badge-info"
        else:
            loss = "None"
            loss_class = "badge-success"

        parts.append(
            f'<tr><td>{html.escape(name)}</td>'
            f'<td>{html.escape(product)}</td>'
            f'<td>{line_count}</td>'
            f'<td>{sd_count}</td>'
            f'<td>{blf_count_val}</td>'
            f'<td><span class="{loss_class}">{loss}</span></td></tr>'
        )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


def _dect_networks_group(store: MigrationStore) -> str:
    """X. DECT Networks — inventory, coverage zones, and design inputs."""
    devices = store.get_objects("device")
    dect_devices = [d for d in devices if d.get("compatibility_tier") == "dect"]
    if not dect_devices:
        return ""

    parts: list[str] = []
    parts.append('<details id="dect-networks">')
    parts.append('<summary><span class="section-indicator">X</span> DECT Networks</summary>')

    # --- Subsection 1: Inventory table ---
    parts.append("<h4>DECT Handset Inventory</h4>")
    parts.append("<table><thead><tr>")
    parts.append("<th>Device Name</th><th>Model</th><th>Owner</th>"
                 "<th>Extension</th><th>Device Pool</th>")
    parts.append("</tr></thead><tbody>")

    for d in sorted(dect_devices, key=lambda x: x.get("cucm_device_name") or ""):
        state = d.get("pre_migration_state") or {}
        device_name = d.get("cucm_device_name") or strip_canonical_id(d.get("canonical_id", ""))
        model = d.get("model", "Unknown")
        owner = state.get("ownerUserName") or "<em>unowned</em>"
        lines = state.get("line_appearances") or d.get("line_appearances") or []
        ext = ""
        if lines:
            dirn = lines[0].get("dirn", {}) if isinstance(lines[0], dict) else {}
            ext = dirn.get("pattern", "")
        dp = state.get("cucm_device_pool", "\u2014")

        parts.append(f"<tr><td>{device_name}</td><td>{model}</td>"
                     f"<td>{owner}</td><td>{ext}</td><td>{dp}</td></tr>")

    parts.append("</tbody></table>")

    # --- Subsection 2: Coverage zone analysis ---
    zones: dict[str, list[dict]] = {}
    for d in dect_devices:
        dp = (d.get("pre_migration_state") or {}).get("cucm_device_pool", "Unknown")
        zones.setdefault(dp, []).append(d)

    parts.append("<h4>Coverage Zone Analysis</h4>")
    parts.append("<table><thead><tr>")
    parts.append("<th>Coverage Zone (Device Pool)</th><th>Handset Count</th>"
                 "<th>Owned</th><th>Unowned</th>")
    parts.append("</tr></thead><tbody>")

    for zone_name in sorted(zones):
        handsets = zones[zone_name]
        total = len(handsets)
        owned = sum(1 for h in handsets if (h.get("pre_migration_state") or {}).get("ownerUserName"))
        unowned = total - owned
        parts.append(f"<tr><td>{zone_name}</td><td>{total}</td>"
                     f"<td>{owned}</td><td>{unowned}</td></tr>")

    parts.append("</tbody></table>")

    # --- Subsection 3: Design inputs ---
    total_handsets = len(dect_devices)
    zone_count = len(zones)
    parts.append("<h4>DECT Network Design Inputs</h4>")
    parts.append('<div class="callout">')
    parts.append(f"<p><strong>Total DECT handsets:</strong> {total_handsets}</p>")
    parts.append(f"<p><strong>Implied coverage zones:</strong> {zone_count} "
                 f"(from device pool grouping)</p>")
    parts.append("<p><strong>Recommended:</strong> Provide base station inventory "
                 "(MAC addresses and model) for each coverage zone.</p>")

    for zone_name in sorted(zones):
        count = len(zones[zone_name])
        if count > 30:
            parts.append(f"<p><strong>{zone_name}:</strong> {count} handsets \u2014 "
                         f"multi-cell DBS-210 network recommended</p>")
        else:
            parts.append(f"<p><strong>{zone_name}:</strong> {count} handsets \u2014 "
                         f"single-cell DBS-110 or multi-cell DBS-210</p>")

    parts.append("</div>")

    # --- Subsection 4: Shared handset warning (conditional) ---
    unowned_total = sum(
        1 for d in dect_devices
        if not (d.get("pre_migration_state") or {}).get("ownerUserName")
    )
    if unowned_total:
        parts.append("<h4>Shared Handset Warnings</h4>")
        parts.append('<div class="callout">')
        parts.append(
            f"<p><strong>{unowned_total} DECT handset{'s' if unowned_total != 1 else ''} "
            f"with no owner.</strong> These may be shared or roaming handsets that need "
            f"workspace assignment in Webex.</p>"
        )
        parts.append("</div>")

    parts.append("</details>")
    return "\n".join(parts)


def _intercept_candidates(store: MigrationStore) -> str:
    """Y. Call Intercept Candidates."""
    candidates = store.get_objects("intercept_candidate")
    if not candidates:
        return ""
    parts = [
        '<details id="intercept-candidates">',
        f'<summary>Y. Call Intercept Candidates <span class="summary-count">'
        f'\u2014 {len(candidates)} candidates</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>User</th><th>DN</th><th>Partition</th>'
        '<th>Signal Type</th><th>Forward Destination</th></tr></thead>',
        '<tbody>',
    ]
    em = "—"
    for ic in sorted(candidates, key=lambda c: c.get("pre_migration_state", {}).get("userid", "")):
        pre = ic.get("pre_migration_state", {}) or {}
        userid = pre.get("userid") or em
        dn = pre.get("dn") or em
        partition = pre.get("partition") or em
        signal = (pre.get("signal_type") or "unknown").replace("_", " ").title()
        fwd = pre.get("forward_destination") or em
        parts.append(
            f'<tr><td>{html.escape(userid)}</td>'
            f'<td>{html.escape(dn)}</td>'
            f'<td>{html.escape(partition)}</td>'
            f'<td>{html.escape(signal)}</td>'
            f'<td>{html.escape(fwd)}</td></tr>'
        )
    parts.extend(['</tbody></table>', '</div></details>'])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Z. Executive/Assistant Pairings
# ---------------------------------------------------------------------------

def _executive_assistant_group(store: MigrationStore) -> str:
    """Z. Executive/Assistant Pairings — delegation relationships."""
    ea_objs = store.get_objects("executive_assistant")
    if not ea_objs:
        return ""

    parts = [
        '<details id="section-exec-assistant">',
        f'<summary>Z. Executive/Assistant Pairings '
        f'<span class="summary-count">— {len(ea_objs)} executive(s)</span></summary>',
        '<div class="details-content">',
        "<p>Executive/assistant pairings configured in CUCM. Each executive has one or "
        "more assistants who can answer, screen, and place calls on their behalf.</p>",
        "<table>",
        "<thead><tr>"
        "<th>Executive</th>"
        "<th>Assistants</th>"
        "<th>Alerting</th>"
        "<th>Filtering</th>"
        "<th>Screening</th>"
        "</tr></thead>",
        "<tbody>",
    ]

    for ea in ea_objs:
        exec_id = ea.get("executive_canonical_id", "")
        exec_name = strip_canonical_id(exec_id)
        assistants = ea.get("assistant_canonical_ids", [])
        asst_names = ", ".join(strip_canonical_id(a) for a in assistants)
        alerting = ea.get("alerting_mode", "SIMULTANEOUS")
        filtering = "No"
        if ea.get("filter_enabled"):
            filter_type = ea.get("filter_type", "")
            filtering = f"Yes ({html.escape(filter_type)})" if filter_type else "Yes"
        screening = "Yes" if ea.get("screening_enabled") else "No"

        parts.append(
            f"<tr>"
            f"<td>{html.escape(exec_name)}</td>"
            f"<td>{html.escape(asst_names)}</td>"
            f"<td>{html.escape(alerting)}</td>"
            f"<td>{filtering}</td>"
            f"<td>{screening}</td>"
            f"</tr>"
        )

    parts.extend(["</tbody>", "</table>", "</div>", "</details>"])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# AA. Receptionist Users
# ---------------------------------------------------------------------------

def _receptionist_group(store: MigrationStore) -> str:
    """AA. Receptionist Users — detected users with receptionist-style BLF/KEM/template configs."""
    receptionists = store.get_objects("receptionist_config")
    if not receptionists:
        return ""

    total = len(receptionists)
    sorted_recs = sorted(receptionists, key=lambda r: -(r.get("detection_score") or 0))

    em_dash = "\u2014"

    parts = [
        '<details id="receptionist-users">',
        f'<summary>AA. Receptionist Users <span class="summary-count">'
        f'\u2014 {total} detected</span></summary>',
        '<div class="details-content">',
        '<p>These users were detected as likely receptionists based on BLF monitoring lists, '
        'KEM modules, and phone button templates. They may be using Cisco Unified Attendant '
        'Console (CUAC) or CUCM receptionist console features. Each requires attention during '
        'migration to preserve answering workflows and directory visibility.</p>',
        '<table>',
        '<thead><tr>'
        '<th>User</th>'
        '<th>Location</th>'
        '<th class="num">BLF Count</th>'
        '<th>KEM</th>'
        '<th>Template</th>'
        '<th class="num">Score</th>'
        '<th>Main #</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for rec in sorted_recs:
        user_raw = rec.get("user_canonical_id", "")
        loc_raw = rec.get("location_canonical_id", "")
        user_display = strip_canonical_id(user_raw) if user_raw else em_dash
        loc_display = strip_canonical_id(loc_raw) if loc_raw else em_dash
        blf_count = rec.get("blf_count") or 0
        has_kem = rec.get("has_kem") or False
        template = rec.get("template_name") or em_dash
        score = rec.get("detection_score") or 0
        is_main = rec.get("is_main_number_holder") or False

        parts.append(
            f'<tr>'
            f'<td>{html.escape(user_display)}</td>'
            f'<td>{html.escape(loc_display)}</td>'
            f'<td class="num">{blf_count}</td>'
            f'<td>{"Yes" if has_kem else em_dash}</td>'
            f'<td>{html.escape(str(template))}</td>'
            f'<td class="num">{score}</td>'
            f'<td>{"Yes" if is_main else em_dash}</td>'
            f'</tr>'
        )

    parts.append('</tbody></table>')

    # Migration Impact sub-table
    parts.extend([
        '<h4>Migration Impact</h4>',
        '<table>',
        '<thead><tr>'
        '<th>CUCM Feature</th>'
        '<th>Webex Equivalent</th>'
        '<th>Action</th>'
        '</tr></thead>',
        '<tbody>',
        '<tr>'
        '<td>BLF monitoring list</td>'
        '<td>Receptionist Client monitored members</td>'
        '<td>Automatic \u2014 migrated from BLF entries</td>'
        '</tr>',
        '<tr>'
        '<td>Phone button template layout</td>'
        '<td>Line key template</td>'
        '<td>Automatic \u2014 migrated by DeviceLayoutMapper</td>'
        '</tr>',
        '<tr>'
        '<td>CUAC desktop application</td>'
        '<td>Webex Receptionist Console (web)</td>'
        '<td>Manual \u2014 requires user training</td>'
        '</tr>',
        '<tr>'
        '<td>CUAC directory search</td>'
        '<td>Receptionist Contact Directories</td>'
        '<td>Semi-automatic \u2014 directories created during execution</td>'
        '</tr>',
        '<tr>'
        '<td>CTI application user routing</td>'
        '<td>No direct equivalent</td>'
        '<td>Rebuild \u2014 use Auto Attendant or Call Queue</td>'
        '</tr>',
        '</tbody></table>',
        '</div></details>',
    ])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# AB. Selective Call Handling Opportunities
# ---------------------------------------------------------------------------

_SCH_PATTERN_DISPLAY = {
    "multi_partition_dn": "Multi-Partition DN",
    "low_membership_partition": "Low-Membership Partition",
    "naming_convention": "Naming Convention",
}


def _selective_call_handling(store: MigrationStore) -> str:
    """AB. Selective Call Handling Opportunities — CUCM CSS patterns."""
    candidates: list[dict[str, Any]] = []
    for d in store.get_all_decisions():
        if d.get("type") != "FEATURE_APPROXIMATION":
            continue
        if d.get("chosen_option") == "__stale__":
            continue
        ctx = d.get("context", {}) or {}
        pattern = ctx.get("selective_call_handling_pattern")
        if not pattern:
            continue
        candidates.append(d)

    if not candidates:
        return ""

    parts = [
        '<details id="selective-call-handling">',
        f'<summary>AB. Selective Call Handling '
        f'<span class="summary-count">— {len(candidates)} candidate(s)</span>'
        f'</summary>',
        '<div class="details-content">',
        '<p>CUCM CSS/partition patterns suggest caller-specific routing. '
        'Webex Calling offers four explicit per-person features that can '
        'replicate this behaviour: Selective Forward, Selective Accept, '
        'Selective Reject, and Priority Alert. The first three are '
        'admin-configurable; Priority Alert requires per-user OAuth.</p>',
        '<table>',
        '<thead><tr>'
        '<th>Affected Object</th>'
        '<th>Pattern Type</th>'
        '<th>Partitions</th>'
        '<th>Recommended Webex Feature</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for d in sorted(candidates, key=lambda x: x.get("decision_id", "")):
        ctx = d.get("context", {}) or {}
        pattern = ctx.get("selective_call_handling_pattern", "")
        pattern_display = _SCH_PATTERN_DISPLAY.get(
            pattern, pattern.replace("_", " ").title()
        )
        affected_ids = ctx.get("_affected_objects", []) or []
        affected_display = ", ".join(
            strip_canonical_id(obj_id) for obj_id in affected_ids
        ) or "—"
        partitions = ", ".join(ctx.get("partitions", [])) or "—"
        feature = ctx.get("recommended_webex_feature", "—")
        parts.append(
            f'<tr>'
            f'<td>{html.escape(affected_display)}</td>'
            f'<td>{html.escape(pattern_display)}</td>'
            f'<td>{html.escape(partitions)}</td>'
            f'<td>{html.escape(feature)}</td>'
            f'</tr>'
        )

    parts.extend(['</tbody></table>', '</div></details>'])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# AC. Device Settings Coverage
# ---------------------------------------------------------------------------

_AUTOMATED_SETTINGS_BY_FAMILY: dict[str, list[str]] = {
    "9800": ["Line keys", "PSK mappings", "Screen layout", "DND", "Language", "Backlight timer", "USB ports", "CDP/LLDP"],
    "8875": ["Line keys", "PSK mappings", "Screen layout", "DND", "Language", "Backlight timer", "USB ports", "CDP/LLDP"],
    "78xx": ["Line keys", "DND", "Language", "Backlight timer", "CDP/LLDP"],
    "68xx": ["Line keys", "DND", "Language", "Backlight timer"],
}

_MANUAL_SETTINGS_BY_FAMILY: dict[str, list[str]] = {
    "9800": ["Wallpaper / background image", "Wi-Fi credentials", "Bluetooth pairing", "Network VLAN"],
    "8875": ["Wallpaper / background image", "Wi-Fi credentials", "Bluetooth pairing", "Network VLAN"],
    "78xx": ["Wallpaper / background image", "Network VLAN"],
    "68xx": ["Wallpaper / background image", "Network VLAN"],
}


def _device_settings_coverage(store: MigrationStore) -> str:
    """AC. Device Settings Coverage — automated vs manual settings by model family."""
    templates = store.get_objects("device_settings_template")
    if not templates:
        return ""

    # Count phones per model family across only native_mpp / convertible devices
    family_phone_counts: dict[str, int] = defaultdict(int)
    family_override_counts: dict[str, int] = defaultdict(int)
    family_unmappable: dict[str, list[str]] = defaultdict(list)

    for t in templates:
        family = t.get("model_family") or "unknown"
        family_phone_counts[family] += t.get("phones_using") or 0
        overrides = t.get("per_device_overrides") or []
        family_override_counts[family] += len(overrides)
        unmappable = t.get("unmappable_settings") or []
        for field in unmappable:
            if field not in family_unmappable[family]:
                family_unmappable[family].append(field)

    total_phones = sum(family_phone_counts.values())
    total_automated = sum(
        len(_AUTOMATED_SETTINGS_BY_FAMILY.get(f, []))
        for f in family_phone_counts
    )
    total_manual = sum(
        len(_MANUAL_SETTINGS_BY_FAMILY.get(f, []))
        for f in family_phone_counts
    )

    summary = (
        f"{len(family_phone_counts)} phone model {'families' if len(family_phone_counts) != 1 else 'family'}, "
        f"{total_phones} phones, "
        f"{total_automated} automated settings, "
        f"{total_manual} require manual Control Hub configuration"
    )

    parts = [
        '<details id="device-settings-coverage">',
        f'<summary>AC. Device Settings Coverage <span class="summary-count">— {summary}</span></summary>',
        '<div class="details-content">',
        '<p>Settings the pipeline configures automatically (from CUCM <code>productSpecificConfiguration</code>) '
        'vs settings that require manual action in Control Hub after migration.</p>',
        '<table>',
        '<thead><tr>'
        '<th>Model Family</th>'
        '<th class="num">Phones</th>'
        '<th>Automated Settings</th>'
        '<th>Manual Settings</th>'
        '<th class="num">Overrides</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for family in sorted(family_phone_counts.keys()):
        phone_count = family_phone_counts[family]
        automated = _AUTOMATED_SETTINGS_BY_FAMILY.get(family, ["Line keys", "Language"])
        manual = _MANUAL_SETTINGS_BY_FAMILY.get(family, ["Wallpaper", "Network VLAN"])
        overrides = family_override_counts.get(family, 0)
        automated_str = ", ".join(automated)
        manual_str = ", ".join(manual)
        unmappable = family_unmappable.get(family, [])
        if unmappable:
            manual_str += f"; also unmappable from CUCM: {', '.join(unmappable)}"
        parts.append(
            f'<tr>'
            f'<td><strong>{html.escape(family)}</strong></td>'
            f'<td class="num">{phone_count}</td>'
            f'<td>{html.escape(automated_str)}</td>'
            f'<td>{html.escape(manual_str)}</td>'
            f'<td class="num">{overrides}</td>'
            f'</tr>'
        )

    parts.extend(['</tbody></table>'])

    # Callout for manual steps
    parts.append(
        '<div class="callout">'
        '<p><strong>Manual Control Hub steps required post-migration:</strong> '
        'Wallpaper images, Wi-Fi credentials, and Bluetooth pairing must be configured '
        'directly in Control Hub or via device configuration templates. These settings '
        'cannot be extracted from CUCM automatically.</p>'
        '</div>'
    )

    parts.extend(['</div></details>'])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# AD. Feature Forwarding Status
# ---------------------------------------------------------------------------

def _feature_forwarding_status(store: MigrationStore) -> str:
    """AD. Feature Forwarding Status — AA/HG/CQ with forwarding configuration gaps."""
    feature_rows: list[dict] = []

    # Hunt groups: check for forwarding destinations from CUCM
    for hg in store.get_objects("hunt_group"):
        name = hg.get("name") or strip_canonical_id(hg.get("canonical_id", ""))
        pre = hg.get("pre_migration_state") or {}

        # CUCM forwarding: forwardHuntNoAnswer, forwardHuntBusy on hunt pilot
        cucm_fwd_no_answer = _axl_str(pre.get("forwardHuntNoAnswer", {}).get("destination") if isinstance(pre.get("forwardHuntNoAnswer"), dict) else pre.get("forwardHuntNoAnswer"))
        cucm_fwd_busy = _axl_str(pre.get("forwardHuntBusy", {}).get("destination") if isinstance(pre.get("forwardHuntBusy"), dict) else pre.get("forwardHuntBusy"))
        has_cucm_fwd = bool(cucm_fwd_no_answer or cucm_fwd_busy)

        # Webex: check canonical fields populated by FeatureMapper
        webex_fwd_dest = hg.get("forward_no_answer_destination") or hg.get("forward_busy_destination") or hg.get("forward_always_destination")
        has_webex_fwd = bool(webex_fwd_dest)

        gap = has_cucm_fwd and not has_webex_fwd
        feature_rows.append({
            "name": name,
            "type": "Hunt Group",
            "has_cucm_fwd": has_cucm_fwd,
            "cucm_detail": cucm_fwd_no_answer or cucm_fwd_busy or "",
            "has_webex_fwd": has_webex_fwd,
            "gap": gap,
        })

    # Call queues: check queue_full_destination, max_wait_time_destination, etc.
    for cq in store.get_objects("call_queue"):
        name = cq.get("name") or strip_canonical_id(cq.get("canonical_id", ""))
        pre = cq.get("pre_migration_state") or {}

        # CUCM forwarding on queueCalls
        queue_calls = pre.get("queueCalls") or {}
        if isinstance(queue_calls, dict):
            cucm_full = _axl_str(queue_calls.get("queueFullDestination"))
            cucm_wait = _axl_str(queue_calls.get("maxWaitTimeDestination"))
        else:
            cucm_full = ""
            cucm_wait = ""
        has_cucm_fwd = bool(cucm_full or cucm_wait)

        webex_fwd = cq.get("queue_full_destination") or cq.get("forward_always_destination")
        has_webex_fwd = bool(webex_fwd)

        gap = has_cucm_fwd and not has_webex_fwd
        cucm_detail = cucm_full or cucm_wait or ""
        feature_rows.append({
            "name": name,
            "type": "Call Queue",
            "has_cucm_fwd": has_cucm_fwd,
            "cucm_detail": cucm_detail,
            "has_webex_fwd": has_webex_fwd,
            "gap": gap,
        })

    # Auto attendants: check callForwardAll from CTI route point
    for aa in store.get_objects("auto_attendant"):
        name = aa.get("name") or strip_canonical_id(aa.get("canonical_id", ""))
        pre = aa.get("pre_migration_state") or {}

        cfa = pre.get("callForwardAll") or {}
        if isinstance(cfa, dict):
            cucm_dest = _axl_str(cfa.get("destination"))
        else:
            cucm_dest = _axl_str(cfa)
        has_cucm_fwd = bool(cucm_dest)

        webex_fwd = aa.get("forward_always_destination")
        has_webex_fwd = bool(webex_fwd)

        gap = has_cucm_fwd and not has_webex_fwd
        feature_rows.append({
            "name": name,
            "type": "Auto Attendant",
            "has_cucm_fwd": has_cucm_fwd,
            "cucm_detail": cucm_dest,
            "has_webex_fwd": has_webex_fwd,
            "gap": gap,
        })

    if not feature_rows:
        return ""

    gap_count = sum(1 for r in feature_rows if r["gap"])
    total = len(feature_rows)
    summary = f"{total} features checked, {gap_count} forwarding gap{'s' if gap_count != 1 else ''}"

    parts = [
        '<details id="feature-forwarding-status">',
        f'<summary>AD. Feature Forwarding Status <span class="summary-count">— {summary}</span></summary>',
        '<div class="details-content">',
        '<p>Hunt groups, call queues, and auto attendants with forwarding/overflow rules in CUCM. '
        'A Gap means CUCM had a forwarding destination configured that was not mapped to Webex — '
        'these features will use Webex defaults for overflow behavior after migration.</p>',
        '<table>',
        '<thead><tr>'
        '<th>Feature Name</th>'
        '<th>Type</th>'
        '<th>CUCM Forwarding?</th>'
        '<th>Webex Configured?</th>'
        '<th>Status</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for row in sorted(feature_rows, key=lambda r: (not r["gap"], r["type"], r["name"])):
        cucm_cell = f'Yes ({html.escape(row["cucm_detail"])})' if row["cucm_detail"] else ("Yes" if row["has_cucm_fwd"] else "No")
        webex_cell = "Yes" if row["has_webex_fwd"] else "No"
        if row["gap"]:
            status_cell = '<span class="badge badge-warning">Gap</span>'
        elif row["has_cucm_fwd"] and row["has_webex_fwd"]:
            status_cell = '<span class="badge badge-success">Mapped</span>'
        else:
            status_cell = '<span class="badge badge-info">No forwarding</span>'

        parts.append(
            f'<tr>'
            f'<td>{html.escape(row["name"])}</td>'
            f'<td>{html.escape(row["type"])}</td>'
            f'<td>{cucm_cell}</td>'
            f'<td>{webex_cell}</td>'
            f'<td>{status_cell}</td>'
            f'</tr>'
        )

    parts.extend(['</tbody></table>'])

    if gap_count > 0:
        parts.append(
            '<div class="callout warning">'
            f'<p><strong>{gap_count} forwarding gap{"s" if gap_count != 1 else ""} detected.</strong> '
            'These features had overflow or forwarding rules in CUCM that could not be '
            'automatically mapped to Webex. After migration, affected features will use '
            'Webex default overflow behavior. Review each gap and configure forwarding '
            'destinations manually in Control Hub if required.</p>'
            '</div>'
        )

    parts.extend(['</div></details>'])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# AE. Workspace Settings Coverage
# ---------------------------------------------------------------------------

def _workspace_settings_coverage(store: MigrationStore) -> str:
    """AE. Workspace Settings Coverage — common-area phones with/without configured settings."""
    workspaces = store.get_objects("workspace")
    if not workspaces:
        return ""

    total = len(workspaces)
    configured = [w for w in workspaces if w.get("call_settings")]
    unconfigured = [w for w in workspaces if not w.get("call_settings")]

    summary = (
        f"{total} workspace{'s' if total != 1 else ''}, "
        f"{len(configured)} with configured settings, "
        f"{len(unconfigured)} using defaults"
    )

    parts = [
        '<details id="workspace-settings-coverage">',
        f'<summary>AE. Workspace Settings Coverage <span class="summary-count">— {summary}</span></summary>',
        '<div class="details-content">',
        '<p>Common-area phones (conference rooms, lobby phones, shared desks) mapped to Webex Workspaces. '
        'Settings count shows how many call settings were extracted from CUCM and will be configured '
        'automatically. Workspaces with 0 settings will use Webex defaults.</p>',
        '<table>',
        '<thead><tr>'
        '<th>Workspace</th>'
        '<th>Location</th>'
        '<th>License</th>'
        '<th class="num">Settings Count</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for ws in sorted(workspaces, key=lambda w: w.get("display_name") or ""):
        name = ws.get("display_name") or strip_canonical_id(ws.get("canonical_id", ""))
        loc_id = ws.get("location_id") or ws.get("location_canonical_id") or ""
        loc_obj = store.get_object(loc_id) if loc_id else None
        loc_name = loc_obj.get("name", strip_canonical_id(loc_id)) if loc_obj else (strip_canonical_id(loc_id) if loc_id else "\u2014")
        license_tier = ws.get("license_tier") or "Workspace"
        call_settings = ws.get("call_settings") or {}
        settings_count = len(call_settings)

        if settings_count == 0:
            count_cell = '<span class="muted">0 — defaults</span>'
        else:
            count_cell = str(settings_count)

        parts.append(
            f'<tr>'
            f'<td>{html.escape(name)}</td>'
            f'<td>{html.escape(loc_name)}</td>'
            f'<td>{html.escape(license_tier)}</td>'
            f'<td class="num">{count_cell}</td>'
            f'</tr>'
        )

    parts.extend(['</tbody></table>'])

    if unconfigured:
        parts.append(
            '<div class="callout">'
            f'<p><strong>{len(unconfigured)} workspace{"s" if len(unconfigured) != 1 else ""} '
            f'will use default call settings.</strong> '
            'If custom settings were configured in CUCM for these devices, review them in '
            'Control Hub after migration. Common defaults to verify: DND, call forwarding, '
            'and music on hold.</p>'
            '</div>'
        )

    parts.extend(['</div></details>'])
    return "\n".join(parts)
