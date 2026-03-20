---
name: manage-licensing
description: |
  Audit, assign, and reclaim Webex licenses across the organization.
  Covers license inventory, usage analysis, bulk assignment, and license
  reclamation workflows.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation — e.g. "audit usage", "assign licenses", "reclaim unused", "check capacity"]
---

# Manage Licensing Workflow

## Step 1: Load references

1. Read `docs/reference/authentication.md` for token setup and scope requirements
2. Read `docs/reference/admin-licensing.md` for license API patterns, PATCH body schema, and error codes
3. Read `docs/reference/provisioning.md` for how licensing connects to user provisioning

## Step 2: Verify auth token is working

Before any licensing operation, confirm the token is valid and has the required scopes.

### Required scopes by operation

| Operation | Scope(s) |
|-----------|----------|
| List/view licenses | Admin token (full or read-only admin) |
| Assign/remove licenses (PATCH) | Admin token (full admin) |
| List people (for cross-reference) | `spark-admin:people_read` |

### Verification sequence

**2a. Check token identity:**

```bash
wxcli whoami
```

Inspect the output:
- Confirm a valid user/admin identity is returned (display name, org ID present).
- If this fails with 401 — token is expired or missing. Run `wxcli configure` or check `~/.wxcli/config.json`.
- If this fails with 403 — token exists but lacks permissions. You may have a user-level token instead of an admin token.
- Personal access tokens last 12 hours. Service app tokens vary by grant type.

**2b. Verify admin scope by exercising the license API:**

```bash
wxcli licenses-api list
```

Inspect the output:
- **Success (license table returned):** Admin read scope confirmed. Proceed.
- **403 Forbidden:** Token is not an admin token, or the admin role is insufficient. Stop and resolve.
- **401 Unauthorized:** Token is invalid or expired. Re-run `wxcli configure`.
- **Empty result (no licenses):** Unusual — confirm org ID is correct via `wxcli whoami` output.

**2c. For write operations (assign/remove), verify full admin:**

If the user's operation requires assignment or removal, confirm the token is a **full admin** token (not read-only admin). Read-only admins can list licenses but cannot PATCH. The only reliable test is to note the admin role from `wxcli whoami` output, or to attempt the operation and handle a 403.

### Gate

**Do not proceed until token confirmed valid.** Both `wxcli whoami` and `wxcli licenses-api list` must succeed before moving to Step 3. If either fails, stop and troubleshoot auth:
- Token expired — re-run `wxcli configure` with a fresh token
- Token not configured — run `wxcli configure` or check `~/.wxcli/config.json`
- Token lacks admin access — read-only admins can list but cannot assign/remove licenses
- Wrong org — verify the org ID in `wxcli whoami` matches the target organization

## Step 3: Determine the operation

Ask the user which licensing operation they need. The six supported operations are:

| Operation | What It Does | CLI Group |
|-----------|-------------|-----------|
| **License inventory** | See all licenses and usage counts | `licenses-api list` |
| **License details** | Get details for a specific license | `licenses-api show` |
| **Assign licenses** | Add licenses to users | `licenses-api update` (PATCH with `--json-body`) |
| **Usage audit** | Find unused/unassigned licenses | `licenses-api` + `people` (cross-reference) |
| **Reclaim licenses** | Remove licenses from inactive users | `licenses-api update` + `people` |
| **Calling license check** | Quick calling-focused license list | `licenses list --calling-only` |

Confirm with the user before proceeding:
- **Which operation** from the table above
- **Target details** (license type, user emails, usage threshold, etc.)
- **For reclamation**: criteria for "inactive" (days since last login, specific users, etc.)

## Step 4: Check prerequisites

Run these checks based on the operation. **Stop and report** if any prerequisite fails.

### For license inventory or audit:
```bash
# List all licenses — verify API access works
wxcli licenses-api list
```

### For license assignment:
```bash
# 1. Find the target license and check capacity
wxcli licenses-api list -o json
# Look for the target license name — confirm consumed < total

# 2. Verify the target user exists
wxcli people list --email user@example.com -o json

# 3. For calling licenses: verify location exists
wxcli locations list --calling-only
```

