# Admin: Partner Operations

Partner/VAR/MSP multi-tenant management -- customer org management, admin assignment, tagging, and partner-level reporting.

**Audience note:** This doc serves partner/VAR/MSP organizations. Most single-org admins will never use these commands. All commands require a partner-level admin token.

## Sources

- OpenAPI spec: `webex-admin.json` (tags: Partner Administrators, Partner Tags, Partner Reports Templates)
- CLI source: `src/wxcli/commands/partner_admins.py`, `partner_tags.py`, `partner_reports.py`

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark-admin:reports_read` | List and retrieve partner reports and templates. |
| `spark-admin:reports_write` | Create and delete partner reports. |
| Partner admin token | Required for `partner-admins` and `partner-tags` commands. These APIs are only accessible to partner-level administrators (VAR/MSP). |

**Token requirement:** A standard org admin token will not work. You must authenticate as a partner administrator with access to the partner organization. Service app tokens scoped to a single customer org will also fail.

---

## 1. Partner Admins (`partner-admins`)

Manage assignment of partner administrators to customer organizations.

### API Endpoints

| Operation | Method | URL |
|-----------|--------|-----|
| List customer orgs | GET | `/v1/partner/organizations` |
| List partner admins for customer | GET | `/v1/partner/organizations/{orgId}/partnerAdmins` |
| Assign partner admin | POST | `/v1/partner/organizations/{orgId}/partnerAdmin/{personId}/assign` |
| Unassign partner admin | DELETE | `/v1/partner/organizations/{orgId}/partnerAdmin/{personId}/unassign` |
| Revoke all partner admin roles | DELETE | `/v1/partner/organizations/partnerAdmin/{personId}` |

### Command Reference

| Command | Description | Key Arguments |
|---------|-------------|---------------|
| `list` | Get all customers managed by a partner admin | `--managed-by PERSON_ID` |
| `list-partner-admins` | Get all partner admins assigned to a customer | `ORG_ID` (required) |
| `create` | Assign partner admin to a customer | `ORG_ID PERSON_ID` (both required) |
| `delete` | Unassign partner admin from a customer | `ORG_ID PERSON_ID` (both required), `--force` |
| `delete-partner-admin` | Revoke all partner admin roles for a person | `PERSON_ID` (required), `--force` |

### CLI Examples

```bash
# List all customer orgs managed by the authenticated partner
wxcli partner-admins list

# List customer orgs managed by a specific partner admin
wxcli partner-admins list --managed-by Y2lzY29zcGFyazovL3...

# List all partner admins assigned to a customer org
wxcli partner-admins list-partner-admins Y2lzY29zcGFyazovL3VzL09SR...

# Assign a partner admin to a customer org
wxcli partner-admins create Y2lzY29zcGFyazovL3VzL09SR... Y2lzY29zcGFyazovL3VzL1BF...

# Unassign a partner admin from a customer (skip confirmation)
wxcli partner-admins delete Y2lzY29zcGFyazovL3VzL09SR... Y2lzY29zcGFyazovL3VzL1BF... --force

# Revoke ALL partner admin roles for a person across all customer orgs
wxcli partner-admins delete-partner-admin Y2lzY29zcGFyazovL3VzL1BF... --force
```

### Raw HTTP Fallback

```bash
# List customer orgs (optionally filter by managedBy person ID)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/organizations?managedBy=PERSON_ID"

# Assign partner admin to customer
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://webexapis.com/v1/partner/organizations/{orgId}/partnerAdmin/{personId}/assign"

# Unassign partner admin from customer
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/organizations/{orgId}/partnerAdmin/{personId}/unassign"

# Revoke all partner admin roles for a person
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/organizations/partnerAdmin/{personId}"
```

---

## 2. Partner Tags (`partner-tags`)

Tag customer organizations and subscriptions for categorization (region, tier, vertical, etc.). Tags are free-form strings managed at the partner level.

### API Endpoints

| Operation | Method | URL |
|-----------|--------|-----|
| List all customer tags | GET | `/v1/partner/tags` |
| Assign/replace org tags | POST | `/v1/partner/tags/organizations/{orgId}/assignTags` |
| Get org tags | GET | `/v1/partner/tags/organizations/{orgId}` |
| Find orgs by tags | GET | `/v1/partner/tags/organizations` |
| Assign/replace subscription tags | POST | `/v1/partner/tags/organizations/{orgId}/subscriptions/{subscriptionId}/assignTags` |
| Find subscriptions by tags | GET | `/v1/partner/tags/subscriptions` |
| Get a subscription | GET | `/v1/partner/tags/organizations/{orgId}/subscriptions/{subscriptionId}` |

### Command Reference

| Command | Description | Key Arguments |
|---------|-------------|---------------|
| `show` | Retrieve all customer tags | `--type TYPE` (required) |
| `create` | Create or replace org tags | `ORG_ID` (required), `--json-body` |
| `show-organizations-tags` | Get a customer org's tags | `ORG_ID` (required) |
| `show-organizations-tags-1` | Fetch all customers matching a set of tags | `--tags TAG1,TAG2` (required), `--max N` |
| `create-assign-tags` | Create or replace subscription tags | `ORG_ID SUBSCRIPTION_ID` (required), `--json-body` |
| `show-subscriptions-tags` | List subscriptions matching a set of tags | `--tags TAG1,TAG2` (required), `--max N` |
| `show-subscriptions-organizations` | Fetch a specific subscription | `ORG_ID SUBSCRIPTION_ID` (required) |

### CLI Examples

```bash
# List all tags of a given type
wxcli partner-tags show --type organization

