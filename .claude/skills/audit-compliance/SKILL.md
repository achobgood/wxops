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

## Step 2: Verify auth

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

### Required scopes by audit type

| Audit Type | Scope | Notes |
|------------|-------|-------|
| Admin audit events | Standard admin token | Full or read-only admin. No special scope beyond admin auth. |
| Security audit events | `audit:events_read` | Specifically required. Standard admin token without this scope returns 401/403. |
| Platform events (compliance) | Standard admin token | Full or read-only admin. Compliance officer role also works. |
| Authorizations review | Standard admin token | Lists OAuth grants for users and the org. |
| Service app tokens | Admin + service app credentials | Requires `client-id`, `client-secret`, and `target-org-id`. |

## Step 3: Identify the audit need

Ask the user what they want to investigate. Present this decision matrix if they are unsure:

| Need | Operation | CLI Group |
|------|-----------|-----------|
| Who changed what in Control Hub | Admin audit events | `audit-events` |
| Security incidents (failed logins, policy changes) | Security audit events | `security-audit` |
| Compliance review (messages, calls, meetings) | Platform events | `events` |
| Review OAuth grants and integrations | Authorization audit | `authorizations` |
| Create/rotate service app credentials | Service app token | `service-apps` |
| List available audit event categories | Category reference | `audit-events` |

## Step 4: Admin audit events

Use `wxcli audit-events` to see who changed what in Control Hub. Every admin action is logged: user created, setting changed, license assigned, location modified, policy updated.

### 4a. Discover available event categories

```bash
wxcli audit-events list-event-categories -o json
```

This returns the list of category names you can use to filter audit events.

### 4b. List audit events with a date range

```bash
wxcli audit-events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

### 4c. Filter by admin (actor)

```bash
# Step 1: Get the admin's person ID
wxcli people list --email "admin@company.com" -o json

# Step 2: Pull their audit events
wxcli audit-events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

### 4d. Filter by event category

```bash
wxcli audit-events list \
  --event-categories "Users" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

### 4e. Limit results for a quick check

```bash
wxcli audit-events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  --limit 50 \
  -o json
```

## Step 5: Security audit events

Use `wxcli security-audit` for security-related events: login failures, suspicious activity, security policy changes, authentication anomalies. This is the API to use when investigating security incidents or feeding events into an external SIEM.

### 5a. List security events for a date range

```bash
wxcli security-audit list \
  --start-time "2026-03-12T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json
```

Note: `security-audit` uses `--start-time`/`--end-time`, NOT `--from`/`--to` like the other audit APIs.

### 5b. Filter by actor

```bash
wxcli security-audit list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --start-time "2026-03-01T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json
```

### 5c. Filter by event category

```bash
wxcli security-audit list \
  --event-categories "Logins" \
  --start-time "2026-03-18T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  -o json
```

### 5d. Export for SIEM ingestion

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

## Step 6: Platform events (compliance)

Use `wxcli events` for general Webex platform activity: messages created/deleted, calls placed, meetings held, memberships changed. This is the API for compliance reviews, eDiscovery, and building integrations that react to platform activity.

### 6a. List events with a date range

```bash
wxcli events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json
```

### 6b. Filter by resource type

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

### 6c. Filter by event type

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

### 6d. Compliance review for a specific user

```bash
# Step 1: Get the user's person ID
wxcli people list --email "user@company.com" -o json

# Step 2: Pull all events for that user
wxcli events list \
  --actor-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" \
  --from "2026-03-01T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  -o json

# Step 3: Get full details on a specific event
wxcli events show "Y2lzY29zcGFyazovL3VzL0VWRU5ULzU2Nzg5"
```

### 6e. Event resource types reference

| Resource | Description |
|----------|-------------|
| `messages` | Messages sent/deleted in rooms |
| `memberships` | Room membership changes |
| `rooms` | Room creation/updates |
| `telephony_calls` | Webex Calling call events |
| `meetings` | Meeting events |
| `recordings` | Recording events |
| `meetingMessages` | In-meeting chat messages |

### 6f. Event types reference

| Type | Description |
|------|-------------|
| `created` | Resource was created |
| `updated` | Resource was updated |
| `deleted` | Resource was deleted |
| `ended` | Resource ended (calls, meetings) |

## Step 7: Authorization audit

Use `wxcli authorizations` to review OAuth grants and integrations authorized in the org. This reveals which third-party apps and integrations have access to user or org data.

### 7a. List authorizations for a user

```bash
# By email
wxcli authorizations list --person-email "user@company.com" -o json

