# Webex Connect — SMS & MMS Reference

<!-- ref-tag: connect-sms-v3 -->

SMS and MMS nodes for outbound text and multimedia messaging. SMS is the universal fallback channel — every phone supports it. Use it for confirmations, alerts, and as the fallback when RCS or Apple Messages are unavailable.

**Prerequisite:** This document assumes familiarity with `webex-connect.md` for core flow concepts (variable picker, HTTP nodes, flow structure). For SMS/MMS as side-effects in AI agent flows, see also `webex-connect-advanced.md`.

**Ownership.** This file is the single owner of SMS/MMS **values** — field names, limits, encoding tables, exit paths, output variables, sender-ID types, provisioning and sandbox limits, and SMS delivery status codes. `docs/playbooks/outbound-sms.md` and `docs/playbooks/inbound-sms.md` reproduce many of these so each page works standalone; **this file wins on any disagreement**. Two exceptions: general inbound-webhook / Event-API response codes are owned by `connect-response-codes.md`, and the SMS node's use as a fire-and-forget side effect inside a 30-second AI agent flow is covered in `webex-connect-advanced.md` § SMS Node (Side-Effect Notifications).

---

## Node Inventory

Two separate nodes in the Connect palette (Channels category):

| Node | Palette Name | Purpose |
|------|-------------|---------|
| **SMS** | `SMS` | Text-only messages (GSM-7 or Unicode) |
| **MMS** | `MMS` | Multimedia messages with images, video, audio, documents |

These are distinct nodes — there is no combined "Send SMS" node.

---

## SMS Node

### Required Fields

| Field | Required | Details |
|-------|----------|---------|
| **Destination Type** | Yes | `Customer ID` or `msisdn` (phone number) |
| **Destination** | Yes | E.164 format with country code (e.g., `+15551234567`). Accepts variables: `$(nX.variableName)` |
| **From Number** | Yes | Select from dropdown of provisioned sender IDs, long codes, or short codes |
| **Message Type** | Yes | `Text`, `Flash`, `Binary`, `Unicode`, or `Template` |
| **Message** | Yes | Body text. Hard cap **4,000 characters**; Cisco recommends staying **below 450 characters** for deliverability (see "Message length — two numbers" below). Use `\n` for line breaks. Insert variables via picker. |

### Message length — two numbers, do not confuse them

