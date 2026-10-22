---
name: build-outbound-flow
description: |
  Build a Webex Connect flow for an outbound voice call with TTS. Creates a
  webhook-triggered flow that dials a phone number (or paging group DID) and
  plays a text-to-speech message: Start, Call User, Voice Node Group, and Play nodes.
  Use for: voice-only outbound dialing — automated calls, paging groups, TTS alerts.
  NOT for: SMS/Email/WhatsApp/RCS notifications (build-notification), inbound voice IVRs (design-flow),
  AI agent actions (build-action).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [flow-name]
---

# Build Outbound Flow Workflow

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read this skill's `reference.md` for the quick-reference cheat sheet
2. Read `docs/playbooks/outbound-voice.md` for Call User, Voice Node Group, Play/TTS configuration
3. Read `docs/playbooks/webhook-triggers.md` for Start node webhook setup
4. Read `docs/templates/outbound-flow-config.md` for the output format
5. (If paging group destination) Read `docs/playbooks/webex-calling-paging.md`
6. (If DB lookup needed) Read `docs/reference/webex-connect.md` for general Connect flow conventions
7. (If DB lookup needed) Read `docs/reference/db-integration.md` for DB query patterns

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What is the node sequence for an outbound voice call (which node dials, which node plays audio)? (from `outbound-voice.md`)
- What method and content type must the Start node webhook be configured for? (from `webhook-triggers.md`)

If you cannot answer both, you skipped Step 1. Go back and read the docs.

## Step 2: Gather requirements

Confirm with the user before proceeding:

- **Flow name** (lowercase-hyphens, e.g., `order-ready-notification`)
- **What triggers it** (one sentence: "A webhook fires when an order status changes to 'ready'")
- **Webhook payload fields** -- what data the external system sends (e.g., `order_id`, `customer_phone`, `location_name`)
- **Does it need a DB lookup before calling?** (Yes = HTTP Request node between Start and Call User; No = all data comes in the webhook payload)
- **Destination type**: regular phone number (MSISDN) or Webex Calling paging group DID
- **What the recipient hears** -- the TTS message in plain language
- **TTS format preference**: Plain text (simpler, 3,000 char limit) or SSML (richer control, 6,000 char limit). **Recommend SSML** when: paging group, order/confirmation numbers, currency values, or pauses/emphasis needed.
- **Call failure handling**: what should happen on `onbusy`, `onnoanswer`, `onreject` (end flow? log failure to DB? retry via app layer?)
- **Answering Machine Detection**: needed or not? (Default: off)

## Step 3: Configure the Start Node -- `[Webex Connect → Start node]`

1. Navigate to **Services** > select your service > **Flows**
2. Click **Create Flow**, name it (e.g., `order-ready-notification`), click **Create**
3. Double-click the green **Start** node
4. In the trigger configuration, select **Webhook**
5. Create a new webhook event or select an existing one
6. Enter a name for the webhook (e.g., `order_ready`)
7. In the **PROVIDE SAMPLE INPUT** area, paste a sample JSON payload generated from the user's webhook fields:
   ```json
   {
     "order_id": "ORD-4521",
     "customer_phone": "+15551234567",
     "location_name": "Main Street Store"
   }
   ```
8. Click **PARSE** -- Connect extracts field names and makes them available as `$(n1.inboundWebhook.fieldName)` variables
9. Save the configuration
10. **Note the auto-generated webhook URL** (visible after save by double-clicking the Start node). The flow must be Made Live before the URL accepts requests.

## Step 4: (Conditional) Add HTTP Request Node -- `[Webex Connect → HTTP Request node]`

**Only if the user needs a DB lookup before placing the call.** Skip this step if all data arrives in the webhook payload.

This follows the same HTTP Request node pattern as `build-action` Steps 4-8, but with different variable sources:

- Variable references come from the **Start node webhook payload**: `$(n1.inboundWebhook.order_id)` -- NOT from `$(n2.aiAgent.entity_name)`
- The URL uses webhook payload fields as filter parameters
- Output variables from this node feed into the Play node's TTS text

### HTTP Method

| Goal | Method |
|------|--------|
| Look up / fetch details | GET |
| Log or create a record | POST |

### URL

Use the same PostgREST (or backend-specific) filter syntax from `docs/reference/db-integration.md`:

```
https://{api-base-url}/{table}?{column}=eq.$(n1.inboundWebhook.order_id)
```

### Headers

Configure headers appropriate to the user's backend API (see `reference.md` or `docs/reference/db-integration.md`).

### Output Variables

1. Paste a sample JSON response into the Parse field and click **Parse**
2. Rename `id` to a descriptive name (e.g., `order_id`, `customer_id`)
3. Response path: `$.field_name` (single object) or `$[0].field_name` (array first element)

### Curl Test

Run a live test against the user's database before proceeding:

```bash
curl -s \
  -H "Authorization: Bearer {api_key}" \
  -H "Content-Type: application/json" \
  "{api-base-url}/{table}?{filter}"
```

Verify HTTP 200 and expected response shape.

## Step 5: Add the Call User Node -- `[Webex Connect → Call User node]`

1. Drag a **Call User** node onto the canvas (NOT "Send Voice" -- deprecated in v5.4.x)
2. Wire: Start → [HTTP Request if present] → Call User
3. Configure (from `outbound-voice.md` and `reference.md`):

| Field | Value |
|-------|-------|
| **Destination Type** | `msisdn` |
| **Destination** | Variable picker: `$(n1.inboundWebhook.customer_phone)` -- OR hardcoded paging group DID in E.164 format (e.g., `+15557500`) |
| **From Number** | Select a provisioned voice-enabled number from the dropdown, or select **Dynamic** and use a variable |

4. (Recommended) Set **Expiry Time** -- number of seconds before the request expires
5. (Optional) Set **Correlation ID** for tracking

## Step 6: Configure the Voice Node Group -- `[Webex Connect → Voice Node Group]`

The Voice Node Group auto-creates when the Call User node is added. All voice interaction nodes must live inside it.

### If AMD is needed:

1. Open Voice Node Group **Settings**
2. Enable **Answering Machine Detection**
3. Configure a prompt to play during detection (supports Pre-recorded, Upload File, URL, or TTS; AMD TTS has a **2,000-character limit** — different from Play node limits)
4. Wire outcomes:
   - **Success (green)** → Play node (human answered)
   - `onAnsweringMachine` → End (or a separate Play node for a voicemail message) — fires as the **default** outcome under the Success edge; when detection is ambiguous, the system assumes machine
   - `onCallDrop` → End (call dropped during AMD detection)

### If AMD is not needed:

Leave settings as default. The `onAnswer` exit from Call User automatically enters the Voice Node Group.

## Step 7: Configure the Play Node (TTS) -- `[Webex Connect → Voice Node Group → Play node]`

1. Drag a **Play** node inside the Voice Node Group
2. Wire: Call User `onAnswer` → Voice Node Group → Play
3. Configure TTS settings (from `outbound-voice.md`):

| Setting | Value |
|---------|-------|
| **TTS Processor** | Azure (only supported engine in Connect) |
| **Voice Type** | Neural (Standard is deprecated) |
| **Language** | Select from list (e.g., English US) or "Dynamic" |
| **Voice** | Azure Neural voice name (e.g., `AriaNeural`, `GuyNeural`) or Dynamic |
| **Input Format** | **Plain Text** or **SSML** |

4. Enter the TTS message text using the **variable picker** for dynamic values.

### Generate TTS text from the user's description:

**Plain Text variant:**
```
Hello. Your order $(n3.order_number) is ready for pickup at $(n3.location_name). Thank you.
```

**SSML variant:**
```xml
<speak>
  Hello. Your order number
  <say-as interpret-as="characters">$(n3.order_number)</say-as>
  is ready for pickup at $(n3.location_name).
  <break time="500ms"/>
  Thank you for your business.
</speak>
```

**Paging variant (SSML, repeated for noisy environments):**
```xml
<speak>
  Attention.
  <break time="500ms"/>
  Order number <say-as interpret-as="characters">$(n3.order_number)</say-as>
  is ready for pickup.
  <break time="300ms"/>
  Customer name: $(n3.customer_name).
  <break time="500ms"/>
  Repeating. Order number <say-as interpret-as="characters">$(n3.order_number)</say-as>
  is ready for pickup.
</speak>
```

5. Wire Play `onSuccess` → End

## Step 8: Wire Call Failure Paths -- `[Webex Connect → Call User node exit paths]`

Wire the non-answer exit paths from the Call User node:

| Exit Path | Recommended Wiring |
|-----------|-------------------|
| `onAnswer` | Voice Node Group (already wired) |
| `onbusy` | End (or: HTTP Request to log failure, then End) |
| `onnoanswer` | End (or: HTTP Request to log failure, then End) |
| `onreject` | End (or: HTTP Request to log failure, then End) |
| `onError` | End (fires on invalid destination / missing digits) |
| `oncallfail` | End (network connectivity issue) |
| `onPolicyFail` | End (callback data > 2KB) |
| `onExpiry` | End (only if expiry time was set) |

Ask the user which failure paths they want to handle beyond simple termination:

- **End only** -- simplest, all failures terminate the flow
- **Log failures** -- wire failure paths to an HTTP Request node that POSTs a failure record to their DB, then End
- **Retry** -- out of scope for a single flow (Connect flows are stateless). Recommend implementing retry at the application layer: the DB/app tracks call status, and a scheduled job re-fires the webhook for failed calls.

## Step 9: (Conditional) Paging Group Validation -- `[Control Hub → Webex Calling]`

