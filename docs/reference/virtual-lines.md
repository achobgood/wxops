# Virtual Lines & Virtual Extensions

## Overview

Webex Calling provides two distinct "virtual" constructs for phone number/extension management:

| Concept | What It Is | Primary Use Case |
|---------|-----------|-----------------|
| **Virtual Line** | A fully-featured phone line not tied to a physical user | Shared department lines, lobby phones, general-purpose numbers that need call settings (voicemail, forwarding, recording, etc.) |
| **Virtual Extension** | An extension that maps to an external phone number | Simplified dialing to remote workers or frequently-called external numbers on a separate telephony system |

These are **not interchangeable**. A virtual line lives inside Webex Calling with its own call settings. A virtual extension is a routing alias that forwards to an external PSTN number.

---

## Virtual Lines

### What They Are

A virtual line is a phone line within Webex Calling that is not assigned to a specific person. It has its own phone number and/or extension, and supports the full range of call settings that a person line does (voicemail, call forwarding, call recording, caller ID, etc.).

**Common use cases:**
- Shared department lines (e.g., `+1-555-SALES` rings a group)
- Lobby or front-desk phones
- Lines assigned to devices in common areas that need independent call handling
- Overflow or backup lines with their own voicemail

**Key characteristics:**
- Must be created within a specific location
- Can have a phone number, an extension, or both (at least one is required)
- Can be assigned to physical devices (phones, DECT handsets)
- Supports all person-level call settings (voicemail, forwarding, DND, etc.)
- Appears in directory search (configurable)
- Has its own caller ID settings
- Has its own time zone and announcement language

### SDK Access

```python
# Virtual Lines API is at:
api = wxc_api.telephony.virtual_lines  # VirtualLinesApi instance
```

Base path: `telephony/config/virtualLines`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

### CRUD Operations

#### List Virtual Lines

```python
VirtualLinesApi.list(
    org_id: str = None,
    location_id: list[str] = None,       # Filter by location IDs
    id: list[str] = None,                 # Filter by virtual line IDs
    owner_name: list[str] = None,         # Filter by owner name
    phone_number: list[str] = None,       # Filter by phone number
    location_name: list[str] = None,      # Filter by location name
    order: list[str] = None,              # Sort order (max 3 fields)
    has_device_assigned: bool = None,      # Only with/without devices
    has_extension_assigned: bool = None,   # Only with/without extension
    has_dn_assigned: bool = None,          # Only with/without directory number
) -> Generator[VirtualLine, None, None]
```

Returns a paginated generator of `VirtualLine` objects. Supports multiple filter values per parameter (e.g., multiple `location_id` values).

**Example:**
```python
# List all virtual lines at a location
for vl in api.telephony.virtual_lines.list(location_id=["loc_id_123"]):
    print(f"{vl.display_name}: {vl.number}")
```

#### Create Virtual Line

```python
VirtualLinesApi.create(
    first_name: str,                      # Required, 1-30 chars
    last_name: str,                       # Required, 1-30 chars
    location_id: str,                     # Required
    display_name: str = None,
    phone_number: str = None,             # 1-23 chars; phone_number OR extension required
    extension: str = None,                # 2-10 chars; phone_number OR extension required
    caller_id_last_name: str = None,      # 1-30 chars
    caller_id_first_name: str = None,     # 1-30 chars
    caller_id_number: str = None,         # 1-23 chars
    org_id: str = None,
) -> str  # Returns the new virtual line ID
```

At least one of `phone_number` or `extension` must be provided.

**Example:**
```python
vl_id = api.telephony.virtual_lines.create(
    first_name="Sales",
    last_name="Line",
    location_id="loc_id_123",
    extension="8500",
    phone_number="+15551234567"
)
```

#### Get Virtual Line Details

```python
VirtualLinesApi.details(
    virtual_line_id: str,                 # Required
    org_id: str = None,
) -> VirtualLine
```

Returns the full `VirtualLine` object including location, number, devices, caller ID, time zone, and announcement language.

#### Update Virtual Line

