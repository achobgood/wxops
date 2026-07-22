<!-- Updated by playbook session 2026-03-18 -->
<!-- Updated by playbook session 2026-03-18 -->

# Emergency Services & E911

## Overview

Webex Calling E911 compliance requires three interlocking configurations:

| Layer | What It Configures | Base Endpoint |
|-------|--------------------|---------|
| **Emergency Call Notifications** | Org-level email alerts when any emergency call is placed | `telephony/config/emergencyCallNotification` |
| **Emergency Addresses** | Physical civic addresses associated with locations and phone numbers | `telephony/pstn/emergencyAddress` |
| **Emergency Callback Number (ECBN)** | Per-person/workspace/virtual-line callback number for return calls from PSAP | `telephony/config/{people,workspaces,virtualLines}/{id}/emergencyCallbackNumber` |

All three are needed for full E911 compliance in the United States. Emergency call notifications satisfy **Kari's Law** (U.S. Public Law 115-127), which requires that any emergency call from within an organization generates a notification. Emergency addresses and ECBN satisfy **RAY BAUM's Act** requirements for dispatchable location information.

## Table of Contents

1. [Emergency Call Notifications (Org-Level)](#1-emergency-call-notifications-org-level)
2. [Emergency Addresses](#2-emergency-addresses)
3. [Emergency Callback Number (ECBN)](#3-emergency-callback-number-ecbn)
4. [E911 Compliance Checklist](#4-e911-compliance-checklist)
5. [Raw HTTP Endpoints](#5-raw-http-endpoints)
6. [Gotchas (Cross-Cutting)](#gotchas-cross-cutting)
7. [See Also](#see-also)

---

## 1. Emergency Call Notifications (Org-Level)

### What It Does

When enabled, sends an email to a specified address every time someone in the organization dials emergency services (911 in the U.S.). This is the org-wide kill switch for Kari's Law compliance.

### Base Endpoint

```
telephony/config/emergencyCallNotification
```

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `emergencyCallNotificationEnabled` | boolean | When true, sends email on any emergency call |
| `allowEmailNotificationAllLocationEnabled` | boolean | When true, sends notifications for ALL locations (not just specific ones) |
| `emailAddress` | string | Email address that receives the notification |

### CLI Examples

```bash
# Read org-level emergency call notification settings
wxcli emergency-services show-emergency-call-notification-config

# Enable org-level emergency call notifications for all locations
wxcli emergency-services update-emergency-call-notification-config \
  --emergency-call-notification-enabled \
  --allow-email-notification-all-location-enabled \
  --email-address "security@company.com"

# Read location-level emergency call notification settings
wxcli emergency-services show-emergency-call-notification-locations Y2lzY29...locationId

# Enable location-level emergency call notification with a floor-specific email
wxcli emergency-services update-emergency-call-notification-locations Y2lzY29...locationId \
  --emergency-call-notification-enabled \
  --email-address "floor3-security@company.com"
```

---

## 2. Emergency Addresses

### What They Are

Emergency addresses are the physical civic addresses associated with phone numbers and locations. When someone dials 911, this address is transmitted to the PSAP (Public Safety Answering Point) so first responders know where to go.

Emergency addresses can be set at two levels:
- **Location level** -- default address for all numbers at that location
- **Phone number level** -- per-number override (e.g., for users on different floors or in different buildings at the same location)

### Base Endpoint

```
telephony/pstn
```

Required scopes:
- **Read/Lookup**: `spark-admin:telephony_pstn_read`
- **Write**: `spark-admin:telephony_pstn_write`

### Operations

#### Add Emergency Address to a Location

Adds a validated civic address to a location. Returns the new emergency address ID.

#### Lookup / Validate an Address

Returns a list of suggested addresses. If the input address is valid and unchanged, no errors are returned. If corrections were needed, the response includes the corrected address along with error details in each suggestion's `errors` list.

**Always validate before adding.** The PSAP database requires standardized addresses. This lookup normalizes the input and flags issues.

#### Update Emergency Address for a Location

Updates an existing emergency address, identified by location ID and address ID.

#### Update Emergency Address for a Phone Number

Sets a per-number emergency address that overrides the location default. **Passing an empty/None address deletes the custom address** and reverts the number to the location's default emergency address.

### Data Models

#### EmergencyAddress

| Field | Type | Description |
|-------|------|-------------|
| `address1` | string | Primary street (e.g., "100 Main Street") |
| `address2` | string | Secondary (e.g., "Suite 400", "Floor 3") |
| `city` | string | |
| `state` | string | State / Province / Region |
| `postalCode` | string | |
| `country` | string | Country code (e.g., "US") |

#### SuggestedEmergencyAddress

Extends `EmergencyAddress` with validation metadata:

| Field | Type | Description |
|-------|------|-------------|
| `meta` | object | Additional metadata |
| `errors` | array of AddressLookupError | Validation errors (present when input was corrected) |

#### AddressLookupError

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Error code |
| `title` | string | Error title |
| `detail` | string | Detailed error message |

### CLI Examples

```bash
# Validate/lookup an emergency address for a location (always do this first)
wxcli pstn create Y2lzY29...locationId \
  --address1 "100 Main Street" \
  --city "San Jose" \
  --state "CA" \
  --postal-code "95110" \
  --country "US"

# Add a validated emergency address to a location
wxcli pstn create-emergency-address Y2lzY29...locationId \
  --address1 "100 Main Street" \
  --address2 "Suite 400" \
  --city "San Jose" \
  --state "CA" \
  --postal-code "95110" \
  --country "US"

# Update an existing emergency address for a location
wxcli pstn update-emergency-addresses Y2lzY29...locationId Y2lzY29...addressId \
  --address1 "200 Main Street" \
  --city "San Jose" \
  --state "CA" \
  --postal-code "95110" \
  --country "US"

# Update the emergency address for a specific phone number (per-number override)
wxcli pstn update-emergency-address "+15551234567" \
  --json-body '{"emergencyAddress": {"address1": "100 Main Street", "address2": "Floor 3", "city": "San Jose", "state": "CA", "postalCode": "95110", "country": "US"}}'

# Clear a per-number override (reverts to location default) -- pass empty emergencyAddress
wxcli pstn update-emergency-address "+15551234567" \
  --json-body '{"emergencyAddress": null}'
```

---

## 3. Emergency Callback Number (ECBN)

### What It Is

The Emergency Callback Number (ECBN) is the phone number that the PSAP (Public Safety Answering Point) uses to call back if an emergency call is disconnected. This is critical for extension-only users who don't have a direct DID -- without an ECBN, the PSAP has no number to call back.

ECBN applies to:
- **People** (users)
- **Workspaces**
- **Virtual lines**

### Base Endpoints

ECBN works across three entity types, each with its own endpoint:
- **Person**: `telephony/config/people/{id}/emergencyCallbackNumber`
- **Workspace**: `telephony/config/workspaces/{id}/emergencyCallbackNumber`
- **Virtual Line**: `telephony/config/virtualLines/{id}/emergencyCallbackNumber`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

### ECBN Selection Options

There are multiple sources for where the ECBN comes from, in order of specificity:

| Selection | Enum Value | When To Use |
|-----------|-----------|-------------|
| **Direct Line** | `DIRECT_LINE` | User has their own DID -- PSAP calls back that number directly |
| **Location ECBN** | `LOCATION_ECBN` | Location has a dedicated ECBN different from the main number -- used for extension-only users |
| **Location Member Number** | `LOCATION_MEMBER_NUMBER` | Another user/workspace/virtual line's number at the same location -- used for multi-floor/multi-building locations to get a more accurate ESA |
| **None** | `NONE` | No selection (falls back to system default) |

### Operations

#### Read ECBN Settings

Returns the current ECBN configuration including the selected source, direct line info, location ECBN info, location member info, and the default fallback info.

#### Configure ECBN

Sets the ECBN source for a person, workspace, or virtual line. `locationMemberId` is required when `selected` is `LOCATION_MEMBER_NUMBER`.

- Set a user to use their direct line as ECBN: `selected: DIRECT_LINE`
- Set an extension-only user to use the location ECBN: `selected: LOCATION_ECBN`
- Set ECBN to another member's number (multi-floor scenario): `selected: LOCATION_MEMBER_NUMBER` with `locationMemberId` set to the other member's ID

#### Read ECBN Dependencies

Check what depends on this entity's ECBN before making changes. Returns:
- Whether this entity is the location's default ECBN
- Whether this entity uses itself as ECBN
- How many other members use this entity as their ECBN

### ECBN Fallback Logic

The system applies fallback rules when the configured ECBN source is unavailable:

1. If `DIRECT_LINE` is selected but the user has no valid DID, falls back to location ECBN
2. If `LOCATION_ECBN` is selected but no location ECBN is configured, falls back to the location's main number
3. If `LOCATION_MEMBER_NUMBER` is selected but the member's number is invalid, falls back to location ECBN or location main number

The `effectiveLevel` and `effectiveValue` fields on the response show which ECBN will actually be used after fallback resolution.

### Data Models

#### PersonECBN (Main Response)

| Field | Type | Description |
|-------|------|-------------|
| `selected` | enum: `DIRECT_LINE`, `LOCATION_ECBN`, `LOCATION_MEMBER_NUMBER`, `NONE` | The selected ECBN source |
| `directLineInfo` | object (PersonECBNDirectLine shape) | Info for the direct line option |
| `locationEcbnInfo` | object (PersonECBNDirectLine shape) | Info for the location ECBN option |
| `locationMemberInfo` | object (ECBNLocationMember shape) | Info for the location member option |
| `defaultInfo` | object (ECBNDefault shape) | Default fallback info when nothing else is configured |

#### PersonECBNDirectLine

Shape of `directLineInfo` and `locationEcbnInfo`:

| Field | Type | Description |
|-------|------|-------------|
| `phoneNumber` | string | The callback phone number |
| `firstName` | string | |
| `lastName` | string | |
| `effectiveLevel` | enum | What actually gets used after fallback |
| `effectiveValue` | string | The actual ECBN number after fallback |
| `quality` | enum: `RECOMMENDED`, `NOT_RECOMMENDED`, `INVALID` | |

#### ECBNLocationMember

Shape of `locationMemberInfo`:

| Field | Type | Description |
|-------|------|-------------|
| `phoneNumber` | string | Member's callback number |
| `firstName` | string | |
| `lastName` | string | |
| `memberId` | string | User/workspace/virtual line ID |
| `memberType` | string | Type of the member |
| `effectiveLevel` | enum | |
| `effectiveValue` | string | |
| `quality` | enum | |

#### ECBNDependencies

| Field | Type | Description |
|-------|------|-------------|
| `isLocationEcbnDefault` | boolean | Is this the location's default ECBN? |
| `isSelfEcbnDefault` | boolean | Does this entity use itself as ECBN? |
| `dependentMemberCount` | integer | How many others reference this entity's number |

#### ECBNDefault

Shape of `defaultInfo`:

| Field | Type | Description |
|-------|------|-------------|
| `effectiveValue` | string | The fallback ECBN number |
| `quality` | enum: `RECOMMENDED`, `NOT_RECOMMENDED`, `INVALID` | |

#### Enum Values

- **ECBN source** (see [ECBN Selection Options](#ecbn-selection-options) above): `DIRECT_LINE`, `LOCATION_ECBN`, `LOCATION_MEMBER_NUMBER`, `NONE` -- the configure operation only accepts the first three; `NONE` is read-only, returned when nothing is configured
- **`effectiveLevel`**: `DIRECT_LINE`, `LOCATION_ECBN`, `LOCATION_NUMBER`, `LOCATION_MEMBER_NUMBER`, `NONE`
- **`quality`**: `RECOMMENDED` (activated number on a user/workspace), `NOT_RECOMMENDED` (activated number on AA/HG/etc.), `INVALID` (inactive or non-existent number)

### CLI Examples

```bash
# --- Person ECBN ---

# Read a person's ECBN settings
wxcli emergency-services show-emergency-callback-number-people Y2lzY29...personId

# Set a person to use their direct line as ECBN
wxcli emergency-services update-emergency-callback-number-people Y2lzY29...personId \
  --json-body '{"selected": "DIRECT_LINE"}'

# Set an extension-only user to use the location ECBN
wxcli emergency-services update-emergency-callback-number-people Y2lzY29...personId \
  --json-body '{"selected": "LOCATION_ECBN"}'

# Set ECBN to another member's number (multi-floor scenario)
wxcli emergency-services update-emergency-callback-number-people Y2lzY29...personId \
  --location-member-id Y2lzY29...otherPersonId \
  --json-body '{"selected": "LOCATION_MEMBER_NUMBER", "locationMemberId": "Y2lzY29...otherPersonId"}'

# Check person ECBN dependencies before changing
wxcli emergency-services show-dependencies-emergency-callback-number-1 Y2lzY29...personId

# --- Workspace ECBN ---

# Read a workspace's ECBN settings
wxcli emergency-services show-emergency-callback-number-workspaces Y2lzY29...workspaceId

# Update a workspace's ECBN to use its direct line
wxcli emergency-services update-emergency-callback-number-workspaces Y2lzY29...workspaceId \
  --json-body '{"selected": "DIRECT_LINE"}'

# Check workspace ECBN dependencies
wxcli emergency-services show-dependencies-emergency-callback-number-2 Y2lzY29...workspaceId

# --- Virtual Line ECBN ---

# Read a virtual line's ECBN settings
wxcli emergency-services show-emergency-callback-number-virtual-lines Y2lzY29...virtualLineId

# Set a virtual line to use the location ECBN
wxcli emergency-services update-emergency-callback-number-virtual-lines Y2lzY29...virtualLineId \
  --json-body '{"selected": "LOCATION_ECBN"}'

# Check virtual line ECBN dependencies
wxcli emergency-services show-dependencies-emergency-callback-number-3 Y2lzY29...virtualLineId

# --- Hunt Group ECBN Dependencies ---

# Check hunt group ECBN dependencies (read-only -- no update for hunt groups)
wxcli emergency-services show-dependencies-emergency-callback-number Y2lzY29...huntGroupId

# --- ECBN Available Numbers ---

# List available ECBN numbers for a person
wxcli user-settings list-available-numbers-emergency-callback-number Y2lzY29...personId

# List available ECBN numbers for a workspace
wxcli workspace-settings list-available-numbers-emergency-callback-number Y2lzY29...workspaceId

# List available ECBN numbers for a virtual line
wxcli virtual-line-settings list-available-numbers-emergency-callback-number Y2lzY29...virtualLineId
```

---

## 4. E911 Compliance Checklist

To be fully compliant with Kari's Law and RAY BAUM's Act, an organization should:

### Kari's Law (Emergency Call Notifications)

- [ ] Enable `emergencyCallNotificationEnabled` at the org level
- [ ] Set `allowEmailNotificationAllLocationEnabled` to `true` (covers all locations)
- [ ] Configure `emailAddress` to a monitored mailbox (e.g., security, facilities)
- [ ] Optionally configure location-level notification overrides via `/telephony/config/locations/{locationId}/emergencyCallNotification` (separate from org-level settings; the location-level GET also returns the org-level settings in an `organization` object for reference)

### RAY BAUM's Act (Dispatchable Location)

- [ ] Every location has a validated emergency address (validate/lookup the address before adding it)
- [ ] Multi-building/multi-floor locations have per-number emergency addresses (update the emergency address for the specific phone number)
- [ ] All users with DIDs have `DIRECT_LINE` ECBN (default for users with phone numbers)
- [ ] Extension-only users have `LOCATION_ECBN` or `LOCATION_MEMBER_NUMBER` configured
- [ ] Virtual lines that can place calls have ECBN configured
- [ ] Location ECBN quality is `RECOMMENDED` (not `NOT_RECOMMENDED` or `INVALID`)
- [ ] Check ECBN dependencies before changing any ECBN to avoid breaking other users' callbacks

### Ongoing Maintenance

- When adding new locations: validate and add emergency address, configure location ECBN
- When adding new users: verify ECBN is correctly set (especially extension-only users)
- When moving users between locations: update both emergency address and ECBN
- When deactivating numbers: check ECBN dependencies first -- other users may reference that number

---

## Source

- U.S. Public Law 115-127 (Kari's Law) -- multi-line telephone system notification requirements
- RAY BAUM's Act Section 506 -- dispatchable location requirements for 911

---

## 5. Raw HTTP Endpoints

All endpoints below use the `api.session.rest_*` helper methods. URLs confirmed from working CLI implementations.

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

### CLI Examples (RedSky)

```bash
# Retrieve RedSky account details for the org
wxcli emergency-services show

# Create a RedSky account
wxcli emergency-services create --email "admin@company.com"

# Update RedSky service settings (enable the service with company credentials)
wxcli emergency-services update \
  --enabled \
  --company-id "company_id" \
  --secret "secret_key"

# Get org-level RedSky compliance status
wxcli emergency-services show-status-red-sky

# Update org-level RedSky compliance status
wxcli emergency-services update-status-red-sky \
  --json-body '{"complianceStatus": "ROUTING_ENABLED"}'

# Get org compliance status with per-location breakdown
wxcli emergency-services show-compliance-status --max 1000

# Login to RedSky admin account
wxcli emergency-services login-to-a \
  --email "admin@company.com" \
  --password "password"

# Get a location's RedSky parameters
wxcli emergency-services show-red-sky Y2lzY29...locationId

# Get a location's RedSky compliance status
wxcli emergency-services show-status-red-sky-1 Y2lzY29...locationId

# Update a location's RedSky compliance status
wxcli emergency-services update-status-red-sky-1 Y2lzY29...locationId \
  --json-body '{"complianceStatus": "ROUTING_ENABLED"}'

# Create a RedSky building address for a location
wxcli emergency-services create-building Y2lzY29...locationId \
  --alerting-email "security@company.com"

# Update a RedSky building address for a location
wxcli emergency-services update-building Y2lzY29...locationId \
  --json-body '{"alertingEmail": "new-security@company.com"}'
```

### Emergency Call Notifications (Org-Level)

#### Read Notification Settings

```
GET https://webexapis.com/v1/telephony/config/emergencyCallNotification
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/emergencyCallNotification")
# Returns: {
#   "emergencyCallNotificationEnabled": true,
#   "allowEmailNotificationAllLocationEnabled": true,
#   "emailAddress": "security@company.com"
# }
```

#### Update Notification Settings

```
PUT https://webexapis.com/v1/telephony/config/emergencyCallNotification
```

```python
body = {
    "emergencyCallNotificationEnabled": True,
    "allowEmailNotificationAllLocationEnabled": True,
    "emailAddress": "security@company.com"
}
api.session.rest_put(f"{BASE}/telephony/config/emergencyCallNotification", json=body)
```

### Emergency Call Notifications (Location-Level)

#### Read Location Notification Settings

```
GET https://webexapis.com/v1/telephony/config/locations/{locationId}/emergencyCallNotification
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/emergencyCallNotification")
```

#### Update Location Notification Settings

```
PUT https://webexapis.com/v1/telephony/config/locations/{locationId}/emergencyCallNotification
```

```python
body = {
    "emergencyCallNotificationEnabled": True,
    "emailAddress": "floor3-security@company.com"
}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{location_id}/emergencyCallNotification", json=body)
```

### Emergency Callback Number (ECBN) -- Person

#### Read Person ECBN

```
GET https://webexapis.com/v1/telephony/config/people/{personId}/emergencyCallbackNumber
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber")
# Returns: {
#   "selected": "DIRECT_LINE",
#   "directLineInfo": {"phoneNumber": "+15551234567", "effectiveLevel": "DIRECT_LINE", ...},
#   "locationEcbnInfo": {...},
#   "locationMemberInfo": {...},
#   "defaultInfo": {"effectiveValue": "+15551230000", "quality": "RECOMMENDED"}
# }
```

#### Update Person ECBN

```
PUT https://webexapis.com/v1/telephony/config/people/{personId}/emergencyCallbackNumber
```

```python
body = {
    "selected": "DIRECT_LINE"
    # or "selected": "LOCATION_ECBN"
    # or "selected": "LOCATION_MEMBER_NUMBER", "locationMemberId": "other_person_id"
}
api.session.rest_put(
    f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber", json=body)
```

#### Read Person ECBN Dependencies

```
GET https://webexapis.com/v1/telephony/config/people/{personId}/emergencyCallbackNumber/dependencies
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/people/{person_id}/emergencyCallbackNumber/dependencies")
# Returns: {
#   "isLocationEcbnDefault": false,
#   "isSelfEcbnDefault": true,
#   "dependentMemberCount": 3
# }
```

### Emergency Callback Number (ECBN) -- Workspace

#### Read Workspace ECBN

```
GET https://webexapis.com/v1/telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber")
```

#### Update Workspace ECBN

```
PUT https://webexapis.com/v1/telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber
```

```python
body = {"selected": "DIRECT_LINE"}
api.session.rest_put(
    f"{BASE}/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber", json=body)
```

#### Read Workspace ECBN Dependencies

```
GET https://webexapis.com/v1/telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber/dependencies
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber/dependencies")
```

### Emergency Callback Number (ECBN) -- Virtual Line

#### Read Virtual Line ECBN

```
GET https://webexapis.com/v1/telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/virtualLines/{vl_id}/emergencyCallbackNumber")
```

#### Update Virtual Line ECBN

```
PUT https://webexapis.com/v1/telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber
```

```python
body = {
    "selected": "LOCATION_ECBN"
    # or "selected": "LOCATION_MEMBER_NUMBER", "locationMemberId": "member_id"
}
api.session.rest_put(
    f"{BASE}/telephony/config/virtualLines/{vl_id}/emergencyCallbackNumber", json=body)
```

#### Read Virtual Line ECBN Dependencies

```
GET https://webexapis.com/v1/telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber/dependencies
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/virtualLines/{vl_id}/emergencyCallbackNumber/dependencies")
```

### Emergency Callback Number (ECBN) -- Hunt Group

#### Read Hunt Group ECBN Dependencies

```
GET https://webexapis.com/v1/telephony/config/huntGroups/{huntGroupId}/emergencyCallbackNumber/dependencies
```

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/huntGroups/{hg_id}/emergencyCallbackNumber/dependencies")
```

### RedSky E911 Integration

RedSky is a third-party E911 service provider. These endpoints manage the integration.

#### Get RedSky Account Details

```
GET https://webexapis.com/v1/telephony/config/redSky
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/redSky")
```

#### Create RedSky Account

```
POST https://webexapis.com/v1/telephony/config/redSky
```

```python
body = {
    "email": "admin@company.com",
    "orgPrefix": "ACME",
    # "partnerRedskyOrgId": "partner_org_id"
}
result = api.session.rest_post(f"{BASE}/telephony/config/redSky", json=body)
```

#### Get RedSky Service Settings
<!-- Updated by playbook session 2026-03-18 -->

```
GET https://webexapis.com/v1/telephony/config/redSky/serviceSettings
```

```python
result = api.session.rest_get(f"{BASE}/telephony/config/redSky/serviceSettings")
# Returns: {"enabled": true, "companyId": "...", "secret": "...", ...}
```

#### Update RedSky Service Settings

```
PUT https://webexapis.com/v1/telephony/config/redSky/serviceSettings
```

```python
body = {
    "enabled": True,
    "companyId": "company_id",
    "secret": "secret_key",
    # "externalTenantEnabled": False,
    # "email": "admin@company.com",
    # "password": "password"
}
api.session.rest_put(f"{BASE}/telephony/config/redSky/serviceSettings", json=body)
```

#### RedSky Login

```
POST https://webexapis.com/v1/telephony/config/redSky/actions/login/invoke
```

```python
body = {
    "email": "admin@company.com",
    "password": "password",
    # "redSkyOrgId": "org_id"
}
result = api.session.rest_post(f"{BASE}/telephony/config/redSky/actions/login/invoke", json=body)
```

#### RedSky Compliance Status (Org)

```
GET https://webexapis.com/v1/telephony/config/redSky/status
PUT https://webexapis.com/v1/telephony/config/redSky/status
GET https://webexapis.com/v1/telephony/config/redSky/complianceStatus
```

```python
# Get org status
result = api.session.rest_get(f"{BASE}/telephony/config/redSky/status")

# Update org compliance status
body = {"complianceStatus": "ROUTING_ENABLED"}
api.session.rest_put(f"{BASE}/telephony/config/redSky/status", json=body)

# Get compliance status with per-location breakdown
result = api.session.rest_get(f"{BASE}/telephony/config/redSky/complianceStatus", params={
    "max": 1000,
    # "order": "ASC|DSC"
})
```

#### RedSky Location Settings

```
GET https://webexapis.com/v1/telephony/config/locations/{locationId}/redSky
GET https://webexapis.com/v1/telephony/config/locations/{locationId}/redSky/status
PUT https://webexapis.com/v1/telephony/config/locations/{locationId}/redSky/status
```

```python
# Get location RedSky parameters
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{location_id}/redSky")

# Get location compliance status
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{location_id}/redSky/status")

# Update location compliance status
body = {"complianceStatus": "ROUTING_ENABLED"}
api.session.rest_put(f"{BASE}/telephony/config/locations/{location_id}/redSky/status", json=body)
```

#### RedSky Building Address

```
POST https://webexapis.com/v1/telephony/config/locations/{locationId}/redSky/building
PUT  https://webexapis.com/v1/telephony/config/locations/{locationId}/redSky/building
```

```python
# Create building address with alert email
body = {"alertingEmail": "security@company.com"}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{location_id}/redSky/building", json=body)

# Update building address
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{location_id}/redSky/building", json=body)
```

### Emergency Address (PSTN)

These endpoints are in the PSTN API surface, not the emergency services surface.

#### Lookup/Validate Emergency Address

```
POST https://webexapis.com/v1/telephony/pstn/emergencyAddress/lookup
```

```python
body = {
    "locationId": "loc_id",
    "address": {
        "address1": "100 Main Street",
        "city": "San Jose",
        "state": "CA",
        "postalCode": "95110",
        "country": "US"
    }
}
result = api.session.rest_post(f"{BASE}/telephony/pstn/emergencyAddress/lookup", json=body)
# Returns: list of SuggestedEmergencyAddress with corrections and/or errors
```

#### Add Emergency Address to a Location

```
POST https://webexapis.com/v1/telephony/pstn/emergencyAddress
```

```python
body = {
    "locationId": "loc_id",
    "address": {
        "address1": "100 Main Street",
        "address2": "Suite 400",
        "city": "San Jose",
        "state": "CA",
        "postalCode": "95110",
        "country": "US"
    }
}
result = api.session.rest_post(f"{BASE}/telephony/pstn/emergencyAddress", json=body)
address_id = result.get("id")
```

#### Update Emergency Address for a Location

```
PUT https://webexapis.com/v1/telephony/pstn/emergencyAddress/{addressId}
```

```python
body = {
    "locationId": "loc_id",
    "address": {
        "address1": "200 Main Street",
        "city": "San Jose",
        "state": "CA",
        "postalCode": "95110",
        "country": "US"
    }
}
api.session.rest_put(f"{BASE}/telephony/pstn/emergencyAddress/{address_id}", json=body)
```

#### Update Emergency Address for a Phone Number

```
PUT https://webexapis.com/v1/telephony/pstn/phoneNumbers/{phoneNumber}/emergencyAddress
```

```python
body = {
    "emergencyAddress": {
        "address1": "100 Main Street",
        "address2": "Floor 3",
        "city": "San Jose",
        "state": "CA",
        "postalCode": "95110",
        "country": "US"
    }
}
api.session.rest_put(
    f"{BASE}/telephony/pstn/phoneNumbers/{phone_number}/emergencyAddress", json=body)
```

**Gotcha:** Passing an empty/None `emergencyAddress` deletes the custom address and reverts the number to the location's default.

---

## Gotchas (Cross-Cutting)

- **ECBN update commands use `--json-body` for the `selected` field.** The `selected` enum value (`DIRECT_LINE`, `LOCATION_ECBN`, `LOCATION_MEMBER_NUMBER`) is a body parameter, not a CLI flag. Always pass it via `--json-body '{"selected": "DIRECT_LINE"}'`.
- **Always validate before adding an emergency address.** Use `wxcli pstn create <locationId>` (the lookup/validate endpoint) before `wxcli pstn create-emergency-address`. The PSAP database requires standardized addresses; the lookup normalizes your input and flags corrections.
- **Passing null emergencyAddress deletes the per-number override.** When using `wxcli pstn update-emergency-address`, sending `--json-body '{"emergencyAddress": null}'` reverts the phone number to its location's default emergency address.
- **Check ECBN dependencies before deactivating numbers.** Run `show-dependencies-emergency-callback-number-*` for the entity type before deactivating a number or changing ECBN. Other users may reference that number as their ECBN via `LOCATION_MEMBER_NUMBER`.
- **Hunt groups only support dependency reads, not ECBN updates.** The `show-dependencies-emergency-callback-number` command (hunt group variant) is read-only. Hunt groups do not have a configurable ECBN -- they inherit from the location.
- **RedSky commands are separate from native E911.** The `emergency-services show/create/update` commands (RedSky) are for third-party E911 integration and are distinct from the native Webex emergency call notification and ECBN commands. Not all orgs use RedSky.
- **Location-level notification settings are separate from org-level.** The org-level `show-emergency-call-notification-config` and the location-level `show-emergency-call-notification-locations` are independent endpoints. Enabling at the org level with `allow-email-notification-all-location-enabled` covers all locations, but individual locations can have their own email addresses.

---

## Third-Party E911 Provider Portal (RedSky / Intrado)

The Webex-side RedSky integration endpoints above (`/telephony/config/redSky/*`) manage the *link* between Webex and a third-party dynamic-E911 provider from the Webex API, using your Webex token. The provider itself (RedSky / Intrado) also runs its **own** portal and API (`api.wxc.e911cloud.com`) with a **separate login** — not a Webex token — used to manage buildings, dispatchable locations, network wire-maps, and device tracking. That portal is outside the Webex API surface; configure it in the provider's own console. Webex-native E911 (emergency call notifications, emergency addresses, ECBN) is fully covered above and needs no third-party portal.

---

## See Also

- **[person-call-settings-behavior.md](person-call-settings-behavior.md)** — ECBN configuration is shared between person, workspace, and virtual line settings. That doc covers the same ECBN endpoints from the person-settings perspective, including how ECBN integrates with other call behavior settings.
- **[virtual-lines.md](virtual-lines.md)** — Virtual lines that can place calls need ECBN configured. The ECBN endpoints are listed in the virtual line call settings table there.
