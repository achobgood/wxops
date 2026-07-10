<!-- Updated by playbook session 2026-03-18 -->

# Virtual Lines & Virtual Extensions

## Table of Contents

1. [Overview](#overview)
2. [Virtual Lines](#virtual-lines)
3. [Virtual Extensions](#virtual-extensions)
4. [Raw HTTP](#raw-http)
5. [Virtual Lines vs. Virtual Extensions: Decision Guide](#virtual-lines-vs-virtual-extensions-decision-guide)
6. [Source](#source)
7. [See Also](#see-also)

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

### CLI Examples

The `virtual-line-settings` command group covers virtual line CRUD and all call settings (63 commands total). The commands mirror the person settings commands in `user-settings`.

#### Virtual Line CRUD

```bash
# List all virtual lines
wxcli virtual-line-settings list

# List virtual lines at a specific location
wxcli virtual-line-settings list --location-id Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg=

# List virtual lines with filters
wxcli virtual-line-settings list --owner-name "Sales" --has-device-assigned true

# Show details for a virtual line
wxcli virtual-line-settings show-virtual-lines Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Create a virtual line (firstName, lastName, locationId required; phoneNumber or extension required)
wxcli virtual-line-settings create \
  --first-name "Sales" --last-name "Line" \
  --location-id Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg= \
  --extension 8500 --phone-number "+15551234567"

# Create with caller ID overrides
wxcli virtual-line-settings create \
  --first-name "Front" --last-name "Desk" \
  --location-id Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg= \
  --extension 8000 \
  --caller-id-first-name "Main" --caller-id-last-name "Office" \
  --caller-id-number "+15559999999"

# Update a virtual line
wxcli virtual-line-settings update-virtual-lines Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --first-name "Sales" --last-name "Main Line" --extension 8501

# Update time zone and announcement language
wxcli virtual-line-settings update-virtual-lines Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --time-zone "America/Chicago" --announcement-language "en_us"

# Delete a virtual line
wxcli virtual-line-settings delete Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Delete without confirmation prompt
wxcli virtual-line-settings delete Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --force

# Get phone number assigned to a virtual line
wxcli virtual-line-settings show-number Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# List devices assigned to a virtual line
wxcli virtual-line-settings list-devices Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0
```

#### Call Handling Settings

```bash
# Read call forwarding settings
wxcli virtual-line-settings show-call-forwarding Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Enable always-forward (nested settings require --json-body)
wxcli virtual-line-settings update-call-forwarding Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --json-body '{"callForwarding":{"always":{"enabled":true,"destination":"+15551234567","ringReminderEnabled":true}}}'

# Enable no-answer forwarding with 5 rings
wxcli virtual-line-settings update-call-forwarding Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --json-body '{"callForwarding":{"noAnswer":{"enabled":true,"destination":"+15556667777","numberOfRings":5}}}'

# Enable business continuity forwarding
wxcli virtual-line-settings update-call-forwarding Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --json-body '{"businessContinuity":{"enabled":true,"destination":"+18889990000"}}'

# Read call waiting settings
wxcli virtual-line-settings show-call-waiting Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Enable call waiting
wxcli virtual-line-settings update-call-waiting Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --enabled

# Disable call waiting
wxcli virtual-line-settings update-call-waiting Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --no-enabled

# Read DND settings
wxcli virtual-line-settings show-do-not-disturb Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Enable DND with ring splash
wxcli virtual-line-settings update-do-not-disturb Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --enabled --ring-splash-enabled

# Disable DND
wxcli virtual-line-settings update-do-not-disturb Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --no-enabled
```

#### Voicemail & Media Settings

```bash
# Read voicemail settings
wxcli virtual-line-settings show-voicemail Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Enable voicemail with default greetings (nested settings require --json-body)
wxcli virtual-line-settings update-voicemail Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --json-body '{"enabled":true,"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":3}}'

# Enable voicemail with simple flag (just enable/disable)
wxcli virtual-line-settings update-voicemail Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --enabled

# Read caller ID settings
wxcli virtual-line-settings list-caller-id Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Update caller ID to use direct line
wxcli virtual-line-settings update-caller-id-virtual-lines Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --selected DIRECT_LINE

# Update caller ID to use a custom number
wxcli virtual-line-settings update-caller-id-virtual-lines Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --selected CUSTOM --custom-number "+15559999999" \
  --first-name "Sales" --last-name "Department"

# Read call recording settings
wxcli virtual-line-settings show Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Enable call recording (always record)
wxcli virtual-line-settings update Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --enabled --record "Always"

# Enable call recording with voicemail recording
wxcli virtual-line-settings update Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 \
  --enabled --record "Always" --record-voicemail-enabled
```

#### Permissions & Other Settings

```bash
# Read incoming permission settings
wxcli virtual-line-settings show-incoming-permission Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Read outgoing permission settings
wxcli virtual-line-settings list-outgoing-permission Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Read barge-in settings
wxcli virtual-line-settings show-barge-in Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Read call intercept settings
wxcli virtual-line-settings show-intercept Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Read music on hold settings
wxcli virtual-line-settings show-music-on-hold Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# List DECT network handsets assigned to a virtual line
wxcli virtual-line-settings list-dect-networks Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0

# Enable directory search visibility
wxcli virtual-line-settings update-directory-search Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --enabled

# Disable directory search visibility
wxcli virtual-line-settings update-directory-search Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfTElORS8xMjM0 --no-enabled
```

> **Note:** The `show` and `update` commands in `virtual-line-settings` map to call recording settings (not virtual line details). Use `show-virtual-lines` and `update-virtual-lines` for virtual line details.

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

### CLI Examples

The `virtual-extensions` command group covers virtual extension CRUD, ranges, settings, and validation (14 commands).

#### Individual Virtual Extensions

```bash
# List all virtual extensions
wxcli virtual-extensions list

# List virtual extensions filtered by location
wxcli virtual-extensions list --location-id Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg=

# List org-level virtual extensions only
wxcli virtual-extensions list --org-level-only true

# Filter by name or extension number
wxcli virtual-extensions list --name "Alice" --extension 7001

# Show details for a virtual extension
wxcli virtual-extensions show Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfRVhULzEyMzQ=

# Create a virtual extension (displayName, phoneNumber, extension required)
wxcli virtual-extensions create \
  --display-name "Alice Remote" --phone-number "+15559876543" --extension 7001 \
  --first-name "Alice" --last-name "Remote"

# Create a location-level virtual extension
wxcli virtual-extensions create \
  --display-name "Branch PBX" --phone-number "+15551112222" --extension 7050 \
  --location-id Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg=

# Update a virtual extension
wxcli virtual-extensions update Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfRVhULzEyMzQ= \
  --display-name "Alice Remote (Updated)" --phone-number "+15559876544"

# Delete a virtual extension
wxcli virtual-extensions delete Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfRVhULzEyMzQ=

# Delete without confirmation prompt
wxcli virtual-extensions delete Y2lzY29zcGFyazovL3VzL1ZJUlRVQUxfRVhULzEyMzQ= --force

# Validate external phone numbers before creating extensions
wxcli virtual-extensions validate-an-external \
  --json-body '{"phoneNumbers":["+15551112222","+15553334444"]}'
```

#### Extension Settings (Mode)

```bash
# Show current virtual extension mode (STANDARD or ENHANCED)
wxcli virtual-extensions show-settings

# Update virtual extension mode
wxcli virtual-extensions update-settings --mode STANDARD
```

#### Virtual Extension Ranges

```bash
# List all virtual extension ranges
wxcli virtual-extensions list-virtual-extension-ranges

# Show details for a range
wxcli virtual-extensions show-virtual-extension-ranges Y2lzY29zcGFyazovL3VzL1JBTkdFLzEyMzQ=

# Create a range with wildcard patterns (patterns via --json-body)
wxcli virtual-extensions create-virtual-extension-ranges \
  --name "Remote Office Block" --prefix "+15559870000" \
  --json-body '{"patterns":["70XX","71XX"]}'

# Create a location-level range
wxcli virtual-extensions create-virtual-extension-ranges \
  --name "Branch Block" --prefix "+15559870000" \
  --location-id Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg= \
  --json-body '{"patterns":["80XX"]}'

# Update a range (add new patterns)
wxcli virtual-extensions update-virtual-extension-ranges Y2lzY29zcGFyazovL3VzL1JBTkdFLzEyMzQ= \
  --action ADD --json-body '{"patterns":["72XX"]}'

# Delete a range
wxcli virtual-extensions delete-virtual-extension-ranges Y2lzY29zcGFyazovL3VzL1JBTkdFLzEyMzQ=

# Validate a range before creating
wxcli virtual-extensions validate-the-prefix \
  --json-body '{"name":"Test Range","prefix":"+15559870000","patterns":["70XX"]}'
```

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

**Enhanced mode**: Prefix can be E.164 or non-E.164, but requires PSTN provider support for special network signaling extensions. The API documentation states: "virtual extensions won't function properly in this mode unless your PSTN provider supports special network signaling extensions and there aren't many PSTN providers that do." No specific provider list is published in the API documentation or OpenAPI spec. Contact your Cisco account team or PSTN provider to confirm Enhanced mode support.

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

## Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All virtual line and virtual extension operations can be performed via raw HTTP using `api.session.rest_*()`. This is the preferred execution pattern -- wxc_sdk handles auth and session management, while you control the exact request.

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"
```

### Virtual Lines CRUD

```python
# ── List virtual lines ───────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/telephony/config/virtualLines", params={
    "max": 1000,
    "locationId": location_id,            # filter by location
})
virtual_lines = result.get("virtualLines", [])

# ── List with filters ────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/telephony/config/virtualLines", params={
    "max": 1000,
    "ownerName": "Sales",
    "hasDeviceAssigned": "true",
    "hasExtensionAssigned": "true",
})
virtual_lines = result.get("virtualLines", [])

# ── Get virtual line details ─────────────────────────────────────
vl = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}")

# ── Create a virtual line ────────────────────────────────────────
body = {
    "firstName": "Sales",
    "lastName": "Line",
    "locationId": location_id,
    "extension": "8500",
    "phoneNumber": "+15551234567",
    "callerIdLastName": "Sales",
    "callerIdFirstName": "Department",
}
result = api.session.rest_post(f"{BASE}/telephony/config/virtualLines", json=body)
new_vl_id = result["id"]

# ── Update a virtual line ────────────────────────────────────────
body = {
    "firstName": "Sales",
    "lastName": "Main Line",
    "extension": "8501",
}
api.session.rest_put(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}", json=body)

# ── Delete a virtual line ────────────────────────────────────────
api.session.rest_delete(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}")

# ── Get phone number ─────────────────────────────────────────────
num = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}/number")

# ── Update directory search ──────────────────────────────────────
api.session.rest_put(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}/directorySearch", json={
    "enabled": True,
})

