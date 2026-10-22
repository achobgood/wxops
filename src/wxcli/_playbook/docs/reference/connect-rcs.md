# Webex Connect — RCS Messaging Reference

<!-- ref-tag: connect-rcs-v4 -->

RCS (Rich Communication Services) Business Messaging delivers rich, app-like messages to Android devices — rich cards with images, carousels, interactive suggestion chips, and branding. Requires a two-node pattern: check whether the recipient supports RCS, then send the message with an SMS fallback if they don't.

**Prerequisite:** This document assumes familiarity with `webex-connect.md` for core flow concepts (variable picker, HTTP nodes, flow structure).

---

## Node Inventory

Two RCS-specific nodes in the Connect palette:

| Node | Palette Name | Purpose |
|------|-------------|---------|
| **RCS Capability** | `RCS Capability` | Checks if recipient's device supports RCS before sending |
| **RCS Message** | `RCS Message` | Sends outbound RCS messages (text, file, rich card, carousel, typing indicator) |

Both are safe within the 30-second AI agent flow timeout when using Gateway Submit mode and cached capability lookups.

---

## RCS Capability Node

Verifies whether a recipient's device can receive RCS messages. **Always run this before sending RCS** — not every Android device has RCS enabled, and no iOS devices support it. ⚠ The "no iOS support" part is **toolkit guidance, not a published Cisco statement** — no crawled Webex Connect page states it either way [`docs/tests/findings/multi-channel-routing-findings.md` § Items Not Verifiable #3]. Running the capability check is the correct behavior regardless, since it is the node's own answer that decides the branch.

### Configuration Fields

