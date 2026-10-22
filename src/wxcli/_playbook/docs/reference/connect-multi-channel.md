# Webex Connect — Multi-Channel Routing Reference

<!-- ref-tag: connect-multi-channel-v2 -->

Patterns for routing notifications across multiple channels (SMS, Email, RCS, Apple Messages, WhatsApp, Voice) within a single Webex Connect flow. Covers the Branch node routing pattern, customer preference lookup, capability checks, fallback chains, and channel selection logic.

**Prerequisite:** This document assumes familiarity with the per-channel reference docs: `connect-sms.md`, `connect-email.md`, `connect-rcs.md`, `connect-apple-messages.md`, `connect-whatsapp.md`. For voice, see `webex-connect-advanced.md` § Call User Node (Initiates the Call).

---

## Multi-Channel Flow Structure

A single webhook triggers one flow. The flow routes to the appropriate channel based on customer preference or device capability.

```
Start (Webhook: customer_id, message, ...)
  → HTTP Request (lookup customer record — get preferred_channel, phone, email, abcUserId)
  → Branch (preferred_channel)
    → "voice"  → Call User → Voice Node Group [Play TTS] → End
    → "sms"    → SMS → End
    → "email"  → Email → End
    → "rcs"    → RCS Capability → Branch (rcs.enabled == true AND rcs.version == "up2")
                   → Yes → RCS Message → End
                   → No  → SMS (fallback) → End
    → "apple"  → Branch (has active session?)
                   → Yes → Apple Messages → End
                   → No  → SMS (fallback) → End
    → "whatsapp" → WhatsApp (Message Type: Template, or a free-form type
                   inside the 24-hour window) → End
    → default  → SMS (safe fallback) → End
```

The RCS branch tests **both** `rcs.enabled` and `rcs.version` — `enabled` alone only proves basic RCS [`connect-rcs.md` § Critical: `enabled` vs `version`]. See § RCS (Capability Check + SMS Fallback).

ℹ **`abcUserId` and `abcId` are two different things, both correct** — resolved by live verification 2026-07-27, superseding the "UNRESOLVED, may be named `abcId`" note this line previously carried. `abc.abcUserId` is the **inbound** Receive-node output variable; `abcId` is Cisco's prose name for the opaque *value* you store and later send to. The `abcUserId` in the sketch above is a **custom column in your own database** holding that value, so either reading leaves it correct [`connect-apple-messages.md` § `abcUserId` vs `abcId` — two different things, both correct]. See § Apple Messages (Session Check + Fallback) — the **Destination Type dropdown label** is a separate question and is still open.

---

## Branch Node for Channel Selection

The **Branch node** is the routing engine. Configure it with the customer's preferred channel from a DB lookup.

### Configuration

| Field | Value |
|-------|-------|
| **Input Variable** | `$(nX.preferred_channel)` — from HTTP Request output |
| **Branches** | One per supported channel: `voice`, `sms`, `email`, `rcs`, `apple`, `whatsapp` |
| **Condition** | Equals (case-sensitive) |
| **Default** | "None of the above" → SMS (universal fallback) |

### Variable Source

The `preferred_channel` field comes from the customer's record in your database. Common values:

| Value | Routes To |
|-------|-----------|
| `voice` | Call User node |
| `sms` | SMS node |
| `email` | Email node |
| `rcs` | RCS Capability check → RCS Message (or SMS fallback) |
| `apple` | Active session check → Apple Messages (or SMS fallback) |
| `whatsapp` | WhatsApp node (Message Type `Template`, or a free-form type inside the 24-hour window; SMS fallback on error) |

If the customer has no preference, the default branch fires → SMS.

---

## Channel-Specific Routing Patterns

### SMS (Direct Send)

Simplest path — no capability check needed. Every phone supports SMS.

```
Branch (sms) → SMS Node → End
```

Configuration: see `connect-sms.md`.

### Email (Direct Send)

No capability check needed if you have the customer's email address.

```
Branch (email) → Email Node → End
```

Configuration: see `connect-email.md`.

### Voice (Direct Call)

```
Branch (voice) → Call User → Voice Node Group [Play TTS] → End
```

Configuration: see `webex-connect-advanced.md` § Call User Node (Initiates the Call), § Voice Nodes (Voice Node Group) and § Play Node (Voice Node Group). For the build sequence, see `docs/playbooks/outbound-voice.md`.

### RCS (Capability Check + SMS Fallback)

RCS **always** requires a capability check — not every device supports it. This is the most common multi-channel pattern.

```
Branch (rcs)
  → RCS Capability Node (check phone)
    → onSuccess → Branch (rcs.enabled == true AND rcs.version == "up2")
      → [Yes] → RCS Message Node
                  → onSuccess              → End
                  → onSubmit               → End
                  → onDeliveryReportSuccess → End
                  → onError                → SMS Node (fallback) → End
                  → onDeliveryReportFail   → SMS Node (fallback) → End
                  → onPolicyFail           → SMS Node (fallback) → End
                  → onTimeout              → SMS Node (fallback) → End
      → [No]  → SMS Node (fallback) → End
    → onError → SMS Node (fallback) → End
```

**Key details:**
- `rcs.enabled` = `true` only means basic RCS. Check `rcs.version` = `up2` for rich cards/carousels [`connect-rcs.md` § Critical: `enabled` vs `version`].
- Set `Force Refresh: false` for cached lookup (near-instant). `true` adds 3–6s. **The UI defaults to `true`** — the slow option — so leaving this field alone is the wrong choice in an AI agent flow; you must set it explicitly [`connect-rcs.md` § RCS Capability Node → Configuration Fields].
- If sending rich content, also check `rcs.capabilties.richcard` = `true`. ⚠ **That spelling is not a typo in this doc — the platform emits `capabilties`, missing the "i".** A Branch condition typed with the correctly-spelled `rcs.capabilities.richcard` will **never match**: the flow builds, deploys, and runs with no error, it just silently takes the wrong path forever. Never type these names by hand — copy the exact name from the variable picker. The carousel variable uses a *different* typo again (`rcs.capabilites.richcardCarousel`) [`connect-rcs.md` § RCS Capability Node → Output Variables].
- The RCS Message node has **7 exit paths**, and `onSuccess` / `onSubmit` are **distinct branches, not aliases** — each must be wired separately [`connect-rcs.md` § RCS Message Node → Exit Paths]. Wiring only `onError` leaves `onDeliveryReportFail`, `onPolicyFail`, and `onTimeout` unhandled.
- The RCS Capability node itself has 2 exits — `onSuccess` and `onError` [`connect-rcs.md` § RCS Capability Node → Exit Paths].
- Full configuration: see `connect-rcs.md`.

### Apple Messages (Session Check + Fallback)

Apple Messages requires an **active customer session** — you cannot cold-send. You must maintain a table of active sessions.

```
Branch (apple)
  → Branch (has_active_session == true)
    → [Yes] → Apple Messages Node
                → onSuccess    → End
                → onError      → SMS Node (fallback — session may have closed)
                → onPolicyFail → SMS Node (fallback) → End
    → [No]  → SMS Node (fallback) → End
```

