# CUCM Assessment Report Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a migration assessment report generator and file-ingestion path to the existing CUCM migration pipeline, producing a professional HTML/PDF report that Sales Engineers can hand to customers.

**Architecture:** Three new modules added to the existing `src/wxcli/migration/` tree: a complexity scorer, SVG chart generators, and an HTML report assembler. One modification to the existing `discover` CLI command adds `--from-file` ingestion. One new `report` CLI command wires everything together. The standalone collector script and `cucm-assess` PyPI wrapper are out of scope for this plan — they will be separate plans against separate repos.

**Tech Stack:** Python 3.11, existing MigrationStore (SQLite), inline SVG for charts, `@media print` CSS for PDF optimization, optional headless Chromium for `--pdf` flag.

**Spec:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md`

---

## Scope

**In scope (this plan):**
- `--from-file` flag on `wxcli cucm discover`
- Complexity score algorithm (`src/wxcli/migration/report/score.py`)
- SVG chart generators (`src/wxcli/migration/report/charts.py`)
- Executive summary HTML generator (`src/wxcli/migration/report/executive.py`)
- Technical appendix HTML generator (`src/wxcli/migration/report/appendix.py`)
- Report assembler + CSS template (`src/wxcli/migration/report/assembler.py`)
- Decision plain-English explainer (`src/wxcli/migration/report/explainer.py`)
- CLI command `wxcli cucm report` (added to `src/wxcli/commands/cucm.py`)
- Tests for all of the above

**Out of scope (separate plans):**
- `cucm-collect` standalone collector script (separate repo)
- `cucm-assess` PyPI wrapper package (separate repo)
- Visual regression testing (deferred to post-first-report)

## File Map

| File | Purpose |
|------|---------|
| **Create:** `src/wxcli/migration/report/__init__.py` | Package init |
| **Create:** `src/wxcli/migration/report/score.py` | Complexity score algorithm (7 weighted factors → 0-100) |
| **Create:** `src/wxcli/migration/report/charts.py` | SVG generators: gauge, donut, horizontal bar, traffic-light boxes |
| **Create:** `src/wxcli/migration/report/executive.py` | Executive summary HTML (pages 1-4) |
| **Create:** `src/wxcli/migration/report/appendix.py` | Technical appendix HTML (9 conditional sections) |
| **Create:** `src/wxcli/migration/report/explainer.py` | Decision type → plain-English explanation templates |
| **Create:** `src/wxcli/migration/report/assembler.py` | Combines CSS + executive + appendix into single HTML file |
| **Create:** `src/wxcli/migration/report/styles.py` | CSS template string (embedded in HTML) |
| **Modify:** `src/wxcli/commands/cucm.py` | Add `report` command + `--from-file` on `discover` |
| **Create:** `tests/migration/report/__init__.py` | Test package init |
| **Create:** `tests/migration/report/test_score.py` | Score algorithm tests |
| **Create:** `tests/migration/report/test_charts.py` | SVG chart output tests |
| **Create:** `tests/migration/report/test_executive.py` | Executive summary section tests |
| **Create:** `tests/migration/report/test_appendix.py` | Appendix section tests |
| **Create:** `tests/migration/report/test_explainer.py` | Explainer template tests |
| **Create:** `tests/migration/report/test_assembler.py` | Full report assembly tests |
| **Create:** `tests/migration/report/test_from_file.py` | File ingestion tests |
| **Create:** `tests/migration/report/conftest.py` | Shared fixtures (populated MigrationStore) |

---

### Task 1: Test Fixtures + `--from-file` Ingestion

**Files:**
- Create: `tests/migration/report/__init__.py`
- Create: `tests/migration/report/conftest.py`
- Create: `src/wxcli/migration/report/__init__.py`
- Create: `src/wxcli/migration/report/ingest.py`
- Create: `tests/migration/report/test_from_file.py`
- Modify: `src/wxcli/commands/cucm.py:374-451` (add `--from-file` to discover)

This task creates the shared test fixtures all subsequent tasks use, plus the file ingestion path that lets SEs load collector output files.

- [ ] **Step 1: Create test + report packages**

Create empty `tests/migration/report/__init__.py` and `src/wxcli/migration/report/__init__.py`.

- [ ] **Step 2: Write conftest.py with populated store fixture**

Create `tests/migration/report/conftest.py` with a `populated_store` fixture. This builds a realistic MigrationStore simulating a post-analyze state with:
- 3 locations (Dallas HQ, Austin Branch, London Office)
- 50 users across locations (25/15/10)
- 45 devices (40 native MPP CP-8845, 3 convertible CP-7841, 2 incompatible CP-7962G)
- 6 features (2 hunt groups, 1 AA, 1 call queue, 1 call park, 1 pickup group)
- Routing (2 trunks, 1 route group, 1 dial plan)
- 3 CSSes with 5 partitions, cross-refs wired
- 5 decisions (2 FEATURE_APPROXIMATION, 1 CSS_ROUTING_MISMATCH, 1 DEVICE_INCOMPATIBLE auto-resolved, 1 SHARED_LINE_COMPLEX)
- All stages marked complete through `analyze`

Also add a `sample_collector_file` fixture that writes a minimal gzipped JSON collector file to tmp_path.

Verify the store fixture methods match the actual `MigrationStore` API — read `src/wxcli/migration/store.py` for exact method signatures before writing. If `upsert_raw()` doesn't exist, construct `MigrationObject` instances and use `upsert_object()`. Note: MigrationObject subclasses require a `Provenance` field (with `source_system`, `source_id`, `source_name`, `extracted_at`) — read `src/wxcli/migration/models.py` for the exact class and include it in all fixture objects.

- [ ] **Step 3: Write failing tests for file ingestion**

Create `tests/migration/report/test_from_file.py` with tests:
- `test_ingest_collector_file_reads_gzip` — loads .json.gz, returns dict with expected keys
- `test_ingest_collector_file_reads_plain_json` — loads .json (uncompressed)
- `test_ingest_collector_file_rejects_invalid` — missing `collector_version` raises ValueError
- `test_collector_to_raw_data_mapping` — verifies key mappings match discovery.py raw_data contract

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_from_file.py -v`
Expected: FAIL — `ingest` module doesn't exist.

