# Contact Center: AI, Analytics, Monitoring, and Events

Reference for Webex Contact Center AI features, customer journey analytics, call monitoring,
event subscriptions, and task management. Covers 13 CLI groups with 123 commands generated
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
14. [Raw HTTP Endpoint Table](#raw-http-endpoint-table)
15. [Gotchas](#gotchas)
16. [See Also](#see-also)

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

CLI group: `wxcli cc-agent-summaries` (2 commands)

Search and list agent interaction summaries. Both endpoints use POST (not GET) because
the query parameters are passed in the request body.

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create` | POST `/generated-summaries/search` | Search summaries |
| `create-list` | POST `/summary/list` | List summaries |

### Key Parameters

- `--json-body` — Search/filter criteria in the request body

### CLI Examples

```bash
# Search summaries
wxcli cc-agent-summaries create --json-body '{
  "filter": {"agentId": "agent-456", "from": "2026-03-01T00:00:00Z"}
}'

# List summaries
wxcli cc-agent-summaries create-list --json-body '{
  "agentId": "agent-456"
}'
```

### Raw HTTP

```
# Search summaries
POST https://api.wxcc-us1.cisco.com/generated-summaries/search
Authorization: Bearer {cc_token}
Content-Type: application/json

{"filter": {"agentId": "agent-456", "from": "2026-03-01T00:00:00Z"}}

# List summaries
POST https://api.wxcc-us1.cisco.com/summary/list
Authorization: Bearer {cc_token}
Content-Type: application/json

{"agentId": "agent-456"}
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

### Commands

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create-monitor` | POST `/v1/monitor` | Create monitoring request |
| `list` | GET `/v1/monitor/sessions` | Fetch monitoring sessions |
| `delete` | DELETE `/v1/monitor/{requestId}` | Delete monitoring request |
| `create-barge-in` | POST `/v1/monitor/{taskId}/bargeIn` | Barge-in to monitored call |
| `create-end` | POST `/v1/monitor/{taskId}/end` | End monitoring session |
| `create-hold` | POST `/v1/monitor/{taskId}/hold` | Hold monitoring request |
| `create` | POST `/v1/monitor/{taskId}/unhold` | Unhold monitoring request |

### Key Parameters

- `task-id` (positional) — Task ID of the contact to monitor (for barge-in, end, hold, unhold)
- `request-id` (positional) — Monitoring request ID (for delete)
- `--json-body` — Monitoring request configuration

### CLI Examples

```bash
# Create a monitoring session
wxcli cc-call-monitoring create-monitor --json-body '{
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
wxcli cc-call-monitoring create task-789

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

CLI group: `wxcli cc-tasks` (24 commands)

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
| `create-pause` | POST `/v1/tasks/{taskId}/record/pause` | Pause recording |
| `create-resume` | POST `/v1/tasks/{taskId}/record/resume` | Resume recording |
| `create-reject` | POST `/v1/tasks/{taskId}/reject` | Reject task |
| `create-transfer-tasks` | POST `/v1/tasks/{taskId}/transfer` | Transfer task |
| `create-unhold` | POST `/v1/tasks/{taskId}/unhold` | Resume (unhold) |
| `create-wrapup` | POST `/v1/tasks/{taskId}/wrapup` | Wrap up task |
| `create-tasks` | POST `/v2/tasks` | Create task (v2) |
| `create-messages` | POST `/v2/tasks/{taskId}/messages` | Update task (v2 messages) |
| `create-accept-preview-task` | POST `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/accept` | Accept preview task |
| `create-remove` | POST `/v1/dialer/campaign/{campaignId}/preview-task/{taskId}/remove` | Remove preview task |
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
wxcli cc-tasks list --channel-types telephony

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

# Preview dialer: accept/skip/remove
wxcli cc-tasks create-accept-preview-task campaign-001 task-789
wxcli cc-tasks create-skip campaign-001 task-789
wxcli cc-tasks create-remove campaign-001 task-789
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

CLI group: `wxcli cc-search` (1 command)

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
| `show` | GET `/organization/{orgid}/address-book/{id}` | Get address book (v1) |
| `update` | PUT `/organization/{orgid}/address-book/{id}` | Update address book (v1) |
| `delete` | DELETE `/organization/{orgid}/address-book/{id}` | Delete address book (v1) |
| `list-incoming-references` | GET `.../address-book/{id}/incoming-references` | Get references |
| `list-address-book-v2` | GET `/organization/{orgid}/v2/address-book` | List (v2) |
| `list-entry` | GET `.../v2/address-book/{addressBookId}/entry` | List entries (v2) |
| `show-entry` | GET `.../address-book/{addressBookId}/entry/{id}` | Get entry |
| `update-entry` | PUT `.../address-book/{addressBookId}/entry/{id}` | Update entry |
| `delete-entry` | DELETE `.../address-book/{addressBookId}/entry/{id}` | Delete entry |
| `list-address-book-v3` | GET `/organization/{orgid}/v3/address-book` | List (v3) |
| `create-address-book` | POST `/organization/{orgid}/v3/address-book` | Create (v3) |
| `show-address-book` | GET `/organization/{orgid}/v3/address-book/{id}` | Get (v3) |
| `update-address-book` | PUT `/organization/{orgid}/v3/address-book/{id}` | Update (v3) |
| `delete-address-book` | DELETE `/organization/{orgid}/v3/address-book/{id}` | Delete (v3) |

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
wxcli cc-address-book delete-entry ab-001 entry-001

# Check incoming references before deleting an address book
wxcli cc-address-book list-incoming-references ab-001
wxcli cc-address-book delete ab-001
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

## Raw HTTP Endpoint Table

All 122 endpoints across the 13 CLI groups. Regional base URL: `https://api.wxcc-{region}.cisco.com`.

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

### Tasks (24)

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

---

## See Also

- [Contact Center: Core](contact-center-core.md) — Agents, queues, teams, skills, desktop, configuration
- [Contact Center: Journey](contact-center-journey.md) — JDS: workspaces, persons, identity, profile views, events
- [Contact Center: Routing](contact-center-routing.md) — Dial plans, campaigns, flows, audio, contacts
- [Webhooks & Events](webhooks-events.md) — Webex platform webhooks (separate from CC subscriptions)
- [Reporting & Analytics](reporting-analytics.md) — Webex Calling CDR, queue stats, call quality
- [Authentication](authentication.md) — CC-specific OAuth scopes and region configuration
