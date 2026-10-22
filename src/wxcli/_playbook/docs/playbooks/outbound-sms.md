# Outbound SMS Playbook

<!-- ref-tag: outbound-sms-v2 -->

> **Values on this page are owned by `docs/reference/connect-sms.md`** (ref-tag `connect-sms-v2`). They are reproduced here so the build can be completed without leaving the page; the reference doc wins on any disagreement. Webhook trigger values are owned by `docs/playbooks/webhook-triggers.md`.

## Overview

This playbook covers how to build outbound SMS notifications in Webex Connect — webhook-triggered flows that send a text message to a phone number. This is the pattern for order confirmations, appointment reminders, status alerts, and two-factor codes.

**Key distinction from AI Agent flows:** Outbound SMS flows use the **Start node** (webhook trigger) and **SMS node** — NOT the Receive node / AI Agent Event / Flow Outcomes pattern documented in `connect-flows.md`.

For webhook setup, authentication, and testing: see `webhook-triggers.md`. This playbook assumes the webhook infrastructure is already configured.

---

## 1. Flow Structure

An outbound SMS flow follows this pattern:

```
Start (Webhook) → [Optional: HTTP Request] → SMS → End
```

### Required Nodes

- **Start node** (always first): webhook trigger receives the external event
- **SMS node**: sends the outbound text message
- **End node**: terminates the flow

### Optional Nodes

- **HTTP Request node** (before SMS): fetch dynamic data from a DB/API before composing the message
- **Branch node** (after SMS): handle different send outcomes (success, error, policy fail)
- **Evaluate node** (before SMS): transform or format variables before inserting into the message

---

## 2. SMS Node Configuration

The **SMS node** lives in the Channels tab on the flow palette. Walk through these fields in order.

> **Owner: `connect-sms.md` § SMS Node.** The field values, message types, exit paths and output variables in this section are reproduced here so this page works standalone; the reference doc wins on any disagreement.

### Step 1: Destination

| Field | Value |
|-------|-------|
| **Destination Type** | `msisdn` (phone number) for webhook-triggered flows |
| **Destination** | E.164 format: `+15551234567`. Use a variable from the webhook payload: `$(n1.inboundWebhook.customer_phone)` |

### Step 2: From Number

Select a provisioned sender ID from the dropdown. This must be a number with SMS enabled — see section 6 for provisioning prerequisites.

### Step 3: Message Type

Available message types:

| Type | When to Use |
|------|-------------|
| **Text** | Standard Latin-character messages |
| **Flash** | Message displays immediately on recipient device without saving to inbox |
| **Binary** | Binary data payloads |
| **Unicode** | Messages containing emoji, non-Latin characters, or special symbols |
| **Template** | Pre-approved DLT templates (required in some regions, e.g., India) |

See section 4 for encoding impact on character limits.

### Step 4: Message Body

Type your message in the **Message** field. The hard cap is **4,000 characters**, and Cisco recommends staying **below 450 characters** for deliverability [`connect-sms.md` § Message length — two numbers, do not confuse them]. Insert variables using the **variable picker** — never type variable syntax manually.

Use `\n` for line breaks.

⚠ This step previously said "max 1,024 characters". A 2026-07-25 crawl of Cisco's SMS node page quotes 4,000 twice; the 1,024 figure came from an earlier crawl of the same page and is retained in the reference doc rather than deleted [`connect-sms.md` § Message length].

### Wait For Setting

| Mode | Behavior | Use in Agent Flows? |
|------|----------|---------------------|
| **Gateway Submit** | Node exits after message is queued for gateway delivery (exact exit timing not specified in official docs) | **Yes** — fast |
| **Delivery Report** | Node blocks until carrier confirms delivery (seconds to minutes) | **No** — will timeout |

**Always use Gateway Submit** in AI agent flows (30-second timeout). Webhook-triggered notification flows can use Delivery Report if you need confirmation before proceeding.

### Exit Paths

| Event | When |
|-------|------|
| `onSuccess` | Message accepted by gateway (Gateway Submit) or delivered (Delivery Report) |
| `onError` | Invalid destination, misconfigured sender, gateway rejection |
| `onPolicyFail` | Contact policy or compliance restrictions block the message |
| `onTimeOut` | Expiry threshold exceeded (mainly relevant in Delivery Report mode) |

Casing is `onTimeOut` with a capital `O`, per Cisco's node-level exception-handling page; older repo files spell it `onTimeout` and mean the same edge [`connect-sms.md` § Exit Paths].

### Output Variables

