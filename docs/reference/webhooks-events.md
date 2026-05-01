<!-- Updated by playbook session 2026-05-01 -->
# Webhooks & Telephony Events Reference

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: specs/webex-cloud-calling.json
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
10. [Org-Level Webhooks](#10-org-level-webhooks)
11. [Webhook Delivery Mechanics](#11-webhook-delivery-mechanics)
12. [Service App Webhooks](#12-service-app-webhooks)
13. [callSessionId Correlation Pattern](#13-callsessionid-correlation-pattern)
14. [Scale Patterns](#14-scale-patterns)
15. [wxcli Command Reference](#15-wxcli-command-reference)

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

| Resource Value | Description | Supports `ownedBy: org`? |
|----------------|-------------|:------------------------:|
| `telephony_calls` | Webex Calling call events | Yes (verified 2026-05-01, not in OpenAPI spec — see §10) |
| `telephony_conference` | Webex Calling conference controls | No |
| `telephony_mwi` | Voicemail message waiting indicator | No |
| `messages` | Messaging (chat) | Yes |
| `memberships` | Room/space memberships | No |
| `rooms` | Rooms/spaces | Yes |
| `meetings` | Meetings | Yes |
| `recordings` | Meeting recordings | Yes |
| `convergedRecordings` | Converged (call) recordings | Yes |
| `meetingParticipants` | Meeting participants | Yes |
| `meetingTranscripts` | Meeting transcripts | Yes |
| `uc_counters` | Unified Communications counters | No |
| `attachmentActions` | Attachment/card actions | No |
| `dataSources` | Data sources | No |
| `serviceApp` | Service app authorization events | No |
| `adminBatchJobs` | Admin batch jobs | Yes |
| `all` | Firehose: all resources | No |

### Event Types (All Available)

The `event` field on webhook creation determines which lifecycle events trigger delivery. Different resources use different event types.

| Event Value | Description | Used By |
|-------------|-------------|---------|
| `created` | Resource was created | telephony_calls, messages, memberships, rooms, attachmentActions |
| `updated` | Resource was modified | telephony_calls, messages, memberships, rooms |
| `deleted` | Resource was removed | telephony_calls, messages, memberships |
| `started` | Resource started | meetings |
| `ended` | Resource ended | meetings |
| `joined` | Participant joined | meetingParticipants |
| `left` | Participant left | meetingParticipants |
| `migrated` | Resource was migrated | meetings |
| `authorized` | App was authorized | serviceApp |
| `deauthorized` | App was deauthorized | serviceApp |
| `statusChanged` | Status changed | adminBatchJobs |
| `all` | Subscribe to all event types for the resource | All resources |

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

#### messages Resource

| Webhook `event` | When It Fires |
|-----------------|---------------|
| `created` | A message was posted to a space |
| `updated` | A message was edited |
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

| Filter | Example | Description |
|--------|---------|-------------|
| `personality` | `personality=terminator` | Only incoming calls |
| `personality` | `personality=originator` | Only outgoing calls |
| `state` | `state=connected` | Only connected state events |
| `callType` | `callType=external` | Only external calls |
| `personId` | `personId=Y2lzY29z...` | Only events for a specific person |
| `address` | `address=+15551234567` | Only events for a specific phone number or SIP address |

**Available filters for messaging resources:**

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

11. **Org-level `telephony_calls` works but is missing from OpenAPI spec** -- The `ownedBy: org` parameter's description in the OpenAPI spec lists supported resources but does NOT include `telephony_calls`. Live testing (2026-05-01) confirmed it works — the API returns 201 with `status: active`. The spec has a documentation gap, not a feature gap.

12. **Service App `application:webhooks_*` scopes not supported** -- Service Apps cannot use `application:webhooks_write` or `application:webhooks_read` scopes. They create webhooks using standard resource read scopes (e.g., `spark:calls_read`). See §12.

13. **Event storm at scale** -- An org-level webhook for 35,000+ users can generate 70,000+ events/hour at peak. If your receiver slows down under load, the auto-deactivation threshold (gotcha #1) may trigger, silently stopping all event delivery. Monitor webhook status and build receiver capacity well above peak estimates.

14. **Org-level + creator-level overlap** -- If you have both an org-level webhook and a creator-level webhook for the same resource, the creator's events are delivered to BOTH webhooks. This is usually a mistake — use `wxcli webhooks list` and `wxcli webhooks list --owned-by org` to audit for overlaps.

15. **`ownedBy` is immutable after creation** -- The `update` endpoint accepts `ownedBy` in the CLI schema, but the OpenAPI spec does not list it as an updatable field. Like `resource`, `event`, and `filter`, ownership is fixed at creation time. Delete and recreate to change.

16. **Missing event types for non-telephony resources** -- The `event` enum includes `started`, `ended`, `joined`, `left`, `migrated`, `authorized`, `deauthorized`, and `statusChanged` in addition to the common `created`/`updated`/`deleted`. These apply to meetings, meetingParticipants, serviceApp, and adminBatchJobs respectively. See the Event Types table in §3.

---

## 10. Org-Level Webhooks

### Creator-Level vs Org-Level

By default, webhooks are **creator-level** (`ownedBy: creator`): they receive events only for the authenticated user who created them. An **org-level** webhook (`ownedBy: org`) receives events for all users in the organization.

| Aspect | Creator-Level (default) | Org-Level (`ownedBy: org`) |
|--------|------------------------|---------------------------|
| Event scope | Events for the creating user only | Events for ALL users in the org |
| Who can create | Any user with read scope on the resource | Admin or Service App with admin-level scopes |
| Typical token | User OAuth (PAT or integration) | Admin OAuth or Service App token |
| Use case | Per-user notifications, bot messages | Org-wide monitoring, compliance, middleware |

### Scope Requirements for Org-Level Webhooks

Creating an org-level webhook requires **admin-level scopes** on the target resource. For example:
- `spark-admin:telephony_config_read` or `spark:calls_read` with an admin token for `telephony_calls`
- `spark-admin:rooms_read` for `rooms`
- `spark-admin:messages_read` for `messages`

The scope requirements are the same read scopes, but the token must belong to an admin (full admin or read-only admin) or a Service App with admin authorization.

### Supported Resources

The OpenAPI spec explicitly lists org-level support for: `meetings`, `recordings`, `convergedRecordings`, `meetingParticipants`, `meetingTranscripts`, `videoMeshAlerts`, `controlHubAlerts`, `rooms`, `messaging`, and `adminBatchJobs`.

> **`telephony_calls` is NOT in this list, but it works.** The OpenAPI spec does not list `telephony_calls` as supporting `ownedBy: org`. However, live API testing (2026-05-01) confirmed that creating an org-level `telephony_calls` webhook succeeds with HTTP 201 and `status: active`. The spec has a documentation gap — the API supports it.
>
> **Verified with:**
> ```bash
> wxcli webhooks create \
>   --name "Org Telephony Test" \
>   --target-url https://example.com/test \
>   --resource telephony_calls \
>   --event all \
>   --owned-by org -o json
> # Result: 201, ownedBy: "org", status: "active"
> ```

### Behavior Details

**Multiple org-level webhooks:** You can create multiple org-level webhooks for the same resource/event. Each receives a copy of every event, resulting in duplicate delivery. This is usually a mistake — clean up duplicates via `wxcli webhooks list --owned-by org`.

**Interaction with `filter`:** Org-level and `filter` combine as AND logic. An org-level webhook with `filter=personality=terminator` receives events for all users in the org, but only for incoming calls. This is the recommended pattern for large-scale deployments — subscribe to all org events, filter server-side.

**Deprovisioning the creator:** When the user or Service App that created an org-level webhook is deprovisioned or deauthorized, the webhook's behavior is undocumented. **Requires live verification:**

```bash
# 1. Create org-level webhook with Service App token
wxcli webhooks create --name "Test" --target-url https://example.com/test \
  --resource messages --event created --owned-by org

# 2. Revoke the Service App authorization in Control Hub
# 3. Check if the webhook still exists and delivers events:
wxcli webhooks list --owned-by org
```

### Raw HTTP: Create Org-Level Webhook

```python
body = {
    "name": "Org Call Events",
    "targetUrl": "https://middleware.example.com/webhooks",
    "resource": "telephony_calls",
    "event": "all",
    "ownedBy": "org",
    "filter": "personality=terminator",
    "secret": "hmac-secret-here"
}
result = api.session.rest_post(f"{BASE}/webhooks", json=body)
```

---

## 11. Webhook Delivery Mechanics

Webex delivers events as HTTP POST requests to your `targetUrl`. Understanding the delivery contract is critical for building reliable receivers.

### Delivery Contract

| Aspect | Behavior | Source |
|--------|----------|--------|
| Transport | HTTPS POST to `targetUrl` | Spec: `targetUrl` must be HTTPS |
| Payload format | JSON (`Content-Type: application/json`) | Observed |
| Signature header | `X-Spark-Signature` (HMAC-SHA1 hex digest) if `secret` is set | Spec + SDK |
| Batching | Events are delivered **individually** (one POST per event) | Observed — no batch envelope in spec |

### Timeout and Response Codes

The Webex platform expects your server to respond quickly. The exact timeout is not documented in the OpenAPI spec.

| Aspect | Documented Behavior |
|--------|-------------------|
| Expected response | 2xx status code (any 200-299) |
| Response body | Ignored — Webex only checks the status code |
| Timeout | **Requires live verification.** Developer community reports suggest ~15 seconds, but this is not in the spec. |

**Test command to measure timeout:**
```python
# Deploy a webhook handler that sleeps increasing durations
# and log which deliveries Webex considers failed.
import time
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    time.sleep(20)  # Adjust to find the cutoff
    return '', 200
```

### Retry Policy

The retry behavior on delivery failure is **not documented** in the OpenAPI spec. Observable behavior:

| Aspect | Observed Behavior |
|--------|-------------------|
| Retry on 5xx | **Requires live verification.** No retry policy is documented. |
| Retry on timeout | **Requires live verification.** |
| Retry on connection refused | **Requires live verification.** |
| Backoff strategy | **Requires live verification.** |

**What IS documented:** After sustained delivery failures, the webhook is auto-deactivated (see below). The absence of documented retries suggests events may be dropped on first failure — design receivers accordingly.

### Auto-Deactivation

Webhooks that fail to receive events are automatically set to `inactive` status.

| Aspect | Behavior |
|--------|----------|
| Trigger | Repeated delivery failures to `targetUrl` |
| Failure threshold | **Not documented.** Developer community suggests ~100 consecutive failures, but this is not in the spec. |
| Time window | **Not documented.** |
| Notification | No notification — poll `wxcli webhooks list` or check `status` field |
| Reactivation | `wxcli webhooks update WEBHOOK_ID --status active` |
| Cannot deactivate via API | You cannot set `status` to `inactive` — only delete the webhook to stop delivery |

**Test command to find the threshold:**
```bash
# 1. Create a webhook pointing at a non-existent URL
wxcli webhooks create --name "Deactivation Test" \
  --target-url https://nonexistent.example.com/webhook \
  --resource messages --event created

# 2. Generate events (send messages)
# 3. Poll until status changes:
wxcli webhooks show WEBHOOK_ID
```

### Event Ordering

**Events are NOT guaranteed to arrive in order.** This is critical for telephony event processing.

For a single call, you might receive events in this order:
```
answered (timestamp: T+0s)
connected (timestamp: T+1s)    ← may arrive before or after "answered"
held (timestamp: T+30s)
resumed (timestamp: T+35s)
disconnected (timestamp: T+60s)
```

**Ordering rules:**
- Events from different calls have no ordering relationship
- Events from the same call (`callSessionId`) may arrive out of order
- Use `data.eventTimestamp` as the authoritative ordering field
- Use `data.callSessionId` to group events belonging to the same call session
- See §13 for a worked correlation example

### Duplicate Delivery

Events may be delivered more than once under these conditions:
1. **Multiple webhooks** for the same resource/event/filter → each receives the event (gotcha #10)
2. **Org-level + creator-level overlap** → user events delivered to both
3. **Infrastructure retries** (if any) → possible duplicate on timeout edge cases

Design receivers to be **idempotent**. Key on `data.callId` + `data.eventType` (or message `data.id` + `event`) for deduplication.

---

## 12. Service App Webhooks

### Can a Service App Create Webhooks?

**Yes, with caveats.** A Service App uses a machine-to-machine OAuth token with scopes authorized by an org admin. If the authorized scopes include read access to the target resource, the Service App can create webhooks.

However, the OpenAPI spec explicitly states that **`application:webhooks_write` and `application:webhooks_read` scopes are NOT supported** for Service Apps (see [authentication.md](authentication.md)). Service Apps create webhooks using the standard resource read scopes, not webhook-specific scopes.

### Required Scopes

| Resource | Scope Needed | Notes |
|----------|-------------|-------|
| `telephony_calls` | `spark:calls_read` or `spark-admin:telephony_config_read` | Admin must authorize these on the Service App |
| `messages` | `spark:messages_read` or `spark-admin:messages_read` | |
| `meetings` | `spark:meetings_read` or `spark-admin:meetings_read` | |
| Any resource | Read scope for that resource | Service App must be authorized for it |

### Org-Level Behavior

A webhook created by a Service App does **not** automatically become org-level. You must explicitly set `ownedBy: org` on creation, same as with user tokens. A Service App token with admin-level scopes can create org-level webhooks for supported resources (see §10 for the supported resource list).

### Token Refresh and Webhook Lifecycle

Service App access tokens expire after **14 days**. Refresh tokens expire after **90 days** of non-use.

| Scenario | Webhook Impact |
|----------|---------------|
| Access token expires, refresh succeeds | **No impact** — webhook continues to deliver events. The webhook is not tied to the token; it's tied to the authorization. |
| Refresh token expires (90 days unused) | **Requires live verification.** The webhook may continue delivering (it's server-side), but you lose the ability to manage it until the Service App is re-authorized. |
| Service App deauthorized by admin | **Requires live verification.** Webhooks created by the app may be auto-deleted or orphaned. Test before relying on this in production. |

**Test commands:**
```bash
# Verify Service App can create webhooks
wxcli webhooks create --name "SA Test" \
  --target-url https://example.com/webhook \
  --resource telephony_calls --event all

# Check the webhook's createdBy and appId fields
wxcli webhooks show WEBHOOK_ID -o json
```

### Cross-Reference

See [admin-apps-data.md](admin-apps-data.md) §1 for Service App registration, authorization, and token management.

---

## 13. callSessionId Correlation Pattern

When processing telephony webhook events, you need to correlate multiple events that belong to the same call. The key fields are:

| Field | Scope | Purpose |
|-------|-------|---------|
| `callSessionId` | Spans the entire call session (including transfers) | Group all events for one end-to-end call |
| `callId` | Unique per call leg | Identify a specific leg (e.g., before vs after transfer) |
| `actorPersonId` | The Webex user whose perspective this event represents | Route events to the correct handler |
| `personality` | `originator` or `terminator` | Distinguish outbound vs inbound perspective |

### Worked Example: Inbound Call with Hold

A customer calls a store associate. The associate answers, places the call on hold to check inventory, resumes, then hangs up.

**Event sequence (6 events, one `callSessionId`):**

```
Event 1: created/alerting
  callSessionId: "session-ABC"
  callId: "call-123"
  actorPersonId: "associate-001"
  personality: "terminator"
  state: "alerting"
  eventTimestamp: "2026-05-01T14:00:01.000Z"
  remoteParty: { number: "+15551234567", callType: "external" }

Event 2: created/answered
  callSessionId: "session-ABC"
  callId: "call-123"
  actorPersonId: "associate-001"
  personality: "terminator"
  state: "connected"
  eventTimestamp: "2026-05-01T14:00:05.000Z"

Event 3: updated/connected
  callSessionId: "session-ABC"
  callId: "call-123"
  actorPersonId: "associate-001"
  personality: "terminator"
  state: "connected"
  eventTimestamp: "2026-05-01T14:00:05.500Z"

Event 4: updated/held
  callSessionId: "session-ABC"
  callId: "call-123"
  actorPersonId: "associate-001"
  personality: "terminator"
  state: "held"
  eventTimestamp: "2026-05-01T14:00:35.000Z"

Event 5: updated/resumed
  callSessionId: "session-ABC"
  callId: "call-123"
  actorPersonId: "associate-001"
  personality: "terminator"
  state: "connected"
  eventTimestamp: "2026-05-01T14:01:05.000Z"

Event 6: deleted/disconnected
  callSessionId: "session-ABC"
  callId: "call-123"
  actorPersonId: "associate-001"
  personality: "terminator"
  state: "disconnected"
  eventTimestamp: "2026-05-01T14:02:30.000Z"
  disconnected: "2026-05-01T14:02:30.000Z"
```

### Correlation Rules

1. **Group by `callSessionId`** to track one call end-to-end. A transfer creates new `callId` values but keeps the same `callSessionId`.
2. **Key timers and state on `callId`**, not `callSessionId`. A transferred call has multiple legs — each leg has its own hold/resume cycle.
3. **Use `actorPersonId`** to route events to the correct user context (e.g., map to a store register).
4. **Use `personality`** to distinguish the user's role: `terminator` = they received the call, `originator` = they placed it.
5. **Use `eventTimestamp`** for ordering, not arrival order. Events can arrive out of sequence (see §11).

### Middleware State Machine

For a hold-timeout middleware (e.g., the AAP retail pattern), the state machine keyed on `callId`:

```
                  answered
     ┌──────────────────────────────┐
     │                              ▼
  [IDLE] ──alerting──▶ [RINGING] ──▶ [ACTIVE]
                                      │    ▲
                                 held │    │ resumed
                                      ▼    │
                                   [ON_HOLD]
                                      │
                              timer fires (60s)
                                      │
                                      ▼
                               [HANGUP_PENDING]
                                      │
                              disconnected (any state)
                                      │
                                      ▼
                                   [IDLE]
```

**Key design decisions:**
- Key the state map on `callId` (not `callSessionId`) — each leg is independent
- Store state in Redis with TTL (e.g., 120s) — auto-cleanup if `disconnected` is lost
- Handle out-of-order: if `resumed` arrives while hangup API call is in flight, the hangup fails safely (call is no longer held)
- Handle duplicate: check current state before acting — if already in `[IDLE]`, ignore the event

### Race Condition Handling

| Race Condition | Resolution |
|----------------|------------|
| `resumed` arrives after timer fires but before hangup completes | Hangup API returns error (call not held) — safe to ignore |
| `disconnected` arrives before `held` | State transitions to IDLE; late `held` ignored (call already gone) |
| Duplicate `held` events | Timer already running — ignore duplicate |
| `connected` arrives before `answered` | Both transition to ACTIVE — idempotent |

---

## 14. Scale Patterns

### One Org-Level Webhook vs Many Filtered Webhooks

| Approach | Pros | Cons |
|----------|------|------|
| **One org-level webhook** (`ownedBy: org`, `event: all`) | Single subscription, simple management, no per-user provisioning | High event volume, receiver must filter/route, org-level may not be supported for all resources (see §10) |
| **Per-user filtered webhooks** (`filter: personId=X`) | Low noise per endpoint, precise routing | O(n) webhook management, provisioning/deprovisioning overhead, webhook count limits |
| **Org-level + server-side filter** | Best of both — one subscription, filter in middleware | Receiver must handle full org volume |

**Recommendation for 1,000+ users:** One org-level webhook with server-side filtering. Per-user webhooks don't scale — you'd need to create/delete webhooks as users are provisioned/deprovisioned, and there may be undocumented limits on total webhook count per org.

### Volume Estimation

Estimate event volume for capacity planning:

```
Events/hour = concurrent_calls × events_per_call × calls_per_hour_per_line

Example (4,500-store retail chain, 35,000 phones):
  Peak concurrent utilization: 10% = 3,500 active calls
  Events per call: ~6 (alerting, answered, connected, [held, resumed], disconnected)
  Call duration: ~3 minutes average
  Calls per hour per active line: ~20

  Peak burst: 3,500 × 6 = 21,000 events in a burst window
  Sustained: ~70,000 events/hour at peak
```

### Stateless Receiver Architecture

For high-volume webhook processing, use stateless HTTP receivers behind a load balancer:

```
Webex Platform
     │
     │ HTTPS POST (one per event)
     ▼
┌─────────────┐
│ Load Balancer│
│ (ALB / CLB) │
└──────┬──────┘
       │
  ┌────┼────┐
  ▼    ▼    ▼
┌───┐┌───┐┌───┐
│ W ││ W ││ W │   Stateless workers
│ 1 ││ 2 ││ 3 │   (Lambda / Cloud Run / K8s pods)
└─┬─┘└─┬─┘└─┬─┘
  │    │    │
  └────┼────┘
       ▼
┌─────────────┐
│ Redis Cluster│   Timer state, dedup, call-to-register mapping
└─────────────┘
```

**Design principles:**
- Workers are stateless — any worker can handle any event
- Shared state (timers, call tracking) lives in Redis with TTLs
- HMAC verification at the worker level (each worker has the secret)
- Return 200 immediately, process asynchronously if heavy work is needed
- No persistent connections to Webex — webhooks are push-only

### Timer State Management (Redis Pattern)

For hold-timeout tracking at scale:

```python
import redis
import json

r = redis.Redis()

def on_held(call_id: str, actor_person_id: str):
    """Start a 60-second hold timer."""
    key = f"hold:{call_id}"
    r.setex(key, 120, json.dumps({  # TTL 120s (2× timer for safety)
        "actor": actor_person_id,
        "held_at": time.time()
    }))
    # Enqueue a delayed job to check at T+60s
    # (use Redis Streams, SQS delay, or scheduled task)

def on_resumed(call_id: str):
    """Cancel the hold timer."""
    r.delete(f"hold:{call_id}")

def on_timer_fire(call_id: str):
    """Timer expired — check if still held, then act."""
    key = f"hold:{call_id}"
    data = r.get(key)
    if not data:
        return  # Already resumed or disconnected
    r.delete(key)
    # Execute hangup via Service App Members API
```

### Why Not XSI for Large-Scale Event Routing

XSI (Extended Services Interface) provides real-time call event streaming but has architectural constraints that make webhooks the better choice at scale:

| Factor | XSI | Webhooks |
|--------|-----|----------|
| Connection model | Persistent streaming (one channel per XSP) | Stateless HTTP POST (push) |
| Scaling model | Single-process Python (GIL-bound) | Horizontally scaled workers |
| Org-wide subscription | Single connection for entire org | Single webhook registration |
| Failure recovery | 60-second gap on channel failure, events lost | Individual event delivery, auto-deactivation on sustained failure |
| Duplicate subscriptions | Duplicate org-wide subscriptions cause duplicate events | Same (multiple webhooks = duplicate delivery) |
| Queue bottleneck | `queue.Queue(maxsize=500)` in-process | External (Redis, SQS, etc.) |
| Deployment | Requires long-running process with DNS SRV discovery | Serverless-compatible (Lambda, Cloud Run) |

**Bottom line:** XSI is designed for single-site monitoring dashboards (wallboards, supervisor consoles). Webhooks are designed for distributed, horizontally-scaled event processing. For 1,000+ users, use webhooks.

See [wxcadm-xsi-realtime.md](wxcadm-xsi-realtime.md) for XSI architecture details and the event streaming API.

---

## 15. wxcli Command Reference

All webhook management is via the `wxcli webhooks` command group.

### webhooks list

```bash
wxcli webhooks list [OPTIONS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--owned-by` | str | (none) | Filter to org-wide webhooks only (value: `org`) |
| `--output`, `-o` | str | `table` | Output format: `table` or `json` |
| `--limit` | int | `0` | Max results (0 = all) |
| `--offset` | int | `0` | Pagination offset |
| `--debug` | flag | | Enable debug output |

```bash
# List all webhooks in table format
wxcli webhooks list

# List org-level webhooks as JSON
wxcli webhooks list --owned-by org -o json

# List first 10 webhooks
wxcli webhooks list --limit 10
```

### webhooks create

```bash
wxcli webhooks create [OPTIONS]
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | str | Yes | User-friendly name |
| `--target-url` | str | Yes | HTTPS URL that receives POST requests |
| `--resource` | str | Yes | Resource type (e.g., `telephony_calls`, `messages`) |
| `--event` | str | Yes | Event type (e.g., `all`, `created`, `updated`, `deleted`) |
| `--filter` | str | No | Filter expression (e.g., `personality=terminator`) |
| `--secret` | str | No | HMAC secret for payload signature verification |
| `--owned-by` | str | No | Set to `org` for org-level webhook |
| `--json-body` | str | No | Full JSON request body (overrides all other options) |
| `--output`, `-o` | str | `id` | Output format: `id` (just the webhook ID) or `json` (full response) |
| `--debug` | flag | | Enable debug output |

```bash
# Create a telephony webhook with HMAC secret
wxcli webhooks create \
  --name "Call Events" \
  --target-url https://middleware.example.com/webhooks \
  --resource telephony_calls \
  --event all \
  --secret "my-hmac-secret"

# Create an org-level filtered webhook, output full JSON
wxcli webhooks create \
  --name "Org Incoming Calls" \
  --target-url https://middleware.example.com/webhooks \
  --resource telephony_calls \
  --event all \
  --owned-by org \
  --filter "personality=terminator" \
  -o json

# Create via JSON body
wxcli webhooks create --json-body '{
  "name": "Custom Webhook",
  "targetUrl": "https://example.com/hook",
  "resource": "messages",
  "event": "created",
  "filter": "roomId=Y2lz..."
}'
```

### webhooks show

```bash
wxcli webhooks show WEBHOOK_ID [OPTIONS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output`, `-o` | str | `json` | Output format: `table` or `json` |
| `--debug` | flag | | Enable debug output |

```bash
# Show webhook details as JSON
wxcli webhooks show "Y2lzY29zcGFyazov..."

# Show as table
wxcli webhooks show "Y2lzY29zcGFyazov..." -o table
```

### webhooks update

```bash
wxcli webhooks update WEBHOOK_ID [OPTIONS]
```

| Flag | Type | Description |
|------|------|-------------|
| `--name` | str | New name |
| `--target-url` | str | New target URL |
| `--secret` | str | New HMAC secret |
| `--owned-by` | str | Ownership (present in CLI but immutable after creation — see gotcha #7) |
| `--status` | str | Set to `active` to reactivate an auto-deactivated webhook |
| `--json-body` | str | Full JSON request body (overrides all other options) |
| `--debug` | flag | Enable debug output |

```bash
# Reactivate an auto-deactivated webhook
wxcli webhooks update "Y2lzY29zcGFyazov..." --status active

# Change target URL and secret
wxcli webhooks update "Y2lzY29zcGFyazov..." \
  --target-url https://new-server.example.com/webhooks \
  --secret "new-hmac-secret"
```

### webhooks delete

```bash
wxcli webhooks delete WEBHOOK_ID [OPTIONS]
```

| Flag | Type | Description |
|------|------|-------------|
| `--force` | flag | Skip confirmation prompt |
| `--debug` | flag | Enable debug output |

```bash
# Delete with confirmation prompt
wxcli webhooks delete "Y2lzY29zcGFyazov..."

# Delete without confirmation
wxcli webhooks delete "Y2lzY29zcGFyazov..." --force
```

---

## See Also

- **[call-control.md](call-control.md)** — Call control actions and the `TelephonyCall` data model. `TelephonyEventData` inherits from `TelephonyCall`, so the `remoteParty`, `state`, `personality`, and other call fields documented there apply directly to webhook event data.
- **[authentication.md](authentication.md)** — Scope definitions and OAuth token management. Creating a `telephony_calls` webhook requires `spark:calls_read` scope; a firehose requires `spark:all`.
- **[admin-apps-data.md](admin-apps-data.md)** — Service App registration, authorization, and token lifecycle. Cross-reference §12 for Service App webhook creation.
- **[wxcadm-xsi-realtime.md](wxcadm-xsi-realtime.md)** — XSI event streaming architecture. Cross-reference §14 for why webhooks scale better than XSI for large deployments.
