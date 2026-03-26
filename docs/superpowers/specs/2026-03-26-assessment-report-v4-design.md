# Assessment Report v4 — Editorial Shell + v3 Data

**Date:** 2026-03-26
**Status:** Draft
**Supersedes:** v3 visual system (styles.py, assembler.py layout); preserves v3 data generation

## Summary

Merge v1's warm editorial visual design with v3's data improvements. The user prefers v1's Lora/Source Sans typography, teal primary color, warm cream backgrounds, and 320px numbered/lettered sidebar navigation. v3's data additions (score breakdown bars, effort bands, gateway analysis, button templates, device layouts, softkeys, key findings, verdict callout, next steps) are all retained but restyled to fit v1's aesthetic.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Visual system | v1 warm editorial | User preference — "visually better and better navigation" |
| Summary bar | Removed | Stats inline in executive summary (user choice B) |
| Appendix structure | v1 lettered A-N | Extended v1's A-I with new v3 sections as J-N (user choice B) |
| Phone compatibility chart | Both | Donut in executive summary, stacked bar in device appendix (user choice C) |
| Score gauge color | Tier-based (green/amber/red) | v1 behavior; v3's always-blue was a known polish item |
| Factor bars accent | Teal primary (#00897B) | Replaces v3's blue (#2563eb) to match v1 palette |
| Content card wrapper | Removed | v1 had no floating white card — content flows directly in detail panel |
| Section kickers | Removed | v1 used direct h2 topic headings, not conclusion-style headings with kickers |

## Visual System (from v1)

### Typography
- **Display/headings:** Lora (serif), Georgia fallback
- **Body:** Source Sans 3, system-ui fallback
- **Monospace:** IBM Plex Mono, Menlo fallback
- **Base size:** 17px (html)

### Color Palette
```
Warm neutrals:   #fdf8f3 (50) → #2a1c10 (900)
Slate:           #f8f9fa (50) → #181c22 (900)
Primary (teal):  #00897B / light: #E0F2F1
Success (green): #2E7D32 / light: #E8F5E9
Warning (orange):#EF6C00 / light: #FFF3E0
Critical (red):  #C62828 / light: #FFEBEE
```

### Layout
- **Sidebar:** 320px, sticky, white background, right border
- **Content:** Scrolling detail panel, 2.5rem 3rem padding
- **Grid:** `grid-template-columns: 320px 1fr`
- **No summary bar**
- **No content card** — warm-50 body background, content flows in detail panel
- **Page header:** slate-900 background, Lora headings, brand + subtitle + meta

### Navigation
- **Executive Summary:** Numbered 1-4, teal circular icons (.exec)
- **Technical Appendix:** Lettered A-N, slate-500 circular icons (.tech)
- **Active state:** warm-100 background + teal left border + teal text
- **Scroll tracking:** IntersectionObserver highlights active nav item

## Executive Summary (4 sections)

### Section 1: Migration Complexity Assessment (`#score`)
- Score gauge (SVG, tier-colored: green/amber/red arc)
- **NEW from v3:** Score breakdown — 7 factor bars below gauge
  - Sorted by raw_score descending
  - Highest factor: teal bar, rest: slate-400 bars
  - Factor labels left-aligned, values right-aligned
- **NEW from v3:** Verdict callout (explanation paragraph)
  - Styled as `.callout.info` (teal left border, teal-light background)
- **NEW from v3:** Key findings list (3-4 bullet items with check/alert icons)
  - Icons use v1 status colors (success green, warning orange)
- Stat grid below: Customer, Cluster, Version, Date, Objects, Sites, Users, Devices

### Section 2: What You Have (`#inventory`)
- Environment stat grid (Users, Devices, Hunt Groups, etc.)
- Phone compatibility **donut chart** (v1 style)
- **NEW from v3:** Feature mapping table (CUCM Feature → Webex Equivalent → Status badge)
- Site breakdown table (Site, Users, Devices, Decisions)
- **NEW from v3:** Analog gateways warning callout (if gateways present)

### Section 3: What Needs Attention (`#decisions`)
- Decision summary stat grid (Auto-resolved, Decisions Needed, Critical)
- **NEW from v3:** Effort bands (auto/planning/manual)
  - Styled with v1's callout pattern: left border + light background
  - Auto: success green border + success-light bg
  - Planning: warning orange border + warning-light bg
  - Manual: critical red border + critical-light bg
  - Each shows top 5 items + "...and N more"
- **NEW from v3:** Resolution progress bar/stat

### Section 4: Next Steps (`#next-steps`) — NEW section from v3
- Pre-migration checklist table (Licenses, Phone Numbers, Decisions)
- Planning phase items (if unresolved decisions)
- CTA box — styled as callout.info with contact info

## Technical Appendix (A-N, collapsible `<details>`)

All sections use v1's collapsible details styling:
- Border: 1px solid warm-200, radius-md
- Open state: primary border color
- Summary: Lora font, 600 weight, chevron indicator
- Content padded inside

| Letter | ID | Section | Content |
|--------|----|---------|---------|
| A | `#objects` | Object Inventory | Main inventory table (type + count) + by-location table |
| B | `#decision-detail` | Decision Detail | Grouped by type, explanation cards with severity badges, collapsible options |
| C | `#css-partitions` | CSS / Partitions | CSS/Partition topology tree (nested ul with colored dots) |
| D | `#device-detail` | Device Inventory | Device compatibility table (model + count + tier) + stacked bar chart |
| E | `#dn-analysis` | DN Analysis | Extension classification table |
| F | `#user-device-map` | User/Device Map | User-device-line mapping table |
| G | `#routing` | Routing Topology | Trunks table + route groups table |
| H | `#voicemail` | Voicemail Analysis | Voicemail profiles table |
| I | `#coverage` | Data Coverage | Object type population + status checkmarks |
| J | `#gateways` | Gateways & Analog Ports | Gateway table + analog port estimates + MGCP warnings |
| K | `#call-features` | Call Features | Feature type inventory + per-type detail tables |
| L | `#button-templates` | Button Templates | Template table + unmapped button types |
| M | `#device-layouts` | Device Layouts | Metrics table (shared lines, speed dials, BLF, KEM) |
| N | `#softkeys` | Softkey Migration | Template table + PSK mapping + unmapped softkeys |

## Implementation Changes

### styles.py
- Replace v3 "Authority Minimal" CSS with v1's warm editorial CSS
- Add new component styles for v3 features, themed to v1:
  - `.score-layout` — 2-column grid (gauge left, factor bars right)
  - `.score-breakdown` / `.factor-row` / `.factor-bar` / `.factor-fill` — teal accent for top factor, slate-400 for rest
  - `.effort-band` — reuse v1 callout pattern (left border + colored bg)
  - `.key-findings` — list with circular status icons in v1 colors
  - `.verdict` — render as `.callout.info`
  - `.cta-box` — render as `.callout.info` with slightly more padding
- Remove: `.content-card`, `.summary-bar`, `.summary-stat`, `.nav-dot`, `.section-kicker`, `.tech-interstitial`
- Keep all v1 components: stat-grid, stat-card, deg-table, badges, callouts, explanations, details/summary, css-topology, checklist, section-indicator
- Restore Google Fonts to load Lora + Source Sans 3 + IBM Plex Mono
- Legacy CSS variable aliases must still work (charts.py, appendix.py, explainer.py reference them)

### assembler.py
- Remove summary bar generation
- Remove content-card wrapper
- Remove dark tech-interstitial
- Restore 320px sidebar with numbered (1-4) + lettered (A-N) nav items
- Use v1's circular step-icon pattern (.exec teal, .tech slate)
- Restore IntersectionObserver JS for scroll tracking
- Sidebar sections: "Executive Summary" (4 items) + "Technical Appendix" (14 items)
- Print header: v1 pattern (centered, teal border-bottom)

### executive.py
- Section 1: Add score breakdown bars + verdict callout + key findings (new from v3, keep data logic)
- Section 2: Use donut_chart() for phone compatibility instead of stacked_bar_chart()
- Section 2: Keep v3's feature mapping table + gateway warning
- Section 3: Rename from "Migration Scope" to "What Needs Attention", keep effort bands
- Section 4: Keep "Next Steps" from v3
- Remove section-kicker elements — use direct h2 headings like v1
- Remove content-card wrapper divs
- Score gauge: pass tier color (score_result.color) instead of hardcoded blue

### appendix.py
- Restructure from 10 topic groups to 14 lettered sections (A-N)
- Each section gets a letter prefix in its summary element
- Restore v1's original sections (A-I) with their original content
- Add J-N sections using v3's existing group functions (gateways, button templates, device layouts, softkeys)
- Move "Call Features" from position 3 in v3 to position K
- Keep v3's decisions grouping logic but place at position B
- Stacked bar chart in section D (Device Inventory)

### charts.py
- No functional changes needed
- Gauge chart will receive tier colors from executive.py (green/amber/red instead of always-blue)
- Donut chart already exists and will be called from executive.py

## Files Modified

| File | Change Type | Scope |
|------|-------------|-------|
| `src/wxcli/migration/report/styles.py` | Rewrite | Replace v3 CSS with v1 editorial + new v3 component styles |
| `src/wxcli/migration/report/assembler.py` | Major edit | Remove summary bar, restore v1 layout/nav, extend to A-N |
| `src/wxcli/migration/report/executive.py` | Moderate edit | Add donut chart, change headings, remove kickers/card wrappers |
| `src/wxcli/migration/report/appendix.py` | Major edit | Restructure to A-N lettered sections |
| `src/wxcli/migration/report/charts.py` | No change | Already has all needed chart functions |
| `src/wxcli/migration/report/CLAUDE.md` | Update | Reflect v4 design system and section structure |

## Test Impact

Existing tests in `tests/migration/report/` will need updates:
- `test_assembler.py` — Remove summary bar assertions, update sidebar nav assertions (A-N letters)
- `test_executive.py` — Update heading text assertions, add donut chart assertion
- `test_appendix.py` — Update section count assertions (10 → up to 14), check letter prefixes
- `test_charts.py` — No changes needed

## What Does NOT Change

- `score.py` — scoring algorithm unchanged
- `explainer.py` — decision explanations unchanged
- `helpers.py` — text formatting unchanged
- `ingest.py` — collector ingestion unchanged
- All data access patterns — same store API calls
- CLI interface — same `wxcli cucm report` command
