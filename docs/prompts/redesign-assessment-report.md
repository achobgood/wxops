# Redesign: CUCM Migration Assessment Report — Visual Overhaul

## Context

We built a CUCM migration assessment tool that generates HTML/PDF reports for Sales Engineers to hand to customers. The tool works — it reads from a SQLite migration database, computes a complexity score, generates charts, explains decisions in plain English, and produces a self-contained HTML file with optional PDF.

**The problem:** The current output looks like a developer's debug page, not a consulting deliverable. It's a flat, long page with basic tables. We need it to look like something a CIO would trust.

**The reference:** `/Users/ahobgood/Documents/wxcc-agent-builder/docs/plans/mcp-requirements-visual.html` — this is the visual quality bar. Study it before doing anything. It has:
- Sidebar navigation with sticky positioning and click-to-navigate
- Rich typography (Lora serif headings, Source Sans body, IBM Plex Mono for data)
- Warm color palette with CSS custom properties
- Summary stat bar across the top
- Colored section indicators with category badges
- Stat cards in grid layouts
- Callout boxes for important notes
- Responsive design (collapses sidebar on mobile)

## What to Redesign

The report generator lives at `src/wxcli/migration/report/`. Read the module's `CLAUDE.md` for architecture and data access patterns before starting.

**Files to modify:**
- `src/wxcli/migration/report/styles.py` — Complete CSS rewrite. Replace the current basic styles with an editorial design system inspired by the reference HTML. Adapt for a consulting report context (not a requirements doc).
- `src/wxcli/migration/report/executive.py` — Restructure the HTML output to use the new design system. Same data, better presentation.
- `src/wxcli/migration/report/appendix.py` — Same treatment for the technical appendix.
- `src/wxcli/migration/report/assembler.py` — Update the HTML shell (header, nav, footer structure).
- `src/wxcli/migration/report/charts.py` — SVG charts may need style adjustments to fit the new palette.

**Files NOT to modify:**
- `src/wxcli/migration/report/score.py` — Algorithm is correct, don't touch it
- `src/wxcli/migration/report/ingest.py` — Ingestion is correct
- `src/wxcli/migration/report/explainer.py` — Decision templates are correct

## Design Requirements

### Layout: Sidebar + Detail (Screen) / Linear (Print)

**Screen view:**
- Left sidebar (fixed ~320px) with navigation sections matching the report structure
- Right panel scrolls with full content
- Top summary bar showing key stats at a glance (score, users, devices, sites)
- Click sidebar items to scroll to sections

**Print/PDF view:**
- Linear layout (sidebar becomes a table of contents on page 1)
- Clean page breaks between major sections
- `@media print` rules hide interactive elements, expand all content
- Page headers/footers with customer name and page numbers

### Typography (match the reference)

```css
--font-display: 'Lora', Georgia, serif;           /* headings, score label */
--font-body: 'Source Sans 3', system-ui, sans-serif; /* body text, tables */
--font-mono: 'IBM Plex Mono', monospace;           /* numbers, data, score */
```

### Color Palette (Webex-adjacent warm tones)

Adapt the reference palette but shift the accent colors toward Webex teal:
```css
--primary: #00897B;        /* Webex-adjacent teal (headers, nav active state) */
--primary-light: #E0F2F1;
--success: #2E7D32;        /* green — Direct, Native MPP, Straightforward */
--success-light: #E8F5E9;
--warning: #EF6C00;        /* amber — Approximation, Convertible, Moderate */
--warning-light: #FFF3E0;
--critical: #C62828;       /* red — Incompatible, Complex */
--critical-light: #FFEBEE;
```
Keep the warm neutrals from the reference (`--warm-50` through `--warm-900`, `--slate-*`).

### Executive Summary Sections