# ── Get assigned devices ─────────────────────────────────────────
devices = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}/devices")

# ── Get DECT network handsets ────────────────────────────────────
dect = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{virtual_line_id}/dectNetworks")
```

### Virtual Line Call Settings

Virtual line call settings use the `/telephony/config/virtualLines/{id}/{feature}` path:

```python
# ── Voicemail ────────────────────────────────────────────────────
vm = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/voicemail")
api.session.rest_put(f"{BASE}/telephony/config/virtualLines/{vl_id}/voicemail", json={
    "enabled": True,
    "sendAllCalls": {"enabled": False},
    "sendBusyCalls": {"enabled": True, "greeting": "DEFAULT"},
    "sendUnansweredCalls": {"enabled": True, "numberOfRings": 3, "greeting": "DEFAULT"},
})

# ── Call Forwarding ──────────────────────────────────────────────
fwd = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/callForwarding")
api.session.rest_put(f"{BASE}/telephony/config/virtualLines/{vl_id}/callForwarding", json={
    "callForwarding": {"always": {"enabled": True, "destination": "+15551234567"}},
})

# ── Call Recording ───────────────────────────────────────────────
rec = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/callRecording")

# ── Call Waiting ─────────────────────────────────────────────────
cw = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/callWaiting")

# ── Caller ID ────────────────────────────────────────────────────
cid = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/callerId")

