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

---

## 1. Common Base Classes

**Source**: `wxc_sdk/person_settings/common.py`

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
  <!-- NEEDS VERIFICATION -- the code constructs the URL as `telephony/config/people/telephony/config/people/{id}/applications/availableMembers/count` which may be a double-prefix bug -->

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

---

## 5. Call Bridge

**Source**: `wxc_sdk/person_settings/callbridge.py`
**API class**: `CallBridgeApi` (extends `PersonSettingsApiChild`, feature=`'callBridge'`)

Controls the UC-One call bridge feature (stutter dial tone when a person is bridged on an active shared line call).

**Not supported for Webex for Government (FedRAMP).**

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

---

## 6. Hoteling

**Source**: `wxc_sdk/person_settings/hoteling.py`
**API class**: `HotelingApi` (extends `PersonSettingsApiChild`, feature=`'hoteling'`)

Enables a person's phone profile (number, features, calling plan) to be temporarily loaded onto a shared (host) phone.

<!-- NEEDS VERIFICATION -- The source code contains a TODO comment: "this seems to be wrong. For workspace devices methods exist with complete coverage for all hoteling settings." The person-level API may be incomplete compared to the workspace-level hoteling API. -->

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
**Not supported for Webex for Government (FedRAMP).**

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

<!-- NEEDS VERIFICATION -- There are two enums (ECBNSelection and SelectedECBN) with overlapping values. ECBNSelection also includes NONE while SelectedECBN does not. The configure() method uses SelectedECBN. -->

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
  <!-- NEEDS VERIFICATION -- the docstring says "read-only administrator" can update, which is unusual -->
- **HTTP**: `PUT telephony/config/people/{entity_id}/emergencyCallbackNumber`
- **Body**: `{"selected": "<value>", "locationMemberId": "<optional>"}`

#### dependencies

```python
def dependencies(self, entity_id: str, org_id: str = None) -> ECBNDependencies
```

Retrieve ECBN dependencies -- whether this entity is used as a default ECBN by its location or by other members.

- **Scope**: `spark-admin:telephony_config_read` (full, user, read-only, or location admin)
- **HTTP**: `GET telephony/config/people/{entity_id}/emergencyCallbackNumber/dependencies`

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

---

## See Also

- **[Emergency Services Reference](emergency-services.md)** — Organization and location-level ECBN configuration, E911 providers, and emergency location management
- **[Devices — Core Reference](devices-core.md)** — Device management, hoteling host configuration, and shared-line appearance settings at the device level
