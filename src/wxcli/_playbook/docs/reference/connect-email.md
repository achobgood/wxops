# Webex Connect — Email Reference

<!-- ref-tag: connect-email-v4 -->

Email node for outbound email notifications — confirmations, alerts, and rich HTML messages with attachments. Supports AWS SES and SMTP sending routes, HTML templates via Email Composer, and open/click tracking.

**Prerequisite:** This document assumes familiarity with `webex-connect.md` for core flow concepts. For Email as a side-effect in AI agent flows, see also `webex-connect-advanced.md`.

---

## Node Inventory

| Node | Palette Name | Purpose |
|------|-------------|---------|
| **Email** | `Email` | Sends outbound email (text, HTML, or template) |

Single node in the Channels category. No separate "Send Email" node.

---

## Email Node Configuration

### Required Fields

| Field | Required | Details |
|-------|----------|---------|
| **Destination Type** | Yes | `Customer ID` or `Email ID` (direct address) |
| **Destination ID** | Yes | One or more email addresses. Comma-separated for multiple. Accepts variables. **Character-set restriction:** AWS SES does not support the SMTPUTF8 extension (RFC 6531). "The part of the email address that precedes the @ sign can only contain 7-bit ASCII characters." If the domain part (after the `@`) contains non-ASCII characters, it must be Punycode-encoded (RFC 3492). [source: https://help.webexconnect.io/docs/email-node] |
| **From Email** | Auto | **Disabled field** — auto-populated from the email app asset configuration. Cannot be typed manually. |
| **Subject** | Yes | Subject line with variable support. e.g., `Order Confirmed - $(n3.order_number)` |
| **Email Type** | Yes | `Text` (plain text), `Template` (HTML from Email Composer), or `HTML` (raw HTML content). Selecting `Template` or `HTML` surfaces an additional **Fallback Text** textbox — see Optional Fields. Selecting `HTML` renames the **Message** field to **HTML Content**. [source: https://help.webexconnect.io/docs/email-node] |
| **Template Type** | Conditional | Appears only when Email Type = `Template`. `Full template` = the entire email body is one Email Composer template, selected from the **Template** dropdown. `Partial template` = combine multiple partial templates at runtime (e.g. separate Header, Body, and Footer partials) via the **Add More Partial Templates** option. [source: https://help.webexconnect.io/docs/email-node] |
| **Message** | Yes | Body content — plain text, HTML markup, or template selection depending on Email Type |

### Optional Fields

| Field | Details |
|-------|---------|
| **From Name** | Sender display name (e.g., `Acme Services`) |
| **Reply-To Email** | Address where replies go instead of From address |
| **CC** | Comma-separated addresses |
| **BCC** | Comma-separated addresses |
| **Fallback Text** | Plain text fallback when HTML is unsupported (appears for Template/HTML types) |
| **List Unsubscribe URL** | Link to subscription management portal |
| **Unsubscribe Mail-To Address** | Email address for unsubscribe requests |
| **Unsubscribe Email Subject** | Subject line for mail-to unsubscribe |
| **Correlation ID** | Custom tracking identifier |
| **Callback Data** | Additional data for delivery reports (max 2,000 chars) |
| **Notify URL** | Webhook endpoint for delivery status. Toggle "Enable Notify URL Auth" for authenticated callbacks. |

### Tracking Options (AWS SES Only)

| Field | Details |
|-------|---------|
| **Enable Link Tracking** | Tracks link clicks; generates "Clicked" receipt (code 7528) |
| **Track Opens** | Monitors email open events (code 7502). Not available for plain text emails. |

### Attachment Configuration

| Field | Details |
|-------|---------|
| **Static Attachments** | Up to **5 files**, **10 MB total** — this is the attachment-field cap only, NOT the total email size limit. See § Size Limits. |
| **MIME Type** | Selected per attachment from a fixed platform list. See § Supported Attachment MIME Types below for the complete enumeration. |
| **Attachment Name** | Filename as shown to recipient |
| **Media URL** | URL where the file is hosted. **"The URL is valid and complete only when it ends with the file extension."** Cisco "recommends uploading the required attachments to Media Manager and use that URL in the attachments section." [source: https://help.webexconnect.io/docs/email-node] |
| **Dynamic Attachments** | Entered in the **Attachment Payload** field as variables or a JSON payload. Cisco: "It's recommended that you use `attachmentType: 2` (using media URL) for sending attachments." Alternatively use `attachmentType: 1` and replace `mediaUrl` with `content` holding a base64-encoded string. Each element also carries `mimeType` and `name`. The same file-extension rule above applies to `mediaUrl`. [source: https://help.webexconnect.io/docs/email-node] |

### Supported Attachment MIME Types

The MIME Type dropdown offers exactly these **39** types. Enumerated in full — do not assume an unlisted type is accepted. [source: https://help.webexconnect.io/docs/email-node]

> **Count discrepancy, resolved:** `docs/plans/2026-07-25-webex-connect-doc-audit.md` item M80 records "26 supported MIME types". That figure is **wrong**. The live page lists 39; the count was verified by extracting every MIME string from the page source (each appears a uniform 4 times, once per render pass) and independently by two documentation fetches that returned the identical 39-row table. Use 39.

| MIME Type | File Extension(s) |
|-----------|-------------------|
| `application/msword` | doc, docx |
| `application/pdf` | pdf |
| `application/rss+xml` | rss |
| `application/vnd.google-earth.kml+xml` | kml |
| `application/vnd.google-earth.kmz` | kmz |
| `application/vnd.ms-excel` | xls, xlsx |
| `application/vnd.ms-powerpoint` | pps, ppt, pptx |
| `application/vnd.oasis.opendocument.presentation` | odp |
| `application/vnd.oasis.opendocument.spreadsheet` | ods |
| `application/vnd.oasis.opendocument.text` | odt |
| `application/vnd.sun.xml.calc` | sxc |
| `application/vnd.sun.xml.writer` | sxw |
| `application/x-gzip` | gzip |
| `application/zip` | zip |
| `audio/basic` | au, snd |
| `audio/flac` | flac |
| `audio/mid` | mid, rmi |
| `audio/mp4` | m4a |
| `audio/mpeg` | mp3 |
| `audio/ogg` | oga, ogg |
| `audio/x-aiff` | aif, aifc, aiff |
| `audio/x-wav` | wav |
| `image/gif` | gif |
| `image/jpeg` | jpeg, jpg, jpe |
| `image/png` | png |
| `image/tiff` | tiff, tif |
| `image/vnd.wap.wbmp` | wbmp |
| `image/x-ms-bmp` | bmp |
| `text/calendar` | ics |
| `text/comma-separated-values` | csv |
| `text/css` | css |
| `text/html` | htm, html |
| `text/plain` | asc, c, diff, log, patch, pot, text, txt |
| `text/x-vcard` | vcf |
| `video/mp4` | mp4 |
| `video/mpeg` | mpeg, mpg, mpe |
| `video/ogg` | ogv |
| `video/quicktime` | qt, mov |
| `video/x-msvideo` | avi |

### Advanced Options

| Setting | Options | Notes |
|---------|---------|-------|
| **Wait For** | A choice of whether to wait for a **delivery report**. ⚠ Cisco documents the *behavior* but names **no option values** for the Email node — see § Wait For Setting before writing a build step that names one. | Do **not** wait for a delivery report in agent flows — it is the slow path |
| **Timeout** | UTC datetime or seconds | "You can also limit the maximum wait time by defining it in the Timeout field" — applies when waiting for a delivery report [source: https://help.webexconnect.io/docs/email-node] |
| **Expiry** | UTC or seconds | Maximum node execution duration |

### SMTP-Specific Headers

"Applicable only when SMTP based Email Sending option is enabled for your tenant." Select one of the following as the **Header Parameter**, then enter its **Value**. [source: https://help.webexconnect.io/docs/email-node]

| Header Parameter | Details |
|-------|---------|
| **Cc** | "when you want to send a copy of the email to anyone else" |
| **Bcc** | "when you want to send a copy of the email to undisclosed recipients" |
| **In-Reply-To** | "when you want to send a reply to a previous message" — SMTP header for email threading |

---

## Exit Paths

| Event | When | Color | Provenance |
|-------|------|-------|------------|
| `onSuccess` | Message submitted to gateway (when not waiting for a delivery report) or delivered (when waiting) — the Wait For option labels are undocumented for Email, see § Wait For Setting | Green | **UI-only** — not explicitly named in official Email node docs |
| `onError` | Internal error during node execution | Red | Documented general node-level event |
| `onInvalidData` | Missing or malformed required data (e.g., no destination) | Red | **UI-only** — not explicitly named in official Email node docs |
| `onPolicyFail` | Policy constraint violated | Red | Documented general node-level event |
| `onTimeout` | Timeout exceeded (Delivery Report mode) | Amber | Documented general node-level event |

`onError`, `onPolicyFail`, and `onTimeout` are documented as general node-level events [source: https://help.webexconnect.io/docs/exception-handling-at-the-node-level]. `onSuccess` and `onInvalidData` are shown in the node UI but not explicitly named in official Email node documentation — confirm both against the node in your tenant before branching on them.

---

## Output Variables

| Variable | Description |
|----------|-------------|
| `send.sentDateTime` | Timestamp when message was sent (ISO 8601 UTC) |
| `send.gatewayTid` | Gateway transaction ID |
| `send.deliveryStatusDescription` | Delivery status text |
| `send.deliveryStatusCode` | Numeric status code |
| `send.response_data` | "The response data received from the user." Example value: `[{"code":"1001","transid":"48ceebcb-8035-40d0-8f22-3608b915e2b6","description":"Queued"}]` |
| `send.response_interactive` | "The interactive response data. Captures if the interactive button in the message is tapped." |

All six variables and their descriptions: [source: https://help.webexconnect.io/docs/email-node].

---

## Email Templates

### Template Types

| Type | Description |
|------|-------------|
| **Full Template** | Single complete email (header + body + footer) |
| **Partial Template** | Reusable blocks that combine. Changes to a partial propagate to all emails using it. |

### Creating Templates

1. **Tools > Templates > Add New Template**
2. Name: lowercase letters and underscores only
3. Channel: Email
4. **Reference ID**: used for dynamic template selection in the Email node
5. Choose Full or Partial
6. Subject: max **998 characters**
7. Use the drag-and-drop **Email Composer**: layouts, text blocks, images, buttons, tables, conditional blocks, dividers
8. **Source Mode** available for direct HTML editing

### Using Templates in Flows

When Email Type = Template:
- Select from dropdown (static) or use Reference ID variable (dynamic)
- All replaceable parameters auto-load for variable mapping
- Map each parameter to a flow variable via the variable picker

### Template Limits

| Constraint | Limit |
|-----------|-------|
| Subject line | 998 characters |
| Conditional elements | Max 120 IF/ELSEIF per template |
| Template naming | Lowercase letters and underscores only |

---

## Variable Insertion

Same `$(nX.variableName)` pattern as all Connect nodes:

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook) | `$(n1.inboundWebhook.fieldName)` | `$(n1.inboundWebhook.customer_email)` |
| Trigger node, AI Agent category — presents as **Configure AI Agent Event** | `$(nX.aiAgent.entityName)` | `$(n2.aiAgent.order_id)` |
| HTTP Request output | `$(nX.outputVar)` | `$(n3.customer_name)` |

⚠ **The node-type path segments in the first two rows are unverified.** Official docs confirm only the general pattern `$(n[nodeID].[nodeType].[fieldName])` [source: https://help.webexconnect.io/docs/variable-management-in-flows]:

- `inboundWebhook` — consistent with platform behavior but not explicitly named in official documentation. Confirm the exact sub-path with the variable picker in your tenant.
- `aiAgent` — **not documented in official docs**; the AI Agent fulfillment page shows no variable-syntax example at all. Use the variable picker to confirm the exact format your tenant produces — **do not type this path from memory** [`webex-connect.md` § Variable Picker].

For **templates**, replaceable parameters are defined in the template and mapped to flow variables when selected in the Email node.

---

## Wait For Setting

⚠ **The option *labels* are not documented for the Email node.** Cisco's Email node page says only: "Before proceeding to the next node, you can choose to wait for a delivery report. You can also limit the maximum wait time by defining it in the Timeout field." It names **no** Wait For option values, and lists **no** node event names at all [source: https://help.webexconnect.io/docs/email-node].

In particular, **`Gateway Submit` is NOT documented for the Email node.** That label is a named `Wait For` option on the **SMS** node only [`connect-sms.md` § Wait For Setting]. A strict search of the Email node page on 2026-07-27 returned no occurrence of it [`docs/tests/findings/outbound-email-findings.md` #3]. **Read the actual control off the Email node in your tenant before naming an option in a build step.**

The *behavioral* choice is documented, and the practical guidance below still holds:

| Mode | Behavior | Agent Flows? | Webhook Flows? |
|------|----------|-------------|----------------|
| **Do not wait for a delivery report** — label undocumented for Email; the equivalent SMS-node label is `Gateway Submit` | Node completes once the message is handed to the email gateway | **Yes** — fast | Yes — fastest |
| **Wait for a delivery report** — behavior documented, exact label undocumented | Waits for delivery/bounce confirmation; bounded by the **Timeout** field | **No** — will time out | Yes, if needed |

---

## Sending Routes

### AWS SES

| Feature | Details |
|---------|---------|
| **Setup** | IAM user with `AmazonSESFullAccess`, `AmazonSNSFullAccess`, `AmazonS3FullAccess` |
| **Domain Verification** | Add TXT record to DNS within 24 hours |
| **DKIM** | Add 3 CNAME records; may take up to 72 hours |
| **SPF** | Automatic with default MAIL FROM domain; DNS record needed for custom MAIL FROM |
| **DMARC** | Configure policy record (`p=none`, `p=quarantine`, or `p=reject`) |
| **MX Records** | Required for inbound email capability |
| **Tracking** | Notify Status events: **Sent, Delivered, Read, Bounce, Spam, Rejected, Answered**. Click tracking is not in that set — link clicks arrive as a separate **Clicked** delivery receipt and require **Enable Link Tracking** on the node. The platform term is **Read**, not "Open", and **Spam**, not "complaint". See § Notify Status. |
| **Dedicated IPs** | Recommended ≥2; each limited to 40 TPS; automatic warm-up for new IPs |

### SMTP Route

| Feature | Details |
|---------|---------|
| **Auth** | Username/Password or OAuth 2.0 (recommended) |
| **Port & Security** | Configure port + security type (SSL, STARTTLS, None) |
| **Limitations** | Notify Status is limited to **Sent** and **Failed**. No delivery tracking, no bounce notifications, no read/click tracking. |

### Notify Status — SES vs SMTP

"Email delivery status tracking is available for emails sent via AWS SES or SMTP based Email App Assets." The set of events you can notify a URL about differs by asset type [source: https://help.webexconnect.io/docs/email-node]:

| Asset type | Notify Status events |
|---|---|
| **AWS SES based** | Sent, Delivered, Read, Bounce, Spam, Rejected, Answered |
| **SMTP based** | Sent, Failed — only these two |

- "The default retention period for email bounce list is **Seven** days for email via AWS SES. To change the retention period, reach out to your account manager."
- "Read receipts are not generated for emails sent as plain text, i.e., when the email type is text."
- **Clicked** is not a Notify Status value. Link clicks "will be sent as Clicked delivery receipt in the outbound webhook" and require **Enable Link Tracking**.
- If you branch on `Read`, `Bounce`, `Spam`, `Rejected`, or `Answered`, confirm the asset is SES-based — on an SMTP asset those events never arrive.

### SES Sandbox Caveat

SES sandbox accounts must allowlist destination email addresses. Unverified destinations get error **7522**. This is an AWS restriction on SES sandbox accounts, **separate from Webex Connect account type** — official docs do not state that the Email node is unavailable in Webex Connect sandbox/trial accounts [source: https://help.webexconnect.io/docs/email-node].

---

## Bounce Handling

- Connect **automatically handles bounces** — do NOT enable AWS SES account-level suppression lists
- Hard-bounced addresses suppressed for **7 days** (configurable 1–365 days)
- Suppression applies across **all email assets** in the account
- Code **7240** ("Already Bounced") fires when sending to a previously bounced address within retention
- **SMTP route does not receive bounce notifications**

---

## Unsubscribe Handling

- Enable "Unsubscribe" in email asset configuration
- Adds `List-Unsubscribe` and `List-Unsubscribe-Post` headers to outbound emails
- Unsubscribed addresses automatically filtered from send lists
- **Limitation:** Unsubscribe checking applies only to `To` addresses, NOT `CC` or `BCC`
- Gmail requirement (5,000+ daily): must support one-click unsubscribe
- Custom management: pass `listUnsubscribeUrl`, `unsubscribeEmailAddress`, `unsubscribeEmailSubject`

---

## Size Limits

| Constraint | Limit |
|-----------|-------|
| Total email size (AWS SES) — the error 7535 threshold | **40 MB** for accounts on v5.6.3 or later, and includes "the email text, images, attachments, and the MIME encoding" [source: https://help.webexconnect.io/changelog/product-update-april-2022]. The raised limit is not automatic — Cisco states it is granted on approval of your use case and requires an explicit subscription, so confirm your tenant's provisioned value before sizing payloads to it. |
| MIME encoding overhead | Counted inside the 40 MB total above. Cisco publishes no overhead percentage — do not assume one. |
| HTML body (API) | 500 KB |
| Static attachments | Max 5 files, 10 MB total — the Email node's own attachment-field cap: "You can add up to 5 attachments and the size cannot exceed 10 MB including all the attachments" [source: https://help.webexconnect.io/docs/email-node]. This is separate from, and much smaller than, the 40 MB total-email-size limit above. |
| Subject line (templates) | 998 characters |
| Callback data | 2,000 characters |
| Email address length | Local: 64 chars, Domain: 255 chars, Total: 320 chars |
| Max recipients per request (SES) | 50 (combined TO + CC + BCC) |

---

## Delivery Tracking (AWS SES Only)

| Event | Status Code | Available On |
|-------|-------------|-------------|
| Submitted | 7501 | SES + SMTP |
| Delivered | 7500 | SES only |
| Read (opened) | 7502 | SES only |
| Bounce | 7520 | SES only |
| Spam/Complaint | 7521 | SES only |
| Clicked | 7528 | SES only |
| Failed | — | SMTP only |

---

## Status Codes

| Code | Description |
|------|-------------|
| 7500 | Delivered |
| 7501 | Submitted |
| 7502 | Read (opened) |
| 7520 | Bounce (permanent, transient, or undetermined) |
| 7521 | Complaint (spam report) |
| 7522 | Not Verified (SES sandbox — destination not allowlisted) |
| 7523 | Invalid email address format |
| 7524 | Email address exceeds length limits |
| 7528 | Clicked (tracked link) |
| 7535 | Attachment size exceeded |
| 7536 | Template error (unable to fetch or parse) |
| 7240 | Already Bounced (within retention window) |
| 7241 | Unsubscribed (on blocked list) |
| 7553 | SMTP auth failed |
| 7554 | SMTP delivery failure |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| From Email field disabled / can't type | By design — From address comes from app asset config | Configure sender in Assets > Apps > Email |
| Variable shows literal `$(n3.order_id)` | Typed manually instead of using picker | Always use variable picker |
| Error 7522: "Not verified" | SES sandbox; destination not allowlisted | Allowlist in SES, or move to production |
| Error 7240: "Already bounced" | Previous hard bounce within retention window | Wait for retention to expire (default 7 days) |
| Error 7536: Template parse error | Template not found or invalid syntax | Verify template exists and Reference ID matches |
| Read receipts not generated | Email Type = "Text" (plain text) — "Read receipts are not generated for emails sent as plain text" — **or** the email app asset is SMTP-based. SMTP assets only ever track **Sent** and **Failed**, never **Read**. | Use "HTML" or "Template" **with an AWS SES based asset**, and enable **Track Opens**. Switching Email Type alone will not produce read receipts on an SMTP asset. |
| No delivery/bounce tracking | Using SMTP route | SMTP only tracks Submitted/Failed; switch to SES |
| CC/BCC delivery not trackable | AWS SES limitation | Track `To` recipients only |
| Unsubscribe not working for CC/BCC | Platform checks only `To` addresses | Use individual `To` sends for unsubscribe compliance |
| Emails land in spam | Missing SPF/DKIM/DMARC | Configure all three DNS records; keep spam rate < 0.10% |
| Same sender/recipient ignored | Platform drops emails where From = To | Use different sender and recipient |
| Attachment size error (7535) | For accounts on v5.6.3 or later, total email size exceeds **40 MB** (email text + images + attachments + MIME encoding). The static attachment field has a separate 10 MB cap that is enforced independently. | Reduce the total payload below 40 MB, and keep the static attachment set at 5 files / 10 MB or under. If the tenant was never subscribed to the raised 40 MB limit, confirm the provisioned value with Cisco before troubleshooting further — see § Size Limits. |
| Max 50 recipients per request | SES limit on combined TO + CC + BCC | Split into multiple sends |

---

## References

- [Email Node](https://help.webexconnect.io/docs/email-node)
- [Email Channel Setup](https://help.webexconnect.io/docs/email)
- [Email Templates](https://help.webexconnect.io/docs/templates-email)
- [Email API (Send Message v2)](https://developers.webexconnect.io/reference/email-api)
- [Email FAQs](https://developers.webexconnect.io/reference/email-faqs)
- [Email Deliverability Best Practices](https://help.webexconnect.io/docs/best-practices-to-improve-email-deliverability)
- [Email Status Codes](https://developers.webexconnect.io/reference/channel-specific-status-codes)
- [Data Streams - Email](https://developers.webexconnect.io/reference/data-streams-email)
- [Product Update April 2022 (v5.6.3) — 40 MB email size limit](https://help.webexconnect.io/changelog/product-update-april-2022)

## See Also

- [webex-connect.md](webex-connect.md) — the Connect flow basics the Email node builds on
- [webex-connect-advanced.md](webex-connect-advanced.md) — other Connect node types
- [connect-sms.md](connect-sms.md) — the SMS channel, a common fallback from email
- [outbound-email.md](../playbooks/outbound-email.md) — the outbound email build steps that pair with this reference
