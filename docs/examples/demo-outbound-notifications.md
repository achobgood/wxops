# WxCC AI Agent Builder — Outbound Notification Walkthrough

## How This Tool Works

The `build-notification` skill guides you through building a Webex Connect flow for outbound notifications — messages sent to customers when an event occurs in your system. It supports SMS, Email, RCS, Apple Messages, WhatsApp, and multi-channel routing. You describe what you want, the skill asks targeted questions one at a time, then generates a complete notification config document with every node, field, exit path, and curl test command ready for copy-paste into Webex Connect.

---

## Scenario A: SMS Order-Ready Notification

### Interview Phase

**User:** I need to send an SMS to customers when their order is ready for pickup.

**Agent:** Got it — this is an outbound SMS notification flow, not an inbound AI agent. The build process is different: it uses a webhook trigger in Webex Connect to fire an SMS when your system sends the event. I'll walk you through it step by step.

Let's start. **What would you like to name this flow?** Use lowercase with hyphens (e.g., `order-ready-notification`).

**User:** `order-ready-sms`

**Agent:** Perfect — flow name: `order-ready-sms`.

**What triggers this notification?** Describe the event in one sentence (e.g., "A webhook fires when an order status changes to 'ready'").

**User:** A webhook fires when the order status changes to 'ready' in our system.

**Agent:** Clear. The flow will start with a webhook that your system POSTs to when an order becomes ready.

**What fields will the webhook payload include?** List the data your system sends when the event fires. I need the field names and example values so I can configure the Start node to parse them.

**User:** `{"order_id": "ORD-4521", "customer_phone": "+15551234567", "customer_name": "Sarah Chen"}`

**Agent:** Got it — three fields: `order_id`, `customer_phone`, and `customer_name`. These will be available as `$(n1.inboundWebhook.order_id)`, `$(n1.inboundWebhook.customer_phone)`, and `$(n1.inboundWebhook.customer_name)` in the flow.

**Does this flow need a database lookup before sending the SMS?** If all the data you need is in the webhook payload, we can skip the DB call. If you need additional data (e.g., item count, store location), we'll add an HTTP Request node.

**User:** Yes — I need to fetch order details (item count, store location) from Supabase.

**Agent:** Got it — we'll add an HTTP Request node after the Start node to look up the order in Supabase by `order_id` and pull back `item_count` and `store_location`.

