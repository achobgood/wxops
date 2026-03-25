# Assessment Report v2 — Design Spec

**Date:** 2026-03-25
**Author:** Adam Hobgood
**Status:** Draft
**Predecessor:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md` (v1)

---

## Problem Statement

The v1 assessment report has working data extraction, scoring, and HTML generation — but the deliverable doesn't serve its audience. The report is organized around the pipeline's internal data model (decision types, canonical IDs, object categories) instead of what the customer cares about: Can we migrate? What's involved? What are the risks?

Specific failures:
- The complexity score (43/100) has no visible breakdown — customers don't know what drives it
- 67 decisions render as 67 identical callout boxes — unreadable wall of noise
- Internal canonical IDs leak into customer-facing text (`css:Standard-Employee-CSS`, `location:fd9b9990ac1b`)
- The "What Needs Attention" section says nothing needs attention (67 auto-resolved, 0 decisions, 0 critical)
- Next Steps section doesn't exist (nav links to `#next-steps` but no section is rendered)
- No verdict or recommendation — the reader doesn't know what to do after reading
- No visual break between executive summary and technical appendix
- Site breakdown shows 0 devices per site (data bug)
- Text contrast is too low — gray text on warm backgrounds is unreadable

## Strategic Context

Unchanged from v1 spec. The report is a pre-sales deliverable designed to:
1. Eliminate the "too hard / too unknown" objection that drives customers to Teams
2. Create momentum toward a paid migration planning engagement
3. Work as both a live presentation aid (SE walks through it in a meeting) and a standalone leave-behind (customer reads it alone at 9pm)

Target audience ranges from CIO (reads pages 1-4) to telecom engineer (reads the technical reference). The report must serve both without making either feel talked down to or overwhelmed.

## Design Rationale

These decisions were made during a brainstorming session reviewing the v1 report output. They drive every structural choice below.

### Audience & Delivery

- **Primary decision this report drives:** Approve a detailed migration planning engagement (not a direct sale, not a quote request). The report is a pre-sales assessment, not a Statement of Work.
- **Delivery mode:** Both. SE hands a printed/PDF copy to the IT Director in a meeting AND emails it as a standalone leave-behind. Every section must be scannable enough for a 5-minute live walkthrough but complete enough that someone reading it cold at 9pm still gets it.
- **Reader range:** From CIO ("give me the bottom line") to telecom engineer ("show me the CSS partition mappings"). The two-tier structure (executive + technical reference) serves both, but they must be visually distinct so neither audience feels lost in the other's content.

### Why Hybrid (Approach C)

Three approaches were evaluated:
- **A) Narrative Arc:** Strong story for the meeting, but appendix stays a data dump. Doesn't serve the engineer reading alone.
- **B) Dashboard + Drilldown:** Great interactive experience, but prints poorly (collapsing panels don't linearize). Feels like a tool, not a deliverable.
- **C) Hybrid:** A's narrative executive + B's drilldown appendix. Most work, but only approach that serves dual-audience AND dual-delivery.

### Why Effort Bands Replace Severity Grouping

The v1 report grouped decisions by pipeline severity (auto-resolved / decisions needed / critical). This is meaningless to a customer — "67 auto-resolved, 0 decisions, 0 critical" looks like "nothing to do" when in fact 16 of those auto-resolved items should be verified during planning. Effort bands (Automatic / Needs Planning / Manual Work) map to what the customer cares about: what happens on its own, what needs their team's attention, and what costs money.

### Design Persona

This report is designed from the perspective of a migration consulting practice lead — someone who has delivered 50+ assessments and knows what makes a customer say "let's go" vs "let me think about it." The visual design serves the content, not the other way around.

## Approach

**Hybrid: Narrative Executive + Technical Reference**

- Pages 1-4: Story arc answering "should I be worried?" → "what do we have?" → "what does migration involve?" → "what's next?"
- Technical Reference: Collapsed by default, grouped by topic, with summary lines visible when closed. Dark interstitial bar separates it from the executive.
- Print: Executive prints as 4 clean pages. Technical reference expands but stays at summary level.

## Design: Executive Summary (Pages 1-4)

### Page 1 — The Verdict

**Purpose:** Answer "should I be worried?" in 5 seconds.

**Layout (stacked, max-width 720px):**

1. **Verdict callout** — teal left border, generated sentence:
   - Score ≤30: "This migration is **straightforward**. [context]."
   - Score 31-55: "This migration is **feasible with planning**. [context]."
   - Score ≥56: "This migration **requires significant planning**. [context]."
   - Context includes: top 2 contributing factors, unresolved decision count.
   - New function: `generate_verdict(score_result, store) → str` in explainer.py.

