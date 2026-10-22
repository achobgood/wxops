# Outbound Email Playbook

## Overview

This playbook covers how to build outbound email notifications in Webex Connect — webhook-triggered flows that send an email with dynamic content. This is the pattern for order confirmations, shipping updates, appointment summaries, and any notification where rich formatting or attachments matter.

**Key distinction from AI Agent flows:** Outbound email flows use the **Start node** (webhook trigger) and **Email node** — NOT the Receive node / AI Agent Event / Flow Outcomes pattern documented in `connect-flows.md`.

For webhook setup, authentication, and testing: see `webhook-triggers.md`. This playbook assumes the webhook infrastructure is already configured.

---

## 1. Flow Structure

An outbound email flow follows this pattern:

```
Start (Webhook) → [Optional: HTTP Request] → Email → End
```

### Required Nodes

- **Start node** (always first): webhook trigger receives the external event
- **Email node**: sends the outbound email
- **End node**: terminates the flow

### Optional Nodes

- **HTTP Request node** (before Email): fetch dynamic data from a DB/API before composing the message
- **Branch node** (after Email): handle different send outcomes (success, error, invalid data)
- **Evaluate node** (before Email): transform or format variables before inserting into the subject/body

---

## 2. Email Node Configuration

The **Email node** lives in the Channels category on the flow palette. Walk through these fields in order:

### Step 1: Destination

| Field | Value |
|-------|-------|
| **Destination Type** | `Email ID` (direct address) for webhook-triggered flows |
| **Destination ID** | One or more email addresses, comma-separated. Use a variable: `$(n1.inboundWebhook.customer_email)` |

### Step 2: From Email

**This field is disabled.** The From address is auto-populated from the email app asset configuration. You cannot type a sender address manually — configure it in **Assets > Apps > Email**.

### Step 3: From Name and Reply-To

| Field | Value |
|-------|-------|
| **From Name** | Display name shown to recipient (e.g., `Acme Services`). Optional. |
| **Reply-To Email** | Address where replies go instead of the From address. Optional. |

### Step 4: Subject

Enter the subject line with variable support:

```
Order Confirmed - $(n3.order_number)
```

### Step 5: Email Type

Choose one of three types — this controls what the Message field accepts:

| Type | Use When |
|------|----------|
| **Text** | Plain text only. No formatting, no open tracking. |
| **HTML** | Raw HTML markup in the message body. Full formatting control. |
| **Template** | Pre-built template from Email Composer. Select from dropdown and map variables. |

When **HTML** or **Template** is selected, a **Fallback Text** field appears — enter a plain text version used when the recipient's email client cannot render HTML.

### Step 6: Message Body

Compose the body content based on your Email Type selection. See section 4 for composition details.

### Wait For Setting

| Mode | Behavior | Use in Agent Flows? |
|------|----------|---------------------|
| **Gateway Submit** | Node exits as soon as message enters email gateway queue | **Yes** — fast |
| **Delivery Report** | Node blocks until delivery/bounce confirmation (seconds to minutes) | **No** — will timeout |

**Always use Gateway Submit** in AI agent flows (AI agent flows have a 30-second timeout limit). Webhook-triggered flows can use Delivery Report if you need bounce confirmation before proceeding.

### Exit Paths

| Event | When |
|-------|------|
| `onSuccess` | Message submitted to gateway (Gateway Submit) or delivered (Delivery Report) |
| `onError` | Internal error during node execution |
| `onInvalidData` | Missing or malformed required data (e.g., no destination) |
| `onPolicyFail` | Policy constraint violated |
| `onTimeout` | Timeout exceeded (Delivery Report mode only) |

`onError`, `onPolicyFail`, and `onTimeout` are documented as general node-level events. `onSuccess` and `onInvalidData` are shown in the node UI but not explicitly named in official Email node documentation.

### Output Variables

| Variable | Description |
|----------|-------------|
| `send.sentDateTime` | Timestamp when message was sent (ISO 8601 UTC) |
| `send.gatewayTid` | Gateway transaction ID |
| `send.deliveryStatusDescription` | Delivery status text |
| `send.deliveryStatusCode` | Numeric status code |
| `send.response_data` | Gateway response data |
| `send.response_interactive` | Interactive button interaction data |

