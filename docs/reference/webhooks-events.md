# Webhooks & Telephony Events Reference

Webex webhooks deliver real-time notifications to your application when resources change. This document covers webhook CRUD operations and the `telephony_calls` resource events specific to Webex Calling.

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark:calls_read` | Required to create a webhook for `telephony_calls` resource (user-level) |
| `spark:all` | Firehose webhook (resource=`all`, event=`all`) |

Creating a webhook requires **read** scope on the resource the webhook is for. For telephony call events, that means `spark:calls_read`.

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
| `updated` | `resumed`, `recording` | A call state changed (resumed from hold, recording state changed) |
| `deleted` | `disconnected`, `forwarded` | A call ended or was forwarded away |

<!-- NEEDS VERIFICATION: The exact mapping of webhook event types (created/updated/deleted) to telephony eventType values may include additional eventType values not listed here. The Webex developer docs should be consulted for the complete list. -->

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
| `eventType` | str | Telephony event type: `answered`, `disconnected`, `forwarded`, `resumed`, `recording` |
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

<!-- NEEDS VERIFICATION: The exact filter field names and supported combinations for telephony_calls may differ from the above. Consult the Webex developer docs filtering guide for the definitive list. -->

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

<!-- NEEDS VERIFICATION: Confirm the exact HMAC algorithm (SHA1 vs SHA256) and header name used for webhook signature verification. The above is based on established Webex webhook documentation patterns. -->

---

## 9. Key Gotchas

1. **Auto-deactivation** -- Webhooks that fail to receive events (target URL returns errors repeatedly) are automatically set to `inactive`. Use the `update` API to reactivate by setting `status: active`.

2. **Cannot deactivate via API** -- You can only reactivate an auto-deactivated webhook. To stop receiving events, you must `delete` the webhook.

3. **Read scope required for creation** -- Creating a `telephony_calls` webhook requires `spark:calls_read` scope, not write scope.

4. **`event` field vs `data.eventType`** -- The top-level `event` field is the generic webhook event type (`created`, `updated`, `deleted`). The telephony-specific event type is in `data.eventType` (`answered`, `disconnected`, `forwarded`, `resumed`, `recording`).

5. **`callId` aliasing** -- In webhook event data, the call identifier field is `callId`. In direct API responses, it is `id`. The SDK's `TelephonyCall` model handles both via the `call_id` property.

6. **Firehose scope** -- A firehose webhook (`resource=all`, `event=all`) requires broad scopes. You will only receive events for resources your token has read access to.

7. **Updatable fields** -- Only `name`, `targetUrl`, `secret`, and `status` can be updated on an existing webhook. You cannot change the `resource`, `event`, or `filter` after creation. Delete and recreate instead.

8. **Webhook URL must be HTTPS** -- The `targetUrl` must be publicly accessible over HTTPS. For local development, use ngrok or a similar tunnel (as shown in the firehose example).

9. **Event delivery is not guaranteed to be ordered** -- Events may arrive out of order. Use `data.eventTimestamp` and `data.callSessionId` to correlate and order events for the same call session.

10. **One webhook per resource/event combo** -- Creating a duplicate webhook (same resource + event + filter) will create a second webhook, resulting in duplicate event delivery. Always clean up old webhooks before creating new ones.
