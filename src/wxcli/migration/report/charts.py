"""Inline SVG chart generators for the CUCM assessment report.

Pure functions that accept data and return SVG strings.
No store dependency, no side effects.
All SVGs are inline-safe for HTML embedding (no JavaScript).
"""

from __future__ import annotations

import math

_FONT = 'font-family="Inter, system-ui, sans-serif"'
_XMLNS = 'xmlns="http://www.w3.org/2000/svg"'


# ---------------------------------------------------------------------------
# 1. Gauge chart — 240-degree arc for complexity score
# ---------------------------------------------------------------------------

def gauge_chart(score: int, color: str, label: str) -> str:
    """Return an SVG gauge chart showing a score from 0-100.

    The gauge is a 240-degree arc (from 150 degrees to 390 degrees,
    i.e. 7-o'clock to 5-o'clock). A gray background arc shows the full
    range; a colored foreground arc shows the proportion filled.

    Args:
        score: Integer 0-100.
        color: Hex color for the foreground arc (e.g. "#2E7D32").
        label: Text label below the score (e.g. "Straightforward").

    Returns:
        SVG string.
    """
    score = max(0, min(100, score))

    cx, cy = 100, 100
    r = 80
    stroke_width = 14
    total_angle = 240  # degrees
    start_angle = 150  # degrees (7-o'clock position)

    def _arc_endpoint(angle_deg: float) -> tuple[float, float]:
        rad = math.radians(angle_deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    def _arc_path(from_angle: float, sweep_deg: float, stroke: str, width: int = stroke_width) -> str:
        if sweep_deg <= 0:
            return ""
        x1, y1 = _arc_endpoint(from_angle)
        x2, y2 = _arc_endpoint(from_angle + sweep_deg)
        large_arc = 1 if sweep_deg > 180 else 0
        return (
            f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large_arc} 1 {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"/>'
        )

    fg_angle = total_angle * score / 100

    parts = [
        f'<svg {_XMLNS} viewBox="0 0 200 220" width="200" height="220">',
        # Background arc (full 240 degrees)
        _arc_path(start_angle, total_angle, "#E0E0E0"),
        # Foreground arc (proportional to score)
        _arc_path(start_angle, fg_angle, color),
        # Score number centered
        f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" '
        f'{_FONT} font-size="42" font-weight="700" fill="{color}">{score}</text>',
        # Label below
        f'<text x="{cx}" y="{cy + 95}" text-anchor="middle" '
        f'{_FONT} font-size="14" fill="#616161">{label}</text>',
        "</svg>",
    ]
    return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# 2. Donut chart — segment breakdown (e.g. phone compatibility)
# ---------------------------------------------------------------------------

def donut_chart(segments: list[dict]) -> str:
    """Return an SVG donut chart with legend.

    Args:
        segments: List of dicts with keys "label", "value", "color".

    Returns:
        SVG string.
    """
    total = sum(s["value"] for s in segments)

    cx, cy = 100, 100
    r = 70
    stroke_width = 30
    circumference = 2 * math.pi * r

    parts = [
        f'<svg {_XMLNS} viewBox="0 0 300 250" width="300" height="250">',
    ]

    if total == 0:
        # Empty state: just draw a gray circle
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="#E0E0E0" stroke-width="{stroke_width}"/>'
        )
    else:
        # Draw each segment using stroke-dasharray on rotated circles.
        cumulative_offset = 0.0
        for seg in segments:
            if seg["value"] <= 0:
                continue
            seg_fraction = seg["value"] / total
            seg_len = circumference * seg_fraction
            gap_len = circumference - seg_len
            # stroke-dashoffset rotates the start; we offset by cumulative.
            # SVG circles start at 3-o'clock; rotate -90 to start at 12-o'clock.
            dash_offset = circumference * 0.25 - cumulative_offset
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                f'stroke="{seg["color"]}" stroke-width="{stroke_width}" '
                f'stroke-dasharray="{seg_len:.2f} {gap_len:.2f}" '
                f'stroke-dashoffset="{dash_offset:.2f}"/>'
            )
            cumulative_offset += seg_len

    # Center label: total count
    parts.append(
        f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" '
        f'{_FONT} font-size="28" font-weight="700" fill="#212121">{total}</text>'
    )

    # Legend — to the right and below
    legend_x = 210
    legend_y = 30
    row_height = 28
    for seg in segments:
        pct = round(seg["value"] / total * 100) if total > 0 else 0
        # Color swatch
        parts.append(
            f'<rect x="{legend_x}" y="{legend_y - 10}" width="12" height="12" '
            f'rx="2" fill="{seg["color"]}"/>'
        )
        # Label + value + percentage
        parts.append(
            f'<text x="{legend_x + 18}" y="{legend_y}" '
            f'{_FONT} font-size="11" fill="#424242">'
            f'{seg["label"]}  {seg["value"]}  ({pct}%)</text>'
        )
        legend_y += row_height

    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. Horizontal bar chart — object inventory
