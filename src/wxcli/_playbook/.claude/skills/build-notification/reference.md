# Outbound Notification — Cross-Channel Quick Reference

## Flow Structures by Channel

| Channel | Flow Pattern |
|---------|-------------|
| SMS | `Start → [HTTP Request] → SMS → End` |
| Email | `Start → [HTTP Request] → Email → End` |
| Voice | `Start → [HTTP Request] → Call User → Voice Node Group [Play TTS] → End` |
| RCS | `Start → [HTTP Request] → RCS Capability → Branch → RCS Message (or SMS) → End` |
| Apple Messages | `Start → [HTTP Request] → Branch (session?) → Apple Messages (or SMS) → End` |
| WhatsApp | `Start → [HTTP Request] → WhatsApp (Template/Text/Media) → End` |
| Multi-channel | `Start → HTTP Request → Branch (preferred_channel) → [per-channel path] → End` |

## Variable Picker Format

| Context | Format |
|---------|--------|
| Webhook payload field | `$(n1.inboundWebhook.{fieldName})` |
| HTTP node output | `$(nX.{variableName})` |
| Evaluate script output | `$(nX.outputName)` |
| Evaluate custom flow variable | `$(variableName)` — no node prefix |
| RCS Capability output | `$(nX.rcs.{variable})` |

**NEVER type manually** — always use the variable picker. Manually typed variables arrive empty at runtime.

## Channel Node Quick Reference

### SMS Node

| Field | Value |
|-------|-------|
| Destination Type | `msisdn` |
| Destination | E.164: `$(n1.inboundWebhook.customer_phone)` |
| From Number | Select provisioned sender from dropdown |
| Message Type | Text (GSM-7) or Unicode (emoji/non-Latin) |
| Message | Max 1,024 chars. 160/segment GSM-7, 70/segment UCS-2 |
| Wait For | **Gateway Submit** (always in agent flows) |

Exit paths: `onSuccess` · `onError` · `onPolicyFail` · `onTimeOut`

**10DLC (US):** Long code SMS to US numbers requires 10DLC brand/campaign registration. Unregistered numbers receive error 7281.

> ⚠️ **Unverified observation:** the error code **7281** is **not confirmed in official Cisco documentation** — only the 10DLC registration requirement is. Treat `7281` as an observed value, not a documented one, and confirm it against a real rejected send before branching on it.

### Email Node

| Field | Value |
|-------|-------|
| Destination Type | `Email ID` |
| Destination ID | Email address: `$(n1.inboundWebhook.customer_email)` |
| From Email | **Disabled** — auto-populated from email app asset config |
| Subject | Supports variables: `Order Confirmed - $(n3.order_number)` |
| Email Type | Text, HTML, or Template |
| Wait For | **Gateway Submit** (always in agent flows) |

Exit paths: `onSuccess` · `onError` · `onInvalidData` · `onPolicyFail` · `onTimeout`

### RCS Capability Node

| Field | Value |
|-------|-------|
| Mobile Number | E.164: `$(n1.inboundWebhook.customer_phone)` |
| Force Refresh | UI defaults to `true` (real-time, 3–6s latency). Set `false` for 7-day cached lookup (near-instant). |

Key outputs: `rcs.enabled` (boolean) · `rcs.version` (`up1`/`up2`/`disabled`) · `rcs.capabilties.richcard` (boolean — note platform typo in variable name)

> **Platform typo warning:** Capability variable names are misspelled in the node output. Do NOT type manually — use the **variable picker**. The actual names include `rcs.capabilties.richcard`, `rcs.capabilites.richcardCarousel`, `rcs.capabilites.dialPhoneNumber` (two different misspellings). Only `rcs.capabilities.openUrl` is correctly spelled.

**Critical:** `enabled=true` ≠ rich features. Branch on `version == "up2"` for rich cards.

Exit paths: `onSuccess` · `onError`

### RCS Message Node

| Field | Value |
|-------|-------|
| Destination Type | `MSISDN` (phone number) or `Customer Id` (profile ID) — casing is exact and node-specific; do not normalise either [source: `docs/reference/connect-rcs.md` § RCS Message Node → Required Fields, ref-tag `connect-rcs-v3`] |
| Destination | E.164: `$(n1.inboundWebhook.customer_phone)` |
| Message Type | Text (1,024 chars — not confirmed in official docs), Rich Card, Carousel Card, File, Typing Indicator |
| Wait For | **Gateway Submit** (always in agent flows) |

Rich Card limits: Title 200 chars · Description 2,000 chars · Media 500 KB · 4 suggestions/card · Chip label 25 chars

Exit paths: `onSuccess` · `onSubmit` · `onDeliveryReportSuccess` · `onError` · `onDeliveryReportFail` · `onPolicyFail` · `onTimeout`

### Apple Messages for Business Node

