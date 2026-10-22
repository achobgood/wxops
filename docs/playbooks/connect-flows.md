# Webex Connect Flows Playbook

<!-- ref-tag: connect-flows-v4 -->

## Overview

This playbook covers how to build Webex Connect flows that back AI agent actions. Each action in AI Agent Studio maps to exactly one Connect flow.

---

## 1. Flow Structure for AI Agent Actions

Each action flow follows this pattern:

```
Start (AI Agent Trigger) → HTTP Request Node(s) → End
```

Flow Outcomes are configured in **Flow Settings** (not a node on the canvas).

### Required Nodes
- **Start node** (always first): triggers on the AI Agent event
- **HTTP Request node(s)**: calls Supabase PostgREST API
- **End node**: terminates the flow

### Prohibited Nodes in AI Agent Flows
These nodes risk exceeding the 30-second execution time limit and break the agent:
- Delay
- Social Hour Check
- Receive
- Call Workflow

---

## 2. Start Node Configuration

The **Start** node is always the first node in a new flow — it is already on the canvas when you create the flow.

1. Click the **Start** node to open its configuration
2. Set **Trigger category** to: **AI Agent**
3. The event auto-populates as "Trigger from AI Agent to initiate flow" — no manual entry needed
4. In the **Provide sample JSON** field, paste a sample payload with one key per slot entity the action declares, then click **Parse** to register the variables

### Also on the Start node — Trigger Conditions and live-session gating