**Key details:**
- The `has_active_session` field must come from YOUR database — Connect does not expose a session check API.
- Track `abcUserId` values from incoming customer messages, reading them with **`$(nX.abc.abcUserId)`**. ℹ **RESOLVED 2026-07-27 by live verification — the two names are two different things, not drift, and the owner is `connect-apple-messages.md` § `abcUserId` vs `abcId` — two different things, both correct.** `abc.abcUserId` is the **inbound Receive-node output variable**, listed verbatim by Cisco; `abcId` is Cisco's **prose name for the opaque value** you store and later send to, and is **not** a Connect output variable name anywhere in the docs. Provenance retained rather than deleted: `docs/tests/findings/digital-inbound-agent-findings.md` § Items Confirmed Accurate #17 confirmed `$(n1.abc.abcUserId)` and **stands**; `docs/tests/findings/outbound-apple-messages-findings.md` #4's specific claim that *"the Connect output variable will be named `abcId`"* is **wrong and must not be applied** — the rest of #4, that official prose says `abcId` for the identifier *value*, stands. The third variant, `docs/tests/findings/multi-channel-routing-findings.md` #7's *"AbcUser Id"*, is a **different field again** — the Destination Type dropdown label — and is **still UNRESOLVED**: Cisco's screenshots show `AbcUser Id` while the prose on the same page says *"Select **User ID** from this dropdown box."* Read the dropdown in your tenant; do not flip either on a single source [`connect-apple-messages.md` § Node Configuration → General Fields].
- Remove sessions when you receive `CONVERSATIONCLOSED` events (reportedly **HTTP 410 Gone** on a subsequent send). ⚠ **Both the event name and the 410 status are unverified** — neither string appears on help.webexconnect.io; the 410 is plausible Apple platform behavior, not documented Webex Connect behavior [`connect-apple-messages.md` § Verification Status, § Session Termination].
- Always wire Apple Messages `onError` to a fallback — sessions can close between the check and the send.
- The node has **exactly three** exit paths — `onSuccess`, `onError`, `onPolicyFail`. There is no `onInvalidData` exit. Also note `onSuccess` means "submitted to Apple," **not** "delivered" — Apple provides no delivery or read receipts to MSPs [`connect-apple-messages.md` § Exit Paths].
- Full configuration: see `connect-apple-messages.md`.

### WhatsApp (Template or Free-Form Message + SMS Fallback)

What the WhatsApp node can send is governed by the **24-hour session window**, not by a message category. Inside the window (customer messaged within the last 24 hours) **all** Message Types are allowed; outside it, and for any business-initiated message with no prior customer message, only `Template` is allowed [`connect-whatsapp.md` § 24-Hour Session Window].

> ⚠ There is **no "session message" Message Type** on the platform. The node's **Message Type** field accepts exactly: `Text`, `Media`, `Template`, `Location`, `Contact`, `List Messages`, `Reply Buttons` [`connect-whatsapp.md` § WhatsApp Node → Required Fields].

```
Branch (whatsapp)
  → WhatsApp Node (Message Type: Template, or a free-form type inside the window)
    → onSuccess               → End
    → onSubmit                → End
    → onDeliveryReportSuccess → End
    → onError                 → SMS Node (fallback) → End
    → onDeliveryReportFail    → SMS Node (fallback) → End
    → onPolicyFail            → SMS Node (fallback) → End
    → onTimeout               → SMS Node (fallback) → End
```

**Key details:**
- **`Template` messages** require pre-approval by Meta. Use templates for proactive/outbound notifications.
- **Free-form Message Types** (`Text`, `Media`, `Location`, `Contact`, `List Messages`, `Reply Buttons`) are allowed only within 24 hours of the customer's last inbound message; each new customer message resets the clock. Sending one outside the window returns **error 7710** [`connect-whatsapp.md` § 24-Hour Session Window]. Track the window in your database.
- The customer's phone number must be in E.164 format with an active WhatsApp account.
- The node has **7 exit paths** — `onSuccess`, `onSubmit`, `onDeliveryReportSuccess`, `onTimeout`, `onError`, `onPolicyFail`, `onDeliveryReportFail` [`connect-whatsapp.md` § Exit Paths]. Which "success" branch fires depends on the **Wait For** setting: `onSuccess` on None, `onSubmit` on Gateway Submit, `onDeliveryReportSuccess` on Delivery Report.
- Wire `onError` to SMS fallback — the recipient may not have WhatsApp installed, or the template may be rejected.
- Full configuration: see `connect-whatsapp.md`.

---

## Customer Preference Lookup

### Database Schema Pattern

Your customer table needs a `preferred_channel` field:

| Column | Type | Values | Default |
|--------|------|--------|---------|
| `preferred_channel` | text | `voice`, `sms`, `email`, `rcs`, `apple`, `whatsapp` | `sms` |
| `phone` | text | E.164 format | — |
| `email` | text | Email address | — |
| `abc_user_id` | text | Apple Messages opaque ID (nullable) | `null` |
| `abc_session_active` | boolean | Track active Apple sessions | `false` |
| `wa_session_active` | boolean | Track active WhatsApp 24-hour session window | `false` |

### HTTP Request Node

```
GET https://{api-base-url}/customers?id=eq.$(n1.inboundWebhook.customer_id)
```

