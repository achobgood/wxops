---
name: audit-compliance
description: |
  Pull and analyze Webex audit logs, security events, and compliance data.
  Covers admin audit trail, security audit events, authorization review,
  and service app credential management. Guides from query design through export.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [audit-type -- e.g. "admin audit", "security events", "compliance review", "authorization check"]
---

# Audit & Compliance Workflow

## Step 1: Load references

1. Read `docs/reference/admin-audit-security.md` for audit event APIs, security audit scopes, event categories, and date parameter conventions
2. Read `docs/reference/authentication.md` for auth token conventions and scope requirements

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

### Required scopes by audit type

| Audit Type | CLI Group | Scope | Date Params | Notes |
|------------|-----------|-------|-------------|-------|
| Admin audit events | `audit-events` | Standard admin token | `--from` / `--to` | Full or read-only admin. No special scope beyond admin auth. |
| Security audit events | `security-audit` | `audit:events_read` | `--start-time` / `--end-time` | Specifically required. Standard admin token without this scope returns 401/403. |
| Platform events (compliance) | `events` | Standard admin token | `--from` / `--to` | Full or read-only admin. Compliance officer role also works. |
| Authorizations review | `authorizations` | Standard admin token | N/A | Lists OAuth grants for users and the org. Full admin required for delete. |
| Service app tokens | `service-apps` | Admin + service app credentials | N/A | Requires `client-id`, `client-secret`, and `target-org-id`. |

### Verification gate

Run a quick probe for the audit type the user needs. If it fails, stop and fix auth before proceeding.

```bash
# Admin audit — verify access
wxcli audit-events list-event-categories -o json

# Security audit — verify audit:events_read scope
wxcli security-audit list \
  --start-time "2026-03-18T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  --limit 1 \
  -o json

# Platform events — verify access
wxcli events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  --limit 1 \
  -o json

# Authorizations — verify access
wxcli authorizations show -o json
```

If the probe returns 401/403, the token lacks the required scope. Resolve before continuing.

## Step 3: Identify the operation

Ask the user what they want to investigate. Present this decision matrix if they are unsure:

| Need | Operation | CLI Group |
|------|-----------|-----------|
| Who changed what in Control Hub | Admin audit events | `audit-events` |
| Security incidents (failed logins, policy changes) | Security audit events | `security-audit` |
| Compliance review (messages, calls, meetings) | Platform events | `events` |
| Review OAuth grants and integrations | Authorization audit | `authorizations` |
| Create/rotate service app credentials | Service app token | `service-apps` |
| List available audit event categories | Category reference | `audit-events` |

## Step 4: Check prerequisites

### 4a. Confirm date range and filters

All audit queries require scoping. Confirm with the user:

1. **Date range** — What period to cover? Use ISO 8601 format (`2026-03-18T00:00:00.000Z`).
2. **Filters** — Any specific actor (admin/user), event category, resource type, or event type?
3. **Date parameter names** — `audit-events` and `events` use `--from`/`--to`. `security-audit` uses `--start-time`/`--end-time`. Mixing them produces errors.

### 4b. Resolve actor IDs if filtering by person

If the user wants to filter by a specific admin or user, resolve their person ID first:

```bash
wxcli people list --email "admin@company.com" -o json
```

For event category filtering on admin audit, discover available categories:

```bash
wxcli audit-events list-event-categories -o json
```

This returns the exact category names (which may be case-sensitive). <!-- NEEDS VERIFICATION: case sensitivity of event categories -->

## Step 5: Build and present deployment plan -- [SHOW BEFORE EXECUTING]

Present the query plan to the user for approval before executing. Include:

1. **Which API** — `audit-events`, `security-audit`, `events`, `authorizations`, or `service-apps`
2. **Date range** — Start and end dates, using the correct parameter names for the chosen API
3. **Filters** — Actor ID, event category, resource type, event type (if any)
4. **Output format and destination** — Screen display, file export, or pipe to analysis
5. **Destructive operations** — Flag any delete/revoke operations and require explicit confirmation

Example plan format:

```
Audit Query Plan:
  API:        wxcli security-audit list
  Date range: 2026-03-12 to 2026-03-19 (--start-time / --end-time)
  Filters:    --event-categories "Logins"
  Output:     JSON to screen
  Destructive: No
```

**Do not proceed to Step 6 until the user approves the plan.**

## Step 6: Execute via wxcli

Execute the approved query plan. Jump to the sub-step matching the audit type identified in Step 3.

### 6a. Admin audit events (`audit-events`)

Use `wxcli audit-events` to see who changed what in Control Hub. Every admin action is logged: user created, setting changed, license assigned, location modified, policy updated.

**List audit events with a date range:**

```bash
wxcli audit-events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

**Filter by admin (actor):**

```bash
wxcli audit-events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