### For license reclamation:
```bash
# 1. Identify the license to reclaim
wxcli licenses-api list -o json

# 2. List users currently assigned to that license
wxcli licenses-api show "LICENSE_ID" --include-assigned-to user -o json

# 3. Cross-reference user status
wxcli people list -o json
```

## Step 5: Build plan — [SHOW BEFORE EXECUTING]

**Present the plan to the user and wait for approval.** Never execute write operations without confirmation.

Format the plan as:

```
=== Licensing Plan ===

Operation: [Assign License / Reclaim License / Audit Usage / etc.]

Target:
  - [specific details — license name, user emails, criteria]

Steps:
  1. [First CLI command — what it does]
  2. [Second CLI command — what it does]
  3. Verify: [what we'll check after]

Prerequisites verified:
  ✓ Auth token valid (authenticated as [name])
  ✓ License available: [name] ([consumed]/[total])
  ✓ Target user exists: [email] ([person_id])
  ✓ [any other checks]

Proceed? [wait for user confirmation]
```

## Step 6: Execute the licensing operation

### Operation A: License Inventory

```bash
# Quick table view of all licenses
wxcli licenses-api list

# Calling-only quick view
wxcli licenses list --calling-only

# Detailed view with availability calculation
wxcli licenses-api list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
for lic in data:
    avail = lic.get('totalUnits', 0) - lic.get('consumedUnits', 0)
    print(f\"{lic['name']}: {lic.get('consumedUnits', 0)}/{lic.get('totalUnits', 0)} (available: {avail})\")
"
```

### Operation B: License Details

```bash
# Basic details
wxcli licenses-api show "LICENSE_ID"

# With list of assigned users
wxcli licenses-api show "LICENSE_ID" --include-assigned-to user -o json

# Paginate assigned users (max 300 per page)
wxcli licenses-api show "LICENSE_ID" --include-assigned-to user --limit 100
```

### Operation C: Assign a Non-Calling License

For Meetings, Messaging, or other non-calling licenses. No `properties` block needed.

```bash
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {"id": "LICENSE_ID", "operation": "add"}
  ]
}'
```

### Operation D: Assign a Calling License

Calling licenses require `properties` with at least `phoneNumber` or `extension`. If `phoneNumber` is omitted, `locationId` is mandatory.

```bash
# With extension and location (most common)
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {
      "id": "CALLING_PRO_LICENSE_ID",
      "operation": "add",
      "properties": {
        "locationId": "LOCATION_ID",
        "extension": "1001"
      }
    }
  ]
}'

# With phone number and extension
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {
      "id": "CALLING_PRO_LICENSE_ID",
      "operation": "add",
      "properties": {
        "locationId": "LOCATION_ID",
        "phoneNumber": "+14085551234",
        "extension": "1001"
      }
    }
  ]
}'
```

**Key constraints:**
- `locationId` is **write-once** — can only be set on initial calling license assignment, cannot be changed after
- `extension` value must NOT include the location routing prefix
- Either `phoneNumber` or `extension` is mandatory for calling licenses
- To move a user to a new location: remove calling license, then re-add with new location (this is destructive)

### Operation E: Remove a License

```bash
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {"id": "LICENSE_ID", "operation": "remove"}
  ]
}'
```

**WARNING:** Removing a Calling license is destructive. ALL calling configuration is deleted: extension, phone number, call forwarding rules, voicemail settings, monitoring lists, and device associations. There is no undo. Always document the user's settings before removing a calling license.

### Operation F: Add and Remove in One Call

Swap licenses (e.g., upgrade from Standard to Professional) in a single PATCH:

```bash
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {
      "id": "NEW_CALLING_PRO_LICENSE_ID",
      "operation": "add",
      "properties": {
        "locationId": "LOCATION_ID",
        "extension": "1001"
      }
    },
    {"id": "OLD_CALLING_STD_LICENSE_ID", "operation": "remove"}
  ]
}'
```

### Operation G: Usage Audit

Cross-reference license inventory with user data to find gaps.

```bash
# Step 1: Get license inventory
wxcli licenses-api list -o json

# Step 2: For each calling license, list assigned users
wxcli licenses-api show "CALLING_LICENSE_ID" --include-assigned-to user -o json

# Step 3: List all people to find unlicensed users
wxcli people list -o json

# Step 4: Compare — users in people list without corresponding license assignment
# are candidates for license assignment or removal from the org
```

