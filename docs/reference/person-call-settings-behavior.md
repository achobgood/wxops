# Person Call Settings -- Behavior, Devices, Apps & Misc

SDK reference for person-level settings that control calling behavior, application/device configuration, shared lines, hoteling, receptionist, number management, preferred answer endpoints, MS Teams integration, mode management, personal assistant, and emergency callback numbers.

**Source**: `wxc_sdk.person_settings` submodules

---

## Table of Contents

1. [Common Base Classes](#1-common-base-classes)
2. [Calling Behavior](#2-calling-behavior)
3. [App Services](#3-app-services)
4. [App Shared Line](#4-app-shared-line)
5. [Call Bridge](#5-call-bridge)
6. [Hoteling](#6-hoteling)
7. [Receptionist Client](#7-receptionist-client)
8. [Numbers](#8-numbers)
9. [Available Numbers](#9-available-numbers)
10. [Preferred Answer Endpoint](#10-preferred-answer-endpoint)
11. [MS Teams](#11-ms-teams)
12. [Mode Management](#12-mode-management)
13. [Personal Assistant](#13-personal-assistant)
14. [Emergency Callback Number (ECBN)](#14-emergency-callback-number-ecbn)
15. [Monitoring](#15-monitoring)
16. [Push-to-Talk](#16-push-to-talk)
17. [Additional Discovered Endpoints](#17-additional-discovered-endpoints)

---

## 1. Common Base Classes

**Source**: `wxc_sdk/person_settings/common.py`

### Two Path Families

Person call settings endpoints split across two URL path families:

| Family | URL Pattern | Settings |
|--------|------------|----------|
| **Classic features** | `/v1/people/{personId}/features/{feature}` | callingBehavior, applications, hoteling, reception, numbers (GET only), monitoring, pushToTalk |
| **Telephony config** | `/v1/telephony/config/people/{personId}/{feature}` | emergencyCallbackNumber, singleNumberReach, musicOnHold, devices, callCaptions, selective rules, callBridge (via `features/callBridge`), personalAssistant (via `features/personalAssistant`), hotDesking/guest, agent/callerId, dectNetworks, preferredAnswerEndpoint, modeManagement/features, settings/msTeams |

**Important endpoint name mismatches** (SDK feature name vs. actual API path):

| SDK Feature Name | Actual API Path Segment | Full Path |
|-----------------|------------------------|-----------|
| `receptionist` | `reception` | `/people/{id}/features/reception` |
| `applicationServicesSettings` | `applications` | `/people/{id}/features/applications` |
| `pushToTalkSettings` | `pushToTalk` | `/people/{id}/features/pushToTalk` |
| `numbers` | `numbers` (two paths) | GET: `/people/{id}/features/numbers`, PUT: `/telephony/config/people/{id}/numbers` |

### ApiSelector (Enum)

Controls which URL path template the API child uses. The same API class can target different entity types.

| Value | URL prefix |
|-------|-----------|
| `person` | `people/{id}/features/{feature}` |
| `workspace` | `workspaces/{id}/features/{feature}` |
| `location` | `telephony/config/locations/{id}/{feature}` |
| `virtual_line` | `telephony/config/virtualLines/{id}/{feature}` |

### PersonSettingsApiChild

Base class for most person-settings APIs. Subclasses set a `feature` class attribute (e.g., `'callingBehavior'`, `'hoteling'`). The base class constructs the endpoint URL via `f_ep(person_id, path=None)` using the selector and feature prefix.

Some feature+selector combinations are remapped internally. For example, `('people', 'callBridge')` maps to `telephony/config/people/{id}/features/callBridge`, and `('people', 'emergencyCallbackNumber')` maps to `telephony/config/people/{id}/emergencyCallbackNumber`.

### CLI Examples

The `user-settings` command group covers most person-level call settings in this document. Use it as the primary CLI entry point for person behavior and feature configuration.

```bash
# List all available user-settings commands
wxcli user-settings --help

# Show a person's application services settings (section 3)
wxcli user-settings show <personId>

# Show calling behavior
wxcli user-settings show-calling-behavior <personId>

# Show hoteling settings
wxcli user-settings show-hoteling <personId>
```

---

## 2. Calling Behavior

**Source**: `wxc_sdk/person_settings/calling_behavior.py`
**API class**: `CallingBehaviorApi` (extends `PersonSettingsApiChild`, feature=`'callingBehavior'`)

Controls which Webex telephony application handles calls for a person. The organization has a default; individual persons can override it.

### Data Models

#### BehaviorType (Enum)

| Value | Constant |
|-------|----------|
| `NATIVE_WEBEX_TEAMS_CALLING` | `native` -- Webex Teams / Hybrid Calling |
| `CALL_WITH_APP_REGISTERED_FOR_CISCOTEL` | `cisco_tel` -- Cisco Jabber |
| `CALL_WITH_APP_REGISTERED_FOR_TEL` | `third_party` -- Third-party app |
| `CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL` | `webex_calling` -- Webex Calling app |
| `NATIVE_SIP_CALL_TO_UCM` | `native_sip_call_to_ucm` -- Calling in Webex Teams (Unified CM) |

#### CallingBehavior

| Field | Type | Description |
|-------|------|-------------|
| `behavior_type` | `Optional[BehaviorType]` | Current setting. `None` = use org default. |
| `effective_behavior_type` | `Optional[BehaviorType]` | Effective value (read-only, reflects org default when `behavior_type` is null). |
| `profile_id` | `Optional[str]` | UC Manager Profile ID. |

### Methods

#### read

```python
def read(self, person_id: str, org_id: str = None) -> CallingBehavior
```

Retrieve the calling behavior and UC Manager Profile for a person.

- **Scope**: `spark-admin:people_read` (full, user, or read-only admin)
- **HTTP**: `GET people/{person_id}/features/callingBehavior`

#### configure

```python
def configure(self, person_id: str, settings: CallingBehavior, org_id: str = None)
```

Update the calling behavior. The `effective_behavior_type` field is excluded from the PUT body (read-only).

- **Scope**: `spark-admin:people_write` (full or user admin)
- **HTTP**: `PUT people/{person_id}/features/callingBehavior`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read calling behavior
url = f"{BASE}/people/{person_id}/features/callingBehavior"
result = api.session.rest_get(url)
# Returns: {"behaviorType": "CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL", "effectiveBehaviorType": "...", "profileId": "..."}

# Update calling behavior
url = f"{BASE}/people/{person_id}/features/callingBehavior"
body = {
    "behaviorType": "CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL",  # or NATIVE_SIP_CALL_TO_UCM, etc.
    "profileId": "<uc-manager-profile-id>"  # optional, for UCM behavior
}
api.session.rest_put(url, json=body)
```

> **Note**: The URL path is `people/{person_id}/features/callingBehavior`, NOT `telephony/config/people/{person_id}/callingBehavior`.

**CLI**: `wxcli user-call-settings show-calling-behavior <personId>` / `update-calling-behavior <personId>`

---

## 3. App Services

**Source**: `wxc_sdk/person_settings/appservices.py`
**API class**: `AppServicesApi` (extends `ApiChild`, base=`''`)

Controls ringing behavior for specific scenarios (Click to Dial, Group Page, Call Park recalled) and which client platforms (browser, desktop, tablet, mobile) can use the Webex Calling application.

The `AppServicesApi` also holds a nested `shared_line` attribute (an `AppSharedLineApi` instance) -- see section 4.

### Data Model

#### AppServicesSettings

| Field | Type | Description |
|-------|------|-------------|
| `ring_devices_for_click_to_dial_calls_enabled` | `Optional[bool]` | Ring devices for outbound Click to Dial. |
| `ring_devices_for_group_page_enabled` | `Optional[bool]` | Ring devices for inbound Group Pages. |
| `ring_devices_for_call_park_enabled` | `Optional[bool]` | Ring devices for Call Park recalled. |
| `browser_client_enabled` | `Optional[bool]` | Browser (WebRTC) Webex Calling app enabled. |
| `browser_client_id` | `Optional[str]` | Device ID of WebRTC client (read-only, present only if enabled). |
| `desktop_client_enabled` | `Optional[bool]` | Desktop Webex Calling app enabled. |
| `desktop_client_id` | `Optional[str]` | Device ID of desktop client (read-only). |
| `tablet_client_enabled` | `Optional[bool]` | Tablet Webex Calling app enabled. |
| `tablet_client_id` | `Optional[str]` | Device ID of tablet client (read-only). |
| `mobile_client_enabled` | `Optional[bool]` | Mobile Webex Calling app enabled. |
| `mobile_client_id` | `Optional[str]` | Device ID of mobile client (read-only). |
| `available_line_count` | `Optional[int]` | Number of available device licenses (read-only). |

The `update()` helper method excludes read-only fields (`*_client_id`, `available_line_count`) from the serialized output.

### Methods

#### read

```python
def read(self, person_id: str, org_id: str = None) -> AppServicesSettings
```

Retrieve app services settings for a person.

- **Scope**: `spark-admin:telephony_config_read` (full, user, read-only, or location admin)
- **HTTP**: `GET people/{person_id}/features/applications`

#### configure

```python
def configure(self, person_id: str, settings: AppServicesSettings, org_id: str = None)
```

Update app services settings.

- **Scope**: `spark-admin:people_write` (full, user, or location admin)
- **HTTP**: `PUT people/{person_id}/features/applications`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read application services settings
url = f"{BASE}/people/{person_id}/features/applications"
result = api.session.rest_get(url)
# Returns: {"ringDevicesForClickToDialCallsEnabled": true, "browserClientEnabled": true, "desktopClientEnabled": true, ...}

# Update application services settings
url = f"{BASE}/people/{person_id}/features/applications"
body = {
    "ringDevicesForClickToDialCallsEnabled": True,
    "ringDevicesForGroupPageEnabled": True,
    "ringDevicesForCallParkEnabled": True,
    "browserClientEnabled": True,
    "desktopClientEnabled": True,
    "tabletClientEnabled": True,
    "mobileClientEnabled": True
}
api.session.rest_put(url, json=body)
```

**CLI**: `wxcli user-call-settings show <personId>` / `update <personId>`

---

## 4. App Shared Line

**Source**: `wxc_sdk/person_settings/app_shared_line.py`
**API class**: `AppSharedLineApi` (extends `ApiChild`, base=`'telephony/config/people'`)

Manages shared-line appearance (SLA) members on Webex Calling apps. Like hardware devices, applications support additional shared lines that can be monitored and utilized.

Accessed via `AppServicesApi.shared_line` or directly.

### Referenced Data Models (from `wxc_sdk.telephony.devices`)

- **`AvailableMember`** -- a person/workspace available for shared-line assignment
- **`DeviceMember`** -- a member currently assigned to a shared line
- **`DeviceMembersResponse`** -- response containing primary and secondary members

### Methods

#### search_members

```python
def search_members(self, person_id: str, order: str = None, location: str = None,
                   name: str = None, phone_number: str = None, extension: str = None,
                   **params) -> Generator[AvailableMember, None, None]
```

Search for members available for shared-line assignment to a Webex Calling app. Returns a paginated generator.

- **Scope**: `spark-admin:telephony_config_read`
- **HTTP**: `GET telephony/config/people/{person_id}/applications/availableMembers`

#### members_count

```python
def members_count(self, person_id: str, location_id: str = None,
                  member_name: str = None, phone_number: str = None,
                  extension: str = None, org_id: str = None) -> int
```

Get the count of members available for shared-line assignment.

- **Scope**: `spark-admin:telephony_config_read`
- **HTTP**: `GET telephony/config/people/{person_id}/applications/availableMembers/count`

#### get_members

```python
def get_members(self, person_id: str) -> DeviceMembersResponse
```

Get primary and secondary members currently assigned to a shared line on a Webex Calling app.

- **Scope**: `spark-admin:telephony_config_read`
- **HTTP**: `GET telephony/config/people/{person_id}/applications/members`

#### update_members

```python
def update_members(self, person_id: str,
                   members: list[Union[DeviceMember, AvailableMember]] = None)
```

Add or modify shared-line members. Accepts either `DeviceMember` or `AvailableMember` instances (the latter is auto-converted). Port indices are auto-assigned sequentially based on `line_weight`.

Fields sent per member: `member_id`, `port`, `primary_owner`, `line_type`, `line_weight`, `line_label`, `allow_call_decline_enabled`.

Pass an empty list (or `None`) to clear all members.

- **Scope**: `spark-admin:telephony_config_write`
- **HTTP**: `PUT telephony/config/people/{person_id}/applications/members`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Search available members for shared-line assignment
url = f"{BASE}/telephony/config/people/{person_id}/applications/availableMembers"
result = api.session.rest_get(url, params={"name": "John"})  # optional filters: location, phoneNumber, extension

# Get count of available members
url = f"{BASE}/telephony/config/people/{person_id}/applications/availableMembers/count"
result = api.session.rest_get(url)

# Get current shared-line members
url = f"{BASE}/telephony/config/people/{person_id}/applications/members"
result = api.session.rest_get(url)

# Update shared-line members
url = f"{BASE}/telephony/config/people/{person_id}/applications/members"
body = {
    "members": [
        {"memberId": "<id>", "port": 1, "primaryOwner": True, "lineType": "SHARED_CALL_APPEARANCE", "lineWeight": 1}
    ]
}
api.session.rest_put(url, json=body)
```

---

## 5. Call Bridge

**Source**: `wxc_sdk/person_settings/callbridge.py`
**API class**: `CallBridgeApi` (extends `PersonSettingsApiChild`, feature=`'callBridge'`)

Controls the UC-One call bridge feature (stutter dial tone when a person is bridged on an active shared line call).

**Not supported for Webex for Government (FedRAMP).** See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

Also used for virtual lines.

### Data Model

#### CallBridgeSetting

| Field | Type | Description |
|-------|------|-------------|
| `warning_tone_enabled` | `bool` | Enable/disable stutter dial tone for all participants when a person is bridged. |

### Methods

#### read

```python
def read(self, entity_id: str, org_id: str = None) -> CallBridgeSetting
```

Retrieve call bridge settings.

- **Scope**: `spark-admin:people_read` (full, user, read-only, or location admin)
- **HTTP**: `GET telephony/config/people/{entity_id}/features/callBridge`

#### configure

```python
def configure(self, entity_id: str, setting: CallBridgeSetting, org_id: str = None)
```

Update call bridge settings.

- **Scope**: `spark-admin:people_write` (full, user, or location admin)
- **HTTP**: `PUT telephony/config/people/{entity_id}/features/callBridge`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read call bridge settings
url = f"{BASE}/telephony/config/people/{person_id}/features/callBridge"
result = api.session.rest_get(url)
# Returns: {"warningToneEnabled": true}

# Update call bridge settings
url = f"{BASE}/telephony/config/people/{person_id}/features/callBridge"
body = {"warningToneEnabled": False}
api.session.rest_put(url, json=body)
```

### CLI Examples

```bash
# Show call bridge settings for a person
wxcli user-settings show-call-bridge <personId>

# Update call bridge settings
wxcli user-settings update-call-bridge <personId> --warning-tone-enabled true
```

---

## 6. Hoteling

**Source**: `wxc_sdk/person_settings/hoteling.py`
**API class**: `HotelingApi` (extends `PersonSettingsApiChild`, feature=`'hoteling'`)

Enables a person's phone profile (number, features, calling plan) to be temporarily loaded onto a shared (host) phone.

### Methods

#### read

```python
def read(self, person_id: str, org_id: str = None) -> bool
```

Returns a single `bool` indicating whether hoteling is enabled for the person.

- **Scope**: `spark-admin:people_read`
- **HTTP**: `GET people/{person_id}/features/hoteling`

#### configure

```python
def configure(self, person_id: str, enabled: bool, org_id: str = None)
```

Enable or disable hoteling for a person.

- **Scope**: `spark-admin:people_write`
- **HTTP**: `PUT people/{person_id}/features/hoteling`
- **Body**: `{"enabled": true/false}`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read hoteling settings
url = f"{BASE}/people/{person_id}/features/hoteling"
result = api.session.rest_get(url)
# Returns: {"enabled": true}

# Update hoteling settings
url = f"{BASE}/people/{person_id}/features/hoteling"
body = {"enabled": True}
api.session.rest_put(url, json=body)
```

**CLI**: `wxcli user-call-settings show-hoteling <personId>` / `update-hoteling <personId>`

### Gotchas

- **Person-level hoteling API may be incomplete.** The wxc_sdk source contains a TODO: "this seems to be wrong. For workspace devices methods exist with complete coverage for all hoteling settings." The person-level API only exposes a single boolean toggle (`enabled`), while workspace-level hoteling has richer configuration including host/guest settings and time limits. If you need full hoteling host configuration, use the workspace/device-level APIs instead.

---

## 7. Receptionist Client

**Source**: `wxc_sdk/person_settings/receptionist.py`
**API class**: `ReceptionistApi` (extends `PersonSettingsApiChild`, feature=`'reception'`)

Configures a person as a telephone attendant who can screen incoming calls to certain numbers within the organization. The receptionist monitors a list of people and/or workspaces.

### Data Model

#### ReceptionistSettings

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `Optional[bool]` | Enable/disable the receptionist client feature. Serialized as `receptionEnabled` (alias). |
| `monitored_members` | `Optional[list[Union[str, MonitoredMember]]]` | People/workspaces to monitor. For updates, can be a list of plain ID strings. |

**`MonitoredMember`** is from `wxc_sdk.common`.

### Methods

#### read

```python
def read(self, person_id: str, org_id: str = None) -> ReceptionistSettings
```

Retrieve receptionist client settings.

- **Scope**: `spark-admin:people_read`
- **HTTP**: `GET people/{person_id}/features/reception`

#### configure

```python
def configure(self, person_id: str, settings: ReceptionistSettings, org_id: str = None)
```

Update receptionist client settings.

**Validation rules enforced in the SDK**:
- `enabled` must not be `None` (mandatory for updates).
- If `monitored_members` is set, `enabled` must be `True`.

The member list is converted to a list of IDs for the API body (`monitoredMembers`), whether the input contains `str` IDs or `MonitoredMember` objects.

- **Scope**: `spark-admin:people_write`
- **HTTP**: `PUT people/{person_id}/features/reception`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read receptionist client settings
url = f"{BASE}/people/{person_id}/features/reception"
result = api.session.rest_get(url)
# Returns: {"receptionEnabled": true, "monitoredMembers": [{"id": "...", "displayName": "..."}]}

# Update receptionist client settings
url = f"{BASE}/people/{person_id}/features/reception"
body = {
    "receptionEnabled": True,
    "monitoredMembers": ["<member-id-1>", "<member-id-2>"]  # list of person/workspace IDs
}
api.session.rest_put(url, json=body)
```

**CLI**: `wxcli user-call-settings show-reception <personId>` / `update-reception <personId>`

---

## 8. Numbers

**Source**: `wxc_sdk/person_settings/numbers.py`
**API class**: `NumbersApi` (extends `PersonSettingsApiChild`, feature=`'numbers'`)

Manages a person's phone numbers, including primary and alternate numbers with distinctive ring patterns.

### Data Models

#### PersonPhoneNumber

| Field | Type | Description |
|-------|------|-------------|
| `primary` | `bool` | Flag indicating if this is the primary number. |
| `direct_number` | `Optional[str]` | Phone number. |
| `extension` | `Optional[str]` | Extension. |
| `routing_prefix` | `Optional[str]` | Routing prefix of the location. |
| `esn` | `Optional[str]` | Routing prefix + extension. |
| `ring_pattern` | `Optional[RingPattern]` | Ring pattern (alternate numbers only). |

#### PersonNumbers

| Field | Type | Description |
|-------|------|-------------|
| `distinctive_ring_enabled` | `bool` | Enable distinctive ring patterns for calls from specific numbers. |
| `phone_numbers` | `list[PersonPhoneNumber]` | List of phone numbers. |

#### UpdatePersonPhoneNumber

| Field | Type | Description |
|-------|------|-------------|
| `primary` | `Literal[False]` | Always `False` (cannot change primary via this API). |
| `action` | `PatternAction` | `ADD` or `DELETE`. |
| `external` | `str` | Phone number being assigned/removed. |
| `extension` | `Optional[str]` | Extension being assigned. |
| `ring_pattern` | `Optional[RingPattern]` | Ring pattern for the number. |

#### UpdatePersonNumbers

| Field | Type | Description |
|-------|------|-------------|
| `enable_distinctive_ring_pattern` | `Optional[bool]` | Enable/disable distinctive ring. |
| `phone_numbers` | `list[UpdatePersonPhoneNumber]` | Numbers to add or delete. |

### Methods

#### read

```python
def read(self, person_id: str, prefer_e164_format: bool = None, org_id: str = None) -> PersonNumbers
```

Get a person's phone numbers including alternate numbers.

- **Scope**: `spark-admin:people_read` (full or user admin)
- **HTTP**: `GET people/{person_id}/features/numbers`
- **Query param**: `preferE164Format` (optional) -- return numbers in E.164 format.

#### update

```python
def update(self, person_id: str, update: UpdatePersonNumbers, org_id: str = None)
```

Assign or unassign alternate phone numbers. Numbers must follow E.164 format (except US which also supports National format).

- **Scope**: `spark-admin:telephony_config_write` (full admin)
- **HTTP**: `PUT telephony/config/people/{person_id}/numbers`

Note: The update endpoint uses a different URL path (`telephony/config/people/...`) than the read endpoint (`people/.../features/numbers`).

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read phone numbers (read path uses people/ prefix)
url = f"{BASE}/people/{person_id}/features/numbers"
result = api.session.rest_get(url, params={"preferE164Format": "true"})  # optional
# Returns: {"distinctiveRingEnabled": true, "phoneNumbers": [{"primary": true, "directNumber": "+1...", "extension": "1234"}]}

# Update phone numbers (update path uses telephony/config/people/ prefix -- different from read!)
url = f"{BASE}/telephony/config/people/{person_id}/numbers"
body = {
    "enableDistinctiveRingPattern": True,
    "phoneNumbers": [
        {"primary": False, "action": "ADD", "external": "+14085551234", "ringPattern": "NORMAL"}
    ]
}
api.session.rest_put(url, json=body)
```

> **Gotcha**: Read and update use different URL prefixes. Read: `people/{id}/features/numbers`. Update: `telephony/config/people/{id}/numbers`.

**CLI**: `wxcli user-call-settings list-numbers <personId>`

### Gotchas

- **Read and update use different URL prefixes.** The read endpoint is `GET people/{id}/features/numbers` (under the `people` prefix), but the update endpoint is `PUT telephony/config/people/{id}/numbers` (under the `telephony/config` prefix). Using the wrong prefix will return a 404. This is one of the few person-settings APIs with mismatched read/write paths.
- **Cannot change primary number via this API.** The `UpdatePersonPhoneNumber` model forces `primary=False`. To change a person's primary number, use the people/provisioning API instead.
- **Update requires `spark-admin:telephony_config_write` scope**, not `spark-admin:people_write`. This differs from the read scope (`spark-admin:people_read`). Ensure your token has both scopes if doing read-then-update workflows.

---

## 9. Available Numbers

**Source**: `wxc_sdk/person_settings/available_numbers.py`
**API class**: `AvailableNumbersApi` (extends `ApiChild`, base=`'telephony/config'`)

Queries for phone numbers available for assignment to a person (or virtual line / workspace, depending on the `ApiSelector` used at construction). Each method targets a different assignment context.

### Data Models

#### AvailableNumber

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | `Optional[str]` | The phone number. |
| `extension` | `Optional[str]` | Extension for a PSTN number. |
| `state` | `Optional[NumberState]` | Phone number state. |
| `is_main_number` | `Optional[bool]` | Whether it is the location CLID. |
| `toll_free_number` | `Optional[bool]` | Whether it is toll-free. |
| `telephony_type` | `Optional[str]` | Telephony type (e.g., `MOBILE_NUMBER`). |
| `mobile_network` | `Optional[str]` | Mobile network (if mobile number). |
| `routing_profile` | `Optional[str]` | Routing profile (if mobile number). |
| `is_service_number` | `Optional[bool]` | High-utilization/concurrency PSTN number (not mobile, not toll-free). |
| `location` | `Optional[IdAndName]` | Location details. |
| `owner` | `Optional[NumberOwner]` | Owner details. |

#### AvailablePhoneNumberLicenseType (Enum)

| Value | Description |
|-------|-------------|
| `VAR_STANDARD` | Standard variable license |
| `VAR_BASIC` | Basic variable license |
| `Webex Calling Professional` | Professional license |
| `Webex Calling Standard` | Standard license |

### Method Availability Matrix

| Method | People | Virtual Lines | Workspaces |
|--------|--------|---------------|------------|
| `primary` | Yes | -- | -- |
| `secondary` | Yes | -- | Yes |
| `fax_message` | Yes | Yes | Yes |
| `call_forward` | Yes | Yes | Yes |
| `ecbn` | Yes | Yes | Yes |
| `available` | -- | Yes | Yes |
| `call_intercept` | Yes | -- | Yes |

### Methods

All methods return `Generator[AvailableNumber, None, None]` (paginated).

All require scope: `spark-admin:telephony_config_read`.

#### primary

```python
def primary(self, location_id: str = None, phone_number: list[str] = None,
            license_type: AvailablePhoneNumberLicenseType = None,
            org_id: str = None, **params) -> Generator[AvailableNumber, None, None]
```

List numbers available as a person's primary phone number. Returns standard and mobile numbers from all locations that are unassigned. `license_type` and `location_id` must align with the person's settings for correct assignment.

- **HTTP**: `GET telephony/config/people/primary/availableNumbers`

#### secondary

```python
def secondary(self, entity_id: str, phone_number: list[str] = None,
              org_id: str = None, **params) -> Generator[AvailableNumber, None, None]
```

List standard numbers available as a person's secondary phone number. Numbers are from the entity's location, active or inactive, unassigned.

- **HTTP**: `GET telephony/config/people/{entity_id}/secondary/availableNumbers`

#### fax_message

```python
def fax_message(self, entity_id: str, phone_number: list[str] = None,
                org_id: str = None, **params) -> Generator[AvailableNumber, None, None]
```

List standard numbers available as a FAX message number.

- **HTTP**: `GET telephony/config/people/{entity_id}/faxMessage/availableNumbers`

#### call_forward

```python
def call_forward(self, entity_id: str, phone_number: list[str] = None,
                 owner_name: str = None, extension: str = None,
                 org_id: str = None, **params) -> Generator[AvailableNumber, None, None]
```

List service and standard numbers available as call forward destinations.

- **HTTP**: `GET telephony/config/people/{entity_id}/callForwarding/availableNumbers`

#### ecbn

```python
def ecbn(self, entity_id: str, phone_number: list[str] = None,
         owner_name: str = None, org_id: str = None,
         **params) -> Generator[AvailableNumber, None, None]
```

List standard numbers available as emergency callback numbers.

- **HTTP**: `GET telephony/config/people/{entity_id}/emergencyCallbackNumber/availableNumbers`

#### available

```python
def available(self, location_id: str = None, phone_number: list[str] = None,
              org_id: str = None, **params) -> Generator[AvailableNumber, None, None]
```

List standard numbers available for assignment (virtual lines and workspaces only -- not people).

- **HTTP**: `GET telephony/config/{selector}/availableNumbers`

#### call_intercept

```python
def call_intercept(self, entity_id: str, phone_number: list[str] = None,
                   owner_name: str = None, extension: str = None,
                   org_id: str = None, **params) -> Generator[AvailableNumber, None, None]
```

List service and standard numbers available as call intercept numbers.

- **HTTP**: `GET telephony/config/people/{entity_id}/callIntercept/availableNumbers`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# List primary available numbers
url = f"{BASE}/telephony/config/people/primary/availableNumbers"
result = api.session.rest_get(url, params={"locationId": "<loc-id>"})

# List secondary available numbers
url = f"{BASE}/telephony/config/people/{person_id}/secondary/availableNumbers"
result = api.session.rest_get(url)

# List available ECBN numbers
url = f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber/availableNumbers"
result = api.session.rest_get(url)

# List available call forward numbers
url = f"{BASE}/telephony/config/people/{person_id}/callForwarding/availableNumbers"
result = api.session.rest_get(url)

# List available fax message numbers
url = f"{BASE}/telephony/config/people/{person_id}/faxMessage/availableNumbers"
result = api.session.rest_get(url)

# List available call intercept numbers
url = f"{BASE}/telephony/config/people/{person_id}/callIntercept/availableNumbers"
result = api.session.rest_get(url)
```

All return paginated arrays of `AvailableNumber` objects.

### CLI Examples

```bash
# List primary available phone numbers for a person
wxcli user-settings list-available-numbers-primary --location-id <locationId>

# List secondary available phone numbers for a person
wxcli user-settings list-available-numbers-secondary <personId>

# List available ECBN numbers for a person
wxcli user-settings list-available-numbers-emergency-callback-number <personId>

# List available call forward numbers for a person
wxcli user-settings list-available-numbers-call-forwarding <personId>

# List available fax message numbers for a person
wxcli user-settings list-available-numbers-fax-message <personId>

# List available call intercept numbers for a person
wxcli user-settings list-available-numbers-call-intercept <personId>
```

---

## 10. Preferred Answer Endpoint

**Source**: `wxc_sdk/person_settings/preferred_answer.py`
**API class**: `PreferredAnswerApi` (extends `ApiChild`, base=`'telephony/config/people'`)

Controls which device or application is the person's preferred answer endpoint. This preferred endpoint can be used by Call Control APIs: `/v1/telephony/calls/dial`, `/v1/telephony/calls/retrieve`, `/v1/telephony/calls/pickup`, `/v1/telephony/calls/barge-in`, `/v1/telephony/calls/answer`.

### Data Models

#### PreferredAnswerEndpointType (Enum)

| Value | Description |
|-------|-------------|
| `APPLICATION` | A software application endpoint |
| `DEVICE` | A hardware device endpoint |

#### PreferredAnswerEndpoint

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier. |
| `type` | `PreferredAnswerEndpointType` | Device or application. |
| `name` | `str` | Name (derived from device tag; if `name=<value>` tag is set, that value is used). |

#### PreferredAnswerResponse

| Field | Type | Description |
|-------|------|-------------|
| `preferred_answer_endpoint_id` | `Optional[str]` | Currently preferred endpoint ID (null if none set). |
| `endpoints` | `list[PreferredAnswerEndpoint]` | All endpoints available for selection. |

### Methods

#### read

```python
def read(self, person_id: str, org_id: str = None) -> PreferredAnswerResponse
```

Get the preferred answer endpoint and list of available endpoints.

- **Scope**: `spark:telephony_config_read` or `spark-admin:telephony_config_read`
- **HTTP**: `GET telephony/config/people/{person_id}/preferredAnswerEndpoint`

#### modify

```python
def modify(self, person_id: str, preferred_answer_endpoint_id: str, org_id: str = None)
```

Set or clear the preferred answer endpoint. Pass `None` for `preferred_answer_endpoint_id` to clear.

- **Scope**: `spark:telephony_config_write` or `spark-admin:telephony_config_write`
- **HTTP**: `PUT telephony/config/people/{person_id}/preferredAnswerEndpoint`
- **Body**: `{"preferredAnswerEndpointId": "<id_or_null>"}`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read preferred answer endpoint
url = f"{BASE}/telephony/config/people/{person_id}/preferredAnswerEndpoint"
result = api.session.rest_get(url)
# Returns: {"preferredAnswerEndpointId": "...", "endpoints": [{"id": "...", "type": "DEVICE", "name": "..."}]}

# Set preferred answer endpoint
url = f"{BASE}/telephony/config/people/{person_id}/preferredAnswerEndpoint"
body = {"preferredAnswerEndpointId": "<endpoint-id>"}  # or None to clear
api.session.rest_put(url, json=body)
```

### CLI Examples

```bash
# List preferred answer endpoint and all available endpoints for a person
wxcli user-settings list-preferred-answer-endpoint <personId>

# Set a preferred answer endpoint
wxcli user-settings update-preferred-answer-endpoint <personId> --preferred-answer-endpoint-id <endpointId>
```

### Gotchas

- **Preferred answer endpoint affects Call Control API behavior.** When set, the `/telephony/calls/dial`, `/telephony/calls/retrieve`, `/telephony/calls/pickup`, `/telephony/calls/barge-in`, and `/telephony/calls/answer` endpoints route to that preferred device/app. If the preferred endpoint is offline or unreachable, call control operations may fail silently or route unexpectedly.
- **Endpoint names derive from device tags.** The `name` field in `PreferredAnswerEndpoint` comes from the device's `name=<value>` tag. If no tag is set, the name may be a generic device model identifier, making it hard to distinguish between multiple devices of the same type.

---

## 11. MS Teams

**Source**: `wxc_sdk/person_settings/msteams.py`

Two API classes: one for person-level settings, one for org-level settings.

### Data Models

#### SettingsObject

| Field | Type | Description |
|-------|------|-------------|
| `setting_name` | `Optional[str]` | Name of the setting (e.g., `HIDE_WEBEX_APP`, `PRESENCE_SYNC`). |
| `level` | `Optional[str]` | Level at which the setting was applied. |
| `value` | `Optional[bool]` | Current boolean value. |
| `last_modified` | `Optional[datetime]` | When the setting was last updated. |

#### MSTeamsSettings (Person-level)

| Field | Type | Description |
|-------|------|-------------|
| `person_id` | `Optional[str]` | Person identifier. |
| `org_id` | `Optional[str]` | Organization identifier. |
| `settings` | `Optional[list[SettingsObject]]` | Array of settings. |

#### OrgMSTeamsSettings (Org-level)

| Field | Type | Description |
|-------|------|-------------|
| `level` | `Optional[str]` | Level at which settings are applied. |
| `org_id` | `Optional[str]` | Organization identifier. |
| `settings` | `Optional[list[SettingsObject]]` | Array of settings. |

### MSTeamsSettingApi (Person-level)

**Base**: `ApiChild`, base=`'telephony/config/people'`

#### read

```python
def read(self, person_id: str, org_id: str = None) -> MSTeamsSettings
```

Retrieve `HIDE_WEBEX_APP` and `PRESENCE_SYNC` settings for a person.

- **Scope**: `spark-admin:telephony_config_read` (full or read-only admin)
- **HTTP**: `GET telephony/config/people/{person_id}/settings/msTeams`

#### configure

```python
def configure(self, person_id: str, setting_name: str, value: bool, org_id: str = None)
```

Update a single MS Teams setting for a person.

- **Scope**: `spark-admin:telephony_config_write` (full admin)
- **HTTP**: `PUT telephony/config/people/{person_id}/settings/msTeams`
- **Body**: `{"settingName": "<name>", "value": true/false}`

Known setting names: `HIDE_WEBEX_APP`. Set `value` to `null` to delete the setting.

### OrgMSTeamsSettingApi (Org-level)

**Base**: `ApiChild`, base=`'telephony/config/settings/msTeams'`
**Not supported for Webex for Government (FedRAMP).** See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

#### read

```python
def read(self, org_id: str = None) -> OrgMSTeamsSettings
```

- **Scope**: `spark-admin:telephony_config_read`
- **HTTP**: `GET telephony/config/settings/msTeams`

#### configure

```python
def configure(self, setting_name: str, value: bool, org_id: str = None)
```

Update an org-level MS Teams setting. Valid `setting_name` values: `HIDE_WEBEX_APP`, `PRESENCE_SYNC`.

- **Scope**: `spark-admin:telephony_config_write`
- **HTTP**: `PUT telephony/config/settings/msTeams`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read person-level MS Teams settings
url = f"{BASE}/telephony/config/people/{person_id}/settings/msTeams"
result = api.session.rest_get(url)
# Returns: {"personId": "...", "settings": [{"settingName": "HIDE_WEBEX_APP", "value": true, ...}]}

# Update person-level MS Teams setting
url = f"{BASE}/telephony/config/people/{person_id}/settings/msTeams"
body = {"settingName": "HIDE_WEBEX_APP", "value": True}
api.session.rest_put(url, json=body)

# Read org-level MS Teams settings
url = f"{BASE}/telephony/config/settings/msTeams"
result = api.session.rest_get(url)

# Update org-level MS Teams setting
url = f"{BASE}/telephony/config/settings/msTeams"
body = {"settingName": "PRESENCE_SYNC", "value": True}
api.session.rest_put(url, json=body)
```

### CLI: `client-settings` (Org-Level MS Teams Settings)

The `client-settings` CLI group manages org-level MS Teams integration settings. These are the same settings documented above for `OrgMSTeamsSettingApi`, exposed as CLI commands.

| Command | Description |
|---------|-------------|
| `client-settings list` | Get org MS Teams settings |
| `client-settings update` | Update org MS Teams settings |

```bash
# Get current org-level MS Teams settings
wxcli client-settings list

# Enable presence sync between Webex and MS Teams
wxcli client-settings update --setting-name PRESENCE_SYNC --value

# Hide the Webex app for MS Teams users (org-wide)
wxcli client-settings update --setting-name HIDE_WEBEX_APP --value

# Disable the HIDE_WEBEX_APP setting
wxcli client-settings update --setting-name HIDE_WEBEX_APP --no-value
```

---

## 12. Mode Management

**Source**: `wxc_sdk/person_settings/mode_management.py`
**API class**: `ModeManagementApi` (extends `ApiChild`, base=`'telephony/config/people'`)

Manages operating mode assignments for a person. Feature identifiers (Auto Attendants, Call Queues, Hunt Groups) with mode-based call forwarding enabled can be assigned to a user. Maximum of 50 features per user.

### Data Models

#### FeatureType (Enum)

| Value | Description |
|-------|-------------|
| `AUTO_ATTENDANT` | Auto Attendant |
| `CALL_QUEUE` | Call Queue |
| `HUNT_GROUP` | Hunt Group |

#### AvailableFeature

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Optional[str]` | Feature identifier. |
| `name` | `Optional[str]` | Feature name. |
| `type` | `Optional[FeatureType]` | Feature type. |
| `phone_number` | `Optional[str]` | Primary phone number. |
| `extension` | `Optional[str]` | Extension. |

#### ExceptionType (Enum)

Describes how the current operating mode became active as an exception.

| Value | Description |
|-------|-------------|
| `MANUAL_SWITCH_BACK` | User manually switched; stays until manual switch back. |
| `AUTOMATIC_SWITCH_BACK_EARLY_START` | User started early; auto-switches at end time. |
| `AUTOMATIC_SWITCH_BACK_EXTENSION` | User extended current mode; auto-switches at extended end time (up to +12 hrs). |
| `AUTOMATIC_SWITCH_BACK_STANDARD` | Normal operation; stays until scheduled end time. |

#### ModeManagementFeature

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Optional[str]` | Feature identifier. |
| `name` | `Optional[str]` | Feature name. |
| `type` | `Optional[FeatureType]` | Feature type. |
| `phone_number` | `Optional[str]` | Primary phone number. |
| `extension` | `Optional[str]` | Extension. |
| `mode_based_forwarding_enabled` | `Optional[bool]` | Whether mode-based call forwarding is enabled. |
| `forward_destination` | `Optional[str]` | Call forwarding destination. |
| `current_operating_mode_name` | `Optional[str]` | Name of the current mode. |
| `current_operating_mode_id` | `Optional[str]` | ID of the current mode. |
| `exception_type` | `Optional[ExceptionType]` | How the current mode was activated. |
| `location` | `Optional[IdAndName]` | Location details. |

### Methods

#### available_features

```python
def available_features(self, person_id: str = None, name: str = None,
                       phone_number: str = None, extension: str = None,
                       order: str = None, org_id: str = None,
                       **params) -> Generator[AvailableFeature, None, None]
```

List features that can be assigned for mode management. Paginated.

- **Scope**: `spark-admin:telephony_config_read` (full, read-only, or location admin)
- **HTTP**: `GET telephony/config/people/{person_id}/modeManagement/availableFeatures`

#### assigned_features

```python
def assigned_features(self, person_id: str = None,
                      org_id: str = None) -> list[ModeManagementFeature]
```

List features already assigned to a user for mode management. Returns a plain list (not paginated).

- **Scope**: `spark-admin:telephony_config_read`
- **HTTP**: `GET telephony/config/people/{person_id}/modeManagement/features`

#### assign_features

```python
def assign_features(self, feature_ids: list[str], person_id: str = None,
                    org_id: str = None)
```

Assign features for mode management. Max 50 features.

- **Scope**: `spark-admin:telephony_config_write` (full or location admin)
- **HTTP**: `PUT telephony/config/people/{person_id}/modeManagement/features`
- **Body**: `{"featureIds": ["id1", "id2", ...]}`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# List available features for mode management
url = f"{BASE}/telephony/config/people/{person_id}/modeManagement/availableFeatures"
result = api.session.rest_get(url)

# List assigned features
url = f"{BASE}/telephony/config/people/{person_id}/modeManagement/features"
result = api.session.rest_get(url)

# Assign features (max 50)
url = f"{BASE}/telephony/config/people/{person_id}/modeManagement/features"
body = {"featureIds": ["<aa-id>", "<cq-id>", "<hg-id>"]}
api.session.rest_put(url, json=body)
```

### CLI Examples

```bash
# List available features for mode management assignment
wxcli user-settings list-available-features <personId>

# List features currently assigned to a user for mode management
wxcli user-settings list-mode-management <personId>

# Assign features to a user for mode management (max 50)
wxcli user-settings update-mode-management <personId> --json-body '{"featureIds": ["<aa-id>", "<cq-id>"]}'

# Additional mode-management commands (org-level mode operations)
wxcli mode-management list
wxcli mode-management show <featureId>
wxcli mode-management switch-mode-for-invoke-1 <featureId>
wxcli mode-management switch-to-normal <featureId>
```

---

## 13. Personal Assistant

**Source**: `wxc_sdk/person_settings/personal_assistant.py`
**API class**: `PersonalAssistantApi` (extends `ApiChild`, base=`''`)

Manages a user's incoming calls when they are away. Supports presence status, call transfer, and alerting behavior.

### Data Models

#### PersonalAssistantPresence (Enum)

| Value | Description |
|-------|-------------|
| `NONE` | Available |
| `BUSINESS_TRIP` | Gone for business trip |
| `GONE_FOR_THE_DAY` | Gone for the day |
| `LUNCH` | Gone for lunch |
| `MEETING` | In a meeting |
| `OUT_OF_OFFICE` | Out of office |
| `TEMPORARILY_OUT` | Temporarily out |
| `TRAINING` | In training |
| `UNAVAILABLE` | Unavailable |
| `VACATION` | On vacation |

#### PersonalAssistantAlerting (Enum)

| Value | Description |
|-------|-------------|
| `ALERT_ME_FIRST` | Ring the recipient first. |
| `PLAY_RING_REMINDER` | Reminder ring to the recipient. |
| `NONE` | No alert. |

#### PersonalAssistant

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `Optional[bool]` | Toggle the feature on/off. |
| `presence` | `Optional[PersonalAssistantPresence]` | Person's availability status. |
| `until_date_time` | `Optional[datetime]` | Date/time until which personal assistant is active. |
| `transfer_enabled` | `Optional[bool]` | Allow transfer and forwarding for the call type. |
| `transfer_number` | `Optional[str]` | Number to transfer to. |
| `alerting` | `Optional[PersonalAssistantAlerting]` | Alert type. |
| `alert_me_first_number_of_rings` | `Optional[int]` | Ring count when alerting is `ALERT_ME_FIRST` (range: 2-20). |

### Methods

#### get

```python
def get(self, person_id: str, org_id: str = None) -> PersonalAssistant
```

Retrieve personal assistant details.

- **Scope**: `spark-admin:telephony_config_read` (full, user, or read-only admin)
- **HTTP**: `GET telephony/config/people/{person_id}/features/personalAssistant`

#### update

```python
def update(self, person_id: str, settings: PersonalAssistant, org_id: str = None)
```

Update personal assistant settings. Only fields that are set (not unset) are included in the PUT body.

- **Scope**: `spark-admin:telephony_config_write` (full or user admin)
- **HTTP**: `PUT telephony/config/people/{person_id}/features/personalAssistant`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read personal assistant settings
url = f"{BASE}/telephony/config/people/{person_id}/features/personalAssistant"
result = api.session.rest_get(url)
# Returns: {"enabled": true, "presence": "MEETING", "transferEnabled": true, ...}

# Update personal assistant settings
url = f"{BASE}/telephony/config/people/{person_id}/features/personalAssistant"
body = {
    "enabled": True,
    "presence": "MEETING",
    "transferEnabled": True,
    "transferNumber": "+14085551234",
    "alerting": "ALERT_ME_FIRST",
    "alertMeFirstNumberOfRings": 3
}
api.session.rest_put(url, json=body)
```

---

## 14. Emergency Callback Number (ECBN)

**Source**: `wxc_sdk/person_settings/ecbn.py`
**API class**: `ECBNApi` (extends `PersonSettingsApiChild`, feature=`'emergencyCallbackNumber'`)

Manages the Emergency Callback Number for a person (also workspaces and virtual lines). Extension-only users must be set up with accurate ECBNs to make emergency calls.

### Data Models

#### ECBNSelection (Enum -- used for updates)

| Value | Description |
|-------|-------------|
| `DIRECT_LINE` | PSAP returns call directly to the member's number. |
| `LOCATION_ECBN` | Uses the location's configured ECBN (for users without dedicated numbers). |
| `LOCATION_MEMBER_NUMBER` | Uses another user's number at the same location (multi-floor/building scenarios). |

#### SelectedECBN (Enum -- also used for updates)

Same values as `ECBNSelection`: `DIRECT_LINE`, `LOCATION_ECBN`, `LOCATION_MEMBER_NUMBER`.

#### ECBNEffectiveLevel (Enum)

| Value | Description |
|-------|-------------|
| `DIRECT_LINE` | Member's own number. |
| `LOCATION_ECBN` | Location's configured ECBN. |
| `LOCATION_NUMBER` | Location's main number. |
| `LOCATION_MEMBER_NUMBER` | Another member's number at the location. |
| `NONE` | No selection. |

#### ECBNQuality (Enum)

| Value | Description |
|-------|-------------|
| `RECOMMENDED` | Activated number associated with a user or workspace. |
| `NOT_RECOMMENDED` | Activated number associated with a non-user entity (AA, Hunt Group, etc.). |
| `INVALID` | Inactive or non-existent number. |

#### PersonECBNDirectLine

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | `Optional[str]` | Callback phone number. |
| `first_name` | `Optional[str]` | User's first name. |
| `last_name` | `Optional[str]` | User's last name. |
| `effective_level` | `Optional[ECBNEffectiveLevel]` | Source of the emergency CLID. |
| `effective_value` | `Optional[str]` | Effective ECBN number (falls back to location main number). |
| `quality` | `Optional[ECBNQuality]` | Whether this is a recommended ECBN. |

#### ECBNLocationMember

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | `Optional[str]` | Callback phone number. |
| `first_name` | `Optional[str]` | First name. |
| `last_name` | `Optional[str]` | Last name. |
| `member_id` | `Optional[str]` | Member ID (user/place/virtual line). |
| `member_type` | `Optional[UserType]` | Member type. |
| `effective_level` | `Optional[ECBNLocationEffectiveLevel]` | Source of emergency CLID. |
| `effective_value` | `Optional[str]` | Effective ECBN number. |
| `quality` | `Optional[ECBNQuality]` | Recommendation status. |

#### ECBNDefault

| Field | Type | Description |
|-------|------|-------------|
| `effective_value` | `Optional[str]` | Effective ECBN number. |
| `quality` | `Optional[ECBNQuality]` | Recommendation status. |

#### PersonECBN (Read response)

| Field | Type | Description |
|-------|------|-------------|
| `selected` | `Optional[ECBNSelection]` | Current ECBN source selection. |
| `direct_line_info` | `Optional[PersonECBNDirectLine]` | Direct line ECBN data. |
| `location_ecbn_info` | `Optional[PersonECBNDirectLine]` | Location ECBN data (alias: `locationECBNInfo`). |
| `location_member_info` | `Optional[ECBNLocationMember]` | Location member ECBN data. |
| `default_info` | `Optional[ECBNDefault]` | Default fallback ECBN data. |

#### ECBNDependencies

| Field | Type | Description |
|-------|------|-------------|
| `is_location_ecbn_default` | `Optional[bool]` | Whether this person is the location's default ECBN. |
| `is_self_ecbn_default` | `Optional[bool]` | Whether this person is their own ECBN default. |
| `dependent_member_count` | `Optional[int]` | Number of members using this person as their ECBN. |

### Methods

#### read

```python
def read(self, entity_id: str, org_id: str = None) -> PersonECBN
```

Retrieve ECBN settings.

- **Scope**: `spark-admin:telephony_config_read` (full, user, read-only, or location admin)
- **HTTP**: `GET telephony/config/people/{entity_id}/emergencyCallbackNumber`

#### configure

```python
def configure(self, entity_id: str, selected: SelectedECBN,
              location_member_id: str = None, org_id: str = None)
```

Update the ECBN. When `selected` is `LOCATION_MEMBER_NUMBER`, pass `location_member_id` to specify which member's number to use.

- **Scope**: `spark-admin:telephony_config_write` (full, location, user, or read-only admin)
- **HTTP**: `PUT telephony/config/people/{entity_id}/emergencyCallbackNumber`
- **Body**: `{"selected": "<value>", "locationMemberId": "<optional>"}`

#### dependencies

```python
def dependencies(self, entity_id: str, org_id: str = None) -> ECBNDependencies
```

Retrieve ECBN dependencies -- whether this entity is used as a default ECBN by its location or by other members.

- **Scope**: `spark-admin:telephony_config_read` (full, user, read-only, or location admin)
- **HTTP**: `GET telephony/config/people/{entity_id}/emergencyCallbackNumber/dependencies`

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read ECBN settings
url = f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber"
result = api.session.rest_get(url)
# Returns: {"selected": "DIRECT_LINE", "directLineInfo": {...}, "locationECBNInfo": {...}, ...}

# Update ECBN
url = f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber"
body = {
    "selected": "LOCATION_MEMBER_NUMBER",  # DIRECT_LINE | LOCATION_ECBN | LOCATION_MEMBER_NUMBER
    "locationMemberId": "<member-id>"  # required when selected=LOCATION_MEMBER_NUMBER
}
api.session.rest_put(url, json=body)

# Read ECBN dependencies
url = f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber/dependencies"
result = api.session.rest_get(url)
# Returns: {"isLocationEcbnDefault": false, "isSelfEcbnDefault": true, "dependentMemberCount": 3}
```

### Gotchas

- **Two overlapping enums for ECBN selection.** The SDK defines both `ECBNSelection` and `SelectedECBN` with overlapping values (`DIRECT_LINE`, `LOCATION_ECBN`, `LOCATION_MEMBER_NUMBER`). `ECBNSelection` also includes `NONE`, while `SelectedECBN` does not. The `configure()` method uses `SelectedECBN`. When reading, the `selected` field uses `ECBNSelection` which may return `NONE`.
- **Read-only admin may have write access.** The docstring for `configure()` lists "read-only administrator" as a valid scope for updating ECBN, which is unusual. Most write operations require full or user admin.
- **Check dependencies before changing ECBN.** Use the `dependencies` endpoint before modifying a person's ECBN. If the person is the location's default ECBN or is used by other members (`dependentMemberCount > 0`), changing their number could break emergency callback for multiple users.

---

## 15. Monitoring
<!-- Updated by playbook session 2026-03-18 -->

**CLI file**: `src/wxcli/commands/user_call_settings.py`

Configures which users, call parks, and shared lines a person monitors (busy lamp field / BLF). Present in the CLI but not yet in the wxc_sdk person_settings docs for this file.

### Raw HTTP

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read monitoring settings
url = f"{BASE}/people/{person_id}/features/monitoring"
result = api.session.rest_get(url)
# Returns: {"enableCallParkNotification": true, "monitoredMembers": [...]}

# Update monitoring settings
url = f"{BASE}/people/{person_id}/features/monitoring"
body = {
    "enableCallParkNotification": True,
    "monitoredMembers": [{"id": "<member-id>"}]  # use --json-body for full control
}
api.session.rest_put(url, json=body)
```

**CLI**: `wxcli user-call-settings show-monitoring <personId>` / `update-monitoring <personId>`

### CLI Examples

```bash
# List monitoring settings (BLF / busy lamp field) for a person
wxcli user-settings list-monitoring <personId>

# Update monitoring settings (use --json-body for member list)
wxcli user-settings update-monitoring <personId> --json-body '{"enableCallParkNotification": true, "monitoredMembers": [{"id": "<member-id>"}]}'
```

---

## 16. Push-to-Talk
<!-- Updated by playbook session 2026-03-18 -->

**CLI file**: `src/wxcli/commands/user_call_settings.py`

Configures push-to-talk (intercom) settings for a person, including connection type, access control, and auto-answer. Present in the CLI but not yet in the wxc_sdk person_settings docs for this file.

### Raw HTTP

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# Read push-to-talk settings
url = f"{BASE}/people/{person_id}/features/pushToTalk"
result = api.session.rest_get(url)
# Returns: {"allowAutoAnswer": true, "connectionType": "TWO_WAY", "accessType": "ALLOW_MEMBERS", "members": [...]}

# Update push-to-talk settings
url = f"{BASE}/people/{person_id}/features/pushToTalk"
body = {
    "allowAutoAnswer": True,
    "connectionType": "TWO_WAY",  # ONE_WAY or TWO_WAY
    "accessType": "ALLOW_MEMBERS",  # ALLOW_MEMBERS or block pattern
    "members": [{"id": "<member-id>"}]  # use --json-body for full control
}
api.session.rest_put(url, json=body)
```

**CLI**: `wxcli user-call-settings show-push-to-talk <personId>` / `update-push-to-talk <personId>`

### CLI Examples

```bash
# List push-to-talk settings for a person
wxcli user-settings list-push-to-talk <personId>

# Update push-to-talk settings (use --json-body for member list and complex config)
wxcli user-settings update-push-to-talk <personId> --json-body '{"allowAutoAnswer": true, "connectionType": "TWO_WAY", "accessType": "ALLOW_MEMBERS", "members": [{"id": "<member-id>"}]}'
```

---

## 17. Additional Discovered Endpoints

The following endpoints were discovered via live API probing and are not yet covered by wxc_sdk person_settings modules. They all live under the telephony config path family.

### Hot Desking Guest

```
GET /v1/telephony/config/people/{personId}/features/hotDesking/guest
```

Returns hot desking guest configuration for a person. Likely controls whether a person can use hot desking as a guest on shared devices.

### Agent Caller ID

```
GET /v1/telephony/config/people/{personId}/agent/callerId
```

Returns the caller ID settings for a person when acting as a call queue or hunt group agent. Separate from the standard person-level caller ID.

### DECT Networks

```
GET /v1/telephony/config/people/{personId}/dectNetworks
```

Returns DECT network associations for a person. Lists which DECT networks/handsets are assigned to this user.

> **Note**: Call Bridge, Personal Assistant, Preferred Answer Endpoint, Mode Management, and MS Teams are also under the telephony config path family but are already documented in sections 5, 13, 10, 12, and 11 respectively.

---

## Scope Summary

| API | Read Scope | Write Scope |
|-----|-----------|-------------|
| Calling Behavior | `spark-admin:people_read` | `spark-admin:people_write` |
| App Services | `spark-admin:telephony_config_read` | `spark-admin:people_write` |
| App Shared Line | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Call Bridge | `spark-admin:people_read` | `spark-admin:people_write` |
| Hoteling | `spark-admin:people_read` | `spark-admin:people_write` |
| Receptionist | `spark-admin:people_read` | `spark-admin:people_write` |
| Numbers (read) | `spark-admin:people_read` | -- |
| Numbers (update) | -- | `spark-admin:telephony_config_write` |
| Available Numbers | `spark-admin:telephony_config_read` | -- |
| Preferred Answer | `spark(-admin):telephony_config_read` | `spark(-admin):telephony_config_write` |
| MS Teams | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Mode Management | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Personal Assistant | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| ECBN | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Monitoring | `spark-admin:people_read` | `spark-admin:people_write` |
| Push-to-Talk | `spark-admin:people_read` | `spark-admin:people_write` |

---

## Gotchas (Cross-Cutting)

- **Two distinct URL path families for person settings.** See the [Two Path Families](#two-path-families) table in section 1 for the complete mapping. Classic features use `people/{id}/features/{feature}`, while newer/specialized settings use `telephony/config/people/{id}/{feature}`. The Numbers API is the worst case: read uses `people/{id}/features/numbers` but update uses `telephony/config/people/{id}/numbers`. Always check the documented HTTP path for each method rather than assuming a pattern.
- **Scope mismatch between read and write.** Several APIs in this doc require different scopes for reading vs. writing. For example, App Services read needs `spark-admin:telephony_config_read` but write needs `spark-admin:people_write`. Numbers read needs `spark-admin:people_read` but update needs `spark-admin:telephony_config_write`. Service apps and integrations should request all four person-settings scopes (`people_read`, `people_write`, `telephony_config_read`, `telephony_config_write`) to avoid unexpected 403 errors.
- **`--json-body` required for nested settings.** Monitoring members, push-to-talk members, receptionist monitored members, shared-line members, and mode management feature assignments all require nested JSON arrays. The CLI generator skips deeply nested body fields, so use `--json-body '{...}'` for these operations.
- **Person vs. workspace API coverage differs.** Hoteling and call bridge have corresponding workspace-level APIs with richer configuration options. If the person-level API feels limited (e.g., hoteling returns only a boolean), check the workspace/device-level APIs in `docs/reference/devices-workspaces.md`.
- **my-settings endpoints require calling-licensed user token.** All `/people/me/*` variants of these endpoints return 404 (error 4008) if the authenticated user lacks a Webex Calling license. Use an admin token with `people/{personId}/` paths instead, or ensure the user token belongs to a calling-licensed user.

---

## See Also

- **[Emergency Services Reference](emergency-services.md)** — Organization and location-level ECBN configuration, E911 providers, and emergency location management
- **[Devices — Core Reference](devices-core.md)** — Device management, hoteling host configuration, and shared-line appearance settings at the device level
- **[self-service-call-settings.md](self-service-call-settings.md)** -- User-level `/people/me/` endpoints for self-service call settings, including 6 user-only settings with no admin path.