**Page 1 — Score Hero:**
- Migration Complexity Score as a large centered element (the gauge chart)
- Score number in `--font-mono`, large (3rem+)
- Label below in `--font-display` italic
- Below the score: a summary stat bar (like the reference's `.summary-bar`) with: Users | Devices | Sites | Decisions | Direct Mapping %
- One-paragraph summary in `--font-display` italic (`.lead-sentence` style from reference)

**Page 2 — What You Have:**
- Object inventory as stat cards in a grid (`.stat-grid` / `.stat-card` from reference), NOT a bar chart
- Phone compatibility as the donut chart (keep the SVG, but style the surrounding container)
- Site breakdown as a clean table with the reference's `.deg-table` styling (not zebra stripes — use subtle bottom borders)

**Page 3 — What Needs Attention:**
- Decision summary as three colored stat cards (green/amber/red) instead of the traffic light SVG boxes
- Top decisions as callout boxes (`.callout` style from reference), each with a colored left border matching severity
- Feature mapping as a `.deg-table` with status badges (`.badge` from reference): "Direct" green, "Approximation" amber, "Decision needed" red

**Page 4 — Next Steps:**
- Prerequisites as a checklist with the reference's list styling
- Call to action in a callout box

### Technical Appendix Sections

- Each section gets a colored section indicator (like the reference's `.step-number`)
- Tables use `.deg-table` styling throughout
- `<details>/<summary>` for collapsibility in screen view; all expanded in print
- Decision detail sections use callout boxes for context
- CSS/Partition topology rendered as indented lists with colored dots, not raw text

### Navigation Sidebar

In screen view:
```html
<nav class="step-list">
  <div class="step-list-section">
    <div class="step-list-section-title">Executive Summary</div>
    <a class="step-item" href="#score">Migration Score</a>
    <a class="step-item" href="#inventory">What You Have</a>
    <a class="step-item" href="#decisions">What Needs Attention</a>
    <a class="step-item" href="#next-steps">Next Steps</a>
  </div>
  <div class="step-list-section">
    <div class="step-list-section-title">Technical Appendix</div>
    <a class="step-item" href="#objects">Object Inventory</a>
    <a class="step-item" href="#decision-detail">Decision Detail</a>
    <!-- etc -->
  </div>
</nav>
```

Use minimal JavaScript for scroll-tracking the active nav item (just an `IntersectionObserver` — 15 lines). This is the ONE exception to "no JavaScript" — navigation UX in the screen version is worth it. Print hides the nav entirely.

### Charts

The existing SVG charts (gauge, donut) stay but need palette updates:
- Match the new `--success`, `--warning`, `--critical` colors
- Font inside SVGs should match `--font-mono` for numbers, `--font-body` for labels
- The gauge chart should be the centerpiece of page 1 — make it larger and more prominent

Replace the traffic light boxes SVG with styled HTML stat cards (they'll look better and match the design system).

Replace the horizontal bar chart SVG with stat cards in a grid — they communicate the same data but match the reference's visual language.

## Constraints

- The report must still be a single self-contained HTML file
- Google Fonts loaded via `<link>` tags (not `@import`) in the `<head>` for faster rendering
- Must print cleanly to PDF via headless Chrome (`wxcli cucm report --pdf`)
- All data access patterns are documented in `src/wxcli/migration/report/CLAUDE.md` — read it
- 66 existing tests must still pass after the redesign (`pytest tests/migration/report/ -v`)
- The `executive_only` flag must still work (skip appendix)

## Process

1. **Read the reference HTML first** (`/Users/ahobgood/Documents/wxcc-agent-builder/docs/plans/mcp-requirements-visual.html`) — study the full CSS and HTML structure
2. **Read the report module CLAUDE.md** (`src/wxcli/migration/report/CLAUDE.md`) — understand the data layer
3. **Read the current report files** — understand what data each section uses
4. Use the **editorial-design** and **frontend-design** skills for the visual implementation
5. Start with `styles.py` (the CSS), then `assembler.py` (the HTML shell), then `executive.py`, then `appendix.py`
6. After each file, run `pytest tests/migration/report/ -v` to check for regressions
7. Generate a report from the test bed: `wxcli cucm report --project cucm-testbed-2026-03-24 --brand "Acme Corporation" --prepared-by "Adam Hobgood" --pdf`
8. Open the HTML in a browser and verify the visual quality matches the reference standard
9. Open the PDF and verify print layout is clean

## Success Criteria

When a CIO opens this PDF, they should feel:
1. **Relief** — "Oh, this is way simpler than I thought"
2. **Confidence** — "These people clearly understand our environment"

The report should look like it came from McKinsey or Deloitte, not from a developer's terminal.
