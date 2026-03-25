# CUCM Migration Assessment Tool — Design Spec

**Date:** 2026-03-24
**Author:** Adam Hobgood
**Status:** Draft

---

## Problem Statement

Customers on Cisco Unified Communications Manager (CUCM) are migrating to Microsoft Teams instead of Webex Calling — not because Teams is technically superior, but because the CUCM-to-Webex migration path feels opaque and risky. "Too hard" really means "too unknown."

The migration assessment tool eliminates this uncertainty by analyzing a customer's CUCM environment and producing a professional report that shows exactly what their migration involves: what maps cleanly, what needs decisions, and how complex it actually is. The report is designed to create relief ("this is simpler than I thought") backed by confidence ("these people clearly understand our environment").

## Strategic Context

### Competitive Landscape

Yarnlab Wrangler (now Kurmi Flow) is the primary commercial migration tool. It's production-proven at scale (1.5M+ users migrated) and covers the full lifecycle: assessment, execution, and testing. However:

- Wrangler is a commercial SaaS with subscription pricing
- Its assessment tool (pre_yarn) is also commercial — there is no free way to scope a migration
- It's a black box: customers and partners can't inspect the analysis logic
- It requires a web UI; it can't be automated or embedded in partner workflows

### Our Position

We've already built the hard part. The CUCM migration pipeline at `src/wxcli/migration/` contains 18,138 lines of production code across 42 modules with 1,294 passing tests. It extracts from CUCM via AXL, normalizes to canonical models, runs 12 independent analyzers that detect 16 types of migration decisions, and builds a dependency-ordered execution plan.

What we haven't built is the **front door** — the piece that turns this analytical engine into a tool Sales Engineers can use in customer meetings.

### Target Outcome

A partner SE runs the assessment against a customer's CUCM environment. Five minutes later, they hand the customer a polished PDF report showing:
- A Migration Complexity Score of 34 (green — "Straightforward Migration")
- 94% of phones are native MPP, 6% need firmware conversion, 0 incompatible
- 847 users across 12 sites, all features map directly except 3 that need a decision
- Estimated migration: 4 batches, 2 weeks

The customer's reaction: "Oh. That's... not bad at all."

The conversation shifts from "should we go to Teams?" to "when do we start?"

## Architecture

### Three Components

```
┌─────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│    Collector     │───>│   Analysis Engine     │───>│   Report Generator   │
│   (on-prem)     │    │  (existing pipeline)  │    │       (new)          │
│                 │    │                      │    │                      │
│  cucm-collect   │    │  wxcli cucm          │    │  wxcli cucm report   │
│  → .json.gz     │    │  discover/normalize/  │    │  → .html / .pdf     │
│                 │    │  analyze              │    │                      │
└─────────────────┘    └──────────────────────┘    └──────────────────────┘
       ↑                        ↑                          ↑
  Customer runs on         SE runs (or              Reads from SQLite
  their own network        automated)               store post-analyze
```

**Collector** — standalone, minimal, read-only. Customer can run it themselves and inspect the output before sending it. No intelligence, no analysis.

**Analysis Engine** — the existing migration pipeline, unchanged. A new `--from-file` flag on `wxcli cucm discover` ingests collector output instead of connecting to CUCM directly.

**Report Generator** — new module that reads the SQLite store and produces a self-contained HTML file. PDF via headless Chrome or manual print.

### Separation of Concerns

The collector knows nothing about Webex. The analysis engine knows nothing about reports. The report generator knows nothing about CUCM. Each component can be developed, tested, and distributed independently.

## Component 1: Collector (`cucm-collect`)

### Purpose

Pull raw CUCM configuration data via AXL and write it to a portable file. Nothing more.

### Interface

```bash
cucm-collect \
  --host 10.1.1.50 \
  --username axl_readonly \
  --password *** \
  --output acme-2026-03-24.json.gz
```

Optional flags:
- `--cucm-version 15.0` — override version detection if AXL serviceability query fails
- `--skip-types "voicemail,schedule"` — skip specific object types (e.g., if AXL permissions are restricted)
- `--timeout 300` — per-query timeout in seconds (default 120)