See `connect-email.md` for the full field list, optional fields (CC, BCC, Fallback Text, List Unsubscribe, Correlation ID, Notify URL, Callback Data), tracking options, and advanced settings.

---

## 3. Variable Insertion

Use Connect's standard `$(nX.variableName)` syntax to insert dynamic values into the subject and body. **Always use the variable picker** — manually typed variables may arrive as literal text.

### HTML Example with Variables

```html
<h2>Order Confirmation</h2>
<p>Hi $(n3.customer_name),</p>
<p>Your order <strong>$(n3.order_number)</strong> has been confirmed.</p>
<ul>
  <li>Items: $(n3.item_summary)</li>
  <li>Total: $(n3.order_total)</li>
  <li>Estimated delivery: $(n3.delivery_date)</li>
</ul>
<p>Thank you for your business.</p>
```

### Variable Sources

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook payload) | `$(n1.inboundWebhook.fieldName)` (sub-path may vary by node version) | `$(n1.inboundWebhook.customer_email)` |
| HTTP Request node output | `$(nX.outputVar)` | `$(n3.customer_name)` |
| Evaluate script output | `$(nX.outputName)` | `$(n4.formatted_date)` |
| Evaluate custom flow variable | `$(variableName)` — no node prefix | `$(formatted_date)` |

For **templates**, replaceable parameters are defined in the template itself. When you select a template in the Email node, all parameters auto-load for mapping to flow variables via the picker.

---

## 4. Message Composition

### Email Type: Text

Plain text body. No formatting, no images, no tracking. Use for simple transactional messages where rendering consistency across all clients is critical.

### Email Type: HTML

Raw HTML markup typed directly into the message body. Full control over layout, styling, and structure.

```html
<div style="font-family: Arial, sans-serif; max-width: 600px;">
  <h2 style="color: #333;">Your Order is Confirmed</h2>
  <p>Hi $(n3.customer_name),</p>
  <p>Order <strong>$(n3.order_number)</strong> — $(n3.item_count) items, total $(n3.order_total).</p>
  <p>Estimated delivery: $(n3.delivery_date)</p>
</div>
```

**Tip:** Use inline CSS — many email clients strip `<style>` blocks and ignore external stylesheets.

### Email Type: Template

Uses a pre-built template from the Email Composer (**Tools > Templates > Add New Template**):

1. Create the template: in the Add New Template flow, select **Email** as the channel type, then build with drag-and-drop blocks (layouts, text, images, buttons, tables)
2. Define replaceable parameters in the template
3. In the Email node, select the template from the dropdown (or use Reference ID for dynamic selection)
4. Map each parameter to a flow variable via the picker

Templates support partial templates (reusable header/footer blocks) and conditional elements (up to 120 IF/ELSEIF per template).

See `connect-email.md` for template creation steps, naming rules, and limits.

---

## 5. Attachments

The Email node supports both static and dynamic attachments.

### Static Attachments

| Constraint | Limit |
|-----------|-------|
| Max files | 5 |
| Max total size | 10 MB |

For each attachment, provide:
- **MIME Type** — select from the list (PDF, Word, Excel, images, etc.)
- **Attachment Name** — filename shown to recipient
- **Media URL** — publicly accessible URL where the file is hosted

### MIME Encoding Overhead

The total size sent through AWS SES includes email text, images, attachments, and MIME encoding combined. The static attachment field has a 10 MB UI limit; the error 7535 threshold for v5.63+ tenants is 40 MB total.

### Dynamic Attachments

Pass a JSON payload with `attachmentType: 2` (media URL) or `attachmentType: 1` (base64 encoded) for programmatic attachment inclusion.

See `connect-email.md` for full attachment configuration, dynamic attachment format, and size limit details.

---

## 6. Channel Prerequisites

### Email Asset Setup

Email sending requires a configured email app asset (**Assets > Apps > Email**). This is where the From address, sending route, and domain settings are configured.

### Sending Routes