⚠ The general variable pattern `$(n[nodeID].[nodeType].[fieldName])` is confirmed in official docs, but **`inboundWebhook` as the specific node-type segment for Start-node webhook fields is unverified** — it is consistent with platform behavior but not explicitly confirmed by Cisco [`docs/tests/findings/webhook-triggers-findings.md` #4]. Confirm the exact variable in the **variable picker** rather than typing it.

Output variables to extract:
- `preferred_channel`
- `phone`
- `email`
- `abc_user_id`
- `abc_session_active`

---

## Fallback Chain Strategy

When the preferred channel fails, fall back gracefully:

### Priority-Based Fallback

```
Preferred Channel → Primary Fallback → Ultimate Fallback
─────────────────────────────────────────────────────────
RCS              → SMS              → (done)
Apple Messages   → SMS              → (done)
WhatsApp         → SMS              → (done)
Email            → SMS              → (done)
Voice            → SMS              → (done)
SMS              → (done)           →
```

SMS is always the **ultimate fallback** — every phone supports it.

### Implementation Pattern

Wire **every** failure exit to the SMS fallback, not just `onError` — each node has more than one:

```
RCS Message    → onError / onDeliveryReportFail / onPolicyFail / onTimeout → SMS → End
Apple Messages → onError / onPolicyFail                                    → SMS → End
WhatsApp       → onError / onDeliveryReportFail / onPolicyFail / onTimeout → SMS → End
Email          → onError / onInvalidData / onPolicyFail / onTimeout        → SMS → End
Call User      → oncallfail / onnoanswer / onbusy / onreject
                 / onError / onPolicyFail / onExpiry                       → SMS → End
```

Exit-path owners: RCS Message 7 exits [`connect-rcs.md` § RCS Message Node → Exit Paths]; Apple Messages exactly 3, with no `onInvalidData` [`connect-apple-messages.md` § Exit Paths]; WhatsApp 7 [`connect-whatsapp.md` § Exit Paths]; Email 5 — but note its owner flags `onSuccess` and `onInvalidData` as **UI-only, not named in official Email node docs**, so confirm those two against the node in your tenant [`connect-email.md` § Exit Paths]; Call User 8 [`webex-connect-advanced.md` § Call User Node (Initiates the Call) → Exit Paths (Events)]. `onExpiry` fires only when an expiry is configured, and `onPolicyFail` on Call User covers Callback Data over 2 KB.

⚠ **Call User event casing is exact and deliberately inconsistent — do NOT "normalise" it.** Four events are all-lowercase (`onbusy`, `onnoanswer`, `onreject`, `oncallfail`) and four are mixed case (`onAnswer`, `onError`, `onPolicyFail`, `onExpiry`). Casing is also **node-specific**: `onNoAnswer` in mixed case is the **Call Patch** node's spelling, not Call User's. Never copy one node's casing onto another [`webex-connect-advanced.md` § Call User Node (Initiates the Call) → Exit Paths (Events)].

### Cascade Fallback (Advanced)

For high-priority notifications, try multiple channels in sequence:

```
RCS Capability → Branch
  → RCS supported → RCS Message
    → onError → Email
      → onError → SMS → End
  → Not supported → Email
    → onError → SMS → End
```

---

## Wait For Settings by Channel

All channels in a multi-channel flow should use **Gateway Submit** for consistent, fast execution:

| Channel | Wait For | Notes |
|---------|----------|-------|
| SMS | Gateway Submit | Delivery Report blocks waiting on a third-party carrier — the wrong shape for a 30-second budget. ⚠ Cisco publishes **no** latency figures; do not quote a specific delay [`connect-sms.md` § Wait For Setting] |
| Email | Gateway Submit | Delivery Report waits for delivery/bounce confirmation — will time out in an agent flow. No published latency figure; do not quote one [`connect-email.md` § Wait For Setting] |
| RCS | Gateway Submit | Read Receipts available but blocks |
| Apple Messages | `GW submit` | No Delivery Report option available — Apple does not provide DRs. ⚠ The label is `GW submit` on this node, not `Gateway Submit` [`connect-apple-messages.md` § Wait For] |
| WhatsApp | Gateway Submit | Delivery Report available but blocks |
| Voice | N/A | Call User node has its own exit paths |

---

## Worked Example — Webhook-Triggered Notification (No AI Agent)

Most multi-channel builds are **not** AI agent builds — they are outbound notifications fired by an external system. This section assembles the fragments above into one end-to-end flow for that case. It is a **sibling** of § Multi-Channel in AI Agent Flows, not a replacement: that section covers the same routing running *inside* an agent action, under the 30-second budget and returning data through a Flow Outcomes key-set. Neither transfers to the other — this flow has no AI Agent trigger, no agent timeout, and **no Flow Outcomes at all** (§ What This Example Does Not Contain).

**Build-sequence owner: `docs/playbooks/multi-channel-routing.md`** — it owns the ordering, the click-by-click steps, and the judgment calls. Webhook infrastructure (Start node setup, payload parsing, authentication, testing) is owned by `docs/playbooks/webhook-triggers.md`. This section shows the assembled result with each value's owner named inline.

### Node Map

| Node | Type | Purpose |
|---|---|---|
| `n1` | Start — trigger category **Webhook** [`webex-connect.md` § Full trigger category inventory] | Receives the third-party POST |
| `n2` | HTTP Request (GET) | Customer lookup — returns the routing key and every destination |
| `n3` | Branch | Channel router on `preferred_channel` |
| `n4` | Send SMS | The `sms` branch |
| `n5` | Email | The `email` branch |
| `n6` | Call User (auto-creates a Voice Node Group containing a Play node) | The `voice` branch |
| `n7` | RCS Capability | Capability probe for the `rcs` branch |
| `n8` | Branch | Rich-capability gate — reads `n7`'s output |
| `n9` | RCS Message | The `rcs` send |
| `n10` | Branch | Apple session gate — reads `n2`'s output |
| `n11` | Apple Messages for Business | The `apple` send |
| `n12` | WhatsApp | The `whatsapp` branch |
| `n13` | Send SMS | **Shared SMS fallback** — every failure exit converges here |

Every node above is on the documented palette: Send SMS, RCS Capability, RCS Message, Email, Apple Messages for Business, WhatsApp and Receive are **Channels**; Branch and HTTP request are **Utilities**; Call User, Voice Node Group and Play are **Embedded Voice** [`webex-connect.md` § Node Palette Inventory].

⚠ Node numbers shift when you add or remove nodes. Re-check every `$(nX.…)` reference in the **variable picker** after any canvas edit — a manually typed or stale reference arrives empty at runtime with no error [`webex-connect.md` § Variable Picker → Rules].

### Flow Sketch

```
n1  Start — Webhook  {customer_id, order_id, customer_phone}
     │
n2  HTTP Request (GET customer record)
     ├─ onSuccess → n3
     ├─ onError   → n13   (see "lookup failure" below)
     └─ onTimeout → n13

n3  Branch on $(n2.preferred_channel)
     ├─ "sms"              → n4  Send SMS
     ├─ "email"            → n5  Email
     ├─ "voice"            → n6  Call User → Voice Node Group [Play TTS]
     ├─ "rcs"              → n7  RCS Capability → n8 Branch → n9 RCS Message
     ├─ "apple"            → n10 Branch (session open?) → n11 Apple Messages
     ├─ "whatsapp"         → n12 WhatsApp
     ├─ None of the above  → n13 Send SMS   (universal default)
     └─ onError            → n13 Send SMS
```

A Branch node's outcomes are **one exit edge per branch, plus "None of the above", plus `onError`** — conditions evaluate top-to-bottom and first match wins [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration].

⚠ **Lookup failure is not what you think it is.** A `404` (customer not found) is expected to leave `n2` through **`onSuccess`**, not `onError` — the request completed, it just returned an error status. ⚠ Cisco never states this outright; it is a **strongly-supported inference**, not a documented statement [`webex-connect-advanced.md` § 4xx/5xx Is Expected to Go Through onSuccess]. The practical consequence: on a 404, `$(n2.preferred_channel)` is empty, so `n3` falls to **"None of the above"** → `n13`, and the customer still gets an SMS. To tell "no record" apart from "no preference", insert a Branch on `$(n2.https.statusCode)` between `n2` and `n3` — the remedy is correct under either reading of the edge [same owner; `https.statusCode` is one of four built-in HTTP outputs, per `webex-connect.md` § Built-in Output Variables].

⚠ **`n13` cannot use `$(n2.phone)`.** Every path that reaches the fallback because the *lookup itself* failed (`n2` `onError`, `n2` `onTimeout`, and the 404 route above) has no `n2` output to read. Source `n13`'s destination from the **webhook payload** instead — see § The Shared SMS Fallback (`n13`). If your payload carries no phone number, those legs have no usable destination and must terminate rather than send.

### `n1` — Start Node (Webhook Trigger)

**Webhook** is a **Custom Triggers** category on the Start node, alongside **Custom event** [`webex-connect.md` § Full trigger category inventory]. In the trigger configuration select **Webhook**, then either pick an existing webhook or create one inline, name it, paste a sample payload into **PROVIDE SAMPLE INPUT**, and click **PARSE** — Connect extracts the field names and makes them available as flow variables [`webhook-triggers.md` § 1. Start Node Webhook Configuration].

```json
{
  "customer_id": "CUST-1234",
  "order_id": "ORD-4521",
  "customer_phone": "+15551234567"
}
```

| Fact | Value | Owner |
|---|---|---|
| Authentication | **Optional** for inbound webhooks — mandatory only for Custom Events | [`webex-connect.md` § Inbound webhooks] |
| Payload cap | **256 KB** default, rejected with error code **430** | [`webex-connect.md` § Inbound webhooks; codes owned by `connect-response-codes.md`] |
| Body handling | The JSON/XML body *"will be parsed as JPath/Xpath and the variables will be made available in flows/rules"* | [`webex-connect.md` § Inbound webhooks] |
| URL | Auto-generated — you cannot choose or construct it. Double-click the Start node after saving to copy it | [`webhook-triggers.md` § 2. Webhook URL] |
| Going live | The flow must be **published (made live)** before the webhook accepts requests | [`webhook-triggers.md` § 2. Webhook URL] |

> ⚠ **The `inboundWebhook` path segment is UNRESOLVED — carry this hedge wherever you copy the example.** This section writes payload fields as `$(n1.inboundWebhook.customer_phone)`, matching the rest of this repo, but **the literal segment `inboundWebhook` appears on no Cisco page** (verified live 2026-07-27 across `variable-management-in-flows`, `inbound-webhooks`, `configure-fulfilment-flows-for-ai-agent-actions` and `ai-agent-node`). Cisco documents only the general shape `$(n[nodeID].[nodeType].[fieldName])` and, for inbound webhooks, shows dot-notation over the parsed payload. **This is not evidence the examples are wrong** — `inboundWebhook` may well be the `[nodeType]` your tenant emits; nothing crawled confirms or refutes it, and only a live tenant's variable picker can settle it. **Owner: `webex-connect.md` § Variable Picker → Inbound webhook payload variables**, which wins on any disagreement. Confirm in the variable picker; do not type it from memory.

### `n2` — HTTP Request (Customer Lookup)

| Field | Value | Owner |
|---|---|---|
| **Method** | `GET` | [`webex-connect.md` § HTTP Request Node -- GET Requests] |
| **URL** | `https://{api-base-url}/customers?id=eq.$(n1.inboundWebhook.customer_id)` | URL shape [`webex-connect.md` § URL Format]; the `inboundWebhook` segment carries the hedge above |
| **Headers** | `Content-Type: application/json`, plus your backend's auth header and an `Accept` header if the backend varies its response shape | [`webex-connect.md` § HTTP Request Node -- GET Requests → Headers] |
| **Connection Timeout** | Max **20,000 ms** from release v5.6.3 onwards | [`webex-connect.md` § Timeouts and the `onTimeout` edge] |
| **Request Timeout** | Max **20,000 ms** from release v5.6.3 onwards | [`webex-connect.md` § Timeouts and the `onTimeout` edge] |

Populate the **Output Variables** tab with **Import from Sample** → paste a sample JSON response into the **Data Parser** dialog → **Parse** → select the key paths → **Import** [`webex-connect.md` § Output Variables Tab]. Output variable names may use only **alphabets, numbers, underscores, hyphens, and spaces** [same owner].

Extract these — the rest of the flow reads them as `$(n2.…)`. The column set is owned by § Customer Preference Lookup → Database Schema Pattern above:

| Output variable | Used by |
|---|---|
| `preferred_channel` | `n3` routing key |
| `phone` | `n4` SMS, `n6` Call User, `n7` RCS Capability, `n9` RCS Message, `n12` WhatsApp |
| `email` | `n5` Email |
| `abc_user_id` | `n11` Apple Messages destination |
| `abc_session_active` | `n10` session gate |
| `order_number`, `location_name` | Message bodies on every channel |

Four built-in outputs are emitted in addition to the key paths you extract: `https.statusCode`, `https.statusText`, `https.responseBody`, `https.responseHeaders` — referenced with the node prefix, e.g. `$(n2.https.statusCode)` [`webex-connect.md` § Built-in Output Variables].

⚠ Query parameters are URL-encoded on the wire — spaces become `+` and special characters are percent-encoded. This matters for PostgREST-style filters such as `ilike.*value*` [`webex-connect.md` § Query Parameter Encoding].

### `n3` — Branch (Channel Router)

**Input Variable:** `$(n2.preferred_channel)`. The Branch node's official operator list is **15** — Equals, Not equals, Less than, Greater than, Less than or equals, Greater than or equals, Regular expression (RegEx), Equals ignore case, Contains, Contains ignore case, In, Not in, Starts with, Ends with, Between — and **AND / OR** combine multiple conditions per branch [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration].

| Branch | Operator | Value | Routes to |
|---|---|---|---|
| 1 | Equals | `sms` | `n4` Send SMS |
| 2 | Equals | `email` | `n5` Email |
| 3 | Equals | `voice` | `n6` Call User |
| 4 | Equals | `rcs` | `n7` RCS Capability |
| 5 | Equals | `apple` | `n10` Branch (session gate) |
| 6 | Equals | `whatsapp` | `n12` WhatsApp |
| Default | None of the above | — | `n13` Send SMS |

The node also emits `branch.output`, returning `True` or `False` [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration].

⚠ **`Equals` is case-sensitive — `SMS` does not match `sms`.** Normalize `preferred_channel` to lowercase in your database. If you cannot, use **`Equals ignore case`** instead, which the Branch node's 15-operator list does include [same owner]. Do **not** copy that spelling to a Start node trigger condition: the Start node spells the same operator `Equals ignore-case` and publishes a **different, 13-operator** list. That difference is genuine in Cisco's own text — do not normalise the spellings across the two nodes [`webex-connect.md` § Trigger Conditions].

### `n4` — Send SMS (the `sms` branch)

| Field | Value | Owner |
|---|---|---|
| **Destination Type** | `msisdn` | [`connect-sms.md` § SMS Node → Required Fields] |
| **Destination** | `$(n2.phone)` — E.164 with country code | [`connect-sms.md` § SMS Node → Required Fields] |
| **From Number** | Select a provisioned sender ID, long code, or short code from the dropdown | [`connect-sms.md` § SMS Node → Required Fields] |
| **Message Type** | `Text` | [`connect-sms.md` § SMS Node → Message Types] |
| **Message** | `Your order $(n2.order_number) is ready at $(n2.location_name).` | [`connect-sms.md` § SMS Node → Required Fields] |
| **Wait For** | `Gateway Submit` | [`connect-sms.md` § SMS Node → Advanced Options] |

Message length is **two numbers, not one**: a hard cap of **4,000 characters** and a Cisco *recommendation* to stay **below 450** for deliverability. Going over 450 is allowed and will send [`connect-sms.md` § Message length — two numbers, do not confuse them]. ⚠ Do not "correct" 4,000 back to the superseded 1,024 figure without a fresh read of the Cisco page [same owner].

⚠ **The SMS node has no output variable for the recipient number and no segment-count variable.** To reference the destination downstream, reuse the value you supplied in the **Destination** field [`connect-sms.md` § SMS Node → Output Variables].

### `n5` — Email (the `email` branch)

| Field | Value | Owner |
|---|---|---|
| **Destination Type** | `Email ID` | [`connect-email.md` § Email Node Configuration → Required Fields] |
| **Destination ID** | `$(n2.email)` — the field is **Destination ID**, not "Destination" | [`connect-email.md` § Email Node Configuration → Required Fields] |
| **From Email** | **Disabled field** — auto-populated from the email app asset. Cannot be typed | [`connect-email.md` § Email Node Configuration → Required Fields] |
| **Subject** | `Order $(n2.order_number) Ready for Pickup` | [`connect-email.md` § Email Node Configuration → Required Fields] |
| **Email Type** | `HTML` — note this **renames the Message field to HTML Content** and surfaces a **Fallback Text** textbox | [`connect-email.md` § Email Node Configuration → Required Fields] |
| **Wait For** | `Gateway Submit` | [`connect-multi-channel.md` § Wait For Settings by Channel; label caveat in `connect-email.md` § Wait For Setting] |

⚠ **Character-set restriction.** AWS SES does not support SMTPUTF8 (RFC 6531): the part of the address before the `@` may contain only 7-bit ASCII, and a non-ASCII domain part must be Punycode-encoded (RFC 3492) [`connect-email.md` § Email Node Configuration → Required Fields].

### `n6` — Call User + Voice Node Group (the `voice` branch)

| Field | Value | Owner |
|---|---|---|
| **Destination Type** | `msisdn` | [`webex-connect-advanced.md` § Call User Node (Initiates the Call) → Required Fields] |
| **Destination** | `$(n2.phone)` — E.164 | [same owner] |
| **From Number** | Select a provisioned voice-enabled number, or choose **Dynamic** and supply a variable | [same owner] |
| **Expiry Time** | Seconds, or a UTC date/time — Webex Connect **strongly advises** setting one | [`webex-connect-advanced.md` § Call User Node → Optional Fields] |
| **Callback Data** | Limited to **2 KB** — exceeding it causes `onPolicyFail` | [same owner] |

Adding the Call User node **auto-creates** the Voice Node Group its `onAnswer` edge connects to; Call User itself *"cannot exist within the Voice Node Group"* [`webex-connect-advanced.md` § Call User Node (Initiates the Call); § Nodes That Must Be OUTSIDE the Group]. Put a **Play** node inside the group:

| Play field | Value | Owner |
|---|---|---|
| **TTS Processor** | Azure — the only supported engine in Connect | [`webex-connect-advanced.md` § Play Node (Voice Node Group) → TTS Settings] |
| **Voice Type** | Neural (Standard is deprecated) | [same owner] |
| **Input Format** | **Plain Text** (3,000 character limit) or **SSML** (6,000 character limit) | [same owner] |
| Text | `Hello. Your order $(n2.order_number) is ready for pickup at $(n2.location_name). Thank you.` | — |

⚠ **3,000 / 6,000 are the Play node's limits.** The **2,000**-character limit belongs to the Voice Node Group's **Answering Machine Detection** prompt and does not apply here; likewise the Play limits do not apply to the AMD prompt [`webex-connect-advanced.md` § Answering Machine Detection (AMD)]. ⚠ `docs/playbooks/multi-channel-routing.md` § 3 → Voice Path states "TTS messages are limited to 2,000 characters" for the Play node — **that disagrees with the owner above and the owner wins.** Logged, not silently corrected.

⚠ **The call drops if you wire an inner node to a group edge.** *"The call terminates immediately when a node inside the group connects to a Voice Node Group edge"* — keep every node of a voice loop inside the group [`webex-connect-advanced.md` § Voice Node Group Rules]. **Wait for** and **Delay** nodes are not supported inside the group [same owner].

⚠ **Azure Neural TTS, not Cisco TTS.** Cisco TTS exists only in WxCC Flow Designer, a separate platform — the two SSML tag sets are not interchangeable [`webex-connect-advanced.md` § Play Node (Voice Node Group) → TTS Settings].

### `n7` → `n8` → `n9` — RCS (Capability Probe, Gate, Send)

**`n7` RCS Capability:**

| Field | Value | Owner |
|---|---|---|
| **Mobile Number** | `$(n2.phone)` — E.164 | [`connect-rcs.md` § RCS Capability Node → Configuration Fields] |
| **Force Refresh** | **`false`** — set it explicitly. **The UI defaults to `true`**, the live network check (3–6 s). `false` is the 7-day cached lookup (near-instant) | [same owner] |
| **Carrier** | An **integer**, not a string carrier code (UI placeholder `302`). Leave blank if unknown | [same owner] |

**`n8` Branch — the rich-capability gate.** Condition: `rcs.enabled` Equals `true` **AND** `rcs.version` Equals `up2`. `rcs.enabled` = `true` alone only proves *basic* RCS — a device on `rcs.version` = `up1` has text only, not rich cards or carousels [`connect-rcs.md` § Critical: `enabled` vs `version`]. `rcs.version` values are `up1`, `up2`, `disabled` [`connect-rcs.md` § RCS Capability Node → Output Variables].

> ⚠️⚠️⚠️ **PLATFORM TYPO — DO NOT "FIX" THESE SPELLINGS.** If you extend the gate to check a rich-content capability, the variable is `rcs.capabilties.richcard` — **`capabilties`, missing the "i"** — and the carousel one uses a **different typo again**: `rcs.capabilites.richcardCarousel` [`connect-rcs.md` § RCS Capability Node → Output Variables]. A Branch condition typed with the correctly-spelled `rcs.capabilities.richcard` **never matches**: the flow builds, deploys, and runs with no error, it just silently takes the wrong path forever. **Never type these names by hand — copy the exact name from the variable picker**, and never "correct" them here [same owner].

**`n9` RCS Message:**

| Field | Value | Owner |
|---|---|---|
| **Destination Type** | `MSISDN` — uppercase, node-specific. The alternative is `Customer Id` with a lowercase "d". Do not normalise either | [`connect-rcs.md` § RCS Message Node → Required Fields] |
| **Destination** | `$(n2.phone)` | [same owner] |
| **Message Type** | `Rich Card` (also valid: `Text`, `File`, `Carousel Card`, `Typing Indicator`) | [same owner] |
| **Title** | `Order $(n2.order_number) is ready` — max **200 characters** | [`connect-rcs.md` § Message Types → Rich Card (Standalone)] |
| **Description** | Max **2,000 characters** | [same owner] |
| **Suggestions** | Up to **4** per card; each chip label max **25 characters** | [`connect-rcs.md` § Message Types → Rich Card (Standalone); § Suggestion Types] |
| **Wait For** | `Gateway Submit` (also available: `Delivery Report`, `Read Receipts`) | [`connect-rcs.md` § RCS Message Node → Optional Fields] |

At least one of media, title, or description is required; total card payload limit **250 KB** [`connect-rcs.md` § Message Types → Rich Card (Standalone)]. Output variables are prefixed **`send.`** — note `send.sentDateTime`, "sen**t**", not "send" [`connect-rcs.md` § RCS Message Node → Output Variables].

### `n10` → `n11` — Apple Messages (Session Gate, Send)

**`n10` Branch — the session gate.** Condition: `$(n2.abc_session_active)` Equals `true`. Apple Messages requires an **active customer session** — you cannot cold-send, and **Connect exposes no session-check API**, so `abc_session_active` is a flag *you* maintain in your own database (§ Customer Preference Lookup → Database Schema Pattern).

**`n11` Apple Messages for Business:**

| Field | Value | Owner |
|---|---|---|
| **Destination Type** | `AbcUser Id` | [`connect-apple-messages.md` § Node Configuration → General Fields] |
| **Destination** | `$(n2.abc_user_id)` — the customer's `abcId` opaque ID | [same owner] |
| **Message Type** | `Rich Link` (also valid: Text, Text with Attachments, List Picker, Time Picker, Payment, New Authentication, iMessage App, Quick Reply, Form Message) | [same owner] |
| **Wait For** | `GW submit` — **the exact UI label; it is not "Gateway Submit" on this node** | [`connect-apple-messages.md` § Node Configuration → Wait For Options] |

⚠ **No Delivery Report option exists on this node** — Apple does not provide delivery or read receipts to MSPs, so `onSuccess` means "submitted to Apple's servers", **not** "delivered to device" [`connect-apple-messages.md` § Node Configuration → Wait For Options; § Exit Paths].

⚠ **UNRESOLVED — the Destination Type dropdown label.** The 2026-04-17 vetting pass, reading the **screenshots** on Cisco's node page, gives `AbcUser Id` and flags `User ID` as an error; the **prose** on that same page says *"Select **User ID** from this dropdown box."* Both can be true — prose can lag the shipped dropdown. Read the actual dropdown in your tenant; **do not flip either value on the strength of a single source** [`connect-apple-messages.md` § Node Configuration → General Fields].

ℹ **`abcUserId` vs `abcId` — two different things, both correct.** Per the owner: `abc.abcUserId` is the **inbound Receive-node output variable** (read an inbound identifier with `$(nX.abc.abcUserId)`), while `abcId` is Cisco's **prose name for the opaque value** you store and later send to — not a Connect output variable name anywhere in the docs. Both are correct in their own sense, and this example's outbound use is the *value* sense [`connect-apple-messages.md` § `abcUserId` vs `abcId` — two different things, both correct]. § Multi-Channel Flow Structure and § Apple Messages (Session Check + Fallback) above carried the older "UNRESOLVED" framing until 2026-07-27 and now match this owner. ⚠ **The Destination Type dropdown label is a separate question and remains open** — see the `n11` table above.

### `n12` — WhatsApp (the `whatsapp` branch)

| Field | Value | Owner |
|---|---|---|
| **Destination Type** | `WA ID` — capital `D`, node-specific. The alternative is `Customer ID`, also capital `D` | [`connect-whatsapp.md` § WhatsApp Node → Required Fields] |
| **Destination** | `$(n2.phone)` — E.164 with country code | [same owner] |
| **Message Type** | `Template` (the full valid set: `Text`, `Media`, `Template`, `Location`, `Contact`, `List Messages`, `Reply Buttons`) | [same owner] |
| Template parameters | `$(n2.order_number)`, `$(n2.location_name)` — flow-builder syntax is `$(nX.variableName)` | [`connect-whatsapp.md` § Template Messages → Template Parameters] |
| **Wait For** | `Gateway Submit` (also available: `None`, `Delivery Report`, `Read`) | [`connect-whatsapp.md` § WhatsApp Node → Wait For Setting] |

**There is no From Number field on this node** — it is configured at the asset level [`connect-whatsapp.md` § WhatsApp Node → Required Fields].

⚠ **`Template` is required here because this is a business-initiated notification.** What the node may send is governed by the **24-hour session window**, not by a message category: inside the window (customer messaged within the last 24 hours) **all** message types are allowed; outside it, and for any business-initiated message with no prior customer message, **Template only**. Sending a free-form type outside the window returns **error 7710** [`connect-whatsapp.md` § 24-Hour Session Window]. Templates are created in **Tools > Templates**, where **Save** submits them to **Meta** — Meta does the approving, not Connect — and only **approved** templates appear in the node's dropdown [`connect-whatsapp.md` § Template Messages → Approval Process].

> ⚠ **There is no Message Type called "session message".** The seven values listed above are the complete set. The 24-hour free-form window is a **constraint on which of those types you may use**, not a type of its own [`connect-whatsapp.md` § WhatsApp Node → Required Fields].

⚠ **Destination Type casing is node-specific across all three nodes in this example and every spelling is live.** WhatsApp: `WA ID` / `Customer ID`. RCS Message: `MSISDN` / `Customer Id`. Call User: `msisdn` / `Customer Id`. All are correct in their own node — **never normalise one node's spelling onto another**; a prior audit pass proposed exactly that and would have introduced a real bug [`connect-whatsapp.md` § WhatsApp Node → Required Fields].

### Complete Exit-Path Wiring

**Every node event must be wired separately** — *"there may be multiple node events associated with the same node (e.g., onSuccess, onError, onPolicyFailure, etc.). You will need to complete this step for all such events separately."* [`webex-connect.md` § Every node event must be wired separately]. Wiring only `onError` is the single most common way this flow leaks. The exit counts differ per channel, so take each set from its owner rather than assuming a shape.

| Node | Exit | Wire to | Owner of the exit set |
|---|---|---|---|
| `n2` HTTP Request | `onSuccess` | `n3` | [`webex-connect-advanced.md` § Error Handling on HTTP Request Nodes → Exit Paths] — **3 exits** |
| | `onError` | `n13` | |
| | `onTimeout` | `n13` | |
| `n3` Branch | 6 channel edges | `n4` / `n5` / `n6` / `n7` / `n10` / `n12` | [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration] — one edge per branch **+ "None of the above" + `onError`** |
| | `None of the above` | `n13` | |
| | `onError` | `n13` | |
| `n4` Send SMS | `onSuccess` | End | [`connect-sms.md` § SMS Node → Exit Paths] — **4 exits** |
| | `onError` | End | |
| | `onPolicyFail` | End | |
| | `onTimeOut` | End | |
| `n5` Email | `onSuccess` | End | [`connect-email.md` § Exit Paths] — **5 exits** |
| | `onError` | `n13` | |
| | `onInvalidData` | `n13` | |
| | `onPolicyFail` | `n13` | |
| | `onTimeout` | `n13` | |
| `n6` Call User | `onAnswer` | Voice Node Group | [`webex-connect-advanced.md` § Call User Node (Initiates the Call) → Exit Paths (Events)] — **8 exits** |
| | `onError` | `n13` | |
| | `oncallfail` | `n13` | |
| | `onnoanswer` | `n13` | |
| | `onbusy` | `n13` | |
| | `onreject` | `n13` | |
| | `onPolicyFail` | `n13` | |
| | `onExpiry` | `n13` | |
| Play (inside the group) | `onSuccess` | End | [`webex-connect-advanced.md` § Play Node (Voice Node Group) → Exit Paths] — **2 exits** |
| | `onError` | End | |
| `n7` RCS Capability | `onSuccess` | `n8` | [`connect-rcs.md` § RCS Capability Node → Exit Paths] — **2 exits** |
| | `onError` | `n13` | |
| `n8` Branch (rich gate) | `enabled` + `up2` | `n9` | [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration] |
| | `None of the above` | `n13` | |
| | `onError` | `n13` | |
| `n9` RCS Message | `onSuccess` | End | [`connect-rcs.md` § RCS Message Node → Exit Paths] — **7 exits** |
| | `onSubmit` | End | |
| | `onDeliveryReportSuccess` | End | |
| | `onError` | `n13` | |
| | `onDeliveryReportFail` | `n13` | |
| | `onPolicyFail` | `n13` | |
| | `onTimeout` | `n13` | |
| `n10` Branch (session gate) | `abc_session_active` = `true` | `n11` | [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration] |
| | `None of the above` | `n13` | |
| | `onError` | `n13` | |
| `n11` Apple Messages | `onSuccess` | End | [`connect-apple-messages.md` § Exit Paths] — **exactly 3 exits** |
| | `onError` | `n13` | |
| | `onPolicyFail` | `n13` | |
| `n12` WhatsApp | `onSuccess` | End | [`connect-whatsapp.md` § Exit Paths] — **7 exits** |
| | `onSubmit` | End | |
| | `onDeliveryReportSuccess` | End | |
| | `onError` | `n13` | |
| | `onDeliveryReportFail` | `n13` | |
| | `onPolicyFail` | `n13` | |
| | `onTimeout` | `n13` | |
| `n13` Send SMS (fallback) | `onSuccess` | End | [`connect-sms.md` § SMS Node → Exit Paths] — **4 exits** |
| | `onError` | End | |
| | `onPolicyFail` | End | |
| | `onTimeOut` | End | |

**Reading that table correctly — five traps:**

1. **Which green edge actually fires depends on `Wait For`.** On `n9` and `n12`, `onSuccess` fires when Wait For = `None`, `onSubmit` when Wait For = `Gateway Submit`, `onDeliveryReportSuccess` when Wait For = `Delivery Report` [`connect-whatsapp.md` § Exit Paths; `connect-rcs.md` § RCS Message Node → Exit Paths]. Since this example sets **Gateway Submit**, `onSubmit` is the live path — but all three must still be wired. **`onSuccess` and `onSubmit` are distinct exit paths, not aliases** [`connect-rcs.md` § RCS Message Node → Exit Paths]. The SMS node has no `onSubmit`: its `onSuccess` covers both "accepted by gateway" and "delivered" [`connect-sms.md` § SMS Node → Exit Paths].
2. **`n11` has exactly three exits and no `onInvalidData`** — do not copy Email's five-exit shape onto it [`connect-apple-messages.md` § Exit Paths].
3. **Email's `onSuccess` and `onInvalidData` are UI-only** — shown in the node UI but not explicitly named in official Email node docs. Confirm both against the node in your tenant before branching on them [`connect-email.md` § Exit Paths].
4. **Call User's event casing is exact and deliberately inconsistent — do NOT normalise it.** Four events are all-lowercase (`onbusy`, `onnoanswer`, `onreject`, `oncallfail`) and four are mixed case (`onAnswer`, `onError`, `onPolicyFail`, `onExpiry`). `onNoAnswer` in mixed case is the **Call Patch** node's spelling, not Call User's [`webex-connect-advanced.md` § Call User Node (Initiates the Call) → Exit Paths (Events)]. `onExpiry` fires only when an expiry is configured, and `onPolicyFail` covers Callback Data over 2 KB.
5. ⚠ **The SMS timeout edge's casing is UNRESOLVED.** Cisco publishes three spellings — `onTimeOut` (exception-handling page heading), `ontimeout` (that same page's body), and `onTimeout` (HTTP Request and RCS Message node pages) — and never states whether the exception-handling event is even the same event as a node's exit path. Recognise all three when reading a flow, and confirm the literal label in your own tenant before writing anything that string-matches on it. This table keeps `onTimeOut` for SMS and `onTimeout` for Email/RCS/WhatsApp/HTTP because that is each owner's existing spelling — a retained value, **not** a verified recommendation [`connect-sms.md` § SMS Node → Exit Paths].

