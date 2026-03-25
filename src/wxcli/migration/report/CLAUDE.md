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
| `ingest.py` | Reads collector output files (.json.gz/.json) into discovery raw_data format. Maps AXL object names to extractor group keys. |
| `score.py` | Migration Complexity Score (0-100). 7 weighted factors: CSS complexity (25%), feature parity (20%), device compatibility (15%), decision density (15%), scale (10%), shared lines (10%), routing (5%). Returns `ScoreResult` dataclass. |
| `charts.py` | 4 inline SVG generators: `gauge_chart()`, `donut_chart()`, `horizontal_bar_chart()`, `traffic_light_boxes()`. Pure functions, no store dependency. |
| `explainer.py` | Translates `DecisionType` + context into plain-English `{"title", "explanation", "reassurance"}` dicts. Covers all 16 decision types. |
| `styles.py` | `REPORT_CSS` string constant — full CSS design system. Webex teal palette, Inter font, print-optimized `@page` rules. |
| `executive.py` | Executive summary HTML (2-4 pages). Complexity score gauge, object inventory bar chart, phone compatibility donut, site breakdown, decision summary with plain-English explanations, feature mapping table. |
| `appendix.py` | Technical appendix HTML (variable length, scales with environment size). 9 conditional `<details>/<summary>` sections: object inventory, decision detail, CSS/partition analysis, device inventory, DN analysis, user-device-line map, routing topology, voicemail analysis, data coverage. |
| `assembler.py` | Wraps executive + appendix in a complete self-contained HTML document with embedded CSS. Supports `executive_only` flag. |

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
result.factors # list[dict] with keys: name, weight, raw_score, weighted_score, detail
```

Thresholds: 0-30 green, 31-55 amber, 56-100 red.

## Chart Functions

All chart functions HTML-escape labels internally — do NOT double-escape.

```python
from wxcli.migration.report.charts import gauge_chart, donut_chart, horizontal_bar_chart, traffic_light_boxes

gauge_chart(score=34, color="#2E7D32", label="Straightforward")  # → SVG string
donut_chart([{"label": "Native MPP", "value": 40, "color": "#2E7D32"}, ...])  # → SVG string
horizontal_bar_chart([{"label": "Users", "value": 50, "color": "#0277BD"}, ...])  # → SVG string
traffic_light_boxes(auto_resolved=5, needs_decision=3, critical=1)  # → SVG string
```

## Explainer

```python
from wxcli.migration.report.explainer import explain_decision

result = explain_decision(
    decision_type="CSS_ROUTING_MISMATCH",
    severity="HIGH",          # must be LOW/MEDIUM/HIGH/CRITICAL (case-insensitive)
    summary="CSS-0 routing scope differs",
    context={"css_name": "CSS-Dallas", "partitions": ["PT-Internal", "PT-LD"]}
)
# Returns: {"title": "...", "explanation": "...", "reassurance": "..."}
```

Handles all 16 `DecisionType` values. Falls back to summary text when context fields are missing.

## CSS Design System

- **Typography:** Inter (via Google Fonts `@import`), fallback to `system-ui, sans-serif`
- **Colors:** Primary #00BCB4 (Webex teal), Success #2E7D32, Warning #F57C00, Critical #C62828, Neutral #37474F
- **Print:** `@page { size: letter; margin: 0.75in; }`, forced page breaks before `<section>` elements
- **Tables:** Zebra striping (#F5F5F5 alternating), header row #37474F with white text
- **Appendix:** `<details>/<summary>` collapsible sections, all expanded in `@media print`

The `@import` for Google Fonts is the first rule in `REPORT_CSS` — if wrapping CSS, ensure it stays first.

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

- `tests/migration/report/conftest.py` — `populated_store` fixture (3 sites, 50 users, 45 devices, 5 decisions) + `sample_collector_file` fixture
- `tests/migration/report/test_from_file.py` — collector file ingestion
- `tests/migration/report/test_score.py` — complexity score algorithm
- `tests/migration/report/test_charts.py` — SVG chart generation
- `tests/migration/report/test_explainer.py` — plain-English decision templates
- `tests/migration/report/test_executive.py` — executive summary HTML
- `tests/migration/report/test_appendix.py` — technical appendix HTML
- `tests/migration/report/test_assembler.py` — full report assembly
- `tests/migration/report/test_e2e.py` — end-to-end pipeline (ingest → normalize → map → analyze → report)

## Design Spec

Full design spec with strategic context, competitive analysis (vs. Yarnlab Wrangler), report content specification, and open-source packaging strategy: `docs/superpowers/specs/2026-03-24-cucm-assess-design.md`

Future SaaS platform plan: `docs/plans/cucm-assess-saas-future.md`
