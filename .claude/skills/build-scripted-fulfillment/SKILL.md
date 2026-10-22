---
name: build-scripted-fulfillment
description: |
  Build fulfillment logic for a SCRIPTED AI agent intent. Handles the inline
  fulfillment pattern for digital channels (Data Parser → Branch on template_key
  → HTTP Request → Evaluate → Channel Reply → loop) and the Custom Event pattern
  for voice channels (Custom Event response → Flow Designer HTTP → state_update).
  Use for: wiring up the HTTP call and response handling when a scripted agent's
  intent needs to call an external API.
  NOT for: autonomous agent actions (build-action), configuring the agent (configure-scripted-agent),
  the conversation loop around it (build-digital-inbound).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [intent-name]
---

# Build Scripted Fulfillment Workflow

> This skill is for **SCRIPTED** agents only. For autonomous agent actions, use `build-action`.

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/reference/ai-agent-studio-scripted.md` — specifically the Fulfillment section
2. Read `docs/reference/webex-connect.md` for Connect flow conventions
3. Read `docs/reference/db-integration.md` for the user's DB patterns
4. Read this skill's `reference.md` for the quick-reference cheat sheet

### Voice channel — additional required reads

If the user's channel is **voice** (or both digital + voice), you MUST also load these Flow Designer docs. The voice fulfillment path uses Flow Designer activities that are NOT covered by the docs above.

5. Read `docs/reference/flow-designer-essentials.md` — covers SetVariable, Play Message, Play Music, Queue Contact, variable types
6. Read the following individual activity files from `docs/reference/flow-designer-activities/`:

   - `docs/reference/flow-designer-activities/parse.md`
   - `docs/reference/flow-designer-activities/http-request.md`
   - `docs/reference/flow-designer-activities/http-connector.md`
   - `docs/reference/flow-designer-activities/custom-connectors.md`
   - `docs/reference/flow-designer-activities/condition.md`
   - `docs/reference/flow-designer-activities/case.md`
   - `docs/reference/flow-designer-activities/virtual-agent-v2.md`

7. Read `docs/reference/flow-designer-patterns.md` — specifically the "Scripted Agent Fulfillment Pattern" section.

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What node type branches on `template_key` to route to the correct fulfillment handler? (from `ai-agent-studio-scripted.md`)
- What HTTP headers are required for the user's DB backend? (from `db-integration.md`)

If the channel is voice, also confirm:
- What fields does the Parse activity require? (from `flow-designer-activities/parse.md`)
- What is the Condition activity's limitation when comparing to empty strings? (from `flow-designer-activities/condition.md`)
- What variable type does VAV2's `eventData` field require, and why does `event_data_string` exist? (from `flow-designer-patterns.md` § Scripted Agent Fulfillment Pattern)

If you cannot answer the applicable questions, you skipped Step 1. Go back and read the docs.

## Step 2: Confirm prerequisites

Before building fulfillment, verify:

- The scripted agent exists in AI Agent Studio with the intent configured
- The intent has a **template key** on its completion response (this is what the flow branches on)
- You know what API/database call the intent requires
- You know what entity values the intent collects (these are the API inputs)
- You know the channel: **digital** (inline fulfillment) or **voice** (Custom Event)

Ask the user:

> "Which intent needs fulfillment, and what's the template key on its response? What API endpoint does it call?"

## Step 3: Determine the channel pattern

| Channel | Fulfillment Pattern | Build Where |
|---------|-------------------|------------|
| **Digital** (SMS, WhatsApp, Chat, Email) | Inline in the conversation flow: Branch on template_key → HTTP → send response | Webex Connect |
| **Voice** | Custom Event response → Flow Designer handles fulfillment → state_update back to agent | WxCC Flow Designer |
| **Both** | Build both patterns — digital first, then voice | Both platforms |

---

## DIGITAL CHANNEL FULFILLMENT

### Step 4d: Identify where to add fulfillment in the conversation flow — `[Webex Connect]`

The digital inbound conversation flow should already exist (built via `build-digital-inbound`). Fulfillment is added **between the AI Agent node and the Channel Reply node**.

Current flow:
```
AI Agent → Channel Reply → Receive → [loop]
```

After adding fulfillment:
```
AI Agent → Data Parser → Branch → [fulfillment path] → Channel Reply → Receive → [loop]
                                → [default path] → Channel Reply → Receive → [loop]