| Variable | Description |
|----------|-------------|
| `send.gatewayTid` | Unique transaction reference ID assigned by the gateway |
| `send.sentDateTime` | Timestamp when the message was sent |
| `send.deliveryStatusCode` | Numeric delivery status code |
| `send.deliveryStatusDescription` | Human-readable delivery status description |
| `send.response_data` | Raw response data from the gateway |
| `send.response_interactive` | Interactive response data (if applicable) |

These are the **send node's** `send.*` variables. The inbound `sms.*` set (`sms.message`, `sms.senderNumber`, `sms.serviceNumber`, `sms.keyword`, `sms.ts`, `sms.transId`) is a different namespace belonging to the trigger/Receive node on a two-way flow — the two never mix [`connect-sms.md` § Inbound SMS Output Variables]. There is no output variable for the recipient number and no segment-count variable.

See `connect-sms.md` for the full field list, optional fields (Correlation ID, Notify URL, Callback Data, SmartLinks, Shortened Links), and encoding details.

---

## 3. Variable Insertion

Use Connect's standard `$(nX.variableName)` syntax to insert dynamic values into the message body. **Always use the variable picker** — manually typed variables may arrive empty.

### Plain Text Example

```
Your order $(n3.order_number) is ready for pickup at $(n3.location_name). Reply STOP to opt out.
```

### Variable Sources

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook payload) | `$(n1.inboundWebhook.fieldName)` (platform convention; not explicitly shown in all tutorial examples) | `$(n1.inboundWebhook.order_id)` |
| HTTP Request node output | `$(nX.outputVar)` | `$(n3.customer_name)` |
| Evaluate script output | `$(nX.outputName)` | `$(n4.formatted_date)` |
| Evaluate custom flow variable | `$(variableName)` — no node prefix | `$(formatted_date)` |

For template-based messages, variable syntax is the same `$(variable_name)` format. See `connect-sms.md` for template details.

---

## 4. Message Composition

### Character Limits & Segmentation

> **Owner: `connect-sms.md` § Character Encoding & Segmentation.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Encoding | Single Segment | Concatenated Per-Part |
|----------|---------------|----------------------|
| **GSM-7** (Latin text) | 160 characters | 153 characters |
| **UCS-2** (Unicode/emoji) | 70 characters | 67 characters |

A **single emoji** forces the entire message to UCS-2, cutting capacity by more than half. Budget accordingly.

### Extended GSM-7 Characters

These consume **two character positions** each: `| ^ € { } [ ] ~`. A 160-character message containing one of these splits into 2 segments. (The euro sign is on the official list and the backslash is not — `connect-sms.md` was corrected to match this list on 2026-07-27 [`connect-sms.md` § Extended GSM-7 Characters].)

### Practical Guidelines

- Keep notification messages under 160 characters when possible (1 segment = 1 billing unit)
- Remove emoji if segment count matters — one emoji forces UCS-2 encoding
- Use `\n` for line breaks in the message body
- The SMS node enforces a **4,000-character** field limit regardless of encoding, and Cisco recommends staying **below 450 characters** for deliverability [`connect-sms.md` § Message length — two numbers, do not confuse them]

See `connect-sms.md` for the full concatenation table and encoding details.

---

## 5. MMS Variant

For messages that include images, video, audio, or documents, use the **MMS node** instead of the SMS node. It is a separate node in the Channels palette.

### Key Differences from SMS

| Feature | SMS | MMS |
|---------|-----|-----|
| Media support | Text only | Audio, Video, Image, Text, PDF, Calendar, Contact |
| Body limit | 4,000 chars (below 450 recommended) | 4,096 characters per slide (live UI may show 5,000; not confirmed in official docs) |
| MMS Message field | None | Up to 80 characters — the field is labelled **"MMS Message"**, not "Subject" |
| Max payload | N/A | 750 KB total (some carriers limit to 250 KB) (not confirmed in official docs) |

> **Owner: `connect-sms.md` § MMS Node.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. Both MMS caveats above ("live UI may show 5,000", "not confirmed in official docs") now also appear at the owner.

### When to Use MMS

- Sending product images with notifications
- Attaching PDF receipts or invoices
- Including calendar invites (.ics)
- Any message where visual content adds value

### MMS Wait For Options

The MMS node has four Wait For options (differs from SMS, which has only two):

| Mode | Behavior |
|------|----------|
| **None** | Default; node exits immediately without waiting for any status |
| **Gateway Submit** | Node exits after message is queued for gateway delivery |
| **Delivery Report** | Node blocks until carrier confirms delivery |
| **Read** | Node blocks until recipient reads the message (MMS only) |

**Media URLs must be publicly accessible.** If the URL is behind auth or returns a redirect, the MMS will fail.

