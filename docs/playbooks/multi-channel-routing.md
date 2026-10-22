# Multi-Channel Routing Playbook

## Overview

This playbook covers how to build a single Webex Connect flow that routes notifications to different channels based on customer preference. One webhook, one flow — the customer gets their preferred channel (SMS, Email, Voice, RCS, Apple Messages, or WhatsApp) with automatic SMS fallback when the preferred channel fails.

**This is the premium pattern.** Instead of building separate flows per channel, you build one flow with a Branch node that routes to the right channel at runtime. Adding a new channel means adding one branch — not a new flow.

**Flow structure:**

```
Start (Webhook: customer_id, message, ...)
  → HTTP Request (GET customer record — preferred_channel, phone, email, abc_user_id, abc_session_active)
  → Branch (preferred_channel)
    → "sms"      → SMS → End
    → "email"    → Email → End
    → "voice"    → Call User → Voice Node Group [Play TTS] → End
    → "rcs"      → RCS Capability → Branch (supported?) → RCS Message or SMS fallback → End
    → "apple"    → Branch (session active?) → Apple Messages or SMS fallback → End
    → "whatsapp" → WhatsApp (Template or session) → End
    → default    → SMS (safe fallback) → End
```

For webhook infrastructure (Start node configuration, payload parsing, authentication, testing), see `webhook-triggers.md`. For exhaustive field tables, channel provisioning details, and the full decision matrix, see `connect-multi-channel.md`.

---

## 1. Customer Preference Lookup

Before routing, you need to know the customer's preferred channel. Add an **HTTP Request** node immediately after the Start node to query your customer database.

### HTTP Request Configuration

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **URL** | `https://{api-base-url}/customers?id=eq.$(n1.inboundWebhook.customer_id)` |
| **Headers** | Add header entry: `Content-Type: application/json` (via "Add Another Header" in the Headers section) |

### Required Output Variables

Extract these fields from the response — the rest of the flow depends on them:

| Variable | Purpose | Example |
|----------|---------|---------|
| `preferred_channel` | Routing key for the Branch node | `sms`, `email`, `voice`, `rcs`, `apple`, `whatsapp` |
| `phone` | Destination for SMS, Voice, RCS, WhatsApp | `+15551234567` (E.164) |
| `email` | Destination for Email | `customer@example.com` |
| `abc_user_id` | Custom DB column — maps to the `abcId` Apple Messages uses as destination (nullable) | `abc-opaque-id-xyz` |
| `abc_session_active` | Custom DB flag — whether an Apple Messages session is open (not a platform-provided variable; you maintain this) | `true` / `false` |

### Database Schema Pattern

Your customer table needs a `preferred_channel` column. Default it to `sms` so customers without a preference still get routed.

See `connect-multi-channel.md` for the full schema pattern and column definitions.

---

## 2. Branch Node Configuration

The **Branch node** is the routing engine. It reads the customer's `preferred_channel` value and sends the flow down the matching path.

### Step-by-Step Configuration

1. Drag a **Branch** node onto the canvas
2. Wire the HTTP Request node's output to this Branch node
3. Add one branch per supported channel:

| Branch # | Condition | Operator | Value | Routes To |
|----------|-----------|----------|-------|-----------|
| 1 | `$(n2.preferred_channel)` | Equals | `sms` | SMS node |
| 2 | `$(n2.preferred_channel)` | Equals | `email` | Email node |
| 3 | `$(n2.preferred_channel)` | Equals | `voice` | Call User node |
| 4 | `$(n2.preferred_channel)` | Equals | `rcs` | RCS Capability node |
| 5 | `$(n2.preferred_channel)` | Equals | `apple` | Apple Messages session check |
| 6 | `$(n2.preferred_channel)` | Equals | `whatsapp` | WhatsApp node |
| Default | None of the above | — | — | SMS node (universal fallback) |

Where `n2` is the HTTP Request node number — verify this matches your flow's node numbering.

### Case Sensitivity Warning

Branch conditions are **case-sensitive**. `SMS` does not match `sms`. Normalize your `preferred_channel` values to lowercase in your database to avoid misroutes. If a value doesn't match any branch, the "None of the above" default fires — which routes to SMS, so the customer still gets notified.

---

## 3. Channel-Specific Delivery Paths

Each branch leads to a channel-specific delivery path. The SMS and Email paths are straightforward. Voice, RCS, Apple Messages, and WhatsApp require additional nodes or considerations before delivery.

