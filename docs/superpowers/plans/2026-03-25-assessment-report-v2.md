# Assessment Report v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the CUCM assessment report from pipeline-centric layout to customer-centric narrative with 4-page executive summary + 6-group collapsed technical reference.

**Architecture:** The report system (8 files, 3,320 lines at `src/wxcli/migration/report/`) reads from a SQLite store and generates self-contained HTML. This plan rewrites 6 files, adds 1 new file, and updates tests. No store API changes. The existing `ingest.py` is untouched.

**Tech Stack:** Python 3.11, inline SVG, CSS custom properties, HTML `<details>/<summary>`, pytest

**Spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v2-design.md`

**Pre-implementation:** Before starting Task 1, create a git tag to preserve v1: `git tag report-v1`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/wxcli/migration/report/helpers.py` | **Create** | `strip_canonical_id()`, `friendly_site_name()` utilities |
| `src/wxcli/migration/report/score.py` | Modify | Add `display_name` to factor dicts |
| `src/wxcli/migration/report/explainer.py` | Modify | Add `generate_verdict()`, `generate_key_findings()`, type display name map |
| `src/wxcli/migration/report/charts.py` | Modify | Add `stacked_bar_chart()`, shrink gauge, remove `traffic_light_boxes()` |
| `src/wxcli/migration/report/styles.py` | Rewrite | Updated CSS with contrast fixes, effort band styles, new component styles |
| `src/wxcli/migration/report/executive.py` | Rewrite | 4 new pages: Verdict, Environment, Migration Scope, Next Steps |
| `src/wxcli/migration/report/appendix.py` | Rewrite | 6 topic groups, decision aggregation, collapsed by default |
| `src/wxcli/migration/report/assembler.py` | Modify | Dark interstitial, updated sidebar nav, max-width 720px |
| `tests/migration/report/test_helpers.py` | **Create** | Tests for helpers.py |
| `tests/migration/report/test_score.py` | Modify | Update for display_name field |
| `tests/migration/report/test_explainer.py` | Modify | Tests for verdict, key findings |
| `tests/migration/report/test_charts.py` | Modify | Tests for stacked_bar_chart, updated gauge |
| `tests/migration/report/test_executive.py` | Rewrite | Tests for new 4-page structure |
| `tests/migration/report/test_appendix.py` | Rewrite | Tests for new 6-group structure |
| `tests/migration/report/test_assembler.py` | Modify | Update assertions for new HTML structure |

---

## Task 1: Helpers Module (new)

**Files:**
- Create: `src/wxcli/migration/report/helpers.py`
- Create: `tests/migration/report/test_helpers.py`

- [ ] **Step 1: Write failing tests for `strip_canonical_id`**

```python
# tests/migration/report/test_helpers.py
"""Tests for report helper utilities."""
import pytest
from wxcli.migration.report.helpers import strip_canonical_id, friendly_site_name


class TestStripCanonicalId:
    def test_css_prefix(self):
        assert strip_canonical_id("css:Standard-Employee-CSS") == "Standard-Employee-CSS"

    def test_device_prefix(self):
        assert strip_canonical_id("device:SEP001122334455") == "SEP001122334455"

    def test_dn_prefix_with_partition(self):
        assert strip_canonical_id("dn:1001:Internal-PT") == "1001 (Internal-PT)"

    def test_voicemail_profile_prefix(self):
        assert strip_canonical_id("voicemail_profile:Default") == "Default"

    def test_location_prefix(self):
        assert strip_canonical_id("location:DP-HQ-Phones") == "DP-HQ-Phones"

    def test_no_prefix(self):
        assert strip_canonical_id("plain-string") == "plain-string"

    def test_empty_string(self):
        assert strip_canonical_id("") == ""

    def test_partition_prefix(self):
        assert strip_canonical_id("partition:Internal-PT") == "Internal-PT"

    def test_unknown_prefix_with_colon(self):
        # Unknown prefixes: strip the prefix
        assert strip_canonical_id("trunk:sip-trunk-1") == "sip-trunk-1"


class TestFriendlySiteName:
    def test_strip_dp_prefix_and_phones_suffix(self):
        assert friendly_site_name("DP-HQ-Phones") == "HQ"

    def test_strip_dp_prefix_and_softphones_suffix(self):
        assert friendly_site_name("DP-HQ-Softphones") == "HQ"

    def test_strip_dp_prefix_and_commonarea_suffix(self):
        assert friendly_site_name("DP-CommonArea") == "CommonArea"

    def test_dp_prefix_only(self):
        assert friendly_site_name("DP-Branch") == "Branch"

    def test_no_prefix_no_suffix(self):
        assert friendly_site_name("MainOffice") == "MainOffice"

    def test_empty_string(self):
        assert friendly_site_name("") == ""

    def test_just_dp(self):
        assert friendly_site_name("DP-") == ""

    def test_multi_segment_name(self):
        assert friendly_site_name("DP-Austin-Branch-Phones") == "Austin-Branch"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_helpers.py -v`
Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Implement helpers.py**

