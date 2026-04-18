# src/wxcli/org_health/report.py
"""HTML report generator for org health assessment.

Reuses CSS design system and chart functions from the migration report module.

Usage:
    python3.14 -m wxcli.org_health.report <results-dir> --brand "Name" --prepared-by "SE"
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import sys
from datetime import datetime
from pathlib import Path

from wxcli.migration.report.styles import REPORT_CSS, GOOGLE_FONTS_LINKS
from wxcli.migration.report.charts import horizontal_bar_chart
from wxcli.org_health.models import CategoryScore, Finding, HealthResult, OrgStats

SEVERITY_COLORS = {
    "HIGH": "#C62828",
    "MEDIUM": "#EF6C00",
    "LOW": "#F9A825",
    "INFO": "#0277BD",
}

SEVERITY_ORDER = ["HIGH", "MEDIUM", "LOW", "INFO"]

CATEGORY_ORDER = ["security", "routing", "feature_utilization", "device_health"]

CATEGORY_ICONS = {
    "security": "🛡",
    "routing": "🔀",
    "feature_utilization": "📊",
    "device_health": "📱",
}


def generate_report(result: HealthResult, *, brand: str, prepared_by: str) -> str:
    parts = [
        _html_head(brand),
        _page_header(brand, prepared_by, result.collected_at),
        _org_overview(result.stats),
        _summary_cards(result.categories),
    ]
    for cat_key in CATEGORY_ORDER:
        cat = result.categories.get(cat_key)
        if cat:
            parts.append(_category_section(cat))
    parts.append(_footer(result))
    parts.append("</div></body></html>")
    return "\n".join(parts)


def _html_head(brand: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_mod.escape(brand)} — Org Health Assessment</title>
{GOOGLE_FONTS_LINKS}
<style>
{REPORT_CSS}
{_EXTRA_CSS}
</style>
</head>
<body>
<div class="detail-panel" style="margin-left:0; max-width:960px; margin:0 auto; padding:2rem;">"""


_EXTRA_CSS = """
/* Org health report additions */
.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 2rem 0; }
.summary-card { background: var(--warm-50, #fdf8f3); border: 1px solid var(--warm-200, #f0dcc6);
    border-radius: 8px; padding: 1.25rem; }
.summary-card h3 { font-family: 'Lora', serif; font-size: 1.1rem; margin-bottom: 0.75rem; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
    font-weight: 600; color: white; margin-right: 4px; }
.badge-high { background: #C62828; }
.badge-medium { background: #EF6C00; }
.badge-low { background: #F9A825; color: #333; }
.badge-info { background: #0277BD; }
.finding-card { border-left: 4px solid; padding: 1rem 1.25rem; margin: 1rem 0;
    background: white; border-radius: 0 6px 6px 0; }
.finding-card.severity-high { border-color: #C62828; }
.finding-card.severity-medium { border-color: #EF6C00; }
.finding-card.severity-low { border-color: #F9A825; }
.finding-card.severity-info { border-color: #0277BD; }
.finding-title { font-weight: 600; margin-bottom: 0.5rem; }
.finding-detail { color: var(--slate-600, #636e7e); margin-bottom: 0.75rem; }
.recommendation { background: var(--warm-50, #fdf8f3); border: 1px solid var(--warm-200, #f0dcc6);
    border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.9rem; }
.recommendation strong { color: var(--primary, #00897B); }
.affected-table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.85rem; }
.affected-table th { text-align: left; text-transform: uppercase; font-size: 0.7rem;
    letter-spacing: 0.05em; color: var(--slate-500, #8e97a5); padding: 4px 8px;
    border-bottom: 1px solid var(--warm-200, #f0dcc6); }
.affected-table td { padding: 4px 8px; border-bottom: 1px solid var(--warm-100, #f9efe4); }
.stat-strip { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }
.checkmark-box { text-align: center; padding: 2rem; color: var(--primary, #00897B); }
.checkmark-box .check { font-size: 2rem; }
"""


