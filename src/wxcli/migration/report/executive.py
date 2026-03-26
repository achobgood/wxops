"""Executive summary HTML generator for CUCM assessment reports (v2).

Generates a 4-page narrative: Verdict → Environment → Scope → Next Steps.
Depends on score, charts, explainer, and helpers modules.

One public function: generate_executive_summary().
"""

from __future__ import annotations

import html
from typing import Any

from wxcli.migration.report.charts import donut_chart, gauge_chart, stacked_bar_chart
from wxcli.migration.report.explainer import (
    DECISION_TYPE_DISPLAY_NAMES,
    explain_decision,
    generate_key_findings,
    generate_verdict,
)
from wxcli.migration.report.helpers import friendly_site_name, strip_canonical_id
from wxcli.migration.report.score import compute_complexity_score
from wxcli.migration.store import MigrationStore


# Feature type display names
_FEATURE_DISPLAY_NAMES = {
    "hunt_group": "Hunt Group",
    "call_queue": "Call Queue",
    "auto_attendant": "Auto Attendant",
    "call_park": "Call Park",
    "pickup_group": "Pickup Group",
    "paging_group": "Paging Group",
    "call_forwarding": "Call Forwarding",
    "monitoring_list": "BLF / Monitoring",
    "line_key_template": "Phone Button Templates",
    "softkey_config": "Softkey Templates",
}

# Webex equivalents for feature types
_WEBEX_EQUIVALENTS = {
    "hunt_group": "Hunt Group",
    "call_queue": "Call Queue",
    "auto_attendant": "Auto Attendant",
    "call_park": "Call Park",
    "pickup_group": "Call Pickup",
    "paging_group": "Paging Group",
    "call_forwarding": "Per-person call forwarding",
    "monitoring_list": "Per-person monitoring list",
    "line_key_template": "Line Key Templates",
    "softkey_config": "Programmable Softkeys (PSK)",
}

# Object types for counts
_REPORT_OBJECT_TYPES = [
    "user", "device", "location", "hunt_group", "call_queue",
    "auto_attendant", "call_park", "pickup_group", "paging_group",
    "trunk", "route_group", "dial_plan", "translation_pattern",
    "css", "partition", "shared_line", "workspace", "virtual_line",
    "operating_mode", "schedule", "voicemail_profile", "calling_permission",
]


def generate_executive_summary(
    store: MigrationStore,
    brand: str,
    prepared_by: str,
    cluster_name: str = "",
    cucm_version: str = "",
) -> str:
    """Generate the 4-page executive summary HTML from a populated store."""
    sections = [
        _page_verdict(store, brand, cluster_name, cucm_version),
        _page_environment(store, brand, cluster_name, cucm_version),
        _page_scope(store),
        _page_next_steps(store, brand, prepared_by),
    ]
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Page 1 — The Verdict
# ---------------------------------------------------------------------------

