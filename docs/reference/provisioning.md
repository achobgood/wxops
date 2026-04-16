# Provisioning Reference

User, license, and location provisioning for Webex Calling via the `wxc_sdk` Python SDK. Each section includes both typed SDK methods and **Raw HTTP** examples using `api.session.rest_*()`.

> **Prerequisite:** All examples assume a configured `WebexSimpleApi` instance. See `authentication.md` for token setup. For the raw HTTP pattern, see `wxc-sdk-patterns.md` section 1.5.

## Sources

- wxc_sdk v1.30.0 (github.com/jeokrohn/wxc_sdk)
- OpenAPI spec: `specs/webex-admin.json` (People, Licenses, Locations, Organizations APIs)
- developer.webex.com People, Licenses, Locations, and Organizations APIs

---

## Table of Contents

1. [Required Scopes](#required-scopes)
2. [People API](#people-api)
3. [Licenses API](#licenses-api)
4. [Locations API](#locations)
5. [Organization API](#organization-api)
6. [Numbers API](#numbers)
7. [Provisioning Workflow](#provisioning-workflow)
8. [Data Models](#data-models)
9. [Gotchas](#gotchas) (cross-cutting)
10. [Bulk Cleanup / Teardown](#bulk-cleanup--teardown)
11. [See Also](#see-also)

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
| Enable location for calling | `spark-admin:telephony_config_write` (and likely `spark-admin:locations_write`) |

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

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All People API operations can be performed via raw HTTP using `api.session.rest_*()`. This is the preferred execution pattern -- wxc_sdk handles auth and session management, while you control the exact request.

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# ── List people ───────────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/people", params={
    "max": 1000,
    "callingData": "true",          # string "true", not bool
})
people = result.get("items", [])

# ── List with filters ────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/people", params={
    "email": "jsmith@example.com",
    "callingData": "true",
})

# ── Get person details ───────────────────────────────────────────
person = api.session.rest_get(f"{BASE}/people/{person_id}", params={
    "callingData": "true",
})

# ── Create a person ──────────────────────────────────────────────
body = {
    "emails": ["jsmith@example.com"],
    "displayName": "John Smith",
    "firstName": "John",
    "lastName": "Smith",
    "licenses": [calling_license_id],
    "locationId": location_id,
    "extension": "1001",
    "phoneNumbers": [{"type": "work", "value": "+15551234567"}],
}
result = api.session.rest_post(f"{BASE}/people", json=body)
new_person_id = result["id"]

# ── Update a person (full PUT -- include all fields) ─────────────
person = api.session.rest_get(f"{BASE}/people/{person_id}", params={
    "callingData": "true",
})
person["extension"] = "2002"
api.session.rest_put(f"{BASE}/people/{person_id}", json=person)

# ── Delete a person ──────────────────────────────────────────────
api.session.rest_delete(f"{BASE}/people/{person_id}")

# ── Get current user ─────────────────────────────────────────────
me = api.session.rest_get(f"{BASE}/people/me", params={
    "callingData": "true",
})
```

**Key differences from typed SDK:**
- `callingData` is a string `"true"`, not a Python bool
- Response key for list is `items`, not `people`
- No auto-pagination -- use `max=1000` for large orgs
- Update is a raw PUT -- you must include all fields (GET first, modify, PUT back)

### CLI Examples

```bash
# ── List all people (table output) ────────────────────────────────
wxcli people list

# ── List with calling data (shows locationId, extension) ─────────
wxcli people list --calling-data true

# ── Search by email ───────────────────────────────────────────────
wxcli people list --email jsmith@example.com

# ── Search by display name (prefix match) ─────────────────────────
wxcli people list --display-name "John"

# ── List people at a specific location ────────────────────────────
wxcli people list --location-id <location_id> --calling-data true

# ── Get person details (JSON output) ──────────────────────────────
wxcli people show <person_id>

# ── Get person details as table ────────────────────────────────────
wxcli people show <person_id> -o table

# ── Get current user details ──────────────────────────────────────
wxcli people list-me --calling-data true

# ── Create a person ───────────────────────────────────────────────
wxcli people create --first-name "John" --last-name "Smith" \
  --display-name "John Smith" --location-id <location_id> \
  --extension "1001"

# ── Create with full JSON body (for emails, licenses, phoneNumbers)
wxcli people create --json-body '{
  "emails": ["jsmith@example.com"],
  "displayName": "John Smith",
  "firstName": "John",
  "lastName": "Smith",
  "licenses": ["<calling_license_id>"],
  "locationId": "<location_id>",
  "extension": "1001",
  "phoneNumbers": [{"type": "work", "value": "+15551234567"}]
}'

# ── Update a person ───────────────────────────────────────────────
wxcli people update <person_id> --extension "2002"
wxcli people update <person_id> --display-name "John A. Smith"
wxcli people update <person_id> --department "Engineering" --title "Senior Engineer"

# ── Delete a person ───────────────────────────────────────────────
wxcli people delete <person_id>

# ── Delete without confirmation prompt ────────────────────────────
wxcli people delete <person_id> --force
```

**CLI notes:**
- `wxcli people list` defaults to table output (`-o table`); use `-o json` for full JSON.
- `wxcli people show` defaults to JSON output; use `-o table` for a summary view.
- The `--calling-data true` flag is the CLI equivalent of `calling_data=True` in the SDK. Pass it when you need calling fields (locationId, extension, phoneNumbers).
- For create/update operations with complex nested fields (emails, licenses, phoneNumbers), use `--json-body` with the full JSON payload.
- The `--limit` and `--offset` flags control client-side pagination of results.

### Gotchas

**`calling_data=True` is not optional -- it is mandatory for calling fields.**
The single most common mistake. Without `calling_data=True` on `list()`, `details()`, `create()`, and `update()`, the response will **not include** `location_id`, `extension`, or calling-related `phone_numbers`. Your code will see `None` for these fields and may incorrectly conclude the user is not calling-enabled.

**`location_id` is write-once for calling users.**
You can set `location_id` when you first assign a calling license to a user. After that, `location_id` **cannot be changed** via the People API update. To move a user to a different location, you would need to remove the calling license, re-add it with the new location.

**The People API is a composite of multiple microservices.**
A create or update call can **partially succeed**. For example, the user may be created but the phone number assignment may fail (especially with invalid numbers). Always verify with a subsequent GET after errors.

**Performance limits with `calling_data=True`.**
The SDK enforces a soft limit of 10 users per page when fetching with `calling_data=True` (constant `MAX_USERS_WITH_CALLING_DATA = 10`). This is due to backend performance issues. For large orgs, consider the async API with `concurrent_requests` tuning.

**Extension vs. work_extension.**
- When **writing**: set `person.extension = '1001'` (no routing prefix).
- When **reading**: `phone_numbers` of type `work_extension` will have the value `<routing_prefix><extension>` (e.g., `'8001001'` where `800` is the prefix and `1001` is the extension).

**Deleting a calling user may have delayed side effects.**
After deleting a user, their phone numbers may not be immediately available for reassignment. The SDK test suite retries number removal with delays of up to 10 seconds between attempts when encountering 502 errors.

**`PeopleApi.create()` takes a `Person` model, not kwargs.**

```python
from wxc_sdk.people import Person
person = Person(emails=[email], first_name=first, last_name=last)
result = api.people.create(settings=person)
```

Do NOT call `api.people.create(emails=[...], first_name=...)` — this raises `TypeError`.

---

## Licenses API

> For full org-wide license auditing, assignment, and reclamation, see [admin-licensing.md](admin-licensing.md).

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

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# ── List all licenses ────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/licenses", params={"max": 1000})
licenses = result.get("items", [])

# ── Get license details ──────────────────────────────────────────
license_detail = api.session.rest_get(f"{BASE}/licenses/{license_id}")

# ── Find calling licenses ────────────────────────────────────────
calling_licenses = [
    lic for lic in licenses
    if "Webex Calling" in lic.get("name", "")
]

# ── Assign license to user (PATCH) ──────────────────────────────
# The PATCH endpoint for license assignment:
body = {
    "email": "jsmith@example.com",
    "licenses": [
        {
            "id": calling_license_id,
            "operation": "add",
            "properties": {
                "locationId": location_id,
                "extension": "1001",
            }
        }
    ]
}
api.session.rest_post(f"{BASE}/licenses/users", json=body)
```

**Note:** The Licenses API is read-only for license inventory (list/details). License assignment to users is done via the `/licenses/users` PATCH-style endpoint (implemented as POST). There is no create/update/delete for license definitions themselves.

### Gotchas

**License ID assignment requires the full base64-encoded ID.**
License IDs in Webex are long base64-encoded strings (e.g., `Y2lzY29zcGFyazov...`). Always retrieve them programmatically from `api.licenses.list()` -- never hardcode them, as they vary by organization and subscription.

**SCIM 2.0 is now the recommended path for user creation.**
As of January 2024, Webex recommends SCIM 2.0 (`wxc_sdk.scim.ScimV2Api`) over the People API for user creation and management due to higher performance and standard connectors. Users created via SCIM can then be licensed using the `assign_licenses_to_users` PATCH method.

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

```python
# SDK method:
api.telephony.location.enable_for_calling(location_id='<id>', ...)

# Raw HTTP equivalent:
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}",
    json={"announcementLanguage": "en_us"},  # lowercase required
)
```

The `announcement_language` field is **required** when enabling a location for Webex Calling. It must be **lowercase** (`en_us`, not `en_US`) -- see gotchas #13 and #14.

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# ── List locations ───────────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/locations", params={"max": 1000})
locations = result.get("items", [])

# ── List with name filter ────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/locations", params={
    "name": "headquarters",
    "max": 1000,
})

# ── Get location details ─────────────────────────────────────────
location = api.session.rest_get(f"{BASE}/locations/{loc_id}")

# ── Create a location ────────────────────────────────────────────
body = {
    "name": "San Jose Office",
    "timeZone": "America/Los_Angeles",
    "preferredLanguage": "en_us",
    "announcementLanguage": "en_us",
    "address": {
        "address1": "123 Main St",
        "city": "San Jose",
        "state": "CA",
        "postalCode": "95113",
        "country": "US",
    },
}
result = api.session.rest_post(f"{BASE}/locations", json=body)
new_loc_id = result["id"]

# ── Update a location ────────────────────────────────────────────
location = api.session.rest_get(f"{BASE}/locations/{loc_id}")
location["name"] = "San Jose HQ"
api.session.rest_put(f"{BASE}/locations/{loc_id}", json=location)

# ── Delete a location ────────────────────────────────────────────
# WARNING: Calling-enabled locations return 409 -- see gotcha #15
api.session.rest_delete(f"{BASE}/locations/{loc_id}")

# ── Enable location for Webex Calling ────────────────────────────
# This is a SEPARATE telephony endpoint, not the Locations API
body = {
    "announcementLanguage": "en_us",  # MUST be lowercase -- see gotcha #13
}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}",
    json=body,
)
```

**Raw HTTP gotchas for locations:**
- `announcementLanguage` must be **lowercase** (`en_us` not `en_US`) when calling `enable_for_calling` -- the telephony backend rejects mixed case with "Invalid Language Code" (gotcha #13)
- `announcementLanguage` returns `None` from the locations details endpoint even when set -- always set it explicitly before enabling calling (gotcha #14)
- Calling-enabled locations **cannot be deleted via API** -- returns `409 Conflict: Location is being referenced, cannot be deleted`. Must use Control Hub (gotcha #15)
- The `safe_delete_check` response uses field `locationDeleteStatus` (not `status`), with value `"UNBLOCKED"` or `"BLOCKED"` (gotcha #17)
- The `address` field in raw HTTP is a nested object with `address1`, `city`, `state`, `postalCode`, `country`. The SDK flattens these to top-level kwargs in `locations.create()`.

### CLI Examples

```bash
# ── List all locations ────────────────────────────────────────────
wxcli locations list

# ── Filter locations by name (case-insensitive contains match) ────
wxcli locations list --name "headquarters"

# ── List locations as JSON ────────────────────────────────────────
wxcli locations list -o json

# ── Get location details ──────────────────────────────────────────
wxcli locations show <location_id>

# ── Get location details as table ─────────────────────────────────
wxcli locations show <location_id> -o table

# ── Create a location (all required fields) ───────────────────────
wxcli locations create \
  --name "San Jose Office" \
  --time-zone "America/Los_Angeles" \
  --preferred-language "en_us" \
  --announcement-language "en_us" \
  --json-body '{
    "address": {
      "address1": "123 Main St",
      "city": "San Jose",
      "state": "CA",
      "postalCode": "95113",
      "country": "US"
    }
  }'

# ── Update a location ────────────────────────────────────────────
wxcli locations update <location_id> --name "San Jose HQ"
wxcli locations update <location_id> --time-zone "America/New_York"
```

**CLI notes:**
- The `locations` group covers both REST CRUD (list, create, show, update, delete) and floors management.
- `wxcli locations create` requires `--name`, `--time-zone`, `--preferred-language`, and `--announcement-language`. The address must be passed via `--json-body` since it is a nested object.
- Use lowercase language codes (e.g., `en_us` not `en_US`) for `--announcement-language` to avoid "Invalid Language Code" errors when later enabling calling.
- Location names must be 80 characters or fewer if the location will be enabled for Webex Calling.

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

### Gotchas

**Location must exist before user assignment.**
You cannot assign a user to a location that does not exist. Create the location first, optionally enable it for calling, then assign users.

**Location name length for calling.**
Locations enabled for Webex Calling must have names of **80 characters or fewer**. The general Locations API allows 256, but calling features and Control Hub enforce the shorter limit.

**`enable_for_calling` requires lowercase language codes.**
The telephony `enable_for_calling` API rejects `en_US` (mixed case) for `announcement_language` with error `Invalid Language Code`. Use `en_us` (all lowercase). The general Locations API stores `preferredLanguage` as `en_US` but the telephony backend expects lowercase.

```python
location = api.locations.details(location_id=loc_id)
if not location.announcement_language:
    location.announcement_language = (location.preferred_language or "en_US").lower()
api.telephony.location.enable_for_calling(location=location)
```

**`announcement_language` returns None from details endpoint.**
`LocationsApi.details()` returns `announcement_language = None` even on locations that have it set. This is a Webex API inconsistency. Always set it explicitly before calling `enable_for_calling`.

**Cannot delete calling-enabled locations via API.**
`LocationsApi.delete()` returns `409 Conflict: Location is being referenced, cannot be deleted` for any location with Webex Calling enabled. There is **no API to disable calling on a location** — `wxcadm` confirms: "There is currently no way to delete a Location outside of Control Hub." The `safe_delete_check_before_disabling_calling_location` precheck may return `UNBLOCKED` but the delete still fails due to the telephony reference.

Calling-enabled locations can only be deleted from Control Hub.

**`SafeDeleteCheckResponse` uses `location_delete_status`, not `status`.**
The response model field is `location_delete_status` (value: `"UNBLOCKED"` or `"BLOCKED"`), not `status`. The `blocking` field contains a model with `users_in_use_count`, `trunks_in_use_count`, etc.

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

### Raw HTTP

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# ── List organizations ──────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/organizations", params={"max": 1000})
orgs = result.get("items", [])

# ── List with calling data (XSI endpoints) ─────────────────────
result = api.session.rest_get(f"{BASE}/organizations", params={
    "callingData": "true",
    "max": 1000,
})

# ── Get organization details ────────────────────────────────────
org = api.session.rest_get(f"{BASE}/organizations/{org_id}", params={
    "callingData": "true",
})
# XSI fields: xsiActionsEndpoint, xsiEventsEndpoint,
#              xsiEventsChannelEndpoint, xsiDomain

# ── Delete an organization ──────────────────────────────────────
# WARNING: Requires Full Administrator Role. Deletion takes up to 10 min.
api.session.rest_delete(f"{BASE}/organizations/{org_id}")
```

**Key differences from typed SDK:**
- `callingData` is a string `"true"`, not a Python bool
- Response key for list is `items`, not `organizations`
- XSI field names are camelCase in raw JSON: `xsiActionsEndpoint`, `xsiEventsEndpoint`, `xsiEventsChannelEndpoint`, `xsiDomain`

---

## Numbers API

Base path: `/v1/telephony/config/numbers` (list) and `/v1/telephony/config/locations/{locationId}/numbers` (add/activate/remove)

Numbers must be added to a location's inventory before they can be assigned to users or workspaces. The Numbers API manages the phone number lifecycle: adding numbers to locations, activating/deactivating them, and removing them.

### CLI Examples

```bash
# ── List all phone numbers in the org ─────────────────────────────
wxcli numbers list

# ── List numbers for a specific location ──────────────────────────
wxcli numbers list --location-id <location_id>

# ── Search for a specific phone number ────────────────────────────
wxcli numbers list --phone-number "+15551234567"

# ── List only available (unassigned) numbers ──────────────────────
wxcli numbers list --available true

# ── Filter by number state ────────────────────────────────────────
wxcli numbers list --state ACTIVE
wxcli numbers list --state INACTIVE

# ── Filter by owner type ──────────────────────────────────────────
wxcli numbers list --owner-type PEOPLE
wxcli numbers list --owner-type PLACE

# ── Filter by number type ────────────────────────────────────────
wxcli numbers list --number-type NUMBER
wxcli numbers list --number-type EXTENSION

# ── List numbers as JSON ──────────────────────────────────────────
wxcli numbers list -o json

# ── Add phone numbers to a location ───────────────────────────────
wxcli numbers create <location_id> --json-body '{
  "phoneNumbers": ["+15551234567", "+15551234568"]
}'

# ── Activate numbers in a location ────────────────────────────────
wxcli numbers update <location_id> --action ACTIVATE --json-body '{
  "phoneNumbers": ["+15551234567"]
}'

# ── Deactivate numbers in a location ──────────────────────────────
wxcli numbers update <location_id> --action DEACTIVATE --json-body '{
  "phoneNumbers": ["+15551234567"]
}'

# ── Remove phone numbers from a location ──────────────────────────
wxcli numbers delete <location_id>

# ── Remove without confirmation prompt ────────────────────────────
wxcli numbers delete <location_id> --force

# ── Validate phone numbers before adding ──────────────────────────
wxcli numbers validate-phone-numbers --json-body '{
  "phoneNumbers": ["+15551234567", "+15551234568"]
}'
```

**CLI notes:**
- The `numbers` group covers number CRUD, validation, and manage-numbers jobs.
- `wxcli numbers list` returns org-wide numbers by default. Use `--location-id` to scope to a specific location.
- Adding and activating numbers requires `--json-body` with a `phoneNumbers` array since the CLI cannot flatten nested array body fields into flags.
- Numbers must be added to a location (`create`) and activated (`update --action ACTIVATE`) before they can be assigned to users.
- Use `validate-phone-numbers` to check number validity before adding them to avoid errors.

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

## Gotchas

Cross-cutting gotchas that span multiple API surfaces. Section-specific gotchas are inline within their respective sections above.

### 403 errors on license or people calls

Usually means the access token does not have admin scopes. Verify the token has `spark-admin:people_read`, `spark-admin:people_write`, and `spark-admin:licenses_read`.

### Phone numbers must be provisioned to the location first

Before assigning a DID/TN to a user, the number must already be added to the location's number inventory via the telephony location numbers API:

```python
api.telephony.location.number.add(
    location_id='<location_id>',
    phone_numbers=['+15551234567']
)
```

### Numbers list API returns key `phoneNumbers`, not `numbers`

`GET /telephony/config/numbers` returns a response body with the key `phoneNumbers`, not `numbers`. Code that looks for `response['numbers']` will get a `KeyError`.

### Workspaces list API returns key `items`, not `workspaces`

`GET /workspaces` returns a response body with the key `items`, not `workspaces`. Parse using `response['items']` when working with raw API responses.

### Manage numbers jobs list API returns key `items`, not `manageNumbers`

The manage numbers jobs list endpoint returns its results under the key `items`, not `manageNumbers`. This is inconsistent with other telephony job endpoints.

### Manage numbers job body uses `numberList` array, not `phoneNumbers`

The manage numbers job creation body expects a `numberList` array where each element contains `locationId` and `numbers`. Do not use `phoneNumbers` as the key -- the API will reject or ignore it.

### Location creation is two steps: create + enable calling

`POST /v1/locations` creates the location but does NOT enable Webex Calling. You must separately call `POST /v1/telephony/config/locations` with the location's `id`, `name`, `timeZone`, `preferredLanguage`, `announcementLanguage`, and `address`. Without this second call, assigning calling-licensed users to the location fails with "Calling flag not set".

### Calling user creation requires extension or phone number

`POST /v1/people?callingData=true` with a calling license and location requires either `extension` or `phoneNumbers` in the body. The API rejects with "Create Calling user either Phone number or Extension is required" if neither is provided. You cannot create a calling user first and assign an extension separately — it must be done atomically.

### User create with callingData=false may silently create the user

If `POST /v1/people?callingData=false` fails with 400 (e.g., "Calling flag not set"), the user may have already been created without calling configuration. A subsequent retry returns 409 Conflict. Always check `GET /v1/people?email=...` before retrying user creation. If the user exists, use `PUT` to update with calling data instead.

### Number porting has no public API

Number port-in requests, LOA submission, porting status tracking, and new number ordering from Cisco Calling Plan are all done through the Control Hub UI or via Cisco's PTS (PSTN Technical Support) team. The Numbers API (`wxcli numbers`) only manages numbers *after* they are ported in or provisioned — it cannot initiate a port.

### Location deletion via API is unreliable for calling-enabled locations

Locations with Webex Calling enabled cannot be deleted directly via the public
API (`409 Conflict: Location is being referenced`). The older guidance to
"disable calling first" via a `wxcli location-call-settings update-location-calling`
command is stale for this repo:

- that command does **not** exist in the current CLI
- the public API does **not** expose a reliable "disable calling on location"
  operation for general teardown workflows

What you *can* do with CLI/API:
1. Delete all location-scoped resources first (virtual lines, call parks, hunt groups, call queues, schedules, trunks, devices, workspaces, users)
2. Run `wxcli location-settings safe-delete-check LOCATION_ID` to inspect visible blockers
3. Retry `wxcli locations delete --force LOCATION_ID`

What may still require Control Hub:
- final disable/delete of a calling-enabled location, even after all visible
  dependencies have been removed via API

Practical operator rule: use CLI/API to clear dependencies, but warn the user
that the final location removal may still need to be completed in Control Hub.

---

## Bulk Cleanup / Teardown

When tearing down resources programmatically (e.g., cleaning up after a stress test or migration dry run), resources must be deleted in **reverse dependency order**. Deleting in the wrong order produces 409 (Conflict) or 400 (reference still exists) errors.

### Deletion Order (top-to-bottom)

| Step | Resource Type | wxcli Delete Command | Notes |
|------|--------------|---------------------|-------|
| 1 | Dial Plans | `wxcli call-routing delete --force {id}` | Just `delete`, not `delete-dial-plan` |
| 2 | Route Lists | `wxcli call-routing delete-route-lists --force {id}` | Plural suffix |
| 3 | Route Groups | `wxcli call-routing delete-route-groups --force {id}` | Plural suffix |
| 4 | Translation Patterns | `wxcli call-routing delete-translation-patterns-call-routing --force {id}` | |
| 5 | Trunks | `wxcli call-routing delete-trunks --force {id}` | Check for dial plan refs first (Error 27349) |
| 6 | Call Queues | `wxcli call-queue delete --force {locationId} {id}` | Needs locationId |
| 7 | Hunt Groups | `wxcli hunt-group delete --force {locationId} {id}` | Needs locationId |
| 8 | Auto Attendants | `wxcli auto-attendant delete --force {locationId} {id}` | Needs locationId |
| 9 | Paging Groups | `wxcli paging-group delete --force {locationId} {id}` | Needs locationId |
| 10 | Call Parks | `wxcli call-park delete --force {locationId} {id}` | **Must list per-location** (see below) |
| 11 | Call Pickups | `wxcli call-pickup delete --force {locationId} {id}` | **Must list per-location** (see below) |
| 12 | Virtual Lines | Raw `DELETE /v1/telephony/config/virtualLines/{id}` | See VL bug below |
| 13 | Workspaces | `wxcli workspaces delete --force {id}` | |
| 14 | Users | `wxcli users delete --force {id}` | |
| 15 | Schedules | `wxcli location-schedules delete --force {locationId} {type} {scheduleId}` | |
| 16 | Locations | `wxcli locations delete --force {id}` | Clear blockers first; final delete of a calling-enabled location may still require Control Hub |

### Key Behaviors

**Always use `--force` on delete commands** to skip the `[y/N]` confirmation prompt that blocks non-interactive execution.

**Call Parks and Call Pickups must be listed per-location.** `wxcli call-park list` and `wxcli call-pickup list` without a location argument return empty even when resources exist. You must iterate over each location:
```bash
for LOC_ID in $(wxcli locations list -o json | jq -r '.[].id // empty'); do
  wxcli call-park list "$LOC_ID" -o json
  wxcli call-pickup list "$LOC_ID" -o json
done
```

**Virtual Line ID type mismatch bug:** The Numbers API returns virtual line owners with `VIRTUAL_LINE`-encoded IDs, but `wxcli virtual-extensions delete` sends them to the `/virtualExtensions/` endpoint which expects `VIRTUAL_EXTENSION`-encoded IDs. This always fails with 400 "Wrong type of Webex ID provided". Workaround: use raw HTTP `DELETE /v1/telephony/config/virtualLines/{id}` with a bearer token. Discover VL IDs from `wxcli numbers list -o json` (owner field) — `wxcli virtual-extensions list` may return empty.

**Location deletion cooldown:** Even after disabling calling and deleting all sub-resources, location DELETE may return 409 for minutes to hours. Preferred recovery: **re-invoke `wxcli cleanup run` (it is idempotent and resumes from where it left off)** — do NOT write an inline Python/bash `time.sleep` polling loop inside a single Bash tool call. The Bash tool has a ~10-minute hard timeout and long loops die silently mid-wait, leaving partial state. If bespoke retry is required, split into **discrete Bash tool calls** (one per location per attempt) with the sleep **between** tool calls, cap total wall time at ≤3 minutes, and if 409s persist, report them and stop rather than looping. See `.claude/skills/teardown/SKILL.md` → "Rule: never hand-roll polling loops".

**CCP-integrated PSTN gotcha (dCloud / Cisco Calling Plan orgs):** On orgs using Cisco Calling Plan, number deletion returns `ERR.V.TRM.TMN60004` ("DELETE number is supported only for non-integrated CCP") because phone-number lifecycle is owned by the PSTN portal, not the API. After trunk/route-group teardown, location DELETE then 409s with "being referenced" indefinitely — not because of locally visible resources but because Webex's internal PSTN backend is async-releasing trunk references. This typically clears in **1-4 hours** and no API action can unblock it. `wxcli cleanup run` detects this signature in two places:
1. **Numbers:** a `ERR.V.TRM.TMN60004` response is logged as `[number=<ext/e164>] skipped — CCP-integrated, managed via PSTN portal` and treated as a clean skip, not a failure.
2. **Locations:** if the 409 body contains `ERR.V.TRM.TMN60004`, OR says "being referenced" while a pre-check finds no local dependencies (users, workspaces, devices, features, trunks, route groups), the retry loop short-circuits and the cleanup exits 0 with a dedicated footer: `N locations blocked by CCP backend — retry in a few hours`. Re-invoke `wxcli cleanup run` later — the command is idempotent and picks up where it left off.

**Trunk deletion requires no remaining references:** Error 27349 names the referencing dial plan in the message.

### API Format Differences for Members

Different features use different agent/member formats in POST bodies:

| Feature | Field | Format | Example |
|---------|-------|--------|---------|
| Hunt Group | `agents` | Array of objects | `[{"id": "person_id", "weight": 50}]` |
| Call Queue | `agents` | Array of objects | `[{"id": "person_id"}]` |
| Call Pickup | `agents` | Array of strings | `["person_id_1", "person_id_2"]` |
| Paging Group | `targets`, `originators` | Array of strings | `["person_id_1"]` |

Using the wrong format (e.g., `[{"id": ...}]` for pickup) produces 400 "Invalid field value: agents".

---

## See Also

- **`authentication.md`** — Token setup, OAuth flows, and scope reference.
- **`wxc-sdk-patterns.md`** — Async bulk provisioning patterns (recipes 5.3, 5.4), workspace provisioning (recipe 5.12).
- **`location-call-settings-core.md`** — Location calling enablement and location-level telephony configuration.
