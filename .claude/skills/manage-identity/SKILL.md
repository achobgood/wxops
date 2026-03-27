---
name: manage-identity
description: |
  Manage Webex identity and directory: SCIM user/group sync, bulk provisioning,
  domain verification, org contacts, group membership, and directory cleanup.
  Guides from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation — e.g. "sync users", "verify domain", "bulk import", "cleanup directory"]
---

<!-- Updated by playbook session 2026-03-19 -->

# Manage Identity Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What is the critical difference between SCIM PUT and PATCH for user updates? (Answer: PUT replaces the entire user resource — any field omitted is deleted. PATCH modifies only specified fields. Always use PATCH for partial updates.)
2. What must be completed before SCIM sync can work for a domain? (Answer: Domain verification — the domain must be verified and claimed in Control Hub before SCIM can provision users with that email domain.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/admin-identity-scim.md` for SCIM users, groups, bulk, schemas, identity org, and People/Groups API patterns
2. Read `docs/reference/admin-org-management.md` for domains, org contacts, roles, and org settings

## Step 2: Verify auth token is working

Before any identity operation, confirm the token is valid and has appropriate scopes.

```bash
wxcli whoami
```

If this fails with 401/403, stop and troubleshoot auth before proceeding. Common causes:
- Token expired (personal access tokens last 12 hours)
- Token not configured -- run `wxcli configure` or check `~/.wxcli/config.json`
- Token lacks identity scopes -- SCIM endpoints require `identity:people_rw` or `identity:people_read`, NOT the `spark-admin:people_*` scopes used by Calling APIs

Check the org ID (needed for all SCIM and domain commands):

```bash
wxcli organizations list
```

## Step 3: Determine the operation

Ask the user which identity operation they need. The eight supported operations are:

| Need | Operation | CLI Group | Prerequisites |
|------|-----------|-----------|---------------|
| Sync users from IdP (Azure AD, Okta) | SCIM bulk import | `scim-bulk`, `scim-users` | Domain verified and claimed; `identity:people_rw` scope |
| Search/find users in directory | SCIM user search | `scim-users` | `identity:people_read` scope; org ID |
| Create/update/delete individual users | SCIM user CRUD | `scim-users` | `identity:people_rw` scope; org ID |
| Manage groups and membership | Group CRUD | `scim-groups` or `groups` | `identity:people_rw` (SCIM) or admin token (Webex Groups) |
| Import org contacts (directory listing) | Bulk contact import | `org-contacts` | `identity:contacts_rw` scope; org ID |
| Verify/claim a domain before sync | Domain verification | `domains` | `identity:organizations_rw` scope; DNS access |
| Clean up stale/inactive users | Directory cleanup | `scim-users`, `scim-bulk` | `identity:people_rw` scope; org ID |
| Check SCIM schema for field mapping | Schema introspection | `scim-schemas` | `identity:people_read` scope |

Confirm with the user before proceeding:
- **Which operation** from the table above
- **Target details** (user emails, group names, domain name, contact list, etc.)
- **For bulk**: CSV or list of users/contacts to provision

## Step 4: Check prerequisites

Run these checks based on the operation. **Stop and report** if any prerequisite fails.

### For all SCIM operations (scim-users, scim-groups, scim-bulk):
```bash
# Get the org ID (required as positional argument for all SCIM commands)
wxcli organizations list
# Note the org ID from the output -- you will pass it as the first argument
```

### For domain verification:
```bash
# Check current domain status (if available)
wxcli domains get-domain-verification $ORG_ID --domain "example.com"
# This returns the DNS TXT token. The user must add this to their DNS before verify-domain will succeed.
```

**DNS is outside the CLI's control.** If the user has not added the TXT record, provide the token value and instruct them to:
1. Add a TXT record at their domain root with the returned token value
2. Wait for DNS propagation (typically 15-60 minutes, up to 48 hours)
3. Return when ready to proceed with verification

### For SCIM sync (bulk import):
```bash
# Verify domain is claimed before syncing users at that domain
# The domain must be verified AND claimed, or SCIM user creation for that domain will fail
wxcli domains verify-domain $ORG_ID --domain "example.com"
```

### For user search/lookup:
```bash
# SCIM search -- use filter syntax
wxcli scim-users list $ORG_ID --filter 'userName eq "target@example.com"'

# Or use People API (no org ID needed)
wxcli people list --email "target@example.com"
```

### For org contacts:
```bash
# Check existing contacts before importing
wxcli org-contacts list $ORG_ID
```

## Step 5: Build plan -- [SHOW BEFORE EXECUTING]

**Present the plan to the user and wait for approval.** Never execute write operations without confirmation.

Format the plan as:

```
=== Identity Management Plan ===

Operation: [SCIM Bulk Import / Domain Verification / Directory Cleanup / etc.]

Target:
  - [specific details -- domain, user list, group name, etc.]

Steps:
  1. [First CLI command -- what it does]
  2. [Second CLI command -- what it does]
  3. Verify: [what we'll check after]

Prerequisites verified:
  - Auth token valid (authenticated as [name])
  - Org ID: [org_id]
  - Domain verified: [domain] (if applicable)
  - Scope confirmed: [identity:people_rw / identity:contacts_rw / etc.]

Proceed? [wait for user confirmation]
```

## Step 6: Execute the identity operation

### Operation A: Domain Verification

Complete end-to-end flow for adding a domain to the Webex org.

```bash
# Step 1: Get the verification token
wxcli domains get-domain-verification $ORG_ID --domain "newdomain.com"
# Response includes a token like: "webex-verification=abc123def456"

# Step 2: DNS TXT record must be added by the user (outside CLI)
# Record type: TXT, Name: @ (or newdomain.com), Value: the returned token

# Step 3: Verify the domain
wxcli domains verify-domain $ORG_ID --domain "newdomain.com"

# Step 4: Claim the domain for user provisioning
wxcli domains claim-domain $ORG_ID

# Or combine verify + claim in one step:
wxcli domains verify-domain $ORG_ID --domain "newdomain.com" --claim-domain true
```

### Operation B: SCIM User Search

```bash
# Search by exact email
wxcli scim-users list $ORG_ID --filter 'userName eq "jsmith@example.com"'

# Search by display name (contains)
wxcli scim-users list $ORG_ID --filter 'displayName co "Smith"'

# Search by email domain
wxcli scim-users list $ORG_ID --filter 'userName co "@acme.com"'

# Get specific attributes only
wxcli scim-users list $ORG_ID --filter 'userName sw "j"' --attributes "userName,displayName,emails"

# Get a specific user by ID
wxcli scim-users show $ORG_ID $USER_ID -o json
```

### Operation C: SCIM User Create/Update/Delete

**Create:**

```bash
# Create a single user
wxcli scim-users create $ORG_ID --user-name "newuser@example.com" --display-name "New User" --active

# Create with full JSON body (for nested fields: name, emails, addresses)
wxcli scim-users create $ORG_ID --json-body '{
  "userName": "jdoe@example.com",
  "displayName": "Jane Doe",
  "name": {"givenName": "Jane", "familyName": "Doe"},
  "emails": [{"value": "jdoe@example.com", "type": "work", "primary": true}],
  "active": true
}'
```

**Update (PATCH — always use this for modifications):**

```bash
# Change display name (only this field changes, everything else preserved)
wxcli scim-users update-users $ORG_ID $USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "replace", "path": "displayName", "value": "Jane M. Doe"}
  ]
}'

