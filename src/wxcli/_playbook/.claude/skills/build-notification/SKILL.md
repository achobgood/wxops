---
name: build-notification
description: |
  Build a Webex Connect flow for a multi-channel outbound notification. Supports
  SMS, Email, RCS, Apple Messages, WhatsApp, and multi-channel routing with
  automatic fallback: webhook trigger, optional DB lookup, channel selection,
  delivery nodes, failure handling, and fallback paths.
  Use for: sending messages TO customers via one or more digital channels,
  triggered by external webhook events.
  NOT for: voice calls with TTS (build-outbound-flow), inbound conversations (build-digital-inbound),
  AI agent actions (build-action).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [flow-name]
---

# Build Notification Workflow

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read this skill's `reference.md` for the cross-channel quick-reference cheat sheet
2. Read `docs/playbooks/webhook-triggers.md` for Start node webhook setup
3. Read the channel-specific playbook(s) based on the user's channel choice:
   - SMS: `docs/playbooks/outbound-sms.md`
   - Email: `docs/playbooks/outbound-email.md`
   - Voice: `docs/playbooks/outbound-voice.md`
   - RCS: `docs/playbooks/outbound-rcs.md`
   - Apple Messages: `docs/playbooks/outbound-apple-messages.md`
   - WhatsApp: `docs/playbooks/outbound-whatsapp.md`
   - Multi-channel: `docs/playbooks/multi-channel-routing.md`
4. Read the channel-specific reference doc(s) for detailed node configuration:
   - SMS/MMS: `docs/reference/connect-sms.md`
   - Email: `docs/reference/connect-email.md`
   - RCS: `docs/reference/connect-rcs.md`
   - Apple Messages: `docs/reference/connect-apple-messages.md`
   - WhatsApp: `docs/reference/connect-whatsapp.md`
   - Multi-channel: `docs/reference/connect-multi-channel.md`
5. (If DB lookup needed) Read `docs/reference/db-integration.md` for DB patterns
6. (If DB lookup needed) Read `docs/reference/webex-connect.md` for HTTP Request node details
7. Read `docs/templates/notification-config.md` for the output format

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What method and content type must the Start node webhook be configured for? (from `webhook-triggers.md`)
- For the selected channel: what is the delivery node type and its required configuration fields? (from the channel-specific playbook)

If you cannot answer both, you skipped Step 1. Go back and read the docs.

## Step 2: Gather requirements

Ask the user ONE question at a time. Confirm all answers before proceeding.

### Required information:

1. **Flow name** (lowercase-hyphens, e.g., `order-ready-notification`)
2. **What triggers it** (one sentence: "A webhook fires when an order status changes to 'ready'")
3. **Webhook payload fields** -- what data the external system sends (e.g., `order_id`, `customer_phone`, `location_name`)
4. **Does it need a DB lookup before sending?** (Yes = HTTP Request node between Start and delivery; No = all data comes in the webhook payload)
5. **Which channel(s)?**
   - Single channel: SMS, Email, Voice, RCS, Apple Messages, or WhatsApp
   - Multi-channel: route to customer's preferred channel with fallback

### Channel-specific questions:

**If SMS:**
- Message content (plain text, max 1,024 chars)
- Contains emoji or non-Latin characters? (affects encoding — Unicode vs GSM-7)

**If Email:**
- Subject line
- Email Type: Text, HTML, or Template?
- Attachments needed?

**If Voice:**
- What the recipient hears (TTS message)
- TTS format: Plain Text or SSML? **Recommend SSML** for order/confirmation numbers, currency, or paging.
- Destination: regular phone number or Webex Calling paging group DID?

**If RCS:**
- Message format: Text, Rich Card, or Carousel Card?
- If Rich Card: title, description, media URL, suggestion buttons
- Include SMS fallback? (almost always yes)

**If Apple Messages:**
- Does the customer have an active Apple Messages session? (required — cannot cold-send)
- Message format: Rich Link, List Picker, or Time Picker?
- Include SMS fallback? (required)

