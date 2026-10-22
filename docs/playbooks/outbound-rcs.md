# Outbound RCS Notification Playbook

## Overview

This playbook covers how to build outbound RCS (Rich Communication Services) notifications in Webex Connect — specifically, webhook-triggered flows that check device capability, send a rich card or text message via RCS, and fall back to SMS when the recipient doesn't support RCS. This is the pattern for order-ready notifications, appointment confirmations, and promotional alerts on Android devices.

**Key distinction from SMS flows:** RCS flows require a **two-node pattern** — an RCS Capability check before the RCS Message node. You cannot blindly send RCS; not every Android device supports it, and no iOS devices do. Always wire an SMS fallback.

**Flow structure:**

```
Start (Webhook)
  → [Optional: HTTP Request]
  → RCS Capability (check recipient)
    → onSuccess → Branch (rcs.enabled == true AND rcs.version == "up2")
      → [Yes] → RCS Message (rich card / text) → End
      → [No]  → SMS (plain text fallback) → End
    → onError → SMS (safe fallback) → End
```

For webhook infrastructure (Start node configuration, payload parsing, authentication, testing), see `webhook-triggers.md`. This playbook focuses on the RCS-specific nodes and the capability-check-then-branch pattern.

---

## 1. RCS Capability Check

The **RCS Capability** node verifies whether the recipient's device can receive RCS messages. This MUST run before every RCS Message node.

### Step-by-Step Configuration

1. Drag an **RCS Capability** node from the Channels palette onto the canvas
2. Wire the Start node (or HTTP Request node) output to this node's input
3. Configure the fields:

> **Owner: `connect-rcs.md` § RCS Capability Node → Configuration Fields.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Field | Value |
|-------|-------|
| **Mobile Number** | Variable from webhook payload: `$(n1.inboundWebhook.customer_phone)` — must be E.164 format |
| **Force Refresh** | Set it to `false` explicitly — **the UI defaults to `true`**. `false` = 7-day cached lookup (near-instant). `true` = live network check (3–6s latency). Because the default is the slow option, leaving this field alone is the wrong choice |
| **Carrier** | Leave blank unless you know the recipient's carrier. Takes an **integer** value (e.g., `302`) — not a string carrier code |

*(Provenance: the 7-day cache window, the 3–6s live-check latency, and the `true` default all come from the RCS findings review — the same evidence behind `connect-rcs.md` and `webex-connect-advanced.md`. They are outside the scope of the Webex Connect documentation crawl, which covered the core node pages only.)*

### Output Variables

After this node runs, the following variables are available for branching:

> **Owner: `connect-rcs.md` § RCS Capability Node → Output Variables.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. It also carries `rcs.carrierCode`, which this flow does not use.

**Core variables:**

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `rcs.enabled` | Device has any RCS support | `true` / `false` |
| `rcs.version` | RCS version level | `up1`, `up2`, `disabled` |
| `rcs.platform` | RCS platform provider | `Google`, `Samsung` |
| `rcs.msisdn` | E.164 formatted number | `+15551234567` |

**Per-feature capability booleans** (check these for specific rich content):

> ⚠️ **STOP — PLATFORM TYPO WARNING — DO NOT "FIX" THESE SPELLINGS** ⚠️
>
> The RCS Capability node emits variable names that are **misspelled on the platform**, and inconsistently so — two different typos appear (`capabilties` and `capabilites`), and one variable is spelled correctly.
>
> **Why this matters:** a Branch condition typed with the correctly-spelled `rcs.capabilities.richcard` will **never match**. The flow builds, deploys, and runs with no error — it just silently takes the wrong path forever.
>
> 1. **NEVER type these names manually.** Run the RCS Capability node, then copy the exact name from the **variable picker**.
> 2. **NEVER "correct" the spellings in the table below.** They are wrong on purpose, because the platform is wrong.
> 3. Rows marked **spelling unverified** have **no evidence either way** — Cisco's page neither confirms nor denies them. Treat them as suspect and confirm each in the variable picker before use.