# Change multiple fields at once
wxcli scim-users update-users $ORG_ID $USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "replace", "path": "displayName", "value": "Jane M. Doe"},
    {"op": "replace", "path": "title", "value": "Senior Engineer"}
  ]
}'

# Deactivate a user
wxcli scim-users update-users $ORG_ID $USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": false}]
}'

# Add a value to a multi-valued attribute
wxcli scim-users update-users $ORG_ID $USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "add", "path": "phoneNumbers", "value": [{"value": "+15551234567", "type": "work"}]}
  ]
}'
```

PATCH operations: `add` (append value), `replace` (change value), `remove` (delete value). The `schemas` field with `PatchOp` URN is required in every PATCH body.

**Full replace (PUT — DANGEROUS, rarely needed):**

> **WARNING: `scim-users update` uses HTTP PUT, which REPLACES the entire user resource. Any attribute not included in the body is DELETED.** This means emails, phone numbers, addresses, group memberships, and active status are all removed if not explicitly included. Use PATCH (`update-users`) instead unless you have a specific reason to replace the full resource.

```bash
# ONLY use PUT when you need to replace the entire resource
# Step 1: GET the current full resource
wxcli scim-users show $ORG_ID $USER_ID -o json > user.json

# Step 2: Edit user.json (make your changes to the full object)

