# Assessment Report v4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge v1's warm editorial visual design with v3's data improvements into a unified v4 report.

**Architecture:** Replace styles.py CSS, restructure assembler.py layout (remove summary bar, restore 320px sidebar with numbered/lettered nav), update executive.py sections (remove kickers, add donut chart, tier-colored gauge), and restructure appendix.py from 10 topic groups to 14 lettered sections (A-N).

**Tech Stack:** Python (string-based HTML generation), CSS, inline SVG charts

**Spec:** `docs/superpowers/specs/2026-03-26-assessment-report-v4-design.md`

**IMPORTANT:** Write large files in sections using create-then-append. Never write >300 lines in a single Write call. For styles.py (~1000 lines), write the initial file with the first ~250 lines, then use Edit to append remaining sections.

---

### Task 1: Rewrite styles.py — v1 Editorial CSS + v3 Component Styles

**Files:**
- Rewrite: `src/wxcli/migration/report/styles.py`

The v1 CSS lives in `assessment-report.html` lines 10-856. Extract it and adapt into styles.py, then add new component styles for v3 features (score-layout, effort-bands, key-findings, verdict, cta-box, resolution-bar).

- [ ] **Step 1: Write styles.py header + Google Fonts + CSS root variables (lines 1-100)**

Replace the entire file. Start with:

```python
"""CSS design system for the CUCM assessment report v4 (Editorial + v3 Data).

Single constant ``REPORT_CSS`` — embedded directly into the HTML report
by the assembler.  Google Fonts loaded via <link> tags in the <head>
(see GOOGLE_FONTS_LINKS).
"""

GOOGLE_FONTS_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=IBM+Plex+Mono:wght@400;500&'
    'family=Lora:ital,wght@0,400;0,600;0,700;1,400&'
    'family=Source+Sans+3:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
)

REPORT_CSS = """\
/* ==========================================================================
   CUCM Assessment Report v4 — Editorial Design System
   ========================================================================== */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    /* -- Warm neutrals ---------------------------------------------------- */
    --warm-50:  #fdf8f3;
    --warm-100: #f9efe4;
    --warm-200: #f0dcc6;
    --warm-300: #e3c4a0;
    --warm-400: #d4a574;
    --warm-500: #b8864e;
    --warm-600: #96693a;
    --warm-700: #6b4a2a;
    --warm-800: #45301c;
    --warm-900: #2a1c10;

    --slate-50:  #f8f9fa;
    --slate-100: #eef0f3;
    --slate-200: #dde1e7;
    --slate-300: #bcc3cd;
    --slate-400: #8e97a5;
    --slate-500: #636e7e;
    --slate-600: #4a5363;
    --slate-700: #353d4a;
    --slate-800: #242a33;
    --slate-900: #181c22;

    /* -- Brand / status palette ------------------------------------------- */
    --primary:       #00897B;
    --primary-light: #E0F2F1;
    --success:       #2E7D32;
    --success-light: #E8F5E9;
    --warning:       #EF6C00;
    --warning-light: #FFF3E0;
    --critical:      #C62828;
    --critical-light:#FFEBEE;

    /* Legacy aliases (charts.py, appendix.py, explainer.py reference these) */
    --color-primary:  #00897B;
    --color-success:  #2E7D32;
    --color-warning:  #EF6C00;
    --color-critical: #C62828;
    --color-neutral:  var(--slate-700);
    --color-bg:       var(--warm-50);
    --color-border:   var(--warm-200);
    --color-text:     var(--slate-800);
    --color-text-muted: var(--slate-500);
    --color-text-light: var(--slate-400);
    --color-zebra:   var(--warm-100);

    /* -- Typography ------------------------------------------------------- */
    --font-display: 'Lora', Georgia, serif;
    --font-body:    'Source Sans 3', 'Source Sans Pro', system-ui, sans-serif;
    --font-mono:    'IBM Plex Mono', 'Menlo', monospace;
    --font-family:  var(--font-body);

    /* -- Spacing (8px grid) ----------------------------------------------- */
    --spacing-xs:  4px;
    --spacing-sm:  8px;
    --spacing-md:  16px;
    --spacing-lg:  24px;
    --spacing-xl:  32px;
    --spacing-xxl: 48px;

    /* -- Radii ------------------------------------------------------------ */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
}
```

- [ ] **Step 2: Append base, page-header, sidebar, and detail-panel CSS**

Use Edit to append after the `:root` block closing `}`. This section covers: html/body base styles, page-header (slate-900 bg), sidebar+content grid layout (320px sidebar), step-list nav items, step-icon circles, detail-panel. Copy these directly from v1 (`assessment-report.html` lines 86-253).

Key classes:
- `html` — font-size 17px, antialiased
- `body` — font-family var(--font-body), background var(--warm-50), color var(--slate-800)
- `.page-header` — background slate-900, Lora headings
- `.main-layout` — grid 320px 1fr
- `.step-list` — sticky sidebar, white bg, right border
- `.step-item` — flex, 3px left border, hover warm-100
- `.step-icon` — 22px circle, .exec=primary, .tech=slate-500
- `.detail-panel` — padding 2.5rem 3rem, overflow-y auto

- [ ] **Step 3: Append headings, prose, sections, score-hero, stat-grid CSS**

Append heading styles (h1-h4 with Lora, serif), prose (.muted, .small, .lead-sentence), section margin, score-hero (centered gauge), stat-grid (auto-fill minmax 140px), stat-card (warm-100 bg, colored border variants). Copy from v1 lines 256-383.