### The Shared SMS Fallback (`n13`)

Fourteen edges converge on `n13`. That is fine — but the destination has to resolve on **all** of them, and three of those edges exist precisely because `n2` failed.

| Field | Value | Why |
|---|---|---|
| **Destination Type** | `msisdn` [`connect-sms.md` § SMS Node → Required Fields] | — |
| **Destination** | `$(n1.inboundWebhook.customer_phone)` | Sourced from the **webhook payload**, not `$(n2.phone)` — the `n2` `onError` / `onTimeout` / 404 legs have no `n2` output. Carries the `inboundWebhook` hedge above |
| **Message** | A single generic body covering every path | There is one fallback node; it cannot know which channel failed unless you set a custom variable on each leg |

If you need per-channel fallback copy, set a **custom flow variable** on each failing leg with a **Set Variable** transition action (or an Evaluate script) and interpolate it into the fallback body — custom variables are referenced with **no node prefix**, e.g. `$(failed_channel)`, and must first be declared in **Flow Settings > Custom Variables** [`webex-connect-advanced.md` § Branch Node (Conditional Logic) → Example: HTTP Error Routing; § Transition Actions (Set Variable / Debug Logging)].

Voice is the one channel where the fallback is a **judgment call, not a default**: wiring `onbusy` / `onnoanswer` / `onExpiry` to SMS guarantees delivery but double-notifies a customer who simply did not pick up. `docs/playbooks/multi-channel-routing.md` § 4 → Voice Fallback (Optional) owns that decision — fall back for critical notifications, terminate for the rest.

