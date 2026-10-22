---
name: design-flow
description: |
  Design a WxCC Flow Designer voice flow from scratch. Interviews the user about
  requirements, selects blueprints, composes activities, validates ports, and
  produces a design document in docs/plans/. Covers inbound IVR, callback, queue
  treatment, DNIS routing, skill-based routing, business hours, multilingual
  menus, and post-call survey.
  Use for: starting a new Flow Designer voice flow — STEP 1 of the pipeline
  (design-flow → build-flow-designer). Run first for "I need an IVR" or "design a voice flow".
  NOT for: building from a finished design (build-flow-designer), AI agents (configure-ai-agent,
  design-scripted-agent), Webex Connect flows (build-action and the other Connect skills).
allowed-tools: Read, Grep, Glob, Bash, WebSearch
argument-hint: [interview-summary or requirements text]
---

# Design Flow Workflow

## The Flow Designer pipeline

When building a Flow Designer voice flow, skills must be invoked in the correct sequence. Skipping steps produces incomplete or incorrect output.

### Required Pipeline

```
design-flow → [user review] → build-spec-diagram (optional) → build-flow-designer OR build-flow-programmatic → wxcc-setup
```

1. **`design-flow`** — Translates requirements into a complete design doc (activities, connections, variables, event handlers). Saves to `docs/plans/`. The user must review and approve this before proceeding.
2. **`build-spec-diagram`** (optional) — Generates a .drawio visual diagram from the design doc. Useful for user review but not required for the build.
3. **Build the flow** (one of two paths):
   - **`build-flow-designer`** — Generates step-by-step UI build instructions from the design doc. The user manually creates each activity in the Flow Designer UI. REQUIRES a design doc.
   - **`build-flow-programmatic`** — Generates FlowIR JSON, validates via `wxcli` (the `cc-flow*` and `cc-functions` groups), and creates the flow programmatically. Faster but requires CLI access and a valid API token. REQUIRES a design doc.
4. **WxCC setup** — Control Hub configuration (entry point, queue, team, PSTN, flow assignment). Uses `docs/playbooks/wxcc-setup.md`.

### Hard Rules

- NEVER invoke `build-flow-designer` or `build-flow-programmatic` without a design doc in `docs/plans/`. Both skills require a design doc — without one, they cannot produce correct activity-level output.
- NEVER skip user review of the design doc. The design doc is the contract — if activities or connections are wrong, the build output will be wrong too.
- If the user asks to "build a flow" without prior design work, start with `design-flow`, not a build skill.
- If a design doc already exists in `docs/plans/`, either build skill can consume it directly — no need to re-run `design-flow`.

### Choosing Between Build Paths

- Use **`build-flow-designer`** when the user wants to learn the Flow Designer UI or needs manual control over each activity.
- Use **`build-flow-programmatic`** when the user wants fast automated flow creation via `wxcli` (the `cc-flow*` and `cc-functions` groups).
- If ambiguous, ask: "Do you want step-by-step UI build instructions (manual) or programmatic flow creation via the CLI (automated)?"

## Step 1: Load references + Checkpoint