| Variable | Feature | Spelling status |
|----------|---------|-----------------|
| `rcs.capabilties.richcard` | Standalone rich card | ⚠️ **Verified MISSPELLED** (`capabilties` — missing the "i"). Do not change |
| `rcs.capabilites.richcardCarousel` | Carousel cards | ⚠️ **Verified MISSPELLED** (`capabilites` — a *different* typo from the row above). Do not change |
| `rcs.capabilites.dialPhoneNumber` | Dial phone action | ⚠️ **Verified MISSPELLED**, but **which** typo is unresolved: Cisco's page shows `rcs.capabilites.dialPhoneNumber` in the body text and `rcs.capabilties.dialPhoneNumber` in the sidebar. Both are misspelled; which one the node emits is unknown. Copy from the variable picker |
| `rcs.capabilities.openUrl` | Open URL action | ✅ **Verified spelled CORRECTLY** (body text and sidebar agree). Do not change |
| `rcs.capabilities.calendarEvent` | Calendar event action | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.shareLocation` | Share location | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.viewLocation` | View location | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.chat` | Chat | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.fileTransfer` | File transfer | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.paymentsV1` | Payments | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.videoCall` | Video call | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.revocation` | Message revocation | ❓ Spelling unverified — confirm in the variable picker |

### Critical: `enabled` vs `version`

> **Owner: `connect-rcs.md` § RCS Capability Node → Critical: `enabled` vs `version`.** Reproduced verbatim so this page works standalone; the reference doc wins on any disagreement. **This rule fails silently when you get it wrong** — the flow builds, deploys, and runs, and simply delivers a degraded message forever. Do not paraphrase it.

`rcs.enabled` = `true` does **not** guarantee rich features. A device with `rcs.version` = `up1` has basic RCS (text only) — NOT rich cards or carousels. Branch on `rcs.version` = `up2` or check individual capability booleans for rich content.

**In this playbook's Branch node** that means the condition `$(nX.rcs.version)` Equals `up2` — see § 2 below.

### Exit Paths

> **Owner: `connect-rcs.md` § RCS Capability Node → Exit Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. These two are the node's **only** exit paths.

| Event | When |
|-------|------|
| `onSuccess` | Capability check completed — proceed to Branch |
| `onError` | Invalid number, network error, lookup failed — fall back to SMS |

---

## 2. Branch Node for RCS Support

After the Capability check succeeds, add a **Branch** node to route the flow based on the recipient's RCS support level.

### Step-by-Step Configuration

1. Drag a **Branch** node onto the canvas
2. Wire `RCS Capability → onSuccess` to this Branch node
3. Configure Branch condition #1 (the "RCS capable" path):

   | Condition | Operator | Value |
   |-----------|----------|-------|
   | `$(nX.rcs.enabled)` | Equals | `true` |
   | **AND** | | |
   | `$(nX.rcs.version)` | Equals | `up2` |

   Where `nX` is the RCS Capability node number (check your flow's node numbering).

   **For maximum safety with rich cards**, add a third condition: `$(nX.rcs.capabilties.richcard)` Equals `true` (note the typo in `capabilties` — use the variable picker to get the exact name; spelling status table in § 1 above, owned by `connect-rcs.md` § RCS Capability Node → Output Variables). This confirms the device specifically supports rich card rendering, not just RCS version 2.

4. Label this branch "RCS Supported" (or similar)
5. The **None of the above** exit becomes the SMS fallback path — this catches:
   - `rcs.enabled` = `false` (no RCS at all — likely iOS or older Android)
   - `rcs.version` = `up1` (basic RCS only — cannot render rich cards)
   - `rcs.version` = `disabled`

### Wiring

```
Branch
  → [RCS Supported] → RCS Message node
  → [None of the above] → SMS node (fallback)
