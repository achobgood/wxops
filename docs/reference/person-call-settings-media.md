<!-- Updated by playbook session 2026-03-18 -->
# Person Call Settings -- Voicemail, Caller ID, Privacy & Recording

Reference for per-person (also virtual line and workspace) call settings covering voicemail, caller ID, anonymous call rejection, privacy, barge-in, call recording, call intercept, monitoring, push-to-talk, and music on hold.

All APIs in this group follow the same structural pattern: they extend `PersonSettingsApiChild`, which builds REST endpoints using the formula `people/{person_id}/features/{feature}` for persons (with alternate URL patterns for workspaces, virtual lines, and locations). Each sub-API exposes a `read()` and `configure()` method pair, sometimes with additional action methods.

## Sources

- wxc_sdk v1.30.0 (PersonSettingsApi)
- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Person Call Settings APIs

## Required Scopes

| Feature | Read Scope | Write Scope | Notes |
|---------|-----------|------------|-------|
| Voicemail | `spark-admin:people_read` | `spark-admin:people_write` | Self: `spark:people_read` / `spark:people_write` |
| Voicemail Passcode | `spark-admin:telephony_config_write` | `spark-admin:telephony_config_write` | Write-only; uses `telephony/config/people` path |
| Voicemail PIN Reset | `spark-admin:people_write` | `spark-admin:people_write` | Write-only action |
| Caller ID | `spark-admin:people_read` | `spark-admin:people_write` | Self: `spark:people_read` / `spark:people_write` |
| Agent Caller ID | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` | Available caller IDs uses `spark-admin:people_read` |
| Anonymous Call Rejection | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` | Workspace-only admin endpoint. No admin-level `/people/{id}` path exists; self-service via `/me` only.  |
| Privacy | `spark-admin:people_read` | `spark-admin:people_write` | |
| Barge-In | `spark-admin:people_read` | `spark-admin:people_write` | Self: `spark:people_read` / `spark:people_write` |
| Call Recording | `spark-admin:people_read` | `spark-admin:people_write` | |
| Call Intercept | `spark-admin:people_read` | `spark-admin:people_write` | Greeting upload: self `spark:people_write` also works |
| Monitoring | `spark-admin:people_read` | `spark-admin:people_write` | |
| Push-to-Talk | `spark-admin:people_read` | `spark-admin:people_write` | |
| Music on Hold | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` | Uses `telephony/config/people` path |

---

## Table of Contents

1. [Voicemail](#1-voicemail)
2. [Caller ID](#2-caller-id)
3. [Agent Caller ID](#3-agent-caller-id)
4. [Anonymous Call Rejection](#4-anonymous-call-rejection)
5. [Privacy](#5-privacy)
6. [Barge-In](#6-barge-in)
7. [Call Recording](#7-call-recording)
8. [Call Intercept](#8-call-intercept)
9. [Monitoring](#9-monitoring)
10. [Push-to-Talk](#10-push-to-talk)
11. [Music on Hold](#11-music-on-hold)
12. [Common Patterns](#12-common-patterns)

---

## 1. Voicemail

**API class:** `VoicemailApi`
**Feature key:** `voicemail`
**Source:** `wxc_sdk/person_settings/voicemail.py`

### Data Models

#### `VoicemailSettings`

Top-level settings object returned by `read()` and passed to `configure()`.

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Voicemail is enabled or disabled |
| `send_all_calls` | `VoicemailEnabled` | Settings for sending all calls to voicemail |
| `send_busy_calls` | `VoicemailEnabledWithGreeting` | Settings for sending calls to voicemail when line is busy |
| `send_unanswered_calls` | `UnansweredCalls` | Settings for calls sent to voicemail when unanswered |
| `notifications` | `VoicemailNotifications` | Settings for new voicemail notifications |
| `transfer_to_number` | `VoicemailTransferToNumber` | Transfer to a different number by pressing 0 |
| `email_copy_of_message` | `VoicemailCopyOfMessage` | Send copy of voicemail audio via email |
| `message_storage` | `VoicemailMessageStorage` | Message storage settings (internal vs. external) |
| `fax_message` | `VoicemailFax` | Fax message settings |
| `voice_message_forwarding_enabled` | `bool` | Read-only; excluded from updates |

#### `VoicemailEnabledWithGreeting` (extends `VoicemailEnabled`)

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Whether this condition is active |
| `greeting` | `Greeting` | `DEFAULT` or `CUSTOM` (.wav file) |
| `greeting_uploaded` | `bool` | Read-only; indicates custom greeting exists |
| `audio_file` | `MediaFile` | Details of the custom audio file |

#### `UnansweredCalls` (extends `VoicemailEnabledWithGreeting`)

| Field | Type | Description |
|-------|------|-------------|
| `number_of_rings` | `int` | Rings before unanswered call goes to voicemail |
| `system_max_number_of_rings` | `int` | Read-only; system-wide max for number_of_rings |

#### Default Settings

`VoicemailSettings.default()` returns:

```python
VoicemailSettings(
    enabled=True,
    send_all_calls=VoicemailEnabled(enabled=False),
    send_busy_calls=VoicemailEnabledWithGreeting(enabled=False, greeting=Greeting.default),
    send_unanswered_calls=UnansweredCalls(enabled=True, greeting=Greeting.default, number_of_rings=3),
    notifications=VoicemailNotifications(enabled=False),
    transfer_to_number=VoicemailTransferToNumber(enabled=False),
    email_copy_of_message=VoicemailCopyOfMessage(enabled=False),
    message_storage=VoicemailMessageStorage(mwi_enabled=True, storage_type=StorageType.internal),
    fax_message=VoicemailFax(enabled=False),
    voice_message_forwarding_enabled=False,
)
```

### Methods

#### `read`

```python
VoicemailApi.read(entity_id: str, org_id: str = None) -> VoicemailSettings
```

Retrieve voicemail settings for a person, virtual line, or workspace.

- **Scopes (read):** `spark-admin:people_read` (admin) or `spark:people_read` (self)

#### `configure`

```python
VoicemailApi.configure(entity_id: str, settings: VoicemailSettings, org_id: str = None)
```

Update voicemail settings. The `settings.update()` method automatically strips read-only fields (`greeting_uploaded`, `system_max_number_of_rings`, `voice_message_forwarding_enabled`) before sending.

- **Scopes (write):** `spark-admin:people_write` (admin) or `spark:people_write` (self)

#### `configure_busy_greeting`

```python
VoicemailApi.configure_busy_greeting(
    entity_id: str,
    content: Union[BufferedReader, str],
    upload_as: str = None,
    org_id: str = None,
)
```

Upload a custom `.wav` greeting for the busy condition. Uses multipart/form-data with `audio/wav` content type. Endpoint: `actions/uploadBusyGreeting/invoke`.

- `content` can be a file path (str) or an open binary reader.
- `upload_as` is required if `content` is a reader (must be a `.wav` filename).

#### `configure_no_answer_greeting`

```python
VoicemailApi.configure_no_answer_greeting(
    entity_id: str,
    content: Union[BufferedReader, str],
    upload_as: str = None,
    org_id: str = None,
)
```

Same as above but for the no-answer condition. Endpoint: `actions/uploadNoAnswerGreeting/invoke`.

#### `modify_passcode`

```python
VoicemailApi.modify_passcode(entity_id: str, passcode: str, org_id: str = None)
```

Set a new voicemail passcode. Passcode length must be 6-30 characters.

- **Scopes:** `spark-admin:telephony_config_write`
- **Note:** Uses a different URL pattern: `telephony/config/people/{person_id}/voicemail/passcode`

#### `reset_pin`

```python
VoicemailApi.reset_pin(entity_id: str, org_id: str = None)
```

Reset the voicemail PIN. Endpoint: `actions/resetPin/invoke` (POST).

- **Scopes:** `spark-admin:people_write`

### Usage Example (from `examples/modify_voicemail.py`)

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi()
vm = api.person_settings.voicemail

# Read current settings
vm_settings = vm.read(person_id=person_id)

# Modify number of rings
vm_settings.send_unanswered_calls.number_of_rings = 6

# Write back
vm.configure(person_id, settings=vm_settings)
```

The example script reads a CSV of usernames, filters to calling users, and bulk-updates ring count using `ThreadPoolExecutor`.

