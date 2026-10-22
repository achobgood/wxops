# Webex Connect — Apple Messages for Business Reference

<!-- ref-tag: connect-apple-messages-v3 -->

Apple Messages for Business delivers rich, interactive messages to iOS users — rich links, list pickers, time pickers, forms, Apple Pay, and OAuth authentication, all rendering natively in the Messages app. The critical constraint: **customers must initiate the conversation first**. You cannot cold-send to a phone number.

**Prerequisite:** This document assumes familiarity with `webex-connect.md` for core flow concepts. For Apple Messages as a side-effect in AI agent flows, see also `webex-connect-advanced.md`.

---

## ⚠ Verification Status — claims NOT confirmed in official Webex Connect docs

A vetting pass against `help.webexconnect.io` on 2026-04-17 could not confirm the
following claims, which this document previously stated as fact
[`docs/tests/findings/outbound-apple-messages-findings.md` § Items Not Verifiable].
They are now hedged in place. **Do not restore the confident wording without a
source.**

| Claim | Status |
|-------|--------|
| Sessions have **no time limit** | **UNVERIFIED.** Official Webex Connect docs neither confirm nor deny a session expiry. Treat as *undocumented*, not as *proven unlimited* — see § Session Duration |
| `CONVERSATIONCLOSED` event name | Not documented on help.webexconnect.io |
| **HTTP 410 Gone** on a closed session | Not documented on help.webexconnect.io; plausible Apple platform behavior |
| **64 KB** cap on interactive-message images | Not stated anywhere in official docs |
| **iOS 11.3+ / macOS 10.13.4+** minimum versions | Not stated in official Webex Connect docs |
| Bot / human-handoff policy | Apple platform policy; not documented on help.webexconnect.io |
| `support@webexconnect.com` as the Apple-review contact | No support email appears in official docs |

---

## Node Inventory

| Node | Palette Name | Purpose |
|------|-------------|---------|
| **Apple Messages for Business** | `Apple Messages for Business` | Sends outbound messages within an active customer session |

Single node in the **Node Palette**, under `SERVICES & FLOWS`. Formerly called "Apple Business Chat" — the API channel parameter is still `"AppleBusinessChat"`.

---

## Critical Constraint: Active Session Required

**Businesses CANNOT initiate conversations.** The customer must message your business first. This is an Apple platform policy, not a Webex Connect limitation.

### How Customers Initiate

- Messages button on your website
- In-app Messages button
- QR code scan / NFC tag tap
- Apple Maps business listing
- Spotlight / Siri suggestions
- Wallet passes
- Direct URL: `https://bcrw.apple.com/urn:biz:<business-id>`

### Session Duration

**No time limit (UNVERIFIED — not confirmed in official Webex Connect docs).** Apple Messages has no *documented* session expiry, unlike WhatsApp's explicit 24-hour window, so replying hours or days later is expected to work. But "not documented" is not "proven unlimited": the official docs neither confirm nor deny an expiry [`docs/tests/findings/outbound-apple-messages-findings.md` #17].

⚠ **Build implication.** Do not design a flow that *depends* on an unlimited window. A build that assumes "no limit" fails silently — messages simply stop arriving — if a limit exists. Always wire the `onError` exit to a fallback channel (see § Implications for Multi-Channel Flows).

### Session Termination

