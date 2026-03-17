# Provisioning Reference

User, license, and location provisioning for Webex Calling via the `wxc_sdk` Python SDK.

---

## Table of Contents

1. [Required Scopes](#required-scopes)
2. [People API](#people-api)
3. [Licenses API](#licenses-api)
4. [Locations API](#locations-api)
5. [Organization API](#organization-api)
6. [Provisioning Workflow](#provisioning-workflow)
7. [Data Models](#data-models)
8. [Common Gotchas](#common-gotchas)

---

## Required Scopes

| Operation | Scope(s) Required |
|-----------|-------------------|
| List/view people | `spark:people_read` (own info) or `spark-admin:people_read` (all org users) |
| Create/update/delete people | `spark-admin:people_write` **and** `spark-admin:people_read` |
| List licenses | `spark-admin:licenses_read` |
| Assign licenses (PATCH) | `spark-admin:people_write` |
| List/view locations | `spark-admin:locations_read`, `spark-admin:people_read`, or `spark-admin:device_read` |
| Create/update/delete locations | `spark-admin:locations_write` |
| Delete organization | `spark-admin:organizations_write` |
| Enable location for calling | `spark-admin:locations_write` <!-- NEEDS VERIFICATION --> |

All provisioning operations require an **administrator auth token**. Non-admin tokens can only read people via `spark:people_read` with email or displayName filters.

---

## People API

Base path: `/v1/people`

### Listing People

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi()

# List ALL people (admin only, no filter required)
all_users = list(api.people.list())

# Filter by email
user = next(api.people.list(email='jsmith@example.com'), None)

# Filter by display name (prefix match)
users = list(api.people.list(display_name='John'))

# Filter by location
users_at_hq = list(api.people.list(location_id='<location_id>'))

# List by IDs (up to 85)
users = list(api.people.list(id_list=['id1', 'id2', 'id3']))
```

### The `calling_data=True` Parameter (Critical)

To get calling-specific fields (`location_id`, `phone_numbers` with `work_extension` type, `extension`), you **must** pass `calling_data=True`. Without it, these fields are absent from the response.

```python
# WITHOUT calling_data -- location_id and calling fields are missing
user = api.people.details(person_id='<id>')
print(user.location_id)  # None

# WITH calling_data -- calling fields populated
user = api.people.details(person_id='<id>', calling_data=True)
print(user.location_id)  # 'Y2lzY29zcGF...'
print(user.extension)    # '1001'
```

This applies to `list()`, `details()`, `create()`, and `update()`.

### Identifying Calling Users

A calling user is one with a `location_id` set. The SDK examples demonstrate two approaches:

**Approach 1 -- Filter on `location_id` (synchronous)**

```python
# From examples/calling_users.py
calling_users = [user for user in api.people.list(calling_data=True)
                 if user.location_id]
```

**Approach 2 -- Filter on calling license IDs (async)**

```python
# From examples/calling_users_async.py
calling_license_ids = set(
    lic.license_id for lic in await api.licenses.list()
    if lic.webex_calling
)
calling_users = [
    user async for user in api.people.list_gen()
    if any(lic_id in calling_license_ids for lic_id in user.licenses)
]
```

### Creating a Person

At minimum, one of `displayName`, `firstName`, or `lastName` is required. For a **Webex Calling** user, you must also provide `phoneNumbers` or `extension`, `locationId`, and `licenses` in the same request.

```python
from wxc_sdk.people import Person, PhoneNumber, PhoneNumberType

new_user = api.people.create(
    settings=Person(
        emails=['jsmith@example.com'],
        display_name='John Smith',
        first_name='John',
        last_name='Smith',
        licenses=['<calling_license_id>'],
        location_id='<location_id>',
        extension='1001',
        phone_numbers=[PhoneNumber(type=PhoneNumberType.work, value='5551234567')]
    ),
    calling_data=True
)
```

**Important notes on create:**
- A POST that returns 400 may **still have created the person**. Check with a GET before retrying.
- SIP addresses are assigned asynchronously -- they may not appear in the POST response. Verify with a subsequent GET.
- When assigning multiple licenses, the system assigns all valid ones and silently skips invalid ones.

### Updating a Person

The update is a **full PUT** -- you must include all fields, not just the changed ones. Standard pattern: GET details first, modify, then PUT.

```python
# GET current state
user = api.people.details(person_id='<id>', calling_data=True)

# Modify
user.extension = '2002'

# PUT back
updated = api.people.update(person=user, calling_data=True)
```

**Key constraints on update:**
- `location_id` can only be set when **first assigning** a calling license. It cannot be changed for an existing calling user.
- The `extension` field value should **not** include the location routing prefix. The `work_extension` phone number in the response *will* include it, but when setting `extension` on update, omit the prefix.
- When updating a user with multiple email addresses, the **primary email must be listed first** in the array.
- Some licenses are implicitly assigned by the system and cannot be removed. If you get an error about implicit licenses, make sure they remain in the `licenses` array.
- A PUT that returns an error **may still have partially modified** the person. Always do a GET afterward to verify current state.

### Deleting a Person

```python
api.people.delete_person(person_id='<id>')
```

Required roles: Full Administrator, User Administrator, or External Full Administrator.

### Get Current User

```python
me = api.people.me(calling_data=True)
```

---

## Licenses API

Base path: `/v1/licenses`

### Listing Licenses

```python
all_licenses = api.licenses.list()

for lic in all_licenses:
    print(f'{lic.name}: {lic.consumed_units}/{lic.total_units}')
```

### Finding Specific Licenses

The `License` model has convenience properties for common license types:

| Property | License Name Matched |
|----------|---------------------|
| `lic.webex_calling_professional` | `"Webex Calling - Professional"` |
| `lic.webex_calling_basic` | `"Webex Calling - Basic"` |
| `lic.webex_calling_workspaces` | `"Webex Calling - Workspaces"` |
| `lic.webex_calling` | Any of the above three |
| `lic.cx_essentials` | `"Customer Experience - Essential"` |

**Find the Webex Calling Professional license:**

```python
wxc_pro_license = next(
    (lic for lic in api.licenses.list()
     if lic.webex_calling_professional),
    None
)
```

**Find an available calling license (with capacity):**

```python
def get_calling_license(api):
    """Get ID of an available calling license with remaining capacity."""
    licenses = [
        lic for lic in api.licenses.list()
        if lic.webex_calling and not lic.webex_calling_workspaces
    ]
    available = next(
        (lic for lic in licenses
         if lic.consumed_units < lic.total_units),
        None
    )
    return available.license_id if available else None
```

**Find and store both Calling and UCM licenses (for migration):**

```python
# From Cisco Live lab
wxc_pro_license = None
ucm_license = None

for lic in api.licenses.list():
    if lic.name == 'Webex Calling - Professional':
        wxc_pro_license = lic
    if lic.name == 'Unified Communication Manager (UCM)':
        ucm_license = lic
```

### License Details

```python
license_detail = api.licenses.details(license_id='<id>')
print(f'Name: {license_detail.name}')
print(f'Used: {license_detail.consumed_units}/{license_detail.total_units}')
print(f'By users: {license_detail.consumed_by_users}')
print(f'By workspaces: {license_detail.consumed_by_workspaces}')
```

### Listing Users Assigned to a License

```python
users = list(api.licenses.assigned_users(license_id='<id>'))
for user in users:
    print(f'{user.display_name} ({user.email}) - {user.type}')
```

### Assigning Licenses to Users (PATCH Method)

The `assign_licenses_to_users` method is the **recommended approach** for license assignment, especially for Webex Calling. It supports adding and removing licenses in a single call, and it handles calling-specific properties (location, phone number, extension).

```python
from wxc_sdk.licenses import LicenseRequest, LicenseProperties, LicenseRequestOperation

# Assign a Webex Calling license with location and extension
api.licenses.assign_licenses_to_users(
    person_id='<person_id>',
    licenses=[
        LicenseRequest(
            id='<calling_license_id>',
            operation=LicenseRequestOperation.add,  # default is 'add'
            properties=LicenseProperties(
                location_id='<location_id>',
                extension='1001'
            )
        )
    ]
)
```

**With phone number instead of extension:**

```python
api.licenses.assign_licenses_to_users(
    person_id='<person_id>',
    licenses=[
        LicenseRequest(
            id='<calling_license_id>',
            properties=LicenseProperties(
                location_id='<location_id>',
                phone_number='+15551234567'
            )
        )
    ]
)
```

**Removing a license:**

```python
api.licenses.assign_licenses_to_users(
    person_id='<person_id>',
    licenses=[
        LicenseRequest(
            id='<license_id_to_remove>',
            operation=LicenseRequestOperation.remove
        )
    ]
)
```

**Combined: remove UCM + add Calling in one call:**

```python
api.licenses.assign_licenses_to_users(
    person_id='<person_id>',
    licenses=[
        LicenseRequest(
            id=ucm_license.license_id,
            operation=LicenseRequestOperation.remove
        ),
        LicenseRequest(
            id=wxc_pro_license.license_id,
            operation=LicenseRequestOperation.add,
            properties=LicenseProperties(
                location_id='<location_id>',
                extension='1001'
            )
        )
    ]
)
```

**LicenseProperties requirements for Calling licenses:**
- Either `phone_number` or `extension` is mandatory.
- If `phone_number` is not provided, then `location_id` is mandatory.

You can identify the user by either `email` or `person_id` (at least one required).

---

## Locations API

Base path: `/v1/locations`

### Listing Locations

```python
# All locations
locations = list(api.locations.list())

# Filter by name (case-insensitive contains match)
locations = list(api.locations.list(name='headquarters'))

# Filter by ID
locations = list(api.locations.list(location_id='<id>'))
```

### Find Location by Exact Name

The SDK provides a convenience method not available in the raw API:

```python
location = api.locations.by_name('Pod18')
if location:
    print(f'Found: {location.name} (ID: {location.location_id})')
```

This iterates the list internally and matches on exact name equality.

### Location Details

```python
location = api.locations.details(location_id='<id>')
print(f'Name: {location.name}')
print(f'Address: {location.address.address1}, {location.address.city}, {location.address.state}')
print(f'Timezone: {location.time_zone}')
```

### Creating a Location

All of the following parameters are **required**:
- `name`
- `time_zone`
- `preferred_language`
- `announcement_language`
- `address1`, `city`, `state`, `postal_code`, `country`

```python
location_id = api.locations.create(
    name='San Jose Office',
    time_zone='America/Los_Angeles',
    preferred_language='en_us',
    announcement_language='en_us',
    address1='123 Main St',
    city='San Jose',
    state='CA',
    postal_code='95113',
    country='US'
)
print(f'Created location: {location_id}')
```

Optional parameters: `address2`, `latitude`, `longitude`, `notes`.

**Name length constraint:** While the API supports up to 256 characters, locations that will be **enabled for Webex Calling** must have names with a maximum of **80 characters**.

The return value is the new location's ID string.

### Updating a Location

```python
location = api.locations.details(location_id='<id>')
location.name = 'San Jose HQ'
api.locations.update(location_id=location.location_id, settings=location)
```

The same 80-character name limit applies if the location is calling-enabled.

### Deleting a Location

```python
api.locations.delete(location_id='<id>')
```

**Prerequisite:** Webex Calling must be **disabled** for the location before it can be deleted.

### Enabling a Location for Webex Calling

Creating a location via the Locations API does **not** automatically enable it for Webex Calling. You must use the separate Location Call Settings API:

<!-- NEEDS VERIFICATION -->
```python
# Enable via the telephony location API
# This is a separate API endpoint, not part of LocationsApi
api.telephony.location.enable_for_calling(location_id='<id>', ...)
```

The `announcement_language` field on the Location model is described as "required when enabling a location for Webex Calling."

### Floors

Locations support floor management for workspace organization:

```python
# List floors
floors = api.locations.list_floors(location_id='<id>')

# Create a floor
floor = api.locations.create_floor(location_id='<id>', floor_number=3, display_name='3rd Floor')

# Get floor details
floor = api.locations.floor_details(location_id='<id>', floor_id='<floor_id>')

# Update a floor
floor.display_name = 'Third Floor - Engineering'
api.locations.update_floor(floor=floor)

# Delete a floor
api.locations.delete_floor(location_id='<id>', floor_id='<floor_id>')
```

---

## Organization API

Base path: `/v1/organizations`

### Listing Organizations

```python
orgs = api.organizations.list()

# With XSI (BroadSoft) endpoint data
orgs = api.organizations.list(calling_data=True)
```

### Organization Details

```python
org = api.organizations.details(org_id='<id>', calling_data=True)
print(f'Name: {org.display_name}')
print(f'XSI Actions: {org.xsi_actions_endpoint}')
print(f'XSI Events: {org.xsi_events_endpoint}')
print(f'XSI Domain: {org.xsi_domain}')
```

The `calling_data=True` parameter returns XSI (BroadSoft) endpoint values:
- `xsi_actions_endpoint` -- base path to xsi-actions
- `xsi_events_endpoint` -- base path to xsi-events
- `xsi_events_channel_endpoint` -- base path to xsi-events-channel
- `xsi_domain` -- api-prepended bcBaseDomain for the org

### Deleting an Organization

```python
api.organizations.delete(org_id='<id>')
```

Requires authorization from a user with the **Full Administrator Role**. Deletion may take up to 10 minutes to complete after the response returns.

---

## Provisioning Workflow

Step-by-step process to enable a user for Webex Calling. Based on the Cisco Live provisioning lab and SDK test patterns.

### Method A: Using People API (update licenses on Person object)

This approach manipulates the `licenses` array directly on the Person object.

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi()

# ── Step 1: Find the required licenses ──────────────────────────────
wxc_pro_license = None
ucm_license = None

for lic in api.licenses.list():
    if lic.name == 'Webex Calling - Professional':
        wxc_pro_license = lic
    if lic.name == 'Unified Communication Manager (UCM)':
        ucm_license = lic

print(f'WxC Pro: {wxc_pro_license.license_id}')
print(f'UCM:     {ucm_license.license_id if ucm_license else "not found"}')

# ── Step 2: Find the target location ────────────────────────────────
location = api.locations.by_name('San Jose Office')
print(f'Location: {location.name} (ID: {location.location_id})')

# ── Step 3: Get the user's full details ─────────────────────────────
user = next(api.people.list(email='jsmith@example.com'), None)
user_details = api.people.details(person_id=user.person_id, calling_data=True)

# ── Step 4: Update licenses and location ────────────────────────────
# Add Webex Calling Professional license
if wxc_pro_license.license_id not in user_details.licenses:
    user_details.licenses.append(wxc_pro_license.license_id)

# Remove UCM license (if migrating from on-prem)
if ucm_license and ucm_license.license_id in user_details.licenses:
    user_details.licenses.remove(ucm_license.license_id)

# Set location and extension
user_details.location_id = location.location_id
user_details.extension = '1001'

# ── Step 5: Push the update ─────────────────────────────────────────
updated_user = api.people.update(person=user_details, calling_data=True)

# ── Step 6: Verify ──────────────────────────────────────────────────
verified = api.people.details(person_id=updated_user.person_id, calling_data=True)
assert verified.location_id is not None
assert wxc_pro_license.license_id in verified.licenses
print(f'User {verified.display_name} enabled for calling at {location.name}')
```

### Method B: Using Licenses PATCH API (recommended for new provisioning)

This approach uses the dedicated `assign_licenses_to_users` PATCH endpoint, which is cleaner for new license assignments and supports calling-specific properties natively.

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.licenses import LicenseRequest, LicenseProperties
from wxc_sdk.people import Person

api = WebexSimpleApi()

# ── Step 1: Find the calling license ────────────────────────────────
calling_license_id = next(
    (lic.license_id for lic in api.licenses.list()
     if lic.webex_calling_professional
     and lic.consumed_units < lic.total_units),
    None
)

# ── Step 2: Find the target location ────────────────────────────────
location = api.locations.by_name('San Jose Office')

# ── Step 3: Create the user (if new) ────────────────────────────────
new_user = api.people.create(
    settings=Person(
        emails=['jsmith@example.com'],
        display_name='John Smith',
        first_name='John',
        last_name='Smith'
    )
)

# ── Step 4: Assign calling license with location and extension ──────
response = api.licenses.assign_licenses_to_users(
    person_id=new_user.person_id,
    licenses=[
        LicenseRequest(
            id=calling_license_id,
            properties=LicenseProperties(
                location_id=location.location_id,
                extension='1001'
            )
        )
    ]
)

# ── Step 5: Verify ──────────────────────────────────────────────────
verified = api.people.details(person_id=new_user.person_id, calling_data=True)
assert calling_license_id in verified.licenses
assert verified.location_id is not None
print(f'License response: {response}')
```

### Method B is preferred when:
- You are provisioning net-new users (create user, then assign license separately).
- You need to set calling-specific properties (`phone_number`, `extension`, `location_id`) as part of the license assignment in one atomic call.
- You are bulk-provisioning users created via SCIM 2.0.

### Method A is preferred when:
- You are migrating existing users (e.g., removing UCM, adding WxC).
- You need to modify other Person fields at the same time as license changes.

---

## Data Models

### Person

| Field | Type | Notes |
|-------|------|-------|
| `person_id` | `str` | Unique ID (aliased from `id` in JSON) |
| `emails` | `list[str]` | Currently only one email supported |
| `phone_numbers` | `list[PhoneNumber]` | Requires `calling_data=True` to populate |
| `extension` | `str` | Webex Calling extension (no routing prefix). Requires `calling_data=True` |
| `location_id` | `str` | Calling location. Requires `calling_data=True`. Only settable on initial calling license assignment |
| `display_name` | `str` | Full name |
| `first_name` | `str` | |
| `last_name` | `str` | |
| `org_id` | `str` | Organization |
| `licenses` | `list[str]` | License IDs assigned to user |
| `roles` | `list[str]` | Role IDs |
| `department` | `str` | Business department |
| `manager` | `str` | Manager identifier |
| `manager_id` | `str` | Manager's Person ID |
| `title` | `str` | Job title |
| `addresses` | `list[PersonAddress]` | Postal addresses |
| `site_urls` | `list[str]` | Webex Meetings site URLs |
| `timezone` | `str` | User's timezone |
| `status` | `PeopleStatus` | Presence status (org members only) |
| `invite_pending` | `bool` | Awaiting activation (admin-visible only) |
| `login_enabled` | `bool` | Can use Webex (admin-visible only) |
| `person_type` | `PersonType` | `person`, `bot`, or `appuser` |
| `sip_addresses` | `list[SipAddress]` | Read-only SIP addresses |
| `created` | `datetime` | Read-only |
| `last_modified` | `datetime` | Read-only |

**Helper properties on Person:**
- `person_id_uuid` -- Person ID decoded to UUID format
- `plus_e164` -- List of +E.164 phone numbers
- `tn` -- First +E.164 phone number (primary TN)

### PhoneNumber

| Field | Type | Values |
|-------|------|--------|
| `number_type` | `PhoneNumberType` | `work`, `work_extension`, `mobile`, `fax`, `enterprise`, `alternate1`, `alternate2` |
| `value` | `str` | The phone number or extension value |
| `primary` | `bool` | Whether this is the primary number |

Note: `work_extension` values include the location **routing prefix** prepended to the extension. When setting `extension` on a Person, do **not** include the routing prefix.

### License

| Field | Type | Notes |
|-------|------|-------|
| `license_id` | `str` | Unique ID (aliased from `id`) |
| `name` | `str` | Human-readable license name |
| `total_units` | `int` | Total allocated |
| `consumed_units` | `int` | Total consumed |
| `consumed_by_users` | `int` | Consumed by users |
| `consumed_by_workspaces` | `int` | Consumed by workspaces |
| `subscription_id` | `str` | Associated subscription |
| `site_url` | `str` | Webex Meetings site (if applicable) |
| `site_type` | `SiteType` | `Control Hub managed site`, `Linked site`, or `Site Admin managed site` |

**Helper properties on License:**
- `webex_calling` -- True if any calling license type
- `webex_calling_professional` -- True if name is `"Webex Calling - Professional"`
- `webex_calling_basic` -- True if name is `"Webex Calling - Basic"`
- `webex_calling_workspaces` -- True if name is `"Webex Calling - Workspaces"`
- `cx_essentials` -- True if name is `"Customer Experience - Essential"`

### LicenseRequest (for PATCH assignment)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | License ID to add/remove |
| `operation` | `LicenseRequestOperation` | `add` (default) or `remove` |
| `properties` | `LicenseProperties` | Location, phone, extension (for calling licenses) |

### LicenseProperties

| Field | Type | Notes |
|-------|------|-------|
| `location_id` | `str` | Required if `phone_number` not provided |
| `phone_number` | `str` | Work phone number (E.164) |
| `extension` | `str` | Webex Calling extension |

Either `phone_number` or `extension` is mandatory for Calling license assignment. If `phone_number` is omitted, `location_id` is mandatory.

### Location

| Field | Type | Notes |
|-------|------|-------|
| `location_id` | `str` | Unique ID (aliased from `id`) |
| `name` | `str` | Max 80 chars if calling-enabled |
| `org_id` | `str` | Organization |
| `address` | `LocationAddress` | Physical address |
| `time_zone` | `str` | IANA timezone |
| `preferred_language` | `str` | Default email language |
| `announcement_language` | `str` | Phone announcement language. Required for calling enablement |
| `latitude` | `float` | |
| `longitude` | `float` | |
| `notes` | `str` | |

### LocationAddress

| Field | Type |
|-------|------|
| `address1` | `str` |
| `address2` | `str` |
| `city` | `str` |
| `state` | `str` |
| `postal_code` | `str` |
| `country` | `str` (ISO-3166 2-letter code) |

### Organization

| Field | Type | Notes |
|-------|------|-------|
| `org_id` | `str` | Unique ID (aliased from `id`) |
| `display_name` | `str` | Organization name |
| `created` | `datetime` | Creation timestamp |
| `xsi_actions_endpoint` | `str` | BroadSoft XSI actions path. Requires `calling_data=True` |
| `xsi_events_endpoint` | `str` | BroadSoft XSI events path. Requires `calling_data=True` |
| `xsi_events_channel_endpoint` | `str` | XSI events channel path. Requires `calling_data=True` |
| `xsi_domain` | `str` | api-prepended bcBaseDomain. Requires `calling_data=True` |

---

## Common Gotchas

### 1. `calling_data=True` is not optional -- it is mandatory for calling fields

The single most common mistake. Without `calling_data=True` on `list()`, `details()`, `create()`, and `update()`, the response will **not include** `location_id`, `extension`, or calling-related `phone_numbers`. Your code will see `None` for these fields and may incorrectly conclude the user is not calling-enabled.

### 2. Location must exist before user assignment

You cannot assign a user to a location that does not exist. Create the location first, optionally enable it for calling, then assign users.

### 3. `location_id` is write-once for calling users

You can set `location_id` when you first assign a calling license to a user. After that, `location_id` **cannot be changed** via the People API update. To move a user to a different location, you would need to remove the calling license, re-add it with the new location. <!-- NEEDS VERIFICATION -->

### 4. License ID assignment requires the full base64-encoded ID

License IDs in Webex are long base64-encoded strings (e.g., `Y2lzY29zcGFyazov...`). Always retrieve them programmatically from `api.licenses.list()` -- never hardcode them, as they vary by organization and subscription.

### 5. The People API is a composite of multiple microservices

A create or update call can **partially succeed**. For example, the user may be created but the phone number assignment may fail (especially with invalid numbers). Always verify with a subsequent GET after errors.

### 6. Performance limits with `calling_data=True`

The SDK enforces a soft limit of 10 users per page when fetching with `calling_data=True` (constant `MAX_USERS_WITH_CALLING_DATA = 10`). This is due to backend performance issues. For large orgs, consider the async API with `concurrent_requests` tuning.

### 7. Extension vs. work_extension

- When **writing**: set `person.extension = '1001'` (no routing prefix).
- When **reading**: `phone_numbers` of type `work_extension` will have the value `<routing_prefix><extension>` (e.g., `'8001001'` where `800` is the prefix and `1001` is the extension).

### 8. 403 errors on license or people calls

Usually means the access token does not have admin scopes. Verify the token has `spark-admin:people_read`, `spark-admin:people_write`, and `spark-admin:licenses_read`.

### 9. Phone numbers must be provisioned to the location first

Before assigning a DID/TN to a user, the number must already be added to the location's number inventory via the telephony location numbers API:

```python
api.telephony.location.number.add(
    location_id='<location_id>',
    phone_numbers=['+15551234567']
)
```

### 10. SCIM 2.0 is now the recommended path for user creation

As of January 2024, Webex recommends SCIM 2.0 (`wxc_sdk.scim.ScimV2Api`) over the People API for user creation and management due to higher performance and standard connectors. Users created via SCIM can then be licensed using the `assign_licenses_to_users` PATCH method.

### 11. Deleting a calling user may have delayed side effects

After deleting a user, their phone numbers may not be immediately available for reassignment. The SDK test suite retries number removal with delays of up to 10 seconds between attempts when encountering 502 errors.

### 12. Location name length for calling

Locations enabled for Webex Calling must have names of **80 characters or fewer**. The general Locations API allows 256, but calling features and Control Hub enforce the shorter limit.