### CLI Examples

```bash
# Read voicemail settings for a person
wxcli user-settings show-voicemail PERSON_ID

# Read voicemail settings as JSON
wxcli user-settings show-voicemail PERSON_ID -o json

# Enable voicemail for a person
wxcli user-settings update-voicemail PERSON_ID --enabled

# Disable voicemail for a person
wxcli user-settings update-voicemail PERSON_ID --no-enabled

# Update voicemail with full settings (nested objects require --json-body)
wxcli user-settings update-voicemail PERSON_ID --json-body '{
  "enabled": true,
  "sendAllCalls": {"enabled": false},
  "sendBusyCalls": {"enabled": false, "greeting": "DEFAULT"},
  "sendUnansweredCalls": {"enabled": true, "greeting": "DEFAULT", "numberOfRings": 6},
  "notifications": {"enabled": false},
  "transferToNumber": {"enabled": false},
  "emailCopyOfMessage": {"enabled": false},
  "messageStorage": {"mwiEnabled": true, "storageType": "INTERNAL"},
  "faxMessage": {"enabled": false}
}'

# Upload a custom busy voicemail greeting
wxcli user-settings configure-busy-voicemail PERSON_ID

# Upload a custom no-answer voicemail greeting
wxcli user-settings configure-no-answer PERSON_ID

# Reset voicemail PIN
wxcli user-settings reset-voicemail-pin PERSON_ID

# Set voicemail passcode
wxcli user-settings update-passcode PERSON_ID --passcode "123456"
```

### Raw HTTP

#### Read Voicemail Settings

```
GET https://webexapis.com/v1/people/{personId}/features/voicemail
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/voicemail")
# Response:
# {
#   "enabled": true,
#   "sendAllCalls": {"enabled": false},
#   "sendBusyCalls": {"enabled": false, "greeting": "DEFAULT", "greetingUploaded": false},
#   "sendUnansweredCalls": {"enabled": true, "greeting": "DEFAULT", "numberOfRings": 3, "systemMaxNumberOfRings": 20},
#   "notifications": {"enabled": false, "destination": ""},
#   "transferToNumber": {"enabled": false, "destination": ""},
#   "emailCopyOfMessage": {"enabled": false, "emailId": ""},
#   "messageStorage": {"mwiEnabled": true, "storageType": "INTERNAL"},
#   "faxMessage": {"enabled": false},
#   "voiceMessageForwardingEnabled": false
# }
```

