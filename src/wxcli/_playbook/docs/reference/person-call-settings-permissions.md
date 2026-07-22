# Person Call Settings — Permissions, Executive & Feature Access

Reference for managing incoming/outgoing call permissions, feature access controls, executive/assistant pairing, and call policy settings.

---

## 1. Incoming Permissions

Controls who can call a person and how incoming external calls can be transferred.

- Feature path segment: `incomingPermission`
- Also used for: virtual lines, workspaces

### Data Models

#### `ExternalTransfer` (enum)

| Value | Meaning |
|-------|---------|
| `ALLOW_ALL_EXTERNAL` | Allow transfer/forward for all external calls including transferred ones |
| `ALLOW_ONLY_TRANSFERRED_EXTERNAL` | Only allow transferred calls to be re-transferred/forwarded |
| `BLOCK_ALL_EXTERNAL` | Block all external calls from being transferred or forwarded |

#### `IncomingPermissions` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_enabled` | `bool` | When `true`, person uses custom permissions instead of org defaults |
| `external_transfer` | `ExternalTransfer` | Transfer behavior for incoming external calls |
| `internal_calls_enabled` | `bool` | Whether internal calls are allowed to be received |
| `collect_calls_enabled` | `bool` | Whether collect calls are allowed to be received |

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

**Base URL:** `https://webexapis.com/v1`

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Read | GET | `people/{personId}/features/incomingPermission` |
| Update | PUT | `people/{personId}/features/incomingPermission` |

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"

# Read incoming permissions
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/incomingPermission")
# Returns: {"useCustomEnabled": bool, "externalTransfer": str, "internalCallsEnabled": bool, "collectCallsEnabled": bool}