```python
# src/wxcli/migration/report/helpers.py
"""Report helper utilities for customer-facing text formatting."""
from __future__ import annotations

# Canonical ID prefixes used in the migration store.
# dn: has a special format — dn:NUMBER:PARTITION
_KNOWN_PREFIXES = (
    "css:", "device:", "location:", "partition:", "trunk:",
    "route_group:", "dial_plan:", "voicemail_profile:",
    "hunt_group:", "auto_attendant:", "call_queue:", "call_park:",
    "pickup_group:", "paging_group:", "workspace:", "schedule:",
    "operating_mode:", "shared_line:", "virtual_line:", "line:",
    "calling_permission:", "translation_pattern:", "user:",
)


def strip_canonical_id(canonical_id: str) -> str:
    """Strip internal canonical ID prefixes for customer-facing display.

    Examples:
        "css:Standard-Employee-CSS" → "Standard-Employee-CSS"
        "dn:1001:Internal-PT" → "1001 (Internal-PT)"
        "voicemail_profile:Default" → "Default"
        "plain-string" → "plain-string"
    """
    if not canonical_id:
        return ""

    # Special case: dn:NUMBER:PARTITION
    if canonical_id.startswith("dn:"):
        parts = canonical_id[3:].split(":", 1)
        if len(parts) == 2:
            return f"{parts[0]} ({parts[1]})"
        return parts[0]

    # Known prefixes
    for prefix in _KNOWN_PREFIXES:
        if canonical_id.startswith(prefix):
            return canonical_id[len(prefix):]

    # Unknown prefix — if there's a colon, strip up to first colon
    if ":" in canonical_id:
        return canonical_id.split(":", 1)[1]

    return canonical_id


# Suffixes to strip from device pool names for friendly display.
_SITE_SUFFIXES = ("-Phones", "-Softphones", "-CommonArea")


def friendly_site_name(device_pool_name: str) -> str:
    """Convert a CUCM device pool name to a customer-friendly site name.

    Examples:
        "DP-HQ-Phones" → "HQ"
        "DP-Branch" → "Branch"
        "MainOffice" → "MainOffice"
    """
    if not device_pool_name:
        return ""

    name = device_pool_name

    # Strip DP- prefix
    if name.startswith("DP-"):
        name = name[3:]

    # Strip known suffixes
    for suffix in _SITE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    return name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_helpers.py -v`
Expected: All 17 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/helpers.py tests/migration/report/test_helpers.py
git commit -m "feat(report): add helpers module with strip_canonical_id and friendly_site_name"
```

---

## Task 2: Score Display Names

**Files:**
- Modify: `src/wxcli/migration/report/score.py` (lines 16-25, 66-78)
- Modify: `tests/migration/report/test_score.py`

- [ ] **Step 1: Write failing test for display_name field**

Add to `tests/migration/report/test_score.py`:

```python
def test_factors_have_display_names(populated_store):
    """Each factor dict should include a display_name field."""
    result = compute_complexity_score(populated_store)
    for factor in result.factors:
        assert "display_name" in factor, f"Factor {factor['name']} missing display_name"
    # Check specific mappings
    names = {f["name"]: f["display_name"] for f in result.factors}
    assert names["CSS Complexity"] == "Calling Restrictions"
    assert names["Feature Parity"] == "Feature Compatibility"
    assert names["Device Compatibility"] == "Device Readiness"
    assert names["Decision Density"] == "Outstanding Decisions"
    assert names["Scale"] == "Scale"
    assert names["Shared Line Complexity"] == "Shared Lines"
    assert names["Routing Complexity"] == "Routing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_score.py::test_factors_have_display_names -v`
Expected: FAIL — KeyError on `display_name`.

- [ ] **Step 3: Add DISPLAY_NAMES map and inject into factor dicts in score.py**

Add after the `WEIGHTS` dict (~line 25):

