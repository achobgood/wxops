# wxcadm Location Management

Reference for location CRUD, calling enablement, schedules, and location-level features in `wxcadm`.

Source files: `wxcadm/location.py`, `wxcadm/location_features.py`

---

## Table of Contents

1. [LocationList](#locationlist)
2. [Location](#location)
   - [Core Properties](#core-properties)
   - [Calling Enablement](#calling-enablement)
   - [Calling Configuration](#calling-configuration)
   - [Number Management](#number-management)
   - [Emergency Services](#emergency-services)
   - [Schedules](#schedules)
   - [Outgoing Call Permissions](#outgoing-call-permissions)
   - [Feature Access Properties](#feature-access-properties)
   - [Floor Management](#floor-management)
   - [Monitoring](#monitoring)
   - [Delete](#delete)
3. [Location Features](#location-features)
   - [LocationSchedule](#locationschedule)
   - [VoicePortal](#voiceportal)
   - [CallParkExtension](#callparkextension)
   - [PagingGroup](#paginggroup)
   - [OutgoingPermissionDigitPattern](#outgoingpermissiondigitpattern)
   - [VoicemailGroup](#voicemailgroup)
4. [wxcadm vs wxc_sdk](#wxcadm-vs-wxc_sdk)

---

## LocationList

`LocationList` extends `collections.UserList`. It is created automatically when you access `org.locations` and fetches all locations from the Webex `v1/locations` API on initialization.

### Constructor

```python
LocationList(org: wxcadm.Org)
```

Fetches all locations on init. The list is iterable and indexable like a normal Python list.

### Methods

#### `refresh()`

```python
def refresh(self) -> None
```

Re-fetches the full location list from Webex. Call this after creating or deleting locations outside the list.

---

#### `get(id=None, name=None, spark_id=None)`

```python
def get(self, id: str = None, name: str = None, spark_id: str = None) -> Optional[Location]
```

Find a Location by ID, name, or Spark ID. Searches in that priority order. Returns `None` if no match.

Raises `ValueError` if called with no arguments.

```python
loc = org.locations.get(name="Main Office")
loc = org.locations.get(id="Y2lzY29...")
```

---

#### `create(...)`

```python
def create(self,
           name: str,
           time_zone: str,
           preferred_language: str,
           address: dict,
           latitude: Optional[str] = None,
           longitude: Optional[str] = None) -> Location
```

Creates a new location via `POST v1/locations`. Automatically refreshes the list and returns the new `Location` instance.

**Address dict format:**

```python
{
    "address1": "100 N. Main",
    "address2": "Suite 200",      # optional
    "city": "Houston",
    "state": "TX",
    "postalCode": "32123",
    "country": "US"
}
```

```python
loc = org.locations.create(
    name="Branch Office",
    time_zone="America/New_York",
    preferred_language="en_US",
    address={"address1": "50 Elm St", "city": "Raleigh", "state": "NC", "postalCode": "27601", "country": "US"}
)
```

---

#### `webex_calling(enabled=True, single=False)`

```python
def webex_calling(self, enabled: bool = True, single: bool = False) -> Location | list[Location]
```

Filters locations by Webex Calling enablement status. Uses the bulk `v1/telephony/config/locations` API (added in v4.3.9) instead of per-location calls.

- `enabled=True` (default): returns locations that have Webex Calling
- `enabled=False`: returns locations that do NOT have Webex Calling
- `single=True`: returns just the first matching Location (useful for API calls that only need one WxC location)

```python
wxc_locations = org.locations.webex_calling()
non_wxc = org.locations.webex_calling(enabled=False)
one_loc = org.locations.webex_calling(single=True)
```

---

#### `with_pstn(has_pstn=True)`

```python
def with_pstn(self, has_pstn: bool = True) -> list[Location]
```

Filters Webex Calling locations by whether they have a PSTN provider configured. Calls `webex_calling(enabled=True)` internally, then checks `loc.pstn.provider`.

#### `without_pstn()`

```python
def without_pstn(self) -> list[Location]
```

Alias for `with_pstn(has_pstn=False)`.

---

## Location

The `Location` class represents a single Webex location. Instances are typically created by `LocationList`, not manually.

### Constructor

```python
Location(org: wxcadm.Org,
         location_id: str,
         name: str,
         time_zone: str,
         preferred_language: str,
         announcement_language: str = None,
         address: dict = None)
```

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Webex ID of the location |
| `name` | `str` | Location name |
| `address` | `dict` | Address dictionary |
| `time_zone` | `str` | Timezone string (e.g. `America/Chicago`) |
| `preferred_language` | `str` | Language for phones/menus (e.g. `en_US`) |
| `announcement_language` | `str` | Language for audio announcements |
| `org_id` | `str` | Org ID (delegates to `self.org.id`) |
| `spark_id` | `str` | Decoded Spark ID (underlying service ID) |

---

### Calling Enablement

#### `calling_enabled` (property + setter)

```python
@property
def calling_enabled(self) -> bool

@calling_enabled.setter
def calling_enabled(self, value: bool)
```

Checks whether the location has Webex Calling by hitting `GET v1/telephony/config/locations/{id}`. The result is cached after the first call. The setter allows manual override without an API call (used internally by `LocationList.webex_calling()`).

#### `enable_webex_calling()`

```python
def enable_webex_calling(self) -> bool
```

Enables Webex Calling on the location via `PUT v1/telephony/config/locations`. No-ops if already enabled. Returns `True` on success.

**Gotcha:** If `address2` is an empty string `''`, the API will reject it. This method cleans it to `None` before sending.

#### `calling_config` (property)

```python
@property
def calling_config(self) -> Optional[dict]
```

Returns the full Webex Calling configuration dict for the location. Cached after first access. Returns `None` if location is not Calling-enabled.

---

### Calling Configuration

#### `external_caller_id_name` (property)

```python
@property
def external_caller_id_name(self) -> Optional[str]
```

The default external Caller ID name for the location.

#### `set_external_caller_id_name(name)`

```python
def set_external_caller_id_name(self, name: str) -> bool
```

Sets the default external Caller ID name. Clears the cached `_calling_config` so the next access re-fetches.

#### `routing_prefix` (property)

```python
@property
def routing_prefix(self) -> Optional[str]
```

The routing prefix (location code) for the location. Derived from `calling_config`.

#### `set_routing_prefix(prefix)`

```python
def set_routing_prefix(self, prefix: str) -> bool
```

Sets the routing prefix via `PUT v1/telephony/config/locations/{id}`.

#### `set_announcement_language(language, update_users=False, update_features=False)`

```python
def set_announcement_language(self,
                              language: str,
                              update_users: bool = False,
                              update_features: bool = False) -> bool
```

Sets the announcement language for the location. With optional flags to propagate to existing users/workspaces and features.

**Important:** Calling without `update_users`/`update_features` only changes the default for *new* users/features. Existing ones keep their current language unless you pass `True`.

```python
# Change default only
loc.set_announcement_language("es_ES")

# Change and update all existing users and features
loc.set_announcement_language("es_ES", update_users=True, update_features=True)
```

#### `unknown_extension_policy` (property)

```python
@property
def unknown_extension_policy(self) -> dict
```

Returns `{'enabled': bool, 'route': Trunk | RouteGroup | None}`. Controls whether unknown extensions are routed to premises via a Trunk or Route Group.

#### `set_unknown_extension_policy(route)`

```python
def set_unknown_extension_policy(self, route: Union[wxcadm.Trunk, wxcadm.RouteGroup, str]) -> bool
```

Pass a `Trunk` or `RouteGroup` to enable, or the string `'disabled'` to disable.

```python
trunk = org.call_routing.trunks.get(name="PBX Trunk")
loc.set_unknown_extension_policy(trunk)

# To disable:
loc.set_unknown_extension_policy('disabled')
```

---

### Number Management

#### `numbers` (property)

```python
@property
def numbers(self) -> Optional[NumberList]
```

All numbers assigned to this location. Returns `None` if not a Calling location.

#### `available_numbers` (property)

```python
@property
def available_numbers(self) -> Optional[list[dict]]
```

Numbers that are available (unassigned) at this location. Includes both Active and Inactive numbers so numbers can be assigned prior to activation/porting.

#### `main_number` (property)

```python
@property
def main_number(self) -> Number
```

The main number for the location. Derived from `calling_config['callingLineId']['phoneNumber']`.

#### `set_main_number(number)`

```python
def set_main_number(self, number: Union[Number, str]) -> bool
```

Sets the main number. Accepts a `Number` instance or a phone number string.

Raises `wxcadm.APIError` if the number is rejected by Webex.

---

### Emergency Services

#### `ecbn` (property)

```python
@property
def ecbn(self) -> dict
```

Emergency Callback Number settings for the location.

#### `set_ecbn(value)`

```python
def set_ecbn(self, value: Union[str, Person, Workspace, VirtualLine, HuntGroup]) -> bool
```

Set the ECBN. Pass the string `'location'` to use the location number, or a `Person`, `Workspace`, `VirtualLine`, or `HuntGroup` to use a member's number.

```python
loc.set_ecbn('location')
loc.set_ecbn(org.people.get(email="jane@example.com"))
```

#### `enhanced_emergency_calling` (property)

```python
@property
def enhanced_emergency_calling(self) -> LocationEmergencySettings
```

Returns a `LocationEmergencySettings` object with boolean attributes `integration` and `routing` (RedSky integration status).

#### `set_enhanced_emergency_calling(mode)`

```python
def set_enhanced_emergency_calling(self, mode: str) -> dict
```

Set the RedSky Enhanced Emergency Calling mode. Valid modes:

| Mode | Effect |
|------|--------|
| `'none'` | Opt out of enhanced emergency calling |
| `'integration'` | Integrate with RedSky (HELD data + 933 test calls) |
| `'routing'` | Route 911 calls through RedSky |

**Known issue (from source):** Running this method with any value will cause the location to show a compliance warning in Control Hub. The config is correct but the warning can only be cleared manually in Control Hub.

---

### Schedules

#### `schedules` (property)

```python
@property
def schedules(self) -> Optional[list[LocationSchedule]]
```

Returns a list of `LocationSchedule` instances (business hours and holidays). Returns `None` if not a Calling location.

See [LocationSchedule](#locationschedule) below for full schedule management.

---

### Outgoing Call Permissions

#### `outgoing_call_permissions` (property)

```python
@property
def outgoing_call_permissions(self) -> Optional[list]
```

The `callingPermissions` list for the location. Each entry is a dict with call type and permission settings.

#### `set_outgoing_call_permissions(outgoing_call_permissions)`

```python
def set_outgoing_call_permissions(self, outgoing_call_permissions: list) -> Optional[bool]
```

Set outgoing call permissions. The easiest approach is to read the current list, modify it, and pass it back.

```python
perms = loc.outgoing_call_permissions
# Modify perms...
loc.set_outgoing_call_permissions(perms)
```

Raises `ValueError` if the argument is not a list.

#### `outgoing_permission_digit_patterns` (property)

```python
@property
def outgoing_permission_digit_patterns(self) -> OutgoingPermissionDigitPatternList
```

Returns an `OutgoingPermissionDigitPatternList` for creating/managing digit pattern-based outgoing call rules. See [OutgoingPermissionDigitPattern](#outgoingpermissiondigitpattern) below.

---

### Feature Access Properties

These properties return feature-specific list objects scoped to the location. All return `None` if the location is not Webex Calling enabled (except where noted).

| Property | Return Type | Description |
|----------|-------------|-------------|
| `hunt_groups` | `HuntGroupList` | Hunt groups at this location |
| `call_queues` | `CallQueueList` | Call queues at this location |
| `auto_attendants` | `AutoAttendantList` | Auto attendants at this location |
| `pickup_groups` | `PickupGroupList` | Pickup groups at this location |
| `park_extensions` | `list[CallParkExtension]` | Call park extensions at this location |
| `dect_networks` | `DECTNetworkList` | DECT networks at this location |
| `virtual_lines` | `VirtualLineList` | Virtual lines at this location |
| `translation_patterns` | `TranslationPatternList` | Translation patterns at this location |
| `workspaces` | `WorkspaceList` | Workspaces at this location |
| `people` | `list` | People assigned to this location (delegates to `org.people.get(location=self)`) |
| `announcements` | `list[Announcement]` | Location-level announcements (excludes org-level) |
| `voice_portal` | `VoicePortal` | Voice portal for this location |
| `recording_vendor` | `LocationRecordingVendorSelection` | Recording vendor selection |
| `pstn` | `LocationPSTN` | PSTN configuration for this location |

#### `create_park_extension(name, extension)`

```python
def create_park_extension(self, name: str, extension: str) -> str
```

Creates a new Call Park Extension. Returns the ID of the created extension.

---

### Floor Management

#### `floors` (property)

```python
@property
def floors(self) -> LocationFloorList
```

Returns a `LocationFloorList` (extends `UserList`) of `LocationFloor` instances.

#### LocationFloorList Methods

```python
def refresh(self) -> None          # Re-fetch from API
def create(self, floor_number: int, name: str) -> LocationFloor  # Create a floor
```

`create()` raises `ValueError` if the floor number already exists.

#### LocationFloor

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Floor ID |
| `floor_number` | `int` | Numeric floor within the building |
| `name` | `str` | Display name (e.g. "Basement", "2nd Floor") |

```python
def update(self, floor_number: Optional[int] = None, name: Optional[str] = None) -> bool
def delete(self) -> bool
```

---

### Monitoring

#### `get_all_monitoring()`

```python
def get_all_monitoring(self) -> dict
```

Returns a dict showing who is monitoring whom at this location:

```python
{
    'people': { person_instance: [list_of_monitors] },
    'workspaces': { workspace_instance: [list_of_monitors] }
}
```

Iterates over all people and Webex Calling workspaces at the location, collecting their monitored elements.

---

### Delete

#### `delete()`

```python
def delete(self) -> bool
```

**Always returns `False`.** Location deletion is not supported via the Webex API. This stub exists so users are not searching for a missing method. Must be done in Control Hub.

---

## Location Features

Defined in `wxcadm/location_features.py`. These classes represent features that are scoped to a specific location.

### LocationSchedule

```python
@dataclass
class LocationSchedule:
    location: wxcadm.Location
    id: str
    name: str
    type: str   # 'businessHours' or 'holidays'
    config: dict  # auto-populated on init
```

Fetches its full configuration from `v1/telephony/config/locations/{loc_id}/schedules/{type}/{id}` on initialization.

#### `refresh_config()`

```python
def refresh_config(self) -> None
```

Re-fetches the schedule config from the API.

#### `add_holiday(name, date, recur=False, recurrence=None)`

```python
def add_holiday(self, name: str, date: str, recur: bool = False, recurrence: Optional[dict] = None) -> bool
```

Adds an all-day holiday event. Only works on `holidays` type schedules (raises `TypeError` otherwise).

- `date` format: `YYYY-MM-DD`
- If `recur=True` and no `recurrence` dict is given, defaults to yearly recurrence on the same month/day (works for fixed-date holidays like Christmas)
- For floating holidays (e.g. Thanksgiving), pass a custom recurrence dict:

```python
recurrence = {
    'recurForEver': True,
    'recurYearlyByDay': {
        'day': 'THURSDAY',
        'week': 'FOURTH',
        'month': 'NOVEMBER'
    }
}
schedule.add_holiday("Thanksgiving", "2026-11-26", recur=True, recurrence=recurrence)
```

#### `create_event(name, start_date, end_date, ...)`

```python
def create_event(self,
                 name: str,
                 start_date: str,
                 end_date: str,
                 start_time: str = "",
                 end_time: str = "",
                 all_day: bool = False,
                 recurrence: Optional[dict] = None) -> bool
```

Generic event creation for either schedule type. If `all_day=False`, both `start_time` and `end_time` are required (raises `ValueError` otherwise).

Recurrence dict example (every weekday):

```python
recurrence = {
    'recurForEver': True,
    'recurWeekly': {
        'monday': True
    }
}
```

#### `update_event(id, ...)`

```python
def update_event(self,
                 id: str,
                 name: str = None,
                 start_date: str = None,
                 end_date: str = None,
                 start_time: str = None,
                 end_time: str = None,
                 all_day: bool = None,
                 recurrence: dict = None) -> bool
```

Updates an existing event by ID. Fetches the current config for the event, merges in provided values, and PUTs it back.

<!-- NEEDS VERIFICATION: The update_event method's API URL appears truncated in source (`v1/telephony/config/`) — it may not include the full schedule/event path. This could be a bug in wxcadm. -->

#### `delete_event(event)`

```python
def delete_event(self, event: str) -> bool
```

Deletes an event by name or ID (both are unique within a schedule).

#### `get_event_config_by_id(id)`

```python
def get_event_config_by_id(self, id: str) -> Optional[dict]
```

Returns the raw event dict from the schedule config for a given event ID. Useful for inspecting or modifying event data.

#### `clone(target_location=None, name=None)`

```python
def clone(self,
          target_location: Optional[wxcadm.Location] = None,
          name: Optional[str] = None) -> str
```

Clones the schedule. You must provide at least one of `target_location` or `name`.

- To clone to another location (same name): `schedule.clone(target_location=other_loc)`
- To clone within the same location (new name): `schedule.clone(name="After Hours v2")`
- Both: `schedule.clone(target_location=other_loc, name="Custom Name")`

Returns the ID of the newly created schedule.

---

### VoicePortal

```python
@dataclass
class VoicePortal(RealtimeClass):
    location: wxcadm.Location
    id: str          # auto-populated
    language: str
    language_code: str
    extension: str
    phone_number: str
    first_name: str
    last_name: str
```

Extends `RealtimeClass` -- changing attributes directly pushes updates to Webex immediately (unlike other wxcadm classes that require explicit save calls).

<!-- NEEDS VERIFICATION: The RealtimeClass behavior (auto-push on attribute change) for `_api_fields` ['phone_number', 'extension'] should be tested to confirm which fields are auto-synced vs. read-only. -->

#### `copy_config(target_location, phone_number=None, passcode=None)`

```python
def copy_config(self,
                target_location: wxcadm.Location,
                phone_number: str = None,
                passcode: str = None) -> bool
```

Copies the Voice Portal settings (language, extension, name) to another Calling-enabled location. Phone number and passcode are NOT copied unless explicitly provided.

Raises `ValueError` if the target location is not Webex Calling enabled.

---

### CallParkExtension

```python
@dataclass
class CallParkExtension:
    location: wxcadm.Location
    id: str
    name: str
    extension: str
```

Created via `loc.park_extensions` (property) or `loc.create_park_extension(name, extension)`.

#### `get_monitored_by()`

```python
def get_monitored_by(self) -> Optional[list]
```

Returns a list of users/workspaces monitoring this park extension. Uses the org-level `get_all_monitoring()` method.

---

### PagingGroup

```python
@dataclass
class PagingGroup:
    location: wxcadm.Location
    id: str
    name: str
    spark_id: str   # auto-computed
    config: dict    # auto-populated on init
```

#### `refresh_config()`

```python
def refresh_config(self) -> None
```

Re-fetches the paging group configuration from `v1/telephony/config/locations/{loc_id}/paging/{id}`.

<!-- NEEDS VERIFICATION: PagingGroup instances are not exposed through any Location property in location.py. It is unclear how they are accessed — they may be created externally or through an org-level list not shown in the source files reviewed. -->

---

### OutgoingPermissionDigitPattern

Accessed via `loc.outgoing_permission_digit_patterns`.

#### OutgoingPermissionDigitPatternList

```python
class OutgoingPermissionDigitPatternList:
    patterns: list[OutgoingPermissionDigitPattern]
```

Methods:

```python
def refresh(self) -> self
def create(self, name: str, pattern: str, action: str, transfer_enabled: Optional[bool] = False) -> OutgoingPermissionDigitPattern
def delete_all(self) -> bool
```

**Valid `action` values:** `'ALLOW'`, `'BLOCK'`, `'AUTH_CODE'`, `'TRANSFER_NUMBER_1'`, `'TRANSFER_NUMBER_2'`, `'TRANSFER_NUMBER_3'`

```python
patterns = loc.outgoing_permission_digit_patterns
new = patterns.create(name="Block 900", pattern="1900XXXXXXX", action="BLOCK")
patterns.delete_all()  # remove all patterns at the location
```

#### OutgoingPermissionDigitPattern Instance

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Pattern ID |
| `name` | `str` | Pattern name |
| `pattern` | `str` | The digit pattern |
| `action` | `str` | Action taken (ALLOW, BLOCK, etc.) |
| `transfer_enabled` | `bool` | Whether applied to transferred/forwarded calls |

```python
def update(self, name=None, pattern=None, action=None, transfer_enabled=None) -> OutgoingPermissionDigitPattern
def delete(self) -> bool
```

Only pass the values you want to change to `update()`.

---

### VoicemailGroup

Managed at the **org level** via `org.voicemail_groups` (a `VoicemailGroupList`), but scoped to a location.

<!-- NEEDS VERIFICATION: The `org.voicemail_groups` attribute is assumed based on the VoicemailGroupList constructor signature. The actual attribute name on the Org class was not in the reviewed source files. -->

#### VoicemailGroupList

```python
class VoicemailGroupList(UserList):
    def __init__(self, org: wxcadm.Org)
```

Methods:

```python
def refresh(self) -> self
def get(self, name: str = None, id: str = None) -> Optional[VoicemailGroup]
def create(self,
           location: wxcadm.Location,
           name: str,
           extension: str,
           passcode: str,
           phone_number: Optional[str] = None,
           first_name: Optional[str] = None,
           last_name: Optional[str] = None,
           language_code: Optional[str] = 'en_us',
           message_storage: Optional[dict] = None,
           notifications: Optional[dict] = None,
           fax_message: Optional[dict] = None,
           transfer_to_number: Optional[dict] = None,
           email_copy_of_message: Optional[dict] = None) -> VoicemailGroup
```

Default values for `create()` if not provided:
- `message_storage`: `{'storageType': 'INTERNAL'}`
- `notifications`, `fax_message`, `transfer_to_number`, `email_copy_of_message`: `{'enabled': False}`

#### VoicemailGroup Instance

Core attributes (available immediately):

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Voicemail Group ID |
| `name` | `str` | Group name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `extension` | `str` | Extension number |
| `enabled` | `bool` | Whether the group is enabled |
| `esn` | `Optional[str]` | ESN |

Lazy-loaded properties (trigger an API call on first access):

| Property | Type | Description |
|----------|------|-------------|
| `phone_number` | `str` | DID |
| `first_name` | `str` | Directory first name |
| `last_name` | `str` | Directory last name |
| `language_code` | `str` | Language code |
| `greeting_type` | `str` | `'DEFAULT'` or `'CUSTOM'` |
| `greeting_uploaded` | `bool` | Whether a custom greeting was uploaded |
| `greeting_description` | `str` | Custom greeting description |
| `message_storage` | `dict` | Storage config |
| `notifications` | `dict` | Notification settings |
| `fax_message` | `dict` | Fax settings |
| `transfer_to_number` | `dict` | Transfer settings |
| `email_copy_of_message` | `dict` | Email copy settings |
| `message_forwarding_enabled` | `bool` | Voice message forwarding status |

Methods:

```python
def update(self, name=None, phone_number=None, extension=None, first_name=None,
           last_name=None, enabled=None, language_code=None, greeting_type=None,
           greeting_description=None, message_storage=None, notifications=None,
           fax_message=None, transfer_to_number=None, email_copy_of_message=None) -> VoicemailGroup
def delete(self) -> bool
def enable_email_copy(self, email: str) -> VoicemailGroup  # shortcut for update()
```

---

## wxcadm vs wxc_sdk

### Location access patterns

| Operation | wxcadm | wxc_sdk |
|-----------|--------|---------|
| List locations | `org.locations` (auto-fetches) | `api.locations.list()` (returns generator) |
| Get by name | `org.locations.get(name="...")` | `api.locations.list(name="...")` then iterate |
| Get by ID | `org.locations.get(id="...")` | `api.locations.details(location_id="...")` |
| Create | `org.locations.create(...)` returns `Location` | `api.locations.create(...)` returns ID string |
| Delete | Not supported (returns `False`) | `api.locations.delete(location_id)` <!-- NEEDS VERIFICATION --> |

### Calling enablement

| Operation | wxcadm | wxc_sdk |
|-----------|--------|---------|
| Check if Calling-enabled | `loc.calling_enabled` (bool property) | Check via `api.telephony.location.details()` |
| Enable Calling | `loc.enable_webex_calling()` | `api.telephony.location.enable_for_calling()` <!-- NEEDS VERIFICATION --> |
| Filter Calling locations | `org.locations.webex_calling()` (bulk API) | Manual filtering required |
| Filter by PSTN | `org.locations.with_pstn()` / `without_pstn()` | Manual filtering required |

### Key architectural differences

1. **Caching**: wxcadm caches calling config, numbers, and feature lists as instance attributes. wxc_sdk generally does not cache and makes a fresh API call each time.

2. **Object model**: wxcadm uses a `Location` object with rich properties that lazily load sub-features (hunt groups, call queues, schedules, etc.). wxc_sdk uses separate API method groups (`api.telephony.callqueue`, `api.telephony.huntgroup`, etc.) that take a `location_id` parameter.

3. **List classes**: wxcadm wraps results in `UserList` subclasses (e.g., `LocationList`, `CallQueueList`) with `.get()` and `.refresh()` methods. wxc_sdk returns plain generators or lists.

4. **Setter pattern**: wxcadm uses separate `set_*` methods (e.g., `set_ecbn()`, `set_routing_prefix()`) rather than property setters that auto-push. The exception is `VoicePortal` which extends `RealtimeClass` for auto-push behavior.

5. **Schedule management**: wxcadm exposes `LocationSchedule` objects with `add_holiday()`, `create_event()`, `clone()`, etc. wxc_sdk uses `api.telephony.schedules` with similar but flatter method signatures. <!-- NEEDS VERIFICATION -->

6. **Bulk operations**: wxcadm's `LocationList.webex_calling()` uses a single bulk API call (`v1/telephony/config/locations`) for efficiency (added in v4.3.9). Earlier versions made per-location calls.

---

## See Also

- [provisioning.md](provisioning.md) — wxc_sdk location provisioning patterns (creation, calling enablement, number assignment)
- [location-call-settings-core.md](location-call-settings-core.md) — wxc_sdk location-level call settings (caller ID, voicemail, music on hold, outgoing permissions)