| | Value | What it is |
|---|---|---|
| **Hard cap** | **4,000 characters** | The platform limit: "You can send short messages up to 4000 characters." / "The message should not be longer than 4000 characters." [source: https://help.webexconnect.io/docs/sms-node, crawled 2026-07-25 — `docs/plans/2026-07-25-webex-connect-doc-audit.md` § W1] |
| **Recommendation** | **below 450 characters** | Deliverability guidance, not a limit: "We recommend that you keep SMS messages below 450 characters for better deliverability and user experience." Going over 450 is allowed and will send [same source] |

⚠ **Superseded value — `1,024` characters.** This file, `outbound-sms.md` and `webex-connect-advanced.md` all previously carried a 1,024-character cap, and an April 2026 vetting pass recorded the same page as saying "should not be longer than 1024 characters" [`docs/tests/findings/outbound-sms-findings.md` § Items Confirmed Accurate #1, vetted 2026-04-17]. The July 2026 crawl of the **same URL** quotes 4,000 twice. The later, dated crawl wins and was applied to `webex-connect-advanced.md` on 2026-07-25 (backlog row 3, item W1); the 1,024 figure is recorded here rather than deleted because it may reflect a real earlier platform limit. **Do not "correct" 4,000 back to 1,024 without a fresh read of the Cisco page.** Status code `7107` below still carries the 1,024 wording — see the note there.

### Optional Fields

| Field | Details |
|-------|---------|
| **Add SmartLink** | Single URL with multiple offers; includes Link Validity (minutes) |
| **Shortened Links** | Auto-shortens HTTPS links; requires domain selection; Track Clicks option. **Warning:** shortened URL domains may be flagged as spam by carriers (⚠ the carrier-spam behaviour is operational knowledge — it is **not** verifiable from official docs [`docs/tests/findings/outbound-sms-findings.md` § Items Not Verifiable #4]). |
| **Correlation ID** | Custom unique ID returned with delivery reports. Accepts variables. |
| **Notify URL** | Webhook URL for delivery report callbacks. Includes "Enable Notify URL Auth" checkbox. |
| **Callback Data** | Additional data sent with delivery reports to the Notify URL |
| **Extra Parameters** | Key-value pairs for additional message attributes |

### Advanced Options

| Setting | Options | Notes |
|---------|---------|-------|
| **Wait For** | `Gateway Submit` or `Delivery Report` | **Always use Gateway Submit in agent flows** |
| **Expiry** | UTC datetime or seconds | "You can define the maximum time allocated for the execution of this node" — this is the field that drives the `onTimeOut` edge |

### Message Types

| Type | Purpose | When to Use |
|------|---------|-------------|
| **Text** | Standard GSM-7 encoded SMS | Default for Latin-character messages |
| **Unicode** | UCS-2 encoded | Required for non-Latin characters, emoji. Reduces per-segment limit to 70 chars. |
| **Flash** | Displays immediately on screen, not stored in inbox | Carrier support varies — test before using |
| **Binary** | Raw binary data (WAP push, vCard) | Specialized use cases only |
| **Template** | References a pre-configured template | Variables mapped via the standard `$(variable_name)` syntax |

### Exit Paths

| Event | When | Color |
|-------|------|-------|
| `onSuccess` | Message accepted by gateway (Gateway Submit) or delivered (Delivery Report) | Green |
| `onError` | Invalid destination, misconfigured sender, gateway rejection | Red |
| `onPolicyFail` | Contact policy or compliance restrictions block the message | Red |
| `onTimeOut` | Expiry threshold exceeded (mainly relevant in Delivery Report mode) | Amber |

⚠ **Casing — UNRESOLVED. Cisco publishes three spellings; do not treat any one as canonical.** Verified live 2026-07-27:

| Spelling | Where Cisco uses it |
|---|---|
| `onTimeOut` | Node-level exception-handling page — **section heading** [source: https://help.webexconnect.io/docs/exception-handling-at-the-node-level, via `docs/tests/findings/outbound-sms-findings.md` #4 and `docs/plans/2026-07-25-webex-connect-doc-audit.md` § M32] |
| `ontimeout` | The **body** of that same page: *"The 'ontimeout' event occurs when the time (in seconds) mentioned in the Timeout field has been exceeded."* |
| `onTimeout` | The HTTP Request node page and the RCS Message node page |

Cisco also never states whether the exception-handling event is even the **same** event as a node's exit path, so the three spellings may not all be describing one thing. Consequences for you: **recognise any of the three when reading a flow** — they refer to the same edge as far as this repo can tell — and **confirm the literal label in your own tenant** before writing automation that string-matches on it. This file's tables keep `onTimeOut` as their existing spelling; that is a retained value, **not** a verified recommendation, and other repo files spelling it `onTimeout` are not thereby wrong. Tracked in `docs/plans/2026-07-27-reference-sweep-triage-ledger.md` (A2/A3, "DO NOT MAKE THIS EDIT").

### Output Variables

These are the variables the **SMS send node** exposes (`send.` namespace):

| Variable | Description |
|----------|-------------|
| `send.gatewayTid` | Unique transaction reference ID assigned by the gateway |
| `send.sentDateTime` | Timestamp when the message was sent |
| `send.deliveryStatusCode` | Numeric delivery status code |
| `send.deliveryStatusDescription` | Human-readable delivery status description |
| `send.response_data` | Raw response data from the gateway |
| `send.response_interactive` | Interactive response data (if applicable) |

Notes:

- There is **no output variable for the recipient number**. To reference the destination downstream, reuse the value you supplied in the **Destination** field.
- There is **no segment-count output variable**. Segment count must be estimated from the encoding tables below.
- Do not confuse these with the **inbound** `sms.*` variables (`sms.message`, `sms.senderNumber`, `sms.serviceNumber`, `sms.keyword`, `sms.transId`) — those belong to the **Receive node** on a two-way/inbound flow, not to the SMS send node. The inbound set is enumerated in the next section. See also `docs/playbooks/inbound-sms.md`.

---

## Inbound SMS Output Variables (`sms.*`)

A **different namespace from the send node's `send.*` set above — the two never mix.** These are the variables an inbound SMS makes available, both on the trigger node of an inbound flow and on a mid-flow **Receive** node. The namespace is `nX.sms.*` for both; only the node-number prefix changes. Cisco's Start node page does not enumerate them — it redirects to the Receive node page [source: https://help.webexconnect.io/docs/receive-node, via `docs/tests/findings/inbound-sms-findings.md` § Items Confirmed Accurate #20].

| Variable | Description | Example |
|----------|-------------|---------|
| `sms.message` | Full text content of the inbound SMS | `5551234567,5559876543` |
| `sms.senderNumber` | Sender's phone number (E.164) | `+15557770001` |
| `sms.serviceNumber` | Your number that received the message (E.164) | `+15550001234` |
| `sms.keyword` | Matched keyword, when keyword filtering is configured | `UPDATE` |
| `sms.ts` | Receipt timestamp, ISO 8601 UTC | `2026-04-17T14:30:00Z` |
| `sms.transId` | Transaction identifier | `uuid-string` |

**For these channel-specific `sms.*` variables there is no `.receive.` segment** on either node — it is `$(nX.sms.message)`, never `$(nX.receive.sms.message)` [`docs/tests/findings/inbound-sms-findings.md` #9].

⚠ **Scope: this rule is about channel-specific variables only — it is NOT a global "Connect has no `.receive.` segment" rule.** Verified live 2026-07-27: Cisco documents a **generic** Receive-node capture variable that *does* carry the segment — *"the customer response that a receive node captures is stored in the `nodeid.receive.message` output variable"*, with the example `$(n11.receive.message)` [source: https://help.webexconnect.io/docs/variable-management-in-flows]. Cisco is not contradicting itself: the **generic** capture is `nodeid.receive.message`, while **channel-specific** inbound variables are namespaced by channel (`sms.message`, `whatsapp.waId`, `abc.abcUserId`) with no `.receive.`. Both forms are real. An earlier, unscoped version of this sentence caused a triage pass to wrongly flag `webex-connect.md`'s generic `.receive.` example as an error — do not repeat that.

**Receive node success exit:** for SMS the Receive node's success edge is labelled **`sms.mo`**, not a generic `onSuccess` [`docs/tests/findings/inbound-sms-findings.md` #10].

⚠ **Two unresolved names in this table.**

- **`sms.ts` vs `sms.timestamp`.** The official Receive node page names it `sms.ts` ("SMS timestamp in ISO8601 format in UTC timezone"), but search results and page content conflicted during vetting. Unverified — confirm on the tenant before building on it [`docs/tests/findings/inbound-sms-findings.md` #3 and § Items Not Verifiable #6].
- **`sms.msisdn` vs `sms.senderNumber`.** Older repo text referenced `$(nX.sms.msisdn)` for the sender's number. `sms.msisdn` does **not** appear in the official SMS output-variables table; `sms.senderNumber` does, and is the canonical reference. `sms.msisdn` is retained here as a claim of unknown provenance, not as a recommendation [`docs/tests/findings/inbound-sms-findings.md` #4 and § Items Not Verifiable #3].

### ⚠ Open item O5 — the inbound SMS trigger name is NOT settled

**Three spellings of the inbound SMS trigger are live in this repo**: `SMS - Mobile Originated - MO`, `Mobile Originated - MO`, and `SMS - Mobile Originated`. None has been verified against a tenant, and they are deliberately **not** unified. Tracked as **open item O5** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` § 6 "Open items requiring tenant or platform access"; the same hedge appears in `docs/reference/digital-inbound.md`.

Resolving it requires reading the literal label out of the Webex Connect trigger-node trigger picker on the tenant. **Do not settle it from the other two spellings, from majority use in this repo, or from memory.** One April 2026 vetting note reports the official Start node page carries the `- MO` suffix [`docs/tests/findings/inbound-sms-findings.md` #1] — that note was already on file when the backlog kept O5 open, so it is **not** sufficient to close it on its own.

---

## Character Encoding & Segmentation

### GSM-7 vs UCS-2

| Encoding | Single Message | Concatenated Per-Part | Triggers When |
|----------|---------------|----------------------|---------------|
| **GSM-7** | 160 characters | 153 characters | All characters are in the GSM-7 alphabet |
| **UCS-2** | 70 characters | 67 characters | Any non-GSM-7 character present (emoji, CJK, Arabic, etc.) |

A **single emoji** forces the entire message to UCS-2, cutting capacity by more than half.

### Concatenation Table

| Parts | GSM-7 Total | UCS-2 Total |
|-------|-------------|-------------|
| 1 | 160 | 70 |
| 2 | 306 | 134 |
| 3 | 459 | 201 |
| 4 | 612 | 268 |
| 5 | 765 | 335 |

The Connect SMS node enforces a **4,000-character** field limit regardless of encoding — roughly 26 GSM-7 segments or 59 UCS-2 segments (that segment count is arithmetic from the per-part figures above, not a Cisco-published number). See "Message length — two numbers" above for the cap's provenance and the superseded 1,024 figure.

### Extended GSM-7 Characters (2 Characters Each)

These consume **two character positions** in GSM-7:

```
| ^ € { } [ ] ~
```

A 160-character message containing one of these splits into 2 segments.

⚠ **Corrected 2026-07-27 — `\` out, `€` in.** This file previously listed `| ^ ~ { } [ ] \`. The official length-and-encoding reference lists `| ^ € { } [ ] ~`: the backslash is **not** on it, and the euro sign is [source: https://developers.webexconnect.io/reference/sms-length-and-encoding-copy1, via `docs/tests/findings/outbound-sms-findings.md` #6 and `docs/plans/2026-07-25-findings-corpus-audit.md` § 3g PF3]. `outbound-sms.md` already carried the corrected list; this file was the one still wrong. The backslash claim is recorded here rather than deleted — if you find a tenant that bills `\` as two positions, that is new evidence, not a regression.

---

## MMS Node

### Required Fields

| Field | Required | Details |
|-------|----------|---------|
| **Destination Type** | Yes | `Customer ID` or `msisdn` |
| **Destination** | Yes | E.164 format with country code |
| **From Number** | Yes | Select from dropdown |
| **MMS Message** | Yes | The header/subject line — up to **80 characters** including Unicode. ⚠ The field is labelled **"MMS Message"** in the UI ("Enter the text in the MMS Message field"), **not** "Subject" or "Subject line", which is how this file previously named it [`docs/tests/findings/outbound-sms-findings.md` #8, #9]. The 80-character limit is confirmed. |
| **Media Type** | Yes | Select up to **9 media types** per message |
| **MMS Slide Media URL** | Yes | Publicly accessible URL for each media file |
| **Message** | Yes | Body text, up to **4,096 characters** per slide. ⚠ The official MMS page states 4,096, but the live UI screenshot shows "Characters remaining: 5000" — the real field limit may be 5,000. Unresolved; do not build a hard truncation on either number without checking your tenant [`docs/tests/findings/outbound-sms-findings.md` #7]. |

### Optional Fields

| Field | Details |
|-------|---------|
| **Correlation ID** | Custom tracking ID |
| **Notify URL** | Webhook URL with optional auth |
| **Callback Data** | Custom data for delivery reports |

### Advanced Options

| Setting | Options |
|---------|---------|
| **Wait For** | `None` (default), `Gateway Submit`, `Delivery Report`, `Read` |
| **Expiry** | UTC or Seconds |

MMS has **four** Wait For options; the SMS node has only **two** (`Gateway Submit`, `Delivery Report`). `None` and `Read` are MMS-only [`docs/tests/findings/outbound-sms-findings.md` #10, #11].

### Supported Media Types

| Type | Extensions | Max Size |
|------|-----------|----------|
| Image | .jpg, .png, .gif | 750 KB |
| Audio | .mp3 | 750 KB |
| Video | .mp4 | 750 KB |
| Text | ⚠ not enumerated by the source | 750 KB |
| PDF | .pdf | 750 KB |
| Calendar | .ics, .ical | 750 KB |
| Contact | .vcf, .vcard | 750 KB |
| Excel ⚠ | .xlsx, .xls | 750 KB |

⚠ **Two rows in this table have different standing from the rest.**

- **`Text` was added 2026-07-27 — it completes a half-applied correction.** Cisco's MMS node page lists **Audio, Video, Image, Text, PDF, Calendar, Contact** [source: https://help.webexconnect.io/docs/mms-node, via `docs/tests/findings/outbound-sms-findings.md` #12]. That finding required two changes: rename `vCard` → `Contact`, and add `Text`. Only the rename landed; the missing `Text` row is restored here. The source names the media **type** but does **not** enumerate its file extensions, so the extension cell is deliberately blank rather than guessed.
- **`Excel` is unsourced — provenance unknown.** It does **not** appear in Cisco's MMS media-type list, and a repo-wide search on 2026-07-27 found no other source for it as an *MMS* media type (the `xls`/`xlsx` entries in `connect-email.md` § Supported Attachment MIME Types belong to the **Email** node, a different node with a different list). It is retained rather than deleted because it may be a real operational observation, and a deleted claim cannot later be confirmed — but **do not rely on Excel attachments in MMS without testing on your tenant.**

**Overall MMS payload limit: 750 KB** (including headers). Some carriers outside US/Canada limit to **250 KB**.

⚠ **Both KB figures are unverified.** The official MMS node page specifies **no** KB payload limit at all; 750 KB / 250 KB may be carrier-sourced rather than platform-documented [`docs/tests/findings/outbound-sms-findings.md` #13 and § Items Not Verifiable #2]. They are kept because they may be a real operational observation — treat them as a working budget, not a platform contract.

### Slide Composition Rules

- Max **9 slides** per MMS submission
- **No duplicate MIME types** in the same slide
- Image slides: can include audio, cannot include video
- Video slides: can only include text
- vCard/iCal/PDF slides: cannot mix with audio/video/image
- Video auto-reduces quality to fit; if still too large, falls back to SMS with link

### MMS Exit Paths

| Event | When |
|-------|------|
| `onSuccess` | Message accepted by gateway |
| `onError` | Invalid destination, media URL unreachable, gateway rejection |
| `onDeliveryReportFail` | Timeout during Delivery Report wait |
| `onTimeOut` | Expiry threshold exceeded (same casing note as the SMS node above) |

---

## Variable Insertion

Same `$(nX.variableName)` pattern as all Connect nodes:

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook) | `$(n1.inboundWebhook.fieldName)` — ⚠ node-type segment unverified, see below | `$(n1.inboundWebhook.customer_phone)` |
| Trigger node (Configure AI Agent Event) | `$(nX.aiAgent.entityName)` — ⚠ node-type segment unverified, see below | `$(n2.aiAgent.phone_number)` |
| HTTP Request output | `$(nX.outputVar)` | `$(n3.confirmation_number)` |
| Evaluate script output | `$(nX.outputName)` | `$(n4.formatted_date)` |
| Evaluate custom flow variable | `$(variableName)` — no node prefix | `$(formatted_date)` |

⚠ **The `inboundWebhook` and `aiAgent` node-type segments are UNRESOLVED — do not type either path from memory.** Verified live 2026-07-27: **neither literal segment appears on any Cisco page** (checked `variable-management-in-flows`, `inbound-webhooks` on both help.webexconnect.io and developers.webexconnect.io, `configure-fulfilment-flows-for-ai-agent-actions`, and `ai-agent-node`). Cisco documents only the general shape `$(n[nodeID].[nodeType].[fieldName])` [source: https://help.webexconnect.io/docs/variable-management-in-flows], and for inbound webhooks shows dot-notation over the parsed payload (`employee.name`) rather than a fixed segment; the AI Agent fulfillment page shows no variable-syntax example at all.

**This is not evidence the two examples above are wrong** — each may well be the `[nodeType]` your tenant emits. Nothing crawled confirms or refutes them, so both examples are kept. Only a live tenant's **variable picker** can settle it. **Insert these values from the picker rather than typing them** — a manually typed variable arrives empty at runtime with no error. Owner of both hedges: `webex-connect.md` § Variable Picker (`aiAgent` and `inboundWebhook` notes), which wins on any disagreement.

**Templates use the same syntax** — `$(replacement_parameter)`, with parentheses. There is no curly-brace form in Webex Connect. (The `${...}` form belongs to **AI Agent Studio** response templates, a different product — see `ai-agent-studio-scripted.md`.)

---

## Wait For Setting

| Mode | Behavior | Agent Flows? | Webhook Flows? |
|------|----------|-------------|----------------|
| **Gateway Submit** | Completes when the message enters the gateway queue | **Yes** — fast | Yes — fastest |
| **Delivery Report** | Waits for carrier delivery confirmation | **No** — will timeout | Yes, if needed |

**Always use Gateway Submit** in AI agent flows.

⚠ **Two things here are inference, not Cisco statements.**

- **Exit timing.** Official docs describe the queuing mechanism but never say the node exits *immediately* or *as soon as* the message enters the queue. The exact exit timing is unspecified [`docs/tests/findings/outbound-sms-findings.md` #15].
- **Latency.** Cisco's SMS node page confirms both modes exist and publishes **no** latency figures for either. "Seconds to minutes, will time out in an agent flow" is this project's inference from the 30-second AI agent flow limit [`webex-connect-advanced.md` § Critical: Wait For Setting]. The recommendation stands — a mode that waits on a third-party carrier is the wrong shape for a 30-second budget — but do not quote a specific delay.

---

## Sender ID Types

| Type | Format | Two-Way? | Throughput | Use Case |
|------|--------|----------|------------|----------|
| **Long Code (10DLC)** | 10-digit local number | Yes | Lower (regulated) | Low-to-medium volume business messaging |
| **Short Code** | 5–7 digits | Yes (keywords) | High | High-volume campaigns, notifications |
| **Toll-Free** | +1-8XX format | Yes | Medium | Customer support, transactional |
| **Alphanumeric Sender ID** | 3–11 chars (e.g., "ACME") | **No** (one-way) | Varies | Brand recognition in supported countries |

### US A2P 10DLC Registration

US carriers require 10DLC registration for application-to-person SMS on long codes:

1. Purchase a US landline number with SMS feature enabled
2. Register **Brand** (business identity) with The Campaign Registry (TCR)
3. Register **Campaign** (use case) linked to the brand
4. In Connect: **Assets > Numbers** > select number > **Actions > Request 10DLC** > assign Brand ID and Campaign ID
5. Status badge shows "10DLC Requested" → "10DLC" when approved

**Non-compliance (code 7281):** Messages from unregistered 10DLC numbers are rejected by US carriers.

⚠ **The registration requirement is confirmed; the `7281` mapping is not.** US 10DLC registration for long-code A2P SMS is confirmed [`docs/tests/findings/outbound-sms-findings.md` § Items Confirmed Accurate #18]. The specific code `7281` mapped to it was **not found on any public help.webexconnect.io page** [same file, § Items Not Verifiable #1]. `connect-response-codes.md` § Channel Delivery Error Codes names this file as `7281`'s owner, so the code is kept here — but **do not build Branch logic that matches on `7281`** without confirming it against a real rejected send on your tenant. `outbound-sms.md` § 6 and § 8 carry the same caveat.

### India DLT Registration

Numbers for SMS in India must be registered on the DLT portal. Provide Entity ID and `dltTemplateId` with each API call.

---

## SMS Templates

Templates use the standard `$(variable_name)` syntax (parentheses — the same form as every other Connect field). When Message Type = Template:

- Select a pre-configured template from the dropdown
- All template variables must be mapped to flow values
- Templates configured at **Tools > Templates > SMS**
- India DLT: templates must carry a matching `dltTemplateId`

---

## Opt-Out / STOP Keyword Handling

### Contact Policy

Webex Connect has a **Contact Policy** app for consent management with Consent Groups and frequency caps.

**Critical:** Contact Policy does **NOT** auto-enforce on Send nodes. You must add an explicit Contact Policy check in your flow before the SMS node and branch on consent status.

⚠ **Unverified.** This is plausible and is treated as the safe default, but it could not be verified from the SMS or sandbox pages [`docs/tests/findings/outbound-sms-findings.md` § Items Not Verifiable #3]. Adding the explicit check costs a node and is safe whether or not auto-enforcement exists; assuming auto-enforcement is not.

### STOP Keyword

- Configure keyword management at **Assets > Numbers > Keywords**
- Recommended STOP confirmation: `"[Brand] We're sorry to see you go! You will receive no further messages. Reply HELP for help."`
- US carriers require STOP/HELP keyword support — failure to honor opt-outs can result in carrier-level blocking

---

## Delivery Reports

### In Flows

- **Gateway Submit**: node continues on `onSuccess` once the message is queued for the gateway. No delivery confirmation. (⚠ "immediately" is an inference — see the caveat under § Wait For Setting.)
- **Delivery Report**: node blocks until the carrier confirms. (⚠ No latency figure is published — see the same caveat.)
- **Notify URL**: Configure webhook on the SMS node. DLRs posted asynchronously regardless of Wait For mode.

### Status Values

| Status | Code | Meaning |
|--------|------|---------|
| Submitted | 7501 | Submitted to network, awaiting delivery |
| Delivered | 7500 | Confirmed delivered to handset |
| Failed | varies | Delivery failed at gateway level |
| Un-Delivered | varies | Routed to operator but rejected or expired |
| Clicked | — | Recipient clicked tracked link (API v2 only) |

---

## Provisioning Prerequisites

### Number Provisioning

1. **Assets > Numbers > Get Numbers**
2. Select Phone Number, Short Code, or Sender ID
3. For phone numbers: select country, number type, ensure SMS feature is checked
4. For short codes: choose country, preferred series, volume estimate
5. For sender IDs: choose country, describe use case — operations responds within 3 business days

### Sandbox Limitations

**Owner of these figures.** `outbound-sms.md` § 6 and `inbound-sms.md` § 12 reproduce this table so each page works standalone; this one wins on any disagreement.

| Constraint | Limit | Verified |
|-----------|-------|----------|
| Lifetime SMS + WhatsApp requests | 10,000 (combined) | ✅ Cisco: "maximum of 10000 SMS or WhatsApp API requests (combined limit) over the lifetime of Webex Connect Sandbox usage" [`docs/tests/findings/outbound-sms-findings.md` #16] |
| Registered test phone numbers | Up to 5 (same country, cannot change) | ✅ [`outbound-sms-findings.md` § Confirmed #14; `inbound-sms-findings.md` § Confirmed #18] |
| Two-way SMS | 18 countries | ✅ [`outbound-sms-findings.md` § Confirmed #16; `inbound-sms-findings.md` § Confirmed #16] |
| One-way SMS | 70+ countries | ✅ [`outbound-sms-findings.md` § Confirmed #16] |
| From number | Auto-populated, cannot change | ✅ [`outbound-sms-findings.md` § Confirmed #15] |
| Nodes available in sandbox | ~15 (vs 50+ in a full tenant) | ✅ count confirmed [`inbound-sms-findings.md` § Confirmed #19]; ⚠ **which** ~15 is not enumerated by Cisco, so Receive-node availability in sandbox is unknown [same file, § Not Verifiable #2] |

Each inbound **and** each outbound message counts against the 10,000 — a parse-and-reply test flow burns two per run.

---

## Status Codes

**Scope.** The codes below are **SMS delivery** status codes, returned on the SMS node's exit paths and in delivery reports. They are **not** the inbound-webhook / Event-API response codes (`1002`, `7000`–`7029`, `430`) that an external caller sees when triggering a flow — those have a single owner in `connect-response-codes.md` § Inbound Webhook / Event API Response Codes and are deliberately not duplicated here. `connect-response-codes.md` § Channel Delivery Error Codes names this file as the owner of the SMS-specific `7281`.

### Success

| Code | Meaning |
|------|---------|
| 7500 | Delivered to handset |
| 7501 | Submitted to network |

### Common Failures

| Code | Meaning |
|------|---------|
| 7004 | Invalid parameters/values |
| 7101 | Invalid Sender ID (not authorized for destination operator) |
| 7102 | Invalid address (phone number) |
| 7107 | Message length exceeded (⚠ this row's threshold was recorded as 1,024 characters; the Message field's documented cap is now **4,000** — see § Message length. Which number the platform actually enforces on `7107` is **unresolved**; do not quote a figure with this code) |
| 7109 | User on Do Not Disturb list |
| 7111 | Spam content detected by carrier |
| 7201 | Rejected by operator |
| 7203 | Unknown subscriber (invalid number) |
| 7206 | Subscriber SIM full |
| 7207 | Out of coverage area |
| 7208 | Message expired (TTL exceeded) |
| 7209 | Unable to deliver multipart message |
| 7281 | **10DLC campaign error** — sender not registered (⚠ not found on any public Cisco page — see the caveat under § US A2P 10DLC Registration before branching on it) |
| 7282 | Invalid route — unsupported operator or landline |
| 7302 | Rate limit exceeded |
| 7720 | Recipient blocked messages from sender |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Message arrives garbled as `?????` | Unicode characters sent with Message Type = "Text" | Set Message Type to "Unicode" |
| Single emoji doubles segment count | One emoji forces UCS-2 encoding (70 chars/segment) | Remove emoji or budget for 2x segments |
| Extended GSM chars (`\| ^ € { } [ ] ~`) eat 2 chars each | Escape sequences in GSM-7 | Count them as 2 when estimating length. Note `€` is on the official list and `\` is not — see § Extended GSM-7 Characters |
| 7281 Campaign error in US | 10DLC brand/campaign not registered | Register brand + campaign with TCR, assign to number. ⚠ The `7281` mapping is unverified — see § US A2P 10DLC Registration |
| Delivery Report mode times out in agent flow | Waiting on a third-party carrier does not fit a 30-second budget (⚠ no Cisco latency figure exists — see § Wait For Setting) | **Always use Gateway Submit** in agent flows |
| Contact Policy not blocking opted-out users | Policy does not auto-enforce on Send nodes (⚠ unverified — see § Contact Policy) | Add explicit consent check before SMS node |
| Shortened URLs blocked by carrier | Some carriers flag shortened domains as spam (⚠ operational knowledge, not in official docs) | Test with target carriers; consider full URLs |
| Variable arrives empty | Typed manually instead of using picker | Always use the variable picker |
| From number rejected in destination country | Sender ID not supported/registered in that country | Use locally provisioned number or registered Sender ID |
| MMS media not rendering | URL not publicly accessible, or file exceeds 750 KB | Ensure public URL; compress under 750 KB |
| MMS falls back to SMS with link | Video too large after compression | Reduce video length/quality before upload |
| Flash SMS not received | Not all carriers/devices support it | Use standard Text type for reliability |

---

## References

- [SMS Node](https://help.webexconnect.io/docs/send-sms)
- [MMS Node](https://help.webexconnect.io/docs/mms-node)
- [SMS Length and Encoding](https://developers.webexconnect.io/reference/sms-length-and-encoding-copy1)
- [Character Sets Supported](https://help.webexconnect.io/docs/character-sets-supported-for-messaging)
- [Send SMS API v1](https://developers.webexconnect.io/reference/send-sms-api-v1)
- [Send Message API v2 (SMS)](https://developers.webexconnect.io/reference/send-sms-message-api-v2)
- [SMS FAQs](https://developers.webexconnect.io/reference/sms-faqs)
- [MMS API](https://developers.webexconnect.io/reference/mms-api)
- [Supported File Types](https://help.webexconnect.io/docs/supported-file-types-for-channels)
- [SMS Status Codes](https://developers.webexconnect.io/reference/channel-specific-status-codes-1)
- [Sender ID](https://help.webexconnect.io/docs/sender-id)
- [Short Codes](https://help.webexconnect.io/docs/shortcodes)
- [10DLC Number Assignment](https://help.webexconnect.io/docs/assigning-number-10dlc)
- [Contact Policy](https://help.webexconnect.io/docs/contact-policy)
- [Sandbox SMS](https://help.webexconnect.io/docs/sending-and-receiving-sms-using-sandbox)
- [SMS Templates](https://help.webexconnect.io/docs/templates)
- [Receive Node](https://help.webexconnect.io/docs/receive-node) — inbound `sms.*` output variables and the `sms.mo` success exit
- [Node-level Exception Handling](https://help.webexconnect.io/docs/exception-handling-at-the-node-level) — `onError` / `onPolicyFail` / `onTimeOut`
- Response codes for inbound webhooks / the Event API: `connect-response-codes.md`
- Procedures that reproduce these values: `docs/playbooks/outbound-sms.md`, `docs/playbooks/inbound-sms.md`
- Vetting evidence cited throughout: `docs/tests/findings/outbound-sms-findings.md`, `docs/tests/findings/inbound-sms-findings.md`, `docs/plans/2026-07-25-webex-connect-doc-audit.md`, `docs/plans/2026-07-25-findings-corpus-audit.md`

## See Also

- [webex-connect.md](webex-connect.md) — the Connect flow basics the SMS nodes build on
- [webex-connect-advanced.md](webex-connect-advanced.md) — other Connect node types
- [connect-response-codes.md](connect-response-codes.md) — response codes for inbound SMS webhooks
- [outbound-sms.md](../playbooks/outbound-sms.md) — the outbound SMS build steps that pair with this reference
- [inbound-sms.md](../playbooks/inbound-sms.md) — the inbound SMS build steps that pair with this reference