### What "End" Means Here

Every `End` in the sketch and the table above is a **terminating edge**, not a palette node. *"There is no 'End node' you drag from the palette for this."* You drag the edge from the node's right-edge dot *"and release it in the free space"*, which opens a configuration window where you select the node event and its corresponding flow result [`webex-connect.md` § How you actually create a terminating edge]. Documented flow result codes include **102 — Flow completed with an error** and **103 — Flow ended due to an interruption** [`webex-connect.md` § Flow result codes on termination]. Connector colours are semantic: *"green for continuation, orange for time-bound events, red for errors"* [same file, § Connector colour semantics].

⚠ **UNRESOLVED — "End node" as a term.** § Multi-Channel in AI Agent Flows below refers to an **End (END FLOW)** node, and the sketches throughout this file draw `→ End` as if it were one. Cisco's own palette inventory lists no End node [`webex-connect.md` § Node Palette Inventory], and the terminating-edge mechanism above is what the docs describe. Whether the tenant UI additionally surfaces a literal "END FLOW" element is not settled by anything crawled — treat `End` in this file as shorthand for the terminating edge, and confirm the UI affordance in your tenant. Do not resolve this by editing either side on plausibility.

### What This Example Does Not Contain

| Absent | Why |
|---|---|
| **Flow Outcomes** | It is a **flow-level settings area reached from the Flow Settings button**, not a canvas node — there is nothing to wire an edge to [`webex-connect.md` § Flow Outcomes (Flow Settings — NOT a node)]. It exists to hand data back to an **AI agent**. A webhook-triggered notification flow has no agent to hand data to, so it plays **no part in this example at all**. If you are looking for it, you want § Multi-Channel in AI Agent Flows below |
| **The 30-second budget** | That timeout is the AI agent action flow's. This flow is not one, so the RCS path's extra nodes are not a timing risk here — set `Force Refresh: false` for latency, not for survival |
| **A Receive node** | Nothing in this flow waits for an inbound customer message. Receive belongs to two-way messaging flows |
| **An AI Agent node** | Process Message / Close Session belong to digital inbound *conversation* flows — `digital-inbound.md` is their owner |