**If WhatsApp:**
- Has the customer opted in to receive WhatsApp messages? (Required by Meta policy — not optional)
- Template message or session message? (Template for proactive notifications — works outside 24-hour window)
- If template: which approved template? Template name/ID?
- If template: header parameters? Body parameters? **Always use sequential `{{1}}`, `{{2}}` placeholders — never named `{{variable_name}}` placeholders**
- If session: message type? (Text, Media, Interactive)
- Contains rich content? (Images, documents, list messages, reply buttons)

**If Multi-channel:**
- Which channels to support? (SMS, Email, Voice, RCS, Apple Messages, WhatsApp)
- What's the customer preference field in the DB?
- What's the default fallback channel? (usually SMS)

### For all channels:
- **Failure handling**: what should happen on send failure? (end flow / log to DB / fallback to SMS)

## Step 3: Configure the Start Node -- `[Webex Connect → Start node]`

Follow the webhook setup from `docs/playbooks/webhook-triggers.md`:

1. Navigate to **Services** > select your service > **Flows**
2. Click **Create Flow**, name it (e.g., `order-ready-notification`), click **Create**
3. Double-click the green **Start** node
4. Select trigger: **Webhook**
5. Create a new webhook event, enter a name
6. Paste sample JSON payload generated from the user's webhook fields:
   ```json
   {
     "field1": "example_value",
     "field2": "+15551234567"
   }
   ```
7. Click **PARSE** -- variables become available as `$(n1.inboundWebhook.fieldName)`
8. Save the configuration
9. Note the auto-generated webhook URL (visible after save)

## Step 4: (Conditional) Add HTTP Request Node -- `[Webex Connect → HTTP Request node]`

**Only if the user needs a DB lookup before sending.** Skip if all data arrives in the webhook payload.

Follow the HTTP Request pattern from `docs/reference/webex-connect.md`:

- Variable references come from the Start node: `$(n1.inboundWebhook.order_id)` -- NOT from `$(n2.aiAgent.entity_name)`
- Configure Method (GET for lookup), URL with filters, Headers, Output Variables
- Run a curl test against the user's database before proceeding

## Step 5: Channel selection decision point

### Single channel

Go directly to the channel-specific delivery step (Step 6).

### Multi-channel routing

Follow `docs/playbooks/multi-channel-routing.md`:

1. The HTTP Request from Step 4 must return `preferred_channel`, `phone`, `email`, `abcId`, `abc_session_active`
2. Add a **Branch** node on `$(nX.preferred_channel)`
3. Configure one branch per supported channel
4. Set "None of the above" default → SMS (universal fallback)
5. Wire each branch to its channel-specific delivery node (Step 6)

## Step 6: Configure channel-specific delivery node

**Channel checkpoint — answer from the channel playbook before proceeding:**

- **SMS:** What is the Destination Type field value? What Wait For setting? What US compliance requirement for long codes?
- **Email:** What field is auto-populated and cannot be typed manually? What Wait For setting?
- **RCS:** What node must precede the RCS Message node? What Branch condition determines RCS support?
- **Apple Messages:** What precondition is required before sending (cannot cold-send)? What Wait For setting?
- **WhatsApp:** What placeholder syntax do templates use — named or sequential? What error code for messages outside the 24-hour window?
- **Voice:** What two nodes are needed in sequence for an outbound call with TTS?

If you cannot answer for your selected channel, re-read the channel playbook from Step 1 before continuing.

Follow the corresponding playbook for the user's channel choice:

### SMS -- follow `docs/playbooks/outbound-sms.md`
- Configure SMS node: Destination (E.164), From Number, Message Type, Message body
- Set Wait For: Gateway Submit
- Wire ALL exit paths: onSuccess → End, onError → End (or log), onPolicyFail → End (or log), onTimeOut → End (or log)
- **10DLC reminder (US):** If sending to US numbers on a long code, 10DLC brand/campaign registration is required. Unregistered numbers receive error 7281 and messages are rejected.
  - ⚠️ **Unverified observation:** the specific code **7281** for unregistered 10DLC is **not confirmed in official Cisco documentation**. The 10DLC registration requirement itself is documented; the error code mapped to it is not. Do not build Branch logic that matches on `7281` without confirming the code against a real rejected send on your tenant.

