# Assessment Report v3 — Visual Design Spec ("Authority Minimal")

**Date:** 2026-03-25
**Author:** Adam Hobgood + Claude
**Status:** Draft
**Predecessor:** `docs/superpowers/specs/2026-03-25-assessment-report-v2-design.md` (content structure)
**Mockups:** `.superpowers/brainstorm/38786-1774470618/content/` (01 comparison, 02 design system, 03 verdict page)

---

## Problem Statement

The v2 spec solved the content problem — the 4-page executive narrative + 6-group technical reference structure is correct. But the visual design system (editorial: Lora/Source Sans 3, warm cream palette, teal accent) is wrong for the deliverable type. This report is a pre-sales consulting assessment, not a magazine article. It needs to look like something produced by McKinsey or Deloitte, not Medium.

The editorial design system creates three specific problems:
1. **Wrong authority signal.** Serif headlines + warm earthy palette reads as "editorial content" not "technical consulting assessment." The audience (CIO, IT Director, telecom engineer) expects authoritative precision, not literary warmth.
2. **Teal accent everywhere.** The Webex teal (#00897B) serves as both brand accent and heading color, diluting its emphasis function. When everything is teal, nothing stands out.
3. **Flat white background.** No visual depth — the report feels like a web page, not a printed deliverable handed over in a meeting.

## Design Philosophy: Authority Minimal

"What if Linear designed a Deloitte report."

Principles from $100k consulting report research (McKinsey, BCG, Bain, Deloitte patterns):
- **Restraint = authority.** Two fonts, one accent color, 80% white. Every element earns its place.
- **Conclusion headings.** Section titles state the takeaway, not the topic. Not "Device Readiness" but "7 of 11 phones need firmware conversion."
- **Progressive density.** Executive summary is spacious (CIO scans it in 5 seconds). Technical reference is dense (engineer reads it at their desk). Whitespace decreases as you go deeper.
- **One accent, rest gray.** In charts, the focal data series gets the accent color; everything else is gray. No rainbow categorization.
- **Floating page.** White content card on subtle gray background with layered shadow — the "printed page on desk" effect that signals physical deliverable quality.

## Scope & Relationship to v2

This spec covers ONLY the visual design system: palette, typography, layout, chart language, component styles, and print styles. It **supersedes** the v2 spec's Typography and Layout sections (lines 252-258) and the Global Rules > Contrast section (lines 218-227). Everything else in v2 remains authoritative.

Specifically, this spec does NOT change:
- Page structure (4 exec pages + 6 tech reference groups) — v2 spec, sections "Design: Executive Summary" and "Design: Technical Reference"
- Content generation logic (verdict, key findings, effort bands, heading text) — v2 spec
- Score algorithm and factor weights — v2 spec, section "Design: Score Algorithm"
- Helper functions (strip_canonical_id, friendly_site_name) — v2 spec, section "Design: Global Rules"
- Chart data logic (stacked_bar_chart segments, gauge score arc) — v2 spec, section "Design: Charts"
- Data extraction or store API — unchanged

**If v2 and v3 conflict on a visual treatment, v3 wins.**

## Design System

### Color Palette

```css
:root {
    /* -- Structure --------------------------------------------------------- */
    --navy-900: #0f1729;        /* Sidebar bg, tech interstitial */
    --navy-800: #1e293b;        /* Sidebar hover states */

    /* -- Text -------------------------------------------------------------- */
    --text-primary: #111827;    /* Headings, KPI numbers, emphasis */
    --text-body:    #374151;    /* Body text, table cells */
    --text-muted:   #6b7280;   /* Secondary text, labels, captions */
    --text-faint:   #9ca3af;   /* Disabled, footer, timestamps */

    /* -- Accent ------------------------------------------------------------ */
    --accent:       #2563eb;    /* Primary accent — links, active nav, focal chart data */
    --accent-tint:  #eff6ff;    /* Accent background — verdict callout, info callout */

    /* -- Semantic (status only, never decorative) -------------------------- */
    --success:       #059669;   /* Auto-resolved, direct-map, positive findings */
    --success-tint:  #ecfdf5;
    --warning:       #d97706;   /* Needs planning, approximation, attention items */
    --warning-tint:  #fffbeb;
    --critical:      #dc2626;   /* Blocking, incompatible, manual work required */
    --critical-tint: #fef2f2;

    /* -- Chart ------------------------------------------------------------- */
    --chart-focal:   #2563eb;   /* Highest-scoring factor, primary data series */
    --chart-gray:    #94a3b8;   /* All non-focal data series */
    --chart-bg:      #f3f4f6;   /* Bar background track */

    /* -- Surfaces ---------------------------------------------------------- */
    --surface:       #ffffff;   /* Content card, table background, stat cards */
    --page-bg:       #f4f5f7;   /* Page background behind content card */
    --border:        #e5e7eb;   /* Table rows, card borders, dividers */
    --border-strong: #d1d5db;   /* Table headers, summary bar border */
}
```

**Usage rules:**
- **80% of the page is white.** Color is functional (status, emphasis, data), never decorative.
- **No gradients anywhere.** Flat solid fills only.
- **Accent blue for emphasis only.** Links, active nav state, focal chart data, verdict callout border. Never on headings.
- **Semantic colors for status only.** Green = success/auto. Amber = planning/attention. Red = blocking/manual. Never used for decoration or branding.
- **Body text is #374151, headings are #111827.** Never lighter. The v1/v2 issue of gray-on-warm is eliminated — text is always dark on white.

### Typography

```css
:root {
    --font-body: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', 'Menlo', 'Consolas', monospace;
}
```

Google Fonts import: `IBM+Plex+Sans:wght@300;400;500;600;700` and `IBM+Plex+Mono:wght@400;500;600`.

**No serif font.** This is a consulting report, not editorial. IBM Plex Sans reads as "enterprise but modern" — exactly where Webex Calling sits.

**Type scale (rem-based, 1rem = 16px):**

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| `--text-3xl` | 1.625rem (26px) | 600 | Page 1 verdict heading only |
| `--text-2xl` | 1.375rem (22px) | 600 | Section headings (h2) |
| `--text-xl` | 1.125rem (18px) | 600 | Subsection headings (h3) |
| `--text-lg` | 1rem (16px) | 400 | Lead paragraphs, verdict callout body |
| `--text-base` | 0.9375rem (15px) | 400 | Body text |
| `--text-sm` | 0.8125rem (13px) | 400 | Table cells, appendix body text, finding text |
| `--text-xs` | 0.6875rem (11px) | 500-600 | Section kickers, table headers, nav labels. Always uppercase + letter-spacing: 0.08em+ |
| `--text-mono` | 0.875rem (14px) | 500 | KPI numbers, score values, device IDs |

**Heading rules:**
- All headings use `font-weight: 600` (semibold), not 700 (bold). More refined.
- All headings use `letter-spacing: -0.01em`. Tighter tracking = authority.
- `line-height: 1.25-1.3` for headings, `1.6` for body text.
- **Conclusion-style headings.** Every h2 states the takeaway:
  - Not "Assessment Verdict" → "Migration is feasible with planning — calling restrictions and device readiness drive moderate complexity"
  - Not "Your Environment" → "10 users across 2 sites with 11 devices and 4 shared lines"
  - Not "Migration Scope" → "67 items migrate automatically — 0 require manual work"
  - Not "Next Steps" → "Ready to plan — all prerequisites identified"

**Section kicker pattern:**
Above every conclusion heading, a small uppercase label identifies the section:
```html
<div class="section-kicker">The Verdict</div>
<h2>Migration is feasible with planning — calling restrictions...</h2>
```
The kicker is `--text-xs`, uppercase, `letter-spacing: 0.1em`, `color: var(--text-muted)`.

### Spacing

8px baseline grid, unchanged from v2:
```css
:root {
    --spacing-xs:  4px;
    --spacing-sm:  8px;
    --spacing-md:  16px;
    --spacing-lg:  24px;
    --spacing-xl:  32px;
    --spacing-xxl: 48px;
}
```

**Progressive density rule:**
- Executive sections: `--spacing-xxl` (48px) between sections, `--spacing-lg` (24px) between components.
- Technical reference: `--spacing-lg` (24px) between sections, `--spacing-md` (16px) between components.
- This is what makes the executive feel "airy" and the appendix feel "dense."

### Layout

**Screen layout:** Sidebar (260px) + summary bar (fixed top) + content card (floating on gray bg).

```
┌──────────┬──────────────────────────────────────────┐
│          │  Score 43 | Users 10 | Devices 11 | ...  │ ← Summary bar (fixed)
│ SIDEBAR  ├──────────────────────────────────────────┤
│ 260px    │     ┌─────────────────────────┐          │
│ navy-900 │     │                         │          │ ← Gray page-bg (#f4f5f7)
│          │     │    Content Card          │          │
│ nav      │     │    max-width: 760px      │          │ ← White card with shadow
│ items    │     │    padding: 2.5rem 3rem  │          │
│          │     │                         │          │
│          │     └─────────────────────────┘          │
└──────────┴──────────────────────────────────────────┘
```

**Content card:** `max-width: 760px`, `margin: 1.5rem auto`, `border-radius: 10px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 32px rgba(0,0,0,0.06)`.

**Summary bar:** Fixed top, spans full width right of sidebar. Horizontal layout with `gap: 2.5rem`. Each stat is inline: `<value> <label>` on one line, not stacked. Mono font for values, regular for labels.

**Sidebar:**
- Header: kicker "Migration Assessment" (xs, uppercase) + brand name (1.0625rem, 600) + meta "Prepared by X · Date" (xs, faint)
- Nav: Two groups separated by divider. Executive group with blue dots, technical reference with gray dots.
- Active state: `background: rgba(255,255,255,0.08)`, `border-left: 2px solid var(--accent)`.
- No numbered circles. Dots only (6px, `border-radius: 50%`). Numbers added visual clutter without adding value.

**Print layout:** Sidebar and summary bar hidden. Content card becomes full-width, no shadow, no rounded corners. Print header appears (brand, title, date).

### Components

#### Verdict Callout
```css
.verdict-callout {
    border-left: 3px solid var(--accent);
    background: var(--accent-tint);
    padding: 1rem 1.25rem;
    border-radius: 0 6px 6px 0;
    font-size: var(--text-lg);     /* 1rem / 16px */
    line-height: 1.65;
    color: var(--text-body);
}
.verdict-callout strong {
    color: var(--text-primary);
    font-weight: 600;
}
```

#### Stat Cards
```css
.stat-card {
    text-align: center;
    padding: 1rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
}
.stat-number {
    font-family: var(--font-mono);
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.stat-label {
    font-size: var(--text-xs);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}
```

#### Tables
- No vertical borders. Horizontal borders only, subtle (`var(--border)`).
- Header: `font-size: var(--text-xs)`, `font-weight: 600`, `text-transform: uppercase`, `letter-spacing: 0.05em`, `color: var(--text-muted)`, `border-bottom: 2px solid var(--border-strong)`.
- Cells: `font-size: var(--text-sm)`, `color: var(--text-body)`.
- Numeric columns: right-aligned, `font-family: var(--font-mono)`, `font-variant-numeric: tabular-nums`.
- No zebra striping. Hover: `background: var(--page-bg)` (very subtle).
- Last row: no bottom border.

#### Badges
```css
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
/* Status badges — dark text on tint bg */
.badge-direct   { background: var(--success-tint); color: #065f46; }
.badge-approx   { background: var(--warning-tint); color: #92400e; }
.badge-decision { background: var(--critical-tint); color: #991b1b; }

/* Severity badges — white text on solid bg */
.badge-critical { background: var(--critical); color: #fff; }
.badge-high     { background: #E65100;         color: #fff; }
.badge-medium   { background: var(--warning);   color: #fff; }
.badge-low      { background: var(--success);   color: #fff; }
.badge-info     { background: var(--chart-gray); color: #fff; }
```

#### Effort Bands
```css
.effort-band {
    border-left: 3px solid;
    padding: 0.75rem 1rem;
    border-radius: 0 6px 6px 0;
    margin-bottom: 0.5rem;
    font-size: var(--text-sm);
}
.effort-band.auto     { border-color: var(--success); background: var(--success-tint); }
.effort-band.planning { border-color: var(--warning); background: var(--warning-tint); }
.effort-band.manual   { border-color: var(--critical); background: var(--critical-tint); }
```

#### Key Findings
```css
.finding {
    display: flex;
    gap: 0.625rem;
    align-items: flex-start;
    padding: 0.5rem 0;
}
.finding-icon {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6875rem;
    font-weight: 700;
    flex-shrink: 0;
}
.finding-icon.alert { background: var(--warning-tint); color: #92400e; }
.finding-icon.check { background: var(--success-tint); color: #065f46; }
```

#### Callout Variants
All use left-border + tint background pattern:
```css
.callout         { border-left: 3px solid var(--border-strong); background: var(--page-bg); }
.callout.info    { border-left-color: var(--accent);   background: var(--accent-tint); }
.callout.success { border-left-color: var(--success);  background: var(--success-tint); }
.callout.warning { border-left-color: var(--warning);  background: var(--warning-tint); }
.callout.critical{ border-left-color: var(--critical); background: var(--critical-tint); }
```

#### CTA Box (Next Steps)
```css
.cta-box {
    background: var(--accent-tint);
    border: 2px solid var(--accent);
    border-radius: 8px;
    padding: var(--spacing-lg);
    text-align: center;
}
.cta-box h3 {
    color: var(--accent);
}
```

### Chart Language

**Universal rules:**
- One accent color (`--chart-focal: #2563eb`) for the most important data series. Everything else in `--chart-gray: #94a3b8`.
- Direct-label all data points — no separate legends.
- Sort bars by value descending (highest first), not alphabetically.
- Chart titles state the insight, not the metric name.
- Source attribution always present at bottom: small text, `var(--text-faint)`.
- All charts are static SVG — no interactivity, no animation.

**Score gauge:**
- Background arc: `stroke: #e5e7eb`
- Score arc: `stroke: var(--chart-focal)` (#2563eb)
- Score number: `fill: var(--text-primary)` (#111827) — NOT the accent color. The number is data.
- Label: `fill: var(--text-muted)`, uppercase, letter-spacing 0.1em

**Factor bars:**
- Highest-scoring factor: `background: var(--chart-focal)` (blue)
- All other factors: `background: var(--chart-gray)` (gray)
- Bar height: 8px, border-radius 4px
- Track: `background: var(--chart-bg)` (#f3f4f6)

**Stacked horizontal bar (device compatibility):**
- Segments: `var(--success)` for native, `var(--warning)` for convertible, `var(--critical)` for incompatible
- Omit 0-count segments
- Legend below: inline swatches (8x8px squares) with count + percentage

**Resolution bar (decision status):**
- Same stacked bar pattern: green for resolved, amber for pending, red for unresolved
- Height: 24px, border-radius 4px

### Tech Interstitial

The dark bar separating executive from technical reference:
```css
.tech-interstitial {
    background: var(--navy-900);
    color: rgba(255,255,255,0.85);
    text-align: center;
    padding: var(--spacing-lg) var(--spacing-md);
    font-size: var(--text-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}
```

On screen: full-width within the content card. On print: `print-color-adjust: exact`.

### Print Styles

```css
@page {
    size: letter;
    margin: 0.75in 1in;   /* Generous — consulting standard */
}

@media print {
    html { font-size: 10pt; }   /* pt for print only */
    body { color: #000; background: #fff; }

    .sidebar, .summary-bar { display: none !important; }

    .print-header {
        display: block;
        text-align: center;
        margin-bottom: var(--spacing-lg);
    }

    .main { margin-left: 0; padding-top: 0; }

    .content-card {
        max-width: none;
        box-shadow: none;
        border-radius: 0;
        padding: 0;
        background: transparent;
    }

    /* Page breaks */
    section { page-break-before: always; }
    section:first-of-type { page-break-before: avoid; }
    h2, h3 { page-break-after: avoid; }
    table, figure, .chart-container { page-break-inside: avoid; }

    /* Details: force open */
    details { border: none; }
    details > summary { display: none; }
    details > .details-content { display: block !important; }

    /* Preserve color on key elements */
    .badge, .effort-band, .callout, .tech-interstitial {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    /* Footer */
    .report-footer {
        font-size: 8pt;
        color: #999;
    }
}
```

## File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `styles.py` | **Rewrite** | Replace entire CSS with Authority Minimal design system. All tokens, all components. |
| `assembler.py` | **Modify** | Update Google Fonts import (IBM Plex Sans/Mono instead of Lora/Source Sans 3). Update sidebar HTML to new structure (dots, kicker, meta). Update summary bar to inline layout. Wrap content in `.content-card` div. Set `body` class for `--page-bg`. |
| `executive.py` | **Modify** | Update heading generation to use section kicker + conclusion heading pattern. Update score gauge SVG colors (#2563eb arc, #111827 number, #e5e7eb track). Update bar chart colors (highest=focal, rest=gray). Sort factors by score descending. |
| `charts.py` | **Modify** | Update gauge SVG colors and font-family. Update stacked bar chart colors. Update factor bar rendering (focal vs gray logic). |
| `appendix.py` | **Minor** | Badge class names unchanged (`.badge-direct`, etc.) but colors update via CSS. No structural changes. |
| `explainer.py` | **No change** | Text content generation is unaffected by visual redesign. |
| `score.py` | **No change** | Score algorithm is unaffected. |

**Key: No new files.** This is a CSS rewrite in `styles.py` plus minor HTML adjustments in `assembler.py`, `executive.py`, and `charts.py`.

## What This Spec Does NOT Cover

- **Content structure changes** (page order, section grouping, effort band logic) — see v2 spec
- **New Python functions** (generate_verdict, generate_key_findings, etc.) — see v2 spec
- **Helper utilities** (strip_canonical_id, friendly_site_name) — see v2 spec
- **Database or store API changes** — none needed
- **Test changes** — CSS-only changes don't affect test assertions on content structure

## Validation Criteria

After implementation, the report should pass this checklist:

- [ ] No teal (#00897B) anywhere in the rendered HTML — replaced by blue (#2563eb) or semantic colors
- [ ] No Lora, Source Sans, or Inter fonts — only IBM Plex Sans and IBM Plex Mono
- [ ] No pt units in screen CSS (pt allowed only inside `@media print`)
- [ ] Content card floats on gray (#f4f5f7) background with layered shadow
- [ ] Every h2 on executive pages is a conclusion statement, preceded by a section kicker
- [ ] Score gauge number is #111827 (dark), not accent-colored
- [ ] Factor bars sorted by score descending, highest in blue, rest in gray
- [ ] Summary bar uses inline layout (value + label on one line), not stacked cards
- [ ] Sidebar has dot indicators (not numbered circles), blue for exec, gray for tech
- [ ] All body text is #374151 or darker — no gray-on-warm contrast issues
- [ ] Print: sidebar hidden, content full-width, details forced open, page breaks correct
- [ ] Existing test suite still passes (content assertions unaffected by CSS changes)