**Which channel should this notification use?** Options: SMS, Email, Voice, RCS, Apple Messages, WhatsApp, or Multi-channel (route to customer's preferred channel with fallback).

**User:** SMS only.

**Agent:** SMS it is. Now for the SMS-specific details.

**What should the message say?** You can reference variables from the webhook payload (`customer_name`) and the DB lookup (`item_count`, `store_location`). Max 1,024 characters.

**User:** "Hi $(customer_name), your order $(order_number) with $(item_count) items is ready for pickup at $(store_location). Show this text at the counter."

**Agent:** Good message. I'll map those to the correct variable picker references in the config. Quick question — **does this message contain emoji or non-Latin characters?** This affects encoding: GSM-7 (standard Latin text) gives you 160 characters per segment, while Unicode (emoji/non-Latin) cuts that to 70.

**User:** No emoji — GSM-7 encoding is fine.

**Agent:** Perfect — Message Type will be set to `Text` (GSM-7). Your message is well under 160 characters, so it'll send as a single segment.

Last question: **What should happen if the SMS fails to send?** Options: end the flow silently, log the error to your database via HTTP Request, or fall back to another channel.

**User:** Log to DB via HTTP Request on error.

**Agent:** Got it. I'll wire the SMS node's `onError` exit to an HTTP Request node that POSTs the failure details to your database.

That's everything I need. Let me generate the complete notification config.

---

### Generated Output

## Notification Flow Config: order-ready-sms

### 1. Flow Purpose

When an order status changes to "ready," a webhook fires and the flow sends an SMS to the customer with their order details and pickup instructions.

### 2. Webhook Payload — `[External System → POST]`

```json
{
  "order_id": "ORD-4521",
  "customer_phone": "+15551234567",
  "customer_name": "Sarah Chen"
}
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| order_id | String | Unique order identifier |
| customer_phone | String | Customer's phone number in E.164 format |
| customer_name | String | Customer's display name |

### 3. Webhook URL — `[Webex Connect → Start node]`

```
https://{auto-generated-url}
```

Authentication header: `key: {service_key}`

> **Note:** The webhook URL is only generated after you save the flow. Double-click the Start node after saving to copy it.

### 4. HTTP Request Node — `[Webex Connect → HTTP Request node]`

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `https://{supabase-project-ref}.supabase.co/rest/v1/orders?order_id=eq.$(n1.inboundWebhook.order_id)&select=order_number,item_count,store_location` |

Headers:

| Header | Value |
|--------|-------|
| apikey | {supabase_anon_key} |
| Authorization | Bearer {supabase_anon_key} |
| Content-Type | application/json |
| Accept | application/vnd.pgrst.object+json |

Sample Response JSON (paste into Parse button):

```json
{
  "order_number": "ORD-4521",
  "item_count": 3,
  "store_location": "Downtown Store - 123 Main St"
}
```

Output Variables:

| Variable Name | Response Path |
|---------------|---------------|
| order_number | $.order_number |
| item_count | $.item_count |
| store_location | $.store_location |

### 5. Channel Configuration

#### Channel: SMS

| Field | Value |
|-------|-------|
| Destination Type | msisdn |
| Destination | Use variable picker → `$(n1.inboundWebhook.customer_phone)` |
| From Number | Select provisioned sender from dropdown |
| Message Type | Text (GSM-7 — no emoji, Latin characters only) |
| Wait For | Gateway Submit |

### 6. Message Content

**SMS:**
```
Hi $(n1.inboundWebhook.customer_name), your order $(n2.order_number) with $(n2.item_count) items is ready for pickup at $(n2.store_location). Show this text at the counter.
```

> **Important:** Use the variable picker to insert all `$(nX.variableName)` references. Never type them manually — manually typed variables arrive empty at runtime.

Character count: ~130 characters (well within 160-char single-segment GSM-7 limit).

### 7. Failure Handling

| Channel | Exit Path | Wired To |
|---------|-----------|----------|
| SMS | onSuccess | End |
| SMS | onError | HTTP Request (log error to DB) → End |
| SMS | onPolicyFail | End |

**Error Logging HTTP Request Node (n3):**

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `https://{supabase-project-ref}.supabase.co/rest/v1/notification_errors` |
| Body | `{"order_id": "$(n1.inboundWebhook.order_id)", "channel": "sms", "error": "send_failed", "destination": "$(n1.inboundWebhook.customer_phone)", "timestamp": "$(n1.inboundWebhook.timestamp)"}` |

Headers: same as the lookup HTTP Request (apikey, Authorization, Content-Type).

### 8. Fallback Configuration

N/A — single-channel SMS flow, no fallback needed.

### 9. Test Command

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {service_key}" \
  -d '{"order_id": "ORD-4521", "customer_phone": "+15551234567", "customer_name": "Sarah Chen"}' \
  "https://{webhook-url}"
```

Expected: Response code `1002` (queued). SMS delivered to +15551234567 with resolved variables (not literal `$(nX.var)` text).

### 10. Integration Notes

| Approach | How |
|----------|-----|
| **Application-level** | Your app POSTs to the webhook URL after updating order status to "ready" in the database |
| **Database trigger** | Supabase Database Webhook or Edge Function fires on `UPDATE orders SET status = 'ready'` |
| **Polling service** | Lightweight service polls for `status = 'ready'` rows and fires webhooks |

The simplest path: have your application code POST to the webhook URL immediately after the status change. See `webhook-triggers.md` Section 10 for Supabase-specific trigger patterns.

---

### Flow Diagram

```
Start (Webhook: order_id, customer_phone, customer_name)
  |
  v
HTTP Request (GET order details from Supabase by order_id)
  |  Output: order_number, item_count, store_location
  |
  v
SMS (destination: $(n1.inboundWebhook.customer_phone),
     from: provisioned sender,
     message: "Hi $(n1.inboundWebhook.customer_name), your order
               $(n2.order_number) with $(n2.item_count) items is ready
               for pickup at $(n2.store_location). Show this text
               at the counter.")
  |
  |--- onSuccess ---> End
  |--- onError -----> HTTP Request (POST error to notification_errors table) ---> End
  |--- onPolicyFail -> End
```

---

## Scenario B: Multi-Channel RCS + SMS Fallback

### Interview Phase

**User:** I want to send a rich notification when a customer's repair is complete. Use RCS if they support it, fall back to SMS.

**Agent:** Great — this is an outbound notification flow with RCS as the primary channel and SMS as the fallback. RCS lets you send rich cards with images, titles, and interactive buttons — but it only works on Android devices with RCS support. For everyone else (iOS, older Android), we'll automatically fall back to SMS.

The flow pattern is: Start (Webhook) → HTTP Request (DB lookup) → RCS Capability Check → Branch (supported?) → RCS Message or SMS Fallback → End.

Let's get started. **What would you like to name this flow?**

**User:** `repair-complete-notification`

**Agent:** Got it — flow name: `repair-complete-notification`.

**What triggers this notification?** Describe the event in one sentence.

**User:** Webhook fires when a repair ticket status changes to 'completed'.

**Agent:** Perfect. Your system will POST to the webhook URL when a repair ticket is marked complete.

**What fields will the webhook payload include?** List the field names and example values.

**User:** `{"ticket_id": "RPR-892", "customer_phone": "+15559876543"}`

**Agent:** Two fields: `ticket_id` and `customer_phone`. These will be available as `$(n1.inboundWebhook.ticket_id)` and `$(n1.inboundWebhook.customer_phone)` in the flow.

**Does this flow need a database lookup before sending?** If you need more data beyond what's in the webhook payload, we'll add an HTTP Request node.

**User:** Yes — fetch repair details: device_type, repair_description, cost, pickup_deadline.

**Agent:** Got it — we'll query your repairs table by `ticket_id` to get `device_type`, `repair_description`, `cost`, and `pickup_deadline`.

**Which channel(s) should this notification use?**

**User:** RCS with SMS fallback.

**Agent:** Perfect. RCS with SMS fallback follows a specific pattern:
1. **RCS Capability** node checks if the recipient's device supports RCS
2. **Branch** node routes to RCS if supported, SMS if not
3. **RCS Message** node sends the rich notification
4. **SMS** node catches all fallback cases

Now for the RCS-specific details. **What format should the RCS message use?** Options: Text (plain text, up to 1,024 chars), Rich Card (image + title + description + suggestion buttons), or Carousel (multiple cards the user swipes through).

**User:** Rich Card with title "Your Repair is Complete! ✅", description with repair details, media image of the repaired device (URL from DB), and two suggestion buttons: "Schedule Pickup" (URL) and "Call Store" (phone action).

**Agent:** Great choices. Here's what I'll configure for the Rich Card:

- **Title:** "Your Repair is Complete! ✅"
- **Description:** Repair details with dynamic variables (device_type, repair_description, cost, pickup_deadline)
- **Media:** Image URL from your DB (the repaired device photo)
- **Suggestion 1:** "Schedule Pickup" — Open URL action
- **Suggestion 2:** "Call Store" — Dial Phone action

Suggestion chip labels must be 25 characters or fewer — both of yours fit.

**What should the SMS fallback message say?** This goes to recipients whose devices don't support RCS (all iOS users, older Android). Keep it plain text — no images or buttons.

**User:** "Your $(device_type) repair is complete. Cost: $(cost). Pick up by $(pickup_deadline). Call us: 555-0100"

**Agent:** Good — clear and concise. That's well under the 160-character GSM-7 limit.

Last question: **What should happen on failure?** For RCS flows, there are two failure points: (1) the RCS Message node can fail even after passing the capability check, and (2) the SMS fallback can fail. What should happen at each?

**User:** SMS fallback on RCS error; log to DB on SMS error.

**Agent:** Perfect:
- RCS Message `onError` → SMS fallback node
- SMS `onError` → HTTP Request (log error to DB)

That's everything. Let me generate the complete notification config.

---

### Generated Output

## Notification Flow Config: repair-complete-notification

### 1. Flow Purpose

When a repair ticket status changes to "completed," a webhook fires and the flow sends a rich RCS notification (with image, details, and interactive buttons) to the customer's phone. If the recipient's device doesn't support RCS, the flow falls back to a plain-text SMS.

### 2. Webhook Payload — `[External System → POST]`

```json
{
  "ticket_id": "RPR-892",
  "customer_phone": "+15559876543"
}
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| ticket_id | String | Unique repair ticket identifier |
| customer_phone | String | Customer's phone number in E.164 format |

### 3. Webhook URL — `[Webex Connect → Start node]`

```
https://{auto-generated-url}
```

Authentication header: `key: {service_key}`

> **Note:** The webhook URL is only generated after you save the flow. Double-click the Start node after saving to copy it.

### 4. HTTP Request Node — `[Webex Connect → HTTP Request node]`

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `https://{supabase-project-ref}.supabase.co/rest/v1/repairs?ticket_id=eq.$(n1.inboundWebhook.ticket_id)&select=device_type,repair_description,cost,pickup_deadline,device_image_url,pickup_schedule_url,store_phone` |

Headers:

| Header | Value |
|--------|-------|
| apikey | {supabase_anon_key} |
| Authorization | Bearer {supabase_anon_key} |
| Content-Type | application/json |
| Accept | application/vnd.pgrst.object+json |

Sample Response JSON (paste into Parse button):

```json
{
  "device_type": "iPhone 15 Pro",
  "repair_description": "Screen replacement",
  "cost": "$129.00",
  "pickup_deadline": "March 25, 2026",
  "device_image_url": "https://cdn.example.com/repairs/RPR-892/completed.jpg",
  "pickup_schedule_url": "https://app.example.com/schedule-pickup/RPR-892",
  "store_phone": "+15550100"
}
```

Output Variables:

| Variable Name | Response Path |
|---------------|---------------|
| device_type | $.device_type |
| repair_description | $.repair_description |
| cost | $.cost |
| pickup_deadline | $.pickup_deadline |
| device_image_url | $.device_image_url |
| pickup_schedule_url | $.pickup_schedule_url |
| store_phone | $.store_phone |

### 5. Channel Configuration

#### Channel: RCS (with SMS fallback)

**Node 3: RCS Capability Check**

| Field | Value |
|-------|-------|
| Mobile Number | Use variable picker → `$(n1.inboundWebhook.customer_phone)` |
| Force Refresh | false (7-day cached lookup, near-instant) |

**Node 4: Branch (RCS Support Check)**

| Condition | Operator | Value |
|-----------|----------|-------|
| `$(n3.rcs.enabled)` | Equals | `true` |
| **AND** | | |
| `$(n3.rcs.version)` | Equals | `up2` |

- Branch label: "RCS Supported"
- "None of the above" exit → SMS fallback node

**Node 5: RCS Message (Rich Card)**

| Field | Value |
|-------|-------|
| Destination Type | MSISDN |
| Destination | Use variable picker → `$(n1.inboundWebhook.customer_phone)` |
| Message Type | Rich Card |
| Wait For | Gateway Submit |

**Node 6: SMS Fallback**

| Field | Value |
|-------|-------|
| Destination Type | msisdn |
| Destination | Use variable picker → `$(n1.inboundWebhook.customer_phone)` |
| From Number | Select provisioned sender from dropdown |
| Message Type | Text (GSM-7) |
| Wait For | Gateway Submit |

### 6. Message Content

**Rich Card (RCS):**

| Field | Value |
|-------|-------|
| Card Orientation | Vertical |
| Media URL | Use variable picker → `$(n2.device_image_url)` |
| Media Height | MEDIUM |
| Title | Your Repair is Complete! ✅ |
| Description | Your $(n2.device_type) repair ($(n2.repair_description)) is finished. Total cost: $(n2.cost). Please pick up by $(n2.pickup_deadline). |
| Suggestion 1 | Type: Open URL, Label: "Schedule Pickup", URL: `$(n2.pickup_schedule_url)` |
| Suggestion 2 | Type: Dial Phone, Label: "Call Store", Phone: `$(n2.store_phone)` |

> **Important:** Use the variable picker to insert all references in the Title, Description, and Suggestion fields. Manually typed variable references in rich card fields may arrive empty.

> **Media constraint:** Image must be publicly accessible, max 500 KB, max 2,048-character URL.

> **Suggestion label limit:** 25 characters max per chip. "Schedule Pickup" (15 chars) and "Call Store" (10 chars) both fit.

**SMS Fallback:**
```
Your $(n2.device_type) repair is complete. Cost: $(n2.cost). Pick up by $(n2.pickup_deadline). Call us: 555-0100
```

Character count: ~95 characters (single segment, GSM-7).

### 7. Failure Handling

| Channel | Exit Path | Wired To |
|---------|-----------|----------|
| RCS Capability | onSuccess | Branch (RCS support check) |
| RCS Capability | onError | SMS fallback node |
| Branch | "RCS Supported" | RCS Message node |
| Branch | "None of the above" | SMS fallback node |
| RCS Message | onSuccess/onSubmit | End |
| RCS Message | onError | SMS fallback node |
| SMS | onSuccess | End |
| SMS | onError | HTTP Request (log error to DB) → End |
| SMS | onPolicyFail | End |

**Error Logging HTTP Request Node (n7):**

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `https://{supabase-project-ref}.supabase.co/rest/v1/notification_errors` |
| Body | `{"ticket_id": "$(n1.inboundWebhook.ticket_id)", "channel": "sms_fallback", "error": "send_failed", "destination": "$(n1.inboundWebhook.customer_phone)"}` |

### 8. Fallback Configuration

| Primary Channel | Fallback Trigger | Fallback Channel |
|----------------|-----------------|-----------------|
| RCS | Capability check fails (onError) | SMS |
| RCS | Device not RCS-capable or version != up2 (Branch "None of the above") | SMS |
| RCS | RCS Message send error (onError) | SMS |

SMS Fallback message:
```
Your $(n2.device_type) repair is complete. Cost: $(n2.cost). Pick up by $(n2.pickup_deadline). Call us: 555-0100
```

Three inputs wire to the SMS fallback node:
1. RCS Capability → `onError`
2. Branch → "None of the above"
3. RCS Message → `onError`

### 9. Test Command

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {service_key}" \
  -d '{"ticket_id": "RPR-892", "customer_phone": "+15559876543"}' \
  "https://{webhook-url}"
```

Expected: Response code `1002` (queued).

**Verify:**
- RCS-capable Android device: Rich Card renders with image, title, description, and two suggestion buttons
- iOS or non-RCS device: SMS fallback delivers the plain text message
- Variables resolved (not literal `$(nX.var)` text)
- Check Flow Debug in Connect for the execution trace

**To test SMS fallback explicitly:** Send to a phone number that doesn't support RCS (any iPhone number). The flow should route through Branch → "None of the above" → SMS.

### 10. Integration Notes

| Approach | How |
|----------|-----|
| **Application-level** | Your app POSTs to the webhook URL after updating ticket status to "completed" |
| **Database trigger** | Supabase Database Webhook or Edge Function fires on `UPDATE repairs SET status = 'completed'` |
| **Change Data Capture** | Debezium or similar streams DB changes to the webhook |

The simplest path: have your application code POST to the webhook URL immediately after the status change.

---

### Flow Diagram

```
Start (Webhook: ticket_id, customer_phone)
  |
  v
HTTP Request (GET repair details from Supabase by ticket_id)
  |  Output: device_type, repair_description, cost, pickup_deadline,
  |          device_image_url, pickup_schedule_url, store_phone
  |
  v
RCS Capability (check $(n1.inboundWebhook.customer_phone), Force Refresh: false)
  |
  |--- onSuccess ---> Branch (rcs.enabled == true AND rcs.version == "up2")
  |                      |
  |                      |--- [RCS Supported] ---> RCS Message (Rich Card)
  |                      |                            Title: "Your Repair is Complete! ✅"
  |                      |                            Description: device_type, repair details, cost, deadline
  |                      |                            Media: $(n2.device_image_url)
  |                      |                            Suggestions: [Schedule Pickup] [Call Store]
  |                      |                            |
  |                      |                            |--- onSuccess ---> End
  |                      |                            |--- onError -----> SMS (fallback) ---+
  |                      |                                                                  |
  |                      |--- [None of the above] ---> SMS (fallback) ----+                 |
  |                                                                       |                 |
  |--- onError ------> SMS (fallback) ----+                               |                 |
                                          |                               |                 |
                                          v                               v                 v
                                   (All SMS fallback paths converge to one SMS node)
                                   SMS (destination: $(n1.inboundWebhook.customer_phone),
                                        message: "Your $(n2.device_type) repair is complete.
                                                  Cost: $(n2.cost). Pick up by
                                                  $(n2.pickup_deadline). Call us: 555-0100")
                                     |
                                     |--- onSuccess ---> End
                                     |--- onError -----> HTTP Request (log error to DB) ---> End
                                     |--- onPolicyFail -> End
```

---

## What Happens Next

### Make Live

1. Click **Save** in the top toolbar of Webex Connect
2. Click **Make Live** — the webhook URL only accepts requests when the flow is live
3. Copy the webhook URL from the Start node (double-click Start after saving)

### Test with curl

Fire the test commands above from your terminal or API client. Verify:
- Response code `1002` (queued)
- Message delivered to the correct channel
- Dynamic variables resolved (actual values, not literal `$(nX.var)` text)
- For Scenario B: test both RCS delivery (Android with RCS) and SMS fallback (iPhone or non-RCS device)

### Production Considerations

- **Webhook authentication:** Configure a service key (`key` header) or JWT for production webhooks. Never leave webhooks unauthenticated in production.
- **DB-triggered webhooks:** For automatic notifications on database changes, see `webhook-triggers.md` Section 10 for Supabase Database Webhook and Edge Function patterns.
- **RCS availability:** RCS is NOT available in the Webex Connect Sandbox. You need a full platform license to test RCS. SMS is available in sandbox (10,000 lifetime messages, 5 test numbers).
- **10DLC registration (US):** If sending SMS in the US on a long code, register your brand and campaign with TCR. Unregistered numbers receive error 7281.
- **Contact policy:** Webex Connect contact policy does not auto-enforce opt-out on Send nodes. Add an explicit consent check before sending if you need TCPA/GDPR compliance.
