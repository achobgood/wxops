---
name: provision-calling
description: |
  Provision Webex Calling users, locations, and licenses via the wxc_sdk Python SDK.
  Guides through auth verification, prerequisite checks, deployment planning, execution,
  and result verification for any provisioning operation.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation — e.g. "create location", "enable user", "assign license", "bulk provision"]
---

# Provision Calling Workflow

## Step 1: Load references

1. Read `docs/reference/authentication.md` for token setup and scope requirements
2. Read `docs/reference/provisioning.md` for People, Licenses, and Locations API patterns
3. Read `docs/reference/wxc-sdk-patterns.md` for SDK setup (sync vs async, bulk patterns)

## Step 2: Verify auth token is working

Before any provisioning operation, confirm the token is valid and has admin scopes.

```python
from dotenv import load_dotenv
from wxc_sdk import WebexSimpleApi

load_dotenv(override=True)
api = WebexSimpleApi()

me = api.people.me(calling_data=True)
print(f'Authenticated as: {me.display_name} ({me.emails[0]})')
print(f'Org ID: {me.org_id}')
```

If this fails with 401/403, stop and troubleshoot auth before proceeding. Common causes:
- Token expired (personal access tokens last 12 hours)
- Missing `WEBEX_ACCESS_TOKEN` environment variable
- Token lacks admin scopes (`spark-admin:people_write`, `spark-admin:licenses_read`, etc.)

## Step 3: Determine the operation

Ask the user which provisioning operation they need. The six supported operations are:

| Operation | What It Does | Prerequisites |
|-----------|-------------|---------------|
| **Create location** | Add a new physical location | Admin token with `spark-admin:locations_write` |
| **Enable location for calling** | Turn on Webex Calling for an existing location | Location must exist; `spark-admin:telephony_config_write` |
| **Create user** | Add a new person to the org | Admin token with `spark-admin:people_write` |
| **Enable user for calling** | Assign calling license + location + extension to existing user | Location must exist; calling license available |
| **Assign/change licenses** | Add or remove licenses on a user | License with available capacity |
| **Bulk provision** | Provision multiple users in one run | All of the above + async pattern for performance |

Confirm with the user before proceeding:
- **Which operation** from the table above
- **Target details** (location name/address, user email, license type, etc.)
- **For bulk**: CSV or list of users to provision

## Step 4: Check prerequisites

Run these checks based on the operation. **Stop and report** if any prerequisite fails.

### For location creation:
```python
# Check if location name already exists
existing = api.locations.by_name('Target Location Name')
if existing:
    print(f'Location already exists: {existing.location_id}')
    # Ask user: update existing or abort?
```

### For user provisioning:
```python
# 1. Verify location exists
location = api.locations.by_name('Target Location Name')
assert location, 'Location not found — create it first'

# 2. Find an available calling license with capacity
calling_license = next(
    (lic for lic in api.licenses.list()
     if lic.webex_calling_professional
     and lic.consumed_units < lic.total_units),
    None
)
assert calling_license, 'No available Webex Calling Professional licenses'
print(f'License: {calling_license.name} ({calling_license.consumed_units}/{calling_license.total_units} used)')

# 3. Check if user already exists
user = next(api.people.list(email='target@example.com'), None)
if user:
    user = api.people.details(person_id=user.person_id, calling_data=True)
    if user.location_id:
        print(f'User already calling-enabled at location {user.location_id}')
        # Ask user: update or abort?
```

### For phone number assignment:
```python
# Verify number is in location inventory before assigning to a user
# Numbers must be added to location first via telephony API
api.telephony.location.number.add(
    location_id='<location_id>',
    phone_numbers=['+15551234567']
)
```

## Step 5: Build deployment plan — SHOW BEFORE EXECUTING

**Present the plan to the user and wait for approval.** Never execute without confirmation.

Format the plan as:

```
=== Provisioning Plan ===

Operation: [Create Location / Enable User / etc.]

Target:
  - [specific details]

Steps:
  1. [First API call — what it does]
  2. [Second API call — what it does]
  3. Verify: [what we'll check after]

Prerequisites verified:
  ✓ Auth token valid (authenticated as [name])
  ✓ Location exists: [name] ([id])
  ✓ License available: [name] ([consumed]/[total])
  ✓ [any other checks]

Proceed? [wait for user confirmation]
```

## Step 6: Execute the provisioning operation

### Operation A: Create a Location

All parameters are **required**: name, time_zone, preferred_language, announcement_language, address1, city, state, postal_code, country.

```python
location_id = api.locations.create(
    name='San Jose Office',           # Max 80 chars if will be calling-enabled
    time_zone='America/Los_Angeles',
    preferred_language='en_us',
    announcement_language='en_us',     # MUST be lowercase for calling enablement
    address1='123 Main St',
    city='San Jose',
    state='CA',
    postal_code='95113',
    country='US'
)
print(f'Created location: {location_id}')
```

### Operation B: Enable Location for Calling

