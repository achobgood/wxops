<!-- Not directly verified via CLI — documents wxcadm library (not generated CLI commands) -->
<!-- wxcadm v4.6.1 review 2026-03-27: All v4.5.0–v4.6.1 changes verified present. Meraki optional dependency (lazy import), CPAPI auto-init commented out, Applications(org) signature — all accurately documented. Location.set_default_moh/upload_moh_file removed from Location class (only in CPAPI section, which is correct). No discrepancies found. -->
# wxcadm Advanced Modules

Covers wxcadm capabilities that go **beyond** the standard Webex Calling API: RedSky E911 management, Meraki network-to-E911 integration, the CP-API (Control Hub internal API), application/service-app lifecycle, Wholesale provisioning, and the Bifrost internal API.

These modules are **unique to wxcadm** -- none of them have equivalents in `wxc_sdk`.

---

<!-- Updated by playbook session 2026-03-18 -->
## When to Use wxcadm vs Raw HTTP

**Everything in this doc is unique to wxcadm. There are no raw HTTP equivalents in the standard Webex API.**

| Use wxcadm when | Use raw HTTP when |
|---|---|
| RedSky E911 management (buildings, locations, network discovery wire-maps, HELD devices) | **Never** -- RedSky has its own API (`api.wxc.e911cloud.com`) with separate auth; wxcadm is the only Python wrapper |
| Meraki-to-RedSky automated wire-map sync | **Never** -- requires both Meraki Dashboard API and RedSky API orchestration that wxcadm handles |
| CP-API operations (VM PIN reset, MOH upload, AA greeting upload, workspace caller ID) | **Never** -- CP-API is Control Hub's internal API (`cpapi-a.wbx2.com`), not exposed through `api.webex.com` |
| Wholesale partner provisioning (customer/subscriber management) | **Never** -- the `/v1/wholesale/*` endpoints require partner-level tokens and are not part of the standard Webex Calling API |
| Service App lifecycle (create, authorize, token exchange) | **Never** -- involves multi-step OAuth flows that wxcadm orchestrates |
| Bifrost location enrichment | **Never** -- internal Webex API (`bifrost-a.wbx2.com`) not available publicly |

> **Note:** The playbook uses raw HTTP via `api.session.rest_*()` for standard CRUD operations against the public Webex API. None of the capabilities in this doc are accessible through the public API. If you need E911 management, CP-API operations, Wholesale provisioning, or Bifrost data, wxcadm is required.

---

## Table of Contents