```

### Step 5d: Add a Data Parser node — `[Webex Connect → Data Parser node]`

1. Drag a **Data Parser** node onto the canvas after the AI Agent node
2. Set **Input**: select the AI Agent node's **SessionMetadata** output variable
3. Set **Parse Format**: JSON
4. Add an output variable:
   - **Variable Name**: `template_key`
   - **JSON Path**: `$.model_state.template_key`
5. Wire the AI Agent node's **onSuccess** output to this Data Parser node

This extracts the template_key that tells you which intent/response just fired.

### Step 6d: Add a Branch node — `[Webex Connect → Branch node]`

1. Drag a **Branch** node after the Data Parser
2. Wire the Data Parser's output to the Branch node
3. Add conditions — one per intent that needs fulfillment:

| Condition | Operator | Value | Route To |
|-----------|----------|-------|----------|
| `$(nX.DataParser.template_key)` | equals | `booking_confirmed` | Fulfillment path for booking |
| `$(nX.DataParser.template_key)` | equals | `status_result` | Fulfillment path for status lookup |
| Default | — | — | Direct response path (no fulfillment) |

Use the **variable picker** to select the Data Parser output — never type variable references manually.

### Step 7d: Build the fulfillment path — `[Webex Connect → HTTP Request node]`

For each Branch condition that requires an API call:

1. Drag an **HTTP Request** node
2. Configure:
   - **Method**: GET / POST / PATCH / DELETE (based on intent purpose)
   - **URL**: Your API endpoint with entity values from the AI Agent's SessionMetadata
   - **Headers**: Standard headers for your backend (see `reference.md`)

**Accessing entity values from the scripted agent:**

Entity values collected by the agent are in the SessionMetadata. Extract them via additional Data Parser outputs:

- JSON Path: `$.model_state.entities.<entity_name>.value`
- Example: `$.model_state.entities.phone_number.value` → `$(nX.DataParser.phone_number)`

Or add a second Data Parser node specifically for entity extraction if you need multiple values.

3. Configure **Output Variables**:
   - Click the **Output Variables** tab
   - Click **Import from Sample**, paste a sample JSON response into the Data Parser dialog, click **Parse**, select the key paths to extract under "Select key paths to be extracted", then click **Import** — rows auto-generate
   - Renaming output variables after parsing is not documented in official docs; use consistent field names in your sample JSON to avoid naming conflicts across nodes

### Step 8d: Add an Evaluate node — `[Webex Connect → Evaluate node]`

1. Drag an **Evaluate** node after the HTTP Request
2. Use it to format the user-facing response message from the API data
3. Build the response string using variables from the HTTP node:
   ```
   Your appointment is confirmed for $(nX.https.date) at $(nX.https.time). Confirmation number: $(nX.https.confirmation_number).
   ```

### Step 9d: Wire to Channel Reply and Receive — `[Webex Connect]`

1. Wire the Evaluate node to a **Channel Reply** node (sends the formatted response to the customer)
2. Wire the Channel Reply to an **Append Conversation** node (adds the response to the conversation history)
3. Wire to the **Receive** node (waits for the next customer message)
4. Wire the Receive node back to the **AI Agent** node (continues the conversation loop)

### Step 10d: Wire the default (no-fulfillment) path — `[Webex Connect]`

For the Branch node's **Default** output (intents that don't need fulfillment):

1. Wire directly to a Channel Reply node that sends the AI Agent's **TextResponse**
2. Wire to Receive → loop back to AI Agent

### Step 11d: Run a live test — `[Terminal / API Client]`

Test the actual API URL with real headers and entity values:

- Construct a curl command matching the HTTP Request node's configuration
- **Show the curl command to the user and ask if they want you to run it**
- Verify HTTP 200, response shape matches output variables, expected data present

### Step 12d: Present the fulfillment config to the user

Format for the user:

1. **Template key** being branched on
2. **Data Parser config** (SessionMetadata → template_key extraction)
3. **Branch conditions** (template_key values → routes)
4. **Entity extraction** (JSON paths for each entity value)
5. **HTTP Request config** (method, URL with entity placeholders, headers, output variables)
6. **Evaluate expression** (formatted response string)
7. **Wiring diagram** (node connections)
8. **Curl test result**

---

## VOICE CHANNEL FULFILLMENT

### Step 4v: Configure Custom Event response in AI Agent Studio — `[AI Agent Studio]`

1. Navigate to the intent's **Responses** section
2. Select the **Voice** channel
3. Add a response with type **Custom Event**
4. Set **Event Name** (e.g., `check_availability`)
5. Set **Payload** — include entity values the flow needs:
   ```json
   {
     "phone_number": "${entity.phone_number}",
     "date": "${entity.appointment_date}",
     "time": "${entity.appointment_time}"
   }
   ```

### Step 5v: Wire Flow Designer — `[WxCC Flow Designer]`

1. Open the call flow containing the **Virtual Agent V2** activity
2. VAV2 exits via its **ENDED** path when the agent raises a Custom Event. `VirtualAgentV2.StateEventName` contains the event name, and `VirtualAgentV2.MetaData` contains the payload.
3. Create these **flow variables** (Flow Designer → Variables panel):

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `event_name` | STRING | (empty) | State Event name to send back to agent |
| `event_data` | JSON | `{}` | Parsed API response |
| `event_data_string` | STRING | (empty) | Stringified event_data (VAV2 requires STRING) |
| `http_input` | STRING | (empty) | Parsed from MetaData — the Custom Event payload |

4. Wire the activity chain:

**Single intent:**
```
VirtualAgentV2 (ENDED) → Parse → HTTP Request → Condition → SetVariable (x2) → VirtualAgentV2 (resume)
```

**Multiple intents (add a Case activity after Parse):**
```
VirtualAgentV2 (ENDED) → Parse → Case (StateEventName)
  ├── "intent_a_exit" → HTTP Request A → Condition → SetVariable event_name = "intent_a_confirm_entry"
  ├── "intent_b_exit" → HTTP Request B → Condition → SetVariable event_name = "intent_b_confirm_entry"
  └── default → DisconnectContact
  [each success path] → SetVariable event_data_string = "{{ event_data }}" → VirtualAgentV2
  [each failure path] → PlayMessage (TTS error) → QueueContact