- [ ] **Step 4: Append tables, badges, callouts, explanations CSS**

Append table styles (deg-table pattern: uppercase headers, warm-200 borders, hover), badges (direct/low green, approx/medium orange, decision/critical/high red, auto teal), callout boxes (left border + colored bg), explanation cards (severity-colored). Copy from v1 lines 385-511.

- [ ] **Step 5: Append NEW v3 component styles — score-layout, score-breakdown, key-findings**

These are new styles adapted to v1's palette. Append:

```css
/* ==========================================================================
   Score Layout (v3 data, v1 theme)
   ========================================================================== */

.score-layout {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 2rem;
    align-items: start;
    margin: 1rem 0 2rem;
}

.score-gauge {
    display: flex;
    justify-content: center;
    align-items: center;
}

.score-gauge svg {
    width: 100%;
    height: auto;
    max-width: 180px;
}


/* -- Score breakdown bars ------------------------------------------------- */
.score-breakdown {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.score-breakdown .factor-row {
    display: grid;
    grid-template-columns: 140px 1fr 36px;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
}

.score-breakdown .factor-label {
    color: var(--slate-500);
    text-align: right;
    white-space: nowrap;
}

.score-breakdown .factor-bar {
    height: 10px;
    border-radius: 5px;
    background: var(--slate-100);
    overflow: hidden;
}

.score-breakdown .factor-fill {
    height: 100%;
    border-radius: 5px;
}

.score-breakdown .factor-value {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--slate-800);
    text-align: right;
}


/* -- Key findings --------------------------------------------------------- */
.key-findings {
    list-style: none;
    padding: 0;
    margin: 1rem 0;
}

.key-findings li {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--warm-200);
    font-size: 0.875rem;
    color: var(--slate-700);
    line-height: 1.5;
}

.key-findings li:last-child {
    border-bottom: none;
}

.key-findings .finding-icon {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.7rem;
    margin-top: 2px;
}

.key-findings .finding-icon.check {
    background: var(--success-light);
    color: var(--success);
}

.key-findings .finding-icon.alert {
    background: var(--warning-light);
    color: var(--warning);
}
```

- [ ] **Step 6: Append NEW v3 component styles — effort-bands, verdict, cta-box, resolution-bar**

```css
/* ==========================================================================
   Effort Bands (v3 data, v1 theme)
   ========================================================================== */

.effort-band {
    border-left: 3px solid var(--slate-300);
    background: var(--slate-50);
    padding: 0.875rem 1.125rem;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    margin: 0.75rem 0;
}

.effort-band h4 {
    margin: 0 0 0.375rem 0;
    font-family: var(--font-display);
    font-size: 0.95rem;
}

.effort-band p {
    font-size: 0.85rem;
    color: var(--slate-500);
    margin-bottom: 0.5rem;
}

.effort-band.auto {
    border-left-color: var(--success);
    background: var(--success-light);
}
.effort-band.auto h4 { color: var(--success); }

.effort-band.planning {
    border-left-color: var(--warning);
    background: var(--warning-light);
}
.effort-band.planning h4 { color: var(--warning); }

.effort-band.manual {
    border-left-color: var(--critical);
    background: var(--critical-light);
}
.effort-band.manual h4 { color: var(--critical); }

.effort-band ul {
    margin: 0;
    padding-left: var(--spacing-lg);
    font-size: 0.85rem;
    color: var(--slate-700);
}

.effort-band ul li {
    margin-bottom: 4px;
}


/* -- Verdict callout ------------------------------------------------------ */
.verdict {
    padding: 1rem 1.25rem;
    border-left: 3px solid var(--primary);
    background: var(--primary-light);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    margin: 0.75rem 0 1.5rem;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--slate-700);
}


/* -- CTA box -------------------------------------------------------------- */
.cta-box {
    background: var(--primary-light);
    border: 2px solid var(--primary);
    border-radius: var(--radius-md);
    padding: var(--spacing-lg);
    text-align: center;
    margin: var(--spacing-lg) 0;
}

.cta-box h3 {
    color: var(--primary);
    margin-top: 0;
}


/* -- Decision resolution bar ---------------------------------------------- */
.resolution-bar {
    display: flex;
    height: 20px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    margin: var(--spacing-sm) 0;
}

.resolution-bar .bar-auto { background: var(--success); }
.resolution-bar .bar-planning { background: var(--warning); }
.resolution-bar .bar-manual { background: var(--critical); }
```

- [ ] **Step 7: Append chart containers, details/summary, CSS topology, section-indicator, checklist, footer CSS**