# ── DND ──────────────────────────────────────────────────────────
dnd = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/doNotDisturb")

# ── Call Intercept ───────────────────────────────────────────────
intercept = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/callIntercept")

# ── Privacy ──────────────────────────────────────────────────────
privacy = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/privacy")

# ── ECBN ─────────────────────────────────────────────────────────
ecbn = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/emergencyCallbackNumber")

# ── Incoming Permissions ─────────────────────────────────────────
perm_in = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/incomingPermission")

# ── Outgoing Permissions ─────────────────────────────────────────
perm_out = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/outgoingPermission")

# ── Music on Hold ────────────────────────────────────────────────
moh = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/musicOnHold")

# ── Barge-In ─────────────────────────────────────────────────────
barge = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/bargeIn")

# ── Push to Talk ─────────────────────────────────────────────────
ptt = api.session.rest_get(f"{BASE}/telephony/config/virtualLines/{vl_id}/pushToTalk")
```

### Virtual Extensions CRUD

```python
# ── List virtual extensions ──────────────────────────────────────
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions", params={
    "max": 1000,
    "locationId": location_id,
})
extensions = result.get("virtualExtensions", [])

# ── List org-level only ──────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions", params={
    "max": 1000,
    "orgLevelOnly": "true",
})

# ── Get virtual extension details ────────────────────────────────
ve = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions/{extension_id}")

# ── Create a virtual extension ───────────────────────────────────
body = {
    "displayName": "Alice Remote",
    "phoneNumber": "+15559876543",
    "extension": "7001",
    "firstName": "Alice",
    "lastName": "Remote",
    "locationId": location_id,            # omit for org-level
}
result = api.session.rest_post(f"{BASE}/telephony/config/virtualExtensions", json=body)
new_ve_id = result["id"]

