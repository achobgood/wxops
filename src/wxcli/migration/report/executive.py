"""Executive summary HTML generator for CUCM assessment reports.

Generates a 2-4 page executive summary from a populated MigrationStore.
Depends on Phase A (score) and Phase B (charts, explainer, styles).

One public function: generate_executive_summary().
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.report.charts import (
    donut_chart,
    gauge_chart,
)
from wxcli.migration.report.explainer import explain_decision
from wxcli.migration.report.score import compute_complexity_score
from wxcli.migration.store import MigrationStore


# Severity ordering for sorting: CRITICAL > HIGH > MEDIUM > LOW
_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

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
}

# Object types for the inventory stat cards
_INVENTORY_TYPES = [
    ("user", "Users", "#1565C0"),
    ("device", "Devices", "#2E7D32"),
    ("hunt_group", "Hunt Groups", "#6A1B9A"),
    ("call_queue", "Call Queues", "#00838F"),
    ("auto_attendant", "Auto Attendants", "#E65100"),
    ("call_park", "Call Parks", "#AD1457"),
    ("pickup_group", "Pickup Groups", "#4E342E"),
    ("trunk", "Trunks", "#37474F"),
    ("route_group", "Route Groups", "#546E7A"),
    ("dial_plan", "Dial Plans", "#78909C"),
    ("css", "CSSes", "#5D4037"),
    ("partition", "Partitions", "#795548"),
]


def generate_executive_summary(
    store: MigrationStore,
    brand: str,
    prepared_by: str,
    cluster_name: str = "",
    cucm_version: str = "",
) -> str:
    """Generate the executive summary HTML from a populated store."""
    sections = [
        _page_headline(store, brand, cluster_name, cucm_version),
        _page_what_you_have(store),
        _page_what_needs_attention(store),
    ]

    # Page 4 is conditional: only if > 100 objects or > 3 sites
    total_objects = _total_object_count(store)
    location_count = store.count_by_type("location")
    if total_objects > 100 or location_count > 3:
        sections.append(_page_next_steps(store, brand, prepared_by))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Page 1 — The Headline (Score Hero)
# ---------------------------------------------------------------------------

def _page_headline(
    store: MigrationStore,
    brand: str,
    cluster_name: str,
    cucm_version: str,
) -> str:
    """Build Page 1: complexity gauge, summary stat bar, lead sentence."""
    result = compute_complexity_score(store)

    gauge_svg = gauge_chart(result.score, result.color, result.label)

    # Build lead sentence
    user_count = store.count_by_type("user")
    device_count = store.count_by_type("device")
    location_count = store.count_by_type("location")
    decisions = store.get_all_decisions()
    unresolved = [d for d in decisions if d.get("chosen_option") is None]

    summary_text = (
        f"The {html.escape(brand)} CUCM environment contains "
        f"{user_count} users, {device_count} devices across "
        f"{location_count} site{'s' if location_count != 1 else ''}. "
        f"The overall migration complexity is "
        f"<strong>{html.escape(result.label)}</strong> "
        f"(score: {result.score}/100)"
    )
    if unresolved:
        summary_text += (
            f" with {len(unresolved)} decision{'s' if len(unresolved) != 1 else ''} "
            f"requiring attention"
        )
    summary_text += "."

    # Environment snapshot as stat cards
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_objects = _total_object_count(store)

    snapshot_items = [
        ("Customer", html.escape(brand)),
        ("Assessment Date", now_str),
        ("Total Objects", str(total_objects)),
        ("Sites", str(location_count)),
        ("Users", str(user_count)),
        ("Devices", str(device_count)),
    ]
    if cluster_name:
        snapshot_items.insert(1, ("CUCM Cluster", html.escape(cluster_name)))
    if cucm_version:
        idx = 2 if cluster_name else 1
        snapshot_items.insert(idx, ("CUCM Version", html.escape(cucm_version)))

    # Build snapshot as a stat grid
    snapshot_cards = ['<div class="stat-grid">']
    for label, value in snapshot_items:
        snapshot_cards.append(
            f'<div class="stat-card">'
            f'<div class="stat-label">{label}</div>'
            f'<div class="stat-value">{value}</div>'
            f'</div>'
        )
    snapshot_cards.append('</div>')

    return (
        f'<section id="score" class="page-headline">\n'
        f'<h2>Migration Complexity Assessment</h2>\n'
        f'<div class="score-hero">\n'
        f'  <div class="score-gauge">\n{gauge_svg}\n  </div>\n'
        f'</div>\n'
        f'<p class="lead-sentence">{summary_text}</p>\n'
        f'<h3>Environment Snapshot</h3>\n'
        + "\n".join(snapshot_cards) + "\n"
        f'</section>'
    )


# ---------------------------------------------------------------------------
# Page 2 — What You Have
# ---------------------------------------------------------------------------

def _page_what_you_have(store: MigrationStore) -> str:
    """Build Page 2: inventory stat cards, phone donut, site table."""
    parts = [
        '<section id="inventory" class="page-inventory">',
        '<h2>What You Have</h2>',
    ]

    # Object inventory as stat cards (not bar chart)
    inventory_items = []
    for type_key, label, color in _INVENTORY_TYPES:
        count = store.count_by_type(type_key)
        if count > 0:
            inventory_items.append((label, count))

    if inventory_items:
        parts.append('<h3>Environment Overview</h3>')
        parts.append('<div class="stat-grid">')
        for label, count in inventory_items:
            parts.append(
                f'<div class="stat-card">'
                f'<div class="stat-label">{html.escape(label)}</div>'
                f'<div class="stat-value">{count}</div>'
                f'</div>'
            )
        parts.append('</div>')

    # Phone compatibility donut chart
    devices = store.get_objects("device")
    if devices:
        native = sum(1 for d in devices if d.get("compatibility_tier") == "native_mpp")
        convertible = sum(1 for d in devices if d.get("compatibility_tier") == "convertible")
        incompatible = sum(1 for d in devices if d.get("compatibility_tier") == "incompatible")

        segments = [
            {"label": "Native MPP", "value": native, "color": "#2E7D32"},
            {"label": "Convertible", "value": convertible, "color": "#F57C00"},
            {"label": "Incompatible", "value": incompatible, "color": "#C62828"},
        ]

        parts.append('<h3>Phone Compatibility</h3>')
        parts.append('<div class="chart-container"><div>')
        parts.append(donut_chart(segments))
        parts.append('</div></div>')

    # Site breakdown table
    locations = store.get_objects("location")
    if locations:
        parts.append('<h3>Site Breakdown</h3>')
        site_rows = _build_site_breakdown(store, locations)
        parts.append(_build_table(
            headers=["Site", "Users", "Devices", "Decisions", "Complexity"],
            rows=site_rows,
        ))

    parts.append('</section>')
    return "\n".join(parts)


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
        loc_name = loc.get("name", loc_id)

        user_count = sum(1 for u in all_users if u.get("location_id") == loc_id)
        loc_user_ids = {u.get("canonical_id") for u in all_users if u.get("location_id") == loc_id}
        device_count = sum(1 for d in all_devices if d.get("owner_canonical_id") in loc_user_ids)
        loc_decision_count = _count_decisions_for_location(store, decisions, loc_id, loc_user_ids)

        if loc_decision_count == 0:
            complexity = '<span class="badge badge-direct">Straightforward</span>'
        elif loc_decision_count <= 2:
            complexity = '<span class="badge badge-approx">Moderate</span>'
        else:
            complexity = '<span class="badge badge-decision">Complex</span>'

        rows.append((
            html.escape(loc_name),
            str(user_count),
            str(device_count),
            str(loc_decision_count),
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


# ---------------------------------------------------------------------------
# Page 3 — What Needs Attention
# ---------------------------------------------------------------------------

def _page_what_needs_attention(store: MigrationStore) -> str:
    """Build Page 3: decision stat cards, top decisions as callouts, feature table with badges."""
    decisions = store.get_all_decisions()
    parts = [
        '<section id="decisions" class="page-decisions">',
        '<h2>What Needs Attention</h2>',
    ]

    # Decision summary as three colored stat cards
    auto_resolved = sum(1 for d in decisions if d.get("chosen_option") is not None)
    unresolved = [d for d in decisions if d.get("chosen_option") is None]
    critical = sum(
        1 for d in unresolved
        if d.get("severity", "").upper() == "CRITICAL"
    )
    needs_decision = len(unresolved) - critical

    parts.append('<h3>Decision Summary</h3>')
    parts.append('<div class="stat-grid">')
    parts.append(
        f'<div class="stat-card success">'
        f'<div class="stat-label">Auto-resolved</div>'
        f'<div class="stat-value">{auto_resolved}</div>'
        f'</div>'
    )
    parts.append(
        f'<div class="stat-card warning">'
        f'<div class="stat-label">Decisions Needed</div>'
        f'<div class="stat-value">{needs_decision}</div>'
        f'</div>'
    )
    parts.append(
        f'<div class="stat-card critical">'
        f'<div class="stat-label">Critical</div>'
        f'<div class="stat-value">{critical}</div>'
        f'</div>'
    )
    parts.append('</div>')

    # Top 5 unresolved decisions as callout boxes
    if unresolved:
        sorted_unresolved = sorted(
            unresolved,
            key=lambda d: _SEVERITY_ORDER.get(d.get("severity", "LOW").upper(), 99),
        )
        top_decisions = sorted_unresolved[:5]

        parts.append('<h3>Top Decisions Requiring Attention</h3>')
        for d in top_decisions:
            explained = explain_decision(
                decision_type=d["type"],
                severity=d["severity"],
                summary=d.get("summary", ""),
                context=d.get("context", {}),
            )
            severity_lower = d["severity"].lower()
            parts.append(
                f'<div class="explanation severity-{severity_lower}">\n'
                f'  <h4>{html.escape(explained["title"])} '
                f'<span class="badge badge-{severity_lower}">'
                f'{html.escape(d["severity"])}</span></h4>\n'
                f'  <p>{html.escape(explained["explanation"])}</p>\n'
                f'  <p class="reassurance">{html.escape(explained["reassurance"])}</p>\n'
                f'</div>'
            )

    # Feature mapping table with status badges
    feature_table = _build_feature_mapping_table(store, decisions)
    if feature_table:
        parts.append('<h3>Feature Mapping</h3>')
        parts.append(feature_table)

    parts.append('</section>')
    return "\n".join(parts)


def _build_feature_mapping_table(
    store: MigrationStore,
    decisions: list[dict[str, Any]],
) -> str:
    """Build a 4-column feature mapping table with status badges."""
    webex_equivalents: dict[str, str] = {
        "hunt_group": "Hunt Group",
        "call_queue": "Call Queue",
        "auto_attendant": "Auto Attendant",
        "call_park": "Call Park",
        "pickup_group": "Call Pickup",
        "paging_group": "Paging Group",
        "call_forwarding": "Per-person call forwarding",
        "monitoring_list": "Per-person monitoring list",
    }

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

        webex_equiv = webex_equivalents.get(type_key, display_name)
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


# ---------------------------------------------------------------------------
# Page 4 — Next Steps (conditional)
# ---------------------------------------------------------------------------

def _page_next_steps(
    store: MigrationStore,
    brand: str,
    prepared_by: str,
) -> str:
    """Build Page 4: prerequisites checklist and call to action."""
    decisions = store.get_all_decisions()
    unresolved = [d for d in decisions if d.get("chosen_option") is None]
    user_count = store.count_by_type("user")

    checklist_items = [
        (f"Webex Calling licenses needed: {user_count}", "Verify with Cisco"),
        (f"Phone numbers to port: {user_count}", "Confirm with carrier"),
        (f"Decisions to resolve: {len(unresolved)}",
         "Pending review" if unresolved else "Complete"),
    ]

    parts = [
        f'<section id="next-steps" class="page-next-steps">',
        '<h2>Next Steps</h2>',
        '<h3>Prerequisites Checklist</h3>',
        '<table>',
        '<thead><tr><th>Item</th><th class="num">Count</th><th>Status</th></tr></thead>',
        '<tbody>',
        f'<tr><td>Webex Calling licenses needed</td>'
        f'<td class="num">{user_count}</td>'
        f'<td>Verify with Cisco</td></tr>',
        f'<tr><td>Phone numbers to port</td>'
        f'<td class="num">{store.count_by_type("user")}</td>'
        f'<td>Confirm with carrier</td></tr>',
        f'<tr><td>Decisions to resolve</td>'
        f'<td class="num">{len(unresolved)}</td>'
        f'<td>{"Pending review" if unresolved else "Complete"}</td></tr>',
        '</tbody>',
        '</table>',
        f'<div class="callout info">'
        f'<p><strong>Ready to begin?</strong> For questions about this assessment '
        f'or to start the migration, contact <strong>{html.escape(prepared_by)}</strong>.</p>'
        f'</div>',
        '</section>',
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPORT_OBJECT_TYPES = [
    "user", "device", "location", "hunt_group", "call_queue",
    "auto_attendant", "call_park", "pickup_group", "paging_group",
    "trunk", "route_group", "dial_plan", "translation_pattern",
    "css", "partition", "shared_line", "workspace", "virtual_line",
    "operating_mode", "schedule", "voicemail_profile", "calling_permission",
]


def _total_object_count(store: MigrationStore) -> int:
    """Count all objects in the store across known report types."""
    return sum(store.count_by_type(t) for t in _REPORT_OBJECT_TYPES)


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