```

### Step 6v: Parse MetaData — `[WxCC Flow Designer → Parse activity]`

> **Source:** Configure per the field table in `flow-designer-activities/parse.md` (loaded in Step 1). The fields below must match what you read there.

The Parse activity extracts the Custom Event payload from `VirtualAgentV2.MetaData`:

| Field | Value |
|---|---|
| **Input Variable** | `{{VirtualAgentV2.MetaData}}` |
| **Content Type** | JSON |
| **Output Variable** | `http_input` |
| **Path Expression** | `$` (root — captures entire payload) |

The `http_input` variable now contains the JSON payload from the Custom Event (e.g., `{"phone_number":"+15551234567","date":"2026-05-10"}`). This becomes the HTTP Request body.

**If you need individual entity values** (for query parameters or URL interpolation), add additional output variables with specific paths:

| Variable Name | JSON Path |
|---------------|-----------|
| `phone_number` | `$.phone_number` |
| `date` | `$.date` |
| `time` | `$.time` |

### Step 7v: HTTP Request — `[WxCC Flow Designer → HTTP Request activity]`

> **Source:** Configure per the field tables in `flow-designer-activities/http-request.md`, `flow-designer-activities/http-connector.md`, and `flow-designer-activities/custom-connectors.md` (loaded in Step 1). The fields below must match what you read there. If any field name or default value differs from the loaded doc, use the doc's version.

**If calling a WxCC API** (Search, CC Configuration, etc.): use an **HTTP Connector** instead of manual auth headers. The connector manages OAuth tokens automatically. In the HTTPRequest activity, enable **Use Authenticated Endpoint**, select the connector, and enter only the **Request Path** (e.g., `/search`) — the connector supplies the base URL and auth.

**Alternative for external APIs with OAuth:** Use a **Custom Connector** (Control Hub → Contact Center → Connectors → Custom Connectors) for managed auth to third-party services like ServiceNow or Salesforce. Enable "Use Authenticated Endpoint" and select the custom connector — same usage pattern as the WxCC Connector but for external APIs.

**If calling an external API manually** (Supabase, custom backend, etc.): configure without a connector. Use the HTTP Request Activity field table from the loaded doc — key fields:

- **Use Authenticated Endpoint**: Off (unless using a connector)
- **Request URL**: Full API endpoint URL
- **Method**: GET / POST / PATCH / DELETE
- **Content Type**: Application/JSON
- **Response Timeout**: Use the default from the loaded doc — increase for slow APIs

**Query Parameters:** Add as key-value rows (click **Add New**). Use `{{variableName}}` for dynamic values from parsed entities.

**HTTP Request Headers:** Add as key-value rows. Standard headers for your backend (see `reference.md`).

**Request Body (POST/PATCH):** Enter raw JSON with `{{variableName}}` interpolation. Set Content Type to Application/JSON.

**Parse Settings:** Configure per the Parse Settings subsection in the loaded HTTP Request Activity doc. Key points:

- Content Type: JSON
- Output Variable: Flow variable name to receive parsed value
- Path Expression: JSONPath — always JSONPath regardless of response content type

All responses are normalized to JSON before path expression evaluation.

### Step 8v: Condition + State Event Resume — `[WxCC Flow Designer]`

Add a **Condition** activity to check success/failure:

> **Condition expression syntax:** Refer to `flow-designer-activities/condition.md` (loaded in Step 1) for the full operator list, limitations, and recommended patterns. Key points: use `{{variableName}}` with operators, numeric comparisons are most reliable, and empty string comparison has a documented limitation.

**On success — resume agent with result via State Event:**

1. Add a **SetVariable** activity: set `event_name` = `<intent>_confirm_entry` (e.g., `check_availability_confirm_entry`)
2. Add a second **SetVariable** activity: set `event_data_string` = `{{ event_data }}` (converts the JSON response to string)
3. Wire back to the **VirtualAgentV2** activity — it re-enters and sends the State Event to the agent

The VAV2 activity's properties must reference these variables:
- **eventName**: `{{ event_name }}`
- **eventData**: `{{ event_data_string }}`

The agent receives the data and can use `${eventStore.<key>}` in its response templates to deliver the result to the caller.

**On failure — two options:**

*Option A: Escalate to human*
Wire to PlayMessage (TTS error) → QueueContact → PlayMusic (hold).

*Option B: Re-prompt via state_update*
Set `event_data_string` to a state_update payload that clears the slot:

```json
{
  "intent": "book_appointment",
  "slots": {
    "time": ""
  }
}
```

Setting a slot to `""` clears it and triggers the agent to re-prompt for that value. Wire back to VAV2 to resume.

> **Full pattern reference:** See `docs/reference/flow-designer-patterns.md` § Scripted Agent Fulfillment Pattern for the complete State Event resume mechanism, multi-event routing, and `CustomAIAgentInteractionOutcome` analytics variable.
> **Reference flows:** Import from [wxcc-ai-agent-scripted-appointment](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-appointment) (4-intent multi-event) or [wxcc-ai-agent-scripted-tracking](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-tracking) (single-intent with outcome tracking). See `docs/examples/flow-designer-scripted-*.env.template` for the UUID replacement list.

### Step 9v: Present the fulfillment config to the user

Format for the user:

1. **Custom Event config** (event name, payload JSON with entity variables)
2. **Flow Designer wiring** (ENDED path → Parse MetaData → Case on StateEventName → HTTP → Condition → SetVariable event_name/event_data_string → resume VAV2)
3. **Flow variables to create** (event_name STRING, event_data JSON, event_data_string STRING, http_input STRING)
4. **HTTP Request config** (URL, method, headers, body using http_input, output variable paths)
5. **State Event resume config** (event_name value for each intent, event_data_string wiring)
6. **Error path** (PlayMessage TTS → QueueContact for failures)
7. **Curl test result**
8. **Org-specific values to replace** — list every UUID/name the user must customize:

```
# Values to replace before this flow works in your org:
VIRTUAL_AGENT_ID=<your AI Agent ID from AI Agent Studio>
VIRTUAL_AGENT_NAME=<your agent display name>
QUEUE_ID=<your escalation queue ID from Control Hub>
QUEUE_NAME=<your queue display name>
```

---

## CRITICAL REMINDERS

- **NEVER type variable references manually** in Webex Connect — always use the variable picker
- **SessionMetadata is scripted-only on digital** — autonomous agents don't have this output
- **Data Parser node is required** to extract template_key and entity values from SessionMetadata JSON
- **Custom Events are voice-only** — digital channels use the inline Branch pattern instead
- **state_update can clear slots** by setting them to empty string `""` — this is the re-prompting mechanism
- **Evaluate node** formats the user-facing message — do NOT send raw API JSON to customers
- **Append Conversation** is required after Channel Reply on digital — without it, the conversation history breaks
- **Prohibited nodes**: Delay, Social Hour Check, Receive Node, Call Workflow — these risk exceeding the 30-second execution time limit
- **Flow Designer Set Variable has no string functions** — `substring()`, `replace()`, `trim()` do not work. The literal text is appended to the variable value. Design API calls to accept raw variable formats. (Confirmed in `flow-designer-essentials.md`)
- **Flow Designer Condition cannot compare to `""`** — use numeric checks instead (e.g., `{{resultCount}} > 0`). See `flow-designer-activities/condition.md` for the full limitations table and workarounds.

## ANTI-HALLUCINATION GUARD

Every field name, header value, variable syntax, and node configuration detail in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
