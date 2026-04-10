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
| `styles.py` | `REPORT_CSS` + `GOOGLE_FONTS_LINKS` — v4 editorial CSS design system. Lora/Source Sans 3/IBM Plex Mono, teal primary (#00897B), warm neutrals, 320px sidebar, score-layout 2-column grid, effort-band/verdict/cta-box components, print optimization. Legacy CSS variable aliases for backward compat. |
| `executive.py` | 4-page executive summary with direct h2 headings (no section kickers). Page 1 (Migration Complexity Assessment — tier-colored gauge+factor bars with "Complexity Impact" Low/High scale, key findings, stat grid), Page 2 (What You Have — People/Devices with floated donut chart/Features/Sites), Page 3 (What Needs Attention — decision stats + effort bands: auto/planning/manual), Page 4 (Next Steps — prerequisites, planning, CTA). Gauge uses tier-based color (green/amber/red). Factor bars sorted by score descending, highest in teal, rest gray, no bare numbers. |
| `appendix.py` | Technical appendix: 22 lettered sections A-V as collapsed `<details>` elements (Object Inventory, Decision Detail, CSS/Partitions, Device Inventory, DN Analysis, User/Device Map, Routing, Voicemail, Data Coverage, Gateways, Call Features, Button Templates, Device Layouts, Softkeys, O. Cloud-Managed Resources, P. Feature Gaps, Q. Manual Reconfiguration, R. Planning Inputs, S. Call Recording, T. Single Number Reach, U. Caller ID Transformations, V. Extension Mobility). All canonical IDs stripped via helpers. |
| `assembler.py` | Full HTML document with 320px sidebar nav (step-icon circles, numbered 1-4 exec + lettered A-V tech), page-header (slate-900 bg), IntersectionObserver scroll tracking, no summary bar or dark interstitial, footer inside detail-panel. |

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
- `"webex_app"` — software phone transitioning to Webex App (no device needed)
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

## CSS Design System (v4 — Editorial + v3 Data)

Design philosophy: Warm editorial design merged with v3's data-rich components. Combines v1's Lora/Source Sans typography and teal primary with v3's score-layout, effort-bands, and data tables.

- **Typography:** Lora (display/headings, serif) + Source Sans 3 (body, sans-serif) + IBM Plex Mono (data) via Google Fonts. 17px base. Headings: Lora semibold (600).
- **Layout (screen):** Slate-900 page-header + 320px white sidebar (sticky, right border) with step-icon circles (teal exec, gray tech) + scrolling detail-panel. Score section uses 2-column grid (gauge left, factor bars right). IntersectionObserver highlights active nav on scroll.
- **Colors:** Primary teal #00897B, Success #2E7D32, Warning #EF6C00, Critical #C62828. Warm neutral bg #fdf8f3. Slate text hierarchy (#242a33 / #636e7e / #8e97a5). Legacy aliases map to new tokens.
- **Heading pattern:** Direct h2 topic headings (no section kickers). H2 has border-bottom warm-200.
- **Chart language:** Teal for focal data (highest-scoring factor), slate-400 for the rest. Gauge arc uses tier-based color (green/amber/red from `result.color`). Factor bars have "Complexity Impact" scale header with Low/High labels (no bare numbers). Donut chart floated right in executive Section 2 (`.env-donut`, 420px), stacked bar in appendix device section.
- **Components:** `.score-layout` (2-col grid), `.step-item` / `.step-icon` (sidebar nav), `.effort-band` (left-border + tint bg), `.score-breakdown` (factor bars + `.factor-scale` header), `.key-findings`, `.verdict`, `.cta-box`, `.stat-card` (warm-100 bg), `.env-donut` (floated right), `.callout`, `.badge-*`, `.css-topology` (nested list with teal dots)
- **Print:** Sidebar/page-header hidden, `<details>` forced open, page breaks between sections, 9.5pt font size, footer fixed to bottom
- **Tables:** No vertical borders, uppercase small headers, warm-200 bottom borders, hover: warm-100
- **Legacy aliases:** `--color-primary`, `--color-success`, `--color-warning`, `--color-critical`, `--color-text`, `--color-text-muted`, `--color-text-light`, `--color-bg`, `--color-border` all alias to v4 tokens so charts.py and explainer.py work without changes.

Google Fonts loaded via `GOOGLE_FONTS_LINKS` constant in `styles.py`, injected by `assembler.py` in `<head>`.

## Known Polish Items (Future Iteration)

These were identified during the v4 visual review and deferred:

- **Stat card zero values:** "0" for Native MPP still renders — should suppress zero-count stat cards
- **Print optimization:** Not re-verified after v4 changes — needs a print-to-PDF test pass
- **Logo/partner branding:** `--logo` flag not yet implemented
- **Score calibration:** No real CUCM environments tested yet — manual validation needed

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
- `tests/migration/report/test_appendix_tier3.py` — Tier 3 informational appendix sections O-R
- `tests/migration/report/test_tier4_appendix.py` — Tier 4 appendix sections S-V (recording, SNR, transformations, extension mobility)
- `tests/migration/report/test_cli_integration.py` — CLI command integration

## Design Spec

- **v1 spec:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md` — strategic context, competitive analysis
- **v2 spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v2-design.md` — narrative redesign, effort bands, customer-centric layout (content structure — still authoritative)
- **v3 spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v3-visual-design.md` — "Authority Minimal" visual redesign (superseded by v4)
- **v4 spec:** `docs/superpowers/specs/2026-03-26-assessment-report-v4-design.md` — merges v1 editorial warmth with v3 data richness
- **v4 plan:** `docs/superpowers/plans/2026-03-26-assessment-report-v4.md` — 6-task implementation plan

v4 merges v1's warm editorial design (Lora serif, Source Sans 3, teal primary, warm neutrals, 320px sidebar with step-icons) with v3's data components (score-layout, effort-bands, decision stats). The v3 "Authority Minimal" style (IBM Plex, navy+blue, dark sidebar) was too corporate — the editorial warmth better matches the SE-to-customer delivery context.

Future SaaS platform plan: `docs/plans/cucm-assess-saas-future.md`