```python
# Customer-friendly display names for score factors
DISPLAY_NAMES = {
    "CSS Complexity": "Calling Restrictions",
    "Feature Parity": "Feature Compatibility",
    "Device Compatibility": "Device Readiness",
    "Decision Density": "Outstanding Decisions",
    "Scale": "Scale",
    "Shared Line Complexity": "Shared Lines",
    "Routing Complexity": "Routing",
}
```

In `compute_complexity_score()`, modify the `factors.append()` call (~line 72) to include `display_name`:

```python
        factors.append({
            "name": name,
            "display_name": DISPLAY_NAMES[name],
            "weight": weight,
            "raw_score": raw_score,
            "weighted_score": round(weighted_score, 1),
            "detail": detail,
        })
```

- [ ] **Step 4: Run all score tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_score.py -v`
Expected: All PASS (existing tests unaffected — they don't check for absence of extra keys).

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/score.py tests/migration/report/test_score.py
git commit -m "feat(report): add customer-friendly display_name to score factors"
```

---

## Task 3: Explainer — Verdict, Key Findings, Type Name Map

**Files:**
- Modify: `src/wxcli/migration/report/explainer.py`
- Modify: `tests/migration/report/test_explainer.py`

- [ ] **Step 1: Write failing tests for generate_verdict**

Add to `tests/migration/report/test_explainer.py`:

```python
from wxcli.migration.report.explainer import (
    explain_decision,
    generate_verdict,
    generate_key_findings,
    DECISION_TYPE_DISPLAY_NAMES,
)
from wxcli.migration.report.score import ScoreResult


class TestGenerateVerdict:
    def test_straightforward(self, populated_store):
        score = ScoreResult(score=25, label="Straightforward", color="#2E7D32", factors=[
            {"name": "CSS Complexity", "display_name": "Calling Restrictions", "weight": 25, "raw_score": 20, "weighted_score": 5.0, "detail": ""},
            {"name": "Device Compatibility", "display_name": "Device Readiness", "weight": 15, "raw_score": 10, "weighted_score": 1.5, "detail": ""},
        ])
        result = generate_verdict(score, populated_store)
        assert "straightforward" in result.lower()
        assert isinstance(result, str)
        assert len(result) > 20

    def test_moderate(self, populated_store):
        score = ScoreResult(score=43, label="Moderate", color="#F57C00", factors=[
            {"name": "CSS Complexity", "display_name": "Calling Restrictions", "weight": 25, "raw_score": 72, "weighted_score": 18.0, "detail": ""},
            {"name": "Feature Parity", "display_name": "Feature Compatibility", "weight": 20, "raw_score": 50, "weighted_score": 10.0, "detail": ""},
        ])
        result = generate_verdict(score, populated_store)
        assert "feasible with planning" in result.lower()

    def test_complex(self, populated_store):
        score = ScoreResult(score=72, label="Complex", color="#C62828", factors=[
            {"name": "CSS Complexity", "display_name": "Calling Restrictions", "weight": 25, "raw_score": 90, "weighted_score": 22.5, "detail": ""},
            {"name": "Device Compatibility", "display_name": "Device Readiness", "weight": 15, "raw_score": 80, "weighted_score": 12.0, "detail": ""},
        ])
        result = generate_verdict(score, populated_store)
        assert "requires significant planning" in result.lower()


class TestGenerateKeyFindings:
    def test_returns_list_of_dicts(self, populated_store):
        findings = generate_key_findings(populated_store)
        assert isinstance(findings, list)
        assert len(findings) >= 2
        for f in findings:
            assert "icon" in f
            assert "text" in f
            assert f["icon"] in ("!", "✓")

    def test_device_finding_present(self, populated_store):
        """populated_store has 40 native, 3 convertible, 2 incompatible."""
        findings = generate_key_findings(populated_store)
        texts = " ".join(f["text"] for f in findings)
        # Should mention device counts
        assert "device" in texts.lower() or "phone" in texts.lower()


class TestDecisionTypeDisplayNames:
    def test_all_17_types_mapped(self):
        from wxcli.migration.models import DecisionType
        for dt in DecisionType:
            assert dt.value in DECISION_TYPE_DISPLAY_NAMES, f"{dt.value} missing from display name map"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_explainer.py::TestGenerateVerdict -v`
Expected: ImportError — `generate_verdict` not found.

- [ ] **Step 3: Implement generate_verdict, generate_key_findings, and type name map**

