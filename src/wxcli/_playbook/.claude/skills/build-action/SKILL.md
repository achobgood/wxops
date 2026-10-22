---
name: build-action
description: |
  Build a Webex Connect flow for one AUTONOMOUS AI agent action. Creates the
  HTTP Request nodes, headers, output variables, and Flow Outcomes that connect
  an AI Agent Studio action to an external API or database query.
  Use for: building the Webex Connect flow that executes when an autonomous
  AI agent triggers a specific action (e.g., "look up order status").
  NOT for: scripted fulfillment (build-scripted-fulfillment), conversation loops (build-digital-inbound),
  outbound notifications (build-notification, build-outbound-flow).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [action-name]
---

# Build Action Workflow (Autonomous Only)

> **Scripted agents?** This skill builds standalone Connect flows for autonomous agent actions. Scripted agents handle fulfillment differently — inline within the conversation flow, branching on `template_key`. See `docs/reference/ai-agent-studio-scripted.md` for the scripted fulfillment pattern.

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/reference/webex-connect.md` for Connect flow conventions
2. Read `docs/reference/db-integration.md` for the user's DB patterns
3. Read `docs/templates/action-config.md` for the output format
4. Read this skill's `reference.md` for the quick-reference cheat sheet

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What mode must Flow Outcomes use, and what happens if you use the other mode? (from `webex-connect.md`)
- What HTTP headers are required for the user's DB backend? (from `db-integration.md`)

If you cannot answer both, you skipped Step 1. Go back and read the docs.

## Step 2: Gather requirements

Confirm with the user before proceeding:

- **Action name** (must be lowercase_underscores, e.g. `get_account`)
- **What it does** (one sentence: "Looks up a customer's account by phone number")
- **Which table(s)** it queries
- **Input entities** the caller provides (phone_number, date, test name, etc.)
- **What it returns** to the agent (which fields)

## Step 3: Create the Connect Flow — `[Webex Connect]`

1. Navigate to **Services** > select your service > **Flows**
2. Click **Create Flow**, name it to match the action name (e.g., `lookup_patient`), click **Create**
3. The canvas opens with a green **Start** node already placed
4. From the node palette on the left, drag these nodes onto the canvas:
   - **HTTP Request** — calls your database/API
   - **End** node
   - (If multi-node: drag additional HTTP Request nodes as needed)
5. Wire the nodes left to right: **Start → HTTP Request → End** (drag from output connector to input connector)
6. Click the **Start** node to configure the AI Agent trigger:
   - Set **Trigger category** to **AI Agent**
   - The event auto-populates as "Trigger from AI Agent to initiate flow" — no manual entry needed
   - In the **Provide sample JSON** field, paste a sample payload with one key per slot entity the action declares, then click **Parse** to register the variables
7. Double-click the **HTTP Request** node — URL, headers, output variables covered in following steps

## Step 4: Determine HTTP method — `[Webex Connect → HTTP Request node]`

| Goal | Method |
|------|--------|
| Look up / search / list | GET |
| Create a new record | POST |
| Update an existing record | PATCH |
| Delete / cancel (hard delete) | DELETE |

## Step 5: Build the URL — `[Webex Connect → HTTP Request node → URL field]`

- Use PostgREST filter syntax from `reference.md`
- Insert variable picker placeholders: `$(n2.aiAgent.entity_name)`
- Hardcode any known UUIDs (location IDs, etc.) directly in the URL
- For fuzzy text search use `ilike.*$(n2.aiAgent.entity)*`
- For date ranges use `gte.{start}&col=lte.{end}`
- Add `&order=col.asc&limit=N` as needed

## Step 6: Determine headers — `[Webex Connect → HTTP Request node → Headers section]`

Start with the standard set (from `db-integration.md` and `reference.md`):

| Header | Value | Include? |
|--------|-------|----------|
| apikey | {anon_key} | Always |
| Authorization | Bearer {anon_key} | Always |
| Content-Type | application/json | Always |
| Accept | application/vnd.pgrst.object+json | Single-object responses ONLY; omit for arrays |
| Prefer | return=representation | POST/PATCH ONLY |

## Step 7: Define output variables — `[Webex Connect → HTTP Request node → Output Variables tab]`

- Click the **Output Variables** tab in the HTTP Request node configuration
- Click **Import from Sample**, paste a sample response JSON into the Data Parser dialog, click **Parse**, select the key paths to extract under "Select key paths to be extracted", then click **Import** — rows auto-generate
- Renaming output variables after parsing is not documented in official docs; use consistent field names in your sample JSON to avoid naming conflicts across nodes
- Response path format (not documented in official docs — the UI uses key-path selection): `$.field_name` (single object) or `$` (whole array)

## Step 8: Run a live curl test — `[Terminal / API Client]`

Test the actual URL with real headers and a real filter value against the user's database. Verify:

- HTTP 200 (or 201 for POST)
- Response shape matches expected output variables
- All expected fields are present
- Auto-generated fields appear in POST responses

## Step 9: Configure Flow Outcomes — `[Webex Connect → Flow Settings]`

Flow Outcomes is **not a node** — there is nothing to drag onto the canvas, and the End node carries no outcome tag.

1. Click **Flow Settings** on the Flow Builder page
2. Navigate to the **Flow Outcomes** tab
3. Open the **Last Execution Status** row and enable the **Notify** parameter, then confirm **Notify AI Agent** is the selected notification target (**UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — check the tenant UI either way; see `docs/reference/webex-connect.md` § "The Last Execution Status row")
4. Use **Enter key and value** mode (NOT Enter JSON mode — it doesn't resolve variables)
5. Add one row per variable to return: **Key** = variable name, **Value** = use variable picker to select from HTTP node
6. There is **one key-set for the whole flow** — you cannot return a different payload per Branch leg. Converge the legs and return a status/error variable through this single key-set. Max payload length **16,000 characters**
7. Click **Save**

## Step 10: Save and Make Live — `[Webex Connect]`

1. Click **Save** in the top toolbar
2. Click **Make Live** to activate the flow — the flow must be live before AI Agent Studio can select it in the action dropdown

## Step 11: Generate the full 10-step action config

Use the template from `docs/templates/action-config.md`. Fill in all 10 sections:

1. Action Description
2. Input Entities table
3. Configure AI Agent Event sample JSON
4. HTTP Method
5. URL (with variable picker placeholders)
6. Headers note
7. Output Variables table
8. Sample Response JSON (for Parse)
9. Flow Outcomes key-value table
10. Live curl test result

## Step 12: Present to user

**Present the config exactly once.** If the user requests changes, update the specific section — do not regenerate the entire config.

Format the config for direct copy-paste into Webex Connect. If the flow requires multiple HTTP nodes (e.g., lookup ID then create record), document each node separately with clear variable chaining:

- Node N (GET): URL, headers, output variables
- Node N+1 (POST): URL, headers, body (referencing `$(nN.variable_name)` from previous node), output variables

## Step 13: Multi-node flows

If the action needs multiple HTTP nodes:

1. Document each node separately
2. Show variable chaining: `$(n{previousNode}.{variableName})` -- no `aiAgent` prefix for node-to-node references
3. Flow Outcomes only need the final output variables

---

## CRITICAL REMINDERS

- **NEVER type variable references manually** -- always show `$(n{X}.aiAgent.variable_name)` format and tell user to use the variable picker in Connect
- **Flow Outcomes MUST use Enter key and value mode**, NOT Enter JSON mode (Enter JSON does not resolve variables)
- **Verify Notify AI Agent is selected** in Flow Settings > Flow Outcomes > Last Execution Status (**UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — Cisco documents it as enabled by default for the AI Agent start node, the platform owner describes selecting it explicitly, and the two have not been reconciled; check the tenant UI and confirm it is selected either way — open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6)
- **Rename `id`** to a descriptive name after Parse auto-generates output variable rows (renaming not confirmed in official docs — use consistent field names in sample JSON as a reliable alternative)
- **For POST/PATCH**: add `Prefer: return=representation` header
- **Prohibited nodes**: Delay, Social Hour Check, Receive Node, Call Workflow -- these risk exceeding the 30-second execution time limit
- **HTTP 4xx/5xx goes through onSuccess**, not onError. If your action involves a lookup that might return no results, recommend a Branch node to check status code. See `webex-connect-advanced.md`.
- **Do NOT include auto-generated fields** (IDs, confirmation numbers) in POST request bodies -- capture them from the response
- **Phone numbers and human-speakable identifiers only** -- never use UUIDs as slot entities

## ANTI-HALLUCINATION GUARD

Every field name, header value, variable syntax, and node configuration detail in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
