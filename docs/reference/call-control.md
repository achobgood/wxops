<!-- Updated by playbook session 2026-03-18 -->
# Call Control API Reference

Webex Calling Call Control APIs enable 3rd-party applications to manage calls on behalf of users. These are **3rd Party Call Control** APIs only, applicable to **Webex Calling Multi-Tenant users** (not UCM or Dedicated Instance users).

> **Base path:** `POST /v1/telephony/calls/{action}`
> **GET endpoints:** `GET /v1/telephony/calls` and `GET /v1/telephony/calls/{callId}`

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: webex-cloud-calling.json
- developer.webex.com Call Control APIs

## Table of Contents

1. [Required Scopes](#required-scopes)
2. [Raw HTTP Reference](#raw-http-reference-all-call-control-endpoints)
3. [CLI Examples](#cli-examples)
4. [Call Connection](#1-call-connection)
5. [Mid-Call Actions](#2-mid-call-actions)
6. [Call Details & History](#3-call-details--history)
7. [Data Models](#4-data-models)
8. [Service App / Admin API](#5-service-app--admin-api-call-controls-members)
9. [Additional API: External Voicemail MWI](#6-additional-api-external-voicemail-mwi)
10. [Common Use Cases](#7-common-use-cases)
11. [Key Gotchas](#8-key-gotchas)
12. [See Also](#see-also)

---

## Required Scopes

| Scope | Grants | Used By |
|-------|--------|---------|
| `spark:calls_read` | List calls, get call details, call history | User tokens (personal) |
| `spark:calls_write` | All call control actions (dial, answer, hold, transfer, etc.) | User tokens (personal) |
| `spark-admin:calls_read` | List calls, get call details for any member | Service App tokens (admin) |
| `spark-admin:calls_write` | All call control actions for any member | Service App tokens (admin) |

- **User-level APIs** (`CallsApi`) use `spark:calls_read` / `spark:calls_write` and operate on the authenticated user's calls.
- **Service App / Admin APIs** (`CallControlsMembersApi`) use `spark-admin:calls_read` / `spark-admin:calls_write` and operate on any person, workspace, or virtual line by `member_id`.

---

## Raw HTTP Reference (All Call Control Endpoints)

All call control endpoints use `https://webexapis.com/v1/telephony/calls/{action}`. Most are POST actions that take a JSON body. GET endpoints retrieve call state.

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"
```

### User-Level Call Actions

| Action | Method | URL | Body Fields |
|--------|--------|-----|-------------|
| Dial | POST | `{BASE}/telephony/calls/dial` | `destination` (required), `endpointId`, `lineOwnerId` |
| Answer | POST | `{BASE}/telephony/calls/answer` | `callId` (required), `endpointId`, `lineOwnerId` |
| Reject | POST | `{BASE}/telephony/calls/reject` | `callId` (required), `action`, `lineOwnerId` |
| Hangup | POST | `{BASE}/telephony/calls/hangup` | `callId` (required), `lineOwnerId` |
| Hold | POST | `{BASE}/telephony/calls/hold` | `callId` (required), `lineOwnerId` |
| Resume | POST | `{BASE}/telephony/calls/resume` | `callId` (required), `lineOwnerId` |
| Mute | POST | `{BASE}/telephony/calls/mute` | `callId` (required), `lineOwnerId` |
| Unmute | POST | `{BASE}/telephony/calls/unmute` | `callId` (required), `lineOwnerId` |
| Divert | POST | `{BASE}/telephony/calls/divert` | `callId` (required), `destination`, `toVoicemail`, `lineOwnerId` |
| Transfer | POST | `{BASE}/telephony/calls/transfer` | `callId1`, `callId2`, `destination`, `lineOwnerId` |
| Park | POST | `{BASE}/telephony/calls/park` | `callId` (required), `destination`, `isGroupPark`, `lineOwnerId` |
| Retrieve | POST | `{BASE}/telephony/calls/retrieve` | `destination`, `endpointId`, `lineOwnerId` |
| Pull | POST | `{BASE}/telephony/calls/pull` | `endpointId`, `lineOwnerId` |
| Push | POST | `{BASE}/telephony/calls/push` | `callId`, `lineOwnerId` |
| Pickup | POST | `{BASE}/telephony/calls/pickup` | `target`, `endpointId`, `lineOwnerId` |
| Barge In | POST | `{BASE}/telephony/calls/bargeIn` | `target` (required), `endpointId`, `lineOwnerId` |
| Conference | POST | `{BASE}/telephony/calls/conference` | `callId1`, `callId2`, `lineOwnerId` |
| Start Recording | POST | `{BASE}/telephony/calls/startRecording` | `callId` (required), `lineOwnerId` |
| Stop Recording | POST | `{BASE}/telephony/calls/stopRecording` | `callId` (required), `lineOwnerId` |
| Pause Recording | POST | `{BASE}/telephony/calls/pauseRecording` | `callId` (required), `lineOwnerId` |
| Resume Recording | POST | `{BASE}/telephony/calls/resumeRecording` | `callId` (required), `lineOwnerId` |
| Transmit DTMF | POST | `{BASE}/telephony/calls/transmitDtmf` | `callId` (required), `dtmf` (required), `lineOwnerId` |

### User-Level Read Endpoints

| Action | Method | URL | Query Params | Response Key |
|--------|--------|-----|-------------|--------------|
| List Calls | GET | `{BASE}/telephony/calls` | `lineOwnerId` | `calls` |
| Get Call Details | GET | `{BASE}/telephony/calls/{callId}` | `lineOwnerId` | (direct object) |
| List Call History | GET | `{BASE}/telephony/calls/history` | `type` | `history` |

### Service App / Members Endpoints

| Action | Method | URL | Body Fields |
|--------|--------|-----|-------------|
| Dial by Member | POST | `{BASE}/telephony/calls/members/{memberId}/dial` | `destination`, `endpointId` |
| Answer by Member | POST | `{BASE}/telephony/calls/members/{memberId}/answer` | `callId`, `endpointId` |
| Hangup by Member | POST | `{BASE}/telephony/calls/members/{memberId}/hangup` | `callId` |
| List Calls by Member | GET | `{BASE}/telephony/calls/members/{memberId}/calls` | (none) |
| Get Call Details by Member | GET | `{BASE}/telephony/calls/members/{memberId}/calls/{callId}` | (none) |

### Raw HTTP Examples

#### Dial a call

```python
body = {"destination": "+12223334444", "endpointId": "Y2lzY29zcGFyay..."}
result = api.session.rest_post(f"{BASE}/telephony/calls/dial", json=body)
# Returns: {callId, callSessionId}
```

#### List active calls

```python
result = api.session.rest_get(f"{BASE}/telephony/calls")
calls = result.get("calls", [])
# Each call: {id, callSessionId, personality, state, remoteParty: {name, number, ...}, created, answered, ...}
```

#### Get call details

```python
result = api.session.rest_get(f"{BASE}/telephony/calls/{call_id}")
# Returns full call object with state, remoteParty, timestamps, etc.
```

#### List call history

```python
result = api.session.rest_get(f"{BASE}/telephony/calls/history", params={"type": "placed"})
history = result.get("history", [])
# Each record: {type, name, number, privacyEnabled, time}
```

#### Hold, then transfer

```python
# Put caller on hold
api.session.rest_post(f"{BASE}/telephony/calls/hold", json={"callId": caller_call_id})

# Dial consult target
consult = api.session.rest_post(f"{BASE}/telephony/calls/dial", json={"destination": "+15551234567"})

# Transfer both calls together
api.session.rest_post(f"{BASE}/telephony/calls/transfer", json={
    "callId1": caller_call_id,
    "callId2": consult["callId"]
})
```

#### Park and retrieve

```python
# Park
parked = api.session.rest_post(f"{BASE}/telephony/calls/park", json={"callId": call_id})
park_number = parked.get("parkedAgainst", {}).get("number")

# Retrieve (from any device)
retrieved = api.session.rest_post(f"{BASE}/telephony/calls/retrieve", json={"destination": park_number})
```

#### Service App: Dial on behalf of a member

```python
body = {"destination": "+12223334444"}
result = api.session.rest_post(f"{BASE}/telephony/calls/members/{member_id}/dial", json=body)
# Returns: {callId, callSessionId}
```

#### External Voicemail MWI

```python
body = {"action": "SET"}  # or "CLEAR"
api.session.rest_post(f"{BASE}/telephony/externalVoicemail/mwi", json=body, params={
    "id": user_id,
    "orgId": org_id
})
```

### Raw HTTP Gotchas

1. **All action endpoints are POST** -- even hold, resume, mute, unmute. Only list/details/history are GET.
2. **Response varies by action** -- `dial`, `pickup`, `retrieve`, `pull`, `bargeIn` return `{callId, callSessionId}`. Most others return 204 (no content).
3. **Transfer response depends on mode** -- auto/consultative returns 204; mute transfer returns 201 with `{callId, callSessionId}`.
4. **`id` vs `callId`** -- GET responses return `id` as the call identifier. Webhook events use `callId`. When passing to action endpoints, always use `callId` in the request body.
5. **`lineOwnerId`** is optional on all endpoints -- only needed when controlling a secondary line belonging to another user/workspace/virtual line.
6. **Members API does not have `lineOwnerId`** -- the member_id in the URL serves the same purpose.
7. **No pagination on call list** -- `list_calls` returns all active calls for the user (typically a small number).
8. **History max 20 per type** -- `list_call_history` returns at most 20 records per type (placed/missed/received), max 60 total.

---

## CLI Examples

> **Important:** Call control commands require a **user-level OAuth token**, not an admin token. Admin tokens return 400 "Target user not authorized". Configure wxcli with a user's personal access token: `wxcli configure`.

### Command Reference

All 29 commands in the `call-controls` group:

| Command | Description | Key Options |
|---------|-------------|-------------|
| `create` | Dial | `--destination` (required), `--endpoint-id`, `--line-owner-id` |
| `create-answer-calls` | Answer | `--call-id` (required), `--endpoint-id`, `--line-owner-id` |
| `create-reject` | Reject | `--call-id` (required), `--action`, `--line-owner-id` |
| `create-hangup-calls` | Hangup | `--call-id` (required), `--line-owner-id` |
| `create-hold` | Hold | `--call-id` (required), `--line-owner-id` |
| `create-resume` | Resume | `--call-id` (required), `--line-owner-id` |
| `create-mute` | Mute | `--call-id` (required), `--line-owner-id` |
| `create-unmute` | Unmute | `--call-id` (required), `--line-owner-id` |
| `create-divert` | Divert | `--call-id` (required), `--destination`, `--to-voicemail`, `--line-owner-id` |
| `create-transfer` | Transfer | `--call-id1`, `--call-id2`, `--destination`, `--line-owner-id` |
| `create-park` | Park | `--call-id` (required), `--destination`, `--is-group-park`, `--line-owner-id` |
| `create-retrieve` | Retrieve | `--destination`, `--endpoint-id`, `--line-owner-id` |
| `create-pull` | Pull | `--endpoint-id`, `--line-owner-id` |
| `create-push` | Push | `--call-id`, `--line-owner-id` |
| `create-pickup` | Pickup | `--target`, `--endpoint-id`, `--line-owner-id` |
| `create-barge-in` | Barge In | `--target` (required), `--endpoint-id`, `--line-owner-id` |
| `create-start-recording` | Start Recording | `--call-id`, `--line-owner-id` |
| `create-stop-recording` | Stop Recording | `--call-id`, `--line-owner-id` |
| `create-pause-recording` | Pause Recording | `--call-id`, `--line-owner-id` |
| `create-resume-recording` | Resume Recording | `--call-id`, `--line-owner-id` |
| `create-transmit-dtmf` | Transmit DTMF | `--call-id`, `--dtmf`, `--line-owner-id` |
| `list` | List Calls | `--line-owner-id`, `-o table\|json` |
| `show` | Get Call Details | `CALL_ID` (positional, required), `--line-owner-id`, `-o table\|json` |
| `list-history` | List Call History | `--type placed\|missed\|received`, `-o table\|json` |
| `create-dial` | Dial by Member ID | `MEMBER_ID` (positional), `--destination` (required), `--endpoint-id` |
| `create-answer-members` | Answer by Member ID | `MEMBER_ID` (positional), `--call-id` (required), `--endpoint-id` |
| `create-hangup-members` | Hangup by Member ID | `MEMBER_ID` (positional), `--call-id` (required) |
| `list-calls` | List Calls by Member ID | `MEMBER_ID` (positional), `-o table\|json` |
| `show-calls` | Get Call Details by Member ID | `MEMBER_ID` `CALL_ID` (positional), `-o table\|json` |

### Call Connection

```bash
# Dial a number (rings all user devices, then places outbound call)
wxcli call-controls create --destination "+12223334444"

# Dial an extension
wxcli call-controls create --destination "1234"

# Dial on a specific device/app
wxcli call-controls create --destination "+12223334444" --endpoint-id Y2lzY29zcGFyay...

# Answer an incoming call
wxcli call-controls create-answer-calls --call-id Y2lzY29zcGFyay...

# Answer on a specific device
wxcli call-controls create-answer-calls --call-id Y2lzY29zcGFyay... --endpoint-id Y2lzY29zcGFyay...

# Reject an incoming call (defaults to busy)
wxcli call-controls create-reject --call-id Y2lzY29zcGFyay...

# Reject with a specific action (busy, temporarilyUnavailable, ignore)
wxcli call-controls create-reject --call-id Y2lzY29zcGFyay... --action temporarilyUnavailable

# Hang up a call
wxcli call-controls create-hangup-calls --call-id Y2lzY29zcGFyay...

# Pick up a call from your call pickup group
wxcli call-controls create-pickup

# Pick up a call from a specific user
wxcli call-controls create-pickup --target "+12223334444"

# Divert a call to another number
wxcli call-controls create-divert --call-id Y2lzY29zcGFyay... --destination "+15551234567"

# Divert a call to voicemail
wxcli call-controls create-divert --call-id Y2lzY29zcGFyay... --to-voicemail
```

### Mid-Call Actions

```bash
# Hold a call
wxcli call-controls create-hold --call-id Y2lzY29zcGFyay...

# Resume a held call
wxcli call-controls create-resume --call-id Y2lzY29zcGFyay...

# Mute a call
wxcli call-controls create-mute --call-id Y2lzY29zcGFyay...

# Unmute a call
wxcli call-controls create-unmute --call-id Y2lzY29zcGFyay...
```

### Transfer

```bash
# Auto transfer (user has exactly 2 calls -- they are merged automatically)
wxcli call-controls create-transfer

# Consultative/attended transfer (specify both call IDs)
wxcli call-controls create-transfer --call-id1 Y2lzY29zcGFyay_call1... --call-id2 Y2lzY29zcGFyay_call2...

# Mute transfer (transfer to a new destination; waits for answer)
wxcli call-controls create-transfer --call-id1 Y2lzY29zcGFyay... --destination "+15551234567"
```

### Park / Retrieve

```bash
# Park a call (parks against self; returns the park extension number)
wxcli call-controls create-park --call-id Y2lzY29zcGFyay...

# Park a call at a specific extension
wxcli call-controls create-park --call-id Y2lzY29zcGFyay... --destination "7001"

# Park using the call park group (auto-selects an available slot)
wxcli call-controls create-park --call-id Y2lzY29zcGFyay... --is-group-park

# Retrieve a parked call (use the park number from the park response)
wxcli call-controls create-retrieve --destination "7001"
```

### Recording Control

```bash
# Start recording (user must have "On Demand" recording mode)
wxcli call-controls create-start-recording --call-id Y2lzY29zcGFyay...

# Pause recording (e.g., for sensitive info like credit card numbers)
wxcli call-controls create-pause-recording --call-id Y2lzY29zcGFyay...

# Resume recording
wxcli call-controls create-resume-recording --call-id Y2lzY29zcGFyay...

# Stop recording
wxcli call-controls create-stop-recording --call-id Y2lzY29zcGFyay...
```

### Other Actions

```bash
# Transmit DTMF tones (comma = pause between digits)
wxcli call-controls create-transmit-dtmf --call-id Y2lzY29zcGFyay... --dtmf "1,234"

# Pull a call to a different device (move call between desk phone, mobile, desktop)
wxcli call-controls create-pull --endpoint-id Y2lzY29zcGFyay...

# Push a call to the executive (executive-assistant feature only)
wxcli call-controls create-push --call-id Y2lzY29zcGFyay...

# Barge in on another user's active call
wxcli call-controls create-barge-in --target "+12223334444"
```

### Call Details & History

```bash
# List all active calls
wxcli call-controls list
wxcli call-controls list -o json

# Get details for a specific active call
wxcli call-controls show Y2lzY29zcGFyay...
wxcli call-controls show Y2lzY29zcGFyay... -o table

# List call history (all types -- placed, missed, received; max 20 each)
wxcli call-controls list-history

# List only missed calls
wxcli call-controls list-history --type missed

# List only placed calls as JSON
wxcli call-controls list-history --type placed -o json
```

### Service App / Members API

> These commands use `spark-admin:calls_read` / `spark-admin:calls_write` scopes and operate on behalf of a person, workspace, or virtual line by member ID.

```bash
# Dial on behalf of a user (Service App token required)
wxcli call-controls create-dial <member_id> --destination "+12223334444"

# Answer a call on behalf of a user
wxcli call-controls create-answer-members <member_id> --call-id Y2lzY29zcGFyay...

# Hang up a call on behalf of a user
wxcli call-controls create-hangup-members <member_id> --call-id Y2lzY29zcGFyay...

# List active calls for a user
wxcli call-controls list-calls <member_id>

# Get call details for a specific call on a user
wxcli call-controls show-calls <member_id> Y2lzY29zcGFyay...
```

### Hold, Consult, Transfer Pattern (CLI Workflow)

A common call center pattern: put the caller on hold, dial a consult target, then transfer both calls together.

```bash
# Step 1: Put the current call on hold
wxcli call-controls create-hold --call-id <caller_call_id>

# Step 2: Dial the transfer target
wxcli call-controls create --destination "+15551234567"
# Note the new call_id from the response

# Step 3: After speaking with the transfer target, transfer both calls
wxcli call-controls create-transfer --call-id1 <caller_call_id> --call-id2 <consult_call_id>
```

---

## 1. Call Connection

### Dial (Click-to-Call)

Initiate an outbound call. Alerts all user devices (or a specific endpoint). When the user answers on one device, the outbound call is placed from that device to the destination.

```
POST /v1/telephony/calls/dial
```

**SDK Signature:**
```python
CallsApi.dial(
    destination: str,           # digits, URI, SIP address, tel: URI
    endpoint_id: str = None,    # specific device/app to alert
    line_owner_id: str = None   # secondary line owner (user/workspace/virtual line)
) -> CallInfo
```

**Request body:**
```json
{
  "destination": "+12223334444",
  "endpointId": "Y2lzY29zcGFyay..."
}
```

**Response (201):**
```json
{
  "callId": "Y2lzY29zcGFyay...",
  "callSessionId": "OGQ3YzhkNzgt..."
}
```

**Destination formats:** `1234`, `2223334444`, `+12223334444`, `*73`, `tel:+12223334444`, `user@company.domain`, `sip:user@company.domain`

---

### Answer

Answer an incoming call on a specific device (or the user's primary device if no endpoint specified).

```
POST /v1/telephony/calls/answer
```

**SDK Signature:**
```python
CallsApi.answer(
    call_id: str,
    endpoint_id: str = None,
    line_owner_id: str = None
) -> None
```

**Request body:**
```json
{
  "callId": "Y2lzY29zcGFyay...",
  "endpointId": "Y2lzY29zcGFyay..."
}
```

**Notes:**
- Rejected if the device is not alerting for the call.
- Rejected if the device does not support answer via API.

---

### Pickup

Pick up an incoming call ringing on another user's device. Initiates a new call (similar to dial) to perform the pickup.

```
POST /v1/telephony/calls/pickup
```

**SDK Signature:**
```python
CallsApi.pickup(
    target: str = None,         # user to pick up from; omit for call pickup group
    endpoint_id: str = None,
    line_owner_id: str = None
) -> CallInfo
```

- **No target:** picks up from the user's call pickup group.
- **With target:** picks up from the specified user (digits or URI).

**Response:** Returns `CallInfo` (callId + callSessionId).

---

### Reject

Reject an unanswered incoming call.

```
POST /v1/telephony/calls/reject
```

**SDK Signature:**
```python
CallsApi.reject(
    call_id: str,
    action: RejectAction = None,    # defaults to 'busy' if omitted
    line_owner_id: str = None
) -> None
```

**RejectAction values:**

| Value | Behavior |
|-------|----------|
| `busy` | Send the call to busy (default) |
| `temporarilyUnavailable` | Send the call to temporarily unavailable |
| `ignore` | Continue ringback to caller, stop alerting user's devices |

---

### Divert (Blind Transfer)

Divert a call to another destination or to voicemail.

```
POST /v1/telephony/calls/divert
```

**SDK Signature:**
```python
CallsApi.divert(
    call_id: str,
    destination: str = None,     # required if toVoicemail is false
    to_voicemail: bool = None,   # True = send to voicemail
    line_owner_id: str = None
) -> None
```

**Request body examples:**

Divert to another number:
```json
{
  "callId": "Y2lzY29zcGFyay...",
  "destination": "+12223334444"
}
```

Divert to own voicemail:
```json
{
  "callId": "Y2lzY29zcGFyay...",
  "toVoicemail": true
}
```

Divert to another user's voicemail:
```json
{
  "callId": "Y2lzY29zcGFyay...",
  "destination": "+12223334444",
  "toVoicemail": true
}
```

### Gotchas

- **Answer rejection:** Answer is rejected if the device is not alerting for the call, or if the device does not support answer via API.

---

## 2. Mid-Call Actions

### Hold

Place a connected call on hold.

```
POST /v1/telephony/calls/hold
```

**SDK Signature:**
```python
CallsApi.hold(call_id: str, line_owner_id: str = None) -> None
```

---

### Resume

Resume a held call.

```
POST /v1/telephony/calls/resume
```

**SDK Signature:**
```python
CallsApi.resume(call_id: str, line_owner_id: str = None) -> None
```

---

### Transfer

Transfer two calls together. Supports multiple transfer modes depending on parameters.

```
POST /v1/telephony/calls/transfer
```

**SDK Signature:**
```python
CallsApi.transfer(
    call_id1: str = None,
    call_id2: str = None,
    destination: str = None,
    line_owner_id: str = None
) -> CallInfo
```

**Transfer modes:**

| Mode | Parameters | Response | Description |
|------|-----------|----------|-------------|
| **Auto (2 calls)** | Neither callId1/callId2 | 204 | User has exactly 2 calls; they are automatically selected and transferred |
| **Consultative / Attended** | `callId1` + `callId2` | 204 | Transfer two specific calls together (supervised transfer) |
| **Mute Transfer** | `callId1` + `destination` | 201 | Transfer call to new destination; waits for destination to answer before completing. If destination doesn't answer, call is not transferred |

**Note:** Unanswered incoming calls cannot be transferred. Use `divert` instead.

---

### Park

Park a connected call. Returns the extension/number to use for retrieval.

```
POST /v1/telephony/calls/park
```

**SDK Signature:**
```python
CallsApi.park(
    call_id: str,
    destination: str = None,      # where to park; omit to park against self
    is_group_park: bool = None,   # True = auto-select from call park group
    line_owner_id: str = None
) -> TelephonyParty                # parkedAgainst details including number
```

**Response:** Returns a `TelephonyParty` object (the `parkedAgainst` party). The `number` field from this response is used as the destination for the `retrieve` command.

---

### Retrieve (Unpark)

Retrieve a parked call. Initiates a new call (similar to dial) to perform the retrieval.

```
POST /v1/telephony/calls/retrieve
```

**SDK Signature:**
```python
CallsApi.retrieve(
    destination: str = None,    # where the call is parked; omit if parked against self
    endpoint_id: str = None,
    line_owner_id: str = None
) -> CallInfo
```

---

### Pull

Pull a call from one device to another. Useful for moving a call between desk phone, mobile app, and desktop app.

```
POST /v1/telephony/calls/pull
```

**SDK Signature:**
```python
CallsApi.pull(
    endpoint_id: str = None,
    line_owner_id: str = None
) -> CallInfo
```

A temporary new call is initiated. When the user answers on the target device, that device connects to the pulled call and the temporary call is released.

---

### Push (Executive Assistant)

Push a call from an assistant to the associated executive.

```
POST /v1/telephony/calls/push
```

**SDK Signature:**
```python
CallsApi.push(
    call_id: str = None,
    line_owner_id: str = None
) -> None
```

**Note:** Only valid when the assistant's call is associated with an executive.

---

### Barge In

Barge into another user's answered call. Initiates a new call (similar to dial).

```
POST /v1/telephony/calls/bargeIn
```

**SDK Signature:**
```python
CallsApi.barge_in(
    target: str,                # user to barge in on (digits or URI)
    endpoint_id: str = None,
    line_owner_id: str = None
) -> CallInfo
```

---

### Conference (3-Way Merge)

Merge two active calls into a three-way conference call. The user must have two calls (one active, one held) to merge.

```
POST /v1/telephony/calls/conference
```

**SDK Signature:**
```python
CallsApi.conference(
    call_id1: str = None,
    call_id2: str = None,
    line_owner_id: str = None
) -> None
```

If `call_id1` and `call_id2` are omitted, the user must have exactly two calls; they are automatically selected and merged. When specified, both calls are merged into a three-way conference with the user.

---

### Hangup

Disconnect a call. If used on an unanswered incoming call, the call is rejected and sent to busy.

```
POST /v1/telephony/calls/hangup
```

**SDK Signature:**
```python
CallsApi.hangup(call_id: str, line_owner_id: str = None) -> None
```

---

### Mute / Unmute

Mute or unmute a call. Only valid on calls that report `muteCapable: true` in call details.

```
POST /v1/telephony/calls/mute
POST /v1/telephony/calls/unmute
```

**SDK Signatures:**
```python
CallsApi.mute(call_id: str, line_owner_id: str = None) -> None
CallsApi.unmute(call_id: str, line_owner_id: str = None) -> None
```

---

### Recording Control

Control call recording. Availability depends on the user's call recording mode.

| Endpoint | SDK Method | Recording Mode Required |
|----------|-----------|------------------------|
| `POST .../startRecording` | `start_recording(call_id, line_owner_id)` | "On Demand" |
| `POST .../stopRecording` | `stop_recording(call_id, line_owner_id)` | "On Demand" |
| `POST .../pauseRecording` | `pause_recording(call_id, line_owner_id)` | "On Demand" or "Always with Pause/Resume" |
| `POST .../resumeRecording` | `resume_recording(call_id, line_owner_id)` | "On Demand" or "Always with Pause/Resume" |

**RecordingState values:**

| Value | Description |
|-------|-------------|
| `pending` | Recording requested but not yet started |
| `started` | Recording is active |
| `paused` | Recording is paused |
| `stopped` | Recording has been stopped |
| `failed` | Recording failed |

---

### Transmit DTMF

Send DTMF tones on an active call.

```
POST /v1/telephony/calls/transmitDtmf
```

**SDK Signature:**
```python
CallsApi.transmit_dtmf(
    call_id: str = None,
    dtmf: str = None,           # e.g. "1,234" (comma = pause)
    line_owner_id: str = None
) -> None
```

**Valid DTMF characters:** `0-9`, `*`, `#`, `A`, `B`, `C`, `D`
**Pause:** Use a comma `,` to insert a pause between digits. Example: `"1,234"` sends `1`, pauses, then sends `2`, `3`, `4`.

### Gotchas

- **Transfer restrictions:** Unanswered incoming calls cannot be transferred. Use `divert` instead.
- **Push is executive-assistant only:** `push` is only valid when the assistant's call is associated with an executive.
- **Mute capability check:** Only calls that report `muteCapable: true` in call details support `mute`/`unmute`. Always check before calling.
- **DTMF pause character:** Use a comma `,` to insert a pause between DTMF digits. This is not documented prominently in the API reference.
- **Recording mode dependency:** `start_recording`/`stop_recording` only work when the user's recording mode is "On Demand". `pause_recording`/`resume_recording` work with both "On Demand" and "Always with Pause/Resume".

---

## 3. Call Details & History

### List Active Calls

Get all active calls for the user.

```
GET /v1/telephony/calls
```

**SDK Signature:**
```python
CallsApi.list_calls(line_owner_id: str = None) -> list[TelephonyCall]
```

---

### Get Call Details

Get details of a specific active call.

```
GET /v1/telephony/calls/{callId}
```

**SDK Signature:**
```python
CallsApi.call_details(
    call_id: str,
    line_owner_id: str = None
) -> TelephonyCall
```

---

### List Call History

Get the user's call history. Returns a maximum of **20 records per type**.

```
GET /v1/telephony/calls/history
```

**SDK Signature:**
```python
CallsApi.call_history(history_type: HistoryType = None) -> list[CallHistoryRecord]
```

**HistoryType values:**

| Value | Description |
|-------|-------------|
| `placed` | Outgoing calls placed by the user |
| `missed` | Incoming calls not answered |
| `received` | Incoming calls answered |

If `history_type` is omitted, all types are returned (up to 20 each = max 60 total).

**CallHistoryRecord fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | HistoryType | placed, missed, or received |
| `name` | str (optional) | Party name (if available and privacy not enabled) |
| `number` | str (optional) | Party number (digits or URI) |
| `privacy_enabled` | bool | Whether privacy is enabled |
| `time` | datetime | When the record was created (placed=call time, missed=disconnect time, received=answer time) |

### Gotchas

- **Call history limit:** `call_history` returns a maximum of 20 records per type (placed/missed/received). If `history_type` is omitted, all types are returned (up to 20 each = max 60 total).
- **No pagination on call list:** `list_calls` returns all active calls for the user (typically a small number). There is no pagination support.

---

## 4. Data Models

### TelephonyCall (Call Object)

The primary call object returned by list/details endpoints and included in webhook event data.

| Field | Type | Description |
|-------|------|-------------|
| `call_id` | str | Unique call identifier (aliased from `id` in API responses, `callId` in events) |
| `call_session_id` | str | Session ID to correlate multiple calls in the same session |
| `personality` | Personality | Whether user is originator, terminator, or clickToDial |
| `state` | CallState | Current call state |
| `remote_party` | TelephonyParty | Details of the other party |
| `appearance` | int (optional) | Appearance value for ordering calls consistent with device display |
| `created` | datetime | When the call was created |
| `answered` | datetime (optional) | When the call was answered |
| `redirections` | list[Redirection] | Previous redirections (most recent first), only present when state is alerting |
| `recall` | Recall (optional) | Recall details (e.g., park recall) |
| `recording_state` | RecordingState (optional) | Current recording state, only present if recording was invoked |
| `disconnected` | datetime (optional) | When the call was disconnected |
| `mute_capable` | bool (optional) | Whether the call supports mute/unmute API |
| `muted` | bool (optional) | Whether the call is currently muted |

### CallInfo (Dial/Pickup/Retrieve Response)

Returned by actions that initiate a new call.

| Field | Type | Description |
|-------|------|-------------|
| `call_id` | str | Unique call identifier |
| `call_session_id` | str | Session ID for correlating related calls |

### Personality

| Value | Description |
|-------|-------------|
| `originator` | An outgoing call originated by the user |
| `terminator` | An incoming call received by the user |
| `clickToDial` | Alerting for a Click-to-Dial action; becomes `originator` when answered |

### CallState

| Value | Description |
|-------|-------------|
| `connecting` | Remote party is being alerted |
| `alerting` | User's devices are alerting for incoming or Click-to-Dial call |
| `connected` | Call is connected |
| `held` | User has placed the call on hold |
| `remoteHeld` | Remote party (same org) has placed the call on hold |
| `disconnected` | Call has been disconnected |

### CallType

| Value | Description |
|-------|-------------|
| `location` | Party is within the same location |
| `organization` | Party is within the same org but different location |
| `external` | Party is outside the organization |
| `emergency` | Emergency call destination |
| `repair` | Repair call destination |
| `other` | Does not match any defined type (e.g., feature activation code) |

### TelephonyParty

| Field | Type | Description |
|-------|------|-------------|
| `name` | str (optional) | Party name (if available and privacy not enabled) |
| `number` | str | Party number (digits or URI) |
| `person_id` | str (optional) | Party's person ID |
| `place_id` | str (optional) | Party's place ID |
| `privacy_enabled` | bool (optional) | Whether privacy is enabled |
| `call_type` | CallType (optional) | Call type for the party |

### RedirectReason

| Value | Description |
|-------|-------------|
| `busy` | Forwarded by Call Forwarding Busy |
| `noAnswer` | Forwarded by Call Forwarding No Answer |
| `unavailable` | Forwarded by Business Continuity |
| `unconditional` | Forwarded by Call Forwarding Always |
| `timeOfDay` | Forwarded by Selective Call Forwarding (schedule) |
| `divert` | Redirected by divert action |
| `followMe` | Redirected by Simultaneous Ring |
| `huntGroup` | Redirected by Hunt Group routing |
| `callQueue` | Redirected by Call Queue routing |
| `unknown` | Unknown redirect reason |

### RejectAction

| Value | Behavior |
|-------|----------|
| `busy` | Send to busy (default) |
| `temporarilyUnavailable` | Send to temporarily unavailable |
| `ignore` | Continue ringback, stop alerting user devices |

### RecordingState

| Value | Description |
|-------|-------------|
| `pending` | Requested but not yet started |
| `started` | Recording is active |
| `paused` | Recording is paused |
| `stopped` | Recording has been stopped |
| `failed` | Recording failed |

---

## 5. Service App / Admin API (Call Controls Members)

For **Service Apps** that need to control calls on behalf of users, workspaces, or virtual lines. Uses `spark-admin:calls_read` and `spark-admin:calls_write` scopes.

**Base path:** `POST /v1/telephony/calls/members/{memberId}/{action}`

The Members API mirrors the user-level API but adds `member_id` and `org_id` parameters.

### Available Members Endpoints

| Action | SDK Method | Returns |
|--------|-----------|---------|
| List Calls | `CallControlsMembersApi.list_calls(member_id, org_id)` | `list[TelephonyCall]` |
| Get Call Details | `CallControlsMembersApi.get_call_details(member_id, call_id, org_id)` | `TelephonyCall` |
| Dial | `CallControlsMembersApi.dial(member_id, destination, endpoint_id, org_id)` | `CallInfo` |
| Answer | `CallControlsMembersApi.answer(member_id, call_id, endpoint_id, org_id)` | None |
| Hangup | `CallControlsMembersApi.hangup(member_id, call_id, org_id)` | None |

**`member_id`** can be one of: person ID, workspace ID, or virtual line ID.

<!-- Corrected via OpenAPI spec (webex-cloud-calling.json) 2026-03-19: The Members API supports exactly 5 endpoints — dial, answer, hangup, list calls, and get call details. No hold, resume, transfer, park, or other actions exist for the Members API. These additional call control actions are only available on the user-level /telephony/calls/* endpoints. -->

---

## 6. Additional API: External Voicemail MWI

Set or clear Message Waiting Indicator (MWI) for a person or workspace. Service App only.

```
POST /v1/telephony/externalVoicemail/mwi?id={userId}&orgId={orgId}
```

**SDK Signature:**
```python
CallsApi.update_external_voicemail_mwi(
    id: str,                              # person or workspace ID
    action: ExternalVoicemailMwiAction,   # 'SET' or 'CLEAR'
    org_id: str = None
) -> None
```

**Scope required:** `spark-admin:calls_write`

### CLI: `external-voicemail` (MWI Control)

The `external-voicemail` CLI group sets or clears the Message Waiting Indicator (MWI) for a person or workspace. Requires a Service App token with `spark-admin:calls_write` scope.

| Command | Description |
|---------|-------------|
| `external-voicemail create` | Set or clear MWI status for a user or workspace |

```bash
# Set MWI (light the voicemail indicator) for a user
wxcli external-voicemail create --id <person_id> --action SET

# Clear MWI (turn off the voicemail indicator) for a user
wxcli external-voicemail create --id <person_id> --action CLEAR

# Set MWI for a workspace phone
wxcli external-voicemail create --id <workspace_id> --action SET
```

---

## 7. Common Use Cases

### Click-to-Dial from CRM
```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens=tokens)

# Place a call from the CRM contact page
result = api.telephony.calls.dial(destination="+12223334444")
print(f"Call initiated: {result.call_id}")
```

### Agent Dashboard: List Active Calls
```python
calls = api.telephony.calls.list_calls()
for call in calls:
    print(f"{call.call_id} | {call.state} | {call.remote_party.name} ({call.remote_party.number})")
```

### Consultative Transfer
```python
# Agent has two calls: original caller and the transfer target
# Transfer them together
api.telephony.calls.transfer(call_id1=original_call_id, call_id2=consult_call_id)
```

### Hold, Consult, Transfer Pattern
```python
# 1. Put caller on hold
api.telephony.calls.hold(call_id=caller_call_id)

# 2. Dial the transfer target
consult = api.telephony.calls.dial(destination="+15551234567")

# 3. After speaking with transfer target, transfer both calls
api.telephony.calls.transfer(call_id1=caller_call_id, call_id2=consult.call_id)
```

### Park and Retrieve
```python
# Park the call
parked = api.telephony.calls.park(call_id=call_id)
print(f"Parked against: {parked.number}")

# Later, retrieve it (from any device)
retrieved = api.telephony.calls.retrieve(destination=parked.number)
```

### Call Recording Control
```python
# Start recording (user must have "On Demand" recording mode)
api.telephony.calls.start_recording(call_id=call_id)

# Pause for sensitive info (credit card, SSN)
api.telephony.calls.pause_recording(call_id=call_id)

# Resume
api.telephony.calls.resume_recording(call_id=call_id)

# Stop
api.telephony.calls.stop_recording(call_id=call_id)
```

### Service App: Control Calls for a User
```python
# Using admin/service app credentials with spark-admin:calls_write
from wxc_sdk.telephony.call_contols_members import CallControlsMembersApi

# Dial on behalf of a user
result = members_api.dial(
    member_id="person-uuid-here",
    destination="+12223334444"
)
```

---

## 8. Key Gotchas

1. **3rd Party Call Control only** -- These APIs do not work with Webex app's native calling. They are for building external call control applications.

2. **Multi-Tenant only** -- Not applicable for UCM or Dedicated Instance users.

3. **Service Apps cannot use CallsApi** -- Service Apps must use the `CallControlsMembersApi` (members endpoint) instead.

4. **`callId` vs `id`** -- The API returns `id` in direct call responses but `callId` in webhook events. The SDK's `TelephonyCall` model handles both aliases transparently via the `call_id` property.

5. **Click-to-Dial personality transition** -- A dial request starts with `personality: clickToDial` while alerting the user's devices. Once the user answers, it transitions to `personality: originator`.

6. **Transfer restrictions** -- Unanswered incoming calls cannot be transferred. Use `divert` for unanswered calls.

7. **`lineOwnerId` parameter** -- Present on nearly all methods. Used when the API caller has a secondary line belonging to another user, workspace, or virtual line on their device.

8. **Recording mode dependency** -- `start_recording` / `stop_recording` only work when the user's recording mode is "On Demand". `pause_recording` / `resume_recording` work with both "On Demand" and "Always with Pause/Resume".

9. **Mute capability check** -- Always check `muteCapable` in call details before calling `mute` or `unmute`. Not all calls support it.

10. **Call history limit** -- `call_history` returns a maximum of 20 records per type (placed/missed/received).

---

## See Also

- **[webhooks-events.md](webhooks-events.md)** — Real-time call event notifications via webhooks. The `TelephonyEventData` model inherits from `TelephonyCall` documented here; use webhooks for event-driven call control rather than polling `list_calls`.
- **[person-call-settings-media.md](person-call-settings-media.md)** — Call recording configuration (recording mode, compliance announcements). Recording mode determines which recording control actions are available in this API.