### Testing

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {your_service_key}" \
  -d '{"customer_id": "CUST-1234", "order_id": "ORD-4521", "customer_phone": "+15551234567"}' \
  "https://{your-webhook-url}"
```

Authentication on the header is **optional** for inbound webhooks [`webex-connect.md` § Inbound webhooks] — the full mechanism set (service keys, JWT, HMAC signature validation, IP allowlisting, rotation) is owned by `connect-auth.md`, and the build procedure by `docs/playbooks/webhook-triggers.md`. Response codes for the webhook call itself are owned by `connect-response-codes.md`; ⚠ do **not** reconcile those against a channel's delivery codes — the two are separate numbering spaces that both use `7xxx` with different meanings.

Exercise **one branch per test run** by changing `preferred_channel` on the customer record between calls, and verify each channel's failure legs by pointing the destination at an invalid value. A branch you never fired is a branch you never wired.

---

## Multi-Channel in AI Agent Flows

When using channels as side-effects within the 30-second agent flow timeout:

```
Start (Trigger category: AI Agent — presents as "Configure AI Agent Event")
  → HTTP GET → HTTP POST → Branch (preferred_channel)
    → rcs      → RCS Capability → Branch → RCS Message (or SMS) → End
    → email    → Email          → End
    → sms      → SMS            → End
    → apple    → Apple Messages → End
    → whatsapp → WhatsApp       → End
