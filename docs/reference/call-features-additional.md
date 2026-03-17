# Additional Call Features Reference

Comprehensive reference for Webex Calling Paging Groups, Call Park, Call Park Extensions, Call Pickup, Voicemail Groups, and CX Essentials using the `wxc_sdk`.

---

## Table of Contents

1. [SDK Access Paths](#sdk-access-paths)
2. [Required Scopes](#required-scopes)
3. [Paging Groups](#paging-groups)
4. [Call Park](#call-park)
5. [Call Park Extensions](#call-park-extensions)
6. [Call Pickup](#call-pickup)
7. [Voicemail Groups](#voicemail-groups)
8. [CX Essentials](#cx-essentials)
9. [Data Models Quick Reference](#data-models-quick-reference)
10. [Dependencies & Relationships](#dependencies--relationships)

---

## SDK Access Paths

All features in this document are accessed through the `TelephonyApi` instance:

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens='...')

api.telephony.paging                # PagingApi
api.telephony.callpark              # CallParkApi
api.telephony.callpark_extension    # CallparkExtensionApi
api.telephony.callpickup            # CallPickupApi
api.telephony.voicemail_groups      # VoicemailGroupsApi
api.telephony.cx_essentials         # CustomerExperienceEssentialsApi
```

<!-- NEEDS VERIFICATION: exact attribute names on api.telephony for callpark, callpark_extension, callpickup -->

---

## Required Scopes

| Operation | Scope |
|-----------|-------|
| Read paging groups, call parks, call pickups, call park extensions, voicemail groups | `spark-admin:telephony_config_read` |
| Create/update/delete paging groups, call parks, call pickups, call park extensions, voicemail groups | `spark-admin:telephony_config_write` |
| Read CX Essentials queue recording | `spark-admin:people_read` |
| Configure CX Essentials queue recording | `spark-admin:people_write` |
| Read CX Essentials wrap-up reasons, screen pop, available agents | `spark-admin:telephony_config_read` |
| Modify CX Essentials wrap-up reasons, screen pop | `spark-admin:telephony_config_write` |

All APIs accept an optional `org_id` parameter, allowing partner administrators to operate on a customer organization.

---

## Paging Groups

### Overview

Group Paging allows a person to place a **one-way call or group page** to up to **75 people and/or workspaces** by dialing a number or extension assigned to a specific paging group. The paging service makes a simultaneous call to all assigned targets.

Use cases: overhead announcements, warehouse pages, emergency notifications to a group of phones.

### SDK API Class

```python
class PagingApi(ApiChild, base='telephony/config')
```

### API Operations

#### List Paging Groups

Returns all paging groups across the organization (or filtered by location).

```python
def list(
    self,
    location_id: str = None,
    name: str = None,
    phone_number: str = None,
    org_id: str = None,
    **params
) -> Generator[Paging, None, None]
```

- `location_id`: Filter to a specific location. Default is all locations.
- `name`: Filter by matching name.
- `phone_number`: Filter by matching primary phone number or extension.
- Returns paginated results with item key `locationPaging`.

#### Get Paging Group Details

```python
def details(
    self,
    location_id: str,
    paging_id: str,
    org_id: str = None
) -> Paging
```

Returns the full `Paging` object including `originators` and `targets` with detailed agent info (first/last name, phone number, extension, type).

#### Create Paging Group

```python
def create(
    self,
    location_id: str,
    settings: Paging,
    org_id: str = None
) -> str  # returns new paging group ID
```

**Validation rule**: If `originators` are provided, `originator_caller_id_enabled` is **required** (raises `TypeError` otherwise).

Convenience factory:

```python
settings = Paging.create(name='Warehouse Page', extension='8100')
paging_id = api.telephony.paging.create(location_id=loc_id, settings=settings)
```

#### Update Paging Group

```python
def update(
    self,
    location_id: str,
    update: Paging,
    paging_id: str,
    org_id: str = None
) -> None
```

#### Delete Paging Group

```python
def delete_paging(
    self,
    location_id: str,
    paging_id: str,
    org_id: str = None
) -> None
```

#### Get Available Phone Numbers

```python
def primary_available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

Lists service and standard numbers available for assignment as the paging group's primary phone number. Numbers are associated with the specified location, can be active or inactive, and must be unassigned.

### Key Data Models

#### `Paging`

| Field | Type | Required for Create | Notes |
|-------|------|-------------------|-------|
| `paging_id` | `str` (alias: `id`) | -- | Read-only, set by API |
| `enabled` | `bool` | No | Default varies |
| `name` | `str` | **Yes** | Max 30 chars |
| `phone_number` | `str` | **One of phone_number/extension** | Max 23 chars |
| `extension` | `str` | **One of phone_number/extension** | 2-10 chars |
| `toll_free_number` | `bool` | -- | Read-only |
| `language` | `str` | No | Read-only (use `language_code` for write) |
| `language_code` | `str` | No | e.g., `en_us` |
| `originator_caller_id_enabled` | `bool` | **Yes, if originators set** | Shows page originator ID on target caller ID |
| `originators` | `list[PagingAgent]` | No | People/workspaces who can originate pages |
| `targets` | `list[PagingAgent]` | No | People/workspaces/virtual lines who receive pages |
| `first_name` / `last_name` | `str` | No | **Deprecated** -- use `direct_line_caller_id_name` and `dial_by_name` |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | No | Replacement for first/last name |
| `dial_by_name` | `str` | No | Name used for dial-by-name directory |

#### `PagingAgent`

| Field | Type | Notes |
|-------|------|-------|
| `agent_id` (alias: `id`) | `str` | **Only field sent in create/update** |
| `first_name` | `str` | Read-only (returned from details) |
| `last_name` | `str` | Read-only |
| `agent_type` (alias: `type`) | `UserType` | `PEOPLE` or `PLACE` |
| `phone_number` | `str` | Read-only |
| `extension` | `str` | Read-only |
| `routing_prefix` | `str` | Read-only |
| `esn` | `str` | Read-only (routing prefix + extension) |

**Important**: When creating or updating, `originators` and `targets` are serialized as flat lists of IDs only, not full agent objects.

### Phone Number / Extension Assignment

- Either `phone_number` or `extension` is mandatory (enforced by `Paging.create()` factory).
- Use `primary_available_phone_numbers()` to find unassigned numbers at a location.
- The `toll_free_number` flag is read-only and reflects whether the assigned number is toll-free.

### Member Management

- **Originators**: People/workspaces who can initiate a page. Set via `originators` field as a list of `PagingAgent` with `agent_id` populated.
- **Targets**: People/workspaces/virtual lines who receive the page broadcast. Set via `targets` field. Up to 75 targets.
- On create/update, pass agent IDs only. On read (details), full agent info is returned.

---

## Call Park

### Overview

Call Park allows a call recipient to place a call **on hold at a designated park location** so it can be retrieved from another device. Users park calls against extensions or Call Park Extensions, then other users retrieve them by dialing the park extension.

Use cases: front-desk parks a call, employee picks it up from their desk phone; warehouse environments where users move between stations.

### SDK API Class

```python
class CallParkApi(ApiChild, base='telephony/config/callParks')
```

### API Operations

#### List Call Parks

```python
def list(
    self,
    location_id: str,
    order: str = None,       # 'ASC' or 'DSC'
    name: str = None,        # filter by name (max 80 chars)
    org_id: str = None,
    **params
) -> Generator[CallPark, None, None]
```

**NOTE**: The Call Park ID will change upon modification of the Call Park name.

#### Get Call Park Details

```python
def details(
    self,
    location_id: str,
    callpark_id: str,
    org_id: str = None
) -> CallPark
```

#### Create Call Park

```python
def create(
    self,
    location_id: str,
    settings: CallPark,
    org_id: str = None
) -> str  # returns new call park ID
```

Convenience factory (minimal call park with recall to parking user only):

```python
settings = CallPark.default(name='Lobby Park')
park_id = api.telephony.callpark.create(location_id=loc_id, settings=settings)
```

#### Update Call Park

```python
def update(
    self,
    location_id: str,
    callpark_id: str,
    settings: CallPark,
    org_id: str = None
) -> str  # returns updated call park ID
```

**NOTE**: The Call Park ID changes when the name is modified. The returned ID is the new one.

#### Delete Call Park

```python
def delete_callpark(
    self,
    location_id: str,
    callpark_id: str,
    org_id: str = None
) -> None
```

#### Get Available Agents

```python
def available_agents(
    self,
    location_id: str,
    call_park_name: str = None,
    name: str = None,
    phone_number: str = None,
    order: str = None,
    org_id: str = None,
    **params
) -> Generator[PersonPlaceAgent, None, None]
```

Returns people and workspaces eligible to be added as call park agents. Sort fields: `fname`, `lname`, `number`, `extension` (pipe-separated, max 3).

#### Get Available Recall Hunt Groups

```python
def available_recalls(
    self,
    location_id: str,
    name: str = None,
    order: str = None,
    org_id: str = None,
    **params
) -> Generator[AvailableRecallHuntGroup, None, None]
```

Lists hunt groups that can be used as recall destinations.

#### Get Location Call Park Settings

```python
def call_park_settings(
    self,
    location_id: str,
    org_id: str = None
) -> LocationCallParkSettings
```

#### Update Location Call Park Settings

```python
def update_call_park_settings(
    self,
    location_id: str,
    settings: LocationCallParkSettings,
    org_id: str = None
) -> None
```

### Key Data Models

#### `CallPark`

| Field | Type | Notes |
|-------|------|-------|
| `callpark_id` (alias: `id`) | `str` | Read-only. **Changes when name is modified.** |
| `name` | `str` | Max 80 chars |
| `location_name` | `str` | Read-only |
| `location_id` | `str` | Read-only |
| `recall` | `RecallHuntGroup` | Recall options (who gets alerted when park times out) |
| `agents` | `list[PersonPlaceAgent]` | People/workspaces eligible to receive parked calls |
| `park_on_agents_enabled` | `bool` | Whether calls can be parked on agents as a destination |
| `call_park_extensions` | `list[CallParkExtension]` | Park extensions assigned to this call park |

**Important**: On create/update, `agents` and `call_park_extensions` are serialized as flat lists of IDs only.

#### `RecallHuntGroup`

| Field | Type | Notes |
|-------|------|-------|
| `hunt_group_id` | `str` | Hunt group ID for recall alternate destination |
| `hunt_group_name` | `str` | Read-only (excluded from create/update) |
| `option` | `CallParkRecall` | Recall behavior enum |

#### `CallParkRecall` (Enum)

| Value | Constant | Description |
|-------|----------|-------------|
| `ALERT_PARKING_USER_ONLY` | `parking_user_only` | Alert only the user who parked the call |
| `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP` | `parking_user_first_then_hunt_group` | Alert parking user first, then hunt group |
| `ALERT_HUNT_GROUP_ONLY` | `hunt_group_only` | Alert hunt group only |

#### `CallParkSettings` (Location-Level)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `ring_pattern` | `RingPattern` | `normal` | Ring pattern when park extension is called |
| `recall_time` | `int` | `45` | Seconds before recall (30-600 range) |
| `hunt_wait_time` | `int` | `45` | Seconds before reverting to hunt group (30-600 range) |

#### `LocationCallParkSettings`

Wraps `call_park_recall` (`RecallHuntGroup`) and `call_park_settings` (`CallParkSettings`) into a single object for location-level configuration.

### Phone Number / Extension Assignment

Call Parks themselves do not have phone numbers or extensions directly. They are groups of agents and park extensions. Calls are parked **to** a Call Park Extension (see next section) or to an agent's extension.

### Member Management

- **Agents**: People and workspaces eligible to receive parked calls. Added via the `agents` field (list of IDs on create/update).
- **Call Park Extensions**: Dedicated extensions for parking. Added via `call_park_extensions` field (list of IDs on create/update).
- Use `available_agents()` to discover eligible agents at a location.
- Use `available_recalls()` to discover hunt groups eligible as recall destinations.

---

## Call Park Extensions

### Overview

Call Park Extensions are **dedicated extensions defined within the Call Park service** for holding parked calls. A user parks a call to one of these extensions, and another user retrieves it by dialing that extension. Call Park Extensions can also be added as **monitored lines** on Cisco phones, so users can park and retrieve calls by pressing a line key.

The Call Park service is enabled for all users by default.

### SDK API Class

```python
class CallparkExtensionApi(ApiChild, base='telephony')
```

### API Operations

#### List Call Park Extensions

```python
def list(
    self,
    extension: str = None,
    name: str = None,
    location_id: str = None,
    location_name: str = None,
    order: str = None,
    org_id: str = None,
    **params
) -> Generator[CallParkExtension, None, None]
```

Lists across all locations if `location_id` is not specified. Sort fields: `groupName`, `callParkExtension`, `callParkExtensionName`, `callParkExtensionExternalId`.

#### Get Call Park Extension Details

```python
def details(
    self,
    location_id: str,
    cpe_id: str,
    org_id: str = None
) -> CallParkExtension
```

Returns `CallParkExtension` with `name` and `extension` fields.

#### Create Call Park Extension

```python
def create(
    self,
    location_id: str,
    name: str,           # max 30 chars
    extension: str,      # 2-10 chars, must be unique
    org_id: str = None
) -> str  # returns new call park extension ID
```

#### Update Call Park Extension

```python
def update(
    self,
    location_id: str,
    cpe_id: str,
    name: str = None,
    extension: str = None,
    org_id: str = None
) -> None
```

Both `name` and `extension` are optional -- only the provided fields are updated.

#### Delete Call Park Extension

```python
def delete(
    self,
    location_id: str,
    cpe_id: str,
    org_id: str = None
) -> None
```

### Key Data Models

#### `CallParkExtension` (from `wxc_sdk.common`)

| Field | Type | Notes |
|-------|------|-------|
| `cpe_id` (alias: `id`) | `str` | Unique identifier |
| `name` | `str` | Max 30 chars |
| `extension` | `str` | 2-10 chars, must be unique within location |

This is a lightweight model -- just a name and extension. The `CallParkExtension` model is shared from `wxc_sdk.common` and also used within the `CallPark` model to list assigned park extensions.

### Phone Number / Extension Assignment

- Each Call Park Extension has a **unique extension** within its location.
- No phone number assignment -- these are extension-only entities.
- Extensions are dialed internally to park or retrieve calls.

### Member Management

Call Park Extensions do not have members. They are simple extension holders assigned to Call Park groups (see the `call_park_extensions` field on `CallPark`).

---

## Call Pickup

### Overview

Call Pickup enables a user (agent) to **answer any ringing line within their pickup group**. When a call rings unanswered for a configurable period, all members of the pickup group can be notified via audio, visual, or both.

Use cases: small offices where team members cover each other's calls; receptionist groups.

### SDK API Class

```python
class CallPickupApi(ApiChild, base='telephony/config/callPickups')
```

### API Operations

#### List Call Pickups

```python
def list(
    self,
    location_id: str,
    order: Literal['ASC', 'DSC'] = None,
    name: str = None,
    org_id: str = None,
    **params
) -> Generator[CallPickup, None, None]
```

**NOTE**: The Call Pickup ID will change upon modification of the Call Pickup name.

#### Get Call Pickup Details

```python
def details(
    self,
    location_id: str,
    pickup_id: str,
    org_id: str = None
) -> CallPickup
```

#### Create Call Pickup

```python
def create(
    self,
    location_id: str,
    settings: CallPickup,
    org_id: str = None
) -> str  # returns new call pickup ID
```

#### Update Call Pickup

```python
def update(
    self,
    location_id: str,
    pickup_id: str,
    settings: CallPickup,
    org_id: str = None
) -> str  # returns updated call pickup ID
```

**NOTE**: The Call Pickup ID changes when the name is modified.

#### Delete Call Pickup

```python
def delete_pickup(
    self,
    location_id: str,
    pickup_id: str,
    org_id: str = None
) -> None
```

#### Get Available Agents

```python
def available_agents(
    self,
    location_id: str,
    call_pickup_name: str = None,
    name: str = None,
    phone_number: str = None,
    order: str = None,
    org_id: str = None,
    **params
) -> Generator[PersonPlaceAgent, None, None]
```

Returns people, workspaces, and virtual lines eligible to be added to pickup groups. Sort fields: `fname`, `lname`, `number`, `extension` (pipe-separated, max 3).

### Key Data Models

#### `CallPickup`

| Field | Type | Notes |
|-------|------|-------|
| `pickup_id` (alias: `id`) | `str` | Read-only. **Changes when name is modified.** |
| `name` | `str` | Max 80 chars |
| `location_name` | `str` | Read-only |
| `location_id` | `str` | Read-only |
| `notification_type` | `PickupNotificationType` | How members are notified of unanswered calls |
| `notification_delay_timer_seconds` | `int` | Seconds before notification fires |
| `agents` | `list[PersonPlaceAgent]` | People, workspaces, virtual lines in the group |

**Important**: On create/update, `agents` is serialized as a flat list of IDs only.

#### `PickupNotificationType` (Enum)

| Value | Constant | Description |
|-------|----------|-------------|
| `NONE` | `none` | No notification sent |
| `AUDIO_ONLY` | `audio_only` | Audio notification after delay |
| `VISUAL_ONLY` | `visual_only` | Visual notification after delay |
| `AUDIO_AND_VISUAL` | `audio_and_visual` | Both audio and visual after delay |

### Phone Number / Extension Assignment

Call Pickup groups do not have their own phone numbers or extensions. They are groupings of agents -- members pick up ringing calls within the group using a feature access code (e.g., `*98`).

<!-- NEEDS VERIFICATION: exact feature access code for call pickup -->

### Member Management

- **Agents**: People, workspaces, and virtual lines. Set via the `agents` field (list of IDs on create/update).
- Use `available_agents()` to discover eligible agents at a location that are not yet assigned to another pickup group.
- A user can only belong to **one** call pickup group at a time.

<!-- NEEDS VERIFICATION: one-pickup-group-per-user constraint -->

---

## Voicemail Groups

### Overview

Voicemail Groups provide a **shared voicemail box** (and optional inbound fax box) that can be assigned to users or call routing features like auto attendants, call queues, or hunt groups. They are useful for team-level voicemail where multiple people need access to the same messages.

### SDK API Class

```python
class VoicemailGroupsApi(ApiChild, base='telephony/config/voicemailGroups')
```

### API Operations

#### List Voicemail Groups

```python
def list(
    self,
    location_id: str = None,
    name: str = None,
    phone_number: str = None,
    org_id: str = None,
    **params
) -> Generator[VoicemailGroup, None, None]
```

- `name`: Search (contains) based on voicemail group name.
- `phone_number`: Search (contains) based on number or extension.

#### Get Voicemail Group Details

```python
def details(
    self,
    location_id: str,
    voicemail_group_id: str,
    org_id: str = None
) -> VoicemailGroupDetail
```

#### Create Voicemail Group

```python
def create(
    self,
    location_id: str,
    settings: VoicemailGroupDetail,
    org_id: str = None
) -> str  # returns new voicemail group ID
```

Convenience factory with sensible defaults (internal storage, all notifications disabled):

```python
settings = VoicemailGroupDetail.create(
    name='Support VM',
    extension='8200',
    first_name='Support',
    last_name='Team',
    passcode=740384,
    language_code='en_us',
    phone_number='+14155551234'  # optional
)
vmg_id = api.telephony.voicemail_groups.create(
    location_id=loc_id, settings=settings
)
```

#### Update Voicemail Group

```python
def update(
    self,
    location_id: str,
    voicemail_group_id: str,
    settings: VoicemailGroupDetail,
    org_id: str = None
) -> None
```

#### Delete Voicemail Group

```python
def delete(
    self,
    location_id: str,
    voicemail_group_id: str,
    org_id: str = None
) -> None
```

#### Get Available Phone Numbers

```python
def available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

#### Get Fax Message Available Phone Numbers

```python
def fax_message_available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

Lists numbers available to be assigned as the voicemail group's fax message phone number.

### Key Data Models

#### `VoicemailGroup` (List Model)

| Field | Type | Notes |
|-------|------|-------|
| `group_id` (alias: `id`) | `str` | Unique identifier |
| `name` | `str` | Group name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `extension` | `str` | Extension number |
| `phone_number` | `str` | Phone number |
| `routing_prefix` | `str` | Location routing prefix |
| `esn` | `str` | Routing prefix + extension |
| `enabled` | `bool` | Whether incoming calls are sent to voicemail |
| `toll_free_number` | `bool` | Read-only |

#### `VoicemailGroupDetail` (Detail/Create/Update Model)

| Field | Type | Required for Create | Notes |
|-------|------|-------------------|-------|
| `group_id` (alias: `id`) | `str` | -- | Read-only |
| `name` | `str` | **Yes** | Group name |
| `phone_number` | `str` | No | Voicemail group phone number |
| `extension` | `str` | **Yes** | Extension number |
| `first_name` | `str` | **Yes** | **Deprecated** -- use `direct_line_caller_id_name` |
| `last_name` | `str` | **Yes** | **Deprecated** -- use `direct_line_caller_id_name` |
| `passcode` | `int` | **Yes** | Access passcode |
| `enabled` | `bool` | No | For update only |
| `language_code` | `str` | No | Default `en_us` in factory |
| `greeting` | `Greeting` | No | Greeting type enum |
| `greeting_uploaded` | `bool` | -- | Read-only; `True` if custom greeting uploaded |
| `greeting_description` | `str` | No | Description for custom greeting |
| `message_storage` | `VoicemailMessageStorage` | **Yes** (set by factory) | Storage type config |
| `notifications` | `VoicemailNotifications` | **Yes** (set by factory) | Notification settings |
| `fax_message` | `VoicemailFax` | **Yes** (set by factory) | Fax receive settings |
| `transfer_to_number` | `VoicemailTransferToNumber` | **Yes** (set by factory) | Transfer settings |
| `email_copy_of_message` | `VoicemailCopyOfMessage` | **Yes** (set by factory) | Email copy settings |
| `voice_message_forwarding_enabled` | `bool` | No | Enable/disable voice message forwarding |
| `time_zone` | `str` | No | <!-- NEEDS VERIFICATION: undocumented field --> |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | No | Replaces deprecated first/last name |
| `dial_by_name` | `str` | No | Name for dial-by-name directory |

The `VoicemailGroupDetail.create()` factory sets these defaults:
- `message_storage`: `StorageType.internal`
- `notifications`: disabled
- `fax_message`: disabled
- `transfer_to_number`: disabled
- `email_copy_of_message`: disabled

### Phone Number / Extension Assignment

- `extension` is **required** on create.
- `phone_number` is optional.
- Use `available_phone_numbers()` and `fax_message_available_phone_numbers()` to find unassigned numbers at a location.

### Member Management

Voicemail Groups do not have explicit member lists. They are shared voicemail boxes that are **assigned to** other features (auto attendants, call queues, hunt groups) or users through those features' overflow/no-answer settings.

---

## CX Essentials

### Overview

Webex **Customer Experience Essentials** provides enhanced queue capabilities beyond the Customer Experience Basic suite. It adds features such as:

- **Screen Pop**: Pop a URL (CRM, ticketing system) when an agent receives a queued call
- **Queue Call Recording**: Hosted call recording for quality assurance, compliance, and training
- **Wrap-Up Reasons**: Post-call categorization codes that agents select after ending a call
- **CX Essentials Agent Licensing**: Ability to query agents with CX Essentials licenses

These APIs are distinct from Customer Experience Basic and require CX Essentials licensing.

### SDK API Class

```python
@dataclass(init=False, repr=False)
class CustomerExperienceEssentialsApi(ApiChild, base='telephony/config')
```

Sub-APIs:

```python
api.telephony.cx_essentials.callqueue_recording   # QueueCallRecordingSettingsApi
api.telephony.cx_essentials.wrapup_reasons         # WrapupReasonApi
```

### Screen Pop Configuration

Screen pop lets agents view customer-related info in a pop-up window when receiving a call from a queue.

#### Get Screen Pop Configuration

```python
def get_screen_pop_configuration(
    self,
    location_id: str = None,
    queue_id: str = None,
    org_id: str = None
) -> ScreenPopConfiguration
```

#### Modify Screen Pop Configuration

```python
def modify_screen_pop_configuration(
    self,
    location_id: str,
    queue_id: str,
    settings: ScreenPopConfiguration,
    org_id: str = None
) -> None
```

#### `ScreenPopConfiguration` Model

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Enable/disable screen pop |
| `screen_pop_url` | `str` | URL to pop (CRM, ticketing, etc.) |
| `desktop_label` | `str` | Label for the screen pop config |
| `query_params` | `dict[str, Any]` | Query parameters appended to the screen pop URL |

### Available Agents

#### List CX Essentials Available Agents

```python
def available_agents(
    self,
    location_id: str,
    has_cx_essentials: bool = None,
    org_id: str = None
) -> Generator[AvailableAgent, None, None]
```

- `has_cx_essentials=True`: Returns only agents with CX Essentials license.
- `has_cx_essentials=False`: Returns only agents with CX Basic license.
- Omit for all agents.

### Queue Call Recording

Hosted call recording for queues. Records calls placed and received on the platform for replay and archival.

#### Read Queue Call Recording Settings

```python
def read(
    self,
    location_id: str,
    queue_id: str,
    org_id: str = None
) -> CallRecordingSetting
```

**Scope**: `spark-admin:people_read`

#### Configure Queue Call Recording Settings

```python
def configure(
    self,
    location_id: str,
    queue_id: str,
    recording: CallRecordingSetting,
    org_id: str = None
) -> None
```

**Scope**: `spark-admin:people_write`

**Note**: A person with a Webex Calling Standard license is eligible for call recording only when the recording vendor is Webex.

### Wrap-Up Reasons

Wrap-up reasons let agents categorize the outcome of a call after it ends. Admins configure reasons and assign them to queues. A configurable timer (default 60 seconds) dictates how long agents have to select a reason post-call.

#### List Wrap-Up Reasons (Org-Level)

```python
def list(self) -> List[WrapUpReason]
```

Returns all wrap-up reasons configured for the organization. No parameters needed.

#### Get Wrap-Up Reason Details

```python
def details(
    self,
    wrapup_reason_id: str
) -> WrapUpReasonDetails
```

Returns the reason details including assigned queues.

#### Create Wrap-Up Reason

```python
def create(
    self,
    name: str,
    description: str = None,
    queues: List[str] = None,
    assign_all_queues_enabled: bool = None
) -> str  # returns wrap-up reason ID
```

- `queues`: List of queue IDs to assign.
- `assign_all_queues_enabled`: Assign to all queues at once.

#### Update Wrap-Up Reason

```python
def update(
    self,
    wrapup_reason_id: str,
    name: str = None,
    description: str = None,
    queues_to_assign: List[str] = None,
    queues_to_unassign: List[str] = None,
    assign_all_queues_enabled: bool = None,
    unassign_all_queues_enabled: bool = None
) -> None
```

Queue assignment is **incremental** -- you can assign and unassign specific queues without replacing the full list.

#### Delete Wrap-Up Reason

```python
def delete(
    self,
    wrapup_reason_id: str
) -> None
```

#### Validate Wrap-Up Reason Name

```python
def validate(
    self,
    name: str
) -> None
```

Check if a wrap-up reason name is valid (not already taken). Raises an error on conflict.

#### Read Queue Wrap-Up Settings

```python
def read_queue_settings(
    self,
    location_id: str,
    queue_id: str
) -> QueueWrapupReasonSettings
```

Returns wrap-up configuration for a specific queue: timer settings and assigned reasons.

#### Update Queue Wrap-Up Settings

```python
def update_queue_settings(
    self,
    location_id: str,
    queue_id: str,
    wrapup_reasons: list[str] = None,
    default_wrapup_reason_id: str = None,
    wrapup_timer_enabled: bool = None,
    wrapup_timer: int = None
) -> None
```

- `default_wrapup_reason_id`: Set as `''` (empty string) to clear the default.
- `wrapup_timer`: Timer value in seconds (default is 60).

#### Get Available Queues for Wrap-Up Reason

```python
def available_queues(
    self,
    wrapup_reason_id: str
) -> List[AvailableQueue]
```

Returns queues that are not yet assigned to this wrap-up reason and can be added.

### CX Essentials Data Models

#### `WrapUpReason` (List Model)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Reason name |
| `description` | `str` | Reason description |
| `number_of_queues_assigned` | `int` | Count of assigned queues |

#### `WrapUpReasonDetails` (Detail Model)

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Reason name |
| `description` | `str` | Reason description |
| `default_wrapup_queues_count` | `int` | Number of queues where this is the default |
| `queues` | `list[WrapupReasonQueue]` | Assigned queues with full details |

#### `WrapupReasonQueue`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Queue ID |
| `name` | `str` | Queue name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `phone_number` | `str` | Queue phone number |
| `extension` | `int` | Queue extension |
| `default_wrapup_enabled` | `bool` | Whether this reason is the default for the queue |

#### `QueueWrapupReasonSettings`

| Field | Type | Notes |
|-------|------|-------|
| `wrapup_timer_enabled` | `bool` | Whether the wrap-up timer is active |
| `wrapup_timer` | `int` | Timer value in seconds |
| `wrapup_reasons` | `list[QueueSettingsReason]` | Reasons assigned to this queue |

#### `QueueSettingsReason`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Wrap-up reason ID |
| `name` | `str` | Reason name |
| `description` | `str` | Reason description |
| `default_enabled` | `bool` | Whether this reason is the default for the queue |

#### `AvailableQueue`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Queue ID |
| `name` | `str` | Queue name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `phone_number` | `str` | Queue phone number |
| `extension` | `int` | Queue extension |

---

## Data Models Quick Reference

### Shared Models (from `wxc_sdk.common`)

| Model | Used By | Description |
|-------|---------|-------------|
| `PersonPlaceAgent` | Call Park, Call Pickup | Person/workspace agent with ID, name, phone, extension, type |
| `CallParkExtension` | Call Park, Call Park Extensions | Lightweight model: id, name, extension |
| `RingPattern` | Call Park Settings | Enum: ring pattern (e.g., `normal`) |
| `UserType` | Paging | Enum for person vs. workspace |
| `DirectLineCallerIdName` | Paging, Voicemail Groups | Caller ID name settings (replaces deprecated first/last name) |
| `AvailableNumber` | Paging, Voicemail Groups | Available phone number for assignment |
| `CallRecordingSetting` | CX Essentials (Queue Recording) | Full call recording configuration |

### Feature-Specific Models

| Model | Module | Description |
|-------|--------|-------------|
| `Paging`, `PagingAgent` | `telephony.paging` | Paging group and its members |
| `CallPark`, `CallParkSettings`, `LocationCallParkSettings` | `telephony.callpark` | Call park group and location-level settings |
| `CallParkRecall`, `RecallHuntGroup`, `AvailableRecallHuntGroup` | `telephony.callpark` | Recall behavior when park times out |
| `CallPickup`, `PickupNotificationType` | `telephony.callpickup` | Pickup group and notification enums |
| `VoicemailGroup`, `VoicemailGroupDetail` | `telephony.voicemail_groups` | Voicemail group list/detail models |
| `ScreenPopConfiguration` | `telephony.cx_essentials` | Screen pop settings |
| `WrapUpReason`, `WrapUpReasonDetails`, `QueueWrapupReasonSettings` | `telephony.cx_essentials.wrapup_reasons` | Wrap-up reason models |
| `AvailableQueue`, `WrapupReasonQueue`, `QueueSettingsReason` | `telephony.cx_essentials.wrapup_reasons` | Queue-related models for wrap-up |

---

## Dependencies & Relationships

```
Call Park ──────────── Call Park Extensions (assigned to park groups)
    |
    +──── Agents (PersonPlaceAgent: people, workspaces)
    |
    +──── Recall Hunt Group (optional: fallback when park times out)

Call Pickup ─────────── Agents (PersonPlaceAgent: people, workspaces, virtual lines)

Paging Group ────────── Originators (PagingAgent: who can page)
    |
    +──── Targets (PagingAgent: who receives pages, up to 75)

Voicemail Group ──────── Assigned to auto attendants, call queues, hunt groups
    |
    +──── Available Numbers (for primary and fax)

CX Essentials ────────── Call Queues (screen pop, recording, wrap-up per queue)
    |
    +──── Wrap-Up Reasons (org-level, assigned to queues)
    |
    +──── Available Agents (CX Essentials or Basic licensed)
```

### Key Dependency Notes

1. **Call Park requires Call Park Extensions**: You create Call Park Extensions first, then assign them to Call Park groups.
2. **Call Park recall requires Hunt Groups**: If using `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP` or `ALERT_HUNT_GROUP_ONLY`, a Hunt Group must exist at the location.
3. **CX Essentials requires Call Queues**: Screen pop, queue recording, and wrap-up reasons are all per-queue configurations. Call queues must be created first.
4. **CX Essentials requires licensing**: The `has_cx_essentials` filter on `available_agents()` distinguishes between CX Essentials and CX Basic licensed agents.
5. **Voicemail Groups are location-scoped**: Created within a location, but listed org-wide.
6. **Paging Groups are location-scoped**: Created within a location, but can be listed org-wide.
7. **ID instability for Call Park and Call Pickup**: The IDs for Call Park and Call Pickup entities change when their names are modified. Always re-fetch the ID after a name change.
