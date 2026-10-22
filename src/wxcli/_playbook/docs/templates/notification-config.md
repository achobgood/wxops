# Notification Flow Config: [FLOW_NAME]

## 1. Flow Purpose

[One sentence: what triggers it, who gets notified, what channel(s), what they receive]

## 2. Webhook Payload -- `[External System → POST]`

```json
{
  "field1": "example_value",
  "field2": "+15551234567"
}
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| field1 | String | [description] |
| field2 | String | [description] |

## 3. Webhook URL -- `[Webex Connect → Start node]`

```
https://{auto-generated-url}
```

Authentication header: `key: {service_key}`

## 4. HTTP Request Node (if applicable) -- `[Webex Connect → HTTP Request node]`

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `https://...?id=eq.$(n1.inboundWebhook.field1)` |

Headers:

| Header | Value |
|--------|-------|
| apikey | {api_key} |
| Authorization | Bearer {api_key} |
| Content-Type | application/json |
| Accept | application/vnd.pgrst.object+json |

Sample Response JSON (paste into Parse button):

```json
{
  "field_name": "example_value"
}
```

Output Variables:

| Variable Name | Response Path |
|---------------|---------------|
| [name] | $.[path] |

## 5. Channel Configuration

### Channel: [SMS / Email / Voice / RCS / Apple Messages / WhatsApp / Multi-channel]

**For SMS:**

| Field | Value |
|-------|-------|
| Destination Type | msisdn |
| Destination | `$(n1.inboundWebhook.customer_phone)` |
| From Number | [provisioned number] |
| Message Type | Text / Unicode |
| Wait For | Gateway Submit |

**For Email:**

| Field | Value |
|-------|-------|
| Destination Type | Email ID |
| Destination ID | `$(n1.inboundWebhook.customer_email)` |
| From Email | [auto from asset] |
| Subject | [subject with variables] |
| Email Type | Text / HTML / Template |
| Wait For | Gateway Submit |

**For Voice:**

| Field | Value |
|-------|-------|
| Destination Type | MSISDN |
| Destination | `$(n1.inboundWebhook.customer_phone)` or paging DID |
| From Number | [provisioned number] |
| TTS Processor | Azure |
| Voice Type | Neural |
| Language | [e.g., English (US)] |
| Voice | [e.g., AriaNeural, GuyNeural] |
| Input Format | Plain Text / SSML |

**For RCS:**

| Field | Value |
|-------|-------|
| Capability Check | Force Refresh: false |
| Branch Condition | `rcs.enabled == true AND rcs.version == "up2"` |
| Destination Type | MSISDN |
| Destination | `$(n1.inboundWebhook.customer_phone)` |
| Message Type | Rich Card / Text / Carousel |
| Wait For | Gateway Submit |
| SMS Fallback | [yes — same content as plain text] |

**For Apple Messages:**

| Field | Value |
|-------|-------|
| Session Check | `abc_session_active == true` from DB |
| Destination Type | User ID |
| Destination | `$(nX.abc_user_id)` |
| Message Type | Rich Link / List Picker / Time Picker |
| Wait For | Gateway Submit |
| SMS Fallback | [yes — always required] |

**For WhatsApp:**

| Field | Value |
|-------|-------|
| Destination Type | msisdn |
| Destination | `$(n1.inboundWebhook.customer_phone)` |
| Message Type | Template / Session |
| Template Name | [registered template name from WhatsApp Business Manager] |
| Template Language | [e.g., en] |
| Template Parameters | [ordered parameter values mapped to `{{1}}`, `{{2}}`, etc.] |
| Wait For | Gateway Submit |
| 24-Hour Window | Session messages only allowed within 24 hours of last customer message. Outside the window, only pre-approved template messages may be sent. |

**For Multi-channel:**

| Branch Value | Channel | Fallback |
|-------------|---------|----------|
| sms | SMS | — |
| email | Email | SMS |
| voice | Voice | SMS (optional) |
| rcs | RCS (with capability check) | SMS |
| apple | Apple Messages (with session check) | SMS |
| whatsapp | WhatsApp (template or session) | SMS |
| default | SMS | — |

