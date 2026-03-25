# report/ — CUCM Migration Assessment Reports

Generates professional HTML/PDF assessment reports from the CUCM migration pipeline's SQLite store. Designed for Sales Engineers to hand to customers showing that CUCM-to-Webex migration isn't as hard as they think.

**Strategic purpose:** Prevent customers from migrating to Microsoft Teams by demystifying the migration path with data-backed evidence.

## How It Works

```
SQLite store (post-analyze) → score.py → charts.py + explainer.py → executive.py + appendix.py → assembler.py → HTML/PDF
```

The report reads from the same SQLite store that the migration pipeline populates. It does NOT modify the store — it's a read-only view. The `wxcli cucm report` CLI command generates the report after running `discover → normalize → map → analyze`.

## Files

| File | Purpose |
|------|---------|
| `helpers.py` | Customer-facing text formatting: `strip_canonical_id()` (removes internal prefixes), `friendly_site_name()` (DP-HQ-Phones → HQ). |
| `ingest.py` | Reads collector output files (.json.gz/.json) into discovery raw_data format. Maps AXL object names to extractor group keys. |
| `score.py` | Migration Complexity Score (0-100). 7 weighted factors with `display_name` field (customer-friendly names). Returns `ScoreResult` dataclass. `DISPLAY_NAMES` maps internal factor names → display names. |
| `charts.py` | SVG/HTML chart generators: `gauge_chart()` (compact 200x155 viewBox), `donut_chart()`, `horizontal_bar_chart()`, `stacked_bar_chart()` (HTML divs with legend). Pure functions, no store dependency. |
| `explainer.py` | Translates `DecisionType` + context into plain-English dicts. Also: `generate_verdict()` (one-paragraph summary), `generate_key_findings()` (3-4 bullet findings), `DECISION_TYPE_DISPLAY_NAMES` (20 types mapped). |
| `styles.py` | `REPORT_CSS` + `GOOGLE_FONTS_LINKS` — v2 CSS design system with sidebar layout, effort bands, score breakdown bars, key findings, tech interstitial, contrast-compliant text, print optimization. |
| `executive.py` | 4-page executive summary: Page 1 (Assessment Verdict — gauge, factor bars, key findings), Page 2 (Your Environment — People/Devices/Features/Sites), Page 3 (Migration Scope — effort bands: auto/planning/manual), Page 4 (Next Steps — prerequisites, planning, CTA). |
| `appendix.py` | Technical appendix: 8 collapsed `<details>` topic groups (People, Devices, Call Features, Routing, Call Forwarding, Speed Dials & Monitoring, Decisions, Data Quality). Decisions grouped by type with aggregated counts. All canonical IDs stripped via helpers. |
| `assembler.py` | Full HTML document with sidebar nav (4 exec + 6 tech items), summary bar, dark interstitial between exec/appendix, max-width 720px content area, print header. |

## Key Data Access Patterns

### Store API

- `store.count_by_type("user")` → `int` — count of objects by type
- `store.get_objects("device")` → `list[dict]` — deserialized dicts (NOT Pydantic models)
- `store.get_all_decisions()` → `list[dict]` — all decisions with `type`, `severity`, `chosen_option`, `context`, `options`
- `store.get_cross_refs(relationship="css_contains_partition")` → `list[dict]` — cross-reference edges

### Device Compatibility

`compatibility_tier` is a **lowercase string** in store dicts, not the enum:
- `"native_mpp"` — direct migration
- `"convertible"` — needs firmware flash
- `"incompatible"` — needs hardware replacement

### CSS/Partition Types

CSS and partition are intermediate object types using the `canonical_id` prefix convention:
- `css:CSS-Internal`, `partition:PT-Internal`
- Query with `store.count_by_type("css")` / `store.get_objects("css")`

### ScoreResult

`ScoreResult` is a dataclass (not a dict):
```python
from wxcli.migration.report.score import compute_complexity_score, ScoreResult
result = compute_complexity_score(store)
result.score   # int, 0-100
result.label   # "Straightforward" | "Moderate" | "Complex"
result.color   # "#2E7D32" | "#F57C00" | "#C62828"
result.factors # list[dict] with keys: name, display_name, weight, raw_score, weighted_score, detail
```

Thresholds: 0-30 green, 31-55 amber, 56-100 red.

## Chart Functions

All chart functions HTML-escape labels internally — do NOT double-escape.

```python
from wxcli.migration.report.charts import gauge_chart, donut_chart, horizontal_bar_chart, stacked_bar_chart

gauge_chart(score=34, color="#2E7D32", label="Straightforward")  # → SVG string (compact 200x155)
donut_chart([{"label": "Native MPP", "value": 40, "color": "#2E7D32"}, ...])  # → SVG string
horizontal_bar_chart([{"label": "Users", "value": 50, "color": "#0277BD"}, ...])  # → SVG string
stacked_bar_chart([{"label": "Native", "value": 40, "color": "#2E7D32"}, ...])  # → HTML divs
```

