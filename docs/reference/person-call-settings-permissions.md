# Person Call Settings — Permissions, Executive & Feature Access

Reference for managing incoming/outgoing call permissions, feature access controls, executive/assistant pairing, and call policy settings via `wxc_sdk`.

**Source files:**
- `wxc_sdk/person_settings/permissions_in.py`
- `wxc_sdk/person_settings/permissions_out.py`
- `wxc_sdk/person_settings/feature_access/__init__.py`
- `wxc_sdk/person_settings/executive/__init__.py`
- `wxc_sdk/person_settings/exec_assistant.py`
- `wxc_sdk/person_settings/call_policy.py`

---

## 1. Incoming Permissions

Controls who can call a person and how incoming external calls can be transferred.

**API class:** `IncomingPermissionsApi` (extends `PersonSettingsApiChild`)
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

**Static helpers:**
- `IncomingPermissions.allow_all()` — custom enabled, allow all external, internal+collect enabled
- `IncomingPermissions.default()` — custom disabled, allow all external, internal+collect enabled

### Methods

#### `read`

```python
def read(self, entity_id: str, org_id: str = None) -> IncomingPermissions
```

Retrieve incoming permission settings for a person/entity.

- **Scope:** `spark-admin:people_read` (full, user, or read-only admin)
- **Returns:** `IncomingPermissions`

#### `configure`

```python
def configure(self, entity_id: str, settings: IncomingPermissions, org_id: str = None)
```

Update incoming permission settings for a person/entity.

- **Scope:** `spark-admin:people_write` (admin) or `spark:people_write` (self)

---

## 2. Outgoing Permissions

Controls what types of outbound calls a person can place, with per-call-type actions, transfer number routing, access codes, and digit pattern overrides.

**API class:** `OutgoingPermissionsApi` (extends `PersonSettingsApiChild`)
- Feature path segment: `outgoingPermission`
- Also used for: user, workspace, location, virtual line settings
- Sub-APIs: `transfer_numbers`, `access_codes`, `digit_patterns`

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

**Key methods:**
- `for_call_type(call_type)` — look up permission by `OutgoingPermissionCallType` enum or string
- `permissions_dict()` — returns `dict[str, CallTypePermission]`
- `CallingPermissions.allow_all()` — all call types allowed with transfer enabled
- `CallingPermissions.default()` — all allowed except `international`, `premium_services_i`, `premium_services_ii` (blocked, transfer disabled)

#### `OutgoingPermissions` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_enabled` | `Optional[bool]` | Use shared control for all outgoing categories |
| `use_custom_permissions` | `Optional[bool]` | Use specified outgoing calling permissions |
| `calling_permissions` | `Optional[CallingPermissions]` | Per-call-type permission settings |

> **Serialization note:** The API returns `callingPermissions` as a list of `{callType, action, transferEnabled}` objects. The SDK validator transforms this to/from the dict-based `CallingPermissions` model automatically. On `model_dump`, call types in `{'url_dialing', 'unknown', 'casual'}` are dropped by default.

#### `AutoTransferNumbers` (model)

| Field | Type | Description |
|-------|------|-------------|
| `use_custom_transfer_numbers` | `Optional[bool]` | Use custom transfer number settings |
| `auto_transfer_number1` | `Optional[str]` | Transfer destination for `TRANSFER_NUMBER_1` action |
| `auto_transfer_number2` | `Optional[str]` | Transfer destination for `TRANSFER_NUMBER_2` action |
| `auto_transfer_number3` | `Optional[str]` | Transfer destination for `TRANSFER_NUMBER_3` action |

**Property:** `configure_unset_numbers` — returns a copy with `None` numbers replaced by empty strings (required to clear a number via the API).

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
| `access_codes` | `Optional[list[AuthCode]]` | List of access codes (from `wxc_sdk.common.AuthCode`) |

### Methods — Main Outgoing Permissions

#### `read`

```python
def read(self, entity_id: str, org_id: str = None) -> OutgoingPermissions
```

Retrieve outgoing calling permissions.

- **Scope:** `spark-admin:people_read` (full, user, or read-only admin)

#### `configure`

```python
def configure(self, entity_id: str, settings: OutgoingPermissions,
              drop_call_types: set[str] = None, org_id: str = None)
```

Update outgoing calling permissions. The `drop_call_types` parameter excludes specific call type names from the update payload (defaults to `{'url_dialing', 'unknown', 'casual'}`).