A session ends when:
1. **Customer deletes the conversation thread** — reported as a `CONVERSATIONCLOSED` event (event name not documented on help.webexconnect.io). Subsequent sends may return **HTTP 410 Gone** (Apple platform behavior — not documented on official Webex Connect help pages) [`docs/tests/findings/outbound-apple-messages-findings.md` #14, #15].
2. **Customer blocks the business.**

Whether these are the *only* two termination causes is likewise undocumented — treat the list as the known causes, not a closed set.

### Re-engagement

If a customer closed the conversation, you **cannot** re-engage them. They must message you again from a valid entry point. They return with the **same opaque user ID**.

### Implications for Multi-Channel Flows

In webhook-triggered notification flows, you MUST handle the case where no active session exists:

```
Start (Webhook)
  → Branch: does customer have active AMB session?
    → YES → Apple Messages for Business node
    → NO  → fallback to SMS / RCS / Voice
```

Maintain a record of active sessions by tracking `abcId` values and `CONVERSATIONCLOSED` events.

---

## Node Configuration

### General Fields (All Message Types)

| Field | Required | Details |
|-------|----------|---------|
| **Destination Type** | Yes | `AbcUser Id` (exact UI dropdown label) |
| **Destination** | Yes | Customer's `abcId` (opaque ID — the identifier name used in the official docs). Accepts variable: `$(nX.variableName)` |
| **Message Type** | Yes | Text, Text with Attachments, Rich Link, List Picker, Time Picker, Payment, New Authentication, iMessage App, Quick Reply, Form Message |
| **Send typing indicator** | No | Checkbox (available on most types) |
| **Correlation ID** | No | Custom tracking ID |
| **Notify URL** | No | Webhook URL for gateway submission status |
| **Callback Data** | No | Custom data for webhook notifications |

⚠ **UNRESOLVED — the Destination Type dropdown label.** Two sources disagree and **neither has been retired. The table above is deliberately unchanged.**

| Source | What it says | Read on |
|---|---|---|
| The 2026-04-17 vetting pass, reading the **screenshots** on the node docs page | The dropdown value is **`AbcUser Id`**. It flagged `User ID` as a severity-**Error** mistake: *"A builder looking for 'User ID' in the dropdown will not find it."* [`docs/tests/findings/outbound-apple-messages-findings.md` #1] | 2026-04-17 |
| The **prose** on the same node docs page | *"Select **User ID** from this dropdown box."* [source: https://help.webexconnect.io/docs/apple-messages-for-business] | 2026-07-27 |

**Both can be true** — the screenshots and the prose are different parts of the same page, and Cisco's prose can lag or differ from the shipped dropdown text. Read the actual dropdown **in your tenant**: if it reads `User ID`, that is a known possibility, not a defect in this doc. **Do not flip either value on the strength of a single source** — a disproven claim was resurrected four times that way [`.claude/rules/doc-placement.md` § The Single-Owner Rule]. Resolve it with a tenant screenshot, then delete this note.

### Wait For Options

| Mode | Behavior | Notes |
|------|----------|-------|
| **None** | Fire and forget | Default |
| **GW submit** | Wait for submission confirmation | Exact UI label is `GW submit`. Use in agent flows |

**No Delivery Report option** — Apple does not provide delivery/read receipts to MSPs.

### Expiry

| Field | Options |
|-------|---------|
| **Expiry** | `UTC` or `Seconds` |
| **Message Expiry** | Date/time or seconds value |

---

## Message Types

### Text

| Field | Details |
|-------|---------|
| **Message** | Up to **10,000 characters** |
| **Send as App Clip** | Optional — iPhones and iPads only |
| **Smart Link** | Optional — with link validity in minutes |

### Text with Attachments

| Field | Details |
|-------|---------|
| **Message** | Text body |
| **URL** | Attachment URL. Use URL-friendly filenames — avoid special characters like `+` |
| **Max attachment size** | **100 MB** |

### Rich Link

| Field | Details |
|-------|---------|
| **Website URL** | Hyperlink destination |
| **Title** | Max **128 characters** |
| **Image URL** | Publicly accessible direct link |
| **MIME** | Dropdown — select the image/video format (e.g. `png`, `jpeg`, `mp4`). Field is labeled `MIME`, not "MIME type", and is a picker, not freetext |
| **Add Video URL** | Optional checkbox — adds video URL + MIME fields |
| **Rich Link Previews** | Up to **25 domains** with custom preview images (.jpeg/.jpg/.png, under 5 MB, min 50 px) |

### List Picker

| Field | Details |
|-------|---------|
| **Bubble Style** | Small, Icon, or Large |
| **Title** | Bubble preview text — **required** |
| **Subtitle** | Bubble preview subtext — a **separate required field**, distinct from Title |
| **Sections** | Max **20 sections**, max **20 items per section** |
| **Section Item Style** | Small, Icon, or Large |
| **Allow multiple selection** | Checkbox |
| **Request Identifier** | Correlates response back to this message |
| **Reply Message Style/Title/Subtitle** | Shown after customer selects |

Interactive images are commonly cited as capped at **64 KB**, but this limit is **UNVERIFIED** — it appears nowhere in the official node documentation [`docs/tests/findings/outbound-apple-messages-findings.md` #8]. Compress thumbnails aggressively regardless; do not treat 64 KB as a guaranteed ceiling in either direction.

### Time Picker

| Field | Details |
|-------|---------|
| **Bubble Style** | Small, Icon, or Large |
| **Title** | Bubble preview text — **required** |
| **Subtitle** | Bubble preview subtext — **required** per the official node docs |
| **Time Slots** | Max **10** — each with title, identifier, timezone, start date/time, duration. The UI labels the duration field `Slot Duration (In Secs)` — seconds |
| **Location** | Title, latitude, longitude, radius |
| **Request Identifier** | Correlates response |
| **Reply Message** | Style, title shown after selection |

### Payment (Apple Pay)

| Field | Details |
|-------|---------|
| **Line Items** | Array: Type (dropdown), Label, Amount |
| **Total** | Type, Label, Total Amount |
| **Shipping Methods** | Optional: Label, Amount, Detail, Identifier |
| **Country Code** | ISO (e.g., "US") |
| **Currency Code** | ISO (e.g., "USD") |
| **Billing Fields** | Required field selection |
| **Request Identifier** | Unique payment request ID |

**Prerequisites:** Apple Developer account, Merchant ID, PEM certificate, payment gateway URL in Manage App.

### New Authentication (OAuth 2.0)

| Field | Details |
|-------|---------|
| **Received/Reply Message** | Title, subtitle, image configuration |
| **Scope** | OAuth scope items |
| **Request Identifier** | Correlates auth response |
| **Additional Parameters** | Extra OAuth params |

**Prerequisites:** OAuth endpoints and client ID in Apple Business Register. Client secret in Connect Manage App.

### Quick Reply

| Field | Details |
|-------|---------|
| **Summary Text** | Notification text |
| **Options** | 2 to 5 buttons, each with Identifier + Title. Single-select only. |
| **Request Identifier** | Correlates response |

### Form Message

| Field | Details |
|-------|---------|
| **Form Elements** | Complete JSON object defining multi-page form. Supports: select, picker, date, input fields. |

### iMessage App

| Field | Details |
|-------|---------|
| **Team ID** | Apple Developer Team ID |
| **Ext Bundle ID / App ID / App Name** | Extension identifiers |
| **App Icon / URL** | Icon and app URLs |
| **Use Live Layout** | Toggle |

---

## Exit Paths

| Event | When | Color |
|-------|------|-------|
| `onSuccess` | Message submitted to Apple gateway | Green |
| `onError` | No active session, invalid destination, gateway rejection | Red |
| `onPolicyFail` | Policy violation | Red |

The node has exactly these three exits. There is **no `onInvalidData` exit path** on the Apple Messages for Business node.

**Important:** `onSuccess` means "submitted to Apple's servers," NOT "delivered to device." Apple does not provide delivery or read receipts to MSPs.

---

## Output Variables

| Variable | Description |
|----------|-------------|
| `send.sentDateTime` | Timestamp (GMT) |
| `send.gatewayTid` | Gateway transaction ID |
| `send.deliveryStatusDescription` | Status description |
| `send.deliveryStatusCode` | Status code |
| `send.response_data` | Gateway response |
| `send.response_interactive` | Interactive response data |

**Message-type-specific:**

| Variable | When |
|----------|------|
| `send.richLink` | Rich Link messages |
| `send.ListPicker` | List Picker messages |
| `send.timePicker` | Time Picker messages |
| `send.quickReplies` | Quick Reply messages |

---

## Variable Insertion

Same `$(nX.variableName)` pattern as all Connect nodes:

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook) | `$(n1.inboundWebhook.fieldName)` | `$(n1.inboundWebhook.customer_name)` |
| Trigger node — AI Agent category, presents as **Configure AI Agent Event** | `$(nX.aiAgent.entityName)` | `$(n2.aiAgent.order_id)` |
| HTTP Request output | `$(nX.outputVar)` | `$(n3.appointment_time)` |

---

## Incoming Event Types

When receiving customer messages or interactive responses:

| Event Type | Description |
|-----------|-------------|
| `MO` | Text messages and attachments |
| `INTERACTIVERESPONSE` | List Picker and Time Picker selections |
| `QuickReplyResponse` | Quick Reply button taps |
| `NewAuthenticationResponse` | OAuth authentication result |
| `FormResponse` | Form submission data |
| `iMessageAppResponse` | iMessage App interactions |
| `TYPINGINDICATOR` | `typing_start` or `typing_end` |
| `CONVERSATIONCLOSED` | Customer deleted the conversation |
| `PaymentResponse` | Apple Pay transaction result |

⚠ The `CONVERSATIONCLOSED` row is the one entry in this table whose **event name is not documented** on help.webexconnect.io — see § Verification Status. Every other event name above is taken from the official docs.

The `capabilityList` field on incoming messages indicates device support: `AUTH`, `LIST`, `TIME`, `QUICK`, `FORM`, `AUTH2`. Apple Pay and Rich Links are supported on all devices.

### `abcUserId` vs `abcId` — two different things, both correct

These look like drift between docs. They are not. **Resolved by live verification 2026-07-27:**

| Name | What it is | Where it is documented |
|---|---|---|
| `abc.abcUserId` | The **inbound Receive-node output variable**. Cisco lists it verbatim: *"`abc.abcUserId` \| Unique user ID of the customer with the corresponding business that never changes even if the customer changes their device."* The string `abcId` **does not appear on the Receive page at all**. | [Receive node — Apple Messages](https://help.webexconnect.io/docs/apple-messages-for-business) |
| `abcId` | Cisco's **prose name for the opaque Apple ID *value*** you send to: *"you will need the `abcId` of the users… the Opaque ID unique to the relationship between the customer's Apple ID and the business's business ID."* It is **not** a Connect output variable name anywhere in the docs. | [Apple Messages Channel Setup](https://help.webexconnect.io/docs/apple-messages-for-business-1) |

∴ Read the identifier off an inbound message with **`$(nX.abc.abcUserId)`**; refer to the *value* you store and later send to as the **`abcId`**. This document's uses of `abcId` (§ Implications for Multi-Channel Flows, § Node Configuration → Destination, § Known Gotchas, § Channel Comparison) are all the outbound/value sense and are correct as written. `digital-inbound.md`'s `$(n1.abc.abcUserId)` is likewise correct.

⚠ `docs/tests/findings/outbound-apple-messages-findings.md` #4 states *"the Connect output variable will be named `abcId`"* — that specific claim is **wrong** and must not be applied. The rest of #4 (that official prose says `abcId`, not `abcUserId`, for the identifier *value*) stands.

⚠ **Flagged, not verified:** Cisco's Receive page appears to list the **MMS** rows using `receive.message` / `receive.channel` rather than the `<channel>.` prefix every other channel uses. Not confirmed, and out of scope for this document — do not act on it here.

---

## Provisioning Prerequisites

### Setup Steps

1. **Apple Business Register** — Register at `register.apple.com/business-chat`. Create a Messages for Business account.
2. **Select the MSP** — The Apple Business Register MSP list shows the legacy name **`IMImobile`**; it may also appear as "Webex Connect" in some regions. Pick whichever of the two the register UI actually offers.
3. **Automatic app creation** — Once Apple approves and links, an app is auto-created in Connect under **Apps** (top-level navigation — not a sub-path under Assets).
4. **Test connection** — Use Apple's "Test your MSP connection" feature. Workaround: append `&name=YOURAPPNAME` to Client Landing Page URL if invalid.
5. **Apple review** — Contact your account manager to start approval. (`support@webexconnect.com` is often quoted for this step, but **no support email address appears in the official Apple Messages setup documentation** — treat it as unverified [`docs/tests/findings/outbound-apple-messages-findings.md` #12].)

### For Apple Pay

Apple Developer account, Merchant ID, PEM certificate (from .p12), payment gateway URL in Manage App.

### For OAuth Authentication

OAuth endpoints + client ID in Apple Business Register. Client secret in Connect Manage App.

### Testing

**No dedicated sandbox — UNVERIFIED, no provenance.** No official Webex Connect or Apple page states this either way, and the 2026-04-17 vetting pass recorded **no finding on it at all** [`docs/tests/findings/outbound-apple-messages-findings.md`]. So "no sandbox exists" is *undocumented*, not established. Confirm with your account manager before planning a test phase around its absence. The test paths below are unaffected either way.

Test via:
- Apple's internal test accounts through Business Register
- MSP connection test tool
- Real Apple devices (see § Supported Devices — the specific minimum OS versions are unverified)

---

## Supported Devices

**Verified:** Apple platforms only — iOS, macOS, iPadOS, watchOS. There is **no Android support**.

**UNVERIFIED:** the specific minimum OS versions below. The official Webex Connect docs state no iOS or macOS version requirement, so these numbers are unsubstantiated [`docs/tests/findings/outbound-apple-messages-findings.md` #18]. Do not quote them to a customer as a supported-platform commitment.

| Platform | Minimum Version (unverified) |
|----------|----------------|
| iOS | 11.3+ |
| macOS | 10.13.4+ (High Sierra) |
| iPadOS | All versions |
| watchOS | Supported (via paired iPhone) |

---

## Platform Policies

| Policy | Details |
|--------|---------|
| **Bot requirement** | Bots/virtual agents allowed ONLY if human agent handoff is available. **Apple platform policy — not documented on help.webexconnect.io.** Apple's own FAQ states escalation must be available *anytime during the conversation*, which is stricter than "a handoff path exists": design for escalation at every turn [`docs/tests/findings/outbound-apple-messages-findings.md` #19] |
| **Blocked industries** | Gaming and gambling |
| **Account inactivity** | Commercial accounts with no activity in 3+ months may be deactivated by Apple (confirmed by official docs) |
| **No delivery receipts** | Apple does not provide delivery, read, or click events to MSPs (confirmed by official docs) |

---

## Limits Summary

| Constraint | Limit |
|-----------|-------|
| Text message length | 10,000 characters |
| Rich Link title | 128 characters |
| List Picker sections | 20 |
| Items per section | 20 |
| Time Picker time slots | 10 |
| Quick Reply options | 2–5 (single-select) |
| Attachment size | 100 MB |
| Interactive message images | 64 KB — **UNVERIFIED**, not stated in official docs |
| Rich Link preview domains | 25 per asset |
| Preview image file types | .jpeg, .jpg, .png only |
| Preview image size | Under 5 MB, min 50 px |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Cannot send to customer | No active session — customer hasn't messaged first | By design. Provide entry points (website button, QR, Apple Maps). |
| HTTP 410 Gone on send (status code unverified — see § Verification Status) | Customer deleted the conversation | Track `CONVERSATIONCLOSED` events. Remove from active session table. Fallback to SMS. |
| No delivery confirmation | Apple doesn't provide DRs | `onSuccess` = submitted to Apple, not delivered. Accept this. |
| Inactive account deactivated | No activity in 3+ months | Ensure regular message activity on commercial accounts. |
| HTTP 404 on send | "No device registrations" — typically during device upgrade | Retry later; messages not auto-retransmitted. |
| Interactive images too large | Reportedly over 64 KB — cap unverified, see § Verification Status | Compress/resize for List Picker, Time Picker thumbnails. |
| Attachment URL with special chars fails | `+` and special chars in filenames | Use URL-friendly filenames. |
| Bot-only deployment rejected | Apple requires human handoff | Add live agent escalation path. |
| Variable arrives empty | Typed manually | Always use variable picker. |
| `abcId` confused with phone number | Opaque ID, not a phone number | Cannot reverse-lookup phone from `abcId`. Maintain own mapping. |
| Classical Authentication deprecated | Old OAuth flow | Use "New Authentication" message type. |

---

## Channel Comparison

| Dimension | SMS | RCS | Apple Messages |
|-----------|-----|-----|---------------|
| Initiation | Business can cold-send | Business can cold-send | Customer must initiate |
| Session window | N/A (stateless) | N/A (stateless) | No *documented* time limit (unverified); ends on delete |
| Delivery receipts | Yes | Yes | No (submission only) |
| Rich messages | No | Yes (cards, carousels) | Yes (rich links, pickers, forms, Pay, Auth) |
| Destination ID | Phone (E.164) | Phone (E.164) | Opaque `abcId` |
| Platform | All phones | Android (RCS-enabled) | Apple devices only (specific minimum OS versions unverified) |
| Fallback needed | No | Yes (to SMS) | Yes (to SMS/RCS — may have no session) |

---

## References

- [Apple Messages for Business Node](https://help.webexconnect.io/docs/apple-messages-for-business)
- [Apple Messages Channel Setup](https://help.webexconnect.io/docs/apple-messages-for-business-1)
- [Apple Messages API](https://developers.webexconnect.io/reference/apple-messages-for-business-apis)
- [Apple Messages FAQs](https://developers.webexconnect.io/reference/faqs-apple-messages-for-business)
- [Apple Messages Outbound Webhooks](https://developers.webexconnect.io/reference/abc-outbound-webhooks)
- [Apple Messages Setup Guide](https://help.webexconnect.io/docs/messages-for-business-setup)
- [WxCC Apple Messages Integration](https://help.webexconnect.io/docs/wxcc-apple-messages-for-business)
- [Apple Business Register FAQ](https://register.apple.com/resources/messages/messaging-documentation/faq)
- [Apple MSP API](https://register.apple.com/resources/messages/msp-api-tutorial/receiving-sending-messages)
- [Rich Link API](https://developers.webexconnect.io/reference/apple-message-for-business-rich-link)
- [List Picker API](https://developers.webexconnect.io/reference/apple-message-for-business_-list-picker)
- [Time Picker API](https://developers.webexconnect.io/reference/apple-message-for-business-time-picker)

## See Also

- [webex-connect.md](webex-connect.md) — the Connect flow basics every channel node builds on
- [webex-connect-advanced.md](webex-connect-advanced.md) — Connect nodes beyond messaging, such as voice
- [connect-multi-channel.md](connect-multi-channel.md) — choosing between channels and falling back to SMS
- [digital-inbound.md](digital-inbound.md) — the inbound side of a digital channel
