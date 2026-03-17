# Location Call Settings -- Recording, Supervisor, Guest Calling, Conference & Misc

Reference for advanced location-level and org-level call settings managed through the wxc_sdk. Covers call recording vendors and compliance, caller reputation (spam scoring), conference controls, supervisor/agent management, guest calling (click-to-call), operating modes, hot desking via voice portal, and shared forwarding patterns used across features.

---

## Table of Contents

1. [Call Recording](#1-call-recording)
2. [Caller Reputation](#2-caller-reputation)
3. [Conference Controls](#3-conference-controls)
4. [Supervisors](#4-supervisors)
5. [Guest Calling (Click-to-Call)](#5-guest-calling-click-to-call)
6. [Operating Modes](#6-operating-modes)
7. [Hot Desking Sign-in via Voice Portal](#7-hot-desking-sign-in-via-voice-portal)
8. [Forwarding (Shared Patterns)](#8-forwarding-shared-patterns)

---

## 1. Call Recording

**SDK module:** `wxc_sdk.telephony.call_recording`
**API class:** `CallRecordingSettingsApi` (base: `telephony/config`)
**Not supported** for Webex for Government (FedRAMP).

Call recording supports multiple third-party vendors. The org has an overall default vendor, but individual locations can override to a different vendor.

### 1.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 1.2 Data Models

#### `CallRecordingInfo`
Top-level org recording status.

| Field | Type | Notes |
|-------|------|-------|
| `organization` | `IdAndName` | Org id and name |
| `enabled` | `bool` | Whether call recording is enabled |
| `vendor_id` | `str` | Current vendor ID |
| `vendor_name` | `str` | Current vendor name |
| `terms_of_service_url` | `str` | Empty for Webex Recording Platform |

#### `CallRecordingTermsOfService`

| Field | Type | Notes |
|-------|------|-------|
| `vendor_id` | `str` | |
| `vendor_name` | `str` | |
| `terms_of_service_enabled` | `bool` | |
| `terms_of_service_url` | `str` | Empty for Webex Recording Platform |

#### `OrgComplianceAnnouncement`
Controls whether the recording START/STOP announcement plays on PSTN calls.

| Field | Type | Notes |
|-------|------|-------|
| `inbound_pstncalls_enabled` | `bool` | Alias: `inboundPSTNCallsEnabled` |
| `outbound_pstncalls_enabled` | `bool` | Alias: `outboundPSTNCallsEnabled` |
| `outbound_pstncalls_delay_enabled` | `bool` | Alias: `outboundPSTNCallsDelayEnabled` |
| `delay_in_seconds` | `int` | Seconds before announcement plays |

**Interaction note:** When the compliance announcement plays to the PSTN party and that party is connected to someone with call recording enabled, the start/stop announcement is inhibited.

#### `LocationComplianceAnnouncement` (extends `OrgComplianceAnnouncement`)

| Additional Field | Type | Notes |
|------------------|------|-------|
| `use_org_settings_enabled` | `bool` | Use org-level defaults |

#### `FailureBehavior` (Enum)
What happens when recording fails:

| Value | Behavior |
|-------|----------|
| `PROCEED_WITH_CALL_NO_ANNOUNCEMENT` | Call continues, no announcement |
| `PROCEED_CALL_WITH_ANNOUNCEMENT` | Call continues, announcement plays |
| `END_CALL_WITH_ANNOUNCEMENT` | Call ends with announcement |

#### `RecordingVendor`

| Field | Type |
|-------|------|
| `id` | `str` |
| `name` | `str` |
| `description` | `str` |
| `migrate_user_creation_enabled` | `bool` |
| `login_url` | `str` |
| `terms_of_service_url` | `str` |

#### `CallRecordingVendors` (org-level)

| Field | Type | Notes |
|-------|------|-------|
| `vendor_id` | `str` | Current vendor |
| `vendor_name` | `str` | |
| `vendors` | `list[RecordingVendor]` | All available vendors |
| `storage_region` | `str` | Only for Webex vendor |
| `failure_behavior` | `FailureBehavior` | |

#### `CallRecordingLocationVendors`

| Field | Type | Notes |
|-------|------|-------|
| `org_default_enabled` | `bool` | |
| `org_default_vendor_id` | `str` | |
| `org_default_vendor_name` | `str` | |
| `default_vendor_id` | `str` | Location-level vendor |
| `default_vendor_name` | `str` | |
| `vendors` | `list[RecordingVendor]` | |
| `org_storage_region_enabled` | `bool` | |
| `org_storage_region` | `str` | |
| `storage_region` | `str` | Location-level region |
| `org_failure_behavior_enabled` | `bool` | |
| `org_failure_behavior` | `FailureBehavior` | |
| `failure_behavior` | `FailureBehavior` | Location-level |

#### `CallRecordingRegion`

| Field | Type |
|-------|------|
| `code` | `str` — two-character region code |
| `name` | `str` |
| `default_enabled` | `bool` |

#### `RecordingUser`

| Field | Type |
|-------|------|
| `id` | `str` |
| `first_name` | `str` |
| `last_name` | `str` |
| `type` | `UserType` |
| `license_type` | `UserLicenseType` |

### 1.3 API Methods

```python
class CallRecordingSettingsApi:

    # --- Org-level recording on/off ---
    def read(self, org_id: str = None) -> CallRecordingInfo
    def update(self, enabled: bool, org_id: str = None)  # Cisco partners only

    # --- Terms of service ---
    def read_terms_of_service(self, vendor_id: str, org_id: str = None) -> CallRecordingTermsOfService
    def update_terms_of_service(self, vendor_id: str, enabled: bool, org_id: str = None)

    # --- Compliance announcement (org) ---
    def read_org_compliance_announcement(self, org_id: str = None) -> OrgComplianceAnnouncement
    def update_org_compliance_announcement(self, settings: OrgComplianceAnnouncement, org_id: str = None)

    # --- Compliance announcement (location) ---
    def read_location_compliance_announcement(self, location_id: str, org_id: str = None) -> LocationComplianceAnnouncement
    def update_location_compliance_announcement(self, location_id: str, settings: LocationComplianceAnnouncement, org_id: str = None)

    # --- Regions ---
    def get_call_recording_regions(self, org_id: str = None) -> list[CallRecordingRegion]

    # --- Vendor users (org) ---
    def list_org_users(self, standard_user_only: bool = None, org_id: str = None, **params) -> Generator[RecordingUser]

    # --- Vendor management (org) ---
    def get_org_vendors(self, org_id: str = None) -> CallRecordingVendors
    def set_org_vendor(self, vendor_id: str, storage_region: str = None,
                       failure_behavior: FailureBehavior = None, org_id: str = None) -> str  # returns jobId

    # --- Vendor management (location) ---
    def get_location_vendors(self, location_id: str, org_id: str = None) -> CallRecordingLocationVendors
    def set_location_vendor(self, location_id: str, id: str = None,
                            org_default_enabled: bool = None, storage_region: str = None,
                            org_storage_region_enabled: bool = None,
                            failure_behavior: FailureBehavior = None,
                            org_failure_behavior_enabled: bool = None,
                            org_id: str = None) -> str  # returns jobId

    # --- Vendor users (location) ---
    def list_location_users(self, location_id: str, standard_user_only: bool = None,
                            org_id: str = None, **params) -> Generator[RecordingUser]
```

### 1.4 Key Behaviors

- `set_org_vendor()` and `set_location_vendor()` return a **job ID** (string). Use the jobs API to check status if the change cannot be applied immediately (HTTP 200 with jobId vs. 204 for immediate).
- `update()` (enable/disable recording) is **Cisco partners only**.
- Storage region is **only applicable when vendor is Webex**; ignored for third-party vendors.
- `standard_user_only` parameter filters to Webex Calling standard license users only.

---

## 2. Caller Reputation

**SDK module:** `wxc_sdk.telephony.caller_reputation`
**API class:** `CallerReputationProviderApi` (base: `telephony/config/serviceSettings/callerReputationProvider`)

Integrates with external calling reputation providers for spam/fraud call scoring.

### 2.1 Data Models

#### `ReputationProviderSettings`

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Provider name |
| `id` | `str` | Provider ID |
| `client_id` | `str` | OAuth client ID for integration |
| `client_secret` | `str` | Write-only; not returned on read |
| `enabled` | `bool` | Service enabled/disabled |
| `call_block_score_threshold` | `str` | Score at which calls are blocked |
| `call_allow_score_threshold` | `str` | Score at which calls are allowed |

#### `ReputationProviderState` (Enum)

| Value | Meaning |
|-------|---------|
| `NOT_CONNECTED` | Not connected |
| `CONNECTING` | Connection in progress |
| `CONNECTED` | Connected |
| `ACTIVE` | Active and operational |
| `EXPIRED` | Session/token expired |
| `AUTH_FAILED` | Authentication failed |
| `PROVIDER_DISABLED` | Provider disabled |

#### `ReputationProviderStatus`

| Field | Type |
|-------|------|
| `id` | `str` |
| `status` | `ReputationProviderState` |

#### `ReputationProviderRegion`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `name` | `str` | |
| `type` | `str` | e.g., primary, secondary |
| `visible` | `bool` | |
| `environment_type` | `str` | e.g., production, staging |

#### `CallerReputationProviderProvider`

| Field | Type |
|-------|------|
| `id` | `str` |
| `enabled` | `bool` |
| `name` | `str` |
| `regions` | `list[ReputationProviderRegion]` |

### 2.2 API Methods

```python
class CallerReputationProviderApi:

    def get(self, organization_id: str = None) -> ReputationProviderSettings
    def update(self, settings: ReputationProviderSettings, organization_id: str = None)
    def unlock(self, rep_id: str, organization_id: str = None)
    def providers(self, organization_id: str = None) -> list[CallerReputationProviderProvider]
    def status(self, organization_id: str = None) -> ReputationProviderStatus
```

### 2.3 Key Behaviors

- **`client_secret` is write-only** -- it is never returned by `get()`. Only usable in `update()`.
- The `unlock()` method invokes `actions/unlock/invoke` -- use this when the provider is in a locked state (e.g., after auth failure). <!-- NEEDS VERIFICATION: exact conditions that trigger a locked state -->
- Note the parameter is `organization_id` (not `org_id`) in this API, differing from most other telephony APIs.
- Score thresholds are strings, not integers. <!-- NEEDS VERIFICATION: whether these are numeric strings or can contain non-numeric values -->

---

## 3. Conference Controls

**SDK module:** `wxc_sdk.telephony.conference`
**API class:** `ConferenceControlsApi` (base: `telephony/conference`)

Runtime conference call management (not configuration). This is a **call-control** API, not an admin config API.

### 3.1 Scopes

| Operation | Scope |
|-----------|-------|
| GET | `spark:calls_read` |
| All others | `spark:calls_write` |

### 3.2 Data Models

#### `ConferenceState` (Enum)

| Value | Meaning |
|-------|---------|
| `connected` | Host is active participant |
| `held` | Host has held the conference |
| `disconnected` | Conference released |

#### `ConferenceTypeEnum` (Enum)

| Value | Usage |
|-------|-------|
| `bargeIn` | Barge-in conference |
| `silentMonitoring` | Silent monitoring |
| `coaching` | Coaching session |

#### `ConferenceParticipant`

| Field | Type | Notes |
|-------|------|-------|
| `call_id` | `str` | Call identifier for this participant |
| `muted` | `bool` | |
| `deafened` | `bool` | Media not transmitted to participant |

#### `ConferenceDetails`

| Field | Type | Notes |
|-------|------|-------|
| `state` | `ConferenceState` | |
| `appearance` | `int` | Appearance index (if assigned) |
| `created` | `datetime` | ISO 8601 start time |
| `muted` | `bool` | Host muted |
| `type` | `ConferenceTypeEnum` | Only for non-standard conferences |
| `participants` | `list[ConferenceParticipant]` | |

### 3.3 API Methods

```python
class ConferenceControlsApi:

    def start_conference(self, call_ids: list[str], line_owner_id: str = None)
    def get_conference_details(self, line_owner_id: str = None) -> ConferenceDetails
    def release_conference(self, line_owner_id: str = None)
    def add_participant(self, call_id: str, line_owner_id: str = None)
    def hold(self, line_owner_id: str = None)
    def resume(self, line_owner_id: str = None)
    def mute(self, call_id: str = None)       # host if call_id omitted
    def unmute(self, call_id: str = None)      # host if call_id omitted
    def deafen_participant(self, call_id: str)
    def undeafen_participant(self, call_id: str)
```

### 3.4 Key Behaviors

- **`start_conference()`** requires a minimum of **two call IDs**. Each must identify an existing call between the invoking user and a participant.
- **`get_conference_details()`** returns an **empty JSON object** if no conference exists.
- **Mute vs. Deafen**: Muting stops a participant's audio from being transmitted to the conference. Deafening stops the conference audio from being transmitted to the participant. They are independent.
- **`mute()` / `unmute()`** operate on the host when `call_id` is omitted, or on a specific participant when provided.
- **`line_owner_id`** is used when invoking the API on behalf of a secondary line owner (user, workspace, or virtual line).
- For three-way calls (3WC), the Transfer API can be used instead of `release_conference()` to keep participants connected while the host drops.

---

## 4. Supervisors

**SDK module:** `wxc_sdk.telephony.supervisor`
**API class:** `SupervisorApi` (base: `telephony/config/supervisors`)

Supervisors manage call queue agents. They can silently monitor, coach, barge in, or take over calls their agents are handling.

### 4.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 4.2 Data Models

#### `AgentOrSupervisor`
Used for both supervisor and agent listings.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `first_name` | `str` | |
| `last_name` | `str` | |
| `display_name` | `str` | |
| `phone_number` | `str` | |
| `extension` | `str` | |
| `routing_prefix` | `str` | Location routing prefix |
| `esn` | `str` | Routing prefix + extension |
| `type` | `UserType` | Person, workspace, or virtual line |
| `has_cx_essentials` | `bool` | Has CX Essentials license |
| `agent_count` | `int` | Agents managed (supervisors only) |

#### `IdAndAction`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Person, workspace, or virtual line ID |
| `action` | `PatternAction` | `ADD` or `DELETE` |

#### `SupervisorAgentStatus`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `status` | `str` | Status result |
| `message` | `str` | Detail message |
| `type` | `UserType` | <!-- NEEDS VERIFICATION: undocumented field, SDK issue 202 --> |

### 4.3 API Methods

```python
class SupervisorApi:

    # --- List / search ---
    def list(self, name: str = None, phone_number: str = None, order: str = None,
             has_cx_essentials: bool = None, org_id: str = None,
             **params) -> Generator[AgentOrSupervisor]

    def available_supervisors(self, name: str = None, phone_number: str = None, order: str = None,
                              has_cx_essentials: bool = None, org_id: str = None,
                              **params) -> Generator[AgentOrSupervisor]

    def available_agents(self, name: str = None, phone_number: str = None, order: str = None,
                         has_cx_essentials: bool = None, org_id: str = None,
                         **params) -> Generator[AgentOrSupervisor]

    # --- CRUD ---
    def create(self, id: str, agents: list[str], has_cx_essentials: bool = None, org_id: str = None)
    def delete(self, supervisor_id: str, org_id: str = None)
    def delete_bulk(self, supervisors_ids: list[str], delete_all: bool = None, org_id: str = None)

    # --- Details and agent assignment ---
    def details(self, supervisor_id: str, name: str = None, phone_number: str = None,
                order: str = None, has_cx_essentials: bool = None,
                org_id: str = None, **additional_params) -> Generator[AgentOrSupervisor]

    def assign_unassign_agents(self, supervisor_id: str, agents: list[IdAndAction],
                               has_cx_essentials: bool = None,
                               org_id: str = None) -> Optional[list[SupervisorAgentStatus]]
```

### 4.4 Key Behaviors

- **A supervisor must have at least one agent** when created via `create()`.
- **`create()` takes agent IDs as a flat `list[str]`**, not `IdAndAction` objects. The SDK wraps them as `[{'id': agent_id}]` internally.
- **`assign_unassign_agents()`** uses `IdAndAction` with `PatternAction.ADD` or `PatternAction.DELETE` to add/remove agents in a single call. Returns `None` if all succeed, or a list of `SupervisorAgentStatus` with per-agent error details.
- **`delete_bulk()`** has a `delete_all` parameter. When set to `True`, the `supervisors_ids` array is ignored and **all supervisors in the org are removed**. Use with extreme caution.
- **CX Essentials vs. CX Basic**: The `has_cx_essentials` parameter gates which license tier you are querying/modifying. When `True`, returns/operates on CX Essentials supervisors only. When omitted or `False`, operates on CX Basic.
- **`details()`** returns a generator of the supervisor's assigned **agents** (not the supervisor's own details). The item key is `agents`.

---

## 5. Guest Calling (Click-to-Call)

**SDK module:** `wxc_sdk.telephony.guest_calling`
**API class:** `GuestCallingApi` (base: `telephony/config/guestCalling`)

Click-to-call allows external (guest) callers to reach internal destinations. Org-level setting.

### 5.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 5.2 Data Models

#### `GuestCallingSettings`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Click-to-call enabled |
| `privacy_enabled` | `bool` | Privacy mode |
| `video_enabled` | `bool` | <!-- NEEDS VERIFICATION: no docstring on this field in SDK --> |

#### `DestinationMember`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `first_name` | `str` | |
| `last_name` | `str` | |
| `phone_number` | `str` | |
| `extension` | `str` | |
| `routing_prefix` | `str` | |
| `esn` | `str` | |
| `type` | `OwnerType` | |
| `location` | `IdAndName` | |

### 5.3 API Methods

```python
class GuestCallingApi:

    def read(self, org_id: str = None) -> GuestCallingSettings
    def update(self, enabled: bool, privacy_enabled: bool,
               destination_members: list[str], org_id: str = None)
    def members(self, member_name: str = None, phone_number: str = None,
                extension: str = None, org_id: str = None,
                **params) -> Generator[DestinationMember]
    def available_members(self, member_name: str = None, phone_number: str = None,
                          extension: str = None, org_id: str = None,
                          **params) -> Generator[DestinationMember]
```

### 5.4 Key Behaviors

- **Supported destination types**: Auto Attendant, Call Queue, Hunt Group, and Virtual Line. Not individual users.
- **`update()` takes destination member IDs** as a flat `list[str]`, not full `DestinationMember` objects.
- **`members()`** returns currently assigned click-to-call destinations.
- **`available_members()`** returns destinations that can be added but are not yet assigned.
- All search parameters (`member_name`, `phone_number`, `extension`) use **contains** matching.

---

## 6. Operating Modes

**SDK module:** `wxc_sdk.telephony.operating_modes`
**API class:** `OperatingModesApi` (base: `telephony/config`)

Operating modes define time-based call routing rules (business hours, after hours, holidays, etc.) used by Auto Attendants, Call Queues, and Hunt Groups via mode-based forwarding.

### 6.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 6.2 Data Models

#### `OperatingModeSchedule` (Enum)

| Value | Meaning |
|-------|---------|
| `SAME_HOURS_DAILY` | Same schedule Mon-Fri and Sat-Sun |
| `DIFFERENT_HOURS_DAILY` | Per-day schedule |
| `HOLIDAY` | Holiday-based with recurrence |
| `NONE` | No schedule defined |

#### `DaySchedule`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Schedule active for this day/group |
| `all_day_enabled` | `bool` | Active entire day |
| `start_time` | `time` | HH:MM format |
| `end_time` | `time` | HH:MM format |

#### `SameHoursDaily`

| Field | Type |
|-------|------|
| `monday_to_friday` | `DaySchedule` |
| `saturday_to_sunday` | `DaySchedule` |

#### `DifferentHoursDaily`
Individual `DaySchedule` fields for: `sunday`, `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`.

#### `OperatingModeHoliday`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `name` | `str` | |
| `all_day_enabled` | `bool` | |
| `start_date` | `date` | YYYY-MM-DD format |
| `end_date` | `date` | |
| `start_time` | `time` | Required if `all_day_enabled` is false |
| `end_time` | `time` | Required if `all_day_enabled` is false |
| `recurrence` | `OperatingModeRecurrence` | |

#### `OperatingModeRecurrence`

| Field | Type |
|-------|------|
| `recur_yearly_by_date` | `OperatingModeRecurYearlyByDate` |
| `recur_yearly_by_day` | `OperatingModeRecurYearlyByDay` |

Two recurrence patterns: by date (day of month + month) or by day (day + week + month, e.g., "first Monday of September").

#### `OperatingMode`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `name` | `str` | |
| `type` | `OperatingModeSchedule` | |
| `level` | `ScheduleLevel` | Org or location |
| `location` | `IdAndName` | Required if level is LOCATION |
| `same_hours_daily` | `SameHoursDaily` | Present if type is `SAME_HOURS_DAILY` |
| `different_hours_daily` | `DifferentHoursDaily` | Present if type is `DIFFERENT_HOURS_DAILY` |
| `holidays` | `list[OperatingModeHoliday]` | Present if type is `HOLIDAY` |
| `call_forwarding` | `CallForwardingCommon` | Forwarding settings for this mode |

### 6.3 API Methods

```python
class OperatingModesApi:

    # --- CRUD ---
    def list(self, limit_to_location_id: str = None, name: str = None,
             limit_to_org_level_enabled: bool = None, order: str = None,
             org_id: str = None, **params) -> Generator[OperatingMode]

    def details(self, mode_id: str, org_id: str = None) -> OperatingMode
    def create(self, settings: OperatingMode, org_id: str = None) -> str  # returns mode ID
    def update(self, mode_id: str, settings: OperatingMode, org_id: str = None)
    def delete(self, mode_id: str, org_id: str = None)

    # --- Holiday management ---
    def holiday_details(self, mode_id: str, holiday_id: str, org_id: str = None) -> OperatingModeHoliday
    def holiday_create(self, mode_id: str, settings: OperatingModeHoliday, org_id: str = None) -> str  # returns holiday ID
    def holiday_update(self, mode_id: str, holiday_id: str, settings: OperatingModeHoliday, org_id: str = None)
    def holiday_delete(self, mode_id: str, holiday_id: str = None, org_id: str = None)

    # --- Availability queries ---
    def available_operating_modes(self, location_id: str, org_id: str = None) -> list[IdAndName]
    def call_forward_available_phone_numbers(self, location_id: str, phone_number: list[str] = None,
                                             owner_name: str = None, extension: str = None,
                                             org_id: str = None, **params) -> Generator[AvailableNumber]
```

### 6.4 Key Behaviors

- **Max 100 operating modes per location** and 100 per org. `available_operating_modes()` returns up to 200 (location + org combined).
- **Max 150 holidays per operating mode.**
- The `create()` method requires at least `name`, `type`, and `level` on the `OperatingMode` object. If `level` is LOCATION, `location.id` must be set.
- On `create()`, the SDK internally converts `location` to `locationId` and strips `id` from holidays. On `update()`, it additionally strips `type` and `level` (immutable after creation).
- `call_forward_available_phone_numbers()` lists PSTN numbers available as forwarding destinations for operating modes at a given location.
- The `list()` result is sorted ascending by operating mode name.

---

## 7. Hot Desking Sign-in via Voice Portal

**SDK module:** `wxc_sdk.telephony.hotdesking_voiceportal`
**API class:** `HotDeskingSigninViaVoicePortalApi` (base: `telephony/config`)

Hot desking allows users to sign in to a shared phone via the voice portal and make calls using their own phone number.

### 7.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 7.2 Data Models

#### `HotDeskingVoicePortalSetting`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | JSON alias: `voicePortalHotDeskSignInEnabled` |

Single boolean -- enables or disables hot desking sign-in via voice portal.

### 7.3 API Methods

```python
class HotDeskingSigninViaVoicePortalApi:

    # --- Location level ---
    def location_get(self, location_id: str, org_id: str = None) -> HotDeskingVoicePortalSetting
    def location_update(self, location_id: str, setting: HotDeskingVoicePortalSetting, org_id: str = None)

    # --- User level ---
    def user_get(self, person_id: str, org_id: str = None) -> HotDeskingVoicePortalSetting
    def user_update(self, person_id: str, setting: HotDeskingVoicePortalSetting, org_id: str = None)
```

### 7.4 Key Behaviors

- Location endpoint: `locations/{location_id}/features/hotDesking`
- User endpoint: `people/{person_id}/features/hotDesking/guest`
- This is a simple enable/disable toggle at both location and per-user levels.
- The user-level setting controls whether a specific user can act as a hot desking guest.

---

## 8. Forwarding (Shared Patterns)

**SDK module:** `wxc_sdk.telephony.forwarding`
**API class:** `ForwardingApi` (base: dynamic per feature)

Shared forwarding settings and selective rules used by **Call Queues**, **Hunt Groups**, and **Auto Attendants**. The `ForwardingApi` is instantiated with a `FeatureSelector` that determines which feature type it operates on.

### 8.1 Feature Selectors

```python
class FeatureSelector(str, Enum):
    queues = 'queues'
    huntgroups = 'huntGroups'
    auto_attendants = 'autoAttendants'
```

The API endpoint is constructed as:
```
telephony/config/locations/{location_id}/{feature}/​{feature_id}/callForwarding[/{path}]
```

### 8.2 Data Models

#### `CallForwarding`
Top-level forwarding configuration for a feature.

| Field | Type | Notes |
|-------|------|-------|
| `always` | `ForwardingSetting` | Forward all calls |
| `selective` | `ForwardingSetting` | Forward based on rules |
| `rules` | `list[ForwardingRule]` | Selective forwarding rules |
| `operating_modes` | `ForwardOperatingModes` | Mode-based forwarding |

#### `ForwardingSetting`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | |
| `destination` | `str` | Forwarding destination number |
| `ring_reminder_enabled` | `bool` | Brief tone on forwarded call |
| `destination_voice_mail_enabled` | `bool` | Forward to destination's voicemail |
| `send_to_voicemail_enabled` | `bool` | Send to voicemail |

#### `ForwardingRule`
Summary of a selective forwarding rule (returned in the rules list).

| Field | Type |
|-------|------|
| `id` | `str` |
| `name` | `str` |
| `calls_from` | `str` |
| `forward_to` | `str` |
| `calls_to` | `str` |
| `enabled` | `bool` |

#### `ForwardingRuleDetails`
Full details of a selective forwarding rule.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | |
| `id` | `str` | |
| `enabled` | `bool` | |
| `holiday_schedule` | `str` | Schedule name for when rule applies |
| `business_schedule` | `str` | Schedule name for when rule applies |
| `forward_to` | `ForwardTo` | |
| `calls_to` | `ForwardCallsTo` | List of numbers/extensions |
| `calls_from` | `CallsFrom` | |

#### `ForwardTo`

| Field | Type | Default |
|-------|------|---------|
| `selection` | `ForwardToSelection` | `FORWARD_TO_DEFAULT_NUMBER` |
| `phone_number` | `str` | |

#### `ForwardToSelection` (Enum)

| Value | Meaning |
|-------|---------|
| `FORWARD_TO_DEFAULT_NUMBER` | Use default forwarding number |
| `FORWARD_TO_SPECIFIED_NUMBER` | Use number in `phone_number` field |
| `DO_NOT_FORWARD` | Do not forward |

#### `ForwardFromSelection` (Enum)

| Value | Meaning |
|-------|---------|
| `ANY` | Match any caller |
| `CUSTOM` | Match specific callers only |

#### `CallsFrom`

| Field | Type | Default |
|-------|------|---------|
| `selection` | `ForwardFromSelection` | `ANY` |
| `custom_numbers` | `CustomNumbers` | |

#### `CustomNumbers`

| Field | Type | Default |
|-------|------|---------|
| `private_number_enabled` | `bool` | `False` |
| `unavailable_number_enabled` | `bool` | `False` |
| `numbers` | `list[str]` | |

#### `ForwardOperatingModes`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Operating modes enabled |
| `current_operating_mode_id` | `str` | Currently active mode |
| `exception_type` | `ExceptionType` | |
| `modes` | `list[ModeForward]` | Configured modes |

#### `ModeForward`

| Field | Type |
|-------|------|
| `normal_operation_enabled` | `bool` |
| `id` | `str` |
| `name` | `str` |
| `type` | `OperatingModeSchedule` |
| `level` | `ScheduleLevel` |
| `forward_to` | `ModeForwardTo` |

#### `ModeForwardTo`

| Field | Type | Notes |
|-------|------|-------|
| `selection` | `ForwardToSelection` | |
| `destination` | `str` | Required when selection is `FORWARD_TO_SPECIFIED_NUMBER` |
| `destination_voicemail_enabled` | `bool` | |
| `default_destination` | `str` | Operating mode's own destination |
| `default_destination_voicemail_enabled` | `bool` | |
| `default_forward_to_selection` | `ModeDefaultForwardToSelection` | |

### 8.3 API Methods

```python
class ForwardingApi:

    def __init__(self, session: RestSession, feature_selector: FeatureSelector)

    # --- Get/Update forwarding settings ---
    def settings(self, location_id: str, feature_id: str, org_id: str = None) -> CallForwarding
    def update(self, location_id: str, feature_id: str,
               forwarding: CallForwarding, org_id: str = None)

    # --- Selective forwarding rules ---
    def create_call_forwarding_rule(self, location_id: str, feature_id: str,
                                    forwarding_rule: ForwardingRuleDetails,
                                    org_id: str = None) -> str  # returns rule ID

    def call_forwarding_rule(self, location_id: str, feature_id: str,
                             rule_id: str, org_id: str = None) -> ForwardingRuleDetails

    def update_call_forwarding_rule(self, location_id: str, feature_id: str,
                                    rule_id: str, forwarding_rule: ForwardingRuleDetails,
                                    org_id: str = None) -> str  # returns new rule ID

    def delete_call_forwarding_rule(self, location_id: str, feature_id: str,
                                    rule_id: str, org_id: str = None)

    # --- Operating mode switch ---
    def switch_mode_for_call_forwarding(self, location_id: str, feature_id: str,
                                        org_id: str = None)
```

### 8.4 Key Behaviors

- **Rule ID changes on rename**: The Call Forwarding Rule ID will change when the rule name is modified via `update_call_forwarding_rule()`. The new ID is returned.
- **NANP number normalization**: The SDK automatically handles +1 prefix transformations. Numbers returned from the platform without a `+` prefix get `+1-` prepended. When serializing for API calls, `+1-` is stripped back off. Non-NANP numbers (those starting with `+`) are left as-is.
- **`switch_mode_for_call_forwarding()`** switches the feature's current operating mode back to normal operations.
- The `update()` method serializes with `exclude_unset=True`, so only fields you explicitly set are sent to the API. It also strips read-only fields (`calls_from`, `forward_to`, `calls_to`, `name`) from rule summaries in the rules list.
- **`CallForwarding.default()`** provides a safe starting point: always-forward disabled, selective disabled, empty rules list.
- Three forwarding modes are available simultaneously: always forward, selective rules, and operating mode-based. The API returns all three as part of the `CallForwarding` object.

---

## Cross-Reference: Scope Summary

| API | Read Scope | Write Scope |
|-----|-----------|-------------|
| Call Recording | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Caller Reputation | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Conference Controls | `spark:calls_read` | `spark:calls_write` |
| Supervisors | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Guest Calling | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Operating Modes | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Hot Desking Voice Portal | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Forwarding | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |

Note that Conference Controls uses **user-level** scopes (`spark:calls_*`), not admin scopes, because it is a runtime call-control API.