def _page_header(brand: str, prepared_by: str, collected_at: str) -> str:
    try:
        date_str = datetime.fromisoformat(collected_at.replace("Z", "+00:00")).strftime("%B %d, %Y")
    except (ValueError, AttributeError):
        date_str = collected_at
    return f"""
<div class="page-header" style="background: var(--slate-900, #0f1419); color: white;
    padding: 2.5rem; border-radius: 8px; margin-bottom: 2rem;">
  <h1 style="font-family: 'Lora', serif; font-size: 1.8rem; margin-bottom: 0.25rem;">
    {html_mod.escape(brand)}</h1>
  <p style="font-size: 1.1rem; opacity: 0.85; margin-bottom: 1rem;">
    Webex Calling Org Health Assessment</p>
  <p style="font-size: 0.85rem; opacity: 0.6;">
    {date_str} &middot; Prepared by {html_mod.escape(prepared_by)}</p>
</div>"""


def _org_overview(stats: OrgStats) -> str:
    cards = [
        ("Users", stats.total_users),
        ("Devices", stats.total_devices),
        ("Locations", stats.total_locations),
        ("Features", stats.total_auto_attendants + stats.total_call_queues + stats.total_hunt_groups),
    ]
    items = []
    for label, value in cards:
        items.append(f"""<div class="stat-card" style="flex:1; min-width:120px;">
  <div style="font-size:1.8rem; font-weight:700; font-family:'IBM Plex Mono',monospace;">
    {value}</div>
  <div style="font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em;
    color:var(--slate-500,#8e97a5);">{label}</div>
</div>""")
    return f'<div class="stat-strip">{"".join(items)}</div>'


def _summary_cards(categories: dict[str, CategoryScore]) -> str:
    cards = []
    for cat_key in CATEGORY_ORDER:
        cat = categories.get(cat_key)
        if not cat:
            continue
        total = cat.high_count + cat.medium_count + cat.low_count + cat.info_count
        icon = CATEGORY_ICONS.get(cat_key, "")
        if total == 0:
            badge_html = '<span style="color:var(--primary,#00897B);font-weight:600;">✓ No issues found</span>'
        else:
            badges = []
            if cat.high_count:
                badges.append(f'<span class="badge badge-high">{cat.high_count} HIGH</span>')
            if cat.medium_count:
                badges.append(f'<span class="badge badge-medium">{cat.medium_count} MEDIUM</span>')
            if cat.low_count:
                badges.append(f'<span class="badge badge-low">{cat.low_count} LOW</span>')
            if cat.info_count:
                badges.append(f'<span class="badge badge-info">{cat.info_count} INFO</span>')
            badge_html = " ".join(badges)
        cards.append(f"""<div class="summary-card">
  <h3>{icon} {html_mod.escape(cat.display_name)}</h3>
  {badge_html}
</div>""")
    return f'<div class="summary-grid">{"".join(cards)}</div>'


def _category_section(cat: CategoryScore) -> str:
    total = cat.high_count + cat.medium_count + cat.low_count + cat.info_count
    icon = CATEGORY_ICONS.get(cat.category, "")
    parts = [f'<h2 style="margin-top:2.5rem;">{icon} {html_mod.escape(cat.display_name)}</h2>']

    if total == 0:
        parts.append('<div class="checkmark-box"><div class="check">✓</div><p>No issues found</p></div>')
        return "\n".join(parts)

    chart_items = []
    for sev in SEVERITY_ORDER:
        count = getattr(cat, f"{sev.lower()}_count", 0)
        if count > 0:
            chart_items.append({"label": sev, "value": count, "color": SEVERITY_COLORS[sev]})
    if chart_items:
        parts.append(horizontal_bar_chart(chart_items))

    sorted_findings = sorted(cat.findings, key=lambda f: SEVERITY_ORDER.index(f.severity))
    for finding in sorted_findings:
        parts.append(_render_finding(finding))

    return "\n".join(parts)


