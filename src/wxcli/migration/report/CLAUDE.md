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
| `styles.py` | `REPORT_CSS` + `GOOGLE_FONTS_LINKS` — v3 "Authority Minimal" CSS design system. IBM Plex Sans/Mono, navy+blue accent, floating white card on gray bg, 260px sidebar, inline summary bar, 2-column score layout, print optimization. Legacy CSS variable aliases for backward compat. |
| `executive.py` | 4-page executive summary with conclusion-style headings and section kickers. Page 1 (The Verdict — 2-column gauge+factor bars, key findings), Page 2 (Your Environment — People/Devices/Features/Sites), Page 3 (Migration Scope — effort bands: auto/planning/manual), Page 4 (Next Steps — prerequisites, planning, CTA). Gauge hardcoded to accent blue (#2563eb). Factor bars sorted by score descending, highest in blue, rest gray. |
| `appendix.py` | Technical appendix: 8 collapsed `<details>` topic groups (People, Devices, Call Features, Routing, Call Forwarding, Speed Dials & Monitoring, Decisions, Data Quality). Decisions grouped by type with aggregated counts. All canonical IDs stripped via helpers. |
| `assembler.py` | Full HTML document with sidebar nav (dot indicators, 4 exec + 7 tech items), fixed inline summary bar, dark interstitial between exec/appendix, content-card wrapper (max-width 960px), print header. |

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

## CSS Design System (v3 — Authority Minimal)

Design philosophy: "What if Linear designed a Deloitte report." Consulting-grade authority with modern tech aesthetics. Based on McKinsey/BCG/Bain report design research.

- **Typography:** IBM Plex Sans (body) + IBM Plex Mono (data) via Google Fonts. rem-based scale, 16px base. Headings: semibold (600), letter-spacing -0.01em.
- **Layout (screen):** 260px fixed dark sidebar + fixed inline summary bar (top) + scrolling content card (max-width 960px, white on #eef0f4 gray, border-radius 10px, layered box-shadow). Score section uses 2-column grid (gauge left, factor bars right).
- **Colors:** Accent #2563eb (corporate blue), Success #059669, Warning #d97706, Critical #dc2626. Text primary #111827 / body #374151 / muted #6b7280. Page bg #eef0f4. No teal — old `--color-primary` aliased to `--accent` for backward compat.
- **Heading pattern:** Every h2 is a conclusion statement (not a topic label). Section kickers (`.section-kicker` — small uppercase) provide the topic name above the heading.
- **Chart language:** One accent color for focal data (highest-scoring factor), gray (#94a3b8) for the rest. Score number always dark (#111827), never accent-colored. Bars sorted by score descending. Gauge arc in accent blue.
- **Components:** `.score-layout` (2-col grid), `.content-card` (floating page), `.effort-band` (left-border + tint bg), `.score-breakdown` (factor bars), `.key-findings`, `.verdict`, `.cta-box`, `.tech-interstitial`, `.stat-card`, `.callout`, `.badge-direct`/`.badge-approx`/`.badge-decision`, `.section-kicker`, `.nav-dot` (exec blue, tech gray)
- **Print:** Sidebar/summary-bar hidden, content-card loses shadow/radius, `<details>` forced open, page breaks between sections, 10pt font size
- **Tables:** No vertical borders, uppercase small headers, no zebra striping, hover: page-bg
- **Legacy aliases:** `--color-primary`, `--color-success`, `--color-warning`, `--color-critical`, `--color-text`, `--color-text-muted`, `--color-text-light`, `--color-bg`, `--color-border`, `--warm-50`, `--slate-*` all alias to new tokens so appendix.py and explainer.py work without changes.

Google Fonts loaded via `GOOGLE_FONTS_LINKS` constant in `styles.py`, injected by `assembler.py` in `<head>`.

## Known Polish Items (Future Iteration)

These were identified during the v3 visual review and deferred:

- **Section spacing:** Executive sections need more generous vertical padding between them (currently `margin-bottom: 48px`, could use 64px+)
- **Verdict callout text:** Slightly cramped — could use more line-height or padding
- **Tech interstitial inside content-card:** The dark bar is constrained by the card's border-radius and padding. Ideally it should break out to full width using negative margins.
- **Stat card zero values:** "0" for Native MPP still renders — should suppress zero-count stat cards
- **Effort band content text:** Body text inside effort bands is small (0.8rem) — bump to 0.875rem
- **Print optimization:** Not re-verified after v3 changes — needs a print-to-PDF test pass
- **Score calibration:** Gauge always uses accent blue regardless of score tier — consider returning to tier-based colors (green/amber/red) for the arc while keeping the number dark

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
- **v2 spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v2-design.md` — narrative redesign, effort bands, customer-centric layout (content structure — still authoritative)
- **v3 spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v3-visual-design.md` — "Authority Minimal" visual redesign (supersedes v2 visual sections)
- **v3 plan:** `docs/superpowers/plans/2026-03-25-assessment-report-v3-visual.md` — 6-task implementation plan
- **v3 mockups:** `.superpowers/brainstorm/38786-1774470618/content/` — comparison, design system, verdict page mockups

v3 visual redesign was driven by research into McKinsey/BCG/Deloitte consulting report design patterns. Key insight: editorial design (serif fonts, warm palette, Medium.com style) is wrong for a consulting assessment deliverable. The audience (CIO, IT Director, telecom engineer) expects authoritative precision, not literary warmth.

Future SaaS platform plan: `docs/plans/cucm-assess-saas-future.md`