## Explainer

```python
from wxcli.migration.report.explainer import (
    explain_decision, generate_verdict, generate_key_findings,
    DECISION_TYPE_DISPLAY_NAMES,
)

result = explain_decision(
    decision_type="CSS_ROUTING_MISMATCH",
    severity="HIGH",          # must be LOW/MEDIUM/HIGH/CRITICAL (case-insensitive)
    summary="CSS-0 routing scope differs",
    context={"css_name": "CSS-Dallas", "partitions": ["PT-Internal", "PT-LD"]}
)
# Returns: {"title": "...", "explanation": "...", "reassurance": "..."}

verdict = generate_verdict(score_result, store)  # → HTML string with <strong> tags
findings = generate_key_findings(store)  # → list of {"icon": "!"/"✓", "text": "..."}
```

Handles all 20 `DecisionType` values. `DECISION_TYPE_DISPLAY_NAMES` maps all types to customer-friendly names.

## Helpers

```python
from wxcli.migration.report.helpers import strip_canonical_id, friendly_site_name

strip_canonical_id("css:Standard-CSS")  # → "Standard-CSS"
strip_canonical_id("dn:1001:PT-Internal")  # → "1001 (PT-Internal)"
friendly_site_name("DP-HQ-Phones")  # → "HQ"
```

## CSS Design System

- **Typography:** Inter via `<link>` tags (`GOOGLE_FONTS_LINKS`), fallback to `system-ui`
- **Layout (screen):** Sidebar nav (280px fixed, dark) + scrolling detail panel (max-width 720px)
- **Colors:** Primary #00897B (Webex teal), Success #2E7D32, Warning #EF6C00, Critical #C62828. Text #1a1f25 / muted #4a5363 (WCAG AA)
- **Components:** `.effort-band` (auto/planning/manual), `.score-breakdown` (factor bars), `.key-findings`, `.verdict`, `.cta-box`, `.tech-interstitial` (dark bar), `.stat-card`, `.callout`, `.badge-direct`/`.badge-approx`/`.badge-decision`
- **Print:** Sidebar hidden, `.print-header` shown, `<details>` forced open, page breaks between sections
- **Tables:** Editorial style (no zebra stripes, uppercase headers, subtle borders)
- **Appendix:** `<details>/<summary>` with `.summary-count` spans, `.details-content` wrapper

Google Fonts loaded via `GOOGLE_FONTS_LINKS` constant in `styles.py`, injected by `assembler.py` in `<head>`.

## CLI Usage

```bash
# After running the pipeline:
wxcli cucm report --brand "Customer Name" --prepared-by "SE Name"
wxcli cucm report --brand "..." --prepared-by "..." --pdf            # also generate PDF
wxcli cucm report --brand "..." --prepared-by "..." --executive-only  # skip appendix
```

Prerequisite: `analyze` stage must be complete. Does NOT require `plan` or `preflight`.

## File Ingestion (--from-file)

```bash
wxcli cucm discover --from-file customer-extract.json.gz
```

Reads collector output files and writes `raw_data.json` in the same format as live AXL extraction. The `COLLECTOR_TO_RAW_DATA_MAP` in `ingest.py` maps AXL object names (e.g., `endUser`, `phone`, `css`) to the extractor group/sub-key pairs that `normalize_discovery()` expects.

## Tests

- `tests/migration/report/conftest.py` — `populated_store` fixture (3 sites, 50 users, 45 devices, 6 decisions) + `sample_collector_file` fixture
- `tests/migration/report/test_helpers.py` — strip_canonical_id, friendly_site_name
- `tests/migration/report/test_from_file.py` — collector file ingestion
- `tests/migration/report/test_score.py` — complexity score algorithm + display_name field
- `tests/migration/report/test_charts.py` — gauge, donut, bar, stacked bar charts
- `tests/migration/report/test_explainer.py` — decision templates + verdict + key findings + type display names
- `tests/migration/report/test_executive.py` — 4-page executive summary (verdict, environment, scope, next steps)
- `tests/migration/report/test_appendix.py` — 6 topic groups, decision aggregation, no canonical IDs
- `tests/migration/report/test_assembler.py` — sidebar nav, dark interstitial, summary bar, max-width
- `tests/migration/report/test_e2e.py` — end-to-end pipeline (ingest → normalize → map → analyze → report)
- `tests/migration/report/test_cli_integration.py` — CLI command integration

## Design Spec

- **v1 spec:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md` — strategic context, competitive analysis
- **v2 spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v2-design.md` — narrative redesign, effort bands, customer-centric layout
- **v2 plan:** `docs/superpowers/plans/2026-03-25-assessment-report-v2.md` — 10-task implementation plan

Future SaaS platform plan: `docs/plans/cucm-assess-saas-future.md`