```

⚠ **There is no Receive node in an AI agent action flow.** The first node is the **Start** node with **Trigger category: AI Agent**, which then presents as **Configure AI Agent Event**. The event auto-populates as *"Trigger from AI Agent to initiate flow"* — you do not type an event name, and nothing has to match the action name in AI Agent Studio [`webex-connect.md` § AI agent action flows].

⚠ **Flow Outcomes is not a node — there is nothing on the canvas to wire an edge to.** It is a **flow-level settings area** reached from the **Flow Settings** button on the Flow Builder page [`webex-connect.md` § Flow Outcomes (Flow Settings — NOT a node)]. Every branch above therefore ends at an **End (END FLOW)** node; the data the agent receives comes from the settings area, not from the canvas.

**Timeout warning:** The RCS path (Capability + Branch + RCS/SMS) adds 3 nodes minimum. Combined with HTTP nodes, test that the full flow stays under 30 seconds. Set `Force Refresh: false` on the Capability node — **the UI defaults to `true`**, the slow live check (3–6s), so this must be set explicitly [`connect-rcs.md` § RCS Capability Node → Configuration Fields].

**Error handling:** Wire every channel's failure exits (not just `onError` — see § Implementation Pattern) to an **End** node so the flow always terminates cleanly and the agent gets its data back, even if the notification fails. The returned data is configured in **Flow Settings > Flow Outcomes** on the **Last Execution Status** row — enable **Notify > Notify AI Agent** and enter the key/value pairs. There is **one key-set per flow**, not one per branch [`ai-agent-studio.md` § Where Flow Outcomes Lives in Webex Connect]. Nothing here is wired on the canvas.

---

## Channel Selection Decision Matrix

| Factor | Best Channel |
|--------|-------------|
| Customer has Android with RCS | RCS (rich cards, suggestions, read receipts) |
| Customer has iOS with active session | Apple Messages (rich links, pickers, Apple Pay) |
| Customer has iOS, no session | SMS (can't initiate Apple Messages) |
| Customer uses WhatsApp | WhatsApp (`Template` for proactive; free-form types for interactive, inside the 24-hour window) |
| Customer has email, prefers written record | Email (HTML with attachments) |
| Urgent, must reach immediately | Voice (phone call) |
| Unknown device / no preference | SMS (universal) |
| High-value notification, wants rich + fallback | RCS → SMS fallback chain |

---

## Provisioning Checklist for Multi-Channel

| Channel | What's Needed | Where to Configure |
|---------|--------------|-------------------|
| SMS | Phone number or Sender ID with SMS feature | Assets > Numbers |
| Email | Email asset (AWS SES or SMTP), domain verification, SPF/DKIM/DMARC | Assets > Apps > Email |
| RCS | RCS app/asset, brand configuration, carrier approval | Assets > Apps > RCS. ⚠ **This navigation path is not confirmed by Cisco** — no crawled page confirms an `Assets > Apps` route for RCS *asset* setup (the documented `Tools > Templates` route covers RCS *Templates*). Confirm in your tenant or with your account manager [`connect-rcs.md` § Provisioning Prerequisites → RCS App/Asset Setup] |
| Apple Messages | Apple Business Register enrollment, MSP linkage | `register.apple.com/business-chat` + **Apps** [`connect-apple-messages.md` § Provisioning Prerequisites] |
| WhatsApp | WABA (WhatsApp Business Account), phone number verification, message template approval | Asset: **Assets > Apps > Configure New App > WhatsApp** (embedded sign-up, authenticated via Facebook login) [`connect-whatsapp.md` § Provisioning Prerequisites]. Templates: created in **Tools > Templates** in Webex Connect — **Save** submits them to Meta, which does the *approval* [`connect-whatsapp.md` § Approval Process] |
| Voice | Voice-enabled phone number | Assets > Numbers (Voice feature) |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Customer gets both RCS and SMS | RCS Capability check succeeded but message also fell through to SMS fallback | Ensure Branch node routes exclusively — don't wire RCS success AND default to SMS |
| Apple Messages `onError` not caught | Forgot to wire `onError` to fallback | Always wire `onError` on Apple Messages to SMS fallback |
| Preferred channel field is null | Customer record has no preference | Default branch → SMS in the Branch node |
| RCS capability check adds latency | `Force Refresh: true` causes 3–6s live lookup — **and `true` is the UI default**, so this is what you get by leaving the field alone | Set `Force Refresh: false` explicitly (7-day cached lookup, near-instant). Because the default is the slow option, leaving the field alone is the wrong choice in an AI agent flow [`connect-rcs.md` § RCS Capability Node → Configuration Fields] |
| Rich-content Branch never matches | Condition typed as the correctly-spelled `rcs.capabilities.richcard` — the platform emits `rcs.capabilties.richcard`, missing the "i" | Copy the exact name from the **variable picker**; never type it. The flow builds, deploys, and runs with no error — it just silently takes the wrong path forever [`connect-rcs.md` § RCS Capability Node → Output Variables] |
| Multi-channel flow exceeds 30s in agent | Too many nodes in RCS path + HTTP lookups | Simplify: skip capability check in agent flows, use SMS only, or move notification to a separate webhook-triggered flow |
| Apple session check is stale | Session closed between DB check and send | Wire `onError` to SMS fallback; update session status on `CONVERSATIONCLOSED` events. ⚠ The event name and the accompanying HTTP 410 Gone are **unverified** — neither appears on help.webexconnect.io [`connect-apple-messages.md` § Verification Status] |
| Branch conditions case-sensitive | `SMS` ≠ `sms` | Normalize `preferred_channel` values in your database (lowercase) |
| WhatsApp template rejected at runtime | Template not approved or was paused/disabled by Meta | Check template status in **Tools > Templates in Webex Connect** before going live — that is where templates are managed, and only **approved** templates appear in the WhatsApp node dropdown. *Approval* is Meta's, not Connect's [`connect-whatsapp.md` § Approval Process] |
| Free-form WhatsApp message sent outside the 24-hour window | Customer hasn't messaged in the last 24 hours | Returns **error 7710**. Track the window in your DB; fall back to a `Template` message or SMS outside it [`connect-whatsapp.md` § 24-Hour Session Window] |
| WhatsApp `onError` not caught | Forgot to wire `onError` to fallback | Always wire `onError` on WhatsApp node to SMS fallback — recipient may not have WhatsApp |
| Same message sent to wrong channel | Variable picker wrong node number | Always use variable picker; verify node numbers after adding/removing nodes |

---

## References

- [Branch Node](https://help.webexconnect.io/docs/branch-node) — conditional routing
- [SMS Node](https://help.webexconnect.io/docs/send-sms) — see also `connect-sms.md`
- [Email Node](https://help.webexconnect.io/docs/email-node) — see also `connect-email.md`
- [RCS Capability + Message](https://help.webexconnect.io/docs/rcs-capability-node) — see also `connect-rcs.md`
- [Apple Messages Node](https://help.webexconnect.io/docs/apple-messages-for-business) — see also `connect-apple-messages.md`
- [WhatsApp Node](https://help.webexconnect.io/docs/whatsapp) — see also `connect-whatsapp.md`
- [Call User Node](https://help.webexconnect.io/docs/voice-call-user) — owned by `webex-connect-advanced.md` § Call User Node (Initiates the Call); build sequence in `docs/playbooks/outbound-voice.md`

## See Also

- [connect-sms.md](connect-sms.md) — the SMS channel in a multi-channel chain
- [connect-whatsapp.md](connect-whatsapp.md) — the WhatsApp channel in a multi-channel chain
- [connect-rcs.md](connect-rcs.md) — the RCS channel in a multi-channel chain
- [connect-apple-messages.md](connect-apple-messages.md) — the Apple Messages channel in a multi-channel chain
- [webex-connect.md](webex-connect.md) — the Connect flow basics