# Get tags assigned to a specific customer org
wxcli partner-tags show-organizations-tags Y2lzY29zcGFyazovL3VzL09SR...

# Assign tags to a customer org (replaces existing tags)
wxcli partner-tags create Y2lzY29zcGFyazovL3VzL09SR... \
  --json-body '{"tags": ["region:west", "tier:gold", "vertical:healthcare"]}'

# Find all customer orgs with specific tags
wxcli partner-tags show-organizations-tags-1 --tags "region:west,tier:gold" --max 50

# Assign tags to a subscription
wxcli partner-tags create-assign-tags Y2lzY29zcGFyazovL3VzL09SR... SUB_ID_HERE \
  --json-body '{"tags": ["billing:annual", "support:premium"]}'

# Find subscriptions by tags
wxcli partner-tags show-subscriptions-tags --tags "billing:annual"

# Get details of a specific subscription
wxcli partner-tags show-subscriptions-organizations Y2lzY29zcGFyazovL3VzL09SR... SUB_ID_HERE
```

### Raw HTTP Fallback

```bash
# List all customer tags of a type
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/tags?type=organization"

# Assign tags to a customer org
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["region:west", "tier:gold"]}' \
  "https://webexapis.com/v1/partner/tags/organizations/{orgId}/assignTags"

# Find orgs by tags (comma-separated)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/tags/organizations?tags=region:west,tier:gold&max=50"

# Assign tags to a subscription
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["billing:annual"]}' \
  "https://webexapis.com/v1/partner/tags/organizations/{orgId}/subscriptions/{subscriptionId}/assignTags"
```

---

## 3. Partner Reports (`partner-reports`)

Generate and manage reports across all customer organizations from the partner level. Uses a template-based system: list available templates, create a report from a template with a date range, then retrieve results.

### API Endpoints

| Operation | Method | URL |
|-----------|--------|-----|
| List reports | GET | `/v1/partner/reports` |
| Create a report | POST | `/v1/partner/reports` |
| Get report details | GET | `/v1/partner/reports/{reportId}` |
| Delete a report | DELETE | `/v1/partner/reports/{reportId}` |
| List report templates | GET | `/v1/partner/reports/templates` |

### Command Reference

| Command | Description | Key Arguments |
|---------|-------------|---------------|
| `list` | List reports | `--service`, `--template-id`, `--from DATE`, `--to DATE`, `--region-id`, `--on-behalf-of-sub-partner-org-id` |
| `create` | Create a report | `--template-id` (required), `--start-date` (required), `--end-date` (required), `--region-id` |
| `show` | Get report details | `REPORT_ID` (required) |
| `delete` | Delete a report | `REPORT_ID` (required), `--force` |
| `list-templates` | List available report templates | `--on-behalf-of-sub-partner-org-id` |

### CLI Examples

```bash
# List available partner report templates
wxcli partner-reports list-templates

# List templates on behalf of a sub-partner
wxcli partner-reports list-templates --on-behalf-of-sub-partner-org-id Y2lzY29zcGFyazovL3Vz...

# Create a report from a template
wxcli partner-reports create \
  --template-id TEMPLATE_ID \
  --start-date 2026-01-01 \
  --end-date 2026-01-31

# Create a report scoped to a region
wxcli partner-reports create \
  --template-id TEMPLATE_ID \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  --region-id us-east

# List all reports
wxcli partner-reports list

# List reports filtered by service and date range
wxcli partner-reports list --service calling --from 2026-01-01 --to 2026-02-01

# Get report details (includes download URL when complete)
wxcli partner-reports show REPORT_ID

# Delete a report
wxcli partner-reports delete REPORT_ID --force
```

### Raw HTTP Fallback

```bash
# List report templates
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/reports/templates"

# Create a report
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"templateId": "TEMPLATE_ID", "startDate": "2026-01-01", "endDate": "2026-01-31"}' \
  "https://webexapis.com/v1/partner/reports"

# Get report details
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/reports/{reportId}"

# List reports with filters
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/reports?service=calling&from=2026-01-01&to=2026-02-01"

