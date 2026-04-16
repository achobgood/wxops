<!-- Updated by playbook session 2026-03-18 -->

# Devices API Reference (wxc_sdk)

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: specs/webex-device.json
- developer.webex.com Device APIs

## Table of Contents

1. [DevicesApi (Cloud Device CRUD)](#1-devicesapi-cloud-device-crud)
2. [DeviceConfigurationsApi (RoomOS / Config-Service Settings)](#2-deviceconfigurationsapi-roomos--config-service-settings)
3. [TelephonyDevicesApi (Webex Calling Device Management)](#3-telephonydevicesapi-webex-calling-device-management)
4. [Code Examples](#4-code-examples)
5. [API Relationship Summary](#5-api-relationship-summary)
6. [Raw HTTP](#6-raw-http)
7. [Gotchas](#7-gotchas)
8. [See Also](#see-also)

---

Three separate API surfaces handle device management in the wxc_sdk. They cover different concerns and live at different SDK paths.

| API | SDK Path | Base Endpoint | Purpose |
|-----|----------|---------------|---------|
| **DevicesApi** | `wxc_sdk.devices` | `devices` | Cloud-registered device CRUD, activation codes, MAC provisioning, tags |
| **DeviceConfigurationsApi** | `wxc_sdk.device_configurations` | `deviceConfigurations` | RoomOS / config-service device-level settings (key-value) |
| **TelephonyDevicesApi** | `wxc_sdk.telephony.devices` | `telephony/config` | Calling-specific: supported models, members/lines, line key templates, layouts, background images, MAC validation |

Access on a `WebexSimpleApi` instance:

```python
api.devices                  # DevicesApi
api.device_configurations    # DeviceConfigurationsApi
api.telephony.devices        # TelephonyDevicesApi
```

---

## 1. DevicesApi (Cloud Device CRUD)

**Module:** `wxc_sdk.devices`

Manages cloud-registered Webex RoomOS devices and Webex Calling phones. Devices may be associated with workspaces or persons.

### 1.1 Required Scopes

| Action | Scope |
|--------|-------|
| Search / view own devices | `spark:devices_read` |
| Update / delete own devices | `spark:devices_write` |
| View all org devices | `spark-admin:devices_read` |
| Add / update / delete all org devices | `spark-admin:devices_write` |
| Generate activation code | `spark-admin:devices_write` + one of `identity:placeonetimepassword_create` or `identity:one_time_password` |

> These APIs cannot be used with Cisco 98xx devices that are not yet Webex Aware. Use Webex Control Hub for those.

### 1.2 Data Models

#### `Device`

Primary device record returned by list/details operations.

| Field | Type | Notes |
|-------|------|-------|
| `device_id` | `str` | Unique ID (alias `id` in JSON) |
| `calling_device_id` | `Optional[str]` | ID for Webex Calling APIs |
| `webex_device_id` | `Optional[str]` | ID for Webex Devices APIs |
| `display_name` | `str` | Friendly name |
| `workspace_id` | `Optional[str]` | Associated workspace |
| `person_id` | `Optional[str]` | Associated person |
| `org_id` | `str` | Organization |
| `capabilities` | `list[str]` | e.g. `xapi` |
| `permissions` | `list[str]` | User permissions for this device |
| `connection_status` | `Optional[ConnectionStatus]` | See enum below |
| `product` | `str` | Display-friendly model name |
| `product_type` | `ProductType` | `phone` or `roomdesk` (alias `type`) |
| `tags` | `list[str]` | Tags assigned to device |
| `ip` | `Optional[str]` | Current IP |
| `active_interface` | `Optional[str]` | Network connectivity type |
| `mac` | `Optional[str]` | MAC address (colons stripped by validator) |
| `primary_sip_url` | `Optional[str]` | Primary SIP address |
| `sip_urls` | `list[Any]` | All SIP addresses |
| `serial` | `Optional[str]` | Serial number |
| `software` | `Optional[str]` | OS / version tag |
| `upgrade_channel` | `Optional[str]` | Upgrade channel assignment |
| `created` | `Optional[datetime]` | Registration timestamp (ISO 8601) |
| `location_id` | `Optional[str]` | Location |
| `workspace_location_id` | `Optional[str]` | Workspace location |
| `first_seen` | `Optional[datetime]` | First seen timestamp |
| `last_seen` | `Optional[datetime]` | Last seen timestamp |
| `managed_by` | `Optional[DeviceManagedBy]` | `CISCO`, `CUSTOMER`, or `PARTNER` |
| `manufacturer` | `Optional[str]` | 3rd-party devices only |
| `line_port` | `Optional[str]` | 3rd-party devices only |
| `outbound_proxy` | `Optional[str]` | 3rd-party devices only |
| `sip_user_name` | `Optional[str]` | 3rd-party devices only |
| `device_platform` | `Optional[DevicePlatform]` | Platform enum |
| `lifecycle` | `Optional[Lifecycle]` | Device lifecycle state |
| `planned_maintenance` | `Optional[MaintenanceMode]` | Maintenance mode |

#### Enums

**`ProductType`**: `phone`, `roomdesk`

**`ConnectionStatus`**: `connected`, `disconnected`, `connected_with_issues`, `offline_expired`, `activating`, `unknown`, `offline_deep_sleep`

**`Lifecycle`**: `UNKNOWN`, `ACTIVE`, `END_OF_SALE`, `END_OF_MAINTENANCE`, `END_OF_SERVICE`, `UPCOMING_END_OF_SUPPORT`, `END_OF_SUPPORT`

**`TagOp`**: `add`, `remove`, `replace`

#### `ActivationCodeResponse`

| Field | Type | Notes |
|-------|------|-------|
| `code` | `str` | The activation code |
| `expiry_time` | `datetime` | Code expiration |

### 1.3 Methods

#### `list(...) -> Generator[Device, None, None]`

Lists all active Webex devices. Administrators see all org devices. Supports pagination.

```python
def list(
    self,
    person_id: str = None,
    workspace_id: str = None,
    location_id: str = None,
    workspace_location_id: str = None,     # deprecated, prefer location_id
    display_name: str = None,
    product: str = None,
    product_type: ProductType = None,       # roomdesk, phone
    tag: str = None,                        # comma-separated for logical AND
    connection_status: ConnectionStatus = None,
    serial: str = None,
    software: str = None,
    upgrade_channel: str = None,
    error_code: str = None,
    capability: str = None,
    permission: str = None,
    mac: str = None,
    device_platform: DevicePlatform = None,
    planned_maintenance: MaintenanceMode = None,
    org_id: str = None,
    **params
) -> Generator[Device, None, None]
```

#### `details(device_id, org_id=None) -> Device`

Get device details by ID.

```python
def details(self, device_id: str, org_id: str = None) -> Device
```

#### `delete(device_id, org_id=None)`

Delete a device by ID.

```python
def delete(self, device_id: str, org_id: str = None)
```

#### `modify_device_tags(device_id, op, value=None, org_id=None) -> Device`

Update device tags using JSON Patch syntax. Uses `application/json-patch+json` content type.

```python
def modify_device_tags(
    self,
    device_id: str,
    op: TagOp,          # add, remove, replace
    value: List[str] = None,
    org_id: str = None
) -> Device
```

#### `activation_code(workspace_id=None, person_id=None, model=None, org_id=None) -> ActivationCodeResponse`

Generate an activation code for a device in a workspace or for a person.

- Provide **either** `workspace_id` **or** `person_id`, not both.
- If no `model` is supplied, the code is only accepted on RoomOS devices.
- For phones, `model` is required (obtain from `telephony.devices.supported_devices()`).
- Adding a device to a workspace with calling type `none` or `thirdPartySipCalling` resets to `freeCalling`.

```python
def activation_code(
    self,
    workspace_id: str = None,
    person_id: str = None,
    model: str = None,
    org_id: str = None
) -> ActivationCodeResponse
```

#### `create_by_mac_address(mac, workspace_id=None, person_id=None, model=None, password=None, org_id=None) -> Optional[Device]`

Create a phone by MAC address in a workspace or for a person.

```python
def create_by_mac_address(
    self,
    mac: str,
    workspace_id: str = None,
    person_id: str = None,
    model: str = None,
    password: str = None,       # required for 3rd-party devices
    org_id: str = None
) -> Optional[Device]
```

### 1.4 Sub-APIs

**`DevicesApi.settings_jobs`** (`DeviceSettingsJobsApi`) -- handles bulk device settings jobs at the location and organization level. Methods: `change(location_id, customization, org_id)` to initiate bulk settings changes, `list(org_id)` to list all jobs, `status(job_id, org_id)` to get job status, and `errors(job_id, org_id)` to list job errors. Defined in `wxc_sdk.telephony.jobs.DeviceSettingsJobsApi`, base path `telephony/config/jobs/devices/callDeviceSettings`.

> **Gotcha — Tags PATCH content type:** `modify_device_tags` uses `application/json-patch+json` content type, not standard JSON. The SDK handles this automatically, but raw HTTP callers must set the header explicitly.

> **Gotcha — Two device API surfaces:** `api.devices` (`/v1/devices`) manages cloud device entities (CRUD, tags, activation). `api.telephony.devices` (`/v1/telephony/config/devices`) manages Webex Calling config (members, settings, layout, line keys). These are separate API surfaces with potentially different device IDs — use `callingDeviceId` for telephony config endpoints.

### 1.5 CLI Examples

CLI group: `wxcli devices` (6 commands)

```bash
# List all devices in the org
wxcli devices list

# List only phones (exclude RoomOS devices)
wxcli devices list --type phone

# List devices for a specific person
wxcli devices list --person-id PERSON_ID

# List devices in a workspace
wxcli devices list --workspace-id WORKSPACE_ID

# Filter by display name, connection status, or location
wxcli devices list --display-name "Lobby Phone"
wxcli devices list --connection-status connected
wxcli devices list --location-id LOCATION_ID

# Filter by tag (comma-separated for AND logic)
wxcli devices list --tag "floor-3,building-a"

# Filter by MAC address
wxcli devices list --mac AABBCCDDEEFF

# Get full device details (JSON output)
wxcli devices show DEVICE_ID

# Get device details in table format
wxcli devices show DEVICE_ID -o table

# Create a device by MAC address (for a workspace)
wxcli devices create --mac AABBCCDDEEFF --model "DMS Cisco 8845" --workspace-id WORKSPACE_ID

# Create a device by MAC for a person
wxcli devices create --mac AABBCCDDEEFF --model "DMS Cisco 8845" --person-id PERSON_ID

# Create a 3rd-party device (requires SIP password)
wxcli devices create --mac AABBCCDDEEFF --model "DMS Cisco 8845" --person-id PERSON_ID --password "sip_pass"

# Generate an activation code for a workspace (RoomOS — no model needed)
wxcli devices create-activation-code --workspace-id WORKSPACE_ID

# Generate an activation code for a phone (model required)
wxcli devices create-activation-code --person-id PERSON_ID --model "DMS Cisco 8845"

# Modify device tags (add, remove, or replace)
wxcli devices update DEVICE_ID --op add --json-body '[{"op":"add","path":"tags","value":["floor-3","building-a"]}]'

# Delete a device (with confirmation prompt)
wxcli devices delete DEVICE_ID

# Delete a device (skip confirmation)
wxcli devices delete DEVICE_ID --force
```

---

## 2. DeviceConfigurationsApi (RoomOS / Config-Service Settings)

**Module:** `wxc_sdk.device_configurations`

Manages key-value configurations on Webex Rooms devices and other devices that use the configuration service. This is for RoomOS-level settings (e.g., `Conference.MaxReceiveCallRate`, `Audio.Ultrasound.*`), not Webex Calling phone settings.

### 2.1 Required Scopes

| Action | Scope |
|--------|-------|
| View configurations | `spark-admin:devices_read` |
| Add / update / delete configurations | `spark-admin:devices_write` + `spark-admin:devices_read` |

### 2.2 Data Models

#### `DeviceConfigurationResponse`

| Field | Type | Notes |
|-------|------|-------|
| `device_id` | `str` | Device the configs belong to |
| `items` | `dict[str, DeviceConfiguration]` | Key = config path, value = config object |

#### `DeviceConfiguration`

| Field | Type | Notes |
|-------|------|-------|
| `value` | `Optional[Any]` | Current effective value |
| `source` | `Literal['default', 'configured']` | Where the current value comes from |
| `sources` | `DeviceConfigurationSources` | Default and configured source details |
| `value_space` | `Any` | JSON Schema describing valid values |

#### `DeviceConfigurationSources`

| Field | Type |
|-------|------|
| `default` | `DeviceConfigurationSource` |
| `configured` | `DeviceConfigurationSource` |

#### `DeviceConfigurationSource`

| Field | Type | Notes |
|-------|------|-------|
| `value` | `Any` | Value at this source level |
| `editability` | `DeviceConfigurationSourceEditability` | Whether this source is editable |
| `level` | `str` | Configuration level |
| `enforced` | `Optional[bool]` | Whether enforced |

#### `DeviceConfigurationSourceEditability`

| Field | Type | Notes |
|-------|------|-------|
| `is_editable` | `bool` | Always `False` for `default` source |
| `reason` | `Optional[str]` | `NOT_AUTHORIZED` or `CONFIG_MANAGED_BY_DIFFERENT_AUTHORITY` |

#### `DeviceConfigurationOperation` (NamedTuple)

Used to build update payloads.

| Field | Type | Notes |
|-------|------|-------|
| `op` | `Literal['remove', 'replace']` | `remove` reverts to default; `replace` sets configured value |
| `key` | `str` | Configuration key path |
| `value` | `Optional[Any]` | Required for `replace`, ignored for `remove` |

### 2.3 Methods

#### `list(device_id, key=None) -> DeviceConfigurationResponse`

List all configurations for a device. Optionally filter by key pattern.

```python
def list(self, device_id: str, key: str = None) -> DeviceConfigurationResponse
```

**Key filtering syntax:**
- **Absolute:** `Conference.MaxReceiveCallRate` -- single config
- **Wildcard:** `Audio.Ultrasound.*` -- all matching configs
- **Range:** `FacilityService.Service[1].Name` (first only), `FacilityService.Service[*].Name` (all), `FacilityService.Service[1..3].Name` (range), `FacilityService.Service[2..n].Name` (from index 2 onward)

#### `update(device_id, operations) -> DeviceConfigurationResponse`

Update configurations. Uses JSON Patch (`application/json-patch+json`).

```python
def update(
    self,
    device_id: str,
    operations: List[DeviceConfigurationOperation]
) -> DeviceConfigurationResponse
```

**Example:**

```python
from wxc_sdk.device_configurations import DeviceConfigurationOperation

# Set a configuration value
ops = [
    DeviceConfigurationOperation(op='replace', key='Conference.MaxReceiveCallRate', value=6000),
    DeviceConfigurationOperation(op='remove', key='Audio.Ultrasound.MaxVolume'),  # revert to default
]
result = api.device_configurations.update(device_id='DEVICE_ID', operations=ops)
```

### 2.4 CLI Examples

CLI group: `wxcli device-configurations` (2 commands)

```bash
# List all configurations for a device
wxcli device-configurations show --device-id DEVICE_ID

# Filter configurations by key (exact match)
wxcli device-configurations show --device-id DEVICE_ID --key "Conference.MaxReceiveCallRate"

# Filter configurations by wildcard
wxcli device-configurations show --device-id DEVICE_ID --key "Audio.Ultrasound.*"

# Update a configuration value (replace)
wxcli device-configurations update --device-id DEVICE_ID \
  --json-body '[{"op":"replace","path":"Conference.MaxReceiveCallRate/sources/configured/value","value":6000}]'

# Revert a configuration to default (remove)
wxcli device-configurations update --device-id DEVICE_ID \
  --json-body '[{"op":"remove","path":"Audio.Ultrasound.MaxVolume/sources/configured/value"}]'
```

> **Note:** The `show` command name is slightly misleading — it lists all configurations for the device (equivalent to the SDK's `list()` method). The `--key` filter supports absolute paths, wildcards (`*`), and index ranges (`[1..3]`).

---

## 3. TelephonyDevicesApi (Webex Calling Device Management)

**Module:** `wxc_sdk.telephony.devices`

Handles Calling-specific device operations: supported device catalog, device members/lines, line key templates, device layouts, background images, MAC validation, and per-person/per-workspace device settings.

### 3.1 Required Scopes

| Action | Scope |
|--------|-------|
| Read telephony device config | `spark-admin:telephony_config_read` |
| Write telephony device config | `spark-admin:telephony_config_write` |

### 3.2 Data Models

#### Device Catalog

**`SupportedDevice`** -- a single device model from the catalog:

| Field | Type | Notes |
|-------|------|-------|
| `model` | `str` | Model identifier |
| `display_name` | `str` | Display name |
| `family_display_name` | `Optional[str]` | Device family |
| `device_type` | `DeviceType` | Alias `type` in JSON |
| `manufacturer` | `DeviceManufacturer` | `CISCO` or `THIRD_PARTY` |
| `managed_by` | `DeviceManagedBy` | `CISCO`, `CUSTOMER`, or `PARTNER` |
| `supported_for` | `list[UserType]` | Where supported (people, places) |
| `onboarding_method` | `list[OnboardingMethod]` | `MAC_ADDRESS`, `ACTIVATION_CODE`, `NONE` |
| `allow_configure_layout_enabled` | `bool` | Layout configuration support |
| `number_of_line_ports` | `int` | Port/line count |
| `kem_support_enabled` | `bool` | Key Expansion Module support |
| `kem_module_count` | `Optional[int]` | Max KEM modules |
| `kem_module_type` | `Optional[list[str]]` | KEM types supported |
| `number_of_line_key_buttons` | `Optional[int]` | Line key button count |
| `touch_screen_phone` | `Optional[bool]` | Touch screen support |
| `t38_enabled` | `Optional[bool]` | T.38 fax support |
| `device_settings_configuration` | `Optional[DeviceSettingsConfiguration]` | Config mode |
| `supports_log_collection` | `Optional[SupportsLogCollection]` | `NONE`, `CISCO_PRT`, `CISCO_ROOMOS` |

**`SupportedDevices`** -- wrapper:

| Field | Type |
|-------|------|
| `upgrade_channel_list` | `Optional[list[str]]` -- `STABLE`, `STABLE_DELAY`, `PREVIEW`, `BETA`, `TESTING` |
| `devices` | `Optional[list[SupportedDevice]]` |

#### Device Enums

**`DeviceManufacturer`**: `CISCO`, `THIRD_PARTY`

**`DeviceManagedBy`**: `CISCO`, `CUSTOMER`, `PARTNER`

**`OnboardingMethod`**: `MAC_ADDRESS`, `ACTIVATION_CODE`, `NONE`

**`DeviceSettingsConfiguration`**: `WEBEX_CALLING_DEVICE_CONFIGURATION`, `WEBEX_DEVICE_CONFIGURATION`, `WEBEX_CALLING_DYNAMIC_DEVICE_CONFIGURATION`, `NONE`

**`ActivationState`**: `activating`, `activated`, `deactivated`

#### Device Details (Telephony)

**`TelephonyDeviceDetails`**:

| Field | Type | Notes |
|-------|------|-------|
| `manufacturer` | `Optional[str]` | |
| `managed_by` | `Optional[str]` | |
| `id` | `Optional[str]` | |
| `ip` | `Optional[str]` | |
| `mac` | `Optional[str]` | |
| `model` | `Optional[str]` | |
| `activation_state` | `Optional[ActivationState]` | Only for activation-code devices |
| `description` | `Optional[list[str]]` | Tags (comma-separated) |
| `owner` | `Optional[TelephonyDeviceOwner]` | `line_port`, `sip_user_name` |
| `proxy` | `Optional[TelephonyDeviceProxy]` | `outbound_proxy` |

#### Members & Lines

**`DeviceMember`** (extends `MemberCommon`):

| Field | Type | Notes |
|-------|------|-------|
| `member_id` | `str` | Alias `id` |
| `member_type` | `UserType` | Default `people` |
| `first_name` | `Optional[str]` | |
| `last_name` | `Optional[str]` | |
| `phone_number` | `Optional[str]` | |
| `extension` | `Optional[str]` | |
| `line_type` | `PrimaryOrShared` | Default `primary` |
| `primary_owner` | `bool` | Is this the device owner? |
| `port` | `int` | Port number (default 1) |
| `line_weight` | `int` | Number of lines for this member |
| `line_label` | `Optional[str]` | |
| `host_ip` | `Optional[str]` | Registration host IP |
| `remote_ip` | `Optional[str]` | Registration remote IP |
| `hotline_enabled` | `bool` | Auto-dial predefined number |
| `hotline_destination` | `Optional[str]` | Required if hotline enabled |
| `t38_fax_compression_enabled` | `Optional[bool]` | ATA devices only |
| `allow_call_decline_enabled` | `Optional[bool]` | Decline on all endpoints or just current |

**`DeviceMembersResponse`**:

| Field | Type |
|-------|------|
| `model` | `str` |
| `members` | `list[DeviceMember]` (sorted by port) |
| `max_line_count` | `int` |

**`AvailableMember`** -- extends `MemberCommon`, no additional fields.

#### MAC Validation

**`MACState`**: `AVAILABLE`, `UNAVAILABLE`, `DUPLICATE_IN_LIST`, `INVALID`

**`MACStatus`**:

| Field | Type |
|-------|------|
| `mac` | `str` |
| `state` | `MACState` |
| `error_code` | `Optional[int]` |
| `message` | `Optional[str]` |

**`MACValidationResponse`**:

| Field | Type |
|-------|------|
| `status` | `ValidationStatus` |
| `mac_status` | `Optional[list[MACStatus]]` |

#### Line Key Templates & Programmable Line Keys

**`LineKeyType`**: `PRIMARY_LINE`, `SHARED_LINE`, `MONITOR`, `CALL_PARK_EXTENSION`, `SPEED_DIAL`, `OPEN`, `CLOSED`, `MODE_MANAGEMENT`

**`ProgrammableLineKey`**:

| Field | Type | Notes |
|-------|------|-------|
| `line_key_index` | `Optional[int]` | Starting from 1 (leftmost key) |
| `line_key_type` | `Optional[LineKeyType]` | Action for this key |
| `line_key_label` | `Optional[str]` | Only for `SPEED_DIAL` |
| `line_key_value` | `Optional[str]` | Only for `SPEED_DIAL` (phone number, ext, or SIP URI) |
| `shared_line_index` | `Optional[int]` | Only for `SHARED_LINE` |

Helper: `ProgrammableLineKey.standard_plk_list(lines=10)` returns a list with key 1 as `PRIMARY_LINE` and the rest as `OPEN`.

**`LineKeyTemplate`**:

| Field | Type | Notes |
|-------|------|-------|
| `id` | `Optional[str]` | Template ID |
| `template_name` | `Optional[str]` | |
| `device_model` | `Optional[str]` | |
| `display_name` | `Optional[str]` | Alias `modelDisplayName` |
| `user_reorder_enabled` | `Optional[bool]` | |
| `line_keys` | `Optional[list[ProgrammableLineKey]]` | |

#### Device Layout

**`LayoutMode`**: `DEFAULT`, `CUSTOM`

**`KemModuleType`**: `KEM_14_KEYS`, `KEM_18_KEYS`, `KEM_20_KEYS`

**`KemKey`**:

| Field | Type | Notes |
|-------|------|-------|
| `kem_module_index` | `Optional[int]` | Module index (from 1) |
| `kem_key_index` | `Optional[int]` | Key index (from 1) |
| `kem_key_type` | `Optional[LineKeyType]` | Action |
| `kem_key_label` | `Optional[str]` | Only for `SPEED_DIAL` |
| `kem_key_value` | `Optional[str]` | Only for `SPEED_DIAL` |
| `shared_line_index` | `Optional[int]` | Only for `SHARED_LINE` |

**`DeviceLayout`**:

| Field | Type |
|-------|------|
| `layout_mode` | `Optional[LayoutMode]` |
| `user_reorder_enabled` | `Optional[bool]` |
| `line_keys` | `Optional[list[ProgrammableLineKey]]` |
| `kem_module_type` | `Optional[KemModuleType]` |
| `kem_keys` | `Optional[list[KemKey]]` |

#### Device Settings (Compression)

**`DeviceSettings`**:

| Field | Type | Notes |
|-------|------|-------|
| `compression` | `Optional[bool]` | `True` = minimize data use (`ON`), `False` = ignore (`OFF`) |

#### Background Images

**`BackgroundImage`**: `background_image_url`, `file_name`, `count`

**`BackgroundImages`**: `background_images` (list), `count`

**`DeleteImageRequestObject`**: `file_name`, `force_delete` (bool)

#### User Device Count

**`UserDeviceCount`**: `total_device_count`, `applications_count`

### 3.3 Methods

#### Supported Device Catalog

```python
def supported_devices(
    self,
    allow_configure_layout_enabled: bool = None,
    type_: str = None,       # e.g. 'MPP', 'not:MPP'
    org_id: str = None
) -> SupportedDevices
```

Scope: `spark-admin:telephony_config_read`

#### Telephony Device Details

```python
def details(self, device_id: str, org_id: str = None) -> TelephonyDeviceDetails
```

Retrieves third-party device management info (line_port, sip_user_name, outbound_proxy). Not supported for FedRAMP. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

Scope: `spark-admin:telephony_config_read`

#### Update Third-Party Device

```python
def update_third_party_device(
    self, device_id: str, sip_password: str, org_id: str = None
)
```

Modify a 3rd-party device's SIP password. Not supported for FedRAMP. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

Scope: `spark-admin:telephony_config_write`

#### Device Members

```python
def members(self, device_id: str, org_id: str = None) -> DeviceMembersResponse

def update_members(
    self,
    device_id: str,
    members: list[Union[DeviceMember, AvailableMember]] = None,
    org_id: str = None
)

def available_members(
    self,
    device_id: str,
    location_id: str = None,
    member_name: str = None,
    phone_number: str = None,
    extension: str = None,
    usage_type: UsageType = None,   # DEVICE_OWNER or SHARED_LINE
    order: str = None,              # 'lname' or 'fname'
    org_id: str = None,
    **params
) -> Generator[AvailableMember, None, None]

def get_count_of_members(
    self,
    device_id: str,
    member_name: str = None,
    phone_number: str = None,
    location_id: str = None,
    extension: str = None,
    usage_type: UsageType = None,
    org_id: str = None
) -> int

def get_count_of_available_members(
    self,
    member_name: str = None,
    phone_number: str = None,
    location_id: str = None,
    extension: str = None,
    usage_type: UsageType = None,
    exclude_virtual_line: bool = None,
    device_location_id: str = None,
    org_id: str = None
) -> int
```

Note: `update_members` auto-assigns port indices sequentially. If the members list is empty/omitted, all members except the primary user are removed.

#### Apply Changes

```python
def apply_changes(self, device_id: str, org_id: str = None)
```

Issues request to the device to download and apply configuration changes.

Scope: `spark-admin:telephony_config_write`

#### Device-Level Calling Settings

```python
def device_settings(
    self, device_id: str, device_model: str = None, org_id: str = None
) -> DeviceCustomization

def update_device_settings(
    self, device_id: str, device_model: str,
    customization: DeviceCustomization, org_id: str = None
)
```

Lists/updates MPP and ATA device-level settings. DECT devices are not supported. **9800-series phones (9811-9871) return 404** on these device-level settings endpoints — use Device Configurations (RoomOS keys) for per-device config instead. However, 9800-series phones DO support person-level device settings (see below) — the response returns limited fields (e.g., `compression`). After updating, call `apply_changes()` to push to the device.

**Example:**

```python
# Get device settings
settings = api.telephony.devices.device_settings(
    device_id=target_device.device_id,
    device_model=target_device.model
)

# Modify a setting and enable customization
settings.customizations.mpp.display_name_format = DisplayNameSelection.person_last_then_first_name
settings.custom_enabled = True

# Push update
api.telephony.devices.update_device_settings(
    device_id=target_device.device_id,
    device_model=target_device.model,
    customization=settings
)

# Apply to the physical device
api.telephony.devices.apply_changes(device_id=target_device.device_id)
```

#### Person / Workspace Device Settings (Compression)

```python
def get_person_device_settings(self, person_id: str, org_id: str = None) -> DeviceSettings
def update_person_device_settings(self, person_id: str, settings: DeviceSettings, org_id: str = None)
def get_workspace_device_settings(self, workspace_id: str, org_id: str = None) -> DeviceSettings
def update_workspace_device_settings(self, workspace_id: str, settings: DeviceSettings, org_id: str = None)
```

Manage compression setting (`ON`/`OFF`) for a person's or workspace's devices.

#### MAC Validation

```python
def validate_macs(self, macs: list[str], org_id: str = None) -> MACValidationResponse
```

Validate a list of MAC addresses. Returns per-MAC status (`AVAILABLE`, `UNAVAILABLE`, `DUPLICATE_IN_LIST`, `INVALID`).

Scope: `spark-admin:telephony_config_write`

#### Line Key Templates (PLK)

```python
def create_line_key_template(self, template: LineKeyTemplate, org_id: str = None) -> str
def list_line_key_templates(self, org_id: str = None) -> list[LineKeyTemplate]
def line_key_template_details(self, template_id: str, org_id: str = None) -> LineKeyTemplate
def modify_line_key_template(self, template: LineKeyTemplate, org_id: str = None)
def delete_line_key_template(self, template_id: str, org_id: str = None)

def preview_apply_line_key_template(
    self,
    action: ApplyLineKeyTemplateAction,     # APPLY_TEMPLATE or factory reset
    template_id: str = None,                # required for APPLY_TEMPLATE
    location_ids: list[str] = None,
    exclude_devices_with_custom_layout: bool = None,
    include_device_tags: list[str] = None,
    exclude_device_tags: list[str] = None,
    advisory_types: LineKeyTemplateAdvisoryTypes = None,
    org_id: str = None
) -> int    # returns device count that would be affected
```

#### Device Layout

```python
def get_device_layout(self, device_id: str, org_id: str = None) -> DeviceLayout
def modify_device_layout(self, device_id: str, layout: DeviceLayout, org_id: str = None)
```

Customize PLK and KEM mappings per device.

#### Background Images

```python
def list_background_images(self, org_id: str = None) -> BackgroundImages
def upload_background_image(
    self,
    device_id: str,
    file: Union[BufferedReader, str],    # path or open file handle (binary mode)
    file_name: str = None,               # required if passing a reader
    org_id: str = None
) -> BackgroundImage
def delete_background_images(
    self,
    background_images: list[DeleteImageRequestObject],
    org_id: str = None
) -> DeleteDeviceBackgroundImagesResponse
```

- Max 100 images per org.
- Upload max 625 KB, `.jpeg` or `.png` only.
- Max 10 images per delete request.
- `force_delete=True` clears references from devices/locations/org that use the deleted image.

#### User Device Count

```python
def user_devices_count(self, person_id: str, org_id: str = None) -> UserDeviceCount
```

Returns total device count and application count. Useful for checking device limits (e.g., standard calling license = 1 physical device).

### 3.4 Dynamic Settings Sub-API

**Module:** `wxc_sdk.telephony.devices.dynamic_settings`

Access: `api.telephony.devices.dynamic_settings`

Manages dynamic device settings using a tag-based system with hierarchical inheritance (system default -> regional default -> organization -> location -> device).

#### Dynamic Settings Data Models

**`SettingsType`**: `TABS`, `GROUPS`, `ALL`

**`SettingsGroup`**: `path`, `friendly_name`, `tab`, `family_or_model_display_name`, `tags` (list of `DeviceSettingsGroupTag`)

**`DeviceTag`** (validation schema):

| Field | Type | Notes |
|-------|------|-------|
| `family_or_model_display_name` | `Optional[str]` | |
| `tag` | `Optional[str]` | Unique setting identifier |
| `friendly_name` | `Optional[str]` | Correlates with UI |
| `tooltip` | `Optional[str]` | |
| `alert` | `Optional[str]` | |
| `level` | `Optional[list[str]]` | Levels where configurable |
| `validation_rule` | `Optional[ValidationRule]` | Type, min/max, regex, enum values |

**`ValidationRule`**:

| Field | Type | Notes |
|-------|------|-------|
| `type` | `Optional[str]` | `string`, `integer`, `boolean`, `enum`, `password`, `network` |
| `values` | `Optional[list[str]]` | For `enum` / `boolean` types |
| `min` | `Optional[int]` | Numeric minimum |
| `max_` | `Optional[int]` | Numeric maximum |
| `increment` | `Optional[int]` | Numeric step |
| `regex` | `Optional[str]` | String validation pattern |
| `max_length` | `Optional[int]` | String max length |
| `validation_hint` | `Optional[str]` | User-facing hint |

**`DevicePutItem`** (for updates):

| Field | Type | Notes |
|-------|------|-------|
| `tag` | `Optional[str]` | Setting identifier |
| `action` | `Optional[SetOrClear]` | `SET` or `CLEAR` |
| `value` | `Optional[str]` | Required when action is `SET` |

**`ParentLevel`**: `SYSTEM_DEFAULT`, `REGIONAL_DEFAULT`, `ORGANIZATION`, `LOCATION`

**`DeviceDynamicTag`**: `family_or_model_display_name`, `tag`, `value`, `parent_value`, `parent_level`

**`DeviceDynamicSettings`**: `tags` (list of `DeviceDynamicTag`), `last_update_time`, `update_in_progress`

#### Dynamic Settings Methods

```python
def get_settings_groups(
    self,
    family_or_model_display_name: str = None,
    include_settings_type: SettingsType = None,   # default ALL
    org_id: str = None
) -> DynamicSettingsGroups

def get_validation_schema(
    self,
    family_or_model_display_name: str = None,
    org_id: str = None
) -> list[DeviceTag]

def update_specified_settings_for_the_device(
    self,
    device_id: str,
    tags: list[DevicePutItem] = None,
    org_id: str = None
)

def get_customer_device_settings(
    self,
    family_or_model_display_name: str,
    tags: list[str] = None,
    org_id: str = None
) -> DeviceDynamicSettings

def get_device_settings(
    self,
    device_id: str,
    tags: list[str] = None,
    org_id: str = None
) -> DeviceDynamicSettings

def get_location_device_settings(
    self,
    location_id: str,
    family_or_model_display_name: str,
    tags: list[str] = None,
    org_id: str = None
) -> DeviceDynamicSettings
```

> **Gotcha — `deviceModel` required for settings endpoints:** `GET/PUT .../devices/{id}/settings` requires the `deviceModel` query parameter. Omitting it returns an error.

> **Gotcha — Apply changes after updates:** After updating device settings, members, or layout, call `apply_changes()` (or `.../actions/applyChanges/invoke` via raw HTTP) to push the configuration to the physical device.

> **Gotcha — Background image upload is multipart:** The upload endpoint requires multipart form data, not JSON. Max 625 KB, `.jpeg` or `.png` only. Max 100 images per org. Use the SDK method for file handling rather than raw HTTP.

### 3.5 CLI Examples

Two CLI groups cover this API surface: `wxcli device-settings` (47 commands) and `wxcli device-dynamic-settings` (10 commands).

#### Device Members & Lines (`device-settings`)

```bash
# List members (lines) on a device
wxcli device-settings list DEVICE_ID

# Get count of members on a device
wxcli device-settings show DEVICE_ID

# Search available members to add as shared lines
wxcli device-settings list-available-members DEVICE_ID

# Search available members filtered by name or usage type
wxcli device-settings list-available-members DEVICE_ID --member-name "Jane" --usage-type SHARED_LINE

# Search available members in a specific location
wxcli device-settings list-available-members DEVICE_ID --location-id LOCATION_ID

# Update members on a device (requires --json-body)
wxcli device-settings update DEVICE_ID --json-body '{
  "members": [
    {"id": "PERSON_ID_1", "port": 1, "lineType": "PRIMARY", "primaryOwner": true},
    {"id": "PERSON_ID_2", "port": 2, "lineType": "SHARED_LINE", "primaryOwner": false}
  ]
}'

# Apply configuration changes to the physical device
wxcli device-settings apply-changes-for DEVICE_ID
```

#### Person & Workspace Devices (`device-settings`)

```bash
# List devices assigned to a person
wxcli device-settings list-devices-people PERSON_ID

# List devices assigned to a workspace
wxcli device-settings list-devices-workspaces WORKSPACE_ID

# Get Webex Calling device details (3rd-party device info)
wxcli device-settings show-devices DEVICE_ID

# Get device settings (MPP/ATA customization)
wxcli device-settings show-settings-devices DEVICE_ID

# Get user device count (total devices + applications)
wxcli device-settings show-count-devices PERSON_ID
```

#### Device Layout (`device-settings`)

```bash
# Get device layout (line keys and KEM keys)
wxcli device-settings list-layout DEVICE_ID

# Update device layout (requires --json-body for line key assignments)
wxcli device-settings update-layout DEVICE_ID --json-body '{
  "layoutMode": "CUSTOM",
  "lineKeys": [
    {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
    {"lineKeyIndex": 2, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Lobby", "lineKeyValue": "2000"},
    {"lineKeyIndex": 3, "lineKeyType": "MONITOR"}
  ]
}'

# Enable user reorder on a device layout
wxcli device-settings update-layout DEVICE_ID --user-reorder-enabled
```

#### Line Key Templates (`device-settings`)

```bash
# List all line key templates
wxcli device-settings list-line-key-templates

# Get line key template details
wxcli device-settings show-line-key-templates TEMPLATE_ID

# Apply a line key template to devices
wxcli device-settings create-apply-line-key-template \
  --action APPLY_TEMPLATE --template-id TEMPLATE_ID

# Apply template, excluding devices with custom layouts
wxcli device-settings create-apply-line-key-template \
  --action APPLY_TEMPLATE --template-id TEMPLATE_ID --exclude-devices-with-custom-layout
```

#### MAC Validation (`device-settings`)

```bash
# Validate MAC addresses (requires --json-body)
wxcli device-settings validate-a-list --json-body '{
  "macs": ["AABBCCDDEEFF", "112233445566", "INVALID"]
}'
```

#### Dynamic Device Settings (`device-dynamic-settings`)

```bash
# List supported devices for dynamic settings
wxcli device-dynamic-settings list

# Filter supported devices by type (e.g., MPP phones)
wxcli device-dynamic-settings list --type MPP

# Get settings groups (tabs/groups structure)
wxcli device-dynamic-settings list-settings-groups

# Get settings groups for a specific device model
wxcli device-dynamic-settings list-settings-groups \
  --family-or-model-display-name "Cisco 8845" --include-settings-type ALL

# Get org-level (customer) dynamic settings for a device model
wxcli device-dynamic-settings get-customer-device \
  --json-body '{"familyOrModelDisplayName": "Cisco 8845"}'

# Get location-level dynamic settings
wxcli device-dynamic-settings get-location-device LOCATION_ID \
  --json-body '{"familyOrModelDisplayName": "Cisco 8845"}'

# Get dynamic settings for a specific device
wxcli device-dynamic-settings get-device-dynamic DEVICE_ID
```

> **Tip:** After updating device members, settings, or layout, always run `wxcli device-settings apply-changes-for DEVICE_ID` to push the configuration to the physical device.

#### Per-Device Softkey PSK Configuration

PSK (Programmable Softkey) slots and softkey state lists are configured via the per-device dynamic settings endpoint. This is separate from the org/location/model-level dynamic settings hierarchy — it applies a specific key-value payload directly to one device.

**Endpoint:**
```
PUT /telephony/config/devices/{device_id}/dynamicSettings
```

**Body:**
```json
{
  "settings": [
    {"key": "softKeyLayout.psk.psk1", "value": "park"},
    {"key": "softKeyLayout.psk.psk2", "value": "hold"},
    {"key": "softKeyLayout.softKeyMenu.idleKeyList", "value": "redial;newcall;cfwd"},
    {"key": "softKeyLayout.softKeyMenu.connectedKeyList", "value": "hold;endcall;xfer"}
  ]
}
```

**Key format:**
- PSK slot: `softKeyLayout.psk.{slot}` where `{slot}` is the slot name **lowercased** (e.g., `PSK1` → `psk1`)
- State key list: `softKeyLayout.softKeyMenu.{state}KeyList` where `{state}` is the Webex state name

**CUCM call state → Webex state name mapping:**

| CUCM state | Webex state | Resulting key |
|------------|-------------|---------------|
| `onHook` | `idle` | `idleKeyList` |
| `offHook` | `offHook` | `offHookKeyList` |
| `ringIn` | `ringing` | `ringingKeyList` |
| `ringOut` | `progressing` | `progressingKeyList` |
| `connected` | `connected` | `connectedKeyList` |
| `onHold` | `hold` | `holdKeyList` |
| `sharedActive` | `sharedActive` | `sharedActiveKeyList` |
| `sharedHeld` | `sharedHeld` | `sharedHeldKeyList` |
| `connectedTransfer` | `startTransfer` | `startTransferKeyList` |
| `connectedConference` | `startConference` | `startConferenceKeyList` |

**State key list value:** Semicolon-separated keyword strings, e.g., `"redial;newcall;cfwd;dnd"`.

> **Gotcha — `progressingKeyList` not `processingKeyList`:** The Webex API state for CUCM's `ringOut` is `progressing`, producing the key `softKeyLayout.softKeyMenu.progressingKeyList`. Using `processing` silently produces a wrong key that the API ignores.

> **Always call applyChanges after PUT dynamicSettings.** The config is not pushed to the physical device until `POST /telephony/config/devices/{device_id}/actions/applyChanges/invoke` is called.

**wxcli:** `wxcli device-dynamic-settings` commands operate at org/location/model scope. Per-device PSK config must be done via `--json-body` with the raw HTTP pattern above.

#### Beta: Dynamic Settings Validation Schema

> **Beta API** — May change without notice.

- `GET /telephony/config/devices/dynamicSettings/validationSchema` — Returns the JSON schema used to validate device dynamic settings payloads. Useful for building validation into provisioning tools before submitting device config changes.

---

## 4. Code Examples

### 4.1 List Room Devices and Their Workspaces

From `examples/room_devices.py` -- uses async API to correlate devices with workspaces, locations, and phone numbers.

```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi
from wxc_sdk.devices import Device

async def list_room_devices(tokens):
    async with AsWebexSimpleApi(tokens=tokens) as api:
        # Get workspaces, numbers, and room/desk devices concurrently
        workspaces, numbers, devices = await asyncio.gather(
            api.workspaces.list(),
            api.telephony.phone_numbers(owner_type=OwnerType.place),
            api.devices.list(product_type='roomdesk'),
        )

        # Filter to workspace-associated devices only
        devices = [d for d in devices if d.workspace_id is not None]

        for device in devices:
            print(f'{device.display_name} - {device.product} ({device.connection_status})')
```

### 4.2 Find Calling Users Without Devices

From `examples/users_wo_devices.py` -- identifies calling users who have no physical device assigned.

```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi

async def find_users_without_devices(tokens):
    async with AsWebexSimpleApi(tokens=tokens) as api:
        # Get calling users (those with a location_id)
        calling_users = [user for user in await api.people.list(calling_data=True)
                         if user.location_id]

        # Fetch device info for all users concurrently
        user_device_infos = await asyncio.gather(
            *[api.person_settings.devices(person_id=user.person_id)
              for user in calling_users]
        )

        # Users with no devices at all
        users_wo_devices = [
            user for user, info in zip(calling_users, user_device_infos)
            if not info.devices
        ]

        print(f'{len(users_wo_devices)} users without devices:')
        for user in sorted(users_wo_devices, key=lambda u: u.display_name):
            print(f'  {user.display_name} ({user.emails[0]})')
```

### 4.3 Create Device by MAC Address

```python
device = api.devices.create_by_mac_address(
    mac='AABBCCDDEEFF',
    workspace_id='WORKSPACE_ID',
    model='DMS Cisco 8845',
    password='sip_password_here'   # only for 3rd-party devices
)
if device:
    print(f'Created: {device.display_name} ({device.device_id})')
```

### 4.4 Generate Activation Code

```python
# For a RoomOS device (no model needed)
response = api.devices.activation_code(workspace_id='WORKSPACE_ID')
print(f'Code: {response.code}, Expires: {response.expiry_time}')

# For a phone (model required)
supported = api.telephony.devices.supported_devices()
phone_model = next(d.model for d in supported.devices if 'Cisco 8845' in d.display_name)
response = api.devices.activation_code(workspace_id='WORKSPACE_ID', model=phone_model)
```

### 4.5 Manage Device Tags

```python
from wxc_sdk.devices import TagOp

# Add tags
device = api.devices.modify_device_tags(
    device_id='DEVICE_ID',
    op=TagOp.add,
    value=['floor-3', 'conference-room']
)

# Replace all tags
device = api.devices.modify_device_tags(
    device_id='DEVICE_ID',
    op=TagOp.replace,
    value=['new-tag-set']
)

# Remove all tags
device = api.devices.modify_device_tags(
    device_id='DEVICE_ID',
    op=TagOp.remove
)
```

### 4.6 Validate MAC Addresses

```python
result = api.telephony.devices.validate_macs(
    macs=['AABBCCDDEEFF', '112233445566', 'INVALID']
)
for mac_status in result.mac_status:
    print(f'{mac_status.mac}: {mac_status.state}')
    # AABBCCDDEEFF: AVAILABLE
    # 112233445566: UNAVAILABLE
    # INVALID: INVALID
```

### 4.7 Manage Device Members (Lines)

```python
# Get current members
response = api.telephony.devices.members(device_id='DEVICE_ID')
print(f'Model: {response.model}, Max lines: {response.max_line_count}')
for member in response.members:
    print(f'  Port {member.port}: {member.first_name} {member.last_name} '
          f'({"primary" if member.primary_owner else "shared"})')

# Search available members
available = list(api.telephony.devices.available_members(
    device_id='DEVICE_ID',
    usage_type=UsageType.SHARED_LINE
))

# Update members: add a shared line appearance
existing = response.members
existing.append(DeviceMember.from_available(available[0]))
api.telephony.devices.update_members(device_id='DEVICE_ID', members=existing)
```

### 4.8 Update Device Layout with Line Key Template

```python
# List available templates
templates = api.telephony.devices.list_line_key_templates()
for t in templates:
    print(f'{t.template_name} ({t.device_model})')

# Preview how many devices would be affected
count = api.telephony.devices.preview_apply_line_key_template(
    action=ApplyLineKeyTemplateAction.APPLY_TEMPLATE,
    template_id=templates[0].id
)
print(f'{count} devices would be affected')
```

---

## 5. API Relationship Summary

```
WebexSimpleApi
  .devices                          -> DevicesApi           (cloud CRUD, tags, activation)
  .device_configurations            -> DeviceConfigurationsApi (RoomOS key-value configs)
  .telephony.devices                -> TelephonyDevicesApi  (calling-specific management)
     .dynamic_settings              -> DevicesDynamicSettingsApi (tag-based dynamic config)
     .settings_jobs                 -> DeviceSettingsJobsApi (bulk jobs, via DevicesApi)
```

**Key distinction:** `DevicesApi` handles the device as a cloud entity (create, delete, activate, tag). `DeviceConfigurationsApi` handles RoomOS-level configs. `TelephonyDevicesApi` handles everything Webex Calling needs: line assignments, phone layouts, supported models, and calling-specific settings.

---

### 5a. Device Settings API Router

Before attempting to read or change device-level settings, determine which API surface the device uses. The wrong API returns 400 — there is no fallback or auto-detection.

#### Quick router (by model family)

| Model Family | Product Type | Settings API | CLI Group |
|-------------|-------------|-------------|-----------|
| MPP 68xx (6821, 6841, 6851, 6861) | `phone` | Telephony Device Settings | `device-settings` |
| MPP 78xx (7811, 7821, 7832, 7841, 7861) | `phone` | Telephony Device Settings | `device-settings` |
| MPP 88xx (8811, 8841, 8845, 8851, 8861, 8865) | `phone` | Telephony Device Settings | `device-settings` |
| ATA 191/192 | `phone` | Telephony Device Settings | `device-settings` |
| **9800-series (9811, 9821, 9841, 9851, 9861, 9871)** | **`phone`** | **Device Configurations (RoomOS keys)** | **`device-configurations`** |
| Room series (Room Kit, Room Bar, etc.) | `roomdesk` | Device Configurations (RoomOS keys) | `device-configurations` |
| Board series (Board 55, Board Pro, etc.) | `roomdesk` | Device Configurations (RoomOS keys) | `device-configurations` |
| Desk series (Desk, Desk Pro, Desk Mini) | `roomdesk` | Device Configurations (RoomOS keys) | `device-configurations` |
| 3rd-party SIP | `phone` | None | CRUD only (`devices`) |

**The 9800-series is the exception that breaks assumptions.** They are `productType: phone` but run PhoneOS (RoomOS-derived) and use RoomOS config keys, not the telephony device settings model. Treating all phones as `device-settings` targets will fail on 9800-series devices.

**9800-series nuances:**
- **Per-device config:** Device Configurations (RoomOS keys) via `device-configurations` -- CONFIRMED working.
- **Line Key Templates:** 9800-series DOES support Line Key Templates (model string `"Cisco 9861"` etc.) via the same `device-settings` LKT endpoints as MPP. This is the one `device-settings` feature that works for 9800-series.
- **Device-level settings:** `show-settings-devices` returns **404** for 9800-series -- CONFIRMED.
- **Person-level device settings:** `get-person-device-settings` works but returns **limited fields** (e.g., `compression`) -- CONFIRMED.

#### Programmatic detection

If the model is unknown or you want to be safe, query the telephony device details and check the `deviceSettingsConfigurationModelId` field:

1. Get the device's telephony details to find its model info:
   ```bash
   wxcli device-settings list-supported-devices --output json
   ```
   Each supported device model includes `deviceSettingsConfiguration`: one of `WEBEX_CALLING_DEVICE_CONFIGURATION`, `WEBEX_DEVICE_CONFIGURATION`, `WEBEX_CALLING_DYNAMIC_DEVICE_CONFIGURATION`, or `NONE`.

2. Match the device's `model` to the supported devices list and read its `deviceSettingsConfiguration` value.

3. Route to the correct API surface using the enum mapping table above.

#### Key differences between API surfaces

| Aspect | `device-settings` | `device-dynamic-settings` | `device-configurations` |
|--------|-------------------|---------------------------|------------------------|
| Config model | Fixed schema per model | Tag-based, model-specific | RoomOS key-value pairs |
| Read | `show-settings-devices DEVICE_ID --device-model "DMS Cisco 8845"` | `get-device-dynamic DEVICE_ID` | `show --device-id DEVICE_ID` |
| Update | `update-settings-devices DEVICE_ID --json-body '{...}'` | `update-device-dynamic DEVICE_ID --json-body '{...}'` | `update --device-id DEVICE_ID --json-body '[...]'` (JSON Patch) |
| Apply changes | **Required:** `apply-changes-for DEVICE_ID` | Not needed | Not needed (auto-applies on resync) |
| Content-Type | `application/json` | `application/json` | `application/json-patch+json` (PATCH) |
| Filtering | N/A (fixed schema) | N/A | `--key "Phone.Multicast*"` (supports wildcards) |
| Scopes | `spark-admin:telephony_config_read/write` | `spark-admin:telephony_config_read/write` | `spark-admin:devices_read/write` |

---

## 6. Raw HTTP

All examples use:

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"
```

No auto-pagination -- pass `max=1000` explicitly. All responses are JSON dicts. Errors raise `RestError`.

### 6.1 DevicesApi (Cloud CRUD)

#### List devices

```python
result = api.session.rest_get(f"{BASE}/devices", params={
    "max": 1000,
    "productType": "phone",           # optional: "phone" or "roomdesk"
    "connectionStatus": "connected",  # optional
    "locationId": loc_id,             # optional
    "tag": "floor-3,building-a",      # optional: comma-separated (AND logic)
})
items = result.get("items", [])
# Each item: {id, displayName, product, type, mac, ip, serial, connectionStatus, personId, workspaceId, locationId, ...}
```

#### Get device details

```python
result = api.session.rest_get(f"{BASE}/devices/{device_id}")
# Returns full device object: {id, displayName, product, type, mac, serial, connectionStatus, tags, ...}
```

#### Delete device

```python
api.session.rest_delete(f"{BASE}/devices/{device_id}")
# Returns 204 No Content
```

#### Generate activation code

```python
body = {"workspaceId": workspace_id}  # or {"personId": person_id, "model": "DMS Cisco 8845"}
result = api.session.rest_post(f"{BASE}/devices/activationCode", json=body)
# Returns: {code, expiryTime}
```

#### Create device by MAC address

```python
body = {
    "mac": "AABBCCDDEEFF",
    "workspaceId": workspace_id,  # or "personId"
    "model": "DMS Cisco 8845",
    "password": "sip_password"    # required for 3rd-party devices
}
result = api.session.rest_post(f"{BASE}/devices", json=body)
# Returns device object or empty on some models
```

#### Modify device tags

```python
import requests
body = [{"op": "add", "path": "tags", "value": ["floor-3", "building-a"]}]
# Note: requires Content-Type: application/json-patch+json
# The SDK's rest_patch handles this; for raw HTTP use:
api.session.rest_patch(f"{BASE}/devices/{device_id}", json=body)
```

### 6.2 TelephonyDevicesApi (Calling-Specific)

#### Supported devices catalog

```python
result = api.session.rest_get(f"{BASE}/telephony/config/supportedDevices")
devices = result.get("devices", [])
# Each: {model, displayName, familyDisplayName, type, manufacturer, managedBy, supportedFor, onboardingMethod, numberOfLinePorts, ...}
```

#### Get telephony device details (3rd-party)

```python
result = api.session.rest_get(f"{BASE}/telephony/config/devices/{device_id}")
# Returns: {manufacturer, managedBy, id, ip, mac, model, activationState, owner: {linePort, sipUserName}, proxy: {outboundProxy}}
```

#### Update 3rd-party device SIP password

```python
api.session.rest_put(f"{BASE}/telephony/config/devices/{device_id}", json={
    "sipPassword": "new_password"
})
```

#### Get device members (lines)

```python
result = api.session.rest_get(f"{BASE}/telephony/config/devices/{device_id}/members")
members = result.get("members", [])
# Each: {id, firstName, lastName, phoneNumber, extension, port, lineType, primaryOwner, lineWeight, hotlineEnabled, ...}
# Also: result["model"], result["maxLineCount"]
```

#### Update device members

```python
body = {
    "members": [
        {"id": person_id, "port": 1, "lineType": "PRIMARY", "primaryOwner": True},
        {"id": shared_person_id, "port": 2, "lineType": "SHARED_LINE", "primaryOwner": False}
    ]
}
api.session.rest_put(f"{BASE}/telephony/config/devices/{device_id}/members", json=body)
```

#### Search available members for a device

```python
result = api.session.rest_get(f"{BASE}/telephony/config/devices/{device_id}/availableMembers", params={
    "max": 1000,
    "memberName": "Jane",        # optional: contains-match
    "usageType": "SHARED_LINE",  # optional: DEVICE_OWNER or SHARED_LINE
    "locationId": loc_id,        # optional
})
members = result.get("members", [])
```

#### Count members / available members

```python
# Count of current members (filtered)
result = api.session.rest_get(f"{BASE}/telephony/config/devices/{device_id}/availableMembers/count", params={
    "memberName": "Jane"
})
count = result.get("count", 0)

# Count of available members (org-wide, no device_id)
result = api.session.rest_get(f"{BASE}/telephony/config/devices/availableMembers/count")
count = result.get("count", 0)
```

#### Apply changes (push config to device)

```python
api.session.rest_post(f"{BASE}/telephony/config/devices/{device_id}/actions/applyChanges/invoke")
# Returns 204. Device downloads and applies configuration.
```

#### Get device settings (MPP/ATA)

```python
result = api.session.rest_get(f"{BASE}/telephony/config/devices/{device_id}/settings", params={
    "deviceModel": "DMS Cisco 8845"  # required
})
# Returns: {customEnabled, customizations: {mpp: {...}, ata: {...}}}
```

#### Update device settings

```python
body = {"customEnabled": True, "customizations": {"mpp": {"displayNameFormat": "PERSON_LAST_THEN_FIRST_NAME"}}}
api.session.rest_put(f"{BASE}/telephony/config/devices/{device_id}/settings", json=body)
# Follow with apply_changes to push to device
```

#### Get/update location device settings

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{location_id}/devices/settings")
# Returns location-level device customization defaults
```

#### Get/update org-level device settings

```python
result = api.session.rest_get(f"{BASE}/telephony/config/devices/settings")
# Returns org-level device customization defaults
```

#### Person device settings (compression)

```python
# Get
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/devices/settings")
# Returns: {compression: true/false}

# Update
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/devices/settings", json={
    "compression": True
})
```

#### Workspace device settings (compression)

```python
# Get
result = api.session.rest_get(f"{BASE}/telephony/config/workspaces/{workspace_id}/devices/settings")

# Update
api.session.rest_put(f"{BASE}/telephony/config/workspaces/{workspace_id}/devices/settings", json={
    "compression": True
})
```

#### List person's devices

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/devices")
devices = result.get("devices", [])
```

#### Get person hoteling settings

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/devices/settings/hoteling")
# Returns: {enabled, limitGuestUse, ...}
```

#### List workspace devices

```python
result = api.session.rest_get(f"{BASE}/telephony/config/workspaces/{workspace_id}/devices")
devices = result.get("devices", [])
```

#### Modify workspace devices

```python
body = {"devices": [{"activationId": activation_id, "model": "DMS Cisco 8845"}]}
api.session.rest_put(f"{BASE}/telephony/config/workspaces/{workspace_id}/devices", json=body)
```

#### User device count

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/devices/count")
# Returns: {totalDeviceCount, applicationsCount}
```

#### Validate MAC addresses

```python
body = {"macs": ["AABBCCDDEEFF", "112233445566"]}
result = api.session.rest_post(f"{BASE}/telephony/config/devices/actions/validateMacs/invoke", json=body)
mac_statuses = result.get("macStatus", [])
# Each: {mac, state, errorCode, message}
# state: AVAILABLE, UNAVAILABLE, DUPLICATE_IN_LIST, INVALID
```

### 6.3 Line Key Templates

#### CRUD

```python
# List
result = api.session.rest_get(f"{BASE}/telephony/config/devices/lineKeyTemplates")
templates = result.get("lineKeyTemplates", [])

# Create
body = {
    "templateName": "Standard Layout",
    "deviceModel": "DMS Cisco 8845",  # MPP: "DMS Cisco XXXX"; 9800-series: "Cisco 98XX" (no "DMS" prefix)
    "lineKeys": [
        {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
        {"lineKeyIndex": 2, "lineKeyType": "MONITOR"},
        {"lineKeyIndex": 3, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Front Desk", "lineKeyValue": "1000"}
    ]
}
result = api.session.rest_post(f"{BASE}/telephony/config/devices/lineKeyTemplates", json=body)
template_id = result.get("id")

# 9800-series example — note no "DMS" prefix in model string
body_9800 = {
    "templateName": "9861 Standard Layout",
    "deviceModel": "Cisco 9861",
    "lineKeys": [
        {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
        {"lineKeyIndex": 2, "lineKeyType": "MONITOR"},
        {"lineKeyIndex": 3, "lineKeyType": "OPEN"}
    ]
}
result = api.session.rest_post(f"{BASE}/telephony/config/devices/lineKeyTemplates", json=body_9800)

# Get details
result = api.session.rest_get(f"{BASE}/telephony/config/devices/lineKeyTemplates/{template_id}")

# Update
api.session.rest_put(f"{BASE}/telephony/config/devices/lineKeyTemplates/{template_id}", json=body)

# Delete
api.session.rest_delete(f"{BASE}/telephony/config/devices/lineKeyTemplates/{template_id}")
```

#### Preview apply template

```python
body = {
    "action": "APPLY_TEMPLATE",
    "templateId": template_id,
    "locationIds": [loc_id],
    "excludeDevicesWithCustomLayout": True
}
result = api.session.rest_post(f"{BASE}/telephony/config/devices/actions/previewApplyLineKeyTemplate/invoke", json=body)
# Returns: {deviceCount}
```

#### Apply template job

```python
# Start job
result = api.session.rest_post(f"{BASE}/telephony/config/jobs/devices/applyLineKeyTemplate", json=body)
job_id = result.get("id")

# List jobs
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/applyLineKeyTemplate")

# Get job status
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/applyLineKeyTemplate/{job_id}")

# Get job errors
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/applyLineKeyTemplate/{job_id}/errors")
```

### 6.4 Device Layout

```python
# Get layout
result = api.session.rest_get(f"{BASE}/telephony/config/devices/{device_id}/layout")
# Returns: {layoutMode, userReorderEnabled, lineKeys: [...], kemModuleType, kemKeys: [...]}

# Update layout
body = {
    "layoutMode": "CUSTOM",
    "lineKeys": [
        {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
        {"lineKeyIndex": 2, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Lobby", "lineKeyValue": "2000"}
    ],
    "kemModuleType": "KEM_14_KEYS",
    "kemKeys": [
        {"kemModuleIndex": 1, "kemKeyIndex": 1, "kemKeyType": "MONITOR"}
    ]
}
api.session.rest_put(f"{BASE}/telephony/config/devices/{device_id}/layout", json=body)
```

### 6.5 Background Images

```python
# List org images
result = api.session.rest_get(f"{BASE}/telephony/config/devices/backgroundImages")
images = result.get("backgroundImages", [])
# Each: {backgroundImageUrl, fileName, count}

# Upload (multipart)
api.session.rest_post(f"{BASE}/telephony/config/devices/{device_id}/actions/backgroundImageUpload/invoke",
    # Requires multipart form upload -- use SDK method for file handling
)

# Delete
body = {"backgroundImages": [{"fileName": "logo.png", "forceDelete": True}]}
api.session.rest_delete(f"{BASE}/telephony/config/devices/backgroundImages", json=body)
```

### 6.6 Device Settings Jobs (Bulk)

```python
# Start bulk device settings job
result = api.session.rest_post(f"{BASE}/telephony/config/jobs/devices/callDeviceSettings", json=body)
job_id = result.get("id")

# List jobs
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/callDeviceSettings")

# Get job status
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/{job_id}")

# Get job errors
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/{job_id}/errors")
```

### 6.7 Rebuild Phones Jobs

```python
# Start rebuild job
result = api.session.rest_post(f"{BASE}/telephony/config/jobs/devices/rebuildPhones", json=body)
job_id = result.get("id")

# List jobs
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/rebuildPhones")

# Get job status
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/rebuildPhones/{job_id}")

# Get job errors
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/devices/rebuildPhones/{job_id}/errors")
```

### 6.8 DECT Supported Devices (via device-call-settings)

```python
# Two endpoints exist for DECT supported device types:
result = api.session.rest_get(f"{BASE}/telephony/config/devices/dects/supportedDevices")
result = api.session.rest_get(f"{BASE}/telephony/config/devices/dectNetworks/supportedDevices")
# Both return: {devices: [{model, displayName, numberOfBasestations, numberOfLinePorts, numberOfRegistrationsSupported}]}
```

---

## 7. Gotchas

1. **`{BASE}/devices` vs `{BASE}/telephony/config/devices`** — These are two different API surfaces. The former manages cloud device entities (CRUD, tags, activation). The latter manages Webex Calling config (members, settings, layout, line keys).
2. **Device IDs differ between surfaces.** A device's `id` from `GET /devices` may differ from its telephony `callingDeviceId`. Use `callingDeviceId` for telephony config endpoints.
3. **`deviceModel` query param is required** for `GET/PUT .../devices/{id}/settings`. Omitting it returns an error.
4. **Apply changes after settings updates.** After updating device settings, members, or layout, call `.../actions/applyChanges/invoke` to push the config to the physical device.
5. **Background image upload is multipart.** The upload endpoint requires multipart form data, not JSON. Max 625 KB, `.jpeg` or `.png` only.
6. **Tags PATCH uses `application/json-patch+json`** content type, not standard JSON. The `rest_patch` method handles this.
7. **No auto-pagination.** Pass `max=1000` on list endpoints. The `rest_get` method does not auto-paginate like SDK generator methods do.
8. **CTI Route Point protocol varies by device pool.** CTI Route Points require SCCP protocol on some device pools — SIP protocol assignment fails with "Device Protocol not valid" error. When creating CTI Route Points via AXL, try SCCP first if SIP fails, or verify the device pool's supported protocols before assignment.
9. **Org/location device settings PUT affects all matching devices on next sync. No rollback.** The PUT to `/telephony/config/locations/{id}/devices/settings` immediately queues the settings for all devices at that location. There is no way to preview or roll back.
10. **9800-series model string format differs from older MPP.** Older MPP phones use `"DMS Cisco 8845"` (with "DMS" prefix); 9800-series phones use `"Cisco 9861"` (no "DMS" prefix). Using the wrong format for Line Key Templates or device creation will fail. Check `list-supported-devices` output for the exact `model` string.
11. **9800-series device settings are split across API surfaces.** Device-level settings (`show-settings-devices`) returns 404. Per-device config uses Device Configurations (RoomOS keys). Person-level device settings (`get-person-device-settings`) works but returns limited fields (e.g., `compression`). Line Key Templates work normally via the `device-settings` LKT endpoints. This makes 9800-series the only phone family that spans three API surfaces.

---

## Bulk Device Jobs

Four bulk job endpoints replace hundreds of per-device API calls with a
single job submission. Used by the CUCM migration engine when the device
count meets `bulk_device_threshold` (see the tuning reference).

### Apply Line Key Template

```
POST /v1/telephony/config/jobs/devices/applyLineKeyTemplate
Scope: spark-admin:telephony_config_write
```

Body: `{"action": "APPLY_TEMPLATE", "templateId": "...", "locationIds": ["...", ...]}`
Also accepts `excludeDevicesWithCustomLayout`, `includeDeviceTags`, `excludeDeviceTags`, and `advisoryTypes`.

Response 202: `{"id": "JOB_ID", "latestExecutionStatus": "STARTING", ...}`

### Change Device Settings

```
POST /v1/telephony/config/jobs/devices/callDeviceSettings
```

Body: `{"locationId": "...", "locationCustomizationsEnabled": true, "customizations": {"mpp": {...}, "ata": {...}, "dect": {...}}}`

**Constraint:** one job per customer per org at a time — 409 if another is running.

### Rebuild Phones

```
POST /v1/telephony/config/jobs/devices/rebuildPhones
```

Body: `{"locationId": "..."}`

**Not supported for Webex for Government.**

### Update Dynamic Device Settings

```
POST /v1/telephony/config/jobs/devices/dynamicDeviceSettings
```

Body: `{"locationId": "", "tags": [{"familyOrModelDisplayName": "Cisco 9861", "tag": "%SOFTKEY_LAYOUT_PSK1%", "action": "SET", "value": "fnc=sd;ext=1234"}]}`

**Constraint:** cannot run in parallel with callDeviceSettings or rebuildPhones on the same org.

### Job Status & Errors

All four jobs share polling endpoints:

```
GET /v1/telephony/config/jobs/devices/{jobType}/{jobId}
GET /v1/telephony/config/jobs/devices/{jobType}/{jobId}/errors
GET /v1/telephony/config/jobs/devices/{jobType}
```

Where `{jobType}` is `applyLineKeyTemplate`, `callDeviceSettings`, `dynamicDeviceSettings`, or `rebuildPhones`.

**Job status lifecycle:** STARTING → STARTED → COMPLETED (exitCode COMPLETED or FAILED).

### Bulk Job Gotchas

- **One-job-at-a-time.** `callDeviceSettings`, `dynamicDeviceSettings`, and `rebuildPhones` return 409 if another of the same family is already running in the org. The CUCM migration engine serializes all four in a single tier to avoid this.
- **Partial failures are common at scale.** The errors endpoint returns per-device failures (`{itemId, trackingId, error: {key, message}}`). The migration engine auto-falls-back to per-device handlers for failed items — other consumers should implement similar logic.
- **FedRAMP.** `rebuildPhones` is explicitly unsupported for Webex for Government.
- **`locationId` semantics for `dynamicDeviceSettings`.** Empty string means org-wide; any non-empty value scopes to a single location. Omitting the key is an error.

---

## See Also

- **[devices-dect.md](devices-dect.md)** — DECT network, base station, and handset management. DECT devices are excluded from `device_settings` / `update_device_settings` in this doc; DECT-specific management lives there.
- **[devices-workspaces.md](devices-workspaces.md)** — Workspace creation and calling settings, including device association with workspaces, activation codes for workspace devices, and workspace-level device compression settings.
