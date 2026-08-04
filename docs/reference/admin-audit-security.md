# Admin: Audit & Security

Admin audit trail, security audit events, and compliance event review for Webex organizations.

## Sources

- [Admin Audit Events API](https://developer.webex.com/docs/api/v1/admin-audit-events)
- [Security Audit Events API](https://developer.webex.com/docs/api/v1/security-audit-events)
- [Events API](https://developer.webex.com/docs/api/v1/events)
- OpenAPI specs: `specs/webex-admin.json` (audit-events, security-audit, events)

---

## Table of Contents

- [Key Concepts](#key-concepts)
- [Required Scopes](#required-scopes)
- [1. Admin Audit Events (`audit-events`)](#1-admin-audit-events-audit-events)
- [2. Security Audit Events (`security-audit`)](#2-security-audit-events-security-audit)
- [3. Events (`events`)](#3-events-events)
- [Recipes](#recipes)
- [Gotchas](#gotchas)
- [See Also](#see-also)

---

## Key Concepts

Three different event APIs serve different purposes. Picking the right one matters.

### Admin Audit Events (`audit-events`)

Who changed what in Control Hub. Every admin action is logged: user created, setting changed, license assigned, location modified, policy updated. Use this when you need an audit trail of administrative changes to the organization.

- **API path:** `GET /v1/adminAudit/events`
- **Date parameters:** `--from` / `--to`
- **Supports event categories** via `--event-categories` (get the list from `list-event-categories`)

### Security Audit Events (`security-audit`)

Security-related events: login failures, suspicious activity, security policy changes, authentication anomalies. Use this when investigating security incidents or feeding events into an external SIEM.

- **API path:** `GET /v1/admin/securityAudit/events`
- **Date parameters:** `--start-time` / `--end-time`
- **Requires scope:** `audit:events_read`

### Events (`events`)

General Webex platform events: messages created/deleted, calls placed, meetings held, memberships changed. Use this for compliance, eDiscovery, or building integrations that react to platform activity.

- **API path:** `GET /v1/events` (list), `GET /v1/events/{eventId}` (detail)
- **Date parameters:** `--from` / `--to`
- **Filterable by resource type** (`--resource`) and event type (`--type`: created, updated, deleted, ended)
- **Filterable by service** (`--service-type calling` to scope to Webex Calling events only)

---

## Required Scopes

| Scope | Required For | Notes |
|-------|-------------|-------|
| `audit:events_read` | `security-audit list` | Specifically required for security audit events. Without it you get 401/403. |
| Standard admin token | `audit-events list`, `audit-events list-event-categories` | Full or read-only admin. No special scope beyond admin auth. |
| Standard admin token | `events list`, `events show` | Full or read-only admin. Compliance officer role also works. |

---

## 1. Admin Audit Events (`audit-events`)

### Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `audit-events list` | List admin audit events | `--from`, `--to`, `--actor-id`, `--event-categories`, `--limit`, `--offset` |
| `audit-events list-event-categories` | List available event categories | (none required) |

### CLI Examples

```bash
# List all available audit event categories
wxcli audit-events list-event-categories -o json

# List audit events from the last 24 hours
wxcli audit-events list --from "2026-03-18T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# List audit events by a specific admin
wxcli audit-events list --actor-id "Y2lzY29zcGFyaz..." --from "2026-03-01T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# Filter by event category (get category names from list-event-categories first)
wxcli audit-events list --event-categories "Users" --from "2026-03-01T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# Limit results
wxcli audit-events list --from "2026-03-18T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" --limit 50 -o json
```

### Raw HTTP

```
GET https://webexapis.com/v1/adminAudit/events?from=2026-03-18T00:00:00.000Z&to=2026-03-19T00:00:00.000Z
Authorization: Bearer <admin_token>
```

Response key: `items` (array of event objects).

```
GET https://webexapis.com/v1/adminAudit/eventCategories
Authorization: Bearer <admin_token>
```

Response key: `eventCategories` (array of category strings).

---

## 2. Security Audit Events (`security-audit`)

### Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `security-audit list` | List security audit events | `--start-time`, `--end-time`, `--actor-id`, `--event-categories`, `--limit` |

### CLI Examples

```bash
# List security events for the last 7 days
wxcli security-audit list --start-time "2026-03-12T00:00:00.000Z" --end-time "2026-03-19T00:00:00.000Z" -o json

# List security events by a specific actor
wxcli security-audit list --actor-id "Y2lzY29zcGFyaz..." --start-time "2026-03-01T00:00:00.000Z" --end-time "2026-03-19T00:00:00.000Z" -o json

# Filter by event category
wxcli security-audit list --event-categories "Logins" --start-time "2026-03-18T00:00:00.000Z" --end-time "2026-03-19T00:00:00.000Z" -o json

# Limit results for a quick check
wxcli security-audit list --start-time "2026-03-18T00:00:00.000Z" --end-time "2026-03-19T00:00:00.000Z" --limit 20 -o json
```

### Raw HTTP

```
GET https://webexapis.com/v1/admin/securityAudit/events?startTime=2026-03-12T00:00:00.000Z&endTime=2026-03-19T00:00:00.000Z
Authorization: Bearer <token_with_audit:events_read_scope>
```

Response key: `items` (array of event objects).

**Scope note:** This endpoint requires the `audit:events_read` scope. A standard admin token without this scope will return 401 or 403.

---

## 3. Events (`events`)

### Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `events list` | List platform events | `--resource`, `--type`, `--actor-id`, `--from`, `--to`, `--service-type`, `--limit` |
| `events show` | Get event details by ID | `EVENT_ID` (positional argument) |

### CLI Examples

```bash
# List all events from the last 24 hours
wxcli events list --from "2026-03-18T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# List only calling events
wxcli events list --service-type calling --from "2026-03-18T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# List only message-created events
wxcli events list --resource messages --type created --from "2026-03-18T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# List events for a specific user (actor)
wxcli events list --actor-id "Y2lzY29zcGFyaz..." --from "2026-03-01T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# List deleted events (compliance/eDiscovery)
wxcli events list --type deleted --from "2026-03-18T00:00:00.000Z" --to "2026-03-19T00:00:00.000Z" -o json

# Get full details for a specific event
wxcli events show "Y2lzY29zcGFyazovL3VzL0VWRU5ULzEyMzQ1"
```

### Raw HTTP

```
GET https://webexapis.com/v1/events?from=2026-03-18T00:00:00.000Z&to=2026-03-19T00:00:00.000Z&resource=messages&type=created
Authorization: Bearer <admin_token>
```

Response key: `items` (array of event objects).

```
GET https://webexapis.com/v1/events/{eventId}
Authorization: Bearer <admin_token>
```

Response: single event object (no wrapper key).

### Event Resource Types

The `--resource` option accepts any Webex resource type. Common values:

| Resource | Description |
|----------|-------------|
| `messages` | Messages sent/deleted in rooms |
| `memberships` | Room membership changes |
| `rooms` | Room creation/updates |
| `telephony_calls` | Webex Calling call events |
| `meetings` | Meeting events |
| `recordings` | Recording events |
| `meetingMessages` | In-meeting chat messages |

### Event Types

| Type | Description |
|------|-------------|
| `created` | Resource was created |
| `updated` | Resource was updated |
| `deleted` | Resource was deleted |
| `ended` | Resource ended (calls, meetings) |

---

## Recipes

### Pull audit trail for a specific admin over a date range

Find all Control Hub changes made by a particular administrator:

```bash
# Step 1: Get the admin's person ID (if you don't have it)
wxcli people list --email "admin@company.com" -o json

# Step 2: Pull their audit events for the date range
wxcli audit-events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

### Export security events for external SIEM ingestion

Pull security audit events in JSON format for import into Splunk, Sentinel, or other SIEM tools:

```bash
# Pull the last 7 days of security events as JSON
wxcli security-audit list \
  --start-time "2026-03-12T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json > security_events_export.json

# For ongoing ingestion, run daily with a 24-hour window
wxcli security-audit list \
  --start-time "2026-03-18T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json >> siem_feed.json
```

### Compliance event review for a specific user

Review all platform activity for a user under investigation:

```bash
# Step 1: Get the user's person ID
wxcli people list --email "user@company.com" -o json

# Step 2: Pull all events for that user
wxcli events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Step 3: Narrow to specific resource types if needed
wxcli events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --resource messages \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Step 4: Get full details on a specific event
wxcli events show "Y2lzY29zcGFyazovL3VzL0VWRU5ULzU2Nzg5"
```

### Filter audit events by category

Use `list-event-categories` to discover category names, then filter:

```bash
# Step 1: See all available categories
wxcli audit-events list-event-categories -o json

# Step 2: Filter audit events by a specific category
wxcli audit-events list \
  --event-categories "Users" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Step 3: Try other categories (Licenses, Settings, Locations, etc.)
wxcli audit-events list \
  --event-categories "Licenses" \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

---

## Gotchas

1. **Three different APIs serve different purposes.** `audit-events` = admin changes in Control Hub. `security-audit` = security/login events. `events` = general platform activity (messages, calls, meetings). Don't confuse them -- they have different endpoints, different parameters, and different scopes.

2. **Date range filtering is essential.** Without `--from`/`--to` (or `--start-time`/`--end-time` for security-audit), you get the full event stream, which can be enormous and slow. Always specify a date range.

3. **Date parameter names differ across APIs.** `audit-events` and `events` use `--from`/`--to`. `security-audit` uses `--start-time`/`--end-time`. Don't mix them up.

4. **`audit:events_read` scope is specifically required for `security-audit`, not for `audit-events`.** This is counterintuitive. The `audit-events` group works with a standard admin token. The `security-audit` group requires the `audit:events_read` scope on the token. If you get 401/403 on `security-audit list`, check your scopes.

5. **Event categories help narrow `audit-events` results.** Run `wxcli audit-events list-event-categories` first to see available category names (34 categories including `USERS`, `WEBEX_CALLING`, `DEVICES`, `LOGINS`, `LICENSE`, `LOCATIONS`, etc.), then pass them via `--event-categories`. The category names are **case-insensitive** — `USERS`, `users`, and `Users` all return the same results.

6. **`events list` resource types are not validated client-side.** If you pass a misspelled `--resource` value, you get an empty result set, not an error. Use the known resource types listed above.

7. **Pagination behavior — and where it stops.** There is no `--max` flag on these commands; the generator suppresses the spec's paging parameters in favour of `--limit`/`--offset`. Three things follow, and they differ per command:

   - **`events list` pages automatically.** With `--limit` omitted (the default) it follows the `Link: <url>; rel="next"` header until the result set is exhausted.
   - **`audit-events list` and `security-audit list` do not page at all.** Their spec operations declare no `Link` response header, so wxcli makes exactly one call and returns one page no matter what. Walk the result set yourself with `--offset`, or use `-o json` and follow `Link` over raw HTTP.
   - **A non-zero `--limit N` collapses to a single call on every list command.** For any N up to one page — the normal case — it returns exactly N, and an N larger than the total returns everything without error (verified live). The boundary is the page: it sends `max=N` and returns at most one response worth of records, so when N exceeds that endpoint's page size you get fewer than N with exit code 0 and no warning, and a very large N may instead be rejected by the API. That above-one-page case is derived from the rendered code, not observed — reproducing it needs an org holding more than a page of a single resource. Of the 182 GET operations that accept `max`, only 7 declare an upper bound at all (2000 on six, 1000 on one), so the cap is usually unknowable from the spec — treat a large `--limit` as unreliable and check the count you actually got. Omit `--limit` when you need a complete set.

8. **ISO 8601 datetime format required.** All date parameters expect ISO 8601 format: `2026-03-18T00:00:00.000Z`. Using other formats will return an error or unexpected results.

9. **`audit-events list` and `security-audit list` fail with a missing-`orgId` error on a single-org token.** Live-verified 2026-07-24:

   ```
   wxcli audit-events list --from 2026-07-20T00:00:00.000Z --to 2026-07-24T00:00:00.000Z -o json
   Error: {"message":"Required request parameter 'orgId' for method parameter type String is not present", ...}
   EXIT: 1
   ```

   These are 2 of only 12 operations in any spec that mark `orgId` **required** as a *query* parameter (the other 10 are Video Mesh). The generated command injects it with `get_org_id()`, which reads the saved config and returns nothing unless `wxcli configure` stored an org — and it only stores one for partner/multi-org tokens. So a normal single-org admin token sends no `orgId` and the API rejects the call.

   **Fixed.** `wxcli configure` now saves the org for single-org tokens too, so a
   freshly configured install works. A config created *before* that change still
   has no `org_id` — repair it once with `wxcli switch-org`, which now saves the
   single org instead of reporting "no org switching needed":

   ```
   wxcli switch-org
   Single-org token — target org set: My Company (Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8...)
   ```

   **In a script or an agent, pass the ID explicitly — `wxcli switch-org <orgId>`.**
   The bare form prompts interactively when the token spans several orgs, which
   blocks a non-interactive caller indefinitely. `wxcli clear-org` reverses it.

---

## See Also

- For Webex Calling CDR (call detail records), see [reporting-analytics.md](reporting-analytics.md).
- For webhook event subscriptions (receiving events in real-time), see [webhooks-events.md](webhooks-events.md).
- For people/user lookups (to get actor IDs), see `wxcli people list`.