### SMS Path (Simplest)

Direct send — no capability check needed. Every phone supports SMS.

```
Branch (sms) → SMS Node → End
```

Configure the SMS node with `$(n2.phone)` as the destination and your notification text in the message body. Use `$(nX.variableName)` syntax for dynamic values from the HTTP Request output.

### Email Path (Direct Send)

No capability check needed if the customer record includes an email address.

```
Branch (email) → Email Node → End
```

Configure with `$(n2.email)` as the destination. Supports HTML body, attachments, and dynamic subject lines.

### Voice Path (Call User + TTS)

The voice path dials the customer and plays a TTS message.

```
Branch (voice) → Call User → Voice Node Group [Play TTS] → End
```

Configure the Call User node with:
- **Destination:** `$(n2.phone)` (E.164 format)
- **From Number:** Select a provisioned voice-enabled number

The Voice Node Group auto-creates when you add the Call User node. Add a Play node inside it with your TTS message. The Play node's **Input Format** sets the budget: **Plain Text = 3,000 characters**, **SSML = 6,000** [`webex-connect-advanced.md` § Play Node (Voice Node Group) → TTS Settings].

⚠ **2,000 is a different field's limit — do not apply it to a Play node.** That figure belongs to the Voice Node Group's **Answering Machine Detection** prompt [`webex-connect-advanced.md` § Answering Machine Detection (AMD)]. This line previously read "TTS messages are limited to 2,000 characters", which is the mix-up the owner doc explicitly warns against; `outbound-voice.md` § 5 has always carried the correct 3,000 / 6,000 figures.

See `outbound-voice.md` for full Call User configuration, TTS settings, SSML examples, and AMD setup.

### RCS Path (Capability Check Required)

RCS requires a two-node check before sending — not every device supports it, and no iOS devices do.

```
Branch (rcs)
  → RCS Capability (check phone)
    → onSuccess → Branch (rcs.enabled == true AND rcs.version == "up2")
      → [Yes] → RCS Message → End
      → [No]  → SMS (fallback) → End
    → onError → SMS (fallback) → End
```

Configure the RCS Capability node with `$(n2.phone)` and `Force Refresh: false` (cached lookup, near-instant). After the capability check succeeds, add a second Branch node to verify `rcs.enabled` = `true` AND `rcs.version` = `up2` before sending rich content.

See `outbound-rcs.md` for the full capability check pattern, rich card configuration, and SMS fallback wiring.

### Apple Messages Path (Session Check Required)

Apple Messages requires an active customer session — you cannot cold-send. Your HTTP Request already fetched `abc_session_active` from the customer record.

```
Branch (apple)
  → Branch (abc_session_active == true)
    → [Yes] → Apple Messages → End
    →          (wire onError, onPolicyFail → SMS fallback → End)
    → [No]  → SMS (fallback) → End
```

Add a second Branch node that checks `$(n2.abc_session_active)` = `true` (a custom DB flag you maintain — the platform does not provide this variable). If active, send via Apple Messages using `$(n2.abc_user_id)` as the destination (the Destination Type is "AbcUser Id" — `abcId` in platform terms). Wire both `onError` and `onPolicyFail` to SMS — the session can close between the check and the send.

See `outbound-apple-messages.md` for the full session check pattern, Rich Link configuration, and session table design.

### WhatsApp Path (Template or Text Message)