YOU MUST use the Read tool on each of these files **sequentially (one at a time)** — do NOT read them in parallel. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/reference/flow-blueprints.md` — the 12 flow pattern catalog with Activities and Connections tables
2. Read `docs/reference/flow-designer-essentials.md` — the essential activities (Play Message, Play Music, Set Variable, Queue Contact, Disconnect Contact), Variable Types, Output Variables, Global Events
3. Read `docs/reference/flow-designer-activities/_index.md` — full activity catalog with file names
4. Read `docs/templates/flow-designer-design-doc.md` — the template this skill fills out
5. Read this skill's `reference.md` — Blueprint Selection Guide, Activity Quick Reference, Port Name Canonical Map, Composition Patterns, Common Design Gotchas

**Checkpoint — do NOT proceed until you can answer these from the docs you just loaded:**

- Q1: What are the 12 flow blueprints and when is each used?
- Q2: What are the exit ports for a Menu activity vs a Condition activity vs a Business Hours activity?
- Q3: What sections does the flow-designer-design-doc.md template require?
- Q4: What is the maximum number of JSON variables per flow and their size limit?

If you cannot answer all four, re-read the docs. Do not proceed to Step 2.

## Step 2: Receive interview summary or existing design doc

This skill operates in two modes:

### Mode A: Existing design doc (validate and update)

Check if an argument path was passed, or use the Glob tool to check `docs/plans/*.md` for a design doc that uses the `flow-designer-design-doc.md` template format (has Activities table, Connections table, Variables section, Event Handlers section).

If a design doc exists:
1. Read it in full
2. Validate every activity type against `flow-designer-activities/_index.md` — flag any activity type that doesn't exist
3. Validate every port name in the Connections table against the Output Paths table in each activity's own doc (loaded in Step 1 / Step 4) — flag mismatches
4. Validate that all connection targets exist in the Activities table — flag dangling references
5. Check that OnGlobalError is present in Event Handlers
6. Check that every HTTP Request has a downstream Condition checking `httpStatusCode`
7. Present findings to the user: "I validated the existing design doc. Found [N] issues: [list]. I'll fix these and update the doc. Does the overall flow design still match your requirements?"
8. Fix validated issues, then proceed to Step 7 (Review and save) with the updated doc

### Mode B: Fresh design (from interview answers)

This skill receives the interview answers directly from the user (or from the agent running it, such as `wxops`). These include:

- What the flow needs to do (business requirements)
- Channel type (inbound voice, outbound, subflow)
- Data sources (APIs, databases, BRE)
- Routing logic (DNIS, skill-based, time-of-day, caller verification)
- Languages and TTS needs
- Queue and escalation requirements
- Any special handling (callback, survey, transfer)

The skill does NOT repeat the questions the agent builder already asked (use case, escalation, data sources, notifications). But the agent builder collects business context — not Flow Designer specifics. After selecting blueprints in Step 3, this skill MUST ask the user for the business details needed to fill in the design doc. These are decisions only the user can make:

- **Menu options:** What choices should each menu offer? (e.g., "1=Sales, 2=Support, 3=Hours")
- **TTS prompts:** What should each greeting/announcement say? (propose a default, let them refine)
- **Queue names:** What queue(s) should callers route to? (confirm names from Q6 answers)
- **Business hours schedule:** What's the schedule name in Control Hub? (or "I need to create one")
- **Transfer destinations:** What extension(s) or numbers should transfers dial?
- **Retry behavior:** How many no-input/invalid retries before disconnect? (propose 3 as default)
- **Languages:** Which TTS languages? (if multilingual was mentioned in Q1)

Ask these as you encounter them during blueprint composition (Step 5), not all at once upfront. One question per message. Don't ask about platform details the user can't answer (port names, variable syntax, activity configuration fields) — those come from docs.

Proceed to Step 3.

## Step 3: Select blueprint(s)

Using the interview answers and `reference.md § Blueprint Selection Guide`:

1. Identify which blueprint(s) match the requirements
2. If multiple blueprints apply, identify how they compose using `reference.md § Blueprint Composition Patterns`
3. Present the selected blueprint(s) to the user:

> "Based on your requirements, I'm using these flow patterns:
> - **Blueprint 3: Business Hours Routing** — route callers differently when open vs closed
> - **Blueprint 2: DNIS-Based Routing** — identify the store from the dialed number
> - **Blueprint 7: Language Selection** — English/Spanish language choice
>
> These compose as: NewPhoneContact → DNIS lookup → Business Hours check → Language Menu → Main Menu → Queue. Does this look right?"

4. Wait for confirmation before proceeding.

## Step 4: Load activity docs

For each activity type in the selected blueprint(s):

1. For essential activities (Play Message, Play Music, Set Variable, Queue Contact, Disconnect Contact): re-read `docs/reference/flow-designer-essentials.md` if it may have been compressed out of context (if more than ~10 tool calls have occurred since Step 1)
2. For all other activities: read the activity's doc file from `docs/reference/flow-designer-activities/{activity}.md`
3. Extract: required settings, optional settings, output variables, exit ports, restrictions
4. Build an internal activity metadata table (not shown to user)

If the flow needs patterns like subflows, business hours, TTS configuration, or Functions Activity:
- Also read `docs/reference/flow-designer-patterns.md` for the relevant section

**This is the critical step.** The activity docs are the source of truth for what fields exist, what ports are available, and what restrictions apply. Every subsequent step uses this metadata.

## Step 5: Customize blueprint for requirements

Using the interview answers + activity metadata:

### 5a. Fill in activity configurations

- TTS prompts (from user's requirements — write actual prompt text)
- HTTP Request URLs, headers, query params (from user's API details)
- Condition expressions (from user's routing logic) — operators go INSIDE braces: `{{var > 0}}`
- Menu options (from user's IVR structure) — max 10 digits (0-9)
- Set Variable expressions (from user's data transformation needs) — use Pebble filter syntax
- Queue Contact settings (from user's queue requirements) — Static Queue for skill-based routing
- Functions Activity code (when data transformation is needed) — 5-second limit, no HTTP calls

### 5b. Define flow variables

For each variable, determine:
- Name (use conventions from `reference.md § Variable Naming Conventions`)
- Type (STRING, INTEGER, BOOLEAN, JSON, DECIMAL, DATE TIME)
- Default value
- Agent Viewable (yes/no) + Desktop Label if yes
- Purpose

**Type rules:**
- Phone numbers → STRING (never INTEGER — leading zeros are stripped)
- JSON variables → max 5 per flow, 16KB each
- Global Variables → STRING max 256 chars at init, 1024 at runtime
- Counters → INTEGER

### 5c. Build the complete connection graph

For every activity, every **non-error** exit port must connect to a target activity. Use the exact port names from `reference.md § Port Name Canonical Map`. Skip Error / Undefined Error ports — they auto-route to OnGlobalError. Only include an Error port row if the flow intentionally routes it to a specific activity instead of OnGlobalError.

The Connections table must form a complete directed graph with:
- No orphaned nodes (every activity is reachable from NewPhoneContact)
- No missing non-error exit paths (every non-error port on every activity has a row)
- Every terminal path ends with Disconnect Contact (main flow) or End Flow (event flows only)
- No Error port rows (unless intentionally routed to a specific activity)

### 5d. Identify event handlers needed

Every flow gets OnGlobalError at minimum. Additional event handlers based on requirements:
- Callback in flow → add CallbackFailed handler
- Post-call survey → add AgentDisconnected handler with Feedback V2
- Screen Pop → add AgentOffered or AgentAccepted handler
- Custom caller ID → add PreDial handler with Set Caller ID

### 5e. Validate against gotchas

Check every design decision against `reference.md § Common Design Gotchas`. Fix any violations before proceeding.

## Step 5f: Validate the design

Before generating the design document, run these checks:

1. **Graph completeness**: Every activity in the Activities table has at least one incoming connection (except NewPhoneContact) and every non-terminal activity has at least one outgoing connection.
2. **Port name accuracy**: Every port name in the Connections table appears in the Port Name Canonical Map (reference.md). Flag any that don't match.
3. **Output variable prefixes**: Every Condition expression that references an activity output variable uses the canonical prefix from the activity doc (not the activity label).
4. **JSON variable count**: Count JSON-typed flow variables. If >5, redesign to use STRING + Parse.
5. **Terminal paths**: Every path through the connection graph ends at a Disconnect Contact node.
6. **No self-loops without counters**: Every connection that loops back to a Menu or Collect Digits passes through a Set Variable (counter increment) and a Condition (counter check) first.

If any check fails, fix the design before presenting to the user.

## Step 6: Generate the design document

**Re-read before generating (sequentially, one file at a time).** Re-read `docs/templates/flow-designer-design-doc.md`, then `docs/reference/flow-designer-essentials.md`. If the flow uses situational activities, re-read their docs too — one at a time. Steps 1-5 may have been long enough for context compression to evict the field tables and port names you need. Fill in every section:

### Section 1: Purpose
- Flow name, what it does, who calls in

### Section 1b: Applicable Blueprints
- Which blueprint(s) were selected, how they compose

### Section 2: Flow Metadata
- Flow Name, Flow Type, Entry Point, PSTN Number, Business Hours Schedule, TTS Connector, Version Label

### Section 3: Variables
- **Flow Variables table**: Name, Type, Default, Agent Viewable, Desktop Label, Purpose
- **Global Variables Referenced table**: Name, Type, Sensitive, Source
- **NewPhoneContact Outputs Used table**: Variable, Purpose

### Section 4: Activities
- Every activity in wiring order with ID, Label, Activity Type, Key Configuration
- Key Configuration uses condensed key-value format from the template

### Section 5: Connections
- Complete directed graph: Source Activity, Port, Target Activity
- Port names must match `reference.md § Port Name Canonical Map` exactly
- Every exit port of every activity must have a row

### Section 6: Event Handlers
- OnGlobalError (mandatory): activity chain + wiring
- Additional handlers: event, handler chain, purpose

### Section 7: TTS Content
- Activity Label, TTS Text, Language — for every TTS prompt in the flow

### Section 8: External Integrations (if applicable)
- Activity Label, API Endpoint, Method, Auth, Expected Response Shape
- HTTP Headers per integration

### Section 9: Business Hours (if applicable)
- Schedule Name, Working Hours, Holidays, Overrides
- Routing by Time table

### Section 10: Queue Configuration
- Queue Name, Team, Priority, Skill Requirements, Skill Relaxation

### Section 11: Error Handling Summary
- Error Source, Failure Mode, Routes To, Rationale

### Section 12: Flow Diagram
- ASCII art showing the complete flow with all paths
- Use the same activity labels from the Activities table
- Show branching with `├──` and `└──` connectors

### Section 13: Test Plan
- Test scenarios for happy path, error paths, and edge cases

### Section 14: Build Checklist
- Every step marked as `pending`
- Include one-time setup items if applicable

Present the complete design doc to the user for review. Do not save it until they approve.

## Step 7: Save and handoff

After user approval:

1. Save the design doc to `docs/plans/YYYY-MM-DD-{flow-name}-design.md` (use today's date). If the file exceeds 150 lines, write it in chunks using sequential Write/Edit calls — never write a large file in a single operation.
2. Tell the user what to do next:

> "Your design doc is saved at `docs/plans/[path]`. Next steps:
> - Run `/build-spec-diagram` to generate a visual .drawio diagram
> - Run `/build-flow-designer` to get step-by-step build instructions
> - Both skills will read this design doc automatically"

---

## CRITICAL REMINDERS

1. **Port names use the design-doc convention.** Use the port names from `reference.md § Port Name Canonical Map`, which match `build-spec-diagram/reference.md` PORT_DEFINITIONS. The standard error port is "Error" (not "Undefined Error"). "Default" and "Out" are different ports on different activities. Read the canonical map to get the right one. Never guess.

2. **Every exit needs a path.** If a Menu has 4 options + No-Input Timeout + Unmatched Entry, the Connections table needs a row for each. Missing a Timeout path means callers hang in silence.

3. **OnGlobalError is mandatory.** Every design doc must include it in Event Handlers. Without it, unhandled errors silently drop calls.

4. **Disconnect Contact at every terminal path.** Not End Flow. End Flow is only for event flows. Main flow paths end with Disconnect Contact.

5. **Variable types have consequences.** JSON variables are limited to 5 per flow with 16KB max each. INTEGER variables cannot store phone numbers (leading zeros). Get the type right in the design doc or the build will fail.

6. **No-input retry requires a counter pattern.** Menu No-Input Timeout → SetVariable(count+1) → Condition(count < 3) → True: loop back to Menu → False: disconnect. Never loop a Menu back to itself without a counter.

7. **HTTP Request needs response time buffer.** If an HTTP Request follows Queue Contact, add a Play Message or Play Music between them. Queue Contact returns immediately; the HTTP Request may not be ready.

8. **Blueprint composition is not concatenation.** When combining blueprints, merge shared activities (don't duplicate Queue Contact), resolve variable name conflicts, and verify the combined connection graph has no orphaned nodes.

9. **This is a DESIGN skill, not a BUILD skill.** Output a design document, not step-by-step GUI instructions. The build skills handle implementation. If the user asks "how do I configure this in Flow Designer," redirect them to `/build-flow-designer`.

10. **Condition expressions: operators go inside braces.** Correct: `{{count > 3}}`. Wrong: `{{count}} > 3`. The expression parser requires the operator inside the double braces.

11. **Functions Activity for data transformation.** When the flow needs complex data transformation (date formatting, DNIS maps, JSON restructuring), design with a Functions Activity (5s limit, no HTTP calls) before proposing external services.

12. **Variable Queue does not support skill-based routing.** If the design needs skill routing, use Static Queue. Variable Queue reverts to Longest Available Agent.

13. **Output variable prefixes use the canonical form from activity docs.** The prefix is the activity type's canonical output variable name (e.g., `BridgedTransfer_dxm.FailureCode`, `HTTPRequest.httpStatusCode`, `CollectDigits.DigitsEntered`), NOT the activity label. Read the Output Variables table from the activity doc file in Step 4 and use those exact prefixes in Condition expressions.

---

## ANTI-HALLUCINATION GUARD

Every activity type, port name, configuration field, and variable syntax in the design document you produce MUST appear verbatim in the docs you loaded in Step 1 and Step 4.

If you are about to write an activity type, port name, or configuration field that you did not read in the docs:

1. STOP and say "I need to verify this — the activity docs don't cover [X]. Would you like me to do a web search?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the Cisco documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]`
5. Do NOT include unverified details in the design document.

Do not invent plausible-sounding platform details under any circumstances. The entire downstream pipeline (spec diagram, build instructions, solution docs) trusts this design document. An invented port name here becomes a wrong instruction in build-flow-designer and a broken edge in build-spec-diagram.
