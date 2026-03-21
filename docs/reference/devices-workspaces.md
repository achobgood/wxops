<!-- Updated by playbook session 2026-03-18 -->

# Devices & Workspaces — wxc_sdk Reference

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: webex-device.json
- developer.webex.com Workspace APIs

Workspaces represent physical places where people work — conference rooms, meeting spaces, lobbies, desks. Devices are associated with workspaces. The wxc_sdk provides four API modules for managing workspaces and their configurations.

**SDK access path:** `api.workspaces`, `api.workspace_settings`, `api.workspace_locations`, `api.workspace_personalization`

---

## Table of Contents

- [Workspaces API](#workspaces-api)
  - [Data Models](#workspace-data-models)
  - [WorkspacesApi Methods](#workspacesapi-methods)
- [Workspace Settings API](#workspace-settings-api)
  - [Calling Settings Sub-APIs](#calling-settings-sub-apis)
  - [Workspace Devices API](#workspace-devices-api)
  - [Workspace Numbers API](#workspace-numbers-api)
- [Workspace Locations API (Legacy)](#workspace-locations-api-legacy)
  - [Location Data Models](#workspace-location-data-models)
  - [WorkspaceLocationApi Methods](#workspacelocationapi-methods)
  - [Floor Management](#floor-management)
- [Workspace Personalization API](#workspace-personalization-api)
- [Required Scopes](#required-scopes)
- [Code Examples](#code-examples)
- [Raw HTTP](#raw-http)
- [CLI Examples](#cli-examples)
  - [Workspaces CRUD](#workspaces-crud)
  - [Workspace Settings](#workspace-settings)
  - [Workspace Locations (Legacy)](#workspace-locations-legacy)

---

## Workspaces API

`api.workspaces` — CRUD operations on workspaces, including calling enablement, calendar integration, hotdesking, and device association.

### Workspace Data Models

#### WorkSpaceType

Enum defining workspace purpose:

| Value | Enum Member | Description |
|-------|------------|-------------|
| `notSet` | `WorkSpaceType.not_set` | No workspace type set |
| `focus` | `WorkSpaceType.focus` | High concentration |
| `huddle` | `WorkSpaceType.huddle` | Brainstorm/collaboration |
| `meetingRoom` | `WorkSpaceType.meeting_room` | Dedicated meeting space |
| `open` | `WorkSpaceType.open` | Open space |
| `desk` | `WorkSpaceType.desk` | Individual desk |
| `other` | `WorkSpaceType.other` | Unspecified |

#### CallingType

Enum defining the calling configuration for a workspace:

| Value | Enum Member | Description |
|-------|------------|-------------|
| `freeCalling` | `CallingType.free` | Free Calling |
| `hybridCalling` | `CallingType.hybrid` | Hybrid Calling (on-premise CUCM + cloud) |
| `webexEdgeForDevices` | `CallingType.edge_for_devices` | Webex Edge For Devices |
| `thirdPartySipCalling` | `CallingType.third_party` | Third-party SIP calling |
| `webexCalling` | `CallingType.webex` | Webex Calling |
| `none` | `CallingType.none` | No calling |

#### CalendarType

Enum for calendar integration:

| Value | Enum Member | Description |
|-------|------------|-------------|
| `none` | `CalendarType.none` | No calendar |
| `google` | `CalendarType.google` | Google Calendar |
| `microsoft` | `CalendarType.microsoft` | Microsoft Exchange or Office 365 |

#### WorkspaceSupportedDevices

Enum for device types a workspace supports:

| Value | Enum Member | Description |
|-------|------------|-------------|
| `collaborationDevices` | `WorkspaceSupportedDevices.collaboration_devices` | Collaboration devices (Room/Board/Desk series) |
| `phones` | `WorkspaceSupportedDevices.phones` | MPP phones |

#### HotdeskingStatus

| Value | Enum Member |
|-------|------------|
| `on` | `HotdeskingStatus.on` |
| `off` | `HotdeskingStatus.off` |
| `none` | `HotdeskingStatus.none_` |

#### Calendar

```python
class Calendar(ApiModel):
    calendar_type: Optional[CalendarType]       # alias: 'type'
    email_address: Optional[str]                # not set when type is 'none'
    resource_group_id: Optional[str]            # only for on-premise Microsoft calendar
```

#### WorkspaceCalling

```python
class WorkspaceCalling(ApiModel):
    type: Optional[CallingType]
    hybrid_calling: Optional[WorkspaceCallingHybridCalling]   # only when type is hybridCalling
    webex_calling: Optional[WorkspaceWebexCalling]            # only when type is webexCalling
```

**Important:** Due to a backend limitation, `webex_calling` details are never returned by the workspace GET API. They are only used when creating a workspace.

#### WorkspaceWebexCalling

```python
class WorkspaceWebexCalling(ApiModel):
    phone_number: Optional[str]
    extension: Optional[str]
    location_id: Optional[str]        # Calling location ID
    licenses: Optional[list[str]]     # Webex Calling license IDs
```

#### Workspace

The main workspace model with all fields:

```python
class Workspace(ApiModel):
    workspace_id: Optional[str]                            # alias: 'id'
    org_id: Optional[str]
    location_id: Optional[str]                             # preferred; use /locations API
    workspace_location_id: Optional[str]                   # legacy; prefer location_id
    floor_id: Optional[str]
    display_name: Optional[str]
    capacity: Optional[int]
    workspace_type: Optional[WorkSpaceType]                # alias: 'type'
    sip_address: Optional[str]
    created: Optional[datetime.datetime]
    calling: Optional[WorkspaceCalling]
    hybrid_calling: Optional[WorkspaceEmail]
    calendar: Optional[Calendar]
    notes: Optional[str]
    hotdesking_status: Optional[HotdeskingStatus]
    supported_devices: Optional[WorkspaceSupportedDevices]
    device_hosted_meetings: Optional[DeviceHostedMeetings]
    device_platform: Optional[DevicePlatform]
    indoor_navigation: Optional[WorkspaceIndoorNavigation]
    health: Optional[WorkspaceHealth]
    devices: Optional[list[Device]]
    capabilities: Optional[CapabilityMap]
    planned_maintenance: Optional[WorkspacePlannedMaintenance]
```

**Key constraints:**
- `location_id` and `supported_devices` **cannot be changed** once set on creation.
- `sip_address`, `created`, `health`, and `devices` are read-only.
- Use `Workspace.create(display_name="name")` as a factory for minimal create payloads.

#### CapabilityMap

Sensor/feature capabilities of workspace devices:

```python
class CapabilityMap(ApiModel):
    occupancy_detection: Optional[SupportAndConfiguredInfo]
    presence_detection: Optional[SupportAndConfiguredInfo]
    ambient_noise: Optional[SupportAndConfiguredInfo]
    sound_level: Optional[SupportAndConfiguredInfo]
    temperature: Optional[SupportAndConfiguredInfo]
    air_quality: Optional[SupportAndConfiguredInfo]
    relative_humidity: Optional[SupportAndConfiguredInfo]
    hot_desking: Optional[SupportAndConfiguredInfo]
    check_in: Optional[SupportAndConfiguredInfo]
    adhoc_booking: Optional[SupportAndConfiguredInfo]
```

Each `SupportAndConfiguredInfo` has `.supported` (bool) and `.configured` (bool).

#### WorkspaceHealth

```python
class WorkspaceHealth(ApiModel):
    level: Optional[WorkspaceHealthLevel]          # error | warning | info | ok
    issues: Optional[list[WorkspaceHealthIssue]]
```

Each `WorkspaceHealthIssue` has: `id`, `created_at`, `title`, `description`, `recommended_action`, `level`.

### WorkspacesApi Methods

#### list

```python
def list(
    self,
    location_id: str = None,
    workspace_location_id: str = None,        # deprecated, use location_id
    floor_id: str = None,
    display_name: str = None,
    capacity: int = None,                     # -1 = no capacity set
    workspace_type: WorkSpaceType = None,
    calling: CallingType = None,
    supported_devices: WorkspaceSupportedDevices = None,
    calendar: CalendarType = None,
    device_hosted_meetings_enabled: bool = None,
    device_platform: DevicePlatform = None,
    health_level: WorkspaceHealthLevel = None,
    include_devices: bool = None,
    include_capabilities: bool = None,
    planned_maintenance: MaintenanceMode = None,
    custom_attribute: str = None,
    org_id: str = None,
    **params
) -> Generator[Workspace, None, None]
```

Returns a paginated generator of `Workspace` instances. Use `include_devices=True` to embed device details in the response.

#### create

```python
def create(
    self,
    settings: Workspace,
    org_id: str = None
) -> Workspace
```

Creates a new workspace. Omitting `calling` defaults to free calling. Omitting `calendar` defaults to no calendar.

**Webex Calling workspace requirements (non-hotdesk):**
- `location_id` is required
- Either `phone_number` or `extension` (or both) in `webex_calling` is required
- `licenses` list is optional; if omitted, the oldest suitable license is auto-applied

**Hot desk only workspace restrictions:**
- `phone_number` and `extension` are not applicable
- `device_hosted_meetings` and `calendar` are not applicable

#### details

```python
def details(
    self,
    workspace_id: str,
    include_devices: bool = None
) -> Workspace
```

Get full details for a single workspace by ID.

#### update

```python
def update(
    self,
    workspace_id: str,
    settings: Workspace
) -> Workspace
```

Updates a workspace. Include all fields from a GET response. Omitting optional fields (`capacity`, `type`, `notes`) clears them. `location_id`, `supported_devices`, `calendar`, and `calling` are preserved when omitted.

**Restrictions:**
- `calling` can only be updated if current type is `freeCalling`, `none`, `thirdPartySipCalling`, or `webexCalling`.
- Cannot change `calling` to `none`, `thirdPartySipCalling`, or `webexCalling` if devices are present.
- `location_id` and `supported_devices` cannot be changed after initial creation.

#### delete_workspace

```python
def delete_workspace(
    self,
    workspace_id: str
) -> None
```

Deletes the workspace and all associated devices. Deleted devices must be reactivated.

#### capabilities

```python
def capabilities(
    self,
    workspace_id: str
) -> CapabilityMap
```

Returns the capability map (sensor/feature status) for a workspace.

---

## Workspace Settings API

`api.workspace_settings` — calling-related settings for workspaces. Most settings mirror the person settings API; pass the workspace ID as the `person_id` parameter.

### Calling Settings Sub-APIs

All sub-APIs below use `ApiSelector.workspace` internally. When calling methods on these, pass the **workspace ID** as the `person_id` parameter.

| Attribute | API Class | Purpose |
|-----------|-----------|---------|
| `anon_calls` | `AnonCallsApi` | Anonymous call rejection |
| `barge` | `BargeApi` | Barge-in settings |
| `call_bridge` | `CallBridgeApi` | Call bridge settings |
| `call_intercept` | `CallInterceptApi` | Call intercept |
| `call_policy` | `CallPolicyApi` | Call policy |
| `call_waiting` | `CallWaitingApi` | Call waiting |
| `caller_id` | `CallerIdApi` | Caller ID configuration |
| `dnd` | `DndApi` | Do Not Disturb |
| `ecbn` | `ECBNApi` | Emergency callback number |
| `forwarding` | `PersonForwardingApi` | Call forwarding rules |
| `monitoring` | `MonitoringApi` | Monitoring (busy lamp field) |
| `music_on_hold` | `MusicOnHoldApi` | Music on hold |
| `permissions_in` | `IncomingPermissionsApi` | Incoming call permissions |
| `permissions_out` | `OutgoingPermissionsApi` | Outgoing call permissions |
| `priority_alert` | `PriorityAlertApi` | Priority alert |
| `privacy` | `PrivacyApi` | Privacy settings |
| `push_to_talk` | `PushToTalkApi` | Push to talk |
| `selective_accept` | `SelectiveAcceptApi` | Selective call acceptance |
| `selective_forward` | `SelectiveForwardApi` | Selective call forwarding |
| `selective_reject` | `SelectiveRejectApi` | Selective call rejection |
| `sequential_ring` | `SequentialRingApi` | Sequential ring |
| `sim_ring` | `SimRingApi` | Simultaneous ring |
| `voicemail` | `VoicemailApi` | Voicemail settings |
| `available_numbers` | `AvailableNumbersApi` | Available number lookup |

### Workspace Devices API

`api.workspace_settings.devices` — manages telephony devices assigned to a workspace.

**Base path:** `telephony/config/workspaces`

#### list

```python
def list(
    self,
    workspace_id: str,
    org_id: str = None
) -> Generator[TelephonyDevice, None, None]
```

Returns a paginated generator of `TelephonyDevice` instances for the workspace.

#### list_and_counts

```python
def list_and_counts(
    self,
    workspace_id: str,
    org_id: str = None
) -> DeviceList
```

Returns a `DeviceList` object with devices and count metadata (not paginated — single response).

#### modify_hoteling

```python
def modify_hoteling(
    self,
    workspace_id: str,
    hoteling: Hoteling,
    org_id: str = None
) -> None
```

Modifies hoteling settings for workspace devices. The `Hoteling` model comes from `wxc_sdk.person_settings`.

### Workspace Numbers API

`api.workspace_settings.numbers` — manages PSTN phone numbers associated with a workspace.

#### Data Models

```python
class WorkspaceNumbers(ApiModel):
    distinctive_ring_enabled: Optional[bool]
    phone_numbers: list[UserNumber]          # primary and alternate numbers
    workspace: IdOnly                         # workspace identifier
    location: IdAndName                       # location identifier + name
    organization: IdAndName                   # org identifier + name
```

```python
class UpdateWorkspacePhoneNumber(ApiModel):
    primary: Optional[bool]                  # marks as primary number
    action: Optional[PatternAction]          # 'ADD' or 'DELETE'
    direct_number: Optional[str]             # E.164 phone number
    extension: Optional[str]                 # extension
    ring_pattern: Optional[RingPattern]      # ring pattern for this number
```

#### read

```python
def read(
    self,
    workspace_id: str,
    org_id: str = None
) -> WorkspaceNumbers
```

Lists PSTN phone numbers associated with the workspace, including location and organization info.

#### update

```python
def update(
    self,
    workspace_id: str,
    phone_numbers: list[UpdateWorkspacePhoneNumber],
    distinctive_ring_enabled: bool = None,
    org_id: str = None
) -> None
```

Assign or unassign alternate phone numbers. Phone numbers must follow E.164 format (National format also accepted for US).

**Note:** This API is only available for **professional licensed** workspaces.

---

## Workspace Locations API (Legacy)

> **Deprecation warning:** The SDK logs `'use of the workspace locations API is not recommended. use locations API instead'` on every call. Prefer the `/locations` API (`api.locations`) for new integrations.

`api.workspace_locations` — manages legacy workspace location records (physical location metadata with coordinates).

### Workspace Location Data Models

#### WorkspaceLocation

```python
class WorkspaceLocation(ApiModel):
    id: str
    location_id: Optional[str]
    display_name: str
    address: str
    country_code: str                # ISO 3166-1
    city_name: str
    longitude: Optional[float]
    latitude: Optional[float]
    notes: Optional[str]
```

Helper properties:
- `.id_uuid` — extracts the UUID portion from the base64-encoded ID
- `.org_id_uuid` — extracts the org UUID from the base64-encoded ID

#### WorkspaceLocationFloor

```python
class WorkspaceLocationFloor(ApiModel):
    id: str
    location_id: str
    floor_number: int
    display_name: str
```

### WorkspaceLocationApi Methods

#### list

```python
def list(
    self,
    display_name: str = None,
    address: str = None,
    country_code: str = None,
    city_name: str = None,
    org_id: str = None,
    **params
) -> Generator[WorkspaceLocation, None, None]
```

#### create

```python
def create(
    self,
    display_name: str,
    address: str,
    country_code: str,
    latitude: float,
    longitude: float,
    city_name: str = None,
    notes: str = None,
    org_id: str = None
) -> WorkspaceLocation
```

#### details

```python
def details(
    self,
    location_id: str,
    org_id: str = None
) -> WorkspaceLocation
```

#### update

```python
def update(
    self,
    location_id: str,
    settings: WorkspaceLocation,
    org_id: str = None
) -> WorkspaceLocation
```

Include all fields from a GET response. Omitting `city_name` or `notes` (setting to `None`) clears them.

#### delete

```python
def delete(
    self,
    location_id: str,
    org_id: str = None
) -> None
```

Workspaces associated with the deleted location lose their location but can be reassigned.

### Floor Management

`api.workspace_locations.floors` — CRUD for floors within a workspace location.

#### floors.list

```python
def list(
    self,
    location_id: str,
    org_id: str = None
) -> Generator[WorkspaceLocationFloor, None, None]
```

#### floors.create

```python
def create(
    self,
    location_id: str,
    floor_number: int,
    display_name: str = None,
    org_id: str = None
) -> WorkspaceLocationFloor
```

#### floors.details

```python
def details(
    self,
    location_id: str,
    floor_id: str,
    org_id: str = None
) -> WorkspaceLocationFloor
```

#### floors.update

```python
def update(
    self,
    location_id: str,
    floor_id: str,
    settings: WorkspaceLocationFloor,
    org_id: str = None
) -> WorkspaceLocationFloor
```

#### floors.delete

```python
def delete(
    self,
    location_id: str,
    floor_id: str,
    org_id: str = None
) -> None
```

---

## Workspace Personalization API

`api.workspace_personalization` — enables Personal Mode on Webex Edge registered devices. This is a one-time migration operation from on-premise to cloud-registered personal mode.

**Applies only to Webex Edge registered devices.**

### Prerequisites

- Workspace must contain a **single** Webex Edge registered, shared mode device
- Workspace must have **no calendars** configured
- The device must be **online**

### personalize_a_workspace

```python
def personalize_a_workspace(
    self,
    workspace_id: str,
    email: str
) -> None
```

Initiates asynchronous personalization for the given user email. Returns a `Location` header with a URL pointing to the task status endpoint. The task typically completes in ~30 seconds.

### get_personalization_task

```python
def get_personalization_task(
    self,
    workspace_id: str
) -> WorkspacePersonalizationTaskResponse
```

Returns task status:
- While in progress: returns `Accepted` with `Retry-After` header
- On completion: returns `OK` with result body

```python
class WorkspacePersonalizationTaskResponse(ApiModel):
    success: Optional[bool]
    error_description: Optional[str]      # populated on failure
```

---

## Required Scopes

| API Module | Read Scope | Write Scope |
|-----------|-----------|-------------|
| Workspaces | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Workspace Settings (devices) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Workspace Settings (numbers) | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| Workspace Locations | `spark-admin:workspace_locations_read` | `spark-admin:workspace_locations_write` |
| Workspace Personalization | — | `spark-admin:devices_write`, `spark:xapi_commands`, `spark:xapi_statuses`, `Identity:one_time_password` |

Partner administrators can manage workspaces in other organizations by supplying `org_id`.

---

## Code Examples

### Create a Webex Calling workspace with a 3rd-party phone

From `workspace_w_3rd_party.py` — the key provisioning logic:

```python
from wxc_sdk.workspaces import (
    CallingType, Workspace, WorkspaceCalling,
    WorkspaceSupportedDevices, WorkspaceWebexCalling,
)
from wxc_sdk.common import DevicePlatform

# Build workspace settings
settings = Workspace(
    location_id=location.location_id,
    display_name="My Workspace",
    type=WorkSpaceType.desk,
    capacity=1,
    supported_devices=WorkspaceSupportedDevices.phones,
    device_platform=DevicePlatform.cisco,
    calling=WorkspaceCalling(
        type=CallingType.webex,
        webex_calling=WorkspaceWebexCalling(
            licenses=[calling_license_id],
            extension="2001",
            location_id=location.location_id,
        ),
    ),
)

# Create the workspace
workspace = await api.workspaces.create(settings=settings)

# Create a device in the workspace by MAC address
device = await api.devices.create_by_mac_address(
    mac="DEADDEAD0001",
    workspace_id=workspace.workspace_id,
    model="Generic IPPhone Customer Managed",
    password="generated_password",
)

# Get device details (SIP credentials, outbound proxy)
details = await api.telephony.devices.details(device_id=device.device_id)
sip_user = details.owner.sip_user_name
line_port = details.owner.line_port
outbound_proxy = details.proxy.outbound_proxy
```

### Add a user as secondary line on a workspace device

From `workspaces_and_users.py`:

```python
from wxc_sdk.common import UserType
from wxc_sdk.telephony.devices import DeviceMember

# Find workspace by name
ws_list = await api.workspaces.list(display_name='Classroom')
target_ws = next(ws for ws in ws_list if ws.display_name == 'Classroom')

# Get devices in the workspace
ws_devices = await api.workspace_settings.devices.list(
    workspace_id=target_ws.workspace_id
)

# Get current members for each device
device_members = await asyncio.gather(
    *[api.telephony.devices.members(device_id=d.device_id) for d in ws_devices]
)

# Keep the workspace (place) membership as line 1, add user as line 2
for device, dmr in zip(ws_devices, device_members):
    new_members = [m for m in dmr.members if m.member_type == UserType.place]
    new_members.append(DeviceMember(member_id=user.person_id))
    await api.telephony.devices.update_members(
        device_id=device.device_id, members=new_members
    )
    await api.telephony.devices.apply_changes(device_id=device.device_id)
```

### List workspaces filtered by calling type

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.workspaces import CallingType

api = WebexSimpleApi(tokens=tokens)

# Get all Webex Calling workspaces with device details
for ws in api.workspaces.list(calling=CallingType.webex, include_devices=True):
    print(f"{ws.display_name} — SIP: {ws.sip_address}")
    if ws.devices:
        for device in ws.devices:
            print(f"  Device: {device.display_name}")
```

### Read and update workspace phone numbers

```python
# Read current numbers
ws_numbers = api.workspace_settings.numbers.read(workspace_id=workspace_id)
for num in ws_numbers.phone_numbers:
    print(f"  {num.external} (primary={num.primary})")

# Add an alternate number
from wxc_sdk.workspace_settings.numbers import UpdateWorkspacePhoneNumber
from wxc_sdk.common import PatternAction

api.workspace_settings.numbers.update(
    workspace_id=workspace_id,
    phone_numbers=[
        UpdateWorkspacePhoneNumber(
            action=PatternAction.add,       # PatternAction.add = 'ADD', PatternAction.delete = 'DELETE' <!-- Verified via wxc_sdk source (common/__init__.py) 2026-03-19 -->
            direct_number="+14155551234",
            primary=False,
        )
    ],
)
```

### Delete a workspace

```python
# WARNING: Also deletes all associated devices (they must be reactivated)
await api.workspaces.delete_workspace(workspace_id=workspace.workspace_id)
```

---

## Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All workspace operations can be performed via raw HTTP using `api.session.rest_*()`. This is the preferred execution pattern -- wxc_sdk handles auth and session management, while you control the exact request.

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"
```

### Workspaces CRUD

```python
# ── List workspaces ──────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/workspaces", params={
    "max": 1000,
    "calling": "webexCalling",           # filter by calling type
    "includeDevices": "true",            # embed device details
})
workspaces = result.get("items", [])     # NOTE: response key is "items", NOT "workspaces"

# ── List with location filter ────────────────────────────────────
result = api.session.rest_get(f"{BASE}/workspaces", params={
    "locationId": location_id,
    "max": 1000,
})
workspaces = result.get("items", [])

# ── Get workspace details ────────────────────────────────────────
ws = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}")

# ── Get workspace details with devices ───────────────────────────
ws = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}", params={
    "includeDevices": "true",
})

# ── Create a workspace ───────────────────────────────────────────
body = {
    "displayName": "Lobby Phone",
    "locationId": location_id,
    "type": "desk",
    "capacity": 1,
    "supportedDevices": "phones",
    "hotdeskingStatus": "off",
    "calling": {
        "type": "webexCalling",
        "webexCalling": {
            "extension": "2001",
            "locationId": location_id,
            "licenses": [calling_license_id],
        },
    },
}
result = api.session.rest_post(f"{BASE}/workspaces", json=body)
new_ws_id = result["id"]

# ── Update a workspace (full PUT -- include all fields) ──────────
ws = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}")
ws["displayName"] = "Lobby Phone (Updated)"
result = api.session.rest_put(f"{BASE}/workspaces/{workspace_id}", json=ws)

# ── Delete a workspace ───────────────────────────────────────────
# WARNING: Also deletes all associated devices (they must be reactivated)
api.session.rest_delete(f"{BASE}/workspaces/{workspace_id}")

# ── Get workspace capabilities ───────────────────────────────────
caps = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/capabilities")
```

### Workspace Call Settings (Features)

Workspace call settings use the `/workspaces/{workspaceId}/features/` path:

```python
# ── Call Forwarding ──────────────────────────────────────────────
fwd = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/callForwarding")
body = {"callForwarding": {"always": {"enabled": True, "destination": "+15551234567"}}}
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/callForwarding", json=body)

# ── Call Waiting ─────────────────────────────────────────────────
cw = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/callWaiting")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/callWaiting", json={"enabled": True})

# ── Caller ID ────────────────────────────────────────────────────
cid = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/callerId")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/callerId", json={
    "selected": "DIRECT_LINE",
    "externalCallerIdNamePolicy": "DIRECT_LINE",
})

# ── Monitoring (BLF) ────────────────────────────────────────────
mon = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/monitoring")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/monitoring", json={
    "enableCallParkNotification": True,
})

# ── Numbers ──────────────────────────────────────────────────────
nums = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/numbers")

# ── Incoming Permission ──────────────────────────────────────────
perm_in = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/incomingPermission")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/incomingPermission", json={
    "useCustomEnabled": False,
    "externalTransfer": "ALLOW_ALL_EXTERNAL",
})

# ── Outgoing Permission ─────────────────────────────────────────
perm_out = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/outgoingPermission")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/outgoingPermission", json={
    "useCustomEnabled": False,
})

# ── Outgoing Permission Access Codes ─────────────────────────────
codes = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/outgoingPermission/accessCodes")
access_codes = codes.get("accessCodes", [])

api.session.rest_post(f"{BASE}/workspaces/{workspace_id}/features/outgoingPermission/accessCodes", json={
    "code": "1234",
    "description": "Long distance override",
})

# ── Auto Transfer Numbers ────────────────────────────────────────
xfer = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/outgoingPermission/autoTransferNumbers")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/outgoingPermission/autoTransferNumbers", json={
    "useCustomTransferNumbers": True,
    "autoTransferNumber1": "+15551234567",
})

# ── Call Intercept ───────────────────────────────────────────────
intercept = api.session.rest_get(f"{BASE}/workspaces/{workspace_id}/features/intercept")
api.session.rest_put(f"{BASE}/workspaces/{workspace_id}/features/intercept", json={
    "enabled": True,
})
```

### Workspace Telephony Devices

Workspace telephony device operations use the `/telephony/config/workspaces/` path:

```python
# ── List telephony devices for workspace ─────────────────────────
result = api.session.rest_get(f"{BASE}/telephony/config/workspaces/{workspace_id}/devices")
devices = result.get("devices", [])

# ── Modify hoteling ─────────────────────────────────────────────
api.session.rest_put(f"{BASE}/telephony/config/workspaces/{workspace_id}/devices/hoteling", json={
    "enabled": True,
    "limitGuestUse": True,
    "guestHotelingLimit": 12,
})
```

### Raw HTTP Gotchas

1. **Response key is `items` not `workspaces`** -- When listing workspaces, the response uses the generic `items` key, not `workspaces`. This differs from most telephony APIs that use a domain-specific key (e.g., `virtualLines`, `virtualExtensions`).
2. **No auto-pagination** -- Use `max=1000` for the first page. The Workspaces API does not auto-paginate; check for a `next` link in the response if you have more than 1000 workspaces.
3. **`includeDevices` and `includeCapabilities` are strings** -- Pass `"true"` not `True` in query params.
4. **Two different base paths** -- CRUD and features use `/workspaces/{id}` and `/workspaces/{id}/features/*`. Telephony device operations use `/telephony/config/workspaces/{id}/devices`.
5. **Update is full PUT** -- Omitting optional fields (`capacity`, `type`, `notes`) clears them. `locationId`, `supportedDevices`, `calendar`, and `calling` are preserved when omitted.
6. **`webexCalling` details not returned on GET** -- The `calling.webexCalling` object is write-only (used on create). GET responses only include `calling.type`.

---

## CLI Examples

Three `wxcli` command groups cover workspace operations:

| CLI Group | Commands | Purpose |
|-----------|----------|---------|
| `wxcli workspaces` | 6 | Workspace CRUD + capabilities |
| `wxcli workspace-settings` | 96 | Workspace call settings (mirrors person settings) |
| `wxcli workspace-locations` | 10 | Legacy workspace locations + floors |

### Workspaces CRUD

```bash
# List all workspaces (table output by default)
wxcli workspaces list

# List Webex Calling workspaces only
wxcli workspaces list --calling webexCalling

# List workspaces at a specific location
wxcli workspaces list --location-id <location_id>

# List workspaces with device details included
wxcli workspaces list --calling webexCalling --include-devices true

# Filter by workspace type (desk, meetingRoom, huddle, focus, open, other)
wxcli workspaces list --type meetingRoom

# Filter by supported device type
wxcli workspaces list --supported-devices phones

# Show workspace details (JSON output by default)
wxcli workspaces show <workspace_id>

# Show workspace details in table format
wxcli workspaces show <workspace_id> -o table

# Get workspace capabilities (sensor/feature support)
wxcli workspaces show-capabilities <workspace_id>

# Create a workspace (simple — flat options)
wxcli workspaces create --display-name "Lobby Phone" --type desk --capacity 1

# Create a Webex Calling workspace (requires --json-body for nested calling config)
wxcli workspaces create --json-body '{
  "displayName": "Conference Room B",
  "locationId": "<location_id>",
  "type": "meetingRoom",
  "capacity": 10,
  "supportedDevices": "phones",
  "calling": {
    "type": "webexCalling",
    "webexCalling": {
      "extension": "2050",
      "locationId": "<location_id>"
    }
  }
}'

# Update a workspace display name
wxcli workspaces update <workspace_id> --display-name "Lobby Phone (Updated)"

# Update workspace type and capacity
wxcli workspaces update <workspace_id> --type meetingRoom --capacity 12

# Enable hotdesking on a workspace
wxcli workspaces update <workspace_id> --hotdesking-status on

# Delete a workspace (prompts for confirmation)
wxcli workspaces delete <workspace_id>

# Delete without confirmation prompt
wxcli workspaces delete <workspace_id> --force
```

### Workspace Settings

> **License note:** Most `/telephony/config/workspaces/{id}/` settings require **Professional** license. Basic workspaces only support `musicOnHold` and `doNotDisturb` at this path. For Basic workspaces, use the `/workspaces/{id}/features/` path family (callForwarding, callWaiting, callerId, intercept, monitoring). See the [endpoint access by license tier table](#key-patterns-and-gotchas) in Gotchas for the full matrix.

The `wxcli workspace-settings` group has 96 commands mirroring person call settings. All take a `workspace_id` as a positional argument.

#### Call Handling

```bash
# ── Call Forwarding ──────────────────────────────────────────────
# Show call forwarding settings
wxcli workspace-settings show <workspace_id>

# Enable always-forward to a destination (nested config requires --json-body)
wxcli workspace-settings update <workspace_id> --json-body '{
  "callForwarding": {
    "always": {
      "enabled": true,
      "destination": "+15551234567",
      "ringReminderEnabled": true
    }
  }
}'

# Enable busy-forward and no-answer-forward
wxcli workspace-settings update <workspace_id> --json-body '{
  "callForwarding": {
    "busy": {"enabled": true, "destination": "+15559876543"},
    "noAnswer": {"enabled": true, "destination": "+15559876543", "numberOfRings": 5}
  },
  "businessContinuity": {"enabled": true, "destination": "+15550001111"}
}'

# ── Call Waiting ─────────────────────────────────────────────────
# Show call waiting settings
wxcli workspace-settings show-call-waiting <workspace_id>

# Enable call waiting
wxcli workspace-settings update-call-waiting <workspace_id> --enabled

# Disable call waiting
wxcli workspace-settings update-call-waiting <workspace_id> --no-enabled

# ── Do Not Disturb ───────────────────────────────────────────────
# Show DND settings (works on Basic + Professional)
wxcli workspace-settings show-do-not-disturb <workspace_id>

# Enable DND with ring splash
wxcli workspace-settings update-do-not-disturb <workspace_id> --enabled --ring-splash-enabled

# Disable DND
wxcli workspace-settings update-do-not-disturb <workspace_id> --no-enabled

# ── Call Intercept ───────────────────────────────────────────────
# Show intercept settings
wxcli workspace-settings show-intercept <workspace_id>

# Enable call intercept (simple toggle)
wxcli workspace-settings update-intercept <workspace_id> --enabled

# Enable with full config (intercept all incoming, allow outgoing to a destination)
wxcli workspace-settings update-intercept <workspace_id> --json-body '{
  "enabled": true,
  "incoming": {
    "type": "INTERCEPT_ALL",
    "voicemailEnabled": true
  },
  "outgoing": {
    "type": "INTERCEPT_ALL",
    "transferEnabled": true,
    "destination": "+15551234567"
  }
}'

# Disable call intercept
wxcli workspace-settings update-intercept <workspace_id> --no-enabled
```

#### Voicemail & Media

```bash
# ── Voicemail (Professional license required) ────────────────────
# Show voicemail settings
wxcli workspace-settings show-voicemail <workspace_id>

# Enable voicemail with send-all-calls
wxcli workspace-settings update-voicemail <workspace_id> --json-body '{
  "enabled": true,
  "sendAllCalls": {"enabled": false},
  "sendBusyCalls": {"enabled": true, "greeting": "DEFAULT"},
  "sendUnansweredCalls": {"enabled": true, "greeting": "DEFAULT", "numberOfRings": 6}
}'

# Disable voicemail
wxcli workspace-settings update-voicemail <workspace_id> --no-enabled

# ── Caller ID ────────────────────────────────────────────────────
# Show caller ID settings
wxcli workspace-settings list <workspace_id>

# Set caller ID to direct line
wxcli workspace-settings update-caller-id <workspace_id> --selected DIRECT_LINE

# Set caller ID to location number
wxcli workspace-settings update-caller-id <workspace_id> \
  --selected LOCATION_NUMBER \
  --external-caller-id-name-policy LOCATION

# Set caller ID to custom number
wxcli workspace-settings update-caller-id <workspace_id> \
  --selected CUSTOM --custom-number "+15551234567"

# ── Music on Hold (works on Basic + Professional) ────────────────
# Show music on hold settings
wxcli workspace-settings show-music-on-hold <workspace_id>

# Enable music on hold with default greeting
wxcli workspace-settings update-music-on-hold <workspace_id> --moh-enabled --greeting DEFAULT

# Enable with custom audio file
wxcli workspace-settings update-music-on-hold <workspace_id> --json-body '{
  "mohEnabled": true,
  "greeting": "CUSTOM",
  "audioAnnouncementFile": {
    "id": "<announcement_file_id>",
    "fileName": "lobby-music.wav",
    "mediaFileType": "WAV",
    "level": "ORGANIZATION"
  }
}'

# Disable music on hold
wxcli workspace-settings update-music-on-hold <workspace_id> --no-moh-enabled

# ── Call Recording (Professional license required) ───────────────
# Show call recording settings
wxcli workspace-settings show-call-recordings <workspace_id>

# Enable always-on recording
wxcli workspace-settings update-call-recordings <workspace_id> --enabled --record Always

# Enable on-demand recording with voicemail recording
wxcli workspace-settings update-call-recordings <workspace_id> \
  --enabled --record "On Demand with User Initiated Start" --record-voicemail-enabled

# Enable with notification beep and start/stop announcements
wxcli workspace-settings update-call-recordings <workspace_id> --json-body '{
  "enabled": true,
  "record": "Always",
  "recordVoicemailEnabled": true,
  "notification": {"type": "Beep", "enabled": true},
  "startStopAnnouncement": {
    "internalCallsEnabled": true,
    "pstnCallsEnabled": true
  }
}'

# Disable call recording
wxcli workspace-settings update-call-recordings <workspace_id> --no-enabled
```

#### Permissions

```bash
# ── Incoming Permissions ─────────────────────────────────────────
# Show incoming permission settings
wxcli workspace-settings show-incoming-permission <workspace_id>

# ── Outgoing Permissions ─────────────────────────────────────────
# Show outgoing permission settings (table output by default)
wxcli workspace-settings list-outgoing-permission <workspace_id>

# Show in JSON
wxcli workspace-settings list-outgoing-permission <workspace_id> -o json

# ── Access Codes ─────────────────────────────────────────────────
# List access codes for outgoing permissions
wxcli workspace-settings list-access-codes <workspace_id>

# ── Anonymous Call Reject (Professional license required) ────────
# Show anonymous call reject settings
wxcli workspace-settings show-anonymous-call-reject <workspace_id>

# ── Barge In (Professional license required) ─────────────────────
# Show barge-in settings
wxcli workspace-settings show-barge-in <workspace_id>

# ── Privacy (Professional license required) ──────────────────────
# Show privacy settings
wxcli workspace-settings list-privacy <workspace_id>
```

#### Behavior & Numbers

```bash
# ── Monitoring (BLF) ────────────────────────────────────────────
# Show monitoring settings
wxcli workspace-settings show-monitoring <workspace_id>

# ── Numbers ──────────────────────────────────────────────────────
# List phone numbers assigned to a workspace
wxcli workspace-settings list-numbers <workspace_id>

# Assign an alternate number (nested config requires --json-body)
wxcli workspace-settings update-numbers <workspace_id> --json-body '{
  "distinctiveRingEnabled": true,
  "phoneNumbers": [
    {
      "action": "ADD",
      "directNumber": "+15551234567",
      "extension": "2051",
      "primary": false
    }
  ]
}'

# Remove a number
wxcli workspace-settings update-numbers <workspace_id> --json-body '{
  "phoneNumbers": [
    {
      "action": "DELETE",
      "directNumber": "+15551234567"
    }
  ]
}'

# List available phone numbers for a workspace
wxcli workspace-settings list-available-numbers-workspaces

# List available ECBN numbers
wxcli workspace-settings list-available-numbers-emergency-callback-number <workspace_id>

# List available call forwarding numbers
wxcli workspace-settings list-available-numbers-call-forwarding <workspace_id>
```

#### Full Command Reference

All 96 `workspace-settings` commands:

| Category | Commands |
|----------|----------|
| **Call Forwarding** | `show`, `update` |
| **Call Waiting** | `show-call-waiting`, `update-call-waiting` |
| **Caller ID** | `list` (show), `update-caller-id` |
| **Monitoring** | `show-monitoring`, `update-monitoring` |
| **Numbers** | `list-numbers`, `update-numbers` |
| **Incoming Permissions** | `show-incoming-permission`, `update-incoming-permission` |
| **Outgoing Permissions** | `list-outgoing-permission`, `update-outgoing-permission` |
| **Access Codes** | `list-access-codes`, `create`, `update-access-codes`, `delete`, `delete-access-codes` |
| **Intercept** | `show-intercept`, `update-intercept`, `upload-call-intercept` |
| **Auto Transfer Numbers** | `show-auto-transfer-numbers`, `update-auto-transfer-numbers` |
| **Music on Hold** | `show-music-on-hold`, `update-music-on-hold` |
| **Digit Patterns** | `list-digit-patterns`, `create-digit-patterns`, `show-digit-patterns`, `update-digit-patterns-outgoing-permission`, `update-digit-patterns-outgoing-permission-1`, `delete-digit-patterns-outgoing-permission`, `delete-digit-patterns-outgoing-permission-1` |
| **Call Recording** | `show-call-recordings`, `update-call-recordings` |
| **Anonymous Call Reject** | `show-anonymous-call-reject`, `update-anonymous-call-reject` |
| **Barge In** | `show-barge-in`, `update-barge-in` |
| **DND** | `show-do-not-disturb`, `update-do-not-disturb` |
| **Call Bridge** | `show-call-bridge`, `update-call-bridge` |
| **Push to Talk** | `list-push-to-talk`, `update-push-to-talk` |
| **Privacy** | `list-privacy`, `update-privacy` |
| **Voicemail** | `show-voicemail`, `update-voicemail`, `update-passcode`, `configure-busy-voicemail`, `configure-no-answer` |
| **Sequential Ring** | `list-sequential-ring`, `update-sequential-ring`, `show-criteria-sequential-ring`, `update-criteria-sequential-ring`, `delete-criteria-sequential-ring`, `create-criteria-sequential-ring` |
| **Call Policies** | `show-call-policies`, `update-call-policies` |
| **Simultaneous Ring** | `list-simultaneous-ring`, `update-simultaneous-ring`, `show-criteria-simultaneous-ring`, `update-criteria-simultaneous-ring`, `delete-criteria-simultaneous-ring`, `create-criteria-simultaneous-ring` |
| **Selective Reject** | `list-selective-reject`, `update-selective-reject`, `show-criteria-selective-reject`, `update-criteria-selective-reject`, `delete-criteria-selective-reject`, `create-criteria-selective-reject` |
| **Selective Accept** | `list-selective-accept`, `update-selective-accept`, `show-criteria-selective-accept`, `update-criteria-selective-accept`, `delete-criteria-selective-accept`, `create-criteria-selective-accept` |
| **Priority Alert** | `list-priority-alert`, `update-priority-alert`, `show-criteria-priority-alert`, `update-criteria-priority-alert`, `delete-criteria-priority-alert`, `create-criteria-priority-alert` |
| **Selective Forward** | `list-selective-forward`, `update-selective-forward`, `show-criteria-selective-forward`, `update-criteria-selective-forward`, `delete-criteria-selective-forward`, `create-criteria-selective-forward` |
| **Available Numbers** | `list-available-numbers-workspaces`, `list-available-numbers-emergency-callback-number`, `list-available-numbers-call-forwarding`, `list-available-numbers-call-intercept`, `list-available-numbers-fax-message`, `list-available-numbers-secondary` |

### Workspace Locations (Legacy)

> **Deprecation note:** Workspace Locations is a legacy API. Prefer `wxcli locations` for new work.

```bash
# List all workspace locations
wxcli workspace-locations list

# Filter by country
wxcli workspace-locations list --country-code US

# Filter by city
wxcli workspace-locations list --city-name "San Francisco"

# Filter by display name
wxcli workspace-locations list --display-name "HQ"

# Show workspace location details
wxcli workspace-locations show <location_id>

# List floors for a workspace location
wxcli workspace-locations list-floors <location_id>

# Show floor details
wxcli workspace-locations show-floors <location_id> <floor_id>
```

---

## Key Patterns and Gotchas

1. **`location_id` vs `workspace_location_id`** — Always use `location_id` (from the `/locations` API). `workspace_location_id` is legacy and deprecated.

2. **`supported_devices` and `location_id` are immutable** — Set correctly on creation; they cannot be changed afterward.

3. **`webex_calling` details not returned on GET** — Due to a backend limitation, the `WorkspaceCalling.webex_calling` field is never populated in API responses. It is only used when creating a workspace.

4. **Workspace settings mirror person settings** — Most `api.workspace_settings.*` sub-APIs are the same classes used for person settings but with `ApiSelector.workspace`. Pass the workspace ID as `person_id`.

5. **Workspace Locations API is deprecated** — The SDK emits a warning on every call. Use `api.locations` instead for new code.

6. **Hot desk workspaces** — When creating with `hotdesking_status=on`, `phone_number`, `extension`, `device_hosted_meetings`, and `calendar` are not applicable and will cause errors if provided.

7. **License handling** — When creating a Webex Calling workspace, you can provide multiple license IDs; the oldest suitable one is applied. If omitted, auto-assigned from active subscriptions.

8. **Device cleanup on workspace delete** — Deleting a workspace deletes all associated devices. Those devices must be reactivated to be reused.

9. **Personalization is one-time** — The Workspace Personalization API is for migrating Edge devices from shared to personal mode. It requires the device to be online and the workspace to have no calendar configured.

10. **Workspace call settings endpoint access by license tier.** <!-- Verified via live API 2026-03-19 -->

    | Endpoint Path | Basic (webexCalling) | Professional Required |
    |---------------|---------------------|-----------------------|
    | `/workspaces/{id}/features/callForwarding` | 200 | — |
    | `/workspaces/{id}/features/callWaiting` | 200 | — |
    | `/workspaces/{id}/features/callerId` | 200 | — |
    | `/workspaces/{id}/features/intercept` | 200 | — |
    | `/workspaces/{id}/features/monitoring` | 200 | — |
    | `/workspaces/{id}/features/voicemail` | 404 | N/A (wrong path) |
    | `/telephony/config/workspaces/{id}/musicOnHold` | 200 | — |
    | `/telephony/config/workspaces/{id}/doNotDisturb` | 200 | — |
    | `/telephony/config/workspaces/{id}/anonymousCallReject` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/callPolicies` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/voicemail` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/bargeIn` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/callBridge` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/pushToTalk` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/privacy` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/selectiveReject` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/selectiveAccept` | 405 | Yes |
    | `/telephony/config/workspaces/{id}/callRecording` | 404 | May not exist |

## CLI: `workspace-metrics` (Workspace Sensor Metrics)

The `workspace-metrics` CLI group retrieves environmental sensor data and usage duration metrics from workspace devices (RoomOS endpoints with sensors).

| Command | Description |
|---------|-------------|
| `workspace-metrics list` | Get workspace sensor metrics (sound, temperature, humidity, etc.) |
| `workspace-metrics list-workspace-duration-metrics` | Get workspace usage duration metrics (time used, time booked) |

```bash
# Get temperature readings for a workspace (last 24 hours, daily aggregation)
wxcli workspace-metrics list --workspace-id <workspace_id> --metric-name temperature --aggregation daily

# Get people count data in Fahrenheit
wxcli workspace-metrics list --workspace-id <workspace_id> --metric-name peopleCount --aggregation hourly

# Get ambient noise levels with a time range
wxcli workspace-metrics list --workspace-id <workspace_id> --metric-name ambientNoise \
  --from 2026-03-01T00:00:00Z --to 2026-03-21T00:00:00Z

# Get workspace usage duration (how long the room was actually used)
wxcli workspace-metrics list-workspace-duration-metrics --workspace-id <workspace_id> \
  --measurement timeUsed --aggregation daily

# Get booked vs used comparison
wxcli workspace-metrics list-workspace-duration-metrics --workspace-id <workspace_id> \
  --measurement timeBooked --aggregation daily
```

---

## See Also

- **[devices-core.md](devices-core.md)** — Device activation codes, MAC provisioning, and telephony device settings (members/lines, line key templates, layouts). Use that API for device-level operations after associating a device with a workspace.
- **[devices-dect.md](devices-dect.md)** — DECT network and handset management, including DECT workspace associations and hot desking session management.
- **[emergency-services.md](emergency-services.md)** — Emergency callback number (ECBN) configuration. The `ecbn` sub-API listed in the calling settings table above is documented in detail there.