# Step 3: PUT the modified full resource back
wxcli scim-users update $ORG_ID $USER_ID --json-body "$(cat user.json)"
```

**When to use PUT vs PATCH:**
- **PATCH (99% of cases):** Changing display name, title, active status, adding/removing phone numbers, updating addresses — any targeted field change
- **PUT (rare):** Replacing a user's entire profile from an external IdP sync, or resetting a corrupted user record to a known-good state

**Delete:**

```bash
wxcli scim-users delete $ORG_ID $USER_ID --force
```

The same PUT/PATCH distinction applies to groups: use `scim-groups update-groups` (PATCH) instead of `scim-groups update` (PUT).

### Operation D: SCIM Bulk Import

```bash
# Bulk create multiple users in a single API call
wxcli scim-bulk create $ORG_ID --fail-on-errors 5 --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "failOnErrors": 5,
  "Operations": [
    {
      "method": "POST",
      "path": "/Users",
      "data": {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "alice@example.com",
        "displayName": "Alice Smith",
        "name": {"givenName": "Alice", "familyName": "Smith"},
        "emails": [{"value": "alice@example.com", "type": "work", "primary": true}],
        "active": true
      }
    },
    {
      "method": "POST",
      "path": "/Users",
      "data": {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "bob@example.com",
        "displayName": "Bob Jones",
        "name": {"givenName": "Bob", "familyName": "Jones"},
        "emails": [{"value": "bob@example.com", "type": "work", "primary": true}],
        "active": true
      }
    }
  ]
}'
```

Check the response for per-operation status. Each operation returns its own status code (e.g., `201` for created, `409` for conflict/duplicate).

**Bulk operation safety:**
- Bulk requests can mix operations (POST create, PUT replace, PATCH update, DELETE remove)
- **Never use PUT operations in bulk unless you have the full resource for every user**
- Prefer PATCH operations in bulk for updates — same safety as individual PATCH
- The `--fail-on-errors` parameter controls how many individual failures abort the entire batch
- **Always check per-operation status in the response** — a 200 response on the bulk endpoint does NOT mean all operations succeeded. Each operation has its own `status` field (201 = created, 200 = updated, 409 = duplicate, 400 = validation error)

### Operation E: Group Management

**SCIM Groups (for IdP sync):**

```bash
# List all SCIM groups
wxcli scim-groups list $ORG_ID

# Create a SCIM group with members
wxcli scim-groups create $ORG_ID --json-body '{
  "displayName": "DevOps Team",
  "members": [
    {"value": "USER_ID_1", "type": "user"},
    {"value": "USER_ID_2", "type": "user"}
  ]
}'

# Add a member via PATCH
wxcli scim-groups update-groups $ORG_ID $GROUP_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "add", "path": "members", "value": [{"value": "USER_ID", "type": "user"}]}
  ]
}'

# Remove a member via PATCH
wxcli scim-groups update-groups $ORG_ID $GROUP_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "remove", "path": "members[value eq \"USER_ID\"]"}
  ]
}'
```

**Webex Groups (native, no org ID needed):**

```bash
# List all groups
wxcli groups list

# Create a group with members
wxcli groups create --json-body '{
  "displayName": "Support Team",
  "members": [
    {"id": "PERSON_ID_1", "type": "user"},
    {"id": "PERSON_ID_2", "type": "user"}
  ]
}'