```python
VirtualLinesApi.update(
    virtual_line_id: str,                 # Required
    first_name: str = None,
    last_name: str = None,
    display_name: str = None,
    phone_number: str = None,
    extension: str = None,
    announcement_language: str = None,
    caller_id_last_name: str = None,
    caller_id_first_name: str = None,
    caller_id_number: str = None,
    time_zone: str = None,
    org_id: str = None,
) -> None
```

Only include fields you want to change. Omitted fields are not modified.

#### Delete Virtual Line

```python
VirtualLinesApi.delete(
    virtual_line_id: str,                 # Required
    org_id: str = None,
) -> None
```

### Additional Virtual Line Operations

#### Get Phone Number

```python
VirtualLinesApi.get_phone_number(
    virtual_line_id: str,
    org_id: str = None,
) -> VirtualLineNumberPhoneNumber
```

Returns the `direct_number`, `extension`, and `primary` flag for the assigned phone number.

#### Update Directory Search

```python
VirtualLinesApi.update_directory_search(
    virtual_line_id: str,
    enabled: bool,                        # Whether the virtual line appears in directory search
    org_id: str = None,
) -> None
```

#### Get Assigned Devices

```python
VirtualLinesApi.assigned_devices(
    virtual_line_id: str,
    org_id: str = None,
) -> VirtualLineDevices
```

Returns the list of devices assigned to the virtual line, the available endpoint type (`PrimaryOrShared`), and the maximum device count.

#### Get DECT Network Handsets

```python
VirtualLinesApi.dect_networks(
    virtual_line_id: str,
    org_id: str = None,
) -> list[AssignedDectNetwork]
```

Returns DECT network handset assignments for the virtual line.

### Virtual Line Call Settings

Virtual lines support the same call settings as person lines. Each is accessed as a sub-API on the `VirtualLinesApi` instance:

| Sub-API | Attribute | What It Controls |
|---------|-----------|-----------------|
| `AgentCallerIdApi` | `.agent_caller_id` | Caller ID when acting as a call queue/hunt group agent |
| `AvailableNumbersApi` | `.available_numbers` | List available numbers for assignment |
| `BargeApi` | `.barge` | Barge-in settings |
| `CallBridgeApi` | `.call_bridge` | Call bridge settings |
| `CallInterceptApi` | `.call_intercept` | Call intercept (redirect/block incoming calls) |
| `CallRecordingApi` | `.call_recording` | Call recording settings |
| `CallWaitingApi` | `.call_waiting` | Call waiting settings |
| `CallerIdApi` | `.caller_id` | Outbound caller ID configuration |
| `DndApi` | `.dnd` | Do Not Disturb settings |
| `ECBNApi` | `.ecbn` | Emergency callback number |
| `PersonForwardingApi` | `.forwarding` | Call forwarding rules (always, busy, no-answer) |
| `MusicOnHoldApi` | `.music_on_hold` | Music on hold settings |
| `IncomingPermissionsApi` | `.permissions_in` | Incoming call permissions |
| `OutgoingPermissionsApi` | `.permissions_out` | Outgoing call permissions |
| `PrivacyApi` | `.privacy` | Privacy settings |
| `PushToTalkApi` | `.push_to_talk` | Push-to-talk settings |
| `VoicemailApi` | `.voicemail` | Voicemail settings (greeting, PIN, notifications, etc.) |

All sub-APIs use the virtual line ID as the entity identifier, and the URL pattern is:
```
telephony/config/virtualLines/{virtual_line_id}/{feature}
```

**Example -- read voicemail settings for a virtual line:**
```python
vm_settings = api.telephony.virtual_lines.voicemail.read(entity_id=vl_id)
```

**Example -- configure call forwarding for a virtual line:**
```python
api.telephony.virtual_lines.forwarding.configure(entity_id=vl_id, ...)
```

### Data Models

#### VirtualLine