Copy from v1 lines 514-695. Key classes:
- `.chart-container` — flex wrap for SVG charts
- `details` / `summary` — collapsible sections (warm-200 border, primary on open, Lora font, chevron)
- `.details-content` — padding inside details (replaces v3's `details > .details-content`)
- `.section-indicator` — 24px circle for appendix letter labels
- `.css-topology` — nested list with teal dots
- `.report-footer` — slate-900 bg
- `.checklist` — checkbox list items

- [ ] **Step 8: Append responsive + print CSS, close the REPORT_CSS string**

Copy responsive styles from v1 lines 728-855 (860px breakpoint, single-column collapse, print styles with sidebar hidden, details forced open, page breaks). Close with `"""` to end the REPORT_CSS string constant.

Key print rules:
- `.main-layout` → display block
- `.step-list` → display none
- `.page-header` → display none
- `.print-header` → display block, teal border-bottom
- `details > summary` → display none
- Page breaks before sections

- [ ] **Step 9: Run existing tests to see what fails**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_assembler.py tests/migration/report/test_executive.py tests/migration/report/test_appendix.py -x --tb=short 2>&1 | head -60`

Expected: Some tests may fail due to missing v3-specific CSS classes. Note failures — they'll be addressed in later tasks.

- [ ] **Step 10: Commit styles.py**

```bash
git add src/wxcli/migration/report/styles.py
git commit -m "refactor(report): replace v3 Authority Minimal CSS with v4 editorial design system

Restores v1 warm editorial palette (Lora/Source Sans, teal primary, warm
neutrals) while adding CSS for v3 data components (score-layout, effort-
bands, key-findings, verdict, cta-box, resolution-bar)."
```

---

### Task 2: Rewrite assembler.py — v1 Layout, Sidebar Nav, IntersectionObserver

**Files:**
- Rewrite: `src/wxcli/migration/report/assembler.py`

Remove summary bar, content-card wrapper, dark tech-interstitial. Restore v1's 320px grid layout with page-header, step-list sidebar (numbered 1-4 exec + lettered A-N tech), detail-panel, and IntersectionObserver JS.

- [ ] **Step 1: Rewrite assemble_report() — remove summary bar, restore v1 layout**

Replace the `assemble_report()` function body. Key changes:
- Remove `summary_bar` variable entirely
- Remove `interstitial_html` variable entirely
- Remove `<div class="content-card">` wrapper
- Use `<div class="page-header">` with brand/subtitle/meta (v1 pattern)
- Use `<div class="main-layout">` grid with `.step-list` sidebar + `.detail-panel`
- Add IntersectionObserver `<script>` before `</body>`
- Footer inside detail-panel (no `margin-left:260px`)

New HTML structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>...</head>
<body>
  <div class="print-header">...</div>
  <div class="page-header">
    <div class="brand">{brand}</div>
    <h1>CUCM Migration Assessment</h1>
    <div class="subtitle">Prepared by {prepared_by}</div>
    <div class="meta">{date_str}</div>
  </div>
  <div class="main-layout">
    <nav class="step-list">...</nav>
    <div class="detail-panel">
      {executive_html}
      {appendix_html}
      <footer class="report-footer">...</footer>
    </div>
  </div>
  <script>/* IntersectionObserver */</script>
</body>
</html>
```

- [ ] **Step 2: Rewrite _build_sidebar_nav() — numbered exec + lettered tech**

Replace with v1's step-item pattern using `.step-icon` circles:

```python
def _build_sidebar_nav(executive_only: bool) -> str:
    """Build the sidebar navigation HTML with numbered exec + lettered tech items."""
    exec_items = [
        ("1", "#score", "Migration Complexity"),
        ("2", "#inventory", "What You Have"),
        ("3", "#decisions", "What Needs Attention"),
        ("4", "#next-steps", "Next Steps"),
    ]

    tech_items = [
        ("A", "#objects", "Object Inventory"),
        ("B", "#decision-detail", "Decision Detail"),
        ("C", "#css-partitions", "CSS / Partitions"),
        ("D", "#device-detail", "Device Inventory"),
        ("E", "#dn-analysis", "DN Analysis"),
        ("F", "#user-device-map", "User/Device Map"),
        ("G", "#routing", "Routing Topology"),
        ("H", "#voicemail", "Voicemail Analysis"),
        ("I", "#coverage", "Data Coverage"),
        ("J", "#gateways", "Gateways & Analog Ports"),
        ("K", "#call-features", "Call Features"),
        ("L", "#button-templates", "Button Templates"),
        ("M", "#device-layouts", "Device Layouts"),
        ("N", "#softkeys", "Softkey Migration"),
    ]

    parts = [
        '<div class="step-list-section">',
        '<div class="step-list-section-title">Executive Summary</div>',
    ]
    for num, href, label in exec_items:
        parts.append(
            f'<a href="{href}" class="step-item">'
            f'<span class="step-icon exec">{num}</span> {html_mod.escape(label)}</a>'
        )
    parts.append('</div>')

    if not executive_only:
        parts.append('<div class="step-list-section">')
        parts.append('<div class="step-list-section-title">Technical Appendix</div>')
        for letter, href, label in tech_items:
            parts.append(
                f'<a href="{href}" class="step-item">'
                f'<span class="step-icon tech">{letter}</span> {html_mod.escape(label)}</a>'
            )
        parts.append('</div>')

    return "\n    ".join(parts)
```

- [ ] **Step 3: Add _intersection_observer_js() helper**

Add a helper that returns the IntersectionObserver script (from v1 lines 1688-1712):

```python
def _intersection_observer_js() -> str:
    """Return IntersectionObserver JS for sidebar scroll tracking."""
    return """<script>
(function() {
  const sections = document.querySelectorAll('.detail-panel section, .detail-panel details');
  const navLinks = document.querySelectorAll('.step-item');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        navLinks.forEach(link => {
          link.classList.toggle('active', link.getAttribute('href') === '#' + id);
        });
      }
    });
  }, { root: document.querySelector('.detail-panel'), threshold: 0.2 });
  sections.forEach(s => { if (s.id) observer.observe(s); });
})();
</script>"""
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_assembler.py -x --tb=short 2>&1 | head -40`

Expected: Several failures related to old assertions (summary-bar, tech-interstitial, etc.). Note them for Task 5.

- [ ] **Step 5: Commit assembler.py**

```bash
git add src/wxcli/migration/report/assembler.py
git commit -m "refactor(report): restore v1 editorial layout in assembler

Removes summary bar, content-card wrapper, and dark interstitial.
Restores 320px sidebar with numbered exec (1-4) and lettered tech (A-N)
nav items, IntersectionObserver scroll tracking, and v1 page-header."
```

---

### Task 3: Update executive.py — v1 Headings, Donut Chart, Tier-Colored Gauge

**Files:**
- Modify: `src/wxcli/migration/report/executive.py`

Remove section-kicker elements. Change heading style to v1's direct topic headings. Add donut_chart import. Pass tier color to gauge. Rename Section 3 heading.

- [ ] **Step 1: Update imports — add donut_chart**

Change line 14 from:
```python
from wxcli.migration.report.charts import gauge_chart, stacked_bar_chart
```
to:
```python
from wxcli.migration.report.charts import donut_chart, gauge_chart, stacked_bar_chart
```

- [ ] **Step 2: Update _page_verdict() — remove kicker, use tier color, change heading**

In `_page_verdict()`, make these changes:

a) Change gauge color from hardcoded `"#2563eb"` to `result.color` (tier-based green/amber/red):
```python
gauge_svg = gauge_chart(result.score, result.color, result.label)
```

