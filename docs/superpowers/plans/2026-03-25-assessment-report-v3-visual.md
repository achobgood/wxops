# Assessment Report v3 — Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the editorial design system (Inter/teal/warm cream) with "Authority Minimal" (IBM Plex Sans/corporate blue/floating card on gray) to make the assessment report look like a $100k consulting deliverable.

**Architecture:** CSS-first rewrite in `styles.py` + targeted HTML adjustments in `assembler.py`, `executive.py`, and `charts.py`. No new files. No store/data/logic changes. Existing class names preserved where possible to minimize test breakage.

**Tech Stack:** Python string templates (HTML/CSS), inline SVG charts, IBM Plex Sans + IBM Plex Mono from Google Fonts.

**Spec:** `docs/superpowers/specs/2026-03-25-assessment-report-v3-visual-design.md`

---

## File Map

| File | Change Type | What Changes |
|------|-------------|-------------|
| `src/wxcli/migration/report/styles.py` | **Rewrite** | Entire REPORT_CSS constant + GOOGLE_FONTS_LINKS |
| `src/wxcli/migration/report/assembler.py` | **Modify** | Sidebar HTML, summary bar layout, content-card wrapper, body bg |
| `src/wxcli/migration/report/charts.py` | **Modify** | `_FONT` constant, gauge score number color, gauge label style |
| `src/wxcli/migration/report/executive.py` | **Modify** | Section kickers, conclusion headings, factor sort order, device bar colors |
| `tests/migration/report/test_charts.py` | **Modify** | Update font assertion in gauge test |
| `tests/migration/report/test_assembler.py` | **Modify** | Update "Assessment Verdict" assertion |
| `tests/migration/report/test_executive.py` | **Modify** | Update "Assessment Verdict" assertion, add kicker test |

## Test Impact Analysis

**106 existing tests.** Only 3 assertions break:

1. `test_assembler.py::test_contains_executive_and_appendix` (line 26) — asserts `"Assessment Verdict" in html`. The h2 text changes to a conclusion heading. Fix: assert on section ID instead.
2. `test_executive.py::test_page1_verdict` (line 24) — same assertion. Fix: assert on verdict class or section kicker text.
3. `test_charts.py::test_gauge_color_matches_input` (line 19) — asserts `"#C62828" in svg`. Still passes because the arc stroke uses the color. No fix needed.

Everything else passes unchanged because tests assert on class names, section IDs, and content text — not CSS values or font names.

---

## Task 1: Rewrite styles.py — Design Tokens and Base Styles

**Files:**
- Modify: `src/wxcli/migration/report/styles.py`

This is the largest task. The entire `REPORT_CSS` string and `GOOGLE_FONTS_LINKS` are replaced. Written in 3 steps to avoid large writes.

- [ ] **Step 1: Update GOOGLE_FONTS_LINKS and CSS custom properties**

Replace the top of `styles.py`:

```python
"""CSS design system for the CUCM assessment report v3 (Authority Minimal).

Single constant `REPORT_CSS` — embedded directly into the HTML report
by the assembler.  Google Fonts loaded via <link> tags in the <head>
(see GOOGLE_FONTS_LINKS).

Design spec: docs/superpowers/specs/2026-03-25-assessment-report-v3-visual-design.md
"""

GOOGLE_FONTS_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=IBM+Plex+Mono:wght@400;500;600&'
    'family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
)
```

Then replace the `:root` block through the base reset section with the new tokens. See the spec's "Color Palette" and "Typography" sections for exact values. Key tokens:

```css
:root {
    --navy-900: #0f1729;
    --navy-800: #1e293b;
    --text-primary: #111827;
    --text-body:    #374151;
    --text-muted:   #6b7280;
    --text-faint:   #9ca3af;
    --accent:       #2563eb;
    --accent-tint:  #eff6ff;
    --success:       #059669;
    --success-tint:  #ecfdf5;
    --warning:       #d97706;
    --warning-tint:  #fffbeb;
    --critical:      #dc2626;
    --critical-tint: #fef2f2;
    --chart-focal:   #2563eb;
    --chart-gray:    #94a3b8;
    --chart-bg:      #f3f4f6;
    --surface:       #ffffff;
    --page-bg:       #f4f5f7;
    --border:        #e5e7eb;
    --border-strong: #d1d5db;
    --font-body: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', 'Menlo', 'Consolas', monospace;
    --spacing-xs:  4px;
    --spacing-sm:  8px;
    --spacing-md:  16px;
    --spacing-lg:  24px;
    --spacing-xl:  32px;
    --spacing-xxl: 48px;

    /* Legacy aliases (keep for appendix.py / explainer.py references) */
    --color-primary:    var(--accent);
    --color-success:    var(--success);
    --color-warning:    var(--warning);
    --color-critical:   var(--critical);
    --color-text:       var(--text-primary);
    --color-text-muted: var(--text-muted);
    --color-text-light: var(--text-faint);
    --color-bg:         var(--page-bg);
    --color-border:     var(--border);
    --warm-50:          var(--page-bg);
    --slate-100:        var(--chart-bg);
    --slate-300:        var(--border-strong);
    --slate-500:        var(--text-muted);
    --slate-900:        var(--navy-900);
}
```

Note: Legacy aliases ensure that appendix.py, explainer.py, and charts.py references to `var(--color-primary)` etc. resolve correctly without modifying those files.

- [ ] **Step 2: Replace base, sidebar, summary bar, heading, and layout CSS**

Replace all CSS from the base reset through the summary bar section. Key changes:
- `html { font-size: 16px; }` (was `10pt`)
- `body { background: var(--page-bg); color: var(--text-body); }` (was white bg)
- `.sidebar { width: 260px; }` (was 280px)
- New `.sidebar-header`, `.sidebar-kicker`, `.sidebar-meta` classes
- New `.nav-dot` class (replaces `.nav-number`)
- `.detail-panel { margin-left: 260px; }` (was 280px)
- New `.content-card` class for floating page effect
- `.summary-bar` becomes fixed-top, horizontal inline layout
- `h1, h2` lose teal color — use `var(--text-primary)`, no border-bottom
- New `.section-kicker` class
- `.verdict` uses `var(--accent)` border and `var(--accent-tint)` bg (was teal)

Exact CSS for each section is in the mockup at `.superpowers/brainstorm/38786-1774470618/content/03-verdict-page.html` and the spec.

- [ ] **Step 3: Replace component CSS (tables, cards, badges, effort bands, print)**

Replace remaining CSS sections. Key changes:
- Tables: `tbody tr:hover { background: var(--page-bg); }` (was warm-50)
- `.stat-card .stat-number { font-size: 1.75rem; }` (was 1.4rem)
- Badge colors updated to new semantic palette
- `.effort-band` uses left-border + tint bg pattern (was bordered card)
- `.callout.info` uses accent (was teal)
- `.cta-box` uses accent (was teal)
- `.css-topology li::before` uses accent (was teal)
- `.explanation` border uses accent (was teal)
- `details[open] { border-color: var(--accent); }` (was teal)
- Print: `html { font-size: 10pt; }`, hide `.summary-bar`, `.content-card { box-shadow: none; border-radius: 0; }`

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/migration/report/test_score.py tests/migration/report/test_helpers.py -v`
Expected: All PASS (no CSS assertions in these files)

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/styles.py
git commit -m "feat(report): rewrite CSS to Authority Minimal design system

Replace Inter/teal/warm cream with IBM Plex Sans/corporate blue/floating
card on gray. All new tokens with legacy aliases for backward compat."
```

---

## Task 2: Update charts.py — Font and Gauge Colors

**Files:**
- Modify: `src/wxcli/migration/report/charts.py`
- Test: `tests/migration/report/test_charts.py`

- [ ] **Step 1: Update the `_FONT` constant**

```python
# Old:
_FONT = 'font-family="Inter, system-ui, sans-serif"'

# New:
_FONT = 'font-family="IBM Plex Sans, system-ui, sans-serif"'
```

- [ ] **Step 2: Update gauge_chart score number fill**

In `gauge_chart()`, change the score text line from:

```python
f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" '
f'{_FONT} font-size="36" font-weight="700" fill="{color}">{score}</text>',
```

To:

```python
f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" '
f'{_FONT} font-size="36" font-weight="700" fill="#111827">{score}</text>',
```

