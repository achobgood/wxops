# Admin: Licensing

License inventory, assignment, usage auditing, and reclamation for Webex organizations.

## Sources

- OpenAPI spec: `specs/webex-admin.json` — Licenses tag (3 endpoints)
- OpenAPI spec: `specs/webex-cloud-calling.json` — Licenses tag (calling-focused subset)
- [Webex Licenses API Reference](https://developer.webex.com/docs/api/v1/licenses)

---

## Table of Contents

1. [License Types](#license-types)
2. [Required Scopes](#required-scopes)
3. [CLI Command Groups](#cli-command-groups)
4. [1. licenses-api (Admin Spec)](#1-licenses-api-admin-spec)
5. [2. licenses (Calling Spec)](#2-licenses-calling-spec)
6. [Raw HTTP Fallback](#raw-http-fallback)
7. [License Assignment Error Codes](#license-assignment-error-codes)
8. [Recipes](#recipes)
9. [Gotchas](#gotchas)
10. [See Also](#see-also)

---

## License Types

Webex organizations contain a mix of license types. Common ones relevant to calling deployments:

| License Name Pattern | Purpose |
|----------------------|---------|
| Webex Calling - Professional | Full calling features: extension, DID, voicemail, call forwarding, device support |
| Webex Calling - Standard | Basic calling with limited features (no voicemail, restricted forwarding) |
| Webex Calling - Common Area | For shared devices (lobby phones, break rooms) |
| Customer Assist (formerly CX Essentials) | Contact center agent capabilities on top of Calling Professional |
| Webex Attendant Console | Receptionist console (requires Calling Professional as prerequisite) |
| Webex Meetings | Meeting host licenses (various tiers) |
| Webex Messaging | Messaging/spaces licenses (free and paid tiers) |

License names vary by subscription and are not standardized strings. Always match by substring (e.g., `"calling"` in the name) rather than exact string comparison.

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| Admin token (full or read-only admin) | List and view license inventory |
| Admin token (full admin) | Assign/remove licenses via PATCH |

The Licenses API does not document explicit OAuth scopes. A standard admin token (from Control Hub admin login or service app with admin grant) provides access. Read-only admins can list and view but cannot assign.

---

## CLI Command Groups

Two CLI groups cover licensing. Use the one that fits your workflow:

| Group | Spec | Commands | Best For |
|-------|------|----------|----------|
| `licenses-api` | admin | 3 (list, show, update) | Full license management: inventory, assignment, removal |
| `licenses` | calling | 2 (list, show) | Quick calling-license audit with `--calling-only` filter |

**When to use which:**
- Use `licenses-api` when you need to assign or remove licenses, see assigned users, or work with non-calling licenses (Meetings, Messaging).
- Use `licenses` when you just need a quick view of calling license counts. It wraps the SDK and supports `--calling-only` for filtering.

---

## 1. licenses-api (Admin Spec)

Full license management: list all org licenses, view details with assigned users, and assign/remove licenses.

### Commands

| Command | Method | Endpoint | Description |
|---------|--------|----------|-------------|
| `licenses-api list` | GET | `/v1/licenses` | List all licenses in the org |
| `licenses-api show` | GET | `/v1/licenses/{licenseId}` | Get license details (optionally with assigned users) |
| `licenses-api update` | PATCH | `/v1/licenses/users` | Assign or remove licenses for a user |

### licenses-api list

List all licenses in the organization with total and consumed unit counts.

```bash
# List all licenses (table format)
wxcli licenses-api list

# JSON output for scripting
wxcli licenses-api list -o json

# With pagination
wxcli licenses-api list --limit 10 --offset 0
```

**Table columns:** ID, Name, Total Units, Consumed.

### licenses-api show

Get details for a specific license. Use `--include-assigned-to user` to see which users hold this license.

```bash
# Basic license details
wxcli licenses-api show "Y2lzY29zcGFyazov..."

# Include list of assigned users
wxcli licenses-api show "Y2lzY29zcGFyazov..." --include-assigned-to user

# Paginate assigned users (max 300 per page)
wxcli licenses-api show "Y2lzY29zcGFyazov..." --include-assigned-to user --limit 100
```

**Response fields:** id, name, totalUnits, consumedUnits, consumedByUsers, consumedByWorkspaces, subscriptionId, siteUrl, siteType, and (if requested) a `users` array with id, type, displayName, email.

### licenses-api update

Assign or remove licenses for a user. This is a PATCH to `/v1/licenses/users`. The body requires `--json-body` for the full `licenses` array structure.

**Identify the user** with `--email` or `--person-id` (at least one required).

```bash
# Add a non-calling license (Meetings, Messaging, etc.)
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {"id": "LICENSE_ID_HERE", "operation": "add"}
  ]
}'

# Add a Calling Professional license (requires location + phone/extension)
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {
      "id": "CALLING_PRO_LICENSE_ID",
      "operation": "add",
      "properties": {
        "locationId": "LOCATION_ID",
        "phoneNumber": "+14085267209",
        "extension": "133"
      }
    }
  ]
}'

# Remove a license
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {"id": "LICENSE_ID_HERE", "operation": "remove"}
  ]
}'

# Add and remove in one call
wxcli licenses-api update --email "user@example.com" --json-body '{
  "email": "user@example.com",
  "licenses": [
    {"id": "NEW_LICENSE_ID", "operation": "add"},
    {"id": "OLD_LICENSE_ID", "operation": "remove"}
  ]
}'
```

### PATCH Body Schema

```json
{
  "email": "string (required, or use personId)",
  "personId": "string (required, or use email)",
  "orgId": "string (optional, defaults to token org)",
  "licenses": [
    {
      "id": "string (required) — license ID from licenses-api list",
      "operation": "add | remove (default: add)",
      "properties": {
        "locationId": "string — required for Calling licenses if no phoneNumber",
        "phoneNumber": "string — required for Calling licenses if no extension",
        "extension": "string — Calling extension"
      }
    }
  ],
  "siteUrls": [
    {
      "siteUrl": "string — Webex Meetings site URL",
      "accountType": "attendee",
      "operation": "add | remove"
    }
  ]
}
```

**Calling license properties rules:**
- For Calling license assignment, either `phoneNumber` or `extension` is required in `properties`.
- If `phoneNumber` is not provided, `locationId` is mandatory.
- Non-calling licenses (Meetings, Messaging) do not need `properties`.

> **Gotcha — Calling licenses require `properties`.** Unlike Meetings or Messaging licenses, Calling license assignment must include `properties` with at least `phoneNumber` or `extension`. If you omit `phoneNumber`, you must provide `locationId`. Error code 400411 indicates missing properties.

> **Gotcha — `licenses-api update` confirms "Updated" even on no-op.** If the user already has the license, the CLI prints "Updated." without error. Always verify the actual state with `licenses-api show` after assignment.

> **Gotcha — Attendant Console has a prerequisite.** You must assign Calling Professional before assigning Attendant Console. Error code 400408 is returned if the prerequisite is missing.

---

## 2. licenses (Calling Spec)

SDK-wrapped license listing with a `--calling-only` convenience filter.

### Commands

| Command | Method | Description |
|---------|--------|-------------|
| `licenses list` | SDK `api.licenses.list()` | List licenses with optional calling filter |
| `licenses show` | SDK `api.licenses.details()` | Show a single license |

```bash
# All licenses
wxcli licenses list

# Only calling-related licenses
wxcli licenses list --calling-only

# JSON output
wxcli licenses list --calling-only -o json

# Show one license
wxcli licenses show "Y2lzY29zcGFyazov..."
```

**Table columns:** ID, Name, Total, Consumed.

> **Gotcha — The `--calling-only` filter uses substring matching.** It filters for `"calling"` in the license name (case-insensitive). This may miss licenses with non-standard naming, or include unexpected matches.

---

## Raw HTTP Fallback

### List Licenses

```
GET https://webexapis.com/v1/licenses
Authorization: Bearer {admin_token}
```

Optional query parameter: `orgId` (list licenses for a specific org).

### Get License Details

```
GET https://webexapis.com/v1/licenses/{licenseId}?includeAssignedTo=user&limit=300
Authorization: Bearer {admin_token}
```

### Assign Licenses

```
PATCH https://webexapis.com/v1/licenses/users
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "email": "user@example.com",
  "licenses": [
    {
      "id": "LICENSE_ID",
      "operation": "add",
      "properties": {
        "locationId": "LOCATION_ID",
        "phoneNumber": "+14085267209",
        "extension": "133"
      }
    }
  ]
}
```

**Response codes:**
- `200` — All licenses assigned successfully.
- `206` — Partial success. Compare returned `licenses` array against requested to find failures.
- `400` — Assignment failed. Check error codes (see Error Codes section below).

---

## License Assignment Error Codes

The PATCH endpoint returns specific error codes for assignment failures:

| Error Code | Meaning |
|------------|---------|
| 400000 | License ID not recognized |
| 400112 | Cannot downgrade Calling Professional to Standard |
| 400404 | Cannot have both Calling Professional and Standard simultaneously |
| 400406 | Cannot have both Calling Standard and Attendant Console |
| 400407 | Cannot have both Calling Standard and Customer Assist |
| 400408 | Attendant Console requires Calling Professional as prerequisite |
| 400410 | Cannot downgrade Customer Assist to Calling Standard |
| 400411 | Calling license missing required `properties` (locationId/phoneNumber/extension) |
| 400413 | Exclusive license conflict (only one from a set can be assigned) |
| 700003 | Free messaging license required before paid messaging |
| 700004 | Free meeting license required before paid meeting |
| 700005 | Free messaging license required for meeting license |
| 700006 | Screen Share license is implicitly assigned and cannot be removed |

---

## Recipes

### Audit License Usage

List all licenses and check consumed vs. total to identify overallocation or available capacity.

```bash
# Quick table view
wxcli licenses-api list

# Script-friendly: extract calling licenses with availability
wxcli licenses-api list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
for lic in data:
    avail = lic.get('totalUnits', 0) - lic.get('consumedUnits', 0)
    print(f\"{lic['name']}: {lic.get('consumedUnits', 0)}/{lic.get('totalUnits', 0)} (available: {avail})\")
"
```

### Find Users Assigned to a Specific License

```bash
# Get the license ID first
wxcli licenses-api list -o json

# Then show assigned users for that license
wxcli licenses-api show "LICENSE_ID" --include-assigned-to user -o json
```

### Bulk License Assignment Workflow

1. List available licenses to get the correct license ID:
   ```bash
   wxcli licenses-api list -o json
   ```

2. Get user person IDs from the people API:
   ```bash
   wxcli people list --email "user@example.com" -o json
   ```

3. Assign the license:
   ```bash
   wxcli licenses-api update --json-body '{
     "email": "user@example.com",
     "licenses": [
       {
         "id": "CALLING_PRO_LICENSE_ID",
         "operation": "add",
         "properties": {
           "locationId": "LOCATION_ID",
           "extension": "200"
         }
       }
     ]
   }'
   ```

4. Verify assignment:
   ```bash
   wxcli licenses-api show "CALLING_PRO_LICENSE_ID" --include-assigned-to user -o json
   ```

### Reclaim Unused Licenses

Find users who hold a license but may no longer need it (e.g., inactive users), then remove the license.

```bash
# Step 1: List users assigned to a calling license
wxcli licenses-api show "CALLING_LICENSE_ID" --include-assigned-to user -o json

# Step 2: Cross-reference with people list to check status
wxcli people list -o json

# Step 3: Remove license from specific user
wxcli licenses-api update --json-body '{
  "email": "departing.user@example.com",
  "licenses": [
    {"id": "CALLING_LICENSE_ID", "operation": "remove"}
  ]
}'
```

---

## Gotchas

1. **License IDs are org-specific base64-encoded strings.** They differ between organizations and subscriptions. Never hardcode license IDs -- always look them up with `licenses-api list` first.

2. **Removing a Calling license is destructive.** When you remove a Webex Calling Professional license from a user, ALL their calling configuration is deleted: extension, phone number, call forwarding rules, voicemail settings, monitoring lists, and device associations. There is no undo. Always document the user's settings before removing a calling license.

3. **206 Partial Content is not an error.** The PATCH endpoint can return HTTP 206 when some licenses in the request succeeded but others failed. Always compare the returned `licenses` array against what you requested to identify which ones failed.

4. **License conflicts are strictly enforced.** A user cannot hold both Calling Professional and Calling Standard, or Calling Standard and Customer Assist. The API returns specific 400-level error codes for each conflict type (see Error Codes table above).

---

## See Also

- [provisioning.md](provisioning.md) — User creation and calling license assignment during initial provisioning
- [person-call-settings-behavior.md](person-call-settings-behavior.md) — Calling behavior settings that depend on having a calling license
- [reporting-analytics.md](reporting-analytics.md) — License usage trends via report templates
- [virtual-lines.md](virtual-lines.md) — Virtual line licensing

For calling license assignment during user provisioning, see [provisioning.md](provisioning.md) and the `provision-calling` skill.