b) Change factor bar focal color from `"var(--chart-focal)"` to `"var(--primary)"` and non-focal from `"var(--chart-gray)"` to `"var(--slate-400)"`:
```python
color = "var(--primary)" if i == 0 and raw > 0 else "var(--slate-400)"
```

c) Replace the section-kicker + conclusion-heading with a direct v1-style heading:
```python
parts = [
    f'<section id="score">',
    f'<h2>Migration Complexity Assessment</h2>',
    f'<div class="verdict">{verdict_text}</div>',
]
```

Remove the heading-building logic (lines 122-131 that construct the conclusion heading from driver names). Keep the detail_parts logic for the verdict — that feeds into `generate_verdict()` which is unchanged.

- [ ] **Step 3: Add stat grid to _page_verdict() after key-findings**

After the key-findings `</ul>`, before `</section>`, add the stat grid that was in v1's Section 1:

```python
# Stat grid
total_objects = _total_object_count(store)
parts.append('<div class="stat-grid">')
parts.append(_stat_card(html.escape(brand), "Customer"))
if cluster_name:
    parts.append(_stat_card(html.escape(cluster_name), "CUCM Cluster"))
if cucm_version:
    parts.append(_stat_card(html.escape(cucm_version), "CUCM Version"))
parts.append(_stat_card(str(total_objects), "Total Objects"))
parts.append(_stat_card(str(store.count_by_type("location")), "Sites"))
parts.append(_stat_card(str(store.count_by_type("user")), "Users"))
parts.append(_stat_card(str(len(store.get_objects("device"))), "Devices"))
parts.append('</div>')
```

This requires passing `brand`, `cluster_name`, and `cucm_version` to `_page_verdict()`. Update the function signature and call in `generate_executive_summary()`:

```python
def _page_verdict(store: MigrationStore, brand: str, cluster_name: str, cucm_version: str) -> str:
```

And in `generate_executive_summary()`:
```python
_page_verdict(store, brand, cluster_name, cucm_version),
```

- [ ] **Step 4: Update _page_environment() — remove kicker, add donut chart**

a) Replace section-kicker + conclusion-heading with direct heading:
```python
parts = [
    f'<section id="inventory">',
    f'<h2>What You Have</h2>',
]
```

b) In the Devices subsection, replace `stacked_bar_chart()` with `donut_chart()`:
```python
# Donut chart for device compatibility (replaces stacked bar)
donut_segments = [
    {"label": "Native MPP", "value": native, "color": "#2E7D32"},
    {"label": "Convertible", "value": convertible, "color": "#EF6C00"},
    {"label": "Incompatible", "value": incompatible, "color": "#C62828"},
]
donut_svg = donut_chart(donut_segments)
if donut_svg:
    parts.append(f'<div class="chart-container">{donut_svg}</div>')
```

Note: Use v1 status colors (#2E7D32, #EF6C00, #C62828) instead of v3's (#059669, #d97706, #dc2626).

- [ ] **Step 5: Update _page_scope() — rename to "What Needs Attention", change ID, add stat grid**

a) Change the section ID and heading:
```python
parts = [
    f'<section id="decisions">',
    f'<h2>What Needs Attention</h2>',
]
```

b) Remove the section-kicker line (`<div class="section-kicker">Migration Scope</div>`).

c) Add a decision summary stat grid BEFORE the effort bands:
```python
# Decision summary stat grid
decisions = store.get_all_decisions()
total_decisions = len(decisions)
resolved = sum(1 for d in decisions if d.get("chosen_option"))
unresolved = total_decisions - resolved
critical = sum(1 for d in decisions if d.get("severity", "").upper() == "CRITICAL")

parts.append('<div class="stat-grid">')
parts.append(_stat_card(str(resolved), "Auto-resolved"))
parts.append(_stat_card(str(unresolved), "Decisions Needed"))
if critical:
    parts.append(_stat_card(str(critical), "Critical"))
parts.append('</div>')
```

Note: The `decisions` variable is already fetched on the next line in the existing code — move the stat grid insertion before the `_classify_decisions()` call but after fetching `decisions`.

d) Keep the effort bands and resolution stats unchanged — they work with the v4 CSS.

- [ ] **Step 6: Update _page_next_steps() — remove kicker**

Replace:
```python
parts = [
    f'<section id="next-steps">',
    f'<div class="section-kicker">Next Steps</div>',
    f'<h2>Ready to plan — all prerequisites identified</h2>',
]
```
with:
```python
parts = [
    f'<section id="next-steps">',
    f'<h2>Next Steps</h2>',
]
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_executive.py -x --tb=short 2>&1 | head -40`