The score number is now always dark (#111827), not accent-colored. The arc still uses the passed `color`.

- [ ] **Step 3: Update gauge_chart label style**

Change the label text line from:

```python
f'<text x="{cx}" y="{cy + 50}" text-anchor="middle" '
f'{_FONT} font-size="12" fill="#616161">{html.escape(label)}</text>',
```

To:

```python
f'<text x="{cx}" y="{cy + 50}" text-anchor="middle" '
f'{_FONT} font-size="9" font-weight="500" letter-spacing="0.1em" '
f'fill="#6b7280">{html.escape(label.upper())}</text>',
```

Label is now uppercase, smaller, with letter-spacing — matches the design system's `--text-xs` pattern.

- [ ] **Step 4: Run chart tests**

Run: `python -m pytest tests/migration/report/test_charts.py -v`
Expected: All 13 tests PASS. The gauge viewBox/width are unchanged. The color assertions still pass because the arc stroke still contains the passed color.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/charts.py
git commit -m "feat(report): update chart font and gauge to Authority Minimal

IBM Plex Sans replaces Inter. Score number is dark (#111827) instead of
accent-colored. Gauge label is uppercase with letter-spacing."
```

---

## Task 3: Update assembler.py — Sidebar, Summary Bar, Content Card

**Files:**
- Modify: `src/wxcli/migration/report/assembler.py`

- [ ] **Step 1: Update sidebar HTML in `_build_sidebar_nav()`**

Replace the nav items to use dot indicators instead of numbered circles:

```python
def _build_sidebar_nav(executive_only: bool) -> str:
    """Build the sidebar navigation HTML."""
    nav_items = [
        '<nav>',
        '<div class="nav-label">Executive Summary</div>',
        '<a href="#score"><span class="nav-dot exec"></span> The Verdict</a>',
        '<a href="#inventory"><span class="nav-dot exec"></span> Your Environment</a>',
        '<a href="#scope"><span class="nav-dot exec"></span> Migration Scope</a>',
        '<a href="#next-steps"><span class="nav-dot exec"></span> Next Steps</a>',
    ]

    if not executive_only:
        nav_items.extend([
            '<div class="nav-divider"></div>',
            '<div class="nav-label">Technical Reference</div>',
            '<a href="#people"><span class="nav-dot tech"></span> People</a>',
            '<a href="#devices"><span class="nav-dot tech"></span> Devices</a>',
            '<a href="#features"><span class="nav-dot tech"></span> Call Features</a>',
            '<a href="#routing"><span class="nav-dot tech"></span> Routing</a>',
            '<a href="#gateways"><span class="nav-dot tech"></span> Gateways</a>',
            '<a href="#decisions"><span class="nav-dot tech"></span> Decisions</a>',
            '<a href="#data-quality"><span class="nav-dot tech"></span> Data Quality</a>',
        ])

    nav_items.append('</nav>')
    return "\n    ".join(nav_items)
```

- [ ] **Step 2: Update sidebar header in `assemble_report()`**

Replace the sidebar brand HTML:

```python
# Old:
    <div class="sidebar-brand">
      <span class="brand-name">{safe_brand}</span>
      <span class="brand-sub">Migration Assessment</span>
    </div>

# New:
    <div class="sidebar-header">
      <div class="sidebar-kicker">Migration Assessment</div>
      <div class="sidebar-brand">{safe_brand}</div>
      <div class="sidebar-meta">Prepared by {safe_prepared_by} &middot; {date_str}</div>
    </div>
```

- [ ] **Step 3: Update summary bar to inline layout**

Replace the summary_bar construction:

```python
    summary_bar = (
        f'<div class="summary-bar">'
        f'<div class="summary-stat"><span class="value">{score_result.score}</span>'
        f'<span class="label">Score</span></div>'
        f'<div class="summary-stat"><span class="value">{user_count}</span>'
        f'<span class="label">Users</span></div>'
        f'<div class="summary-stat"><span class="value">{device_count}</span>'
        f'<span class="label">Devices</span></div>'
        f'<div class="summary-stat"><span class="value">{location_count}</span>'
        f'<span class="label">Sites</span></div>'
        f'</div>'
    )
```

Note: inner elements change from `<div class="stat-value">` to `<span class="value">` and `<div class="stat-label">` to `<span class="label">`. CSS handles the inline layout.

- [ ] **Step 4: Wrap content in content-card div**

In the HTML template, add a `.content-card` wrapper inside `.detail-panel-content`:

```python
  <!-- Main content -->
  <div class="detail-panel">
    <div class="detail-panel-content">
      <div class="content-card">
      {executive_html}
      {interstitial_html}
      {appendix_html}
      </div>
    </div>
  </div>
```

Also update footer to use `margin-left: 260px` (was 280px):

```python
  <footer class="report-footer" style="margin-left:260px;">
```

- [ ] **Step 5: Run assembler tests**

Run: `python -m pytest tests/migration/report/test_assembler.py -v`
Expected: 1 failure on `test_contains_executive_and_appendix` (will fix in Task 5). All others PASS.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/report/assembler.py
git commit -m "feat(report): update sidebar, summary bar, and content card layout

Dot nav indicators replace numbered circles. Summary bar uses inline
value+label. Content wrapped in floating card div."
```

---

## Task 4: Update executive.py — Conclusion Headings and Factor Sort

**Files:**
- Modify: `src/wxcli/migration/report/executive.py`

- [ ] **Step 1: Add section kicker + conclusion heading to Page 1**

In `_page_verdict()`, replace the h2:

```python
# Old:
f'<h2>Assessment Verdict</h2>',

# New:
f'<div class="section-kicker">The Verdict</div>',
f'<h2>{verdict_text}</h2>',
```

And change the verdict callout from using `verdict_text` (which is now the h2) to using a detail sentence. Add a new helper or inline the detail:

```python
def _page_verdict(store: MigrationStore, brand: str) -> str:
    result = compute_complexity_score(store)
    gauge_svg = gauge_chart(result.score, result.color, result.label)
    verdict_text = generate_verdict(result, store)
    findings = generate_key_findings(store)

    # Build detail sentence for callout
    decisions = store.get_all_decisions()
    total = len(decisions)
    resolved = sum(1 for d in decisions if d.get("chosen_option"))
    detail_parts = []
    if total > 0:
        detail_parts.append(
            f'All <strong>{resolved} decisions</strong> were auto-resolved '
            f'— no manual input needed at this stage.'
            if resolved == total else
            f'<strong>{resolved} of {total}</strong> decisions resolved '
            f'— {total - resolved} still need review.'
        )
    # Top contributing factors
    top_factors = sorted(result.factors, key=lambda f: f["raw_score"], reverse=True)[:2]
    if top_factors:
        names = " and ".join(
            f'<strong>{f.get("display_name", f["name"]).lower()}</strong>'
            for f in top_factors
        )
        detail_parts.append(f'Moderate complexity is driven by {names}.')
    detail_text = " ".join(detail_parts)

    parts = [
        f'<section id="score">',
        f'<div class="section-kicker">The Verdict</div>',
        f'<h2>{verdict_text}</h2>',
        f'<div class="verdict">{detail_text}</div>',
        f'<div class="score-gauge">\n{gauge_svg}\n</div>',
    ]
```

- [ ] **Step 2: Sort factor bars by raw_score descending, apply focal/gray logic**

In `_page_verdict()`, replace the factor rendering:

```python
    if result.factors:
        sorted_factors = sorted(result.factors, key=lambda f: f["raw_score"], reverse=True)
        max_score = sorted_factors[0]["raw_score"] if sorted_factors else 0
        parts.append('<div class="score-breakdown">')
        for i, factor in enumerate(sorted_factors):
            display = factor.get("display_name", factor["name"])
            raw = factor["raw_score"]
            # Highest-scoring factor gets accent blue, rest get gray
            color = "var(--chart-focal)" if i == 0 and raw > 0 else "var(--chart-gray)"
            parts.append(
                f'<div class="factor-row">'
                f'<span class="factor-label">{html.escape(display)}</span>'
                f'<div class="factor-bar">'
                f'<div class="factor-fill" style="width:{raw}%;background:{color};"></div>'
                f'</div>'
                f'<span class="factor-value">{raw}</span>'
                f'</div>'
            )
        parts.append('</div>')
```

- [ ] **Step 3: Add section kickers to Pages 2-4**

In `_page_environment()`:
```python
# Old:
f'<h2>Your Environment</h2>',

# New:
f'<div class="section-kicker">Your Environment</div>',
f'<h2>{user_count} users across {location_count} sites with {len(devices) if devices else 0} devices</h2>',
```

In `_page_scope()`:
```python
# Old:
f'<h2>Migration Scope</h2>',

# New:
f'<div class="section-kicker">Migration Scope</div>',
f'<h2>{len(auto)} items migrate automatically — {len(manual)} require manual work</h2>',
```

In `_page_next_steps()`:
```python
# Old:
f'<h2>Next Steps</h2>',

# New:
f'<div class="section-kicker">Next Steps</div>',
f'<h2>Ready to plan — all prerequisites identified</h2>',
```

- [ ] **Step 4: Update device stacked bar colors to use semantic tokens**

In `_page_environment()`, update the device compatibility segment colors:

```python
# Old:
{"label": "Native MPP", "value": native, "color": "#2E7D32"},
{"label": "Convertible", "value": convertible, "color": "#F57C00"},
{"label": "Incompatible", "value": incompatible, "color": "#C62828"},

# New:
{"label": "Native MPP", "value": native, "color": "#059669"},
{"label": "Convertible", "value": convertible, "color": "#d97706"},
{"label": "Incompatible", "value": incompatible, "color": "#dc2626"},
```

These match the new `--success`, `--warning`, `--critical` tokens.

- [ ] **Step 5: Run executive tests**

Run: `python -m pytest tests/migration/report/test_executive.py -v`
Expected: 1 failure on `test_page1_verdict` (asserts "Assessment Verdict"). Will fix in Task 5. All others PASS.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/report/executive.py
git commit -m "feat(report): add conclusion headings and section kickers

Every h2 now states the takeaway, not the topic. Section kickers provide
the original topic label. Factor bars sorted by score descending with
focal/gray color logic."
```

---

## Task 5: Fix Broken Test Assertions

**Files:**
- Modify: `tests/migration/report/test_assembler.py`
- Modify: `tests/migration/report/test_executive.py`

- [ ] **Step 1: Fix test_assembler.py::test_contains_executive_and_appendix**

```python
# Old (line 26):
assert "Assessment Verdict" in html  # executive

# New:
assert 'id="score"' in html  # executive section present
```

- [ ] **Step 2: Fix test_executive.py::test_page1_verdict**

```python
# Old (line 24):
assert "Assessment Verdict" in html

# New:
assert "section-kicker" in html  # kicker present
assert "The Verdict" in html  # kicker text
```

- [ ] **Step 3: Add test for conclusion heading pattern**

Add a new test in `test_executive.py`:

```python
def test_page1_has_conclusion_heading(self, populated_store):
    from wxcli.migration.report.executive import generate_executive_summary
    html = generate_executive_summary(populated_store,
        brand="Acme Corp", prepared_by="Test SE")
    # h2 should contain dynamic content, not a static topic label
    assert "section-kicker" in html
    # The verdict h2 should NOT be a static label
    assert "<h2>Assessment Verdict</h2>" not in html
```

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest tests/migration/report/ -v`
Expected: All 106+ tests PASS (106 original + 1 new).

- [ ] **Step 5: Commit**

```bash
git add tests/migration/report/test_assembler.py tests/migration/report/test_executive.py
git commit -m "test(report): update assertions for Authority Minimal headings

Fix 2 assertions that checked for static 'Assessment Verdict' text.
Add test verifying conclusion heading pattern."
```

---

## Task 6: Generate Report and Visual Verification

**Files:** None (verification only)

- [ ] **Step 1: Generate a fresh report from the test bed**

```bash
cd /Users/ahobgood/Documents/webexCalling
python -m wxcli.main cucm report \
  --db ~/.wxcli/migrations/cucm-testbed-2026-03-24/migration.db \
  --brand "Acme Corporation" \
  --prepared-by "Adam Hobgood" \
  --output assessment-report-v3.html
```

- [ ] **Step 2: Open in browser and verify against spec checklist**

Check each item from the spec's Validation Criteria:
- No teal (#00897B) anywhere
- IBM Plex Sans and IBM Plex Mono only
- No pt units in screen CSS
- Content card floats on gray background with shadow
- Every h2 is a conclusion statement with section kicker above
- Score gauge number is dark (#111827)
- Factor bars sorted by score descending, highest in blue
- Summary bar uses inline layout
- Sidebar has dot indicators with blue/gray distinction
- All body text is #374151 or darker
- Print: sidebar hidden, content full-width

- [ ] **Step 3: Run E2E tests**

Run: `python -m pytest tests/migration/report/test_e2e.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite one final time**

Run: `python -m pytest tests/migration/report/ -v`
Expected: All PASS

- [ ] **Step 5: Commit generated report (optional, for review)**

```bash
git add assessment-report-v3.html
git commit -m "docs: add v3 assessment report sample for visual review"
```
