# CUCM Assessment Report — Phase B: Visual Components

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the visual building blocks: SVG chart generators, decision plain-English explainer, and CSS design system. These are consumed by the report generators in Phase C.

**Architecture:** Three independent modules in `src/wxcli/migration/report/`: `charts.py` (pure SVG generators), `explainer.py` (decision type → plain English), `styles.py` (CSS constant). All are pure functions with no inter-dependencies — Tasks 3, 4, and 5 can run in parallel.

**Tech Stack:** Python 3.11, inline SVG (no JavaScript), CSS `@media print`.

**Spec:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md`
**Master plan:** `docs/superpowers/plans/2026-03-24-cucm-assess-report.md`
**Prerequisite:** Phase A complete (`ingest.py`, `score.py`, test fixtures in `conftest.py`)
**Next phase:** `docs/superpowers/plans/2026-03-24-cucm-assess-phase-c.md` (executive + appendix + assembler + CLI)

---

## File Map

| File | Purpose |
|------|---------|
| **Create:** `src/wxcli/migration/report/charts.py` | SVG generators: gauge, donut, horizontal bar, traffic-light boxes |
| **Create:** `src/wxcli/migration/report/explainer.py` | Decision type → plain-English explanation templates |
| **Create:** `src/wxcli/migration/report/styles.py` | CSS template string (embedded in HTML) |
| **Create:** `tests/migration/report/test_charts.py` | SVG chart output tests |
| **Create:** `tests/migration/report/test_explainer.py` | Explainer template tests |

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

No tests needed — this is a CSS string constant. It gets tested implicitly when the assembler renders a full report in Phase C.

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

## Phase B Verification

After all three tasks complete:

```bash
pytest tests/migration/report/ -v
```

Expected: All Phase A tests still pass + charts and explainer tests pass.

**Parallelism:** Tasks 3, 4, and 5 have no dependencies on each other. They can be dispatched as 3 parallel agents.

**Next:** Run Phase C (`docs/superpowers/plans/2026-03-24-cucm-assess-phase-c.md`) — executive summary, appendix, assembler, CLI command, e2e test.
