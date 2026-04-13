# Admin: Identity & SCIM

SCIM 2.0 user/group provisioning, Webex People/Groups APIs, identity org settings, and directory management.

## Sources

- [SCIM 2.0 Protocol (RFC 7644)](https://datatracker.ietf.org/doc/html/rfc7644) -- Standard protocol for cross-domain identity management
- [Webex SCIM 2.0 Users API](https://developer.webex.com/docs/api/v1/scim2-user) -- Official API docs
- [Webex People API](https://developer.webex.com/docs/api/v1/people) -- Official API docs
- [Webex Groups API](https://developer.webex.com/docs/api/v1/groups) -- Official API docs
- OpenAPI spec: `specs/webex-admin.json` -- Tags: SCIM 2 Users, SCIM 2 Groups, SCIM 2 Schemas, Bulk Manage SCIM 2 Users and Groups, Identity Organization, Groups, People

---

## Key Concepts

### SCIM 2.0 Protocol

SCIM (System for Cross-domain Identity Management) is a standardized REST protocol for provisioning and managing user identities across systems. Webex implements SCIM 2.0 at `/identity/scim/{orgId}/v2/` endpoints. Key SCIM concepts:

- **Resources** are Users and Groups, represented as JSON objects with standard schemas.
- **Schemas** define the attributes available on each resource type. Webex extends the core SCIM schemas with `urn:scim:schemas:extension:cisco:webexidentity:2.0:User` and `urn:scim:schemas:extension:cisco:webexidentity:2.0:Group`.
- **Filters** use SCIM filter syntax for search: `filter=userName eq "user@example.com"` or `filter=displayName co "Engineering"`. Operators: `eq`, `ne`, `co` (contains), `sw` (starts with), `pr` (present), `gt`, `ge`, `lt`, `le`.
- **Bulk operations** allow multiple create/update/delete operations in a single HTTP request via the `/Bulk` endpoint.

### PUT vs PATCH

Both SCIM user and group endpoints support two update methods:

- **PUT** (`update` commands) -- Replaces the entire resource. Any attribute not included in the PUT body is removed. Always GET the resource first, modify the JSON, then PUT the full object back.
- **PATCH** (`update-users` / `update-groups` commands) -- Partial update. Only the specified attributes are changed; all other attributes are left intact. Uses SCIM patch operations: `add`, `replace`, `remove`.

### scim-users vs people

Both manage user accounts, but serve different purposes:

| Aspect | `scim-users` | `people` |
|--------|-------------|----------|
| Protocol | SCIM 2.0 (RFC 7644) | Webex REST API |
| Base path | `/identity/scim/{orgId}/v2/Users` | `/v1/people` |
| Primary use | IdP sync, automated provisioning, directory integration | Webex-native user management, manual CRUD |
| Requires `orgId` arg | Yes | No (uses token's org) |
| Update methods | PUT (full replace) + PATCH (partial) | PUT only |
| Scopes | `identity:people_rw` / `identity:people_read` | `spark-admin:people_write` / `spark-admin:people_read` |
| Calling data | Not returned | Optional via `--calling-data true` |

Use `scim-users` when integrating with an external IdP (Okta, Azure AD, etc.) or doing bulk provisioning. Use `people` for Webex-native user management and when you need calling-specific data.

### scim-groups vs groups

| Aspect | `scim-groups` | `groups` |
|--------|--------------|----------|
| Protocol | SCIM 2.0 | Webex REST API |
| Base path | `/identity/scim/{orgId}/v2/Groups` | `/v1/groups` |
| Primary use | IdP group sync, directory groups | Webex-native group management |
| Requires `orgId` arg | Yes | No (uses token's org) |
| Update methods | PUT + PATCH | PATCH only |
| Member listing | Via `--include-members` on list/show | Separate `list-members` command |

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `identity:people_rw` | Read and write SCIM users, SCIM groups, and SCIM bulk operations. |
| `identity:people_read` | Read-only access to SCIM users and SCIM groups. |
| `identity:organizations_rw` | Read and write identity organization settings. |
| `identity:organizations_read` | Read-only access to identity organization settings. |
| `Identity:one_time_password` | Generate OTP for a user.  |
| `spark-admin:people_write` | Create, update, and delete people (Webex REST API).  |
| `spark-admin:people_read` | List and get people (Webex REST API).  |

**Note:** SCIM endpoints (`scim-users`, `scim-groups`, `scim-bulk`) use `identity:*` scopes. Webex REST endpoints (`people`, `groups`) use `spark-admin:*` scopes. Mixing them up produces 403 errors.

---

## Table of Contents

1. [SCIM Users (`scim-users`)](#1-scim-users-scim-users)
2. [SCIM Groups (`scim-groups`)](#2-scim-groups-scim-groups)
3. [SCIM Schemas (`scim-schemas`)](#3-scim-schemas-scim-schemas)
4. [SCIM Bulk Operations (`scim-bulk`)](#4-scim-bulk-operations-scim-bulk)
5. [Identity Organization (`identity-org`)](#5-identity-organization-identity-org)
6. [Groups (Webex REST API) (`groups`)](#6-groups-webex-rest-api-groups)
7. [People (Webex REST API) (`people`)](#7-people-webex-rest-api-people)
8. [Recipes](#recipes)
9. [Gotchas](#gotchas)
10. [See Also](#see-also)

---

## 1. SCIM Users (`scim-users`)

SCIM 2.0 user provisioning and management. All commands require an `org-id` positional argument.

### Endpoints

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | `/identity/scim/{orgId}/v2/Users` | `scim-users list` |
| POST | `/identity/scim/{orgId}/v2/Users` | `scim-users create` |
| GET | `/identity/scim/{orgId}/v2/Users/{userId}` | `scim-users show` |
| PUT | `/identity/scim/{orgId}/v2/Users/{userId}` | `scim-users update` |
| PATCH | `/identity/scim/{orgId}/v2/Users/{userId}` | `scim-users update-users` |
| DELETE | `/identity/scim/{orgId}/v2/Users/{userId}` | `scim-users delete` |
| GET | `/identity/scim/v2/Users/me` | `scim-users show-me` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `list` | Search users with SCIM filters | `--filter`, `--attributes`, `--excluded-attributes`, `--sort-by`, `--sort-order`, `--start-index`, `--count`, `--return-groups`, `--include-group-details`, `--group-usage-types` |
| `create` | Create a SCIM user | `--user-name` (required), `--display-name`, `--title`, `--active/--no-active`, `--preferred-language`, `--locale`, `--timezone`, `--external-id`, `--nick-name`, `--profile-url`, `--json-body` |
| `show` | Get a single user by ID | `ORG_ID`, `USER_ID` (positional) |
| `update` | Full replace (PUT) of user | Same options as `create` plus `USER_ID` positional. **Replaces entire resource.** |
| `update-users` | Partial update (PATCH) of user | `--json-body` only (SCIM patch operations) |
| `delete` | Delete a user | `--force` to skip confirmation |
| `show-me` | Get authenticated user's own SCIM record | No `org-id` required. Requires user-level token. |

### CLI Examples

```bash
# List all SCIM users in the org
wxcli scim-users list YOUR_ORG_ID

# Search for a specific user by email
wxcli scim-users list YOUR_ORG_ID --filter 'userName eq "jsmith@example.com"'

# Search users by display name (contains)
wxcli scim-users list YOUR_ORG_ID --filter 'displayName co "Smith"'

# Get specific user attributes only
wxcli scim-users list YOUR_ORG_ID --filter 'userName sw "j"' --attributes "userName,displayName,emails"

# Create a new SCIM user
wxcli scim-users create YOUR_ORG_ID --user-name "newuser@example.com" --display-name "New User" --active

# Create user with full JSON body (for nested fields like name, emails, addresses)
wxcli scim-users create YOUR_ORG_ID --json-body '{
  "userName": "jdoe@example.com",
  "displayName": "Jane Doe",
  "name": {"givenName": "Jane", "familyName": "Doe"},
  "emails": [{"value": "jdoe@example.com", "type": "work", "primary": true}],
  "active": true
}'

# Get a specific user
wxcli scim-users show YOUR_ORG_ID USER_ID -o json

# Full replace a user (PUT) -- always GET first to avoid data loss
wxcli scim-users update YOUR_ORG_ID USER_ID --json-body '{ ... full user JSON ... }'

# Partial update a user (PATCH) -- change only specific fields
wxcli scim-users update-users YOUR_ORG_ID USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "replace", "path": "displayName", "value": "Jane M. Doe"},
    {"op": "replace", "path": "title", "value": "Senior Engineer"}
  ]
}'

# Deactivate a user via PATCH
wxcli scim-users update-users YOUR_ORG_ID USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": false}]
}'

# Delete a user (with confirmation skip)
wxcli scim-users delete YOUR_ORG_ID USER_ID --force

# Get your own SCIM identity (user-level token required)
wxcli scim-users show-me -o json
```

### Raw HTTP Fallback

```bash
# List SCIM users
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Users?filter=userName%20eq%20%22user%40example.com%22"

# Create a SCIM user
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Users" \
  -d '{"schemas":["urn:ietf:params:scim:schemas:core:2.0:User"],"userName":"user@example.com","displayName":"New User","active":true}'

# PATCH a SCIM user (partial update)
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Users/USER_ID" \
  -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{"op":"replace","path":"active","value":false}]}'
```

> **Gotcha — PUT Replaces the Entire Resource:**
> The `scim-users update` and `scim-groups update` commands use HTTP PUT, which replaces the entire resource. If you PUT a user without including their `emails`, `phoneNumbers`, or `addresses`, those fields are removed.
>
> **Safe pattern:** Always GET the current resource first, modify the JSON, then PUT the full object back:
> ```bash
> # Step 1: GET current state
> wxcli scim-users show YOUR_ORG_ID USER_ID -o json > user.json
> # Step 2: Edit user.json to change what you need
> # Step 3: PUT the modified full object
> wxcli scim-users update YOUR_ORG_ID USER_ID --json-body "$(cat user.json)"
> ```
> **Better alternative:** Use PATCH (`update-users` / `update-groups`) for partial updates whenever possible.

---

## 2. SCIM Groups (`scim-groups`)

SCIM 2.0 group provisioning and management. All commands require an `org-id` positional argument.

### Endpoints

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | `/identity/scim/{orgId}/v2/Groups` | `scim-groups list` |
| POST | `/identity/scim/{orgId}/v2/Groups` | `scim-groups create` |
| GET | `/identity/scim/{orgId}/v2/Groups/{groupId}` | `scim-groups show` |
| PUT | `/identity/scim/{orgId}/v2/Groups/{groupId}` | `scim-groups update` |
| PATCH | `/identity/scim/{orgId}/v2/Groups/{groupId}` | `scim-groups update-groups` |
| DELETE | `/identity/scim/{orgId}/v2/Groups/{groupId}` | `scim-groups delete` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `list` | Search groups with SCIM filters | `--filter`, `--attributes`, `--excluded-attributes`, `--sort-by`, `--sort-order`, `--start-index`, `--count`, `--include-members`, `--member-type` |
| `create` | Create a SCIM group | `--display-name` (required), `--external-id`, `--json-body` |
| `show` | Get a single group by ID | `--excluded-attributes` |
| `update` | Full replace (PUT) of group | `--display-name`, `--external-id`, `--json-body`. **Replaces entire resource.** |
| `update-groups` | Partial update (PATCH) of group | `--json-body` only (SCIM patch operations) |
| `delete` | Delete a group | `--force` to skip confirmation |

### CLI Examples

```bash
# List all SCIM groups
wxcli scim-groups list YOUR_ORG_ID

# Search for a group by name
wxcli scim-groups list YOUR_ORG_ID --filter 'displayName eq "Engineering"'

# List groups with member details
wxcli scim-groups list YOUR_ORG_ID --include-members true --member-type user

# Create a SCIM group
wxcli scim-groups create YOUR_ORG_ID --display-name "DevOps Team"

# Create a group with members via JSON body
wxcli scim-groups create YOUR_ORG_ID --json-body '{
  "displayName": "DevOps Team",
  "members": [
    {"value": "USER_ID_1", "type": "user"},
    {"value": "USER_ID_2", "type": "user"}
  ]
}'

# Add a member to a group via PATCH
wxcli scim-groups update-groups YOUR_ORG_ID GROUP_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "add", "path": "members", "value": [{"value": "USER_ID", "type": "user"}]}
  ]
}'

# Remove a member from a group via PATCH
wxcli scim-groups update-groups YOUR_ORG_ID GROUP_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "remove", "path": "members[value eq \"USER_ID\"]"}
  ]
}'

# Delete a group
wxcli scim-groups delete YOUR_ORG_ID GROUP_ID --force
```

### Raw HTTP Fallback

```bash
# List SCIM groups
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups"

# Search SCIM groups by name
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups?filter=displayName%20eq%20%22Engineering%22"

# Create a SCIM group
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups" \
  -d '{"schemas":["urn:ietf:params:scim:schemas:core:2.0:Group"],"displayName":"DevOps Team"}'

# Get a SCIM group by ID
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups/GROUP_ID"

# PUT (full replace) a SCIM group
curl -s -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups/GROUP_ID" \
  -d '{"schemas":["urn:ietf:params:scim:schemas:core:2.0:Group"],"displayName":"DevOps Team","members":[{"value":"USER_ID","type":"user"}]}'

# PATCH a SCIM group (add member)
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups/GROUP_ID" \
  -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{"op":"add","path":"members","value":[{"value":"USER_ID","type":"user"}]}]}'

# Delete a SCIM group
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Groups/GROUP_ID"
```

---

## 3. SCIM Schemas (`scim-schemas`)

Retrieve the SCIM schema definitions that describe available attributes for Users and Groups. Useful for discovering which fields are available and their types before creating or updating resources.

### Endpoints

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | `/Schemas/SCIM2/Group` | `scim-schemas show` |
| GET | `/Schemas/SCIM2/User` | `scim-schemas show-user` |
| GET | `/Schemas/SCIM2/{schemaId}` | `scim-schemas show-scim2` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `show` | Get the Group schema definition | `-o json` |
| `show-user` | Get the User schema definition | `-o json` |
| `show-scim2` | Get a schema by its schema ID | `SCHEMA_ID` (positional), `-o json` |

### CLI Examples

```bash
# Get the SCIM User schema (discover all available user attributes)
wxcli scim-schemas show-user -o json

# Get the SCIM Group schema
wxcli scim-schemas show -o json

# Get a specific schema by ID (e.g., the Cisco extension schema)
wxcli scim-schemas show-scim2 "urn:scim:schemas:extension:cisco:webexidentity:2.0:User" -o json
```

### Key Schema URNs

| Schema URN | Description |
|------------|-------------|
| `urn:ietf:params:scim:schemas:core:2.0:User` | Core SCIM user attributes |
| `urn:ietf:params:scim:schemas:core:2.0:Group` | Core SCIM group attributes |
| `urn:scim:schemas:extension:cisco:webexidentity:2.0:User` | Cisco/Webex extension attributes for users |
| `urn:scim:schemas:extension:cisco:webexidentity:2.0:Group` | Cisco/Webex extension attributes for groups |
| `urn:ietf:params:scim:api:messages:2.0:PatchOp` | Schema for PATCH operation payloads |
| `urn:ietf:params:scim:api:messages:2.0:BulkRequest` | Schema for bulk operation request payloads |

### Raw HTTP Fallback

```bash
# Get the SCIM User schema
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/Schemas/SCIM2/User"

# Get the SCIM Group schema
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/Schemas/SCIM2/Group"

# Get a schema by ID (e.g., Cisco extension schema)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/Schemas/SCIM2/urn:scim:schemas:extension:cisco:webexidentity:2.0:User"
```

---

## 4. SCIM Bulk Operations (`scim-bulk`)

Execute multiple SCIM user/group operations in a single HTTP request. Supports creating, updating, and deleting users and groups in bulk.

### Endpoint

| Method | Path | CLI Command |
|--------|------|-------------|
| POST | `/identity/scim/{orgId}/v2/Bulk` | `scim-bulk create` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `create` | Execute a bulk SCIM operation | `ORG_ID` (positional), `--fail-on-errors` (required), `--json-body` |

The `--fail-on-errors` parameter specifies the maximum number of individual operation failures before the entire bulk request is aborted.

### CLI Examples

```bash
# Bulk create multiple users
wxcli scim-bulk create YOUR_ORG_ID --fail-on-errors 5 --json-body '{
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

# Bulk deactivate users
wxcli scim-bulk create YOUR_ORG_ID --fail-on-errors 10 --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "failOnErrors": 10,
  "Operations": [
    {
      "method": "PATCH",
      "path": "/Users/USER_ID_1",
      "data": {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "active", "value": false}]
      }
    },
    {
      "method": "PATCH",
      "path": "/Users/USER_ID_2",
      "data": {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "active", "value": false}]
      }
    }
  ]
}'

# Bulk delete users
wxcli scim-bulk create YOUR_ORG_ID --fail-on-errors 0 --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "failOnErrors": 0,
  "Operations": [
    {"method": "DELETE", "path": "/Users/USER_ID_1"},
    {"method": "DELETE", "path": "/Users/USER_ID_2"}
  ]
}'
```

### Raw HTTP Fallback

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Bulk" \
  -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],"failOnErrors":5,"Operations":[...]}'
```

> **Gotcha — Bulk Operations Can Partially Fail:**
> A `scim-bulk create` request can succeed for some operations and fail for others. The `--fail-on-errors` parameter controls the threshold: if the number of failed operations exceeds this value, the remaining operations are not attempted. Always check the response body, which contains per-operation `status` codes.
>
> Example partial failure response (abridged):
> ```json
> {
>   "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
>   "Operations": [
>     {"method": "POST", "location": "/Users/NEW_ID_1", "status": "201"},
>     {"method": "POST", "status": "409", "response": {"detail": "User already exists"}}
>   ]
> }
> ```

---

## 5. Identity Organization (`identity-org`)

Manage identity-level organization settings and generate one-time passwords for users. All commands require an `org-id` positional argument.

### Endpoints

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | `/identity/organizations/{orgId}` | `identity-org show` |
| PATCH | `/identity/organizations/{orgId}` | `identity-org update` |
| POST | `/identity/organizations/{orgId}/users/{userId}/actions/generateOtp` | `identity-org generate-otp` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `show` | Get identity organization details | `ORG_ID` (positional) |
| `update` | Update organization settings | `--display-name`, `--preferred-language`, `--json-body` |
| `generate-otp` | Generate a one-time password for a user | `ORG_ID`, `USER_ID` (positional), `--json-body` |

### CLI Examples

```bash
# Get identity org details
wxcli identity-org show YOUR_ORG_ID -o json

# Update the org display name
wxcli identity-org update YOUR_ORG_ID --display-name "Acme Corp"

# Set default language for new users
wxcli identity-org update YOUR_ORG_ID --preferred-language "en_US"

# Generate OTP for a user (for first-time login or password reset)
wxcli identity-org generate-otp YOUR_ORG_ID USER_ID
```

### Raw HTTP Fallback

```bash
# Get identity org
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/organizations/YOUR_ORG_ID"

# Update identity org
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/identity/organizations/YOUR_ORG_ID" \
  -d '{"displayName": "Acme Corp", "preferredLanguage": "en_US"}'

# Generate OTP
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/organizations/YOUR_ORG_ID/users/USER_ID/actions/generateOtp"
```

---

## 6. Groups (Webex REST API) (`groups`)

Webex-native group management. Does not require `org-id` -- uses the authenticated token's organization.

### Endpoints

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | `/v1/groups` | `groups list` |
| POST | `/v1/groups` | `groups create` |
| GET | `/v1/groups/{groupId}` | `groups show` |
| PATCH | `/v1/groups/{groupId}` | `groups update` |
| DELETE | `/v1/groups/{groupId}` | `groups delete` |
| GET | `/v1/groups/{groupId}/members` | `groups list-members` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `list` | List and search groups | `--filter`, `--attributes`, `--sort-by`, `--sort-order`, `--include-members`, `--start-index`, `--count` |
| `create` | Create a group | `--display-name` (required), `--external-id`, `--json-body` |
| `show` | Get group details | `GROUP_ID` (positional), `--include-members` |
| `update` | Update a group (PATCH) | `GROUP_ID` (positional), `--json-body` |
| `delete` | Delete a group | `GROUP_ID` (positional), `--force` |
| `list-members` | Get group members with pagination | `GROUP_ID` (positional), `--start-index`, `--count` |

### CLI Examples

```bash
# List all groups
wxcli groups list

# Search groups by name
wxcli groups list --filter 'displayName eq "Sales Team"'

# List groups with members included
wxcli groups list --include-members true

# Create a group
wxcli groups create --display-name "Support Team"

# Create a group with members via JSON body
wxcli groups create --json-body '{
  "displayName": "Support Team",
  "members": [
    {"id": "PERSON_ID_1", "type": "user"},
    {"id": "PERSON_ID_2", "type": "user"}
  ]
}'

# Get group details with members
wxcli groups show GROUP_ID --include-members true -o json

# List group members (paginated)
wxcli groups list-members GROUP_ID --count 100

# Update a group (add/remove members)
wxcli groups update GROUP_ID --json-body '{
  "members": [
    {"id": "PERSON_ID_1", "type": "user", "operation": "add"},
    {"id": "PERSON_ID_3", "type": "user", "operation": "delete"}
  ]
}'

# Delete a group
wxcli groups delete GROUP_ID --force
```

### Raw HTTP Fallback

```bash
# List groups
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/groups?includeMembers=true"

# Get group members
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/groups/GROUP_ID/members?startIndex=1&count=100"

# Create a group
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/v1/groups" \
  -d '{"displayName": "Support Team"}'
```

---

## 7. People (Webex REST API) (`people`)

Webex-native user management. Does not require `org-id` -- uses the authenticated token's organization. Supports Webex Calling data inclusion via `--calling-data`.

### Endpoints

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | `/v1/people` | `people list` |
| POST | `/v1/people` | `people create` |
| GET | `/v1/people/{personId}` | `people show` |
| PUT | `/v1/people/{personId}` | `people update` |
| DELETE | `/v1/people/{personId}` | `people delete` |
| GET | `/v1/people/me` | `people list-me` |

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `list` | List people in the org | `--email`, `--display-name`, `--id` (up to 85 IDs), `--roles`, `--calling-data`, `--location-id`, `--max`, `--exclude-status` |
| `create` | Create a person | `--display-name`, `--first-name`, `--last-name`, `--extension`, `--location-id`, `--org-id`, `--department`, `--manager`, `--manager-id`, `--title`, `--avatar`, `--json-body` |
| `show` | Get person details | `PERSON_ID` (positional) |
| `update` | Update a person (PUT) | `PERSON_ID` (positional), `--display-name`, `--first-name`, `--last-name`, `--nick-name`, `--extension`, `--location-id`, `--department`, `--manager`, `--manager-id`, `--title`, `--avatar`, `--login-enabled/--no-login-enabled`, `--json-body` |
| `delete` | Delete a person | `PERSON_ID` (positional), `--force` |
| `list-me` | Get your own details | `--calling-data` |

### CLI Examples

```bash
# List all people in the org
wxcli people list

# Search by email
wxcli people list --email "jsmith@example.com"

# Search by display name prefix
wxcli people list --display-name "John"

# List people with Webex Calling details
wxcli people list --calling-data true --location-id LOCATION_ID

# List people by multiple IDs
wxcli people list --id "ID1,ID2,ID3"

# Get a specific person
wxcli people show PERSON_ID -o json

# Create a new person (emails must be passed via --json-body)
wxcli people create --json-body '{
  "emails": ["newuser@example.com"],
  "displayName": "New User",
  "firstName": "New",
  "lastName": "User",
  "orgId": "YOUR_ORG_ID"
}'

# Update a person's department and title
wxcli people update PERSON_ID --department "Engineering" --title "Staff Engineer"

# Disable a person's login
wxcli people update PERSON_ID --no-login-enabled

# Delete a person
wxcli people delete PERSON_ID --force

# Get your own details (with calling data)
wxcli people list-me --calling-data true -o json
```

### Raw HTTP Fallback

```bash
# List people by email
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/people?email=jsmith%40example.com"

# Get person with calling data
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/people/PERSON_ID?callingData=true"

# Create a person
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/v1/people" \
  -d '{"emails":["user@example.com"],"displayName":"New User","firstName":"New","lastName":"User"}'

# Update a person (PUT -- sends full replacement)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/v1/people/PERSON_ID" \
  -d '{ ... full person JSON ... }'

# Get my own details
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/people/me?callingData=true"
```

> **Gotcha — People API: emails Must Use --json-body:**
> The `people create` command does not have a `--emails` CLI option. The `emails` field (an array of objects) is too complex for a simple CLI flag. Use `--json-body` to pass the emails array:
> ```bash
> wxcli people create --json-body '{"emails": ["user@example.com"], "displayName": "User Name"}'
> ```

> **Gotcha — People API: update is PUT (Full Replace):**
> Like the SCIM PUT, `people update` uses HTTP PUT. It replaces the entire person record. The CLI does **not** do a GET-merge-PUT for flag-based options -- it sends only the specified fields in the PUT body, which means unspecified fields may be cleared by the API. Always use `--json-body` with the full person record for safe updates, or use the GET-modify-PUT pattern shown in the SCIM section above.

---

## Recipes

### SCIM Bulk User Import

Import multiple users from a CSV/list in a single API call:

```bash
# Build a bulk request JSON file, then submit
wxcli scim-bulk create YOUR_ORG_ID --fail-on-errors 5 --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "failOnErrors": 5,
  "Operations": [
    {
      "method": "POST",
      "path": "/Users",
      "data": {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "user1@example.com",
        "displayName": "User One",
        "name": {"givenName": "User", "familyName": "One"},
        "emails": [{"value": "user1@example.com", "type": "work", "primary": true}],
        "active": true
      }
    },
    {
      "method": "POST",
      "path": "/Users",
      "data": {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "user2@example.com",
        "displayName": "User Two",
        "name": {"givenName": "User", "familyName": "Two"},
        "emails": [{"value": "user2@example.com", "type": "work", "primary": true}],
        "active": true
      }
    }
  ]
}'
```

Check the response for per-operation status. Each operation in the response has its own `status` code (e.g., `201` for created, `409` for conflict/duplicate).

### Search Users by Email or Department

```bash
# SCIM: exact email match
wxcli scim-users list YOUR_ORG_ID --filter 'userName eq "target@example.com"'

# SCIM: users whose email contains a domain
wxcli scim-users list YOUR_ORG_ID --filter 'userName co "@acme.com"'

# People API: search by email
wxcli people list --email "target@example.com"

# People API: search by name prefix
wxcli people list --display-name "John"

# SCIM: search users by department (Enterprise Extension attribute)
wxcli scim-users list YOUR_ORG_ID --filter 'department eq "Engineering"'

# SCIM: search users whose department starts with "Eng"
wxcli scim-users list YOUR_ORG_ID --filter 'department sw "Eng"'
```

### Bulk Deactivate Stale Users

Deactivate users who should no longer have Webex access. Use PATCH for efficiency (no need to send the full user record):

```bash
# Step 1: Identify users to deactivate (list and filter externally)
wxcli scim-users list YOUR_ORG_ID --filter 'active eq true' -o json > active_users.json

# Step 2: For each user to deactivate, PATCH their active status
wxcli scim-users update-users YOUR_ORG_ID USER_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": false}]
}'

# Or use bulk operations for many users at once
wxcli scim-bulk create YOUR_ORG_ID --fail-on-errors 10 --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "failOnErrors": 10,
  "Operations": [
    {"method": "PATCH", "path": "/Users/USER_ID_1", "data": {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"], "Operations": [{"op": "replace", "path": "active", "value": false}]}},
    {"method": "PATCH", "path": "/Users/USER_ID_2", "data": {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"], "Operations": [{"op": "replace", "path": "active", "value": false}]}}
  ]
}'
```

### Group Membership Management

```bash
# Webex Groups API: list members of a group
wxcli groups list-members GROUP_ID

# Webex Groups API: add a member
wxcli groups update GROUP_ID --json-body '{
  "members": [{"id": "PERSON_ID", "type": "user", "operation": "add"}]
}'

# SCIM Groups: add members via PATCH
wxcli scim-groups update-groups YOUR_ORG_ID SCIM_GROUP_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "add", "path": "members", "value": [{"value": "SCIM_USER_ID", "type": "user"}]}
  ]
}'

# SCIM Groups: remove a specific member
wxcli scim-groups update-groups YOUR_ORG_ID SCIM_GROUP_ID --json-body '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "remove", "path": "members[value eq \"SCIM_USER_ID\"]"}
  ]
}'
```

### OTP Generation

Generate a one-time password for a user who needs to sign in for the first time or has been locked out:

```bash
# Generate OTP for a user
wxcli identity-org generate-otp YOUR_ORG_ID USER_ID

# The response contains the OTP value -- share it securely with the user
```

---

## Gotchas

### /me Endpoints Require User-Level Tokens

`scim-users show-me` and `people list-me` hit the `/me` endpoint, which returns the identity of the authenticated user. These commands fail with admin service-app tokens because service apps do not represent a person. Use a user-level OAuth token (authorization code grant flow) instead.

### orgId Requirement on SCIM Commands

All SCIM commands (`scim-users`, `scim-groups`, `scim-bulk`) require `ORG_ID` as a positional argument because the org ID is part of the URL path (`/identity/scim/{orgId}/v2/...`). It cannot be omitted or inferred from the token. The Webex REST API commands (`people`, `groups`) do not require it -- they use the org implied by the token.

### Scope Troubleshooting for Identity Scopes

SCIM endpoints use `identity:*` scopes, not the `spark-admin:*` scopes used by People and Groups. If you get a 403 on SCIM endpoints, check:

1. Your integration/service-app has `identity:people_rw` or `identity:people_read` granted.
2. For `identity-org` endpoints, you need `identity:organizations_rw` or `identity:organizations_read`.
3. For OTP generation, you need `Identity:one_time_password` (note the capital "I" in `Identity`). An alternative scope is `Identity:Config`.
4. These identity scopes must be explicitly requested during OAuth authorization. They are separate from the `spark-admin:people_*` scopes.

### SCIM Filter URL Encoding

SCIM filter values must be URL-encoded when used in raw HTTP requests. The CLI handles this automatically for the `--filter` parameter, but if you are using `curl` directly, you must encode the filter:

```bash
# CLI handles encoding automatically
wxcli scim-users list YOUR_ORG_ID --filter 'userName eq "user@example.com"'

# Raw curl requires manual encoding
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/identity/scim/YOUR_ORG_ID/v2/Users?filter=userName%20eq%20%22user%40example.com%22"
```

---

## See Also

- [provisioning.md](provisioning.md) -- For Webex Calling user provisioning (licenses, extensions, locations)
- [person-call-settings-handling.md](person-call-settings-handling.md) -- For calling-specific person settings (forwarding, DND, sim ring)
- [person-call-settings-behavior.md](person-call-settings-behavior.md) -- For calling behavior, hoteling, numbers
- [authentication.md](authentication.md) -- OAuth flows, token types, scope management
