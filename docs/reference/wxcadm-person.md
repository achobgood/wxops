<!-- Not directly verified via CLI — documents wxcadm library (not generated CLI commands) -->
<!-- wxcadm v4.6.1 review 2026-03-27: All v4.5.0–v4.6.1 changes verified present. PersonList(org, location) signature, PersonList.all(), Person(org=) constructor, Person.single_number_reach, Person.appearance_devices, Person.delete(), PersonList.get_by_email() removal, get_barge_in/push_barge_in removal — all accurately documented. No discrepancies found. -->
# wxcadm — Person Module Reference

Source: `wxcadm/person.py`

This document covers every class, method, and property in the wxcadm `person` module. The module provides person/user management for Webex Calling orgs, including user CRUD, call settings, device management, number management, and ancillary models like UserGroups, SingleNumberReach, and ApplicationServicesSettings.

---

<!-- Updated by playbook session 2026-03-18 -->
## When to Use wxcadm vs Raw HTTP

wxcadm Person has 34 call settings methods, but most wrap standard Webex REST endpoints that raw HTTP can call directly. The truly unique capabilities are the ones worth using wxcadm for.

| Use wxcadm when | Use raw HTTP when |
|---|---|
| You need **XSI session management** — `start_xsi()` has no raw HTTP equivalent | You're reading/writing standard person call settings (forwarding, voicemail, DND, etc.) |
| You need **reverse membership lookups** — `person.hunt_groups`, `person.call_queues` search the org for you | You're doing targeted CRUD on a known person ID |
| You want **`get_full_config()`** to batch-fetch all settings at once | You want to read/write a single setting without loading the full person object |
| You need **`ecbn_null_change()`** — a backend bug workaround not in wxc_sdk | You're building automation that needs predictable, minimal API calls |
| You want **`ApplicationLineAssignments`** for shared call appearance management | You're working with well-documented endpoints that don't need convenience wrappers |
| You need **`spark_id`** decoding or **`set_calling_only()`** license cleanup | You want Pydantic-typed responses (use wxc_sdk models with raw HTTP instead) |

> **Note:** The playbook uses raw HTTP via `api.session.rest_*()` for standard person CRUD and call settings. wxcadm is used for its truly unique capabilities: XSI integration, reverse group lookups, `ecbn_null_change()`, `get_full_config()` batch fetch, and `ApplicationLineAssignments`. Convenience methods like `set_caller_id()` and `enable_call_recording()` are nice but replaceable with raw HTTP + the correct payload.

---

## Table of Contents