```python
class VirtualLine(ApiModel):
    id: Optional[str]                                    # Unique identifier
    first_name: Optional[str]                            # First name (1-30 chars)
    last_name: Optional[str]                             # Last name (1-30 chars)
    display_name: Optional[str]                          # Display name
    caller_id_first_name: Optional[str]                  # CLID first name
    caller_id_last_name: Optional[str]                   # CLID last name
    caller_id_number: Optional[str]                      # CLID phone number
    external_caller_id_name_policy: Optional[ExternalCallerIdNamePolicy]
    custom_external_caller_id_name: Optional[str]
    number: Optional[UserNumber]                         # Phone number + extension
    location: Optional[VirtualLineLocation]              # Location details
    number_of_devices_assigned: Optional[int]
    billing_plan: Optional[str]
    directory_search_enabled: Optional[bool]
    announcement_language: Optional[str]
    time_zone: Optional[str]
    devices: Optional[list[TelephonyDevice]]             # Assigned devices
```

#### VirtualLineLocation

```python
class VirtualLineLocation(ApiModel):
    id: Optional[str]                                    # Location ID
    name: Optional[str]                                  # Location name
    address: Optional[LocationAddress]                   # Physical address
```

#### VirtualLineNumberPhoneNumber

```python
class VirtualLineNumberPhoneNumber(ApiModel):
    direct_number: Optional[str]                         # Assigned phone number
    extension: Optional[str]                             # Assigned extension
    primary: Optional[bool]                              # Whether this is the primary number
```

#### VirtualLineDevices

```python
class VirtualLineDevices(ApiModel):
    devices: Optional[list[TelephonyDevice]]             # Assigned devices
    available_endpoint_type: Optional[PrimaryOrShared]   # Primary or shared line
    max_device_count: Optional[int]                      # Max devices allowed
```

---

## Virtual Extensions

### What They Are

Virtual extensions are **different from virtual lines**. A virtual extension maps an internal extension number to an external phone number (E.164 format). This enables users to dial a short extension to reach someone on a separate telephony system or an external number.

**Common use cases:**
- Remote workers on a different phone system who need to be reachable by extension
- Frequently-called external contacts (clients, vendors) assigned a speed-dial extension
- Branch offices on a separate PBX that you want integrated into the Webex Calling dial plan

**Key characteristics:**
- Can be defined at the **organization level** (reachable from all locations) or the **location level** (reachable by extension within that location, or by ESN from other locations)
- Maps an extension to an external E.164 phone number
- Two operating modes: **Standard** (default, requires E.164 prefix) and **Enhanced** (requires PSTN provider support for special signaling)
- Supports wildcard patterns via virtual extension ranges

### SDK Access

```python
# Virtual Extensions API is at:
api = wxc_api.telephony.virtual_extensions  # VirtualExtensionsApi instance
```