Note failures for Task 5.

- [ ] **Step 8: Commit executive.py**

```bash
git add src/wxcli/migration/report/executive.py
git commit -m "refactor(report): v4 executive summary — v1 headings, donut chart, tier gauge

Removes section-kicker elements, uses direct h2 headings, adds donut
chart for phone compatibility, passes tier color to gauge, renames
Section 3 to 'What Needs Attention', adds stat grid to Section 1."
```

---

### Task 4: Restructure appendix.py — Lettered A-N Sections

**Files:**
- Modify: `src/wxcli/migration/report/appendix.py`

Restructure from 10 unnamed topic groups to 14 lettered sections (A-N). Each `<details>` gets a letter prefix in its `<summary>`. Section IDs match the spec. The existing `_*_group()` functions are reused — we just reorder, rename IDs, and add missing sections (A=Object Inventory, E=DN Analysis, F=User/Device Map, H=Voicemail).

- [ ] **Step 1: Add stacked_bar_chart import**

Add at top of file:
```python
from wxcli.migration.report.charts import stacked_bar_chart
```

- [ ] **Step 2: Rewrite generate_appendix() — ordered A-N sections**

Replace the `generate_appendix()` function:

```python
def generate_appendix(store: MigrationStore) -> str:
    """Generate the technical appendix HTML with lettered A-N sections."""
    sections = [
        ("A", _object_inventory(store)),
        ("B", _decisions_group(store)),
        ("C", _css_partitions(store)),
        ("D", _device_inventory(store)),
        ("E", _dn_analysis(store)),
        ("F", _user_device_map(store)),
        ("G", _routing_group(store)),
        ("H", _voicemail_analysis(store)),
        ("I", _data_quality_group(store)),
        ("J", _gateways_group(store)),
        ("K", _features_group(store)),
        ("L", _button_template_group(store)),
        ("M", _device_layout_group(store)),
        ("N", _softkey_group(store)),
    ]
    # Filter out empty sections
    sections = [(letter, html) for letter, html in sections if html]
    if not sections:
        return '<section id="appendix"></section>'

    return (
        '<section id="appendix">\n'
        + "\n".join(html for _, html in sections)
        + "\n</section>"
    )
```

- [ ] **Step 3: Add _object_inventory() — Section A (new, was in v1)**

This section shows total counts by object type + by-location breakdown. New function:

```python
def _object_inventory(store: MigrationStore) -> str:
    """A. Object Inventory — total counts by type."""
    object_types = [
        "user", "device", "line", "shared_line", "location",
        "hunt_group", "call_queue", "auto_attendant", "call_park",
        "pickup_group", "paging_group", "trunk", "route_group",
        "css", "partition", "translation_pattern", "voicemail_profile",
        "schedule", "gateway", "workspace", "virtual_line",
        "line_key_template", "device_layout", "softkey_config",
    ]
    rows = []
    total = 0
    for ot in object_types:
        count = store.count_by_type(ot)
        if count > 0:
            display = ot.replace("_", " ").title()
            rows.append((display, count))
            total += count

    if not rows:
        return ""

    parts = [
        f'<details id="objects">',
        f'<summary>A. Object Inventory <span class="summary-count">— {total} objects across {len(rows)} types</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Object Type</th><th class="num">Count</th></tr></thead>',
        '<tbody>',
    ]
    for display, count in rows:
        parts.append(f'<tr><td>{html.escape(display)}</td><td class="num">{count}</td></tr>')
    parts.append('</tbody></table>')

    # By-location breakdown
    locations = store.get_objects("location")
    if locations:
        parts.append('<h4>By Location</h4>')
        parts.append('<table>')
        parts.append('<thead><tr><th>Location</th><th class="num">Users</th><th class="num">Devices</th></tr></thead>')
        parts.append('<tbody>')
        all_users = store.get_objects("user")
        all_devices = store.get_objects("device")
        for loc in locations:
            loc_id = loc.get("canonical_id", "")
            loc_name = loc.get("name", "")
            if not loc_name:
                loc_name = strip_canonical_id(loc_id)
            friendly = friendly_site_name(loc_name) if loc_name.startswith("DP-") else loc_name
            u_count = sum(1 for u in all_users if u.get("location_id") == loc_id)
            loc_user_ids = {u.get("canonical_id") for u in all_users if u.get("location_id") == loc_id}
            d_count = sum(1 for d in all_devices if d.get("owner_canonical_id") in loc_user_ids)
            parts.append(f'<tr><td>{html.escape(friendly)}</td><td class="num">{u_count}</td><td class="num">{d_count}</td></tr>')
        parts.append('</tbody></table>')

    parts.append('</div></details>')
    return "\n".join(parts)
```

- [ ] **Step 4: Add _css_partitions() — Section C (extracted from routing)**

Extract CSS/partition topology from `_routing_group()` into its own function:

```python
def _css_partitions(store: MigrationStore) -> str:
    """C. CSS / Partition topology."""
    css_count = store.count_by_type("css")
    pt_count = store.count_by_type("partition")
    if css_count == 0 and pt_count == 0:
        return ""

    parts = [
        f'<details id="css-partitions">',
        f'<summary>C. CSS / Partitions <span class="summary-count">— {css_count} CSSes, {pt_count} partitions</span></summary>',
        '<div class="details-content">',
    ]

    css_objects = store.get_objects("css")
    if css_objects:
        parts.append('<ul class="css-topology">')
        for css in css_objects:
            css_id = css.get("canonical_id", "")
            css_name = strip_canonical_id(css_id)
            parts.append(f'<li>{html.escape(css_name)}')
            css_pt_refs = store.get_cross_refs(
                relationship="css_contains_partition",
                from_id=css_id,
            )
            if css_pt_refs:
                for ref in sorted(css_pt_refs, key=lambda r: r.get("ordinal", 0)):
                    pt_name = strip_canonical_id(ref.get("to_id", ""))
                    parts.append(f'<li class="partition">{html.escape(pt_name)}</li>')
            parts.append('</li>')
        parts.append('</ul>')

    parts.append('</div></details>')
    return "\n".join(parts)
```

- [ ] **Step 5: Add _device_inventory() — Section D (rename from _devices_group, add stacked bar)**

Copy the entire `_devices_group()` function (lines 172-222) and rename to `_device_inventory()`. Change the `<details>` ID and summary, then add stacked bar chart after the model table.

Changes to make in the copy:
1. Rename function to `_device_inventory`
2. Change docstring to `"""D. Device Inventory — by model with stacked bar chart."""`
3. Change `<details id="devices">` to `<details id="device-detail">`
4. Change summary from `Devices` to `D. Device Inventory`
5. After `parts.append('</tbody></table>')` (line 220 equivalent), add:
```python
# Stacked bar chart for device compatibility
segments = [
    {"label": "Native MPP", "value": native, "color": "#2E7D32"},
    {"label": "Convertible", "value": convertible, "color": "#EF6C00"},
    {"label": "Incompatible", "value": incompatible, "color": "#C62828"},
]
bar_html = stacked_bar_chart(segments)
if bar_html:
    parts.append(bar_html)
```

Change the details ID and summary:
```python
f'<details id="device-detail">',
f'<summary>D. Device Inventory <span class="summary-count">— {summary}</span></summary>',
```

- [ ] **Step 6: Add _dn_analysis() and _user_device_map() — Sections E and F**

Extract these from `_people_group()` into separate functions:

`_dn_analysis()` — Section E: DN classification table only.
`_user_device_map()` — Section F: User-device-line mapping table only.

Both use the same data access patterns as `_people_group()` but with their own `<details>` wrappers and letter-prefixed summaries.

```python
def _dn_analysis(store: MigrationStore) -> str:
    """E. DN Analysis — extension classification breakdown."""
    lines = store.get_objects("line")
    if not lines:
        return ""

    classification_counts: dict[str, int] = defaultdict(int)
    for line in lines:
        cls = line.get("classification", "UNKNOWN")
        if hasattr(cls, "value"):
            cls = cls.value
        classification_counts[str(cls)] += 1

    parts = [
        f'<details id="dn-analysis">',
        f'<summary>E. DN Analysis <span class="summary-count">— {len(lines)} extensions</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Classification</th><th class="num">Count</th></tr></thead>',
        '<tbody>',
    ]
    for cls, count in sorted(classification_counts.items(), key=lambda x: -x[1]):
        parts.append(f'<tr><td>{html.escape(cls)}</td><td class="num">{count}</td></tr>')
    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)
```

For `_user_device_map()`, extract the user-device-line table from `_people_group()` lines 76-143:

```python
def _user_device_map(store: MigrationStore) -> str:
    """F. User/Device Map — user-device-line assignments."""
    user_device_refs = store.get_cross_refs(relationship="user_has_device")
    if not user_device_refs:
        return ""

    parts = [
        f'<details id="user-device-map">',
        f'<summary>F. User/Device Map <span class="summary-count">— {len(user_device_refs)} assignments</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>User</th><th>Device</th><th>Model</th><th>Line</th><th>Partition</th></tr></thead>',
        '<tbody>',
    ]

    for ref in user_device_refs:
        user_id = ref.get("from_id", "")
        device_id = ref.get("to_id", "")

        user_obj = store.get_object(user_id)
        device_obj = store.get_object(device_id)

        user_name = ""
        if user_obj:
            first = user_obj.get("first_name", "")
            last = user_obj.get("last_name", "")
            user_name = f"{first} {last}".strip() or strip_canonical_id(user_id)
        else:
            user_name = strip_canonical_id(user_id)

        model = device_obj.get("model", "") if device_obj else ""

        device_line_refs = store.get_cross_refs(
            relationship="device_has_dn", from_id=device_id,
        )

        if device_line_refs:
            for dl_ref in device_line_refs:
                line_id = dl_ref.get("to_id", "")
                line_obj = store.get_object(line_id)
                line_ext = ""
                partition = ""
                if line_obj:
                    line_ext = line_obj.get("extension", "") or line_obj.get("cucm_pattern", "")
                    partition = line_obj.get("route_partition_name", "")
                if not partition:
                    dn_pt_refs = store.get_cross_refs(
                        relationship="dn_in_partition", from_id=line_id,
                    )
                    if dn_pt_refs:
                        partition = strip_canonical_id(dn_pt_refs[0].get("to_id", ""))
                parts.append(
                    f'<tr><td>{html.escape(user_name)}</td>'
                    f'<td>{html.escape(strip_canonical_id(device_id))}</td>'
                    f'<td>{html.escape(model)}</td>'
                    f'<td>{html.escape(line_ext)}</td>'
                    f'<td>{html.escape(partition)}</td></tr>'
                )
        else:
            parts.append(
                f'<tr><td>{html.escape(user_name)}</td>'
                f'<td>{html.escape(strip_canonical_id(device_id))}</td>'
                f'<td>{html.escape(model)}</td>'
                f'<td>—</td><td>—</td></tr>'
            )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)
```

