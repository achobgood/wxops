# Admin: Partner Operations

Partner/VAR/MSP multi-tenant management -- customer org management, admin assignment, tagging, and partner-level reporting.

**Audience note:** This doc serves partner/VAR/MSP organizations. Most single-org admins will never use these commands. All commands require a partner-level admin token.

## Sources

- OpenAPI spec: `specs/webex-admin.json` (tags: Partner Administrators, Partner Tags, Partner Reports Templates)

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark-admin:reports_read` | List and retrieve partner reports and templates. |
| `spark-admin:reports_write` | Create and delete partner reports. |
| `spark-admin:organizations_read` | Read operations for `partner-admins` and `partner-tags` commands. |
| `spark-admin:organizations_write` | Write operations for `partner-admins` and `partner-tags` commands. |
| Partner admin token | Required for `partner-admins` and `partner-tags` commands. These APIs are only accessible to partner-level administrators (VAR/MSP). |

**Token requirement:** A standard org admin token will not work. You must authenticate as a partner administrator with access to the partner organization. Service app tokens scoped to a single customer org will also fail.

**wxcli multi-org support:** wxcli natively handles partner token org targeting. Run `wxcli configure` to auto-detect your multi-org token and select a target customer org. Use `wxcli switch-org` to change the active org and `wxcli clear-org` to reset. Once configured, `orgId` is injected automatically on all applicable commands — no extra flags required. See `docs/reference/authentication.md` (Partner/Multi-Org Tokens section) for full details.

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
| `list-partner-admins` | Get all partner admins assigned to a customer | (none -- customer org comes from config) |
| `create` | Assign partner admin to a customer | `PERSON_ID` (required); customer org comes from config |
| `delete` | Unassign partner admin from a customer | `PERSON_ID` (required), `--force`; customer org comes from config |
| `delete-partner-admin` | Revoke all partner admin roles for a person | `PERSON_ID` (required), `--force` |

> **There is no customer-org argument on these commands.** The `{orgId}` in the endpoint paths
> above is filled from `resolve_org_id()` -- the org saved by `wxcli switch-org`, falling back to
> the token's own org from `GET /v1/people/me`. Passing an org ID as the first positional makes
> `list-partner-admins` fail with "unexpected extra argument", and makes `create`/`delete` treat
> your org ID as the **person** ID.
>
> **This matters most for partners.** These commands act on whichever tenant `switch-org` last
> saved, not on the one you name in the command. Before running any of them, confirm the target
> with `wxcli whoami` (it prints a `Target:` line) and set it explicitly with
> `wxcli switch-org <customerOrgId>`. In automation always pass the ID -- bare `switch-org`
> prompts interactively and will hang.

### CLI Examples

```bash
# Point at the customer org first -- every command below acts on this org
wxcli switch-org Y2lzY29zcGFyazovL3VzL09SR...

# List all customer orgs managed by the authenticated partner
wxcli partner-admins list

# List customer orgs managed by a specific partner admin
wxcli partner-admins list --managed-by Y2lzY29zcGFyazovL3...

# List all partner admins assigned to a customer org
wxcli partner-admins list-partner-admins

# Assign a partner admin to a customer org
wxcli partner-admins create Y2lzY29zcGFyazovL3VzL1BF...

# Unassign a partner admin from a customer (skip confirmation)
wxcli partner-admins delete Y2lzY29zcGFyazovL3VzL1BF... --force

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

**Operational limits:** Maximum tag length is **25 characters**. Maximum tags per organization is **5**.

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
| `list` | Retrieve all customer tags | `--type TYPE` (required), `--limit N`, `--offset N` |
| `create` | Create or replace the target org's tags | `--json-body` |
| `show` | Get the target org's tags | (none) |
| `list-organizations` | Fetch all customers matching a set of tags | `--tags TAG1,TAG2` (required), `--limit N`, `--offset N` |
| `create-assign-tags` | Create or replace subscription tags | `SUBSCRIPTION_ID` (arg), `--json-body` |
| `list-subscriptions` | List subscriptions matching a set of tags | `--tags TAG1,TAG2` (required), `--limit N`, `--offset N` |
| `show-subscriptions` | Fetch a specific subscription | `SUBSCRIPTION_ID` (arg) |

**These commands take no `ORG_ID` argument.** `create`, `show`, `create-assign-tags`, and `show-subscriptions` resolve the target org from your saved config -- set it with `wxcli switch-org` before running them, and confirm it with `wxcli whoami`. If no org is saved, they fall back to the token's own org.

### CLI Examples