### Email -- follow `docs/playbooks/outbound-email.md`
- Configure Email node: Destination (Email ID), Subject, Email Type, Message body
- From Email is auto-populated from asset config (cannot be typed manually)
- Set Wait For: Gateway Submit
- Wire exit paths: onSuccess → End, onError → End (or log)

### Voice -- follow `docs/playbooks/outbound-voice.md`
- Configure Call User node: Destination Type = `msisdn`, Destination (E.164 or paging DID), From Number
- Configure Voice Node Group → Play node (TTS): Azure Neural, Language, Voice, Input Format
- Wire call failure paths: `onbusy`, `onnoanswer`, `onreject` → End (or log) — these Call User event names are all-lowercase on the platform; type them exactly as shown

### RCS -- follow `docs/playbooks/outbound-rcs.md`
- Add RCS Capability node (Force Refresh: false)
- Add Branch node: `rcs.enabled == true AND rcs.version == "up2"`
- Configure RCS Message node: Rich Card (or Text/Carousel Card)
- Set Wait For: Gateway Submit
- Wire ALL RCS Message exit paths: onSuccess → End, onSubmit → End, onDeliveryReportSuccess → End, onError → SMS fallback, onDeliveryReportFail → SMS fallback (or log), onPolicyFail → SMS fallback (or log), onTimeout → SMS fallback (or log)
- Wire SMS fallback from Branch "None of the above" AND Capability onError

### Apple Messages -- follow `docs/playbooks/outbound-apple-messages.md`
- Add Branch node: check `abc_session_active == true` from DB lookup
- Configure Apple Messages node: Destination Type = `AbcUser Id`, Destination = `abcId`, Message Type (Rich Link / List Picker / Time Picker)
- Wire SMS fallback from Branch "None of the above" AND Apple Messages onError AND onPolicyFail

### WhatsApp -- follow `docs/playbooks/outbound-whatsapp.md`
- **Opt-in check:** Confirm the customer has opted in to receive WhatsApp messages (Meta policy requirement — not optional)
- Configure WhatsApp node: Destination (WA ID, E.164), Message Type (Template or Text/Media/Interactive)
- If Template: select approved template, map header and body parameters. **Use sequential `{{1}}`, `{{2}}` placeholders only** — named `{{variable_name}}` placeholders do not exist in WhatsApp templates
- If Text/Media: compose message (max 4,096 chars for text), configure media URL for attachments
- Set Wait For: Gateway Submit
- Wire ALL exit paths: onSuccess → End, onSubmit → End, onDeliveryReportSuccess → End, onError → End (or log), onPolicyFail → End (or log), onTimeout → End (or log), onDeliveryReportFail → End (or log)

## Step 7: Wire failure and fallback paths

For each channel, wire the failure exits:

| Channel | Failure Exits | Recommended Wiring |
|---------|--------------|-------------------|
| SMS | onError, onPolicyFail, onTimeOut | End (or log via HTTP Request) |
| Email | onError, onInvalidData, onPolicyFail, onTimeout | End (or log) |
| Voice (Call User) | `onbusy`, `onnoanswer`, `onreject`, `oncallfail` (all-lowercase on the platform), `onError`, `onPolicyFail`, `onExpiry` (mixed case) | End (or SMS fallback) |
| RCS | Capability onError, Branch "No", RCS Message onError, onDeliveryReportFail, onPolicyFail, onTimeout | SMS fallback → End |
| Apple Messages | Branch "No session", onError, onPolicyFail | SMS fallback → End |
| WhatsApp | onError, onPolicyFail, onTimeout, onDeliveryReportFail | End (or SMS fallback) |

For multi-channel: wire EVERY channel's onError to the SMS fallback node.

## Step 8: Save and Make Live -- `[Webex Connect]`

1. Click **Save** in the top toolbar
2. Click **Make Live** -- the webhook URL only accepts requests when the flow is live
3. Copy the webhook URL from the Start node (double-click Start after saving)

## Step 9: Test with curl -- `[Terminal / API Client]`

