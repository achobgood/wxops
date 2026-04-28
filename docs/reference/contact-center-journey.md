# Contact Center: Journey Data Service (JDS / CJDS)

Reference for the Webex Contact Center Customer Journey Data Service — identity resolution,
person profiles, profile view templates, journey event ingestion, and real-time streaming.
41 commands in the `cc-journey` CLI group spanning 7 functional areas.

> **Regional base URL:** `https://api.wxcc-{region}.cisco.com`
> **Auth:** `cjp:config_read` / `cjp:config_write` for most operations. JDS admin APIs
> (`/admin/v1/api/...`) additionally require `cjds:admin_org_read` / `cjds:admin_org_write`.
> **Set region:** `wxcli set-cc-region <region>` (defaults to us1)

**Important:** Journey workspaces are NOT Webex Calling workspaces. JDS workspaces organize
journey data, persons, templates, and actions. They have no relation to Webex Calling workspaces
that represent physical rooms/devices.

**Path families:**
- Admin API: `/admin/v1/api/...` — workspace, person, template, and action management
- Runtime API: `/v1/api/...` — live profile views, event streaming, identity operations
- Publish API: `/publish/v1/api/...` — event ingestion

These do NOT follow the `/organization/{orgid}/` pattern used by all other CC APIs.

## Sources

- OpenAPI spec: `specs/webex-contact-center.json`
- developer.webex.com Contact Center APIs

---

## Table of Contents