### Output Format

```json
{
  "collector_version": "1.0.0",
  "cucm_version": "15.0.1.13901",
  "cluster_name": "cucm-pub.acme.com",
  "collected_at": "2026-03-24T14:30:00Z",
  "collection_stats": {
    "total_objects": 2847,
    "duration_seconds": 142,
    "errors": ["listEndUser: AXL blocked, used SQL fallback"],
    "skipped_types": []
  },
  "objects": {
    "endUser": [{ ...raw AXL dict... }, ...],
    "phone": [...],
    "css": [...],
    "routePartition": [...],
    "routePattern": [...],
    "huntPilot": [...],
    "huntList": [...],
    "lineGroup": [...],
    "devicePool": [...],
    "sipTrunk": [...],
    "gateway": [...],
    "transPattern": [...],
    "callPark": [...],
    "callPickupGroup": [...],
    "line": [...],
    "ctiRoutePoint": [...]
  }
}
```

### Design Constraints

- **Read-only AXL operations only.** List + get queries. The collector modifies nothing. Customers can audit the 300-line script and verify this.
- **Minimal dependencies:** `zeep`, `requests`, Python stdlib. No wxcli, no SQLite, no Pydantic. Must install cleanly on any Python 3.9+ machine.
- **Gzipped output.** Large clusters produce 50-100MB uncompressed JSON. Gzip typically achieves 8-12x compression (5-10MB output).
- **Error resilience.** If an AXL query fails (permissions, version mismatch, timeout), log the error, record it in `collection_stats.errors`, and continue. Partial extracts are useful — the report will note coverage gaps.
- **No credentials in output.** The output file contains configuration data only. Passwords, SNMP communities, and other secrets present in AXL responses are stripped before writing.

### Distribution

- **PyPI:** `pip install cucm-collect`
- **Single-file alternative:** `cucm_collect.py` — a self-contained script with vendored zeep for environments where pip isn't available
- **GitHub:** Own repo (`cucm-collect`), MIT license, clear README with sample output

### Reuse of Existing Code

The existing extractors at `src/wxcli/migration/cucm/extractors/` contain the AXL query logic. The collector repackages the extraction queries (list + get patterns) without the normalization, cross-referencing, or SQLite storage. It's a simplified fork of the extraction layer.

## Component 2: Analysis Engine (Existing Pipeline)

### Changes Required

One new ingestion path. Everything else is unchanged.

**`wxcli cucm discover --from-file <path>`**

When `--from-file` is provided:
1. Read and decompress the JSON file
2. Validate the collector version and format
3. Feed raw AXL dicts into the existing extractor output path (the same data structure that extractors produce after their list+get queries)
4. Store to SQLite as if extracted live
5. Record the source in the journal: `"source": "file", "path": "acme-2026-03-24.json.gz"`

From this point forward, `normalize`, `analyze`, and all downstream stages work identically. They don't know or care whether data came from a live CUCM connection or a file.

**No other changes to the analysis engine.** The 18,138 lines of existing code, 12 analyzers, 10 mappers, and 16 decision types all work as-is.

### New Command: `wxcli cucm report`

Added to the existing `cucm` CLI group. Reads from the SQLite store (must be post-analyze) and generates the report.

```bash
wxcli cucm report \
  --brand "Acme Corporation" \
  --prepared-by "Adam Hobgood, Partner SE" \
  --output acme-assessment.html \
  --pdf                              # optional: also generate PDF
  --executive-only                   # optional: skip technical appendix
```

## Component 3: Report Generator

### Design Philosophy

The report is a **consulting deliverable**, not a dashboard. It's designed to be printed, emailed, and circulated internally by the customer. Every element earns its space by either reducing fear or building confidence.

**Visual identity:** Clean, professional, authoritative. Sans-serif typography (Inter or system fonts). Teal/blue accent palette adjacent to the Webex visual family — familiar but not branded. Dense information presented with strong hierarchy. No decorative elements. The data is the design.

**Tone:** Direct, plain-English, jargon-free in the executive summary. Technical precision in the appendix. Never alarming — frame problems as decisions, not blockers.

### Output Format