See `connect-sms.md` for supported media types, slide composition rules, and MMS exit paths.

---

## 6. Channel Prerequisites

> **Owner: `connect-sms.md` § Sender ID Types, § US A2P 10DLC Registration, § Provisioning Prerequisites.** Everything in this section is reproduced so the prerequisites can be checked without leaving the page; the reference doc wins on any disagreement.

### Sender ID Types

| Type | Two-Way? | Throughput | Use Case |
|------|----------|------------|----------|
| **Long Code (10DLC)** | Yes | Lower (regulated) | Low-to-medium volume business messaging |
| **Short Code** | Yes (keywords) | High | High-volume campaigns, notifications |
| **Toll-Free** | Yes | Medium | Customer support, transactional |
| **Alphanumeric Sender ID** | No (one-way) | Varies | Brand recognition (supported countries only) |

### US 10DLC Registration

US carriers require 10DLC registration for application-to-person SMS on long codes. Unregistered numbers receive error **7281** and messages are rejected (error code not confirmed in official docs — do not build Branch logic that matches on `7281` without confirming the code against a real rejected send on your tenant).

Registration steps: Brand registration with TCR, Campaign registration, number assignment in Connect. See `connect-sms.md` for the full 5-step process.

### Sandbox Limitations

All four figures are Cisco-confirmed [`connect-sms.md` § Sandbox Limitations, which owns them]:

- **10,000 lifetime SMS + WhatsApp requests** (combined)
- Up to **5 registered test phone numbers** (same country, cannot change)
- Two-way SMS in 18 countries; one-way in 70+
- From number is auto-populated and cannot be changed

See `connect-sms.md` for provisioning steps and country-specific requirements (India DLT registration, etc.).

---

## 7. Complete Flow Example: Order-Ready SMS

```
Start (Webhook: order_id, customer_phone)
  |
  v
HTTP Request (GET order details from DB by order_id)
  |
  v
SMS (destination: $(n1.inboundWebhook.customer_phone),
     from: provisioned 10DLC number,
     message: "Your order $(n3.order_number) is ready for pickup
               at $(n3.location_name). ETA: $(n3.pickup_window).
               Reply STOP to opt out.")
  |
  |--- onSuccess -----> End
  |--- onError -------> End (or: log error via HTTP Request)
  |--- onPolicyFail --> End
  |--- onTimeOut -----> End
```

### Webhook Payload

```json
{
  "order_id": "ORD-4521",
  "customer_phone": "+15551234567"
}
```

### curl Test

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {your_service_key}" \
  -d '{"order_id": "ORD-4521", "customer_phone": "+15551234567"}' \
  "https://{your-webhook-url}"
```

---

## 8. Known Gotchas

> **Owner: `connect-sms.md` § Known Gotchas** (which lists the cause for each). Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Issue | Fix |
|-------|-----|
| Message arrives as `?????` | Unicode characters sent with Message Type = "Text" — set to "Unicode" |
| Single emoji doubles segment count | One emoji forces UCS-2 encoding (70 chars/segment). Remove emoji or budget for extra segments. |
| Error 7281: campaign error in US | 10DLC brand/campaign not registered. Register with TCR and assign to number in Connect. (The 10DLC registration requirement itself is documented; the specific code `7281` mapped to it is not confirmed in official docs — do not build Branch logic that matches on `7281` without confirming the code against a real rejected send on your tenant.) |
| Variable arrives empty in message | Typed manually instead of using variable picker. Always use the picker. |
| Shortened URLs blocked by carrier | Some carriers flag shortened domains as spam. Test with target carriers or use full URLs. (not confirmed in official docs) |
| Contact Policy not blocking opted-out users | Policy does not auto-enforce on Send nodes. Add an explicit consent check before the SMS node. (not confirmed in official docs) |

Full gotcha list with causes: see `connect-sms.md`.

---

## References

- [SMS Node](https://help.webexconnect.io/docs/send-sms)
- [MMS Node](https://help.webexconnect.io/docs/mms-node)
- [SMS Length and Encoding](https://developers.webexconnect.io/reference/sms-length-and-encoding-copy1)
- [10DLC Number Assignment](https://help.webexconnect.io/docs/assigning-number-10dlc)
- [Sandbox SMS](https://help.webexconnect.io/docs/sending-and-receiving-sms-using-sandbox)
- [SMS Status Codes](https://developers.webexconnect.io/reference/channel-specific-status-codes-1)
- Complete field reference, templates, and provisioning details: `connect-sms.md`
- Webhook setup, authentication, and testing: `webhook-triggers.md`