# By person ID
wxcli authorizations list --person-id "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0" -o json
```

### 7b. Check token expiration status

```bash
wxcli authorizations show -o json
```

### 7c. Revoke an OAuth authorization by client ID

This is destructive -- it revokes access for an integration across the org. Always confirm with the user before executing.

```bash
# Revoke an integration's OAuth grant by its client ID
wxcli authorizations delete --client-id "C1234567890abcdef" --force
```

### 7d. Delete a specific authorization by ID

This is destructive -- it removes a specific authorization. Always confirm with the user before executing.

```bash
wxcli authorizations delete-authorizations "Y2lzY29zcGFyazovL3VzL0FVVEhPUklaQVRJT04vMTIz" --force
```

## Step 8: Service app credential management

Use `wxcli service-apps` to create access tokens for service applications. Service apps are non-interactive integrations that act on behalf of an org.

### 8a. Create a service app access token

```bash
wxcli service-apps create APPLICATION_ID \
  --client-id "C1234567890abcdef" \
  --client-secret "secret_value_here" \
  --target-org-id "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xMjM0"
```

The returned token is short-lived. Store it immediately -- the secret is only shown once at creation time.

## Step 9: Analysis recipes

After retrieving audit data, use these patterns to analyze the results.

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

## Step 10: Verification and query plan

Always show the query plan to the user before executing. Confirm:

1. Which API to use (`audit-events`, `security-audit`, `events`, `authorizations`, or `service-apps`)
2. Date range (and the correct date parameter names for that API)
3. Any filters (actor, category, resource type, event type)
4. Output format and destination (screen, file, or pipe to analysis)

### Quick verification checks

```bash
# Verify audit events are accessible
wxcli audit-events list-event-categories -o json

# Verify security audit scope
wxcli security-audit list \
  --start-time "2026-03-18T00:00:00.000Z" \
  --end-time "2026-03-19T00:00:00.000Z" \
  --limit 1 \
  -o json

# Verify events API access
wxcli events list \
  --from "2026-03-18T00:00:00.000Z" \
  --to "2026-03-19T00:00:00.000Z" \
  --limit 1 \
  -o json

# Verify authorizations access
wxcli authorizations show -o json
```

---

## Critical Rules

1. **`audit-events` and `security-audit` are different APIs with different scopes.** `audit-events` = admin changes in Control Hub, works with standard admin token. `security-audit` = security/login events, requires `audit:events_read` scope. Do not confuse them.
2. **`security-audit` requires `audit:events_read` scope specifically.** A standard admin token without this scope returns 401 or 403. If you get a scope error on `security-audit list`, the token needs the `audit:events_read` scope added.
3. **Date range filtering is essential.** Without date parameters, you get the full event stream, which can be enormous and slow. Always specify a date range.
4. **Date parameter names differ across APIs.** `audit-events` and `events` use `--from`/`--to`. `security-audit` uses `--start-time`/`--end-time`. Mixing them up produces errors.
5. **Events API covers all platform events, not just calling.** Filter by `--resource` and `--type` to narrow results. Use `--service-type calling` to scope to Webex Calling events only.
6. **`authorizations delete` revokes access -- this is destructive.** It removes an OAuth grant by client ID across the org. Always confirm with the user before executing. `delete-authorizations` removes a specific authorization by ID.
7. **Service app token creation returns a short-lived token.** Store it immediately. The credentials (`client-secret`) are only shown once at creation time and cannot be retrieved later.
8. **Always show the query plan before executing.** Present which API, date range, filters, and output format to the user for confirmation before running queries.
9. **ISO 8601 datetime format required.** All date parameters expect ISO 8601 format: `2026-03-18T00:00:00.000Z`. Other formats return errors or unexpected results.
10. **Event categories are case-sensitive.** Always run `wxcli audit-events list-event-categories` first to discover the exact category names before filtering. <!-- NEEDS VERIFICATION: case sensitivity of event categories -->
11. **`events list` resource types are not validated client-side.** Misspelled `--resource` values return empty result sets, not errors. Use the known resource types listed in Step 6e.

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
| Empty results from `events list` | Wrong `--resource` value or no events in date range | Check resource type spelling against Step 6e table; widen the date range |
| 403 on `authorizations list` | Insufficient admin privileges | Requires full admin, not read-only |
| Empty results from `audit-events list` | Date range too narrow or no admin activity | Widen the date range; verify org has admin activity in that period |
| 400 on date parameters | Wrong date format or wrong parameter names for the API | Use ISO 8601 (`2026-03-18T00:00:00.000Z`); check which date params the API expects |

---

## Context Compaction

If context compacts mid-execution, recover by:
1. Read `docs/reference/admin-audit-security.md` to recover API details, scopes, and date parameter conventions
2. Check what data has already been retrieved by reviewing recent command output
3. Resume from the first incomplete step