A single self-contained HTML file with:
- Embedded CSS (no external stylesheets)
- Inline SVG charts (no JavaScript dependencies)
- Print-optimized `@media print` styles with page break control
- `@page` rules for PDF margins, headers, footers

The HTML renders identically in any modern browser. PDF generation via:
- `--pdf` flag: uses headless Chromium (`chrome --headless --print-to-pdf`)
- Manual: open HTML in browser, File → Print → Save as PDF

No JavaScript required for viewing. The report is a static document.

### Migration Complexity Score

The headline metric. A single number (0-100) that answers "how hard is this?" Lower is simpler.

#### Algorithm

Seven weighted factors, each scored 0-100 independently, then combined:

| Factor | Weight | Measures | Scoring Logic |
|---|---|---|---|
| CSS Complexity | 25% | How tangled is the dial plan? | Unique CSS count, avg partitions per CSS, presence of blocking patterns, CSS-to-permission decomposition conflicts |
| Feature Parity | 20% | How well do features translate? | % of features with direct Webex equivalent (100% = 0 score) vs approximation vs no equivalent |
| Device Compatibility | 15% | Can the phones move? | % native MPP (0 score) vs convertible (partial) vs incompatible (full) |
| Decision Density | 15% | How many human choices needed? | Decisions per 100 canonical objects. 0 decisions = 0 score. Scale is logarithmic — diminishing penalty as count rises |
| Scale Factor | 10% | Raw size of environment | Log-scaled user count. 50 users ≈ 2, 500 users ≈ 5, 5000 users ≈ 8. Size alone doesn't make it hard. |
| Shared Line Complexity | 10% | Multi-appearance lines | % of lines shared across devices, complexity of ownership patterns |
| Routing Complexity | 5% | Trunking and translation | Number of trunks, route groups, translation patterns, multi-path routing |

#### Calibration Target

The algorithm is deliberately calibrated so that **typical enterprise CUCM environments score 25-45** (green to low-amber). This is honest — most CUCM configs DO map to Webex Calling without heroics. A score above 55 means genuinely complex CSS topology, extensive shared lines, or significant feature gaps.

- **0-30 (Green): "Straightforward"** — direct mappings dominate, few decisions
- **31-55 (Amber): "Moderate"** — some decisions and approximations, manageable with planning
- **56-100 (Red): "Complex"** — significant CSS decomposition, many approximations, careful planning required

#### Data Sources

All inputs come from data already in the SQLite store after the analyze stage. Access via the `MigrationStore` Python API (not raw SQL) to stay decoupled from schema details:
- Object counts: `store.count_by_type(object_type)` per type, or direct SQL `GROUP BY object_type` for the full breakdown
- Decision counts by type: `store.get_all_decisions()` — filter by `type` and `chosen_option is None`
- Device compatibility: `compatibility_tier` field in each device object's `data` JSON (set by device mapper and cross-reference enrichment, values: `native_mpp`, `convertible`, `incompatible`)
- CSS metrics: cross-refs with `relationship` values `css_contains_partition`, `partition_has_pattern`, `dn_in_partition`
- Feature parity: decisions with `type = 'FEATURE_APPROXIMATION'`

No new analysis is needed. The score is a view over existing data.

### Executive Summary (2-4 pages)

#### Page 1 — The Headline

**Header:** Customer logo/name, date, "CUCM Migration Assessment", prepared by [partner name]

**Migration Complexity Score:** Large circular gauge, centered. Number inside, color-coded, with plain-English label beneath ("Straightforward Migration"). This is the first thing anyone sees.

**One-paragraph summary:**
> "Your CUCM environment at [cluster name] (version [X]) contains [N] users across [Y] sites with [Z] devices and [W] call features. [P]% of your configuration maps directly to Webex Calling with no changes required. [D] items need a decision during migration planning. Estimated migration: [B] batches over [T] weeks."

**Environment snapshot** (small table):
| | |
|---|---|
| CUCM Version | 15.0.1 |
| Cluster | cucm-pub.acme.com |
| Total Objects | 2,847 |
| Sites | 12 |
| Assessment Date | 2026-03-24 |

#### Page 2 — What You Have

