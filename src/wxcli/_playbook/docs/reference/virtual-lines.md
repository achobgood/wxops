<!-- Updated by playbook session 2026-03-18 -->

# Virtual Lines & Virtual Extensions

## Table of Contents

1. [Overview](#overview)
2. [Virtual Lines](#virtual-lines)
3. [Virtual Extensions](#virtual-extensions)
4. [Raw HTTP](#raw-http)
5. [Gotchas](#gotchas)
6. [Virtual Lines vs. Virtual Extensions: Decision Guide](#virtual-lines-vs-virtual-extensions-decision-guide)
7. [Source](#source)
8. [See Also](#see-also)

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

### Base Endpoint

Base path: `telephony/config/virtualLines`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

### Behavior Notes

- Listing supports multiple filter values per parameter (e.g., multiple `locationId` values) and is paginated.
- Creating requires `firstName` (1-30 chars), `lastName` (1-30 chars), and `locationId`; at least one of `phoneNumber` (1-23 chars) or `extension` (2-10 chars) must also be provided.
- Getting details returns the full virtual line object including location, number, devices, caller ID, time zone, and announcement language.
- Updates are partial -- only include fields you want to change; omitted fields are not modified.

### Additional Virtual Line Operations

- **Get Phone Number** -- returns the `directNumber`, `extension`, and `primary` flag for the assigned phone number.
- **Update Directory Search** -- toggles whether the virtual line appears in directory search.
- **Get Assigned Devices** -- returns the devices assigned to the virtual line, the available endpoint type (primary or shared line), and the maximum device count.
- **Get DECT Network Handsets** -- returns DECT network handset assignments for the virtual line.

### Virtual Line Call Settings

Virtual lines support the same call settings as person lines. Each feature is its own endpoint suffix off the virtual line ID:

| Feature | Endpoint Suffix | What It Controls |
|---------|-----------------|-----------------|
| Agent Caller ID | `agentCallerId` | Caller ID when acting as a call queue/hunt group agent |
| Available Numbers | `availableNumbers` | List available numbers for assignment |
| Barge-In | `bargeIn` | Barge-in settings |
| Call Bridge | `callBridge` | Call bridge settings |
| Call Intercept | `callIntercept` | Call intercept (redirect/block incoming calls) |
| Call Recording | `callRecording` | Call recording settings |
| Call Waiting | `callWaiting` | Call waiting settings |
| Caller ID | `callerId` | Outbound caller ID configuration |
| Do Not Disturb | `doNotDisturb` | Do Not Disturb settings |
| Emergency Callback Number | `emergencyCallbackNumber` | Emergency callback number |
| Call Forwarding | `callForwarding` | Call forwarding rules (always, busy, no-answer) |
| Music On Hold | `musicOnHold` | Music on hold settings |
| Incoming Permissions | `incomingPermission` | Incoming call permissions |
| Outgoing Permissions | `outgoingPermission` | Outgoing call permissions |
| Privacy | `privacy` | Privacy settings |
| Push To Talk | `pushToTalk` | Push-to-talk settings |
| Voicemail | `voicemail` | Voicemail settings (greeting, PIN, notifications, etc.) |

All virtual line settings use the virtual line ID as the entity identifier, with URL pattern:
```
telephony/config/virtualLines/{virtual_line_id}/{feature}
```

See the [Raw HTTP](#raw-http) section below for read/write examples against these endpoints, and the CLI Examples section immediately below for the `virtual-line-settings` command equivalents.

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

### Response Fields

#### Virtual Line Object

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `firstName` | First name (1-30 chars) |
| `lastName` | Last name (1-30 chars) |
| `displayName` | Display name |
| `callerIdFirstName` | CLID first name |
| `callerIdLastName` | CLID last name |
| `callerIdNumber` | CLID phone number |
| `externalCallerIdNamePolicy` | External caller ID name policy |
| `customExternalCallerIdName` | Custom external caller ID name |
| `number` | Phone number + extension (see Number object below) |
| `location` | Location details (see Location object below) |
| `numberOfDevicesAssigned` | Count of assigned devices |
| `billingPlan` | Billing plan |
| `directorySearchEnabled` | Whether the line appears in directory search |
| `announcementLanguage` | Announcement language |
| `timeZone` | Time zone |
| `devices` | List of assigned devices |

#### Location Object

| Field | Description |
|-------|-------------|
| `id` | Location ID |
| `name` | Location name |
| `address` | Physical address |

#### Number Object

| Field | Description |
|-------|-------------|
| `directNumber` | Assigned phone number |
| `extension` | Assigned extension |
| `primary` | Whether this is the primary number |

#### Devices Object

| Field | Description |
|-------|-------------|
| `devices` | List of assigned devices |
| `availableEndpointType` | Primary or shared line |
| `maxDeviceCount` | Maximum devices allowed |

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

### Base Endpoint

Base path: `telephony/config`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write` (and `identity:contacts_rw` for create/update/delete of individual extensions)

### Individual Virtual Extensions

- Listing supports filtering by extension, phone number, name, and location; only one of `locationName`, `locationId`, and `orgLevelOnly` may be used at the same time.
- Creating requires `displayName`, `phoneNumber` (E.164 external number), and `extension`.
  - If `locationId` is omitted, the virtual extension is created at the **organization level** (reachable from all locations).
  - If `locationId` is provided, it is a **location-level** extension (reachable as a local extension within that location; other locations use the ESN).
- Validating external phone numbers is a pre-check that numbers are properly formatted, eligible, and not already in use before assigning them as virtual extensions.

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

### Range Behavior Notes

Virtual extension ranges let you define patterns with wildcards to route blocks of extensions to external prefixes. For example, you can route extensions `7000`-`7099` to an external prefix in a single range definition instead of creating 100 individual virtual extensions.

- Listing supports sorting by name or prefix; only one of `locationId` and `orgLevelOnly` is allowed at the same time.
- Creating requires a unique `name` and a `prefix` (E.164 in Standard mode), with up to 100 `patterns`.
- **Pattern wildcards:** Extension patterns can include one or more right-justified `X` characters matching any digit. For example, `70XX` matches extensions 7000-7099.
- Modifying a range accepts up to 100 `patterns` per request. The `action` field is **mandatory** when `patterns` are provided:
  - `ADD` -- add new patterns to the existing range
  - `REMOVE` -- remove specified patterns from the range
  - `REPLACE` -- replace all existing patterns with the new set
- Validating a range is a pre-check before creating or modifying. Returns `status` of `OK` or `ERRORS`. When `ERRORS`, the `validationStatus` list contains per-pattern details.

### Extension Mode Details

**Standard mode** (default): Virtual extensions must have an E.164 prefix. No special PSTN provider support required.

**Enhanced mode**: Prefix can be E.164 or non-E.164, but requires PSTN provider support for special network signaling extensions. The API documentation states: "virtual extensions won't function properly in this mode unless your PSTN provider supports special network signaling extensions and there aren't many PSTN providers that do." No specific provider list is published in the API documentation or OpenAPI spec. Contact your Cisco account team or PSTN provider to confirm Enhanced mode support.

### Response Fields

#### Virtual Extension Object

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `extension` | Internal extension number |
| `routingPrefix` | Location routing prefix |
| `esn` | Enterprise Significant Number |
| `phoneNumber` | External E.164 number |
| `firstName` | First name |
| `lastName` | Last name |
| `displayName` | Display name |
| `level` | `ORGANIZATION` or `LOCATION` |
| `locationId` | Set for location-level only |
| `locationName` | Set for location-level only |

#### Virtual Extension Range Object

| Field | Description |
|-------|-------------|
| `id` | Range ID |
| `name` | Unique range name |
| `prefix` | E.164 prefix (Standard) or any (Enhanced) |
| `level` | `ORGANIZATION` or `LOCATION` |
| `patterns` | Extension patterns (max 100), `X` wildcards |
| `locationId` | Set for location-level only |
| `locationName` | Set for location-level only |

#### Enums

| Enum | Values |
|------|--------|
| Virtual Extension Level | `LOCATION`, `ORGANIZATION` |
| Virtual Extension Mode | `STANDARD`, `ENHANCED` |
| Virtual Extension Range Action | `ADD`, `REMOVE`, `REPLACE` |

#### Validation Response Fields

**Range validation response:**

| Field | Description |
|-------|-------------|
| `status` | `OK` or `ERRORS` |
| `validationStatus` | List of per-pattern results: `name`, `prefix`, `pattern`, `errorCode`, `message`, `status` (`VALID`, `DUPLICATE`, `DUPLICATE_IN_LIST`, `INVALID`, `LIMIT_EXCEEDED`) |

**Phone number validation response:**

| Field | Description |
|-------|-------------|
| `status` | `OK` or `ERRORS` |
| `phoneNumberStatus` | List of per-number results: `phoneNumber`, `state`, `errorCode`, `message` |

---

## Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All virtual line and virtual extension operations can be performed via raw HTTP using `api.session.rest_*()`. Use this when a `wxcli` command doesn't cover what you need -- you get full control over the exact request.

```python
from wxcli.auth import get_api

api = get_api()
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

---

## Gotchas

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
| Does it need its own call settings? | Yes (17+ settings) | No |
| Can it be assigned to a physical phone? | Yes | No |
| Does it need to integrate a remote PBX? | No | Yes |

---

## Source

- CLI command group: `wxcli virtual-line-settings --help` (virtual line CRUD + call settings)
- CLI command group: `wxcli virtual-extensions --help` (virtual extension CRUD, ranges, settings)
- REST base path: `telephony/config/virtualLines`
- REST base path: `telephony/config/virtualExtensions`

---

## See Also

- **[devices-dect.md](devices-dect.md)** — DECT handset Line 2 supports VIRTUAL_LINE member type. Virtual lines can be assigned to DECT handsets as secondary lines.
- **[emergency-services.md](emergency-services.md)** — Emergency callback number (ECBN) configuration for virtual lines. The `emergencyCallbackNumber` endpoint in the virtual line call settings table is documented in detail there.