- [ ] **Step 7: Add _voicemail_analysis() — Section H**

```python
def _voicemail_analysis(store: MigrationStore) -> str:
    """H. Voicemail Analysis — voicemail profiles."""
    profiles = store.get_objects("voicemail_profile")
    if not profiles:
        return ""

    parts = [
        f'<details id="voicemail">',
        f'<summary>H. Voicemail Analysis <span class="summary-count">— {len(profiles)} profiles</span></summary>',
        '<div class="details-content">',
        '<table>',
        '<thead><tr><th>Profile</th><th>Description</th></tr></thead>',
        '<tbody>',
    ]
    for p in profiles:
        name = p.get("name", strip_canonical_id(p.get("canonical_id", "")))
        desc = p.get("description", "—")
        parts.append(f'<tr><td>{html.escape(name)}</td><td>{html.escape(str(desc))}</td></tr>')
    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)
```

- [ ] **Step 8: Update existing group functions — add letter prefixes and new IDs**

Update each existing `_*_group()` function's `<details>` ID and `<summary>` text:

| Function | Old ID | New ID | Summary prefix |
|----------|--------|--------|----------------|
| `_decisions_group` | `decisions` | `decision-detail` | `B.` |
| `_routing_group` | `routing` | `routing` | `G.` |
| `_data_quality_group` | `data-quality` | `coverage` | `I.` |
| `_gateways_group` | `gateways` | `gateways` | `J.` |
| `_features_group` | `features` | `call-features` | `K.` |
| `_button_template_group` | `button-templates` | `button-templates` | `L.` |
| `_device_layout_group` | `device-layouts` | `device-layouts` | `M.` |
| `_softkey_group` | `softkey-status` | `softkeys` | `N.` |

For each, update the `<details id="...">` and `<summary>` prefix.

Also update `_routing_group()` to REMOVE the CSS/partition topology section (now in its own Section C). Only keep trunks and route group tables.

- [ ] **Step 9: Remove _people_group() (replaced by E + F)**

Delete `_people_group()` — its logic is now split between `_dn_analysis()` (Section E) and `_user_device_map()` (Section F).

- [ ] **Step 10: Run tests**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/test_appendix.py -x --tb=short 2>&1 | head -40`

Note failures for Task 5.

- [ ] **Step 11: Commit appendix.py**

```bash
git add src/wxcli/migration/report/appendix.py
git commit -m "refactor(report): restructure appendix to lettered A-N sections

Splits people group into E (DN Analysis) and F (User/Device Map).
Extracts CSS/Partitions into Section C. Adds A (Object Inventory) and
H (Voicemail). All 14 sections have letter prefixes and unique IDs."
```

---

### Task 5: Update Tests

**Files:**
- Modify: `tests/migration/report/test_assembler.py`
- Modify: `tests/migration/report/test_executive.py`
- Modify: `tests/migration/report/test_appendix.py`

Update test assertions to match v4 structure. Keep test names stable where possible.

- [ ] **Step 1: Update test_assembler.py**

Changes needed:

a) `test_dark_interstitial_present` — **Delete or rename**. The dark interstitial no longer exists. Replace with:
```python
def test_no_dark_interstitial(populated_store, tmp_path):
    """v4 removed the dark interstitial between exec and appendix."""
    result = assemble_report(populated_store, "Acme", "SE", "cluster1", "15.0")
    assert "tech-interstitial" not in result
```

b) `test_sidebar_nav_exec_items` — Update expected nav labels:
```python
def test_sidebar_nav_exec_items(populated_store, tmp_path):
    result = assemble_report(populated_store, "Acme", "SE")
    assert "Migration Complexity" in result
    assert "What You Have" in result
    assert "What Needs Attention" in result
    assert "Next Steps" in result
```

c) `test_sidebar_nav_tech_items` — Update expected hrefs:
```python
def test_sidebar_nav_tech_items(populated_store, tmp_path):
    result = assemble_report(populated_store, "Acme", "SE")
    assert 'href="#objects"' in result
    assert 'href="#decision-detail"' in result
    assert 'href="#routing"' in result
    assert 'href="#gateways"' in result
```

d) `test_summary_bar_present` — **Delete or rename**. Summary bar removed. Replace with:
```python
def test_no_summary_bar(populated_store, tmp_path):
    """v4 removed the fixed summary bar — stats are inline."""
    result = assemble_report(populated_store, "Acme", "SE")
    assert "summary-bar" not in result
```

e) `test_max_width_wrapper` — Update to check for v4 layout classes:
```python
def test_layout_structure(populated_store, tmp_path):
    result = assemble_report(populated_store, "Acme", "SE")
    assert "main-layout" in result
    assert "step-list" in result or "step-item" in result
    assert "detail-panel" in result
```

f) `test_contains_executive_and_appendix` — Update appendix section ID checks:
```python
def test_contains_executive_and_appendix(populated_store, tmp_path):
    result = assemble_report(populated_store, "Acme", "SE")
    assert 'id="score"' in result
    assert 'id="objects"' in result or 'id="decision-detail"' in result
```

- [ ] **Step 2: Update test_executive.py**

Changes needed:

a) `test_page1_verdict` — Remove section-kicker assertion:
```python
def test_page1_verdict(populated_store):
    result = generate_executive_summary(populated_store, "Acme", "SE", "cluster1", "15.0")
    assert "Migration Complexity Assessment" in result
    assert "<svg" in result  # gauge chart