**Object inventory** — horizontal bar chart. One bar per resource type (Users, Devices, Lines, Hunt Groups, Auto Attendants, Call Queues, Trunks, etc.). Clean, sortable by count. Color-coded by category (people = blue, features = teal, routing = gray).

**Phone compatibility** — donut chart, three segments:
- Green: Native MPP (direct migration)
- Amber: Firmware convertible (needs flash, then migrates)
- Red: Incompatible (needs replacement)

Adjacent table lists the specific models in each tier with counts. Incompatible models show recommended Webex-compatible replacements.

**Site breakdown** — table with one row per site:
| Site | Users | Devices | Features | Complexity |
|---|---|---|---|---|
| Dallas HQ | 340 | 312 | 8 | Straightforward |
| Austin Branch | 85 | 79 | 3 | Straightforward |
| London Office | 210 | 195 | 5 | Moderate |

Per-site complexity is a mini-score using the same algorithm, scoped to that site's objects.

#### Page 3 — What Needs Attention

**Decision summary** — traffic-light counts:
- 🟢 **[N] Auto-resolved** — handled automatically, no action needed
- 🟡 **[N] Decisions needed** — require input during planning, not blockers
- 🔴 **[N] Critical** — must be resolved before migration can proceed

**Top decisions explained in plain English.** Not "CSS_ROUTING_MISMATCH" — instead:

> **Dallas office international dialing restriction**
> Your Dallas CSS restricts international calls via a blocking partition. Webex Calling handles this through per-user outgoing call permissions instead. You'll choose which users keep the restriction during migration planning. *This is a configuration choice, not a limitation.*

Each decision explanation follows the pattern: what we found → how Webex handles it differently → what you'll choose → why it's manageable.

**Feature mapping table:**

| CUCM Feature | Count | Webex Equivalent | Status |
|---|---|---|---|
| Hunt Group | 4 | Hunt Group | Direct |
| Auto Attendant | 2 | Auto Attendant | Direct |
| Call Park | 3 | Call Park | Direct |
| Extension Mobility | 12 | Hoteling | Approximation |
| Shared Lines (2-party) | 8 | Shared Line | Direct |
| Shared Lines (3+ party) | 2 | Virtual Line | Decision needed |

#### Page 4 — Next Steps (conditional, only if needed for larger environments)

**Migration phases** — Gantt-style timeline showing site-by-site batches:
```
Week 1: [Dallas HQ ████████████]
Week 2: [Austin ████] [London ████████]
Week 3: [Remaining sites ████████████████]
```

**Prerequisites checklist:**
- [ ] Webex Calling Professional licenses (N required)
- [ ] Phone numbers ported to Webex (N numbers across Y sites)
- [ ] [D] migration decisions resolved
- [ ] Firmware conversion scheduled for [N] phones

**Call to action:** "Contact [prepared-by name] to begin migration planning."

### Technical Appendix (variable length)

Scales with environment size. Each section is generated only if relevant data exists.

#### Sections

1. **Full Object Inventory**
   - By type: table with canonical_id, name, site, status
   - By site: grouped tables with all objects at each site
   - Totals row per section

2. **Decision Detail**
   - Every decision with full context: analyzer that produced it, available options with trade-offs, severity, affected objects
   - Grouped by decision type
   - Includes auto-resolved decisions with the rule that resolved them

3. **CSS/Partition Analysis**
   - CSS topology diagram (text-based): CSS → partitions → patterns
   - Which CSSes decompose cleanly into Webex routing + permissions
   - Which CSSes produce mismatches and why
   - Intersection-vs-union analysis results

4. **Device Inventory**
   - Full phone model list with firmware versions and compatibility tier
   - Firmware conversion procedures for convertible models
   - Replacement recommendations for incompatible models with price-tier equivalents

5. **Directory Number Analysis**
   - E.164 normalization results by site
   - Classification breakdown: extension / national / E.164 / ambiguous
   - Conflicts detected (duplicate extensions across sites)
   - Site prefix rules applied

6. **User-Device-Line Map**
   - Cross-reference chains: user → device → line → CSS → partition
   - Shared line ownership analysis
   - Extension mobility associations