def _render_finding(finding: Finding) -> str:
    sev_class = f"severity-{finding.severity.lower()}"
    sev_badge = f'<span class="badge badge-{finding.severity.lower()}">{finding.severity}</span>'

    parts = [f'<div class="finding-card {sev_class}">']
    parts.append(f'<div class="finding-title">{sev_badge} {html_mod.escape(finding.title)}</div>')
    parts.append(f'<div class="finding-detail">{html_mod.escape(finding.detail)}</div>')

    if finding.affected_items:
        parts.append(_render_affected_table(finding.affected_items))

    parts.append(f'<div class="recommendation"><strong>Recommendation:</strong> {html_mod.escape(finding.recommendation)}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def _render_affected_table(items: list[dict]) -> str:
    if not items:
        return ""
    columns = list(items[0].keys())
    header = "".join(f"<th>{html_mod.escape(c)}</th>" for c in columns)
    rows = []
    for item in items[:20]:  # cap at 20 rows
        cells = "".join(f"<td>{html_mod.escape(str(item.get(c, '')))}</td>" for c in columns)
        rows.append(f"<tr>{cells}</tr>")
    overflow = ""
    if len(items) > 20:
        overflow = f'<tr><td colspan="{len(columns)}" style="text-align:center;color:var(--slate-500);">... and {len(items) - 20} more</td></tr>'
    return f'<table class="affected-table"><thead><tr>{header}</tr></thead><tbody>{"".join(rows)}{overflow}</tbody></table>'


def _footer(result: HealthResult) -> str:
    sample_note = ""
    if result.stats.sampled_users_for_permissions > 0:
        sample_note = f"<p>Outgoing permissions sampled from {result.stats.sampled_users_for_permissions} users.</p>"
    return f"""
<hr style="margin-top:3rem; border:none; border-top:1px solid var(--warm-200,#f0dcc6);">
<footer style="padding:1.5rem 0; font-size:0.8rem; color:var(--slate-500,#8e97a5);">
  <p>Generated {result.collected_at}</p>
  {sample_note}
  <p>This report is a point-in-time snapshot. Configuration changes after collection are not reflected.</p>
</footer>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate org health HTML report")
    parser.add_argument("results_dir", type=Path, help="Path to results/ directory")
    parser.add_argument("--brand", required=True, help="Customer/org brand name")
    parser.add_argument("--prepared-by", required=True, help="Name of person generating report")
    args = parser.parse_args()

    results_path = args.results_dir / "results.json"
    if not results_path.exists():
        print(f"ERROR: results.json not found in {args.results_dir}", file=sys.stderr)
        return 1

    data = json.loads(results_path.read_text())
    result = _deserialize_result(data)

    report_dir = args.results_dir.parent / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "org-health-report.html"

    html = generate_report(result, brand=args.brand, prepared_by=args.prepared_by)
    report_path.write_text(html)
    print(f"Report written to {report_path}")
    return 0


def _deserialize_result(data: dict) -> HealthResult:
    findings = [
        Finding(**{k: v for k, v in f.items()})
        for f in data.get("findings", [])
    ]
    categories = {}
    for cat_key, cat_data in data.get("categories", {}).items():
        cat_findings = [
            Finding(**{k: v for k, v in f.items()})
            for f in cat_data.get("findings", [])
        ]
        categories[cat_key] = CategoryScore(
            category=cat_data["category"],
            display_name=cat_data["display_name"],
            high_count=cat_data["high_count"],
            medium_count=cat_data["medium_count"],
            low_count=cat_data["low_count"],
            info_count=cat_data["info_count"],
            findings=cat_findings,
        )
    stats_data = data.get("stats", {})
    stats = OrgStats(**{k: v for k, v in stats_data.items()})
    return HealthResult(
        org_name=data["org_name"],
        org_id=data["org_id"],
        collected_at=data["collected_at"],
        categories=categories,
        findings=findings,
        stats=stats,
    )


if __name__ == "__main__":
    sys.exit(main())
