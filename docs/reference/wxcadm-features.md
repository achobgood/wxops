# wxcadm Call Features Reference

Reference document covering wxcadm's call feature modules: Auto Attendant, Call Queue, Hunt Group, Pickup Group, Announcements (including Playlists), and Recording.

All source paths are relative to the `wxcadm` package root.

---

## Table of Contents

1. [Auto Attendant](#auto-attendant)
2. [Call Queue](#call-queue)
3. [Hunt Group](#hunt-group)
4. [Pickup Group](#pickup-group)
5. [Announcements](#announcements)
6. [Playlists](#playlists)
7. [Recording](#recording)
8. [wxcadm vs wxc_sdk Comparison](#wxcadm-vs-wxc_sdk-comparison)

---

## Auto Attendant

**Source:** `wxcadm/auto_attendant.py`

### Overview

Auto Attendants provide IVR menus that route callers based on key presses, extension dialing, or name dialing. wxcadm models them as an `AutoAttendantList` (a `UserList` subclass) containing `AutoAttendant` dataclass instances. The list can be scoped to the whole Org or to a single Location.

### AutoAttendantList

Collection class. Inherits `UserList`.

**Constructor:**

```python
AutoAttendantList(org: Org, location: Optional[Location] = None)
```

- When `location` is provided, only Auto Attendants at that Location are fetched.
- API endpoint: `GET v1/telephony/config/autoAttendants` (with optional `locationId` param).

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `refresh` | `refresh() -> bool` | `True` | Re-fetches the list from Webex |
| `get` | `get(id=None, name=None, spark_id=None, uuid=None) -> AutoAttendant \| None` | `AutoAttendant` or `None` | Looks up by ID, Name, UUID, or Spark ID (searched in that order). Raises `ValueError` if no argument provided. |
| `create` | See full signature below | `AutoAttendant` | Creates a new Auto Attendant at a Location |

**`create` full signature:**

```python
def create(self,
           name: str,
           first_name: str,
           last_name: str,
           phone_number: Optional[str],
           extension: Optional[str],
           business_hours_schedule: str,
           holiday_schedule: Optional[str],
           business_hours_menu: Optional[dict] = None,
           after_hours_menu: Optional[dict] = None,
           extension_dialing_scope: str = "GROUP",
           name_dialing_scope: str = "GROUP",
           language: Optional[str] = None,
           time_zone: Optional[str] = None,
           location: Optional[Location] = None
) -> AutoAttendant
```

- `phone_number` and/or `extension` must be provided (at least one).
- `business_hours_menu` / `after_hours_menu` default to a simple menu with key `0` = EXIT and extension dialing enabled.
- `language` and `time_zone` default to the Location's `announcement_language` and `time_zone`.
- `extension_dialing_scope` / `name_dialing_scope` accept `"GROUP"` or `"ENTERPRISE"`.
- `location` is required when the list is at the Org level; optional at the Location level.
- API endpoint: `POST v1/telephony/config/locations/{locationId}/autoAttendants`

### AutoAttendant

Dataclass representing a single Auto Attendant.

**Constructor fields:**

| Field | Type | Description |
|-------|------|-------------|
| `org` | `Org` | Parent Org (not shown in repr) |
| `id` | `str` | Webex ID |
| `data` | `dict` | Raw API response dict |

**Attributes set from list-level data (available immediately):**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | AA name |
| `location_id` | `str` | Owning Location ID |
| `phone_number` | `Optional[str]` | DID |
| `extension` | `Optional[str]` | Extension |
| `routing_prefix` | `Optional[str]` | Routing prefix |
| `esn` | `Optional[str]` | ESN |
| `toll_free_number` | `bool` | Whether the number is toll-free |

**Lazy-loaded properties (trigger a detail API call on first access):**

| Property | Type | Description |
|----------|------|-------------|
| `enabled` | `bool` | Whether the AA is enabled |
| `first_name` | `str` | Directory first name |
| `last_name` | `str` | Directory last name |
| `alternate_numbers` | `list` | Alternate numbers |
| `language` | `str` | Language display name |
| `language_code` | `str` | Language code (e.g. `en_us`) |
| `business_schedule` | `str` | Business hours schedule name |
| `holiday_schedule` | `str` | Holiday schedule name |
| `extension_dialing` | `str` | `GROUP` or `ENTERPRISE` |
| `name_dialing` | `str` | `GROUP` or `ENTERPRISE` |
| `time_zone` | `str` | Time zone string |
| `business_hours_menu` | `dict` | Business hours menu config |
| `after_hours_menu` | `dict` | After hours menu config |
| `spark_id` | `str` | Decoded Spark ID |
| `config` | `dict` | Full JSON config (always fetches fresh) |

**Additional properties and methods:**

| Member | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `call_forwarding` | `@property -> dict` | `dict` | Call Forwarding settings (GET `.../callForwarding`) |
| `copy_menu_from_template` | `copy_menu_from_template(source: AutoAttendant, menu_type: str = "both") -> bool` | `bool` | Copies business hours, after hours, or both menus from another AA. **Limitation:** does not work with CUSTOM announcements (only DEFAULT greetings). Accepts `"business_hours"`, `"after_hours"`, or `"both"`. |

**Detail API endpoint:** `GET v1/telephony/config/locations/{locationId}/autoAttendants/{id}`

---

## Call Queue

**Source:** `wxcadm/call_queue.py`

### Overview

Call Queues distribute incoming calls to a pool of agents with configurable routing policies, queue behavior, and overflow handling. wxcadm provides `CallQueueList`, `CallQueue`, and `OrgQueueSettings`.

### OrgQueueSettings

Dataclass (decorated with `@dataclass_json`) for org-wide queue settings. Related to Customer Experience Essentials features.

**Attributes:**

| Attribute | API Field | Type | Description |
|-----------|-----------|------|-------------|
| `maintain_queue_position_for_sim_ring` | `maintainQueuePositionForSimRingEnabled` | `bool` | Maintain queue position for Simultaneous routing |
| `agent_unavailable_on_bounce` | `forceAgentUnavailableOnBouncedEnabled` | `bool` | Mark agent unavailable when calls bounce |
| `play_barge_in_tone` | `playToneToAgentForBargeInEnabled` | `bool` | Notification tone for Supervisor Barge-In |
| `play_monitoring_tone` | `playToneToAgentForSilentMonitoringEnabled` | `bool` | Notification tone for Supervisor Silent Monitoring |
| `play_whisper_tone` | `playToneToAgentForSupervisorCoachingEnabled` | `bool` | Notification tone for Supervisor Coaching (whisper) |

**Methods:**

```python
def set(self,
        maintain_queue_position_for_sim_ring: Optional[bool] = None,
        agent_unavailable_on_bounce: Optional[bool] = None,
        play_barge_in_tone: Optional[bool] = None,
        play_monitoring_tone: Optional[bool] = None,
        play_whisper_tone: Optional[bool] = None
) -> bool
```

Sets one or more attributes and pushes to Webex via `PUT v1/telephony/config/queues/settings`.

### CallQueueList

Collection class. Inherits `UserList`.

**Constructor:**

```python
CallQueueList(org: Org, location: Optional[Location] = None)
```

- API endpoint: `GET v1/telephony/config/queues` (with optional `locationId` param).

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `refresh` | `refresh() -> bool` | `True` | Re-fetches the list from Webex |
| `get` | `get(id=None, name=None, spark_id=None, uuid=None) -> CallQueue \| None` | `CallQueue` or `None` | Looks up by ID, Name (case-insensitive), UUID, or Spark ID. Raises `ValueError` if no argument. |
| `create` | See full signature below | `CallQueue` | Creates a new Call Queue at a Location |

**`create` full signature:**

```python
def create(self,
           name: str,
           first_name: str,
           last_name: str,
           phone_number: Optional[str],
           extension: Optional[str],
           call_policies: dict,
           queue_settings: dict,
           language: Optional[str] = None,
           time_zone: Optional[str] = None,
           allow_agent_join: Optional[bool] = False,
           allow_did_for_outgoing_calls: Optional[bool] = False,
           location: Optional[Location] = None
) -> CallQueue
```

- `call_policies` and `queue_settings` are required dicts; their formats change frequently so consult developer.webex.com.
- `language` / `time_zone` default to the Location values.
- `location` required at Org level, implied at Location level.
- API endpoint: `POST v1/telephony/config/locations/{locationId}/queues`

### CallQueue

Represents a single Call Queue.

**Attributes (set on init from list data):**

| Attribute | Type | Description |
|-----------|------|-------------|
| `org` | `Org` | Parent Org |
| `id` | `str` | Webex ID |
| `name` | `str` | Queue name |
| `location_id` | `str` | Location ID |
| `phone_number` | `str` | DID |
| `extension` | `str` | Extension |
| `enabled` | `bool` | Whether the queue is enabled |

**Properties and methods:**

| Member | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `spark_id` | `@property -> str` | `str` | Decoded Spark ID |
| `config` | `@property -> dict` | `dict` | Full queue config (fetches fresh each time) |
| `call_forwarding` | `@property -> dict` | `dict` | Call Forwarding settings |
| `agents` | `@property -> list` | `list` | List of agents from the config |
| `add_agent` | `add_agent(agent: Person \| Workspace, weight=None, skill=None, joined=True) -> bool` | `bool` | **Not implemented** (`pass` in source) <!-- NEEDS VERIFICATION --> |
| `push` | `push() -> dict` | `dict` | Pushes `self.config` back to Webex via PUT |

**Method aliases:**

- `get_queue_config` = `config`
- `get_queue_forwarding` = `call_forwarding`

---

## Hunt Group

**Source:** `wxcadm/hunt_group.py`

### Overview

Hunt Groups route calls to a list of agents according to a call policy (simultaneous, regular/sequential, circular, weighted). wxcadm provides `HuntGroupList` and `HuntGroup`.

### HuntGroupList

Collection class. Inherits `UserList`.

**Constructor:**

```python
HuntGroupList(org: Org, location: Optional[Location] = None)
```

- API endpoint: `GET v1/telephony/config/huntGroups` (with optional `locationId` param).

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `refresh` | `refresh() -> bool` | `True` | Re-fetches from Webex |
| `get` | `get(id=None, name=None, spark_id=None, uuid=None) -> HuntGroup \| None` | `HuntGroup` or `None` | Case-insensitive name match. Raises `ValueError` if no argument. |
| `create` | See full signature below | `HuntGroup` | Creates a new Hunt Group |

> **Bug note:** The `get` method contains a typo on the `uuid` branch -- `item.spark_id.split('/')[-1].uppper()` should be `.upper()`. This will raise `AttributeError` at runtime when searching by UUID. <!-- NEEDS VERIFICATION -->

**`create` full signature:**

```python
def create(self,
           name: str,
           first_name: str,
           last_name: str,
           phone_number: Optional[str] = None,
           extension: Optional[str] = None,
           call_policies: Optional[dict] = None,
           enabled: bool = True,
           language: Optional[str] = None,
           time_zone: Optional[str] = None,
           location: Optional[Location] = None,
           agents: Optional[list] = None,
           allow_as_agent_caller_id: bool = False
) -> HuntGroup
```

- `call_policies` defaults to a SIMULTANEOUS policy with no forwarding if not provided. Example structure:

```python
{
    'policy': 'SIMULTANEOUS',    # or 'REGULAR', 'CIRCULAR', 'WEIGHTED'
    'waitingEnabled': False,
    'groupBusyEnabled': False,
    'allowMembersToControlGroupBusyEnabled': False,
    'noAnswer': {
        'nextAgentEnabled': False,
        'nextAgentRings': 5,
        'forwardEnabled': False,
        'numberOfRings': 15,
        'systemMaxNumberOfRings': 20,
        'destinationVoicemailEnabled': False
    },
    'busyRedirect': {
        'enabled': False,
        'destinationVoicemailEnabled': False,
    },
    'businessContinuityRedirect': {
        'enabled': False,
        'destinationVoicemailEnabled': False
    }
}
```

- `agents` accepts a list of `Person`, `Workspace`, or `VirtualLine` instances.
- `allow_as_agent_caller_id` maps to `huntGroupCallerIdForOutgoingCallsEnabled` in the API.
- API endpoint: `POST v1/telephony/config/locations/{locationId}/huntGroups`

### HuntGroup

Represents a single Hunt Group.

**Attributes (set on init):**

| Attribute | Type | Description |
|-----------|------|-------------|
| `org` | `Org` | Parent Org |
| `id` | `str` | Webex ID |
| `name` | `str` | Hunt Group name |
| `location_id` | `str` | Location ID |
| `enabled` | `bool` | Whether enabled |
| `phone_number` | `str` | DID |
| `extension` | `str` | Extension |

**Properties and methods:**

| Member | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `config` | `@property -> dict` | `dict` | Full config (fresh fetch) |
| `agents` | `@property -> list` | `list` | Agent list from config |
| `spark_id` | `@property -> str` | `str` | Decoded Spark ID |
| `add_agent` | `add_agent(agent: Person \| Workspace \| VirtualLine, weight: Optional[str] = None) -> bool` | `True` | Adds an agent. `weight` required only for WEIGHTED policy. Fetches current config, appends agent, PUTs the whole config back. |

---

## Pickup Group

**Source:** `wxcadm/pickup_group.py`

### Overview

Pickup Groups (Call Pickup) allow users in the same group to answer each other's ringing calls. wxcadm provides `PickupGroupList` and `PickupGroup`.

**Important:** Unlike the other features, `PickupGroupList` is Location-scoped only -- there is no Org-level constructor.

### PickupGroupList

Collection class. Inherits `UserList`.

**Constructor:**

```python
PickupGroupList(location: Location)
```

- Raises `ValueError` if `location` is not a `Location` instance.
- API endpoint: `GET v1/telephony/config/locations/{locationId}/callPickups`

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `get(id=None, name=None, spark_id=None) -> PickupGroup \| None` | `PickupGroup` or `None` | Looks up by ID, Name, or Spark ID. Raises `ValueError` if no argument. |

> **Note:** There is no `refresh`, `create`, or `delete` method on `PickupGroupList`. <!-- NEEDS VERIFICATION -->

### PickupGroup

Represents a single Pickup Group.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `location` | `Location` | Parent Location |
| `id` | `str` | Webex ID |
| `name` | `str` | Group name |
| `config` | `dict` | Raw JSON config from list response |

**Properties:**

| Property | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `users` | `@property -> list` | `list` | All agents in the group. Fetches detail via `GET .../callPickups/{id}`, then resolves each agent to a `Person`, `Workspace`, or `VirtualLine` instance by type (`PEOPLE`, `PLACE`, `VIRTUAL_LINE`). Falls back to raw dict for unknown types. |

---

## Announcements

**Source:** `wxcadm/announcements.py`

### Overview

Announcements are audio files (WAV) uploaded to Webex for use in Auto Attendants, Call Queues, and other call features. They can exist at the Organization level or at a specific Location level. wxcadm provides `AnnouncementList` and the `Announcement` dataclass.

### AnnouncementList

Collection class. Inherits `UserList`.

**Constructor:**

```python
AnnouncementList(org: Org)
```

- Always fetches all announcements (both Org-level and Location-level) by passing `locationId=all`.
- API endpoint: `GET v1/telephony/config/announcements?locationId=all`

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `get(id=None, name=None, file_name=None, level=None, location=None) -> Announcement \| list[Announcement] \| None` | Single, list, or `None` | Filters announcements by any combination of criteria. `name` uses substring match (`in`). Returns a single `Announcement` if exactly one match, a list if multiple, `None` if zero. |
| `get_by_location_id` | `get_by_location_id(location_id: str) -> list[Announcement]` | `list` | Returns Location-level announcements for a given Location ID. Does not include Org-level announcements. |
| `get_by_id` | `get_by_id(id: str) -> Announcement \| None` | `Announcement` or `None` | Exact ID match |
| `upload` | `upload(name: str, filename: str, location: str \| Location = None) -> str` | `str` (new ID) | Uploads a WAV file. If `location` is provided (as ID string or `Location` instance), uploads at Location level; otherwise uploads at Org level. Uses `MultipartEncoder` from `requests_toolbelt`. |

**Properties:**

| Property | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `stats` | `@property -> dict` | `dict` | Repository usage stats (`GET v1/telephony/config/announcements/usage`) |

### Announcement

Dataclass for a single announcement.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `org` | `Org` | Parent Org (not in repr) |
| `id` | `str` | Announcement ID |
| `name` | `str` | Display name |
| `fileName` | `str` | Name of the uploaded file |
| `fileSize` | `str` | File size in bytes (note: stored as `str`) |
| `mediaFileType` | `str` | File type (e.g. `WAV`) |
| `lastUpdated` | `str` | Timestamp of last update |
| `level` | `str` | `ORGANIZATION` or `LOCATION` |
| `location` | `dict \| None` | Location dict (only for `LOCATION`-level) |

**Properties:**

| Property | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `used_by` | `@property -> list` | `list[dict]` | List of call features using this announcement. Each dict has `id`, `name`, `type`, `location` (resolved to `Location` instance). For Call Queue type, also includes an `instance` key with the `CallQueue` object. |
| `in_use` | `@property -> bool` | `bool` | Whether the announcement is assigned to any feature |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `replace_file` | `replace_file(filename: str) -> bool` | `True` | Replaces the audio file with a new WAV. Uses `PUT` with `MultipartEncoder`. Works for both Org and Location level. |
| `delete` | `delete() -> bool` | `True` or `False` | Deletes the announcement. Returns `False` immediately if `in_use` is True (does not attempt the API call). |

---

## Playlists

**Source:** `wxcadm/announcements.py` (same file as Announcements)

### Overview

Playlists are ordered collections of Announcements that can be assigned to Locations for music-on-hold or similar use. wxcadm provides `PlaylistList` and the `Playlist` dataclass (decorated with `@dataclass_json`).

### PlaylistList

Collection class. Inherits `UserList`.

**Constructor:**

```python
PlaylistList(parent: Org)
```

- API endpoint: `GET v1/telephony/config/announcements/playlists`

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `get(id='', name='') -> Playlist \| None` | `Playlist` or `None` | Looks up by ID or Name |
| `create` | `create(name: str, announcements: list[Announcement]) -> Playlist` | `Playlist` | Creates a new Playlist from a list of Announcement instances |

### Playlist

Dataclass (with `@dataclass_json`) for a single playlist.

**Init fields:**

| Field | API Field | Type | Description |
|-------|-----------|------|-------------|
| `org` | -- | `Org` | Parent Org (not in repr) |
| `id` | `id` | `str` | Playlist ID |
| `name` | `name` | `str` | Playlist name |
| `file_count` | `fileCount` | `int` | Number of files in the playlist |
| `last_updated` | `lastUpdated` | `str` | Last update timestamp |
| `in_use` | `isInUse` | `bool` | Whether the playlist is in use (default `False`) |
| `location_count` | `locationCount` | `int` | Number of assigned Locations (default `0`) |

**Lazy-loaded fields (fetched via `__getattr__` on first access):**

| Field | Type | Description |
|-------|------|-------------|
| `file_size` | `int` | Total file size in bytes |
| `announcements` | `list` | List of `Announcement` instances in the playlist |

> **Bug note:** The `__getattr__` method uses `"fv1/telephony/config/announcements/playlists/{self.id}"` as the URL -- the leading `f` is outside the f-string, producing a literal URL starting with `fv1/...`. The `refresh()` method uses the correct URL. This will likely cause the lazy-load to fail. <!-- NEEDS VERIFICATION -->

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `refresh` | `refresh() -> bool` | `True` | Refreshes all playlist details from the API |
| `delete` | `delete() -> bool` | `True` | Deletes the playlist |
| `replace_announcements` | `replace_announcements(announcements: list[Announcement]) -> bool` | `True` | Replaces all announcements in the playlist |

**Properties:**

| Property | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `locations` | `@property -> list[Location]` | `list[Location]` | Locations the playlist is assigned to |

**Additional methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `assign_to_location` | `assign_to_location(location: Location) -> bool` | `True` | Assigns the playlist to a Location (preserves existing Location assignments and appends the new one) |

---

## Recording

**Source:** `wxcadm/recording.py`

### Overview

The recording module covers three concerns:

1. **Recording vendor selection** (Org and Location level) -- which provider records calls and what happens on failure.
2. **Compliance announcements** -- the tone/announcement played to inform parties that a call is being recorded.
3. **Converged Recordings** -- accessing, downloading, transcribing, and managing actual recording files.

### RecordingVendor / RecordingVendorsList

**`RecordingVendor`** is a `@dataclass_json` dataclass.

| Field | API Field | Type | Description |
|-------|-----------|------|-------------|
| `id` | `id` | `str` | Vendor ID |
| `name` | `name` | `str` | Vendor name |
| `description` | `description` | `str` | Vendor description |
| `auto_user_account_creation` | `migrateUserCreationEnabled` | `bool` | Auto user account provisioning |
| `login_url` | `loginUrl` | `str` | Vendor login URL |
| `tos_url` | `termsOfServiceUrl` | `str` | Terms of Service URL |

**`RecordingVendorsList`** (`UserList`) wraps a list of `RecordingVendor` instances.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `get(id='', name='') -> RecordingVendor \| None` | Match or `None` | Looks up by ID or name |

### OrgRecordingVendorSelection

Manages the Org-level recording vendor configuration.

**Constructor:**

```python
OrgRecordingVendorSelection(org: Org)
```

- API endpoint: `GET v1/telephony/config/callRecording/vendors`

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `available_vendors` | `RecordingVendorsList` | All vendors available to the Org |
| `selected_vendor` | `RecordingVendor` | Currently selected vendor |
| `storage_region` | `Optional[str]` | Storage region (Webex recording only) |
| `failure_behavior` | `Optional[str]` | Behavior when recording session fails |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `change_vendor` | `change_vendor(new_vendor: RecordingVendor) -> bool` | `True` | Switches the Org recording vendor |
| `set_failure_behavior` | `set_failure_behavior(failure_behavior: str) -> bool` | `False` | **Not implemented** (returns `False`). Valid values would be `PROCEED_WITH_CALL_NO_ANNOUNCEMENT`, `PROCEED_CALL_WITH_ANNOUNCEMENT`, `END_CALL_WITH_ANNOUNCEMENT`. <!-- NEEDS VERIFICATION --> |

### LocationRecordingVendorSelection

Manages Location-level recording vendor configuration with the ability to override or inherit Org-level settings.

**Constructor:**

```python
LocationRecordingVendorSelection(location: Location)
```

- API endpoint: `GET v1/telephony/config/locations/{locationId}/callRecording/vendors`

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `available_vendors` | `RecordingVendorsList` | Available vendors |
| `use_org_vendor` | `bool` | Whether Location uses the Org vendor |
| `org_vendor` | `RecordingVendor` | The Org-level vendor |
| `location_vendor` | `RecordingVendor` | The Location-level vendor |
| `use_org_storage_region` | `Optional[bool]` | Whether to use Org storage region |
| `org_storage_region` | `Optional[str]` | Org storage region |
| `location_storage_region` | `Optional[str]` | Location storage region |
| `use_org_failure_behavior` | `bool` | Whether to use Org failure behavior |
| `org_failure_behavior` | `str` | Org failure behavior |
| `location_failure_behavior` | `str` | Location failure behavior |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `change_vendor` | `change_vendor(new_vendor: RecordingVendor) -> bool` | `True` | Sets a Location-specific vendor (disables Org default) |
| `set_storage_region` | `set_storage_region(region: str) -> bool` | `True` | Sets a Location-specific storage region (2-char code) |
| `set_failure_behavior` | `set_failure_behavior(failure_behavior: str) -> bool` | `True` | Sets Location-specific failure behavior. Valid: `PROCEED_WITH_CALL_NO_ANNOUNCEMENT`, `PROCEED_CALL_WITH_ANNOUNCEMENT`, `END_CALL_WITH_ANNOUNCEMENT` |
| `clear_vendor_override` | `clear_vendor_override() -> bool` | `True` | Reverts to Org default vendor |
| `clear_region_override` | `clear_region_override() -> bool` | `True` | Reverts to Org default storage region |
| `clear_failure_override` | `clear_failure_override() -> bool` | `True` | Reverts to Org default failure behavior |

### ComplianceAnnouncementSettings

Manages compliance announcement settings (the recording notification played to callers) at Org or Location level.

**Constructor:**

```python
ComplianceAnnouncementSettings(
    org: Org,
    inboundPSTNCallsEnabled: bool,
    outboundPSTNCallsEnabled: bool,
    outboundPSTNCallsDelayEnabled: bool,
    delayInSeconds: int,
    useOrgSettingsEnabled: Optional[bool] = None,
    location: Optional[Location] = None
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `inbound_pstn_calls_enabled` | `bool` | Play compliance announcement for inbound PSTN calls |
| `outbound_pstn_calls_enabled` | `bool` | Play compliance announcement for outbound PSTN calls |
| `outbound_pstn_calls_delay_enabled` | `bool` | Delay the announcement on outbound calls |
| `delay` | `int` | Seconds to delay |
| `use_org_settings` | `Optional[bool]` | For Location-level: `False` means overriding Org settings |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `to_webex` | `to_webex() -> dict` | `dict` | Returns dict with Webex API field names |
| `to_json` | `to_json() -> str` | `str` | JSON string representation |
| `push` | `push() -> bool` | `True` | Pushes settings to Webex. Uses Location endpoint if `self.location` is set, otherwise Org endpoint. |

> **Bug note:** The Location-level endpoint in `push()` has a double slash: `v1//telephony/config/locations/...`. This may cause API failures. <!-- NEEDS VERIFICATION -->

### RecordingList

Collection class for converged recordings. Inherits `UserList`.

**Constructor:**

```python
RecordingList(
    org: Org,
    from_date_time: Optional[str] = None,
    to_date_time: Optional[str] = None,
    status: Optional[str] = None,
    service: Optional[str] = None,
    owner: Optional[Person | Workspace | VirtualLine] = None,
    region: Optional[str] = None,
    location: Optional[Location] = None
)
```

- All filter parameters are optional. `max` is hardcoded to 100.
- API endpoint: `GET v1/admin/convergedRecordings`

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `refresh` | `refresh() -> bool` | `True` | Re-fetches with same params |
| `get` | `get(id=None, call_id=None) -> Recording \| list[Recording]` | Single `Recording` by ID, `list` by call_id | When using `call_id`, always returns a list (may be empty). Raises `ValueError` if neither argument provided. |
| `reassign_owner` | `reassign_owner(current_owner, new_owner: Person, recording_list=None) -> bool` | `True` | Reassigns recordings from one owner to another. `new_owner` must be a `Person`. If `recording_list` is None, reassigns all. |

### Recording

Represents a single converged recording.

**Constructor:**

```python
Recording(org: Org, id: str, details: Optional[dict] = None, timezone: Optional[str] = None)
```

- If `details` is `None`, fetches from API on init.
- API endpoint: `GET v1/convergedRecordings/{id}`

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `metadata` | `dict` | Recording metadata (lazy-loaded from `/metadata` endpoint) |
| `status` | `str` | Recording status |
| `temporary_download_links` | `dict` | Dict of temporary download URLs |
| `url` | `Optional[str]` | Audio download URL |
| `transcript_url` | `Optional[str]` | Transcript download URL |
| `suggested_notes_url` | `Optional[str]` | Suggested notes download URL |
| `action_items_url` | `Optional[str]` | Action items download URL |
| `short_notes_url` | `str` | Short notes download URL |
| `download_expires` | `str` | Expiration timestamp for download links |
| `file_format` | `str` | Recording file format |
| `duration` | `int` | Duration in seconds |
| `file_size` | `int` | Size in bytes |
| `topic` | `str` | Topic/description |
| `service_type` | `str` | Service type (e.g. `calling`) |
| `storage_region` | `str` | Storage region |
| `created` | `str` | File creation timestamp |
| `recorded` | `str` | Call recording timestamp |
| `owner_id` | `str` | Owner UUID |
| `owner_type` | `str` | Owner type (user, workspace, virtual line) |
| `owner_email` | `str` | Owner email |
| `location_id` | `Optional[str]` | Location ID (Calling service only; returns `None` for non-calling) |
| `call_session_id` | `Optional[str]` | Call Session ID (Calling service only) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `refresh` | `refresh() -> None` | -- | Refreshes details from API |
| `download` | `download(filename: str) -> bool` | `True` | Downloads the audio file to a local path (uses `requests.get` directly, not the Org API client) |
| `get_transcript` | `get_transcript(text_only: bool = False) -> str` | `str` | Gets the transcript. If `text_only=True`, strips timestamps and WEBVTT headers, returning just the spoken text joined by spaces. |
| `get_suggested_notes` | `get_suggested_notes() -> str` | `str` | Downloads suggested notes text |
| `get_action_items` | `get_action_items() -> str` | `str` | Downloads action items text |
| `get_short_notes` | `get_short_notes() -> str` | `str` | Downloads short notes text |

---

## wxcadm vs wxc_sdk Comparison

| Aspect | wxcadm | wxc_sdk |
|--------|--------|---------|
| **Architecture** | List classes (UserList subclasses) own data fetching; item classes are plain classes or dataclasses. Lazy-loaded properties on items. | Strongly typed Pydantic/dataclass models with a central API client. Separate API method classes (e.g. `AutoAttendantApi`). <!-- NEEDS VERIFICATION --> |
| **Data fetching** | Automatic on list init; manual `refresh()` to update. Detail calls are lazy (triggered on first property access). | Explicit method calls on API objects (e.g. `api.telephony.auto_attendant.list()`). <!-- NEEDS VERIFICATION --> |
| **Scoping** | List classes accept `org` + optional `location` in constructor (except `PickupGroupList` which is Location-only). | Location filtering via method parameters. <!-- NEEDS VERIFICATION --> |
| **Lookup pattern** | `.get(id=, name=, spark_id=, uuid=)` on every list class. Search order: ID, Name, UUID, Spark ID. | Typically separate `get_by_id()` methods or list with filter params. <!-- NEEDS VERIFICATION --> |
| **Create pattern** | `.create(...)` on list class; returns the new item instance. Location defaults from parent if scoped. | `api.telephony.<feature>.create(...)` methods. <!-- NEEDS VERIFICATION --> |
| **Update pattern** | Modify `config` dict, then call `push()` (Call Queue) or use dedicated methods (Hunt Group `add_agent`). No universal update pattern. | PUT via typed update methods. <!-- NEEDS VERIFICATION --> |
| **Serialization** | Mix of plain dicts, `@dataclass`, and `@dataclass_json`. No unified serialization layer. | Pydantic models with automatic serialization. <!-- NEEDS VERIFICATION --> |
| **Recordings** | Full converged recordings support: list, download, transcript, reassign, compliance settings, vendor selection at Org and Location level. | Recording support scope unclear. <!-- NEEDS VERIFICATION --> |
| **Announcements** | Full support including upload, delete, replace, Playlists with Location assignment. | Announcement support scope unclear. <!-- NEEDS VERIFICATION --> |
| **Pickup Groups** | Location-only; read-only (no create/delete). | May have full CRUD. <!-- NEEDS VERIFICATION --> |
| **Known gaps in wxcadm** | `CallQueue.add_agent` not implemented. `OrgRecordingVendorSelection.set_failure_behavior` not implemented. Several typos in API URLs (see bug notes above). | N/A |

---

## Common Patterns

### Shared List Class Interface

All list classes (`AutoAttendantList`, `CallQueueList`, `HuntGroupList`, `PickupGroupList`, `AnnouncementList`, `PlaylistList`, `RecordingList`) inherit from `UserList` and share these patterns:

- Data is fetched automatically in `__init__`.
- Most have `refresh()` to re-fetch.
- Most have `get(...)` with various lookup keys.
- Most have `create(...)` for provisioning new items.

### Lazy-Loaded Detail Properties

`AutoAttendant` uses private `_field` attributes initialized to `None`, with `@property` accessors that call `_get_details()` on first access. Other classes (like `CallQueue`, `HuntGroup`) use the `config` property which fetches the full config dict fresh on every access.

### API URL Patterns

| Feature | List Endpoint | Detail Endpoint |
|---------|--------------|-----------------|
| Auto Attendant | `v1/telephony/config/autoAttendants` | `v1/telephony/config/locations/{locId}/autoAttendants/{id}` |
| Call Queue | `v1/telephony/config/queues` | `v1/telephony/config/locations/{locId}/queues/{id}` |
| Hunt Group | `v1/telephony/config/huntGroups` | `v1/telephony/config/locations/{locId}/huntGroups/{id}` |
| Pickup Group | `v1/telephony/config/locations/{locId}/callPickups` | `v1/telephony/config/locations/{locId}/callPickups/{id}` |
| Announcements | `v1/telephony/config/announcements` | `v1/telephony/config/announcements/{id}` or `v1/telephony/config/locations/{locId}/announcements/{id}` |
| Playlists | `v1/telephony/config/announcements/playlists` | `v1/telephony/config/announcements/playlists/{id}` |
| Recordings | `v1/admin/convergedRecordings` | `v1/convergedRecordings/{id}` |
| Recording Vendors (Org) | `v1/telephony/config/callRecording/vendors` | -- |
| Recording Vendors (Location) | `v1/telephony/config/locations/{locId}/callRecording/vendors` | -- |
| Compliance Announcement (Org) | `v1/telephony/config/callRecording/complianceAnnouncement` | -- |
| Compliance Announcement (Location) | `v1/telephony/config/locations/{locId}/callRecording/complianceAnnouncement` | -- |

---

## Known Bugs and Incomplete Features

1. **`CallQueue.add_agent`** -- method body is `pass`; not implemented.
2. **`OrgRecordingVendorSelection.set_failure_behavior`** -- returns `False` immediately; not implemented.
3. **`HuntGroupList.get` uuid branch** -- typo `.uppper()` instead of `.upper()` will raise `AttributeError`.
4. **`Playlist.__getattr__`** -- URL string `"fv1/telephony/..."` is not an f-string; the literal `f` is prepended to the path, causing the API call to fail. The `refresh()` method has the correct URL.
5. **`ComplianceAnnouncementSettings.push`** -- Location-level endpoint has a double slash: `v1//telephony/config/locations/...`.
6. **`PickupGroupList`** -- no `refresh()`, `create()`, or `delete()` methods.
