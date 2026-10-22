---
name: build-flow-designer
description: |
  Build step-by-step instructions for a WxCC Flow Designer voice flow from an
  existing design document in docs/plans/: activity-by-activity build
  instructions for inbound IVR, callback, queue treatment, DNIS routing,
  skill-based routing, business hours, multilingual menus, and post-call survey.
  Use for: generating build instructions AFTER a design document exists — STEP 2
  of the pipeline (design-flow → build-flow-designer). REQUIRES a design doc.
  NOT for: creating the design (design-flow), AI agents (configure-ai-agent, design-scripted-agent),
  Webex Connect flows (build-action and the other Connect skills).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [flow-type or path-to-design-doc]
---

# Build Flow Designer Workflow

## Step 1: Load essential references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/reference/flow-designer-essentials.md` — activity config for Play Message, Play Music, Set Variable, Queue Contact, Disconnect, Variable Types, Output Variables, Global Events
2. Read `docs/reference/flow-designer-activities/_index.md` — lists all available activity files
3. Read this skill's `reference.md` — wiring patterns and gotchas cheat sheet
4. Read `docs/reference/flow-blueprints.md` — common flow patterns with pre-built Activities and Connections tables

**Checkpoint — do NOT proceed until you can answer from loaded docs:**
- What are the 3 variable categories and how do they differ? (from essentials, Variable Types)
- What does OnGlobalError do and why is it mandatory? (from essentials, Global Event Flows)
- What are Queue Contact's failure codes? (from essentials)

If you cannot answer all three, go back and read the docs.

## Step 1.5: Check for existing design doc

Check if the user passed a plan document path as an argument, or if `docs/plans/` contains a design doc for this flow.

1. If an argument was passed: read the plan document at that path
2. If no argument: use the Glob tool to check `docs/plans/*.md` for recent flow design docs
3. If a design doc exists and uses the `flow-designer-design-doc.md` template format (has sections: Activities table, Connections table, Variables, Event Handlers):
   - Read it and extract the flow structure
   - Tell the user: "I found an existing design doc at [path]. I'll use this as the flow specification. Let me know if anything needs to change before I walk you through the build."
   - **Skip Steps 2, 4, and 5** (flow type determination, requirements gathering, flow design) — all of that is already in the design doc
   - **Still run Step 3** (Load additional activities) — read the activity doc for EVERY activity type in the design doc's Activities table. Without these docs loaded, Step 6 cannot produce correct field-level build instructions.
   - Then **proceed to Step 6** (Build — Create flow and configure activities)
4. If no design doc exists: proceed to Step 2 as normal

## Step 2: Determine flow type

Ask the user what they're building. Classify into one of these types:

| Type | Key Indicator | Additional Activities to Load |
|------|--------------|-------------------------------|
| **Standard IVR** | Menu/DTMF routing to queues | Menu, Collect Digits, Business Hours |
| **Callback** | Caller opts out of waiting, gets called back | Callback, Get Queue Info, Call Progress Analysis, Wait |
| **Queue Treatment** | Hold music with periodic announcements/escalation | Get Queue Info, Advanced Queue Information, Escalate CDG |
| **DNIS Routing** | Different queues per dialed number | Case, Functions Activity |
| **Skill-Based Routing** | Route by agent skills with relaxation | (Queue Contact skill config is in essentials) |
| **Data Dip + Route** | HTTP lookup mid-flow, route on result | HTTP Request, Parse, Case, Condition |
| **Post-Call Survey** | CSAT/NPS after agent disconnects | Feedback V2 |
| **Transfer Flow** | Blind/bridged transfer to external DN | Blind Transfer, Bridged Transfer |
| **Scheduled Callback** | Future callback at a scheduled time | Schedule Callback |

If the user's request spans multiple types (e.g., "IVR with callback option"), combine the activity loads.

## Step 3: Load additional activities

For each additional activity identified in Step 2, read its file directly from `docs/reference/flow-designer-activities/`:

Example: if building a Standard IVR, read:
- `docs/reference/flow-designer-activities/menu.md`
- `docs/reference/flow-designer-activities/collect-digits.md`
- `docs/reference/flow-designer-activities/business-hours.md`

File naming is kebab-case of the activity name. Check `_index.md` if unsure of the filename.

Also load `docs/reference/flow-designer-patterns.md` if the flow needs:
- Subflows (reusable components)
- Percentage allocation (A/B testing)
- Dynamic variables
- Custom connectors for HTTP auth
- Functions Activity patterns

## Step 4: Gather requirements

Confirm with the user before building:

- **Flow name** (descriptive, e.g., "Main IVR with Callback")
- **Entry Point** — which EP will this flow be assigned to? (or "I'll create one")
- **Business hours** — does the flow need hours-based routing? (if yes: which schedule name?)
- **Queue(s)** — which queue(s) will contacts route to? (names or "I'll create them")
- **Hold treatment** — what should callers hear while waiting? (music file? periodic announcements?)
- **Error handling** — play a message + queue to fallback, or just disconnect?
- **Any conditional routing** — DNIS, skills, caller data lookups?

Do NOT ask about:
- Variable syntax (provide it from docs)
- Activity configuration details (provide from loaded docs)
- TTS connector options (tell them — Cisco Cloud TTS is default)
- Failure code meanings (tell them from docs)

## Step 5: Design the flow structure

Present the flow diagram to the user for approval BEFORE building:

```
NewPhoneContact
  → [Business Hours (if needed)]
    ├── Working Hours → [Menu / Collect Digits / VA V2]
    │     → [Case/routing logic]
    │     → Queue Contact (target queue)
    │     → Play Music (hold loop)
    │     → [Callback option if configured]
    │     → Disconnect Contact
    ├── Holidays/Default → Play Message ("We're closed") → Disconnect Contact
  → OnGlobalError → Play Message (error) → Queue Contact (fallback) → Play Music → Disconnect
```

Adapt this skeleton based on the user's requirements. If a matching blueprint exists in `docs/reference/flow-blueprints.md`, use its Activities and Connections tables as the starting point and customize.

**Save the design:** Read `docs/templates/flow-designer-design-doc.md` and fill in the template with the approved flow structure. Save to `docs/plans/YYYY-MM-DD-{flow-name}.md`. This is the compaction recovery safety net — if context resets mid-build, the design doc preserves all the activities, connections, variables, and TTS content.

Get explicit approval before proceeding.

## Step 6: Build — Create flow and configure activities

> If entering from Step 1.5 (existing design doc), use the Activities table (Section 4), Connections table (Section 5), and flow diagram (Section 12) from the design doc instead of Step 5's output.

**Re-read before building.** The docs loaded in Steps 1 and 3 may have been compressed out of context by now. Before generating configuration instructions for the first activity, re-read `docs/reference/flow-designer-essentials.md`. This is not optional — if you cannot see the field tables in your current context, your instructions will be wrong.

Walk through each activity in wiring order. For EACH activity:

1. Name the exact UI location: **Contact Center > Flows > [flow name] > [activity name]**
2. State exactly which activity to drag from the Activity Library
3. List every field and the exact value to enter (from loaded docs)
4. State which output path to wire to which next activity
5. Never say "configure as needed" — specify the value

**Do NOT generate wiring instructions for Error / Undefined Error ports.** These auto-route to OnGlobalError — telling the user to wire them is redundant and clutters the instructions. Only mention Error port wiring if the design doc explicitly routes an Error port to a specific activity (not OnGlobalError).

### NewPhoneContact (Start)

Every flow starts here. No configuration needed — it auto-exists.

### OnGlobalError (mandatory)

Wire in the Event Flows tab:
1. Click **Event Flows** tab in the canvas toolbar
2. Select **OnGlobalError**
3. Drag: Play Message → Queue Contact → Play Music → Disconnect Contact
4. Configure Play Message: TTS = "We're experiencing technical difficulties. Please hold while we connect you to an agent."
5. Configure Queue Contact: select the fallback queue
6. Configure Play Music: select default hold music, duration = 600 seconds

### Remaining activities

Build in the order shown in the flow diagram from Step 5. For each activity:

1. **Re-read its activity doc** — use the Read tool on the specific file in `docs/reference/flow-designer-activities/` for this activity type. Do this even if you read it earlier. Context compression may have evicted the field tables you need. If the activity is an essential (Play Message, Play Music, Set Variable, Queue Contact, Disconnect Contact), re-read `docs/reference/flow-designer-essentials.md` instead.
2. Reference the specific field tables from the doc you just re-read
3. Use `{{variable}}` syntax for dynamic values (Pebble template format)
4. Specify TTS connector as Cisco Cloud TTS unless user has Google TTS configured

## Step 7: Configure variables

Based on the flow, create necessary variables:

1. **Flow Settings** (gear icon) → **Variable Definition** → **Add Flow Variable**
2. For each variable, specify:
   - Name
   - Type (String, Integer, Boolean, JSON, etc.)
   - Default value (if any)
   - Agent Viewable (yes/no)
   - Desktop Label (if Agent Viewable)

List the specific variables needed based on the flow design.

## Step 8: Validate and publish

Walk the user through:

1. Click **Validate** in the toolbar — fix any errors shown
2. Click **Publish** — choose version label:
   - `Dev` for initial testing
   - `Live` for production
3. Assign to Entry Point:
   - **Control Hub > Contact Center > Entry Points** → edit the EP
   - Under **Flow**, select the published flow
   - Under **Version Label**, select `Live` (or `Dev` for testing)
   - Save

## Step 9: Present complete configuration

Summarize the full flow with:
- Flow diagram (ASCII art showing all paths)
- Variable table (name, type, purpose, default)
- Queue assignments
- Business hours schedule (if applicable)
- Error handling paths
- Any Global Variables referenced

---

## CRITICAL REMINDERS

- **This is Flow Designer, NOT Webex Connect.** Different platform, different UI, different variable syntax. Flow Designer uses `{{variable}}` Pebble syntax. Connect uses `$(nX.field)` syntax.
- **Never generate flow JSON.** Walk users through the GUI step by step.
- **Every instruction must come from loaded docs.** If a field or behavior isn't in the docs you loaded, say "I don't have that documented — would you like me to do a web search to find the correct answer?" If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation, and mark the result as `[FROM WEB SEARCH — not yet in project docs]`. Do not invent plausible-sounding platform details under any circumstances.
- **OnGlobalError is mandatory.** Every flow must have it wired. Without it, unhandled errors silently drop calls.
- **Queue Contact before Play Music.** The queue goes first, THEN Play Music provides hold treatment while waiting.
- **Disconnect Contact at every exit.** Every flow path must terminate with Disconnect Contact (not End Flow for main flow paths).
- **End Flow is for event flows only.** Use it in AgentDisconnected, PhoneContactEnded, etc. — not in the main flow.
- **Variable Types matter.** JSON variables have a 5-per-flow limit and 16KB size cap. Global Variables max 256 chars at init, 1024 at runtime.
- **Play Message is uninterruptible.** If callers need to interrupt, use Menu or Collect Digits instead.
- **HTTP Request after Queue Contact needs a buffer.** Add Play Message or Play Music between them.
