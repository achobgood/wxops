<!-- Updated by playbook session 2026-03-18 -->
# Call Control API Reference

Webex Calling Call Control APIs enable 3rd-party applications to manage calls on behalf of users. These are **3rd Party Call Control** APIs only, applicable to **Webex Calling Multi-Tenant users** (not UCM or Dedicated Instance users).

This is **not** call *configuration* (forwarding, recording mode, permissions — see `person-call-settings-*.md`), **not** after-the-fact call records (CDR — see `reporting-analytics.md`), and **not** Contact Center task control (`cc-tasks` — a WxCC agent's task, not a Calling call). It acts on calls that are live right now.

> **Base paths — three scopes of the same action** (see [Choosing a Scope](#choosing-a-scope)):
> - `POST /v1/telephony/calls/{action}` — the token's own user (CLI: bare names, e.g. `create-hold`)
> - `POST /v1/telephony/calls/members/me/{action}` — the token's own user (CLI: `-me`, e.g. `create-hold-me`)
> - `POST /v1/telephony/calls/members/{memberId}/{action}` — another member, for admins / Service Apps (CLI: `-members`, e.g. `create-hold-members MEMBER_ID`)
>
> **GET endpoints:** `GET /v1/telephony/calls`, `GET /v1/telephony/calls/{callId}`, `GET /v1/telephony/calls/history`, each with the same `/members/me/` and `/members/{memberId}/` siblings (`calls`, `calls/{callId}`, `history`).

## Sources

- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Call Control APIs

## Table of Contents

- [Required Scopes](#required-scopes) — including [Choosing a Scope](#choosing-a-scope) (bare vs `-me` vs `-members`)
- [Raw HTTP Reference](#raw-http-reference-all-call-control-endpoints)
- [CLI Examples](#cli-examples)
- [1. Call Connection](#1-call-connection)
- [2. Mid-Call Actions](#2-mid-call-actions)
- [3. Call Details & History](#3-call-details--history)
- [4. Data Models](#4-data-models)
- [5. Service App / Admin API](#5-service-app--admin-api-call-controls-members)
- [6. Wrap-Up Reasons](#6-wrap-up-reasons-call-controls-members--call-controls-members-me)
- [7. Conference Controls: Three Scopes](#7-conference-controls-three-scopes)
- [8. Additional API: External Voicemail MWI](#8-additional-api-external-voicemail-mwi)
- [9. Common Use Cases](#9-common-use-cases)
- [10. Key Gotchas](#10-key-gotchas)
- [See Also](#see-also)

---

## Required Scopes

| Scope | Grants | Used By |
|-------|--------|---------|
| `spark:calls_read` | List calls, get call details, call history | User tokens (personal) |
| `spark:calls_write` | All call control actions (dial, answer, hold, transfer, etc.) | User tokens (personal) |
| `spark-admin:calls_read` | List calls, get call details for any member | Service App tokens (admin) |
| `spark-admin:calls_write` | All call control actions for any member | Service App tokens (admin) |

- **User-level APIs** use `spark:calls_read` / `spark:calls_write` and operate on the authenticated user's calls.
- **Service App / Admin APIs** use `spark-admin:calls_read` / `spark-admin:calls_write` and operate on any person, workspace, or virtual line by `member_id`.

### Choosing a Scope

Every call action and every conference action is published up to three times, once per scope. The scope decides *whose* call you are touching, and it is fixed by the path, not by a flag. This is **not** a choice of feature — `create-hold`, `create-hold-me` and `create-hold-members` all put a call on hold; they differ only in who owns the call.

| Scope | Path family | CLI suffix | Whose call | Spec evidence |
|-------|-------------|-----------|------------|---------------|
| Bare | `/telephony/calls/{action}`, `/telephony/conference/...` | none (`create-hold`, `list-history`) | The user the token belongs to | Descriptions speak of "the user"; body/query accepts `lineOwnerId`, "a secondary line on a device owned by the user invoking the API" |
| Self | `/telephony/calls/members/me/{action}`, `/telephony/conference/members/me/...` | `-me` (`create-hold-me`, `list-history-me`) | The user the token belongs to | Same descriptions and same `lineOwnerId` field as bare; `wrapupreasons` says "the authenticated user's last completed call" |
| Member | `/telephony/calls/members/{memberId}/{action}`, `/telephony/conference/members/{memberId}/...` | `-members` + `MEMBER_ID` positional (`create-hold-members MEMBER_ID`) | Any person, workspace or virtual line in the org | `memberId` path param; optional `orgId` query — "If not provided, the orgId of the Service App is used"; `wrapupreasons` says "for admins/service apps to perform actions on behalf of a user". No `lineOwnerId` |

**When to use which:**

- **You hold a user's own OAuth token and act on that user's calls** → bare. It is the long-standing path every example in this doc uses. `-me` reaches the same calls by a second published path; nothing in the spec says one is preferred.
- **You are a Service App or admin integration acting on someone else's calls** → `-members MEMBER_ID`. The bare and `-me` paths act on the token's own user, which is why an admin token on a bare command gets 400 "Target user not authorized" (CLAUDE.md known issue #1).
- **You need a secondary line on the user's own device** → bare or `-me` with `--line-owner-id`. `-members` has no `lineOwnerId`; the `MEMBER_ID` itself names the line owner.

**Asymmetries — not every action has all three:**

| Action | Bare | `-me` | `-members` |
|--------|------|-------|-----------|
| List calls on a call queue (`list-calls-queues QUEUE_ID`, `GET /telephony/queues/{queueId}/calls`) | yes | — | — |
| Set wrap-up reasons | — | `call-controls-members-me create-wrapupreasons` | `call-controls-members create-wrapupreasons MEMBER_ID` |
| Conference supervisor modes (barge-in, silent monitor, coach) | — | `conference create-barge-in-me` etc. | `conference create-barge-in-members MEMBER_ID` etc. |

**Unverified:** the scope descriptions above are read from the spec's own operation text (`specs/webex-cloud-calling.json`); none of the `-me` or `-members` siblings added in the post-2026-09-21 sync has been exercised against a live org. The spec does not state which OAuth scopes each family accepts — the `spark-admin:calls_*` mapping for `-members` is this doc's long-standing claim (see the caveat in §5), not something the new spec text confirms.

---

## Raw HTTP Reference (All Call Control Endpoints)

All call control endpoints use `https://webexapis.com/v1/telephony/calls/{action}`. Most are POST actions that take a JSON body. GET endpoints retrieve call state.

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

### User-Level Call Actions

| Action | Method | URL | Body Fields |
|--------|--------|-----|-------------|
| Dial | POST | `{BASE}/telephony/calls/dial` | `destination` (required), `endpointId`, `singleNumberReachPhoneNumber`, `lineOwnerId` |
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
| Retrieve | POST | `{BASE}/telephony/calls/retrieve` | `destination`, `endpointId`, `singleNumberReachPhoneNumber`, `lineOwnerId` |
| Pull | POST | `{BASE}/telephony/calls/pull` | `endpointId`, `lineOwnerId` |
| Push | POST | `{BASE}/telephony/calls/push` | `callId`, `lineOwnerId` |
| Pickup | POST | `{BASE}/telephony/calls/pickup` | `target`, `endpointId`, `singleNumberReachPhoneNumber`, `lineOwnerId` |
| Barge In | POST | `{BASE}/telephony/calls/bargeIn` | `target` (required), `endpointId`, `singleNumberReachPhoneNumber`, `lineOwnerId` |
| Start Recording | POST | `{BASE}/telephony/calls/startRecording` | `callId`, `lineOwnerId` |
| Stop Recording | POST | `{BASE}/telephony/calls/stopRecording` | `callId`, `lineOwnerId` |
| Pause Recording | POST | `{BASE}/telephony/calls/pauseRecording` | `callId`, `lineOwnerId` |
| Resume Recording | POST | `{BASE}/telephony/calls/resumeRecording` | `callId`, `lineOwnerId` |
| Transmit DTMF | POST | `{BASE}/telephony/calls/transmitDtmf` | `callId`, `dtmf`, `lineOwnerId` |

The spec marks no body field required on the four recording actions or Transmit DTMF. To merge calls into a conference, use `POST {BASE}/telephony/conference` with `callIds` (§7) — the spec publishes no `/telephony/calls/conference`.

### User-Level Read Endpoints

| Action | Method | URL | Query Params | Response Key |
|--------|--------|-----|-------------|--------------|
| List Calls | GET | `{BASE}/telephony/calls` | `lineOwnerId` | `calls` |
| Get Call Details | GET | `{BASE}/telephony/calls/{callId}` | `lineOwnerId` | (direct object) |
| List Call History | GET | `{BASE}/telephony/calls/history` | `type` | `history` |

### Service App / Members Endpoints and the `members/me` Family

Every user-level action above is also published under two prefixes — see [Choosing a Scope](#choosing-a-scope) for which to use:

| Prefix | Who | Body fields |
|--------|-----|-------------|
| `{BASE}/telephony/calls/members/{memberId}/{action}` | Another person, workspace or virtual line (admin / Service App); optional `?orgId=` | Same as the user-level row **minus `lineOwnerId`** |
| `{BASE}/telephony/calls/members/me/{action}` | The token's own user | Identical to the user-level row, `lineOwnerId` included |

The `{action}` suffixes are the same as the user-level paths: `dial`, `answer`, `reject`, `hangup`, `hold`, `resume`, `mute`, `unmute`, `divert`, `transfer`, `park`, `retrieve`, `pull`, `push`, `pickup`, `bargeIn`, `startRecording`, `stopRecording`, `pauseRecording`, `resumeRecording`, `transmitDtmf`. The reads are `GET .../calls`, `GET .../calls/{callId}` and `GET .../history`. One extra exists only under these prefixes: `POST .../wrapupreasons` (§6). **Unverified** against a live org — read from the spec.

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

#### Service App: hold, then transfer, a member's call

```python
# Same bodies as the user-level calls, minus lineOwnerId. Unverified live.
api.session.rest_post(f"{BASE}/telephony/calls/members/{member_id}/hold", json={"callId": caller_call_id})
consult = api.session.rest_post(f"{BASE}/telephony/calls/members/{member_id}/dial", json={"destination": "+15551234567"})
api.session.rest_post(f"{BASE}/telephony/calls/members/{member_id}/transfer", json={
    "callId1": caller_call_id,
    "callId2": consult["callId"]
})
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
6. **`/members/{memberId}/` takes no `lineOwnerId`, but `/members/me/` does.** On the member path the `memberId` in the URL already names the line owner, so the spec drops the field; the `members/me` family keeps it exactly as the bare path does. In the CLI, `-members` commands have no `--line-owner-id` and `-me` commands do.
7. **No pagination on call list** -- `GET .../telephony/calls` returns all active calls for the user (typically a small number).
8. **History max 20 per type** -- `GET .../telephony/calls/history` returns at most 20 records per type (placed/missed/received), max 60 total.

---

## CLI Examples

> **Important:** The bare and `-me` commands act as the token's own user and need a **user-level OAuth token**; an admin token returns 400 "Target user not authorized". Configure wxcli with a user's personal access token: `wxcli configure`. Acting on someone else's calls from a Service App or admin integration is what the `-members` commands are for — see [Choosing a Scope](#choosing-a-scope).

### Command Reference

The `call-controls` group holds every call action three times over: a bare name, a `-me` sibling and a `-members` sibling. The bare names below are the original commands, unchanged; they still hit `/telephony/calls/...`.

| Bare command | Description | Key Options | `-me` sibling | `-members` sibling (`MEMBER_ID` positional) |
|--------------|-------------|-------------|---------------|-------------------|
| `create` | Dial | `--destination` (required), `--endpoint-id`, `--single-number-reach-phone-number`, `--line-owner-id` | `create-dial-me` | `create-dial-members` |
| `create-answer-calls` | Answer | `--call-id` (required), `--endpoint-id`, `--line-owner-id` | `create-answer-me` | `create-answer-members` |
| `create-reject` | Reject | `--call-id` (required), `--action`, `--line-owner-id` | `create-reject-me` | `create-reject-members` |
| `create-hangup-calls` | Hangup | `--call-id` (required), `--line-owner-id` | `create-hangup-me` | `create-hangup-members` |
| `create-hold` | Hold | `--call-id` (required), `--line-owner-id` | `create-hold-me` | `create-hold-members` |
| `create-resume` | Resume | `--call-id` (required), `--line-owner-id` | `create-resume-me` | `create-resume-members` |
| `create-mute` | Mute | `--call-id` (required), `--line-owner-id` | `create-mute-me` | `create-mute-members` |
| `create-unmute` | Unmute | `--call-id` (required), `--line-owner-id` | `create-unmute-me` | `create-unmute-members` |
| `create-divert` | Divert | `--call-id` (required), `--destination`, `--to-voicemail`, `--line-owner-id` | `create-divert-me` | `create-divert-members` |
| `create-transfer` | Transfer | `--call-id1`, `--call-id2`, `--destination`, `--line-owner-id` | `create-transfer-me` | `create-transfer-members` |
| `create-park` | Park | `--call-id` (required), `--destination`, `--is-group-park`, `--line-owner-id` | `create-park-me` | `create-park-members` |
| `create-retrieve` | Retrieve | `--destination`, `--endpoint-id`, `--single-number-reach-phone-number`, `--line-owner-id` | `create-retrieve-me` | `create-retrieve-members` |
| `create-pull` | Pull | `--endpoint-id`, `--line-owner-id` | `create-pull-me` | `create-pull-members` |
| `create-push` | Push | `--call-id`, `--line-owner-id` | `create-push-me` | `create-push-members` |
| `create-pickup` | Pickup | `--target`, `--endpoint-id`, `--single-number-reach-phone-number`, `--line-owner-id` | `create-pickup-me` | `create-pickup-members` |
| `create-barge-in` | Barge In | `--target` (required), `--endpoint-id`, `--single-number-reach-phone-number`, `--line-owner-id` | `create-barge-in-me` | `create-barge-in-members` |
| `create-start-recording` | Start Recording | `--call-id`, `--line-owner-id` | `create-start-recording-me` | `create-start-recording-members` |
| `create-stop-recording` | Stop Recording | `--call-id`, `--line-owner-id` | `create-stop-recording-me` | `create-stop-recording-members` |
| `create-pause-recording` | Pause Recording | `--call-id`, `--line-owner-id` | `create-pause-recording-me` | `create-pause-recording-members` |
| `create-resume-recording` | Resume Recording | `--call-id`, `--line-owner-id` | `create-resume-recording-me` | `create-resume-recording-members` |
| `create-transmit-dtmf` | Transmit DTMF | `--call-id`, `--dtmf`, `--line-owner-id` | `create-transmit-dtmf-me` | `create-transmit-dtmf-members` |
| `list` | List Calls | `--line-owner-id`, `-o table\|json` | `list-calls-me` | `list-calls-members` |
| `show` | Get Call Details | `CALL_ID` (positional, required), `--line-owner-id`, `-o table\|json` | `show-calls-me CALL_ID` | `show-calls-members MEMBER_ID CALL_ID` |
| `list-history` | List Call History | `--type placed\|missed\|received`, `-o table\|json` | `list-history-me` | `list-history-members` |
| `list-calls-queues` | List Call Queue Calls | `QUEUE_ID` (positional, required) | — | — |

The siblings take the same options as the bare command, except that **`-members` commands never take `--line-owner-id`** (the `MEMBER_ID` already names the line owner). Wrap-up reasons are not in this group — they are the separate `call-controls-members` / `call-controls-members-me` groups (§6).

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

> These commands use `spark-admin:calls_read` / `spark-admin:calls_write` scopes and operate on behalf of a person, workspace, or virtual line by member ID. `MEMBER_ID` is help-typed "Webex PEOPLE id", but the spec accepts a person, workspace **or** virtual line ID — on ID kinds the spec outranks `--help` (CLAUDE.md, Source of Truth). The `orgId` query parameter is filled from the org saved in wxcli config (`wxcli switch-org`); there is no `--org-id` flag.

```bash
# Dial on behalf of a user (Service App token required)
wxcli call-controls create-dial-members <member_id> --destination "+12223334444"

# Answer a call on behalf of a user
wxcli call-controls create-answer-members <member_id> --call-id Y2lzY29zcGFyay...

# Hang up a call on behalf of a user
wxcli call-controls create-hangup-members <member_id> --call-id Y2lzY29zcGFyay...

# List active calls for a user
wxcli call-controls list-calls-members <member_id>

# Get call details for a specific call on a user
wxcli call-controls show-calls-members <member_id> Y2lzY29zcGFyay...

# Mid-call actions have member siblings too (Unverified live — spec-derived)
wxcli call-controls create-hold-members <member_id> --call-id Y2lzY29zcGFyay...
wxcli call-controls create-resume-members <member_id> --call-id Y2lzY29zcGFyay...
wxcli call-controls create-transfer-members <member_id> --call-id1 Y2lzY29zcGFyay_call1... --call-id2 Y2lzY29zcGFyay_call2...
wxcli call-controls create-park-members <member_id> --call-id Y2lzY29zcGFyay...
wxcli call-controls create-start-recording-members <member_id> --call-id Y2lzY29zcGFyay...
wxcli call-controls list-history-members <member_id> --type missed -o json
```

### Self-Scoped (`-me`) Siblings

```bash
# The token's own user, via /telephony/calls/members/me/... (Unverified live — spec-derived)
wxcli call-controls create-hold-me --call-id Y2lzY29zcGFyay...
wxcli call-controls list-calls-me -o json
wxcli call-controls list-history-me --type placed -o json
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

- **No target:** picks up from the user's call pickup group.
- **With target:** picks up from the specified user (digits or URI).

**Response:** Returns `CallInfo` (callId + callSessionId).

---

### Reject

Reject an unanswered incoming call.

```
POST /v1/telephony/calls/reject
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

---

### Resume

Resume a held call.

```
POST /v1/telephony/calls/resume
```

---

### Transfer

Transfer two calls together. Supports multiple transfer modes depending on parameters.

```
POST /v1/telephony/calls/transfer
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

**Response:** Returns a `TelephonyParty` object (the `parkedAgainst` party). The `number` field from this response is used as the destination for the `retrieve` command.

---

### Retrieve (Unpark)

Retrieve a parked call. Initiates a new call (similar to dial) to perform the retrieval.

```
POST /v1/telephony/calls/retrieve
```

---

### Pull

Pull a call from one device to another. Useful for moving a call between desk phone, mobile app, and desktop app.

```
POST /v1/telephony/calls/pull
```

A temporary new call is initiated. When the user answers on the target device, that device connects to the pulled call and the temporary call is released.

---

### Push (Executive Assistant)

Push a call from an assistant to the associated executive.

```
POST /v1/telephony/calls/push
```

**Note:** Only valid when the assistant's call is associated with an executive.

---

### Barge In

Barge into another user's answered call. Initiates a new call (similar to dial).

```
POST /v1/telephony/calls/bargeIn
```

---

### Conference (3-Way Merge)

Merge two or more of the user's calls into a conference. This is **not** a `/telephony/calls/...` action: the spec publishes no `/telephony/calls/conference`, and `transfer` with two call IDs is *not* a merge — the spec calls it an Attended/Consultative Transfer, which hands the two calls to each other rather than keeping the user in a conference with both.

```
POST /v1/telephony/conference
{"callIds": ["CALL_ID_1", "CALL_ID_2"]}
```

The spec requires `callIds` with a minimum of two entries, each an existing call between the user and a participant. CLI: `wxcli conference create --json-body '{"callIds":["CALL_ID_1","CALL_ID_2"]}'` (or `create-conference-me` / `create-conference-members MEMBER_ID`). Full conference controls are in §7.

---

### Hangup

Disconnect a call. If used on an unanswered incoming call, the call is rejected and sent to busy.

```
POST /v1/telephony/calls/hangup
```

---

### Mute / Unmute

Mute or unmute a call. Only valid on calls that report `muteCapable: true` in call details.

```
POST /v1/telephony/calls/mute
POST /v1/telephony/calls/unmute
```

---

### Recording Control

Control call recording. Availability depends on the user's call recording mode.

| Endpoint | Recording Mode Required |
|----------|------------------------|
| `POST .../startRecording` | "On Demand" |
| `POST .../stopRecording` | "On Demand" |
| `POST .../pauseRecording` | "On Demand" or "Always with Pause/Resume" |
| `POST .../resumeRecording` | "On Demand" or "Always with Pause/Resume" |

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

**Valid DTMF characters:** `0-9`, `*`, `#`, `A`, `B`, `C`, `D`
**Pause:** Use a comma `,` to insert a pause between digits. Example: `"1,234"` sends `1`, pauses, then sends `2`, `3`, `4`.

### Gotchas

- **Transfer restrictions:** Unanswered incoming calls cannot be transferred. Use `divert` instead.
- **Push is executive-assistant only:** `push` is only valid when the assistant's call is associated with an executive.
- **Mute capability check:** Only calls that report `muteCapable: true` in call details support `mute`/`unmute`. Always check before calling.
- **DTMF pause character:** Use a comma `,` to insert a pause between DTMF digits. This is not documented prominently in the API reference.
- **Recording mode dependency:** Start/Stop Recording only work when the user's recording mode is "On Demand". Pause/Resume Recording work with both "On Demand" and "Always with Pause/Resume".

---

## 3. Call Details & History

### List Active Calls

Get all active calls for the user.

```
GET /v1/telephony/calls
```

---

### Get Call Details

Get details of a specific active call.

```
GET /v1/telephony/calls/{callId}
```

---

### List Call History

Get the user's call history. Returns a maximum of **20 records per type**.

```
GET /v1/telephony/calls/history
```

**HistoryType values:**

| Value | Description |
|-------|-------------|
| `placed` | Outgoing calls placed by the user |
| `missed` | Incoming calls not answered |
| `received` | Incoming calls answered |

If the `type` query parameter is omitted, all types are returned (up to 20 each = max 60 total).

**CallHistoryRecord fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | HistoryType | placed, missed, or received |
| `name` | str (optional) | Party name (if available and privacy not enabled) |
| `number` | str (optional) | Party number (digits or URI) |
| `privacy_enabled` | bool | Whether privacy is enabled |
| `time` | datetime | When the record was created (placed=call time, missed=disconnect time, received=answer time) |

### Gotchas

- **Call history limit:** List Call History returns a maximum of 20 records per type (placed/missed/received). If the `type` query parameter is omitted, all types are returned (up to 20 each = max 60 total).
- **No pagination on call list:** List Calls returns all active calls for the user (typically a small number). There is no pagination support.

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

> **Note:** The `spark-admin:calls_read` and `spark-admin:calls_write` scopes listed above for the Members API cannot be confirmed from any publicly indexed developer.webex.com page. They may be accurate but should be verified against the live API reference or Webex TAC before building production integrations against the Members API.

**Base path:** `POST /v1/telephony/calls/members/{memberId}/{action}`

The Members API mirrors the user-level API but adds a `memberId` path parameter (and optionally `orgId`).

### Available Members Endpoints

**Unverified:** read from the spec, not exercised against a live org. The spec synced after 2026-09-21 publishes the Members API at parity with the user-level API: 24 call operations under `/telephony/calls/members/{memberId}/` — one for every user-level action and read — plus `wrapupreasons`. The `/telephony/calls/members/me/` family publishes the same 24 plus its own `wrapupreasons`, scoped to the token's own user (see [Choosing a Scope](#choosing-a-scope)).

| Action | Endpoint suffix | Returns (per spec) |
|--------|-----------------|---------|
| List Calls | `GET calls` | List of call objects |
| Get Call Details | `GET calls/{callId}` | Call object |
| Call History | `GET history` | List of history records (max 20 per type) |
| Dial | `dial` | 201 `{callId, callSessionId}` |
| Answer / Hangup / Reject | `answer`, `hangup`, `reject` | 204 No Content |
| Hold / Resume | `hold`, `resume` | 204 No Content |
| Mute / Unmute | `mute`, `unmute` | 204 No Content |
| Divert | `divert` | 204 No Content |
| Transfer | `transfer` | 204 (attended) or 201 `{callId, callSessionId}` (mute transfer) |
| Park | `park` | 200 `{parkedAgainst}` |
| Retrieve / Pickup / Pull | `retrieve`, `pickup`, `pull` | 201 `{callId, callSessionId}` |
| Push | `push` | 204 No Content |
| Barge-In | `bargeIn` | 201 `{callId, callSessionId}` |
| Transmit DTMF | `transmitDtmf` | 204 No Content |
| Recording control | `startRecording`, `stopRecording`, `pauseRecording`, `resumeRecording` | 204 No Content |
| Set Wrap-Up Reasons | `wrapupreasons` | 204 — a CLI group of its own, see [§6](#6-wrap-up-reasons-call-controls-members--call-controls-members-me) |

**`memberId`** can be one of: person ID, workspace ID, or virtual line ID.

In the CLI every one of these except `wrapupreasons` lives in the `call-controls`
group, suffixed by scope: bare for `/telephony/calls/...`, `-members` for
`/members/{memberId}/...`, `-me` for `/members/me/...`. The full name mapping is
the [Command Reference](#command-reference) table.

### CLI Examples

```bash
# Admin/Service App: put another member's call on hold
wxcli call-controls create-hold-members MEMBER_ID --call-id CALL_ID

# The same action on the token's own call, via /members/me/
wxcli call-controls create-hold-me --call-id CALL_ID

# The bare user-level path, unchanged
wxcli call-controls create-hold --call-id CALL_ID
```

### Raw HTTP

```bash
# Member-scoped: no lineOwnerId in the body; orgId is an optional query parameter
curl -X POST "https://webexapis.com/v1/telephony/calls/members/MEMBER_ID/hold" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"callId":"CALL_ID"}'

# Self-scoped: same body as the bare path, lineOwnerId allowed
curl -X POST "https://webexapis.com/v1/telephony/calls/members/me/hold" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"callId":"CALL_ID"}'
```

### Gotchas

- **The Members API is no longer limited to five actions — Hold, Resume, Transfer, Mute, Park, Barge-in and the rest are all published under `/members/{memberId}/`.** Through the 2026-09-21 spec this surface published only Dial, Answer, Hangup, List Calls and Get Call Details, and this doc used to tell Service App integrations that every other action was user-level only and needed the target user's own OAuth token. That advice is now wrong: the spec publishes 19 more call operations for a member (including `history`), plus `wrapupreasons`. **Unverified:** the parity is read from the spec, not exercised against a live org — confirm scope behaviour on one action before building on all of them.
- **`-me` is a distinct path family, not an alias for the bare user-level path.** `/telephony/calls/hold` and `/telephony/calls/members/me/hold` are two separately published endpoints with identical descriptions and bodies, and the CLI ships them as two commands (`create-hold`, `create-hold-me`). **Unverified:** the spec does not say which token types each accepts. Known issue #1 — admin tokens get 400 "Target user not authorized" on user-level call control — is the reason to test the one you pick rather than assume they are interchangeable.
- **`-members` commands take no `--line-owner-id`, and `MEMBER_ID` is mislabelled "Webex PEOPLE id" in `--help`.** The member path drops `lineOwnerId` because the path's `memberId` already names the line owner. The spec says that `memberId` may be a person, workspace or virtual line ID; where `--help` and the spec disagree on an ID kind, the spec is right (CLAUDE.md, Source of Truth). **Unverified** against a live workspace or virtual line.

---

## 6. Wrap-Up Reasons (`call-controls-members` / `call-controls-members-me`)

Applies wrap-up reasons — the short disposition labels an agent picks after a call ("Sale", "Callback requested") — to a member's **last completed call**. Cisco tagged these two operations apart from the rest of Call Controls (`Call Controls Members`, `Call Controls Members Me`), so in the CLI they are two groups holding one command each rather than commands inside `call-controls`. There is no bare `/telephony/calls/wrapupreasons`.

This is **not** where the list of wrap-up reasons is *defined*: that is Customer Assist configuration (`wxcli customer-assist list`/`create`, org-level reasons assigned to a queue — see `call-features-additional.md`). This surface only *applies* reasons, by name, to a call that has already ended. It is also **not** the Contact Center wrap-up surface: WxCC keeps its own auxiliary/wrap-up codes (`cc-aux-code`) against a WxCC task, on a different API behind a region-scoped base URL and a `cjp:` scope. And it is **not** a read surface — neither group publishes a GET, so there is no way to ask what wrap-up reasons a call already carries.

| Group | Scope | Command | Endpoint |
|-------|-------|---------|----------|
| `call-controls-members` | another member; "for admins/service apps to perform actions on behalf of a user" (spec) | `create-wrapupreasons MEMBER_ID` | `POST /v1/telephony/calls/members/{memberId}/wrapupreasons` |
| `call-controls-members-me` | "the authenticated user" (spec) | `create-wrapupreasons` | `POST /v1/telephony/calls/members/me/wrapupreasons` |

**Body (both):** `{"wrapupReasons": ["Reason1", "Reason2"]}` — an array of wrap-up reason **names**. There is no `callId`: the spec applies them to the member's last completed call. Returns 204.

### CLI Examples

```bash
# Set wrap-up reasons on your own last completed call
wxcli call-controls-members-me create-wrapupreasons --json-body '{"wrapupReasons":["Sale"]}'

# Admin / Service App: set them on another member's last completed call
wxcli call-controls-members create-wrapupreasons MEMBER_ID --json-body '{"wrapupReasons":["Sale","Callback requested"]}'
```

### Raw HTTP

```bash
# Self-scoped
curl -X POST "https://webexapis.com/v1/telephony/calls/members/me/wrapupreasons" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"wrapupReasons":["Sale"]}'

# Member-scoped (admin / Service App)
curl -X POST "https://webexapis.com/v1/telephony/calls/members/MEMBER_ID/wrapupreasons" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"wrapupReasons":["Sale","Callback requested"]}'
```

### Gotchas

- **`--json-body` is the only way to send the reasons — the command has no `--wrapup-reasons` flag.** The single body field is an array of strings, which the generator does not flatten into an option; without `--json-body` the command sends an empty body, and the spec says "the request must provide wrapupReasons". The `--help` text shows the shape: `'{"wrapupReasons":["..."]}'`. **Unverified:** what the API returns for an empty body has not been observed.
- **There is no `callId` — the reasons land on the member's *last completed* call, so timing decides which call you tag.** If the member finishes another call before you post, the reasons go to that one instead. Post straight after the call ends (a `telephony_calls` `disconnected` webhook is the natural trigger). **Unverified** live.
- **Reasons are sent by name, so they presumably have to match names already configured for the member's queue.** The spec calls them "wrap-up reason names to apply to the agent's last completed call"; those names are defined in Customer Assist (`customer-assist` group). **Unverified:** whether an unknown name is rejected or silently stored is not stated in the spec and has not been observed.

---

## 7. Conference Controls: Three Scopes

Controls a multi-party *Calling* conference that a user hosts — start one from existing calls, add, mute, deafen, hold, release — plus three supervisor modes that change how a member sits in a conference. This is **not** a Webex Meetings meeting (that is `manage-meetings`), **not** the Customer Assist supervisor *configuration* that decides who may monitor whom (`location-recording-advanced.md` §4), and **not** `call-controls create-barge-in`, which places a *new call* to barge into someone else's call and returns a `callId`. The conference data model (`ConferenceDetails`, `ConferenceTypeEnum`) and the bare commands are already documented in `location-recording-advanced.md` §3; this section covers the scope split.

Every bare `conference` command keeps its name and still hits `/telephony/conference/...`. Each has a `-me` sibling (`/telephony/conference/members/me/...`) and a `-members` sibling (`/telephony/conference/members/{memberId}/...`); see [Choosing a Scope](#choosing-a-scope).

| Action | Bare | `-me` | `-members` (`MEMBER_ID`) | Body / key options |
|--------|------|-------|--------------------------|--------------------|
| Get conference details | `list` | `list-conference-me` | `list-conference-members` | bare/`-me`: `--line-owner-id` |
| Start conference | `create` | `create-conference-me` | `create-conference-members` | `--json-body '{"callIds":[...]}'` (min 2, required) |
| Release conference | `delete` | `delete-conference-me` | `delete-conference-members` | `--force` skips the confirmation prompt |
| Add participant | `create-add-participant` | `create-add-participant-me` | `create-add-participant-members` | `--call-id` (required) |
| Mute / unmute | `create-mute` / `create-unmute` | `create-mute-me` / `create-unmute-me` | `create-mute-members` / `create-unmute-members` | `--call-id` optional — omit it to mute/unmute the **host** |
| Deafen / undeafen | `create-deafen` / `create-undeafen` | `create-deafen-me` / `create-undeafen-me` | `create-deafen-members` / `create-undeafen-members` | `--call-id` (required) |
| Hold / resume host | `create-hold` / `create-resume` | `create-hold-me` / `create-resume-me` | `create-hold-members` / `create-resume-members` | no body; bare/`-me`: `--line-owner-id` |
| Supervisor: barge-in | — | `create-barge-in-me` | `create-barge-in-members` | no body |
| Supervisor: silent monitor | — | `create-silent-monitor-me` | `create-silent-monitor-members` | no body |
| Supervisor: coach | — | `create-supervisor-coach-me` | `create-supervisor-coach-members` | no body |

The three supervisor modes, in the spec's words, "transition the member's conference type": **barge-in** — "join the conference as a full participant where all parties can hear the supervisor"; **silent monitor** — "listen to the conference without being heard"; **coach** — "a one-way audio session where only the agent can hear the supervisor". They correspond to the `bargeIn`, `silentMonitoring` and `coaching` values of `ConferenceTypeEnum`.

### CLI Examples

```bash
# Service App / admin: read a member's conference (empty object if none)
wxcli conference list-conference-members MEMBER_ID -o json

# Service App / admin: merge two of a member's calls into a conference
wxcli conference create-conference-members MEMBER_ID --json-body '{"callIds":["CALL_ID_1","CALL_ID_2"]}'

# Mute one participant in a member's conference (omit --call-id to mute the host)
wxcli conference create-mute-members MEMBER_ID --call-id PARTICIPANT_CALL_ID

# Switch a supervisor's conference from silent monitoring to coaching, then to full barge-in
wxcli conference create-silent-monitor-members MEMBER_ID
wxcli conference create-supervisor-coach-members MEMBER_ID
wxcli conference create-barge-in-members MEMBER_ID

# End a member's conference without the interactive prompt
wxcli conference delete-conference-members MEMBER_ID --force

# The token's own user, via /members/me/
wxcli conference list-conference-me -o json
wxcli conference create-silent-monitor-me
```

### Raw HTTP

```bash
# Start a conference for a member (Service App / admin)
curl -X POST "https://webexapis.com/v1/telephony/conference/members/MEMBER_ID/conference" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"callIds":["CALL_ID_1","CALL_ID_2"]}'

# Get / release a member's conference
curl "https://webexapis.com/v1/telephony/conference/members/MEMBER_ID/conference" -H "Authorization: Bearer $TOKEN"
curl -X DELETE "https://webexapis.com/v1/telephony/conference/members/MEMBER_ID/conference" -H "Authorization: Bearer $TOKEN"

# Supervisor modes: no request body, 204 on success
curl -X POST "https://webexapis.com/v1/telephony/conference/members/MEMBER_ID/silentMonitor"   -H "Authorization: Bearer $TOKEN"
curl -X POST "https://webexapis.com/v1/telephony/conference/members/MEMBER_ID/supervisorCoach" -H "Authorization: Bearer $TOKEN"
curl -X POST "https://webexapis.com/v1/telephony/conference/members/MEMBER_ID/bargeIn"         -H "Authorization: Bearer $TOKEN"

# Self-scoped equivalents live under /telephony/conference/members/me/...
curl -X POST "https://webexapis.com/v1/telephony/conference/members/me/silentMonitor" -H "Authorization: Bearer $TOKEN"
```

Note the member path for start/get/release ends in `/conference` (`.../members/{memberId}/conference`), unlike the bare `POST|GET|DELETE /telephony/conference`.

### Gotchas

- **The supervisor modes exist only on the `-me` and `-members` paths — there is no bare `conference create-barge-in`.** Do not reach for `call-controls create-barge-in` as the bare equivalent: that one places a new call against a `--target` and returns 201 with a `callId`, while the conference modes take no body and return 204, transitioning a conference that already exists. **Unverified:** the spec does not say what state the member must be in for a transition to succeed (for example, whether silent monitoring must already be active before `supervisorCoach`), and none of the three has been exercised live.
- **`create-mute` / `create-unmute` with no `--call-id` act on the host, not a participant.** The spec: "Mutes the host when no request body is provided". Forgetting the flag silences the person running the conference rather than the participant you meant. Applies to all three scopes. **Unverified** live.
- **`delete` and `delete-conference-*` prompt for confirmation and will block a script; pass `--force`.** They release the whole conference. **Unverified** live.
- **`-members` conference commands take no `--line-owner-id`; bare and `-me` ones do where the spec allows it.** Same rule as call control: the `MEMBER_ID` names the line owner. **Unverified** live.

---

## 8. Additional API: External Voicemail MWI

Set or clear Message Waiting Indicator (MWI) for a person or workspace. Service App only.

```
POST /v1/telephony/externalVoicemail/mwi?id={userId}&orgId={orgId}
POST /v1/telephony/externalVoicemail/members/{memberId}/mwi?orgId={orgId}
```

**Query-param form:** `id` (person or workspace ID, required), `orgId` (optional). **Member-path form:** the target goes in the path as `memberId` — per the spec "person, workspace, or virtual line" — and only `orgId` is a query param. **Body (both):** `{"action": "SET"}` or `{"action": "CLEAR"}`.

**Scope required:** `spark-admin:calls_write`

### CLI: `external-voicemail` (MWI Control)

The `external-voicemail` CLI group sets or clears the Message Waiting Indicator (MWI) — the voicemail light/badge — when an **external** voicemail system holds the messages. It does not create, store, or read voicemail, and it is not the Webex voicemail message surface (`user-call-settings-members`, see `person-call-settings-media.md` §13). Requires a Service App token with `spark-admin:calls_write` scope.

| Command | Description |
|---------|-------------|
| `external-voicemail create` | Set or clear MWI status; target passed as `--id` (person or workspace) |
| `external-voicemail create-mwi` | Same action by member ID in the path (person, workspace, or virtual line) |

```bash
# Set MWI (light the voicemail indicator) for a user
wxcli external-voicemail create --id <person_id> --action SET

# Clear MWI (turn off the voicemail indicator) for a user
wxcli external-voicemail create --id <person_id> --action CLEAR

# Set MWI for a workspace phone
wxcli external-voicemail create --id <workspace_id> --action SET

# Member-path form — the one to use for a virtual line
wxcli external-voicemail create-mwi MEMBER_ID --action SET
wxcli external-voicemail create-mwi MEMBER_ID --action CLEAR
```

```bash
# Raw HTTP, member-path form (204 No Content on success)
curl -X POST "https://webexapis.com/v1/telephony/externalVoicemail/members/MEMBER_ID/mwi" \
  -H "Authorization: Bearer $SERVICE_APP_TOKEN" -H "Content-Type: application/json" \
  -d '{"action": "SET"}'
```

### Gotchas

- **Only the member-path form names a virtual line.** The spec lists `memberId` as "person, workspace, or virtual line" for `create-mwi`, while `create`'s `id` is "the user or workspace". If the external mailbox belongs to a virtual line, use `create-mwi`. **Unverified:** spec text only; no virtual line MWI has been set live.
- **`create-mwi`'s `MEMBER_ID` is not only a person, whatever `--help` says.** `--help` types the positional "Webex PEOPLE id"; the spec's `memberId` accepts a workspace or virtual line too. On an ID kind, the doc outranks `--help` (root CLAUDE.md, Source of Truth Precedence). **Unverified:** spec text only.
- **The member-path description still tells you to pass an `id` query parameter — don't.** Upstream copied the query-param form's prose ("Specify the target user or workspace with the required `id` query parameter") onto the member path, but that operation declares no `id` parameter; the target is the path segment. **Unverified:** read from the spec's parameter list; not confirmed against a live call.
- **Neither command has a read-back.** Both are POST-only, return 204, and there is no GET for MWI state in this group, so verify on the device's indicator. **Unverified:** for `create-mwi`; inferred from the spec, which publishes no GET.

---

## 9. Common Use Cases

> **Executable path:** run these flows with `wxcli call-controls` (the [CLI Examples](#cli-examples) section — including the same Hold/Consult/Transfer and Park/Retrieve patterns) or the endpoints in the [Raw HTTP Reference](#raw-http-reference-all-call-control-endpoints). For a Service App acting on another member, swap `/telephony/calls/{action}` for `/telephony/calls/members/{memberId}/{action}` and drop `lineOwnerId` (§5). The Python below shows the same call sequence using `api.session.rest_*()` raw HTTP calls.

### Click-to-Dial from CRM
```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"

# Place a call from the CRM contact page
result = api.session.rest_post(f"{BASE}/telephony/calls/dial", json={"destination": "+12223334444"})
print(f"Call initiated: {result['callId']}")
```

### Agent Dashboard: List Active Calls
```python
result = api.session.rest_get(f"{BASE}/telephony/calls")
for call in result.get("calls", []):
    remote = call.get("remoteParty", {})
    print(f"{call['id']} | {call['state']} | {remote.get('name')} ({remote.get('number')})")
```

### Consultative Transfer
```python
# Agent has two calls: original caller and the transfer target
# Transfer them together
api.session.rest_post(f"{BASE}/telephony/calls/transfer", json={
    "callId1": original_call_id,
    "callId2": consult_call_id
})
```

### Hold, Consult, Transfer Pattern
```python
# 1. Put caller on hold
api.session.rest_post(f"{BASE}/telephony/calls/hold", json={"callId": caller_call_id})

# 2. Dial the transfer target
consult = api.session.rest_post(f"{BASE}/telephony/calls/dial", json={"destination": "+15551234567"})

# 3. After speaking with transfer target, transfer both calls
api.session.rest_post(f"{BASE}/telephony/calls/transfer", json={
    "callId1": caller_call_id,
    "callId2": consult["callId"]
})
```

### Park and Retrieve
```python
# Park the call
parked = api.session.rest_post(f"{BASE}/telephony/calls/park", json={"callId": call_id})
park_number = parked.get("parkedAgainst", {}).get("number")
print(f"Parked against: {park_number}")

# Later, retrieve it (from any device)
retrieved = api.session.rest_post(f"{BASE}/telephony/calls/retrieve", json={"destination": park_number})
```

### Call Recording Control
```python
# Start recording (user must have "On Demand" recording mode)
api.session.rest_post(f"{BASE}/telephony/calls/startRecording", json={"callId": call_id})

# Pause for sensitive info (credit card, SSN)
api.session.rest_post(f"{BASE}/telephony/calls/pauseRecording", json={"callId": call_id})

# Resume
api.session.rest_post(f"{BASE}/telephony/calls/resumeRecording", json={"callId": call_id})

# Stop
api.session.rest_post(f"{BASE}/telephony/calls/stopRecording", json={"callId": call_id})
```

### Service App: Control Calls for a User
```python
# Using admin/service app credentials with spark-admin:calls_write
member_id = "person-uuid-here"

# Dial on behalf of a user
result = api.session.rest_post(f"{BASE}/telephony/calls/members/{member_id}/dial", json={
    "destination": "+12223334444"
})
```

---

## 10. Key Gotchas

1. **3rd Party Call Control only** -- These APIs do not work with Webex app's native calling. They are for building external call control applications.

2. **Multi-Tenant only** -- Not applicable for UCM or Dedicated Instance users.

3. **Service Apps cannot use the user-level call endpoints** -- Service Apps must use the members path (`POST /v1/telephony/calls/members/{memberId}/{action}`; CLI: the `wxcli call-controls *-members` commands) instead. Since the post-2026-09-21 spec every call action has a member form, so this no longer limits what a Service App can do (§5; **Unverified** live). The `-me` commands are *not* the Service App path — like the bare ones, they act on the token's own user ([Choosing a Scope](#choosing-a-scope)).

4. **`callId` vs `id`** -- The API returns `id` in direct call responses but `callId` in webhook events. Always use `callId` when passing the identifier to action endpoints.

5. **Click-to-Dial personality transition** -- A dial request starts with `personality: clickToDial` while alerting the user's devices. Once the user answers, it transitions to `personality: originator`.

6. **Transfer restrictions** -- Unanswered incoming calls cannot be transferred. Use `divert` for unanswered calls.

7. **`lineOwnerId` parameter** -- Present on nearly all bare and `/members/me/` endpoints, and on none of the `/members/{memberId}/` ones. Used when the API caller has a secondary line belonging to another user, workspace, or virtual line on their device. It is **not** a way for a Service App to pick whose call to act on — that is the `memberId` path segment.

8. **Recording mode dependency** -- Start/Stop Recording only work when the user's recording mode is "On Demand". Pause/Resume Recording work with both "On Demand" and "Always with Pause/Resume".

9. **Mute capability check** -- Always check `muteCapable` in call details before calling `mute` or `unmute`. Not all calls support it.

10. **Call history limit** -- List Call History returns a maximum of 20 records per type (placed/missed/received).

---

## See Also

- [`contact-center-core.md`](contact-center-core.md) — read this if the wrap-up
  reason you are trying to set belongs to a WxCC task rather than a Calling call;
  the two surfaces share a word and share nothing else, and picking the wrong one
  fails with a 403 on scope rather than anything that names the mistake.
- [`call-features-additional.md`](call-features-additional.md) — go here to *define*
  the wrap-up reason names that §6 applies: Customer Assist keeps the org-level list
  and the per-queue assignment, and §6 sends those names, not IDs.
- [`location-recording-advanced.md`](location-recording-advanced.md) — its §3 has the
  conference data model (`ConferenceDetails`, `ConferenceTypeEnum`) that §7's
  commands return and switch between, and its §4 configures which supervisors may
  monitor which agents — the permission side of §7's barge-in / monitor / coach modes.

- **[webhooks-events.md](webhooks-events.md)** — Real-time call event notifications via webhooks. Webhook call event payloads share the same fields as the `TelephonyCall` object documented here (§4 Data Models); use webhooks for event-driven call control rather than polling List Calls.
- **[person-call-settings-media.md](person-call-settings-media.md)** — Call recording configuration (recording mode, compliance announcements). Recording mode determines which recording control actions are available in this API.
