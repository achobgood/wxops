---
name: call-control
description: |
  Real-time Webex Calling call control, telephony webhook/event monitoring, and conference controls.
  Covers the Call Control API (user-level and Service App), telephony webhook subscriptions and
  event parsing, and conference controls for real-time call monitoring and programmatic call control.
  NOT for: messaging webhooks/bot events (use messaging-bots skill), call settings/forwarding
  configuration (use manage-call-settings skill), or CDR/call history queries (use reporting skill).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [call-control | webhooks | conference]
---

<!-- Created 2026-03-19 -->

# Call Control & Real-time Events Workflow

> **CRITICAL WARNING: USER-LEVEL OAUTH TOKEN REQUIRED**
>
> The Call Control API (`/v1/telephony/calls/*`) requires a **user-level OAuth token** with `spark:calls_read` / `spark:calls_write` scopes. Admin tokens get **400 "Target user not authorized"**. This is the #1 gotcha.
>
> **Service Apps** (with `spark-admin:calls_read` / `spark-admin:calls_write`) must use the **Members API** (`/v1/telephony/calls/members/{memberId}/*`) instead of the user-level endpoints.
>
> `wxcli call-controls` commands use user-level endpoints by default. Do NOT use them with admin/service-app tokens.

---

**Checkpoint — do NOT proceed until you can answer these:**
1. What token type does the Call Control API require, and what error do admin tokens get? (Answer: User-level OAuth with `spark:calls_read`/`spark:calls_write`. Admin tokens get 400 "Target user not authorized".)
2. What API path must Service Apps use instead of user-level endpoints? (Answer: Members API — `/v1/telephony/calls/members/{memberId}/*` with `spark-admin:calls_read`/`spark-admin:calls_write`.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

Load the reference docs needed for the requested operation. Load both if the user hasn't specified which approach they need yet; otherwise load only the relevant one(s).

| Reference doc | When to load |
|---------------|-------------|
| `docs/reference/call-control.md` | Call Control API operations, conference controls |
| `docs/reference/webhooks-events.md` | Webhook setup, telephony event subscriptions |

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags. Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

---

## Step 2: Verify authentication

Before any call control or webhook operations, confirm the user has a working token:

```bash
wxcli whoami
```

If this fails, resolve authentication first (`wxcli configure`).

### Scope verification

After confirming a valid token, verify the token has the scopes required for the user's intended approach:

| Approach | Required Scopes | Token Type |
|----------|----------------|------------|
| **Call Control (user)** | `spark:calls_read`, `spark:calls_write` | User-level OAuth (Integration flow) |
| **Call Control (Service App)** | `spark-admin:calls_read`, `spark-admin:calls_write` | Service App token |
| **Webhooks** | `spark:calls_read` (to create telephony_calls webhook) | User-level OAuth |
| **WebRTC Calling** | `spark:webrtc_calling` | User-level OAuth |
| **Firehose webhook** | `spark:all` | User-level OAuth |

**Scope-checking logic:**

1. Run `wxcli whoami` — confirm the token is valid and note whether it is a user token, admin token, or Service App token.
2. Match the token type against the table above:
   - If **user-level token** → proceed with user-level Call Control or Webhooks.
   - If **Service App token** → MUST use Members API endpoints (`/calls/members/{memberId}/*`). Standard call-control commands will fail with 400.
   - If **admin token only** → call control will fail. Advise the user to obtain a user-level token or use a Service App with the correct scopes.
3. If scope is unclear, warn the user: *"Call Control requires a user-level token with `spark:calls_read` + `spark:calls_write`. Admin tokens get 400 'Target user not authorized'."*
4. The 12-hour developer token from developer.webex.com works for testing if it was generated with the correct scopes.

---

## Step 3: Identify the operation

Present this decision matrix if the user is unsure which approach fits their need:

| Need | Approach | Tool |
|------|----------|------|
| Control calls from an external app (click-to-dial, hold, transfer) | **Call Control API** | `wxcli call-controls` or raw HTTP via `WebexSession` |
| Control calls on behalf of users (admin/service app) | **Members API** | `wxcli call-controls create-dial-members`, `create-answer-members`, etc. |
| Get notified when calls start/end/change state (push model) | **Webhooks** | `wxcli webhooks` or raw HTTP |
| Multi-party conference management | **Conference Controls** | `wxcli conference` |
| Poll for active calls or call history | **Call Control API (GET)** | `wxcli call-controls list` / `list-history` |

**Key distinctions:**
- **Call Control API** = REST API on `api.webex.com`, requires user token, works for 3rd-party call control apps
- **Webhooks** = push notifications to your HTTPS endpoint when call events occur
- **Conference Controls** = separate API for multi-party conference management

---

## Step 4: Check prerequisites

Based on the approach identified in Step 3, verify the prerequisites below.

### 4a. Call Control prerequisites

- Token is **user-level** with `spark:calls_read` + `spark:calls_write` (verified in Step 2).
- For Service App usage, token has `spark-admin:calls_read` + `spark-admin:calls_write` and you will use the Members API.
- The target user has a **Webex Calling license** assigned. Users without a calling license return 404 (error 4008).
- Confirm CLI access: `wxcli call-controls --help`

### 4b. Webhook prerequisites

- Token has `spark:calls_read` scope.
- The webhook target URL is **publicly accessible over HTTPS**. For local development, use ngrok or a similar tunnel.
- No duplicate webhooks exist for the same resource/event combo (duplicates cause duplicate event delivery). Check with: `wxcli webhooks list -o json`

---

## Step 5: Build and present deployment plan [SHOW BEFORE EXECUTING]

Before executing any call control, webhook, or conference operations, present the deployment plan to the user for approval. Include:

1. **Approach selected** — which approach from Step 3 (Call Control, Webhooks, Conference)
2. **Token type confirmed** — user-level, Service App, or admin (from Step 2)
3. **Operations to perform** — list of specific commands/API calls that will be executed
4. **Prerequisites verified** — confirm all Step 4 checks passed
5. **Risks or warnings** — any relevant Critical Rules that apply (e.g., "webhook auto-deactivation if target URL is unreachable", "recording start/stop requires On Demand mode")

Example plan format:

```
## Call Control Deployment Plan

**Approach:** Call Control API (user-level)
**Token:** User OAuth (verified via wxcli whoami)

### Operations
1. Initiate click-to-dial to +12223334444
2. Monitor call state via list-active
3. Transfer to +15551234567 when connected

### Prerequisites
- [x] User-level token with spark:calls_read + spark:calls_write
- [x] Target user has Webex Calling license
- [x] wxcli call-controls accessible

### Warnings
- Transfer requires the call to be answered first (unanswered = use divert instead)
```

Wait for user approval before proceeding to Step 6.

---

## Step 6: Execute via wxcli

### 6a. Call control operations

#### Call state machine

Understanding the call state machine is essential for correct call control:

```
                 ┌──────────────┐
     dial ──────>│  connecting  │
                 └──────┬───────┘
                        │ remote rings
                        v
  incoming ────>┌──────────────┐
                │   alerting   │──── reject ────> disconnected
                └──────┬───────┘
                       │ answer
                       v
                ┌──────────────┐
          ┌────>│  connected   │──── hangup ────> disconnected
          │     └──┬────┬──────┘
          │        │    │
   resume │   hold │    │ remote hold
          │        v    v
          │  ┌──────┐  ┌────────────┐
          └──│ held  │  │ remoteHeld │
             └──────┘  └────────────┘
```

**CallState values:** `connecting`, `alerting`, `connected`, `held`, `remoteHeld`, `disconnected`

**Personality values:** `originator` (outgoing), `terminator` (incoming), `clickToDial` (alerting for click-to-dial, becomes `originator` on answer)

#### Core call operations via wxcli

##### Initiate a call (click-to-dial)

```bash
wxcli call-controls create --destination "+12223334444"
```

Optional: `--endpoint-id DEVICE_ID` to target a specific device.

##### Answer an incoming call

```bash
wxcli call-controls create-answer-calls --call-id CALL_ID
```

##### Hold and resume

```bash
wxcli call-controls create-hold --call-id CALL_ID
wxcli call-controls create-resume --call-id CALL_ID
```

##### Transfer

Three transfer modes:

| Mode | CLI flags | Description |
|------|-----------|-------------|
| Auto (2 calls) | (no call IDs) | User has exactly 2 calls, auto-selected |
| Consultative | `--call-id1 X --call-id2 Y` | Transfer two specific calls together |
| Mute transfer | `--call-id1 X --destination NUM` | Transfer to new destination, waits for answer |

```bash
# Consultative transfer
wxcli call-controls create-transfer --call-id1 CALL_ID_1 --call-id2 CALL_ID_2

# Mute transfer to a number
wxcli call-controls create-transfer --call-id1 CALL_ID --destination "+15551234567"
```

**Important:** Unanswered incoming calls cannot be transferred. Use `create-divert` instead.

##### Park and retrieve

```bash
# Park a call (returns the park extension)
wxcli call-controls create-park --call-id CALL_ID

# Retrieve a parked call
wxcli call-controls create-retrieve --destination PARK_EXTENSION
```

##### Recording control

```bash
wxcli call-controls create-start-recording --call-id CALL_ID
wxcli call-controls create-stop-recording --call-id CALL_ID
wxcli call-controls create-pause-recording --call-id CALL_ID
wxcli call-controls create-resume-recording --call-id CALL_ID
```

Recording mode determines which actions are available:
- **On Demand**: start, stop, pause, resume
- **Always with Pause/Resume**: pause, resume only
- **Always**: no manual control

##### Other actions

```bash
# Reject incoming call
wxcli call-controls create-reject --call-id CALL_ID

# Hangup
wxcli call-controls create-hangup-calls --call-id CALL_ID

# Mute/unmute
wxcli call-controls create-mute --call-id CALL_ID
wxcli call-controls create-unmute --call-id CALL_ID

# Divert (blind transfer or send to voicemail)
wxcli call-controls create-divert --call-id CALL_ID --destination "+12223334444"
wxcli call-controls create-divert --call-id CALL_ID --to-voicemail

# Send DTMF tones
wxcli call-controls create-transmit-dtmf --call-id CALL_ID --dtmf "1,234"

# Pick up another user's ringing call
wxcli call-controls create-pickup --target "+12223334444"

# Pull call to another device
wxcli call-controls create-pull --endpoint-id DEVICE_ID

# Push call to executive (assistant only)
wxcli call-controls create-push --call-id CALL_ID

# Barge into another user's call
wxcli call-controls create-barge-in --target "+12223334444"
```

#### Query active calls and history

```bash
# List all active calls for the user
wxcli call-controls list -o json

# Get details of a specific call (--line-owner-id required for Service App tokens)
wxcli call-controls show CALL_ID -o json
wxcli call-controls show CALL_ID --line-owner-id USER_ID -o json

# List call history (max 20 per type, 60 total)
wxcli call-controls list-history -o json
```

#### Service App / Members API commands

For Service Apps that control calls on behalf of users:

```bash
# Dial on behalf of a member
wxcli call-controls create-dial-members MEMBER_ID --destination "+12223334444"

# Answer on behalf of a member
wxcli call-controls create-answer-members MEMBER_ID --call-id CALL_ID

# Hangup on behalf of a member
wxcli call-controls create-hangup-members MEMBER_ID --call-id CALL_ID

# List calls for a member
wxcli call-controls list-calls-members MEMBER_ID -o json

# Get call details for a member
wxcli call-controls show-calls-members MEMBER_ID CALL_ID -o json
```

### 6b. Webhook setup for telephony events

#### Creating a telephony call webhook

Webhooks deliver push notifications to your HTTPS endpoint when call events occur. The webhook target URL must be publicly accessible over HTTPS (use ngrok for local development).

##### Via wxcli (preferred)

```bash
# List existing webhooks to check for duplicates
wxcli webhooks list --output json

# Delete old webhook if it exists (avoid duplicate delivery)
wxcli webhooks delete WEBHOOK_ID

# Create webhook for all telephony call events
wxcli webhooks create \
  --name "My Call Monitor" \
  --target-url "https://your-server.com/webhooks/calls" \
  --resource "telephony_calls" \
  --event "all" \
  --secret "your-hmac-secret"

# Verify it was created
wxcli webhooks list --output json
```

##### Via raw HTTP (for programmatic HMAC verification or complex webhook management)

```python
from wxcli.auth import get_api

api = get_api()
BASE = "https://webexapis.com/v1/webhooks"

# Clean up old webhooks first (avoid duplicate delivery)
existing = list(api.session.follow_pagination(BASE))
for wh in existing:
    if wh["name"] == "My Call Monitor":
        api.session.rest_delete(f"{BASE}/{wh['id']}")

# Create webhook for all telephony call events
webhook = api.session.rest_post(BASE, json={
    "name": "My Call Monitor",
    "targetUrl": "https://your-server.com/webhooks/calls",
    "resource": "telephony_calls",
    "event": "all",
    "secret": "your-hmac-secret"
})
```

#### Webhook event types

The `event` field (top-level) maps to telephony-specific `data.eventType` values:

| Webhook `event` | `data.eventType` | When it fires |
|-----------------|-------------------|---------------|
| `created` | `alerting` | Call is ringing |
| `created` | `answered` | Call was answered |
| `updated` | `connected` | Call transitioned to connected |
| `updated` | `held` | User placed call on hold |
| `updated` | `remoteHeld` | Remote party placed call on hold |
| `updated` | `resumed` | Held call was resumed |
| `updated` | `recording` | Recording state changed |
| `deleted` | `disconnected` | Call ended |
| `deleted` | `forwarded` | Call was forwarded away |

#### Filtering webhooks

Narrow which events are delivered using the `filter` parameter:

```bash
# Incoming calls only (filter on personality=terminator)
wxcli webhooks create \
  --name "Incoming Calls" \
  --target-url "https://example.com/incoming" \
  --resource "telephony_calls" \
  --event "all" \
  --filter "personality=terminator"
```

Available filters: `personality`, `state`, `callType`, `personId`.

#### Parsing webhook event payloads

```python
def handle_webhook(request_json: dict):
    data = request_json["data"]

    print(f"Event: {data['eventType']}")
    print(f"Call ID: {data['callId']}")
    print(f"State: {data['state']}")
    print(f"Remote: {data['remoteParty']['name']} ({data['remoteParty']['number']})")
```

The webhook `data` object carries the full telephony call payload — `callId`, `state`, `personality`, `remoteParty`, and event-timing fields are all present on each event.

#### HMAC signature verification

When a `secret` is provided, verify the `X-Spark-Signature` header:

```python
import hmac, hashlib

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, signature)
```

#### Webhook management

```bash
# List all webhooks
wxcli webhooks list --output json

# Reactivate an auto-deactivated webhook
wxcli webhooks update WEBHOOK_ID --json-body '{"name": "Reactivated", "targetUrl": "https://...", "status": "active"}'

# Delete a webhook
wxcli webhooks delete WEBHOOK_ID
```

#### Other telephony webhook resources

| Resource | Description |
|----------|-------------|
| `telephony_calls` | Call events (alerting, connected, held, disconnected, etc.) |
| `telephony_conference` | Conference control events |
| `telephony_mwi` | Voicemail message waiting indicator |
| `convergedRecordings` | Call recording events |

### 6c. Conference control operations

#### CLI commands

```bash
wxcli conference --help
```

#### Available conference commands

| Command | Key Options | Description |
|---------|-------------|-------------|
| `wxcli conference list` | `--line-owner-id` | Get conference details |
| `wxcli conference create` | `--json-body` | Start a conference |
| `wxcli conference delete` | `--line-owner-id` | Release (end) a conference |
| `wxcli conference create-add-participant` | `--call-id` (required), `--line-owner-id` | Add a participant |
| `wxcli conference create-mute` | `--call-id` | Mute a participant |
| `wxcli conference create-unmute` | `--call-id` | Unmute a participant |
| `wxcli conference create-deafen` | `--call-id` (required) | Deafen a participant (can't hear) |
| `wxcli conference create-undeafen` | `--call-id` (required) | Undeafen a participant |
| `wxcli conference create-hold` | `--line-owner-id` | Hold the conference |
| `wxcli conference create-resume` | `--line-owner-id` | Resume the conference |

**Note:** Conference commands do NOT take a positional conference ID. Use `--line-owner-id` to specify whose conference to operate on (required for Service App tokens).

#### 3-way merge via Call Control API

The Call Control API also supports merging two active calls into a conference:

```bash
# Merge two calls (user must have one active, one held)
wxcli call-controls create-transfer --call-id1 CALL_ID_1 --call-id2 CALL_ID_2
```

Or via raw HTTP:

```python
from wxcli.auth import get_api
api = get_api()
api.session.rest_post("https://webexapis.com/v1/telephony/calls/conference",
    json={"callId1": call_id_1, "callId2": call_id_2})
```

---

## Step 7: Verification

### Verify call control is working

```bash
# List active calls (should return empty list if no calls)
wxcli call-controls list -o json

# Check call history (confirms API access)
wxcli call-controls list-history -o json
```

### Verify webhook is receiving events

```bash
# List webhooks and check status — look for status: "active"
wxcli webhooks list --output json
```

If a webhook shows `inactive`, it was auto-deactivated due to delivery failures. Fix the target URL and reactivate:

```bash
wxcli webhooks update WEBHOOK_ID --json-body '{"name": "My Call Monitor", "targetUrl": "https://fixed-url.com/webhooks", "status": "active"}'
```

---

## Step 8: Report results

Summarize the completed operations and their outcomes:

1. **What was configured** — which approach (Call Control, Webhooks, Conference) and what specific operations were performed
2. **Verification results** — confirmation that the configuration is working (API responses, webhook status)
3. **Active resources** — list any persistent resources created (webhooks, etc.) that the user should be aware of
4. **Next steps** — any follow-up actions the user may want to take (e.g., "webhook is active — test by placing a call")
5. **Cleanup reminders** — resources that should be cleaned up when no longer needed (e.g., "delete the webhook when done testing")

---

## Critical Rules

1. **User-level token required for call control.** Admin tokens get 400 "Target user not authorized". Service Apps must use the Members API (`/calls/members/{memberId}/*`). This is the most common failure.

2. **Webhook auto-deactivation.** Webhooks that fail to deliver events (target URL returns errors repeatedly) are automatically set to `inactive`. You must explicitly reactivate them via the update API. You cannot deactivate a webhook via API -- only delete it.

3. **Webhook resource/event/filter are immutable.** You cannot change these after creation. Delete and recreate instead. Only `name`, `targetUrl`, `secret`, and `status` can be updated.

4. **Webhook URL must be HTTPS.** For local development, use ngrok or a similar tunnel.

5. **`callId` vs `id` aliasing.** Call Control API responses use `id`; webhook events use `callId`. They identify the same call — normalize the two in your own event-handling code.

6. **Transfer restrictions.** Unanswered incoming calls cannot be transferred. Use `divert` (blind transfer / send to voicemail) for unanswered calls.

7. **Recording mode dependency.** `start/stop` only work with "On Demand" mode. `pause/resume` work with both "On Demand" and "Always with Pause/Resume". Check the user's recording configuration first.

8. **Call history limit.** `list-history` returns max 20 records per type (placed/missed/received), max 60 total.

9. **Conference via Call Control API requires two calls.** The user must have one active and one held call to merge. Use `hold` first, then `dial` the second party, then `conference`.

10. **Webhook event delivery is not guaranteed to be ordered.** Use `data.eventTimestamp` and `data.callSessionId` to correlate and order events.

11. **One webhook per resource/event combo.** Creating duplicates results in duplicate event delivery. Always clean up old webhooks before creating new ones.

---

## Scope Quick Reference

| Scope | Purpose |
|-------|---------|
| `spark:calls_read` | List calls, call details, call history, create telephony webhooks (user) |
| `spark:calls_write` | All call control actions: dial, answer, hold, transfer, park, record (user) |
| `spark-admin:calls_read` | List/get calls for any member (Service App) |
| `spark-admin:calls_write` | Call control actions for any member (Service App) |
| `spark:webrtc_calling` | WebRTC calling |
| `spark:all` | Firehose webhook (all resources, all events) |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Re-read `docs/reference/call-control.md` for call control API details
2. Re-read `docs/reference/webhooks-events.md` for webhook setup
3. Run `wxcli call-controls --help` and `wxcli conference --help` to rediscover CLI commands
4. Resume from the last completed step