1. [Workspace Management](#1-workspace-management)
2. [Person and Identity Management](#2-person-and-identity-management)
3. [Profile View Templates](#3-profile-view-templates)
4. [Profile Views and Events](#4-profile-views-and-events)
5. [Journey Actions](#5-journey-actions)
6. [WXCC Subscription](#6-wxcc-subscription)
7. [Data Ingestion](#7-data-ingestion)
8. [Raw HTTP Endpoint Table](#8-raw-http-endpoint-table)
9. [Gotchas](#9-gotchas)
10. [See Also](#10-see-also)

---

## 1. Workspace Management

CLI group: `wxcli cc-journey` (5 commands)

JDS workspaces are the top-level container for all journey data. A workspace links to one or
more WXCC subscriptions that feed contact events into the journey stream automatically.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `list` | GET `/admin/v1/api/workspace` | Get all workspaces |
| `create-workspace` | POST `/admin/v1/api/workspace` | Create workspace |
| `show-workspace-id-api` | GET `/admin/v1/api/workspace/workspace-id/{workspaceId}` | Get workspace |
| `update-workspace-id` | PUT `/admin/v1/api/workspace/workspace-id/{workspaceId}` | Update workspace |
| `delete` | DELETE `/admin/v1/api/workspace/workspace-id/{workspaceId}` | Delete workspace |

```bash
# List all JDS workspaces
wxcli cc-journey list

# Create a workspace
wxcli cc-journey create-workspace --json-body '{"name": "Sales Journey"}'

# Get workspace details (includes wxccSubscriptionIds)
wxcli cc-journey show-workspace-id-api ws-abc-123
```

**Workspace response shape:**
```json
{
  "id": "65cfdcee870a2d0e4a9864b8",
  "name": "My JDS Workspace",
  "description": "...",
  "wxccSubscriptionIds": ["69ff3a55-612f-452f-80d2-884d6d248c9a"]
}
```

`wxccSubscriptionIds` lists the WXCC subscription UUIDs linked to this workspace. If empty,
no WXCC events flow in automatically — person records must be created manually or via the
Publish API.

---

## 2. Person and Identity Management

CLI group: `wxcli cc-journey` (10 commands)

Persons are the core identity objects in JDS. Each person has typed identity buckets (`phone`,
`email`, `temporaryId`, `customerId`, `socialId`) and a flattened `aliases` array used for
lookup and merge matching.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show-workspace-id-person` | GET `.../person/workspace-id/{workspaceId}` | List all persons |
| `create-workspace-id-person` | POST `.../person/workspace-id/{workspaceId}` | Create a person |
| `update-person-id-workspace-id` | PATCH `.../person/workspace-id/{wId}/person-id/{pId}` | Update person |
| `delete-person-id` | DELETE `.../person/workspace-id/{wId}/person-id/{pId}` | Delete person |
| `update-person-id-workspace-id-1` | PATCH `.../person/add-identities/workspace-id/{wId}/person-id/{pId}` | Add identities |
| `update` | PATCH `/v1/api/person/remove-identities/...` | Remove identities (runtime) |
| `update-person-id-workspace-id-2` | PATCH `.../person/remove-identities/workspace-id/{wId}/person-id/{pId}` | Remove identities (admin) |
| `show-aliases` | GET `.../person/workspace-id/{wId}/aliases/{aliases}` | Search by alias |
| `create-workspace-id-merge-identities` | POST `.../person/merge-identities/workspace-id/{wId}` | Merge aliases |
| `create-primary-person-id` | POST `.../person/merge/workspace-id/{wId}/primary-person-id/{pId}` | Merge to primary |

Admin paths are prefixed with `/admin/v1/api`.

```bash
# List all persons in a workspace
wxcli cc-journey show-workspace-id-person ws-abc-123 -o json

# Search by alias (use E.164 with + prefix for phone numbers)
wxcli cc-journey show-aliases ws-abc-123 "+19103915567" -o json

# Create a person manually
wxcli cc-journey create-workspace-id-person ws-abc-123 --json-body '{
  "firstName": "John", "lastName": "Doe",
  "identities": [{"type": "phone", "value": "+15551234567"}]
}'

# Delete a person by ID
wxcli cc-journey delete-person-id ws-abc-123 person-id-here

# Merge identities to a primary person
wxcli cc-journey create-primary-person-id ws-abc-123 person-001
```

**Person record shape:**
```json
{
  "id": "69efeb1d2fb1cb6e298ca0f8",
  "firstName": null,
  "lastName": null,
  "phone": ["+14403967184"],
  "email": [],
  "temporaryId": [],
  "customerId": [],
  "socialId": [],
  "aliases": ["+14403967184"],
  "organizationId": "b8410147-6104-42e8-9b93-639730d983ff",
  "workspaceId": "65cfdcee870a2d0e4a9864b8",
  "override": null,
  "createdAt": "2026-04-27T23:02:53.490Z",
  "createdBy": "journey-stream-profiles",
  "updatedAt": "2026-04-27T23:02:53.490Z",
  "updatedBy": "journey-stream-profiles"
}
```

---

## 3. Profile View Templates

CLI group: `wxcli cc-journey` (6 commands)

Profile View Templates define which journey data fields are surfaced in the agent desktop
Customer Journey widget. A template specifies the attributes and layout shown to agents
during an active contact.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show-workspace-id-profile-view-template` | GET `.../profile-view-template/workspace-id/{wId}` | List templates |
| `create-workspace-id-profile-view-template` | POST `.../profile-view-template/workspace-id/{wId}` | Create template |
| `show-template-id-workspace-id` | GET `.../profile-view-template/workspace-id/{wId}/template-id/{tId}` | Get by ID |
| `show-template-name-workspace-id` | GET `.../profile-view-template/workspace-id/{wId}/template-name/{name}` | Get by name |
| `update-template-id` | PUT `.../profile-view-template/workspace-id/{wId}/template-id/{tId}` | Update template |
| `delete-template-id` | DELETE `.../profile-view-template/workspace-id/{wId}/template-id/{tId}` | Delete template |

All paths are prefixed with `/admin/v1/api`.

```bash
# List all profile view templates
wxcli cc-journey show-workspace-id-profile-view-template ws-abc-123

# Get template by name
wxcli cc-journey show-template-name-workspace-id ws-abc-123 "Customer 360"

# Create a template
wxcli cc-journey create-workspace-id-profile-view-template ws-abc-123 --json-body '{
  "name": "Customer 360",
  "attributes": ["firstName", "lastName", "recentOrders"]
}'
```

---

## 4. Profile Views and Events

CLI group: `wxcli cc-journey` (9 commands)

Historic and streaming profile view endpoints plus journey event retrieval.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show` | GET `/admin/v1/api/progressive-profile-view/.../template-name/{name}` | Historic view by person + template name |
| `show-template-name-person-id` | GET `/v1/api/progressive-profile-view/.../person-id/{pId}/template-name/{name}` | Historic view (runtime) |
| `show-template-id-identity` | GET `/v1/api/progressive-profile-view/stream/.../identity/{id}/template-id/{tId}` | Stream views by template ID |
| `show-workspace-id-events` | GET `/v1/api/events/workspace-id/{wId}` | Historic journey events |

Additional profile view endpoints provide access by identity + template ID, identity + template name,
person + template ID, and streaming by template name. All follow the pattern:
`/v1/api/progressive-profile-view/[stream/]workspace-id/{wId}/{lookup-type}/{value}/template-{id|name}/{template}`

```bash
# Get historic profile view by person and template name
wxcli cc-journey show ws-abc-123 person-001 "Customer 360"

# Stream progressive profile views (SSE — long-lived connection)
wxcli cc-journey show-template-id-identity ws-abc-123 "+15551234567" tmpl-001

# Get all historic journey events for a workspace
wxcli cc-journey show-workspace-id-events ws-abc-123 -o json

# Filter events by type (RSQL syntax)
wxcli cc-journey show-workspace-id-events ws-abc-123 \
  --identity "+19103915567" \
  --filter "type=='custom:store_verified'" -o json
```

---

## 5. Journey Actions

CLI group: `wxcli cc-journey` (7 commands)

CLI group: `wxcli cc-journey` (7 commands)

Journey actions define automated responses triggered by journey events — webhooks, notifications,
or other integrations that fire when specific journey conditions are met.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show-workspace-id-journey-actions` | GET `.../journey-actions/workspace-id/{wId}` | Get all actions |
| `show-template-id-workspace-id-1` | GET `.../journey-actions/workspace-id/{wId}/template-id/{tId}` | Get actions for template |
| `create-template-id` | POST `.../journey-actions/workspace-id/{wId}/template-id/{tId}` | Create action |
| `show-action-name` | GET `.../journey-actions/.../action-name/{name}` | Get action by name |
| `show-action-id` | GET `.../journey-actions/.../action-id/{actionId}` | Get action by ID |
| `update-action-id` | PUT `.../journey-actions/.../action-id/{actionId}` | Update action |
| `delete-action-id` | DELETE `.../journey-actions/.../action-id/{actionId}` | Delete action |

All paths are prefixed with `/admin/v1/api`.

```bash
# List all journey actions
wxcli cc-journey show-workspace-id-journey-actions ws-abc-123

# Create an action
wxcli cc-journey create-template-id ws-abc-123 tmpl-001 --json-body '{
  "name": "Send Welcome Email",
  "type": "webhook",
  "config": {"url": "https://example.com/webhook"}
}'

# Get action by name
wxcli cc-journey show-action-name ws-abc-123 tmpl-001 "Send Welcome Email"
```

---

## 6. WXCC Subscription

CLI group: `wxcli cc-journey` (3 commands)

Manage the WXCC event subscription that feeds journey data from the contact center into JDS.
When a subscription is active, every WXCC contact event (`task:new`, `task:ended`, etc.) is
consumed by `journey-stream-profiles`, which creates or updates person records automatically.
A workspace with no subscription receives no automatic data — records must be created manually
or via the Publish API.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `show-workspace-id-wxcc-subscription` | GET `.../wxcc-subscription/workspace-id/{wId}` | Get subscription |
| `create` | POST `.../wxcc-subscription/workspace-id/{wId}` | Create subscription |
| `delete-workspace-id` | DELETE `.../wxcc-subscription/workspace-id/{wId}` | Delete subscription |

All paths are prefixed with `/admin/v1/api`.

```bash
# Check WXCC subscription status
wxcli cc-journey show-workspace-id-wxcc-subscription ws-abc-123

# Create WXCC subscription (links workspace to WXCC event stream)
wxcli cc-journey create ws-abc-123

# Delete WXCC subscription
wxcli cc-journey delete-workspace-id ws-abc-123
```

---

## 7. Data Ingestion

CLI group: `wxcli cc-journey` (1 command)

Post custom journey events from external systems, flows, or applications. Events follow the
CloudEvents 1.0 specification and are ingested asynchronously.

| CLI Command | HTTP | Description |
|-------------|------|-------------|
| `create-event` | POST `/publish/v1/api/event?workspaceId={wId}` | Post a journey event |

```bash
# Publish a custom journey event
wxcli cc-journey create-event --json-body '{
  "id": "unique-event-id",
  "specversion": "1.0",
  "type": "custom:store_verified",
  "source": "wxcc_flow",
  "identity": "+15551234567",
  "identitytype": "phone",
  "datacontenttype": "application/json",
  "data": {"event": "store_verified"}
}'
```

**Raw HTTP:**
```http
POST https://api.wxcc-us1.cisco.com/publish/v1/api/event?workspaceId={workspaceId}
Authorization: Bearer {cc_token}
Content-Type: application/json

{
  "id": "unique-event-id",
  "specversion": "1.0",
  "type": "custom:store_verified",
  "source": "wxcc_flow",
  "identity": "+15551234567",
  "identitytype": "phone",
  "datacontenttype": "application/json",
  "data": {"event": "store_verified"}
}
```

Returns `"Accepted for processing"` on success (202). Events are immutable once ingested.

---

## 8. Raw HTTP Endpoint Table

All JDS endpoints. Admin paths require `cjds:admin_org_read`/`cjds:admin_org_write`.

### Workspace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/v1/api/workspace` | List all workspaces |
| POST | `/admin/v1/api/workspace` | Create workspace |
| GET | `/admin/v1/api/workspace/workspace-id/{wId}` | Get workspace |
| PUT | `/admin/v1/api/workspace/workspace-id/{wId}` | Update workspace |
| DELETE | `/admin/v1/api/workspace/workspace-id/{wId}` | Delete workspace |

### Person

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/v1/api/person/workspace-id/{wId}` | List persons |
| POST | `/admin/v1/api/person/workspace-id/{wId}` | Create person |
| PATCH | `/admin/v1/api/person/workspace-id/{wId}/person-id/{pId}` | Update person |
| DELETE | `/admin/v1/api/person/workspace-id/{wId}/person-id/{pId}` | Delete person |
| GET | `/admin/v1/api/person/workspace-id/{wId}/aliases/{alias}` | Search by alias |
| PATCH | `/admin/v1/api/person/add-identities/workspace-id/{wId}/person-id/{pId}` | Add identities |
| PATCH | `/admin/v1/api/person/remove-identities/workspace-id/{wId}/person-id/{pId}` | Remove identities (admin) |
| PATCH | `/v1/api/person/remove-identities/workspace-id/{wId}/person-id/{pId}` | Remove identities (runtime) |
| POST | `/admin/v1/api/person/merge-identities/workspace-id/{wId}` | Merge aliases |
| POST | `/admin/v1/api/person/merge/workspace-id/{wId}/primary-person-id/{pId}` | Merge to primary |

### Profile View Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/v1/api/profile-view-template/workspace-id/{wId}` | List templates |
| POST | `/admin/v1/api/profile-view-template/workspace-id/{wId}` | Create template |
| GET | `/admin/v1/api/profile-view-template/workspace-id/{wId}/template-id/{tId}` | Get by ID |
| GET | `/admin/v1/api/profile-view-template/workspace-id/{wId}/template-name/{name}` | Get by name |
| PUT | `/admin/v1/api/profile-view-template/workspace-id/{wId}/template-id/{tId}` | Update |
| DELETE | `/admin/v1/api/profile-view-template/workspace-id/{wId}/template-id/{tId}` | Delete |

### Profile Views (Progressive)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/v1/api/progressive-profile-view/.../person-id/{pId}/template-name/{name}` | Historic view (person + name, admin) |
| GET | `/v1/api/progressive-profile-view/.../person-id/{pId}/template-name/{name}` | Historic view (person + name, runtime) |
| GET | `/v1/api/progressive-profile-view/.../person-id/{pId}/template-id/{tId}` | Historic view (person + template ID) |
| GET | `/v1/api/progressive-profile-view/.../identity/{id}/template-id/{tId}` | Historic view (identity + template ID) |
| GET | `/v1/api/progressive-profile-view/.../identity/{id}/template-name/{name}` | Historic view (identity + name) |
| GET | `/v1/api/progressive-profile-view/stream/.../identity/{id}/template-id/{tId}` | Stream views (template ID) |
| GET | `/v1/api/progressive-profile-view/stream/.../identity/{id}/template-name/{name}` | Stream views (template name) |

### Events

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/api/events/workspace-id/{wId}` | Historic events |
| GET | `/v1/api/events/stream/workspace-id/{wId}/identity/{identity}` | Stream events by identity |
| POST | `/publish/v1/api/event?workspaceId={wId}` | Post journey event |

### Journey Actions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/v1/api/journey-actions/workspace-id/{wId}` | Get all actions |
| GET | `/admin/v1/api/journey-actions/workspace-id/{wId}/template-id/{tId}` | Get for template |
| POST | `/admin/v1/api/journey-actions/workspace-id/{wId}/template-id/{tId}` | Create action |
| GET | `/admin/v1/api/journey-actions/.../template-id/{tId}/action-id/{aId}` | Get by ID |
| GET | `/admin/v1/api/journey-actions/.../template-id/{tId}/action-name/{name}` | Get by name |
| PUT | `/admin/v1/api/journey-actions/.../template-id/{tId}/action-id/{aId}` | Update |
| DELETE | `/admin/v1/api/journey-actions/.../template-id/{tId}/action-id/{aId}` | Delete |

### WXCC Subscription

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/v1/api/wxcc-subscription/workspace-id/{wId}` | Get subscription |
| POST | `/admin/v1/api/wxcc-subscription/workspace-id/{wId}` | Create subscription |
| DELETE | `/admin/v1/api/wxcc-subscription/workspace-id/{wId}` | Delete subscription |

---

## 9. Gotchas

1. **JDS APIs use completely different path patterns from the CC config API.** Three path families: `/admin/v1/api/` (admin management), `/v1/api/` (runtime queries and streaming), `/publish/v1/api/` (event ingestion). These do not follow the `/organization/{orgid}/` pattern used by all other CC APIs.

2. **JDS admin operations require separate `cjds:` scopes.** The standard `cjp:config_read`/`cjp:config_write` scopes do NOT grant access to JDS admin APIs (`/admin/v1/api/...`). You also need `cjds:admin_org_read` and/or `cjds:admin_org_write`. Without these, workspace and person management calls return 403.

3. **`task:new` is the event that triggers JDS person record creation.** When a caller first contacts WXCC, the platform fires `task:new`. `journey-stream-profiles` consumes this and creates the JDS person record using the caller's ANI in E.164 format. The record appears within seconds. At the exact moment `task:new` fires the record may not yet exist — but by the time a flow HTTP node queries JDS (a few seconds later), it will be present.

4. **WXCC writes ANI to JDS in E.164 format.** Phone numbers are stored as `+19103915567`, not `9103915567`. Alias lookups from a flow must pass the number with `+1` prefix or they will miss.

5. **Alias lookup strips `+` but does not normalize the country code.** `9103915567`, `19103915567`, and `+19103915567` are three distinct aliases — they will not cross-match. The `+` is stripped before matching, so `+19103915567` matches `19103915567` in `aliases`, but `9103915567` is a completely separate alias.

6. **`createdAt == updatedAt` signals a first-time caller.** A person record where both timestamps are equal and `createdBy` is `journey-stream-profiles` was just created by the current contact — this is their first interaction. A returning caller's record will have `updatedAt > createdAt` or prior events predating the current contact.

7. **Publish API requires `workspaceId` as a query parameter, not in the body.** POST `/publish/v1/api/event?workspaceId={workspaceId}`. The `JourneyCloudEventModel` body schema has no `workspaceId` field. Required body fields: `id`, `specversion`, `type`, `source`, `identity`, `identitytype`, `datacontenttype`, `data`.

8. **Events are immutable — no delete endpoint exists.** The Publish API is write-only. The events read endpoints are GET-only. Once an event is ingested it cannot be removed.

9. **Events filter uses RSQL syntax.** Pass `?filter=type=='custom:store_verified'` to filter by event type. A plain string returns `BAD_REQUEST`. Other filterable fields include `identityType`. See the [RSQL syntax reference](https://github.com/perplexhub/rsql-jpa-specification#rsql-syntax-reference).

10. **Journey streaming endpoints (SSE) are long-lived connections.** The CLI may time out — use `--debug` to see the raw SSE stream or use raw HTTP with an SSE-capable client.

11. **`wxcli cc-journey show-workspace-id-events` had a missing `/v1/` prefix bug.** Fixed in `src/wxcli/commands/cc_journey.py` lines 1138 and 1200. Both commands now correctly hit `/v1/api/events/...`.

12. **Flow Designer HTTP connector requires a full absolute URL.** Relative paths like `/publish/v1/api/event` return HTTP 500 "is not a valid HTTP URL". Always use `https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId=...`.

13. **For Flow Designer JDS patterns (returning caller detection, posting events from flows), see `contact-center-routing.md` gotchas #16–18.**

---

## 10. See Also

- [Contact Center: Analytics](contact-center-analytics.md) — AI features, monitoring, subscriptions, tasks, search
- [Contact Center: Routing](contact-center-routing.md) — Flow Designer JDS integration patterns (#16–18)
- [Contact Center: Core](contact-center-core.md) — Agents, queues, teams, skills
- [Authentication](authentication.md) — `cjp:` and `cjds:` OAuth scopes