These two settings are not part of the required configuration for an AI Agent action flow, but they live on the same Start node and are the first thing you will need when you build an SMS, RCS or digital-channel flow. Both are documented at [help.webexconnect.io/docs/start-node](https://help.webexconnect.io/docs/start-node).

- **Trigger Conditions** — "The platform allows selective triggering of the flow only when the conditions set on the trigger event are fully met." This is the mechanism for routing different inbound keywords or payload values to different flows. Thirteen operators are available: **Equals**, **Not equals**, **In**, **Not in**, **Contains**, **Greater than**, **Less than**, **Greater than equal to**, **Less than equal to**, **Equals ignore-case**, **Between**, **Starts with**, **Ends with**.
- **Trigger only when there are no live sessions** (checkbox) — present for SMS, RCS and digital channels. It prevents a second flow execution while a Receive-node session is still live. Set it on any two-way SMS flow.

---

## 3. HTTP Request Node — Supabase GET

### URL Format
```
https://{project-ref}.supabase.co/rest/v1/{table}?{filter}
```

Use the **variable picker** (not manual typing) to insert AI Agent variables into the URL:
```
...?phone_number=eq.$(n2.aiAgent.phone_number)
```
Node numbers change based on flow layout — always use the picker to get the correct reference. The `aiAgent` segment in the variable path is not documented in official docs; use the picker to confirm the exact format.

### Headers (standard set)
| Header | Value |
|--------|-------|
| `apikey` | `{anon_key}` |
| `Authorization` | `Bearer {anon_key}` (space before key is required) |
| `Content-Type` | `application/json` |
| `Accept` | `application/vnd.pgrst.object+json` ← **omit for array responses** |

### Output Variables Tab
1. Click **Import from Sample**, paste a sample JSON response into the Data Parser dialog, click **Parse**, select the key paths to extract under "Select key paths to be extracted", then click **Import** — rows auto-generate
2. Renaming output variables after parsing is not documented in official docs; use consistent field names in your sample JSON to avoid naming conflicts across nodes
3. Response path format (not documented in official docs — the UI uses key-path selection):
   - Single object (with Accept header): `$.field_name`
   - Array response (no Accept header): `$[0].field_name` for first element, or `$` for whole array

---

## 4. HTTP Request Node — Supabase POST

For create/update operations:

### Method: POST
### URL: `https://{project-ref}.supabase.co/rest/v1/{table}`

### Additional Headers
Add on top of the standard set:
```
Prefer: return=representation
```
This tells PostgREST to return the created record so you can capture the generated ID and confirmation number.

### Body
- Set body type to **JSON**
- Use variable picker to insert values from previous HTTP nodes or AI agent entities:
```json
{
  "patient_id": "$(n3.patient_id)",
  "location_id": "{known-uuid}",
  "test_id": "$(n2.aiAgent.test_id)",
  "scheduled_at": "$(n2.aiAgent.scheduled_at)",
  "status": "scheduled"
}
```

---

## 5. Chaining Multiple HTTP Nodes

When an action requires multiple API calls (e.g., GET patient_id then POST appointment):

1. Add a second HTTP Request node after the first
2. Wire first node's **Success** output → second node's input
3. Reference output variables from first node in second node's URL or body using the picker
4. Variable format from a previous node: `$(n{nodeNumber}.{variableName})`

---

## 6. Flow Outcomes Configuration

Flow Outcomes is **not a node**. It is configured in **Flow Settings** — click **Flow Settings** on the Flow Builder page, then the **Flow Outcomes** tab. Wire the last HTTP node to an **End** node; the End node carries no outcome tag, and there is **one key-set for the whole flow** (you cannot return a different payload per Branch leg — converge the legs and return a status/error variable instead) [`docs/reference/webex-connect.md` § "Flow Outcomes (Flow Settings — NOT a node)"].

> **⚠ UNRESOLVED — Enter key and value vs. Enter JSON.** Two sources disagree about whether **Enter JSON** mode resolves variables, and nobody in this documentation pass could test it. Read all three points below before you pick a mode.
>
> **1. What Cisco publishes.** [help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions) sanctions the JSON option outright: "You can send a simple JSON payload using key-value pairs or a more complex payload (including arrays) using the 'Paste JSON' option." The same section states "Variables can be added with a '$' prefixed. Variable names are case-sensitive." and "The maximum length of payload can be 16000 characters." On Cisco's account, JSON is the supported route for nested and array payloads and variables *do* resolve inside it.
>
> **2. What this repo has claimed.** That **Enter JSON** mode does *not* resolve variables — that the agent receives the literal `$(nX.y)` strings — and that **Enter key and value** must therefore always be used. This is an **unattributed observation**: no author, date, tenant, or flow was ever recorded alongside it, and it appears on no Cisco page. Do not cite it as documented platform behaviour.
>
> **3. Status: unresolved.** Both statements can be true at once — an observed platform bug on a particular tenant or release versus Cisco's documented intent. Do not resolve this from either source alone, and do not treat the prohibition as settled. Confirming it requires a live Webex Connect tenant, which nobody in this pass had. Tracked as open item **O1** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` § 6 ("Open items requiring tenant or platform access").
>
> **How to proceed while O1 is open.** For a flat set of return keys — the shape every action in this playbook uses — build it in **Enter key and value**: Cisco documents that mode as equally valid for simple payloads, and it is the mode the unverified observation says works. If your action must return a nested object or an array (for example a list of available appointment slots), **Enter JSON** is the only route Cisco documents at all; build it, then verify on your own tenant that the AI agent receives resolved values and not literal `$(nX.y)` strings before you rely on it. Record what you observe against O1.

### Configuration Steps
1. Click **Flow Settings** on the Flow Builder page
2. Go to the **Flow Outcomes** tab
3. Find the **Last Execution Status** outcome row
4. Enable the **Notify** parameter on that row
5. Under **Notification Settings**, select **Notify AI Agent**
6. Add one row per variable to return to the AI agent using **Enter key and value** mode:
   - Key: the name as the AI agent will reference it (e.g., `patient_first_name`)
   - Value: use variable picker to select from HTTP node output

The keys and values entered in step 6 are what map back to your actions in AI Agent Studio.

> **Unresolved — verify in the UI, do not assume.** An earlier version of this playbook recorded **Notify AI Agent** as a radio button already enabled by default under **Last Execution Status**. The tenant owner describes it instead as a selection you make under **Notification Settings**, after enabling the **Notify** parameter on the **Last Execution Status** row. Both can be true at once (the option may be pre-selected once **Notify** is enabled), but that has not been confirmed. Walk steps 3–5 and confirm the state of each control on screen.
>
> The public Flow Settings documentation ([help.webexconnect.io/docs/flow-settings](https://help.webexconnect.io/docs/flow-settings)) documents only the generic **Success** / **Error** / **Incomplete** outcomes and HTTP **Outcome-based Notifications**. It does not mention **Last Execution Status**, a **Notify** parameter, **Notification Settings**, or **Notify AI Agent** — so it neither confirms nor contradicts either description.

### One Key Set Per Flow

Because outcomes live in Flow Settings and not on the canvas, a flow has exactly **ONE** set of return key/values. Every path through the flow returns the same keys — you **cannot** return a different payload per Branch leg.

If different branches need to report different results:

1. Converge the Branch legs back onto a single path before the **End** node
2. On each leg, set a status or error variable (e.g., `status` = `found` / `not_found`, or `error_reason` = `no_appointments`)
3. Return that variable through the single key set configured in Flow Outcomes

The AI agent then reads the status/error key to decide what to say. Any design that assumes per-branch outcome payloads is not buildable in Connect.

---

## 7. Configure AI Agent Event (Sample JSON)

Every action requires a sample JSON payload registered in the **Webex Connect** flow's **Start node** (in the "Provide sample JSON" field of the AI Agent trigger configuration). This tells Connect what shape of data to expect from the agent.

Format example for `lookup_patient`:
```json
{
  "phone_number": "5551234567"
}
```

One key per slot entity the action declares. Use realistic example values.

**Nothing in Connect has to be typed to match the AI Agent Studio action name.** The Start node's event auto-populates once **Trigger category** is set to **AI Agent** (see §2) — there is no event-name field to hand-enter and no string that must match the action name character for character. The only names you author are the sample-JSON keys (which mirror the action's slot entities) and the Flow Outcomes return keys (§6).

---

## 8. Variable Naming Rules

Connect documents **two different naming rules**, depending on which kind of variable you are creating. They are not interchangeable — do not apply one to the other.

### HTTP Request node output variables

Allowed: **alphabets, numbers, underscores, hyphens, and spaces** — "You can only use alphabets, numbers, underscores, hyphens, and spaces in the variable names." ([help.webexconnect.io/docs/http-request-node](https://help.webexconnect.io/docs/http-request-node))

Use lowercase underscores consistently:
- `patient_first_name` ✅
- `patientFirstName` — avoid
- `patient-first-name` — allowed but inconsistent

### Custom flow variables

Allowed: **alphanumeric only** — "Variable name can have Alpha Numeric values(for e.g; channel13). We do not support the use of special characters in the variable name." ([help.webexconnect.io/docs/create-custom-variable-webexconnect](https://help.webexconnect.io/docs/create-custom-variable-webexconnect))

Cisco's own worked example is `channel13` — letters and digits, no separator. The underscore style recommended above is documented for HTTP **output** variables only; it is **not** documented as permitted for custom variables, and whether an underscore is accepted there has not been verified against a tenant. Name a custom variable so it satisfies the stricter rule and is therefore valid under both — `retryCount`, `maxRetryCount`, `oncallNumber` rather than `retry_count`, `max_retry_count`, `oncall_number`.

---

## 9. Common URL Patterns

| Operation | URL Pattern |
|-----------|-------------|
| Lookup by phone | `/{table}?phone_number=eq.$(n2.aiAgent.phone_number)` |
| Fuzzy search by name | `/{table}?name=ilike.*$(n2.aiAgent.search_term)*` |
| Filter by date range | `/{table}?date_col=gte.$(n2.aiAgent.date)T00:00:00&date_col=lte.$(n2.aiAgent.date)T23:59:59` |
| Filter + limit | `&order=date_col.asc&limit=3` |
| Hardcoded UUID filter | `/{table}?location_id=eq.{known-uuid}` |

---

## 10. Testing a Flow

Before wiring it to an AI agent action:

1. Use **curl** to test the raw Supabase URL with the same headers
2. Verify the response shape matches what your output variables expect
3. In Connect, use **Test Flow** (if available) or trigger via a test AI agent session

---

## 11. Known Gotchas

| Issue | Fix |
|-------|-----|
| Variable arrives empty in URL | Variable not substituted — use variable picker, never type manually |
| `401` error | Auth headers missing or `Bearer ` space missing before key |
| `400` error | Wrong filter column (e.g., `id=eq.` when you need `phone_number=eq.`) |
| `406` error | Single-object Accept header used but query returned 0 rows |
| Flow Outcomes variables show as literal strings | Reported after switching to Enter JSON mode; switching back to Enter key and value mode is the recorded workaround. **Unattributed observation, and Cisco documents the JSON option as supported — read the UNRESOLVED note in §6 before acting on this row (open item O1).** |
| Array response breaks output variables | Remove `Accept: application/vnd.pgrst.object+json` header |
| 30-second timeout in agent flow | Prohibited node in use (Delay, Social Hour Check, Receive, Call Workflow) — these risk exceeding the 30-second execution time limit |