WhatsApp supports two message types: **template messages** (pre-approved by Meta, can be sent anytime) and **Text messages** (non-template, free-form — only within 24 hours of the customer's last inbound message). For proactive notifications, use templates.

```
Branch (whatsapp)
  → WhatsApp Node (template or Text message)
    → onSuccess → End
    → onError → SMS (fallback) → End
    → onPolicyFail → SMS (fallback) → End
    → onTimeout → SMS (fallback) → End
    → onDeliveryReportFail → SMS (fallback) → End
```

Configure the WhatsApp node with `$(n2.phone)` as the destination (E.164 format). For template messages, select the approved template and map dynamic parameters. For Text messages (non-template messages), provide the message body directly.

Wire all WhatsApp failure exits to SMS fallback — `onError`, `onPolicyFail`, `onTimeout`, and `onDeliveryReportFail`. The recipient may not have WhatsApp installed, or the template may have been paused/rejected.

See `outbound-whatsapp.md` for full WhatsApp node configuration, template setup, and session message patterns.

---

## 4. Failure & Fallback Wiring

Every channel path must have a fallback. SMS is always the **ultimate fallback** — every phone supports it.

### Standard Fallback: Wire `onError` to SMS

Wire each channel's error exit to a shared SMS fallback node (or individual SMS nodes — both work):

| Channel Path | Error Exit | Fallback |
|-------------|-----------|----------|
| Email | `onError`, `onPolicyFail`, `onTimeout`, `onDeliveryReportFail` | SMS |
| Voice (Call User) | `onbusy`, `onnoanswer`, `onreject`, `oncallfail`, `onExpiry` | SMS (optional — depends on urgency) |
| RCS Capability | `onError` | SMS |
| RCS (Branch: not supported) | "None of the above" | SMS |
| RCS Message | `onError`, `onPolicyFail`, `onTimeout`, `onDeliveryReportFail` | SMS |
| Apple Messages (no session) | "None of the above" | SMS |
| Apple Messages | `onError`, `onPolicyFail` | SMS |
| WhatsApp | `onError`, `onPolicyFail`, `onTimeout`, `onDeliveryReportFail` | SMS |

### RCS Fallback Details

Three SMS fallback wires for the RCS path:
1. **RCS Capability → onError** → SMS (capability check itself failed)
2. **Branch → "None of the above"** → SMS (device doesn't support RCS or only has up1)
3. **RCS Message → onError** → SMS (message send failed after passing checks)

### Apple Messages Fallback Details

Two SMS fallback wires for the Apple Messages path:
1. **Branch → "None of the above"** → SMS (no active session)
2. **Apple Messages → onError / onPolicyFail** → SMS (session closed between check and send, or policy violation)

### Voice Fallback (Optional)

Voice fallback to SMS is optional and depends on notification urgency:
- **For critical notifications:** Wire `onbusy`, `onnoanswer`, and `onExpiry` to SMS so the customer still gets the message
- **For non-critical:** Wire error exits to End — don't double-notify

### Priority-Based Fallback Chain

```
Preferred Channel → Primary Fallback → Ultimate Fallback
─────────────────────────────────────────────────────────
RCS              → SMS              → (done)
Apple Messages   → SMS              → (done)
WhatsApp         → SMS              → (done)
Email            → SMS              → (done)
Voice            → SMS (optional)   → (done)
SMS              → (done)           →
```

For cascade fallback patterns (RCS → Email → SMS), see `connect-multi-channel.md`.

---

## 5. Complete Flow Example: Multi-Channel Order Notification

A single flow that sends an order-ready notification via the customer's preferred channel.

### Flow Diagram

```
Start (Webhook: customer_id, order_id)
  |
  v
HTTP Request (GET customer + order details)
  |  Output: preferred_channel, phone, email, abc_user_id, abc_session_active,
  |          order_number, location_name, directions_url
  |
  v
Branch (preferred_channel)
  |
  |--- "sms" ---------> SMS
  |                       Destination: $(n2.phone)
  |                       Message: "Your order $(n2.order_number) is ready
  |                                 at $(n2.location_name)."
  |                       → End
  |
  |--- "email" -------> Email
  |                       To: $(n2.email)
  |                       Subject: "Order $(n2.order_number) Ready for Pickup"
  |                       Body: HTML with order details
  |                       → onError → SMS (fallback) → End
  |                       → End
  |
  |--- "voice" -------> Call User
  |                       Destination: $(n2.phone)
  |                       → onAnswer → Voice Node Group
  |                       |              Play (TTS): "Hello. Your order
  |                       |              $(n2.order_number) is ready for pickup
  |                       |              at $(n2.location_name). Thank you."
  |                       |              → End
  |                       → onbusy/onnoanswer/onExpiry → SMS (fallback) → End
  |
  |--- "rcs" ---------> RCS Capability (check $(n2.phone), Force Refresh: false)
  |                       → onSuccess → Branch (enabled + up2?)
  |                       |   → [Yes] → RCS Message (Rich Card)
  |                       |   |           Title: "Order $(n2.order_number) is ready"
  |                       |   |           Suggestions: [Get Directions] [Call Store]
  |                       |   |           → onError → SMS (fallback) → End
  |                       |   |           → End
  |                       |   → [No]  → SMS (fallback) → End
  |                       → onError → SMS (fallback) → End
  |
  |--- "apple" -------> Branch (abc_session_active == true)
  |                       → [Active] → Apple Messages (Rich Link)
  |                       |              Destination: $(n2.abc_user_id)
  |                       |              Title: "Order $(n2.order_number) is ready"
  |                       |              URL: directions link
  |                       |              → onError, onPolicyFail → SMS (fallback) → End
  |                       |              → End
  |                       → [None] → SMS (fallback) → End
  |
  |--- "whatsapp" ----> WhatsApp (Template Message)
  |                       Destination: $(n2.phone)
  |                       Template: order_ready
  |                       Params: [$(n2.order_number), $(n2.location_name)]
  |                       → onError, onPolicyFail, onTimeout, onDeliveryReportFail → SMS (fallback) → End
  |                       → End
  |
  |--- default -------> SMS
                          Destination: $(n2.phone)
                          Message: "Your order $(n2.order_number) is ready
                                    at $(n2.location_name)."
                          → End
```

### Webhook Payload

```json
{
  "customer_id": "CUST-1234",
  "order_id": "ORD-4521"
}
```

### curl Test Command

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {your_service_key}" \
  -d '{"customer_id": "CUST-1234", "order_id": "ORD-4521"}' \
  "https://{your-webhook-url}"
```

For webhook setup, authentication, and response codes, see `webhook-triggers.md`.

---

## 6. Known Gotchas

| Issue | Fix |
|-------|-----|
| Customer gets both RCS and SMS | Branch node routes aren't exclusive — ensure the RCS success path does NOT also fall through to the default SMS branch. Each branch exit must wire to its own End node |
| Branch conditions don't match | `preferred_channel` values are case-sensitive. `SMS` ≠ `sms`. Normalize to lowercase in your database |
| Customer with no preference gets nothing | Set the Branch default ("None of the above") to SMS. Also default `preferred_channel` to `sms` in your DB schema |
| RCS path adds 3–6s latency | RCS Capability node with `Force Refresh: true` does a live carrier lookup. Use `Force Refresh: false` for cached lookup (near-instant, 7-day cache). On cache miss, the node automatically falls back to a live lookup |
| Apple Messages sends fail silently | Session closed between your DB check and the send. Wire both `onError` and `onPolicyFail` to SMS fallback |
| Voice call never connects — no error exit fires | Call User `onExpiry` fires (orange exit) when the call request expires before being answered. Wire `onExpiry` to SMS fallback for critical notifications |
| Variable picker shows wrong node's variables | After adding or removing nodes, node numbers shift. Re-verify all `$(nX.variableName)` references match the correct node numbers |
| Flow exceeds 30s when used inside an AI Agent action | Multi-channel routing with RCS + HTTP lookups can exceed the agent timeout. Move notification logic to a separate webhook-triggered flow (this playbook's pattern) instead of embedding in an agent action |
| WhatsApp template rejected at runtime | Template was paused or disabled by Meta after approval. Check template status in **Tools → Templates** within Webex Connect before going live and monitor for status changes |
| WhatsApp Text message fails outside 24-hour window | Customer hasn't messaged in the last 24 hours — Text messages (non-template) only work within that window. Use template messages for proactive outbound, or fall back to SMS |
| SMS fallback node receives duplicate triggers | Multiple error paths wire to the same SMS node. This is fine — Connect handles it. But verify the SMS destination variable resolves correctly from all input paths |

Full gotcha list and channel decision matrix in `connect-multi-channel.md`.

---

## References

- `connect-multi-channel.md` — full multi-channel reference (schema, decision matrix, provisioning checklist, cascade patterns)
- `webhook-triggers.md` — Start node webhook setup, authentication, payload parsing
- `outbound-voice.md` — Call User + TTS configuration, Voice Node Group, AMD
- `outbound-rcs.md` — RCS Capability check, rich card configuration, SMS fallback
- `outbound-apple-messages.md` — session check pattern, Rich Link configuration, session table design
- `outbound-whatsapp.md` — WhatsApp node configuration, template setup, session messages
- [Branch Node](https://help.webexconnect.io/docs/branch-node)
- [SMS Node](https://help.webexconnect.io/docs/send-sms)
- [Email Node](https://help.webexconnect.io/docs/email-node)
- [RCS Capability Node](https://help.webexconnect.io/docs/rcs-capability-node)
- [Apple Messages Node](https://help.webexconnect.io/docs/apple-messages-for-business)
- [Apple Messages for Business Setup](https://help.webexconnect.io/docs/apple-messages-for-business-1)
- [WhatsApp Node](https://help.webexconnect.io/docs/whatsapp)
- [Call User Node](https://help.webexconnect.io/docs/voice-call-user)