# Update incoming permissions
body = {
    "useCustomEnabled": True,
    "externalTransfer": "ALLOW_ALL_EXTERNAL",
    "internalCallsEnabled": True,
    "collectCallsEnabled": True
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/incomingPermission", json=body)
```

**CLI commands:** `show-incoming-permission`, `update-incoming-permission`

### CLI Examples

```bash
# Read incoming permission settings for a person
wxcli user-settings show-incoming-permission Y2lzY29...personId

# Enable custom incoming permissions — allow all external, enable internal + collect
wxcli user-settings update-incoming-permission Y2lzY29...personId \
  --use-custom-enabled \
  --external-transfer ALLOW_ALL_EXTERNAL \
  --internal-calls-enabled \
  --collect-calls-enabled

# Block all external call transfers
wxcli user-settings update-incoming-permission Y2lzY29...personId \
  --use-custom-enabled \
  --external-transfer BLOCK_ALL_EXTERNAL

# Reset to org defaults (disable custom permissions)
wxcli user-settings update-incoming-permission Y2lzY29...personId \
  --no-use-custom-enabled

# Use --json-body for full control
wxcli user-settings update-incoming-permission Y2lzY29...personId \
  --json-body '{"useCustomEnabled": true, "externalTransfer": "ALLOW_ONLY_TRANSFERRED_EXTERNAL", "internalCallsEnabled": true, "collectCallsEnabled": false}'
```

---

## 2. Outgoing Permissions

Controls what types of outbound calls a person can place, with per-call-type actions, transfer number routing, access codes, and digit pattern overrides.

- Feature path segment: `outgoingPermission`
- Also used for: user, workspace, location, virtual line settings

> **Note:** `access_codes` is not available for locations. Use the telephony-level access codes API instead.

### Data Models

#### `OutgoingPermissionCallType` (enum)

| Value | Description |
|-------|-------------|
| `INTERNAL_CALL` | Internal calls |
| `LOCAL` | Local calls (legacy, may be deprecated) |
| `TOLL_FREE` | Toll-free calls |
| `TOLL` | Toll calls (legacy, may be deprecated) |
| `NATIONAL` | National calls |
| `INTERNATIONAL` | International calls |
| `OPERATOR_ASSISTED` | Operator-assisted calls |
| `CHARGEABLE_DIRECTORY_ASSISTED` | Chargeable directory assistance |
| `SPECIAL_SERVICES_I` | Special services tier I |
| `SPECIAL_SERVICES_II` | Special services tier II |
| `PREMIUM_SERVICES_I` | Premium services tier I |
| `PREMIUM_SERVICES_II` | Premium services tier II |

#### `Action` (enum)

| Value | Meaning |
|-------|---------|
| `ALLOW` | Allow the call type |
| `BLOCK` | Block the call type |
| `AUTH_CODE` | Require an authorization code |
| `TRANSFER_NUMBER_1` | Auto-transfer to transfer number 1 |
| `TRANSFER_NUMBER_2` | Auto-transfer to transfer number 2 |
| `TRANSFER_NUMBER_3` | Auto-transfer to transfer number 3 |

#### `CallTypePermission` (model)

| Field | Type | Description |
|-------|------|-------------|
| `action` | `Action` | Action for this call type |
| `transfer_enabled` | `bool` | Whether transfer/forward is allowed for this call type |
| `is_call_type_restriction_enabled` | `Optional[bool]` | If `true`, restriction is system-enforced and cannot be changed |

#### `CallingPermissions` (model)

One `Optional[CallTypePermission]` field for each call type (e.g., `internal_call`, `local`, `toll_free`, `national`, `international`, etc.). Extra/unknown call types are allowed and auto-parsed.

#### `OutgoingPermissions` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_enabled` | `Optional[bool]` | Use shared control for all outgoing categories |
| `use_custom_permissions` | `Optional[bool]` | Use specified outgoing calling permissions |
| `calling_permissions` | `Optional[CallingPermissions]` | Per-call-type permission settings |

> **Serialization note:** The API returns `callingPermissions` as a list of `{callType, action, transferEnabled}` objects, not a dict.

#### `AutoTransferNumbers` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_transfer_numbers` | `Optional[bool]` | Use custom transfer number settings |
| `auto_transfer_number1` | `Optional[str]` | Transfer destination for `TRANSFER_NUMBER_1` action |
| `auto_transfer_number2` | `Optional[str]` | Transfer destination for `TRANSFER_NUMBER_2` action |
| `auto_transfer_number3` | `Optional[str]` | Transfer destination for `TRANSFER_NUMBER_3` action |

**Note:** To clear a transfer number via the API, send an empty string rather than omitting the field.

#### `DigitPattern` (model)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Optional[str]` | Unique identifier |
| `name` | `Optional[str]` | Unique name |
| `pattern` | `Optional[str]` | Digit pattern to match against dialed numbers |
| `action` | `Optional[Action]` | Action when pattern matches |
| `transfer_enabled` | `Optional[bool]` | Whether transfer/forward is allowed |

#### `DigitPatterns` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_digit_patterns` | `Optional[bool]` | Use custom digit pattern settings |
| `digit_patterns` | `Optional[list[DigitPattern]]` | List of digit patterns |

#### `AuthCodes` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_access_codes` | `Optional[bool]` | Use custom access code settings |
| `access_codes` | `Optional[list[AuthCode]]` | List of access codes |

> Access codes are not available for locations — use the telephony-level access codes API instead.

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

**Base URL:** `https://webexapis.com/v1`

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Read outgoing permissions | GET | `people/{personId}/features/outgoingPermission` |
| Update outgoing permissions | PUT | `people/{personId}/features/outgoingPermission` |
| Read transfer numbers | GET | `people/{personId}/features/outgoingPermission/autoTransferNumbers` |
| Update transfer numbers | PUT | `people/{personId}/features/outgoingPermission/autoTransferNumbers` |
| Read access codes | GET | `people/{personId}/features/outgoingPermission/accessCodes` |
| Create access code | POST | `people/{personId}/features/outgoingPermission/accessCodes` |
| Modify access codes | PUT | `people/{personId}/features/outgoingPermission/accessCodes` |
| Delete all access codes | DELETE | `people/{personId}/features/outgoingPermission/accessCodes` |
| List digit patterns | GET | `telephony/config/people/{personId}/outgoingPermission/digitPatterns` |
| Create digit pattern | POST | `telephony/config/people/{personId}/outgoingPermission/digitPatterns` |
| Get digit pattern | GET | `telephony/config/people/{personId}/outgoingPermission/digitPatterns/{digitPatternId}` |
| Update digit pattern | PUT | `telephony/config/people/{personId}/outgoingPermission/digitPatterns/{digitPatternId}` |
| Delete digit pattern | DELETE | `telephony/config/people/{personId}/outgoingPermission/digitPatterns/{digitPatternId}` |
| Delete all digit patterns | DELETE | `telephony/config/people/{personId}/outgoingPermission/digitPatterns` |
| Update category control | PUT | `telephony/config/people/{personId}/outgoingPermission/digitPatterns` |

> **Note:** Main outgoing permissions and transfer numbers/access codes use the `people/{personId}/features/...` base path. Digit patterns use the `telephony/config/people/{personId}/...` base path. The transfer numbers endpoint path is `autoTransferNumbers` (not `transferNumbers`).

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"

# Read outgoing permissions
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/outgoingPermission")
# Returns: {"useCustomEnabled": bool, "useCustomPermissions": bool,
#           "callingPermissions": [{"callType": str, "action": str, "transferEnabled": bool}, ...]}

# Update outgoing permissions (callingPermissions is a list, not a dict)
body = {
    "useCustomEnabled": True,
    "useCustomPermissions": True,
    "callingPermissions": [
        {"callType": "INTERNAL_CALL", "action": "ALLOW", "transferEnabled": True},
        {"callType": "NATIONAL", "action": "ALLOW", "transferEnabled": True},
        {"callType": "INTERNATIONAL", "action": "BLOCK", "transferEnabled": False},
        {"callType": "PREMIUM_SERVICES_I", "action": "BLOCK", "transferEnabled": False},
        {"callType": "PREMIUM_SERVICES_II", "action": "BLOCK", "transferEnabled": False}
    ]
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/outgoingPermission", json=body)

# Read/update transfer numbers
xfer = api.session.rest_get(f"{BASE}/people/{person_id}/features/outgoingPermission/autoTransferNumbers")
api.session.rest_put(f"{BASE}/people/{person_id}/features/outgoingPermission/autoTransferNumbers", json={
    "useCustomTransferNumbers": True,
    "autoTransferNumber1": "+15551234567"
})

# List digit patterns (note: telephony/config path)
patterns = api.session.rest_get(
    f"{BASE}/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
)

# Create digit pattern
api.session.rest_post(
    f"{BASE}/telephony/config/people/{person_id}/outgoingPermission/digitPatterns",
    json={"name": "Block 1900", "pattern": "1900!", "action": "BLOCK", "transferEnabled": False}
)
```

**CLI commands:** `show-outgoing-permission`, `update-outgoing-permission`

### CLI Examples

```bash
# --- Main Outgoing Permissions ---

# Read outgoing calling permissions for a person
wxcli user-settings list-outgoing-permission Y2lzY29...personId

# Read as JSON (includes callingPermissions array)
wxcli user-settings list-outgoing-permission Y2lzY29...personId -o json

# Enable custom outgoing permissions
wxcli user-settings update-outgoing-permission Y2lzY29...personId \
  --use-custom-enabled --use-custom-permissions

# Block international and premium calls via --json-body
wxcli user-settings update-outgoing-permission Y2lzY29...personId \
  --json-body '{"useCustomEnabled": true, "useCustomPermissions": true, "callingPermissions": [{"callType": "INTERNAL_CALL", "action": "ALLOW", "transferEnabled": true}, {"callType": "NATIONAL", "action": "ALLOW", "transferEnabled": true}, {"callType": "INTERNATIONAL", "action": "BLOCK", "transferEnabled": false}, {"callType": "PREMIUM_SERVICES_I", "action": "BLOCK", "transferEnabled": false}, {"callType": "PREMIUM_SERVICES_II", "action": "BLOCK", "transferEnabled": false}]}'

# --- Transfer Numbers ---

# Read auto-transfer numbers
wxcli user-settings show-auto-transfer-numbers Y2lzY29...personId

# Set transfer number 1
wxcli user-settings update-auto-transfer-numbers Y2lzY29...personId \
  --use-custom-transfer-numbers \
  --auto-transfer-number1 "+15551234567"

# --- Access Codes ---

# List access codes for a person
wxcli user-settings list-access-codes Y2lzY29...personId

# Create a new access code
wxcli user-settings create-access-codes Y2lzY29...personId \
  --code "1234" --description "Conference room auth code"

# Modify access codes (e.g., toggle custom codes, delete specific codes)
wxcli user-settings update-access-codes Y2lzY29...personId \
  --json-body '{"useCustomAccessCodes": true, "deleteCodes": ["1234"]}'

# Delete all access codes for a person
wxcli user-settings delete-access-codes Y2lzY29...personId --force

# --- Digit Patterns ---

# List all digit patterns
wxcli user-settings list-digit-patterns Y2lzY29...personId

# Create a digit pattern to block 1-900 numbers
wxcli user-settings create-digit-patterns Y2lzY29...personId \
  --name "Block 1900" --pattern "1900!" --action BLOCK --transfer-enabled

# View a specific digit pattern
wxcli user-settings show-digit-patterns Y2lzY29...personId Y2lzY29...patternId

# Delete a specific digit pattern
wxcli user-settings delete-digit-patterns-outgoing-permission-1 Y2lzY29...personId Y2lzY29...patternId --force

# Delete all digit patterns
wxcli user-settings delete-digit-patterns-outgoing-permission Y2lzY29...personId --force
```

---

## 3. Feature Access Controls

Controls which Webex Calling features end users can modify via User Hub, Webex client, or IP phone.

### Data Models

#### `FeatureAccessLevel` (enum)

| Value | Meaning |
|-------|---------|
| `FULL_ACCESS` | User can modify this feature |
| `NO_ACCESS` | User cannot modify this feature |

#### `FeatureAccessSettings` (model)

All fields are `Optional[FeatureAccessLevel]`:

| Field | Controls access to |
|-------|--------------------|
| `anonymous_call_rejection` | Anonymous call rejection |
| `barge_in` | Barge In |
| `block_caller_id` | Block caller ID |
| `call_forwarding` | Call forwarding |
| `call_waiting` | Call waiting |
| `call_notify` | Call notify |
| `connected_line_identity` | Connected line identity |
| `executive` | Executive/Executive assistant |
| `hoteling` | Hoteling |
| `priority_alert` | Priority alert |
| `selectively_accept_calls` | Selectively accept calls |
| `selectively_reject_calls` | Selectively reject calls |
| `selectively_forward_calls` | Selectively forward calls |
| `sequential_ring` | Sequential ring |
| `simultaneous_ring` | Simultaneous ring |
| `single_number_reach` | Single number reach |
| `voicemail` | Voicemail feature |
| `send_calls_to_voicemail` | Send calls to voicemail |
| `voicemail_email_copy` | Email a copy of voicemail |
| `voicemail_fax_messaging` | Fax messaging |
| `voicemail_message_storage` | Message storage |
| `voicemail_notifications` | Voicemail notifications |
| `voicemail_transfer_number` | Transfer on "0" to another number |
| `generate_activation_code` | Allow end user to generate activation codes and delete phones |
| `voicemail_download` | Download voicemail via User Hub/Webex |

#### `UserFeatureAccessSettings` (model)

| Field | Type | Description |
|-------|------|-------------|
| `user_org_settings_permission_enabled` | `Optional[bool]` | Whether org-level settings apply to this user |
| `user_settings_permissions` | `Optional[FeatureAccessSettings]` | Per-user feature access overrides |

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

**Base URL:** `https://webexapis.com/v1`

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Read org defaults | GET | `telephony/config/featureAccessCodes` |
| Update org defaults | PUT | `telephony/config/featureAccessCodes` |
| Read person settings | GET | `telephony/config/people/{personId}/featureAccessCodes` |
| Update person settings | PUT | `telephony/config/people/{personId}/featureAccessCodes` |
| Reset to org defaults | POST | `telephony/config/people/{personId}/featureAccessCodes/actions/reset/invoke` |

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"

# Read org-level default feature access settings
defaults = api.session.rest_get(f"{BASE}/telephony/config/featureAccessCodes")

# Read person-level feature access settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/featureAccessCodes")
# Returns: {"userOrgSettingsPermissionEnabled": bool,
#           "userSettingsPermissions": {"callForwarding": "FULL_ACCESS", "voicemail": "NO_ACCESS", ...}}

# Update person feature access
body = {
    "callForwarding": "NO_ACCESS",
    "simultaneousRing": "NO_ACCESS",
    "voicemail": "FULL_ACCESS"
}
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/featureAccessCodes", json=body)

# Reset person to org defaults
api.session.rest_post(
    f"{BASE}/telephony/config/people/{person_id}/featureAccessCodes/actions/reset/invoke"
)
```

### CLI Examples

> **Note:** Feature access controls do not have dedicated `wxcli` commands (verified across all 179 command groups). The `my-call-settings list-feature-access-code-settings` command is a different endpoint -- it lists a user's own FAC star codes (`/telephony/config/people/me/settings/featureAccessCode`), not the `featureAccessCodes` access controls below. Use `curl` with the REST endpoints above, or raw HTTP requests directly.

```bash
# Read org-level default feature access settings
curl -s -H "Authorization: Bearer $WEBEX_TOKEN" \
  "https://webexapis.com/v1/telephony/config/featureAccessCodes" | python3 -m json.tool

# Read feature access settings for a specific person
curl -s -H "Authorization: Bearer $WEBEX_TOKEN" \
  "https://webexapis.com/v1/telephony/config/people/Y2lzY29...personId/featureAccessCodes" | python3 -m json.tool

# Update person feature access — block call forwarding and simultaneous ring
curl -s -X PUT -H "Authorization: Bearer $WEBEX_TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/v1/telephony/config/people/Y2lzY29...personId/featureAccessCodes" \
  -d '{"callForwarding": "NO_ACCESS", "simultaneousRing": "NO_ACCESS", "voicemail": "FULL_ACCESS"}'

# Reset a person's feature access back to org defaults
curl -s -X POST -H "Authorization: Bearer $WEBEX_TOKEN" \
  "https://webexapis.com/v1/telephony/config/people/Y2lzY29...personId/featureAccessCodes/actions/reset/invoke"
```

---

## 4. Executive / Assistant Settings

Full executive-assistant pairing, alerting, call filtering, and screening configuration.

### 4a. Exec Assistant Type Assignment

- Feature path segment: `executiveAssistant`

Simple API that reads or sets whether a person is an executive, an executive assistant, or unassigned.

#### `ExecAssistantType` (enum)

| Value | Meaning |
|-------|---------|
| `UNASSIGNED` | Feature not enabled |
| `EXECUTIVE` | Person is an executive |
| `EXECUTIVE_ASSISTANT` | Person is an executive assistant |

### 4b. Executive Settings (Detailed)

- All endpoints under: `telephony/config/people/{person_id}/executive/...`

#### Data Models — Alerting

**`ExecAlertingMode`** (enum): `SEQUENTIAL` | `SIMULTANEOUS`

**`ExecAlertRolloverAction`** (enum):

| Value | Meaning |
|-------|---------|
| `VOICE_MESSAGING` | Send to executive's voicemail |
| `NO_ANSWER_PROCESSING` | Trigger no-answer processing (may invoke call forwarding/voicemail) |
| `FORWARD` | Forward to `rollover_forward_to_phone_number` |

**`ExecAlertClidNameMode`** (enum):

| Value | Display |
|-------|---------|
| `EXECUTIVE_ORIGINATOR` | Executive name followed by caller name |
| `ORIGINATOR_EXECUTIVE` | Caller name followed by executive name |
| `EXECUTIVE` | Only executive name |
| `ORIGINATOR` | Only caller name |
| `CUSTOM` | Custom name |

**`ExecAlertClidPhoneNumberMode`** (enum): `EXECUTIVE` | `ORIGINATOR` | `CUSTOM`

**`ExecAlert`** (model):

| Field | Type | Description |
|-------|------|-------------|
| `alerting_mode` | `ExecAlertingMode` | Sequential or simultaneous alerting |
| `next_assistant_number_of_rings` | `int` | Rings before next assistant (sequential mode) |
| `rollover_enabled` | `bool` | Whether rollover timer is active |
| `rollover_action` | `ExecAlertRolloverAction` | What happens on rollover |
| `rollover_forward_to_phone_number` | `str` | Forward destination (when action=FORWARD) |
| `rollover_wait_time_in_secs` | `int` | Seconds before rollover triggers |
| `clid_name_mode` | `ExecAlertClidNameMode` | Caller ID name display mode |
| `custom_clidname` | `str` | Custom CLID name (deprecated) — alias `customCLIDName` |
| `custom_clidname_in_unicode` | `str` | Custom CLID name in Unicode — alias `customCLIDNameInUnicode` |
| `clid_phone_number_mode` | `ExecAlertClidPhoneNumberMode` | Caller ID phone number mode |
| `custom_clidphone_number` | `str` | Custom CLID phone number — alias `customCLIDPhoneNumber` |

#### Data Models — Assistants

**`ExecOrAssistant`** (model):

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Person ID |
| `first_name` | `str` | First name |
| `last_name` | `str` | Last name |
| `direct_number` | `str` | Direct phone number |
| `extension` | `str` | Extension |
| `opt_in_enabled` | `bool` | Whether assistant can opt in to the pool |
| `location` | `IdAndName` | Location ID and name |

**`AssistantSettings`** (model):

| Field | Type | Description |
|-------|------|-------------|
| `forward_filtered_calls_enabled` | `bool` | Forward filtered calls to a number |
| `forward_to_phone_number` | `str` | Phone number to forward filtered calls to |
| `executives` | `list[ExecOrAssistant]` | List of assigned executives |

#### Data Models — Call Filtering

**`ExecCallFilterType`** (enum):

| Value | Meaning |
|-------|---------|
| `CUSTOM_CALL_FILTERS` | Only specific calls per custom criteria |
| `ALL_CALLS` | All internal and external calls |
| `ALL_INTERNAL_CALLS` | All internal calls only |
| `ALL_EXTERNAL_CALLS` | All external calls only |

**`ExecCallFilteringCriteriaItem`** (model) — summary item in filter list:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Criteria ID |
| `filter_name` | `str` | Name |
| `source` | `SelectiveFrom` | Call source filter |
| `activation_enabled` | `bool` | Whether criteria is active |
| `filter_enabled` | `bool` | `true` = matching calls blocked; `false` = matching calls allowed through as exceptions |

**`ExecCallFiltering`** (model):

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Whether executive call filtering is on |
| `filter_type` | `ExecCallFilterType` | Filter scope |
| `criteria` | `list[ExecCallFilteringCriteriaItem]` | Configured filter criteria |

**`ExecCallFilteringScheduleLevel`** (enum): `PEOPLE` | `LOCATION`

**`ExecCallFilteringToNumber`** (model):

| Field | Type | Description |
|-------|------|-------------|
| `type` | `PrimaryOrSecondary` | Number type |
| `phone_number` | `str` | Phone number |

**`ExecCallFilteringCriteria`** (model) — full criteria detail:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Criteria ID |
| `filter_name` | `str` | Name |
| `schedule_name` | `str` | Associated schedule name |
| `schedule_type` | `ScheduleType` | Schedule type (e.g., holidays) |
| `schedule_level` | `ExecCallFilteringScheduleLevel` | People or location level |
| `calls_from` | `SelectiveFrom` | Source filter (e.g., `ANY_PHONE_NUMBER`) |
| `anonymous_callers_enabled` | `bool` | Apply to anonymous callers |
| `unavailable_callers_enabled` | `bool` | Apply to unavailable callers |
| `phone_numbers` | `list[str]` | Specific phone numbers this criteria applies to |
| `filter_enabled` | `bool` | `true` = block matching; `false` = allow matching (exception) |
| `calls_to_numbers` | `list[ExecCallFilteringToNumber]` | Numbers to route matching calls to |

#### Data Models — Screening

**`ExecScreeningAlertType`** (enum): `SILENT` | `RING_SPLASH`

**`ExecScreening`** (model):

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Whether screening is on |
| `alert_type` | `ExecScreeningAlertType` | Alert sound type |
| `alert_anywhere_location_enabled` | `bool` | Alerts for Single Number Reach |
| `alert_mobility_location_enabled` | `bool` | Alerts for Webex Go |
| `alert_shared_call_appearance_location_enabled` | `bool` | Alerts for Shared Call Appearance |

**Read scope (all executive detailed settings):** `spark-admin:telephony_config_read`
**Write scope (all executive detailed settings):** `spark-admin:telephony_config_write`

> To remove all assistants from an executive, send a null/empty assistants list via `update-assigned-assistants`.

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

**Base URL:** `https://webexapis.com/v1`

Two different base paths are used:

**Exec/Assistant type assignment** (`people/{personId}/features/...`):

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Read type | GET | `people/{personId}/features/executiveAssistant` |
| Set type | PUT | `people/{personId}/features/executiveAssistant` |

**Executive detailed settings** (`telephony/config/people/{personId}/executive/...`):

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Read alert settings | GET | `telephony/config/people/{personId}/executive/alertSettings` |
| Update alert settings | PUT | `telephony/config/people/{personId}/executive/alertSettings` |
| List assigned assistants | GET | `telephony/config/people/{personId}/executive/assignedAssistants` |
| Update assigned assistants | PUT | `telephony/config/people/{personId}/executive/assignedAssistants` |
| List available assistants | GET | `telephony/config/people/{personId}/executive/availableAssistants` |
| Read assistant settings | GET | `telephony/config/people/{personId}/executive/assistant` |
| Update assistant settings | PUT | `telephony/config/people/{personId}/executive/assistant` |
| Read call filtering | GET | `telephony/config/people/{personId}/executive/callFiltering` |
| Update call filtering | PUT | `telephony/config/people/{personId}/executive/callFiltering` |
| Create filter criteria | POST | `telephony/config/people/{personId}/executive/callFiltering/criteria` |
| Get filter criteria | GET | `telephony/config/people/{personId}/executive/callFiltering/criteria/{criteriaId}` |
| Update filter criteria | PUT | `telephony/config/people/{personId}/executive/callFiltering/criteria/{criteriaId}` |
| Delete filter criteria | DELETE | `telephony/config/people/{personId}/executive/callFiltering/criteria/{criteriaId}` |
| Read screening | GET | `telephony/config/people/{personId}/executive/screening` |
| Update screening | PUT | `telephony/config/people/{personId}/executive/screening` |

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"

# --- Exec/Assistant Type Assignment ---
# Read type (returns {"type": "UNASSIGNED"|"EXECUTIVE"|"EXECUTIVE_ASSISTANT"})
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/executiveAssistant")

# Assign as executive
api.session.rest_put(f"{BASE}/people/{person_id}/features/executiveAssistant",
                     json={"type": "EXECUTIVE"})

# --- Executive Detailed Settings (telephony/config path) ---
# Read alert settings
alert = api.session.rest_get(
    f"{BASE}/telephony/config/people/{person_id}/executive/alertSettings"
)

# Update alert settings
api.session.rest_put(
    f"{BASE}/telephony/config/people/{person_id}/executive/alertSettings",
    json={
        "alertingMode": "SEQUENTIAL",
        "nextAssistantNumberOfRings": 4,
        "rolloverEnabled": True,
        "rolloverAction": "VOICE_MESSAGING",
        "rolloverWaitTimeInSecs": 20
    }
)

# Assign assistants to executive
api.session.rest_put(
    f"{BASE}/telephony/config/people/{person_id}/executive/assignedAssistants",
    json={"assistants": [{"id": assistant_person_id}]}
)

# Read assistant settings (from assistant's perspective)
asst = api.session.rest_get(
    f"{BASE}/telephony/config/people/{assistant_id}/executive/assistant"
)

# Read screening settings
screening = api.session.rest_get(
    f"{BASE}/telephony/config/people/{person_id}/executive/screening"
)
```

**CLI commands:** `show-executive-assistant`, `update-executive-assistant`
**CLI commands (self):** `list-assigned-assistants`, `update-assigned-assistants`, `list-available-assistants`, `show-assistant`, `update-assistant`

### CLI Examples

```bash
# --- Exec/Assistant Type Assignment ---

# Read executive/assistant type for a person
wxcli user-settings show-executive-assistant Y2lzY29...personId

# Assign a person as an executive
wxcli user-settings update-executive-assistant Y2lzY29...execPersonId \
  --type EXECUTIVE

# Assign a person as an executive assistant
wxcli user-settings update-executive-assistant Y2lzY29...asstPersonId \
  --type EXECUTIVE_ASSISTANT

# Remove executive/assistant assignment
wxcli user-settings update-executive-assistant Y2lzY29...personId \
  --type UNASSIGNED

# --- Executive Alert Settings ---

# Read executive alert settings
wxcli user-settings show-alert Y2lzY29...execPersonId

# Configure sequential alerting with rollover to voicemail after 20 seconds
wxcli user-settings update-alert Y2lzY29...execPersonId \
  --alerting-mode SEQUENTIAL \
  --next-assistant-number-of-rings 4 \
  --rollover-enabled \
  --rollover-action VOICE_MESSAGING \
  --rollover-wait-time-in-secs 20

# Configure simultaneous alerting with forward rollover
wxcli user-settings update-alert Y2lzY29...execPersonId \
  --alerting-mode SIMULTANEOUS \
  --rollover-enabled \
  --rollover-action FORWARD \
  --rollover-forward-to-phone-number "+15559876543" \
  --rollover-wait-time-in-secs 30

# --- Assistant Assignment ---

# List assistants assigned to an executive
wxcli user-settings list-assigned-assistants Y2lzY29...execPersonId

# Search for available assistants by name
wxcli user-settings list-available-assistants Y2lzY29...execPersonId \
  --name "Jane Smith"

# Assign assistants to an executive (requires --json-body for the array)
wxcli user-settings update-assigned-assistants Y2lzY29...execPersonId \
  --json-body '{"assistants": [{"id": "Y2lzY29...asstPersonId"}]}'

# Remove all assistants (send null)
wxcli user-settings update-assigned-assistants Y2lzY29...execPersonId \
  --json-body '{"assistants": null}'

# --- Assistant Settings (from assistant's perspective) ---

# Read assistant settings (which executives they serve)
wxcli user-settings list-assistant Y2lzY29...asstPersonId

# --- Call Filtering ---

# Read executive call filtering settings
wxcli user-settings list-call-filtering Y2lzY29...execPersonId

# --- Screening ---

# Read screening settings for an executive
wxcli user-settings show-screening Y2lzY29...execPersonId

# Enable screening with ring splash alerts
wxcli user-settings update-screening Y2lzY29...execPersonId \
  --enabled --alert-type RING_SPLASH

# Disable screening
wxcli user-settings update-screening Y2lzY29...execPersonId --no-enabled
```

---

## 5. Call Policy

Controls Connected Line Identification Privacy on redirected calls.

- Feature path segment: `callPolicies`

> **Important:** This API is only available for **professional licensed workspaces** when accessed via admin tokens. The scopes shown (`workspaces_read/write`) are workspace-specific. There is no admin-level `people/{personId}` callPolicies endpoint. However, calling-licensed users can access their own call policy via the self-access endpoint (`/telephony/config/people/me/settings/callPolicies`) with the `spark:telephony_config_read/write` scope.

### Data Models

#### `PrivacyOnRedirectedCalls` (enum)

| Value | Meaning |
|-------|---------|
| `NO_PRIVACY` | Connected line identification is not blocked on redirected calls |
| `PRIVACY_FOR_EXTERNAL_CALLS` | Blocked on redirected calls to external numbers only |
| `PRIVACY_FOR_ALL_CALLS` | Blocked on all redirected calls |

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

> **WARNING: No admin-level person endpoint exists.** The path `people/{personId}/features/callPolicies` returns 404 for persons. Only the workspace admin path and the self-service `/me` path work.

**Base URL:** `https://webexapis.com/v1`

| Operation | Method | Endpoint | Token Type |
|-----------|--------|----------|------------|
| Read (workspace) | GET | `workspaces/{workspaceId}/features/callPolicies` | Admin |
| Update (workspace) | PUT | `workspaces/{workspaceId}/features/callPolicies` | Admin |
| Read (self) | GET | `telephony/config/people/me/settings/callPolicies` | User (calling-licensed) |
| Update (self) | PUT | `telephony/config/people/me/settings/callPolicies` | User (calling-licensed) |

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"

# Read call policy for a workspace (admin token)
result = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/callPolicies")
# Returns: {"connectedLineIdPrivacyOnRedirectedCalls": "NO_PRIVACY"|"PRIVACY_FOR_EXTERNAL_CALLS"|"PRIVACY_FOR_ALL_CALLS"}

# Update call policy for a workspace (admin token)
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/callPolicies",
                     json={"connectedLineIdPrivacyOnRedirectedCalls": "PRIVACY_FOR_EXTERNAL_CALLS"})

# Read call policy for self (calling-licensed user token, spark:telephony_config_read scope)
result = api.session.rest_get(f"{BASE}/telephony/config/people/me/settings/callPolicies")

# Update call policy for self (calling-licensed user token, spark:telephony_config_write scope)
api.session.rest_put(f"{BASE}/telephony/config/people/me/settings/callPolicies",
                     json={"connectedLineIdPrivacyOnRedirectedCalls": "PRIVACY_FOR_EXTERNAL_CALLS"})
```

### CLI Examples

> **Note:** Call Policy is only available for **workspaces** via admin CLI commands (`workspace-settings show-call-policies`, `update-call-policies`). There is no admin-level `people/{personId}` endpoint for call policy. Calling-licensed users can read/update their own call policy via the self-access endpoint (`/telephony/config/people/me/settings/callPolicies` with `spark:telephony_config_read/write` scope), but this requires user-level OAuth, not admin tokens.

```bash
# Read call policy for a workspace
wxcli workspace-settings show-call-policies Y2lzY29...workspaceId

# Set privacy for external calls only
wxcli workspace-settings update-call-policies Y2lzY29...workspaceId \
  --connected-line-id-privacy-on-redirected-calls PRIVACY_FOR_EXTERNAL_CALLS

# Set privacy for all redirected calls
wxcli workspace-settings update-call-policies Y2lzY29...workspaceId \
  --connected-line-id-privacy-on-redirected-calls PRIVACY_FOR_ALL_CALLS

# Remove privacy on redirected calls
wxcli workspace-settings update-call-policies Y2lzY29...workspaceId \
  --connected-line-id-privacy-on-redirected-calls NO_PRIVACY

# For person-level call policy, use the /me self-service endpoint (requires calling-licensed user token)
# NOTE: The admin path people/{personId}/features/callPolicies returns 404 for persons
curl -s -H "Authorization: Bearer $USER_TOKEN" \
  "https://webexapis.com/v1/telephony/config/people/me/settings/callPolicies" | python3 -m json.tool
```

---

## Scope Summary

| API Area | Read Scope | Write Scope |
|----------|-----------|-------------|
| Incoming Permissions | `spark-admin:people_read` | `spark-admin:people_write` or `spark:people_write` (self) |
| Outgoing Permissions (main) | `spark-admin:people_read` | `spark-admin:people_write` or `spark:people_write` (self) |
| Outgoing — Transfer Numbers (person) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Outgoing — Transfer Numbers (workspace) | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Outgoing — Access Codes (person) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Outgoing — Access Codes (workspace) | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Outgoing — Digit Patterns | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Feature Access | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Exec Assistant Type | `spark-admin:people_read` | `spark-admin:people_write` |
| Executive Settings (alert, filtering, screening, assistants) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Call Policy (workspace, admin) | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Call Policy (self, user token) | `spark:telephony_config_read` | `spark:telephony_config_write` |

---

## Gotchas (Cross-Cutting)

1. **Outgoing permissions `callingPermissions` is a list, not a dict.** The API returns and expects `callingPermissions` as an array of `{callType, action, transferEnabled}` objects. When using `--json-body` or raw HTTP, always send an array.

2. **Three different base paths across this doc.** Incoming/outgoing permissions and exec-assistant type use `people/{personId}/features/...`. Digit patterns and feature access use `telephony/config/people/{personId}/...`. Executive detailed settings use `telephony/config/people/{personId}/executive/...`. Mixing up the base path returns 404.

3. **Access codes `modify` uses a different scope.** Read/create/delete access codes require `workspaces_read/write`, but the modify (PUT) endpoint requires `telephony_config_write`. A service app with only workspace scopes can create and delete codes but cannot modify them.

4. **Executive assistant assignment is two steps.** You must first set both persons' types (one as `EXECUTIVE`, one as `EXECUTIVE_ASSISTANT`) via the type assignment API, then assign the assistant to the executive via `update-assigned-assistants`. Setting the type alone does not create the pairing.

5. **Some call types should be excluded from outgoing permission updates.** Call types such as `url_dialing`, `unknown`, and `casual` may appear in read responses but are not valid to include in write payloads. When using `--json-body`, only include call types you want to set.

6. **Feature access `reset` is a POST, not a DELETE.** Resetting a person's feature access to org defaults uses `POST .../actions/reset/invoke`, not a DELETE. Sending DELETE to this endpoint returns 405.

7. **Call Policy has NO admin-level person endpoint.** Live API testing confirms that `people/{personId}/features/callPolicies` returns 404 for persons. The only working paths are: (1) workspace admin: `workspaces/{workspaceId}/features/callPolicies`, and (2) self-service: `telephony/config/people/me/settings/callPolicies` (requires calling-licensed user token with `spark:telephony_config_read/write`). The `wxcli` commands (`show-call-policies`, `update-call-policies`) are under `workspace-settings` only.

8. **Transfer numbers and access codes scopes differ by entity type.** Per the OpenAPI spec, person-level transfer numbers and access codes endpoints (at `telephony/config/people/{personId}/outgoingPermission/...`) require `spark-admin:telephony_config_read/write`, not `workspaces_read/write`. The workspace scopes only apply to workspace-level endpoints.

---

## See Also

- **[Location Recording — Advanced](location-recording-advanced.md)** — Location-level supervisor settings and related administrative controls
- **[self-service-call-settings.md](self-service-call-settings.md)** -- User-level `/people/me/` endpoints for self-service call settings, including 6 user-only settings with no admin path.