| Route | Tracking | Bounce Handling | Setup Complexity |
|-------|----------|-----------------|-----------------|
| **AWS SES** | Sent, Delivered, Read, Bounce, Spam, Rejected, Answered (Click tracking requires Enable Link Tracking) | Automatic suppression | Higher (IAM, DNS records) |
| **SMTP** | Sent/Failed only | No bounce notifications | Lower (credentials or OAuth) |

AWS SES provides delivery tracking, bounce handling, and compliance features that SMTP lacks — consider it for production workloads.

### DNS Authentication (Required for Deliverability)

| Record | Purpose |
|--------|---------|
| **TXT** | Domain ownership verification (required by AWS SES before sending) |
| **SPF** | Authorizes SES to send on behalf of your domain |
| **DKIM** | 3 CNAME records; cryptographic signature on outbound email |
| **DMARC** | Policy record (`p=none`, `p=quarantine`, or `p=reject`) for alignment enforcement |

Missing SPF/DKIM/DMARC is the most common cause of emails landing in spam.

### Sandbox Note

**AWS SES sandbox mode** requires all destination email addresses to be allowlisted — unverified destinations get error **7522**. This is an AWS restriction on SES sandbox accounts, separate from Webex Connect account type.

See `connect-email.md` for full SES setup steps, SMTP configuration, dedicated IP guidance, and bounce handling rules.

---

## 7. Complete Flow Example: Order Confirmation Email

```
Start (Webhook: order_id, customer_email)
  |
  v
HTTP Request (GET order details from DB by order_id)
  |
  v
Email (destination: $(n1.inboundWebhook.customer_email),
       subject: "Order Confirmed - $(n3.order_number)",
       type: HTML,
       body: "<h2>Order Confirmation</h2>
              <p>Hi $(n3.customer_name),</p>
              <p>Your order <strong>$(n3.order_number)</strong> has been confirmed.</p>
              <p>Items: $(n3.item_summary)</p>
              <p>Total: $(n3.order_total)</p>
              <p>Estimated delivery: $(n3.delivery_date)</p>")
  |
  |--- onSuccess -------> End
  |--- onError ---------> End (or: log error via HTTP Request)
  |--- onInvalidData ----> End
  |--- onPolicyFail -----> End
```

### Webhook Payload

```json
{
  "order_id": "ORD-4521",
  "customer_email": "customer@example.com"
}
```

### curl Test

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {your_service_key}" \
  -d '{"order_id": "ORD-4521", "customer_email": "customer@example.com"}' \
  "https://{your-webhook-url}"
```

---

## 8. Known Gotchas

| Issue | Fix |
|-------|-----|
| From Email field disabled / can't type | By design — From address comes from app asset config. Configure in Assets > Apps > Email. |
| Variable shows literal `$(n3.order_id)` in email | Typed manually instead of using variable picker. Always use the picker. |
| Error 7522: "Not verified" | SES sandbox — destination email not allowlisted. Allowlist in SES console, or move to production. |
| Emails land in spam | Missing SPF/DKIM/DMARC DNS records. Configure all three; keep spam complaint rate below 0.10%. |
| Attachment size error (7535) | For v5.63+ tenants, total email size exceeds 40 MB (includes email text, images, attachments, and MIME encoding). The static attachment field has a separate 10 MB UI limit. |
| Read receipts not generated | Email Type set to "Text" (plain text), or using an SMTP asset. Use "HTML" or "Template" with an AWS SES asset — SMTP assets only track Sent and Failed, never Read. |

Full gotcha list with causes: see `connect-email.md`.

---

## References

- [Email Node](https://help.webexconnect.io/docs/email-node)
- [Email Channel Setup](https://help.webexconnect.io/docs/email)
- [Email Templates](https://help.webexconnect.io/docs/templates-email)
- [Email Deliverability Best Practices](https://help.webexconnect.io/docs/best-practices-to-improve-email-deliverability)
- [Email Status Codes](https://developers.webexconnect.io/reference/channel-specific-status-codes)
- Complete field reference, templates, sending routes, and bounce handling: `connect-email.md`
- Webhook setup, authentication, and testing: `webhook-triggers.md`
