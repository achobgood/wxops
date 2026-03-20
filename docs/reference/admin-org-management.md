# Admin: Organization Management

Organizations, org settings, contacts, roles, and domain management for Webex admin operations.

## Table of Contents

1. [Organizations](#1-organizations)
2. [Organization Settings](#2-organization-settings)
3. [Organization Contacts](#3-organization-contacts)
4. [Roles](#4-roles)
5. [Domain Management](#5-domain-management)
6. [Recipes](#6-recipes)
7. [Gotchas](#7-gotchas)

## Sources

- OpenAPI spec: `webex-admin.json` -- Organizations, Organization Settings, Organization Contacts, Roles, Domain Management tags
- CLI source: `src/wxcli/commands/organizations.py`, `org_settings.py`, `org_contacts.py`, `roles.py`, `domains.py`
- [Webex Developer Docs -- Organizations](https://developer.webex.com/docs/api/v1/organizations)

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `identity:organizations_read` | Read organization details and settings. Required for `organizations list`, `organizations show`, `org-settings show`. |
| `identity:organizations_rw` | Write organization settings and manage domains. Required for `org-settings create`, all `domains` commands. |
| `identity:contacts_rw` | Create, update, delete organization contacts. Required for all `org-contacts` write commands. |
| `identity:contacts_read` | Read organization contacts. Required for `org-contacts list`, `org-contacts show`. Without this scope (or `identity:contacts_rw`), the API returns 403 Forbidden. A standard admin token alone is not sufficient. <!-- Verified via live API 2026-03-19: admin token without identity:contacts_read scope gets 403 --> |
| (admin token) | `roles list` and `roles show` require a valid admin token. No additional scopes documented. <!-- Verified via OpenAPI spec (webex-admin.json): "Must be called by an admin user." No scopes listed. 2026-03-19 --> |
| (full admin) | `organizations delete` requires full administrator privileges. |

**Note:** Scope names for organizations and domains use the `identity:` prefix, not the `spark-admin:` prefix used by Calling APIs. This is a common source of 401/403 errors when reusing Calling tokens for admin operations.

---

## 1. Organizations

Manage Webex organizations. Most admin tokens are scoped to a single org, so `organizations list` typically returns one item.

### CLI Commands

| Command | Description | HTTP Method | Path |
|---------|-------------|-------------|------|
| `wxcli organizations list` | List organizations | `GET` | `/v1/organizations` |
| `wxcli organizations show` | Get organization details | `GET` | `/v1/organizations/{orgId}` |
| `wxcli organizations delete` | Delete an organization | `DELETE` | `/v1/organizations/{orgId}` |

### CLI Examples

**List all organizations visible to the current token:**

```bash
wxcli organizations list
```

**Get details for a specific org (returns JSON with display name, creation date, etc.):**

```bash
wxcli organizations show Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0
```

**Delete an organization (prompts for confirmation):**

```bash
wxcli organizations delete Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0
```

**Delete without confirmation prompt (use with extreme caution):**

```bash
wxcli organizations delete Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0 --force
```

### Raw HTTP Fallback

```bash
# List organizations
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/organizations" | jq '.items[]'

# Get organization details
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/organizations/$ORG_ID" | jq .

# Delete organization (irreversible!)
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/organizations/$ORG_ID"
```

### Gotchas

- **`organizations delete` is destructive and irreversible.** Deleting an organization removes all users, licenses, devices, and configuration permanently. The CLI prompts for confirmation unless `--force` is passed. There is no undo.

- **`organizations list` typically returns one org.** Unless your token is a partner/MSP token with cross-org access, you will only see the single organization the token belongs to.

---

## 2. Organization Settings

Read and write org-level settings (key/value pairs). The `create` command is a POST-as-upsert -- it creates the setting if it does not exist, or updates it if it already does.

### CLI Commands

| Command | Description | HTTP Method | Path |
|---------|-------------|-------------|------|
| `wxcli org-settings show` | Get an organization setting by key | `GET` | `/v1/settings/organizations/{orgId}/settings/{settingKey}` |
| `wxcli org-settings create` | Create or update an organization setting | `POST` | `/v1/settings/organizations/{orgId}/settings` |

### CLI Examples

**Read a specific setting by key:**

```bash
wxcli org-settings show Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0 callingBehavior
```

**Set/update a boolean setting:**

```bash
wxcli org-settings create Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0 \
  --key callingBehavior --value
```

**Set a setting to false:**

```bash
wxcli org-settings create Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0 \
  --key callingBehavior --no-value
```

**Use --json-body for non-boolean or complex settings:**

```bash
wxcli org-settings create Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0 \
  --json-body '{"key": "myCustomSetting", "value": "customValue"}'
```

### Raw HTTP Fallback

```bash
# Read a setting
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/settings/organizations/$ORG_ID/settings/callingBehavior" | jq .

# Create or update a setting
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key": "callingBehavior", "value": true}' \
  "https://webexapis.com/v1/settings/organizations/$ORG_ID/settings"
```

### Gotchas

- **`org-settings create` is POST-as-upsert.** Despite the command name `create`, this endpoint creates the setting if it does not exist or updates it if it already does. There is no separate `update` command. The HTTP method is POST, not PUT or PATCH.

- **`org-settings show` value type.** The `--value/--no-value` flag on `org-settings create` only supports boolean settings. The OpenAPI schema (`updateOrgSettingObject`) defines the `value` field as `type: boolean`. For any non-boolean values, use `--json-body`. <!-- Verified via OpenAPI spec (webex-admin.json): updateOrgSettingObject schema defines value as type:boolean. 2026-03-19 -->

---

## 3. Organization Contacts

Manage organization-level contacts (shared directory entries). Contacts use a SCIM-like schema with `urn:cisco:codev:identity:contact:core:1.0`.

### CLI Commands

| Command | Description | HTTP Method | Path |
|---------|-------------|-------------|------|
| `wxcli org-contacts create` | Create a contact | `POST` | `/v1/contacts/organizations/{orgId}/contacts` |
| `wxcli org-contacts show` | Get a contact by ID | `GET` | `/v1/contacts/organizations/{orgId}/contacts/{contactId}` |
| `wxcli org-contacts update` | Update a contact | `PATCH` | `/v1/contacts/organizations/{orgId}/contacts/{contactId}` |
| `wxcli org-contacts delete` | Delete a contact | `DELETE` | `/v1/contacts/organizations/{orgId}/contacts/{contactId}` |
| `wxcli org-contacts list` | Search/list contacts | `GET` | `/v1/contacts/organizations/{orgId}/contacts/search` |
| `wxcli org-contacts create-bulk` | Bulk create or update contacts | `POST` | `/v1/contacts/organizations/{orgId}/contacts/bulk` |
| `wxcli org-contacts create-delete` | Bulk delete contacts | `POST` | `/v1/contacts/organizations/{orgId}/contacts/bulk/delete` |

### CLI Examples

**List all contacts in an org:**

```bash
wxcli org-contacts list $ORG_ID
```

**Search contacts by keyword:**

```bash
wxcli org-contacts list $ORG_ID --keyword "Smith" --source CH
```

**Create a single contact:**

```bash
wxcli org-contacts create $ORG_ID \
  --schemas "urn:cisco:codev:identity:contact:core:1.0" \
  --source CH \
  --display-name "Jane Smith" \
  --first-name "Jane" \
  --last-name "Smith" \
  --company-name "Acme Corp" \
  --primary-contact-method EMAIL
```

**Get contact details:**

```bash
wxcli org-contacts show $ORG_ID $CONTACT_ID
```

**Update a contact's company name:**

```bash
wxcli org-contacts update $ORG_ID $CONTACT_ID \
  --company-name "New Corp Name"
```

**Delete a contact (with confirmation prompt):**

```bash
wxcli org-contacts delete $ORG_ID $CONTACT_ID
```

**Bulk create/update contacts via --json-body:**

```bash
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
```

**Bulk delete contacts:**

```bash
wxcli org-contacts create-delete $ORG_ID \
  --schemas "urn:cisco:codev:identity:contact:core:1.0" \
  --json-body '{
    "schemas": "urn:cisco:codev:identity:contact:core:1.0",
    "contactIds": ["contact-id-1", "contact-id-2"]
  }'
```

### Raw HTTP Fallback

```bash
# List/search contacts
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/contacts/organizations/$ORG_ID/contacts/search?keyword=Smith" | jq .

# Create a contact
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": "urn:cisco:codev:identity:contact:core:1.0",
    "source": "CH",
    "displayName": "Jane Smith",
    "firstName": "Jane",
    "lastName": "Smith",
    "primaryContactMethod": "EMAIL",
    "emails": [{"value": "jane@example.com", "type": "work"}]
  }' \
  "https://webexapis.com/v1/contacts/organizations/$ORG_ID/contacts"

# Update a contact (PATCH)
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"companyName": "Updated Corp"}' \
  "https://webexapis.com/v1/contacts/organizations/$ORG_ID/contacts/$CONTACT_ID"

# Delete a contact
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/contacts/organizations/$ORG_ID/contacts/$CONTACT_ID"

# Bulk create/update
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": "urn:cisco:codev:identity:contact:core:1.0",
    "contacts": [...]
  }' \
  "https://webexapis.com/v1/contacts/organizations/$ORG_ID/contacts/bulk"

# Bulk delete
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": "urn:cisco:codev:identity:contact:core:1.0",
    "contactIds": ["id1", "id2"]
  }' \
  "https://webexapis.com/v1/contacts/organizations/$ORG_ID/contacts/bulk/delete"
```

### Gotchas

- **`org-contacts list` uses a search endpoint.** The list command hits `/contacts/search`, not a plain list endpoint. Without any filters (`--keyword`, `--source`), it returns all contacts, but the response key is `result`, not `items`. The CLI handles this automatically. <!-- Verified via source code 2026-03-19 -->

- **`org-contacts create` requires `--schemas` and `--source`.** Both are mandatory. The schema value is always `"urn:cisco:codev:identity:contact:core:1.0"`. Source must be `CH` (Control Hub) or `Webex4Broadworks`.

- **Bulk operations (`create-bulk`, `create-delete`) require `--json-body`.** The CLI flags for these commands only accept `--schemas`. The actual contact list or contact ID list must be passed via `--json-body` with the full JSON payload.

---

## 4. Roles

List and inspect Webex admin roles. Roles are used when assigning admin privileges to users via the People API. Role IDs are needed when creating or updating a person's `roles` array.

### CLI Commands

| Command | Description | HTTP Method | Path |
|---------|-------------|-------------|------|
| `wxcli roles list` | List all available roles | `GET` | `/v1/roles` |
| `wxcli roles show` | Get details for a specific role | `GET` | `/v1/roles/{roleId}` |

### CLI Examples

**List all roles:**

```bash
wxcli roles list
```

**List roles as JSON (to get full role metadata):**

```bash
wxcli roles list -o json
```

**Get details for a specific role:**

```bash
wxcli roles show Y2lzY29zcGFyazovL3VzL1JPTEUvOTZhYmMyYWEtM2RjYy0xMWU1LWExNTItZmUzNDgxOWNkYzlh
```

### Raw HTTP Fallback

```bash
# List all roles
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/roles" | jq '.items[] | {id, name}'

# Get a specific role
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/roles/$ROLE_ID" | jq .
```

---

## 5. Domain Management

Manage domain verification and claiming for a Webex organization. Domain verification proves ownership via DNS TXT records; claiming associates the domain with the org for user provisioning.

### CLI Commands

| Command | Description | HTTP Method | Path |
|---------|-------------|-------------|------|
| `wxcli domains get-domain-verification` | Get DNS verification token for a domain | `POST` | `/v1/identity/organizations/{orgId}/actions/getDomainVerificationToken` |
| `wxcli domains verify-domain` | Verify a domain (after DNS TXT record is set) | `POST` | `/v1/identity/organizations/{orgId}/actions/verifyDomain` |
| `wxcli domains claim-domain` | Claim a verified domain for the org | `POST` | `/v1/identity/organizations/{orgId}/actions/claimDomain` |
| `wxcli domains unverify-domain` | Remove verification from a domain | `POST` | `/v1/identity/organizations/{orgId}/actions/unverifyDomain` |
| `wxcli domains unclaim-domain` | Release a claimed domain | `POST` | `/v1/identity/organizations/{orgId}/actions/unclaimDomain` |

### CLI Examples

**Step 1 -- Get the DNS verification token:**

```bash
wxcli domains get-domain-verification $ORG_ID --domain "example.com"
```

This returns a token value. Create a DNS TXT record for `example.com` with the returned token.

**Step 2 -- Verify the domain (after DNS propagation):**

```bash
wxcli domains verify-domain $ORG_ID --domain "example.com"
```

**Step 3 -- Claim the domain:**

```bash
wxcli domains claim-domain $ORG_ID
```

**Verify and claim in a single step:**

```bash
wxcli domains verify-domain $ORG_ID --domain "example.com" --claim-domain true
```

**Force-claim a domain (even if users exist on other orgs):**

```bash
wxcli domains claim-domain $ORG_ID --force-domain-claim true
```

**Claim domain without searching/marking existing users:**

```bash
wxcli domains claim-domain $ORG_ID --claim-domain-only true
```

**Unverify a domain:**

```bash
wxcli domains unverify-domain $ORG_ID --domain "example.com"
```

**Unverify and remove pending domain:**

```bash
wxcli domains unverify-domain $ORG_ID --domain "example.com" --remove-pending true
```

**Unclaim (release) a domain:**

```bash
wxcli domains unclaim-domain $ORG_ID --domain "example.com"
```

### Raw HTTP Fallback

```bash
# Get verification token
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}' \
  "https://webexapis.com/v1/identity/organizations/$ORG_ID/actions/getDomainVerificationToken" | jq .

# Verify domain
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}' \
  "https://webexapis.com/v1/identity/organizations/$ORG_ID/actions/verifyDomain" | jq .

# Claim domain
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "https://webexapis.com/v1/identity/organizations/$ORG_ID/actions/claimDomain" | jq .

# Unverify domain
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}' \
  "https://webexapis.com/v1/identity/organizations/$ORG_ID/actions/unverifyDomain" | jq .

# Unclaim domain
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}' \
  "https://webexapis.com/v1/identity/organizations/$ORG_ID/actions/unclaimDomain" | jq .
```

### Gotchas

- **Domain commands are all POST, not GET/PUT/DELETE.** Every domain management command uses POST to an action-style URL (e.g., `/actions/verifyDomain`). This is an RPC-style API, not REST-style.

- **DNS propagation delay.** After adding the TXT record for domain verification, allow time for DNS propagation before calling `verify-domain`. If verification fails, wait and retry -- it can take up to 48 hours in worst cases. The OpenAPI spec documents two errors: 400 ("The domain can't be verified. This error happens if the user didn't request a token before trying to verify the domain") and 409 ("The domain has already been claimed by another organization"). The `verify-domain` endpoint requires `identity:organizations_rw` scope; without it, the API returns 401 with error code 200003 ("Sorry, you don't have sufficient privileges"). The exact error body for DNS-not-yet-propagated (as distinct from the 400 "didn't request a token" error) could not be tested without a real domain setup. <!-- Partially verified via live API 2026-03-19: confirmed 401/200003 without identity:organizations_rw scope. DNS propagation error body still unverified — would require adding a real domain TXT record -->

---

## 6. Recipes

### Recipe: Domain Verification Workflow

Complete end-to-end flow for adding a domain to your Webex org.

```bash
# 1. Get the verification token
wxcli domains get-domain-verification $ORG_ID --domain "newdomain.com"
# Response includes a token like: "webex-verification=abc123def456"

# 2. Add DNS TXT record (outside wxcli -- use your DNS provider)
#    Record type: TXT
#    Name: @ (or newdomain.com)
#    Value: webex-verification=abc123def456
#    Wait for DNS propagation (can take up to 48 hours, typically 15-60 minutes)

# 3. Verify the domain
wxcli domains verify-domain $ORG_ID --domain "newdomain.com"

# 4. Claim the domain for user provisioning
wxcli domains claim-domain $ORG_ID

# Or combine steps 3 and 4:
wxcli domains verify-domain $ORG_ID --domain "newdomain.com" --claim-domain true
```

### Recipe: Bulk Import Organization Contacts

Import a batch of contacts from a prepared JSON file.

```bash
# Prepare contacts.json:
# {
#   "schemas": "urn:cisco:codev:identity:contact:core:1.0",
#   "contacts": [
#     {
#       "displayName": "Alice Johnson",
#       "firstName": "Alice",
#       "lastName": "Johnson",
#       "source": "CH",
#       "primaryContactMethod": "EMAIL",
#       "emails": [{"value": "alice@example.com", "type": "work"}]
#     },
#     {
#       "displayName": "Bob Williams",
#       "firstName": "Bob",
#       "lastName": "Williams",
#       "source": "CH",
#       "primaryContactMethod": "PHONE",
#       "phoneNumbers": [{"value": "+14155551234", "type": "work"}]
#     }
#   ]
# }

wxcli org-contacts create-bulk $ORG_ID \
  --schemas "urn:cisco:codev:identity:contact:core:1.0" \
  --json-body "$(cat contacts.json)"
```

### Recipe: List Admin Roles and Find a Specific Role

```bash
# List all roles in table format
wxcli roles list

# Get full JSON output to see role names and IDs
wxcli roles list -o json

# Once you have the role ID, inspect it
wxcli roles show $ROLE_ID

# Common admin roles to look for:
# - Full Administrator
# - Read-Only Administrator
# - User and Device Administrator
# - Device Administrator
# - Compliance Officer
# - Webex Calling Detailed Call History API access
```

### Recipe: Inspect Your Own Org

```bash
# List orgs to get your org ID
wxcli organizations list

# Get full org details (creation date, display name, etc.)
wxcli organizations show $ORG_ID -o json
```

---

## 7. Gotchas

Cross-cutting gotchas that apply across multiple sections. Section-specific gotchas are inline above.

- **Scope confusion: `identity:` vs `spark-admin:`.** Organization, settings, contacts, and domain APIs use `identity:*` scopes (e.g., `identity:organizations_read`). Webex Calling APIs use `spark-admin:*` scopes. A token with only `spark-admin:` scopes will get 401/403 on organization management endpoints. Verify your integration or service app has the correct `identity:` scopes.

---

## See Also

- **[provisioning.md](provisioning.md)** -- For Webex Calling locations within an org, see the provisioning reference. Organization management sets up the org container; provisioning configures calling-specific resources inside it.
- **[authentication.md](authentication.md)** -- OAuth scopes, token types, and service app configuration. Pay special attention to `identity:*` scopes for the endpoints in this doc.
- **[reporting-analytics.md](reporting-analytics.md)** -- CDR and analytics APIs that operate at the org level. Requires different scopes (`spark-admin:calling_cdr_read`, `analytics:read_all`).