- **Scope:** `spark-admin:people_write` (admin) or `spark:people_write` (self)

### Methods — Transfer Numbers (`OutgoingPermissionsApi.transfer_numbers`)

> **Scope note:** The SDK docstrings list `workspaces_read/write` scopes for Transfer Numbers. These scopes are confirmed for workspace entities. For person-level access, `spark-admin:people_read/write` may also work but this has not been verified. See the [Scope Summary](#scope-summary) footnote.

#### `read`

```python
def read(self, entity_id: str, org_id: str = None) -> AutoTransferNumbers
```

- **Scope:** `spark-admin:workspaces_read` or `spark:workspaces_read` (self)

#### `configure`

```python
def configure(self, entity_id: str, settings: AutoTransferNumbers, org_id: str = None)
```

- **Scope:** `spark-admin:workspaces_write` or `spark:workspaces_write` (self)

### Methods — Access Codes (`OutgoingPermissionsApi.access_codes`)

> Not available for locations — use the telephony-level access codes API.

> **Scope note:** The SDK docstrings list `workspaces_read/write` scopes for Access Codes. These scopes are confirmed for workspace entities. For person-level access, `spark-admin:people_read/write` may also work but this has not been verified. See the [Scope Summary](#scope-summary) footnote.

#### `read`

```python
def read(self, entity_id: str, org_id: str = None) -> AuthCodes
```

- **Scope:** `spark-admin:workspaces_read` or `spark:workspaces_read`

#### `create`

```python
def create(self, entity_id: str, code: str, description: str, org_id: str = None)
```

Create a new access code.

- **Scope:** `spark-admin:workspaces_write` or `spark:workspaces_write`

#### `modify`

```python
def modify(self, entity_id: str, use_custom_access_codes: bool = None,
           delete_codes: list[Union[str, AuthCode]] = None, org_id: str = None)
```

Modify access code settings. Can toggle custom codes on/off and delete specific codes (by code string or `AuthCode` object).

- **Scope:** `spark-admin:telephony_config_write`

#### `delete`

```python
def delete(self, entity_id: str, org_id: str = None)
```

Delete **all** access codes for the entity.

- **Scope:** `spark-admin:workspaces_write` or `spark:workspaces_write`

### Methods — Digit Patterns (`OutgoingPermissionsApi.digit_patterns`)

#### `get_digit_patterns`

```python
def get_digit_patterns(self, entity_id: str, org_id: str = None) -> DigitPatterns
```

- **Scope:** `spark-admin:telephony_config_read`

#### `details`

```python
def details(self, entity_id: str, digit_pattern_id: str, org_id: str = None) -> DigitPattern
```

- **Scope:** `spark-admin:telephony_config_read`

#### `create`

```python
def create(self, entity_id: str, pattern: DigitPattern, org_id: str = None) -> str
```

Returns the new digit pattern ID.

- **Scope:** `spark-admin:telephony_config_write`

#### `update_category_control_settings`

```python
def update_category_control_settings(self, entity_id: str,
                                     use_custom_digit_patterns: bool = None,
                                     org_id: str = None)
```

Toggle whether custom digit patterns are used.

- **Scope:** `spark-admin:telephony_config_write`

#### `update`

```python
def update(self, entity_id: str, settings: DigitPattern, org_id: str = None)
```

Update an existing digit pattern. Uses `settings.id` to identify which pattern.

- **Scope:** `spark-admin:telephony_config_write`

#### `delete`

```python
def delete(self, entity_id: str, digit_pattern_id: str, org_id: str = None)
```

- **Scope:** `spark-admin:telephony_config_write`

#### `delete_all`

```python
def delete_all(self, entity_id: str, org_id: str = None)
```

Delete all digit patterns for the entity.

- **Scope:** `spark-admin:telephony_config_write`

---

## 3. Feature Access Controls

Controls which Webex Calling features end users can modify via User Hub, Webex client, or IP phone.

**API class:** `FeatureAccessApi` (extends `ApiChild`, base=`'telephony'`)

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

### Methods

#### `read_default`

```python
def read_default(self) -> FeatureAccessSettings
```

Read the org-level default feature access settings applied to new users.

- **Scope:** `spark-admin:telephony_config_read`

#### `update_default`

```python
def update_default(self, settings: FeatureAccessSettings)
```

Update org-level default feature access settings.

- **Scope:** `spark-admin:telephony_config_write`

#### `read`

```python
def read(self, person_id: str) -> UserFeatureAccessSettings
```

Read feature access settings for a specific person.

- **Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(self, person_id: str, settings: FeatureAccessSettings)
```

Update feature access settings for a specific person.

- **Scope:** `spark-admin:telephony_config_write`

#### `reset`

```python
def reset(self, person_id: str)
```

Reset a person's feature access configuration back to org defaults. This is a POST to `.../actions/reset/invoke`.

- **Scope:** `spark-admin:telephony_config_write`

---

## 4. Executive / Assistant Settings

Full executive-assistant pairing, alerting, call filtering, and screening configuration.

### 4a. Exec Assistant Type Assignment

**API class:** `ExecAssistantApi` (extends `PersonSettingsApiChild`)
- Feature path segment: `executiveAssistant`

Simple API that reads or sets whether a person is an executive, an executive assistant, or unassigned.

#### `ExecAssistantType` (enum)

| Value | Meaning |
|-------|---------|
| `UNASSIGNED` | Feature not enabled |
| `EXECUTIVE` | Person is an executive |
| `EXECUTIVE_ASSISTANT` | Person is an executive assistant |

#### `read`

```python
def read(self, person_id: str, org_id: str = None) -> ExecAssistantType
```

- **Scope:** `spark-admin:people_read`

#### `configure`

```python
def configure(self, person_id: str, setting: ExecAssistantType, org_id: str = None)
```

- **Scope:** `spark-admin:people_write`

### 4b. Executive Settings (Detailed)

**API class:** `ExecutiveSettingsApi` (extends `ApiChild`, base=`''`)
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

### Executive Settings API Methods

All methods use the `ExecutiveSettingsApi` class.

**Read scope (all read methods):** `spark-admin:telephony_config_read`
**Write scope (all write methods):** `spark-admin:telephony_config_write`

#### Alert Settings

```python
def alert_settings(self, person_id: str, org_id: str = None) -> ExecAlert
def update_alert_settings(self, person_id: str, settings: ExecAlert, org_id: str = None)
```

#### Assigned Assistants

```python
def assigned_assistants(self, person_id: str, org_id: str = None) -> list[ExecOrAssistant]
def update_assigned_assistants(self, person_id: str, assistant_ids: list[str] = None, org_id: str = None)
```

To remove all assistants, pass `assistant_ids=None` (sends null).

#### Available Assistants

```python
def executive_available_assistants(self, person_id: str, name: str = None,
                                   phone_number: str = None, org_id: str = None) -> list[ExecOrAssistant]
```

Search for people available for assignment. Filter by `name` (first+last combo) or `phone_number`.

#### Executive Assistant Settings (from assistant's perspective)

```python
def executive_assistant_settings(self, person_id: str, org_id: str = None) -> AssistantSettings
def update_executive_assistant_settings(self, person_id: str, settings: AssistantSettings, org_id: str = None)
```

Read/update settings for a person who is configured **as an executive assistant** — includes the list of executives they serve.

#### Call Filtering Settings

```python
def executive_call_filtering_settings(self, person_id: str, org_id: str = None) -> ExecCallFiltering
def update_executive_call_filtering_settings(self, person_id: str, settings: ExecCallFiltering, org_id: str = None)
```

#### Call Filtering Criteria (CRUD)

```python
def create_call_filtering_criteria(self, person_id: str, settings: ExecCallFilteringCriteria,
                                   org_id: str = None) -> str  # returns criteria ID

def get_filtering_criteria(self, person_id: str, id: str,
                           org_id: str = None) -> ExecCallFilteringCriteria

def update_call_filtering_criteria(self, person_id: str, id: str,
                                   settings: ExecCallFilteringCriteria, org_id: str = None)

def delete_call_filtering_criteria(self, person_id: str, id: str, org_id: str = None)
```

#### Screening Settings

```python
def screening_settings(self, person_id: str, org_id: str = None) -> ExecScreening
def update_screening_settings(self, person_id: str, settings: ExecScreening, org_id: str = None)
```

---

## 5. Call Policy

Controls Connected Line Identification Privacy on redirected calls.

**API class:** `CallPolicyApi` (extends `PersonSettingsApiChild`)
- Feature path segment: `callPolicies`

> **Important:** This API is only available for **professional licensed workspaces**. The scopes shown (`workspaces_read/write`) are workspace-specific; for person-level use, `people_read/write` may apply instead, but this has not been verified. <!-- NEEDS VERIFICATION: Whether this also applies to persons or only workspaces -->

### Data Models

#### `PrivacyOnRedirectedCalls` (enum)

| Value | Meaning |
|-------|---------|
| `NO_PRIVACY` | Connected line identification is not blocked on redirected calls |
| `PRIVACY_FOR_EXTERNAL_CALLS` | Blocked on redirected calls to external numbers only |
| `PRIVACY_FOR_ALL_CALLS` | Blocked on all redirected calls |

### Methods

#### `read`

```python
def read(self, entity_id: str, org_id: str = None) -> PrivacyOnRedirectedCalls
```

- **Scope:** `spark-admin:workspaces_read`

#### `configure`

```python
def configure(self, entity_id: str,
              connected_line_id_privacy_on_redirected_calls: PrivacyOnRedirectedCalls,
              org_id: str = None)
```

- **Scope:** `spark-admin:workspaces_write`

---

## Scope Summary

| API Area | Read Scope | Write Scope |
|----------|-----------|-------------|
| Incoming Permissions | `spark-admin:people_read` | `spark-admin:people_write` or `spark:people_write` (self) |
| Outgoing Permissions (main) | `spark-admin:people_read` | `spark-admin:people_write` or `spark:people_write` (self) |
| Outgoing — Transfer Numbers | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Outgoing — Access Codes (read/create/delete) | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Outgoing — Access Codes (modify) | — | `spark-admin:telephony_config_write` |
| Outgoing — Digit Patterns | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Feature Access | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Exec Assistant Type | `spark-admin:people_read` | `spark-admin:people_write` |
| Executive Settings (alert, filtering, screening, assistants) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Call Policy | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |

<!-- NEEDS VERIFICATION: The scope annotations on TransferNumbersApi and AccessCodesApi reference workspaces_read/write even for person settings. The SDK docstrings copy workspace scope text — confirm whether spark-admin:people_read/write also works for person-level transfer numbers and access codes. -->

---

## Usage Patterns

### Setting per-call-type outgoing permissions

```python
from wxc_sdk.person_settings.permissions_out import (
    OutgoingPermissions, CallingPermissions, Action, OutgoingPermissionCallType
)

# Start with defaults (blocks international + premium)
perms = CallingPermissions.default()

# Also block operator-assisted
op = perms.for_call_type(OutgoingPermissionCallType.operator_assisted)
op.action = Action.block
op.transfer_enabled = False

settings = OutgoingPermissions(
    use_custom_enabled=True,
    use_custom_permissions=True,
    calling_permissions=perms
)

api.person_settings.permissions_out.configure(person_id, settings)
```

### Assigning an executive and assistant

```python
from wxc_sdk.person_settings.exec_assistant import ExecAssistantType

# Mark person as executive
api.person_settings.exec_assistant.configure(exec_person_id, ExecAssistantType.executive)

# Mark another person as assistant
api.person_settings.exec_assistant.configure(asst_person_id, ExecAssistantType.executive_assistant)

# Assign assistant to executive
api.person_settings.executive.update_assigned_assistants(exec_person_id, assistant_ids=[asst_person_id])
```

### Configuring executive alerting

```python
from wxc_sdk.person_settings.executive import (
    ExecAlert, ExecAlertingMode, ExecAlertRolloverAction
)

alert = ExecAlert(
    alerting_mode=ExecAlertingMode.sequential,
    next_assistant_number_of_rings=4,
    rollover_enabled=True,
    rollover_action=ExecAlertRolloverAction.voice_messaging,
    rollover_wait_time_in_secs=20
)

api.person_settings.executive.update_alert_settings(exec_person_id, alert)
```

### Restricting feature access for a user

```python
from wxc_sdk.person_settings.feature_access import FeatureAccessSettings, FeatureAccessLevel

settings = FeatureAccessSettings(
    call_forwarding=FeatureAccessLevel.no_access,
    simultaneous_ring=FeatureAccessLevel.no_access,
    voicemail=FeatureAccessLevel.full_access
)

api.person_settings.feature_access.update(person_id, settings)
```

---

## See Also

- **[Location Call Settings — Advanced](location-call-settings-advanced.md)** — Location-level supervisor settings and related administrative controls