| Field | Value |
|-------|-------|
| Destination Type | `AbcUser Id` |
| Destination | `$(nX.abcId)` — opaque ID, NOT a phone number |
| Message Type | Text, Rich Link, List Picker, Time Picker, Quick Reply, Form, Apple Pay, Auth |
| Wait For | **None** (default) or **GW submit** (no Delivery Report option — Apple doesn't provide DRs) |

Rich Link: Title max 128 chars · List Picker: max 20 sections × 20 items · Time Picker: max 10 slots

**Session required:** Customer must have messaged first. No cold-send. Check `abc_session_active` before sending.

Exit paths: `onSuccess` · `onError` · `onPolicyFail`

### WhatsApp Node

| Field | Value |
|-------|-------|
| Destination Type | `WA ID` or `Customer ID` |
| Destination | E.164: `$(n1.inboundWebhook.customer_phone)` |
| Message Type | Template (proactive) or Text/Media/Interactive (24hr window) |
| Wait For | **Gateway Submit** (always in agent flows) |

Template: select approved template, map parameters via variable picker.
Text: max 4,096 chars. Supports *bold*, _italic_, ~strikethrough~.
Media: Image (5MB), Video (16MB), Audio (16MB), Document (100MB).

> **Both Destination Type options are verified, and `Customer ID` is spelled differently here than on other nodes — do not "normalise" it.** Cisco documents exactly two options for the WhatsApp node: "The destination type can be one of the following two options: **WA ID**: WhatsApp ID (phone number including country code) of your customer/ recipient of this message. **Customer ID**: Primary key of customer profile." [source: https://help.webexconnect.io/docs/whatsapp-node § Destination type — raw page fetched 2026-07-25; case-sensitive counts on the raw HTML: `Customer ID` ×4, `Customer Id` ×0, `WA ID` ×8, `WA Id` ×0]. The **Call User** node (§ Call User Node (Voice), below) and the **RCS Message** node use `Customer Id` (lowercase `d`) for the same concept [source: `docs/reference/connect-rcs.md` § RCS Message Node → Required Fields, ref-tag `connect-rcs-v3`] — that is the platform's own inconsistency, not an error to correct. The cross-node casing rule is owned by the reference doc [source: `docs/reference/webex-connect-advanced.md` § WhatsApp (Side-Effect Notifications) → Required Fields, ref-tag `connect-advanced-v8`].

Exit paths: `onSuccess` · `onSubmit` · `onDeliveryReportSuccess` · `onError` · `onPolicyFail` · `onTimeout` · `onDeliveryReportFail`

### Call User Node (Voice)

| Field | Value |
|-------|-------|
| Destination Type | `msisdn` (phone number) or `Customer Id` (platform identifier) |
| Destination | E.164 or hardcoded paging DID |
| From Number | Provisioned voice-enabled number |

Exit paths: `onAnswer` · `onbusy` · `onnoanswer` · `onreject` · `onError` · `oncallfail` · `onPolicyFail` · `onExpiry`

> **Casing is exact and deliberately inconsistent — do not "normalise" it.** On the **Call User** node the platform spells four events all-lowercase (`onbusy`, `onnoanswer`, `onreject`, `oncallfail`) and four in mixed case (`onAnswer`, `onError`, `onPolicyFail`, `onExpiry`) [source: https://help.webexconnect.io/docs/voice-call-user]. Casing is also **node-specific**: the **Call Patch** node (a different node, inside the Voice Node Group) uses `onNoAnswer` in mixed case [source: `docs/reference/webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Exit Paths]. Never copy one node's casing onto another.

### Play Node (TTS, inside Voice Node Group)

| Setting | Value |
|---------|-------|
| TTS Processor | Azure (only engine in Connect) |
| Voice Type | Neural (Standard deprecated) |
| Input Format | Plain Text (3,000 chars) or SSML (6,000 chars) |

## Multi-Channel Branch Configuration

| Branch Value | Routes To | Requires |
|-------------|-----------|----------|
| `sms` | SMS node | Phone number |
| `email` | Email node | Email address |
| `voice` | Call User → Voice Node Group → Play | Phone number, voice-enabled From |
| `rcs` | RCS Capability → Branch → RCS Message or SMS | Phone number, RCS app asset |
| `apple` | Branch (session?) → Apple Messages or SMS | `abcId`, active session |
| `whatsapp` | WhatsApp node | Phone number, WhatsApp asset, approved template (if proactive) |
| *(default)* | SMS | Phone number |

## Fallback Wiring

| Channel | When Fallback Fires | Fallback To |
|---------|-------------------|-------------|
| RCS | Capability check fails, `rcs.enabled=false`, `version=up1`, send error | SMS |
| Apple Messages | No active session, send error (HTTP 410) | SMS |
| Email | Send error | SMS (if phone available) |
| Voice | Call User `onbusy`, `onnoanswer`, `onreject` | SMS (optional) |
| WhatsApp | Template rejected, send error, 24hr window expired (session msg) | SMS |

SMS is always the **ultimate fallback** — every phone supports it.

## Webhook Config (Start Node)

| Property | Value |
|----------|-------|
| HTTP Method | POST only |
| Content Types | `application/json`, `application/xml` |
| Payload Limit | 256 KB default |
| Auth Options | Service key (`key` header), JWT, HMAC signature |

### Response Codes

| Code | Meaning |
|------|---------|
| 1002 | Queued — request accepted |
| 7000 | Invalid JSON |
| 7001 | Authentication failed |
| 7002 | Service Key missing |
| 7005 | Internal error |
| 7007 | Service inactive |
| 7008 | Inactive profile (this repo previously recorded it as "Invalid or unsaved event endpoint"; unconfirmed which applies to inbound webhooks specifically) |
| 7010 | Source IP not allow listed |
| 7020 | Max transaction limit reached |
| 7027 | Invalid XML |
| 7028 | Invalid signature |
| 7029 | Mandatory Signature Missing |
| 430 | Payload too large |

**Owner: `docs/reference/connect-response-codes.md` § Inbound Webhook / Event API Response Codes** (ref-tag `connect-response-codes-v1`), which carries the per-code provenance column. The table is mirrored here only so a build does not have to leave the skill mid-step — if it disagrees with the reference doc, the reference doc wins.

`7008` carries an **unresolved** conflict between Cisco's "Inactive Profile" and this repo's prior "Invalid or unsaved event endpoint"; both are retained deliberately. `7010` **is** Cisco-verified ("Source IP is not in the allowed list", `references-api-codes` Event section, corroborated by the v6.4.0 changelog) — an earlier note here called it audit-sourced-only, which was stale and is corrected. `7027`/`7028`/`7029` are **not** on that Cisco page and keep playbook-only provenance.

## Channel Provisioning Checklist

| Channel | What's Needed | Where |
|---------|--------------|-------|
| SMS | Phone number or Sender ID with SMS feature | Assets > Numbers |
| Email | Email asset (AWS SES or SMTP), domain verification (SPF/DKIM/DMARC) | Assets > Apps > Email |
| RCS | RCS app/asset, brand config, carrier approval (~7 days) | Assets > Apps > RCS |
| Apple Messages | Apple Business Register enrollment, Webex Connect as MSP | register.apple.com/business-chat + Assets > Apps |
| Voice | Voice-enabled phone number | Assets > Numbers (Voice feature) |
| WhatsApp | WhatsApp Business Account (WABA), phone verification, Meta approval for templates | Assets > Apps > WhatsApp |

## Sandbox Availability

| Channel | Available in Sandbox? |
|---------|---------------------|
| SMS | Yes (10,000 lifetime, 5 test numbers) |
| Voice | Yes (5,000 lifetime calls, 5 test numbers) |
| Email | **Limited** — AWS SES sandbox requires destination allowlisting (error 7522) |
| RCS | **No** — requires full license |
| Apple Messages | **No** — test via Apple Business Register |
| WhatsApp | Yes (10,000 lifetime combined with SMS, 5 test numbers, pre-provisioned templates only) |

## Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Variable arrives empty | Typed manually | Use variable picker |
| E.164 format error | Missing `+` or country code | Always include `+` and country code |
| RCS rich card renders as text | Recipient has `rcs.version=up1` | Branch on `version == "up2"` |
| Apple Messages 410 Gone | Customer deleted conversation | Track `CONVERSATIONCLOSED`, wire onError → SMS |
| Email From field disabled | By design | Configure sender in Assets > Apps > Email |
| SMS arrives garbled | Unicode chars with Message Type = Text | Set Message Type to Unicode |
| Flow doesn't trigger | Not Made Live | Click Make Live after saving |
| Webhook returns 7001 | Auth failed | Check `key` header matches service key |
| 30s timeout in agent flow ⚠️ | Too many nodes or Delivery Report mode | Use Gateway Submit, minimize node count |
| Contact Policy not enforced ⚠️ | Policy doesn't auto-apply to Send nodes | Add explicit consent check before sending |
| Template not in dropdown | Not yet approved by Meta | Wait for approval (24-72 hrs), check status in Tools > Templates |
| Free-form message fails outside 24hr | Session window expired | Use template message for proactive notifications |
| WhatsApp error 7710 | Re-engagement outside window | Send approved template message |

> ⚠️ **Unverified observation (rows marked ⚠️ above):** neither the **30-second execution time limit applying to notification flows** nor **Contact Policy failing to auto-enforce on Send nodes** is **confirmed in official Cisco documentation**. Both are carried forward from field observation. The recommended fixes (Gateway Submit, minimal node count, an explicit consent check before the Send node) are safe regardless, so keep applying them — but do not quote either limit to a customer as documented platform behaviour, and do not design around 30 seconds as a hard, published cap. `docs/playbooks/outbound-sms.md § Gotchas` carries the same Contact Policy caveat.

## Error Logging Pattern

When wiring onError/onPolicyFail/onTimeout exits to an error logging HTTP Request node (POST to PostgREST):

| Header | Value | Required? |
|--------|-------|-----------|
| apikey | {anon_key} | Always |
| Authorization | Bearer {anon_key} | Always |
| Content-Type | application/json | Always |
| Prefer | return=representation | Always (POST) |

The `Prefer: return=representation` header ensures PostgREST returns the inserted row, confirming the log was written. Without it, POST returns an empty `201` with no body.
