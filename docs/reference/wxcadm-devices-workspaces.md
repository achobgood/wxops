# wxcadm: Devices, DECT, Workspaces & Virtual Lines

Reference for device management, DECT networks, workspaces, virtual lines, and number management in wxcadm.

---

## Table of Contents

1. [Device Class](#device-class)
2. [Device Members & Layout](#device-members--layout)
3. [DECT Networks](#dect-networks)
4. [Workspace Class](#workspace-class)
5. [Virtual Lines](#virtual-lines)
6. [Number Management](#number-management)
7. [wxcadm vs wxc_sdk](#wxcadm-vs-wxc_sdk)

---

## Device Class

Source: `wxcadm/device.py`

### Access Patterns

Devices can be accessed from three scopes:

```python
# Org-level — all devices in the org
all_devices = org.devices

# Person-level — devices for a specific person
person_devices = person.devices

# Workspace-level — devices for a specific workspace
ws_devices = workspace.devices

# Location-level — devices at a location
loc_devices = DeviceList(org, parent=location)
```

All return a `DeviceList` (subclass of `UserList`).

### DeviceList Methods

#### `DeviceList.get(...)`

Find a device by various criteria. Returns a single `Device` or `None` (except `connection_status`, which returns a list).

```python
DeviceList.get(
    id: Optional[str] = None,
    name: Optional[str] = None,           # Case-insensitive
    mac_address: Optional[str] = None,     # Accepts colons, dashes, or raw
    spark_id: Optional[str] = None,
    connection_status: Optional[str] = None  # Returns a list
) -> Optional[Device]
```

```python
device = org.devices.get(mac_address="AA:BB:CC:DD:EE:FF")
device = org.devices.get(name="Lobby Phone")
disconnected = org.devices.get(connection_status="disconnected")
```

#### `DeviceList.create(...)`

Add a new device. Requires a `SupportedDevice` model reference.

```python
DeviceList.create(
    model: SupportedDevice,
    mac: Optional[str] = None,              # Omit to generate activation code
    password: Optional[str] = None,         # For non-Cisco-managed devices
    person: Optional[Person] = None,        # Required when DeviceList is Org-level
    workspace: Optional[Workspace] = None   # Required when DeviceList is Org-level
) -> dict
```

Return value varies by device type:

| Scenario | Keys in returned dict |
|---|---|
| Activation code (no MAC) | `device_id`, `activation_code` |
| MAC-based, Cisco-managed | `device_id`, `mac`, `device_object` |
| MAC-based, partner/customer-managed | `device_id`, `mac`, `device_object`, `sip_auth_user`, `line_port`, `password`, `sip_userpart`, `sip_hostpart`, `sip_outbound_proxy`, `sip_outbound_proxy_srv` |

```python
# Get a supported device model
model_8865 = org.devices.supported_devices.get("Cisco 8865")

# Create with activation code
result = workspace.devices.create(model=model_8865)
print(result['activation_code'])

# Create with MAC
result = workspace.devices.create(
    model=model_8865,
    mac="AABBCCDDEEFF"
)
print(result['device_id'])
```

**Scope note:** Your token needs `identity:placeonetimepassword_create` to generate activation codes.

#### `DeviceList.refresh()`

Re-fetches the device list from Webex.

#### `DeviceList.webex_calling(enabled=True)`

Filter to devices with Webex Calling enabled or disabled.

```python
wxc_devices = org.devices.webex_calling()
non_wxc = org.devices.webex_calling(enabled=False)
```

#### `DeviceList.get_by_status(status: str)`

Filter devices by connection status. Accepts raw API values plus grouping shortcuts:

| Value | Matches |
|---|---|
| `"online"` | `connected`, `connected_with_issues` |
| `"offline"` | `disconnected`, `offline_expired`, `offline_deep_sleep` |
| `"connected"` | Exact match |
| `"disconnected"` | Exact match |
| `"activating"` | Exact match |
| `"unknown"` | Exact match |

```python
offline_devices = org.devices.get_by_status("offline")
```

### Device Attributes

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Device ID |
| `model` | `str` | Model name (e.g. `"DMS Cisco 8865"`) |
| `mac` | `str` | MAC address (uppercase, no delimiters) |
| `display_name` | `str` | Display name in Webex |
| `ip_address` | `str` | Device IP |
| `activation_state` | `str` | Activation state |
| `type` | `str` | Type of device association |
| `is_owner` | `bool` | Whether parent is primary owner |
| `connection_status` | `str` | Online/offline status |
| `serial` | `str` | Serial number |
| `software` | `str` | OS/firmware version |
| `upgrade_channel` | `str` | Assigned upgrade channel |
| `tags` | `list` | Device tags |
| `capabilities` | `list` | Device capabilities |
| `user_permissions` | `list` | User permissions (e.g. `"xapi"`) |
| `owner` | `Person\|Workspace\|None` | Resolved primary owner |
| `location_id` | `str` | Location ID |
| `created` | `str` | Creation timestamp |
| `first_seen` | `str` | First online timestamp |
| `last_seen` | `str` | Last online timestamp |

### Device Properties & Methods

#### `Device.calling_id` (property)

The telephony-side device ID. Used internally for `/v1/telephony/config/devices/` API calls. Fetched lazily from the telephony config endpoint if not present in the device record.

#### `Device.config` (property)

Returns the full telephony device configuration as a dict.

#### `Device.settings` (property, settable)

Read or write the device settings. The structure varies by device model -- the raw dict from Webex is returned.

```python
# Read
settings = device.settings

# Write
device.settings = updated_settings_dict
```

#### `Device.layout` (property)

Returns the `DeviceLayout` for the device. See [DeviceLayout](#devicelayout) below.

#### `Device.members` (property)

Returns a `DeviceMemberList` of configured lines on the device. See [Device Members](#device-members--layout).

#### `Device.apply_changes() -> bool`

Issues a request to the device to download and apply configuration changes.

```python
device.apply_changes()
```

#### `Device.delete() -> bool`

Deletes the device from Webex Calling and Control Hub entirely.

#### `Device.change_tags(operation, tag=None)`

Modify the device tags.

```python
Device.change_tags(
    operation: str,   # "add", "remove", or "replace"
    tag: Optional[str | list] = None
) -> bool
```

```python
device.change_tags("add", "floor-3")
device.change_tags("replace", ["lobby", "reception"])
device.change_tags("remove")
```

### SupportedDevice & SupportedDeviceList

`SupportedDeviceList` enumerates all device models Webex supports. Access via:

```python
supported = org.devices.supported_devices
```

#### `SupportedDeviceList.get(model_name: str)`

Partial, case-insensitive match. Returns a single `SupportedDevice` if one match, or a list if multiple.

```python
model = org.devices.supported_devices.get("Cisco 8865")
# Returns a SupportedDevice dataclass

all_cisco_models = org.devices.supported_devices.get("Cisco")
# Returns a list of SupportedDevice
```

#### SupportedDevice Attributes

| Attribute | Type | Description |
|---|---|---|
| `model` | `str` | Model string (e.g. `"DMS Cisco 8865"`) |
| `display_name` | `str` | Human-friendly display name |
| `type` | `str` | Device type |
| `manufacturer` | `str` | Manufacturer name |
| `managed_by` | `str` | `"CISCO"` or third-party |
| `supported_for` | `list` | `["PEOPLE"]`, `["PLACE"]`, or both |
| `onboarding_method` | `list` | e.g. `["ACTIVATION_CODE", "MAC_ADDRESS"]` |
| `number_of_line_ports` | `int` | Number of line ports |
| `kem_support_enabled` | `bool` | KEM module support |
| `kem_module_count` | `int\|None` | Number of KEM modules supported |
| `kem_module_type` | `list\|None` | KEM module types |
| `allow_configure_layout_enabled` | `bool` | Layout configuration support |
| `allow_configure_ports_enabled` | `bool` | Port configuration support |
| `customizable_line_label_enabled` | `bool` | Custom line labels support |
| `upgrade_channel_enabled` | `bool` | Multiple upgrade channels |
| `customized_behaviors_enabled` | `bool` | Custom behaviors support |
| `default_upgrade_channel` | `str\|None` | Default upgrade channel |
| `additional_primary_line_appearances_enabled` | `bool\|None` | Additional PLA support |
| `basic_emergency_nomadic_enabled` | `bool\|None` | HELD support |

---

## Device Members & Layout

### DeviceMemberList

Each device has a `members` property returning a `DeviceMemberList` -- the configured lines on the phone.

```python
members = device.members
print(members.max_line_count)  # e.g. 10
```

#### `DeviceMemberList.add(...)`

Add a configured line (shared line appearance, primary line, etc.) to the device.

```python
DeviceMemberList.add(
    members: Person | Workspace | VirtualLine | list,
    line_type: str = 'shared',         # "primary" or "shared"
    line_label: Optional[str] = None,  # MPP only
    hotline_enabled: bool = False,
    hotline_destination: Optional[str] = None,
    allow_call_decline: bool = False
) -> bool
```

```python
# Add a shared line appearance
device.members.add(some_person, line_type='shared', line_label="Sales")

# Add multiple members at once (all get same settings)
device.members.add([person_a, person_b], line_type='shared')
```

**ATA note:** For Cisco 191/192 ATAs, the `t38FaxCompression` field is automatically set to `False` in the payload.

#### `DeviceMemberList.available_members()`

Returns a list of People and Workspaces eligible for assignment to this device.

#### `DeviceMemberList.ports_available()`

Returns a list of available port numbers.

#### `DeviceMemberList.port_map()`

Returns a dict mapping every port number to its assigned `DeviceMember` (or `None` if unassigned).

```python
port_map = device.members.port_map()
# {1: <DeviceMember>, 2: None, 3: None, ...}
```

#### `DeviceMemberList.get(person=None, workspace=None)`

Find a specific member on the device.

#### `DeviceMemberList.refresh()`

Re-fetch configured lines from Webex.

### DeviceMember

Represents a single configured line on a device.

#### DeviceMember Attributes

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Member ID (Person/Workspace/VirtualLine ID) |
| `member_type` | `str` | `"person"` or `"workspace"` |
| `port` | `int` | Port/line number on the device |
| `primary_owner` | `bool` | Whether this is the primary owner |
| `line_type` | `str` | `"PRIMARY"` or `"SHARED_CALL_APPEARANCE"` |
| `line_weight` | `int` | Number of ports this line consumes |
| `hotline_enabled` | `bool` | Hotline status |
| `hotline_destination` | `str\|None` | Hotline destination number |
| `call_decline_all` | `bool` | Decline-all-devices behavior |
| `line_label` | `str\|None` | Custom line label (MPP only) |
| `first_name` | `str\|None` | Member first name |
| `last_name` | `str\|None` | Member last name |
| `phone_number` | `str\|None` | Member phone number |
| `extension` | `str\|None` | Member extension |
| `esn` | `str\|None` | Enterprise Significant Number |
| `location_id` | `str\|None` | Location ID |

#### `DeviceMember.set_line_label(label: str) -> DeviceMember`

Set or update the line label on the device. MPP devices only.

```python
member = device.members.get(person=some_person)
member.set_line_label("Front Desk")
```

#### `DeviceMember.set_hotline(enabled: bool, destination: Optional[str]) -> DeviceMember`

Enable or disable hotline for the line.

```python
member.set_hotline(enabled=True, destination="+15551234567")
member.set_hotline(enabled=False)
```

#### `DeviceMember.set_call_decline_all(enabled: bool) -> DeviceMember`

Control decline behavior. When `True`, declining on this device declines on all devices. When `False`, only silences this device.

### DeviceLayout

Manages the key layout on a device (line keys and KEM keys).

#### DeviceLayout Attributes

| Attribute | Type | Description |
|---|---|---|
| `layout_mode` | `str` | Layout mode |
| `user_reorder_enabled` | `bool` | Whether user can reorder |
| `line_keys` | `list` | Line key configuration |
| `kem_type` | `str\|None` | KEM module type |
| `kem_keys` | `list\|None` | KEM key configuration |

#### Reading and Setting Layout

```python
layout = device.layout
print(layout.line_keys)

# Modify and apply
layout.line_keys = [...]  # See Webex Developer docs for format
device.set_layout(layout)
```

The `line_keys` and `kem_keys` lists use the raw format from the Webex Developer documentation. See: https://developer.webex.com/docs/api/v1/device-call-settings/modify-device-layout-by-device-id

---

## DECT Networks

Source: `wxcadm/dect.py`

DECT networks manage Cisco DBS110/DBS210 base stations and their associated handsets.

### Access Pattern

```python
# Org-level — all DECT networks
dect_networks = DECTNetworkList(org)

# Location-level — DECT networks at a specific location
dect_networks = DECTNetworkList(org, location=location)
```

<!-- NEEDS VERIFICATION -->
**Note:** The access pattern above shows direct instantiation. The actual accessor on `Org` or `Location` (e.g. `org.dect_networks` or `location.dect_networks`) depends on how these are wired up in the parent classes, which is outside the files reviewed here.

### DECTNetworkList Methods

#### `DECTNetworkList.create(...)`

Create a new DECT network.

```python
DECTNetworkList.create(
    name: str,
    model: str,                              # "DBS110", "110", "DBS210", or "210"
    default_access_code: Optional[str] = None,
    handset_display_name: Optional[str] = None,
    location: Optional[Location] = None      # Required for Org-level lists
) -> DECTNetwork
```

The `model` parameter is normalized internally:
- `"110"` or `"DBS110"` becomes `"DMS Cisco DBS110"`
- `"210"` or `"DBS210"` becomes `"DMS Cisco DBS210"`

```python
network = dect_networks.create(
    name="Building A DECT",
    model="DBS210",
    default_access_code="1234",
    location=building_a_location
)
```

#### `DECTNetworkList.delete(network: DECTNetwork)`

Delete a DECT network. Returns the updated `DECTNetworkList`.

#### `DECTNetworkList.refresh()`

Re-query the list from Webex.

#### `DECTNetworkList.with_base_stations(count=1)`

Filter to networks with at least `count` base stations.

#### `DECTNetworkList.with_handsets(count=1)`

Filter to networks with at least `count` handsets assigned.

### DECTNetwork Attributes

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Network ID |
| `name` | `str` | Network name |
| `display_name` | `str` | Display name |
| `chain_id` | `str` | Chain ID |
| `model` | `str` | Base station model |
| `default_access_code_enabled` | `bool` | Whether default access code is on |
| `default_access_code` | `str` | The default access code |
| `number_of_base_stations` | `int` | Count of base stations |
| `number_of_handsets_assigned` | `int` | Count of assigned handsets |
| `number_of_lines` | `int` | Count of lines |
| `location_id` | `str` | Location ID |

### DECTNetwork Methods

#### `DECTNetwork.base_stations` (property)

Returns a list of `DECTBaseStation` instances.

#### `DECTNetwork.handsets` (property)

Returns a list of `DECTHandset` instances.

#### `DECTNetwork.add_base_stations(mac_list: list) -> list[DECTBaseStation]`

Add one or more base stations by MAC address. Returns the full list of base stations (including pre-existing ones).

```python
stations = network.add_base_stations(["AABBCCDDEEFF", "112233445566"])
```

#### `DECTNetwork.delete_base_station(base_station: str | DECTBaseStation) -> list`

Delete a base station by `DECTBaseStation` instance or MAC address string. Returns remaining base stations.

```python
network.delete_base_station("AABBCCDDEEFF")
```

#### `DECTNetwork.get_base_station(mac: str) -> Optional[DECTBaseStation]`

Find a base station by MAC address.

#### `DECTNetwork.add_handset(...)`

Add a handset to the network.

```python
DECTNetwork.add_handset(
    display_name: str,                    # 16 chars max
    line1: Person | Workspace,            # Required
    line2: Optional[Person | Workspace]   # Optional second line
) -> bool
```

```python
network.add_handset(
    display_name="Warehouse 1",
    line1=warehouse_workspace,
    line2=manager_person
)
```

#### `DECTNetwork.delete_handset(handset: DECTHandset) -> list`

Delete a handset. Returns remaining handsets.

#### `DECTNetwork.set_name(name: str, display_name: Optional[str]) -> bool`

Change the network name (and optionally display name).

#### `DECTNetwork.set_display_name(display_name: str) -> bool`

Change only the display name.

#### `DECTNetwork.enable_default_access_code(access_code: Optional[str]) -> bool`

Enable the default access code. If the code was previously set and disabled, it can be re-enabled without passing the code again.

Raises `ValueError` if no code exists and none is provided.

#### `DECTNetwork.disable_default_access_code() -> bool`

Disable the default access code (preserves the stored code value).

#### `DECTNetwork.delete() -> bool`

Delete the entire DECT network.

### DECTBaseStation

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Base station ID |
| `mac` | `str` | MAC address (uppercase) |
| `number_of_lines_registered` | `int` | Lines registered to this base |

#### `DECTBaseStation.delete() -> bool`

Delete the base station.

#### `DECTBaseStation.get_handsets() -> list[DECTHandset]`

Get handsets associated with this specific base station.

### DECTHandset

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Handset ID |
| `index` | `str` | Handset index |
| `display_name` | `str` | Display name |
| `access_code` | `str` | Access code |
| `lines` | `list` | Configured lines |
| `mac` | `str` (property) | MAC address (lazy-loaded) |

#### `DECTHandset.delete() -> bool`

Delete the handset.

#### `DECTHandset.set_handset_display_name(display_name: str) -> bool`

Change the text displayed on the handset screen.

---

## Workspace Class

Source: `wxcadm/workspace.py`

Workspaces represent shared physical locations (conference rooms, lobby phones, common areas) in Webex Calling.

### Access Pattern

```python
# Org-level
workspaces = org.workspaces    # WorkspaceList

# Location-level
workspaces = WorkspaceList(org, location=location)
```

### WorkspaceList Methods

#### `WorkspaceList.create(...)`

Create a new Workspace with Webex Calling enabled.

```python
WorkspaceList.create(
    location: Location,
    name: str,
    floor: Optional[LocationFloor] = None,
    capacity: Optional[int] = None,
    type: Optional[str] = 'notSet',          # See types below
    phone_number: Optional[str] = None,
    extension: Optional[str] = None,
    notes: Optional[str] = None,
    hotdesking: Optional[bool] = False,
    supported_devices: Optional[str] = 'phones',   # "phones" or "collaborationDevices"
    license_type: str = 'workspace',                # "workspace", "professional", or "hotdesk"
    ignore_license_overage: Optional[bool] = True
) -> Workspace
```

**Workspace types:** `"notSet"`, `"focus"`, `"huddle"`, `"meetingRoom"`, `"open"`, `"desk"`, `"other"`

**License types:**
- `"workspace"` -- Standard Workspace license
- `"professional"` -- Professional license (full calling features)
- `"hotdesk"` -- Hot Desking license (requires `hotdesking=True`)

```python
lobby = workspaces.create(
    location=hq_location,
    name="Main Lobby",
    extension="8100",
    phone_number="+15559998100",
    type="open",
    supported_devices="phones",
    license_type="workspace"
)
```

Raises:
- `ValueError` if neither `extension` nor `phone_number` is provided (unless `hotdesk` license)
- `wxcadm.NotSubscribedForLicenseError` if the license type is not available
- `wxcadm.LicenseOverageError` if `ignore_license_overage=False` and assignment would exceed count

#### `WorkspaceList.get(id=None, name=None, uuid=None)`

Find a workspace by ID, name, or UUID.

```python
ws = workspaces.get(name="Main Lobby")
ws = workspaces.get(id="some-workspace-id")
```

#### `WorkspaceList.get_by_id(id: str)`

Find a workspace by ID only.

#### `WorkspaceList.webex_calling()`

Return only workspaces with Webex Calling enabled.

#### `WorkspaceList.professional()`

Return only workspaces with a Professional license.

#### `WorkspaceList.refresh()`

Re-query the workspace list from Webex.

### Workspace Attributes

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Workspace ID |
| `name` | `str` | Display name |
| `org` | `Org` | Parent org |
| `location` | `Location\|None` | Assigned location |
| `capacity` | `int` | Room capacity |
| `type` | `str` | Workspace type |
| `sip_address` | `str` | SIP URI |
| `calling` | `str` | Calling type (`webexCalling`, `freeCalling`, etc.) |
| `calendar` | `dict\|None` | Calendar connector info |
| `notes` | `str` | Free-form notes |
| `licenses` | `list` | Assigned license IDs |
| `created` | `str` | Creation timestamp |

### Workspace Properties

#### `Workspace.number` (property)

Returns the phone number. Single number returns a string; multiple numbers returns a list. Makes an API call on first access.

#### `Workspace.extension` (property)

Returns the extension. Same single/list behavior as `number`.

#### `Workspace.esn` (property)

The Enterprise Significant Number.

#### `Workspace.devices` (property)

Returns the `DeviceList` for this workspace.

#### `Workspace.caller_id` (property)

Returns the Caller ID settings as a dict.

#### `Workspace.ecbn` (property)

Returns the Emergency Callback Number details.

#### `Workspace.barge_in` (property)

Returns the `BargeInSettings` for the workspace, or `None` if not configured.

#### `Workspace.monitoring` (property)

Returns the `MonitoringList` associated with the workspace.

#### `Workspace.license_type` (property)

Returns the license type: `"WORKSPACE"`, `"PROFESSIONAL"`, `"HOTDESK"`, `"MULTIPLE"`, or `None`.

#### `Workspace.spark_id` (property)

The internal Webex identifier (decoded from base64).

### Workspace Methods

#### `Workspace.set_caller_id(name, number, block_for_received_calls=False) -> bool`

Set the Caller ID for the workspace.

```python
Workspace.set_caller_id(
    name: str,      # "direct", "location", or custom string
    number: str,    # "direct", "location", or custom number
    block_for_received_calls: Optional[bool] = False
) -> bool
```

```python
workspace.set_caller_id(name="Main Lobby", number="direct")
workspace.set_caller_id(name="location", number="location")
workspace.set_caller_id(name="Custom Name", number="+15551234567")
```

#### `Workspace.set_ecbn(value) -> bool`

Set the Emergency Callback Number.

```python
# Use the workspace's own direct line
workspace.set_ecbn("direct")

# Use the location ECBN
workspace.set_ecbn("location")

# Use another member's number
workspace.set_ecbn(some_person)       # Person, Workspace, or VirtualLine
```

#### `Workspace.assign_wxc(...) -> bool`

Enable Webex Calling for a workspace that does not currently have it.

```python
Workspace.assign_wxc(
    location: Location,
    phone_number: Optional[str] = None,
    extension: Optional[str] = None,
    license_type: str = 'workspace',
    ignore_license_overage: bool = True
) -> bool
```

#### `Workspace.unassign_wxc() -> bool`

Disable Webex Calling. Only works for workspaces with `supportedDevices="collaborationDevices"`. Phone-based workspaces must be deleted and recreated.

#### `Workspace.set_professional_license() -> bool`

Upgrade the workspace to a Professional license. No-op if already Professional.

#### `Workspace.set_hotdesk(enabled=True) -> bool`

Enable or disable hot desking.

#### `Workspace.delete() -> bool`

Delete the workspace entirely.

#### `Workspace.get_config()`

Refresh the workspace config from the API.

#### `Workspace.get_monitored_by()`

Returns a list of users/workspaces that are monitoring this workspace.

---

## Virtual Lines

Source: `wxcadm/virtual_line.py`

Virtual Lines represent phone identities that are not tied to a specific person -- used for shared numbers, lobby lines, or lines that appear on multiple devices.

### Access Pattern

```python
# Org-level
virtual_lines = org.virtual_lines    # VirtualLineList

# Location-level
virtual_lines = VirtualLineList(org, location=location)
```

### VirtualLineList Methods

#### `VirtualLineList.create(...)`

Create a new Virtual Line.

```python
VirtualLineList.create(
    first_name: str,
    last_name: str,
    phone_number: Optional[str] = None,
    extension: Optional[str] = None,
    location: Optional[Location | str] = None,     # Required for Org-level lists
    caller_id_first_name: Optional[str] = None,
    caller_id_last_name: Optional[str] = None,
    caller_id_number: Optional[str] = None
) -> VirtualLine
```

At least one of `phone_number` or `extension` is required.

```python
vl = virtual_lines.create(
    first_name="Sales",
    last_name="Line",
    extension="8200",
    phone_number="+15559998200",
    location=hq_location
)
```

**Note:** The returned `VirtualLine` only has the `id` populated initially. Call `vl.refresh_config()` to populate all fields.

#### `VirtualLineList.get(...)`

Find a virtual line by ID or name.

```python
VirtualLineList.get(
    id: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    name: Optional[str] = None            # "first last" shortcut
) -> Optional[VirtualLine]
```

```python
vl = virtual_lines.get(name="Sales Line")
vl = virtual_lines.get(first_name="Sales", last_name="Line")
```

Name matching is case-insensitive. Both `first_name` and `last_name` are required when searching by name (unless using the `name` shortcut).

#### `VirtualLineList.refresh()`

Re-query from Webex.

### VirtualLine Attributes

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Virtual Line ID |
| `first_name` | `str` | First name |
| `last_name` | `str` | Last name |
| `caller_id_first_name` | `str` | Caller ID first name |
| `caller_id_last_name` | `str` | Caller ID last name |
| `caller_id_number` | `str` | Caller ID number |
| `external_caller_id_policy` | `str` | External caller ID policy |
| `extension` | `str\|None` | Extension |
| `esn` | `str\|None` | Enterprise Significant Number |
| `phone_number` | `str\|None` | DID phone number |
| `location_id` | `str` | Location ID |
| `billing_plan` | `str` | Billing plan |
| `num_devices_assigned` | `int` | Count of assigned devices |

### VirtualLine Properties (Lazy-Loaded)

These trigger a detail API call on first access:

| Property | Type | Description |
|---|---|---|
| `display_name` | `str` | Full display name |
| `name` | `str` | Alias for `display_name` |
| `directory_search_enabled` | `bool` | Directory search visibility |
| `announcement_language` | `str` | Announcement language |
| `time_zone` | `str` | Time zone |
| `ecbn` | `dict` | Emergency Callback Number details |

### VirtualLine Methods

#### `VirtualLine.update(**kwargs) -> bool`

Update any attribute(s) with keyword arguments.

```python
vl.update(first_name="Reception", last_name="Desk")
vl.update(phone_number="+15559998201")
vl.update(extension="8201", time_zone="America/New_York")
```

Raises `AttributeError` if you pass a non-existing attribute.

#### `VirtualLine.set_ecbn(value)`

Set the Emergency Callback Number. Same interface as `Workspace.set_ecbn()`.

```python
vl.set_ecbn("direct")
vl.set_ecbn("location")
vl.set_ecbn(some_person)
```

#### `VirtualLine.enable_call_recording(...) -> bool`

Enable and configure call recording.

```python
VirtualLine.enable_call_recording(
    type: str,                        # "always", "never", "always_with_pause", "on_demand"
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

```python
vl.enable_call_recording(
    type="always",
    announcement_enabled=True,
    transcribe=True,
    ai_summary=True
)
```

**Note:** The `transcribe`, `can_play`, etc. parameters only apply to Webex-platform recording. Third-party recording providers ignore them.

#### `VirtualLine.disable_call_recording() -> bool`

Disable call recording. Returns `True` even if recording was not previously enabled.

#### `VirtualLine.get_call_recording() -> dict`

Returns the current call recording configuration.

<!-- NEEDS VERIFICATION -->
**Note:** This method appears to have a bug in the source -- it passes `'get'` as the first argument to `self.org.api.get()`, which may be interpreted as the URL instead of the intended endpoint. The intended URL is `v1/telephony/config/virtualLines/{id}/callRecording`.

#### `VirtualLine.refresh_config() -> bool`

Re-fetch the Virtual Line config from Webex. Useful after `create()` since the initial instance only has the ID.

#### `VirtualLine.delete() -> bool`

Delete the Virtual Line.

<!-- NEEDS VERIFICATION -->
**Note:** The `delete()` method returns `False` on success (appears to be a bug -- other `delete()` methods return `True`).

#### `VirtualLine.get_monitored_by()`

Returns a list of users/workspaces monitoring this virtual line.

---

## Number Management

Source: `wxcadm/number.py`

### Access Pattern

```python
# Org-level
numbers = org.numbers    # NumberList

# Location-level
numbers = NumberList(org, location=location)
```

### Number Dataclass

`Number` is a `@dataclass_json` decorated dataclass with automatic camelCase mapping.

| Attribute | Type | Description |
|---|---|---|
| `phone_number` | `str\|None` | The phone number (E.164) |
| `extension` | `str\|None` | Extension |
| `routing_prefix` | `str\|None` | Location routing prefix |
| `esn` | `str\|None` | Enterprise Significant Number |
| `state` | `str\|None` | Number state (`"ACTIVE"`, `"INACTIVE"`) |
| `phone_number_type` | `str\|None` | Number type |
| `included_telephony_types` | `str\|None` | Telephony types included |
| `main_number` | `bool\|None` | Whether this is a location main number |
| `toll_free_number` | `bool\|None` | Whether toll-free |
| `location` | `Location\|dict` (property) | Resolved Location or raw dict |
| `owner` | `Person\|Workspace\|VirtualLine\|...` (property) | Resolved owner |

The `owner` property resolves across multiple types: `PEOPLE`, `PLACE` (Workspace), `VIRTUAL_LINE`, `CALL_QUEUE`, `HUNT_GROUP`, `AUTO_ATTENDANT`, `PAGING_GROUP`, `VOICEMAIL_GROUP`, and `VOICE_MESSAGING` (voice portal).

#### `Number.activate() -> bool`

Activate the phone number at its location.

```python
number = numbers.get(phone_number="+15551234567")
number.activate()
```

### NumberList Methods

#### `NumberList.get(...)`

Find numbers by various criteria.

```python
NumberList.get(
    phone_number: Optional[str] = None,    # Partial match supported
    extension: Optional[str] = None,
    esn: Optional[str] = None,
    state: Optional[str] = None,
    location: Optional[Location] = None
) -> Optional[Number | list[Number]]
```

Return type depends on the search:
- `phone_number` or `esn`: Returns a single `Number` or `None`
- `extension` + `location`: Returns a single `Number` or `None`
- `extension` alone: Returns a `Number` if one match, `list` if multiple
- `state` or `location` alone: Returns a `list`

```python
num = numbers.get(phone_number="+15551234567")
nums = numbers.get(state="ACTIVE")
nums = numbers.get(location=hq_location)
```

#### `NumberList.get_by_owner(owner)`

Find a number by its owner (Person, Workspace, VirtualLine, etc.).

```python
num = numbers.get_by_owner(some_person)
```

#### `NumberList.add(...)`

Add numbers to a location. Only supported for Local Gateway or Non-integrated PSTN locations.

```python
NumberList.add(
    location: Location,
    numbers: list,                         # List of number strings
    number_type: Optional[str] = 'DID',    # "DID" or "TOLLFREE"
    state: Optional[str] = 'ACTIVE'        # "ACTIVE" or "INACTIVE"
) -> NumberList
```

```python
numbers.add(
    location=hq_location,
    numbers=["+15551110001", "+15551110002", "+15551110003"],
    number_type="DID",
    state="ACTIVE"
)
```

Returns the refreshed `NumberList`.

#### `NumberList.validate(numbers: list) -> dict`

Validate phone numbers before adding. Returns the Webex validation response.

```python
result = numbers.validate(["+15551110001", "+15551110002"])
```

#### `NumberList.refresh()`

Re-fetch the number list from Webex.

---

## wxcadm vs wxc_sdk

Both libraries wrap the same Webex Calling APIs, but they differ in design philosophy and usage patterns.

### Design Philosophy

| Aspect | wxcadm | wxc_sdk |
|---|---|---|
| Pattern | Object-oriented, stateful | Flat API wrapper, mostly stateless |
| Data model | Rich classes with methods (e.g. `Device.apply_changes()`) | Pydantic models as data containers + separate API methods |
| Lists | `UserList` subclasses with built-in filtering | API methods return plain lists of models |
| Lazy loading | Properties fetch on first access (e.g. `Device.calling_id`, `VirtualLine.display_name`) | Explicit API calls required |
| Authentication | `Org` object holds the API session | `WebexSimpleApi` holds the token |

### Device Management Comparison

```python
# wxcadm — object-oriented
device = workspace.devices.get(mac_address="AABBCCDDEEFF")
device.settings = new_settings
device.apply_changes()

# wxc_sdk — functional
api = WebexSimpleApi(tokens=token)
devices = api.devices.list(workspace_id=ws_id)
device = next(d for d in devices if d.mac == "AABBCCDDEEFF")
api.telephony.devices.update_settings(device_id=device.device_id, settings=new_settings)
api.telephony.devices.apply_changes(device_id=device.device_id)
```

### Workspace Comparison

```python
# wxcadm — create workspace with calling
ws = org.workspaces.create(
    location=location, name="Lobby", extension="8100",
    license_type="workspace"
)
# License selection is automatic

# wxc_sdk — more manual steps
ws = api.workspaces.create(settings=WorkspaceSettings(...))
# License assignment often separate or embedded in settings
```

### Key Differences for Device/Workspace Operations

| Operation | wxcadm | wxc_sdk |
|---|---|---|
| List supported devices | `org.devices.supported_devices` | `api.telephony.supported_devices()` |
| Create device (activation code) | `workspace.devices.create(model=m)` | `api.devices.create_by_activation_code(...)` |
| Get device members/lines | `device.members` (property) | `api.telephony.devices.members(device_id=...)` |
| Add shared line | `device.members.add(person)` | `api.telephony.devices.update_members(device_id=..., members=[...])` |
| Create DECT network | `dect_list.create(name=..., model=...)` | `api.telephony.dect_devices.create_network(...)` <!-- NEEDS VERIFICATION --> |
| Virtual line CRUD | `org.virtual_lines.create(...)` / `vl.update(...)` / `vl.delete()` | `api.telephony.virtual_lines.create(...)` / `.update(...)` / `.delete(...)` <!-- NEEDS VERIFICATION --> |

### When to Use Which

- **wxcadm**: Better for scripts that navigate the object graph (org -> location -> workspace -> device -> members). The stateful design means fewer IDs to track.
- **wxc_sdk**: Better for targeted API operations when you already have IDs, or when you need access to newer API endpoints that wxcadm may not yet wrap. Also has Pydantic validation on inputs.

---

## Common Patterns

### Provision a Workspace with a Phone

```python
import wxcadm

org = wxcadm.Org(access_token="...")
location = org.locations.get(name="Headquarters")

# 1. Create workspace
ws = org.workspaces.create(
    location=location,
    name="Conference Room B",
    extension="8150",
    type="meetingRoom",
    license_type="workspace"
)

# 2. Get the supported device model
model = org.devices.supported_devices.get("Cisco 8845")

# 3. Create device with activation code
result = ws.devices.create(model=model)
print(f"Activation Code: {result['activation_code']}")
```

### Add a Shared Line Appearance

```python
device = person.devices[0]
target_workspace = org.workspaces.get(name="Lobby Phone")

device.members.add(
    target_workspace,
    line_type="shared",
    line_label="Lobby"
)
device.apply_changes()
```

### Set Up a DECT Network

```python
location = org.locations.get(name="Warehouse")
dect_list = DECTNetworkList(org, location=location)

# Create network
network = dect_list.create(
    name="Warehouse DECT",
    model="DBS210",
    default_access_code="5678",
    location=location
)

# Add base stations
network.add_base_stations(["AABBCCDDEEFF", "112233445566"])

# Add a handset
warehouse_ws = org.workspaces.get(name="Warehouse Floor")
network.add_handset(
    display_name="Floor 1",
    line1=warehouse_ws
)
```

### Bulk Number Add and Virtual Line Creation

```python
location = org.locations.get(name="Branch Office")

# Add numbers to the location (Local Gateway/Non-integrated PSTN only)
org.numbers.add(
    location=location,
    numbers=["+15559990001", "+15559990002"]
)

# Create a virtual line with one of the new numbers
vl = org.virtual_lines.create(
    first_name="Reception",
    last_name="Line",
    phone_number="+15559990001",
    extension="9001",
    location=location
)
vl.refresh_config()

# Assign to a device as a shared line
device = org.devices.get(mac_address="FFEEDDCCBBAA")
device.members.add(vl, line_type="shared", line_label="Reception")
```

---

## See Also

- [devices-core.md](devices-core.md) — wxc_sdk device management APIs (listing, creation, configuration, members)
- [devices-dect.md](devices-dect.md) — wxc_sdk DECT network management for comparison with wxcadm's `DECTNetworkList`
- [devices-workspaces.md](devices-workspaces.md) — wxc_sdk workspace device provisioning and workspace call settings