# ── Update a virtual extension ───────────────────────────────────
body = {
    "displayName": "Alice Remote (Updated)",
    "phoneNumber": "+15559876544",
}
api.session.rest_put(f"{BASE}/telephony/config/virtualExtensions/{extension_id}", json=body)

# ── Delete a virtual extension ───────────────────────────────────
api.session.rest_delete(f"{BASE}/telephony/config/virtualExtensions/{extension_id}")

# ── Validate external phone numbers ─────────────────────────────
result = api.session.rest_post(
    f"{BASE}/telephony/config/virtualExtensions/actions/validateNumbers/invoke",
    json={"phoneNumbers": ["+15551112222", "+15553334444"]},
)
# Returns: {status: "OK"|"ERRORS", phoneNumberStatus: [...]}

# ── Get/set extension mode ───────────────────────────────────────
settings = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions/settings")
# Returns: {mode: "STANDARD"|"ENHANCED"}

api.session.rest_put(f"{BASE}/telephony/config/virtualExtensions/settings", json={
    "mode": "STANDARD",
})
```

### Virtual Extension Ranges

```python
# ── List ranges ──────────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensionRanges", params={
    "max": 1000,
})
ranges = result.get("virtualExtensionRanges", [])

# ── Get range details ────────────────────────────────────────────
rng = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensionRanges/{range_id}")

# ── Create a range ───────────────────────────────────────────────
body = {
    "name": "Remote Office Block",
    "prefix": "+15559870000",
    "patterns": ["70XX", "71XX"],
    "locationId": location_id,            # omit for org-level
}
result = api.session.rest_post(f"{BASE}/telephony/config/virtualExtensionRanges", json=body)
new_range_id = result["id"]

# ── Modify a range (ADD/REMOVE/REPLACE patterns) ────────────────
api.session.rest_put(f"{BASE}/telephony/config/virtualExtensionRanges/{range_id}", json={
    "name": "Remote Office Block",
    "prefix": "+15559870000",
    "patterns": ["72XX"],
    "action": "ADD",                      # ADD, REMOVE, or REPLACE
})

# ── Delete a range ───────────────────────────────────────────────
api.session.rest_delete(f"{BASE}/telephony/config/virtualExtensionRanges/{range_id}")

# ── Validate a range ─────────────────────────────────────────────
result = api.session.rest_post(
    f"{BASE}/telephony/config/virtualExtensionRanges/actions/validate/invoke",
    json={
        "name": "Test Range",
        "prefix": "+15559870000",
        "patterns": ["70XX"],
    },
)
# Returns: {status: "OK"|"ERRORS", validationStatus: [...]}
```

### Raw HTTP Gotchas

1. **Virtual lines response key is `virtualLines`** -- Not `items`. This differs from the Workspaces API which uses `items`.
2. **Virtual extensions response key is `virtualExtensions`** -- Consistent with the domain-specific naming pattern.
3. **Virtual extension ranges response key is `virtualExtensionRanges`** -- Same pattern.
4. **Virtual line update is partial** -- Only include fields you want to change. Omitted fields are not modified. This differs from workspace update which is a full PUT.
5. **`action` is mandatory when modifying range patterns** -- If you include `patterns` in a range PUT, you must also include `action` (ADD, REMOVE, or REPLACE).
6. **`orgLevelOnly` is mutually exclusive with `locationId`/`locationName`** -- Only one filter type is allowed when listing virtual extensions or ranges.
7. **No auto-pagination** -- Use `max=1000` for the first page. Check for pagination links if you have more results.
8. **Virtual line call settings path vs workspace features path** -- Virtual lines use `/telephony/config/virtualLines/{id}/{feature}`. Workspaces use `/workspaces/{id}/features/{feature}`. These are completely different base paths.
9. **`virtual-extensions` CLI commands use wrong ID type.** The generated `virtual-extensions` command group maps to the Virtual Extensions API which uses `VIRTUAL_EXTENSION`-encoded IDs. Virtual lines created via `/telephony/config/virtualLines` use `VIRTUAL_LINE` IDs. `virtual-extensions list` returns empty, and `virtual-extensions delete` returns 400. **Workaround:** Use raw REST calls (`DELETE /v1/telephony/config/virtualLines/{id}`). The `wxcli cleanup` command already uses raw REST for this reason. The `virtual-line-settings` group uses the correct path family but only has settings commands, not CRUD. <!-- Documented from CLI known issue, 2026-03-31 -->

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