### Operation H: Reclaim Licenses from Inactive Users

```bash
# Step 1: List users holding the target license
wxcli licenses-api show "CALLING_LICENSE_ID" --include-assigned-to user -o json

# Step 2: Cross-reference with people list to check login activity
wxcli people list -o json
# Look for users with lastActivity > N days ago, or status != "active"

# Step 3: Document the user's calling settings BEFORE removal
wxcli users show PERSON_ID -o json

# Step 4: Remove the license (after user approval)
wxcli licenses-api update --email "inactive.user@example.com" --json-body '{
  "email": "inactive.user@example.com",
  "licenses": [
    {"id": "CALLING_LICENSE_ID", "operation": "remove"}
  ]
}'

# Step 5: Verify license was freed
wxcli licenses-api show "CALLING_LICENSE_ID"
# Confirm consumedUnits decreased by 1
```

### Operation I: Bulk License Assignment

For assigning the same license to multiple users, loop the PATCH command:

```bash
LICENSE_ID="<license_id>"
LOCATION_ID="<location_id>"
EXT=200

for email in user1@example.com user2@example.com user3@example.com; do
  wxcli licenses-api update --json-body "{
    \"email\": \"$email\",
    \"licenses\": [
      {
        \"id\": \"$LICENSE_ID\",
        \"operation\": \"add\",
        \"properties\": {
          \"locationId\": \"$LOCATION_ID\",
          \"extension\": \"$EXT\"
        }
      }
    ]
  }"
  echo "Assigned to: $email (ext $EXT)"
  EXT=$((EXT + 1))
done
```

> **Note:** For large batches (20+ users), consider the async Python SDK pattern in `docs/reference/wxc-sdk-patterns.md` for better performance with concurrent requests and automatic 429 retry handling.

## Step 7: Verify results

Always read back the modified resources to confirm.

### Verify a license assignment:
```bash
# Check the license's consumed count changed
wxcli licenses-api show "LICENSE_ID"

# Verify the user appears in the assigned users list
wxcli licenses-api show "LICENSE_ID" --include-assigned-to user -o json
# Search for the target user's email in the output

# Verify the user's own record reflects the license
wxcli users show PERSON_ID -o json
```

### Verify a license removal:
```bash
# Confirm consumed count decreased
wxcli licenses-api show "LICENSE_ID"

# Confirm user no longer appears in assigned users
wxcli licenses-api show "LICENSE_ID" --include-assigned-to user -o json
```

### Verify bulk operations:
```bash
# Check overall capacity after bulk assignment
wxcli licenses-api list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
for lic in data:
    if 'calling' in lic.get('name', '').lower():
        avail = lic.get('totalUnits', 0) - lic.get('consumedUnits', 0)
        print(f\"{lic['name']}: {lic.get('consumedUnits', 0)}/{lic.get('totalUnits', 0)} (available: {avail})\")
"
```

## Step 8: Report results

Summarize what was done:

```
=== Licensing Operation Complete ===

Operation: [what was done]
Results:
  - [license]: [action] for [user/count] ([status])
  - Capacity: [consumed]/[total] (was [old_consumed]/[total])

Verification:
  ✓ [what was confirmed]

Next steps:
  - [any follow-up actions needed]
```

---

## Critical Rules

1. **ALWAYS test auth first** -- Run `wxcli whoami` before any licensing call. Do not proceed on auth failure.

2. **ALWAYS show plan before executing** -- Present the licensing plan and wait for user confirmation. Never assign or remove licenses without approval.

3. **Removing a Calling license is destructive** -- ALL calling configuration is deleted: extension, phone number, call forwarding rules, voicemail settings, monitoring lists, and device associations. There is no undo. Always document settings before removal.

4. **License IDs are org-specific base64 strings** -- Never hardcode them. Always retrieve via `wxcli licenses-api list` first.

5. **Calling licenses require `properties`** -- Unlike Meetings or Messaging licenses, Calling license assignment must include `properties` with at least `phoneNumber` or `extension`. If you omit `phoneNumber`, you must provide `locationId`. Error code 400411 indicates missing properties.