# Delete a report
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/partner/reports/{reportId}"
```

### Response Keys

The `list` command extracts items from the `Report Attributes` key in the API response. The `list-templates` command extracts from the `Template Collection` key. Use `-o json` to see the full raw response if the table output is empty.

---

## Recipes

### List all customer orgs managed by this partner

```bash
# Get all customer orgs (paginated, default table output)
wxcli partner-admins list -o json

# Get orgs managed by a specific partner admin
wxcli partner-admins list --managed-by PARTNER_ADMIN_PERSON_ID -o json
```

### Assign a partner admin to a new customer org

```bash
# 1. Get the partner admin's person ID (from partner org's people list)
wxcli people list --display-name "Jane Partner" -o json

# 2. Assign them to the customer org
wxcli partner-admins create CUSTOMER_ORG_ID PARTNER_ADMIN_PERSON_ID

# 3. Verify the assignment
wxcli partner-admins list-partner-admins CUSTOMER_ORG_ID
```

### Tag customers by region and tier

```bash
# Tag customer orgs for portfolio management
wxcli partner-tags create ORG_ID_WEST_1 \
  --json-body '{"tags": ["region:west", "tier:gold", "vertical:finance"]}'

wxcli partner-tags create ORG_ID_EAST_1 \
  --json-body '{"tags": ["region:east", "tier:silver", "vertical:retail"]}'

# Find all gold-tier customers
wxcli partner-tags show-organizations-tags-1 --tags "tier:gold"

# Find all west-region finance customers
wxcli partner-tags show-organizations-tags-1 --tags "region:west,vertical:finance"
```

### Generate a partner-level report

```bash
# 1. List available templates to find the right one
wxcli partner-reports list-templates -o json

# 2. Create a monthly report
wxcli partner-reports create \
  --template-id TEMPLATE_ID \
  --start-date 2026-02-01 \
  --end-date 2026-03-01

# 3. Check report status (reports are generated asynchronously)
wxcli partner-reports show REPORT_ID

# 4. When status shows complete, the response includes a download URL
```

---

## Gotchas

1. **Partner-level token required.** All three command groups (`partner-admins`, `partner-tags`, `partner-reports`) require authentication as a partner administrator. A standard org admin token or a service app token scoped to a single org will return 403 or 401 errors.

2. **`show-organizations-tags-1` is a generator artifact.** The `-1` suffix exists because the OpenAPI spec has two endpoints on `/v1/partner/tags/organizations` -- one for getting a specific org's tags (by path parameter) and one for querying orgs by tags (by query parameter). The generator disambiguated them with the `-1` suffix. The command works correctly despite the awkward name.

3. **`show-subscriptions-organizations` name is misleading.** Despite the name, this command fetches a single subscription's details (given an org ID and subscription ID), not a list of organizations. The name comes from the URL path structure `/organizations/{orgId}/subscriptions/{subscriptionId}`.

4. **Tag create commands replace, not append.** Both `partner-tags create` and `partner-tags create-assign-tags` replace all existing tags with the provided list. To add a tag, you must first read the current tags, add the new one to the list, and write the full set back.

5. **`partner-reports` vs `reports`.** The `partner-reports` group (at `/v1/partner/reports`) is for partner-level cross-org reporting. The separate `reports` group (at `/v1/reports`) is for single-org reports. They use different API endpoints, different templates, and different scopes. Do not confuse them.

6. **Report generation is asynchronous.** After `partner-reports create`, the report is queued for generation. Poll with `partner-reports show REPORT_ID` until the status indicates completion. The completed response includes a download URL for the CSV/report file.

7. **Response key extraction.** The `partner-reports list` command looks for results under the `Report Attributes` key, and `list-templates` looks under `Template Collection`. If the API changes these keys, the table output will appear empty. Use `-o json` to see the raw response. <!-- Verified via OpenAPI spec (ReportCollectionResponse, TemplateCollectionResponse schemas) and CLI source (partner_reports.py lines 53, 174) 2026-03-19 -->

8. **`--type` parameter on `partner-tags show`.** This parameter is required but the valid values are not enumerated in the OpenAPI spec. The spec provides `ORGANIZATION` (uppercase) as the example value. The endpoint requires partner admin privileges — a standard org admin token gets 403 Forbidden for all values tested (`ORGANIZATION`, `SUBSCRIPTION`, `organization`). Both `ORGANIZATION` and `SUBSCRIPTION` return the same 403 (not a 400 "invalid value"), suggesting both may be valid types, but this cannot be confirmed without a partner admin token. <!-- Partially verified via live API 2026-03-19: all values return 403 with org admin token (partner admin required). No 400 "invalid type" error observed for ORGANIZATION or SUBSCRIPTION. -->

---

## See Also

- [reporting-analytics.md](reporting-analytics.md) -- For org-level report templates, CDR, call quality, and queue/AA statistics (single-org scope).
- [authentication.md](authentication.md) -- Auth methods, token types, and scopes.