## 6. Message Content

[Full message text, HTML body, Rich Card fields, or TTS script with variable references]

**SMS/Text:**
```
[message body with $(nX.variableName) references]
```

**HTML (Email):**
```html
[HTML body with $(nX.variableName) references]
```

**SSML (Voice):**
```xml
<speak>
  [TTS message with $(nX.variableName) references]
</speak>
```

**Rich Card (RCS):**

| Field | Value |
|-------|-------|
| Card Orientation | Vertical / Horizontal |
| Media URL | [image URL] |
| Media Height | SHORT / MEDIUM / TALL |
| Title | [with variables] |
| Description | [with variables] |
| Suggestions | [type: label, action] |

**Carousel (RCS):**

| Card # | Title | Description | Media URL | Suggestions |
|--------|-------|-------------|-----------|-------------|
| 1 | [with variables] | [with variables] | [URL] | [type: label] |
| 2 | [with variables] | [with variables] | [URL] | [type: label] |

Card Width: SMALL / MEDIUM. Media Height must match across all cards.

**Rich Link (Apple Messages):**

| Field | Value |
|-------|-------|
| Title | [with variables] |
| Website URL | [with variables] |
| Image URL | [image URL] |
| MIME Type | image/png / image/jpeg |

**List Picker (Apple Messages):**

| Field | Value |
|-------|-------|
| Bubble Style | Small / Icon / Large |
| Title | [bubble preview text] |
| Sections | [section titles and items] |
| Multi-select | Yes / No |
| Request Identifier | [unique ID] |

**Time Picker (Apple Messages):**

| Field | Value |
|-------|-------|
| Bubble Style | Small / Icon / Large |
| Title | [bubble preview text] |
| Time Slots | [start time, duration, identifier per slot] |
| Location | [title, latitude, longitude] |
| Request Identifier | [unique ID] |

**WhatsApp Template Message:**

| Field | Value |
|-------|-------|
| Template Name | [registered template name] |
| Template Language | [e.g., en] |
| Header | [none / text / image / document / video] |
| Body Parameters | `{{1}}` = `$(nX.variableName)`, `{{2}}` = `$(nX.variableName)` |
| Footer | [optional footer text — not parameterized] |
| Buttons | [quick reply / call-to-action — as registered in template] |

**WhatsApp Session Message:**

| Field | Value |
|-------|-------|
| Message Type | Text / Image / Document / Location / Contact |
| Body | [message body with `$(nX.variableName)` references] |
| Note | Session messages are only deliverable within 24 hours of the customer's last inbound message. Outside the 24-hour window, use a pre-approved template message instead. |

## 7. Failure Handling

| Channel | Exit Path | Wired To |
|---------|-----------|----------|
| [channel] | onSuccess | End |
| [channel] | onError | End / SMS fallback / Log |

## 8. Fallback Configuration (if applicable)

| Primary Channel | Fallback Trigger | Fallback Channel |
|----------------|-----------------|-----------------|
| RCS | Capability check fails / version != up2 / send error | SMS |
| Apple Messages | No active session / send error (410 Gone) | SMS |
| WhatsApp | Template rejected / outside 24-hour window / send error | SMS |

SMS Fallback message:
```
[plain text version of the notification]
```

## 9. Test Command

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {service_key}" \
  -d '{"field1": "value", "field2": "+15551234567"}' \
  "https://{webhook-url}"
```

Expected: Response code 1002 (queued). Message delivered to correct channel. Variables resolved.

## 10. Integration Notes

How to trigger this flow from your application or database:

| Approach | How |
|----------|-----|
| **Application-level** | Your app POSTs to the webhook URL after updating the database |
| **Database trigger** | Postgres `pg_net`, Supabase Database Webhooks, or Edge Functions fire on row changes |
| **Change Data Capture** | Debezium or similar streams DB changes to the webhook |
| **Polling service** | Lightweight service polls for status changes and fires webhooks |

The simplest path: have your application code POST to the webhook URL immediately after the triggering event. See `webhook-triggers.md` Section 10 for detailed patterns.