# Add/remove members
wxcli groups update $GROUP_ID --json-body '{
  "members": [
    {"id": "PERSON_ID", "type": "user", "operation": "add"}
  ]
}'

# List group members (paginated)
wxcli groups list-members $GROUP_ID --count 100
```

### Operation F: Org Contacts Import

```bash
# Create a single contact
wxcli org-contacts create $ORG_ID \
  --schemas "urn:cisco:codev:identity:contact:core:1.0" \
  --source CH \
  --display-name "Jane Smith" \
  --first-name "Jane" \
  --last-name "Smith" \
  --company-name "Acme Corp" \
  --primary-contact-method EMAIL

# Bulk create/update contacts
wxcli org-contacts create-bulk $ORG_ID \
  --schemas "urn:cisco:codev:identity:contact:core:1.0" \
  --json-body '{
    "schemas": "urn:cisco:codev:identity:contact:core:1.0",
    "contacts": [
      {
        "displayName": "Alice Johnson",
        "firstName": "Alice",
        "lastName": "Johnson",
        "source": "CH",
        "primaryContactMethod": "EMAIL",
        "emails": [{"value": "alice@example.com", "type": "work"}]
      },
      {
        "displayName": "Bob Williams",
        "firstName": "Bob",
        "lastName": "Williams",
        "source": "CH",
        "primaryContactMethod": "PHONE",
        "phoneNumbers": [{"value": "+14155551234", "type": "work"}]
      }
    ]
  }'

# Bulk delete contacts
wxcli org-contacts create-delete $ORG_ID \
  --schemas "urn:cisco:codev:identity:contact:core:1.0" \
  --json-body '{
    "schemas": "urn:cisco:codev:identity:contact:core:1.0",
    "contactIds": ["contact-id-1", "contact-id-2"]
  }'
```

### Operation G: Directory Cleanup (Deactivate Stale Users)

```bash
# Step 1: List active users
wxcli scim-users list $ORG_ID --filter 'active eq true' -o json

# Step 2: Deactivate individual users via PATCH
wxcli scim-users update-users $ORG_ID $USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": false}]
}'