- [ ] **Step 5: Implement ingest.py**

Create `src/wxcli/migration/report/ingest.py` with:
- `COLLECTOR_TO_RAW_DATA_MAP` — dict mapping AXL names to `(extractor_group, sub_key)` tuples. Source for correct mappings: `src/wxcli/migration/cucm/discovery.py` lines 51-71 (DiscoveryResult.raw_data contract).
- `ingest_collector_file(file_path) -> dict` — reads .json.gz or .json, validates required keys (`collector_version`, `cucm_version`, `cluster_name`, `collected_at`, `objects`), maps collector keys to raw_data format, returns dict matching DiscoveryResult.raw_data structure.

Export both from `__init__.py`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_from_file.py -v`
Expected: All PASS.

- [ ] **Step 7: Add `--from-file` to discover CLI command**

Modify `src/wxcli/commands/cucm.py` discover function:
1. Add `from_file: Optional[str] = typer.Option(None, "--from-file", help="Path to collector file (.json.gz or .json)")` parameter
2. Make `--host`, `--username`, `--password` optional (default None) so they aren't required with `--from-file`
3. Add validation: if neither `--from-file` nor `--host` provided, print error and exit
4. When `--from-file` is set: call `ingest_collector_file()`, write result to `project_dir / "raw_data.json"`, record journal entry, mark discover stage complete, print summary of loaded objects, return early (skip AXL connection)

Read the existing discover function carefully before modifying — preserve all existing behavior for the live-AXL path.

- [ ] **Step 8: Commit**

```bash
git add src/wxcli/migration/report/ tests/migration/report/ src/wxcli/commands/cucm.py
git commit -m "feat(cucm): add --from-file ingestion + report package scaffold"
```

---

### Task 2: Complexity Score Algorithm

**Files:**
- Create: `src/wxcli/migration/report/score.py`
- Create: `tests/migration/report/test_score.py`

Pure computation — no HTML, no SVG. Takes a MigrationStore, queries it, returns a score and factor breakdown.

- [ ] **Step 1: Write failing tests for score algorithm**

Create `tests/migration/report/test_score.py`:

```python
"""Tests for migration complexity score algorithm."""
import pytest