2. **Score gauge** — centered, smaller than v1 (160px wide), with "Moderate Complexity" label below.

3. **Score breakdown** — full-width CSS grid (label | bar | weighted/max). 7 factors with customer-friendly names:
   | v1 Name | v2 Name |
   |---------|---------|
   | CSS Complexity | Calling Restrictions |
   | Feature Parity | Feature Compatibility |
   | Device Compatibility | Device Readiness |
   | Decision Density | Outstanding Decisions |
   | Scale | Scale |
   | Shared Line Complexity | Shared Lines |
   | Routing Complexity | Routing |

   Bar color: green (#2E7D32) if weighted_score < 40% of max weight, amber (#F57C00) otherwise.

4. **Key findings** — single-column list, 3-4 items auto-generated from data:
   - `!` (amber) for attention items, `✓` (green) for positive findings
   - One line each, bold count + short phrase: "**7 of 11 phones** need firmware conversion; 4 need replacement"
   - Generated by a new `generate_key_findings(store) → list[dict]` function.
   - Finding templates: device compatibility split, CSS routing decisions, feature mapping summary, decision resolution rate.

**What's NOT on this page:** No stat cards repeating Users/Devices/Sites (those are in the summary bar). No Environment Snapshot. No metadata cards (customer name, cluster IP, assessment date — those are in the header).

### Page 2 — Your Environment

**Purpose:** Show "we understand what you have" — grouped by customer concern, not CUCM object type.

**Layout (max-width 720px):**

Four semantic groups, each with a teal header and teal bottom border:

1. **People** — 3 stat cards in a row:
   - Users (count), Shared Lines (count), Extensions (DN count)

2. **Devices & Infrastructure** — 3 stat cards + device compatibility panel:
   - Total Devices (count), Workspaces (count), Sites (count)
   - Phone Compatibility: **stacked horizontal bar** (not donut chart). Omit 0% categories. Include one-sentence explanation below ("Convertible phones need a firmware flash...").

3. **Call Features** — table:
   - Columns: Feature | Count | Webex Equivalent | Status (badge: Direct/Approximation/Decision)
   - Moved here from v1 Page 3. Features are inventory, not decisions.

4. **Sites** — table:
   - Columns: Site | Users | Devices | Features
   - Site names: strip `DP-` prefix and `-Phones` suffix heuristically. Footnote: "Site names derived from CUCM Device Pools."
   - **Data bug fix:** Site device counts must aggregate from device→device_pool→location cross-refs, not from the broken current logic.

### Page 3 — Migration Scope

**Purpose:** Answer "what does this migration actually involve?" Grouped by effort, not pipeline decision type.

**Layout (max-width 720px):**

Intro sentence, then three effort bands as colored cards:

1. **Migrates Automatically** (green card, #E8F5E9):
   - Count of objects with direct-map resolutions
   - One sentence listing what types: "Users, hunt groups, auto attendants..."

2. **Needs Planning** (amber card, #FFF3E0):
   - Count of items that were auto-resolved but should be verified
   - Summary table: aggregated by customer-visible outcome, not DecisionType
   - Example rows: "7 devices need firmware conversion" | "3 calling restrictions don't map" | "4 CSS routing rules have scope differences"
   - Right column: brief context ("8845, 8851, 7841" / "900, 976, intl blocks")

3. **Requires Manual Work** (red card, #FFEBEE):
   - Count of items that cannot be automated
   - Summary table with specific items and cost signal
   - Example: "1 ATA 191 — incompatible, needs ATA 192 replacement" | "hardware cost"

**Effort band assignment logic** (new function in executive.py):
- **Automatic:** type is ARCHITECTURE_ADVISORY, OR (severity LOW + resolved + chosen_option is "direct map" or "skip" or "upgrade firmware")
- **Needs Planning:** auto-resolved but severity HIGH/MEDIUM, OR type is CSS_ROUTING_MISMATCH, CALLING_PERMISSION_MISMATCH, FEATURE_APPROXIMATION, DEVICE_FIRMWARE_CONVERTIBLE, LOCATION_AMBIGUOUS, SHARED_LINE_COMPLEX, EXTENSION_CONFLICT, DN_AMBIGUOUS, VOICEMAIL_INCOMPATIBLE, WORKSPACE_LICENSE_TIER, WORKSPACE_TYPE_UNCERTAIN, HOTDESK_DN_CONFLICT
- **Manual:** type is DEVICE_INCOMPATIBLE, DUPLICATE_USER, or NUMBER_CONFLICT, OR unresolved decisions, OR MISSING_DATA where missing fields include required address/email fields
- **Default:** any DecisionType not explicitly listed falls to Planning if resolved, Manual if unresolved

See the customer-friendly type name table in the Technical Reference section for the complete mapping of all 17 DecisionType values to effort bands.

4. **Decision Resolution bar** — progress bar showing resolved/total with percentage. For this test data: 67/67 (100%). For a real customer with unresolved decisions, this is the SE's conversation point.

### Page 4 — Next Steps

**Purpose:** Close on the planning engagement. Always present (v1 conditionally hid this for small environments).

**Layout (max-width 720px):**

1. **Intro sentence** — "This assessment identified the scope. The next phase is a detailed migration plan."

2. **Before Migration** (checklist on white card):
   - Static prerequisites, always shown:
     - Webex Control Hub provisioned with Calling licenses
     - Location addresses confirmed for each site (E911)
     - PSTN connectivity established
     - Number porting initiated (if applicable)
     - User email addresses verified in Webex identity
   - Visual: empty checkbox squares (print-friendly, SE can check off with pen)

3. **Planning Phase Should Address** (numbered items on white card):
   - Auto-generated from Page 3 effort bands. Each "Needs Planning" and "Manual Work" item becomes a numbered action item with specific context.
   - Orange filled number circles (white text on #EF6C00)
   - Example: "1. Device firmware conversion plan — 7 phones across 3 models need MPP flash."

4. **CTA box** — white background, teal border, centered text:
   - "Ready to Plan Your Migration?"
   - "Contact your Webex Calling partner to schedule a detailed migration planning session."

5. **Footer note** — italic, links to Technical Reference below.

## Design: Technical Reference (Appendix)

### Structure

**6 topic groups** replace the current 9 data-type sections:

| Group | Contains (merged from v1) | Summary Line Example |
|-------|--------------------------|---------------------|
| People & Identity | Object Inventory (users), DN Analysis, User/Device Map, Shared Lines | "10 users, 4 shared lines, 9 extensions" |
| Devices & Workspaces | Device Inventory, Voicemail, Workspaces | "11 devices (7 convertible, 4 incompatible), 5 workspaces" |
| Call Features | Feature inventory, Operating Modes | "19 features across 4 types, all direct-map" |
| Routing & Dial Plan | CSS/Partitions, Routing Topology, Translation Patterns | "3 trunks, 2 route groups, 6 CSSes, 12 partitions" |
| All Decisions | Decision Detail (aggregated by type) | "67 total, 67 resolved" |
| Data Quality | Data Coverage, Journal | "2 journal entries, no collection errors" |

### Behavior

- **Collapsed by default** on screen. Summary line visible when closed.
- **Dark interstitial bar** (#1a1f25 background, white text "TECHNICAL REFERENCE") separates executive from appendix.
- **Sidebar nav updates:** Executive section (teal icons 1-4), Technical Reference section (gray icons, topic names not letters A-I).
- **Click to expand.** Each group uses `<details>/<summary>` with the summary line as the `<summary>` content.
- **Print:** All groups forced open. Decision detail stays at type-summary level (not individual decisions).

### Decision Aggregation (All Decisions group)

**Replaces 67 individual callout boxes with grouped cards.**

Each DecisionType gets one card:
- **Header:** Type name (customer-friendly) + count + resolution badge
- **Body (when expanded):** explainer.py summary text (once per type, not per decision) + aggregated summary table
- **Individual decisions accessible** via expandable detail within each type card (nested `<details>`)

Customer-friendly type names (all 17 DecisionType enum values):
| DecisionType | Display Name | Default Effort Band |
|-------------|-------------|---------------------|
| MISSING_DATA | Missing Data | Manual (if required fields) / Planning (otherwise) |
| CSS_ROUTING_MISMATCH | CSS Routing Mismatch | Planning |
| CALLING_PERMISSION_MISMATCH | Calling Restrictions | Planning |
| DEVICE_FIRMWARE_CONVERTIBLE | Device Firmware Conversion | Planning |
| DEVICE_INCOMPATIBLE | Incompatible Devices | Manual |
| FEATURE_APPROXIMATION | Feature Approximation | Planning |
| WORKSPACE_LICENSE_TIER | Workspace Licensing | Planning |
| LOCATION_AMBIGUOUS | Location Mapping | Planning |
| SHARED_LINE_COMPLEX | Shared Line Complexity | Planning |
| EXTENSION_CONFLICT | Extension Conflicts | Planning |
| DN_AMBIGUOUS | Directory Number Ambiguity | Planning |
| VOICEMAIL_INCOMPATIBLE | Voicemail Compatibility | Planning |
| DUPLICATE_USER | Duplicate Users | Manual |
| WORKSPACE_TYPE_UNCERTAIN | Workspace Type | Planning |
| HOTDESK_DN_CONFLICT | Hot Desk Conflicts | Planning |
| NUMBER_CONFLICT | Number Conflicts | Manual |
| ARCHITECTURE_ADVISORY | Architecture Advisory | Automatic (informational) |

## Design: Global Rules

### Contrast

- **Body text:** #1a1f25 (near-black) minimum. Never lighter than #353d4a.
- **Secondary text:** #4a5363 minimum. Never lighter than #636e7e.
- **Card backgrounds:** Always #fff with visible border (#bcc3cd or stronger).
- **Page background:** #fdf8f3 (warm-50) — page only, never card backgrounds.
- **Table headers:** #1a1f25 text, not gray.
- **Badge text:** Darker shade of badge color (#1b5e20 on green, #bf360c on amber, #b71c1c on red).

### Canonical ID Stripping

New utility function in a new `src/wxcli/migration/report/helpers.py` module:

`strip_canonical_id(canonical_id: str) → str`:
- `"css:Standard-Employee-CSS"` → `"Standard-Employee-CSS"`
- `"device:SEP001122334455"` → `"SEP001122334455"`
- `"location:fd9b9990ac1b"` → look up human-readable name from store, fall back to hash
- `"dn:1001:Internal-PT"` → `"1001 (Internal-PT)"`
- `"voicemail_profile:Default"` → `"Default"`

Applied in all customer-facing output: executive.py, appendix.py, assembler.py.

### Site Name Heuristic

Also in `helpers.py`:

`friendly_site_name(device_pool_name: str) → str`:
- Strip `DP-` prefix if present
- Strip `-Phones`, `-Softphones`, `-CommonArea` suffixes if present
- Example: `"DP-HQ-Phones"` → `"HQ"`, `"DP-Branch-Phones"` → `"Branch"`
- Fallback: return raw name unchanged

### Typography

Preserved from v1: Lora (display), Source Sans 3 (body), IBM Plex Mono (data). No changes.

### Layout

Preserved from v1: sidebar + detail panel on screen, linear on print. Max-width 720px on detail panel content to prevent over-stretching on wide screens.

## Design: Score Algorithm

**No weight changes.** The 7 factors and their weights (25/20/15/15/10/10/5) are preserved.

**Changes:**
1. Factor `display_name` field added to ScoreResult factors list (customer-friendly names per table above)
2. `generate_verdict()` added to explainer.py — returns a single paragraph string
3. `generate_key_findings()` added — returns a list of `{icon: "!" | "✓", text: str}` dicts

## Design: Charts

**Changes:**
1. **Donut chart replaced by stacked horizontal bar** for device compatibility. New function `stacked_bar_chart(segments) → str` in charts.py. Omits 0-count segments.
2. **Gauge chart** preserved but smaller viewBox (200x155 instead of 240x260).
3. **Horizontal bar chart** preserved (used in appendix if needed).
4. **Traffic light boxes** removed (replaced by effort band cards on Page 3).

## File Changes Summary

| File | Change |
|------|--------|
| `score.py` | Add `display_name` to factor dicts |
| `explainer.py` | Add `generate_verdict()`, `generate_key_findings()`, customer-friendly type name map |
| `charts.py` | Add `stacked_bar_chart()`, shrink gauge viewBox, remove `traffic_light_boxes()` |
| `executive.py` | Complete rewrite: 4 new pages (verdict, environment, scope, next steps) |
| `appendix.py` | Complete rewrite: 6 topic groups, decision aggregation, collapsed by default |
| `assembler.py` | Add dark interstitial, update sidebar nav, max-width 720px on content |
| `styles.py` | Update contrast values, add effort band styles, add stacked bar styles, remove unused classes |
| `helpers.py` | **New file.** `strip_canonical_id()`, `friendly_site_name()` utilities |
| `ingest.py` | No changes |

## Testing

- All 66 existing tests must pass (some will need assertion updates for new HTML structure)
- New tests for: `generate_verdict()`, `generate_key_findings()`, `stacked_bar_chart()`, `strip_canonical_id()`, `friendly_site_name()`, effort band assignment logic
- E2E test: generate report from test bed data, verify no canonical ID prefixes in output HTML

## Migration / Versioning

- Back up current report code before implementation: `git tag report-v1` or copy to a branch
- The v1 design spec remains at `docs/superpowers/specs/2026-03-24-cucm-assess-design.md` for reference
- No database schema changes — report reads the same store API
