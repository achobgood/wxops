---
name: provision-calling
description: |
  Provision Webex Calling users, locations, and licenses via the wxcli CLI.
  Guides through auth verification, prerequisite checks, deployment planning, execution,
  and result verification for any provisioning operation.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation — e.g. "create location", "enable user", "assign license", "bulk provision"]
---

<!-- Updated by playbook session 2026-03-18 -->

# Provision Calling Workflow

## Step 1: Load references

1. Read `docs/reference/authentication.md` for token setup and scope requirements
2. Read `docs/reference/provisioning.md` for People, Licenses, and Locations API patterns
3. Read `docs/reference/wxc-sdk-patterns.md` for SDK setup (sync vs async, bulk patterns)

## Step 2: Verify auth token is working

Before any provisioning operation, confirm the token is valid and has admin scopes.

```bash
wxcli whoami
```

If this fails with 401/403, stop and troubleshoot auth before proceeding. Common causes:
- Token expired (personal access tokens last 12 hours)
- Token not configured — run `wxcli configure` or check `~/.wxcli/config.json`
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
| **Bulk provision** | Provision multiple users in one run | All of the above |

Confirm with the user before proceeding:
- **Which operation** from the table above
- **Target details** (location name/address, user email, license type, etc.)
- **For bulk**: CSV or list of users to provision

## Step 4: Check prerequisites

Run these checks based on the operation. **Stop and report** if any prerequisite fails.

### For location creation:
```bash
# Check if location name already exists
wxcli locations list --calling-only
# Look for a match in the output. If the target name appears:
wxcli locations show LOCATION_ID
# Ask user: update existing or abort?
```

### For user provisioning:
```bash
# 1. Verify location exists
wxcli locations list --calling-only
wxcli locations show LOCATION_ID

# 2. Find an available calling license with capacity
wxcli licenses list
# Look for "Webex Calling - Professional" with consumed < total

# 3. Check if user already exists
wxcli users list --email target@example.com --output json
# If user exists, check if already calling-enabled:
wxcli users show PERSON_ID --output json
# If location_id is set, user is already calling-enabled.
# Ask user: update or abort?
```

### For phone number assignment:
```bash
# Verify number is in location inventory before assigning to a user
# Numbers must be added to location first via numbers-manage commands
wxcli numbers-api create LOCATION_ID --json-body '{"phoneNumbers": ["+15551234567"], "numberType": "DID"}'
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
  1. [First CLI command — what it does]
  2. [Second CLI command — what it does]
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

Required flags: `--name`, `--timezone`, `--address`, `--city`, `--state`, `--zip`. Country defaults to US. Language defaults to en_US.

```bash
wxcli locations create \
  --name "San Jose Office" \
  --timezone "America/Los_Angeles" \
  --announcement-language en_us \
  --address "123 Main St" \
  --city "San Jose" \
  --state CA \
  --zip 95113 \
  --country US
```

### Operation B: Enable Location for Calling

Creating a location does NOT automatically enable calling. Separate command required.

```bash
wxcli locations enable-calling LOCATION_ID
```

**Important:** `announcement_language` must be lowercase (`en_us` not `en_US`) or the API rejects with "Invalid Language Code". If the location was created without it, update first.

**Warning:** Once calling is enabled on a location, it **cannot be disabled via API**. Calling-enabled locations can only be deleted from Control Hub, not via the API (returns 409 Conflict).

### Operation C: Create a New User

```bash
wxcli users create \
  --email jsmith@example.com \
  --display-name "John Smith" \
  --first-name John \
  --last-name Smith
```

**Gotcha:** A POST that returns 400 may **still have created the person**. Always check with a GET before retrying:
```bash
wxcli users list --email jsmith@example.com --output json
```

### Operation D: Enable Existing User for Calling

Assign a calling license, location, and extension to an existing user.

> **Note:** `wxcli licenses` only has `list` and `show` — license assignment requires raw HTTP. This is one of the gaps where the CLI falls back to Python.

```bash
# Look up current user state
wxcli users show PERSON_ID --output json

# Look up the calling license ID
wxcli licenses list --output json
# Find the license where name contains "Calling - Professional"
```

```python
# Assign license via raw HTTP (PATCH API)
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

api.session.rest_patch(f"{BASE}/licenses/users", json={
    "personId": "PERSON_ID",
    "licenses": [{
        "id": "CALLING_LICENSE_ID",
        "properties": {
            "locationId": "LOCATION_ID",
            "extension": "1001"
        }
    }]
})
```

**Key constraints:**
- `location_id` is **write-once** — can only be set on initial calling license assignment, cannot be changed after
- `extension` value must NOT include the location routing prefix
- Either `phone_number` or `extension` is mandatory for calling licenses
- To move a user, remove calling license and re-add with new location

### Operation E: Bulk Provision

For small batches (< 20 users), loop wxcli commands:

```bash
# Small batch: loop wxcli commands
for email in user1@example.com user2@example.com user3@example.com; do
  wxcli users create --email "$email" --display-name "User $(echo $email | cut -d@ -f1)"
  echo "Created: $email"
