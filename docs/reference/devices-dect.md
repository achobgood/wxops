<!-- Updated by playbook session 2026-03-18 -->

# DECT Devices & Hot Desking Reference

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: webex-device.json
- developer.webex.com DECT Device APIs

DECT network management (networks, base stations, handsets, line assignment) and hot desk session management via the `wxc_sdk` Python SDK.

**Not supported for Webex for Government (FedRAMP).** See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

---

## Table of Contents

1. [Required Scopes](#required-scopes)
2. [API Access Path](#api-access-path)
3. [DECT Network Management](#dect-network-management)
4. [Base Station Management](#base-station-management)
5. [Handset Management](#handset-management)
6. [Association Queries](#association-queries)
7. [Available Members Search](#available-members-search)
8. [Serviceability Password](#serviceability-password)
9. [Hot Desking](#hot-desking)
10. [Data Models](#data-models)
11. [Raw HTTP](#raw-http)
12. [Common Gotchas](#common-gotchas)

---

## Required Scopes

| Operation | Scope(s) Required |
|-----------|-------------------|
| List/view DECT networks, base stations, handsets | `spark-admin:telephony_config_read` |
| Create/update/delete DECT networks, base stations, handsets | `spark-admin:telephony_config_write` |
| Generate serviceability password | `spark-admin:telephony_config_write` **or** `spark-admin:devices_write` |
| Get serviceability password status | `spark-admin:telephony_config_read` **or** `spark-admin:devices_read` |
| Update serviceability password status | `spark-admin:telephony_config_write` **or** `spark-admin:devices_write` |
| List/delete hot desk sessions | Admin token required (scopes not explicitly documented in OpenAPI spec, but the endpoints work with a full admin token). The hot desk session endpoints are at `/v1/hotdesk/sessions`, separate from the DECT/telephony config scope. | <!-- Verified via live API 2026-03-19: GET /v1/hotdesk/sessions succeeds with admin token -->

All DECT operations require a **full or read-only administrator auth token**.

---

## API Access Path

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens='<token>')

# DECT devices API
dect = api.telephony.dect_devices

# Hot desk API
hotdesk = api.telephony.hotdesk  # <!-- Corrected via wxc_sdk source (telephony/__init__.py line 651) 2026-03-19 -->
```

---

## DECT Network Management

DECT networks provide roaming voice services via base stations and wireless handsets. A network can be provisioned with up to 1000 lines across up to 254 base stations.

### Supported Device Models

| Enum Value | Display Name | Base Stations | Line Ports |
|------------|-------------|---------------|------------|
| `DECTNetworkModel.dms_cisco_dbs110` | DMS Cisco DBS110 | 1 | 30 |
| `DECTNetworkModel.cisco_dect_110_base` | Cisco DECT 110 Base | 1 | 30 |
| `DECTNetworkModel.dms_cisco_dbs210` | DMS Cisco DBS210 | 250 | 1000 |
| `DECTNetworkModel.cisco_dect_210_base` | Cisco DECT 210 Base | 250 | 1000 |

Only Cisco DECT device models are currently supported.

### List Supported Device Types

```python
def device_type_list(
    self,
    org_id: str = None
) -> list[DectDevice]
```

Returns a static list of DECT device types with base station and line port counts.

### Create a DECT Network

```python
def create_dect_network(
    self,
    location_id: str,
    name: str,
    model: DECTNetworkModel,
    default_access_code_enabled: bool,
    default_access_code: str,
    display_name: str = None,
    org_id: str = None
) -> str  # returns dect_network_id
```

| Parameter | Notes |
|-----------|-------|
| `name` | Must be unique across the location. 1-40 characters. |
| `display_name` | Shown on handsets. 11 characters max. If omitted, defaults to indexed number + network name. |
| `default_access_code_enabled` | `True` = shared 4-digit access code for all users. `False` = auto-generated per-handset codes. |
| `default_access_code` | Required when `default_access_code_enabled` is `True`. Must be 4 numeric digits, unique within the location. |

**Note:** There is currently no public API to retrieve auto-generated access codes for handsets when `default_access_code_enabled` is `False`. Use Control Hub instead.

### List DECT Networks

```python
def list_dect_networks(
    self,
    name: str = None,
    location_id: str = None,
    org_id: str = None
) -> list[DECTNetworkDetail]
```

Lists all DECT networks in an organization. Both `name` and `location_id` are optional filters.

### Get DECT Network Details

```python
def dect_network_details(
    self,
    location_id: str,
    dect_network_id: str,
    org_id: str = None
) -> DECTNetworkDetail
```

### Update a DECT Network

```python
def update_dect_network(
    self,
    location_id: str,
    dect_network_id: str,
    name: str,
    default_access_code_enabled: bool,
    default_access_code: str = None,
    display_name: str = None,
    org_id: str = None
) -> None
```

`name` and `default_access_code_enabled` are required. `default_access_code` is mandatory when `default_access_code_enabled` is `True`.

### Update DECT Network from Settings Object

```python
def update_dect_network_settings(
    self,
    settings: DECTNetworkDetail,
    org_id: str = None
) -> None
```

Convenience method. Uses `settings.location.id` and `settings.id` to address the network. Only `name`, `display_name`, `default_access_code_enabled`, and `default_access_code` fields are sent in the update.

### Delete a DECT Network

```python
def delete_dect_network(
    self,
    location_id: str,
    dect_network_id: str,
    org_id: str = None
) -> None
```

### CLI Examples

```bash
# List all DECT networks in the org
wxcli dect-devices list

# List DECT networks filtered by location
wxcli dect-devices list --location-id <location_id>

# List DECT networks filtered by name
wxcli dect-devices list --name "Building A"

# Show details of a specific DECT network
wxcli dect-devices show <location_id> <dect_network_id>

# Show details as JSON
wxcli dect-devices show <location_id> <dect_network_id> -o json

# Create a DECT network (DBS-210 multi-cell with shared access code)
wxcli dect-devices create <location_id> \
  --name "Building A DECT" \
  --model "DMS Cisco DBS210" \
  --default-access-code-enabled \
  --default-access-code "1234"

# Create a DECT network (DBS-110 single-cell with display name)
wxcli dect-devices create <location_id> \
  --name "Lobby DECT" \
  --model "DMS Cisco DBS110" \
  --default-access-code-enabled \
  --default-access-code "5678" \
  --display-name "Lobby"

# Update a DECT network name and access code
wxcli dect-devices update <location_id> <dect_network_id> \
  --name "Building A DECT v2" \
  --default-access-code-enabled \
  --default-access-code "9999"

# Disable shared access code (switches to per-handset auto-generated codes)
wxcli dect-devices update <location_id> <dect_network_id> \
  --no-default-access-code-enabled

# Delete a DECT network (with confirmation prompt)
wxcli dect-devices delete <location_id> <dect_network_id>

# Delete a DECT network (skip confirmation)
wxcli dect-devices delete <location_id> <dect_network_id> --force
```

---

## Base Station Management

Two types of base stations:
- **DBS-110 (Single-Cell):** 1 base station, up to 30 line registrations
- **DBS-210 (Multi-Cell):** Up to 254 base stations, up to 1000 line registrations

### Create Multiple Base Stations

```python
def create_base_stations(
    self,
    location_id: str,
    dect_id: str,
    base_station_macs: list[str],
    org_id: str = None
) -> list[BaseStationResponse]
```

Pass a list of MAC addresses. Returns a list of `BaseStationResponse` objects, each containing the MAC and a result with HTTP status code and base station ID.

### List Base Stations

```python
def list_base_stations(
    self,
    location_id: str,
    dect_network_id: str,
    org_id: str = None
) -> list[BaseStationsResponse]
```

Returns base station IDs, MACs, and registered line counts.

### Get Base Station Details

```python
def base_station_details(
    self,
    location_id: str,
    dect_network_id: str,
    base_station_id: str,
    org_id: str = None
) -> BaseStationDetail
```

Returns the base station with its registered handsets and their line member details.

### Delete All Base Stations

```python
def delete_bulk_base_stations(
    self,
    location_id: str,
    dect_network_id: str,
    org_id: str = None
) -> None
```

Deletes **all** base stations in the specified DECT network.

### Delete a Specific Base Station

```python
def delete_base_station(
    self,
    location_id: str,
    dect_network_id: str,
    base_station_id: str,
    org_id: str = None
) -> None
```

### CLI Examples

```bash
# List base stations in a DECT network
wxcli dect-devices list-base-stations <location_id> <dect_network_id>

# List base stations as JSON
wxcli dect-devices list-base-stations <location_id> <dect_network_id> -o json

# Show details of a specific base station
wxcli dect-devices show-base-stations <location_id> <dect_network_id> <base_station_id>

# Create base stations (bulk by MAC, requires --json-body)
wxcli dect-devices create-base-stations <location_id> <dect_network_id> \
  --json-body '{"baseStationMacs":["AABBCCDDEEFF","112233445566"]}'

# Delete a specific base station
wxcli dect-devices delete-base-stations-dect-networks-1 <location_id> <dect_network_id> <base_station_id>

# Delete a specific base station (skip confirmation)
wxcli dect-devices delete-base-stations-dect-networks-1 <location_id> <dect_network_id> <base_station_id> --force

# Delete ALL base stations in a DECT network
wxcli dect-devices delete-base-stations-dect-networks <location_id> <dect_network_id>

# Delete ALL base stations (skip confirmation)
wxcli dect-devices delete-base-stations-dect-networks <location_id> <dect_network_id> --force
```

---

## Handset Management

Each handset supports up to **2 lines**. A DECT network supports a total of 120 lines across all handsets.

- **Line 1:** Member type can be PEOPLE or PLACE
- **Line 2:** Member type can be PEOPLE, PLACE, or VIRTUAL_LINE

### Add a Single Handset

```python
def add_a_handset(
    self,
    location_id: str,
    dect_network_id: str,
    line1_member_id: str,
    line2_member_id: str = None,
    custom_display_name: str = None,
    org_id: str = None
) -> None
```

`custom_display_name` is mandatory (1-16 characters). Raises `ValueError` if `None`.

### Add a List of Handsets (Bulk)

```python
def add_list_of_handsets(
    self,
    location_id: str,
    dect_network_id: str,
    items: list[AddDECTHandset],
    org_id: str = None
) -> list[AddDECTHandsetBulkResponse]
```

Add up to **50 handsets** in a single call. Each `AddDECTHandset` contains `line1_member_id`, `line2_member_id` (optional), and `custom_display_name` (optional).

Returns per-item results with status codes and error details if any failed.

### List Handsets

```python
def list_handsets(
    self,
    location_id: str,
    dect_network_id: str,
    basestation_id: str = None,
    member_id: str = None,
    org_id: str = None
) -> DECTHandsetList
```

Returns a `DECTHandsetList` containing `number_of_handsets_assigned`, `number_of_lines_assigned`, and the list of `DECTHandsetItem` objects. Filter by `basestation_id` or `member_id`.

### Get Handset Details

```python
def handset_details(
    self,
    location_id: str,
    dect_network_id: str,
    handset_id: str,
    org_id: str = None
) -> DECTHandsetItem
```

### Update Handset (Line Assignment)

```python
def update_handset(
    self,
    location_id: str,
    dect_network_id: str,
    handset_id: str,
    line1_member_id: str,
    custom_display_name: str,
    line2_member_id: str = None,
    org_id: str = None
) -> None
```

Updates the line assignment on a handset. `line1_member_id` and `custom_display_name` are required.

### Delete a Single Handset

```python
def delete_handset(
    self,
    location_id: str,
    dect_network_id: str,
    handset_id: str,
    org_id: str = None
) -> None
```

### Delete Multiple Handsets

```python
def delete_handsets(
    self,
    location_id: str,
    dect_network_id: str,
    handset_ids: list[str],
    delete_all: bool = None,
    org_id: str = None
) -> None
```

If `delete_all` is `True`, the `handset_ids` array is ignored and all handsets in the network are deleted.

### CLI Examples

```bash
# List all handsets in a DECT network
wxcli dect-devices list-handsets <location_id> <dect_network_id>

# List handsets as JSON
wxcli dect-devices list-handsets <location_id> <dect_network_id> -o json

# List handsets filtered by base station
wxcli dect-devices list-handsets <location_id> <dect_network_id> \
  --basestation-id <base_station_id>

# List handsets filtered by member (person, workspace, or virtual line)
wxcli dect-devices list-handsets <location_id> <dect_network_id> \
  --member-id <person_id>

# Show details of a specific handset
wxcli dect-devices show-handsets <location_id> <dect_network_id> <handset_id>

# Add a single handset with one line
wxcli dect-devices create-handsets <location_id> <dect_network_id> \
  --line1-member-id <person_id> \
  --custom-display-name "Reception"

# Add a single handset with two lines (line 2 can be a virtual line)
wxcli dect-devices create-handsets <location_id> <dect_network_id> \
  --line1-member-id <person_id> \
  --line2-member-id <virtual_line_id> \
  --custom-display-name "Front Desk"

# Update handset line assignment and display name
wxcli dect-devices update-handsets <location_id> <dect_network_id> <handset_id> \
  --line1-member-id <new_person_id> \
  --custom-display-name "Updated Name"

# Update handset to add a second line
wxcli dect-devices update-handsets <location_id> <dect_network_id> <handset_id> \
  --line2-member-id <virtual_line_id>

# Delete a single handset
wxcli dect-devices delete-handsets-dect-networks <location_id> <dect_network_id> <handset_id>

# Delete a single handset (skip confirmation)
wxcli dect-devices delete-handsets-dect-networks <location_id> <dect_network_id> <handset_id> --force

# Delete multiple handsets (bulk)
wxcli dect-devices delete-handsets-dect-networks-1 <location_id> <dect_network_id>

# Delete multiple handsets (skip confirmation)
wxcli dect-devices delete-handsets-dect-networks-1 <location_id> <dect_network_id> --force

# Bulk add handsets (up to 50, requires --json-body)
wxcli dect-devices create-bulk <location_id> <dect_network_id> \
  --json-body '{"items":[{"line1MemberId":"<person_id_1>","customDisplayName":"User 1"},{"line1MemberId":"<person_id_2>","line2MemberId":"<vl_id>","customDisplayName":"User 2"}]}'
```

---

## Association Queries

Query which DECT networks are associated with a specific person, workspace, or virtual line.

### DECT Networks for a Person

```python
def dect_networks_associated_with_person(
    self,
    person_id: str,
    org_id: str = None
) -> list[AssignedDectNetwork]
```

### DECT Networks for a Workspace

```python
def dect_networks_associated_with_workspace(
    self,
    workspace_id: str,
    org_id: str = None
) -> list[AssignedDectNetwork]
```

### DECT Networks for a Virtual Line

```python
def dect_networks_associated_with_virtual_line(
    self,
    virtual_line_id: str,
    org_id: str = None
) -> list[AssignedDectNetwork]
```

### CLI Examples

```bash
# List DECT networks associated with a person
wxcli dect-devices list-dect-networks-people <person_id>

# List DECT networks associated with a workspace
wxcli dect-devices list-dect-networks-workspaces <workspace_id>

# Output as JSON
wxcli dect-devices list-dect-networks-people <person_id> -o json
```

---

## Available Members Search

Search for members that can be assigned to DECT handset lines.

```python
def available_members(
    self,
    member_name: str = None,
    phone_number: str = None,
    extension: str = None,
    location_id: str = None,
    order: str = None,
    exclude_virtual_line: bool = None,
    usage_type: UsageType = None,
    org_id: str = None,
    **params
) -> Generator[AvailableMember, None, None]
```

| Parameter | Notes |
|-----------|-------|
| `member_name` | Contains-match on member name |
| `phone_number` | Contains-match on number |
| `extension` | Contains-match on extension |
| `order` | Sort by `lname` (last name, default) or `fname` (first name), ascending |
| `exclude_virtual_line` | If `True`, virtual lines are excluded. Virtual lines cannot be the primary line. |
| `usage_type` | Filter by `UsageType` -- eligible as device owner or shared line |

Returns a **Generator** (paginated). Yields `AvailableMember` instances.

### CLI Examples

```bash
# Search all available members for DECT line assignment
wxcli dect-devices list-available-members

# Search by member name
wxcli dect-devices list-available-members --member-name "Jane"

# Search by phone number
wxcli dect-devices list-available-members --phone-number "+1555"

# Search by extension
wxcli dect-devices list-available-members --extension "1001"

# Filter by location
wxcli dect-devices list-available-members --location-id <location_id>

# Exclude virtual lines (for line 1 assignment — virtual lines can only be line 2)
wxcli dect-devices list-available-members --exclude-virtual-line true

# Filter by usage type (device owner vs shared line)
wxcli dect-devices list-available-members --usage-type DEVICE_OWNER

# Sort by first name instead of last name (default)
wxcli dect-devices list-available-members --order fname

# Output as JSON
wxcli dect-devices list-available-members --member-name "Jane" -o json
```

---

## Serviceability Password

The DECT serviceability password (also called the admin override password) provides read/write access to DECT base stations for system serviceability and troubleshooting.

### Generate and Enable Password

```python
def generate_and_enable_dect_serviceability_password(
    self,
    location_id: str,
    dect_network_id: str,
    org_id: str = None
) -> str  # returns the 16-character password
```

**Warning:** Generating a new password and transmitting it to the DECT network can **reboot the entire network**. Choose an appropriate maintenance window.

### Get Password Status

```python
def get_dect_serviceability_password_status(
    self,
    location_id: str,
    dect_network_id: str,
    org_id: str = None
) -> bool  # True if enabled
```

Note: If the password is enabled but has not been generated, status still returns `True` even though there is no active password.

### Update Password Status (Enable/Disable)

```python
def update_dect_serviceability_password_status(
    self,
    location_id: str,
    dect_network_id: str,
    enabled: bool,
    org_id: str = None
) -> None
```

When `enabled` is `False`, the Cisco-owned password is required for serviceability access instead.

**Warning:** Enabling or disabling the password can **reboot the entire network**.

### CLI Examples

```bash
# Generate and enable a serviceability password (WARNING: may reboot DECT network)
wxcli dect-devices generate-and-enable <location_id> <dect_network_id>

# Check serviceability password status (enabled/disabled)
wxcli dect-devices show-serviceability-password <location_id> <dect_network_id>

# Enable serviceability password (WARNING: may reboot DECT network)
wxcli dect-devices update-serviceability-password <location_id> <dect_network_id> --enabled

# Disable serviceability password (WARNING: may reboot DECT network)
wxcli dect-devices update-serviceability-password <location_id> <dect_network_id> --no-enabled
```

---

## Hot Desking

Hot desking allows users to temporarily sign into a shared workspace device and use it as their own phone. The `HotDeskApi` manages active hot desk sessions.

### API Access

```python
hotdesk = api.telephony.hotdesk  # <!-- Corrected via wxc_sdk source (telephony/__init__.py line 651) 2026-03-19 -->
```

### Data Model

```python
class HotDesk(ApiModel):
    session_id: Optional[str] = None       # Unique session identifier
    workspace_id: Optional[str] = None     # Workspace where session is active
    person_id: Optional[str] = None        # Person who initiated the session
    booking_start_time: Optional[datetime] = None
    booking_end_time: Optional[datetime] = None
```

### List Sessions

```python
def list_sessions(
    self,
    person_id: str = None,
    workspace_id: str = None,
    org_id: str = None
) -> list[HotDesk]
```

Both `person_id` and `workspace_id` are optional filters. When used together, they act as an AND filter. The `org_id` parameter is for partner administrators acting on a managed organization.

### Delete Session

```python
def delete_session(
    self,
    session_id: str
) -> None
```

Ends a hot desk session by its unique session ID.

---

## Data Models

### DECT Network Models

#### `DECTNetworkModel` (Enum)

| Value | String |
|-------|--------|
| `dms_cisco_dbs110` | `'DMS Cisco DBS110'` |
| `cisco_dect_110_base` | `'Cisco DECT 110 Base'` |
| `dms_cisco_dbs210` | `'DMS Cisco DBS210'` |
| `cisco_dect_210_base` | `'Cisco DECT 210 Base'` |

#### `DECTNetworkDetail`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Network name (unique per location) |
| `display_name` | `str` | Name shown on handsets |
| `chain_id` | `int` | Chain ID of the network |
| `model` | `DECTNetworkModel` | Base station model deployed |
| `default_access_code_enabled` | `bool` | Whether a shared access code is used |
| `default_access_code` | `str` | 4-digit shared access code (if enabled) |
| `number_of_base_stations` | `int` | Count of base stations |
| `number_of_handsets_assigned` | `int` | Count of assigned handsets |
| `number_of_lines` | `int` | Count of lines |
| `location` | `IdAndName` | Location id and name |

#### `DectDevice`

| Field | Type | Description |
|-------|------|-------------|
| `model` | `str` | Model name |
| `display_name` | `str` | Display name |
| `number_of_base_stations` | `int` | Supported base station count |
| `number_of_line_ports` | `int` | Supported line port count |
| `number_of_registrations_supported` | `int` | Supported registration count |

### Base Station Models

#### `BaseStationResponse` (creation result)

| Field | Type | Description |
|-------|------|-------------|
| `mac` | `str` | MAC address added |
| `result` | `BaseStationResult` | Contains `status` (int) and `id` (str) |

#### `BaseStationsResponse` (list item)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Base station ID |
| `mac` | `str` | MAC address |
| `number_of_lines_registered` | `int` | Registered handset line count |

#### `BaseStationDetail`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Base station ID |
| `mac` | `str` | MAC address |
| `handsets` | `list[Handset]` | Registered handsets with line details |

### Handset Models

#### `DECTHandsetLine`

| Field | Type | Description |
|-------|------|-------------|
| `member_id` | `str` | Member ID (PEOPLE or PLACE) |
| `first_name` | `str` | Member's first name |
| `last_name` | `str` | Member's last name |
| `external` | `str` | Primary phone number |
| `extension` | `str` | Extension |
| `routing_prefix` | `str` | Location routing prefix |
| `esn` | `str` | Routing prefix + extension |
| `last_registration_time` | `str` | Last registration timestamp |
| `host_ip` | `str` | Registration host IP (JSON alias: `hostIP`) |
| `remote_ip` | `str` | Registration remote IP (JSON alias: `remoteIP`) |
| `location` | `IdAndName` | Location id and name |
| `member_type` | `UserType` | Member type indicator |

#### `Handset`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Handset unique identifier |
| `display_name` | `str` | Display name |
| `access_code` | `str` | Access code for pairing |
| `lines` | `list[DECTHandsetLine]` | Up to 2 line members |

#### `DECTHandsetItem`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Handset unique identifier |
| `index` | `int` | Handset index |
| `default_display_name` | `str` | Default display name |
| `custom_display_name` | `str` | Custom display name set by admin |
| `base_station_id` | `str` | Associated base station ID |
| `mac` | `str` | MAC address |
| `access_code` | `str` | Access code for pairing |
| `primary_enabled` | `bool` | Whether this is a primary line |
| `lines` | `list[DECTHandsetLine]` | Up to 2 line members |

#### `DECTHandsetList`

| Field | Type | Description |
|-------|------|-------------|
| `number_of_handsets_assigned` | `int` | Total handsets |
| `number_of_lines_assigned` | `int` | Total lines |
| `handsets` | `list[DECTHandsetItem]` | Handset details |

#### `AddDECTHandset` (for bulk add)

| Field | Type | Description |
|-------|------|-------------|
| `line1_member_id` | `str` | Line 1 member (PEOPLE or PLACE) |
| `line2_member_id` | `str` | Line 2 member (PEOPLE, PLACE, or VIRTUAL_LINE) |
| `custom_display_name` | `str` | Custom name (1-16 characters) |

#### `AddDECTHandsetBulkResponse`

| Field | Type | Description |
|-------|------|-------------|
| `custom_display_name` | `str` | The custom display name submitted |
| `result` | `AddDECTHandsetBulkResult` | Contains `status` (int) and `error` (`AddDECTHandsetBulkError` with `message` and `error_code`) |

---

## Raw HTTP

All examples use:

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"
```

No auto-pagination -- pass `max=1000` explicitly. All responses are JSON dicts. Errors raise `RestError`.

### DECT Networks

#### Create a DECT network

```python
body = {
    "name": "Building A DECT",
    "model": "DMS Cisco DBS210",
    "defaultAccessCodeEnabled": True,
    "defaultAccessCode": "1234",
    "displayName": "Bldg A"  # max 11 chars
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{location_id}/dectNetworks", json=body)
network_id = result.get("dectNetworkId")  # NOTE: key is "dectNetworkId", not "id"
```

#### List DECT networks (org-wide)

```python
result = api.session.rest_get(f"{BASE}/telephony/config/dectNetworks", params={
    "max": 1000,
    "name": "Building A",      # optional filter
    "locationId": location_id,  # optional filter
})
networks = result.get("dectNetworks", [])
# Each: {id, name, displayName, model, defaultAccessCodeEnabled, numberOfBaseStations, numberOfHandsetsAssigned, numberOfLines, location: {id, name}}
```

#### Get DECT network details

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}")
# Returns full DECTNetworkDetail object
```

#### Update a DECT network

```python
body = {
    "name": "Building A DECT Updated",
    "defaultAccessCodeEnabled": True,
    "defaultAccessCode": "5678",
    "displayName": "Bldg A v2"
}
api.session.rest_put(f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}", json=body)
```

#### Delete a DECT network

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}")
```

### Base Stations

#### Create base stations (bulk by MAC)

```python
body = {"baseStationMacs": ["AABBCCDDEEFF", "112233445566"]}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/baseStations",
    json=body
)
# Returns list of results: [{mac, result: {status, id}}, ...]
```

#### List base stations

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/baseStations"
)
stations = result.get("baseStations", [])
# Each: {id, mac, numberOfLinesRegistered}
```

#### Get base station details

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/baseStations/{base_station_id}"
)
# Returns: {id, mac, handsets: [{id, displayName, accessCode, lines: [...]}]}
```

#### Delete a specific base station

```python
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/baseStations/{base_station_id}"
)
```

#### Delete all base stations in a network

```python
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/baseStations"
)
```

### Handsets

#### Add a single handset

```python
body = {
    "line1MemberId": person_id,
    "line2MemberId": virtual_line_id,  # optional
    "customDisplayName": "Reception"   # 1-16 chars, required
}
api.session.rest_post(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets",
    json=body
)
```

#### Add handsets in bulk (up to 50)

```python
body = {
    "items": [
        {"line1MemberId": person_id_1, "customDisplayName": "User 1"},
        {"line1MemberId": person_id_2, "line2MemberId": vl_id, "customDisplayName": "User 2"}
    ]
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets/bulk",
    json=body
)
# Returns per-item results: [{customDisplayName, result: {status, error: {message, errorCode}}}]
```

#### List handsets

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets",
    params={
        "basestationId": base_station_id,  # optional filter
        "memberId": person_id,             # optional filter
    }
)
handsets = result.get("handsets", [])
# Also: result["numberOfHandsetsAssigned"], result["numberOfLinesAssigned"]
```

#### Get handset details

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets/{handset_id}"
)
# Returns: {id, index, defaultDisplayName, customDisplayName, baseStationId, mac, accessCode, primaryEnabled, lines: [...]}
```

#### Update handset

```python
body = {
    "line1MemberId": new_person_id,
    "customDisplayName": "Updated Name",
    "line2MemberId": new_vl_id  # optional
}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets/{handset_id}",
    json=body
)
```

#### Delete a single handset

```python
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets/{handset_id}"
)
```

#### Delete multiple handsets

```python
body = {
    "handsetIds": [handset_id_1, handset_id_2],
    "deleteAll": False  # set True to delete all handsets (ignores handsetIds)
}
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/handsets/",
    json=body
)
```

### Association Queries

```python
# DECT networks for a person
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/dectNetworks")
networks = result.get("dectNetworks", [])

# DECT networks for a workspace
result = api.session.rest_get(f"{BASE}/telephony/config/workspaces/{workspace_id}/dectNetworks")
networks = result.get("dectNetworks", [])
```

### Available Members

```python
result = api.session.rest_get(f"{BASE}/telephony/config/devices/availableMembers", params={
    "max": 1000,
    "memberName": "Jane",
    "locationId": location_id,
    "excludeVirtualLine": True,  # virtual lines can't be line 1
})
members = result.get("members", [])
# Each: {id, firstName, lastName, phoneNumber, extension, memberType}
```

### Serviceability Password

```python
# Generate and enable password (WARNING: may reboot entire DECT network)
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/serviceabilityPassword/actions/generate/invoke"
)
password = result.get("password")  # 16-character string

# Get password status
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/serviceabilityPassword"
)
enabled = result.get("enabled")  # bool

# Update password status (WARNING: may reboot entire DECT network)
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{location_id}/dectNetworks/{network_id}/serviceabilityPassword",
    json={"enabled": False}
)
```

### Raw HTTP Gotchas

1. **`dectNetworkId` not `id` in create response.** The create network response returns `{"dectNetworkId": "..."}`, not `{"id": "..."}`. Parse accordingly.
2. **`list_dect_networks` is org-wide.** The list endpoint is `GET /telephony/config/dectNetworks` (no location in path). Pass `locationId` as a query param to filter.
3. **90-second cooldown on handset changes.** Adding or removing handsets within 90 seconds may leave base stations out of sync until rebooted.
4. **Bulk handset add uses `/handsets/bulk`**, not `/handsets`. The single-add endpoint is `POST /handsets` (no `/bulk` suffix).
5. **Delete multiple handsets uses trailing slash.** The URL is `.../handsets/` (with trailing slash), taking a JSON body with `handsetIds` array.
6. **Serviceability password operations can reboot the network.** Both generating a new password and toggling enabled status trigger a network-wide reboot.
7. **No API for auto-generated access codes.** When `defaultAccessCodeEnabled` is `false`, per-handset codes are auto-generated but cannot be retrieved via API.

---

## Common Gotchas

1. **Adding a DECT handset to a person with a Webex Calling Standard license disables Webex Calling** across their mobile, tablet, desktop, and browser applications. Deleting the handset re-enables it.

2. **90-second cooldown on handset changes.** Adding or removing handsets in less than 90 seconds may result in the base station not having the latest configuration until it is rebooted.

3. **No API for auto-generated access codes.** When `default_access_code_enabled` is `False`, per-handset access codes are auto-generated but cannot be retrieved via API. Use Control Hub.

4. **Access code uniqueness.** The default access code must be unique within the same location to prevent handsets from accidentally registering with base stations on different DECT networks in range.

5. **Serviceability password reboots the network.** Both generating a new password and toggling the enabled status can reboot the entire DECT network.

6. **Display name limits differ.** Network `display_name` is 11 characters max. Handset `custom_display_name` is 1-16 characters.

7. **Line 1 vs Line 2 member types.** Line 1 supports only PEOPLE and PLACE. Line 2 also supports VIRTUAL_LINE. Virtual lines cannot be the primary (line 1) member.

8. **Hot desk scopes not documented.** The source code for `HotDeskApi` does not include scope documentation in the docstrings, and the OpenAPI specs also omit security/scope blocks for the Hot Desk endpoints. <!-- Verified via wxc_sdk source and OpenAPI spec (webex-cloud-calling.json, webex-device.json) 2026-03-19 -->

9. **`DECTNetworkModel` has alternate names.** `dms_cisco_dbs110` and `cisco_dect_110_base` both refer to the same physical hardware (DBS-110). Same for the 210 variants. Choose either enum value.

10. **`list_dect_networks` is org-wide.** Unlike most DECT methods that require `location_id`, `list_dect_networks` searches across the entire org and accepts `location_id` as an optional filter.

11. **DECT network create returns `dectNetworkId`, not `id`, in response body.**
<!-- Verified via CLI implementation 2026-03-18 -->
The `create_dect_network` API response body returns the new network's identifier under the key `dectNetworkId`, not `id`. Code that parses the raw JSON response as `response['id']` will get a `KeyError`. The wxc_sdk method handles this internally and returns the ID as a string.

---

## See Also

- **[devices-core.md](devices-core.md)** — Cloud device CRUD, activation codes, MAC provisioning, and telephony device settings. DECT devices are excluded from `device_settings` / `update_device_settings` in that API.
- **[devices-workspaces.md](devices-workspaces.md)** — Workspace management including `HotdeskingStatus` enum and workspace hot desk creation constraints.
- **[virtual-lines.md](virtual-lines.md)** — Virtual line management. DECT handset Line 2 supports VIRTUAL_LINE member type; see that doc for virtual line CRUD and call settings.