- [PersonList](#personlist)
- [Person](#person)
  - [User Info & Management](#user-info--management)
  - [Call Settings](#call-settings)
  - [Number Management](#number-management)
  - [Device Management](#device-management)
  - [Permissions & Access](#permissions--access)
  - [Monitoring & Group Membership](#monitoring--group-membership)
  - [XSI](#xsi)
- [Me (subclass of Person)](#me)
- [Data Models](#data-models)
  - [VoiceMessage](#voicemessage)
  - [UserGroups / UserGroup](#usergroups--usergroup)
  - [ApplicationServicesSettings](#applicationservicessettings)
  - [ApplicationLineAssignments / ApplicationLine](#applicationlineassignments--applicationline)
  - [SingleNumberReach / SnrNumber](#singlenumberreach--snrnumber)
- [wxcadm vs wxc_sdk](#wxcadm-vs-wxc_sdk)

---

## PersonList

Extends `collections.UserList`. Lazy-loads people from the Webex `v1/people` API with `callingData=true`.

### Constructor

```python
PersonList(org: wxcadm.Org, location: Optional[wxcadm.Location] = None)
```

Internal state flags:
- `__data_loaded` — tracks whether any data has been fetched
- `__data_filtered` — tracks whether `self.data` is a filtered subset
- `__filters` — remembers the last filter dict used for `refresh()`

### Methods

#### `get`

```python
def get(
    self,
    id: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    location: Optional[wxcadm.Location] = None,
    uuid: Optional[str] = None
) -> Union[Person, PersonList]
```

Unified getter. Returns a single `Person` when exactly one result is found (and no location scope), otherwise returns the `PersonList` itself. Uses cached data for `id`/`email` lookups when data is already loaded and unfiltered.

- `name` matches against `display_name` (case-insensitive, full match, sent as `displayName` API param)
- `uuid` is sent as the `id` API filter — used primarily for CDR correlation

#### `get_by_id`

```python
def get_by_id(self, id: str) -> Optional[Person]
```

Linear search through already-loaded `self.data`. Does not make API calls.

#### `all`

```python
def all(self) -> Union[Person, PersonList]
```

Resets `__data_loaded` flag and calls `get()` with no filters. Returns all people in the org.

#### `refresh`

```python
def refresh(self) -> None
```

Re-fetches the list using the same filters from the last `get()` call.

#### `webex_calling`

```python
def webex_calling(self, enabled: bool = True) -> list[Person]
```

Filters the loaded list to people where `Person.wxc` matches `enabled`. Lazy-loads data if not already loaded.

#### `recorded`

```python
def recorded(self, enabled: bool = True) -> list[Person]
```

Returns people whose call recording `enabled` flag matches the argument. Calls `get_call_recording()` on each WxC-enabled person — can be slow on large orgs.

#### `create`

```python
def create(
    self,
    email: str,
    location: Optional[Union[str, Location]] = None,
    licenses: list = None,
    calling: bool = True,
    phone_number: str = None,
    extension: str = None,
    first_name: str = None,
    last_name: str = None,
    display_name: str = None
) -> Person
```

Creates a new user via `POST v1/people`. If `licenses` is not provided and `calling=True`, automatically finds a Professional Calling license. If no names are given, `display_name` defaults to the email.

Raises `wxcadm.exceptions.LicenseError` if no calling license is available.
Raises `wxcadm.exceptions.PutError` if creation fails.

---

## Person

### Constructor

```python
Person(user_id: str, org: wxcadm.Org, config: Optional[dict] = None)
```

If `config` is omitted, makes a `GET v1/people/{user_id}?callingData=true` call. The `wxc` flag is set to `True` only when the person has both a Webex Calling license AND an assigned location.

### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Webex person ID |
| `org` | `wxcadm.Org` | Parent org |
| `email` | `str` | Primary email |
| `first_name` | `str` | First name |
| `last_name` | `str` | Last name |
| `display_name` | `str` | Display name |
| `wxc` | `bool` | True if Webex Calling enabled |
| `licenses` | `list` | License IDs |
| `location` | `str` | Location ID |
| `roles` | `list` | Role IDs |
| `numbers` | `list` | Phone numbers from Common Identity (list of dicts with `type`/`value`) |
| `extension` | `Optional[str]` | Extension |
| `avatar` | `Optional[str]` | Avatar URL |
| `department` | `Optional[str]` | Department |
| `manager` | `Optional[str]` | Manager name |
| `manager_id` | `Optional[str]` | Manager's person ID |
| `title` | `Optional[str]` | Job title |
| `addresses` | `Optional[list]` | Addresses |
| `status` | `Optional[str]` | Presence status |
| `login_enabled` | `Optional[bool]` | Whether sign-in is allowed |
| `xsi` | `Optional[XSI]` | XSI session (set by `start_xsi()`) |

Settings dicts (populated by their respective `get_*` methods):

| Attribute | Populated By |
|-----------|-------------|
| `vm_config` | `get_vm_config()` |
| `call_recording` | `get_call_recording()` |
| `call_forwarding` | `get_call_forwarding()` |
| `caller_id` | `get_caller_id()` |
| `intercept` | `get_intercept()` |
| `dnd` | `get_dnd()` |
| `calling_behavior` | `get_calling_behavior()` |
| `hoteling` | `get_hoteling()` |
| `ptt` | `get_ptt()` |
| `outgoing_permission` | `get_outgoing_permission()` |
| `executive_assistant` | `get_executive_assistant()` |
| `applications_settings` | `get_applications_settings()` |

---

### User Info & Management

#### Properties

##### `org_id`

```python
@property
def org_id(self) -> Optional[str]
```

Returns `self.org.id`.

##### `spark_id`

```python
@property
def spark_id(self) -> str
```

Base64-decodes the person ID to get the internal Webex/Spark identifier. Useful for internal correlation.

##### `name`

```python
@property
def name(self) -> str
```

Alias for `display_name`.

#### Methods

##### `role_names`

```python
def role_names(self) -> Optional[list]
```

Returns a list of role name strings by resolving role IDs against `self.org.roles`. Returns `None` if the person has no roles.

> **Note:** There is a bug in the source — `return roles` is inside the `for` loop (line 483 of person.py), so only the first role is ever returned. <!-- Verified via wxcadm source 2026-03-19 -->

##### `delete`

```python
def delete(self) -> bool
```

Deletes the person via `DELETE v1/people/{id}`.

##### `refresh_person`

```python
def refresh_person(self, raw: bool = False) -> Union[bool, dict]
```

Re-fetches person details from the API and updates instance attributes. If `raw=True`, returns the raw API dict.

##### `update_person`

```python
def update_person(
    self,
    email=None,
    numbers=None,
    extension=None,
    location=None,
    display_name=None,
    first_name=None,
    last_name=None,
    roles=None,
    licenses=None,
    avatar: Optional[str] = None,
    department: Optional[str] = None,
    title: Optional[str] = None,
    addresses: Optional[list] = None
) -> bool
```

PUT update to `v1/people/{id}`. Any omitted argument uses the current instance value as the default, so you can modify an instance attribute directly (e.g., `person.extension = "1234"`) then call `update_person()` with no args to push the change.

##### `license_details`

```python
def license_details(self) -> list
```

Returns the full license objects (from `org.licenses`) for all licenses assigned to this person.

##### `assign_wxc`

```python
def assign_wxc(
    self,
    location: wxcadm.Location,
    phone_number: Optional[str] = None,
    extension: Optional[str] = None,
    unassign_ucm: Optional[bool] = False,
    license_type: Optional[str] = 'professional',
    ignore_license_overage: Optional[bool] = True
) -> bool
```

Assigns Webex Calling to the user. Finds the appropriate license automatically. `license_type` can be `'standard'` or `'professional'`. If `unassign_ucm=True`, removes UCM licenses first.

##### `unassign_wxc`

```python
def unassign_wxc(self) -> bool
```

Removes all Webex Calling licenses and clears the extension.

##### `set_calling_only`

```python
def set_calling_only(self) -> bool
```

Removes Messaging and Meetings licenses, keeping only Calling (and screen share). Uses `update_person()` internally.

---

### Call Settings

All `get_*` methods store their result on the corresponding instance attribute and also return it. All `push_*` methods accept a config dict and send it via PUT.

#### Voicemail

##### `get_vm_config`

```python
def get_vm_config(self) -> dict
```

`GET v1/people/{id}/features/voicemail`

##### `push_vm_config`

```python
def push_vm_config(self, vm_config: dict = None) -> Union[dict, bool]
```

`PUT v1/people/{id}/features/voicemail`. If `vm_config` is omitted, pushes `self.vm_config`. Returns the refreshed config on success, `False` on failure.

##### `reset_vm_pin`

```python
def reset_vm_pin(self, pin: str = None) -> bool
```

If `pin` is provided, sets it directly via `PUT .../voicemail/passcode`. If omitted, triggers a reset that sends a temporary PIN to the user by email.

##### `enable_vm_to_email`

```python
def enable_vm_to_email(self, email: str = None, push: bool = True) -> dict
```

Enables sending VM copies to email. Defaults to the person's own email.

##### `disable_vm_to_email`

```python
def disable_vm_to_email(self, push: bool = True) -> dict
```

Disables VM-to-email.

##### `enable_vm_notification`

```python
def enable_vm_notification(self, email: str = None, push: bool = True) -> dict
```

Enables VM notification to email. Defaults to the person's own email.

##### `disable_vm_notification`

```python
def disable_vm_notification(self, email: str = None, push: bool = True) -> dict
```

Disables VM notification.

##### `set_voicemail_rings`

```python
def set_voicemail_rings(self, rings: int, push: bool = True) -> dict
```

Sets the number of rings before unanswered calls go to voicemail.

##### `upload_busy_greeting`

```python
def upload_busy_greeting(self, filename: str, activate: bool = True) -> bool
```

Uploads a WAV file as the busy greeting via multipart POST. If `activate=True`, also sets the greeting type to `CUSTOM`. No format validation is performed.

##### `upload_no_answer_greeting`

```python
def upload_no_answer_greeting(self, filename: str, activate: bool = True) -> bool
```

Uploads a WAV file as the no-answer greeting. Same behavior as `upload_busy_greeting`.

#### Call Forwarding

##### `get_call_forwarding`

```python
def get_call_forwarding(self) -> dict
```

`GET v1/people/{id}/features/callForwarding`

##### `push_cf_config`

```python
def push_cf_config(self, cf_config: dict = None) -> Union[dict, bool]
```

`PUT v1/people/{id}/features/callForwarding`. If `cf_config` is omitted, pushes `self.call_forwarding`.

#### Caller ID

##### `get_caller_id`

```python
def get_caller_id(self) -> dict
```

`GET v1/people/{id}/features/callerId`

##### `push_caller_id`

```python
def push_caller_id(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/callerId`. Sends the raw config dict. For a friendlier interface, use `set_caller_id()`.

##### `set_caller_id`

```python
def set_caller_id(self, name: str, number: str) -> bool
```

Convenience method that builds the correct API payload from keywords:

| `name` value | API field set |
|-------------|--------------|
| `"direct"` | `externalCallerIdNamePolicy: "DIRECT_LINE"` |
| `"location"` | `externalCallerIdNamePolicy: "LOCATION"` |
| anything else | `externalCallerIdNamePolicy: "OTHER"`, `customExternalCallerIdName: name` |

| `number` value | API field set |
|---------------|--------------|
| `"direct"` | `selected: "DIRECT_LINE"` |
| `"location"` | `selected: "LOCATION_NUMBER"` |
| anything else | `selected: "CUSTOM"`, `customNumber: number` |

#### Call Recording

##### `get_call_recording`

```python
def get_call_recording(self) -> dict
```

`GET v1/people/{id}/features/callRecording`

##### `push_call_recording`

```python
def push_call_recording(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/callRecording`. Automatically strips Dubber-specific keys (`serviceProvider`, `externalGroup`, `externalIdentifier`) before sending, since the PUT endpoint does not accept them.

##### `enable_call_recording`

```python
def enable_call_recording(
    self,
    type: str,
    record_vm: bool = False,
    announcement_enabled: bool = False,
    reminder_tone: bool = False,
    reminder_interval: int = 30,
    can_play: bool = True,
    can_download: bool = True,
    can_delete: bool = True,
    can_share: bool = True,
    transcribe: bool = True,
    ai_summary: bool = True
) -> bool
```

`type` must be one of: `'always'`, `'never'`, `'always_with_pause'`, `'on_demand'`.

Raises `ValueError` for invalid type values.

> **Note:** `transcribe`, `can_play`, and similar params only apply when Webex platform recording is used. Third-party recording providers ignore them.

##### `disable_call_recording`

```python
def disable_call_recording(self) -> bool
```

Sets `enabled: False` and pushes.

#### Call Intercept

##### `get_intercept`

```python
def get_intercept(self) -> dict
```

`GET v1/people/{id}/features/intercept`

##### `push_intercept`

```python
def push_intercept(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/intercept`

#### Do Not Disturb

##### `get_dnd`

```python
def get_dnd(self) -> dict
```

`GET v1/people/{id}/features/doNotDisturb`

##### `push_dnd`

```python
def push_dnd(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/doNotDisturb`

#### Calling Behavior

##### `get_calling_behavior`

```python
def get_calling_behavior(self) -> dict
```

`GET v1/people/{id}/features/callingBehavior`

##### `push_calling_behavior`

```python
def push_calling_behavior(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/callingBehavior`

#### Hoteling

##### `get_hoteling`

```python
def get_hoteling(self) -> dict
```

`GET v1/people/{id}/features/hoteling`

##### `push_hoteling`

```python
def push_hoteling(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/hoteling`. Re-fetches after success.

#### Push-to-Talk

##### `get_ptt`

```python
def get_ptt(self) -> dict
```

`GET v1/people/{id}/features/pushToTalk`

##### `push_ptt`

```python
def push_ptt(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/pushToTalk`

#### Executive Assistant

##### `get_executive_assistant`

```python
def get_executive_assistant(self) -> dict
```

`GET v1/people/{id}/features/executiveAssistant`

##### `push_executive_assistant`

```python
def push_executive_assistant(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/executiveAssistant`

#### Application Services

##### `get_applications_settings`

```python
def get_applications_settings(self) -> dict
```

`GET v1/people/{id}/features/applications`. Returns the raw dict.

##### `push_applications_settings`

```python
def push_applications_settings(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/applications`

##### `applications` (property)

```python
@property
def applications(self) -> ApplicationServicesSettings
```

Returns a lazy-loaded `ApplicationServicesSettings` dataclass instance. See [ApplicationServicesSettings](#applicationservicessettings) for its methods.

#### Barge-In

##### `barge_in` (property)

```python
@property
def barge_in(self) -> Optional[BargeInSettings]
```

Returns a lazy-loaded `BargeInSettings` dataclass. Fetches from `GET v1/people/{id}/features/bargeIn`.

#### Single Number Reach

##### `single_number_reach` (property)

```python
@property
def single_number_reach(self) -> SingleNumberReach
```

Returns a lazy-loaded `SingleNumberReach` instance. See [SingleNumberReach](#singlenumberreach--snrnumber).

#### Outgoing Permission

##### `get_outgoing_permission`

```python
def get_outgoing_permission(self) -> dict
```

`GET v1/people/{id}/features/outgoingPermission`

##### `push_outgoing_permission`

```python
def push_outgoing_permission(self, config: dict) -> bool
```

`PUT v1/people/{id}/features/outgoingPermission`

#### Preferred Answer Endpoint

##### `preferred_answer_endpoint` (property)

```python
@property
def preferred_answer_endpoint(self) -> Union[dict, None]
```

`GET v1/telephony/config/people/{id}/preferredAnswerEndpoint`. Returns the dict for the currently preferred endpoint, or `None` if not set.

##### `set_preferred_answer_endpoint`

```python
def set_preferred_answer_endpoint(self, endpoint: Union[wxcadm.Device, str]) -> bool
```

Sets the preferred answer endpoint. Accepts a `Device` instance or a string ID.

> **Note:** Cisco 9800 (PhoneOS) devices do not work with this API endpoint due to an API-side issue.

##### `available_answer_endpoints` (property)

```python
@property
def available_answer_endpoints(self) -> Optional[list[Union[Device, str]]]
```

Returns a list of `Device` objects (for type `DEVICE`) and string IDs (for type `APPLICATION`). Cached after first access.

#### Bulk Config Fetch

##### `get_full_config`

```python
def get_full_config(self) -> Union[Person, bool]
```

Fetches all calling settings in one call: forwarding, voicemail, caller ID, recording, DND, calling behavior, hoteling, intercept, outgoing permission, and PTT. Returns `self` on success, `False` if the person is not a WxC user.

---

### Number Management

##### `wxc_numbers` (property)

```python
@property
def wxc_numbers(self) -> dict
```

`GET v1/people/{id}/features/numbers`. Returns numbers from the Webex Calling platform (not Common Identity). Includes the primary number and any aliases. Unlike `self.numbers`, this does not include Active Directory data.

##### `change_phone_number`

```python
def change_phone_number(self, new_number: str, new_extension: str = None) -> bool
```

Changes the person's phone number (and optionally extension) via `update_person()`.

##### `remove_did`

```python
def remove_did(self) -> str
```

Removes the `work`-type phone number from the person. Returns the removed number string (useful for re-adding after a user move).

##### `add_did`

```python
def add_did(self, phone_number: str, primary: Optional[bool] = True) -> list
```

Adds a DID to the person. Returns the updated numbers list.

##### `ecbn` (property)

```python
@property
def ecbn(self) -> dict
```

`GET v1/telephony/config/people/{id}/emergencyCallbackNumber`

##### `set_ecbn`

```python
def set_ecbn(self, value: Union[str, Person, Workspace, VirtualLine]) -> bool
```

Sets the Emergency Callback Number. Accepts:
- `"direct"` or `"direct_line"` — user's own DID
- `"location"` or `"location_ecbn"` — location ECBN
- A `Person`, `Workspace`, or `VirtualLine` instance — that entity's number

Raises `ValueError` for unknown string values.

##### `ecbn_null_change`

```python
def ecbn_null_change(self) -> bool
```

Re-sends the current ECBN config unchanged. Workaround for a backend bug where ECBN settings become out of sync between Control Hub and Webex Calling.

---

### Device Management

##### `devices` (property)

```python
@property
def devices(self) -> DeviceList
```

Returns a lazy-loaded `DeviceList` for this person.

##### `appearance_devices` (property)

```python
@property
def appearance_devices(self) -> list[dict]
```

`GET v1/telephony/config/people/{id}/devices`. Returns raw dicts of devices that have this person as a line appearance. Values like `mac` in the returned dicts can be used to cross-reference with `self.devices`.

---

### Permissions & Access

##### `outgoing_permission`

See [get_outgoing_permission / push_outgoing_permission](#outgoing-permission) in Call Settings above.

##### `user_groups` (property)

```python
@property
def user_groups(self) -> list
```

Returns the list of `UserGroup` instances that this person is a member of. Delegates to `org.usergroups.find_person_assignments()`.

---

### Monitoring & Group Membership

##### `monitoring` (property)

```python
@property
def monitoring(self) -> MonitoringList
```

Returns a lazy-loaded `MonitoringList` for viewing/controlling monitoring. Fetches from `GET v1/people/{id}/features/monitoring`.

##### `get_monitored_by`

```python
def get_monitored_by(self) -> Optional[dict]
```

Returns a dict of users and workspaces that are monitoring this person. Uses `org.get_all_monitoring()` to get the full org-wide monitoring map.

##### `hunt_groups` (property)

```python
@property
def hunt_groups(self) -> list
```

Returns `HuntGroup` instances where this person is an agent. Iterates all org hunt groups and checks each agent list. Can be slow on large orgs.

##### `call_queues` (property)

```python
@property
def call_queues(self) -> list
```

Returns `CallQueue` instances where this person is an agent. Same iteration approach as `hunt_groups`.

---

### XSI

##### `start_xsi`

```python
def start_xsi(self, get_profile: bool = False, cache: bool = False) -> XSI
```

Starts an XSI session for the person. Sets `self.xsi` and returns the `XSI` instance. See `wxcadm-xsi-realtime.md` for XSI details.

---

## Me

```python
class Me(Person)
```

Subclass of `Person` representing the token owner. Provides methods only available at owner scope.

### Methods

#### `get_voice_messages`

```python
def get_voice_messages(self, unread: bool = False) -> list[VoiceMessage]
```

`GET v1/telephony/voiceMessages`. Returns a list of `VoiceMessage` instances. If `unread=True`, filters to unread only.

#### `voicemail_summary` (property)

```python
@property
def voicemail_summary(self) -> Optional[dict]
```

`GET v1/telephony/voiceMessages/summary`. Returns a dict:

```python
{
    'newMessages': int,
    'oldMessages': int,
    'newUrgentMessages': int,
    'oldUrgentMessages': int
}
```

---

## Data Models

### VoiceMessage

```python
@dataclass
class VoiceMessage:
    org: wxcadm.Org
    id: str
    duration: int           # seconds; not present for fax
    callingParty: dict      # caller details
    read: bool
    created: str            # ISO timestamp
    urgent: bool = False
    confidential: bool = False
    faxPageCount: Optional[int] = None
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `mark_read` | `() -> bool` | Marks the message as read |
| `mark_unread` | `() -> bool` | Marks the message as unread |
| `delete` | `() -> bool` | Deletes the voice message |

---

### UserGroups / UserGroup

#### UserGroups (list class)

Extends `UserList`. Eagerly fetches all groups from `GET v1/groups` on init.

```python
UserGroups(org: wxcadm.Org)
```

##### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_group` | `(name: str, description: str = '', members: Optional[list] = None) -> bool` | Creates a new group. `members` is a list of `Person` instances. |
| `find_person_assignments` | `(person: Person) -> list[UserGroup]` | Returns all groups containing the given person. |

#### UserGroup (dataclass)

```python
@dataclass
class UserGroup:
    org: wxcadm.Org
    id: str
    displayName: str
    orgId: str
    created: str
    lastModified: str
    usage: str = 'Unknown'      # removed from API response since v3.0.0
    memberSize: int = 0
    description: str = ''
```

##### Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `members` | `list` | List of `Person` instances (or raw IDs for non-person members). Fetches from `GET v1/groups/{id}/members`. |
| `name` | `str` | Alias for `displayName` |

##### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `delete` | `() -> bool` | Deletes the group |
| `add_member` | `(person: Person) -> bool` | Adds a person via PATCH |
| `delete_member` | `(person: Person) -> bool` | Removes a person via PATCH |

---

### ApplicationServicesSettings

`@dataclass_json @dataclass` — lazy-loaded via `Person.applications` property.

```python
class ApplicationServicesSettings:
    person: wxcadm.Person
    ring_devices_for_click_to_dial: bool    # ringDevicesForClickToDialCallsEnabled
    ring_devices_for_group_page: bool       # ringDevicesForGroupPageEnabled
    ring_devices_for_call_park: bool        # ringDevicesForCallParkEnabled
    browser_client_enabled: bool            # browserClientEnabled
    desktop_client_enabled: bool            # desktopClientEnabled
    tablet_client_enabled: bool             # tabletClientEnabled
    mobile_client_enabled: bool             # mobileClientEnabled
    available_line_count: int               # availableLineCount
    browser_client_id: Optional[str]        # browserClientId
    desktop_client_id: Optional[str]        # desktopClientId
```

##### Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `line_assignments` | `Optional[ApplicationLineAssignments]` | Line assignments for the desktop client. `None` if desktop client not enabled. |

##### Setter Methods

Each pushes a single-key payload to `PUT v1/people/{id}/features/applications`:

| Method | Parameter |
|--------|-----------|
| `set_ring_devices_for_click_to_dial(enabled: bool)` | `ringDevicesForClickToDialCallsEnabled` |
| `set_ring_devices_for_group_page(enabled: bool)` | `ringDevicesForGroupPageEnabled` |
| `set_ring_devices_for_call_park(enabled: bool)` | `ringDevicesForCallParkEnabled` |
| `set_browser_client_enabled(enabled: bool)` | `browserClientEnabled` |
| `set_desktop_client_enabled(enabled: bool)` | `desktopClientEnabled` |
| `set_tablet_client_enabled(enabled: bool)` | `tabletClientEnabled` |
| `set_mobile_client_enabled(enabled: bool)` | `mobileClientEnabled` |

---

### ApplicationLineAssignments / ApplicationLine

#### ApplicationLineAssignments

```python
class ApplicationLineAssignments:
    def __init__(self, person: wxcadm.Person, client_id: str)
```

Fetches from `GET v1/telephony/config/people/{id}/applications/{client_id}/members`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `person` | `Person` | The owning person |
| `client_id` | `str` | The application client ID |
| `lines` | `list[ApplicationLine]` | The line assignments |
| `model` | `str` | Application name |
| `max_line_count` | `int` | Max device ports |

##### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `(line_owner: Person \| VirtualLine \| Workspace) -> Optional[ApplicationLine]` | Find the line for a given owner |
| `add` | `(line_owner: Person \| VirtualLine \| Workspace) -> ApplicationLine` | Add a new line assignment. Added at next available port with defaults. |

#### ApplicationLine (dataclass)

`@dataclass_json @dataclass`

| Field | Type | API Field Name |
|-------|------|---------------|
| `port` | `int` | `port` |
| `member_type` | `str` | `memberType` |
| `id` | `str` | `id` |
| `line_type` | `str` | `lineType` |
| `primary_owner` | `bool` | `primaryOwner` |
| `num_lines` | `int` | `lineWeight` |
| `hotline_enabled` | `bool` | `hotlineEnabled` |
| `allow_call_decline` | `bool` | `allowCallDeclineEnabled` |
| `line_label` | `Optional[str]` | `lineLabel` |
| `hotline_destination` | `Optional[bool]` | `hotlineDestination` |
| `line_owner` | `Person \| Workspace \| VirtualLine \| None` | (resolved in `__post_init__`) |

`__post_init__` resolves `line_owner` by looking up the `id` in the appropriate org collection based on `member_type` (`PEOPLE`, `VIRTUAL_LINE`, `PLACE`).

##### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `set_hotline` | `(enabled: bool, destination: Optional[bool] = None) -> bool` | Enable/disable hotline. `destination` required when enabling. |
| `set_call_decline` | `(enabled: bool) -> bool` | Enable/disable call decline across all endpoints |
| `set_label` | `(label: str \| None) -> bool` | Set line label; `None` reverts to default |
| `delete` | `() -> bool` | Remove this line assignment |

---

### SingleNumberReach / SnrNumber

#### SingleNumberReach

```python
@dataclass
class SingleNumberReach:
    enabled: bool
    alert_all_for_click_to_dial: bool
    numbers: list[SnrNumber]
    person: wxcadm.Person
```

Accessed via `Person.single_number_reach` property.

##### Class Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `from_api` | `(person: Person) -> SingleNumberReach` | Alternate constructor that fetches from API |

##### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_number` | `(phone_number: str, name: str, enabled: bool, do_not_forward_calls: bool = False, answer_confirmation: bool = False) -> SnrNumber` | Add a new SNR destination |

#### SnrNumber

`@dataclass_json @dataclass`

| Field | Type | API Field Name |
|-------|------|---------------|
| `id` | `Optional[str]` | `id` |
| `phone_number` | `str` | `phoneNumber` |
| `enabled` | `bool` | `enabled` |
| `name` | `str` | `name` |
| `do_not_forward_calls` | `bool` | `doNotForwardCallsEnabled` |
| `answer_confirmation` | `bool` | `answerConfirmationEnabled` |

##### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `enable` | `() -> bool` | Enable this SNR number |
| `disable` | `() -> bool` | Disable this SNR number |
| `change_name` | `(name: str) -> bool` | Rename the SNR entry |
| `set_answer_confirmation` | `(enabled: bool) -> bool` | Toggle answer confirmation |
| `set_do_not_forward_calls` | `(enabled: bool) -> bool` | Toggle call forwarding prevention |
| `delete` | `() -> bool` | Delete the SNR number |

> **Note:** In `set_do_not_forward_calls`, the source code sets `self.answer_confirmation = enabled` instead of `self.do_not_forward_calls = enabled` (line 2547 of person.py). This is a confirmed copy-paste bug — the API call itself sends the correct `doNotForwardCallsEnabled` payload, but the local instance attribute is stale after the call. <!-- Verified via wxcadm source 2026-03-19 -->

---

## Person Call Settings Coverage

wxcadm covers **19 of the ~34 person call settings** available through the Webex Calling API. The following settings are **not implemented in wxcadm** and require wxc_sdk or direct Webex REST API calls:

| Setting | Notes |
|---------|-------|
| Call Waiting | Not exposed |
| Selective Call Forwarding (rules-based) | Not exposed |
| Selective Call Acceptance | Not exposed |
| Selective Call Rejection | Not exposed |
| Anonymous Call Rejection (REST) | Available via XSI only (`person.xsi.anonymous_call_rejection`), not via REST API |
| Sequential Ring | Not exposed |
| Simultaneous Ring | Not exposed |
| Priority Alert | Not exposed |
| Incoming Call Notification | Not exposed |
| Connected Line ID Restriction (COLR) | Not exposed |
| Calling Line ID Restriction (CLIR) | Not exposed |
| Music on Hold (person-level) | Not exposed |
| Receptionist Client | Not exposed |
| Call Bridge | Not exposed |
| Agent Join/Unjoin (Call Queue specific) | Not exposed |
| Executive settings (caller-side) | Executive Assistant is covered; the executive's own settings are not |

For the complete person settings surface, see the wxc_sdk person-call-settings docs linked in [See Also](#see-also) below.

---

## wxcadm vs wxc_sdk

### Structural Differences

| Aspect | wxcadm | wxc_sdk |
|--------|--------|---------|
| **Person access** | `org.people.get(email=...)` returns `Person` with methods | `api.people.list(email=...)` returns data-only `Person` objects |
| **Settings access** | Methods on the `Person` object: `person.get_vm_config()` | Separate API class: `api.person_settings.voicemail.read(person_id=...)` |
| **Mutation pattern** | `person.push_vm_config(config)` — method on the instance | `api.person_settings.voicemail.configure(person_id=..., settings=...)` |
| **Lazy loading** | Settings dicts start empty; populated by `get_*()` calls | No state caching; every call hits the API |
| **Data models** | Mix of raw dicts and dataclasses (`BargeInSettings`, `ApplicationServicesSettings`, `SingleNumberReach`) | Strongly typed Pydantic models for everything |
| **List behavior** | `PersonList` extends `UserList` with smart caching + filter memory | Returns plain lists; pagination handled internally |

### Feature Coverage Comparison

| Feature | wxcadm Person | wxc_sdk Equivalent |
|---------|--------------|-------------------|
| User CRUD | `PersonList.create()`, `Person.delete()`, `Person.update_person()` | `PeopleApi.create()`, `.delete()`, `.update()` |
| License management | `assign_wxc()`, `unassign_wxc()`, `set_calling_only()` | Manual via `PeopleApi.update()` |
| Voicemail greeting upload | `upload_busy_greeting()`, `upload_no_answer_greeting()` | `VoicemailApi.configure_busy_greeting()` / `.configure_no_answer_greeting()` <!-- Corrected via wxc_sdk source 2026-03-19 --> |
| Caller ID (friendly) | `set_caller_id(name, number)` with keyword shortcuts | Must build payload manually for `PersonSettingsApi.caller_id.configure()` |
| Call recording (friendly) | `enable_call_recording(type=..., transcribe=..., ai_summary=...)` | Must build `CallRecordingSetting` model manually |
| XSI session | `start_xsi()` — built-in XSI integration | Not available |
| Spark ID decode | `spark_id` property (base64 decode) | Not available |
| ECBN management | `ecbn` property, `set_ecbn()`, `ecbn_null_change()` | `PersonSettingsApi.ecbn` (`ECBNApi`) <!-- Verified via wxc_sdk source 2026-03-19 --> |
| Single Number Reach | `single_number_reach` property with full `SnrNumber` management | `PersonSettingsApi.single_number_reach` (`SingleNumberReachApi`) <!-- Verified via wxc_sdk source 2026-03-19 --> |
| Application line assignments | `ApplicationLineAssignments` with add/remove/configure | `PersonSettingsApi.app_shared_line` (`AppSharedLineApi`) — has `search_members()`, `get_members()`, `update_members()` <!-- Corrected via wxc_sdk source 2026-03-19 --> |
| Hunt Group / Call Queue membership | `hunt_groups`, `call_queues` properties (reverse lookup) | Must query `HuntGroupApi` / `CallQueueApi` directly |
| Monitoring (who monitors whom) | `monitoring` property, `get_monitored_by()` | `PersonSettingsApi.monitoring` |
| User Groups | `UserGroups`/`UserGroup` classes with CRUD | `GroupsApi` (at `api.groups`) — list, create, get, update, delete, members <!-- Corrected via wxc_sdk source 2026-03-19 --> |
| Voice Messages (Me scope) | `Me.get_voice_messages()`, `Me.voicemail_summary` | `TelephonyApi.voice_messaging` (`VoiceMessagingApi`) — `.summary()`, `.list()`, `.delete()`, `.mark_as_read()`, `.mark_as_unread()` <!-- Corrected via wxc_sdk source 2026-03-19 --> |

### wxcadm-Unique Capabilities

These features have no direct wxc_sdk equivalent or are significantly more convenient in wxcadm:

1. **`set_caller_id(name, number)`** — keyword-based shortcuts (`"direct"`, `"location"`, or custom) instead of building the raw payload
2. **`enable_call_recording(...)`** — single method with all recording parameters including AI transcription/summary flags
3. **`set_calling_only()`** — one-call license cleanup that intelligently keeps screen share
4. **`ecbn_null_change()`** — backend bug workaround not present in wxc_sdk
5. **`spark_id`** — decoded internal identifier
6. **`start_xsi()`** — integrated XSI session management
7. **`get_full_config()`** — batch fetch of all person settings
8. **`PersonList` filter memory** — `refresh()` re-runs with the same filters
9. **Reverse hunt group/call queue lookups** — `person.hunt_groups` and `person.call_queues` search the org
10. **`ApplicationLineAssignments`** — manages shared call appearances on the desktop client with `add()`, line labels, hotline, and call decline settings

---

## Gotchas

- **`role_names()` returns only the first role.** <!-- Verified via wxcadm source 2026-03-19 --> The source code has `return roles` inside the `for` loop (line 483 of person.py), so it exits after resolving the first role ID instead of collecting all of them.
- **`SnrNumber.set_do_not_forward_calls()` has a confirmed copy-paste bug.** <!-- Verified via wxcadm source 2026-03-19 --> The method sets `self.answer_confirmation = enabled` instead of `self.do_not_forward_calls = enabled` on the local instance (line 2547 of person.py). The API payload is correct, but the local state is stale after the call.
- **Reverse group lookups are slow on large orgs.** `person.hunt_groups` and `person.call_queues` iterate every hunt group/call queue in the org and check each agent list. On orgs with many groups, this generates significant API traffic.
- **`push_call_recording()` silently strips Dubber keys.** The method removes `serviceProvider`, `externalGroup`, and `externalIdentifier` before PUT, since the API rejects them. If you build a config dict from a GET response and push it back, this is handled automatically, but be aware the round-trip is not lossless.
- **wxc_sdk equivalents have been verified and corrected.** <!-- Verified via wxc_sdk source 2026-03-19 --> Key corrections: voicemail greeting upload uses `VoicemailApi.configure_busy_greeting()` / `.configure_no_answer_greeting()`; application line assignments use `AppSharedLineApi` (not "not exposed"); groups use `GroupsApi` (not `GroupApi`); voice messages use `TelephonyApi.voice_messaging` (not `.voicemail`).
- **`get_full_config()` returns `False` silently for non-WxC users.** If you call it on a person without a Webex Calling license, it returns `False` instead of raising an exception. Check the return value or verify `person.wxc` first.

## See Also

- [person-call-settings-handling.md](person-call-settings-handling.md) — wxc_sdk call handling settings (forwarding, call waiting, sequential ring, simultaneous ring, selective forwarding/acceptance/rejection)
- [person-call-settings-media.md](person-call-settings-media.md) — wxc_sdk media and recording settings (call recording, voicemail, music on hold)
- [person-call-settings-permissions.md](person-call-settings-permissions.md) — wxc_sdk permissions and screening settings (outgoing permission, incoming permission, caller ID, anonymous call rejection)
- [person-call-settings-behavior.md](person-call-settings-behavior.md) — wxc_sdk behavior and presence settings (calling behavior, DND, hoteling, barge-in, push-to-talk)