class TestComplexityScore:
    """Score should be 0-100 with 7 weighted factors."""

    def test_score_returns_int_in_range(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        assert 0 <= result.score <= 100

    def test_score_has_seven_factors(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        assert len(result.factors) == 7

    def test_score_factors_have_required_fields(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        for factor in result.factors:
            assert "name" in factor
            assert "weight" in factor
            assert "raw_score" in factor  # 0-100 before weighting
            assert "weighted_score" in factor  # raw * weight
            assert "detail" in factor  # human-readable explanation

    def test_factor_weights_sum_to_100(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        total_weight = sum(f["weight"] for f in result.factors)
        assert total_weight == 100

    def test_score_label_straightforward(self, populated_store):
        """Fixture has moderate data — should score green or low amber."""
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        assert result.label in ("Straightforward", "Moderate")
        assert result.color in ("#2E7D32", "#F57C00")

    def test_empty_store_scores_zero(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.score import compute_complexity_score
        store = MigrationStore(tmp_path / "empty.db")
        result = compute_complexity_score(store)
        assert result.score == 0
        assert result.label == "Straightforward"

    def test_device_factor_all_native(self, populated_store):
        """With 40/45 native MPP, device factor should be low."""
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        device_factor = next(f for f in result.factors if f["name"] == "Device Compatibility")
        assert device_factor["raw_score"] < 30  # mostly native

    def test_decision_factor_scales_with_count(self, populated_store):
        """5 decisions / 50+ objects = low density."""
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        decision_factor = next(f for f in result.factors if f["name"] == "Decision Density")
        assert decision_factor["raw_score"] < 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_score.py -v`
Expected: FAIL — `score` module doesn't exist.

- [ ] **Step 3: Implement score.py**

Create `src/wxcli/migration/report/score.py`:

Key design:
- `ScoreResult` dataclass with `score: int`, `label: str`, `color: str`, `factors: list[dict]`
- `compute_complexity_score(store: MigrationStore) -> ScoreResult` — main entry point
- 7 private factor functions, each returning `(raw_score: int, detail: str)`:
  1. `_css_complexity(store)` — count CSSes, avg partitions per CSS via `css_contains_partition` cross-refs, check for CSS_ROUTING_MISMATCH and CALLING_PERMISSION_MISMATCH decisions
  2. `_feature_parity(store)` — count FEATURE_APPROXIMATION decisions relative to total features
  3. `_device_compatibility(store)` — query all device objects, count by `compatibility_tier` field in data JSON
  4. `_decision_density(store)` — total unresolved decisions / total objects * 100, log-scaled
  5. `_scale_factor(store)` — `math.log10(max(user_count, 1)) * 10`, capped at 100
  6. `_shared_line_complexity(store)` — count SHARED_LINE_COMPLEX decisions, shared line objects
  7. `_routing_complexity(store)` — count trunks, route groups, translation patterns

Weights: `[25, 20, 15, 15, 10, 10, 5]`

Label thresholds: 0-30 = "Straightforward" (#2E7D32), 31-55 = "Moderate" (#F57C00), 56-100 = "Complex" (#C62828)

Read from store using `store.count_by_type()`, `store.get_all_decisions()`, `store.get_cross_refs()`, and `store.get_objects()`. Device compatibility_tier is available directly as `obj["compatibility_tier"]` — `get_objects()` returns already-parsed dicts, no need for `json.loads()`.

Note: `store.get_objects(type)` returns `list[dict]` with the data already deserialized. `store.query_by_type(type)` returns `list[MigrationObject]` (Pydantic models). Use `get_objects()` for dict access.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_score.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/score.py tests/migration/report/test_score.py
git commit -m "feat(report): add migration complexity score algorithm"
```

---

### Task 3: SVG Chart Generators

**Files:**
- Create: `src/wxcli/migration/report/charts.py`
- Create: `tests/migration/report/test_charts.py`

Pure functions that return SVG strings. No store dependency — they take data as input.

- [ ] **Step 1: Write failing tests for charts**

Create `tests/migration/report/test_charts.py`:

```python
"""Tests for inline SVG chart generators."""
import pytest


class TestGaugeChart:
    """Circular arc gauge for the complexity score."""

    def test_gauge_returns_valid_svg(self):
        from wxcli.migration.report.charts import gauge_chart
        svg = gauge_chart(score=34, color="#2E7D32", label="Straightforward")
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert "34" in svg
        assert "Straightforward" in svg

    def test_gauge_color_matches_input(self):
        from wxcli.migration.report.charts import gauge_chart
        svg = gauge_chart(score=60, color="#C62828", label="Complex")
        assert "#C62828" in svg

    def test_gauge_arc_scales_with_score(self):
        from wxcli.migration.report.charts import gauge_chart
        svg_low = gauge_chart(score=10, color="#2E7D32", label="Easy")
        svg_high = gauge_chart(score=90, color="#C62828", label="Hard")
        # Both should be valid SVGs with different arc paths
        assert "<path" in svg_low
        assert "<path" in svg_high


class TestDonutChart:
    """Donut chart for phone compatibility breakdown."""

    def test_donut_returns_valid_svg(self):
        from wxcli.migration.report.charts import donut_chart
        segments = [
            {"label": "Native MPP", "value": 40, "color": "#2E7D32"},
            {"label": "Convertible", "value": 3, "color": "#F57C00"},
            {"label": "Incompatible", "value": 2, "color": "#C62828"},
        ]
        svg = donut_chart(segments)
        assert svg.startswith("<svg")
        assert "Native MPP" in svg
        assert "89%" in svg or "88%" in svg  # 40/45

    def test_donut_handles_single_segment(self):
        from wxcli.migration.report.charts import donut_chart
        segments = [{"label": "All Native", "value": 100, "color": "#2E7D32"}]
        svg = donut_chart(segments)
        assert "100%" in svg

    def test_donut_handles_zero_total(self):
        from wxcli.migration.report.charts import donut_chart
        segments = [{"label": "None", "value": 0, "color": "#999"}]
        svg = donut_chart(segments)
        assert "</svg>" in svg


class TestBarChart:
    """Horizontal bar chart for object inventory."""

    def test_bar_returns_valid_svg(self):
        from wxcli.migration.report.charts import horizontal_bar_chart
        items = [
            {"label": "Users", "value": 50, "color": "#0277BD"},
            {"label": "Devices", "value": 45, "color": "#0277BD"},
            {"label": "Hunt Groups", "value": 2, "color": "#00BCB4"},
        ]
        svg = horizontal_bar_chart(items)
        assert svg.startswith("<svg")
        assert "Users" in svg
        assert "50" in svg

    def test_bar_sorts_by_value(self):
        from wxcli.migration.report.charts import horizontal_bar_chart
        items = [
            {"label": "Small", "value": 2, "color": "#999"},
            {"label": "Big", "value": 100, "color": "#999"},
        ]
        svg = horizontal_bar_chart(items)
        # Big should appear before Small (sorted descending)
        big_pos = svg.index("Big")
        small_pos = svg.index("Small")
        assert big_pos < small_pos


class TestTrafficLight:
    """Traffic light boxes for decision summary."""

    def test_traffic_light_returns_valid_svg(self):
        from wxcli.migration.report.charts import traffic_light_boxes
        svg = traffic_light_boxes(auto_resolved=5, needs_decision=3, critical=1)
        assert svg.startswith("<svg")
        assert "5" in svg
        assert "3" in svg
        assert "1" in svg
        assert "#2E7D32" in svg  # green
        assert "#F57C00" in svg  # amber
        assert "#C62828" in svg  # red
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_charts.py -v`
Expected: FAIL — `charts` module doesn't exist.

- [ ] **Step 3: Implement charts.py**

Create `src/wxcli/migration/report/charts.py`:

4 public functions, each returning an SVG string:

1. `gauge_chart(score: int, color: str, label: str) -> str`
   - 240° arc (not full circle), centered. Score number inside, label below.
   - Background arc in #E0E0E0, foreground arc in `color`, proportional to score/100.
   - Use SVG `<path>` with arc commands. Calculate arc endpoint from score percentage.
   - Viewbox: 200x220 (room for label below arc).

2. `donut_chart(segments: list[dict]) -> str`
   - Each segment: `{"label": str, "value": int, "color": str}`
   - SVG donut via `stroke-dasharray` on circles with increasing `stroke-dashoffset`.
   - Center shows total count. Legend below with label, count, percentage.
   - Viewbox: 300x250.

3. `horizontal_bar_chart(items: list[dict]) -> str`
   - Each item: `{"label": str, "value": int, "color": str}`
   - Sorted descending by value. Label left, bar proportional to max, value right.
   - Dynamic height based on item count (30px per row + padding).
   - Viewbox: 500 x (items * 30 + 40).

4. `traffic_light_boxes(auto_resolved: int, needs_decision: int, critical: int) -> str`
   - Three colored rectangles side by side. Count number centered inside each.
   - Labels below: "Auto-resolved", "Decisions needed", "Critical".
   - Colors: green (#2E7D32), amber (#F57C00), red (#C62828).
   - Viewbox: 450x100.

All SVGs use `xmlns="http://www.w3.org/2000/svg"`, no JavaScript, inline-safe for HTML embedding. Font: `font-family="Inter, system-ui, sans-serif"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_charts.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/charts.py tests/migration/report/test_charts.py
git commit -m "feat(report): add inline SVG chart generators"
```

---

### Task 4: Decision Explainer

**Files:**
- Create: `src/wxcli/migration/report/explainer.py`
- Create: `tests/migration/report/test_explainer.py`

Translates machine-readable decision types into plain-English explanations for the executive summary. Each decision type gets a template that fills in context-specific details.

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_explainer.py`:

```python
"""Tests for decision plain-English explainer."""
import pytest
from wxcli.migration.models import DecisionType


class TestExplainer:
    def test_explains_all_decision_types(self):
        from wxcli.migration.report.explainer import explain_decision
        for dt in DecisionType:
            result = explain_decision(dt.value, severity="MEDIUM",
                summary="test", context={})
            assert result["title"]  # non-empty
            assert result["explanation"]  # non-empty
            assert result["reassurance"]  # non-empty

    def test_css_routing_mismatch_uses_context(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "CSS_ROUTING_MISMATCH", severity="HIGH",
            summary="CSS-0 routing scope differs",
            context={"css_name": "CSS-Dallas", "partitions": ["PT-Internal", "PT-LD"]})
        assert "CSS-Dallas" in result["title"] or "CSS-Dallas" in result["explanation"]

    def test_device_incompatible_shows_model(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "DEVICE_INCOMPATIBLE", severity="LOW",
            summary="CP-7962G is incompatible",
            context={"model": "CP-7962G", "count": 5})
        assert "7962" in result["explanation"]

    def test_feature_approximation_names_both_features(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "FEATURE_APPROXIMATION", severity="MEDIUM",
            summary="Extension Mobility maps to Hoteling",
            context={"cucm_feature": "Extension Mobility", "webex_feature": "Hoteling"})
        assert "Extension Mobility" in result["explanation"]
        assert "Hoteling" in result["explanation"]

    def test_severity_affects_tone(self):
        from wxcli.migration.report.explainer import explain_decision
        high = explain_decision("CSS_ROUTING_MISMATCH", "HIGH", "test", {})
        low = explain_decision("EXTENSION_CONFLICT", "LOW", "test", {})
        # High severity should not use minimizing language
        assert "critical" not in low["reassurance"].lower() or "minor" in low["reassurance"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_explainer.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement explainer.py**

Create `src/wxcli/migration/report/explainer.py`:

```python
"""Translate DecisionType + context into plain-English explanations.

Each decision type has a template that produces:
- title: Short heading for the report (e.g., "Dallas office international dialing restriction")
- explanation: What we found and how Webex handles it differently
- reassurance: Why this is manageable, not a blocker

Tone: direct, jargon-free, never alarming. Frame problems as decisions, not blockers.
"""
```

One function: `explain_decision(decision_type: str, severity: str, summary: str, context: dict) -> dict`

Returns: `{"title": str, "explanation": str, "reassurance": str}`

Template dispatch by decision_type. Each template extracts relevant fields from context dict. If context fields are missing, fall back to the summary string.

Key templates:
- `CSS_ROUTING_MISMATCH`: "Your [css_name] uses partitions that restrict routing scope. Webex Calling uses flat org-wide routing instead. During planning, you'll choose how to map these restrictions."
- `DEVICE_INCOMPATIBLE`: "You have [count] [model] phones that aren't compatible with Webex Calling. These will need to be replaced with [recommended model]."
- `FEATURE_APPROXIMATION`: "[cucm_feature] doesn't have a direct Webex equivalent. The closest match is [webex_feature], which handles most of the same use cases."
- `SHARED_LINE_COMPLEX`: "Extension [dn] appears on [devices] devices with [owners] different owners. Webex handles this through Virtual Lines or Shared Lines — you'll choose during planning."

Reassurance varies by severity:
- LOW/MEDIUM: "This is a configuration choice, not a limitation."
- HIGH: "This requires planning but has well-defined resolution options."
- CRITICAL: "This must be resolved before migration but the options are clear."

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_explainer.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/explainer.py tests/migration/report/test_explainer.py
git commit -m "feat(report): add decision plain-English explainer"
```

---

### Task 5: CSS Template + Report Styles

**Files:**
- Create: `src/wxcli/migration/report/styles.py`

No tests needed — this is a CSS string constant. It gets tested implicitly when the assembler renders a full report.

- [ ] **Step 1: Write styles.py**

Create `src/wxcli/migration/report/styles.py` containing a single `REPORT_CSS` string constant.

Design system (from spec):
- **Typography:** Inter SemiBold headings, Inter Regular body (10pt print), Inter Regular 9pt monospace-numbers for tables. Fallback: `system-ui, -apple-system, sans-serif`.
- **Colors:** Primary #00BCB4 (Webex teal), Success #2E7D32, Warning #F57C00, Critical #C62828, Neutral #37474F, Background #FFFFFF, Table alternating #F5F5F5.
- **Layout:** Max-width 900px centered, generous padding. Tables full-width with zebra striping.
- **Print:** `@page { size: letter; margin: 0.75in; }`. Page breaks forced before `<section>` elements. `@media print` hides navigation, adjusts font sizes. Header/footer via `@page` margin content if supported, otherwise CSS `position: fixed` fallback.
- **`<details>/<summary>`:** Styled for appendix collapsible sections. Open by default in screen, all expanded in print.
- **Tables:** Border-collapse, header row #37474F with white text, alternating rows, no outer border, subtle bottom-border per row.
- **Score gauge container:** Centered, 250px max width.
- **Chart containers:** Flex layout, wrap on narrow screens.

Include `@font-face` for Inter via Google Fonts CDN, with `font-display: swap` for fallback. The CSS should be fully self-contained (no external dependencies for rendering — Inter is enhancement, system fonts work fine).

- [ ] **Step 2: Commit**

```bash
git add src/wxcli/migration/report/styles.py
git commit -m "feat(report): add CSS design system for assessment report"
```

---

### Task 6: Executive Summary HTML Generator

**Files:**
- Create: `src/wxcli/migration/report/executive.py`
- Create: `tests/migration/report/test_executive.py`

Generates the 2-4 page executive summary HTML. Depends on Tasks 2 (score), 3 (charts), 4 (explainer).

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_executive.py`:

```python
"""Tests for executive summary HTML generation."""
import pytest


class TestExecutiveSummary:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<section" in html
        assert "</section>" in html

    def test_contains_complexity_score(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<svg" in html  # gauge chart
        assert "Straightforward" in html or "Moderate" in html

    def test_contains_brand_name(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Acme Corp" in html

    def test_contains_environment_snapshot(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "50" in html  # user count
        assert "45" in html  # device count

    def test_contains_phone_compatibility_chart(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Native MPP" in html
        assert "Convertible" in html
        assert "Incompatible" in html

    def test_contains_site_breakdown(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Dallas" in html or "loc_dallas" in html

    def test_contains_decision_summary(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Auto-resolved" in html or "auto-resolved" in html
        assert "Decision" in html or "decision" in html

    def test_contains_feature_mapping_table(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Hunt Group" in html
        assert "Auto Attendant" in html

    def test_contains_plain_english_decisions(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        # Should use explainer, not raw decision type names
        assert "CSS_ROUTING_MISMATCH" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_executive.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement executive.py**

Create `src/wxcli/migration/report/executive.py`:

One public function: `generate_executive_summary(store: MigrationStore, brand: str, prepared_by: str, cluster_name: str = "", cucm_version: str = "") -> str`

Returns an HTML string containing `<section>` elements for each page:

**Page 1 — The Headline:**
- Calls `compute_complexity_score(store)` → score, label, color, factors
- Calls `gauge_chart(score, color, label)` → SVG
- Builds one-paragraph summary by querying store for counts
- Environment snapshot table (CUCM version, cluster, total objects, sites, date)

**Page 2 — What You Have:**
- Queries `store.get_objects()` for each type, builds inventory data
- Calls `horizontal_bar_chart()` for object inventory
- Queries device objects, groups by `compatibility_tier`, calls `donut_chart()` for phone compatibility
- Builds per-site breakdown table by grouping objects by `location_id`
- Per-site complexity: use simplified counts (user count, device count, decision count for that site) rather than calling `compute_complexity_score()` per site — the scoring function operates on the full store, not filtered subsets. Map the simplified counts to labels: 0 decisions = "Straightforward", 1-2 = "Moderate", 3+ = "Complex".

**Page 3 — What Needs Attention:**
- Queries `store.get_all_decisions()`, groups by resolution status
- Calls `traffic_light_boxes()` for decision summary
- Gets top 5 unresolved decisions (highest severity first)
- Calls `explain_decision()` for each → plain-English blocks
- Builds feature mapping table from feature-type objects + FEATURE_APPROXIMATION decisions

**Page 4 — Next Steps (conditional):**
- Only generated if > 100 objects or > 3 sites
- Prerequisites checklist (license count, number count, decision count)
- Call to action with `prepared_by` name

All HTML uses semantic elements (`<section>`, `<table>`, `<h2>`, `<p>`) with CSS classes matching `styles.py`. No inline styles except on SVG elements.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_executive.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/executive.py tests/migration/report/test_executive.py
git commit -m "feat(report): add executive summary HTML generator"
```

---

### Task 7: Technical Appendix HTML Generator

**Files:**
- Create: `src/wxcli/migration/report/appendix.py`
- Create: `tests/migration/report/test_appendix.py`

Generates the variable-length technical appendix. Each section is wrapped in `<details>/<summary>` for collapsibility. Sections are only generated if relevant data exists.

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_appendix.py`:

```python
"""Tests for technical appendix HTML generation."""
import pytest


class TestAppendix:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<section" in html

    def test_contains_object_inventory(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Object Inventory" in html
        assert "<table" in html

    def test_contains_decision_detail(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Decision Detail" in html
        assert "FEATURE_APPROXIMATION" in html or "Feature Approximation" in html

    def test_contains_device_inventory(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Device Inventory" in html
        assert "CP-8845" in html

    def test_uses_details_summary_elements(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<details" in html
        assert "<summary>" in html

    def test_skips_empty_sections(self, tmp_path):
        """Appendix for empty store should have minimal content."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.appendix import generate_appendix
        store = MigrationStore(tmp_path / "empty.db")
        html = generate_appendix(store)
        # Should not have device inventory if no devices
        assert "Device Inventory" not in html or "No devices" in html

    def test_css_partition_analysis(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "CSS" in html and "Partition" in html

    def test_routing_topology(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Routing" in html
        assert "PSTN Trunk" in html or "trunk" in html.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_appendix.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement appendix.py**

Create `src/wxcli/migration/report/appendix.py`:

One public function: `generate_appendix(store: MigrationStore) -> str`

9 private section generators, each returning `str` (HTML fragment) or empty string if no data:

1. `_object_inventory(store)` — tables grouped by type and by location. Uses `store.get_objects(type)` for each type, groups by location_id.
2. `_decision_detail(store)` — every decision with context, options, severity. Groups by DecisionType. Uses `store.get_all_decisions()`.
3. `_css_partition_analysis(store)` — text-based topology (CSS → partitions → patterns via cross-refs). Uses `store.get_cross_refs(relationship="css_contains_partition")` and `partition_has_pattern`.
4. `_device_inventory(store)` — full phone model list with compatibility tier. Groups by tier. Shows firmware conversion steps for convertible, replacements for incompatible.
5. `_dn_analysis(store)` — E.164 classification breakdown. Queries line objects for classification data.
6. `_user_device_line_map(store)` — cross-ref chains. Uses `user_has_device`, `device_has_dn`, `dn_in_partition` cross-refs to build chains.
7. `_routing_topology(store)` — trunk, route group, dial plan inventory tables.
8. `_voicemail_analysis(store)` — voicemail profile mapping. Queries voicemail_profile objects + VOICEMAIL_INCOMPATIBLE decisions.
9. `_data_coverage(store)` — reads journal for collection errors. If no journal data, notes "collected via live AXL extraction".

Each section is wrapped in:
```html
<details open>
  <summary>Section Title</summary>
  ... content ...
</details>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_appendix.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/appendix.py tests/migration/report/test_appendix.py
git commit -m "feat(report): add technical appendix HTML generator"
```

---

### Task 8: Report Assembler + CLI Command

**Files:**
- Create: `src/wxcli/migration/report/assembler.py`
- Create: `tests/migration/report/test_assembler.py`
- Modify: `src/wxcli/commands/cucm.py` (add `report` command)

Combines everything into a single self-contained HTML file and wires the CLI.

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_assembler.py`:

```python
"""Tests for full report assembly."""
import pytest


class TestAssembler:
    def test_assemble_returns_complete_html(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "<style>" in html  # embedded CSS
        assert "Acme Corp" in html

    def test_html_is_self_contained(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        # No external references
        assert 'href="http' not in html or 'fonts.googleapis' in html  # font CDN is OK
        assert '<script src="' not in html  # no external JS
        assert '<link rel="stylesheet" href="http' not in html

    def test_contains_executive_and_appendix(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Migration Complexity Score" in html or "Complexity" in html  # executive
        assert "Object Inventory" in html  # appendix

    def test_executive_only_flag(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE",
            executive_only=True)
        assert "Object Inventory" not in html  # no appendix
        assert "Acme Corp" in html  # executive still there

    def test_print_styles_present(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "@media print" in html
        assert "@page" in html

    def test_write_report_to_file(self, populated_store, tmp_path):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        out_path = tmp_path / "report.html"
        out_path.write_text(html)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000  # not trivially small
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_assembler.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement assembler.py**

Create `src/wxcli/migration/report/assembler.py`:

One public function:
```python
def assemble_report(
    store: MigrationStore,
    brand: str,
    prepared_by: str,
    cluster_name: str = "",
    cucm_version: str = "",
    executive_only: bool = False,
) -> str:
```

Assembly:
1. Generate executive summary HTML via `generate_executive_summary()`
2. If not `executive_only`, generate appendix HTML via `generate_appendix()`
3. Combine into full HTML document:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CUCM Migration Assessment — {brand}</title>
  <style>{REPORT_CSS}</style>
</head>
<body>
  <header class="report-header">
    <h1>CUCM Migration Assessment</h1>
    <p class="brand">{brand}</p>
    <p class="meta">Prepared by {prepared_by} | {date}</p>
  </header>
  <main>
    {executive_html}
    {appendix_html if not executive_only}
  </main>
  <footer class="report-footer">
    <p>Generated by cucm-assess</p>
  </footer>
</body>
</html>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_assembler.py -v`
Expected: All PASS.

- [ ] **Step 5: Add `report` CLI command to cucm.py**

Add to `src/wxcli/commands/cucm.py`:

```python
@app.command()
def report(
    brand: str = typer.Option(..., "--brand", help="Customer name for report header"),
    prepared_by: str = typer.Option(..., "--prepared-by", help="SE/partner name"),
    output: str = typer.Option("assessment-report", "--output", "-o",
        help="Output filename (without extension)"),
    pdf: bool = typer.Option(False, "--pdf", help="Also generate PDF via headless Chrome"),
    executive_only: bool = typer.Option(False, "--executive-only",
        help="Generate executive summary only, skip technical appendix"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Generate a migration assessment report (HTML + optional PDF)."""
```

Implementation:
1. Resolve project dir, check that `analyze` stage is complete. Note: `report` is not in `PIPELINE_STAGES` or `STAGE_PREREQUISITES` — add it, or do a manual check by reading the stages file. The `report` command's prerequisite is `analyze` (not `plan` or `preflight` — those are for execution, not assessment).
2. Open store, read config for cluster_name/cucm_version
3. Call `assemble_report()`
4. Write to `{output}.html`
5. If `--pdf`: run `shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")` — if found, run `subprocess.run([browser, "--headless", "--disable-gpu", "--print-to-pdf={output}.pdf", f"file://{output_path.absolute()}"])`. If no Chrome found, print warning with manual instructions.
6. Print success message with file path(s)

- [ ] **Step 6: Run all report tests**

Run: `pytest tests/migration/report/ -v`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/report/assembler.py tests/migration/report/test_assembler.py \
  src/wxcli/commands/cucm.py
git commit -m "feat(cucm): add report assembler + wxcli cucm report command"
```

---

### Task 9: End-to-End Test + Polish

**Files:**
- Create: `tests/migration/report/test_e2e.py`
- Modify: `src/wxcli/migration/report/__init__.py` (public API)

Final integration test: collector file → discover --from-file → normalize → analyze → report.

- [ ] **Step 1: Write end-to-end test**

Create `tests/migration/report/test_e2e.py`:

```python
"""End-to-end test: collector file → pipeline → report."""
import json
import gzip
import pytest
from pathlib import Path


class TestEndToEnd:
    def test_full_pipeline_from_collector_file(self, tmp_path, sample_collector_file):
        """Ingest → normalize → analyze → report should produce valid HTML."""
        from wxcli.migration.report.ingest import ingest_collector_file
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.pipeline import normalize_discovery
        from wxcli.migration.transform.engine import TransformEngine
        from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
        from wxcli.migration.report.assembler import assemble_report

        # 1. Ingest collector file
        raw_data = ingest_collector_file(sample_collector_file)

        # 2. Store + normalize (pass 1 + pass 2)
        store = MigrationStore(tmp_path / "e2e.db")
        normalize_discovery(raw_data, store)

        # 3. Map (creates canonical objects with compatibility_tier, etc.)
        TransformEngine().run(store)

        # 4. Analyze
        AnalysisPipeline().run(store)

        # 4. Generate report
        html = assemble_report(store,
            brand="E2E Test Corp", prepared_by="Test SE")

        assert "<!DOCTYPE html>" in html
        assert "E2E Test Corp" in html
        assert "Complexity" in html.lower() or "straightforward" in html.lower()

        # Write and verify file
        out = tmp_path / "e2e-report.html"
        out.write_text(html)
        assert out.stat().st_size > 2000

    def test_report_from_populated_fixture(self, populated_store, tmp_path):
        """Report from test fixture should have all expected sections."""
        from wxcli.migration.report.assembler import assemble_report

        html = assemble_report(populated_store,
            brand="Fixture Corp", prepared_by="Fixture SE")

        out = tmp_path / "fixture-report.html"
        out.write_text(html)

        # Executive sections
        assert "Migration Complexity" in html or "Complexity Score" in html
        assert "<svg" in html  # charts present
        assert "Fixture Corp" in html

        # Appendix sections
        assert "Object Inventory" in html
        assert "Decision Detail" in html
        assert "Device Inventory" in html
```

- [ ] **Step 2: Run end-to-end test**

Run: `pytest tests/migration/report/test_e2e.py -v`
Expected: All PASS. If normalize_discovery, TransformEngine, or AnalysisPipeline have import issues or require additional setup, fix and re-run.

Note: The e2e test that uses `sample_collector_file` may need the normalize/analyze functions to handle minimal data gracefully (1 user, 1 phone). If they crash on sparse data, that's a bug worth fixing — real collector files may have sparse data too.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All existing tests still pass + all new report tests pass. No regressions.

- [ ] **Step 4: Generate a sample report from the CUCM test bed**

If you have access to the test bed at 10.201.123.107, run:
```bash
wxcli cucm init sample-report
wxcli cucm discover --host 10.201.123.107 --username axl_admin --password ***
wxcli cucm normalize
wxcli cucm analyze
wxcli cucm report --brand "Sample Customer" --prepared-by "Adam Hobgood"
```

Open the resulting HTML in a browser and verify:
- [ ] Complexity score gauge renders correctly
- [ ] Phone compatibility donut chart has correct proportions
- [ ] Object inventory bar chart is sorted and labeled
- [ ] Decision explanations are in plain English (no raw type names)
- [ ] Tables have zebra striping and correct alignment
- [ ] Print preview (Cmd+P) shows clean page breaks
- [ ] All SVGs render at high resolution

If no CUCM access, generate from the fixture:
```bash
pytest tests/migration/report/test_e2e.py::TestEndToEnd::test_report_from_populated_fixture -v
```
Then open the written HTML file from the tmp_path output.

- [ ] **Step 5: Commit**

```bash
git add tests/migration/report/test_e2e.py src/wxcli/migration/report/__init__.py
git commit -m "test(report): add end-to-end assessment report tests"
```

---

## Task Dependency Graph

```
Task 1 (fixtures + --from-file)
  ↓
Task 2 (score) ──────────────────┐
Task 3 (charts) ─────────────────┤
Task 4 (explainer) ──────────────┤
Task 5 (CSS styles) ─────────────┤
  ↓                               ↓
Task 6 (executive summary)       │
Task 7 (appendix)                │
  ↓                               ↓
Task 8 (assembler + CLI) ←───────┘
  ↓
Task 9 (e2e test + polish)
```

Tasks 2, 3, 4, 5 can run in parallel after Task 1.
Tasks 6 and 7 can run in parallel after Tasks 2-5.
Task 8 depends on Tasks 5, 6, 7.
Task 9 depends on Task 8.