**Filter by event category:**

```bash
wxcli audit-events list \
  --event-categories "Users" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

**Limit results for a quick check:**

```bash
wxcli audit-events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  --limit 50 \
  -o json
```

### 6b. Security audit events (`security-audit`)

Use `wxcli security-audit` for security-related events: login failures, suspicious activity, security policy changes, authentication anomalies. This is the API to use when investigating security incidents or feeding events into an external SIEM.

**List security events for a date range:**

```bash
wxcli security-audit list \
  --start-time "2026-03-12T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json
```

Note: `security-audit` uses `--start-time`/`--end-time`, NOT `--from`/`--to` like the other audit APIs.

**Filter by actor:**

```bash
wxcli security-audit list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --start-time "2026-03-01T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json
```

**Filter by event category:**

```bash
wxcli security-audit list \
  --event-categories "Logins" \
  --start-time "2026-03-18T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json
```

**Export for SIEM ingestion:**

```bash
# Pull the last 7 days of security events as JSON file
wxcli security-audit list \
  --start-time "2026-03-12T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json > security_events_export.json

# For ongoing daily ingestion, use a 24-hour window
wxcli security-audit list \
  --start-time "2026-03-18T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json >> siem_feed.json
```

### 6c. Platform events — compliance (`events`)

Use `wxcli events` for general Webex platform activity: messages created/deleted, calls placed, meetings held, memberships changed. This is the API for compliance reviews, eDiscovery, and building integrations that react to platform activity.

**List events with a date range:**

```bash
wxcli events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

**Filter by resource type:**

```bash
# Only calling events
wxcli events list \
  --service-type calling \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Only message events
wxcli events list \
  --resource messages \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

**Filter by event type:**

```bash
# Deleted resources (compliance/eDiscovery)
wxcli events list \
  --type deleted \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Created messages only
wxcli events list \
  --resource messages \
  --type created \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

**Compliance review for a specific user:**

```bash
# Get the user's person ID (if not already resolved in Step 4b)
wxcli people list --email "user@company.com" -o json

# Pull all events for that user
wxcli events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Get full details on a specific event
wxcli events show "Y2lzY29zcGFyazovL3VzL0VWRU5ULzU2Nzg5"
```

**Event resource types reference:**

| Resource | Description |
|----------|-------------|
| `messages` | Messages sent/deleted in rooms |
| `memberships` | Room membership changes |
| `rooms` | Room creation/updates |
| `telephony_calls` | Webex Calling call events |
| `meetings` | Meeting events |
| `recordings` | Recording events |
| `meetingMessages` | In-meeting chat messages |

**Event types reference:**

| Type | Description |
|------|-------------|
| `created` | Resource was created |
| `updated` | Resource was updated |
| `deleted` | Resource was deleted |
| `ended` | Resource ended (calls, meetings) |

### 6d. Authorization audit (`authorizations`)

Use `wxcli authorizations` to review OAuth grants and integrations authorized in the org. This reveals which third-party apps and integrations have access to user or org data.

**List authorizations for a user:**

```bash
# By email
wxcli authorizations list --person-email "user@company.com" -o json

# By person ID
wxcli authorizations list --person-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" -o json
```

**Check token expiration status:**

```bash
wxcli authorizations show -o json
```

**Revoke an OAuth authorization by client ID:**

This is destructive -- it revokes access for an integration across the org. Always confirm with the user before executing.

```bash
# Revoke an integration's OAuth grant by its client ID
wxcli authorizations delete --client-id "C1234567890abcdef" --force
```

**Delete a specific authorization by ID:**

This is destructive -- it removes a specific authorization. Always confirm with the user before executing.

```bash
wxcli authorizations delete-authorizations "Y2lzY29zcGFyazovL3VzL0FVVEhPUklaQVRJT04vMTIz" --force
```

### 6e. Service app credential management (`service-apps`)

Use `wxcli service-apps` to create access tokens for service applications. Service apps are non-interactive integrations that act on behalf of an org.

**Create a service app access token:**

```bash
wxcli service-apps create APPLICATION_ID \
  --client-id "C1234567890abcdef" \
  --client-secret "secret_value_here" \
  --target-org-id "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0"
```

The returned token is short-lived. Store it immediately -- the secret is only shown once at creation time.

## Step 7: Verify

After executing the query, verify the results are correct and complete.

### Quick verification checks

1. **Non-empty results** — If the query returned empty, check: date range too narrow? Wrong filter values? Misspelled `--resource` type (returns empty, not error)?
2. **Expected scope** — Do results cover the expected time period and event types?
3. **Actor correlation** — If filtering by actor, confirm the returned events match the expected admin/user.

### Spot-check a specific record