6. **`locationId` is write-once on calling licenses** -- Can only be set when first assigning a calling license. Cannot be changed after. To move a user, remove calling license and re-add with new location (destructive).

7. **`licenses-api update` confirms "Updated" even on no-op** -- If the user already has the license, the CLI prints "Updated." without error. Always verify the actual state with `licenses-api show` after assignment.

8. **License conflicts are strictly enforced** -- A user cannot hold both Calling Professional and Calling Standard. The API returns specific error codes for each conflict (400404, 400406, 400407, 400410).

9. **Attendant Console has a prerequisite** -- Assign Calling Professional before assigning Attendant Console. Error code 400408 if the prerequisite is missing.

10. **206 Partial Content is not an error** -- The PATCH endpoint can return HTTP 206 when some licenses succeeded but others failed. Always compare the returned `licenses` array against what was requested.

11. **`licenses-api` (admin spec) vs `licenses` (calling spec)** -- Use `licenses-api` for assignment/removal and full inventory. Use `licenses` with `--calling-only` for quick calling-license audits.

12. **Log all operations** -- Print what you are about to do before each CLI command, and print the result after. This creates an audit trail for troubleshooting.

---

## Error Handling

When a wxcli command fails:

**A. Fix and retry** -- Missing required field, wrong ID, format issue:
1. Read the full error message
2. Run `wxcli licenses-api update --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** -- License already assigned or already removed:
1. Verify current state: `wxcli licenses-api show LICENSE_ID --include-assigned-to user -o json`
2. If state is correct, skip to next operation

**C. Escalate** -- Unclear or persistent error:
1. Run with `--debug` for raw HTTP details
2. Invoke `/wxc-calling-debug` for systematic diagnosis

Licensing-specific errors:
- 400 with code 400000: License ID not recognized -- re-run `licenses-api list` to get correct IDs
- 400 with code 400411: Missing `properties` on calling license -- add `locationId`, `phoneNumber`, or `extension`
- 400 with code 400404: Cannot hold both Calling Professional and Standard simultaneously -- remove one first
- 400 with code 400408: Attendant Console requires Calling Professional prerequisite
- 400 with code 400112: Cannot downgrade Calling Professional to Standard
- 206: Partial success -- check which licenses in the array failed
- 403: Token lacks admin write access -- verify admin role

---

## Required Scopes Reference

| Operation | Scope(s) |
|-----------|----------|
| List/view licenses | Admin token (full or read-only admin) |
| Assign/remove licenses (PATCH) | Admin token (full admin) |
| List people (for cross-reference) | `spark-admin:people_read` |

---

## Two CLI Groups for Licensing

| | `licenses-api` (admin spec) | `licenses` (calling spec) |
|---|---|---|
| **Commands** | list, show, update | list, show |
| **Best for** | Full lifecycle: inventory, details with assigned users, assign, remove | Quick calling-license audit |
| **Assignment** | Yes -- via `update` with `--json-body` | No -- read-only |
| **Filter** | No built-in filter (use JSON output + script) | `--calling-only` flag |

---

## License Type Quick Reference

| License Name Pattern | Type | Properties Required |
|----------------------|------|---------------------|
| Webex Calling - Professional | Calling | locationId + (phoneNumber or extension) |
| Webex Calling - Standard | Calling | locationId + (phoneNumber or extension) |
| Webex Calling - Common Area | Calling | locationId + (phoneNumber or extension) |
| CX Essentials | Calling add-on | Requires Calling Professional first |
| Webex Attendant Console | Calling add-on | Requires Calling Professional first |
| Webex Meetings | Non-calling | None (optionally siteUrl) |
| Webex Messaging | Non-calling | None |

Match by substring (e.g., `"calling"` in name), not exact string. License names vary by subscription.

---

## Cross-Reference

For calling license assignment during user provisioning, see the `provision-calling` skill. The `licenses-api update` command now provides CLI-native license assignment.

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read `docs/reference/admin-licensing.md` to recover PATCH body format and error codes
2. Check current license state: `wxcli licenses-api list -o json`
3. Resume from the first incomplete step
