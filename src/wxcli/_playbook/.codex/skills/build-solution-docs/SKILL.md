---
name: build-solution-docs
description: |
  Generate solution documentation from a plan/design document in docs/plans/:
  an HTML page with Mermaid.js architecture and sequence diagrams (dark Cisco
  theme) and a matching 10-slide PPTX deck. Works for any plan document.
  Triggers on: "create solution docs", "build presentation", "make a deck for this plan".
  Use for: polished solution documentation (HTML + PPTX) from an existing design document.
  NOT for: activity-level .drawio flow diagrams (build-spec-diagram), Obsidian/MARP slides, Gamma decks.
allowed-tools: Read, Bash, Write, Grep, Glob
argument-hint: [path-to-plan-document]
---

# Build Solution Docs Workflow

## Step 1: Load references

1. Read this skill's `reference.md` for the Cisco theme CSS, Mermaid config, PPTX specs, and section templates
2. Use the CSS and layout specs from this skill's `reference.md` for the dark theme layout — they contain the complete theme definition. If your workspace has a local HTML style reference under `docs/plans/`, you may read it as an additional visual guide.
3. Use the PPTX specs from this skill's `reference.md` for slide layout — they contain the complete slide definitions. If your workspace has a local PPTX style reference under `docs/plans/` (inspect with python-pptx), you may read it as an additional visual guide.
4. Read the user's plan document (the argument passed to this skill, or ask the user which plan to use)

**Checkpoint — do NOT proceed until you can answer these:**
- What are the CSS custom properties for the dark theme? (from `reference.md`)
- What are the 10 PPTX slide types in order? (from `reference.md`)
- What sections does the plan document contain? (from the plan you just read)

## Step 2: Extract content sections from the plan

Map the plan document's sections to deliverable sections. For each, extract or synthesize:

| Deliverable Section | Source from Plan |
|---|---|
| **Title** | Plan title / H1 heading |
| **Subtitle** | First sentence or use-case summary |
| **Tagline** | 3 key capabilities or technologies, dot-separated |
| **The Problem** | Use case description — what's broken or needed |
| **The Solution** | How it's solved — the core approach (1-2 sentences + key components) |
| **Architecture diagram** | Main topology/flow from the Architecture section — convert to Mermaid `graph TB` with subgraphs |
| **Primary path sequence** | Happy path — convert to Mermaid `sequenceDiagram` with actors, participants, activations, notes |
| **Secondary path sequence** | Alternate path (error/fallback/unverified) — same Mermaid sequence format |
| **Technical details** | Auth, domains, gotchas — extract 4 summary cards |
| **API reference** | Endpoints, methods, parse expressions — extract into comparison table or code block |
| **Auth & scopes** | Authentication requirements — extract into colored left-bar cards |
| **Gotchas** | Platform quirks, edge cases — extract into 2-column grid cards |
| **Next steps** | Implementation steps — extract into numbered circle list |

### Flow Designer Design Doc Mapping

If the plan uses the `flow-designer-design-doc.md` template (identified by having sections numbered 1-14 with Activities table, Connections table, etc.), use this mapping:

| Deliverable Section | FD Template Source |
|---|---|
| **The Problem** | §1 Purpose — first sentence (what problem, who calls in) |
| **The Solution** | §1 Purpose — remaining sentences (how the flow solves it) |
| **Architecture diagram** | §12 Flow Diagram — convert ASCII art to Mermaid `graph TB` |
| **Primary path sequence** | §5 Connections — trace the happy path from NewPhoneContact to Disconnect |
| **Secondary path sequence** | §5 Connections — trace the error/fallback path through OnGlobalError |
| **Technical details** | §8 External Integrations — summarize into 4 cards |
| **API reference** | §8 External Integrations table — convert to comparison table |
| **Auth & scopes** | §8 HTTP Headers table — extract auth patterns |
| **Gotchas** | §11 Error Handling Summary — convert to 2-column grid |
| **Next steps** | §14 Build Checklist — convert to numbered list |

Not all plans will have every section. Skip sections that don't apply; don't fabricate content.

## Step 3: Generate the HTML page

Create `{plan-name}-diagrams.html` in the same directory as the source plan.

**Naming convention:** Strip the date prefix if present. E.g., `2026-04-28-retail-store-inbound-routing-v2.md` → `retail-store-routing-diagrams.html`.

**Structure the HTML exactly as follows:**

