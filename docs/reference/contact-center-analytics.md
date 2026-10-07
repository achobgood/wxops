# Contact Center: AI, Analytics, Monitoring, and Events

Reference for Webex Contact Center AI features, customer journey analytics, call monitoring,
event subscriptions, and task management. Covers 15 CLI groups with 132 commands generated
from the Contact Center OpenAPI spec.

> **Regional base URL:** `https://api.wxcc-{region}.cisco.com`
> **Regions:** us1, eu1, eu2, anz1, ca1, jp1, sg1
> **Auth:** CC-specific OAuth scopes (`cjp:config_read`, `cjp:config_write`)
> **Set region:** `wxcli set-cc-region <region>` (defaults to us1)

## Sources

- OpenAPI spec: `specs/webex-contact-center.json`
- developer.webex.com Contact Center APIs

## Table of Contents

1. [AI Assistant](#1-ai-assistant)
2. [AI Feature](#2-ai-feature)
3. [Auto CSAT](#3-auto-csat)
4. [Generated Summaries](#4-generated-summaries)
5. [Agent Summaries](#5-agent-summaries)
6. [Journey (Moved)](#6-journey-moved) → [`contact-center-journey.md`](contact-center-journey.md)
7. [Call Monitoring](#7-call-monitoring)
8. [Realtime](#8-realtime)
9. [Subscriptions](#9-subscriptions)
10. [Tasks](#10-tasks)
11. [Notifications](#11-notifications)
12. [Search](#12-search)
13. [Address Book](#13-address-book)
14. [Usage Reports](#14-usage-reports)
15. [External Data Updates](#15-external-data-updates-external-data-updates)
16. [Raw HTTP Endpoint Table](#raw-http-endpoint-table)
17. [Gotchas](#gotchas)
18. [See Also](#see-also)

---

## 1. AI Assistant

CLI group: `wxcli cc-ai-assistant` (1 command)

The AI Assistant endpoint accepts events and returns AI-generated suggestions for agents
during active contact handling. This is a runtime API that feeds the agent desktop with
contextual recommendations.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/event` | Get suggestions from the AI assistant |

### Key Parameters

- `--json-body` — Full JSON body containing the event payload (required for meaningful responses)

### CLI Examples

```bash
# Get AI suggestions for an active contact
wxcli cc-ai-assistant create --json-body '{
  "eventType": "agent:desktop",
  "contactId": "abc123",
  "agentId": "agent-456"
}'
```

### Raw HTTP

```
POST https://api.wxcc-us1.cisco.com/event
Authorization: Bearer {cc_token}
Content-Type: application/json

{
  "eventType": "agent:desktop",
  "contactId": "abc123",
  "agentId": "agent-456"
}
```

---

## 2. AI Feature

CLI group: `wxcli cc-ai-feature` (3 commands)

Manage AI feature configurations for the contact center organization. AI features control
which AI capabilities (agent answers, auto-summaries, sentiment analysis, etc.) are enabled
and how they are configured.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show` | GET `/organization/{orgid}/ai-feature/{id}` | Get specific AI Feature resource by ID |
| `update` | PATCH `/organization/{orgid}/ai-feature/{id}` | Partially update AI Feature resource by ID |
| `list` | GET `/organization/{orgid}/v2/ai-feature` | List AI Feature resources |

### Key Parameters

- `id` (positional) — AI Feature resource ID (for show/update)
- `--json-body` — Partial update payload (for update)
- `--output` / `-o` — Output format: `table` or `json`

### CLI Examples

```bash
# List all AI features
wxcli cc-ai-feature list

# Get a specific AI feature
wxcli cc-ai-feature show feat-abc-123

# Enable/disable an AI feature
wxcli cc-ai-feature update feat-abc-123 --json-body '{"active": true}'
```

### Raw HTTP

```
# List AI features
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/ai-feature
Authorization: Bearer {cc_token}

# Get specific AI feature
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/ai-feature/{id}
Authorization: Bearer {cc_token}

# Partial update
PATCH https://api.wxcc-us1.cisco.com/organization/{orgId}/ai-feature/{id}
Authorization: Bearer {cc_token}
Content-Type: application/json

{"active": true}
```

---

## 3. Auto CSAT

> **Deprecated (April 2026).** The standalone Auto CSAT API is deprecated and will be removed in a future release. Use the consolidated `AI Feature` API (Section 2) instead. Existing configurations continue to work until removal is announced.

CLI group: `wxcli cc-auto-csat` (8 commands)

Auto CSAT (Customer Satisfaction) automates customer satisfaction scoring using AI analysis
of contact interactions. The API has a two-level structure: Auto CSAT configurations at the
top level, with mapped questions nested underneath.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `.../auto-csat/{autoCsatId}/question` | Create a new mapped question |
| `create-bulk` | POST `.../auto-csat/{autoCsatId}/question/bulk` | Bulk save mapped questions |
| `show` | GET `.../auto-csat/{autoCsatId}/question/{id}` | Get specific mapped question by ID |
| `delete` | DELETE `.../auto-csat/{autoCsatId}/question/{id}` | Delete specific mapped question by ID |
| `show-auto-csat` | GET `.../auto-csat/{id}` | Get specific Auto CSAT resource by ID |
| `update` | PUT `.../auto-csat/{id}` | Update specific Auto CSAT resource by ID |
| `list` | GET `.../v2/auto-csat` | List Auto CSAT resources (v2) |
| `list-question` | GET `.../v2/auto-csat/{autoCsatId}/question` | List mapped questions (v2) |

All paths are prefixed with `/organization/{orgid}`.

### Key Parameters

- `auto-csat-id` (positional) — Auto CSAT configuration ID
- `id` (positional) — Question ID (for show/delete)
- `--json-body` — Full JSON body for create/update operations

### CLI Examples

```bash
# List all Auto CSAT configurations
wxcli cc-auto-csat list

# Get a specific Auto CSAT config
wxcli cc-auto-csat show-auto-csat csat-001

# List questions for an Auto CSAT config
wxcli cc-auto-csat list-question csat-001

# Create a new mapped question
wxcli cc-auto-csat create csat-001 --json-body '{
  "question": "How satisfied were you with the service?",
  "questionType": "rating",
  "scale": 5
}'

# Bulk save questions
wxcli cc-auto-csat create-bulk csat-001 --json-body '{
  "questions": [
    {"question": "Rate agent helpfulness", "questionType": "rating", "scale": 5},
    {"question": "Would you recommend us?", "questionType": "boolean"}
  ]
}'
```

### Raw HTTP

```
# List Auto CSAT configs
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/auto-csat
Authorization: Bearer {cc_token}

# Create mapped question
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/auto-csat/{autoCsatId}/question
Authorization: Bearer {cc_token}
Content-Type: application/json

{"question": "How satisfied were you?", "questionType": "rating", "scale": 5}
```

---

## 4. Generated Summaries

CLI group: `wxcli cc-summaries` (3 commands)

Manage AI-generated summary configurations. These control how the system generates
post-interaction summaries for agents and supervisors.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show` | GET `/organization/{orgid}/generated-summaries/{id}` | Get specific resource by ID |
| `update` | PUT `/organization/{orgid}/generated-summaries/{id}` | Update specific resource by ID |
| `list` | GET `/organization/{orgid}/v2/generated-summaries` | List resources (v2) |

### Key Parameters

- `id` (positional) — Generated Summaries resource ID
- `--json-body` — Full JSON body for update
- `--output` / `-o` — Output format: `table` or `json`

### CLI Examples

```bash
# List generated summary configs
wxcli cc-summaries list

# Get a specific summary config
wxcli cc-summaries show summary-abc-123

# Update summary config
wxcli cc-summaries update summary-abc-123 --json-body '{"active": true}'
```

### Raw HTTP

```
# List
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/generated-summaries
Authorization: Bearer {cc_token}

# Update
PUT https://api.wxcc-us1.cisco.com/organization/{orgId}/generated-summaries/{id}
Authorization: Bearer {cc_token}
Content-Type: application/json

{"active": true}
```

---

## 5. Agent Summaries

CLI group: `wxcli cc-agent-summaries` (1 command)

Search agent interaction summaries. The endpoint uses POST (not GET) because
the query parameters are passed in the request body.

To list or fetch generated summaries by ID, use the `wxcli cc-summaries` group (section 4).

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/generated-summaries/search` | Search summaries |

### Key Parameters

- `--json-body` — Search/filter criteria in the request body

### CLI Examples

```bash
# Search summaries
wxcli cc-agent-summaries create --json-body '{
  "filter": {"agentId": "agent-456", "from": "2026-03-01T00:00:00Z"}
}'
```

### Raw HTTP

```
# Search summaries
POST https://api.wxcc-us1.cisco.com/generated-summaries/search
Authorization: Bearer {cc_token}
Content-Type: application/json

{"filter": {"agentId": "agent-456", "from": "2026-03-01T00:00:00Z"}}
```

---

## 6. Journey (Moved)

**JDS has been moved to its own reference doc: [`contact-center-journey.md`](contact-center-journey.md).**

41 commands covering workspaces, persons, identity resolution, profile view templates,
progressive profile views, event ingestion, and WXCC subscriptions. See that doc for
full API reference, raw HTTP table, and gotchas.

---

## 7. Call Monitoring

CLI group: `wxcli cc-call-monitoring` (7 commands)

Real-time call monitoring for supervisors. Supports creating monitoring sessions, barge-in,
hold/unhold monitoring, and session management. Most operations use `taskId` to identify the
contact being monitored, but delete uses `requestId`.

This group acts on calls that are happening now. Stored, recurring monitoring **schedules** —
which supervisor covers which teams and queues, and when — are a different group,
`cc-monitoring-schedules`, on the config API; see
[contact-center-core.md §21](contact-center-core.md#21-call-monitoring-schedules-cc-monitoring-schedules)
when the request is about a plan rather than a live call.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/v1/monitor` | Create monitoring request |
| `list` | GET `/v1/monitor/sessions` | Fetch monitoring sessions |
| `delete` | DELETE `/v1/monitor/{requestId}` | Delete monitoring request |
| `create-barge-in` | POST `/v1/monitor/{taskId}/bargeIn` | Barge-in to monitored call |
| `create-end` | POST `/v1/monitor/{taskId}/end` | End monitoring session |
| `create-hold` | POST `/v1/monitor/{taskId}/hold` | Hold monitoring request |
| `create-unhold` | POST `/v1/monitor/{taskId}/unhold` | Unhold monitoring request |

### Key Parameters

- `task-id` (positional) — Task ID of the contact to monitor (for barge-in, end, hold, unhold)
- `request-id` (positional) — Monitoring request ID (for delete)
- `--json-body` — Monitoring request configuration

### CLI Examples

```bash
# Create a monitoring session (id and monitorType are required)
wxcli cc-call-monitoring create --json-body '{
  "id": "req-abc-123",
  "taskId": "task-789",
  "monitorType": "silentMonitor"
}'

# List active monitoring sessions
wxcli cc-call-monitoring list

# Barge into a monitored call
wxcli cc-call-monitoring create-barge-in task-789

# Hold monitoring
wxcli cc-call-monitoring create-hold task-789

# Unhold monitoring
wxcli cc-call-monitoring create-unhold task-789

# End monitoring session
wxcli cc-call-monitoring create-end task-789

# Delete a monitoring request
wxcli cc-call-monitoring delete req-abc-123
```

### Raw HTTP

```
# Create monitoring session
POST https://api.wxcc-us1.cisco.com/v1/monitor
Authorization: Bearer {cc_token}
Content-Type: application/json

{"taskId": "task-789", "monitorType": "silentMonitor"}

# List active sessions
GET https://api.wxcc-us1.cisco.com/v1/monitor/sessions
Authorization: Bearer {cc_token}

# Barge in
POST https://api.wxcc-us1.cisco.com/v1/monitor/{taskId}/bargeIn
Authorization: Bearer {cc_token}
```

---

## 8. Realtime

CLI group: `wxcli cc-realtime` (1 command)

Subscribe to real-time notification feeds for contact center events. Returns a WebSocket
or SSE connection for streaming agent state, task, and queue updates.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/v1/realtime/subscribe` | Subscribe to realtime notifications |

### CLI Examples

```bash
# Subscribe to realtime notifications
wxcli cc-realtime create --json-body '{
  "resource": "task",
  "subscriptionIds": ["sub-001"]
}'
```

### Raw HTTP

```
POST https://api.wxcc-us1.cisco.com/v1/realtime/subscribe
Authorization: Bearer {cc_token}
Content-Type: application/json

{"resource": "task", "subscriptionIds": ["sub-001"]}
```

---

## 9. Subscriptions

CLI group: `wxcli cc-subscriptions` (12 commands)

Manage event subscriptions for the contact center. Subscriptions define which events
(agent state changes, task events, queue updates) are delivered to your application.
Both v1 and v2 APIs are available — v2 adds enhanced event types.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `list-event-types-v1` | GET `/v1/event-types` | List event types (v1) |
| `list` | GET `/v1/subscriptions` | List subscriptions (v1) |
| `create` | POST `/v1/subscriptions` | Register subscription (v1) |
| `show` | GET `/v1/subscriptions/{id}` | Get subscription (v1) |
| `delete` | DELETE `/v1/subscriptions/{id}` | Delete subscription (v1) |
| `update` | PATCH `/v1/subscriptions/{id}` | Update subscription (v1) |
| `list-event-types-v2` | GET `/v2/event-types` | List event types (v2) |
| `list-subscriptions` | GET `/v2/subscriptions` | List subscriptions (v2) |
| `create-subscriptions` | POST `/v2/subscriptions` | Register subscription (v2) |
| `show-subscriptions` | GET `/v2/subscriptions/{id}` | Get subscription (v2) |
| `delete-subscriptions` | DELETE `/v2/subscriptions/{id}` | Delete subscription (v2) |
| `update-subscriptions` | PATCH `/v2/subscriptions/{id}` | Update subscription (v2) |

### Key Parameters

- `id` (positional) — Subscription ID (for show/update/delete)
- `--json-body` — Subscription registration or update payload

### CLI Examples

```bash
# List available event types (v2)
wxcli cc-subscriptions list-event-types-v2

# Register a v2 subscription (uses resourceVersion, v2 event names)
wxcli cc-subscriptions create-subscriptions --json-body '{
  "name": "Agent State Changes",
  "eventTypes": ["agent:channel_state_change"],
  "resourceVersion": "agent:2.0.0",
  "callbackUrl": "https://example.com/cc-webhook"
}'

# List active subscriptions
wxcli cc-subscriptions list-subscriptions

# Get subscription details
wxcli cc-subscriptions show-subscriptions sub-001

# Update subscription
wxcli cc-subscriptions update-subscriptions sub-001 --json-body '{
  "eventTypes": ["agent:channel_state_change", "task:new"]
}'

# Delete subscription
wxcli cc-subscriptions delete-subscriptions sub-001
```

### Raw HTTP

```
# List event types (v2)
GET https://api.wxcc-us1.cisco.com/v2/event-types
Authorization: Bearer {cc_token}

# Register subscription (v2)
POST https://api.wxcc-us1.cisco.com/v2/subscriptions
Authorization: Bearer {cc_token}
Content-Type: application/json

{
  "name": "Agent State Changes",
  "eventTypes": ["agent:channel_state_change"],
  "resourceVersion": "agent:2.0.0",
  "callbackUrl": "https://example.com/cc-webhook"
}

# Get subscription
GET https://api.wxcc-us1.cisco.com/v2/subscriptions/{id}
Authorization: Bearer {cc_token}
```

---

## 10. Tasks

CLI group: `wxcli cc-tasks` (26 commands)

The Tasks API is the primary agent interaction API — it handles the full contact/call
lifecycle from creation through wrap-up. Agents accept, hold, transfer, consult, conference,
and wrap up tasks. The API also handles preview dialer tasks and recording controls.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `list` | GET `/v1/tasks` | Get tasks |
| `create` | POST `/v1/tasks` | Create task (v1) |
| `update` | PATCH `/v1/tasks/{taskId}` | Update task |
| `create-accept-tasks` | POST `/v1/tasks/{taskId}/accept` | Accept task |
| `create-assign` | POST `/v1/tasks/{taskId}/assign` | Assign task |
| `create-exit` | POST `/v1/tasks/{taskId}/conference/exit` | Exit conference |
| `create-consult` | POST `/v1/tasks/{taskId}/consult` | Consult |
| `create-accept-consult` | POST `/v1/tasks/{taskId}/consult/accept` | Accept consult |
| `create-conference` | POST `/v1/tasks/{taskId}/consult/conference` | Consult conference |
| `create-end-consult` | POST `/v1/tasks/{taskId}/consult/end` | End consult |
| `create-transfer-consult` | POST `/v1/tasks/{taskId}/consult/transfer` | Consult transfer |
| `create-end-tasks` | POST `/v1/tasks/{taskId}/end` | End task |
| `create-hold` | POST `/v1/tasks/{taskId}/hold` | Hold task |
| `create-pause` | POST `/v1/tasks/{taskId}/record/pause` | Pause **recording** |
| `create-resume` | POST `/v1/tasks/{taskId}/record/resume` | Resume **recording** |
| `create-pause-tasks` | POST `/v1/tasks/{taskId}/pause` | Pause the **task** (added 2026-09-21) |
| `create-resume-tasks` | POST `/v1/tasks/{taskId}/resume` | Resume the **task** (added 2026-09-21) |
| `create-reject` | POST `/v1/tasks/{taskId}/reject` | Reject task |
| `create-transfer-tasks` | POST `/v1/tasks/{taskId}/transfer` | Transfer task |
| `create-unhold` | POST `/v1/tasks/{taskId}/unhold` | Resume (unhold) |
| `create-wrapup` | POST `/v1/tasks/{taskId}/wrapup` | Wrap up task |
| `create-tasks` | POST `/v2/tasks` | Create task (v2) |
| `create-messages` | POST `/v2/tasks/{taskId}/messages` | Update task (v2 messages) |
| `create-accept-preview-task` | POST `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/accept` | Accept preview task |
| `delete-preview-task` | POST `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/remove` | Remove preview task (args: `TASK_ID CAMPAIGN_ID`) |
| `create-skip` | POST `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/skip` | Skip preview task |

### Key Parameters

- `task-id` (positional) — Task ID for most operations
- `campaign-id` (positional) — Campaign ID (for preview dialer tasks)
- `--channel-types` — Filter by channel type(s) (for list)
- `--from` / `--to` — Epoch timestamp filters (for list)
- `--page-size` — Results per page (for list)
- `--json-body` — Request body for create/update/action operations

### CLI Examples

```bash
# List active tasks
wxcli cc-tasks list --from 1784592000000 --channel-types telephony

# Create a task
wxcli cc-tasks create --json-body '{
  "channelType": "telephony",
  "destination": "+15551234567",
  "direction": "OUTBOUND"
}'

# Accept a task
wxcli cc-tasks create-accept-tasks task-789

# Hold a task
wxcli cc-tasks create-hold task-789

# Resume (unhold) a task
wxcli cc-tasks create-unhold task-789

# Consult transfer
wxcli cc-tasks create-consult task-789 --json-body '{
  "destination": "agent-456",
  "destinationType": "agent"
}'

# Transfer after consult
wxcli cc-tasks create-transfer-consult task-789

# End task
wxcli cc-tasks create-end-tasks task-789

# Wrap up task
wxcli cc-tasks create-wrapup task-789 --json-body '{
  "wrapUpReason": "resolved"
}'

# Pause/resume recording
wxcli cc-tasks create-pause task-789
wxcli cc-tasks create-resume task-789

# Preview dialer: accept/skip/remove (TASK_ID first, then CAMPAIGN_ID)
wxcli cc-tasks create-accept-preview-task task-789 campaign-001
wxcli cc-tasks create-skip task-789 campaign-001
wxcli cc-tasks delete-preview-task task-789 campaign-001
```

### Raw HTTP

```
# List tasks
GET https://api.wxcc-us1.cisco.com/v1/tasks?channelTypes=telephony
Authorization: Bearer {cc_token}

# Create task
POST https://api.wxcc-us1.cisco.com/v1/tasks
Authorization: Bearer {cc_token}
Content-Type: application/json

{"channelType": "telephony", "destination": "+15551234567", "direction": "OUTBOUND"}

# Accept task
POST https://api.wxcc-us1.cisco.com/v1/tasks/{taskId}/accept
Authorization: Bearer {cc_token}

# Consult transfer
POST https://api.wxcc-us1.cisco.com/v1/tasks/{taskId}/consult/transfer
Authorization: Bearer {cc_token}

# Wrap up
POST https://api.wxcc-us1.cisco.com/v1/tasks/{taskId}/wrapup
Authorization: Bearer {cc_token}
Content-Type: application/json

{"wrapUpReason": "resolved"}
```

---

## 11. Notifications

CLI group: `wxcli cc-notification` (1 command)

Subscribe to contact center notifications. This is a separate mechanism from the
Subscriptions API (Section 9) and Realtime API (Section 8) — notifications provide
push-based event delivery.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/v1/notification/subscribe` | Subscribe to notifications |

### CLI Examples

```bash
# Subscribe to notifications
wxcli cc-notification create --json-body '{
  "notificationType": "agentDesktop",
  "resource": "task"
}'
```

### Raw HTTP

```
POST https://api.wxcc-us1.cisco.com/v1/notification/subscribe
Authorization: Bearer {cc_token}
Content-Type: application/json

{"notificationType": "agentDesktop", "resource": "task"}
```

---

## 12. Search

CLI groups: `wxcli cc-search` (1 command), `wxcli cc-search-metadata` (1 command)

Search for tasks using POST with query criteria in the request body (not GET with
query parameters).

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/search` | Search tasks |

### CLI Examples

```bash
# Search for tasks by agent and time range
wxcli cc-search create --json-body '{
  "query": {
    "agentId": "agent-456",
    "channelType": "telephony",
    "from": "2026-03-01T00:00:00Z",
    "to": "2026-03-28T23:59:59Z"
  }
}'
```

### Raw HTTP

```
POST https://api.wxcc-us1.cisco.com/search
Authorization: Bearer {cc_token}
Content-Type: application/json

{
  "query": {
    "agentId": "agent-456",
    "channelType": "telephony",
    "from": "2026-03-01T00:00:00Z",
    "to": "2026-03-28T23:59:59Z"
  }
}
```

### Search Metadata

CLI group: `wxcli cc-search-metadata` (1 command)

Returns the schema behind the Search GraphQL API: which query types exist, which fields each
one carries, their data types, and per field whether it is sortable, filterable, groupable, and
which aggregation operations it accepts. It is a **description of the search surface, not a
search** — it returns no tasks, contacts or statistics, and it provisions nothing. Reach for it
when you need to know whether a field can be filtered on before writing a `cc-search create`
query; reach for `cc-search` to get the records themselves.

#### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `list` | GET `/search/v2/meta` | Get search metadata |

The response is keyed on `queries`, one entry per GraphQL query type (`task`, and its siblings),
each carrying a nested `fields` array. There are no required flags and no positional arguments.

#### CLI Examples

```bash
# Every query type and its fields
wxcli cc-search-metadata list -o json

# Just the query type names
wxcli cc-search-metadata list --fields '[].name' -o json

# Which fields of the task query can be filtered on
# (flatten with `fields[] |` first — a filter projection applied straight to another
#  filter projection tests each nested LIST, never its items, and always yields [])
wxcli cc-search-metadata list --fields "[?name=='task'].fields[] | [?filter!=null].name" -o json

# Which fields can be grouped by, with their aggregation operations
wxcli cc-search-metadata list --fields '[].fields[?groupBy].{field:name,ops:aggregation.operations}' -o json
```

#### Raw HTTP

```
GET https://api.wxcc-us1.cisco.com/search/v2/meta
Authorization: Bearer {cc_token}
```

Requires `cjp:config` or `cjp:config_read`. An asterisk (`*`) in the rendered response schema
marks a required property.

---

## 13. Address Book

CLI group: `wxcli cc-address-book` (19 commands)

Manage contact center address books and their entries. Address books provide agent-facing
contact directories. The API has a two-level structure (address book then entries) and
spans three API versions (v1, v2, v3).

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `list` | GET `/organization/{orgid}/address-book` | List address books (v1) |
| `create` | POST `/organization/{orgid}/address-book` | Create address book (v1) |
| `list-bulk-export` | GET `/organization/{orgid}/address-book/bulk-export` | Bulk export |
| `create-entry` | POST `.../address-book/{addressBookId}/entry` | Create entry |
| `create-bulk` | POST `.../address-book/{addressBookId}/entry/bulk` | Bulk save entries |
| `show-address-book-organization` | GET `/organization/{orgid}/address-book/{id}` | Get address book (v1) |
| `update-address-book-organization` | PUT `/organization/{orgid}/address-book/{id}` | Update address book (v1) |
| `delete-address-book-organization` | DELETE `/organization/{orgid}/address-book/{id}` | Delete address book (v1) |
| `list-incoming-references` | GET `.../address-book/{id}/incoming-references` | Get references |
| `list-address-book-v2` | GET `/organization/{orgid}/v2/address-book` | List (v2) |
| `list-entry` | GET `.../v2/address-book/{addressBookId}/entry` | List entries (v2) |
| `show` | GET `.../address-book/{addressBookId}/entry/{id}` | Get entry |
| `update` | PUT `.../address-book/{addressBookId}/entry/{id}` | Update entry |
| `delete` | DELETE `.../address-book/{addressBookId}/entry/{id}` | Delete entry |
| `list-address-book-v3` | GET `/organization/{orgid}/v3/address-book` | List (v3) |
| `create-address-book` | POST `/organization/{orgid}/v3/address-book` | Create (v3) |
| `show-address-book-v3` | GET `/organization/{orgid}/v3/address-book/{id}` | Get (v3) |
| `update-address-book-v3` | PUT `/organization/{orgid}/v3/address-book/{id}` | Update (v3) |
| `delete-address-book-v3` | DELETE `/organization/{orgid}/v3/address-book/{id}` | Delete (v3) |

### Key Parameters

- `id` (positional) — Address book ID
- `address-book-id` (positional) — Address book ID (for entry operations)
- `--json-body` — Full JSON body for create/update operations

### CLI Examples

```bash
# List address books (v3)
wxcli cc-address-book list-address-book-v3

# Create address book (v3)
wxcli cc-address-book create-address-book --json-body '{
  "name": "Sales Contacts",
  "description": "External sales contacts"
}'

# Create an entry
wxcli cc-address-book create-entry ab-001 --json-body '{
  "firstName": "Jane",
  "lastName": "Smith",
  "phoneNumber": "+15559876543"
}'

# Bulk save entries
wxcli cc-address-book create-bulk ab-001 --json-body '{
  "entries": [
    {"firstName": "Alice", "phoneNumber": "+15551111111"},
    {"firstName": "Bob", "phoneNumber": "+15552222222"}
  ]
}'

# Bulk export
wxcli cc-address-book list-bulk-export

# List entries for an address book
wxcli cc-address-book list-entry ab-001

# Delete entry
wxcli cc-address-book delete ab-001 entry-001

# Check incoming references before deleting an address book
wxcli cc-address-book list-incoming-references ab-001
wxcli cc-address-book delete-address-book-v3 ab-001
```

### Raw HTTP

```
# List address books (v3)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v3/address-book
Authorization: Bearer {cc_token}

# Create address book (v3)
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/v3/address-book
Authorization: Bearer {cc_token}
Content-Type: application/json

{"name": "Sales Contacts", "description": "External sales contacts"}

# Create entry
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/address-book/{addressBookId}/entry
Authorization: Bearer {cc_token}
Content-Type: application/json

{"firstName": "Jane", "lastName": "Smith", "phoneNumber": "+15559876543"}

# Bulk export
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/address-book/bulk-export
Authorization: Bearer {cc_token}
```

---

## 14. Usage Reports

CLI group: `wxcli usage-reports` (6 commands)

Usage Reports generate and retrieve **billing-style consumption extracts** — how much of a given
resource type the org consumed over a date range — as asynchronously produced downloadable files.
This is not real-time analytics and not the queue/agent statistics in `reporting-cc`: nothing here
answers "what is happening right now", and the numbers arrive as a file you download rather than as
JSON rows you filter. It is also unrelated to Webex Calling CDR (`wxcli cdr`, see
`reporting-analytics.md`) and to meetings usage reports.

**Unverified:** this section is derived from `specs/webex-contact-center.json` (2026-09-21 refresh)
and the generated module. No live call was made, so report lifecycle timings and file formats are
spec-stated, not measured.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `list-resource-types` | GET `/v1/usage-reports/resource-types` | Resource types a report can be generated for, with the dates data exists for |
| `create` | POST `/v1/usage-reports` | Create a usage report (generated asynchronously) |
| `list-usage-reports` | GET `/v1/usage-reports` | List usage reports in the org |
| `show` | GET `/v1/usage-reports/{reportId}` | Get one report's details, including `reportFiles[]` |
| `list-download` | GET `/v1/usage-reports/{fileId}/download` | Download one completed report FILE as a binary stream |
| `delete` | DELETE `/v1/usage-reports/{reportId}` | Delete a report and its file — cannot be undone |

`list` is a hidden alias of `list-resource-types` and exists only so an older invocation keeps
working. Prefer the explicit name: the bare `list` in this group returns resource *types*, not
reports, which is the trap the rename removes.

### Key Parameters

- `--resource-type` — which resource the report covers; take the value from `list-resource-types`, not from memory.
- `--start-date` / `--end-date` — `yyyy-MM-dd`. Start is inclusive, **end is exclusive**.
- `report_id` (positional) — for `show` and `delete`.
- `file_id` (positional) — for `list-download`, and it is **not** a report id (see the gotcha).

### CLI Examples

```bash
# What can be reported on, and for which dates does data exist?
wxcli usage-reports list-resource-types

# Request a report (returns the reportId; generation is asynchronous)
wxcli usage-reports create --resource-type <resource-type> --start-date 2026-08-01 --end-date 2026-09-01

# List reports that already exist
wxcli usage-reports list-usage-reports --all

# Get one report's details and the file ids it produced
wxcli usage-reports show <report-id>

# Pull just the file ids out of that report
wxcli usage-reports show <report-id> --fields 'reportFiles[].fileId' -o text

# Download ONE file, by fileId (not reportId) -- binary stream
wxcli usage-reports list-download <file-id>

# Delete a report and its file (irreversible)
wxcli usage-reports delete <report-id>
```

### Raw HTTP

```bash
# Available resource types
GET https://api.wxcc-us1.cisco.com/v1/usage-reports/resource-types
Authorization: Bearer {cc_token}

# Create a usage report
POST https://api.wxcc-us1.cisco.com/v1/usage-reports
Content-Type: application/json
{"resourceType":"{resourceType}","startDate":"2026-08-01","endDate":"2026-09-01"}

# Report details (carries reportFiles[])
GET https://api.wxcc-us1.cisco.com/v1/usage-reports/{reportId}

# Download one file
GET https://api.wxcc-us1.cisco.com/v1/usage-reports/{fileId}/download
```

### Gotcha

**`list-download` takes a `fileId`, and a `reportId` in that position will not work — even though
the two ids sit in the same response and the path looks like every other item route in this group.**
The spec says it outright: *"Use the `fileId` returned in the report's `reportFiles` array. A
`reportId` identifies the overall report and cannot be used with this endpoint."* One request can
produce **several** files, because a report covering a long range (up to 36 months of raw data) is
split by calendar month, so `reportFiles[]` is routinely longer than one entry and there is no
single "the" file for a report. Read the ids out of `show` first —
`wxcli usage-reports show <report-id> --fields 'reportFiles[].fileId' -o text` — and download each.
Note also that `create` returns exactly one `reportId` regardless of how many files it will yield,
so a successful create tells you nothing about how many downloads follow.

See also `reporting-analytics.md` for the Webex **Calling** side of usage measurement (CDR, queue
and auto-attendant statistics): if the question is about calls rather than Contact Center resource
consumption, this group is the wrong one and that doc is where to go.

---

## 15. External Data Updates (`external-data-updates`)

CLI group: `wxcli external-data-updates` (1 command)

Writes **numeric global-variable values onto one Contact Center task that has already ended** — a correction or enrichment after the fact. The spec's own summary: "Updates numeric global variable values associated with a completed Webex Contact Center task." It is one command against `PUT /v1/data/updateExternal` on the regional CC host. The body carries `orgId`, `updateType` (the only accepted value is `contact`), and a `data` array holding the task: its `id` (the **task** ID), its `startTimestamp` and `endTimestamp`, and up to 30 `globalVariables` as name/number pairs.

What this surface is **not**:

- **Not how a variable is set during a live interaction.** That happens inside the flow, or on the live task through `cc-tasks update` (`PATCH /v1/tasks/{taskId}`, [section 10](#10-tasks)) or the Agent Desktop SDK.
- **Not where a global variable is defined.** The variable must already exist; creating or editing definitions is `cc-global-vars` in [contact-center-core.md §20](contact-center-core.md#20-global-variables-cc-global-vars).
- **Not a read surface.** There is no GET here: it can change a value but cannot tell you what a task currently holds. Reading task data is the task and search surfaces in [section 10](#10-tasks) and [section 12](#12-search).
- **Not a bulk tool.** One task per request, and only a task that ended within the preceding two days.

**Unverified:** this section is read from `specs/webex-contact-center.json` and the generated module `external_data_updates.py`. No live call was made.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `update` | PUT `/v1/data/updateExternal` | Update global variables on one completed task |

### Key Parameters

- **`orgId`** (required, UUID) — must be the org the token belongs to (or the org in an `X-ORGANIZATION-ID` header, which wxcli does not send). Not auto-injected; see gotcha 5
- **`updateType`** (required) — `contact`
- **`data`** (required) — an array holding exactly one task record:
  - `id` — the task ID
  - `startTimestamp` / `endTimestamp` — ISO-8601 UTC strings in `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` form, e.g. `2026-09-22T10:30:00.000Z`
  - `globalVariables` — at most 30 entries of `{"name": ..., "value": <number>}`; integer, long and double values are accepted

### CLI Examples

```bash
# Print the request-body skeleton (exits before authenticating)
wxcli external-data-updates update --generate-json-body

# Set one numeric global variable on one task that ended in the last two days
wxcli external-data-updates update --json-body '{"orgId":"ORG_UUID","updateType":"contact","data":[{"id":"TASK_ID","startTimestamp":"2026-09-22T10:00:00.000Z","endTimestamp":"2026-09-22T10:30:00.000Z","globalVariables":[{"name":"UpSell","value":12}]}]}'

# The same body kept in a file
wxcli external-data-updates update --json-body file://task-update.json
```

### Raw HTTP

```bash
curl -X PUT "https://api.wxcc-us1.cisco.com/v1/data/updateExternal" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "orgId": "ORG_UUID",
        "updateType": "contact",
        "data": [
          {
            "id": "TASK_ID",
            "startTimestamp": "2026-09-22T10:00:00.000Z",
            "endTimestamp": "2026-09-22T10:30:00.000Z",
            "globalVariables": [{"name": "UpSell", "value": 12}]
          }
        ]
      }'
```

The spec also accepts an optional `TrackingId` request header for tracing a request in support cases.

### Gotchas

1. **A success response means "accepted for processing", not "applied".** The spec's success status is `202 Accepted`, described as: the request "passed configuration-level validation and was accepted for processing. Additional interaction-level validation may occur after acceptance." A problem with the task itself — wrong timestamps, a variable the task cannot take — can therefore fail after this call has already returned success. Confirm the change through the search surface ([section 12](#12-search)) rather than trusting the exit code. **Unverified:** spec wording; no request was observed through to completion.

2. **Timestamps are ISO-8601 strings, not the epoch milliseconds used almost everywhere else in Contact Center.** Both fields take `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` in UTC, and they identify the task together with its `id`, so they need to be the task's real start and end. Epoch values copied from a task or search response must be converted first. **Unverified:** the format is spec-stated; how closely the timestamps must match the task's own was not tested.

3. **Only a task that ended within the preceding two days can be updated.** The spec states it on the operation and again on `endTimestamp`. A correction for an older task is expected to be rejected with 400, so this is a near-real-time fix-up tool, not a way to backfill history. **Unverified:** spec wording; the exact cut-off behaviour was not tested.

4. **One task per request, at most 30 variables, and numbers only.** The spec says each request "may contain only one task", caps `globalVariables` at 30 entries, and defines a global variable here as numeric (integer, long or double). String or boolean variables cannot be written through this endpoint. Correcting many tasks means many calls, and the spec documents a rate limit of five requests per second per org (429 beyond it). **Unverified:** spec wording; the limits were not exercised.

5. **`orgId` goes in the body and wxcli does not fill it in.** Unlike the `/organization/{orgid}/…` commands, whose org ID is injected from config (gotcha 13), this command sends only what you put in the body. The spec declares `orgId` a UUID that must match the token's org, so use the bare UUID form, not the base64 Webex org ID — the same decoding described in [contact-center-core.md](contact-center-core.md#25-gotchas) gotcha #19. **Unverified:** read from the generated module and the spec's field format; the server's reaction to a base64 org ID was not observed.

6. **`data[]` has no flag, so a call made with flags alone cannot succeed.** `--org-id` and `--update-type` exist, but without `--json-body` the body contains no `data` key at all, and the spec marks `data` required — expect a 400, not a silent no-op. Start from `--generate-json-body`. **Unverified:** read from the generated body assembly; the 400 is the spec's documented response for missing required data, not an observed one.

7. **It is a Contact Center API even though nothing in its name or help says so.** The group has no `cc-` prefix and its `--help` reads "Manage Webex Calling external-data-updates", but the command calls the regional CC host (`api.wxcc-{region}.cisco.com`, set with `wxcli set-cc-region`), not `webexapis.com`. The spec names no specific OAuth scope for this operation and describes 403 as missing "required scopes or roles", so treat a 403 the way gotcha 11 describes. A `423 Locked` is different: the spec says the API is disabled by a feature flag or service kill switch, which no token change will fix. **Unverified:** base URL read from the generated module; scope and 423 behaviour are spec wording.

---

## Raw HTTP Endpoint Table

All 92 endpoints tabulated below, across 15 CLI groups. Regional base URL: `https://api.wxcc-{region}.cisco.com`.

### AI Assistant (1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/event` | Get AI suggestions |

### AI Feature (3)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/organization/{orgid}/ai-feature/{id}` | Get by ID |
| PATCH | `/organization/{orgid}/ai-feature/{id}` | Partial update |
| GET | `/organization/{orgid}/v2/ai-feature` | List |

### Auto CSAT (8)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/organization/{orgid}/auto-csat/{autoCsatId}/question` | Create question |
| POST | `/organization/{orgid}/auto-csat/{autoCsatId}/question/bulk` | Bulk save questions |
| GET | `/organization/{orgid}/auto-csat/{autoCsatId}/question/{id}` | Get question |
| DELETE | `/organization/{orgid}/auto-csat/{autoCsatId}/question/{id}` | Delete question |
| GET | `/organization/{orgid}/auto-csat/{id}` | Get Auto CSAT |
| PUT | `/organization/{orgid}/auto-csat/{id}` | Update Auto CSAT |
| GET | `/organization/{orgid}/v2/auto-csat` | List (v2) |
| GET | `/organization/{orgid}/v2/auto-csat/{autoCsatId}/question` | List questions (v2) |

### Generated Summaries (3)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/organization/{orgid}/generated-summaries/{id}` | Get by ID |
| PUT | `/organization/{orgid}/generated-summaries/{id}` | Update by ID |
| GET | `/organization/{orgid}/v2/generated-summaries` | List (v2) |

### Agent Summaries (2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generated-summaries/search` | Search summaries |
| POST | `/summary/list` | List summaries |

*Journey endpoints (41 commands) moved to [`contact-center-journey.md`](contact-center-journey.md).*

### Call Monitoring (7)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/monitor` | Create monitoring request |
| GET | `/v1/monitor/sessions` | Fetch sessions |
| DELETE | `/v1/monitor/{requestId}` | Delete request |
| POST | `/v1/monitor/{taskId}/bargeIn` | Barge-in |
| POST | `/v1/monitor/{taskId}/end` | End monitoring |
| POST | `/v1/monitor/{taskId}/hold` | Hold |
| POST | `/v1/monitor/{taskId}/unhold` | Unhold |

### Realtime (1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/realtime/subscribe` | Subscribe to realtime notifications |

### Subscriptions (12)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/event-types` | List event types (v1) |
| GET | `/v1/subscriptions` | List (v1) |
| POST | `/v1/subscriptions` | Register (v1) |
| GET | `/v1/subscriptions/{id}` | Get (v1) |
| DELETE | `/v1/subscriptions/{id}` | Delete (v1) |
| PATCH | `/v1/subscriptions/{id}` | Update (v1) |
| GET | `/v2/event-types` | List event types (v2) |
| GET | `/v2/subscriptions` | List (v2) |
| POST | `/v2/subscriptions` | Register (v2) |
| GET | `/v2/subscriptions/{id}` | Get (v2) |
| DELETE | `/v2/subscriptions/{id}` | Delete (v2) |
| PATCH | `/v2/subscriptions/{id}` | Update (v2) |

### Tasks (26)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/tasks` | Get tasks |
| POST | `/v1/tasks` | Create task (v1) |
| PATCH | `/v1/tasks/{taskId}` | Update task |
| POST | `/v1/tasks/{taskId}/accept` | Accept |
| POST | `/v1/tasks/{taskId}/assign` | Assign |
| POST | `/v1/tasks/{taskId}/conference/exit` | Exit conference |
| POST | `/v1/tasks/{taskId}/consult` | Consult |
| POST | `/v1/tasks/{taskId}/consult/accept` | Consult accept |
| POST | `/v1/tasks/{taskId}/consult/conference` | Consult conference |
| POST | `/v1/tasks/{taskId}/consult/end` | Consult end |
| POST | `/v1/tasks/{taskId}/consult/transfer` | Consult transfer |
| POST | `/v1/tasks/{taskId}/end` | End task |
| POST | `/v1/tasks/{taskId}/hold` | Hold |
| POST | `/v1/tasks/{taskId}/record/pause` | Pause recording |
| POST | `/v1/tasks/{taskId}/record/resume` | Resume recording |
| POST | `/v1/tasks/{taskId}/pause` | Pause the task itself |
| POST | `/v1/tasks/{taskId}/resume` | Resume the task itself |
| POST | `/v1/tasks/{taskId}/reject` | Reject |
| POST | `/v1/tasks/{taskId}/transfer` | Transfer |
| POST | `/v1/tasks/{taskId}/unhold` | Resume (unhold) |
| POST | `/v1/tasks/{taskId}/wrapup` | Wrap up |
| POST | `/v2/tasks` | Create task (v2) |
| POST | `/v2/tasks/{taskId}/messages` | Update (v2 messages) |
| POST | `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/accept` | Accept preview |
| POST | `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/remove` | Remove preview |
| POST | `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/skip` | Skip preview |

### Notifications (1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/notification/subscribe` | Subscribe |

### Search (1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search` | Search tasks |

### Search Metadata (1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/search/v2/meta` | Get search metadata |

### Address Book (19)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/organization/{orgid}/address-book` | List (v1) |
| POST | `/organization/{orgid}/address-book` | Create (v1) |
| GET | `/organization/{orgid}/address-book/bulk-export` | Bulk export |
| POST | `/organization/{orgid}/address-book/{addressBookId}/entry` | Create entry |
| POST | `/organization/{orgid}/address-book/{addressBookId}/entry/bulk` | Bulk save entries |
| GET | `/organization/{orgid}/address-book/{addressBookId}/entry/{id}` | Get entry |
| PUT | `/organization/{orgid}/address-book/{addressBookId}/entry/{id}` | Update entry |
| DELETE | `/organization/{orgid}/address-book/{addressBookId}/entry/{id}` | Delete entry |
| GET | `/organization/{orgid}/address-book/{id}` | Get (v1) |
| PUT | `/organization/{orgid}/address-book/{id}` | Update (v1) |
| DELETE | `/organization/{orgid}/address-book/{id}` | Delete (v1) |
| GET | `/organization/{orgid}/address-book/{id}/incoming-references` | References |
| GET | `/organization/{orgid}/v2/address-book` | List (v2) |
| GET | `/organization/{orgid}/v2/address-book/{addressBookId}/entry` | List entries (v2) |
| GET | `/organization/{orgid}/v3/address-book` | List (v3) |
| POST | `/organization/{orgid}/v3/address-book` | Create (v3) |
| GET | `/organization/{orgid}/v3/address-book/{id}` | Get (v3) |
| PUT | `/organization/{orgid}/v3/address-book/{id}` | Update (v3) |
| DELETE | `/organization/{orgid}/v3/address-book/{id}` | Delete (v3) |

### Usage Reports (6)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/usage-reports/resource-types` | Available resource types + data dates |
| POST | `/v1/usage-reports` | Create usage report (asynchronous) |
| GET | `/v1/usage-reports` | List usage reports |
| GET | `/v1/usage-reports/{reportId}` | Report details, incl. `reportFiles[]` |
| GET | `/v1/usage-reports/{fileId}/download` | Download one report file |
| DELETE | `/v1/usage-reports/{reportId}` | Delete report and file |

### External Data Updates (1)

| Method | Path | Description |
|--------|------|-------------|
| PUT | `/v1/data/updateExternal` | Update numeric global variables on one completed task |

---

## Gotchas

1. **JDS gotchas have moved to [`contact-center-journey.md`](contact-center-journey.md).** All JDS-specific gotchas (alias normalization, Publish API, event immutability, RSQL syntax, scopes, etc.) are in the journey doc's gotchas section.

2. **Tasks API is the primary agent interaction API.** It handles the full contact/call lifecycle: create, accept, hold, consult, conference, transfer, record, wrap up. This is the API that drives the agent desktop.

3. **The AI Assistant endpoint (POST `/event`) uses a generic path.** Easy to confuse with the JDS event ingestion endpoint (POST `/publish/v1/api/event`) — completely different path and purpose.

4. **Subscriptions have v1 and v2 variants.** v2 adds enhanced event types and requires a `resourceVersion` field (e.g., `"resourceVersion": "agent:2.0.0"`) when creating subscriptions. Use `list-event-types-v2` to see the full set of available events. **Breaking rename in v2:** `agent:state_change` (v1 event name) is renamed to `agent:channel_state_change` — update subscriptions and webhook handlers when migrating to v2. v1.0.0 agent events are deprecated and supported until December 16, 2026.

5. **Call monitoring uses `taskId` for most operations but `requestId` for delete.** The create-monitor endpoint returns a `requestId` which is needed to delete the monitoring session. The taskId-based endpoints (barge-in, hold, unhold, end) operate on the contact being monitored.

6. **Search endpoint uses POST (not GET).** The query criteria are passed in the request body, not as query parameters.

7. **Agent Summaries uses POST endpoints for searching.** Both `create` (search) and `create-list` (list) use POST — the search/filter criteria go in the request body.

8. **Auto CSAT has a two-level structure.** Auto CSAT configurations sit at the top level; mapped questions are nested under each config by `autoCsatId`. You must create the Auto CSAT config before adding questions.

9. **Address Book has a two-level structure with v1/v2/v3 API versions.** Address books contain entries. v1 provides full CRUD, v2 adds enhanced list/query, v3 adds further improvements. Entry CRUD uses the v1 path regardless of which version was used to create the address book.

10. **Notifications and Realtime are separate subscription mechanisms.** `cc-notification` (POST `/v1/notification/subscribe`) is push-based delivery. `cc-realtime` (POST `/v1/realtime/subscribe`) is for WebSocket/SSE streaming. `cc-subscriptions` manages durable webhook-style subscriptions. All three coexist and serve different consumption patterns.

11. **All CC APIs require CC-specific OAuth scopes.** Standard Webex admin tokens will not work. You need `cjp:config_read` and/or `cjp:config_write` scopes. JDS admin endpoints additionally need `cjds:admin_org_read`/`cjds:admin_org_write`. The CLI detects 403 errors and prints a scope tip.

12. **Regional base URL is required.** All CC API requests go to `https://api.wxcc-{region}.cisco.com`, not `https://webexapis.com`. Set the region with `wxcli set-cc-region <region>` (defaults to `us1`).

13. **`orgId` is auto-injected.** For endpoints under `/organization/{orgid}/`, the orgId path parameter is automatically resolved from the saved config or the authenticated user's org. No manual `--org-id` flag is needed.

14. **WXCC CloudEvents webhook envelope.** All CC webhook events follow CloudEvents 1.0:

    **v1 envelope fields:** `id` (UUID), `specversion` ("1.0"), `type` (event name), `source` (contains subscription ID), `comciscoorgid` (org ID), `datacontenttype` ("application/json"), `data` (event payload).

    **v2 envelope adds:** `comciscotimestamp` (UTC epoch ms). v2 subscriptions also add headers: `X-WebexCC-Timestamp` (epoch ms), `X-WebexCC-Webhook-Version`, `X-WebexCC-Signature` (HMAC-SHA256 hex).

    v1 subscriptions use `X-WebexCC-Signature` only.

15. **Complete webhook event type taxonomy (22 types).** The full set of supported types for subscriptions:
    - Agent (v1): `agent:login`, `agent:logout`, `agent:state_change`
    - Agent (v2): `agent:login`, `agent:logout`, `agent:channel_state_change`, `agent:channelType_state_change`
    - Capture: `capture:available`
    - Task: `task:new`, `task:connect`, `task:connected`, `task:parked`, `task:on-hold`, `task:hold-done`, `task:consulting`, `task:consult-done`, `task:conferencing`, `task:conference-done`, `task:conference-transferred`, `task:ended`, `task:failed`, `task:origin-updated`
    - Task message: `task-message:appended`, `task-message:append-failed`

    v2 event data fields — **`agent:channel_state_change`**: `agentId`, `currentState` (idle/available/ringing/not-responding/connected/on-hold/hold-done/consulting/conferencing/consult-done/conference-done/wrapup/wrapup-done), `channelId`, `channelType` (telephony/email/chat/social), `destination`, `queueId`, `taskId`, `createdTime` (epoch ms), `idleCodeId`, `wrapUpAuxCodeId`, `teamId`.

    **`agent:channelType_state_change`**: `agentId`, `currentState` (Available/Idle/Engaged/EngagedOther/WrapUp/Reserved/LoggedOut), `channelType`, `pendingIdleState` (boolean), `idleCodeName`, `teamId`, `createdTime`. Note: the `comciscotimestamp` CloudEvents envelope field is **only** present in `agent:channelType_state_change` events.

16. **Queue Statistics and Agent Statistics REST APIs reach EOL March 31, 2027.** Both are deprecated in favor of the GraphQL Search API. Same auth scopes apply (`cjp:config` or `cjp:config_read`). Migrate before the EOL date.

17. **Bulk export APIs deprecated April 2026.** The `/bulk-export` GET endpoints across 19 config resources (Address Book, Auxiliary Code, Business Hours, Desktop Layout, Skills, Teams, Users, and others) are deprecated. Use the corresponding list endpoints (`/v2/` or `/v3/` variants) instead. The `list-bulk-export` CLI commands for these resources will stop working after removal.

18. **`cc-search-metadata` answers "which fields", `cc-search` answers "which records".** They sit on
    adjacent paths (`GET /search/v2/meta` and `POST /search`) and both belong to the Search API, but
    only one returns data. `cc-search-metadata list` is a GET with no body and no required flags that
    describes the schema; `cc-search create` is a POST whose body carries the GraphQL query and
    mandatory `from`/`to` epoch bounds. If a search returns an error about an unknown or
    non-filterable field, check the metadata before rewriting the query — the metadata states per
    field whether it is `sortable`, has a `filter`, allows `groupBy`, and which `aggregation`
    operations it accepts. **Unverified:** read from the spec's schema and descriptions; no live call
    was made against `/search/v2/meta`.

19. **`cc-tasks create-pause` pauses the RECORDING; `create-pause-tasks` pauses the TASK.** Upstream
    added `POST /v1/tasks/{taskId}/pause` and `/resume` on 2026-09-21, beside the recording controls
    that have shipped for months on `/v1/tasks/{taskId}/record/pause` and `/record/resume`. The two
    pairs do different things to a live contact, and the shorter-looking name is the recording one,
    which is the opposite of what the spelling suggests. `create-pause`/`create-resume` were pinned
    to the recording endpoints at the 2026-09-21 spec sync so they did not silently move to the new
    task-level routes — the same class of silent retarget as known issue #18. The names to reach
    for: `create-pause`/`create-resume` when you mean recording (these mirror `task.pauseRecording()`
    in the agent SDK), `create-pause-tasks`/`create-resume-tasks` when you mean the task itself.
    **Unverified:** the task-level pair is read from the 2026-09-21 spec refresh; no live call was
    made against either route.

---

## See Also

- [Contact Center: Core](contact-center-core.md) — Agents, queues, teams, skills, desktop, configuration. Go to its §20 before calling `external-data-updates`: the global variable named in the body must already be defined there (`cc-global-vars`), and must be numeric. Go to its §21 when the request is for a supervisor monitoring **schedule** rather than the live session in §7 here
- [Contact Center: Journey](contact-center-journey.md) — JDS: workspaces, persons, identity, profile views, events
- [Contact Center: Routing](contact-center-routing.md) — Dial plans, campaigns, flows, audio, contacts
- [Contact Center: Agent Desktop SDK](contact-center-agent-sdk.md) — The `@webex/contact-center` JS SDK. The `cc-tasks` group documented here is the server-side counterpart to a live task in a custom desktop: `wxcli cc-tasks update` is `PATCH /v1/tasks/{taskId}`, the route that writes call variables on a task that is still live (for a task that has already ended, §15's `external-data-updates` writes numeric global variables instead), and `create-pause`/`create-resume` mirror `task.pauseRecording()`
- [Webhooks & Events](webhooks-events.md) — Webex platform webhooks (separate from CC subscriptions)
- [Reporting & Analytics](reporting-analytics.md) — Webex Calling CDR, queue stats, call quality
- [Authentication](authentication.md) — CC-specific OAuth scopes and region configuration