Base path: `telephony/config`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write` (and `identity:contacts_rw` for create/update/delete of individual extensions)

### Individual Virtual Extensions

#### List Virtual Extensions

```python
VirtualExtensionsApi.list_extensions(
    order: str = None,                    # ASC or DSC
    extension: str = None,                # Filter by extension number
    phone_number: str = None,             # Filter by phone number
    name: str = None,                     # Filter by first or last name
    location_name: str = None,            # Filter by location name
    location_id: str = None,              # Filter by location ID
    org_level_only: bool = None,          # Only org-level extensions
    org_id: str = None,
) -> Generator[VirtualExtension, None, None]
```

Note: Only one of `location_name`, `location_id`, and `org_level_only` is allowed at the same time.

#### Create Virtual Extension

```python
VirtualExtensionsApi.create_extension(
    display_name: str,                    # Required
    phone_number: str,                    # Required, E.164 external number
    extension: str,                       # Required
    first_name: str = None,
    last_name: str = None,
    location_id: str = None,             # Omit for org-level
    org_id: str = None,
) -> str  # Returns the new virtual extension ID
```

- If `location_id` is omitted, the virtual extension is created at the **organization level** (reachable from all locations).
- If `location_id` is provided, it is a **location-level** extension (reachable as a local extension within that location; other locations use the ESN).

**Example:**
```python
ve_id = api.telephony.virtual_extensions.create_extension(
    display_name="Alice Remote",
    phone_number="+15559876543",
    extension="7001",
    first_name="Alice",
    last_name="Remote"
)
```

#### Get Virtual Extension Details

```python
VirtualExtensionsApi.details_extension(
    extension_id: str,                    # Required
    org_id: str = None,
) -> VirtualExtension
```

#### Update Virtual Extension

```python
VirtualExtensionsApi.update_extension(
    extension_id: str,                    # Required
    first_name: str = None,
    last_name: str = None,
    display_name: str = None,
    phone_number: str = None,
    extension: str = None,
    org_id: str = None,
) -> None
```

#### Delete Virtual Extension

```python
VirtualExtensionsApi.delete_extension(
    extension_id: str,                    # Required
    org_id: str = None,
) -> None
```

#### Validate External Phone Numbers

```python
VirtualExtensionsApi.validate_external_phone_number(
    phone_numbers: list[str],             # List of E.164 numbers to validate
    org_id: str = None,
) -> ValidatePhoneNumber
```

Pre-check that external numbers are properly formatted, eligible, and not already in use before assigning them as virtual extensions.

### Virtual Extension Ranges

Virtual extension ranges let you define patterns with wildcards to route blocks of extensions to external prefixes. For example, you can route extensions `7000`-`7099` to an external prefix in a single range definition instead of creating 100 individual virtual extensions.

#### List Ranges

```python
VirtualExtensionsApi.list_range(
    order: str = None,                    # Sort by name or prefix (ASC/DSC)
    name: str = None,                     # Filter by range name
    prefix: str = None,                   # Filter by prefix
    location_id: str = None,              # Filter by location ID
    org_level_only: bool = None,          # Only org-level ranges
    org_id: str = None,
) -> Generator[VirtualExtensionRange, None, None]
```

Only one of `location_id` and `org_level_only` is allowed at the same time.

#### Create Range

```python
VirtualExtensionsApi.create_range(
    name: str,                            # Required, unique name
    prefix: str,                          # Required, E.164 in Standard mode
    patterns: list[str] = None,           # Up to 100 patterns, wildcards "X" allowed
    location_id: str = None,              # Omit for org-level
    org_id: str = None,
) -> str  # Returns the new range ID
```

**Pattern wildcards:** Extension patterns can include one or more right-justified `X` characters matching any digit. For example, `70XX` matches extensions 7000-7099.

**Example:**
```python
range_id = api.telephony.virtual_extensions.create_range(
    name="Remote Office Block",
    prefix="+15559870000",
    patterns=["70XX", "71XX"]
)
```

#### Get Range Details

```python
VirtualExtensionsApi.details_range(
    extension_range_id: str,
    org_id: str = None,
) -> VirtualExtensionRange
```

#### Modify Range

```python
VirtualExtensionsApi.modify_range(
    extension_range_id: str,              # Required
    name: str = None,
    prefix: str = None,
    patterns: list[str] = None,           # Max 100 patterns per request
    action: VirtualExtensionRangeAction = None,  # ADD, REMOVE, or REPLACE
    org_id: str = None,
) -> None
```

The `action` parameter is **mandatory** when `patterns` are provided:
- `ADD` -- add new patterns to the existing range
- `REMOVE` -- remove specified patterns from the range
- `REPLACE` -- replace all existing patterns with the new set

#### Delete Range

```python
VirtualExtensionsApi.delete_range(
    extension_range_id: str,
    org_id: str = None,
) -> None
```

#### Validate Range

```python
VirtualExtensionsApi.validate_range(
    location_id: str = None,
    name: str = None,
    prefix: str = None,
    patterns: list[str] = None,           # Max 100
    range_id: str = None,                 # Include when validating existing range
    org_id: str = None,
) -> ValidateVirtualExtensionRange
```

Pre-check before creating or modifying. Returns `status` of `OK` or `ERRORS`. When `ERRORS`, the `validation_status` list contains per-pattern details.

### Extension Settings (Mode)

#### Get Mode

```python
VirtualExtensionsApi.get_extension_settings(
    org_id: str = None,
) -> VirtualExtensionMode  # STANDARD or ENHANCED
```

#### Set Mode

```python
VirtualExtensionsApi.modify_extension_settings(
    mode: VirtualExtensionMode,           # STANDARD or ENHANCED
    org_id: str = None,
) -> None
```

**Standard mode** (default): Virtual extensions must have an E.164 prefix. No special PSTN provider support required.

**Enhanced mode**: Prefix can be E.164 or non-E.164, but requires PSTN provider support for special network signaling extensions. Very few PSTN providers support this. <!-- NEEDS VERIFICATION: exact list of PSTN providers supporting Enhanced mode -->

### Data Models

#### VirtualExtension

```python
class VirtualExtension(ApiModel):
    id: Optional[str]                                    # Unique identifier
    extension: Optional[str]                             # Internal extension number
    routing_prefix: Optional[str]                        # Location routing prefix
    esn: Optional[str]                                   # Enterprise Significant Number
    phone_number: Optional[str]                          # External E.164 number
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    level: Optional[VirtualExtensionLevel]               # ORGANIZATION or LOCATION
    location_id: Optional[str]                           # Set for location-level only
    location_name: Optional[str]                         # Set for location-level only