```

b) `test_page1_has_conclusion_heading` — **Delete or replace**. Conclusion headings removed:
```python
def test_page1_has_direct_heading(populated_store):
    result = generate_executive_summary(populated_store, "Acme", "SE")
    assert "Migration Complexity Assessment" in result
    assert "section-kicker" not in result
```

c) `test_page3_effort_bands` — Update section ID check:
```python
def test_page3_effort_bands(populated_store):
    result = generate_executive_summary(populated_store, "Acme", "SE")
    assert 'id="decisions"' in result  # was id="scope"
    assert "Migrates Automatically" in result
```

d) `test_page2_phone_compatibility` — Add donut chart check:
```python
def test_page2_phone_compatibility(populated_store):
    result = generate_executive_summary(populated_store, "Acme", "SE")
    assert "Native MPP" in result
    assert "Convertible" in result
    # Donut chart SVG present
    assert "circle" in result.lower() or "donut" in result.lower() or "<svg" in result
```

e) `test_analog_gateway_callout` — Update "Technical Appendix" text check (exact wording may differ):
The callout now says "Technical Appendix" — keep as is if that text is still in executive.py.

- [ ] **Step 3: Update test_appendix.py**

Changes needed:

a) `test_has_six_details_elements` — Update count:
```python
def test_has_multiple_details_elements(populated_store):
    result = generate_appendix(populated_store)
    details_count = result.count("<details")
    assert details_count >= 5  # varies by data, but should be many
```

b) `test_section_ids` — Update to new IDs:
```python
def test_section_ids(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="objects"' in result
    assert 'id="decision-detail"' in result
    assert 'id="device-detail"' in result
    assert 'id="routing"' in result
    assert 'id="gateways"' in result
    assert 'id="coverage"' in result
```

c) `test_people_group` — Replace with separate DN and User/Device tests:
```python
def test_dn_analysis_section(populated_store):
    result = generate_appendix(populated_store)
    assert "DN Analysis" in result or 'id="dn-analysis"' in result

def test_user_device_map_section(populated_store):
    result = generate_appendix(populated_store)
    assert "User/Device Map" in result or 'id="user-device-map"' in result
```

d) `test_devices_group` — Update to check new section ID:
```python
def test_devices_section(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="device-detail"' in result
    assert "CP-8845" in result
```

e) `test_features_group` — Update ID:
```python
def test_features_section(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="call-features"' in result or "Call Features" in result
```

f) `test_routing_group_includes_css` — CSS topology is now in Section C:
```python
def test_routing_section(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="routing"' in result

def test_css_partitions_section(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="css-partitions"' in result
```

g) `test_gateways_section_id` — Update:
```python
def test_gateways_section_id(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="gateways"' in result
```

h) `test_decisions_grouped_by_type` — Update ID:
```python
def test_decisions_grouped_by_type(populated_store):
    result = generate_appendix(populated_store)
    assert 'id="decision-detail"' in result
```

- [ ] **Step 4: Run full test suite**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/ -x --tb=short 2>&1 | head -60`

All tests should pass.

- [ ] **Step 5: Commit test updates**

```bash
git add tests/migration/report/test_assembler.py tests/migration/report/test_executive.py tests/migration/report/test_appendix.py
git commit -m "test(report): update assertions for v4 layout and section structure

Updates assembler tests for removed summary-bar/interstitial, new nav
labels and IDs. Updates executive tests for direct headings (no kickers).
Updates appendix tests for lettered A-N section IDs."
```

---

### Task 6: Update CLAUDE.md + Generate Report + Visual Verification

**Files:**
- Modify: `src/wxcli/migration/report/CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md — reflect v4 design system**

Key sections to update:
- Module docstring at top: "v4 (Editorial + v3 Data)" instead of "v3 (Authority Minimal)"
- `styles.py` description: "v4 editorial CSS — Lora/Source Sans, teal, warm neutrals, 320px sidebar"
- `assembler.py` description: "320px sidebar nav (numbered 1-4 exec, lettered A-N tech), no summary bar, IntersectionObserver"
- `appendix.py` description: "14 lettered sections A-N"
- CSS Design System section: Replace Authority Minimal description with editorial system (Lora, Source Sans 3, teal primary, warm neutrals)
- Remove references to `.content-card`, `.tech-interstitial`, `.nav-dot`, `.section-kicker`
- Add references to `.step-item`, `.step-icon`, `.score-layout`, `.effort-band`, `.verdict`, `.cta-box`
- Known Polish Items: Remove items that were fixed in v4, add any new ones discovered

- [ ] **Step 2: Generate the report**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m wxcli cucm report --brand "Acme Corporation" --prepared-by "Adam Hobgood" 2>&1 | tail -5`

Expected: Report generates without errors, output file at `assessment-report.html`.

- [ ] **Step 3: Visual spot-check**

Open the generated HTML in a browser and verify:
- Warm cream background (not gray)
- Lora serif headings (not IBM Plex Sans)
- Teal primary color (not blue)
- 320px white sidebar with numbered/lettered nav items
- No summary bar at top
- Score gauge with tier-based color (green/amber/red, not blue)
- Donut chart in executive summary
- Stacked bar in device appendix
- Effort bands in Section 3
- Lettered A-N appendix sections
- IntersectionObserver highlights active nav on scroll

- [ ] **Step 4: Run full test suite one more time**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/ --tb=short 2>&1 | tail -10`

Expected: All tests pass.

- [ ] **Step 5: Commit CLAUDE.md**

```bash
git add src/wxcli/migration/report/CLAUDE.md
git commit -m "docs(report): update CLAUDE.md for v4 editorial design system"
```

---