Creating a location does NOT automatically enable calling. Separate API call required.

```python
location = api.locations.details(location_id=loc_id)

# announcement_language returns None from details — always set explicitly
# MUST be lowercase (en_us not en_US) or API rejects with "Invalid Language Code"
if not location.announcement_language:
    location.announcement_language = (location.preferred_language or "en_US").lower()

api.telephony.location.enable_for_calling(location=location)
```

**Warning:** Once calling is enabled on a location, it **cannot be disabled via API**. Calling-enabled locations can only be deleted from Control Hub, not via the API (returns 409 Conflict).

### Operation C: Create a New User

The `create()` method takes a `Person` model, NOT kwargs.

```python
from wxc_sdk.people import Person, PhoneNumber, PhoneNumberType

new_user = api.people.create(
    settings=Person(
        emails=['jsmith@example.com'],
        display_name='John Smith',
        first_name='John',
        last_name='Smith',
        # Include these if assigning calling at creation time:
        licenses=['<calling_license_id>'],
        location_id='<location_id>',
        extension='1001',
        phone_numbers=[PhoneNumber(type=PhoneNumberType.work, value='+15551234567')]
    ),
    calling_data=True      # ← REQUIRED to set calling fields
)
```

**Gotcha:** A POST that returns 400 may **still have created the person**. Always check with a GET before retrying.

### Operation D: Enable Existing User for Calling (Method A — People API PUT)

Standard pattern: GET details first, modify, then PUT back.

```python
# GET current state — calling_data=True is REQUIRED
user = api.people.details(person_id='<id>', calling_data=True)

# Modify: add calling license, set location and extension
if calling_license.license_id not in user.licenses:
    user.licenses.append(calling_license.license_id)
user.location_id = location.location_id
user.extension = '1001'                    # NO routing prefix

# PUT back — calling_data=True is REQUIRED
updated = api.people.update(person=user, calling_data=True)
```

**Key constraints:**
- `location_id` is **write-once** — can only be set on initial calling license assignment, cannot be changed after
- `extension` value must NOT include the location routing prefix
- Primary email must be listed first in the emails array
- Some licenses are implicitly assigned and cannot be removed

### Operation E: Assign License (Method B — Licenses PATCH API, recommended)

Cleaner for new provisioning. Supports calling-specific properties natively.

```python
from wxc_sdk.licenses import LicenseRequest, LicenseProperties

api.licenses.assign_licenses_to_users(
    person_id='<person_id>',
    licenses=[
        LicenseRequest(
            id=calling_license.license_id,
            properties=LicenseProperties(
                location_id=location.location_id,
                extension='1001'
                # OR: phone_number='+15551234567'
            )
        )
    ]
)
```

**LicenseProperties rules:**
- Either `phone_number` or `extension` is mandatory for calling licenses
- If `phone_number` is omitted, `location_id` is mandatory
- Can combine add + remove in one call (e.g., remove UCM + add WxC Professional)

**When to use which method:**
- **Method B (PATCH)** — net-new users, SCIM-created users, atomic license+location+extension assignment
- **Method A (PUT)** — migrating existing users, modifying other Person fields simultaneously

### Operation F: Bulk Provision (Async)

For provisioning multiple users, use the async API for performance.

```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi
from wxc_sdk.licenses import LicenseRequest, LicenseProperties

async def provision_user(api, email, license_id, location_id, extension):
    """Provision a single user — called in parallel."""
    user = next(iter(await api.people.list(email=email)), None)
    if not user:
        print(f'User not found: {email}')
        return None

    await api.licenses.assign_licenses_to_users(
        person_id=user.person_id,
        licenses=[
            LicenseRequest(
                id=license_id,
                properties=LicenseProperties(
                    location_id=location_id,
                    extension=extension
                )
            )
        ]
    )
    return email

async def main():
    async with AsWebexSimpleApi(concurrent_requests=10) as api:
        # Define users to provision
        users_to_provision = [
            {'email': 'user1@example.com', 'extension': '1001'},
            {'email': 'user2@example.com', 'extension': '1002'},
            # ...
        ]

        results = await asyncio.gather(
            *[provision_user(api, u['email'], license_id, location_id, u['extension'])
              for u in users_to_provision],
            return_exceptions=True    # collect errors without stopping
        )

        # Report results
        for user_info, result in zip(users_to_provision, results):
            if isinstance(result, Exception):
                print(f"FAILED: {user_info['email']} — {result}")
            elif result is None:
                print(f"SKIPPED: {user_info['email']} — user not found")
            else:
                print(f"OK: {result}")

asyncio.run(main())
```

**Bulk tuning:**
- `concurrent_requests=10` is conservative — can increase to 40 for large batches
- SDK auto-retries 429 rate limits when `retry_429=True` (default)
- `MAX_USERS_WITH_CALLING_DATA = 10` is hardcoded in SDK — limits concurrent calling data fetches

## Step 7: Verify results

Always read back the created/updated resources to confirm.