- [RedSky E911](#redsky-e911)
  - [Architecture: Building / Location](#architecture-building--location)
  - [Connecting to RedSky](#connecting-to-redsky)
  - [Buildings](#buildings)
  - [Locations](#locations)
  - [Network Discovery (Wire-Mapping)](#network-discovery-wire-mapping)
  - [HELD Devices](#held-devices)
  - [Users](#users)
- [Meraki Integration](#meraki-integration)
  - [Tag-Based Location Convention](#tag-based-location-convention)
  - [Connecting to Meraki](#connecting-to-meraki)
  - [Attaching RedSky to a Meraki Network](#attaching-redsky-to-a-meraki-network)
  - [Running the Audit](#running-the-audit)
  - [Audit Results](#audit-results)
  - [Device Types](#device-types)
- [CP-API (Control Hub Internal API)](#cp-api-control-hub-internal-api)
  - [Voicemail PIN Management](#voicemail-pin-management)
  - [Workspace Caller ID](#workspace-caller-id)
  - [Music on Hold Upload](#music-on-hold-upload)
  - [Auto Attendant Greetings](#auto-attendant-greetings)
  - [Numbers (Deprecated)](#numbers-deprecated)
- [Applications](#applications)
  - [Listing Applications](#listing-applications)
  - [Service Applications](#service-applications)
  - [Token Management](#token-management)
- [Wholesale](#wholesale)
  - [Customers and Locations](#customers-and-locations)
  - [Subscriber Provisioning](#subscriber-provisioning)
- [Bifrost](#bifrost)

---

## RedSky E911

**Module:** `wxcadm.redsky`

RedSky (now Intrado) powers Kari's Law / RAY BAUM's Act E911 compliance for Webex Calling in the US. wxcadm wraps the RedSky Horizon REST API (`api.wxc.e911cloud.com`) to manage buildings, locations, network discovery wire-maps, and device tracking -- all programmatically.

This is a **standalone** connection separate from the Webex API. RedSky has its own user accounts; you authenticate with a RedSky Horizon admin username and password, not a Webex token.

### Architecture: Building / Location

RedSky uses a two-tier hierarchy:

| Tier | wxcadm Class | Meaning |
|------|-------------|---------|
| **Building** | `RedSkyBuilding` | A physical building with a validated street address |
| **Location** | `RedSkyLocation` | A dispatchable zone within a building (floor, wing, zone) |

A Building contains one or more Locations. Network discovery entries (MAC, LLDP, BSSID, IP range) map to a **Location**, not a Building.

Webex Calling "Locations" are more abstract (could span a campus), so wxcadm deliberately does **not** auto-map between the two. The `add_building()` method bridges them when a 1:1 mapping is desired.

### Connecting to RedSky

```python
import wxcadm

redsky = wxcadm.RedSky(username="admin@domain.com", password="secret")
```

```python
RedSky.__init__(self, username: str, password: str)
```

Authenticates against `https://api.wxc.e911cloud.com/auth-service/login`. Stores an access token internally and handles token refresh automatically when a 401 is encountered.

**Key attributes after init:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `org_id` | `str` | The RedSky company/organization ID |

### Buildings

#### Listing buildings

```python
@property
RedSky.buildings -> list[RedSkyBuilding]
```

Returns all buildings in the account. Handles pagination internally (100 per page).

#### Finding a building

```python
RedSky.get_building_by_name(name: str) -> RedSkyBuilding | None
```

Case-insensitive name match.

```python
RedSky.get_building_by_webex_location(location: wxcadm.Location) -> RedSkyBuilding | None
```

Tries to match by supplemental data (last 20 chars of the Webex Location ID), then falls back to case-insensitive name match. This works when the building was originally created via `add_building()`.

#### Creating a building from a Webex Location

```python
RedSky.add_building(
    webex_location: Optional[wxcadm.Location] = None,
    address_string: Optional[str] = None,
    create_location: bool = True
) -> RedSkyBuilding
```

- Accepts either a Webex `Location` instance or a raw address string
- When `create_location=True` (default), also creates a "Default" `RedSkyLocation` inside the building, with the location's main number as the ECBN (Emergency Callback Number)
- Raises `ValueError` for non-US locations

**Example: bulk-add all Webex locations as RedSky buildings**

```python
import wxcadm

webex = wxcadm.Webex(access_token, fast_mode=True)
redsky = wxcadm.RedSky(redsky_user, redsky_pass)

for location in webex.org.locations:
    if location.address['country'] != "US":
        continue
    building = redsky.add_building(location, create_location=True)
    print(f"{building.name} -> {building.id}")
```

#### RedSkyBuilding attributes and methods

| Attribute / Method | Type / Signature | Description |
|--------------------|-----------------|-------------|
| `id` | `str` | Building ID |
| `name` | `str` | Building name |
| `address` | `dict` | Physical address (includes `normalizedAddress`, `streetAddress`) |
| `supplemental_data` | `str` | Custom data (wxcadm stores last 20 chars of Webex Location ID here) |
| `type` | `str` | Building type |
| `locations` | `list[RedSkyLocation]` | All locations within the building |
| `get_location_by_name(name: str)` | `-> RedSkyLocation \| None` | Case-insensitive location lookup |
| `add_location(location_name: str, ecbn: str = "", location_info: str = "")` | `-> bool` | Creates a new location in the building |
| `bssid_discovery` | `list[dict]` | All BSSID entries across all locations in this building |
| `lldp_discovery` | `list[dict]` | All LLDP entries across all locations in this building |
| `mac_discovery` | `list[dict]` | All MAC entries across all locations in this building |
| `ip_range_discovery` | `list[dict]` | All IP range entries across all locations in this building |

### Locations

`RedSkyLocation` represents a dispatchable zone inside a building.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Location ID (used in all network discovery mappings) |
| `name` | `str` | Location name (e.g., "Floor 1", "Default") |
| `address` | `dict` | Address information |
| `elin` | `dict` | Emergency Location Identification Number |
| `info` | `str` | Additional location info text |
| `address_entity_name` | `str` | Address entity name from RedSky |
| `bssid_discovery` | `list[dict]` | BSSID entries mapped to this location |
| `lldp_discovery` | `list[dict]` | LLDP entries mapped to this location |
| `mac_discovery` | `list[dict]` | MAC entries mapped to this location |
| `ip_range_discovery` | `list[dict]` | IP range entries mapped to this location |

### Network Discovery (Wire-Mapping)

RedSky determines a caller's dispatchable address by matching the device's network fingerprint against stored mappings. wxcadm supports all four discovery types.

#### MAC Address Discovery

```python
RedSky.get_mac_discovery(mac: Optional[str] = None) -> list | dict | None
```

Without args: returns all MAC mappings. With `mac`: returns the matching entry or `None`.

```python
RedSky.add_mac_discovery(
    mac: str,
    location: RedSkyLocation,
    description: str = ""
) -> dict
```

```python
RedSky.delete_mac_discovery(
    mac: Optional[str] = None,
    entry_id: Optional[str] = None
) -> bool
```

Pass either `mac` (looks up the entry for you) or `entry_id` (the `['id']` from a previous `get_mac_discovery()` call). If both are given, `entry_id` takes precedence.

#### LLDP Chassis/Port Discovery

```python
RedSky.get_lldp_discovery() -> list[dict]
```

Returns all chassis mappings, each with a nested `ports` list.

```python
RedSky.get_lldp_discovery_by_chassis(chassis_id: str) -> dict | None
```

```python
RedSky.add_lldp_discovery(
    chassis: str,
    location: RedSkyLocation,
    ports: list = None,       # e.g. ['1', '2', '3'] or ['B000B4BB1BF4:P1']
    description: str = ""
) -> dict
```

If `ports` are provided and the chassis already exists, only the ports are added. If the chassis doesn't exist, it's created first.

```python
RedSky.delete_lldp_chassis(chassis_id: str, delete_ports: bool = False) -> bool
```

When `delete_ports=True`, all port mappings are deleted before the chassis.

```python
RedSky.update_lldp_location(
    entry_id: str,
    chassis: str,
    new_location: RedSkyLocation,
    description: str
) -> bool
```

```python
RedSky.update_lldp_port_location(
    entry_id: str,
    chassis_id: str,
    port: str,
    new_location: RedSkyLocation,
    description: str
) -> bool
```

#### BSSID (WiFi Access Point) Discovery

```python
RedSky.get_bssid_discovery(bssid: Optional[str] = None) -> list | dict | None
```

```python
RedSky.add_bssid_discovery(
    bssid: str,
    location: RedSkyLocation,
    description: str = "",
    masking: bool = True        # apply default last-digit masking
) -> dict
```

```python
RedSky.delete_bssid_discovery(
    bssid: Optional[str] = None,
    entry_id: Optional[str] = None
) -> bool
```

#### IP Range Discovery

```python
RedSky.get_ip_range_discovery(
    ip_start: Optional[str] = None,
    ip_end: Optional[str] = None,
    range_for_ip: Optional[str] = None,   # find the range containing this IP
    type: Optional[str] = 'private'        # 'private' or 'public'
) -> list | dict | None
```

`range_for_ip` is particularly useful: pass an IP address and it returns the range entry that contains it.

```python
RedSky.add_ip_range_discovery(
    ip_start: str,
    ip_end: str,
    location: RedSkyLocation,
    description: str = ""
) -> dict
```

```python
RedSky.add_public_ip_range(
    ip_start: str,
    ip_end: str,
    description: str = ""
) -> dict
```

Public IP ranges are **not** mapped to a Location. They identify recognized corporate networks so RedSky accepts HELD requests from them.

```python
RedSky.delete_ip_range_discovery(ip_start: str, ip_end: str) -> bool
```

### HELD Devices

```python
@property
RedSky.held_devices -> list[dict]
```

Returns all HELD and HELD+ devices known to RedSky.

```python
RedSky.phones_without_location() -> list[dict]
```

Devices of type `HELD` (desk phones) that have no associated location.

```python
RedSky.clients_without_location() -> list[dict]
```

Devices of type `HELD_PLUS` (soft clients / Webex app) that have no associated location.

### Users

```python
@property
RedSky.users -> RedSkyUsers   # extends UserList
```

**RedSkyUsers** is a `UserList` of `RedSkyUser` dataclass instances.

```python
RedSkyUsers.get_by_email(email: str) -> RedSkyUser | None
```

**RedSkyUser** attributes and properties:

| Attribute / Property | Type | Description |
|---------------------|------|-------------|
| `id` | `str` | RedSky user ID |
| `email` | `str` | User's email (mapped from `heldUserId` in RedSky) |
| `user_locations` | `list[dict]` | Locations the user has manually entered (via Webex app or MyE911) |
| `devices` | `list[dict]` | Soft client devices associated with the user (not desk phones) |

```python
RedSky.get_all_locations() -> dict[str, list[dict]]
```

Returns `{'corporate': [...], 'personal': [...]}` -- corporate locations from the org and personal locations entered by individual users.

---

## Meraki Integration

**Module:** `wxcadm.meraki`

Provides automated synchronization between Meraki Dashboard device inventory and RedSky Network Discovery. This is the "killer feature" for E911 wire-mapping: network engineers tag devices in Meraki, and wxcadm pushes the correct LLDP/BSSID mappings to RedSky.

**Requires the `meraki` Python library:** install with `pip install wxcadm[meraki]` or `pip install meraki`.

### Tag-Based Location Convention

Meraki devices and switch ports are tagged with a `911-` prefix to indicate the RedSky Location name:

| Tag in Meraki | RedSky Location Name |
|---------------|---------------------|
| `911-Floor_1` | `Floor 1` |
| `911-West_Wing` | `West Wing` |
| `911-Server_Room` | `Server Room` |

Underscores in the tag are converted to spaces. Devices without a `911-` tag are ignored during audits.

**Building determination:** the Meraki device's address field is matched against RedSky building addresses. Matching is attempted first on the full normalized address, then falls back to street address only.

### Connecting to Meraki

```python
import wxcadm

meraki = wxcadm.Meraki(api_key="your_meraki_dashboard_api_key")
```

```python
Meraki.__init__(self, api_key: Optional[str] = None)
```

Initializes a connection to the Meraki Dashboard API.

```python
Meraki.get_orgs() -> list[MerakiOrg]
Meraki.get_org_by_name(name: str) -> MerakiOrg | None
```

```python
MerakiOrg.get_networks() -> list[MerakiNetwork]
MerakiOrg.get_network_by_name(name: str) -> MerakiNetwork | None
```

### Attaching RedSky to a Meraki Network

Before running an audit, a RedSky connection must be attached to the network:

```python
MerakiNetwork.attach_redsky(username: str, password: str) -> bool
```

This creates a `RedSky` instance and propagates it to all devices in the network.

### Running the Audit

```python
MerakiNetwork.redsky_audit(simulate: bool = False) -> MerakiAuditResults
```

The audit iterates over all switches and access points in the network:

**For switches (model contains "MS"):**
1. Matches the Meraki device address to a RedSky Building
2. Reads the `911-` tag on the switch to determine the chassis Location
3. Creates the Location in RedSky if it doesn't exist
4. Creates or updates the LLDP chassis mapping
5. For each tagged port, creates or updates the LLDP port mapping (port-level tags override the chassis Location)

**For access points (model contains "MR"):**
1. Matches the Meraki device address to a RedSky Building
2. Reads the `911-` tag to determine the AP Location
3. Creates the Location if it doesn't exist
4. Retrieves all BSSIDs from the AP's wireless status
5. Creates BSSID mappings for any enabled BSSIDs not already in RedSky

When `simulate=True`, no changes are made to RedSky. The `MerakiAuditResults` still reports what *would* have changed.

**Complete example:**

```python
import wxcadm

meraki = wxcadm.Meraki("meraki_api_key")
org = meraki.get_org_by_name("My Org")
network = org.get_network_by_name("Main Office")
network.attach_redsky(username="redsky_admin", password="redsky_pass")

# Dry run first
results = network.redsky_audit(simulate=True)
print(f"Would add {len(results.added_chassis)} chassis entries")
print(f"Would add {len(results.added_bssid)} BSSID entries")
print(f"Missing buildings: {results.missing_buildings}")

# Then run for real
results = network.redsky_audit()
```

### Audit Results

`MerakiAuditResults` has the following attributes (all are lists):

| Attribute | Contents |
|-----------|----------|
| `missing_buildings` | Addresses with no matching RedSky building |
| `added_locations` | `[{'building': RedSkyBuilding, 'location': str}]` |
| `switches` | All MerakiSwitch devices found |
| `access_points` | All MerakiWireless devices found |
| `added_chassis` | Chassis LLDP entries added |
| `added_ports` | Port LLDP entries added |
| `ignored_devices` | Devices skipped (no `911-` tag) |
| `updated_locations` | Existing entries whose Location was corrected |
| `added_bssid` | BSSID strings added to RedSky |

### Device Types

| Class | Base | Represents |
|-------|------|-----------|
| `MerakiDevice` | -- | Base class; holds `address`, `serial`, `mac`, `model`, `tags`, `name` |
| `MerakiSwitch` | `MerakiDevice` | Switch (model contains "MS"); has `get_ports() -> list[MerakiSwitchPort]` |
| `MerakiWireless` | `MerakiDevice` | Access point (model contains "MR"); has `get_bss_list() -> list[dict]` |
| `MerakiSwitchPort` | -- | Individual port; holds `switch`, `port_id`, `name`, `tags`, `enabled`, `type` |

All devices have `get_redsky_building(redsky: Optional[RedSky] = None) -> RedSkyBuilding | None` for manual building lookups outside of the audit workflow.

**Utility functions:**

```python
wxcadm.meraki.tags_decoder(tags: list, match_string: Optional[str] = "911-") -> Optional[str]
```

Finds the first tag matching `match_string`, strips the prefix, converts underscores to spaces.

---

## CP-API (Control Hub Internal API)

**Module:** `wxcadm.cpapi`

The CP-API is the **internal** API used by the Webex Control Hub web UI (`cpapi-a.wbx2.com`). wxcadm wraps it to expose operations that are **not available** through the public Webex developer API.

> **Warning:** All CP-API methods require an access token with CP-API scope. A standard developer token may not have this. If the scope is missing, methods raise `TokenError`.

```python
CPAPI.__init__(self, org: wxcadm.Org, access_token: str)
```

Normally instantiated automatically by Org methods, not manually.

### Voicemail PIN Management

```python
CPAPI.set_global_vm_pin(pin: str) -> bool
```

Sets the org-wide default voicemail PIN. Raises `ValueError` if the PIN doesn't comply with the security policy.

```python
CPAPI.clear_global_vm_pin() -> str
```

Disables the org-wide default PIN.

```python
CPAPI.reset_vm_pin(person: Person, pin: str = None) -> bool
```

Resets a user's VM PIN to the org default. If `pin` is provided, temporarily sets the global PIN to that value, resets the user, then clears it -- enabling per-user PIN assignment.

 The `reset_vm_pin` method's temporary global-pin-set-and-clear pattern will cause race conditions if called concurrently for multiple users. The source confirms there is no locking: it calls `set_global_vm_pin(pin)`, resets the user, then `clear_global_vm_pin()` sequentially with no mutex.

### Workspace Caller ID

```python
CPAPI.change_workspace_caller_id(
    workspace_id: str,    # CP-API workspace (Place) ID, not the Webex Calling ID
    name: str,            # externalCallerIdNamePolicy value
    number: str           # selected number value
) -> bool
```

Changes the external caller ID for a workspace. Note that the CP-API uses a different workspace ID than the Webex Calling API.

### Music on Hold Upload

```python
CPAPI.upload_moh_file(location_id: str, filename: str) -> bool
```

Uploads a WAV file as the custom Music on Hold for a location. `location_id` is the Base64-encoded Webex Location ID.

```python
CPAPI.set_custom_moh(location_id: str, filename: str) -> bool
```

Activates the uploaded custom MOH file for the location.

```python
CPAPI.set_default_moh(location_id: str) -> bool
```

Reverts to the system default MOH.

### Auto Attendant Greetings

```python
CPAPI.upload_aa_greeting(autoattendant, type: str, filename: str) -> bool
```

Uploads a WAV greeting file. `type` must be `"business_hours"` or `"after_hours"`.

```python
CPAPI.set_custom_aa_greeting(autoattendant, type: str, filename: str) -> bool
```

Activates the uploaded custom greeting and sets the greeting mode to `CUSTOM`.

### Numbers (Deprecated)

```python
CPAPI.get_numbers() -> list[dict]
```

 This method is marked as deprecated in the source with the comment: "This method is deprecated and will likely be removed eventually. The Webex API now supports a Numbers GET." The CP-API wrapper is unnecessary for orgs using the public API.

### Workspace Calling Location

```python
CPAPI.get_workspace_calling_location(workspace_id: str) -> Location
```

Returns the Webex Calling `Location` instance for a workspace. Useful because Webex Calling uses a different Location model than the standard Workspace Location.

---

## Applications

**Module:** `wxcadm.applications`

Manages Webex applications (integrations, bots, service apps) via the public `/v1/applications` API.

### Listing Applications

```python
WebexApplications(org: wxcadm.Org)   # auto-initialized; extends UserList
```

Accessed as `org.applications`.

```python
WebexApplications.org_apps -> list[WebexApplication]
```

Filters to only apps owned by the current org.

```python
WebexApplications.get_app_by_name(name: str) -> WebexApplication | list | None
```

Returns a single instance if one match, a list if multiple matches (same-name apps are allowed), or `None`.

```python
WebexApplications.get_app_by_id(id: str) -> WebexApplication
```

Checks local cache first, then calls the API if not found.

### Service Applications

```python
WebexApplications.add_service_application(
    name: str,
    contact_email: str,
    scopes: list,
    logo: str = "https://pngimg.com/uploads/hacker/hacker_PNG6.png"
) -> dict
```

Creates a Service App (formerly Authorized App). The response includes `clientSecret` -- **store it immediately**, as it will not be visible later.

 The wxcadm source docstring says: "The Service App capability is in Early Field Trial and may not be available for your Org." Whether this has since reached GA would require checking the live Webex developer portal.

**Service App authorization flow:**

1. **Developer** creates the app with `add_service_application()`
2. **Admin** of the target org retrieves the app by ID and calls `app.authorize()`
3. **Developer** calls `app.get_token(client_secret, target_org_id)` to get an access token
4. Token refresh via `app.get_token_refresh(client_secret, refresh_token)`

### Token Management

**WebexApplication** is a `@dataclass` with the following key methods:

```python
WebexApplication.authorize() -> bool
```

Authorizes the app for the org.

```python
WebexApplication.get_token(
    client_secret: str,
    target_org: wxcadm.Org | str     # Org instance or Base64 org ID
) -> dict
```

Returns `{'access_token': ..., 'expires_in': ..., 'refresh_token': ..., 'refresh_token_expires_in': ..., 'token_type': 'Bearer'}`.

```python
WebexApplication.get_token_refresh(client_secret: str, refresh_token: str) -> dict
```

```python
WebexApplication.regenerate_client_secret() -> str | False
```

Generates a new client secret if the original was lost or compromised.

```python
WebexApplication.delete()
```

Deletes the application entirely.

**Notable WebexApplication attributes (dataclass fields):**

`id`, `name`, `type`, `friendlyId`, `orgId`, `clientId`, `scopes`, `redirectUrls`, `botEmail`, `botPersonId`, `description`, `contactEmail`, `companyName`, `createdBy`, `created`, `modified`, `submissionStatus`

---

## Wholesale

**Module:** `wxcadm.wholesale`

For **service providers** using the Webex Wholesale program. Provides customer and subscriber management through the `/v1/wholesale/*` API endpoints.

```python
Wholesale.__init__(self, access_token: str)
```

Standalone entry point (not under `Webex` or `Org`). Uses the partner's access token.

### Customers and Locations

```python
@property
Wholesale.customers -> list[WholesaleCustomer]
```

```python
Wholesale.get_customer(
    id: str = None,
    name: str = None,
    spark_id: str = None
) -> WholesaleCustomer | None
```

Searches by ID, external name, or decoded Spark ID.

```python
@property
Wholesale.orgs -> list[Org]
```

Returns wxcadm `Org` instances for each wholesale customer, enabling the full wxcadm Org feature set on customer orgs.

**WholesaleCustomer** attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Customer ID |
| `org_id` | `str` | Webex Org ID |
| `external_id` | `str` | Partner-assigned external identifier (used as "name") |
| `address` | `dict` | Customer address |
| `status` | `str` | Customer status |
| `packages` | `list` | Assigned packages |
| `resource_details` | `dict` | Resource detail information |
| `spark_id` | `str` (property) | Decoded Spark ID |
| `locations` | `list[Location]` (property) | Customer's locations as wxcadm `Location` instances |

```python
WholesaleCustomer.get_location(
    id: str = None,
    name: str = None,
    spark_id: str = None
) -> Location | None
```

### Subscriber Provisioning

```python
WholesaleCustomer.add_subscriber(
    email: str,
    package: str,
    first_name: str,
    last_name: str,
    phone_number: str,
    extension: str,
    location: Location
) -> dict
```

Provisions a new subscriber (end user) under a wholesale customer with the specified calling package and location assignment.

---

## Bifrost

**Module:** `wxcadm.bifrost`

Bifrost is a **Webex internal API** (`bifrost-a.wbx2.com`) that exposes location data with additional configuration detail not available through the public API.

```python
Bifrost.__init__(self, org: wxcadm.Org, access_token: str)
```

Like CPAPI, this is normally instantiated automatically, not manually.

```python
Bifrost.get_location() -> list[dict]
```

Retrieves all locations from the Bifrost API and **enriches** the corresponding wxcadm `Location` instances by setting `location.bifrost_config` on each matched location. This attaches the full Bifrost configuration dict to the Location object.

 The exact contents of `bifrost_config` are not documented in the source. The `get_location()` method fetches from `bifrost-a.wbx2.com/api/v2/customers/{id}/locations`, paginates through all results, and assigns each raw location dict to the matching wxcadm `Location` object's `bifrost_config` attribute. The Bifrost module is exactly 52 lines with only the `get_location()` method.

---

## What's Unique to wxcadm (Not in wxc_sdk)

| Capability | Module | Why It Matters |
|-----------|--------|---------------|
| **RedSky E911 management** | `redsky` | Full CRUD for buildings, locations, and all 4 network discovery types. No other Python library wraps the RedSky Horizon API. |
| **Meraki-to-RedSky audit** | `meraki` | Automated wire-map sync from Meraki Dashboard to RedSky. Tag-driven, supports simulate mode. |
| **CP-API operations** | `cpapi` | VM PIN reset, MOH file upload, AA greeting upload, workspace caller ID -- none available via public API. |
| **Service App lifecycle** | `applications` | Create, authorize, token exchange, secret rotation for Service Applications. |
| **Wholesale provisioning** | `wholesale` | Partner-level customer and subscriber management. |
| **Bifrost location enrichment** | `bifrost` | Internal location config not exposed publicly. |

---

## Gotchas

- **CPAPI.reset_vm_pin() has a confirmed race condition.** The method temporarily sets the org-wide global VM PIN, resets the user's PIN, then clears the global PIN. No locking exists; concurrent calls for multiple users will collide.
- **CPAPI.get_numbers() is deprecated.** The source code comment confirms: "This method is deprecated and will likely be removed eventually. The Webex API now supports a Numbers GET."
- **Service Apps marked as "Early Field Trial" in wxcadm source.** The `add_service_application()` docstring warns EFT status. Whether this has reached GA would require checking the live Webex developer portal.
- **Bifrost config contents are undocumented.** `location.bifrost_config` is populated by `Bifrost.get_location()` with the raw location dict from the Bifrost API. The exact keys depend on the Bifrost API response and are not documented in wxcadm source. The module is exactly 52 lines with a single method.
- **CP-API requires a special token scope.** Standard developer tokens may lack CP-API scope. Methods raise `TokenError` if the scope is missing — there is no graceful fallback.
- **RedSky is a separate auth domain.** RedSky credentials (username/password for `api.wxc.e911cloud.com`) are completely independent from Webex tokens. The `add_building()` method only supports US locations and raises `ValueError` for non-US addresses.

---

## See Also

- [emergency-services.md](emergency-services.md) — wxc_sdk emergency services APIs for comparison with wxcadm's RedSky integration
- [wxcadm-locations.md](wxcadm-locations.md) — wxcadm location management including `enhanced_emergency_calling` and `set_enhanced_emergency_calling()` which interact with RedSky