Generate a curl command for testing:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {service_key}" \
  -d '{"field1": "value1", "field2": "+15551234567"}' \
  "https://{webhook-url}"
```

Verify:
- Response code `1002` (queued)
- Message delivered to the correct channel
- Dynamic variables resolved (not literal `$(nX.var)` text)
- Fallback fires correctly when primary channel fails (test by using an invalid destination for RCS/Apple)

## Step 10: Generate the notification config document

Use the template from `docs/templates/notification-config.md`. Fill in all sections:

1. Flow Name & Purpose
2. Webhook Payload (sample JSON with field descriptions)
3. Webhook URL (user fills in after Make Live)
4. HTTP Request Node (if applicable)
5. Channel Configuration (per-channel node settings)
6. Message Content (text, HTML, rich card, TTS — whatever applies)
7. Failure Handling (exit path wiring per channel)
8. Fallback Configuration (SMS fallback for RCS/Apple/multi-channel)
9. Test Command (curl ready to copy-paste)
10. Integration Notes (how to trigger from app/database)

## Step 11: Present to user

Format the config for direct copy-paste into Webex Connect. Show the complete flow diagram appropriate to the channel(s):

**Single channel (SMS example):**
```
Start (Webhook: order_id, customer_phone)
  → HTTP Request (GET order details)
    → onSuccess → SMS (destination, from, message)
      → onSuccess → End
      → onError → Error Log (HTTP POST) → End
      → onPolicyFail → End
      → onTimeout → End
    → onError → Error Log (HTTP POST) → End
```

**Multi-channel:**
```
Start (Webhook: customer_id, ...)
  → HTTP Request (lookup customer: preferred_channel, phone, email, abcId)
  → Branch (preferred_channel)
    → "sms"   → SMS → End
    → "email" → Email → End
    → "voice" → Call User → Voice Node Group [Play TTS] → End
    → "rcs"   → RCS Capability → Branch → RCS Message (or SMS fallback) → End
    → "apple" → Branch (session?) → Apple Messages (or SMS fallback) → End
    → "whatsapp" → WhatsApp (Template or session) → End
    → default → SMS → End
```

Remind the user:
- The webhook URL is only active when the flow is **Made Live**
- For production: configure webhook authentication (service key or JWT)
- For DB-triggered webhooks: see `docs/playbooks/webhook-triggers.md` Section 10 for DB trigger patterns

---

## CRITICAL REMINDERS

- **NEVER type variable references manually** -- always show the format and tell the user to use the variable picker
- **Webhook variables**: `$(n1.inboundWebhook.{fieldName})` -- NOT `$(n2.aiAgent.{entity_name})`
- **No Flow Outcomes**: notification flows have no AI agent to return data to
- **No Receive node**: notification flows use Start node with Webhook, not Receive with AI Agent Event
- **No AI Agent Studio**: notification flows are self-contained in Connect
- **Wait For: Gateway Submit** for all messaging channels in agent flows
- **RCS requires capability check** before every send -- never skip it
- **Apple Messages requires active session** -- always wire SMS fallback
- **WhatsApp template required outside 24-hour window** -- free-form messages fail with error 7710
- **WhatsApp template parameters are sequential** (`{{1}}`, `{{2}}`), never named (`{{variable_name}}`). Do not use named placeholders even in drafts.
- **Template approval takes 24-72 hours** -- plan ahead
- **Opt-in required for WhatsApp template messages** -- always confirm with user before building WhatsApp flows. This is a Meta policy requirement, not optional.
- **Error logging POST requests** to PostgREST must include `Prefer: return=representation` header per `db-integration.md`
- **10DLC registration required (US)** -- SMS to US numbers on long codes requires 10DLC brand/campaign registration (error 7281 if missing — ⚠️ **unverified observation**, the code `7281` is not confirmed in official Cisco documentation; the registration requirement is)
- **E.164 format required** for phone numbers: `+` and country code
- **SMS is the universal fallback** -- every multi-channel flow should have it

## ANTI-HALLUCINATION GUARD

Every field name, header value, variable syntax, node name, and configuration detail in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