def _page_verdict(store: MigrationStore, brand: str, cluster_name: str = "", cucm_version: str = "") -> str:
    """Page 1: Answer 'should I be worried?' in 5 seconds."""
    result = compute_complexity_score(store)
    gauge_svg = gauge_chart(result.score, result.color, result.label)
    verdict_text = generate_verdict(result, store)
    findings = generate_key_findings(store)

    parts = [
        f'<section id="score">',
        f'<h2>Migration Complexity Assessment</h2>',
        f'<div class="verdict">{verdict_text}</div>',
    ]

    # Score layout: gauge left, factor bars right
    parts.append('<div class="score-layout">')
    parts.append(f'<div class="score-gauge">\n{gauge_svg}\n</div>')

    if result.factors:
        sorted_factors = sorted(result.factors, key=lambda f: f["raw_score"], reverse=True)
        parts.append('<div class="score-breakdown">')
        for i, factor in enumerate(sorted_factors):
            display = factor.get("display_name", factor["name"])
            raw = factor["raw_score"]
            color = "var(--primary)" if i == 0 and raw > 0 else "var(--slate-400)"
            parts.append(
                f'<div class="factor-row">'
                f'<span class="factor-label">{html.escape(display)}</span>'
                f'<div class="factor-bar">'
                f'<div class="factor-fill" style="width:{raw}%;background:{color};"></div>'
                f'</div>'
                f'<span class="factor-value">{raw}</span>'
                f'</div>'
            )
        parts.append('</div>')
    parts.append('</div>')  # close score-layout

    # Key findings
    if findings:
        parts.append('<ul class="key-findings">')
        for f in findings:
            icon_class = "check" if f["icon"] == "✓" else "alert"
            icon_text = "✓" if f["icon"] == "✓" else "!"
            parts.append(
                f'<li>'
                f'<span class="finding-icon {icon_class}">{icon_text}</span>'
                f'<span>{f["text"]}</span>'
                f'</li>'
            )
        parts.append('</ul>')

    # Stat grid
    total_objects = _total_object_count(store)
    parts.append('<div class="stat-grid">')
    parts.append(_stat_card(html.escape(brand), "Customer"))
    if cluster_name:
        parts.append(_stat_card(html.escape(cluster_name), "CUCM Cluster"))
    if cucm_version:
        parts.append(_stat_card(html.escape(cucm_version), "CUCM Version"))
    parts.append(_stat_card(str(total_objects), "Total Objects"))
    parts.append(_stat_card(str(store.count_by_type("location")), "Sites"))
    parts.append(_stat_card(str(store.count_by_type("user")), "Users"))
    parts.append(_stat_card(str(len(store.get_objects("device"))), "Devices"))
    parts.append('</div>')

    parts.append('</section>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Page 2 — Your Environment
# ---------------------------------------------------------------------------

def _page_environment(
    store: MigrationStore,
    brand: str,
    cluster_name: str,
    cucm_version: str,
) -> str:
    """Page 2: Four semantic groups — People, Devices, Call Features, Sites."""
    user_count = store.count_by_type("user")
    device_count = len(store.get_objects("device"))
    location_count = store.count_by_type("location")

    parts = [
        f'<section id="inventory">',
        f'<h2>What You Have</h2>',
    ]

    # --- People ---
    shared_line_count = store.count_by_type("shared_line")
    line_count = store.count_by_type("line")

    parts.append('<h3>People</h3>')
    parts.append('<div class="stat-grid">')
    parts.append(_stat_card(str(user_count), "Users"))
    if shared_line_count:
        parts.append(_stat_card(str(shared_line_count), "Shared Lines"))
    if line_count:
        parts.append(_stat_card(str(line_count), "Extensions"))
    parts.append('</div>')

    # --- Devices ---
    devices = store.get_objects("device")
    if devices:
        total = len(devices)
        native = sum(1 for d in devices if d.get("compatibility_tier") == "native_mpp")
        convertible = sum(1 for d in devices if d.get("compatibility_tier") == "convertible")
        incompatible = sum(1 for d in devices if d.get("compatibility_tier") == "incompatible")

        parts.append('<h3>Devices</h3>')
        parts.append('<div class="stat-grid">')
        parts.append(_stat_card(str(total), "Total Phones"))
        parts.append(_stat_card(str(native), "Native MPP"))
        if convertible:
            parts.append(_stat_card(str(convertible), "Convertible"))
        if incompatible:
            parts.append(_stat_card(str(incompatible), "Incompatible"))
        parts.append('</div>')

        # Donut chart for device compatibility (replaces stacked bar)
        donut_segments = [
            {"label": "Native MPP", "value": native, "color": "#2E7D32"},
            {"label": "Convertible", "value": convertible, "color": "#EF6C00"},
            {"label": "Incompatible", "value": incompatible, "color": "#C62828"},
        ]
        donut_svg = donut_chart(donut_segments)
        if donut_svg:
            parts.append(f'<div class="chart-container">{donut_svg}</div>')

    # --- Analog Gateways (if present) ---
    gateways = store.get_objects("gateway")
    if gateways:
        analog_count = 0
        estimated_ports = 0
        for gw in gateways:
            state = gw.get("pre_migration_state", {})
            product = (state.get("product", "") or "").upper()
            protocol = (state.get("protocol", "") or "").upper()
            is_analog = protocol in ("MGCP", "H.323", "H323") or any(
                kw in product for kw in ("VG", "ATA", "ISR", "FXS", "FXO")
            )
            if is_analog:
                analog_count += 1
                # Quick port estimate from product name
                for model, ports in [("ATA 191", 2), ("ATA 192", 2), ("VG310", 24),
                                     ("VG350", 48), ("VG400", 8), ("VG450", 200)]:
                    if model.upper() in product:
                        estimated_ports += ports
                        break

        if analog_count > 0:
            port_text = f" with an estimated <strong>{estimated_ports} ports</strong>" if estimated_ports else ""
            parts.append(
                f'<div class="callout warning">'
                f'<p><strong>{analog_count} analog gateway{"s" if analog_count != 1 else ""}</strong>'
                f'{port_text} serving fax, paging, and analog devices. '
                f'Each port requires manual mapping to a Webex workspace with ATA provisioning. '
                f'See Gateway &amp; Analog Port Review in the Technical Appendix.</p>'
                f'</div>'
            )

    # --- Call Features ---
    feature_types = ["hunt_group", "call_queue", "auto_attendant",
                     "call_park", "pickup_group", "paging_group",
                     "call_forwarding", "monitoring_list"]
    feature_data = []
    for ft in feature_types:
        count = store.count_by_type(ft)
        if count > 0:
            feature_data.append((ft, _FEATURE_DISPLAY_NAMES.get(ft, ft), count))

    if feature_data:
        parts.append('<h3>Call Features</h3>')
        parts.append('<div class="stat-grid">')
        for ft, display, count in feature_data:
            parts.append(_stat_card(str(count), display))
        parts.append('</div>')

    # Feature mapping table with badges
    feature_table = _build_feature_mapping_table(store)
    if feature_table:
        parts.append(feature_table)

    # --- Sites ---
    locations = store.get_objects("location")
    if locations:
        parts.append('<h3>Sites</h3>')
        site_rows = _build_site_breakdown(store, locations)
        parts.append(_build_table(
            headers=["Site", "Users", "Devices", "Complexity"],
            rows=site_rows,
        ))

    parts.append('</section>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Page 3 — Migration Scope (Effort Bands)
# ---------------------------------------------------------------------------

def _page_scope(store: MigrationStore) -> str:
    """Page 3: Three effort bands — auto, planning, manual."""
    decisions = store.get_all_decisions()

    # Decision summary stat grid
    total_decisions = len(decisions)
    resolved = sum(1 for d in decisions if d.get("chosen_option"))
    unresolved = total_decisions - resolved
    critical = sum(1 for d in decisions if d.get("severity", "").upper() == "CRITICAL")

    auto, planning, manual = _classify_decisions(decisions)

    parts = [
        f'<section id="decisions">',
        f'<h2>What Needs Attention</h2>',
    ]

    parts.append('<div class="stat-grid">')
    parts.append(_stat_card(str(resolved), "Auto-resolved"))
    parts.append(_stat_card(str(unresolved), "Decisions Needed"))
    if critical:
        parts.append(_stat_card(str(critical), "Critical"))
    parts.append('</div>')

    # Effort band: Migrates Automatically
    parts.append('<div class="effort-band auto">')
    parts.append(f'<h4>Migrates Automatically</h4>')
    parts.append(f'<p>{len(auto)} items migrate with no manual intervention.</p>')
    if auto:
        parts.append('<ul>')
        for d in auto[:5]:
            display_type = DECISION_TYPE_DISPLAY_NAMES.get(d["type"], d["type"])
            summary = d.get("summary", "")
            parts.append(f'<li><strong>{html.escape(display_type)}:</strong> {html.escape(summary)}</li>')
        if len(auto) > 5:
            parts.append(f'<li><em>...and {len(auto) - 5} more</em></li>')
        parts.append('</ul>')
    parts.append('</div>')

    # Effort band: Needs Planning
    parts.append('<div class="effort-band planning">')
    parts.append(f'<h4>Needs Planning</h4>')
    parts.append(f'<p>{len(planning)} items need configuration decisions during planning.</p>')
    if planning:
        parts.append('<ul>')
        for d in planning[:5]:
            display_type = DECISION_TYPE_DISPLAY_NAMES.get(d["type"], d["type"])
            summary = d.get("summary", "")
            parts.append(f'<li><strong>{html.escape(display_type)}:</strong> {html.escape(summary)}</li>')
        if len(planning) > 5:
            parts.append(f'<li><em>...and {len(planning) - 5} more</em></li>')
        parts.append('</ul>')
    parts.append('</div>')

    # Effort band: Requires Manual Work
    parts.append('<div class="effort-band manual">')
    parts.append(f'<h4>Requires Manual Work</h4>')
    parts.append(f'<p>{len(manual)} items require manual configuration or hardware changes.</p>')
    if manual:
        parts.append('<ul>')
        for d in manual[:5]:
            display_type = DECISION_TYPE_DISPLAY_NAMES.get(d["type"], d["type"])
            summary = d.get("summary", "")
            parts.append(f'<li><strong>{html.escape(display_type)}:</strong> {html.escape(summary)}</li>')
        if len(manual) > 5:
            parts.append(f'<li><em>...and {len(manual) - 5} more</em></li>')
        parts.append('</ul>')
    parts.append('</div>')

    # Decision resolution bar
    total = len(decisions)
    resolved = sum(1 for d in decisions if d.get("chosen_option"))
    if total > 0:
        pct = round(resolved / total * 100)
        parts.append(
            f'<p style="font-size:0.85rem;color:var(--color-text-muted);">'
            f'Decision resolution: <strong>{resolved} of {total}</strong> auto-resolved ({pct}%)</p>'
        )

    parts.append('</section>')
    return "\n".join(parts)


def _classify_decisions(
    decisions: list[dict[str, Any]],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Classify decisions into auto/planning/manual effort bands.

    Returns:
        (auto_resolved, needs_planning, requires_manual) — three lists.
    """
    auto = []
    planning = []
    manual = []

    # Types that typically require manual work
    manual_types = {"DEVICE_INCOMPATIBLE", "VOICEMAIL_INCOMPATIBLE", "MISSING_DATA"}
    # Types that need planning decisions
    planning_types = {
        "CSS_ROUTING_MISMATCH", "CALLING_PERMISSION_MISMATCH", "LOCATION_AMBIGUOUS",
        "SHARED_LINE_COMPLEX", "EXTENSION_CONFLICT", "DN_AMBIGUOUS",
        "WORKSPACE_TYPE_UNCERTAIN", "WORKSPACE_LICENSE_TIER",
        "HOTDESK_DN_CONFLICT", "NUMBER_CONFLICT", "DUPLICATE_USER",
    }

    for d in decisions:
        if d.get("chosen_option"):
            auto.append(d)
        elif d.get("type") in manual_types:
            manual.append(d)
        elif d.get("type") in planning_types:
            planning.append(d)
        elif d.get("severity", "").upper() in ("CRITICAL", "HIGH"):
            manual.append(d)
        else:
            planning.append(d)

    return auto, planning, manual


# ---------------------------------------------------------------------------
# Page 4 — Next Steps
# ---------------------------------------------------------------------------

def _page_next_steps(
    store: MigrationStore,
    brand: str,
    prepared_by: str,
) -> str:
    """Page 4: Prerequisites, planning phase items, CTA."""
    decisions = store.get_all_decisions()
    unresolved = [d for d in decisions if d.get("chosen_option") is None]
    user_count = store.count_by_type("user")
    device_count = len(store.get_objects("device"))

    parts = [
        f'<section id="next-steps">',
        f'<h2>Next Steps</h2>',
    ]

    # Before Migration
    parts.append('<h3>Before Migration</h3>')
    parts.append('<table>')
    parts.append('<thead><tr><th>Item</th><th class="num">Count</th><th>Status</th></tr></thead>')
    parts.append('<tbody>')
    parts.append(
        f'<tr><td>Webex Calling licenses needed</td>'
        f'<td class="num">{user_count}</td>'
        f'<td>Verify with Cisco</td></tr>'
    )
    parts.append(
        f'<tr><td>Phone numbers to port</td>'
        f'<td class="num">{user_count}</td>'
        f'<td>Confirm with carrier</td></tr>'
    )
    parts.append(
        f'<tr><td>Decisions to resolve</td>'
        f'<td class="num">{len(unresolved)}</td>'
        f'<td>{"Pending review" if unresolved else "Complete"}</td></tr>'
    )
    parts.append('</tbody></table>')

    # Planning Phase
    if unresolved:
        parts.append('<h3>Planning Phase</h3>')
        parts.append(f'<p>{len(unresolved)} decisions need review before migration can proceed:</p>')
        parts.append('<ul>')
        # Group by type
        type_counts: dict[str, int] = {}
        for d in unresolved:
            dt = d.get("type", "UNKNOWN")
            type_counts[dt] = type_counts.get(dt, 0) + 1
        for dt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            display = DECISION_TYPE_DISPLAY_NAMES.get(dt, dt)
            parts.append(f'<li>{html.escape(display)}: {count}</li>')
        parts.append('</ul>')

    # CTA box
    parts.append(
        f'<div class="cta-box">'
        f'<h3>Ready to Plan</h3>'
        f'<p>For questions about this assessment or to start the migration planning engagement, '
        f'contact <strong>{html.escape(prepared_by)}</strong>.</p>'
        f'</div>'
    )

    parts.append('</section>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stat_card(value: str, label: str) -> str:
    """Render a stat card HTML fragment."""
    return (
        f'<div class="stat-card">'
        f'<div class="stat-number">{html.escape(value)}</div>'
        f'<div class="stat-label">{html.escape(label)}</div>'
        f'</div>'
    )


def _build_site_breakdown(
    store: MigrationStore,
    locations: list[dict[str, Any]],
) -> list[tuple[str, ...]]:
    """Build per-site breakdown rows."""
    decisions = store.get_all_decisions()
    all_users = store.get_objects("user")
    all_devices = store.get_objects("device")
    rows = []

    for loc in locations:
        loc_id = loc.get("canonical_id", "")
        loc_name = loc.get("name", "")
        if not loc_name:
            loc_name = strip_canonical_id(loc_id)
        friendly = friendly_site_name(loc_name) if loc_name.startswith("DP-") else loc_name

        user_count = sum(1 for u in all_users if u.get("location_id") == loc_id)
        loc_user_ids = {u.get("canonical_id") for u in all_users if u.get("location_id") == loc_id}
        device_count = sum(1 for d in all_devices if d.get("owner_canonical_id") in loc_user_ids)
        loc_decisions = _count_decisions_for_location(store, decisions, loc_id, loc_user_ids)

        if loc_decisions == 0:
            complexity = '<span class="badge badge-direct">Straightforward</span>'
        elif loc_decisions <= 2:
            complexity = '<span class="badge badge-approx">Moderate</span>'
        else:
            complexity = '<span class="badge badge-decision">Complex</span>'

        rows.append((
            html.escape(friendly),
            str(user_count),
            str(device_count),
            complexity,
        ))

    return rows


def _count_decisions_for_location(
    store: MigrationStore,
    decisions: list[dict[str, Any]],
    loc_id: str,
    loc_user_ids: set[str],
) -> int:
    """Count decisions that reference a given location or its objects."""
    count = 0
    for d in decisions:
        ctx = d.get("context", {})
        obj_id = ctx.get("object_id", "")
        css_id = ctx.get("css_id", "")

        if obj_id:
            obj = store.get_object(obj_id)
            if obj and obj.get("location_id") == loc_id:
                count += 1
            elif obj_id in loc_user_ids:
                count += 1
        elif css_id:
            count += 1
    return count


def _build_feature_mapping_table(
    store: MigrationStore,
) -> str:
    """Build feature mapping table with Direct/Approximation badges."""
    decisions = store.get_all_decisions()
    approx_by_object: dict[str, dict[str, Any]] = {}
    for d in decisions:
        if d["type"] == "FEATURE_APPROXIMATION":
            obj_id = d.get("context", {}).get("object_id", "")
            if obj_id:
                approx_by_object[obj_id] = d

    rows = []
    for type_key, display_name in _FEATURE_DISPLAY_NAMES.items():
        count = store.count_by_type(type_key)
        if count == 0:
            continue

        webex_equiv = _WEBEX_EQUIVALENTS.get(type_key, display_name)
        has_approx = False
        has_unresolved = False

        objects = store.get_objects(type_key)
        for obj in objects:
            obj_id = obj.get("canonical_id", "")
            if obj_id in approx_by_object:
                has_approx = True
                d = approx_by_object[obj_id]
                ctx_webex = d.get("context", {}).get("webex_feature", "")
                if ctx_webex:
                    webex_equiv = ctx_webex
                if d.get("chosen_option") is None:
                    has_unresolved = True

        if not has_approx:
            status = '<span class="badge badge-direct">Direct</span>'
        elif has_unresolved:
            status = '<span class="badge badge-decision">Decision needed</span>'
        else:
            status = '<span class="badge badge-approx">Approximation</span>'

        rows.append((
            display_name,
            str(count),
            html.escape(webex_equiv),
            status,
        ))

    if not rows:
        return ""

    return _build_table(
        headers=["CUCM Feature", "Count", "Webex Equivalent", "Status"],
        rows=rows,
    )


def _build_table(
    headers: list[str],
    rows: list[tuple[str, ...]],
) -> str:
    """Build an HTML table from headers and row tuples."""
    parts = ['<table>']
    parts.append('<thead><tr>')
    for h in headers:
        parts.append(f'<th>{html.escape(h)}</th>')
    parts.append('</tr></thead>')
    parts.append('<tbody>')
    for row in rows:
        parts.append('<tr>')
        for cell in row:
            parts.append(f'<td>{cell}</td>')
        parts.append('</tr>')
    parts.append('</tbody>')
    parts.append('</table>')
    return "\n".join(parts)


def _total_object_count(store: MigrationStore) -> int:
    """Count all objects in the store across known report types."""
    return sum(store.count_by_type(t) for t in _REPORT_OBJECT_TYPES)