done
```

For enabling calling on multiple existing users:

```bash
# Assign calling license to multiple users
LOCATION_ID="<location_id>"
LICENSE_ID="<calling_license_id>"
EXT=1001

for email in user1@example.com user2@example.com user3@example.com; do
  # Create the user
  wxcli users create --email "$email" --display-name "User $EXT" --first-name "User" --last-name "$EXT"
  echo "Created $email"
  EXT=$((EXT + 1))
done
# License assignment requires raw HTTP — see Operation D above
```

> **Raw HTTP fallback for bulk operations:** For large batches (20+ users), the async Python SDK pattern provides better performance with concurrent requests and automatic 429 retry handling. See `docs/reference/wxc-sdk-patterns.md` for the `AsWebexSimpleApi` async pattern with `concurrent_requests=10..40`.

## Step 7: Verify results

Always read back the created/updated resources to confirm.

### Verify a user:
```bash
wxcli users show PERSON_ID --output json
# Confirm: location_id is set, calling license appears in licenses list, extension is correct
```

### Verify a location:
```bash
wxcli locations show LOCATION_ID --output json
# Confirm: name, address, timezone are correct
```

### Verify bulk:
```bash
# List all users at a location
wxcli users list --location LOCATION_ID --output json
# Count results to confirm expected number of users provisioned
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

1. **ALWAYS test auth first** — Run `wxcli whoami` before any provisioning call. Do not proceed on auth failure.

2. **ALWAYS show plan before executing** — Present the deployment plan and wait for user confirmation. Never provision without approval.

3. **`location_id` is write-once** — Can only be set when first assigning a calling license. Cannot be changed after. To move a user, remove calling license and re-add with new location.

4. **`announcement_language` must be lowercase** — `en_us` not `en_US`. The telephony `enable_for_calling` API rejects mixed case with "Invalid Language Code".

5. **`announcement_language` returns None from details** — Always set it explicitly before calling `enable_for_calling`, even if it was set during creation.

6. **Calling-enabled locations cannot be deleted via API** — Returns 409 Conflict. Must use Control Hub.

7. **Phone numbers must be in location inventory first** — Before assigning a DID to a user, add it via `wxcli numbers-api create LOCATION_ID`.

8. **POST/PUT may partially succeed** — A 400 response on user create/update may have still created/modified the resource. Always verify with a subsequent GET before retrying.

9. **License IDs are org-specific base64 strings** — Never hardcode them. Always retrieve via `wxcli licenses list`.

10. **Extension values must NOT include the routing prefix** — Set extension to `1001`. The work_extension in the response will include the prefix (e.g., `8001001`), but when writing, omit it.

11. **Log all operations** — Print what you're about to do before each CLI command, and print the result after. This creates an audit trail for troubleshooting.

12. **For bulk operations (20+ users), consider the async Python SDK** — wxcli runs one command at a time. For large batches, the `AsWebexSimpleApi` async pattern in `docs/reference/wxc-sdk-patterns.md` is significantly faster.

---

## Error Handling

When a wxcli command fails:

**A. Fix and retry** — Missing required field, wrong ID, format issue:
1. Read the full error message
2. Run `wxcli <group> <command> --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** — Resource already exists or already configured:
1. Verify current state: `wxcli users show PERSON_ID` or `wxcli locations show LOCATION_ID`
2. If state is correct, skip to next operation

**C. Escalate** — Unclear or persistent error:
1. Run with `--debug` for raw HTTP details
2. Invoke `/wxc-calling-debug` for systematic diagnosis

Provisioning-specific errors:
- 400 on `users create`: Check email format, verify no existing user with same email
- 400 on `numbers-api create`: Check E.164 format (+1XXXXXXXXXX), verify number not already assigned
- 403: Check token has `spark-admin:people_write` and `spark-admin:telephony_config_write` scopes
- 409: User/location already exists — GET current state first

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

> For bulk license assignment, usage auditing, and reclamation workflows, see the `manage-licensing` skill. The `licenses-api update` command provides CLI-native license assignment.

```bash
# List all licenses — look for "Webex Calling - Professional" with available capacity
wxcli licenses list

# Key license types to look for in the output:
#   "Webex Calling - Professional"   — full calling license
#   "Webex Calling - Basic"          — basic calling (limited features)
#   "Webex Calling - Workspaces"     — for workspace devices
# Check that consumed < total for the license you need
```

---

## Two License Assignment Methods

| | Method A: People API PUT | Method B: Licenses PATCH API |
|---|---|---|
| **CLI equivalent** | `wxcli users update` (modify user fields) | Raw HTTP PATCH `/licenses/users` (license assignment not in CLI yet) |
| **Best for** | Migrating existing users, changing multiple Person fields | Net-new provisioning, SCIM users, atomic license+location+extension |
| **Gotcha** | Must GET full person first, include ALL fields in PUT | Requires extension or phone_number for calling licenses |
| **Can combine add+remove** | Manually modify the licenses list | Yes, add + remove operations in same call |

---

## Context Compaction

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