# ---------------------------------------------------------------------------

def horizontal_bar_chart(items: list[dict]) -> str:
    """Return an SVG horizontal bar chart, sorted descending by value.

    Args:
        items: List of dicts with keys "label", "value", "color".

    Returns:
        SVG string.
    """
    sorted_items = sorted(items, key=lambda x: x["value"], reverse=True)

    row_height = 30
    padding_top = 10
    padding_bottom = 30
    label_width = 120
    value_width = 50
    bar_area_width = 300
    total_width = 500
    total_height = len(sorted_items) * row_height + padding_top + padding_bottom

    max_value = max((it["value"] for it in sorted_items), default=1)
    if max_value == 0:
        max_value = 1

    parts = [
        f'<svg {_XMLNS} viewBox="0 0 {total_width} {total_height}" '
        f'width="{total_width}" height="{total_height}">',
    ]

    for i, item in enumerate(sorted_items):
        y = padding_top + i * row_height
        bar_width = (item["value"] / max_value) * bar_area_width if max_value else 0
        text_y = y + row_height * 0.65

        # Label (right-aligned within label area)
        parts.append(
            f'<text x="{label_width - 8}" y="{text_y}" text-anchor="end" '
            f'{_FONT} font-size="12" fill="#424242">{item["label"]}</text>'
        )
        # Bar
        parts.append(
            f'<rect x="{label_width}" y="{y + 4}" '
            f'width="{bar_width:.1f}" height="{row_height - 10}" '
            f'rx="3" fill="{item["color"]}"/>'
        )
        # Value (after bar)
        parts.append(
            f'<text x="{label_width + bar_area_width + 8}" y="{text_y}" '
            f'{_FONT} font-size="12" font-weight="600" fill="#424242">{item["value"]}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 4. Traffic light boxes — decision summary
# ---------------------------------------------------------------------------

def traffic_light_boxes(auto_resolved: int, needs_decision: int, critical: int) -> str:
    """Return an SVG with three colored boxes for decision status.

    Args:
        auto_resolved: Count of auto-resolved decisions.
        needs_decision: Count of decisions needing human input.
        critical: Count of critical/blocking decisions.

    Returns:
        SVG string.
    """
    boxes = [
        {"count": auto_resolved, "label": "Auto-resolved", "color": "#2E7D32"},
        {"count": needs_decision, "label": "Decisions needed", "color": "#F57C00"},
        {"count": critical, "label": "Critical", "color": "#C62828"},
    ]

    box_width = 130
    box_height = 56
    gap = 15
    total_width = len(boxes) * box_width + (len(boxes) - 1) * gap
    viewbox_width = total_width + 20  # 10px padding each side
    viewbox_height = 100

    parts = [
        f'<svg {_XMLNS} viewBox="0 0 {viewbox_width} {viewbox_height}" '
        f'width="{viewbox_width}" height="{viewbox_height}">',
    ]

    for i, box in enumerate(boxes):
        x = 10 + i * (box_width + gap)
        # Rounded rectangle
        parts.append(
            f'<rect x="{x}" y="4" width="{box_width}" height="{box_height}" '
            f'rx="6" fill="{box["color"]}"/>'
        )
        # Count number centered in box
        parts.append(
            f'<text x="{x + box_width / 2}" y="40" text-anchor="middle" '
            f'{_FONT} font-size="24" font-weight="700" fill="#FFFFFF">{box["count"]}</text>'
        )
        # Label below box
        parts.append(
            f'<text x="{x + box_width / 2}" y="{4 + box_height + 18}" text-anchor="middle" '
            f'{_FONT} font-size="11" fill="#616161">{box["label"]}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