```

**Also wire** `RCS Capability → onError` directly to the SMS fallback node. If the capability check itself fails (bad number, network issue), always fall back to SMS.

---

## 3. RCS Message Configuration

The **RCS Message** node sends the outbound notification. For notifications, **Rich Card** is the primary format — it delivers a branded, visually structured message with an image, title, description, and interactive suggestion chips.

### Step-by-Step Configuration

1. Drag an **RCS Message** node from the Channels palette
2. Wire the Branch node's "RCS Supported" exit to this node
3. Configure the required fields:

> **Owner: `connect-rcs.md` § RCS Message Node → Required Fields.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Field | Value |
|-------|-------|
| **Destination Type** | `MSISDN` (phone number) or `Customer Id` (profile ID) |
| **Destination** | `$(n1.inboundWebhook.customer_phone)` |
| **Message Type** | Select the appropriate type (see below) |

⚠ **Casing is exact and node-specific — do NOT normalise it across nodes.** The RCS Message node spells these `MSISDN` (all caps) and `Customer Id` (lowercase "d"). The Call User node uses `msisdn` / `Customer Id`; the WhatsApp node uses `WA ID` / `Customer ID`. All three are correct in their own node [`connect-rcs.md` § RCS Message Node → Required Fields].

### Message Type: Rich Card (Primary for Notifications)

Rich Card is the recommended format for notifications — it renders as a branded card with an image, title, description, and up to 4 interactive suggestion chips.

> **Owner: `connect-rcs.md` § Message Types → Rich Card (Standalone).** Reproduced here so this page works standalone; the reference doc wins on any disagreement. It also carries Thumbnail Alignment, Thumbnail URL limits, and the 250 KB total card payload cap.

| Field | Value / Details |
|-------|-----------------|
| **Card Orientation** | `VERTICAL` (most common for notifications) |
| **Media URL** | Public URL to your image — max 2,048 chars, max 500 KB |
| **Media Height** | `SHORT` (1085×310), `MEDIUM` (1080×720), or `TALL` (pixel dimensions not specified in official docs for standalone rich card) |
| **Title** | Notification headline — max 200 characters |
| **Description** | Notification body — max 2,000 characters |
| **Suggestions** | Up to 4 per card (Reply, Open URL, Dial Phone, etc.) |

**Example: Order-Ready Rich Card**

| Field | Example Value |
|-------|---------------|
| **Title** | `Your order $(n3.order_number) is ready` |
| **Description** | `Pick up at $(n3.location_name). Open today until $(n3.closing_time).` |
| **Media URL** | `https://cdn.example.com/store-photo.jpg` |
| **Suggestion 1** | Type: Open URL, Label: "Get Directions", URL: `$(n3.directions_url)` |
| **Suggestion 2** | Type: Dial Phone, Label: "Call Store", Phone: `$(n3.store_phone)` |
| **Suggestion 3** | Type: Reply, Label: "On my way", Postback: `omw_$(n3.order_number)` |
| **Suggestion 4** | Type: Calendar Event, Label: "Add Pickup", Meeting Title: `Pickup $(n3.order_number)` |

**Suggestion chip labels are limited to 25 characters.** Keep labels concise.

### Message Type: Text

For simpler notifications that don't need visual formatting:

> **Owner: `connect-rcs.md` § Message Types → Text.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Field | Value / Details |
|-------|-----------------|
| **Text** | Message content — max 1,024 characters (not confirmed in official docs; use as guidance) |
| **Suggestions** | Up to 11 suggestion chips outside the message (documented in carousel context; may vary for standalone text messages) |

### Message Type: Carousel Card

For multi-item notifications (e.g., "Your 3 items are ready"):