| Field | Required | Details |
|-------|----------|---------|
| **Mobile Number** | Yes | Phone number in E.164 format or variable: `$(nX.variableName)` |
| **Force Refresh** | No | Set it to `false` explicitly — **the UI defaults to `true`**. `false` = 7-day cached lookup (near-instant). `true` = live network check (3–6s latency — avoid in agent flows). Because the default is the slow option, leaving this field alone is the wrong choice in an AI agent flow |
| **Carrier** | No | An **integer** value, not a string carrier code — the UI shows a placeholder of `302`. Leave blank if unknown; improves throughput for single-operator sends [source: [Carrier IDs for RCS Capability and RCS Message Nodes](https://help.webexconnect.io/docs/carrier-ids-for-rcs-capability-and-rcs-message-nodes), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #22] |

*(Provenance: the 7-day cache window, the 3–6s live-check latency, and the `true` default all come from the RCS findings review — the same evidence behind `webex-connect-advanced.md` and `outbound-rcs.md`. They are outside the scope of the Webex Connect documentation crawl, which covered the core node pages only.)*

### Output Variables

**Core variables:**

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `rcs.msisdn` | E.164 formatted number | `+447500661610` |
| `rcs.carrierCode` | Carrier identifier | `CA_ROGERS` |
| `rcs.enabled` | Boolean — device has any RCS support | `true` / `false` |
| `rcs.version` | RCS version level | `up1`, `up2`, `disabled` |
| `rcs.platform` | RCS platform provider | `Google`, `Samsung` |

**Per-feature capability booleans:**

> ⚠️⚠️⚠️ **STOP — PLATFORM TYPO WARNING — DO NOT "FIX" THESE SPELLINGS** ⚠️⚠️⚠️
>
> **The RCS Capability node emits variable names that are MISSPELLED on the platform.** The misspellings are inconsistent — two different typos appear (`capabilties` and `capabilites`), and one variable is spelled correctly.
>
> **Why this matters:** a Branch condition typed with the correctly-spelled `rcs.capabilities.richcard` will **never match**. The flow builds, deploys, and runs with no error — it just silently takes the wrong path forever.
>
> **Rules:**
> 1. **NEVER type these names manually.** Run the RCS Capability node, then copy the exact name from the **variable picker**.
> 2. **NEVER "correct" the spellings in this table.** They are wrong on purpose, because the platform is wrong. Verified against [RCS Capability Node](https://help.webexconnect.io/docs/rcs-capability-node) on 2026-04-17 — see `docs/tests/findings/outbound-rcs-findings.md` #1–#4.
> 3. Rows marked **spelling unverified** below have **no evidence either way** — the official page neither confirms nor denies their spelling. Treat them as suspect and confirm each one in the variable picker before use.

| Variable | Feature | Spelling status |
|----------|---------|-----------------|
| `rcs.capabilties.richcard` | Standalone rich card | ⚠️ **Verified MISSPELLED** on platform (`capabilties` — missing the "i"). Do not change |
| `rcs.capabilites.richcardCarousel` | Carousel cards | ⚠️ **Verified MISSPELLED** on platform (`capabilites` — a *different* typo from the row above). Do not change |
| `rcs.capabilities.calendarEvent` | Calendar event action | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilites.dialPhoneNumber` | Dial phone action | ⚠️ **Verified MISSPELLED** on platform. ⚠️ Cisco's own page is self-contradictory here: the body text shows `rcs.capabilites.dialPhoneNumber` and the sidebar shows `rcs.capabilties.dialPhoneNumber`. Both are misspelled; which one the node emits is **unresolved**. Copy from the variable picker |
| `rcs.capabilities.openUrl` | Open URL action | ✅ **Verified spelled CORRECTLY** on platform (body text and sidebar agree). Do not change |
| `rcs.capabilities.shareLocation` | Share location action | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.viewLocation` | View location action | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.chat` | Chat / text messaging | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.fileTransfer` | File/media transfer | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.paymentsV1` | Payments | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.videoCall` | Video calling | ❓ Spelling unverified — confirm in the variable picker |
| `rcs.capabilities.revocation` | Message revocation | ❓ Spelling unverified — confirm in the variable picker |

### Critical: `enabled` vs `version`

`rcs.enabled` = `true` does **not** guarantee rich features. A device with `rcs.version` = `up1` has basic RCS (text only) — NOT rich cards or carousels. Branch on `rcs.version` = `up2` or check individual capability booleans for rich content.

### Exit Paths

| Event | When | Color |
|-------|------|-------|
| `onSuccess` | Capability check completed | Green |
| `onError` | Invalid number, network error, lookup failed | Red |

---

## RCS Message Node

### Required Fields

| Field | Details |
|-------|---------|
| **Destination Type** | `MSISDN` (phone number) or `Customer Id` (profile ID) — casing is exact and node-specific: the live RCS Message node page returns `"MSISDN"` uppercase and `"Customer Id"` with a lowercase "d". Do not normalise either |
| **Destination** | Phone number in E.164 format or variable: `$(nX.variableName)` |
| **Message Type** | `Text`, `File`, `Rich Card`, `Carousel Card`, or `Typing Indicator` |

### Optional Fields

| Field | Details |
|-------|---------|
| **Carrier** | Integer. Leave blank if unknown |
| **Correlation ID** | User-defined unique ID, returned with delivery reports |
| **Callback Data** | Additional data sent with delivery reports (max 2,000 chars) |
| **Notify URL** | Webhook URL for delivery status notifications |
| **Wait For** | `Gateway Submit`, `Delivery Report`, or `Read Receipts` |
| **Time out** | Seconds duration (used with Wait For) |
| **Expiry** | UTC date/time or seconds |

### Exit Paths

| Event | When | Color |
|-------|------|-------|
| `onSuccess` | Message sent successfully | Green |
| `onSubmit` | The **Wait For: Gateway Submit** condition was met | Green |
| `onDeliveryReportSuccess` | Delivery confirmed (Delivery Report mode) | Green |
| `onError` | Invalid destination, gateway rejection, RCS not supported | Red |
| `onDeliveryReportFail` | Delivery report returned failure | Red |
| `onPolicyFail` | Expiry condition not met | Red |
| `onTimeout` | Timeout period elapsed | Amber |

⚠ `onSuccess` and `onSubmit` are **distinct exit paths, not aliases** — they are separate branches and must be wired separately. `onSuccess` fires when the message is sent successfully; `onSubmit` fires specifically when the **Wait For: Gateway Submit** condition is met [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #13].

### Output Variables

RCS Message output variables are **prefixed `send.`** [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #15]. Note `send.sentDateTime` — "sen**t**", not "send".

| Variable | Description |
|----------|-------------|
| `send.sentDateTime` | Message send timestamp |
| `send.gatewayTid` | Gateway transaction ID |
| `send.deliveryStatusDescription` | Success/failure status text |
| `send.deliveryStatusCode` | Numeric status code |
| `send.response_data` | Raw response from gateway |
| `send.response_interactive` | Interactive response data (postback from suggestions) |

---

## Message Types

### Text

| Field | Limit |
|-------|-------|
| **Text** | Max **1,024 characters** (no 160-char SMS limit) — ⚠ **not confirmed by Cisco.** The official RCS Message Node page states no character limit for the Text message type at all; 1,024 is toolkit guidance, not a published limit [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #11 and "Items Not Verifiable" #3] |
| **Suggestions** | Up to **11** suggestion chips outside the message — ⚠ the 11-chip figure is documented **in the carousel context**; whether it applies identically to a standalone Text message is not stated [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #12] |

### File

| Field | Details |
|-------|---------|
| **Media Content URL** | Publicly accessible direct URL |
| **File Size** | In bytes (must be > 0) |

Supported formats and limits:

| Type | Formats | Max Size |
|------|---------|----------|
| Image | BMP, GIF, JPEG (recommended), PNG | 500 KB |
| Video | MPEG-4 | 500 KB |
| Audio | MP4, M4A, MP3, WAV | 500 KB |
| PDF | PDF (v6.5.0+) | Not documented; may fail on some MaaP providers |

### Rich Card (Standalone)

| Field | Details / Limits |
|-------|-----------------|
| **Card Orientation** | `VERTICAL` or `HORIZONTAL` |
| **Thumbnail Alignment** | `LEFT` or `RIGHT` (horizontal cards only) |
| **Media URL** | Max 2,048 characters; publicly accessible |
| **Media Height** | `SHORT`, `MEDIUM`, or `TALL` |
| **Thumbnail URL** | Max 2,048 chars; max 100 KB (recommended ≤50 KB), 800×800 px square, JPG/PNG |
| **Title** | Max **200 characters** |
| **Description** | Max **2,000 characters** |
| **Suggestions** | Up to **4** per card |

At least one of media, title, or description is required. Total card payload limit: **250 KB**.

Image resolution guidelines:

| Media Height | Recommended Size |
|-------------|-----------------|
| SHORT | 1085 × 310 px — confirmed |
| MEDIUM | 1080 × 720 px — confirmed |
| TALL | ⚠ **Not published for a standalone rich card.** 1080 × 787 px is the **carousel card** recommended resolution and was previously mis-listed here as the standalone TALL dimension. Cisco does not specify a standalone rich card TALL pixel size [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #10] |

### Carousel Card

| Field | Details / Limits |
|-------|-----------------|
| **Card Width** | `SMALL` or `MEDIUM` |
| **Media Height** | `SHORT`, `MEDIUM`, or `TALL` — **must match across all cards** |
| **Cards** | Min **2**, max **10** |
| **Per-card fields** | Same as Rich Card: Media URL, Thumbnail URL, Title (200 chars), Description (2,000 chars) |
| **Suggestions per card** | Up to **4** in flow builder |
| **Global suggestions** | Up to **11** outside the carousel |
| **Recommended resolution** | 1080 × 787 px [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #10]. ⚠ See the UNRESOLVED note below |

> ⚠ **UNRESOLVED — carousel media dimensions. Needs a tenant check.** Cisco's RCS Message Node page carries two claims that cannot both hold:
>
> - **Reading A:** the carousel card recommended resolution is **1080 × 787 px**.
> - **Reading B:** carousels require **square media dimensions**.
>
> 1080 × 787 is not square. Both statements are on the same official page, so this cannot be settled from documentation — it needs verification against a live tenant by sending a carousel with each aspect ratio and observing which renders. Until then, treat 1080 × 787 as the working value (it is the explicitly *recommended* figure) and expect that a square asset may also be accepted. Do not delete either reading. [source: [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #23]

Dynamic carousels: Reference an array variable using JSONPath notation (`$.cars[0].name`). Loops process first-level array nesting only, up to 10 cards max. Incomplete arrays cause loop failure.

### Typing Indicator

Sends a typing notification to the user. No content fields required.

---

## Suggestion Types

Six suggestion types for interactive chips on messages and cards:

| Type | Fields | Description |
|------|--------|-------------|
| **Reply** | `displayText` (max 25 chars), `postbackData` | Pre-configured text reply; tapping sends label text back |
| **Open URL** | `displayText` (max 25 chars), `url` (required), `postbackData` | Opens URL in browser |
| **Dial Phone** | `displayText` (max 25 chars), `phone` (required), `postbackData` | Initiates a phone call |
| **View Location** | `displayText` (max 25 chars), `latitude`, `longitude`, `address`, `postbackData` | Shows location on map |
| **Share Location** | `displayText` (max 25 chars), `postbackData` | Prompts user to share their location |
| **Calendar Event** | `displayText` (max 25 chars), `startTime`, `endTime` (ISO 8601), `meetingTitle` (required), `meetingDescription`, `postbackData` | Creates calendar event |

**Constraints:** Max 25 characters per chip label. Max 4 suggestions per card. Max 11 chip-list suggestions outside the message — the 11-chip figure is carousel-documented; see § Message Types → Text for the caveat.

---

## RCS + SMS Fallback Pattern

### Flow-Based (Recommended for Notifications)

```
Start (Webhook)
  → RCS Capability (check $(n1.inboundWebhook.phone))
    → onSuccess → Branch (rcs.enabled == true AND rcs.version == "up2")
      → [Yes] → RCS Message (rich card / text)
      → [No]  → SMS (plain text fallback)
    → onError → SMS (safe fallback)
```

⚠ `$(n1.inboundWebhook.phone)` above is illustrative: the `inboundWebhook` node-type segment is **unverified** — insert the Start node field from the **variable picker** rather than typing it (see § Variable Insertion).

### API-Based (Send Message v2 with Automatic Fallback)

The Send Message API v2 supports automatic SMS fallback via the `options` block:

```json
{
  "channel": "rcs",
  "content": { "type": "text", "text": "Your order is ready." },
  "options": {
    "smsFallback": true,
    "smsSenderId": "your_sms_sender_id",
    "text": "Your order is ready. Reply STOP to opt out."
  }
}
```

Failed RCS messages generate transaction IDs appended with `_fallbackrcs` for tracking.

### GSMA API Fallback (v6.5.0+)

Three parameters: `smsFallback` (boolean), `smsSenderId` (mandatory if enabled), `text` (mandatory if enabled). Requires SMS outbound webhook configured with GSMA FNW.11 API flag enabled.

---

## Delivery Receipts

RCS supports four receipt types:

| Receipt | Status | Code |
|---------|--------|------|
| Submitted | Message entered gateway | `7501` |
| Delivered | Message reached device | `7500` |
| Read | Message opened by recipient | `7502` |
| Failed | Delivery failed | varies |

**RCS advantage over SMS:** Read receipts are available (SMS only provides Submitted and Delivered).

---

## Wait For Setting

| Mode | Behavior | Use in Agent Flows? | Use in Webhook Flows? |
|------|----------|--------------------|-----------------------|
| **Gateway Submit** | Completes when message enters gateway queue | **Yes** — fast, stays under 30s | Yes — fastest |
| **Delivery Report** | Waits for carrier delivery confirmation | **No** — will timeout | Yes, if you need delivery confirmation |
| **Read Receipts** | Waits for recipient to open message | **No** — will timeout | Yes, if you need read confirmation |

**Always use Gateway Submit** in AI agent flows. Webhook-triggered notification flows can use Delivery Report if needed.

---

## Variable Insertion

Same `$(nX.variableName)` pattern as all Connect nodes:

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook) | `$(n1.inboundWebhook.fieldName)` — ⚠ node-type segment unverified, see below | `$(n1.inboundWebhook.customer_phone)` |
| Trigger node — AI Agent category, presents as **Configure AI Agent Event** | `$(n2.aiAgent.entity_name)` — ⚠ node-type segment unverified, see below | `$(n2.aiAgent.phone_number)` |
| HTTP Request output | `$(nX.outputVar)` | `$(n3.customer_name)` |
| Capability node output | `$(nX.rcs.enabled)` | `$(n4.rcs.enabled)` |

⚠ **Two node-type segments above are unverified — confirm both in the variable picker.**

- `inboundWebhook` — the general pattern `$(n[nodeID].[nodeType].[fieldName])` is confirmed in official docs, but `inboundWebhook` as the specific node-type identifier for Start node webhook fields is consistent with platform behavior and **not explicitly confirmed** in official documentation [`docs/tests/findings/multi-channel-routing-findings.md` § Items Not Verifiable #2].
- `aiAgent` — **not documented in official docs**; the AI Agent fulfillment page shows no variable-syntax example at all. Use the variable picker to confirm the exact format your tenant produces — **do not type this path from memory** [owner: `webex-connect.md` § Variable Picker].

**Critical:** API substitutions apply **exclusively to text field content** — not to rich card titles, descriptions, or suggestion labels in the API. In the flow builder, use the variable picker for all fields.

---

## Provisioning Prerequisites

### RCS App/Asset Setup

1. **Assets > Apps** in Webex Connect → **Configure New App** → select **RCS**. ⚠ **This navigation path is not confirmed by Cisco.** The RCS Onboarding Guidelines page documents RCS *Templates* under **Tools > Templates**; no page on the crawl confirms an `Assets > Apps` route for asset setup. The path may vary by platform version — confirm in your tenant or with your account manager [source: [RCS App/Asset Setup](https://help.webexconnect.io/docs/rcs-1), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #21]
2. Configure brand:
   - Display Name (max 40 chars, recommended <25) — confirmed
   - Description (max 100 chars) — confirmed
   - Brand Color (min 4.5:1 contrast ratio vs white) — confirmed
   - Logo (224×224 px, **JPG or PNG**). ⚠ Cisco specifies the dimensions and both formats, but **publishes no logo file-size limit** — an earlier `<50 KB, JPEG` figure here was toolkit-added and restricted the format incorrectly [source: [RCS Onboarding Guidelines](https://help.webexconnect.io/docs/rcs-onboarding-guidelines), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #16 and "Items Not Verifiable" #4]
   - Banner Images (1440×448 px, JPEG/PNG). ⚠ 1440×448 is confirmed; a **1080×1080 px alternative size is not mentioned** in the onboarding guidelines — treat it as unverified [source: [RCS Onboarding Guidelines](https://help.webexconnect.io/docs/rcs-onboarding-guidelines), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #17 and "Items Not Verifiable" #5]
   - Contact Info: up to 3 each of websites, phone numbers, email addresses
   - Privacy Policy URL (required)
   - Terms of Service URL (required)
3. Add test phone numbers for validation
4. Submit for approval — production launch requires carrier sign-off via account manager

### Platform Requirements

- **Android only** — Android 8+ with Android Messages or Samsung Messages. No iOS support. ⚠ The Android 8+ floor is mentioned informally in the Cisco docs but is **not stated as a hard requirement** [`docs/tests/findings/outbound-rcs-findings.md` "Items Not Verifiable" #6]. ⚠ **"No iOS support" is equally unconfirmed** — it is not stated on any crawled Webex Connect page [`docs/tests/findings/multi-channel-routing-findings.md` § Items Not Verifiable #3]. Treat both as toolkit guidance and gate rich sends on the RCS Capability node's own result rather than on an assumed device platform
- Service provider typically **Google** (Google RBM / Jibe platform)
- Carrier must have RCS enabled in the region
- **Supported countries:** USA, Canada, UK, France, Germany, Spain, Norway, Sweden, India, Japan, Mexico, Brazil, Jordan (expanding). ⚠ **Not verifiable** — Cisco publishes no supported-country list on any crawled page, so this list can be neither confirmed nor denied. Confirm the current list with your account manager [source: [RCS Channel Overview](https://help.webexconnect.io/docs/rcs), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #19]
- Approval timeline: ~7 days for basic messaging program — confirmed verbatim ("It takes approximately 7 days to configure a simple messaging program") [source: [RCS Onboarding Guidelines](https://help.webexconnect.io/docs/rcs-onboarding-guidelines), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #20]

### Sandbox Limitations

**RCS is NOT available in the Webex Connect Sandbox.** Sandbox supports only SMS, Voice, and WhatsApp. Full platform license required for RCS testing.

⚠ **This exclusion is not explicitly confirmed by Cisco.** The RCS Channel Overview page references the sandbox without ever stating that RCS is excluded from it — the blanket claim above is toolkit-added. Verify with your account manager before planning a sandbox test [source: [RCS Channel Overview](https://help.webexconnect.io/docs/rcs), verified 2026-04-17 — `docs/tests/findings/outbound-rcs-findings.md` #18 and "Items Not Verifiable" #2].

---

## Status Codes

| Code | Description |
|------|-------------|
| 7500 | **Delivered** |
| 7501 | **Submitted** |
| 7502 | **Read** |
| 7000 | Invalid input (JSON) |
| 7006 | Internal server error |
| 7010 | Service provider exception |
| 7011 | Unknown exception |
| 7301 | Message expired |
| 7307 | Endpoint not reachable |
| 7318 | General bad request |
| 7319 | Not found |
| 7320 | Invalid JSON |
| 7321 | Invalid content (bad field, invalid phone number) |
| 7322 | Provider not configured for chatbot |
| 7323 | Unable to locate carrier for recipient |
| 7324 | Max TPS reached |
| 7325 | Unauthorized access |
| 7326 | Internal system error |
| 7327 | External system error |
| 7328 | Pass-through error detail |
| 7329 | Carrier lookup process failure |
| 7330 | MaaP-specific error |
| 7331 | Rate limited at MaaP, retries expired |
| 7334 | MaaP returned failure IMDN |
| 7740 | Invalid media details |

---

## Limits Summary

| Constraint | Limit |
|-----------|-------|
| Text message length | 1,024 characters — ⚠ toolkit guidance, not a Cisco-published limit (see § Message Types → Text) |
| Rich card title | 200 characters |
| Rich card description | 2,000 characters |
| Media URL length | 2,048 characters |
| Image/video/audio file size | 500 KB |
| Thumbnail size | 100 KB (≤50 KB recommended) |
| Thumbnail dimensions | 800 × 800 px square |
| Total card payload | 250 KB per card |
| Carousel cards | Min 2, max 10 |
| Suggestions per card | 4 |
| Global suggestions outside message | 11 — ⚠ carousel-documented; standalone-text applicability unstated (see § Message Types → Text) |
| Suggestion chip label | 25 characters |
| Callback data | 2,000 characters |
| SMS fallback text | 1,024 characters |
| Scheduled message window | Max 7 days ahead |
| Display name | 40 characters (recommended <25) |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Rich card renders as plain text | Recipient has `rcs.version` = `up1` (basic RCS only) | Branch on `rcs.version` = `up2` or check `rcs.capabilties.richcard` (note the platform typo — see the callout in § RCS Capability Node → Output Variables) |
| Capability says enabled but message fails | `rcs.enabled` only means basic RCS, not rich features | Check individual capability booleans for specific features |
| Carousel cards misaligned | Media height values don't match across cards | Set identical `Media Height` on every card in the carousel |
| Media fails to load | File > 500 KB, URL not publicly accessible, or `fileSize` set to 0 | Ensure public URL, correct size, and size parameter > 0 |
| Variables empty in suggestion chips | API substitutions only apply to text field content | Use variable picker in flow builder for all fields |
| SMS fallback not firing (API) | Missing required fields | All three required: `smsFallback`, `smsSenderId`, and `text` |
| SMS fallback not firing (flow) | No Branch node after Capability | Wire Branch node to check `rcs.enabled` and route to SMS |
| Cannot test in sandbox | RCS not available in sandbox — ⚠ **this exclusion is not confirmed by Cisco** (see § Provisioning Prerequisites → Sandbox Limitations) | Requires full Webex Connect platform license; confirm with your account manager before ruling out a sandbox test |
| `7322` error | Provider not configured for chatbot | RCS app not set up or not carrier-approved |
| `7323` error | Unable to locate carrier | Number not recognized or carrier not RCS-enabled |
| `7324` / `7331` rate limit errors | Send rate too high | Reduce rate or contact account manager for throughput increase |
| Dynamic carousel fails silently | Incomplete array (nulls) | Ensure arrays are complete with no null entries |
| Brand logo/color not appearing | Wrong dimensions or contrast | Logo: 224×224 px, JPG or PNG (Cisco publishes no file-size limit — see § Provisioning Prerequisites). Color: 4.5:1 contrast vs white |

---

## References

- [RCS Message Node](https://help.webexconnect.io/docs/rcs-message-node)
- [RCS Capability Node](https://help.webexconnect.io/docs/rcs-capability-node)
- [RCS Channel Overview](https://help.webexconnect.io/docs/rcs)
- [RCS App/Asset Setup](https://help.webexconnect.io/docs/rcs-1)
- [RCS Onboarding Guidelines](https://help.webexconnect.io/docs/rcs-onboarding-guidelines)
- [Carrier IDs for RCS Capability and RCS Message Nodes](https://help.webexconnect.io/docs/carrier-ids-for-rcs-capability-and-rcs-message-nodes)
- [RCS API (Send Message v2)](https://developers.webexconnect.io/reference/rcs-api)
- [RCS Capability API](https://developers.webexconnect.io/reference/capability-api)
- [RCS FAQs](https://developers.webexconnect.io/reference/rich-communication-services-faqs)
- [RCS Status Codes](https://developers.webexconnect.io/reference/channel-specific-status-codes-1)
- [v6.5.0 Changelog (GSMA SMS Fallback)](https://help.webexconnect.io/changelog/product-update-v650-january-2024)

## See Also

- [webex-connect.md](webex-connect.md) — the Connect flow basics the RCS nodes build on
- [webex-connect-advanced.md](webex-connect-advanced.md) — other Connect node types
- [connect-sms.md](connect-sms.md) — the SMS channel used as the RCS fallback
- [outbound-rcs.md](../playbooks/outbound-rcs.md) — the outbound RCS build steps that pair with this reference