### Verify a user:
```python
verified = api.people.details(person_id=user.person_id, calling_data=True)
assert verified.location_id is not None, 'location_id not set'
assert calling_license.license_id in verified.licenses, 'calling license not assigned'
print(f'User: {verified.display_name}')
print(f'Location: {verified.location_id}')
print(f'Extension: {verified.extension}')
print(f'Licenses: {len(verified.licenses)} assigned')
```

### Verify a location:
```python
location = api.locations.details(location_id=loc_id)
print(f'Location: {location.name}')
print(f'Address: {location.address.address1}, {location.address.city}, {location.address.state}')
print(f'Timezone: {location.time_zone}')
```

### Verify bulk:
```python
# Count calling-enabled users at the target location
users_at_location = [
    u for u in api.people.list(location_id=location.location_id, calling_data=True)
]
print(f'{len(users_at_location)} users at {location.name}')
```

## Step 8: Report results

Summarize what was done:

```
=== Provisioning Complete ===

Operation: [what was done]
Results:
  - [resource]: [status] ([id])
  - [resource]: [status] ([id])

Verification:
  ✓ [what was confirmed]

Next steps:
  - [any follow-up actions needed]
```

---

## CRITICAL RULES

1. **ALWAYS test auth first** — Run `api.people.me()` before any provisioning call. Do not proceed on auth failure.

2. **ALWAYS show plan before executing** — Present the deployment plan and wait for user confirmation. Never provision without approval.

3. **NEVER skip `calling_data=True`** — Required on `list()`, `details()`, `create()`, and `update()` for any People API call involving calling fields. Without it, `location_id`, `extension`, and calling `phone_numbers` are all `None`.

4. **`PeopleApi.create()` takes a `Person` model, not kwargs** — `api.people.create(settings=Person(...))`, not `api.people.create(emails=[...])`. The latter raises `TypeError`.

5. **`location_id` is write-once** — Can only be set when first assigning a calling license. Cannot be changed after. To move a user, remove calling license and re-add with new location.

6. **`announcement_language` must be lowercase** — `en_us` not `en_US`. The telephony `enable_for_calling` API rejects mixed case with "Invalid Language Code".

7. **`announcement_language` returns None from `details()`** — Always set it explicitly before calling `enable_for_calling`, even if it was set during creation.

8. **Calling-enabled locations cannot be deleted via API** — Returns 409 Conflict. Must use Control Hub.

9. **Phone numbers must be in location inventory first** — Before assigning a DID to a user, add it via `api.telephony.location.number.add()`.

10. **Handle 429 rate limits** — The SDK auto-retries when `retry_429=True` (default). For bulk operations, set `concurrent_requests` appropriately (10 for conservative, 40 for large batches).

11. **POST/PUT may partially succeed** — A 400 response on People create/update may have still created/modified the resource. Always verify with a subsequent GET before retrying.

12. **License IDs are org-specific base64 strings** — Never hardcode them. Always retrieve via `api.licenses.list()`.

13. **Extension values must NOT include the routing prefix** — Set `person.extension = '1001'`. The `work_extension` phone number in the response will include the prefix (e.g., `8001001`), but when writing, omit it.

14. **Log all operations** — Print what you're about to do before each API call, and print the result after. This creates an audit trail for troubleshooting.

---

## Required Scopes Reference

| Operation | Scope(s) |
|-----------|----------|
| List/view people | `spark-admin:people_read` |
| Create/update/delete people | `spark-admin:people_write` + `spark-admin:people_read` |
| List licenses | `spark-admin:licenses_read` |
| Assign licenses (PATCH) | `spark-admin:people_write` |
| List/view locations | `spark-admin:locations_read` |
| Create/update/delete locations | `spark-admin:locations_write` |
| Enable location for calling | `spark-admin:telephony_config_write` |

---

## License Lookup Quick Reference

```python
# Find Webex Calling Professional license with available capacity
wxc_pro = next(
    (lic for lic in api.licenses.list()
     if lic.webex_calling_professional
     and lic.consumed_units < lic.total_units),
    None
)

# Helper properties on License model:
#   lic.webex_calling              — True for any calling license
#   lic.webex_calling_professional — True for "Webex Calling - Professional"
#   lic.webex_calling_basic        — True for "Webex Calling - Basic"
#   lic.webex_calling_workspaces   — True for "Webex Calling - Workspaces"
```

---

## Two License Assignment Methods

| | Method A: People API PUT | Method B: Licenses PATCH API |
|---|---|---|
| **SDK call** | `api.people.update(person=user, calling_data=True)` | `api.licenses.assign_licenses_to_users(person_id=..., licenses=[...])` |
| **Best for** | Migrating existing users, changing multiple Person fields | Net-new provisioning, SCIM users, atomic license+location+extension |
| **Gotcha** | Must GET full person first, include ALL fields in PUT | `LicenseProperties` requires extension or phone_number for calling |
| **Can combine add+remove** | Manually modify the `licenses` list | Yes, via `LicenseRequestOperation.add` / `.remove` in same call |