> **Owner: `connect-rcs.md` § Message Types → Carousel Card.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. It also carries the dynamic-carousel JSONPath pattern and an **UNRESOLVED** note on carousel media dimensions (Cisco's page states both "1080×787 recommended" and "square media dimensions required" — read it before committing to an asset size).

| Field | Value / Details |
|-------|-----------------|
| **Card Width** | `SMALL` or `MEDIUM` |
| **Media Height** | Must match across ALL cards. Recommended resolution: 1080×787 px |
| **Cards** | Min 2, max 10 |
| **Per-card fields** | Same as Rich Card |
| **Global suggestions** | Up to 11 outside the carousel |

### Message Type: File

Sends a file to the recipient.

> **Owner: `connect-rcs.md` § Message Types → File.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Field | Value / Details |
|-------|-----------------|
| **Media Content URL** | Publicly accessible direct URL |
| **File Size** | In bytes — must be greater than `0`, or the media fails to load |

| Type | Formats | Max Size |
|------|---------|----------|
| Image | BMP, GIF, JPEG (recommended), PNG | 500 KB |
| Video | MPEG-4 | 500 KB |
| Audio | MP4, M4A, MP3, WAV | 500 KB |
| PDF | PDF (v6.5.0+) | Not documented; may fail on some MaaP providers |

### Message Type: Typing Indicator

Displays a typing indicator to the recipient. No content fields required — used to signal that a response is being prepared.

See `connect-rcs.md` for the full field list, limits, and all message type options.

### Exit Paths

> **Owner: `connect-rcs.md` § RCS Message Node → Exit Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. ⚠ `onSuccess` and `onSubmit` are **distinct exit paths, not aliases** — wire them separately.

| Event | When |
|-------|------|
| `onSuccess` | Message sent successfully — wire to End |
| `onSubmit` | "Wait For: Gateway Submit" condition met — wire to End |
| `onDeliveryReportSuccess` | Delivery confirmed by carrier — wire to End |
| `onError` | Gateway rejection — **recommended:** wire to SMS fallback |
| `onDeliveryReportFail` | Delivery report returned failure — wire to SMS fallback (or log) |
| `onPolicyFail` | Expiry condition not met — wire to SMS fallback (or log) |
| `onTimeout` | Timeout period elapsed — wire to SMS fallback (or log) |

### Output Variables

> **Owner: `connect-rcs.md` § RCS Message Node → Output Variables.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

After the RCS Message node runs, these variables are available (prefixed `send.*` — note `send.sentDateTime` is "sen**t**", not "send"):

| Variable | Description |
|----------|-------------|
| `send.sentDateTime` | Timestamp when the message was sent |
| `send.gatewayTid` | Gateway transaction ID |
| `send.deliveryStatusDescription` | Delivery status description |
| `send.deliveryStatusCode` | Delivery status code |
| `send.response_data` | Raw response data from gateway |
| `send.response_interactive` | Interactive response data (for replies) |

### Wait For Setting

> **Owner: `connect-rcs.md` § Wait For Setting.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Mode | Behavior | Use in Agent Flows? |
|------|----------|---------------------|
| **Gateway Submit** | Node exits as soon as message enters gateway queue | **Yes** — fast |
| **Delivery Report** | Waits for carrier delivery confirmation | **No** — will timeout |
| **Read Receipts** | Waits for recipient to open message | **No** — will timeout |

**Always use Gateway Submit** in AI agent flows. Webhook-triggered notification flows like the one in this playbook are **not** bound by the 30-second agent-flow timeout, so they may use Delivery Report or Read Receipts when you need delivery or read confirmation.

---

## 4. SMS Fallback Path

The SMS fallback fires when the recipient doesn't support RCS or when the capability check fails. Deliver the same notification content as plain text.

### Step-by-Step Configuration

1. Drag an **SMS** node onto the canvas
2. Wire three inputs to this node:
   - Branch node → "None of the above" exit
   - RCS Capability node → `onError` exit
   - (Optional) RCS Message node → `onError` exit
3. Configure the SMS node:

| Field | Value |
|-------|-------|
| **Destination** | `$(n1.inboundWebhook.customer_phone)` |
| **Message** | Plain text version of the notification |

**Example:**
```
Your order $(n3.order_number) is ready for pickup at $(n3.location_name). Directions: $(n3.directions_url)
```

Wire `SMS → onSuccess`, `SMS → onError`, `SMS → onPolicyFail`, and `SMS → onTimeout` to End nodes.

### Alternative: API-based automatic fallback

If you are sending via the **Send Message API v2** rather than building the Branch in the flow, RCS supports automatic SMS fallback through the `options` block — all three of `smsFallback`, `smsSenderId`, and `text` are required, or the fallback silently never fires. Failed RCS messages generate transaction IDs suffixed `_fallbackrcs`. Full request shape and the GSMA FNW.11 prerequisite in `connect-rcs.md` § RCS + SMS Fallback Pattern (owner).

---

## 5. Variable Insertion

Use Connect's standard `$(nX.variableName)` syntax to insert dynamic values.

### Where Variables Work

| Context | Variable Method |
|---------|----------------|
| Text message body | `$(nX.variableName)` — direct substitution |
| Rich Card title | Use the **variable picker** in the flow builder |
| Rich Card description | Use the **variable picker** in the flow builder |
| Suggestion chip labels | Use the **variable picker** in the flow builder |
| SMS fallback text | `$(nX.variableName)` — direct substitution |

### Critical Rule

**API substitutions (`$(nX.variableName)`) apply exclusively to text field content** — NOT to rich card titles, descriptions, or suggestion labels when using the API. In the flow builder, always use the **variable picker** for all fields. Manually typed variable references in card fields may arrive empty. [`connect-rcs.md` § Variable Insertion]

### Variable Sources

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook) | `$(n1.inboundWebhook.fieldName)` | `$(n1.inboundWebhook.order_id)` |
| HTTP Request output | `$(nX.outputVar)` | `$(n3.customer_name)` |
| Capability node output | `$(nX.rcs.enabled)` | `$(n4.rcs.enabled)` |

---

## 6. Channel Prerequisites

> **Owner: `connect-rcs.md` § Provisioning Prerequisites.** Reproduced here so this page works standalone; the reference doc wins on any disagreement — and it records which of these figures Cisco confirms and which are unverified.

### RCS App/Asset Setup