1. `<!DOCTYPE html>` with `<meta charset="UTF-8">` and viewport meta
2. Mermaid.js from CDN: `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js`
3. Full inline CSS from `reference.md` (Inter font import, all CSS variables, all component styles, print media query)
4. **Hero section** — title, subtitle, tagline pill
5. **Summary row** — 4 summary cards: The Problem (default blue top), The Solution (green), How It Updates/Verifies (orange), How It Routes (red)
6. **Divider**
7. **Section 1** — Architecture diagram (numbered section-header + section-desc + diagram-card with Mermaid `graph TB`)
8. **Divider**
9. **Section 2** — Primary path sequence diagram (numbered section-header + section-desc + diagram-card with Mermaid `sequenceDiagram`)
10. **Divider**
11. **Section 3** — Secondary path sequence diagram (same format)
12. **Divider**
13. **Section 4** — Technical details (numbered section-header + summary-row with 4 summary-cards)
14. **Divider**
15. **Section 5** — API Reference (numbered section-header + diagram-card with either comparison-table or code-block)
16. **Footer** — plan title, "Solution Architecture", key technologies
17. **Mermaid initialization script** — use the exact config from `reference.md`

**Mermaid diagram rules:**
- Architecture (`graph TB`): Use the flowchart themeVariables from `reference.md`. Use subgraphs for logical groups. Style success nodes green (#1bb34c), failure nodes red (#e84d3d), key nodes Cisco blue (#049FD9).
- Sequence diagrams: Use the sequence themeVariables from `reference.md`. Include `activate`/`deactivate`, `Note` annotations, `rect` highlights for key sections.
- All Mermaid blocks go inside `<pre class="mermaid">` tags within a `diagram-card` div.

## Step 4: Generate the PPTX

Create `{plan-name}-solution.pptx` in the same directory as the source plan.

**Check python-pptx is installed:**
```bash
python3 -c "import pptx" 2>/dev/null || pip3 install python-pptx
```

**Write a Python script and execute it.** The script must create all 10 slides using the exact specs from `reference.md`:

| Slide | Background | Layout Pattern |
|---|---|---|
| 1. Title | Dark (#1A1F25) | 4 text boxes: title (large, Cisco blue), subtitle, tagline, "Solution Architecture & Technical Overview" |
| 2. The Problem | Light (#FFFFFF) | Title + pink problem box (#FEF3F2) + "What they need:" label + blue square bullet cards |
| 3. The Solution | Dark (#1A1F25) | Title + description text + 3-column component cards OR detail box (#0A3D5C) |
| 4. Architecture | Light (#FFFFFF) | Title + subtitle + 3 colored flow boxes (green/blue/orange) with connectors + description cards below |
| 5. Primary Path | Light (#FFFFFF) | Title + subtitle + step cards (progressive color: gray → light blue → Cisco blue → green) with connectors |
| 6. Secondary Path | Light (#FFFFFF) | Title + subtitle + step cards (same progressive pattern) with connectors |
| 7. API Reference | Dark (#1A1F25) | Title + subtitle + table rows (alternating #222830 / #2A3038) with header row in Cisco blue |
| 8. Auth & Scopes | Light (#FFFFFF) | Title + colored left-bar cards (red for warnings, blue for info, orange for caveats) |
| 9. Gotchas | Dark (#1A1F25) | Title + 2-column grid of cards on #222830 background (title + description per card) |
| 10. Next Steps | Dark (#1A1F25) | Title + numbered circle items (Cisco blue circles) + detail box (#0A3D5C) at bottom |

**PPTX specs (from `reference.md`):**
- Slide dimensions: 13.33 × 7.50 inches (Emu(12191695) × Emu(6858000))
- Font: Calibri throughout
- Use `pptx.util.Inches`, `pptx.util.Pt`, `pptx.util.Emu` for positioning
- Use `RGBColor` for all colors
- Rounded rectangles use `MSO_SHAPE.ROUNDED_RECTANGLE` with `adjustments[0] = 0.1`

## Step 5: Open both files for review

After generating both files, tell the user:
1. The file paths for both deliverables
2. Suggest opening the HTML in a browser to verify Mermaid diagrams render correctly
3. Suggest opening the PPTX in PowerPoint/Keynote to verify slide layout

```bash
open {path-to-html}
open {path-to-pptx}
```

---

## CRITICAL REMINDERS

- **Self-contained HTML** — all CSS inline, Mermaid from CDN, no external dependencies
- **Match the theme exactly** — use the CSS variables, colors, and Mermaid themeVariables from `reference.md`
- **Both files go in the same directory** as the source plan document
- **Don't fabricate content** — only use information present in the plan document
- **Mermaid syntax must be valid** — test that diagram definitions parse correctly
- **PPTX via python-pptx only** — no other libraries; check it's installed before running
- **General purpose** — this skill works for ANY plan document, not just WxCC/Cisco plans. The visual theme is Cisco-branded but the content extraction is universal.