Add to the end of `src/wxcli/migration/report/explainer.py`:

```python
from wxcli.migration.report.score import ScoreResult
from wxcli.migration.store import MigrationStore


# Customer-friendly display names for all 17 DecisionType values.
DECISION_TYPE_DISPLAY_NAMES: dict[str, str] = {
    "MISSING_DATA": "Missing Data",
    "CSS_ROUTING_MISMATCH": "CSS Routing Mismatch",
    "CALLING_PERMISSION_MISMATCH": "Calling Restrictions",
    "DEVICE_FIRMWARE_CONVERTIBLE": "Device Firmware Conversion",
    "DEVICE_INCOMPATIBLE": "Incompatible Devices",
    "FEATURE_APPROXIMATION": "Feature Approximation",
    "WORKSPACE_LICENSE_TIER": "Workspace Licensing",
    "LOCATION_AMBIGUOUS": "Location Mapping",
    "SHARED_LINE_COMPLEX": "Shared Line Complexity",
    "EXTENSION_CONFLICT": "Extension Conflicts",
    "DN_AMBIGUOUS": "Directory Number Ambiguity",
    "VOICEMAIL_INCOMPATIBLE": "Voicemail Compatibility",
    "DUPLICATE_USER": "Duplicate Users",
    "WORKSPACE_TYPE_UNCERTAIN": "Workspace Type",
    "HOTDESK_DN_CONFLICT": "Hot Desk Conflicts",
    "NUMBER_CONFLICT": "Number Conflicts",
    "ARCHITECTURE_ADVISORY": "Architecture Advisory",
}


def generate_verdict(score_result: ScoreResult, store: MigrationStore) -> str:
    """Generate a one-paragraph verdict sentence from score and store data.

    Returns a string like:
    "This migration is **feasible with planning**. Moderate complexity is
    driven by calling restriction differences and firmware-convertible
    devices. All 67 decisions were auto-resolved — no manual decisions
    required at this stage."
    """
    # Verdict phrase based on score label
    if score_result.score <= 30:
        opener = "This migration is <strong>straightforward</strong>."
    elif score_result.score <= 55:
        opener = "This migration is <strong>feasible with planning</strong>."
    else:
        opener = "This migration <strong>requires significant planning</strong>."

    # Top 2 contributing factors (by weighted_score, descending)
    sorted_factors = sorted(
        score_result.factors, key=lambda f: f["weighted_score"], reverse=True
    )
    top_factors = sorted_factors[:2]
    display_names = [f.get("display_name", f["name"]).lower() for f in top_factors]

    if len(display_names) == 2:
        driver = f"{score_result.label} complexity is driven by {display_names[0]} and {display_names[1]}."
    elif len(display_names) == 1:
        driver = f"{score_result.label} complexity is driven by {display_names[0]}."
    else:
        driver = ""

    # Decision resolution
    decisions = store.get_all_decisions()
    total = len(decisions)
    resolved = sum(1 for d in decisions if d.get("chosen_option"))
    unresolved = total - resolved

    if total == 0:
        decision_text = "No migration decisions were generated."
    elif unresolved == 0:
        decision_text = f"All {total} decisions were auto-resolved — no manual decisions required at this stage."
    else:
        decision_text = f"{unresolved} of {total} decisions require manual input before migration can proceed."

    return f"{opener} {driver} {decision_text}"


def generate_key_findings(store: MigrationStore) -> list[dict[str, str]]:
    """Generate 3-4 key findings from store data.

    Returns list of {"icon": "!" or "✓", "text": "..."} dicts.
    """
    findings: list[dict[str, str]] = []

    # 1. Device compatibility
    devices = store.get_objects("device")
    if devices:
        total = len(devices)
        native = sum(1 for d in devices if d.get("compatibility_tier") == "native_mpp")
        convertible = sum(1 for d in devices if d.get("compatibility_tier") == "convertible")
        incompatible = sum(1 for d in devices if d.get("compatibility_tier") == "incompatible")

        if incompatible > 0 or convertible > 0:
            parts = []
            if convertible > 0:
                parts.append(f"{convertible} need firmware conversion")
            if incompatible > 0:
                parts.append(f"{incompatible} need replacement")
            findings.append({
                "icon": "!",
                "text": f"<strong>{convertible + incompatible} of {total} phones</strong> {'; '.join(parts)}",
            })
        elif native == total and total > 0:
            findings.append({
                "icon": "✓",
                "text": f"<strong>All {total} phones</strong> are native MPP — no firmware or hardware changes needed",
            })

    # 2. Feature mapping
    feature_types = ["hunt_group", "auto_attendant", "call_queue", "call_park", "pickup_group", "paging_group"]
    feature_count = sum(store.count_by_type(ft) for ft in feature_types)
    feature_decisions = [
        d for d in store.get_all_decisions()
        if d.get("type") == "FEATURE_APPROXIMATION"
    ]
    if feature_count > 0:
        if not feature_decisions:
            types_with_data = [ft.replace("_", " ").title() for ft in feature_types if store.count_by_type(ft) > 0]
            count = len(types_with_data)
            findings.append({
                "icon": "✓",
                "text": f"<strong>All {count} call feature types</strong> have direct Webex equivalents",
            })
        else:
            findings.append({
                "icon": "!",
                "text": f"<strong>{len(feature_decisions)} features</strong> need approximation — no direct Webex equivalent",
            })

    # 3. CSS/routing decisions
    routing_decisions = [
        d for d in store.get_all_decisions()
        if d.get("type") in ("CSS_ROUTING_MISMATCH", "CALLING_PERMISSION_MISMATCH")
    ]
    if routing_decisions:
        findings.append({
            "icon": "!",
            "text": f"<strong>{len(routing_decisions)} calling restriction rules</strong> differ between CUCM and Webex — {'all auto-resolved' if all(d.get('chosen_option') for d in routing_decisions) else 'review needed'}",
        })

    # 4. Decision resolution rate
    all_decisions = store.get_all_decisions()
    total = len(all_decisions)
    resolved = sum(1 for d in all_decisions if d.get("chosen_option"))
    if total > 0:
        if resolved == total:
            findings.append({
                "icon": "✓",
                "text": f"<strong>{total} of {total} decisions</strong> auto-resolved — no manual input needed at this stage",
            })
        else:
            unresolved = total - resolved
            findings.append({
                "icon": "!",
                "text": f"<strong>{unresolved} of {total} decisions</strong> require manual input before migration",
            })

    return findings
```