7. **Routing Topology**
   - Trunks, route groups, route lists, dial plans
   - Translation pattern inventory
   - PSTN connectivity summary

8. **Voicemail Analysis**
   - Voicemail profile mapping (Unity Connection → Webex voicemail)
   - Incompatible profiles with reasons
   - Pilot number routing

9. **Data Coverage**
   - What the collector captured vs. what failed
   - AXL permission gaps
   - Objects that couldn't be fully extracted (with impact assessment)

## Open Source Strategy

### What's Public

| Package | Repo | License | Contents |
|---|---|---|---|
| `cucm-collect` | `cucm-collect` | MIT | Standalone collector script (zeep + stdlib only, no wxcli dependency) |
| `cucm-assess` | `cucm-assess` | MIT | Assessment pipeline + report generator. Embeds the migration analysis modules (models, store, normalizers, cross-reference, mappers, analyzers, e164, cucm_pattern) as vendored code — NOT a wxcli dependency. Excludes execution-layer code (planner, preflight, batch, runtime, skills). |

### What Stays Private

| Component | Reason |
|---|---|
| Migration execution layer | Operational advantage (planning, preflight, execution, rollback) |
| wxcli CLI (100 command groups) | Broader product, not assessment-specific |
| Domain skills (provision-calling, configure-features, etc.) | Execution IP |
| wxc-calling-builder agent | Builder workflow IP |

### Distribution

- **PyPI:** Both packages installable via pip
- **GitHub:** Public repos with clear READMEs
- **Sample report:** A redacted example report in the README. The sample report IS the marketing — it shows what the tool produces before anyone installs it.
- **No account required.** No telemetry. No phoning home. Download and run.

### The README Sells the Tool

The `cucm-assess` README opens with a redacted sample report screenshot (the executive summary page), followed by:

```
$ cucm-assess --from-file customer-extract.json.gz --brand "Acme Corp"
✓ Loaded 2,847 objects from CUCM 15.0.1
✓ Normalized to 22 canonical types
✓ 12 analyzers complete — 3 decisions found
✓ Migration Complexity Score: 34 (Straightforward)
✓ Report written to acme-assessment.html (+ acme-assessment.pdf)
```

Four commands. Two minutes. A professional PDF the customer can hand to their CIO.

## CLI Workflow

### Full Assessment (Direct CUCM Access)

```bash
# Install
pip install cucm-assess

# Run assessment
cucm-assess \
  --host 10.1.1.50 \
  --username axl_readonly \
  --password *** \
  --brand "Acme Corporation" \
  --prepared-by "Adam Hobgood" \
  --output acme-assessment
# Produces: acme-assessment.html, acme-assessment.pdf
```

### Assessment from Collector File

```bash
# Customer runs collector on their network:
pip install cucm-collect
cucm-collect --host 10.1.1.50 --user axl --pass *** -o acme-extract.json.gz

# Customer sends you acme-extract.json.gz

# You run assessment:
cucm-assess \
  --from-file acme-extract.json.gz \
  --brand "Acme Corporation" \
  --prepared-by "Adam Hobgood" \
  --output acme-assessment
```

### Power User (via wxcli)

For users who already have wxcli installed and want step-by-step control:

```bash
wxcli cucm init acme
wxcli cucm discover --from-file acme-extract.json.gz
wxcli cucm normalize
wxcli cucm analyze
wxcli cucm report \
  --brand "Acme Corporation" \
  --prepared-by "Adam Hobgood" \
  --pdf
```

### `cucm-assess` Wrapper

`cucm-assess` is a self-contained package that embeds the analysis modules (models, store, normalizers, analyzers, mappers, report generator) from the wxcli migration pipeline as vendored code. It does NOT depend on wxcli at runtime. It runs `discover` → `normalize` → `analyze` → `report` in sequence so the common case is a single command.

When `--host` is provided, `cucm-assess` connects to CUCM directly (it includes the extraction logic from `cucm-collect`). When `--from-file` is provided, it ingests a collector file instead.

Power users who already have wxcli installed can use `wxcli cucm` commands directly for step-by-step control and inspection of intermediate state.

