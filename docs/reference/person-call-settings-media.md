# Person Call Settings -- Voicemail, Caller ID, Privacy & Recording

Reference for per-person (also virtual line and workspace) call settings covering voicemail, caller ID, anonymous call rejection, privacy, barge-in, call recording, call intercept, monitoring, push-to-talk, and music on hold.

All APIs in this group follow the same structural pattern: they extend `PersonSettingsApiChild`, which builds REST endpoints using the formula `people/{person_id}/features/{feature}` for persons (with alternate URL patterns for workspaces, virtual lines, and locations). Each sub-API exposes a `read()` and `configure()` method pair, sometimes with additional action methods.

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

---

## 4. Anonymous Call Rejection

**API class:** `AnonCallsApi`
**Feature key:** `anonymousCallReject`
**Source:** `wxc_sdk/person_settings/anon_calls.py`

When enabled, blocks all incoming calls from unidentified or blocked caller IDs.

> **Note from source:** This API is documented as "only available for professional licensed workspaces," but the `PersonSettingsApiChild` base makes it usable for persons, virtual lines, and workspaces. <!-- NEEDS VERIFICATION: whether this works for persons or only workspaces in practice -->

### Methods

#### `read`

```python
AnonCallsApi.read(entity_id: str, org_id: str = None) -> bool
```

Returns a simple boolean: `True` if anonymous call rejection is enabled.

- **Scopes:** `spark-admin:people_read` <!-- NEEDS VERIFICATION: exact scope may differ for workspaces -->

#### `configure`

```python
AnonCallsApi.configure(entity_id: str, enabled: bool, org_id: str = None)
```

Enable or disable anonymous call rejection.

- Body: `{"enabled": true|false}`

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
| `summary_and_action_items_enabled` | `bool` | <!-- NEEDS VERIFICATION: undocumented field, SDK issue 201 --> |
| `transcript_enabled` | `bool` | <!-- NEEDS VERIFICATION: undocumented field, SDK issue 201 --> |

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

- **Scopes:** `spark-admin:people_write` (Note: the source docstring says `people_write` for read -- this may be a documentation error) <!-- NEEDS VERIFICATION: read scope may actually be people_read -->

#### `configure`

```python
CallRecordingApi.configure(entity_id: str, recording: CallRecordingSetting, org_id: str = None)
```

- **Scopes:** `spark-admin:people_write`
- **Gotcha:** When `notification.notification_type` is `None` (the enum value), the update method converts it to JSON `null` (the API returns the string `"None"` on reads but expects `null` on writes).
- Read-only fields (`service_provider`, `external_group`, `external_identifier`) are automatically excluded.

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
| Anonymous Call Rejection | <!-- NEEDS VERIFICATION --> | Yes (documented) | -- |
| Privacy | Yes | Yes | Yes |
| Barge-In | Yes | Yes | Yes |
| Call Recording | Yes | Yes | Yes |
| Call Intercept | Yes | Yes | Yes |
| Monitoring | Yes | Yes | -- |
| Push-to-Talk | Yes | Yes | Yes |
| Music on Hold | Yes | Yes | Yes |