- [ ] **Step 4: Run all explainer tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_explainer.py -v`
Expected: All PASS (existing tests + new ones).

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/explainer.py tests/migration/report/test_explainer.py
git commit -m "feat(report): add generate_verdict, generate_key_findings, and type display name map"
```

---

## Task 4: Charts — Stacked Bar, Gauge Resize, Remove Traffic Light

**Files:**
- Modify: `src/wxcli/migration/report/charts.py`
- Modify: `tests/migration/report/test_charts.py`

- [ ] **Step 1: Write failing test for stacked_bar_chart**

Add to `tests/migration/report/test_charts.py`:

```python
from wxcli.migration.report.charts import stacked_bar_chart


class TestStackedBarChart:
    def test_basic_output(self):
        segments = [
            {"label": "Convertible", "value": 7, "color": "#F57C00"},
            {"label": "Incompatible", "value": 4, "color": "#C62828"},
        ]
        svg = stacked_bar_chart(segments)
        assert "<svg" in svg
        assert "Convertible" in svg
        assert "Incompatible" in svg

    def test_omits_zero_segments(self):
        segments = [
            {"label": "Native MPP", "value": 0, "color": "#2E7D32"},
            {"label": "Convertible", "value": 7, "color": "#F57C00"},
        ]
        svg = stacked_bar_chart(segments)
        assert "Native MPP" not in svg
        assert "Convertible" in svg

    def test_single_segment(self):
        segments = [{"label": "All Native", "value": 45, "color": "#2E7D32"}]
        svg = stacked_bar_chart(segments)
        assert "All Native" in svg

    def test_empty_segments(self):
        svg = stacked_bar_chart([])
        assert svg == ""

    def test_all_zero(self):
        segments = [
            {"label": "A", "value": 0, "color": "#ccc"},
            {"label": "B", "value": 0, "color": "#ddd"},
        ]
        svg = stacked_bar_chart(segments)
        assert svg == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_charts.py::TestStackedBarChart -v`
Expected: ImportError — `stacked_bar_chart` not found.

- [ ] **Step 3: Implement stacked_bar_chart in charts.py**

Add to `src/wxcli/migration/report/charts.py`:

```python
def stacked_bar_chart(segments: list[dict]) -> str:
    """Render a horizontal stacked bar with legend.

    Args:
        segments: List of {"label": str, "value": int, "color": hex}.
                  Zero-value segments are omitted.

    Returns:
        HTML string (div with inline stacked bar + legend), or "" if no data.
    """
    # Filter out zero-value segments
    segments = [s for s in segments if s.get("value", 0) > 0]
    if not segments:
        return ""

    total = sum(s["value"] for s in segments)
    if total == 0:
        return ""

    # Build stacked bar divs
    bar_parts = []
    for seg in segments:
        pct = seg["value"] / total * 100
        bar_parts.append(
            f'<div style="background:{seg["color"]};width:{pct:.1f}%;" '
            f'title="{html.escape(seg["label"])}: {seg["value"]}"></div>'
        )

    # Build legend
    legend_parts = []
    for seg in segments:
        pct = seg["value"] / total * 100
        legend_parts.append(
            f'<span>'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:2px;'
            f'background:{seg["color"]};margin-right:4px;vertical-align:middle;"></span>'
            f'{html.escape(seg["label"])}: {seg["value"]} ({pct:.0f}%)</span>'
        )

    return (
        f'<div style="display:flex;height:20px;border-radius:4px;overflow:hidden;">'
        f'{"".join(bar_parts)}</div>'
        f'<div style="display:flex;justify-content:space-between;margin-top:0.35rem;'
        f'font-size:0.7rem;font-family:var(--font-body);color:var(--slate-500);">'
        f'{"".join(legend_parts)}</div>'

    # NOTE: Use html.escape() (already imported in charts.py), NOT html.escape() which doesn't exist.
    )
```

- [ ] **Step 4: Shrink gauge_chart viewBox**

In `charts.py`, find the `gauge_chart()` function. Change the viewBox from `"0 0 240 260"` to `"0 0 200 155"` and adjust the arc path, text positions, and default width/height accordingly. The gauge should render at 160px wide in the report.

Update the SVG dimensions: `width="160" height="125"`. Recalculate the arc center and radius to fit the smaller viewBox (center at 100,95, radius 70, stroke-width 12).

- [ ] **Step 5: Remove traffic_light_boxes**

In `charts.py`, delete the `traffic_light_boxes()` function entirely. It's replaced by the effort band cards in executive.py.

- [ ] **Step 6: Run all chart tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_charts.py -v`
Expected: All PASS. If existing tests reference `traffic_light_boxes`, update them to remove those assertions.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/report/charts.py tests/migration/report/test_charts.py
git commit -m "feat(report): add stacked_bar_chart, shrink gauge, remove traffic_light_boxes"
```

---

## Task 5: Styles Rewrite

**Files:**
- Rewrite: `src/wxcli/migration/report/styles.py`

This is a CSS-only change. No new tests needed — the existing assembler/executive/appendix tests will validate the CSS is included.

- [ ] **Step 1: Read current styles.py to understand structure**

Read `src/wxcli/migration/report/styles.py` to identify the `REPORT_CSS` constant and `GOOGLE_FONTS_LINKS`.

- [ ] **Step 2: Update REPORT_CSS with contrast fixes and new component styles**