# Or bulk deactivate many users at once
wxcli scim-bulk create $ORG_ID --fail-on-errors 10 --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "failOnErrors": 10,
  "Operations": [
    {"method": "PATCH", "path": "/Users/USER_ID_1", "data": {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"], "Operations": [{"op": "replace", "path": "active", "value": false}]}},
    {"method": "PATCH", "path": "/Users/USER_ID_2", "data": {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"], "Operations": [{"op": "replace", "path": "active", "value": false}]}}
  ]
}'

# Step 3: For permanent removal, delete after deactivation
wxcli scim-users delete $ORG_ID $USER_ID --force
```

### Operation H: Schema Introspection

```bash
# Get the SCIM User schema (discover all available user attributes)
wxcli scim-schemas show-user -o json

# Get the SCIM Group schema
wxcli scim-schemas show -o json

# Get a specific schema by URN (e.g., the Cisco extension schema)
wxcli scim-schemas show-scim2 "urn:scim:schemas:extension:cisco:webexidentity:2.0:User" -o json
```

## Step 7: Verify results

Always read back the created/updated resources to confirm.

### Verify SCIM users:
```bash
# Verify a specific user was created/updated
wxcli scim-users show $ORG_ID $USER_ID -o json
# Confirm: userName, displayName, active status, group memberships

# Verify bulk import -- search for imported users
wxcli scim-users list $ORG_ID --filter 'userName co "@example.com"'
# Count results to confirm expected number of users imported
```

### Verify groups:
```bash
# SCIM group
wxcli scim-groups list $ORG_ID --filter 'displayName eq "DevOps Team"' --include-members true

# Webex group
wxcli groups show $GROUP_ID --include-members true -o json
```

### Verify domain:
```bash
# Re-run verify to confirm domain status
wxcli domains verify-domain $ORG_ID --domain "example.com"
```

### Verify org contacts:
```bash
# Search for imported contacts
wxcli org-contacts list $ORG_ID --keyword "Smith"
```

## Step 8: Report results

Summarize what was done:

```
=== Identity Management Complete ===

Operation: [what was done]
Results:
  - [resource]: [status] ([id])
  - [resource]: [status] ([id])

Verification:
  - [what was confirmed]

Next steps:
  - [any follow-up actions needed]
```

---

## Critical Rules

1. **ALWAYS test auth first** -- Run `wxcli whoami` before any identity call. Do not proceed on auth failure.

2. **ALWAYS show plan before executing** -- Present the plan and wait for user confirmation. Never modify users, groups, or contacts without approval.

3. **NEVER use `scim-users update` (PUT) for partial changes** — PUT replaces the entire resource, deleting any attributes not included. Always use `scim-users update-users` (PATCH) for targeted changes. See Operation C for the full pattern and examples. Same applies to `scim-groups update` vs `scim-groups update-groups`.

4. **SCIM PATCH is partial update -- safer for targeted changes** -- Use `scim-users update-users` or `scim-groups update-groups` with SCIM patch operations (`add`, `replace`, `remove`) to change specific fields without risk of data loss.

5. **Bulk operations can partially fail** -- A `scim-bulk create` request can succeed for some operations and fail for others. The `--fail-on-errors` parameter controls the abort threshold. Always check the response body for per-operation `status` codes (e.g., `201` for created, `409` for duplicate).

6. **`/me` endpoint requires user-level token, not admin** -- `scim-users show-me` and `people list-me` return the identity of the authenticated user. These fail with admin service-app tokens because service apps do not represent a person. Use a user-level OAuth token.

7. **Domain verification requires DNS TXT record -- this skill cannot verify DNS** -- After providing the verification token, instruct the user to add the TXT record and wait for propagation (typically 15-60 minutes, up to 48 hours). Do not call `verify-domain` until the user confirms the TXT record is in place.

8. **Org contacts bulk import/delete are async jobs -- poll for completion** -- The `create-bulk` and `create-delete` commands may return before all items are processed. Verify results after completion.

9. **ALWAYS show plan before executing write operations** -- Never create, update, or delete users, groups, contacts, or domains without presenting the plan and getting user confirmation.

10. **SCIM commands require org ID as positional argument** -- All `scim-users`, `scim-groups`, and `scim-bulk` commands require `ORG_ID` as the first positional argument. Webex REST API commands (`people`, `groups`) do not -- they use the org implied by the token.

11. **Identity scopes are separate from Calling scopes** -- SCIM endpoints require `identity:people_rw` / `identity:people_read`. Webex REST endpoints (`people`, `groups`) require `spark-admin:people_write` / `spark-admin:people_read`. Mixing them up produces 403 errors.

12. **People API `emails` must use `--json-body`** -- The `people create` command does not have a `--emails` CLI option. Pass emails via `--json-body '{"emails": ["user@example.com"], ...}'`.

13. **If users need Webex Calling after identity provisioning**, switch to the `provision-calling` skill to assign calling licenses and configure locations. SCIM user creation does not assign calling licenses — that's a separate workflow.

14. **If bulk-creating 20+ users with calling licenses**, consider using `provision-calling` skill directly instead of SCIM → license assignment as two separate steps. The provisioning skill can handle the full user+license workflow.

---

## Error Handling

When a wxcli command fails:

**A. Fix and retry** -- Missing required field, wrong ID, format issue:
1. Read the full error message
2. Run `wxcli <group> <command> --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** -- Resource already exists or already configured:
1. Verify current state: `wxcli scim-users show $ORG_ID $USER_ID` or `wxcli people show $PERSON_ID`
2. If state is correct, skip to next operation

**C. Escalate** -- Unclear or persistent error:
1. Run with `--debug` for raw HTTP details
2. Invoke `/wxc-calling-debug` for systematic diagnosis

Identity-specific errors:

- **403 on SCIM endpoints**: Token lacks `identity:people_rw` or `identity:people_read` scope. These are separate from `spark-admin:people_*` scopes. Verify your integration/service-app has identity scopes granted.
- **403 on domain commands**: Token lacks `identity:organizations_rw` scope. Domain management uses org-level identity scopes.
- **403 on org-contacts**: Token lacks `identity:contacts_rw` scope.
- **404 on `show-me` / `list-me`**: Using an admin/service-app token. Switch to a user-level OAuth token.
- **409 on SCIM create**: User or group already exists. GET the existing resource and decide whether to update or skip.
- **400 on SCIM filter**: Invalid SCIM filter syntax. Valid operators: `eq`, `ne`, `co` (contains), `sw` (starts with), `pr` (present), `gt`, `ge`, `lt`, `le`. Attribute names are case-sensitive.
- **400 on bulk operations**: Check per-operation status in the response. Individual operations may fail while others succeed.
- **Domain verification failure**: DNS TXT record not yet propagated. Wait and retry after confirming TXT record is in place.
- **400 on `org-contacts create`**: Missing `--schemas` or `--source`. Both are required. Schema value is always `"urn:cisco:codev:identity:contact:core:1.0"`. Source must be `CH` or `Webex4Broadworks`.

**SCIM update errors:**
- **Accidental PUT data loss:** If `scim-users update` (PUT) was run with incomplete data and attributes were deleted, recover immediately:
  1. Check if the user still exists: `wxcli scim-users show $ORG_ID $USER_ID -o json`
  2. If the user exists but is missing attributes, use PATCH to restore them:
     ```bash
     wxcli scim-users update-users $ORG_ID $USER_ID --json-body '{
       "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
       "Operations": [
         {"op": "add", "path": "emails", "value": [{"value": "user@example.com", "type": "work", "primary": true}]},
         {"op": "replace", "path": "active", "value": true}
       ]
     }'
     ```
  3. If group memberships were lost, re-add via `scim-groups update-groups`
- **400 on PATCH (invalid operation):** Check the `Operations` array format. Each operation needs `op` (add/replace/remove), `path` (attribute name), and `value` (for add/replace). The `schemas` array with the PatchOp URN is required.
- **409 on create (user exists):** The user already exists in this org. Use `scim-users list` with a filter to find the existing record: `wxcli scim-users list $ORG_ID --filter 'userName eq "user@example.com"' -o json`

---

## Required Scopes Reference

| Operation | Scope(s) |
|-----------|----------|
| List/search SCIM users | `identity:people_read` |
| Create/update/delete SCIM users | `identity:people_rw` |
| List/search SCIM groups | `identity:people_read` |
| Create/update/delete SCIM groups | `identity:people_rw` |
| SCIM bulk operations | `identity:people_rw` |
| SCIM schema introspection | `identity:people_read` |
| Identity org settings (read) | `identity:organizations_read` |
| Identity org settings (write) | `identity:organizations_rw` |
| Generate OTP for a user | `Identity:one_time_password` |
| List/view people (Webex API) | `spark-admin:people_read` |
| Create/update/delete people (Webex API) | `spark-admin:people_write` + `spark-admin:people_read` |
| Domain verification/claiming | `identity:organizations_rw` |
| Org contacts (read) | `identity:contacts_read` |
| Org contacts (write) | `identity:contacts_rw` |
| List roles | Admin token (no additional scope documented) |

---

## SCIM vs Webex API Quick Reference

Use this to decide which CLI group to use:

| Use Case | SCIM (`scim-users`, `scim-groups`) | Webex REST (`people`, `groups`) |
|----------|------------------------------------|---------------------------------|
| IdP integration (Okta, Azure AD) | Yes | No |
| Automated bulk provisioning | Yes (via `scim-bulk`) | Loop with `people create` |
| Need calling-specific data | No | Yes (`--calling-data true`) |
| Partial update (PATCH) | Yes (`update-users`) | No (PUT only on `people update`) |
| Requires org ID argument | Yes | No (uses token's org) |
| Scopes needed | `identity:people_rw` | `spark-admin:people_write` |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been done: run the relevant `list` commands
3. Resume from the first incomplete step
