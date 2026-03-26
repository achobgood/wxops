"""Technical appendix HTML generator for CUCM assessment reports (v2).

Generates 10 topic groups, each as a collapsed <details> element:
People, Devices, Call Features, Routing, Gateways, Button Templates,
Device Layouts, Softkeys, Decisions, Data Quality.

One public function: generate_appendix().
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

from wxcli.migration.report.explainer import (
    DECISION_TYPE_DISPLAY_NAMES,
    explain_decision,
)
from wxcli.migration.report.helpers import friendly_site_name, strip_canonical_id
from wxcli.migration.store import MigrationStore


def generate_appendix(store: MigrationStore) -> str:
    """Generate the technical appendix HTML with topic groups."""
    groups = [
        _people_group(store),
        _devices_group(store),
        _features_group(store),
        _routing_group(store),
        _gateways_group(store),
        _button_template_group(store),
        _device_layout_group(store),
        _softkey_group(store),
        _decisions_group(store),
        _data_quality_group(store),
    ]
    # Filter out empty groups
    groups = [g for g in groups if g]
    if not groups:
        return '<section id="appendix"></section>'

    return (
        '<section id="appendix">\n'
        + "\n".join(groups)
        + "\n</section>"
    )


# ---------------------------------------------------------------------------
# Group 1: People
# ---------------------------------------------------------------------------

def _people_group(store: MigrationStore) -> str:
    """Users, shared lines, extensions."""
    user_count = store.count_by_type("user")
    if user_count == 0:
        return ""

    shared_count = store.count_by_type("shared_line")
    line_count = store.count_by_type("line")

    summary_parts = [f"{user_count} users"]
    if shared_count:
        summary_parts.append(f"{shared_count} shared lines")
    if line_count:
        summary_parts.append(f"{line_count} extensions")

    parts = [
        f'<details id="people">',
        f'<summary>People <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
        '<div class="details-content">',
    ]

    # User-device-line map (from cross-refs)
    user_device_refs = store.get_cross_refs(relationship="user_has_device")
    if user_device_refs:
        parts.append('<h4>User–Device–Line Map</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>User</th><th>Device</th><th>Model</th><th>Line</th><th>Partition</th></tr></thead>')
        parts.append('<tbody>')

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

            # Get lines for this device
            device_line_refs = store.get_cross_refs(
                relationship="device_has_dn",
                from_id=device_id,
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

                    # Get partition from dn_in_partition cross-ref if not on object
                    if not partition:
                        dn_pt_refs = store.get_cross_refs(
                            relationship="dn_in_partition",
                            from_id=line_id,
                        )
                        if dn_pt_refs:
                            partition = strip_canonical_id(dn_pt_refs[0].get("to_id", ""))

                    parts.append(
                        f'<tr>'
                        f'<td>{html.escape(user_name)}</td>'
                        f'<td>{html.escape(strip_canonical_id(device_id))}</td>'
                        f'<td>{html.escape(model)}</td>'
                        f'<td>{html.escape(line_ext)}</td>'
                        f'<td>{html.escape(partition)}</td>'
                        f'</tr>'
                    )
            else:
                parts.append(
                    f'<tr>'
                    f'<td>{html.escape(user_name)}</td>'
                    f'<td>{html.escape(strip_canonical_id(device_id))}</td>'
                    f'<td>{html.escape(model)}</td>'
                    f'<td>—</td><td>—</td>'
                    f'</tr>'
                )

        parts.append('</tbody></table>')

    # DN classification breakdown
    lines = store.get_objects("line")
    if lines:
        parts.append('<h4>Extension Analysis</h4>')
        classification_counts: dict[str, int] = defaultdict(int)
        for line in lines:
            cls = line.get("classification", "UNKNOWN")
            if hasattr(cls, "value"):
                cls = cls.value
            classification_counts[str(cls)] += 1

        parts.append('<table>')
        parts.append('<thead><tr><th>Classification</th><th class="num">Count</th></tr></thead>')
        parts.append('<tbody>')
        for cls, count in sorted(classification_counts.items(), key=lambda x: -x[1]):
            parts.append(f'<tr><td>{html.escape(cls)}</td><td class="num">{count}</td></tr>')
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Group 2: Devices
# ---------------------------------------------------------------------------

def _devices_group(store: MigrationStore) -> str:
    """Device inventory by model and compatibility tier."""
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
    incompatible = sum(1 for d in devices if d.get("compatibility_tier") == "incompatible")

    summary = f"{total} phones — {native} native, {convertible} convertible, {incompatible} incompatible"

    parts = [
        f'<details id="devices">',
        f'<summary>Devices <span class="summary-count">— {summary}</span></summary>',
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
        for tier_name in ["native_mpp", "convertible", "incompatible"]:
            if tiers.get(tier_name, 0) > 0:
                tier_list.append(f'{tier_name.replace("_", " ").title()}: {tiers[tier_name]}')
        tier_str = ", ".join(tier_list) if tier_list else "Unknown"

        parts.append(
            f'<tr><td>{html.escape(model)}</td>'
            f'<td class="num">{total_model}</td>'
            f'<td>{html.escape(tier_str)}</td></tr>'
        )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Group 3: Call Features
# ---------------------------------------------------------------------------

def _features_group(store: MigrationStore) -> str:
    """Feature inventory with counts."""
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
        f'<details id="features">',
        f'<summary>Call Features <span class="summary-count">— {total} features across {len(feature_rows)} types</span></summary>',
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
# Group 4: Routing
# ---------------------------------------------------------------------------

def _routing_group(store: MigrationStore) -> str:
    """Trunks, route groups, dial plans, CSS/partition topology."""
    trunk_count = store.count_by_type("trunk")
    rg_count = store.count_by_type("route_group")
    dp_count = store.count_by_type("dial_plan")
    tp_count = store.count_by_type("translation_pattern")
    css_count = store.count_by_type("css")
    pt_count = store.count_by_type("partition")

    total = trunk_count + rg_count + dp_count + tp_count + css_count + pt_count
    if total == 0:
        return ""

    summary_parts = []
    if trunk_count:
        summary_parts.append(f"{trunk_count} trunks")
    if css_count:
        summary_parts.append(f"{css_count} CSSes")
    if pt_count:
        summary_parts.append(f"{pt_count} partitions")
    if dp_count:
        summary_parts.append(f"{dp_count} dial plans")

    parts = [
        f'<details id="routing">',
        f'<summary>Routing <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
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

    # CSS / Partition topology
    css_objects = store.get_objects("css")
    if css_objects:
        parts.append('<h4>CSS / Partition Topology</h4>')
        parts.append('<ul class="css-topology">')
        for css in css_objects:
            css_id = css.get("canonical_id", "")
            css_name = strip_canonical_id(css_id)
            parts.append(f'<li>{html.escape(css_name)}')

            # Get partitions
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
# Group 5: Gateways & Analog Ports
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
    # ISR with NIM — can't estimate without slot info
    if "ISR" in product.upper():
        return None
    return None


def _gateways_group(store: MigrationStore) -> str:
    """Gateway & analog port review."""
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
        # Only SIP gateways — brief summary, no review needed
        summary = f"{len(gateways)} gateways — all SIP, no analog review needed"
        parts = [
            f'<details id="gateways">',
            f'<summary>Gateways <span class="summary-count">— {summary}</span></summary>',
            '<div class="details-content">',
            f'<p>{len(sip_gws)} SIP gateways detected. No analog ports requiring manual review.</p>',
            '</div></details>',
        ]
        return "\n".join(parts)

    port_note = f", ~{total_estimated_ports} estimated analog ports" if total_estimated_ports else ""
    summary = f"{len(gateways)} gateways — {len(analog_gws)} analog-capable{port_note}"

    parts = [
        f'<details id="gateways">',
        f'<summary>Gateways & Analog Ports <span class="summary-count">— {summary}</span></summary>',
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
# Group: Button Template Inventory
# ---------------------------------------------------------------------------

def _button_template_group(store: MigrationStore) -> str:
    """Phone button template inventory — template names, button types, usage counts."""
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
        f'<summary>Button Template Inventory <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
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
# Group: Device Layout Summary
# ---------------------------------------------------------------------------

def _device_layout_group(store: MigrationStore) -> str:
    """Per-device layout summary — shared lines, speed dials, BLF, KEM stats."""
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
        f'<summary>Device Layout Summary <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
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
# Group: Softkey Migration Status
# ---------------------------------------------------------------------------

def _softkey_group(store: MigrationStore) -> str:
    """Softkey template migration status — PSK mapping, classic MPP flags."""
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
        f'<details id="softkey-status">',
        f'<summary>Softkey Migration Status <span class="summary-count">— {", ".join(summary_parts)}</span></summary>',
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
# Group 6: Decisions
# ---------------------------------------------------------------------------

def _decisions_group(store: MigrationStore) -> str:
    """Decisions grouped by type with aggregated counts."""
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
        f'<details id="decisions">',
        f'<summary>Decisions <span class="summary-count">— {total} total, {resolved} auto-resolved</span></summary>',
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
# Group 6: Data Quality
# ---------------------------------------------------------------------------

def _data_quality_group(store: MigrationStore) -> str:
    """Data coverage and completeness."""
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
        f'<details id="data-quality">',
        f'<summary>Data Quality <span class="summary-count">— {types_with_data}/{total_types_checked} object types populated</span></summary>',
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