```bash
# List all tags of a given type
wxcli partner-tags list --type organization

# Point at the customer org you want to work on, then read its tags
wxcli switch-org
wxcli partner-tags show

# Assign tags to that customer org (replaces existing tags)
wxcli partner-tags create \
  --json-body '{"tags": [{"name": "region:west", "description": "West region"}, {"name": "tier:gold", "description": "Gold tier"}]}'

# Find all customer orgs with specific tags
wxcli partner-tags list-organizations --tags "region:west,tier:gold" --limit 50

# Assign tags to a subscription
wxcli partner-tags create-assign-tags SUB_ID_HERE \
  --json-body '{"tags": [{"name": "billing:annual", "description": "Annual billing"}]}'

# Find subscriptions by tags
wxcli partner-tags list-subscriptions --tags "billing:annual"

# Get details of a specific subscription
wxcli partner-tags show-subscriptions SUB_ID_HERE
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

# 2. Point at the customer org -- steps 3 and 4 have no org argument
wxcli switch-org CUSTOMER_ORG_ID
wxcli whoami          # confirm the "Target:" line names the customer org

# 3. Assign them to the customer org
wxcli partner-admins create PARTNER_ADMIN_PERSON_ID

# 4. Verify the assignment
wxcli partner-admins list-partner-admins
```

### Tag customers by region and tier

```bash
# Tag customer orgs for portfolio management. `create` always writes to the org
# saved in config, so switch targets between customers.
wxcli switch-org ORG_ID_WEST_1
wxcli partner-tags create \
  --json-body '{"tags": [{"name": "region:west", "description": "West region"}, {"name": "tier:gold", "description": "Gold tier"}, {"name": "vertical:finance", "description": "Finance"}]}'

wxcli switch-org ORG_ID_EAST_1
wxcli partner-tags create \
  --json-body '{"tags": [{"name": "region:east", "description": "East region"}, {"name": "tier:silver", "description": "Silver tier"}, {"name": "vertical:retail", "description": "Retail"}]}'

# Find all gold-tier customers
wxcli partner-tags list-organizations --tags "tier:gold"

# Find all west-region finance customers
wxcli partner-tags list-organizations --tags "region:west,vertical:finance"
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

2. **Two different commands share the `/v1/partner/tags/organizations` path.** The OpenAPI spec puts two endpoints on it -- one gets a specific org's tags (by path parameter), the other queries orgs by tags (by query parameter). These are now `show` and `list-organizations` respectively. An older generator emitted them as `show-organizations-tags` and `show-organizations-tags-1`; scripts using those names will fail, so update them.

3. **`show-subscriptions` fetches one subscription; `list-subscriptions` queries by tag.** The names are close but the operations differ: `show-subscriptions SUBSCRIPTION_ID` returns a single subscription's details, while `list-subscriptions --tags` returns every subscription matching a tag set. An older generator named the former `show-subscriptions-organizations` (after the `/organizations/{orgId}/subscriptions/{subscriptionId}` path); that name no longer exists.

4. **Tag create commands replace, not append.** Both `partner-tags create` and `partner-tags create-assign-tags` replace all existing tags with the provided list. To add a tag, you must first read the current tags, add the new one to the list, and write the full set back. Passing an empty array (`[]`) removes all tags from the org. Once a tag is unassigned from its last customer org, it is automatically removed from the API listing.

5. **`partner-reports` vs `reports`.** The `partner-reports` group (at `/v1/partner/reports`) is for partner-level cross-org reporting. The separate `reports` group (at `/v1/reports`) is for single-org reports. They use different API endpoints, different templates, and different scopes. Do not confuse them.

6. **Report generation is asynchronous.** After `partner-reports create`, the report is queued for generation. Poll with `partner-reports show REPORT_ID` until the status indicates completion. The completed response includes a download URL for the CSV/report file.

7. **Response key extraction.** The `partner-reports list` command looks for results under the `Report Attributes` key, and `list-templates` looks under `Template Collection`. If the API changes these keys, the table output will appear empty. Use `-o json` to see the raw response.

8. **`--type` parameter on `partner-tags list`.** This parameter is required but the valid values are not enumerated in the OpenAPI spec. The spec provides `ORGANIZATION` (uppercase) as the example value. The endpoint requires partner admin privileges — a standard org admin token gets 403 Forbidden for all values tested (`ORGANIZATION`, `SUBSCRIPTION`, `organization`). Both `ORGANIZATION` and `SUBSCRIPTION` are confirmed valid type values per the live API reference. <!-- Partially verified via live API 2026-03-19: all values return 403 with org admin token (partner admin required). No 400 "invalid type" error observed for ORGANIZATION or SUBSCRIPTION. -->

---

## See Also

- [reporting-analytics.md](reporting-analytics.md) -- For org-level report templates, CDR, call quality, and queue/AA statistics (single-org scope).
- [authentication.md](authentication.md) -- Auth methods, token types, and scopes.