Key changes to the CSS:
- **Contrast:** Update `--color-text` to `#1a1f25`, `--color-text-muted` to `#4a5363`, `--slate-500` uses to `#4a5363` where text
- **New components:** `.effort-band`, `.effort-band.auto`, `.effort-band.planning`, `.effort-band.manual` — colored cards for Page 3
- **Stacked bar:** `.stacked-bar` container styles
- **Score breakdown:** `.score-breakdown` grid (label | bar | value)
- **Key findings:** `.key-findings` list with icon + text
- **Tech reference interstitial:** `.tech-interstitial` dark bar
- **Max-width:** `.detail-panel-content { max-width: 720px; margin: 0 auto; }`
- **Remove:** `.summary-boxes` (traffic light), unused `.score-hero` flex centering
- **Badge contrast:** Update badge colors to darker text shades (#1b5e20, #bf360c, #b71c1c)
- **Card backgrounds:** Ensure all `.stat-card`, `.callout`, `.explanation` use `background: #fff` with `border: 1px solid var(--slate-200)`

- [ ] **Step 3: Run existing tests to verify CSS is still embedded correctly**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_assembler.py -v`
Expected: PASS (tests check that CSS is present in output, not specific CSS values).

- [ ] **Step 4: Commit**

```bash
git add src/wxcli/migration/report/styles.py
git commit -m "feat(report): update CSS design system with contrast fixes and v2 component styles"
```

---

## Task 6: Executive Summary Rewrite

**Files:**
- Rewrite: `src/wxcli/migration/report/executive.py`
- Rewrite: `tests/migration/report/test_executive.py`

This is the largest task. The entire executive.py (509 lines) is replaced with the 4-page narrative structure.

- [ ] **Step 1: Write tests for the new 4-page structure**

Rewrite `tests/migration/report/test_executive.py` with tests for:
- `generate_executive_summary()` returns HTML containing all 4 section IDs (`#score`, `#inventory`, `#scope`, `#next-steps`)
- Page 1: contains `"Assessment Verdict"`, score gauge SVG, score breakdown bars, key findings
- Page 2: contains `"People"`, `"Devices"`, `"Call Features"`, `"Sites"` group headers
- Page 3: contains `"Migrates Automatically"`, `"Needs Planning"`, `"Requires Manual Work"` effort bands
- Page 4: contains `"Before Migration"`, `"Planning Phase"`, `"Ready to Plan"`
- No canonical ID prefixes in output (`css:`, `device:`, `dn:`, `location:`, `voicemail_profile:` should not appear)
- Feature table present with `Direct` / `Approximation` badges

Use the `populated_store` fixture from conftest.py.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_executive.py -v`
Expected: FAIL — old HTML structure doesn't match new assertions.

- [ ] **Step 3: Implement new executive.py**

Rewrite `src/wxcli/migration/report/executive.py` with:
- `generate_executive_summary(store, brand, prepared_by, cluster_name="", cucm_version="") → str`
- Internal functions: `_page_verdict()`, `_page_environment()`, `_page_scope()`, `_page_next_steps()`
- Import and use: `generate_verdict()`, `generate_key_findings()` from explainer
- Import and use: `gauge_chart()`, `stacked_bar_chart()` from charts
- Import and use: `strip_canonical_id()`, `friendly_site_name()` from helpers
- Import and use: `compute_complexity_score()` from score
- Effort band assignment logic as `_classify_decisions()` returning 3 lists
- All text uses contrast-compliant colors (#1a1f25 body, #4a5363 secondary)
- Section IDs: `score`, `inventory`, `scope`, `next-steps`

**Note:** This file will be 400-600 lines. Write it in full — don't leave placeholders. Reference the mockups from the brainstorm for exact HTML structure.

- [ ] **Step 4: Run tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_executive.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/executive.py tests/migration/report/test_executive.py
git commit -m "feat(report): rewrite executive summary with 4-page narrative structure"
```

---

## Task 7: Appendix Rewrite

**Files:**
- Rewrite: `src/wxcli/migration/report/appendix.py`
- Rewrite: `tests/migration/report/test_appendix.py`

- [ ] **Step 1: Write tests for new 6-group structure**

Rewrite `tests/migration/report/test_appendix.py` with tests for:
- `generate_appendix()` returns HTML with 6 `<details>` elements
- Section IDs: `people`, `devices`, `features`, `routing`, `decisions`, `data-quality`
- Decisions grouped by type (not individual callout boxes)
- No canonical ID prefixes in output
- Each `<summary>` contains a count summary line
- CSS topology rendered inside routing group (not standalone)
- User/device map inside people group

Use the `populated_store` fixture.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_appendix.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement new appendix.py**

Rewrite `src/wxcli/migration/report/appendix.py` with:
- `generate_appendix(store) → str`
- 6 topic group functions: `_people_group()`, `_devices_group()`, `_features_group()`, `_routing_group()`, `_decisions_group()`, `_data_quality_group()`
- Decision aggregation: group `store.get_all_decisions()` by `type`, render one card per type with count + explainer summary + optional detail table
- Use `strip_canonical_id()` on all canonical IDs in output
- Use `DECISION_TYPE_DISPLAY_NAMES` for type headers
- All `<details>` start **without** the `open` attribute (collapsed by default)
- Each `<summary>` includes a count summary (e.g., "10 users, 4 shared lines, 9 extensions")

- [ ] **Step 4: Run tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_appendix.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/appendix.py tests/migration/report/test_appendix.py
git commit -m "feat(report): rewrite appendix with 6 topic groups and decision aggregation"
```

---

## Task 8: Assembler Updates

**Files:**
- Modify: `src/wxcli/migration/report/assembler.py`
- Modify: `tests/migration/report/test_assembler.py`

- [ ] **Step 1: Write tests for new assembler features**

Add to / update `tests/migration/report/test_assembler.py`:
- Dark interstitial bar present (`"TECHNICAL REFERENCE"` text)
- Sidebar nav has 4 executive items (numbered 1-4) and 6 technical items (topic names)
- `max-width` rule present in detail panel
- Summary bar still present with score, users, devices, sites

- [ ] **Step 2: Update assembler.py**

Modify `src/wxcli/migration/report/assembler.py`:
- Update sidebar nav: 4 executive items (`The Verdict`, `Your Environment`, `Migration Scope`, `Next Steps`) with teal icons + 6 technical items with gray icons
- Add dark interstitial `<div>` between executive HTML and appendix HTML
- Add `max-width: 720px; margin: 0 auto;` wrapper around detail panel content
- Update summary bar to match new section structure

- [ ] **Step 3: Run all assembler tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_assembler.py -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add src/wxcli/migration/report/assembler.py tests/migration/report/test_assembler.py
git commit -m "feat(report): update assembler with dark interstitial, new sidebar nav, max-width"
```

---

## Task 9: Full Test Suite & E2E Validation

**Files:**
- Modify: `tests/migration/report/test_e2e.py` (if assertions need updating)
- Run: all report tests

- [ ] **Step 1: Run the full report test suite**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/ -v`
Expected: All tests PASS. Fix any remaining assertion failures from v1 → v2 changes.

- [ ] **Step 2: Run the full migration test suite (broader regression check)**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/ -v --timeout=60`
Expected: All 1294+ tests PASS. Report changes are read-only on the store — no side effects expected.

- [ ] **Step 3: Generate report from test bed and verify visually**

```bash
cd /Users/ahobgood/Documents/webexCalling
wxcli cucm report --brand "Acme Corporation" --prepared-by "Adam Hobgood" --project cucm-testbed-2026-03-24
open ~/.wxcli/migrations/cucm-testbed-2026-03-24/assessment-report.html
```

Manual visual checks:
- Page 1: Verdict sentence present, score gauge smaller, factor bars visible, key findings list
- Page 2: Four semantic groups (People, Devices, Call Features, Sites), stacked bar for devices
- Page 3: Three effort bands (green/amber/red), aggregated items, decision resolution bar
- Page 4: Prerequisite checklist, planning phase items, CTA box
- Technical Reference: Dark interstitial bar visible, 6 collapsed groups, click to expand works
- No canonical ID prefixes visible anywhere (`css:`, `device:`, `dn:`, `location:`, `voicemail_profile:`)
- Text is readable — no gray-on-warm contrast issues
- Print: Ctrl+P shows linear layout, 4 executive pages, expanded appendix

- [ ] **Step 4: E2E test for no canonical IDs in output**

Add to `tests/migration/report/test_e2e.py`:

```python
def test_no_canonical_id_prefixes_in_report(self):
    """Customer-facing report should not contain internal canonical ID prefixes."""
    html = self.report_html  # from existing e2e setup
    # These prefixes should never appear in customer-facing output
    for prefix in ["css:", "device:", "location:", "dn:", "voicemail_profile:", "partition:"]:
        # Allow them in HTML id attributes and nav hrefs, but not in visible text
        # Simple check: they shouldn't appear outside of attribute values
        visible_text = html.replace('id="', '').replace('href="#', '')
        assert f">{prefix}" not in visible_text, f"Canonical prefix '{prefix}' found in visible report text"
```

- [ ] **Step 5: Run final test suite**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/ -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/migration/report/
git commit -m "test(report): update e2e tests for v2 report structure"
```

---

## Task 10: Update Module CLAUDE.md

**Files:**
- Modify: `src/wxcli/migration/report/CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md to reflect v2 architecture**

Key updates:
- Add `helpers.py` to the file table
- Update executive.py description (4 pages: Verdict, Environment, Scope, Next Steps)
- Update appendix.py description (6 topic groups, decision aggregation)
- Update charts.py description (stacked_bar_chart replaces donut, traffic_light_boxes removed)
- Update explainer.py description (generate_verdict, generate_key_findings, DECISION_TYPE_DISPLAY_NAMES)
- Update score.py description (display_name field)
- Update CSS design system section (contrast rules, effort bands, max-width)
- Add v2 design spec reference

- [ ] **Step 2: Commit**

```bash
git add src/wxcli/migration/report/CLAUDE.md
git commit -m "docs(report): update CLAUDE.md for v2 report architecture"
```
