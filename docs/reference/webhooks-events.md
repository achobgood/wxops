<!-- Updated by playbook session 2026-03-18 -->
# Webhooks & Telephony Events Reference

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: webex-cloud-calling.json
- developer.webex.com Webhooks APIs

Webex webhooks deliver real-time notifications to your application when resources change. This document covers webhook CRUD operations and the `telephony_calls` resource events specific to Webex Calling.

## Table of Contents

1. [Webhook CRUD Operations](#1-webhook-crud-operations)
2. [Webhook Data Model](#2-webhook-data-model)
3. [Webhook Resources (All Available)](#3-webhook-resources-all-available)
4. [Telephony Call Events](#4-telephony-call-events)
5. [Filtering Telephony Webhooks](#5-filtering-telephony-webhooks)
6. [Webhook Setup: Step-by-Step](#6-webhook-setup-step-by-step)
7. [Webhook Event Data Class Hierarchy](#7-webhook-event-data-class-hierarchy)
8. [Webhook Security: HMAC Signature Verification](#8-webhook-security-hmac-signature-verification)
9. [Key Gotchas](#9-key-gotchas)

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark:calls_read` | Required to create a webhook for `telephony_calls` resource (user-level) |
| `spark:all` | Firehose webhook (resource=`all`, event=`all`) |

Creating a webhook requires **read** scope on the resource the webhook is for. For telephony call events, that means `spark:calls_read`.

---

## Raw HTTP Reference (All Webhook Endpoints)

Webhook endpoints use standard REST verbs on `https://webexapis.com/v1/webhooks`. No special scoping beyond read access for the target resource.

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"
```

### Webhook CRUD Endpoints

| Action | Method | URL | Body / Params |
|--------|--------|-----|---------------|
| List Webhooks | GET | `{BASE}/webhooks` | Query: `ownedBy` (optional) |
| Create Webhook | POST | `{BASE}/webhooks` | `name`, `targetUrl`, `resource`, `event`, `filter`, `secret`, `ownedBy` |
| Get Webhook | GET | `{BASE}/webhooks/{webhookId}` | (none) |
| Update Webhook | PUT | `{BASE}/webhooks/{webhookId}` | `name`, `targetUrl`, `secret`, `status` |
| Delete Webhook | DELETE | `{BASE}/webhooks/{webhookId}` | (none) |

### Raw HTTP Examples

#### Create a telephony call webhook

```python
body = {
    "name": "Call Events",
    "targetUrl": "https://example.com/webhooks/calls",
    "resource": "telephony_calls",
    "event": "all",
    "secret": "my-hmac-secret"
}
result = api.session.rest_post(f"{BASE}/webhooks", json=body)
# Returns: {id, name, targetUrl, resource, event, status, created, orgId, ...}
webhook_id = result["id"]
```

#### List all webhooks

```python
result = api.session.rest_get(f"{BASE}/webhooks")
webhooks = result.get("items", [])
for wh in webhooks:
    print(f"{wh['id']} | {wh['resource']} | {wh['event']} | {wh['status']}")
```

#### Get webhook details

```python
result = api.session.rest_get(f"{BASE}/webhooks/{webhook_id}")
# Returns full webhook object
```

#### Update a webhook (reactivate after auto-deactivation)

```python
body = {
    "name": "Call Events (reactivated)",
    "targetUrl": "https://example.com/webhooks/calls",
    "status": "active"
}
result = api.session.rest_put(f"{BASE}/webhooks/{webhook_id}", json=body)
```

#### Delete a webhook

```python
api.session.rest_delete(f"{BASE}/webhooks/{webhook_id}")
# Returns 204 (no content)
```

#### Create filtered webhook (incoming calls only)

```python
body = {
    "name": "Incoming Calls",
    "targetUrl": "https://example.com/webhooks/incoming",
    "resource": "telephony_calls",
    "event": "all",
    "filter": "personality=terminator"
}
result = api.session.rest_post(f"{BASE}/webhooks", json=body)
```

### Raw HTTP Gotchas

1. **List response key is `items`** -- `GET /webhooks` returns `{"items": [...]}`, not a bare array.
2. **Update uses PUT, not PATCH** -- You must supply all updatable fields (`name`, `targetUrl`, `secret`, `status`), not just the changed ones.
3. **Cannot change resource/event/filter** -- These are immutable after creation. Delete and recreate instead.
4. **Delete returns 204** -- No response body on successful deletion.
5. **`ownedBy` on create vs list** -- On create, set `"ownedBy": "org"` for org-level webhooks. On list, pass as query param to filter.
6. **For telephony events** -- Set `resource` to `"telephony_calls"` (underscore, not hyphen). The `event` field is the webhook trigger type (`created`, `updated`, `deleted`, `all`), distinct from `data.eventType` in the delivered payload.

---

## 1. Webhook CRUD Operations

All webhook management is under `POST/GET/PUT/DELETE /v1/webhooks`.

### Create Webhook

```
POST /v1/webhooks
```

**SDK Signature:**
```python
WebhookApi.create(
    name: str,                          # user-friendly name
    target_url: str,                    # URL that receives POST requests
    resource: WebhookResource,          # e.g. 'telephony_calls'
    event: WebhookEventType,            # e.g. 'all', 'created', 'updated', 'deleted'
    filter: str = None,                 # scope filter (see Filtering section)
    secret: str = None,                 # HMAC secret for payload signature
    owned_by: str = None                # 'org' for org-level webhooks
) -> Webhook
```

**Request body:**
```json
{
  "name": "My Telephony Webhook",
  "targetUrl": "https://example.com/webhooks/calls",
  "resource": "telephony_calls",
  "event": "all",
  "secret": "my-secret-for-hmac"
}
```

**Response (201):**
```json
{
  "id": "Y2lzY29zcGFyay...",
  "name": "My Telephony Webhook",
  "targetUrl": "https://example.com/webhooks/calls",
  "resource": "telephony_calls",
  "event": "all",
  "status": "active",
  "created": "2024-01-15T10:30:00.000Z",
  "orgId": "OWM5LTRINWQt...",
  "createdBy": "YzOC1jODQw...",
  "appId": "Y2lzY29zcGFyay..."
}
```

---

### List Webhooks

```
GET /v1/webhooks
```

**SDK Signature:**
```python
WebhookApi.list(owned_by: str = None) -> Generator[Webhook, None, None]
```

Returns a paginated generator of all webhooks. Use `owned_by='org'` to filter to org-level webhooks only.

---

### Get Webhook Details

```
GET /v1/webhooks/{webhookId}
```

**SDK Signature:**
```python
WebhookApi.details(webhook_id: str) -> Webhook
```

---

### Update Webhook

```
PUT /v1/webhooks/{webhookId}
```

**SDK Signature:**
```python
WebhookApi.update(webhook_id: str, update: Webhook) -> Webhook
```

**Updatable fields:** `name`, `targetUrl`, `secret`, `status`

All other fields are ignored if supplied. You can reactivate an auto-deactivated webhook by setting `status` to `active`, but you **cannot** use this call to deactivate a webhook.

---

### Delete Webhook

```
DELETE /v1/webhooks/{webhookId}
```

**SDK Signature:**
```python
WebhookApi.webhook_delete(webhook_id: str) -> None
```

---

## 2. Webhook Data Model

### Webhook Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique webhook identifier |
| `name` | str | User-friendly name |
| `targetUrl` | str | URL that receives POST requests |
| `resource` | WebhookResource | Resource type (e.g., `telephony_calls`) |
| `event` | WebhookEventType | Event type (e.g., `created`, `updated`, `deleted`, `all`) |
| `filter` | str (optional) | Filter defining webhook scope |
| `secret` | str (optional) | Secret for HMAC payload signature |
| `status` | WebhookStatus | `active` or `inactive` |
| `created` | datetime | When the webhook was created |
| `orgId` | str (optional) | Organization ID |
| `createdBy` | str (optional) | Person ID of creator |
| `appId` | str (optional) | Application ID |
| `ownedBy` | str (optional) | `creator` or `org` |

### WebhookStatus

| Value | Description |
|-------|-------------|
| `active` | Webhook is active and receiving events |
| `inactive` | Webhook is inactive (auto-deactivated after delivery failures) |

---

## 3. Webhook Resources (All Available)

| Resource Value | Description |
|----------------|-------------|
| `telephony_calls` | Webex Calling call events |
| `telephony_conference` | Webex Calling conference controls |
| `telephony_mwi` | Voicemail message waiting indicator |
| `messages` | Messaging (chat) |
| `memberships` | Room/space memberships |
| `rooms` | Rooms/spaces |
| `meetings` | Meetings |
| `recordings` | Meeting recordings |
| `convergedRecordings` | Converged (call) recordings |
| `meetingParticipants` | Meeting participants |
| `meetingTranscripts` | Meeting transcripts |
| `attachmentActions` | Attachment/card actions |
| `dataSources` | Data sources |
| `serviceApp` | Service app authorization |
| `adminBatchJobs` | Admin batch jobs |
| `all` | Firehose: all resources |

---

## 4. Telephony Call Events

The `telephony_calls` resource uses the standard webhook event types (`created`, `updated`, `deleted`) which map to specific telephony event types in the `data.eventType` field.

### Event Type Mapping

| Webhook `event` | `data.eventType` values | When it fires |
|-----------------|------------------------|---------------|
| `created` | `answered` | A call was answered |
| `created` | `alerting` | A call is ringing on the user's devices |
| `updated` | `connected` | A call transitioned to connected state |
| `updated` | `held` | The user placed the call on hold |
| `updated` | `remoteHeld` | The remote party placed the call on hold |
| `updated` | `resumed` | A held call was resumed |
| `updated` | `recording` | Recording state changed on the call |
| `deleted` | `disconnected` | A call ended (hung up) |
| `deleted` | `forwarded` | A call was forwarded away from the user |

<!-- Partial verification 2026-03-19: event_type is a free-form str (not an enum), so additional values beyond those listed may appear. The listed values (alerting, answered, connected, held, remoteHeld, resumed, recording, disconnected, forwarded) match the wxc_sdk TelephonyEventData class and Webex developer docs. Full confirmation requires receiving live call events. -->

### Event Payload Structure

When a webhook fires, Webex sends a POST to your `targetUrl` with the full webhook object plus event-specific `data`.

**Full event payload (disconnected call example):**
```json
{
  "id": "Y2lzY29zcGFyazovL3VzL1...",
  "name": "My Telephony Webhook",
  "targetUrl": "https://example.com/webhooks/calls",
  "resource": "telephony_calls",
  "event": "deleted",
  "orgId": "OWM5LTRINWQtYjZiOCO5NDZ3MGI...",
  "createdBy": "YzOC1jODQwLTMmU...",
  "appId": "Y2lzY29zcGFyazovLY...",
  "ownedBy": "creator",
  "status": "active",
  "created": "2022-09-14T18:03:25.829Z",
  "actorId": "Y2lzY29zcGFyazovL3VzL1...",
  "data": {
    "eventType": "disconnected",
    "actorPersonId": "RS84MWNhZjUzOC1j...",
    "orgId": "OWM5LTRINWQtYjZiOCO5NDZ3MGI...",
    "eventTimestamp": "2022-10-15T18:06:20.781Z",
    "callId": "Y2lzY29zcGFyazovL3Vz...",
    "callSessionId": "OGQ3YzhkNzgtZjIxZib...",
    "personality": "terminator",
    "state": "disconnected",
    "remoteParty": {
      "name": "agent x",
      "number": "1012",
      "personId": "Y2lzY29zcGFyazovL3V...",
      "privacyEnabled": false,
      "callType": "location"
    },
    "created": "2022-09-15T18:06:10.269Z",
    "answered": "2022-09-15T18:06:17.211Z",
    "disconnected": "2022-09-15T18:06:20.781Z"
  }
}
```

### Event Data Fields (`data` object)

The `data` object in telephony_calls events corresponds to the SDK's `TelephonyEventData` class, which extends both `WebhookEventData` and `TelephonyCall`.

| Field | Type | Description |
|-------|------|-------------|
| `eventType` | str | Telephony event type: `alerting`, `answered`, `connected`, `held`, `remoteHeld`, `resumed`, `recording`, `disconnected`, `forwarded` |
| `actorPersonId` | str | Person ID of the actor who triggered the event |
| `orgId` | str | Organization ID |
| `eventTimestamp` | datetime | When the event occurred |
| `callId` | str | Unique call identifier |
| `callSessionId` | str | Session ID to correlate multiple calls in the same session |
| `personality` | str | `originator`, `terminator`, or `clickToDial` |
| `state` | str | Current call state: `connecting`, `alerting`, `connected`, `held`, `remoteHeld`, `disconnected` |
| `remoteParty` | object | Details of the other party (see below) |
| `appearance` | int (optional) | Appearance value for call ordering |
| `created` | datetime | When the call was created |
| `answered` | datetime (optional) | When the call was answered |
| `disconnected` | datetime (optional) | When the call was disconnected |
| `redirections` | array (optional) | Previous redirections (most recent first) |
| `recall` | object (optional) | Recall details (e.g., park recall) |
| `recordingState` | str (optional) | `pending`, `started`, `paused`, `stopped`, `failed` |

### remoteParty Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | str (optional) | Party name |
| `number` | str | Party number (digits or URI) |
| `personId` | str (optional) | Person ID |
| `placeId` | str (optional) | Place ID |
| `privacyEnabled` | bool | Whether privacy is enabled |
| `callType` | str | `location`, `organization`, `external`, `emergency`, `repair`, `other` |

---

### 4b. Messaging Resource Events

The messaging webhook resources (`messages`, `memberships`, `rooms`, `attachmentActions`) follow the same delivery pattern as telephony: Webex POSTs to your `targetUrl` with the webhook envelope plus a `data` object containing resource metadata.

**Critical gotcha for `messages` webhooks:** The webhook payload does NOT include the message text when the receiving token is a bot. The bot must call `GET /messages/{messageId}` (or `wxcli messages show MESSAGE_ID`) to retrieve the actual message content. This is the standard bot pattern: webhook fires → bot fetches message → bot processes text.

<!-- Verified: messages, memberships, and attachmentActions data fields confirmed via wxc_sdk source (MessagesData, MembershipsData, AttachmentActionData classes) 2026-03-19. rooms data fields unverifiable (no RoomsData class in SDK). -->

#### messages Resource

| Webhook `event` | When It Fires |
|-----------------|---------------|
| `created` | A message was posted to a space |
| `updated` | A message was edited | <!-- Verified via wxc_sdk firehose.py example 2026-03-19 -->
| `deleted` | A message was deleted from a space |

**Event payload `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Message ID |
| `roomId` | str | Space the message was posted in |
| `roomType` | str | `direct` or `group` |
| `personId` | str | Person who sent the message |
| `personEmail` | str | Email of the sender |
| `created` | datetime | When the message was created |

<!-- Verified via wxc_sdk MessagesData class 2026-03-19 -->

**Note:** `text` is NOT included in the webhook payload for bot tokens (security measure). Always call `wxcli messages show MESSAGE_ID` to retrieve the text.

**CLI to fetch full message:**
```bash
wxcli messages show MESSAGE_ID
```

#### memberships Resource

| Webhook `event` | When It Fires |
|-----------------|---------------|
| `created` | Someone was added to a space |
| `updated` | A membership was changed (e.g., moderator status) |
| `deleted` | Someone was removed from a space |

**Event payload `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Membership ID |
| `roomId` | str | Space the membership is in |
| `personId` | str | Person whose membership changed |
| `personEmail` | str | Email of the person |
| `personDisplayName` | str (optional) | Display name of the person |
| `personOrgId` | str (optional) | Organization ID of the person |
| `isModerator` | bool | Whether the person is a moderator |
| `isMonitor` | bool | Whether the person is a monitor (deprecated) |
| `isRoomHidden` | bool (optional) | Whether the direct type room is hidden |
| `roomType` | str (optional) | Type of room (`direct` or `group`) |
| `created` | datetime | When the membership was created |

<!-- Verified via wxc_sdk MembershipsData class (inherits Membership) 2026-03-19 -->

#### rooms Resource

| Webhook `event` | When It Fires |
|-----------------|---------------|
| `created` | A new space was created |
| `updated` | A space was modified (title, lock status, etc.) |

**Event payload `data` fields:**

<!-- Partial verification 2026-03-19: Rooms webhook creation confirmed via live API. The Webex Filtering Webhooks guide confirms `type` and `isLocked` as valid rooms filter fields, implying these are present in the data payload. Full data field confirmation requires receiving a live rooms event. -->

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Space (room) ID |
| `title` | str | Space title |
| `type` | str | `direct` or `group` |
| `isLocked` | bool | Whether the space is locked |
| `creatorId` | str | Person ID of the space creator |
| `created` | datetime | When the space was created |
| `lastActivity` | datetime | Timestamp of last activity |

#### attachmentActions Resource

| Webhook `event` | When It Fires |
|-----------------|---------------|
| `created` | A user submitted an adaptive card (`Action.Submit`) |

**Event payload `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Attachment action ID |
| `type` | str | Always `submit` |
| `messageId` | str | ID of the message containing the card |
| `personId` | str | Person who submitted the card action |
| `roomId` | str | Space where the card was submitted |
| `created` | datetime | When the action was submitted |

<!-- Verified via wxc_sdk AttachmentActionData class 2026-03-19 -->

**Note:** `inputs` (the user's form values) are NOT included in the webhook payload. Call `wxcli attachment-actions show ACTION_ID` to retrieve the submitted values.

**CLI to fetch card response inputs:**
```bash
wxcli attachment-actions show ACTION_ID
```

---

## 5. Filtering Telephony Webhooks

Use the `filter` parameter when creating a webhook to narrow which events are delivered.

### Filter Syntax

Filters use the format: `fieldName=value` or `fieldName=value1,value2` for multiple values.

**Available filters for `telephony_calls`:**

<!-- Verified via live API 2026-03-19: API error message confirms exactly these 5 filters. All 5 tested and accepted. -->

| Filter | Example | Description |
|--------|---------|-------------|
| `personality` | `personality=terminator` | Only incoming calls |
| `personality` | `personality=originator` | Only outgoing calls |
| `state` | `state=connected` | Only connected state events |
| `callType` | `callType=external` | Only external calls |
| `personId` | `personId=Y2lzY29z...` | Only events for a specific person |
| `address` | `address=+15551234567` | Only events for a specific phone number or SIP address |

**Available filters for messaging resources:**

<!-- Verified via live API 2026-03-19: API error messages confirm complete filter lists for messages and memberships. mentionedPeople=me, personEmail, roomId all tested and accepted. -->

| Resource | Filter | Example | Description |
|----------|--------|---------|-------------|
| `messages` | `roomId` | `roomId=Y2lz...` | Only messages in a specific space |
| `messages` | `roomType` | `roomType=group` | Only messages in `direct` or `group` spaces |
| `messages` | `personId` | `personId=Y2lz...` | Only messages from a specific person |
| `messages` | `personEmail` | `personEmail=user@example.com` | Only messages from a specific email |
| `messages` | `mentionedPeople` | `mentionedPeople=me` | Only messages that @mention someone (use `me` for the authenticated user) |
| `messages` | `mentionedGroups` | `mentionedGroups=all` | Only messages that @mention a group (e.g., `all`) |
| `messages` | `hasFiles` | `hasFiles=true` | Only messages with file attachments |
| `messages` | `hasAttachments` | `hasAttachments=true` | Only messages with adaptive card attachments |
| `memberships` | `roomId` | `roomId=Y2lz...` | Only membership changes in a specific space |
| `memberships` | `personId` | `personId=Y2lz...` | Only membership changes for a specific person |
| `memberships` | `personEmail` | `personEmail=user@example.com` | Only membership changes for a specific email |
| `memberships` | `isModerator` | `isModerator=true` | Only moderator status changes |

**Example: Create a webhook for incoming calls only:**
```python
api.webhook.create(
    name="Incoming Calls Only",
    target_url="https://example.com/incoming",
    resource=WebhookResource.telephony_calls,
    event=WebhookEventType.all,
    filter="personality=terminator"
)
```

---

## 6. Webhook Setup: Step-by-Step

### Register for Telephony Call Events

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.webhook import WebhookResource, WebhookEventType

api = WebexSimpleApi(tokens=tokens)

# 1. Clean up old webhooks (optional)
existing = list(api.webhook.list())
for wh in existing:
    if wh.name == "My Call Monitor":
        api.webhook.webhook_delete(webhook_id=wh.webhook_id)

# 2. Create webhook for all telephony call events
webhook = api.webhook.create(
    name="My Call Monitor",
    target_url="https://your-server.com/webhooks/calls",
    resource=WebhookResource.telephony_calls,
    event=WebhookEventType.all,
    secret="your-hmac-secret"
)

print(f"Webhook created: {webhook.webhook_id}")
print(f"Status: {webhook.status}")
```

### Parse Incoming Events

```python
from wxc_sdk.webhook import WebhookEvent
from wxc_sdk.telephony.calls import TelephonyEventData

# In your webhook handler (e.g., Flask route)
def handle_webhook(request_json: dict):
    event = WebhookEvent.model_validate(request_json)

    # The data field is auto-parsed to TelephonyEventData
    # for telephony_calls resource
    data: TelephonyEventData = event.data

    print(f"Event type: {data.event_type}")
    print(f"Call ID: {data.call_id}")
    print(f"State: {data.state}")
    print(f"Personality: {data.personality}")
    print(f"Remote party: {data.remote_party.name} ({data.remote_party.number})")

    if data.event_type == "disconnected":
        print(f"Call ended at: {data.disconnected}")
    elif data.event_type == "answered":
        print(f"Call answered at: {data.answered}")
```

### Firehose Webhook (All Events)

The firehose pattern creates a webhook for all resources and all events. Useful for logging or debugging.

```python
# Create firehose
api.webhook.create(
    name="Firehose",
    resource=WebhookResource.all,    # resource='all'
    event=WebhookEventType.all,      # event='all'
    target_url="https://your-server.com/firehose"
)
```

The SDK's `firehose.py` example demonstrates a complete Flask-based firehose listener that:
1. Uses ngrok for a public URL
2. Cleans up old webhooks matching the class name
3. Creates a firehose webhook (`resource='all'`, `event='all'`)
4. Routes events to resource-specific handlers
5. Auto-parses `WebhookEvent` from the POST body, which dispatches to the correct `WebhookEventData` subclass based on the resource (e.g., `TelephonyEventData` for `telephony_calls`)

---

### 6b. Bot Webhook Pattern

This section covers the standard webhook interaction loop for bots. For webhook CRUD commands, see Sections 1 and 6 above.

#### Message Handling Loop

How a bot "hears" and responds to messages:

**Step 1 — Create a webhook for incoming messages:**
```bash
wxcli webhooks create \
  --name "Bot Messages" \
  --target-url https://your-bot.example.com/webhook \
  --resource messages \
  --event created
```

**Step 2-5 — The interaction loop (at runtime):**

1. User sends a message to a space where the bot is a member (or @mentions the bot)
2. Webex fires a POST to your `targetUrl` with message metadata — **no message text** (bot security restriction)
3. Bot extracts `data.id` from the webhook payload and fetches the message:
   ```bash
   wxcli messages show MESSAGE_ID
   ```
4. Bot processes the message text and sends a response:
   ```bash
   wxcli messages create --room-id ROOM_ID --text "Response text here"
   ```

**Key rule:** Never assume the webhook payload contains the message text. Always fetch via `wxcli messages show MESSAGE_ID`. See Section 4b for the complete list of fields available in the payload.

#### Card Interaction Loop

How a bot sends adaptive cards and captures user responses:

**Step 1 — Create a webhook for card submissions:**
```bash
wxcli webhooks create \
  --name "Bot Card Responses" \
  --target-url https://your-bot.example.com/webhook \
  --resource attachmentActions \
  --event created
```

**Step 2-5 — The card interaction loop (at runtime):**

1. Bot sends a message containing an adaptive card:
   ```bash
   wxcli messages create --json-body '{
     "roomId": "ROOM_ID",
     "text": "Approval request (fallback)",
     "attachments": [{
       "contentType": "application/vnd.microsoft.card.adaptive",
       "content": { ... card payload ... }
     }]
   }'
   ```
2. User clicks `Action.Submit` in the rendered card
3. Webex fires a POST to your `targetUrl` with action metadata — `inputs` (the user's form values) are NOT in the payload
4. Bot extracts `data.id` from the payload and fetches the action:
   ```bash
   wxcli attachment-actions show ACTION_ID
   ```
5. Bot reads the `inputs` object from the response and sends a follow-up:
   ```bash
   wxcli messages create --room-id ROOM_ID --text "Got your response: Approved"
   ```

#### Typical Bot Webhook Setup (both loops)

Most interactive bots need both webhooks:

```bash
# 1. Subscribe to incoming messages
wxcli webhooks create \
  --name "Bot Messages" \
  --target-url https://your-bot.example.com/webhook \
  --resource messages \
  --event created

# 2. Subscribe to card responses
wxcli webhooks create \
  --name "Bot Card Responses" \
  --target-url https://your-bot.example.com/webhook \
  --resource attachmentActions \
  --event created

# 3. Verify both are active
wxcli webhooks list --output json
```

Add `--filter "roomId=ROOM_ID"` to either webhook to scope it to a specific space.

---

## 7. Webhook Event Data Class Hierarchy

The SDK uses a registration pattern to auto-parse event data:

```
WebhookEventDataForbid (base, with registry)
  └── WebhookEventData (allows extra fields)
        └── TelephonyEventData (resource = 'telephony_calls')
              ├── inherits: WebhookEventData (metadata fields)
              └── inherits: TelephonyCall (call detail fields)
```

**SDK class definition:**
```python
class TelephonyEventData(WebhookEventData, TelephonyCall):
    """data in a webhook 'telephony_calls' event"""
    resource = 'telephony_calls'
    event_type: str
    event_timestamp: datetime.datetime
```

When `WebhookEvent.model_validate(payload)` processes the JSON, it checks `data.resource` against the registry and automatically instantiates the correct subclass. For `telephony_calls`, the `data` field becomes a `TelephonyEventData` instance with all `TelephonyCall` fields plus `event_type` and `event_timestamp`.

---

## 8. Webhook Security: HMAC Signature Verification

When you provide a `secret` during webhook creation, Webex signs each event payload. The signature is sent in the `X-Spark-Signature` HTTP header as an HMAC-SHA1 hex digest.

**Verification example:**
```python
import hmac
import hashlib

def verify_webhook_signature(request_body: bytes, signature: str, secret: str) -> bool:
    """Verify the X-Spark-Signature header."""
    expected = hmac.new(
        secret.encode('utf-8'),
        request_body,
        hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

<!-- Partial verification 2026-03-19: Webhook creation with secret confirmed via live API (secret is echoed back in the response). X-Spark-Signature with HMAC-SHA1 is the established pattern from Webex developer documentation and community resources but cannot be confirmed from SDK/OpenAPI source code alone. Full confirmation requires receiving a signed webhook delivery and inspecting the header. -->

---

## 9. Key Gotchas

1. **Auto-deactivation** -- Webhooks that fail to receive events (target URL returns errors repeatedly) are automatically set to `inactive`. Use the `update` API to reactivate by setting `status: active`.

2. **Cannot deactivate via API** -- You can only reactivate an auto-deactivated webhook. To stop receiving events, you must `delete` the webhook.

3. **Read scope required for creation** -- Creating a `telephony_calls` webhook requires `spark:calls_read` scope, not write scope.

4. **`event` field vs `data.eventType`** -- The top-level `event` field is the generic webhook event type (`created`, `updated`, `deleted`). The telephony-specific event type is in `data.eventType` (`alerting`, `answered`, `connected`, `held`, `remoteHeld`, `resumed`, `recording`, `disconnected`, `forwarded`).

5. **`callId` aliasing** -- In webhook event data, the call identifier field is `callId`. In direct API responses, it is `id`. The SDK's `TelephonyCall` model handles both via the `call_id` property.

6. **Firehose scope** -- A firehose webhook (`resource=all`, `event=all`) requires broad scopes. You will only receive events for resources your token has read access to.

7. **Updatable fields** -- Only `name`, `targetUrl`, `secret`, and `status` can be updated on an existing webhook. You cannot change the `resource`, `event`, or `filter` after creation. Delete and recreate instead.

8. **Webhook URL must be HTTPS** -- The `targetUrl` must be publicly accessible over HTTPS. For local development, use ngrok or a similar tunnel (as shown in the firehose example).

9. **Event delivery is not guaranteed to be ordered** -- Events may arrive out of order. Use `data.eventTimestamp` and `data.callSessionId` to correlate and order events for the same call session.

10. **One webhook per resource/event combo** -- Creating a duplicate webhook (same resource + event + filter) will create a second webhook, resulting in duplicate event delivery. Always clean up old webhooks before creating new ones.

---

## See Also

- **[call-control.md](call-control.md)** — Call control actions and the `TelephonyCall` data model. `TelephonyEventData` inherits from `TelephonyCall`, so the `remoteParty`, `state`, `personality`, and other call fields documented there apply directly to webhook event data.
- **[authentication.md](authentication.md)** — Scope definitions and OAuth token management. Creating a `telephony_calls` webhook requires `spark:calls_read` scope; a firehose requires `spark:all`.