**Only if the destination is a Webex Calling paging group.** Skip for regular phone numbers.

1. Confirm paging group exists in Control Hub: **Services > Calling > Features > Paging Group**
2. Confirm a **DID is assigned** to the paging group (extensions are internal-only, not reachable from PSTN)
3. Warn about **originator enforcement**:

> "Paging groups have a configured list of Originators. When Connect dials the DID via PSTN, the caller is the Connect phone number, not a Webex Calling user. You need to test whether PSTN calls to the paging DID trigger the page. If they don't, workarounds include: adding the Connect number as an originator, using the Webex Calling Dial API, or routing through an Auto Attendant."

4. Recommend a **manual test call** to the paging DID from an external phone before building the flow
5. There is **no dedicated "trigger a page" API** -- the Paging Group APIs are administrative/provisioning only

## Step 10: Save and Make Live -- `[Webex Connect]`

1. Click **Save** in the top toolbar
2. Click **Make Live** -- the webhook URL only accepts requests when the flow is live
3. Copy the webhook URL from the Start node (double-click Start node after saving)

## Step 11: Test the Webhook End-to-End -- `[Terminal / API Client]`

Generate a curl command for testing:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {service_key}" \
  -d '{"order_id": "ORD-4521", "customer_phone": "+15551234567", "location_name": "Main Street Store"}' \
  "https://{webhook-url}"
```

Verify:
- Response code `1002` (queued)
- Phone rings at the destination number
- TTS plays correctly with dynamic variable values resolved (not literal `$(nX.var)` text)
- Call disconnects cleanly after TTS completes
- For paging: TTS broadcasts on target phones

If testing fails, check:
- Flow is Made Live
- Webhook URL is correct (copy from Start node)
- Service key is correct (Service dashboard > API tab)
- Destination number is in E.164 format
- Flow Debug panel (10 most recent executions with step traces)

## Step 12: Generate the outbound flow config document

Use the template from `docs/templates/outbound-flow-config.md`. Fill in all 10 sections:

1. Flow Purpose
2. Webhook Payload (sample JSON with field descriptions)
3. Webhook URL (user fills in after Make Live)
4. HTTP Request Node (if applicable -- method, URL, headers, output variables)
5. Call User Configuration (destination, from number, expiry)
6. TTS Message (full text with variable references)
7. Call Failure Handling (exit path wiring)
8. Paging Group Details (if applicable)
9. Test Command (curl ready to copy-paste)
10. Integration Notes (how to trigger from app/database)

## Step 13: Present to user

Format the config for direct copy-paste into Webex Connect. Show the complete flow diagram:

```
Start (Webhook: field1, field2, ...)
  → [HTTP Request (optional)]
  → Call User (destination, from)
    → onAnswer → Voice Node Group [ Play (TTS) ] → End
    → onbusy → End
    → onnoanswer → End
    → ...
```

Remind the user:
- The webhook URL is only active when the flow is **Made Live**
- For production: configure webhook authentication (service key or JWT)
- For DB-triggered webhooks: see `docs/playbooks/webhook-triggers.md` Section 10 for DB trigger patterns (application-level, Supabase Edge Functions, CDC, polling)

---

## CRITICAL REMINDERS

- **NEVER type variable references manually** -- always show the format and tell the user to use the variable picker in Connect
- **Webhook variables**: `$(n1.inboundWebhook.{fieldName})` -- NOT `$(n2.aiAgent.{entity_name})`
- **Call User node**: use "Call User" NOT "Send Voice" (deprecated in v5.4.x)
- **Destination format**: must be E.164 (`+15551234567`). Missing `+` or country code causes `onError`
- **TTS engine**: Azure Neural only in Connect. Cisco TTS is only in WxCC Flow Designer (different platform)
- **SSML Input Format**: if using SSML tags, set Input Format to "SSML" not "Plain Text" -- otherwise tags are read aloud literally
- **Voice Node Group**: all voice nodes (Play, Collect Input, IVR Menu) go INSIDE the group. Placing them outside causes silent failure
- **No Flow Outcomes**: there is no Flow Outcomes node to add — Flow Outcomes is a settings area (**Flow Settings** button on the Flow Builder page → **Flow Outcomes**), not a canvas node. Outbound flows have no AI agent to notify, so leave the **Notify AI Agent** path unconfigured
- **No Receive node**: outbound flows use the Start node with a Webhook trigger, not a Receive node with AI Agent Event
- **No AI Agent Studio**: outbound flows are self-contained in Connect. No action description, slot entities, or agent instructions
- **Paging originator enforcement**: MUST be tested before building. Call the paging DID from an external phone to verify it triggers the page
- **Webhook is async**: the HTTP response (code 1002) only confirms the request was queued, not that the call succeeded. Use Flow Debug to trace execution

## ANTI-HALLUCINATION GUARD

Every field name, header value, variable syntax, node name, and configuration detail in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