```bash
# For platform events, get full details on one event
wxcli events show "EVENT_ID_FROM_RESULTS"

# For admin audit, re-query a narrow window to confirm
wxcli audit-events list \
  --from "2026-03-18T12:00:00.000Z" \
  --to "2026-03-18T13:00:00.000Z" \
  --limit 5 \
  -o json
```

## Step 8: Report results

After retrieving and verifying audit data, analyze and present the results.

### Summarize admin changes by category

```bash
wxcli audit-events list \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
if isinstance(data, dict):
    data = data.get('items', [data])
categories = Counter(e.get('eventCategory', 'Unknown') for e in data)
for cat, count in categories.most_common():
    print(f'{cat}: {count} events')
"
```

### Identify most active admins

```bash
wxcli audit-events list \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
if isinstance(data, dict):
    data = data.get('items', [data])
actors = Counter(e.get('actorEmail', e.get('actorId', 'Unknown')) for e in data)
for actor, count in actors.most_common(10):
    print(f'{actor}: {count} actions')
"
```

### Count events by resource type

```bash
wxcli events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
if isinstance(data, dict):
    data = data.get('items', [data])
resources = Counter(e.get('resource', 'Unknown') for e in data)
for res, count in resources.most_common():
    print(f'{res}: {count} events')
"
```

### List all OAuth integrations for a user

```bash
wxcli authorizations list --person-email "user@company.com" -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, dict):
    data = data.get('items', [data])
for auth in data:
    print(f\"App: {auth.get('applicationName', 'Unknown')} | Client: {auth.get('clientId', 'N/A')} | Scope: {auth.get('scope', 'N/A')}\")
"
```

---

## Critical Rules

1. **`audit-events` and `security-audit` are different APIs with different scopes.** `audit-events` = admin changes in Control Hub, works with standard admin token. `security-audit` = security/login events, requires `audit:events_read` scope. Do not confuse them.
2. **`security-audit` requires `audit:events_read` scope specifically.** A standard admin token without this scope returns 401 or 403. If you get a scope error on `security-audit list`, the token needs the `audit:events_read` scope added.
3. **Date range filtering is essential.** Without date parameters, you get the full event stream, which can be enormous and slow. Always specify a date range.
4. **Date parameter names differ across APIs.** `audit-events` and `events` use `--from`/`--to`. `security-audit` uses `--start-time`/`--end-time`. Mixing them up produces errors. See Step 2 scopes table for the mapping.
5. **Events API covers all platform events, not just calling.** Filter by `--resource` and `--type` to narrow results. Use `--service-type calling` to scope to Webex Calling events only.
6. **`authorizations delete` revokes access -- this is destructive.** It removes an OAuth grant by client ID across the org. Always confirm with the user before executing. `delete-authorizations` removes a specific authorization by ID.
7. **Service app token creation returns a short-lived token.** Store it immediately. The credentials (`client-secret`) are only shown once at creation time and cannot be retrieved later.
8. **Always show the query plan before executing (Step 5).** Present which API, date range, filters, and output format to the user for confirmation before running queries.
9. **ISO 8601 datetime format required.** All date parameters expect ISO 8601 format: `2026-03-18T00:00:00.000Z`. Other formats return errors or unexpected results.
10. **Event categories are case-sensitive.** Always run `wxcli audit-events list-event-categories` first (Step 4b) to discover the exact category names before filtering. <!-- NEEDS VERIFICATION: case sensitivity of event categories -->
11. **`events list` resource types are not validated client-side.** Misspelled `--resource` values return empty result sets, not errors. Use the known resource types listed in Step 6c.

---

## Scope Quick Reference

| Scope | Grants Access To |
|-------|-----------------|
| Standard admin token | Admin audit events (`wxcli audit-events`), platform events (`wxcli events`), authorizations (`wxcli authorizations`) |
| `audit:events_read` | Security audit events (`wxcli security-audit`) |
| Compliance officer role | Platform events with compliance-level access (`wxcli events`) |

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| 401/403 on `security-audit list` | Token missing `audit:events_read` scope | Regenerate token with `audit:events_read` scope or use a service app with that scope |
| Empty results from `events list` | Wrong `--resource` value or no events in date range | Check resource type spelling against Step 6c resource types table; widen the date range |
| 403 on `authorizations list` | Insufficient admin privileges | Requires full admin, not read-only |
| Empty results from `audit-events list` | Date range too narrow or no admin activity | Widen the date range; verify org has admin activity in that period |
| 400 on date parameters | Wrong date format or wrong parameter names for the API | Use ISO 8601 (`2026-03-18T00:00:00.000Z`); check Step 2 table for which date params the API expects |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read `docs/reference/admin-audit-security.md` to recover API details, scopes, and date parameter conventions
2. Check what data has already been retrieved by reviewing recent command output
3. Resume from the first incomplete step