1. Navigate to the RCS app configuration in Webex Connect (official docs reference **Tools > Templates** for RCS setup; the exact path may vary by platform version — confirm with your account manager)
2. Configure brand: Display Name (max 40 chars), Description (max 100 chars), Brand Color (4.5:1 contrast ratio vs white), Logo (224×224 px, JPG or PNG — Cisco publishes no logo file-size limit)
3. Add Banner Images (1440×448 px; 1080×1080 px as an alternative size is not confirmed in official docs)
4. Set Privacy Policy URL and Terms of Service URL (both required)
5. Add test phone numbers for validation
6. Submit for carrier approval — production launch requires carrier sign-off via your account manager

### Platform Requirements

- **Android only** — Android 8+ with Android Messages or Samsung Messages. No iOS support.
- Carrier must have RCS enabled in the recipient's region
- **Supported countries:** USA, Canada, UK, France, Germany, Spain, Norway, Sweden, India, Japan, Mexico, Brazil, Jordan (not verified in official docs — confirm current list with your account manager)
- Approval timeline: ~7 days for basic messaging program

### Sandbox Limitations

**RCS is NOT available in the Webex Connect Sandbox** (not explicitly confirmed in official docs — verify with your account manager). Sandbox supports only SMS, Voice, and WhatsApp. You need a full platform license to test RCS.

See `connect-rcs.md` § Provisioning Prerequisites (owner) for the remaining brand fields — contact info limits, Privacy Policy and Terms of Service URLs, and the service-provider note.

---

## 7. Complete Flow Example: Order-Ready RCS Notification

```
Start (Webhook: order_id, customer_phone)
  |
  v
HTTP Request (GET order details from DB by order_id)
  |  Output: order_number, location_name, closing_time, directions_url, store_phone
  |
  v
RCS Capability (check $(n1.inboundWebhook.customer_phone), Force Refresh: false)
  |
  |--- onSuccess ---> Branch (rcs.enabled == true AND rcs.version == "up2")
  |                      |
  |                      |--- [RCS Supported] ---> RCS Message (Rich Card)
  |                      |                            Title: "Your order $(n3.order_number) is ready"
  |                      |                            Description: "Pick up at $(n3.location_name)."
  |                      |                            Suggestions: [Get Directions] [Call Store] [On my way]
  |                      |                            |
  |                      |                            |--- onSuccess ---> End
  |                      |                            |--- onError -----> SMS (fallback) ---> End
  |                      |
  |                      |--- [None of the above] ---> SMS (fallback)
  |                                                      "Your order $(n3.order_number) is ready
  |                                                       at $(n3.location_name). Directions:
  |                                                       $(n3.directions_url)"
  |                                                      |
  |                                                      v
  |                                                     End
  |
  |--- onError ------> SMS (fallback) ---> End
```

### Webhook Payload

```json
{
  "order_id": "ORD-4521",
  "customer_phone": "+15551234567"
}
```

For webhook setup, authentication, and testing with curl, see `webhook-triggers.md`.

---

## 8. Known Gotchas

| Issue | Fix |
|-------|-----|
| Rich card renders as plain text on recipient's device | Recipient has `rcs.version` = `up1` (basic RCS only). Branch on `rcs.version` == `up2` or check `rcs.capabilties.richcard` before sending rich content |
| Capability says `enabled` but RCS Message fails | `rcs.enabled` only means basic RCS — does not guarantee rich features. Check individual capability booleans |
| Variables empty in rich card title or suggestion labels | API substitutions only apply to text content. Use the **variable picker** in the flow builder for card fields |
| SMS fallback never fires | No Branch node wired after the Capability check. Must explicitly route "None of the above" to SMS |
| Cannot test — "RCS not available" error | RCS is not available in the Webex Connect Sandbox. Requires a full platform license |
| Carousel cards display misaligned | Media Height values don't match across cards. Set identical Media Height on every card in the carousel |

> **Owner: `connect-rcs.md` § Known Gotchas and § Status Codes.** The rows above are reproduced here so this page works standalone; the reference doc wins on any disagreement and carries the full 25-code status table plus gotchas this playbook omits (`7322` provider-not-configured, `7323` carrier-lookup, `7324`/`7331` rate limits, dynamic-carousel null arrays, brand logo/color).

---

## References

- `connect-rcs.md` — full RCS node reference (all fields, limits, status codes, suggestion types)
- `webhook-triggers.md` — Start node webhook setup, authentication, payload parsing
- [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node)
- [RCS Capability Node](https://help.webexconnect.io/docs/rcs-capability-node)
- [RCS Channel Overview](https://help.webexconnect.io/docs/rcs)
- [RCS App/Asset Setup](https://help.webexconnect.io/docs/rcs-1)
- [RCS API (Send Message v2)](https://developers.webexconnect.io/reference/rcs-api)
