<!-- Updated by playbook session 2026-03-18 -->

# Devices & Workspaces — API Reference

## Sources

- OpenAPI spec: specs/webex-device.json
- developer.webex.com Workspace APIs

Workspaces represent physical places where people work — conference rooms, meeting spaces, lobbies, desks. Devices are associated with workspaces. Four API domains cover managing workspaces and their configurations: Workspaces, Workspace Settings, Workspace Locations (legacy), and Workspace Personalization.

---

## Table of Contents

- [Workspaces API](#workspaces-api)
  - [Data Models](#workspace-data-models)
  - [Workspace API Behavior Notes](#workspace-api-behavior-notes)
- [Workspace Settings API](#workspace-settings-api)
  - [Calling Settings Reference](#calling-settings-reference)
  - [Workspace Devices API](#workspace-devices-api)
  - [Workspace Numbers API](#workspace-numbers-api)
- [Workspace Locations API (Legacy)](#workspace-locations-api-legacy)
  - [Location Data Models](#workspace-location-data-models)
  - [Workspace Location API Behavior Notes](#workspace-location-api-behavior-notes)
  - [Floor Management](#floor-management)
- [Workspace Personalization API](#workspace-personalization-api)
- [Required Scopes](#required-scopes)
- [Raw HTTP](#raw-http)
- [CLI Examples](#cli-examples)
  - [Workspaces CRUD](#workspaces-crud)
  - [Workspace Settings](#workspace-settings)
  - [Workspace Locations (Legacy)](#workspace-locations-legacy)

---

## Workspaces API

**Base endpoint:** `/v1/workspaces` — CRUD operations on workspaces, including calling enablement, calendar integration, hotdesking, and device association.

### Workspace Data Models

#### WorkSpaceType

Enum defining workspace purpose:

| Value | Description |
|-------|-------------|
| `notSet` | No workspace type set |
| `focus` | High concentration |
| `huddle` | Brainstorm/collaboration |
| `meetingRoom` | Dedicated meeting space |
| `open` | Open space |
| `desk` | Individual desk |
| `other` | Unspecified |

#### CallingType

Enum defining the calling configuration for a workspace:

| Value | Description |
|-------|-------------|
| `freeCalling` | Free Calling |
| `hybridCalling` | Hybrid Calling (on-premise CUCM + cloud) |
| `webexEdgeForDevices` | Webex Edge For Devices |
| `thirdPartySipCalling` | Third-party SIP calling |
| `webexCalling` | Webex Calling |
| `none` | No calling |

#### CalendarType

Enum for calendar integration:

| Value | Description |
|-------|-------------|
| `none` | No calendar |
| `google` | Google Calendar |
| `microsoft` | Microsoft Exchange or Office 365 |

#### WorkspaceSupportedDevices

Enum for device types a workspace supports:

| Value | Description |
|-------|-------------|
| `collaborationDevices` | Collaboration devices (Room/Board/Desk series) |
| `phones` | MPP phones |

#### HotdeskingStatus

Accepted values: `on`, `off`, `none`.

#### Calendar

| Field | Type | Description |
|-------|------|-------------|
| `calendar_type` | `CalendarType` (optional, alias `type`) | Calendar integration type |
| `email_address` | `str` (optional) | Not set when `type` is `none` |
| `resource_group_id` | `str` (optional) | Only for on-premise Microsoft calendar |

#### WorkspaceCalling

| Field | Type | Description |
|-------|------|-------------|
| `type` | `CallingType` (optional) | Calling configuration type |
| `hybrid_calling` | `WorkspaceCallingHybridCalling` (optional) | Only when `type` is `hybridCalling` |
| `webex_calling` | `WorkspaceWebexCalling` (optional) | Only when `type` is `webexCalling` |

**Important:** Due to a backend limitation, `webex_calling` details are never returned by the workspace GET API. They are only used when creating a workspace.

#### WorkspaceWebexCalling

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | `str` (optional) | Direct phone number |
| `extension` | `str` (optional) | Extension |
| `location_id` | `str` (optional) | Calling location ID |
| `licenses` | `list[str]` (optional) | Webex Calling license IDs |

#### Workspace

The main workspace object, with all fields:

| Field | Type | Description |
|-------|------|-------------|
| `workspace_id` | `str` (optional, alias `id`) | Workspace ID |
| `org_id` | `str` (optional) | Organization ID |
| `location_id` | `str` (optional) | Preferred location ID; use the `/locations` API |
| `workspace_location_id` | `str` (optional) | Legacy; prefer `location_id` |
| `floor_id` | `str` (optional) | Floor ID |
| `display_name` | `str` (optional) | Workspace display name |
| `capacity` | `int` (optional) | Workspace capacity |
| `workspace_type` | `WorkSpaceType` (optional, alias `type`) | Workspace type |
| `sip_address` | `str` (optional, read-only) | SIP address |
| `created` | `datetime` (optional, read-only) | Creation timestamp |
| `calling` | `WorkspaceCalling` (optional) | Calling configuration |
| `hybrid_calling` | `str` (optional) | Hybrid calling detail |
| `calendar` | `Calendar` (optional) | Calendar integration |
| `notes` | `str` (optional) | Free-text notes |
| `hotdesking_status` | `HotdeskingStatus` (optional) | Hot desking status |
| `supported_devices` | `WorkspaceSupportedDevices` (optional) | Supported device type |
| `device_hosted_meetings` | object (optional) | Device-hosted meetings config |
| `device_platform` | `DevicePlatform` (optional) | Device platform |
| `indoor_navigation` | object (optional) | Indoor navigation config |
| `health` | `WorkspaceHealth` (optional, read-only) | Workspace health status |
| `devices` | list (optional, read-only) | Devices in the workspace |
| `capabilities` | `CapabilityMap` (optional) | Sensor/feature capabilities |
| `planned_maintenance` | object (optional) | Planned maintenance window |

**Key constraints:**
- `location_id` and `supported_devices` **cannot be changed** once set on creation.
- `sip_address`, `created`, `health`, and `devices` are read-only.

#### CapabilityMap

Sensor/feature capabilities of workspace devices:

| Field | Type | Description |
|-------|------|-------------|
| `occupancy_detection` | `SupportAndConfiguredInfo` (optional) | Occupancy detection capability |
| `presence_detection` | `SupportAndConfiguredInfo` (optional) | Presence detection capability |
| `ambient_noise` | `SupportAndConfiguredInfo` (optional) | Ambient noise sensing capability |
| `sound_level` | `SupportAndConfiguredInfo` (optional) | Sound level sensing capability |
| `temperature` | `SupportAndConfiguredInfo` (optional) | Temperature sensing capability |
| `air_quality` | `SupportAndConfiguredInfo` (optional) | Air quality sensing capability |
| `relative_humidity` | `SupportAndConfiguredInfo` (optional) | Relative humidity sensing capability |
| `hot_desking` | `SupportAndConfiguredInfo` (optional) | Hot desking capability |
| `check_in` | `SupportAndConfiguredInfo` (optional) | Check-in capability |
| `adhoc_booking` | `SupportAndConfiguredInfo` (optional) | Ad-hoc booking capability |

Each `SupportAndConfiguredInfo` object has `supported` (bool) and `configured` (bool) fields.

#### WorkspaceHealth

| Field | Type | Description |
|-------|------|-------------|
| `level` | `WorkspaceHealthLevel` (optional) | Overall health: `error`, `warning`, `info`, or `ok` |
| `issues` | `list[WorkspaceHealthIssue]` (optional) | List of health issues |

Each `WorkspaceHealthIssue` has: `id`, `created_at`, `title`, `description`, `recommended_action`, `level`.

### Workspace API Behavior Notes

#### Listing workspaces

`GET /v1/workspaces` returns a paginated list of workspaces, filterable by location, floor, display name, capacity, workspace type, calling type, supported devices, calendar type, device-hosted-meetings flag, device platform, health level, and custom attribute. Pass `includeDevices=true` to embed device details, and `includeCapabilities=true` to embed the capability map, in the response.

#### Creating a workspace

`POST /v1/workspaces` creates a new workspace. Omitting `calling` defaults to free calling; omitting `calendar` defaults to no calendar.

**Webex Calling workspace requirements (non-hotdesk):**
- `locationId` is required
- Either `phoneNumber` or `extension` (or both) under `calling.webexCalling` is required
- `licenses` is optional; if omitted, the oldest suitable license is auto-applied

**Hot desk only workspace restrictions:**
- `phoneNumber` and `extension` are not applicable
- `deviceHostedMeetings` and `calendar` are not applicable

#### Workspace details

`GET /v1/workspaces/{workspaceId}` returns full details for a single workspace. Pass `includeDevices=true` to embed device details.

#### Updating a workspace

`PUT /v1/workspaces/{workspaceId}` updates a workspace. Include all fields from a GET response — omitting optional fields (`capacity`, `type`, `notes`) clears them. `locationId`, `supportedDevices`, `calendar`, and `calling` are preserved when omitted.

**Restrictions:**
- `calling` can only be updated if the current type is `freeCalling`, `none`, `thirdPartySipCalling`, or `webexCalling`.
- Cannot change `calling` to `none`, `thirdPartySipCalling`, or `webexCalling` if devices are present.
- `locationId` and `supportedDevices` cannot be changed after initial creation.

#### Deleting a workspace

`DELETE /v1/workspaces/{workspaceId}` deletes the workspace and all associated devices. Deleted devices must be reactivated.

#### Workspace capabilities

`GET /v1/workspaces/{workspaceId}/capabilities` returns the capability map (sensor/feature status) for a workspace.

---

## Workspace Settings API

Calling-related settings for workspaces. Most settings mirror the person call settings API (see the `person-call-settings-*.md` reference docs), addressed by workspace ID instead of person ID.

### Calling Settings Reference

The settings below are exposed under `/telephony/config/workspaces/{workspaceId}/{endpoint}` (Professional-licensed workspaces) or `/workspaces/{workspaceId}/features/{endpoint}` (Basic-compatible subset) — see the [license tier table](#key-patterns-and-gotchas) for which path applies to each.

| Setting | Endpoint Segment | Purpose |
|-----------|-----------|---------|
| Anonymous call reject | `anonymousCallReject` | Anonymous call rejection |
| Barge in | `bargeIn` | Barge-in settings |
| Call bridge | `callBridge` | Call bridge settings |
| Call intercept | `intercept` | Call intercept |
| Call policy | `callPolicies` | Call policy |
| Call waiting | `callWaiting` | Call waiting |
| Caller ID | `callerId` | Caller ID configuration |
| Do Not Disturb | `doNotDisturb` | Do Not Disturb |
| Emergency callback number | `ecbn` | Emergency callback number |
| Call forwarding | `callForwarding` | Call forwarding rules |
| Monitoring | `monitoring` | Monitoring (busy lamp field) |
| Music on hold | `musicOnHold` | Music on hold |
| Incoming permissions | `incomingPermission` | Incoming call permissions |
| Outgoing permissions | `outgoingPermission` | Outgoing call permissions |
| Priority alert | `priorityAlert` | Priority alert |
| Privacy | `privacy` | Privacy settings |
| Push to talk | `pushToTalk` | Push to talk |
| Selective accept | `selectiveAccept` | Selective call acceptance |
| Selective forward | `selectiveForward` | Selective call forwarding |
| Selective reject | `selectiveReject` | Selective call rejection |
| Sequential ring | `sequentialRing` | Sequential ring |
| Simultaneous ring | `simultaneousRing` | Simultaneous ring |
| Voicemail | `voicemail` | Voicemail settings |
| Available numbers | `availableNumbers` | Available number lookup |

### Workspace Devices API

Manages telephony devices assigned to a workspace.

**Base endpoint:** `/v1/telephony/config/workspaces/{workspaceId}/devices`

#### Listing workspace telephony devices

`GET /v1/telephony/config/workspaces/{workspaceId}/devices` returns a paginated list of telephony devices for the workspace. The same response also includes device count metadata by type, in a single non-paginated payload.

#### Modifying hoteling

`PUT /v1/telephony/config/workspaces/{workspaceId}/devices/hoteling` modifies hoteling settings for workspace devices (`enabled`, `limitGuestUse`, `guestHotelingLimit`).

### Workspace Numbers API

**Base endpoint:** `/v1/telephony/config/workspaces/{workspaceId}/numbers` — manages PSTN phone numbers associated with a workspace.

#### Data Models

| Field | Type | Description |
|-------|------|-------------|
| `distinctive_ring_enabled` | `bool` (optional) | Distinctive ring enabled |
| `phone_numbers` | `list[UserNumber]` | Primary and alternate numbers |
| `workspace` | `IdOnly` | Workspace identifier |
| `location` | `IdAndName` | Location identifier + name |
| `organization` | `IdAndName` | Organization identifier + name |

| Field | Type | Description |
|-------|------|-------------|
| `primary` | `bool` (optional) | Marks as primary number |
| `action` | `PatternAction` (optional) | `ADD` or `DELETE` |
| `direct_number` | `str` (optional) | E.164 phone number |
| `extension` | `str` (optional) | Extension |
| `ring_pattern` | `RingPattern` (optional) | Ring pattern for this number |

#### Reading workspace numbers

`GET /v1/telephony/config/workspaces/{workspaceId}/numbers` lists PSTN phone numbers associated with the workspace, including location and organization info.

#### Updating workspace numbers

`PUT /v1/telephony/config/workspaces/{workspaceId}/numbers` assigns or unassigns alternate phone numbers. Phone numbers must follow E.164 format (national format also accepted for US).

**Note:** This API is only available for **professional licensed** workspaces.

---

## Workspace Locations API (Legacy)

> **Deprecation warning:** This is a legacy API. Prefer the `/locations` API for new integrations.

**Base endpoint:** `/v1/workspaceLocations` — manages legacy workspace location records (physical location metadata with coordinates).

### Workspace Location Data Models

#### WorkspaceLocation

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Workspace location ID |
| `location_id` | `str` (optional) | Associated `/locations` location ID |
| `display_name` | `str` | Display name |
| `address` | `str` | Street address |
| `country_code` | `str` | ISO 3166-1 country code |
| `city_name` | `str` | City name |
| `longitude` | `float` (optional) | Longitude |
| `latitude` | `float` (optional) | Latitude |
| `notes` | `str` (optional) | Free-text notes |

Webex IDs (`id` and the org portion) are base64-encoded; decode to extract the raw UUID if needed.

#### WorkspaceLocationFloor

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Floor ID |
| `location_id` | `str` | Workspace location ID |
| `floor_number` | `int` | Floor number |
| `display_name` | `str` | Floor display name |

### Workspace Location API Behavior Notes

#### Listing workspace locations

`GET /v1/workspaceLocations` returns a paginated list, filterable by `displayName`, `address`, `countryCode`, and `cityName`.

#### Creating a workspace location

`POST /v1/workspaceLocations` creates a workspace location. Requires `displayName`, `address`, `countryCode`, `latitude`, and `longitude`; `cityName` and `notes` are optional.

#### Workspace location details

`GET /v1/workspaceLocations/{locationId}` returns details for a single workspace location.

#### Updating a workspace location

`PUT /v1/workspaceLocations/{locationId}` updates a workspace location. Include all fields from a GET response — omitting `cityName` or `notes` clears them.

#### Deleting a workspace location

`DELETE /v1/workspaceLocations/{locationId}` deletes a workspace location. Workspaces associated with the deleted location lose their location but can be reassigned.

### Floor Management

**Base endpoint:** `/v1/workspaceLocations/{locationId}/floors` — CRUD for floors within a workspace location.

#### Listing floors

`GET /v1/workspaceLocations/{locationId}/floors` returns a paginated list of floors for the location.

#### Creating a floor

`POST /v1/workspaceLocations/{locationId}/floors` creates a floor. Requires `floorNumber`; `displayName` is optional.

#### Floor details

`GET /v1/workspaceLocations/{locationId}/floors/{floorId}` returns details for a single floor.

#### Updating a floor

`PUT /v1/workspaceLocations/{locationId}/floors/{floorId}` updates a floor.

#### Deleting a floor

`DELETE /v1/workspaceLocations/{locationId}/floors/{floorId}` deletes a floor.

---

## Workspace Personalization API

**Base endpoint:** `/v1/workspaces/{workspaceId}/personalize` (initiate) and `/v1/workspaces/{workspaceId}/personalizationTask` (status) — enables Personal Mode on Webex Edge registered devices. This is a one-time migration operation from on-premise to cloud-registered personal mode.

**Applies only to Webex Edge registered devices.**

### Prerequisites

- Workspace must contain a **single** Webex Edge registered, shared mode device
- Workspace must have **no calendars** configured
- The device must be **online**

### Personalizing a workspace

`POST /v1/workspaces/{workspaceId}/personalize` initiates asynchronous personalization for the given user email (in the request body). Returns a `Location` header with a URL pointing to the task status endpoint. The task typically completes in ~30 seconds.

### Personalization task status

`GET /v1/workspaces/{workspaceId}/personalizationTask` returns task status:
- While in progress: returns `202 Accepted` with a `Retry-After` header
- On completion: returns `200 OK` with a result body

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` (optional) | Whether personalization succeeded |
| `error_description` | `str` (optional) | Populated on failure |

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

## Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All workspace operations can be performed via raw HTTP using `api.session.rest_*()`. This is the preferred execution pattern — the authenticated client handles auth and session management, while you control the exact request.

```python
from wxcli.auth import get_api

api = get_api()
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
7. **Migration tool populates workspace `call_settings` from CUCM common-area phones.** `WorkspaceMapper._extract_workspace_call_settings` translates CUCM `dndStatus`, `voiceMailProfile`, per-line `callForward*`, and `privacy` into Webex `/telephony/config/workspaces/{id}/{feature}` PUT bodies. Output is license-gated: Workspace-tier workspaces only keep `doNotDisturb` and `musicOnHold`; everything else requires Professional Workspace. See the spec at `docs/superpowers/specs/2026-04-10-workspace-call-settings.md`. Under the default license-tier inference, most workspaces land at Workspace tier, so only `doNotDisturb` actually migrates — `voicemail`, `callForwarding`, and `privacy` only activate when an operator overrides the tier to Professional Workspace during decision review.

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

# Record external calls only, both directions. selectiveCallRecordingSettings
# (added upstream 2026-08-03) has no flag — nested objects reach the body only
# through --json-body. All four toggles are required when the object is sent,
# and it applies only on --record "Always" or "Always with Pause/Resume".
wxcli workspace-settings update-call-recordings <workspace_id> --verify --json-body '{
  "enabled": true,
  "record": "Always",
  "selectiveCallRecordingSettings": {
    "recordInboundInternalCallsEnabled": false,
    "recordInboundExternalCallsEnabled": true,
    "recordOutboundInternalCallsEnabled": false,
    "recordOutboundExternalCallsEnabled": true
  }
}'

# Disable call recording
wxcli workspace-settings update-call-recordings <workspace_id> --no-enabled
```

The four toggles are the same object people and virtual lines carry — field-by-field
detail in [Person Call Settings: Media](person-call-settings-media.md#7-call-recording).

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
wxcli workspace-settings list-monitoring <workspace_id>

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
| **Access Codes** | `list-access-codes`, `create`, `update-access-codes`, `delete-access-codes-all`, `delete-access-codes` |
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

4. **Workspace settings mirror person settings** — Most workspace calling-settings endpoints are the same underlying settings used for person call settings, addressed by workspace ID instead of person ID (see the [Calling Settings Reference](#calling-settings-reference) table).

5. **Workspace Locations API is deprecated** — Use the `/locations` API instead for new integrations (`wxcli locations`).

6. **Hot desk workspaces** — When creating with `hotdesking_status=on`, `phone_number`, `extension`, `device_hosted_meetings`, and `calendar` are not applicable and will cause errors if provided.

7. **License handling** — When creating a Webex Calling workspace, you can provide multiple license IDs; the oldest suitable one is applied. If omitted, auto-assigned from active subscriptions.

8. **Device cleanup on workspace delete** — Deleting a workspace deletes all associated devices. Those devices must be reactivated to be reused.

9. **Personalization is one-time** — The Workspace Personalization API is for migrating Edge devices from shared to personal mode. It requires the device to be online and the workspace to have no calendar configured.

10. **Workspace call settings endpoint access by license tier.**

    **Rule of thumb:** Under `/telephony/config/workspaces/{id}/`, only `musicOnHold` and `doNotDisturb` work on Basic. Everything else returns 405 "Invalid Professional Place". For Basic workspaces, use the `/workspaces/{id}/features/` path family instead (5 endpoints listed below).

    | Endpoint Path | Basic | Professional | Notes |
    |---------------|:-----:|:------------:|-------|
    | **`/workspaces/{id}/features/` path (works on Basic)** | | | |
    | `/workspaces/{id}/features/callForwarding` | 200 | 200 | |
    | `/workspaces/{id}/features/callWaiting` | 200 | 200 | |
    | `/workspaces/{id}/features/callerId` | 200 | 200 | |
    | `/workspaces/{id}/features/intercept` | 200 | 200 | |
    | `/workspaces/{id}/features/monitoring` | 200 | 200 | |
    | `/workspaces/{id}/features/incomingPermission` | 200 | 200 | |
    | `/workspaces/{id}/features/outgoingPermission` | 200 | 200 | |
    | `/workspaces/{id}/features/voicemail` | 404 | N/A | Wrong path for voicemail; use `/telephony/config/` |
    | **`/telephony/config/workspaces/{id}/` path (Basic exceptions)** | | | |
    | `/telephony/config/workspaces/{id}/musicOnHold` | 200 | 200 | Basic exception |
    | `/telephony/config/workspaces/{id}/doNotDisturb` | 200 | 200 | Basic exception |
    | **`/telephony/config/workspaces/{id}/` path (Professional only)** | | | |
    | `/telephony/config/workspaces/{id}/anonymousCallReject` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/bargeIn` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/callBridge` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/callForwarding` | 405 | 200 | Duplicate of `/features/` path |
    | `/telephony/config/workspaces/{id}/callPolicies` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/callRecording` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/callWaiting` | 405 | 200 | Duplicate of `/features/` path |
    | `/telephony/config/workspaces/{id}/callerId` | 405 | 200 | Duplicate of `/features/` path |
    | `/telephony/config/workspaces/{id}/ecbn` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/intercept` | 405 | 200 | Duplicate of `/features/` path |
    | `/telephony/config/workspaces/{id}/monitoring` | 405 | 200 | Duplicate of `/features/` path |
    | `/telephony/config/workspaces/{id}/numbers` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/priorityAlert` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/privacy` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/pushToTalk` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/selectiveAccept` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/selectiveForward` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/selectiveReject` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/sequentialRing` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/simultaneousRing` | 405 | 200 | |
    | `/telephony/config/workspaces/{id}/voicemail` | 405 | 200 | |

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