#### Configure Voicemail Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/voicemail
```

```python
body = {
    "enabled": True,
    "sendAllCalls": {"enabled": False},
    "sendBusyCalls": {"enabled": False, "greeting": "DEFAULT"},
    "sendUnansweredCalls": {"enabled": True, "greeting": "DEFAULT", "numberOfRings": 6},
    "notifications": {"enabled": False},
    "transferToNumber": {"enabled": False},
    "emailCopyOfMessage": {"enabled": False},
    "messageStorage": {"mwiEnabled": True, "storageType": "INTERNAL"},
    "faxMessage": {"enabled": False}
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/voicemail", json=body)
```

#### Upload Busy Greeting

```
POST https://webexapis.com/v1/people/{personId}/features/voicemail/actions/uploadBusyGreeting/invoke
```

Multipart/form-data with `.wav` file. Uses `rest_post` with file upload.

#### Upload No-Answer Greeting

```
POST https://webexapis.com/v1/people/{personId}/features/voicemail/actions/uploadNoAnswerGreeting/invoke
```

Multipart/form-data with `.wav` file. Uses `rest_post` with file upload.

#### Reset Voicemail PIN

```
POST https://webexapis.com/v1/people/{personId}/features/voicemail/actions/resetPin/invoke
```

```python
api.session.rest_post(f"{BASE}/people/{person_id}/features/voicemail/actions/resetPin/invoke")
```

#### Modify Voicemail Passcode

```
PUT https://webexapis.com/v1/telephony/config/people/{personId}/voicemail/passcode
```

```python
body = {"passcode": "123456"}
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/voicemail/passcode", json=body)
```

**Gotchas:**
- Exclude read-only fields from PUT body: `greetingUploaded`, `systemMaxNumberOfRings`, `voiceMessageForwardingEnabled`.
- Passcode endpoint uses `telephony/config/people` path (not `people/{id}/features`). Requires `spark-admin:telephony_config_write` scope.
- Greeting uploads use POST with multipart/form-data, not JSON.

---

## 2. Caller ID

**API class:** `CallerIdApi`
**Feature key:** `callerId`
**Source:** `wxc_sdk/person_settings/caller_id.py`

### Data Models

#### `CallerIdSelectedType` (Enum)

| Value | Description |
|-------|-------------|
| `DIRECT_LINE` | Show the caller's direct line number and/or extension |
| `LOCATION_NUMBER` | Show the main number for the location |
| `MOBILE_NUMBER` | Show the mobile number for this person |
| `CUSTOM` | Show the value from `custom_number` |

#### `ExternalCallerIdNamePolicy` (Enum)

| Value | Description |
|-------|-------------|
| `DIRECT_LINE` | Show the caller's direct line name |
| `LOCATION` | Show the site name for the location |
| `OTHER` | Show the value from `custom_external_caller_id_name` |

#### `CallerId`

| Field | Type | Description |
|-------|------|-------------|
| `caller_id_types` | `list[CallerIdSelectedType]` | Read-only. Allowed types for `selected`. (JSON alias: `types`) |
| `selected` | `CallerIdSelectedType` | Which type of outgoing caller ID is used (number portion) |
| `direct_number` | `str` | Direct line number (shown if `DIRECT_LINE` selected) |
| `extension_number` | `str` | Extension number (shown if `DIRECT_LINE` selected) |
| `location_number` | `str` | Location number (shown if `LOCATION_NUMBER` selected) |
| `mobile_number` | `str` | Mobile number (shown if `MOBILE_NUMBER` selected) |
| `toll_free_location_number` | `bool` | Indicates if the location number is toll-free |
| `custom_number` | `str` | Custom number (shown if `CUSTOM` selected). Must be from the entity's location or a matching location. |
| `first_name` | `str` | **Deprecated.** Use `direct_line_caller_id_name` and `dial_by_first_name` instead. |
| `last_name` | `str` | **Deprecated.** Use `direct_line_caller_id_name` and `dial_by_last_name` instead. |
| `block_in_forward_calls_enabled` | `bool` | Block identity when receiving transferred/forwarded calls |
| `external_caller_id_name_policy` | `ExternalCallerIdNamePolicy` | Which external caller ID name policy is used |
| `custom_external_caller_id_name` | `str` | Custom name shown when policy is `OTHER` |
| `location_external_caller_id_name` | `str` | Read-only. Location's caller ID name. |
| `additional_external_caller_id_direct_line_enabled` | `bool` | Set user's main number as additional external caller ID |
| `additional_external_caller_id_location_number_enabled` | `bool` | Set location main number as additional external caller ID |
| `additional_external_caller_id_custom_number` | `str` | Set any number across location as additional external caller ID |
| `display_name` | `str` | **Deprecated.** Use `direct_line_caller_id_name` and `dial_by_name` instead. |
| `display_detail` | `str` | **Deprecated.** Use `direct_line_caller_id_name` and `dial_by_name` instead. |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | Settings for direct line caller ID name |
| `dial_by_name` | `str` | Name used for dial-by-name functions |
| `dial_by_first_name` | `str` | First name for dial-by-name |
| `dial_by_last_name` | `str` | Last name for dial-by-name |

**Note:** Number fields (`direct_number`, `location_number`, `mobile_number`, `custom_number`) are validated through the `plus1` E.164 normalizer.

### Methods

#### `read`

```python
CallerIdApi.read(entity_id: str, org_id: str = None) -> CallerId
```

- **Scopes:** `spark-admin:people_read` or `spark:people_read` (self)

#### `configure` (parameter-based)

```python
CallerIdApi.configure(
    entity_id: str,
    org_id: str = None,
    selected: CallerIdSelectedType = None,
    custom_number: str = None,
    first_name: str = None,
    last_name: str = None,
    external_caller_id_name_policy: ExternalCallerIdNamePolicy = None,
    custom_external_caller_id_name: str = None,
)
```

Update caller ID using individual parameters. Only non-None parameters are sent.

- **Scopes:** `spark-admin:people_write` or `spark:people_write` (self)

#### `configure_settings` (object-based)

```python
CallerIdApi.configure_settings(entity_id: str, settings: CallerId, org_id: str = None)
```

Update caller ID by passing a full `CallerId` object. Uses `settings.update()` which limits to `fields_for_update` and excludes read-only fields.

```python
# Example: enable block-in-forward-calls
caller_id_settings = api.person_settings.caller_id.read(entity_id=person_id)
caller_id_settings.block_in_forward_calls_enabled = True
api.person_settings.caller_id.configure_settings(entity_id=person_id, settings=caller_id_settings)
```

### CLI Examples

```bash
# Read caller ID settings for a person
wxcli user-settings list PERSON_ID

# Read caller ID settings as JSON
wxcli user-settings list PERSON_ID -o json

# Set caller ID to direct line
wxcli user-settings update-caller-id-features PERSON_ID --selected DIRECT_LINE

# Set caller ID to location number
wxcli user-settings update-caller-id-features PERSON_ID --selected LOCATION_NUMBER

# Set caller ID to a custom number
wxcli user-settings update-caller-id-features PERSON_ID --selected CUSTOM --custom-number "+12125559999"

# Set external caller ID name policy to location name
wxcli user-settings update-caller-id-features PERSON_ID --external-caller-id-name-policy LOCATION

# Set external caller ID name policy to custom name
wxcli user-settings update-caller-id-features PERSON_ID \
  --external-caller-id-name-policy OTHER \
  --custom-external-caller-id-name "Sales Department"

# Block identity when receiving forwarded calls
wxcli user-settings update-caller-id-features PERSON_ID --block-in-forward-calls-enabled

# Set dial-by-name fields
wxcli user-settings update-caller-id-features PERSON_ID \
  --dial-by-first-name "Jane" --dial-by-last-name "Doe"
```

### Raw HTTP

#### Read Caller ID Settings

```
GET https://webexapis.com/v1/people/{personId}/features/callerId
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/callerId")
# Response:
# {
#   "types": ["DIRECT_LINE", "LOCATION_NUMBER", "CUSTOM"],
#   "selected": "DIRECT_LINE",
#   "directNumber": "+12125551234",
#   "extensionNumber": "1234",
#   "locationNumber": "+12125550000",
#   "blockInForwardCallsEnabled": false,
#   "externalCallerIdNamePolicy": "DIRECT_LINE",
#   "locationExternalCallerIdName": "Main Office",
#   "additionalExternalCallerIdDirectLineEnabled": false,
#   "additionalExternalCallerIdLocationNumberEnabled": false,
#   "dialByFirstName": "Jane",
#   "dialByLastName": "Doe"
# }
```

#### Configure Caller ID Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/callerId
```

```python
body = {
    "selected": "DIRECT_LINE",
    "blockInForwardCallsEnabled": True,
    "externalCallerIdNamePolicy": "DIRECT_LINE"
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/callerId", json=body)
```

**Gotchas:**
- `types` is read-only (returned as JSON key `types`); do not include in PUT body.
- `locationExternalCallerIdName` is read-only.
- `selected` values: `"DIRECT_LINE"`, `"LOCATION_NUMBER"`, `"MOBILE_NUMBER"`, `"CUSTOM"`.
- `externalCallerIdNamePolicy` values: `"DIRECT_LINE"`, `"LOCATION"`, `"OTHER"`.
- When `selected` is `"CUSTOM"`, include `customNumber` in the body.

---

## 3. Agent Caller ID

**API class:** `AgentCallerIdApi`
**Feature key:** `agent`
**Source:** `wxc_sdk/person_settings/agent_caller_id.py`

Allows agents to set their outgoing caller ID to a call queue or hunt group instead of their personal caller ID.

### Data Models

#### `AvailableCallerIdType` (Enum)

| Value | Description |
|-------|-------------|
| `CALL_QUEUE` | A call queue has been selected |
| `HUNT_GROUP` | A hunt group has been selected |

#### `AgentCallerId`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Call queue or hunt group unique identifier |
| `type` | `AvailableCallerIdType` | `CALL_QUEUE` or `HUNT_GROUP` |
| `name` | `str` | Call queue or hunt group name |
| `phone_number` | `str` | Phone number (if set) |
| `extension` | `str` | Extension number (if set) |

#### `QueueCallerId`

Internal model used for the read response. Contains:

| Field | Type | Description |
|-------|------|-------------|
| `queue_caller_id_enabled` | `bool` | `true` when using the selected queue for caller ID; `false` for agent's own |
| `selected_queue` | `AgentCallerId` | The selected queue/hunt group (empty when disabled) |

### Methods

#### `available_caller_ids`

```python
AgentCallerIdApi.available_caller_ids(entity_id: str, org_id: str = None) -> list[AgentCallerId]
```

Get call queues and hunt groups available for caller ID use by this agent.

- **Scopes:** `spark-admin:people_read`
- **Endpoint:** `telephony/config/people/{entity_id}/agent/availableCallerIds`

#### `read`

```python
AgentCallerIdApi.read(entity_id: str) -> AgentCallerId
```

Retrieve the agent's currently selected caller ID.

- **Scopes:** `spark-admin:telephony_config_read`
- **Endpoint:** `telephony/config/people/{entity_id}/agent/callerId`

#### `configure`

```python
AgentCallerIdApi.configure(entity_id: str, selected_caller_id: str = None)
```

Set the agent's caller ID to a specific call queue or hunt group. Pass `None` to revert to the agent's own caller ID.

- **Scopes:** `spark-admin:telephony_config_write`
- Body: `{"selectedCallerId": "<id_or_null>"}`

### CLI Examples

```bash
# List available caller IDs (call queues/hunt groups) for an agent
wxcli user-settings list-available-caller-ids PERSON_ID

# Read the agent's currently selected caller ID
wxcli user-settings show-caller-id PERSON_ID

# Read agent caller ID as JSON
wxcli user-settings show-caller-id PERSON_ID -o json

# Set agent caller ID to a specific call queue
wxcli user-settings update-caller-id-agent PERSON_ID --selected-caller-id QUEUE_ID

# Revert agent caller ID to the agent's own caller ID
wxcli user-settings update-caller-id-agent PERSON_ID --json-body '{"selectedCallerId": null}'
```

### Raw HTTP

> **Note:** Agent Caller ID uses the `telephony/config/people` path, not `people/{id}/features`.

#### List Available Agent Caller IDs

```
GET https://webexapis.com/v1/telephony/config/people/{personId}/agent/availableCallerIds
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/agent/availableCallerIds")
# Response:
# {
#   "availableCallerIds": [
#     {"id": "queue-id", "type": "CALL_QUEUE", "name": "Sales Queue", "phoneNumber": "+12125551234", "extension": "8001"},
#     {"id": "hg-id", "type": "HUNT_GROUP", "name": "Support HG", "extension": "8002"}
#   ]
# }
```

#### Read Agent Caller ID

```
GET https://webexapis.com/v1/telephony/config/people/{personId}/agent/callerId
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/agent/callerId")
# Response:
# {
#   "queueCallerIdEnabled": true,
#   "selectedQueue": {"id": "queue-id", "type": "CALL_QUEUE", "name": "Sales Queue", ...}
# }
```

#### Configure Agent Caller ID

```
PUT https://webexapis.com/v1/telephony/config/people/{personId}/agent/callerId
```

```python
body = {"selectedCallerId": "queue-id"}
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/agent/callerId", json=body)

# To revert to the agent's own caller ID:
body = {"selectedCallerId": None}
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/agent/callerId", json=body)
```

**Gotchas:**
- Uses `telephony_config_read`/`write` scopes (not `people_read`/`write`).
- Pass `null` for `selectedCallerId` to revert to agent's own caller ID.

---

## 4. Anonymous Call Rejection

**API class:** `AnonCallsApi`
**Feature key:** `anonymousCallReject`
**Source:** `wxc_sdk/person_settings/anon_calls.py`

When enabled, blocks all incoming calls from unidentified or blocked caller IDs.

> **Note from source:** This API is documented as "only available for professional licensed workspaces," and live testing confirms this. The OpenAPI spec only defines endpoints for `/me` (self) and `/workspaces/{id}` -- no admin-level `/people/{id}` endpoint exists. Attempting `GET /v1/telephony/config/people/{personId}/anonymousCallReject` returns 404. The workspace endpoint requires a Professional-licensed workspace (error 25409 returned for non-professional workspaces). The SDK's `PersonSettingsApiChild` base class constructs the person URL pattern, but the API does not accept it.

### Methods

#### `read`

```python
AnonCallsApi.read(entity_id: str, org_id: str = None) -> bool
```

Returns a simple boolean: `True` if anonymous call rejection is enabled.

- **Scopes:** `spark-admin:workspaces_read` (workspace admin), `spark:people_read` (self via `/me`). No admin-level person endpoint exists.

#### `configure`

```python
AnonCallsApi.configure(entity_id: str, enabled: bool, org_id: str = None)
```

Enable or disable anonymous call rejection.

- Body: `{"enabled": true|false}`

### CLI Examples

```bash
# Read anonymous call rejection settings for a workspace
# Note: In wxcli, anonymous call rejection is under workspace-settings, not user-settings.
# The API is documented as "only available for professional licensed workspaces."
wxcli workspace-settings show-anonymous-call-reject WORKSPACE_ID

# Enable anonymous call rejection for a workspace
wxcli workspace-settings update-anonymous-call-reject WORKSPACE_ID --enabled

# Disable anonymous call rejection for a workspace
wxcli workspace-settings update-anonymous-call-reject WORKSPACE_ID --no-enabled
```

### Raw HTTP

> **WARNING: No admin-level person endpoint exists.** The path `people/{personId}/features/anonymousCallReject` returns 404. Only the workspace admin path and the self-service `/me` path work.

#### Read Anonymous Call Rejection (Workspace — admin token)

```
GET https://webexapis.com/v1/telephony/config/workspaces/{workspaceId}/anonymousCallReject
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/workspaces/{workspace_id}/anonymousCallReject")
# Response:
# {
#   "enabled": true
# }
```

#### Read Anonymous Call Rejection (Self — user token, calling-licensed user)

```
GET https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject
```

```python
# Requires calling-licensed user token with spark:telephony_config_read scope
result = api.session.rest_get(f"{BASE}/telephony/config/people/me/settings/anonymousCallReject")
# Response:
# {
#   "enabled": true
# }
```

#### Configure Anonymous Call Rejection (Workspace — admin token)

```
PUT https://webexapis.com/v1/telephony/config/workspaces/{workspaceId}/anonymousCallReject
```

```python
body = {"enabled": True}
api.session.rest_put(f"{BASE}/telephony/config/workspaces/{workspace_id}/anonymousCallReject", json=body)
```

#### Configure Anonymous Call Rejection (Self — user token, calling-licensed user)

```
PUT https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject
```

```python
# Requires calling-licensed user token with spark:telephony_config_write scope
body = {"enabled": True}
api.session.rest_put(f"{BASE}/telephony/config/people/me/settings/anonymousCallReject", json=body)
```

---

## 5. Privacy

**API class:** `PrivacyApi`
**Feature key:** `privacy`
**Source:** `wxc_sdk/person_settings/privacy.py`

Controls whether the entity's line can be monitored by others and whether they are reachable via Auto Attendant services.

### Data Model

#### `Privacy`

| Field | Type | Description |
|-------|------|-------------|
| `aa_extension_dialing_enabled` | `bool` | Enable auto attendant extension dialing |
| `aa_naming_dialing_enabled` | `bool` | Enable auto attendant dialing by first or last name |
| `enable_phone_status_directory_privacy` | `bool` | Enable phone status directory privacy |
| `enable_phone_status_pickup_barge_in_privacy` | `bool` | When `true`, only people in `monitoring_agents` can pick up the call or barge in by dialing the extension |
| `monitoring_agents` | `list[Union[str, PersonPlaceAgent]]` | List of people allowed to monitor. For updates, can pass IDs (strings) directly. |

### Methods

#### `read`

```python
PrivacyApi.read(entity_id: str, org_id: str = None) -> Privacy
```

- **Scopes:** `spark-admin:people_read`

#### `configure`

```python
PrivacyApi.configure(entity_id: str, settings: Privacy, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write`
- When updating `monitoring_agents`, the SDK extracts IDs from `PersonPlaceAgent` objects (using `agent_id`) or passes strings directly.

### CLI Examples

```bash
# Read privacy settings for a person
wxcli user-settings list-privacy PERSON_ID

# Read privacy settings as JSON
wxcli user-settings list-privacy PERSON_ID -o json

# Enable AA extension dialing and directory privacy
wxcli user-settings update-privacy PERSON_ID \
  --aa-extension-dialing-enabled \
  --enable-phone-status-directory-privacy

# Disable AA naming dialing
wxcli user-settings update-privacy PERSON_ID --no-aa-naming-dialing-enabled

# Enable pickup/barge-in privacy
wxcli user-settings update-privacy PERSON_ID --enable-phone-status-pickup-barge-in-privacy

# Update privacy with monitoring agents list (requires --json-body)
wxcli user-settings update-privacy PERSON_ID --json-body '{
  "aaExtensionDialingEnabled": true,
  "aaNamingDialingEnabled": true,
  "enablePhoneStatusDirectoryPrivacy": true,
  "enablePhoneStatusPickupBargeInPrivacy": true,
  "monitoringAgents": ["PERSON_ID_1", "PERSON_ID_2"]
}'
```

### Raw HTTP

#### Read Privacy Settings

```
GET https://webexapis.com/v1/people/{personId}/features/privacy
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/privacy")
# Response:
# {
#   "aaExtensionDialingEnabled": true,
#   "aaNamingDialingEnabled": true,
#   "enablePhoneStatusDirectoryPrivacy": false,
#   "enablePhoneStatusPickupBargeInPrivacy": false,
#   "monitoringAgents": [
#     {"id": "person-id", "firstName": "Jane", "lastName": "Doe", ...}
#   ]
# }
```

#### Configure Privacy Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/privacy
```

```python
body = {
    "aaExtensionDialingEnabled": True,
    "aaNamingDialingEnabled": True,
    "enablePhoneStatusDirectoryPrivacy": True,
    "enablePhoneStatusPickupBargeInPrivacy": False,
    "monitoringAgents": ["person-id-1", "person-id-2"]
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/privacy", json=body)
```

**Gotchas:**
- `monitoringAgents` accepts a flat list of person IDs for updates, even though reads return full agent objects.
- Uses `people/{id}/features/privacy` path (not `telephony/config/people`). <!-- Updated by playbook session 2026-03-18 -->

---

## 6. Barge-In

**API class:** `BargeApi`
**Feature key:** `bargeIn`
**Source:** `wxc_sdk/person_settings/barge.py`

Enables the use of a Feature Access Code (FAC) to answer a call directed to another subscriber, or barge-in on an already-answered call. Works across locations.

### Data Model

#### `BargeSettings`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Whether barge-in is enabled (required, not optional) |
| `tone_enabled` | `bool` | Whether a stutter dial tone plays when someone barges in (required, not optional) |

### Methods

#### `read`

```python
BargeApi.read(entity_id: str, org_id: str = None) -> BargeSettings
```

- **Scopes:** `spark-admin:people_read` or `spark:people_read` (self)

#### `configure`

```python
BargeApi.configure(entity_id: str, barge_settings: BargeSettings, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write` or `spark:people_write` (self)
- Serializes the full `BargeSettings` object as JSON body.

### CLI Examples

```bash
# Read barge-in settings for a person
wxcli user-settings show-barge-in PERSON_ID

# Read barge-in settings as JSON
wxcli user-settings show-barge-in PERSON_ID -o json

# Enable barge-in with tone
wxcli user-settings update-barge-in PERSON_ID --enabled --tone-enabled

# Enable barge-in without tone
wxcli user-settings update-barge-in PERSON_ID --enabled --no-tone-enabled

# Disable barge-in entirely
wxcli user-settings update-barge-in PERSON_ID --no-enabled --no-tone-enabled
```

### Raw HTTP

#### Read Barge-In Settings

```
GET https://webexapis.com/v1/people/{personId}/features/bargeIn
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/bargeIn")
# Response:
# {
#   "enabled": true,
#   "toneEnabled": true
# }
```

#### Configure Barge-In Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/bargeIn
```

```python
body = {
    "enabled": True,
    "toneEnabled": True
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/bargeIn", json=body)
```

#### Beta: User Self-Service Barge-In

> **Beta API** — May change without notice.

Users can read/modify their own barge-in settings via user-level OAuth:

- `GET /telephony/config/people/me/settings/bargeIn`
- `PUT /telephony/config/people/me/settings/bargeIn`

The admin-path equivalent at `/people/{personId}/features/bargeIn` remains the stable, non-beta option for admin-managed configuration.

---

## 7. Call Recording

**API class:** `CallRecordingApi`
**Feature key:** `callRecording`
**Source:** `wxc_sdk/person_settings/call_recording.py`

Provides hosted call recording for replay and archival, for quality assurance, security, and training.

### Data Models

#### `Record` (Enum)

| Value | Description |
|-------|-------------|
| `Always` | Recording is always enabled |
| `Never` | Recording is never enabled |
| `On Demand` | Recording is started/stopped manually by user |
| `Always with Pause/Resume` | Always enabled with ability to pause and resume |
| `On Demand with User Initiated Start` | Started manually by user |

#### `NotificationType` (Enum)

| Value | Description |
|-------|-------------|
| `None` | No notification sound when paused/resumed |
| `Beep` | A beep sound plays when paused/resumed |
| `Play Announcement` | A verbal announcement plays when paused/resumed |

#### `NotificationRepeat`

| Field | Type | Description |
|-------|------|-------------|
| `interval` | `int` | Interval in seconds (10-1800) for periodic warning beep |
| `enabled` | `bool` | Whether the ongoing recording tone plays at the interval |

#### `Notification`

| Field | Type | Description |
|-------|------|-------------|
| `notification_type` | `NotificationType` | Type of notification (JSON alias: `type`) |
| `enabled` | `bool` | Whether notification feature is active |

#### `StartStopAnnouncement`

| Field | Type | Description |
|-------|------|-------------|
| `internal_calls_enabled` | `bool` | Play start/stop announcement for internal calls |
| `pstn_calls_enabled` | `bool` | Play start/stop announcement for PSTN calls |

#### `CallRecordingAccessSettings`

| Field | Type | Description |
|-------|------|-------------|
| `view_and_play_recordings_enabled` | `bool` | Person can view and play recordings |
| `download_recordings_enabled` | `bool` | Person can download recordings |
| `delete_recordings_enabled` | `bool` | Person can delete recordings |
| `share_recordings_enabled` | `bool` | Person can share recordings |

#### `PostCallRecordingSettings`

| Field | Type | Description |
|-------|------|-------------|
| `summary_and_action_items_enabled` | `bool` | Undocumented field; present in SDK source (`call_recording.py` line 83) with `# TODO: undocumented, issue 201`  |
| `transcript_enabled` | `bool` | Undocumented field; present in SDK source (`call_recording.py` line 84) with `# TODO: undocumented, issue 201`  |

#### `CallRecordingSetting`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Whether call recording is enabled |
| `record` | `Record` | Which scenario triggers recording |
| `record_voicemail_enabled` | `bool` | Also record voicemail messages |
| `start_stop_announcement_enabled` | `bool` | Play announcement at start/stop |
| `notification` | `Notification` | Pause/resume notification settings |
| `repeat` | `NotificationRepeat` | Periodic beep settings |
| `service_provider` | `str` | Read-only. Service provider name (excluded from updates). |
| `external_group` | `str` | Read-only. Service provider group (excluded from updates). |
| `external_identifier` | `str` | Read-only. Unique identifier at provider (excluded from updates). |
| `start_stop_announcement` | `StartStopAnnouncement` | Separate start/stop per internal vs. PSTN |
| `call_recording_access_settings` | `CallRecordingAccessSettings` | User's access to their own recordings |
| `post_call_recording_settings` | `PostCallRecordingSettings` | Post-call summary/transcript settings |

#### Default Settings

```python
CallRecordingSetting.default()  # Returns:
CallRecordingSetting(
    enabled=False,
    record=Record.never,
    record_voicemail_enabled=False,
    start_stop_announcement_enabled=False,
    notification=Notification(notification_type=NotificationType.none, enabled=False),
    repeat=NotificationRepeat(interval=15, enabled=False),
    start_stop_announcement=StartStopAnnouncement(
        internal_calls_enabled=False,
        pstn_calls_enabled=False,
    ),
)
```

### Methods

#### `read`

```python
CallRecordingApi.read(entity_id: str, org_id: str = None) -> CallRecordingSetting
```

- **Scopes:** `spark-admin:people_read` (Note: the SDK source docstring incorrectly says `people_write` for read; this is a documentation bug in the SDK -- read operations use `people_read` per the consistent pattern across all PersonSettingsApiChild endpoints)

#### `configure`

```python
CallRecordingApi.configure(entity_id: str, recording: CallRecordingSetting, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write`
- **Gotcha:** When `notification.notification_type` is `None` (the enum value), the update method converts it to JSON `null` (the API returns the string `"None"` on reads but expects `null` on writes).
- Read-only fields (`service_provider`, `external_group`, `external_identifier`) are automatically excluded.

### CLI Examples

```bash
# Read call recording settings for a person
wxcli user-settings show-call-recording PERSON_ID

# Read call recording settings as JSON
wxcli user-settings show-call-recording PERSON_ID -o json

# Enable call recording with "Always" mode
wxcli user-settings update-call-recording PERSON_ID --enabled --record "Always"

# Set call recording to "On Demand with User Initiated Start"
wxcli user-settings update-call-recording PERSON_ID --enabled --record "On Demand with User Initiated Start"

# Disable call recording
wxcli user-settings update-call-recording PERSON_ID --no-enabled --record "Never"

# Enable call recording with voicemail recording
wxcli user-settings update-call-recording PERSON_ID --enabled --record "Always" --record-voicemail-enabled

# Full recording config with notifications (requires --json-body)
wxcli user-settings update-call-recording PERSON_ID --json-body '{
  "enabled": true,
  "record": "Always with Pause/Resume",
  "recordVoicemailEnabled": false,
  "startStopAnnouncementEnabled": true,
  "notification": {"type": null, "enabled": false},
  "repeat": {"interval": 15, "enabled": false},
  "startStopAnnouncement": {"internalCallsEnabled": true, "pstnCallsEnabled": true}
}'
```

### Raw HTTP

> **Note:** The CLI uses `people/{id}/features/callRecording`. The user-provided URL pattern `telephony/config/people/{personId}/callRecording` is the wxc_sdk remapped path; the actual raw HTTP endpoint is `people/{id}/features/callRecording`. <!-- Updated by playbook session 2026-03-18 -->

#### Read Call Recording Settings

```
GET https://webexapis.com/v1/people/{personId}/features/callRecording
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/callRecording")
# Response:
# {
#   "enabled": false,
#   "record": "Never",
#   "recordVoicemailEnabled": false,
#   "startStopAnnouncementEnabled": false,
#   "notification": {"type": null, "enabled": false},
#   "repeat": {"interval": 15, "enabled": false},
#   "serviceProvider": "...",
#   "externalGroup": "...",
#   "externalIdentifier": "...",
#   "startStopAnnouncement": {"internalCallsEnabled": false, "pstnCallsEnabled": false},
#   "callRecordingAccessSettings": {
#     "viewAndPlayRecordingsEnabled": true,
#     "downloadRecordingsEnabled": true,
#     "deleteRecordingsEnabled": true,
#     "shareRecordingsEnabled": true
#   }
# }
```

#### Configure Call Recording Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/callRecording
```

```python
body = {
    "enabled": True,
    "record": "Always",
    "recordVoicemailEnabled": False,
    "startStopAnnouncementEnabled": False,
    "notification": {"type": None, "enabled": False},
    "repeat": {"interval": 15, "enabled": False},
    "startStopAnnouncement": {"internalCallsEnabled": False, "pstnCallsEnabled": False}
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/callRecording", json=body)
```

**Gotchas:**
- Exclude read-only fields from PUT body: `serviceProvider`, `externalGroup`, `externalIdentifier`.
- `record` values: `"Always"`, `"Never"`, `"On Demand"`, `"Always with Pause/Resume"`, `"On Demand with User Initiated Start"`.
- `notification.type`: API returns `"None"` as a string on reads but expects JSON `null` on writes. Pass `None` (Python) which serializes to `null`.

---

## 8. Call Intercept

**API class:** `CallInterceptApi`
**Feature key:** `intercept`
**Source:** `wxc_sdk/person_settings/call_intercept.py`

Gracefully takes an entity's phone out of service while providing callers with informative announcements and alternative routing options.

### Data Models

#### `InterceptTypeIncoming` (Enum)

| Value | Description |
|-------|-------------|
| `INTERCEPT_ALL` | All incoming calls are intercepted |
| `ALLOW_ALL` | Incoming calls are not intercepted |

#### `InterceptTypeOutgoing` (Enum)

| Value | Description |
|-------|-------------|
| `INTERCEPT_ALL` | All outgoing calls are intercepted |
| `ALLOW_LOCAL_ONLY` | Only non-local calls are intercepted |

#### `InterceptNumber`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | If true, caller hears this number announced |
| `destination` | `str` | The number the caller hears |

#### `InterceptAnnouncements`

| Field | Type | Description |
|-------|------|-------------|
| `greeting` | `Greeting` | `DEFAULT` or `CUSTOM` |
| `file_name` | `str` | Read-only. Filename of custom greeting (empty string if none uploaded). Excluded from updates. |
| `new_number` | `InterceptNumber` | Announcement about a new number |
| `zero_transfer` | `InterceptNumber` | How the call is handled if 0 is pressed |

#### `InterceptSettingIncoming`

| Field | Type | Description |
|-------|------|-------------|
| `intercept_type` | `InterceptTypeIncoming` | (JSON alias: `type`) |
| `voicemail_enabled` | `bool` | If true, destination is voicemail |
| `announcements` | `InterceptAnnouncements` | Announcement settings |

#### `InterceptSettingOutgoing`

| Field | Type | Description |
|-------|------|-------------|
| `intercept_type` | `InterceptTypeOutgoing` | (JSON alias: `type`) |
| `transfer_enabled` | `bool` | Allow transfer/forwarding for intercepted calls |
| `destination` | `str` | Number to transfer outbound calls to |

#### `InterceptSetting`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Whether call intercept is active |
| `incoming` | `InterceptSettingIncoming` | Incoming call intercept configuration |
| `outgoing` | `InterceptSettingOutgoing` | Outgoing call intercept configuration |

#### Default Settings

```python
InterceptSetting.default()  # Returns:
InterceptSetting(
    enabled=False,
    incoming=InterceptSettingIncoming(
        intercept_type=InterceptTypeIncoming.intercept_all,
        voicemail_enabled=False,
        announcements=InterceptAnnouncements(
            greeting=Greeting.default,
            new_number=InterceptNumber(enabled=False),
            zero_transfer=InterceptNumber(enabled=False),
        ),
    ),
    outgoing=InterceptSettingOutgoing(
        intercept_type=InterceptTypeOutgoing.intercept_all,
        transfer_enabled=False,
    ),
)
```

### Methods

#### `read`

```python
CallInterceptApi.read(entity_id: str, org_id: str = None) -> InterceptSetting
```

- **Scopes:** `spark-admin:people_read`

#### `configure`

```python
CallInterceptApi.configure(entity_id: str, intercept: InterceptSetting, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write`

#### `greeting`

```python
CallInterceptApi.greeting(
    entity_id: str,
    content: Union[BufferedReader, str],
    upload_as: str = None,
    org_id: str = None,
)
```

Upload a custom intercept greeting (`.wav` file). Uses multipart/form-data. Endpoint: `actions/announcementUpload/invoke`.

- `content`: file path (str) or open binary reader.
- `upload_as`: required if `content` is a reader.
- **Scopes:** `spark-admin:people_write` or `spark:people_write` (self)

### CLI Examples

```bash
# Read call intercept settings for a person
wxcli user-settings show-intercept PERSON_ID

# Read call intercept settings as JSON
wxcli user-settings show-intercept PERSON_ID -o json

# Enable call intercept
wxcli user-settings update-intercept PERSON_ID --enabled

# Disable call intercept
wxcli user-settings update-intercept PERSON_ID --no-enabled

# Enable call intercept with full incoming/outgoing config (requires --json-body)
wxcli user-settings update-intercept PERSON_ID --json-body '{
  "enabled": true,
  "incoming": {
    "type": "INTERCEPT_ALL",
    "voicemailEnabled": true,
    "announcements": {
      "greeting": "DEFAULT",
      "newNumber": {"enabled": true, "destination": "+12125559999"},
      "zeroTransfer": {"enabled": true, "destination": "+12125550000"}
    }
  },
  "outgoing": {
    "type": "ALLOW_LOCAL_ONLY",
    "transferEnabled": false
  }
}'

# Upload a custom intercept greeting
wxcli user-settings configure-call-intercept PERSON_ID
```

### Raw HTTP

#### Read Call Intercept Settings

```
GET https://webexapis.com/v1/people/{personId}/features/intercept
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/intercept")
# Response:
# {
#   "enabled": false,
#   "incoming": {
#     "type": "INTERCEPT_ALL",
#     "voicemailEnabled": false,
#     "announcements": {
#       "greeting": "DEFAULT",
#       "fileName": "",
#       "newNumber": {"enabled": false, "destination": ""},
#       "zeroTransfer": {"enabled": false, "destination": ""}
#     }
#   },
#   "outgoing": {
#     "type": "INTERCEPT_ALL",
#     "transferEnabled": false,
#     "destination": ""
#   }
# }
```

#### Configure Call Intercept Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/intercept
```

```python
body = {
    "enabled": True,
    "incoming": {
        "type": "INTERCEPT_ALL",
        "voicemailEnabled": True,
        "announcements": {
            "greeting": "DEFAULT",
            "newNumber": {"enabled": False},
            "zeroTransfer": {"enabled": False}
        }
    },
    "outgoing": {
        "type": "INTERCEPT_ALL",
        "transferEnabled": False
    }
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/intercept", json=body)
```

#### Upload Custom Intercept Greeting

```
POST https://webexapis.com/v1/people/{personId}/features/intercept/actions/announcementUpload/invoke
```

Multipart/form-data with `.wav` file. Uses `rest_post` with file upload.

**Gotchas:**
- `incoming.announcements.fileName` is read-only; do not include in PUT body.
- `incoming.type` values: `"INTERCEPT_ALL"`, `"ALLOW_ALL"`.
- `outgoing.type` values: `"INTERCEPT_ALL"`, `"ALLOW_LOCAL_ONLY"`.
- The JSON key for intercept type is `type` (not `interceptType`), matching the SDK's JSON alias.

---

## 9. Monitoring

**API class:** `MonitoringApi`
**Feature key:** `monitoring`
**Source:** `wxc_sdk/person_settings/monitoring.py`

Shows specified people, places, virtual lines, or call park extensions that are being monitored. Monitors line status (on-call, parked).

### Data Models

#### `MonitoredElementMember` (extends `MonitoredMember`)

| Field | Type | Description |
|-------|------|-------------|
| (inherited fields) | | From `MonitoredMember` (member_id, first_name, last_name, etc.) |
| `location_id` | `str` | The location ID for this monitored member |

Has a property `ci_location_id` that converts `location_id` to UUID format.

#### `MonitoredElement`

| Field | Type | Description |
|-------|------|-------------|
| `member` | `MonitoredElementMember` | Monitored person or place |
| `cpe` | `CallParkExtension` | Monitored call park extension (JSON alias: `callparkextension`) |

#### `Monitoring`

| Field | Type | Description |
|-------|------|-------------|
| `call_park_notification_enabled` | `bool` | Enable/disable call park notifications |
| `monitored_elements` | `list[Union[str, MonitoredElement]]` | Monitored elements (max 50). For updates, can pass IDs (strings) directly. |

**Convenience properties:**
- `monitored_cpes` -> `list[CallParkExtension]` -- filters to just call park extensions
- `monitored_members` -> `list[MonitoredElementMember]` -- filters to just members

### Methods

#### `read`

```python
MonitoringApi.read(entity_id: str, org_id: str = None) -> Monitoring
```

- **Scopes:** `spark-admin:people_read`

#### `configure`

```python
MonitoringApi.configure(entity_id: str, settings: Monitoring, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write`
- **Max 50 elements.** The SDK extracts IDs from `MonitoredElement` objects (using `member.member_id` or `cpe.cpe_id`) or passes strings directly.
- Body format:
  ```json
  {
    "enableCallParkNotification": true,
    "monitoredElements": ["id1", "id2", ...]
  }
  ```

### CLI Examples

```bash
# Read monitoring settings for a person
wxcli user-settings list-monitoring PERSON_ID

# Read monitoring settings as JSON
wxcli user-settings list-monitoring PERSON_ID -o json

# Enable call park notification
wxcli user-settings update-monitoring PERSON_ID --enable-call-park-notification

# Disable call park notification
wxcli user-settings update-monitoring PERSON_ID --no-enable-call-park-notification

# Update monitored elements list (requires --json-body for element IDs)
wxcli user-settings update-monitoring PERSON_ID --json-body '{
  "enableCallParkNotification": true,
  "monitoredElements": ["PERSON_ID_1", "PERSON_ID_2", "CPE_ID_1"]
}'
```

### Raw HTTP

#### Read Monitoring Settings

```
GET https://webexapis.com/v1/people/{personId}/features/monitoring
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/monitoring")
# Response:
# {
#   "enableCallParkNotification": true,
#   "monitoredElements": [
#     {
#       "member": {
#         "id": "person-id", "firstName": "Jane", "lastName": "Doe",
#         "phoneNumber": "+12223334444", "extension": "1234",
#         "locationId": "location-id"
#       }
#     },
#     {
#       "callparkextension": {
#         "id": "cpe-id", "name": "CPE 1001", "extension": "1001"
#       }
#     }
#   ]
# }
```

#### Configure Monitoring Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/monitoring
```

```python
body = {
    "enableCallParkNotification": True,
    "monitoredElements": ["person-id-1", "person-id-2", "cpe-id-1"]
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/monitoring", json=body)
```

**Gotchas:**
- Maximum 50 monitored elements.
- For updates, pass a flat list of IDs (person, place, or call park extension IDs). Reads return full objects with nested `member` or `callparkextension` details.
- The JSON key for call park extensions is `callparkextension` (lowercase, no hyphen).

---

## 10. Push-to-Talk

**API class:** `PushToTalkApi`
**Feature key:** `pushToTalk`
**Source:** `wxc_sdk/person_settings/push_to_talk.py`

Allows desk phones to function as one-way or two-way intercoms connecting people in different parts of the organization.

### Data Models

#### `PTTConnectionType` (Enum)

| Value | Description |
|-------|-------------|
| `ONE_WAY` | Initiators can chat but the target cannot respond |
| `TWO_WAY` | Both parties can communicate |

#### `PushToTalkAccessType` (Enum)

| Value | Description |
|-------|-------------|
| `ALLOW_MEMBERS` | List of people allowed to use PTT with this person |
| `BLOCK_MEMBERS` | List of people blocked from using PTT with this person |

#### `PushToTalkSettings`

| Field | Type | Description |
|-------|------|-------------|
| `allow_auto_answer` | `bool` | When enabled, person receives and auto-answers PTT calls |
| `connection_type` | `PTTConnectionType` | One-way or two-way |
| `access_type` | `PushToTalkAccessType` | Allow-list or block-list mode |
| `members` | `list[Union[str, MonitoredMember]]` | People allowed or blocked. For updates, can pass member IDs (strings) directly. |

### Methods

#### `read`

```python
PushToTalkApi.read(entity_id: str, org_id: str = None) -> PushToTalkSettings
```

- **Scopes:** `spark-admin:people_read`

#### `configure`

```python
PushToTalkApi.configure(entity_id: str, settings: PushToTalkSettings, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write`
- Members are flattened to a list of IDs before sending (extracted from `MonitoredMember.member_id` or passed as strings).
- Serializes with `exclude_none=False` and `exclude_unset=True`, so explicitly set `None` values are preserved in the request.

### CLI Examples

```bash
# Read push-to-talk settings for a person
wxcli user-settings list-push-to-talk PERSON_ID

# Read push-to-talk settings as JSON
wxcli user-settings list-push-to-talk PERSON_ID -o json

# Enable push-to-talk with auto-answer
wxcli user-settings update-push-to-talk PERSON_ID --allow-auto-answer

# Disable push-to-talk auto-answer
wxcli user-settings update-push-to-talk PERSON_ID --no-allow-auto-answer

# Full push-to-talk config with connection type and members (requires --json-body)
wxcli user-settings update-push-to-talk PERSON_ID --json-body '{
  "allowAutoAnswer": true,
  "connectionType": "TWO_WAY",
  "accessType": "ALLOW_MEMBERS",
  "members": ["PERSON_ID_1", "PERSON_ID_2"]
}'
```

### Raw HTTP

#### Read Push-to-Talk Settings

```
GET https://webexapis.com/v1/people/{personId}/features/pushToTalk
```

```python
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/pushToTalk")
# Response:
# {
#   "allowAutoAnswer": true,
#   "connectionType": "TWO_WAY",
#   "accessType": "ALLOW_MEMBERS",
#   "members": [
#     {"id": "person-id", "firstName": "Jane", "lastName": "Doe", ...}
#   ]
# }
```

#### Configure Push-to-Talk Settings

```
PUT https://webexapis.com/v1/people/{personId}/features/pushToTalk
```

```python
body = {
    "allowAutoAnswer": True,
    "connectionType": "TWO_WAY",
    "accessType": "ALLOW_MEMBERS",
    "members": ["person-id-1", "person-id-2"]
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/pushToTalk", json=body)
```

**Gotchas:**
- `members` accepts a flat list of person IDs for updates, even though reads return full member objects.
- `connectionType` values: `"ONE_WAY"`, `"TWO_WAY"`.
- `accessType` values: `"ALLOW_MEMBERS"`, `"BLOCK_MEMBERS"`.

---

## 11. Music on Hold

**API class:** `MusicOnHoldApi`
**Feature key:** `musicOnHold`
**Source:** `wxc_sdk/person_settings/moh.py`

Music played when a caller is put on hold or the call is parked.

### Data Model

#### `MusicOnHold`

| Field | Type | Description |
|-------|------|-------------|
| `moh_enabled` | `bool` | Music on hold enabled/disabled for the entity |
| `moh_location_enabled` | `bool` | Read-only. Whether MoH is enabled at the location level. Excluded from updates. |
| `greeting` | `Greeting` | `DEFAULT` or `CUSTOM` |
| `audio_announcement_file` | `AnnAudioFile` | Custom audio file details (when greeting is `CUSTOM`) |

**Important interaction between `moh_location_enabled` and `moh_enabled`:**

| `moh_location_enabled` | `moh_enabled` | Result |
|------------------------|---------------|--------|
| `false` | `true` | MoH is **disabled** for user |
| `true` | `false` | MoH is **off** for user |
| `true` | `true` | MoH plays for user |

### Methods

#### `read`

```python
MusicOnHoldApi.read(entity_id: str, org_id: str = None) -> MusicOnHold
```

- **Scopes:** `spark-admin:telephony_config_read`

#### `configure`

```python
MusicOnHoldApi.configure(entity_id: str, settings: MusicOnHold, org_id: str = None)
```

- **Scopes:** `spark-admin:telephony_config_write`
- **Prerequisite:** Music on hold must be enabled at the location level for the person-level setting to take effect.

### CLI Examples

```bash
# Read music on hold settings for a person
wxcli user-settings show-music-on-hold PERSON_ID

# Read music on hold settings as JSON
wxcli user-settings show-music-on-hold PERSON_ID -o json

# Enable music on hold with default greeting
wxcli user-settings update-music-on-hold PERSON_ID --moh-enabled --greeting DEFAULT

# Enable music on hold with custom greeting
wxcli user-settings update-music-on-hold PERSON_ID --moh-enabled --greeting CUSTOM

# Disable music on hold
wxcli user-settings update-music-on-hold PERSON_ID --no-moh-enabled

# Full music on hold config with audio file reference (requires --json-body)
wxcli user-settings update-music-on-hold PERSON_ID --json-body '{
  "mohEnabled": true,
  "greeting": "CUSTOM",
  "audioAnnouncementFile": {"id": "ANNOUNCEMENT_FILE_ID"}
}'
```

### Raw HTTP

> **Note:** Music on Hold uses the `telephony/config/people` path, not `people/{id}/features`.

#### Read Music on Hold Settings

```
GET https://webexapis.com/v1/telephony/config/people/{personId}/musicOnHold
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/musicOnHold")
# Response:
# {
#   "mohEnabled": true,
#   "mohLocationEnabled": true,
#   "greeting": "DEFAULT",
#   "audioAnnouncementFile": {...}
# }
```

#### Configure Music on Hold Settings

```
PUT https://webexapis.com/v1/telephony/config/people/{personId}/musicOnHold
```

```python
body = {
    "mohEnabled": True,
    "greeting": "DEFAULT",
    "audioAnnouncementFile": {"id": "announcement-file-id"}
}
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/musicOnHold", json=body)
```

**Gotchas:**
- `mohLocationEnabled` is read-only; do not include in PUT body.
- Person-level MoH only works if MoH is also enabled at the location level (`mohLocationEnabled` must be `true`).
- Uses `spark-admin:telephony_config_read`/`write` scopes (not `people_read`/`write`).

---

## 12. Common Patterns

### URL Construction

All APIs in this group use `PersonSettingsApiChild.f_ep()` to build endpoints. The pattern depends on the entity type:

| Entity Type | URL Pattern |
|-------------|-------------|
| Person | `people/{entity_id}/features/{feature}` |
| Workspace | `workspaces/{entity_id}/features/{feature}` |
| Virtual Line | `telephony/config/virtualLines/{entity_id}/{feature}` |
| Location | `telephony/config/locations/{entity_id}/{feature}` |

Some features have alternate URL mappings (defined in `common.py`). Notable remaps for persons:

- `agent` -> `telephony/config/people/{id}/agent/...`
- `musicOnHold` -> `telephony/config/people/{id}/musicOnHold`
- `voicemail` passcode -> `telephony/config/people/{id}/voicemail/passcode`

### Read/Update Pattern

Every sub-API follows the same pattern:

1. `read(entity_id, org_id=None)` -- GET request, returns a data model
2. `configure(entity_id, settings, org_id=None)` -- PUT request with JSON body
3. Some APIs have additional action methods (greeting uploads, PIN resets)

### Scopes Summary

| Operation | Typical Admin Scope | Typical Self Scope |
|-----------|--------------------|--------------------|
| Read settings | `spark-admin:people_read` | `spark:people_read` |
| Update settings | `spark-admin:people_write` | `spark:people_write` |
| Telephony config read | `spark-admin:telephony_config_read` | -- |
| Telephony config write | `spark-admin:telephony_config_write` | -- |

APIs using `telephony_config_*` scopes: Agent Caller ID, Music on Hold, Voicemail passcode.

### Greeting/Audio Upload Pattern

Three APIs support custom audio upload (all `.wav` format, multipart/form-data):

| API | Method | Endpoint Suffix |
|-----|--------|----------------|
| Voicemail | `configure_busy_greeting()` | `actions/uploadBusyGreeting/invoke` |
| Voicemail | `configure_no_answer_greeting()` | `actions/uploadNoAnswerGreeting/invoke` |
| Call Intercept | `greeting()` | `actions/announcementUpload/invoke` |

All accept either a file path (str) or `BufferedReader`. When passing a reader, `upload_as` (a `.wav` filename) is required.

### Update Exclusions (Read-Only Fields)

Each model's `update()` method strips fields that cannot be written:

| Model | Excluded Fields |
|-------|----------------|
| `VoicemailSettings` | `greeting_uploaded`, `system_max_number_of_rings`, `voice_message_forwarding_enabled` |
| `CallerId` | `caller_id_types` (not in `fields_for_update`) |
| `CallRecordingSetting` | `service_provider`, `external_group`, `external_identifier` |
| `InterceptSetting` | `incoming.announcements.file_name` |
| `MusicOnHold` | `moh_location_enabled` |

### Entity Applicability

Not all settings apply equally to all entity types:

| Setting | Person | Workspace | Virtual Line |
|---------|--------|-----------|-------------|
| Voicemail | Yes | Yes | Yes |
| Caller ID | Yes | Yes | Yes |
| Agent Caller ID | Yes | -- | Yes |
| Anonymous Call Rejection | No (admin `/people/{id}` endpoint does not exist; self via `/me` only) | Yes (Professional-licensed workspaces only) | -- |
| Privacy | Yes | Yes | Yes |
| Barge-In | Yes | Yes | Yes |
| Call Recording | Yes | Yes | Yes |
| Call Intercept | Yes | Yes | Yes |
| Monitoring | Yes | Yes | -- |
| Push-to-Talk | Yes | Yes | Yes |
| Music on Hold | Yes | Yes | Yes |

---

## Gotchas (Cross-Cutting)

- **Read-only fields cause silent failures.** Every PUT endpoint in this group has read-only fields that must be excluded from the request body. If you include them, the API may return 400 or silently ignore the entire request. Key offenders: `greetingUploaded`, `systemMaxNumberOfRings`, `voiceMessageForwardingEnabled` (voicemail); `types`, `locationExternalCallerIdName` (caller ID); `serviceProvider`, `externalGroup`, `externalIdentifier` (call recording); `fileName` (call intercept); `mohLocationEnabled` (music on hold).
- **Nested settings require `--json-body`.** The wxcli generator skips deeply nested object/array body fields. For voicemail (sendBusyCalls, sendUnansweredCalls, notifications, etc.), call intercept (incoming/outgoing), call recording (notification, repeat, startStopAnnouncement), monitoring (monitoredElements), push-to-talk (members), and privacy (monitoringAgents), use `--json-body` with the full JSON payload.
- **Three different URL path patterns.** Most features use `people/{id}/features/{feature}`, but Agent Caller ID uses `telephony/config/people/{id}/agent/...`, Music on Hold uses `telephony/config/people/{id}/musicOnHold`, and Voicemail Passcode uses `telephony/config/people/{id}/voicemail/passcode`. The corresponding scopes differ too (`telephony_config_*` vs `people_*`).
- **Scope mismatch between read and write.** Agent Caller ID uses `people_read` for listing available IDs but `telephony_config_read` for reading the current selection. Always check the specific scope required per method.
- **Music on Hold depends on location-level setting.** Even if `mohEnabled` is `true` for a person, MoH will not play unless `mohLocationEnabled` is also `true` at the location level. The person-level API cannot change the location-level setting.
- **`notification.type` null serialization.** Call Recording's `notification.type` returns the string `"None"` on reads but expects JSON `null` on writes. In wxcli, pass `"type": null` in `--json-body`.
- **Anonymous Call Rejection has NO admin-level person endpoint.** Live API testing confirms that `GET /v1/people/{personId}/features/anonymousCallReject` and `GET /v1/telephony/config/people/{personId}/anonymousCallReject` both return 404. The only working paths are: (1) workspace admin: `/telephony/config/workspaces/{workspaceId}/anonymousCallReject` (requires Professional-licensed workspace, error 25409 otherwise), and (2) self-service: `/telephony/config/people/me/settings/anonymousCallReject` (requires calling-licensed user token with `spark:telephony_config_read/write`). The wxcli CLI only exposes it under `workspace-settings`, not `user-settings`.
- **Monitoring has a 50-element maximum.** The `monitoredElements` list accepts at most 50 entries (persons, places, virtual lines, and call park extensions combined). The API does not surface this limit in error messages clearly.
- **Members lists return objects but accept IDs.** Privacy (`monitoringAgents`), Monitoring (`monitoredElements`), and Push-to-Talk (`members`) all return full member objects on reads but accept flat lists of ID strings on writes.

---

## See Also

- **[Location Call Settings — Core](location-call-settings-core.md)** — Location-level voicemail policies (transcription toggle), org-wide voicemail settings (expiry, forwarding), and location-level call intercept that govern person-level defaults
- **[Location Recording — Advanced](location-recording-advanced.md)** — Location/org-level call recording vendor settings that must be configured before per-person recording works
- **[self-service-call-settings.md](self-service-call-settings.md)** -- User-level `/people/me/` endpoints for self-service call settings, including 6 user-only settings with no admin path.
