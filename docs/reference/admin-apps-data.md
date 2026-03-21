<!-- Updated by playbook session 2026-03-19 -->

# Admin: Apps, Data & Resources

Service apps, authorizations, user lifecycle operations, recordings management, data sources, and resource groups.

## Sources

- `webex-admin.json` -- OpenAPI 3.0 spec (admin/org management APIs)
- [Webex Service App documentation](https://developer.webex.com/docs/service-apps)
- [Webex Data Sources API](https://developer.webex.com/docs/api/v1/data-sources)
- [Webex Resource Groups API](https://developer.webex.com/docs/api/v1/resource-groups)

---

## Table of Contents

1. [Service Apps & Authorizations](#1-service-apps--authorizations)
2. [User Lifecycle](#2-user-lifecycle)
3. [Recordings (Admin)](#3-recordings-admin)
4. [Data & Compliance](#4-data--compliance)

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark:applications_token` | Create service app access tokens. The admin must have authorized the service app in Control Hub first. |
| `spark-admin:people_write` | Initiate bulk activation email resend jobs. |
| `spark-admin:people_read` | List authorizations, archive user lookup. |
| `spark-admin:datasource_read` | List and retrieve data sources and schemas. |
| `spark-admin:datasource_write` | Create, update, and delete data sources. |
| `spark-admin:resource_groups_read` | List resource groups and memberships. |
| `spark-admin:resource_group_memberships_write` | Update resource group memberships. |
| `spark-compliance:recordings_read` | List recordings as compliance officer. |
| `spark-admin:recordings_read` | List recordings as admin. |
| `spark-admin:recordings_write` | Delete, move to recycle bin, restore, purge recordings. |
| `spark-admin:classifications_read` | List space classifications. |

---

## 1. Service Apps & Authorizations

### Overview

Service apps are machine-to-machine integrations that act on behalf of an organization without a user context. An admin authorizes the service app in Control Hub, then the app exchanges its credentials for a short-lived access token scoped to the target org.

> **Creating a service app?** There is no API for registration — it must be done manually. See [authentication.md → Creating & Registering a Service App](authentication.md#creating--registering-a-service-app) for the full step-by-step guide covering developer portal registration, Control Hub authorization, and token generation.

Authorizations track which OAuth integrations and service apps have been granted access to a user or organization. The `authorizations` group lets admins audit and revoke these grants.

### CLI Commands

#### service-apps

| Command | Description | Key Options |
|---------|-------------|-------------|
| `service-apps create` | Create a service app access token | `APPLICATION_ID` (arg), `--client-id`, `--client-secret`, `--target-org-id` (all required) |

#### authorizations

| Command | Description | Key Options |
|---------|-------------|-------------|
| `authorizations list` | List authorizations for a user | `--person-id`, `--person-email` |
| `authorizations show` | Get expiration status for the current token | (no required options) |
| `authorizations delete` | Delete all authorizations for a client ID in the org | `--client-id` (required), `--force` |
| `authorizations delete-authorizations` | Delete a specific authorization by ID | `AUTHORIZATION_ID` (arg), `--force` |

### CLI Examples

```bash
# Create a service app access token
wxcli service-apps create APP_ID_HERE \
  --client-id "C1234567890abcdef" \
  --client-secret "secret_here" \
  --target-org-id "Y2lzY29zcGFyazovL3VzL09SR..."

# List authorizations for a specific user
wxcli authorizations list --person-email user@example.com

# Check token expiration status
wxcli authorizations show

# Revoke all authorizations for a client ID (destructive)
wxcli authorizations delete --client-id "C1234567890abcdef" --force

# Delete a specific authorization
wxcli authorizations delete-authorizations AUTH_ID_HERE --force
```

### Raw HTTP Fallback

#### Create Service App Token

```
POST https://webexapis.com/v1/applications/{applicationId}/token
```

```bash
curl -X POST "https://webexapis.com/v1/applications/{applicationId}/token" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "C1234567890abcdef",
    "clientSecret": "secret_here",
    "targetOrgId": "Y2lzY29zcGFyazovL3VzL09SR..."
  }'
```

#### List Authorizations

```
GET https://webexapis.com/v1/authorizations?personEmail=user@example.com
```

#### Delete Authorization by Client ID

```
DELETE https://webexapis.com/v1/authorizations?clientId=C1234567890abcdef
```

#### Get Token Expiration Status

```
GET https://webexapis.com/v1/authorizations/tokenStatus
```

---

## 2. User Lifecycle

### Overview

These groups manage user onboarding (activation emails), offboarding (archive lookup), and temporary guest accounts for Webex spaces.

The activation email job is an asynchronous bulk operation: you initiate it, then poll for status and errors. Archive users retrieves data for users who have been removed from the org. Guest management creates temporary identities for external participants.

### CLI Commands

#### activation-email

| Command | Description | Key Options |
|---------|-------------|-------------|
| `activation-email create` | Initiate a bulk activation email resend job | `ORG_ID` (arg) |
| `activation-email list` | Get bulk job status | `ORG_ID` (arg), `JOB_ID` (arg) |
| `activation-email list-errors` | Get bulk job errors | `ORG_ID` (arg), `JOB_ID` (arg), `--max` |

#### archive-users

| Command | Description | Key Options |
|---------|-------------|-------------|
| `archive-users show` | Get archived user data | `ORG_ID` (arg), `USERUUID` (arg) |

#### guest-management

| Command | Description | Key Options |
|---------|-------------|-------------|
| `guest-management create` | Create a guest user | `--subject` (required), `--display-name` (required) |
| `guest-management list` | Get guest count for the org | (no required options) |

### CLI Examples

```bash
# Initiate bulk activation email resend
wxcli activation-email create "Y2lzY29zcGFyazovL3VzL09SR..."

# Poll for job status (use the jobId from the create response)
wxcli activation-email list "Y2lzY29zcGFyazovL3VzL09SR..." "JOB_ID_HERE"

# Check for errors in the job
wxcli activation-email list-errors "Y2lzY29zcGFyazovL3VzL09SR..." "JOB_ID_HERE"

# Look up an archived user
wxcli archive-users show "Y2lzY29zcGFyazovL3VzL09SR..." "USER_UUID_HERE"

# Create a guest
wxcli guest-management create \
  --subject "ext-vendor-12345" \
  --display-name "Jane Vendor"

# Get guest count
wxcli guest-management list
```

### Async Job Pattern (activation-email)

The activation email workflow follows the standard Webex async job pattern:

1. **Initiate:** `activation-email create ORG_ID` returns a job ID.
2. **Poll:** `activation-email list ORG_ID JOB_ID` until status shows completion.
3. **Check errors:** `activation-email list-errors ORG_ID JOB_ID` to see which users failed.

This is the same pattern used by other bulk Webex operations (number management, user CSV import, etc.).

### Raw HTTP Fallback

#### Initiate Bulk Activation Email

```
POST https://webexapis.com/v1/orgs/{orgId}/sendActivationEmail
```

#### Get Job Status

```
GET https://webexapis.com/v1/orgs/{orgId}/sendActivationEmail/{jobId}
```

#### Get Job Errors

```
GET https://webexapis.com/v1/orgs/{orgId}/sendActivationEmail/{jobId}/errors
```

#### Get Archived User

```
GET https://webexapis.com/v1/orgs/{orgId}/archivedUsers/{useruuid}
```

#### Create Guest

```
POST https://webexapis.com/v1/guests
Content-Type: application/json

{
  "subject": "ext-vendor-12345",
  "displayName": "Jane Vendor"
}
```

#### Get Guest Count

```
GET https://webexapis.com/v1/guests/count
```

---

## 3. Recordings (Admin)

### Overview

The `admin-recordings` group provides org-wide recording management for administrators and compliance officers. This covers listing, viewing details, soft-deleting (moving to recycle bin), restoring, permanently purging, sharing, and working with group recordings.

**Important distinction:** Both `admin-recordings` (admin spec) and `recordings` (calling spec) operate on the Webex recordings API. Use `admin-recordings` for org-wide admin and compliance operations: admin-scoped listing across all users, recycle bin management (move/restore/purge), and compliance officer access. Use `recordings` for user-scoped recording access. See [reporting-analytics.md](reporting-analytics.md) for CDR and call recording report details.

### CLI Commands

#### Listing & Details

| Command | Description | Key Options |
|---------|-------------|-------------|
| `admin-recordings list` | List recordings (user scope) | `--from`, `--to`, `--meeting-id`, `--host-email`, `--site-url`, `--topic`, `--format` (MP4/ARF), `--service-type`, `--status` (available/deleted/purged) |
| `admin-recordings list-recordings-admin` | List recordings for an admin or compliance officer | `--from`, `--to`, `--meeting-id`, `--site-url`, `--topic`, `--format`, `--service-type`, `--status` |
| `admin-recordings show` | Get recording details | `RECORDING_ID` (arg), `--host-email` |
| `admin-recordings list-recordings-group` | List group recordings | `--person-id`, `--from`, `--to`, `--site-url`, `--topic`, `--format`, `--service-type` |
| `admin-recordings show-recordings` | Get group recording details | `RECORDING_ID` (arg), `--person-id` |

#### Lifecycle Management

| Command | Description | Key Options |
|---------|-------------|-------------|
| `admin-recordings create` | Move recordings into the recycle bin (soft-delete) | `--host-email`, `--site-url`, `--json-body` |
| `admin-recordings create-restore` | Restore recordings from recycle bin | `--host-email`, `--restore-all/--no-restore-all`, `--site-url`, `--json-body` |
| `admin-recordings create-purge` | Permanently purge recordings from recycle bin | `--host-email`, `--purge-all/--no-purge-all`, `--site-url`, `--json-body` |
| `admin-recordings delete` | Delete a recording by admin (hard delete) | `RECORDING_ID` (arg), `--force` |
| `admin-recordings delete-recordings` | Delete a recording (with host-email context) | `RECORDING_ID` (arg), `--host-email`, `--force` |

#### Sharing

| Command | Description | Key Options |
|---------|-------------|-------------|
| `admin-recordings create-access-list-recordings` | Share a recording by ID | `RECORDING_ID` (arg), `--host-email`, `--send-email/--no-send-email`, `--json-body` |
| `admin-recordings create-access-list-recordings-1` | Share a recording by link | `--host-email`, `--web-share-link`, `--send-email/--no-send-email`, `--json-body` |

### CLI Examples

```bash
# List all recordings for compliance (admin-scoped, last 30 days)
wxcli admin-recordings list-recordings-admin \
  --from "2026-02-17T00:00:00Z" \
  --to "2026-03-19T00:00:00Z" \
  --status available

# List recordings for a specific host
wxcli admin-recordings list --host-email user@example.com

# Get recording details
wxcli admin-recordings show RECORDING_ID_HERE

# Soft-delete recordings to recycle bin (requires JSON body with recording IDs)
wxcli admin-recordings create \
  --host-email user@example.com \
  --json-body '{"recordingIds": ["rec_id_1", "rec_id_2"]}'

# Restore all recordings from recycle bin for a host
wxcli admin-recordings create-restore \
  --host-email user@example.com \
  --restore-all

# Permanently purge all recycle bin recordings for a host
wxcli admin-recordings create-purge \
  --host-email user@example.com \
  --purge-all

# Hard-delete a specific recording (admin)
wxcli admin-recordings delete RECORDING_ID_HERE --force

# Share a recording with email notification
wxcli admin-recordings create-access-list-recordings RECORDING_ID_HERE \
  --host-email host@example.com \
  --send-email \
  --json-body '{"accessList": [{"email": "recipient@example.com", "displayName": "Recipient"}]}'

# List group recordings for a person
wxcli admin-recordings list-recordings-group --person-id PERSON_ID_HERE
```

### Recording Lifecycle States

Recordings move through three states:

| State | Description | Recoverable? |
|-------|-------------|--------------|
| `available` | Active, accessible recording | N/A |
| `deleted` | In the recycle bin (soft-deleted) | Yes, via `create-restore` |
| `purged` | Permanently deleted from recycle bin | No |

Use `--status` on list commands to filter by state.

### Raw HTTP Fallback

#### List Recordings (Admin/Compliance)

```
GET https://webexapis.com/v1/admin/recordings?from=2026-02-17T00:00:00Z&to=2026-03-19T00:00:00Z&status=available
```

#### Move to Recycle Bin

```
POST https://webexapis.com/v1/recordings/softDelete
Content-Type: application/json

{
  "hostEmail": "user@example.com",
  "recordingIds": ["rec_id_1", "rec_id_2"]
}
```

#### Restore from Recycle Bin

```
POST https://webexapis.com/v1/recordings/restore
Content-Type: application/json

{
  "hostEmail": "user@example.com",
  "restoreAll": true
}
```

#### Purge from Recycle Bin

```
POST https://webexapis.com/v1/recordings/purge
Content-Type: application/json

{
  "hostEmail": "user@example.com",
  "purgeAll": true
}
```

#### Delete Recording (Admin)

```
DELETE https://webexapis.com/v1/admin/recordings/{recordingId}
```

#### Share a Recording

```
POST https://webexapis.com/v1/recordings/{recordingId}/accessList
Content-Type: application/json

{
  "hostEmail": "host@example.com",
  "sendEmail": true,
  "accessList": [{"email": "recipient@example.com", "displayName": "Recipient"}]
}
```

#### Share by Link

```
POST https://webexapis.com/v1/recordings/shareLink
Content-Type: application/json

{
  "webShareLink": "https://site.webex.com/...",
  "sendEmail": true
}
```

---

## 4. Data & Compliance

### Overview

This section covers data exchange infrastructure (data sources), content classification (space classifications), hybrid services resource allocation (resource groups and memberships), and report template discovery.

Data sources define endpoints where Webex sends data via JWT-authenticated webhooks. Resource groups control how hybrid services (calendar, calling, messaging) are distributed across on-premises connector clusters. Classifications label Webex spaces for data loss prevention (DLP) policy enforcement.

### CLI Commands

#### data-sources

| Command | Description | Key Options |
|---------|-------------|-------------|
| `data-sources create` | Register a new data source | `--audience`, `--nonce`, `--schema-id`, `--subject`, `--token-lifetime-minutes`, `--url` |
| `data-sources list` | List all data sources | (no required options) |
| `data-sources list-schemas` | List available data source schemas | (no required options) |
| `data-sources show` | Get details of a specific schema | `SCHEMA_ID` (arg) |
| `data-sources show-data-sources` | Get details of a specific data source | `DATA_SOURCE_ID` (arg) |
| `data-sources update` | Update a data source | `DATA_SOURCE_ID` (arg), `--audience`, `--nonce`, `--schema-id`, `--subject`, `--token-lifetime-minutes`, `--url`, `--status`, `--error-message` |
| `data-sources delete` | Delete a data source | `DATA_SOURCE_ID` (arg), `--force` |

#### classifications

| Command | Description | Key Options |
|---------|-------------|-------------|
| `classifications list` | List space classifications for the org | (no required options) |

#### resource-groups

| Command | Description | Key Options |
|---------|-------------|-------------|
| `resource-groups list` | List resource groups | (no required options) |
| `resource-groups show` | Get resource group details | `RESOURCE_GROUP_ID` (arg) |

#### resource-group-memberships

| Command | Description | Key Options |
|---------|-------------|-------------|
| `resource-group-memberships list` | List memberships | `--license-id`, `--person-id`, `--person-org-id`, `--status` (pending/activated/error) |
| `resource-group-memberships list-v2` | List memberships (v2, with type filter) | `--license-id`, `--id`, `--status`, `--type` (User/Workspace) |
| `resource-group-memberships show` | Get membership details | `RESOURCE_GROUP_MEMBERSHIP_ID` (arg) |
| `resource-group-memberships update` | Update a membership | `RESOURCE_GROUP_MEMBERSHIP_ID` (arg), `--resource-group-id`, `--license-id`, `--person-id`, `--person-org-id`, `--status` |

#### report-templates

| Command | Description | Key Options |
|---------|-------------|-------------|
| `report-templates show` | List available report templates | (no required options) |

### CLI Examples

```bash
# List available data source schemas
wxcli data-sources list-schemas

# Register a new data source
wxcli data-sources create \
  --schema-id "SCHEMA_ID_HERE" \
  --url "https://myapp.example.com/webhook" \
  --audience "my-app" \
  --subject "data-feed" \
  --nonce "unique-nonce-value" \
  --token-lifetime-minutes "60"

# List all registered data sources
wxcli data-sources list

# Get data source details
wxcli data-sources show-data-sources DS_ID_HERE

# Update a data source (disable it)
wxcli data-sources update DS_ID_HERE --status "disabled" --error-message "Maintenance window"

# Delete a data source
wxcli data-sources delete DS_ID_HERE --force

# List space classifications
wxcli classifications list

# List resource groups
wxcli resource-groups list

# Get resource group details
wxcli resource-groups show RG_ID_HERE

# List resource group memberships filtered by status
wxcli resource-group-memberships list --status activated

# List v2 memberships filtered by type
wxcli resource-group-memberships list-v2 --type User --status activated

# Move a user to a different resource group
wxcli resource-group-memberships update MEMBERSHIP_ID_HERE \
  --resource-group-id "NEW_RG_ID" \
  --status activated

# List available report templates
wxcli report-templates show
```

### Data Source Registration Flow

1. **Discover schemas:** `data-sources list-schemas` to find the schema ID for the data type you want (e.g., CDR events, compliance events).
2. **Register:** `data-sources create` with the schema ID, your webhook URL, and JWT parameters.
3. **Verify:** `data-sources show-data-sources DS_ID` to confirm registration and check status.
4. **Maintain:** `data-sources update DS_ID --status disabled` to pause, or `data-sources delete DS_ID` to remove.

### Resource Group Assignment Flow

Resource groups are used in hybrid services deployments to control which on-premises cluster handles which users:

1. **List groups:** `resource-groups list` to see available clusters.
2. **Check memberships:** `resource-group-memberships list --license-id LICENSE_ID` to see current assignments.
3. **Reassign:** `resource-group-memberships update MEMBERSHIP_ID --resource-group-id NEW_GROUP_ID` to move a user to a different cluster.

### Raw HTTP Fallback

#### Data Sources

```
# List schemas
GET https://webexapis.com/v1/dataSources/schemas

# Get schema details
GET https://webexapis.com/v1/dataSources/schemas/{schemaId}

# List all data sources
GET https://webexapis.com/v1/dataSources

# Get data source details
GET https://webexapis.com/v1/dataSources/{dataSourceId}

# Register data source
POST https://webexapis.com/v1/dataSources
Content-Type: application/json

{
  "schemaId": "schema_id",
  "url": "https://myapp.example.com/webhook",
  "audience": "my-app",
  "subject": "data-feed",
  "nonce": "unique-nonce-value",
  "tokenLifetimeMinutes": 60
}

# Update data source
PUT https://webexapis.com/v1/dataSources/{dataSourceId}

# Delete data source
DELETE https://webexapis.com/v1/dataSources/{dataSourceId}
```

#### Classifications

```
GET https://webexapis.com/v1/classifications
```

#### Resource Groups

```
# List resource groups
GET https://webexapis.com/v1/resourceGroups

# Get resource group details
GET https://webexapis.com/v1/resourceGroups/{resourceGroupId}
```

#### Resource Group Memberships

```
# List memberships
GET https://webexapis.com/v1/resourceGroup/memberships?status=activated

# List memberships v2
GET https://webexapis.com/v1/resourceGroup/memberships/v2?type=User&status=activated

# Get membership details
GET https://webexapis.com/v1/resourceGroup/memberships/{resourceGroupMembershipId}

# Update membership
PUT https://webexapis.com/v1/resourceGroup/memberships/{resourceGroupMembershipId}
Content-Type: application/json

{
  "resourceGroupId": "new_group_id",
  "licenseId": "license_id",
  "personId": "person_id",
  "personOrgId": "org_id",
  "status": "activated"
}
```

#### Report Templates

```
GET https://webexapis.com/v1/report/templates
```

For calling-specific report creation and download, see [reporting-analytics.md](reporting-analytics.md).

---

## Gotchas

1. **`activation-email create` is an async job.** The response returns a job ID, not immediate confirmation. You must poll with `activation-email list` until the job completes, then check `activation-email list-errors` for failures. There is no webhook notification for job completion.

2. **`authorizations delete` is destructive and org-wide.** It revokes ALL authorizations for the given client ID across the entire organization. There is no undo. Always use `authorizations list` first to understand the blast radius before deleting.

3. **Service app tokens are short-lived.** The token returned by `service-apps create` expires quickly (typically minutes, not hours). Your automation must handle token refresh by calling `service-apps create` again before expiration. The admin must have pre-authorized the service app in Control Hub -- the CLI cannot perform that step.

4. **Client secret and refresh token are shown only once.** When registering a service app on developer.webex.com, the client secret is displayed only at creation time. Similarly, when generating tokens after admin authorization, the refresh token is shown only once. Copy both immediately and store securely. If lost, you must regenerate credentials (client secret) or re-authorize and generate new tokens (refresh token). <!-- Verified via developer.webex.com docs 2026-03-20 -->

5. **`admin-recordings create` is a soft-delete, not a true create.** Despite the command name (`create` maps to POST), this moves recordings into the recycle bin. It does not create a recording. The `--json-body` must include the `recordingIds` array. Similarly, `create-restore` and `create-purge` are POST operations that restore from or permanently delete the recycle bin.

6. **Two delete commands for recordings.** `admin-recordings delete` (admin hard-delete by recording ID) vs `admin-recordings delete-recordings` (delete with host-email context). The former is admin-only; the latter can specify a host email for user-context deletion.

7. **`report-templates show` actually lists templates.** The command is named `show` (maps to GET on a list endpoint) but returns all available report templates, not a single template. Use this to discover template IDs, then use `reports` commands from the calling spec to create and download reports.

8. **Data source `--token-lifetime-minutes` controls JWT expiry.** The token Webex creates for authenticating to your webhook URL expires after this many minutes. Set it long enough to avoid gaps in data delivery, but short enough for security. Must be refreshed before expiration by updating the data source.

9. **Resource group memberships v1 vs v2.** `list-v2` adds the `--type` filter (User/Workspace) and `--id` filter that v1 lacks. Prefer `list-v2` for new implementations.

10. **`admin-recordings list` vs `list-recordings-admin`.** Both list recordings, but `list` is user-scoped (uses `--host-email`) while `list-recordings-admin` is admin/compliance-scoped (searches across all users in the org without requiring a host email).

---

## See Also

- **[reporting-analytics.md](reporting-analytics.md)** -- CDR, report creation/download, call quality metrics, and queue/AA statistics. The `report-templates show` command here discovers template IDs; use `reports` commands from that doc to create and download reports.
- **[authentication.md](authentication.md)** -- OAuth flows, service app authorization, token scopes. Service apps require admin pre-authorization in Control Hub before `service-apps create` can issue tokens.
- **[webhooks-events.md](webhooks-events.md)** -- Webhook event subscriptions. Data sources are a different mechanism (JWT-authenticated push to your endpoint) but serve a similar purpose of delivering Webex data to external systems.