## Report Visual Design

### Typography
- **Headings:** Inter SemiBold (or system sans-serif fallback)
- **Body:** Inter Regular, 10pt for print
- **Data tables:** Inter Regular, 9pt, monospace numbers for alignment
- **Page numbers:** Bottom-right, small

### Color Palette
- **Primary:** #00BCB4 (Webex teal) — headings, chart accents, score gauge
- **Success:** #2E7D32 (green) — "direct mapping", "compatible", score 0-30
- **Warning:** #F57C00 (amber) — "approximation", "convertible", score 31-55
- **Critical:** #C62828 (red) — "incompatible", "no equivalent", score 56-100
- **Neutral:** #37474F (dark gray) — body text
- **Background:** #FFFFFF (white) — clean, printable
- **Table alternating:** #F5F5F5 (light gray)

### Charts (Inline SVG)
- **Complexity Score:** Circular gauge (arc, not full circle). Score number centered inside, color-coded. Label beneath.
- **Object Inventory:** Horizontal bar chart. Sorted by count descending. Category-colored.
- **Phone Compatibility:** Donut chart. Three segments (green/amber/red) with percentage labels.
- **Decision Summary:** Three colored boxes with count inside (traffic-light pattern).

All charts are inline SVG — no JavaScript, no external rendering. They print cleanly and scale to any resolution.

### Print Optimization
- `@page` rules: letter size, 0.75in margins
- Page breaks: forced before each major section, avoided inside tables and charts
- Header/footer: customer name (left), page number (right), light gray rule
- No background colors that waste toner (except chart fills)
- Links rendered as text (URL visible) since they're not clickable in print

## Testing Strategy

### Report Generator Tests
- Unit tests for each section generator (given SQLite data → expected HTML fragment)
- Unit tests for the complexity score algorithm (known inputs → expected scores)
- Snapshot tests: full report generation from fixture data, compared to known-good HTML
- Visual regression: render HTML in headless Chrome, screenshot, compare to baseline

### Collector Tests
- Unit tests for AXL query construction
- Integration tests against CUCM test bed (10.201.123.107)
- Error handling: partial extraction when queries fail
- Credential stripping: verify no passwords in output

### End-to-End Tests
- Collector → file → discover --from-file → normalize → analyze → report
- Verify report contains expected sections for given input data
- Verify PDF generation succeeds (if Chrome available)

## Success Criteria

1. **Time to report:** Under 5 minutes from collector file to PDF for a 1,000-user environment
2. **Report quality:** A partner SE would confidently hand this to a customer's CIO
3. **Complexity score accuracy:** Typical enterprise CUCM environments score 25-45 (green to low-amber)
4. **Collector simplicity:** Customer IT staff can run it with zero training (single command, clear output)
5. **Zero dependencies for viewing:** HTML opens in any browser, PDF is a PDF. No apps, no accounts, no plugins.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Complexity score feels arbitrary | Customers don't trust the headline number | Document the algorithm transparently. Show factor breakdown in the report. Let anyone verify by reading the code. |
| Report design looks amateur | Undermines confidence ("these people know our environment") | Invest in the HTML/CSS template. Get feedback from SEs before shipping. The sample report in the README must look professional. |
| Collector can't access all AXL data | Incomplete assessment, gaps in report | Graceful degradation: report clearly marks what couldn't be assessed and why. Partial data is still valuable. |
| Large environments (10K+ users) produce unwieldy appendix | Technical appendix is 100+ pages | Appendix uses `<details>/<summary>` HTML elements (no JavaScript required) for collapsible sections. PDF renders all sections expanded with a table of contents. Executive summary stays fixed at 2-4 pages regardless. |
| Score calibration is wrong | Environments that should feel "easy" score high, or vice versa | Calibrate against real CUCM test bed data first. Adjust weights. Include a "Score Methodology" section in the appendix for transparency. |

## Future: SaaS Platform (Approach C)

Documented separately in `docs/plans/cucm-assess-saas-future.md`. The assessment tool is designed with this evolution in mind — the analysis pipeline is already stateless and the report generator takes structured data as input. A web frontend would replace the CLI workflow without changing the engine.