```

#### VirtualExtensionRange

```python
class VirtualExtensionRange(ApiModel):
    id: Optional[str]                                    # Range ID
    name: Optional[str]                                  # Unique range name
    prefix: Optional[str]                                # E.164 prefix (Standard) or any (Enhanced)
    level: Optional[VirtualExtensionLevel]               # ORGANIZATION or LOCATION
    patterns: Optional[list[str]]                        # Extension patterns (max 100), "X" wildcards
    location_id: Optional[str]                           # Set for location-level only
    location_name: Optional[str]                         # Set for location-level only
```

#### Enums

```python
class VirtualExtensionLevel(str, Enum):
    location = 'LOCATION'
    organization = 'ORGANIZATION'

class VirtualExtensionMode(str, Enum):
    standard = 'STANDARD'
    enhanced = 'ENHANCED'

class VirtualExtensionRangeAction(str, Enum):
    add = 'ADD'
    remove = 'REMOVE'
    replace = 'REPLACE'
```

#### Validation Models

```python
class ValidateVirtualExtensionRange(ApiModel):
    status: Optional[ValidateVirtualExtensionStatus]     # OK or ERRORS
    validation_status: Optional[list[VirtualExtensionRangeValidationResult]]

class VirtualExtensionRangeValidationResult(ApiModel):
    name: Optional[str]
    prefix: Optional[str]
    pattern: Optional[str]
    error_code: Optional[int]
    message: Optional[str]
    status: Optional[VirtualExtensionValidationStatus]   # VALID, DUPLICATE, DUPLICATE_IN_LIST, INVALID, LIMIT_EXCEEDED

class ValidatePhoneNumber(ApiModel):
    status: Optional[ValidateVirtualExtensionStatus]     # OK or ERRORS
    phone_number_status: Optional[list[PhoneNumberStatus]]

class PhoneNumberStatus(ApiModel):
    phone_number: Optional[str]
    state: Optional[VirtualExtensionValidationStatus]
    error_code: Optional[int]
    message: Optional[str]
```

---

## Virtual Lines vs. Virtual Extensions: Decision Guide

| Question | Virtual Line | Virtual Extension |
|----------|-------------|-------------------|
| Does it need voicemail? | Yes | No |
| Does it need call forwarding/recording? | Yes | No |
| Does it ring a device inside Webex Calling? | Yes | No |
| Does it route to an external PSTN number? | No (it IS a Webex line) | Yes |
| Does it need its own call settings? | Yes (17+ sub-APIs) | No |
| Can it be assigned to a physical phone? | Yes | No |
| Does it need to integrate a remote PBX? | No | Yes |

---

## Source

- SDK source: `wxc_sdk/telephony/virtual_line/__init__.py`
- SDK source: `wxc_sdk/telephony/virtual_extensions/__init__.py`
- SDK source: `wxc_sdk/person_settings/common.py` (ApiSelector, URL routing)

---

## See Also

- **[devices-dect.md](devices-dect.md)** — DECT handset Line 2 supports VIRTUAL_LINE member type. Virtual lines can be assigned to DECT handsets as secondary lines.
- **[emergency-services.md](emergency-services.md)** — Emergency callback number (ECBN) configuration for virtual lines. The `.ecbn` sub-API in the virtual line call settings table is documented in detail there.
