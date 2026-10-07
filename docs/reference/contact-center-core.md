# Contact Center: Agents, Queues, Teams, and Configuration

Reference for Webex Contact Center agent management, queue routing, team assignment, skill-based routing, desktop configuration, and administrative entity management. Covers 24 CLI groups with 227 commands generated from the Contact Center OpenAPI spec.

## Sources

- OpenAPI spec: `specs/webex-contact-center.json`
- [Webex Contact Center API](https://developer.webex.com/docs/api/guides/wxcc-overview) -- Official API docs
- developer.webex.com Contact Center APIs

---

## API Base and Authentication

- **Base URL:** `https://api.wxcc-{region}.cisco.com` (NOT `webexapis.com`)
- **Regions:** `us1` (default), `eu1`, `eu2`, `anz1` (confirmed); `ca1`, `jp1`, `sg1` (plausible but not independently confirmed from public Webex developer documentation — verify against your org's actual token cluster value before use)
- **Set region:** `wxcli set-cc-region us1`
- **Scopes:** `cjp:config_read` (read operations), `cjp:config_write` (write operations)
- **orgId:** Auto-injected from saved config into the `{orgid}` path parameter. Do not pass it manually.

Two path families exist:

| Family | Pattern | Used by |
|--------|---------|---------|
| **Config API** | `/organization/{orgid}/...` | Most admin entities (queues, teams, skills, sites, etc.) |
| **Runtime API** | `/v1/...` and `/v2/...` | Agent state, statistics, queue stats |

---

## Table of Contents

1. [Agents (`cc-agents`)](#1-agents-cc-agents)
2. [Agent Greetings (`cc-agent-greetings`)](#2-agent-greetings-cc-agent-greetings)
3. [Agent Wellbeing (`cc-agent-wellbeing`)](#3-agent-wellbeing-cc-agent-wellbeing)
4. [Users (`cc-users`)](#4-users-cc-users)
5. [User Profiles (`cc-user-profiles`)](#5-user-profiles-cc-user-profiles)
6. [Queues (`cc-queue`)](#6-queues-cc-queue)
7. [Queue Statistics (`cc-queue-stats`)](#7-queue-statistics-cc-queue-stats)
8. [Entry Points (`cc-entry-point`)](#8-entry-points-cc-entry-point)
9. [Teams (`cc-team`)](#9-teams-cc-team)
10. [Skills (`cc-skill`)](#10-skills-cc-skill)
11. [Skill Profiles (`cc-skill-profile`)](#11-skill-profiles-cc-skill-profile)
12. [Multimedia Profiles (`cc-multimedia-profile`)](#12-multimedia-profiles-cc-multimedia-profile)
13. [Desktop Layouts (`cc-desktop-layout`)](#13-desktop-layouts-cc-desktop-layout)
14. [Desktop Profiles (`cc-desktop-profile`)](#14-desktop-profiles-cc-desktop-profile)
15. [Business Hours (`cc-business-hour`)](#15-business-hours-cc-business-hour)
16. [Holiday Lists (`cc-holiday-list`)](#16-holiday-lists-cc-holiday-list)
17. [Aux Codes (`cc-aux-code`)](#17-aux-codes-cc-aux-code)
18. [Work Types (`cc-work-types`)](#18-work-types-cc-work-types)
19. [Sites (`cc-site`)](#19-sites-cc-site)
20. [Global Variables (`cc-global-vars`)](#20-global-variables-cc-global-vars)
21. [Call Monitoring Schedules (`cc-monitoring-schedules`)](#21-call-monitoring-schedules-cc-monitoring-schedules)
22. [Organization Settings (`cc-org-settings`)](#22-organization-settings-cc-org-settings)
23. [Tenant Configuration (`cc-tenant-config`)](#23-tenant-configuration-cc-tenant-config)
24. [Common Patterns](#24-common-patterns)
25. [Gotchas](#25-gotchas)
26. [See Also](#26-see-also)

> **Note:** Agent summaries (`cc-agent-summaries`) are documented in [contact-center-analytics.md](contact-center-analytics.md) alongside the related AI and generated summary features.

---

## 1. Agents (`cc-agents`)

Runtime agent operations: login, logout, state changes, reload, buddy lists, activities, and statistics. These use the runtime path family (`/v1/agents/`, `/v2/agents/`), not the config API.

> **This group does NOT contain the agent roster.** Nothing under `cc-agents` answers "who are my
> agents?" — every command here is a runtime session or telemetry operation. **The roster is
> `wxcli cc-users list`** (verified live 2026-07-29: returns `firstName`, `lastName`, `email`,
> `ciUserId`, `contactCenterEnabled`, `siteId`, `teamIds`, `agentProfileId`, `skillProfileId`),
> and `wxcli cc-users list-with-user-profile` returns the same roster with each user's profile
> permissions expanded inline.
>
> This group deliberately has **no bare `list`**. `GET /v1/agents/activities` was named `list`
> until 2026-07-29, which made the obvious command for "list the agents" return an activity log
> with exit 0 and plausible records — a different question, answered silently. It is now
> `list-activities`; `list` still runs as a hidden alias so nothing scripted breaks.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/v1/agents/activities` | `list-activities` (alias: `list`) | Get Agent Activities — an event log, NOT the roster |
| POST | `/v1/agents/buddyList` | `create-buddy-list` | Buddy Agents List |
| POST | `/v1/agents/login` | `create` | Login (v1) |
| PUT | `/v1/agents/logout` | `update` | Logout |
| POST | `/v1/agents/reload` | `create-reload-agents` | Reload |
| PUT | `/v1/agents/session/state` | `update-state-session` | State Change |
| GET | `/v1/agents/statistics` | `list-statistics` | Get Agent Statistics |
| POST | `/v2/agents/login` | `create-login` | Login (v2) |
| PUT | `/v2/agents/logout` | `update-logout` | Logout (v2) |
| POST | `/v2/agents/reload` | `create-reload-agents-1` | Reload (v2) |
| PUT | `/v2/agents/session/state` | `update-state-session-1` | State Change (v2) |

### Key Parameters

- **Login:** Requires `dialNumber`; optional `teamId`, `isExtension`, `deviceType`, `deviceId`, `roles`
- **State Change:** Requires `state` (Available, Idle, etc.), `auxCodeId` (for idle codes)
- **Activities:** Supports `from`, `to` date filters, `agentId`, `state`
- **Statistics:** Supports `agentId`, `channelType`, `from`, `to`

### CLI Examples

```bash
# Log in an agent (v2)
wxcli cc-agents create-login --dial-number "1001" --team-id "..." --is-extension

# Change agent state to Available
wxcli cc-agents update-state-session-1 --json-body '{
  "agentId": "...",
  "state": "Available"
}'

# List the agent roster (this is NOT in cc-agents)
wxcli cc-users list -o json

# Get agent activities for a date range — an event log, not the roster
wxcli cc-agents list-activities --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z"

# Get agent statistics
wxcli cc-agents list-statistics --agent-ids "..." --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z"

# Log out agent (v2)
wxcli cc-agents update-logout --json-body '{"agentId": "..."}'
```

### Raw HTTP

```bash
# Login (v2)
curl -X POST "https://api.wxcc-us1.cisco.com/v2/agents/login" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agentId":"...","teamId":"...","channelName":"telephony","agentDn":"1001"}'

# State Change (v2)
curl -X PUT "https://api.wxcc-us1.cisco.com/v2/agents/session/state" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agentId":"...","state":"Available"}'

# Get Activities
curl "https://api.wxcc-us1.cisco.com/v1/agents/activities?from=2026-03-01T00:00:00Z&to=2026-03-28T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 2. Agent Greetings (`cc-agent-greetings`)

Manage agent personal greeting files. Supports three API versions (v1, v2, v3) with progressively enhanced features.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| POST | `/organization/{orgid}/agent-personal-greeting` | _(no CLI command)_ | Create (v1) |
| POST | `/organization/{orgid}/agent-personal-greeting/delete-reference` | `delete-references-agent` | Delete references of an agent from greeting files (hidden alias: `create`) |
| DELETE | `/organization/{orgid}/agent-personal-greeting/{id}` | `delete` | Delete (v1) |
| GET | `/organization/{orgid}/agent-personal-greeting/{id}` | `show` | Get by ID (v1) |
| PATCH | `/organization/{orgid}/agent-personal-greeting/{id}` | _(no CLI command)_ | Partial update (v1) |
| PUT | `/organization/{orgid}/agent-personal-greeting/{id}` | _(no CLI command)_ | Update (v1) |
| GET | `/organization/{orgid}/v2/agent-personal-greeting` | `list` | List all (v2) |
| POST | `/organization/{orgid}/v2/agent-personal-greeting` | _(no CLI command)_ | Create (v2) |
| DELETE | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | `delete-agent-personal-greeting` | Delete (v2) |
| GET | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | `show-agent-personal-greeting` | Get by ID (v2) |
| PATCH | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | _(no CLI command)_ | Partial update (v2) |
| PUT | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | _(no CLI command)_ | Update (v2) |
| GET | `/organization/{orgid}/v3/agent-personal-greeting` | `list-agent-personal-greeting` | List (v3) |

> **The short names are v1, not v2.** `show` and `delete` hit the **v1** greeting endpoints;
> the v2 equivalents are `show-agent-personal-greeting` and `delete-agent-personal-greeting`.
> There is **no create or update command** in this group at any version.
> `create` is a hidden alias for `delete-references-agent`, which **strips an agent's greeting
> references and prints `Deleted.`** -- it does not create anything.

### CLI Examples

```bash
# List all agent greetings (v2)
wxcli cc-agent-greetings list

# Get a specific greeting (v1)
wxcli cc-agent-greetings show "greeting-uuid"

# Get a specific greeting (v2)
wxcli cc-agent-greetings show-agent-personal-greeting "greeting-uuid"

# Delete a greeting (v1)
wxcli cc-agent-greetings delete "greeting-uuid"

# Delete a greeting (v2)
wxcli cc-agent-greetings delete-agent-personal-greeting "greeting-uuid"

# Strip an agent's references from greeting files (destructive -- prints "Deleted.")
wxcli cc-agent-greetings delete-references-agent --json-body '{"references": {}}'

# List greetings (v3 -- enhanced filtering)
wxcli cc-agent-greetings list-agent-personal-greeting
```

### Raw HTTP

```bash
# List greetings (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/agent-personal-greeting" \
  -H "Authorization: Bearer $TOKEN"

# Create greeting (v2)
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/agent-personal-greeting" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Welcome Greeting","type":"WELCOME","agentId":"..."}'
```

---

## 3. Agent Wellbeing (`cc-agent-wellbeing`)

> **Deprecation status unconfirmed.** Listed as deprecated April 2026 in internal tracking but this is not reflected in public documentation as of May 2026 — the feature appears active in the February 2025 Webex developer newsletter. Verify against the current API changelog before use. A consolidated `AI Feature` API (`wxcli cc-ai-feature`) exists as a potential successor.

Monitor and manage agent burnout detection. Mixes config paths (`/organization/{orgid}/agent-burnout/`) with runtime paths (`/agentburnout/`, no `/organization/{orgid}` segment).

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/agent-burnout/{id}` | `show` | Get Agent Burnout by ID |
| PUT | `/organization/{orgid}/agent-burnout/{id}` | `update` | Update Agent Burnout by ID |
| GET | `/organization/{orgid}/v2/agent-burnout` | `list` | List Agent Burnout (v2) |
| POST | `/agentburnout/action` | `create-action` | Record realtime burnout events |
| POST | `/agentburnout/subscribe` | `create` | Subscribe for realtime burnout events |

### CLI Examples

```bash
# List agent burnout resources (v2)
wxcli cc-agent-wellbeing list

# Get burnout config for a specific agent
wxcli cc-agent-wellbeing show "burnout-uuid"

# Subscribe for realtime burnout events
wxcli cc-agent-wellbeing create --json-body '{
  "agentId": "...",
  "subscriptionType": "BURNOUT"
}'

# Record a burnout event action
wxcli cc-agent-wellbeing create-action --json-body '{
  "agentId": "...",
  "action": "BREAK_TAKEN"
}'
```

### Raw HTTP

```bash
# List burnout resources (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/agent-burnout" \
  -H "Authorization: Bearer $TOKEN"

# Subscribe for burnout events
curl -X POST "https://api.wxcc-us1.cisco.com/v1/agentburnout/subscribe" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agentId":"...","subscriptionType":"BURNOUT"}'
```

---

## 4. Users (`cc-users`)

Contact Center user management. CC users are Webex users with CC-specific configuration (team assignment, skill profiles, multimedia profiles, etc.).

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/user` | `list` | List User(s) (v1) |
| GET | `/organization/{orgid}/user/by-call-monitoring-id/{id}` | `show` | List the users a call monitoring **schedule** covers — takes a schedule ID (§21), **not** a user ID; for one user use `show-user` |
| PATCH | `/organization/{orgid}/user/bulk` | `update` | Bulk partial update Users |
| GET | `/organization/{orgid}/user/bulk-export` | _(no CLI command)_ | Bulk export User(s) |
| GET | `/organization/{orgid}/user/by-ci-user-id/{id}` | `show-by-ci-user-id-organization` | Get User by CI User ID (v1) |
| POST | `/organization/{orgid}/user/fetch-by-skill-requirements` | `create` | Get agents matching skill requirements |
| POST | `/organization/{orgid}/user/fetch-user-details-by-ids` | `create-fetch-user-details-by-ids` | Get Users by provided IDs |
| GET | `/organization/{orgid}/user/with-user-profile` | `list-with-user-profile` | List Users with profile |
| GET | `/organization/{orgid}/user/with-user-profile/{id}` | `show-with-user-profile` | Get User with profile by ID |
| GET | `/organization/{orgid}/user/{id}` | `show-user` | Get User by ID |
| PATCH | `/organization/{orgid}/user/{id}` | _(no CLI command)_ | Partially update User by ID |
| PUT | `/organization/{orgid}/user/{id}` | `update-user` | Update User by ID |
| GET | `/organization/{orgid}/user/{id}/incoming-references` | `list-incoming-references` | List references for User |
| GET | `/organization/{orgid}/v2/user` | `list-user` | List User(s) (v2) |
| GET | `/organization/{orgid}/v2/user/by-ci-user-id/{id}` | `show-by-ci-user-id-v2` | Get User by CI User ID (v2) |
| PATCH | `/organization/{orgid}/user/bulk/update-dynamic-skill/{skillId}` | `update-dynamic-skill` | Bulk assign/unassign dynamic skill |
| GET | `/organization/{orgid}/user/by-dynamic-skill-id/{skillId}` | `show-by-dynamic-skill-id` | List users with a specific dynamic skill |
| PATCH | `/organization/{orgid}/user/{id}/reskill` | `update-reskill` | Reassign skill profiles/dynamic skills to a user |

### Key Parameters

- **List (v2):** Supports `page`, `pageSize`, `filter` (FIQL syntax), `attributes` (select fields)
- **Bulk update:** Accepts array of user objects with partial fields
- **Fetch by skill:** POST body with `skillRequirements` array
- **CI User ID:** The Webex Common Identity user ID (different from CC user ID)
- **Bulk update dynamic skill:** Takes `skillId` as path parameter. PATCH body with `items` array, each containing `itemIdentifier`, `item` (user/skill mapping), and `requestAction` (SAVE or DELETE)
- **By dynamic skill ID:** Takes `skillId` as path parameter. Supports `search` (filter by firstName, lastName, email, value), `page`, `pageSize`
- **Reskill:** Takes user `id` as path parameter. PATCH body with `skillProfileId` to assign a new skill profile, and `dynamicSkills` with `add`/`remove` arrays for individual skill changes

### CLI Examples

```bash
# List CC users (v2 -- enhanced filtering)
wxcli cc-users list-user

# Get a user with their profile
wxcli cc-users show-with-user-profile "user-uuid"

# Get a user by their Webex CI User ID
wxcli cc-users show-by-ci-user-id-v2 "ci-user-uuid"

# Find agents matching skill requirements
wxcli cc-users create --json-body '{
  "skillRequirements": [
    {"skillId": "...", "operator": "GE", "value": 5}
  ]
}'

# Bulk partial update users
wxcli cc-users update --json-body '[
  {"id": "user1-uuid", "teamId": "team-uuid"},
  {"id": "user2-uuid", "teamId": "team-uuid"}
]'

# List users with a specific dynamic skill
wxcli cc-users show-by-dynamic-skill-id "skill-uuid"

# Bulk assign a dynamic skill to users
wxcli cc-users update-dynamic-skill "skill-uuid" --json-body '{
  "items": [
    {"itemIdentifier": 1, "item": {"id": "user1-uuid"}, "requestAction": "SAVE"},
    {"itemIdentifier": 2, "item": {"id": "user2-uuid"}, "requestAction": "SAVE"}
  ]
}'

# Reskill an agent (change skill profile + add/remove dynamic skills)
wxcli cc-users update-reskill "user-uuid" --json-body '{
  "skillProfileId": "new-profile-uuid",
  "dynamicSkills": {
    "add": ["skill-uuid-1"],
    "remove": ["skill-uuid-2"]
  }
}'
```

### Raw HTTP

```bash
# List users (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/user?page=0&pageSize=50" \
  -H "Authorization: Bearer $TOKEN"

# Get user with profile
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/user/with-user-profile/$USER_ID" \
  -H "Authorization: Bearer $TOKEN"

# Find agents by skill requirements
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/user/fetch-by-skill-requirements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"skillRequirements":[{"skillId":"...","operator":"GE","value":5}]}'
```

---

## 5. User Profiles (`cc-user-profiles`)

User profiles define what a CC agent can do: access to queues, features, and settings. Three API versions exist (v1, v2, v3), but `wxcli` only exposes the v3 endpoints plus the v1 incoming-references lookup (`list`).

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/user-profile` | _(no CLI command)_ | List (v1) |
| POST | `/organization/{orgid}/user-profile/bulk` | _(no CLI command)_ | Bulk save (v1) |
| GET | `/organization/{orgid}/user-profile/bulk-export` | _(no CLI command)_ | Bulk export (v1) |
| POST | `/organization/{orgid}/user-profile/purge-inactive-entities` | _(no CLI command)_ | Purge inactive |
| GET | `/organization/{orgid}/user-profile/{id}` | _(no CLI command)_ | Get by ID (v1) |
| DELETE | `/organization/{orgid}/user-profile/{id}` | _(no CLI command)_ | Delete (v1) |
| PUT | `/organization/{orgid}/user-profile/{id}` | _(no CLI command)_ | Update (v1) |
| GET | `/organization/{orgid}/user-profile/{id}/incoming-references` | `list` | List references |
| GET | `/organization/{orgid}/v2/user-profile` | _(no CLI command)_ | List (v2) |
| GET | `/organization/{orgid}/v3/user-profile` | `list-user-profile` | List (v3) |
| POST | `/organization/{orgid}/v3/user-profile` | `create` | Create (v3) |
| POST | `/organization/{orgid}/v3/user-profile/bulk` | `create-bulk` | Bulk save (v3) |
| GET | `/organization/{orgid}/v3/user-profile/bulk-export` | _(no CLI command)_ | Bulk export (v3) |
| GET | `/organization/{orgid}/v3/user-profile/{id}` | `show` | Get by ID (v3) |
| DELETE | `/organization/{orgid}/v3/user-profile/{id}` | `delete` | Delete (v3) |
| PUT | `/organization/{orgid}/v3/user-profile/{id}` | `update` | Update (v3) |
| GET | `/organization/{orgid}/v3/user-profile/{id}/acl` | `list-acl` | Get ACL (v3) |

### Key Parameters

- **Create (v3):** Requires `name`, optional `description`, `accessRights`, `queues`, `wrapUpCodes`
- **ACL (v3):** Returns access control list for the profile -- which queues and features the profile grants access to
- **Purge:** Removes all soft-deleted/deactivated user profiles permanently

### CLI Examples

```bash
# List user profiles (v3)
wxcli cc-user-profiles list-user-profile

# Get a user profile by ID (v3)
wxcli cc-user-profiles show "profile-uuid"

# Create a user profile (v3)
wxcli cc-user-profiles create --json-body '{
  "name": "Standard Agent Profile",
  "description": "Default profile for voice agents",
  "accessRights": {"queues": ["queue-uuid-1", "queue-uuid-2"]}
}'

# Get profile ACL (v3)
wxcli cc-user-profiles list-acl "profile-uuid"

# Delete a user profile (v3)
wxcli cc-user-profiles delete "profile-uuid"
```

### Raw HTTP

```bash
# List profiles (v3)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v3/user-profile" \
  -H "Authorization: Bearer $TOKEN"

# Create profile (v3)
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v3/user-profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Standard Agent Profile","description":"Default profile for voice agents"}'

# Get ACL (v3)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v3/user-profile/$PROFILE_ID/acl" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 6. Queues (`cc-queue`)

Contact Service Queues route incoming contacts to agents based on routing strategy (skill-based, agent-based, or team-based). This is the largest CC config entity with 30 commands.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/contact-service-queue` | `list` | List (v1) |
| POST | `/organization/{orgid}/contact-service-queue` | _(no CLI command)_ | Create (v1) |
| POST | `/organization/{orgid}/contact-service-queue/bulk` | `create` | Bulk save |
| PATCH | `/organization/{orgid}/contact-service-queue/bulk` | `update` | Bulk partial update |
| GET | `/organization/{orgid}/contact-service-queue/bulk-export` | _(no CLI command)_ | Bulk export |
| GET | `/organization/{orgid}/contact-service-queue/by-skill-profile-id/{id}` | `show` | Get by skill profile ID |
| POST | `/organization/{orgid}/contact-service-queue/delete-reference` | `delete-reference` | Delete References |
| POST | `/organization/{orgid}/contact-service-queue/fetch-manually-assignable-queues` | `create-fetch-manually-assignable-queues` | Fetch assignable queues |
| POST | `/organization/{orgid}/contact-service-queue/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| POST | `/organization/{orgid}/contact-service-queue/v2/bulk` | `create-bulk` | Bulk save (v2) |
| GET | `/organization/{orgid}/contact-service-queue/{id}` | `show-contact-service-queue-organization` | Get by ID |
| DELETE | `/organization/{orgid}/contact-service-queue/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/contact-service-queue/{id}` | `update-contact-service-queue-organization` | Update |
| GET | `/organization/{orgid}/contact-service-queue/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/contact-service-queue` | `list-contact-service-queue-v2` | List (v2) |
| POST | `/organization/{orgid}/v2/contact-service-queue` | `create-contact-service-queue` | Create (v2) |
| GET | `/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/agent-based-queues` | `list-agent-based-queues` | Agent-based queues by user |
| GET | `/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/skill-based-queues` | `list-skill-based-queues` | Skill-based queues by user |
| GET | `/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/team-based-queues` | `list-team-based-queues` | Team-based queues by user |
| GET | `/organization/{orgid}/v2/contact-service-queue/{id}` | `show-contact-service-queue-v2` | Get by ID (v2) |
| PUT | `/organization/{orgid}/v2/contact-service-queue/{id}` | `update-contact-service-queue-v2` | Update (v2) |
| POST | `/organization/{orgid}/v2/contact-service-queue/{id}/reassign-agents` | `create-reassign-agents` | Reassign agents |
| GET | `/organization/{orgid}/v3/contact-service-queue` | `list-contact-service-queue-v3` | List (v3) |
| GET | `/organization/{orgid}/contact-service-queue/by-team-id/{id}/internal` | _(no CLI command)_ | Team CSQs by team ID (internal) |
| GET | `/organization/{orgid}/contact-service-queue/by-user-ci-id/{ciUserId}/internal` | _(no CLI command)_ | Agent CSQs by CI user ID (internal) |
| POST | `/organization/{orgid}/contact-service-queue/fetch-by-dynamic-skills-and-skillProfile` | `create-fetch-by-dynamic-skills-and-skill-profile` | Skill-based CSQs by dynamic skills + profile |
| POST | `/organization/{orgid}/contact-service-queue/fetch-by-userId-skillProfileId` | `create-fetch-by-user-id-skill-profile-id` | Skill-based CSQs by user ID + skill profile ID |
| GET | `/organization/{orgid}/contact-service-queue/skill-based-queues/by-ci-user-id/{id}/internal` | _(no CLI command)_ | Skill-based CSQs by CI user ID (internal) |
| POST | `/organization/{orgid}/v2/contact-service-queue/fetch-by-grouped-assistant-skill` | `create-fetch-by-grouped-assistant-skill` | Queue mapping summary by assistant skill (v2) |

### Key Parameters

- **Create:** Requires `name`, `channelType` (telephony, chat, email, social), `routingType` (SKILL_BASED, AGENT_BASED, TEAM_BASED)
- **Reassign agents:** POST with `agentIds` array and `action` (ADD or REMOVE) for agent-based queues
- **By user ID queries:** Return queues where a specific user is eligible to receive contacts
- **By skill profile ID:** Returns queues that use a specific skill profile for routing
- **By team ID (internal):** Returns team-based CSQs assigned to a specific team. Takes team ID as path parameter.
- **By CI user ID (internal):** Returns agent-based or skill-based CSQs for a Webex Common Identity user. Takes CI user ID as path parameter.
- **Fetch by dynamic skills + profile:** POST body with `skillProfileId`, `userId`, and `dynamicSkills` array (each with `skillId`, `textValue`, `booleanValue`, `proficiencyValue`, or `enumSkillValues`)
- **Fetch by grouped assistant skill:** POST body with `assistantSkillIds` array. Returns queue mapping summary (mapped queue count, last assigned time) grouped by assistant skill. Supports `page`/`pageSize` query params.

### CLI Examples

```bash
# List all queues (v3)
wxcli cc-queue list-contact-service-queue-v3

# List queues (v2)
wxcli cc-queue list-contact-service-queue-v2

# Create a queue (v2)
wxcli cc-queue create-contact-service-queue --json-body '{
  "name": "Sales Queue",
  "queueType": "INBOUND",
  "channelType": "TELEPHONY",
  "routingType": "SKILLS_BASED",
  "queueRoutingType": "SKILL_BASED",
  "checkAgentAvailability": true,
  "serviceLevelThreshold": 60,
  "maxActiveContacts": 100,
  "maxTimeInQueue": 3600,
  "active": true
}'

# Get a specific queue (v2)
wxcli cc-queue show-contact-service-queue-v2 "queue-uuid"

# Get queues where an agent is eligible (agent-based)
wxcli cc-queue list-agent-based-queues "user-uuid"

# Reassign agents to a queue
wxcli cc-queue create-reassign-agents "queue-uuid" --json-body '{
  "agentIds": ["agent1-uuid", "agent2-uuid"],
  "action": "ADD"
}'

# List all queues (v1)
wxcli cc-queue list

# Delete a queue
wxcli cc-queue delete "queue-uuid"

# List team-based queues for a user
wxcli cc-queue list-team-based-queues "user-uuid"

# List skill-based queues for a user
wxcli cc-queue list-skill-based-queues "user-uuid"

# Find skill-based queues matching dynamic skills + profile
wxcli cc-queue create-fetch-by-dynamic-skills-and-skill-profile --json-body '{
  "skillProfileId": "profile-uuid",
  "dynamicSkills": [
    {"skillId": "skill-uuid", "proficiencyValue": 5}
  ]
}'

# Find skill-based queues by user + skill profile
wxcli cc-queue create-fetch-by-user-id-skill-profile-id \
  --user-id "user-uuid" --skill-profile-id "profile-uuid"

# Get queue mapping summary grouped by assistant skill
wxcli cc-queue create-fetch-by-grouped-assistant-skill --json-body '{
  "assistantSkillIds": ["skill-uuid-1", "skill-uuid-2"]
}'
```

### Raw HTTP

```bash
# List queues (v3)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v3/contact-service-queue" \
  -H "Authorization: Bearer $TOKEN"

# Create queue (v2)
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/contact-service-queue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Sales Queue","channelType":"telephony","routingType":"SKILL_BASED"}'

# Reassign agents
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/contact-service-queue/$QUEUE_ID/reassign-agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agentIds":["agent1-uuid","agent2-uuid"],"action":"ADD"}'

# List team-based queues by team ID (internal)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/contact-service-queue/by-team-id/$TEAM_ID/internal" \
  -H "Authorization: Bearer $TOKEN"

# Fetch skill-based queues by dynamic skills + profile
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/contact-service-queue/fetch-by-dynamic-skills-and-skillProfile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","proficiencyValue":5}]}'

# Reskill an agent
curl -X PATCH "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/user/$USER_ID/reskill" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"skillProfileId":"new-profile-uuid","dynamicSkills":{"add":["skill-uuid-1"],"remove":["skill-uuid-2"]}}'

# List users by dynamic skill ID
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/user/by-dynamic-skill-id/$SKILL_ID?page=0&pageSize=50" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 7. Queue Statistics (`cc-queue-stats`)

Runtime queue statistics. Uses the runtime path family (`/v1/queues/`), separate from the queue config group.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/v1/queues/statistics` | `list` | Get Queue Statistics |

### Key Parameters

- **queueId:** Filter by specific queue
- **from / to:** Date range for statistics
- **channelType:** Filter by channel (telephony, chat, email, social)

### CLI Examples

```bash
# Get queue statistics
wxcli cc-queue-stats list --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z"

# Get statistics for a specific queue (--from/--to are required on every call)
wxcli cc-queue-stats list --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z" --queue-ids "queue-uuid"
```

### Raw HTTP

```bash
curl "https://api.wxcc-us1.cisco.com/v1/queues/statistics?from=2026-03-01T00:00:00Z&to=2026-03-28T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. Entry Points (`cc-entry-point`)

Entry points are the initial landing points for customer contacts. Each entry point is associated with a channel type and routes to a flow or queue.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/entry-point` | `list` | List |
| POST | `/organization/{orgid}/entry-point` | `create` | Create |
| POST | `/organization/{orgid}/entry-point/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/entry-point/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/entry-point/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/entry-point/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/entry-point/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/entry-point/{id}` | `update` | Update |
| GET | `/organization/{orgid}/entry-point/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/entry-point` | `list-entry-point` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `entryPointType` (INBOUND/OUTBOUND), `channelType` (TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL), `active`, `serviceLevelThreshold`, `maximumActiveContacts`
- **v2 list:** Enhanced filtering and pagination support

### CLI Examples

```bash
# List all entry points (v2)
wxcli cc-entry-point list-entry-point

# Create a telephony entry point
wxcli cc-entry-point create --json-body '{
  "name": "Main IVR",
  "entryPointType": "INBOUND",
  "channelType": "TELEPHONY",
  "active": true,
  "serviceLevelThreshold": 60,
  "maximumActiveContacts": 100
}'

# Get a specific entry point
wxcli cc-entry-point show "ep-uuid"

# Bulk export all entry points
wxcli cc-entry-point list-bulk-export --type INBOUND

# Delete an entry point
wxcli cc-entry-point delete "ep-uuid"

# List references (what uses this entry point)
wxcli cc-entry-point list-incoming-references "ep-uuid"
```

### Raw HTTP

```bash
# List entry points (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/entry-point" \
  -H "Authorization: Bearer $TOKEN"

# Create entry point
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/entry-point" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Main IVR","channelType":"telephony","serviceLevel":60}'
```

---

## 9. Teams (`cc-team`)

Teams group agents for routing and reporting. A team is assigned to a site, and agents are assigned to teams.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/team` | `list` | List Team(s) |
| POST | `/organization/{orgid}/team` | `create` | Create |
| POST | `/organization/{orgid}/team/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/team/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/team/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/team/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/team/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/team/{id}` | `update` | Update |
| GET | `/organization/{orgid}/team/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/team` | `list-team` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `siteId` (team must belong to a site)
- **Update:** Can reassign team to different site, rename, change capacity
- **References:** Shows which queues, routing strategies, and profiles reference this team

### CLI Examples

```bash
# List all teams (v2)
wxcli cc-team list-team

# Create a team
wxcli cc-team create --json-body '{
  "name": "Sales Team",
  "siteId": "site-uuid"
}'

# Get a specific team
wxcli cc-team show "team-uuid"

# Bulk save multiple teams
wxcli cc-team create-bulk --json-body '[
  {"name": "Support Team A", "siteId": "site-uuid"},
  {"name": "Support Team B", "siteId": "site-uuid"}
]'

# Delete a team
wxcli cc-team delete "team-uuid"

# See what references this team
wxcli cc-team list-incoming-references "team-uuid"
```

### Raw HTTP

```bash
# List teams (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/team" \
  -H "Authorization: Bearer $TOKEN"

# Create team
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/team" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Sales Team","siteId":"site-uuid"}'
```

---

## 10. Skills (`cc-skill`)

Skills are attributes assigned to agents for skill-based routing. Each skill has a type (text, proficiency, boolean, enum) and agents receive skill values through their skill profile.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/skill` | `list` | List Skill(s) |
| POST | `/organization/{orgid}/skill` | `create` | Create |
| POST | `/organization/{orgid}/skill/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/skill/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/skill/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/skill/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/skill/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/skill/{id}` | `update` | Update |
| GET | `/organization/{orgid}/skill/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/skill` | `list-skill` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `serviceLevel`, `skillType` (TEXT, PROFICIENCY, BOOLEAN, ENUM)
- **PROFICIENCY type:** Values 0-10, used for competency-based routing
- **BOOLEAN type:** True/false, used for capability flags (e.g., "speaks_spanish")
- **ENUM type:** Requires `enumValues` array defining the allowed values
- **TEXT type:** Free-form text value

### CLI Examples

```bash
# List all skills (v2)
wxcli cc-skill list-skill

# Create a proficiency skill
wxcli cc-skill create --json-body '{
  "name": "Product Knowledge",
  "skillType": "PROFICIENCY",
  "serviceLevel": 60
}'

# Create a boolean skill
wxcli cc-skill create --json-body '{
  "name": "Spanish Speaker",
  "skillType": "BOOLEAN",
  "serviceLevel": 60
}'

# Create an enum skill
wxcli cc-skill create --json-body '{
  "name": "Region",
  "skillType": "ENUM",
  "serviceLevel": 60,
  "enumValues": ["EAST", "WEST", "CENTRAL"]
}'

# Get a specific skill
wxcli cc-skill show "skill-uuid"

# Delete a skill
wxcli cc-skill delete "skill-uuid"

# Deactivate a skill (PUT replaces the resource, so resend name, type and threshold)
wxcli cc-skill update "skill-uuid" --name "Product Knowledge" --skill-type "Proficiency" \
  --service-level-threshold 60 --no-active
```

### Raw HTTP

```bash
# List skills (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/skill" \
  -H "Authorization: Bearer $TOKEN"

# Create skill
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/skill" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Product Knowledge","skillType":"PROFICIENCY","serviceLevel":60}'
```

---

## 11. Skill Profiles (`cc-skill-profile`)

Skill profiles bundle skill-value pairs and are assigned to agents. When a queue uses skill-based routing, it matches agent skill profiles against the required skill criteria.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/skill-profile` | `list` | List |
| POST | `/organization/{orgid}/skill-profile` | `create` | Create |
| POST | `/organization/{orgid}/skill-profile/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/skill-profile/bulk-export` | _(no CLI command)_ | Bulk export |
| GET | `/organization/{orgid}/skill-profile/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/skill-profile/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/skill-profile/{id}` | `update` | Update |
| GET | `/organization/{orgid}/skill-profile/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/skill-profile` | `list-skill-profile` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `skills` array with `{skillId, skillValue}` entries
- **Skill values:** Must match the skill's type (0-10 for proficiency, true/false for boolean, enum value for enum, text for text)

### CLI Examples

```bash
# List all skill profiles (v2)
wxcli cc-skill-profile list-skill-profile

# Create a skill profile
wxcli cc-skill-profile create --json-body '{
  "name": "Senior Sales Agent",
  "skills": [
    {"skillId": "product-knowledge-uuid", "skillValue": 8},
    {"skillId": "spanish-speaker-uuid", "skillValue": true},
    {"skillId": "region-uuid", "skillValue": "EAST"}
  ]
}'

# Get a specific skill profile
wxcli cc-skill-profile show "profile-uuid"

# Bulk export all skill profiles
wxcli cc-skill-profile list

# Delete a skill profile
wxcli cc-skill-profile delete "profile-uuid"
```

### Raw HTTP

```bash
# List skill profiles (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/skill-profile" \
  -H "Authorization: Bearer $TOKEN"

# Create skill profile
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/skill-profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Senior Sales Agent","skills":[{"skillId":"...","skillValue":8}]}'
```

---

## 12. Multimedia Profiles (`cc-multimedia-profile`)

Multimedia profiles define channel capacity for agents: how many concurrent contacts of each type (voice, chat, email, social) an agent can handle simultaneously.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/multimedia-profile` | `list` | List |
| POST | `/organization/{orgid}/multimedia-profile` | `create` | Create |
| POST | `/organization/{orgid}/multimedia-profile/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/multimedia-profile/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/multimedia-profile/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/multimedia-profile/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/multimedia-profile/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/multimedia-profile/{id}` | `update` | Update |
| GET | `/organization/{orgid}/multimedia-profile/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/multimedia-profile` | `list-multimedia-profile` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, channel capacities (`telephony`, `chat`, `email`, `social` counts)
- **Blended mode:** When set, agent can handle contacts across multiple channels simultaneously

### CLI Examples

```bash
# List multimedia profiles (v2)
wxcli cc-multimedia-profile list-multimedia-profile

# Create a multimedia profile
wxcli cc-multimedia-profile create --json-body '{
  "name": "Voice Only",
  "telephony": 1,
  "chat": 0,
  "email": 0,
  "social": 0,
  "active": true,
  "blendingModeEnabled": false,
  "blendingMode": "EXCLUSIVE"
}'

# Create a blended profile (voice + chat)
wxcli cc-multimedia-profile create --json-body '{
  "name": "Blended Agent",
  "telephony": 1,
  "chat": 3,
  "email": 5,
  "social": 2,
  "active": true,
  "blendingModeEnabled": true,
  "blendingMode": "BLENDED"
}'

# Get a specific profile
wxcli cc-multimedia-profile show "mm-profile-uuid"

# Delete a profile
wxcli cc-multimedia-profile delete "mm-profile-uuid"
```

### Raw HTTP

```bash
# List multimedia profiles (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/multimedia-profile" \
  -H "Authorization: Bearer $TOKEN"

# Create multimedia profile
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/multimedia-profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Voice Only","telephony":1,"chat":0,"email":0,"social":0}'
```

---

## 13. Desktop Layouts (`cc-desktop-layout`)

Desktop layouts define the Agent Desktop UI: widget placement, header, navigation, and custom components. Layouts are JSON objects that the desktop application renders.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| POST | `/organization/{orgid}/desktop-layout` | `create` | Create |
| POST | `/organization/{orgid}/desktop-layout/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/desktop-layout/bulk-export` | _(no CLI command)_ | Bulk export |
| POST | `/organization/{orgid}/desktop-layout/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/desktop-layout/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/desktop-layout/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/desktop-layout/{id}` | `update` | Update |
| GET | `/organization/{orgid}/desktop-layout/{id}/incoming-references` | `list` | List references |
| GET | `/organization/{orgid}/v2/desktop-layout` | `list-desktop-layout` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `editedBy`, `jsonFileName`, `jsonFileContent` (the layout JSON as a string), `global`, `status`, `defaultJsonModified`, `validated`
- **Layout JSON:** Defines widget areas, header, navigation panel, and auxiliary info panel
- **Update:** PUT replaces the entire layout -- GET first, modify, then PUT back

### CLI Examples

```bash
# List desktop layouts (v2)
wxcli cc-desktop-layout list-desktop-layout

# Create a desktop layout
wxcli cc-desktop-layout create --json-body '{
  "name": "Custom Sales Layout",
  "editedBy": "admin@example.com",
  "jsonFileName": "sales-layout.json",
  "jsonFileContent": "{\"header\":{},\"navigation\":{},\"panel\":{}}",
  "global": false,
  "status": true,
  "defaultJsonModified": true,
  "validated": true
}'

# Get a specific layout
wxcli cc-desktop-layout show "layout-uuid"

# Delete a layout
wxcli cc-desktop-layout delete "layout-uuid"
```

### Raw HTTP

```bash
# List layouts (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/desktop-layout" \
  -H "Authorization: Bearer $TOKEN"

# Create layout
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/desktop-layout" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Custom Sales Layout","desktopLayoutJson":"{}"}'
```

---

## 14. Desktop Profiles (`cc-desktop-profile`)

Desktop profiles (API path: `agent-profile`) control agent desktop behavior: which layout to use, dial number settings, agent-available options, buddy team access, and feature toggles.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/agent-profile` | `list` | List |
| POST | `/organization/{orgid}/agent-profile` | `create` | Create |
| POST | `/organization/{orgid}/agent-profile/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/agent-profile/bulk-export` | _(no CLI command)_ | Bulk export |
| POST | `/organization/{orgid}/agent-profile/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/agent-profile/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/agent-profile/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/agent-profile/{id}` | `update` | Update |
| GET | `/organization/{orgid}/agent-profile/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/agent-profile` | `list-agent-profile` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `desktopLayoutId`, optional `dialNumberSettings`, `agentAvailableOptions`, `loginVoiceOptions`
- **Desktop layout link:** The profile references a desktop layout by ID
- **Buddy teams:** Configure which teams an agent can see and consult/transfer to
- **`loginVoiceOptions`** — array of `AGENT_DN` | `EXTENSION` | `BROWSER` (`AgentProfileDTO` in `specs/webex-contact-center.json`). This is the **gate on browser/WebRTC audio**: it is what an agent's `Profile.loginVoiceOptions` reads back as, and `stationLogin({loginOption:'BROWSER'})` fails for an agent whose profile omits `BROWSER` even when everything else is correct. `dialNumberSettings` and `agentAvailableOptions` are *not* this field — do not read either one to decide whether browser audio is available. See [contact-center-agent-sdk.md](contact-center-agent-sdk.md) §1.

### CLI Examples

```bash
# List desktop profiles (v2)
wxcli cc-desktop-profile list-agent-profile

# Create a desktop profile
wxcli cc-desktop-profile create --json-body '{
  "name": "Sales Desktop Profile",
  "desktopLayoutId": "layout-uuid",
  "dialNumberSettings": {"agentDN": true, "otherDN": false}
}'

# Get a specific profile
wxcli cc-desktop-profile show "profile-uuid"

# Delete a profile
wxcli cc-desktop-profile delete "profile-uuid"
```

### Raw HTTP

```bash
# List desktop profiles (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/agent-profile" \
  -H "Authorization: Bearer $TOKEN"

# Create desktop profile
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/agent-profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Sales Desktop Profile","desktopLayoutId":"layout-uuid"}'
```

---

## 15. Business Hours (`cc-business-hour`)

Business hours define when the contact center is open. Entry points and routing strategies reference business hours to determine whether to apply business-hours or after-hours treatment.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/business-hours` | `list` | List |
| POST | `/organization/{orgid}/business-hours` | `create` | Create |
| POST | `/organization/{orgid}/business-hours/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/business-hours/bulk-export` | `list-bulk-export` | Bulk export |
| GET | `/organization/{orgid}/business-hours/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/business-hours/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/business-hours/{id}` | `update` | Update |
| GET | `/organization/{orgid}/business-hours/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/business-hours` | `list-business-hours` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `timezone`, `businessHours` (array of day/time entries)
- **Business hours structure:** Each entry defines a day of week, start time, and end time
- **Timezone:** Important for multi-region deployments; hours are evaluated in the configured timezone

### CLI Examples

```bash
# List business hours (v2)
wxcli cc-business-hour list-business-hours

# Create business hours
wxcli cc-business-hour create --json-body '{
  "name": "US East Business Hours",
  "timezone": "America/New_York",
  "businessHours": [
    {"day": "MONDAY", "startTime": "08:00", "endTime": "17:00"},
    {"day": "TUESDAY", "startTime": "08:00", "endTime": "17:00"},
    {"day": "WEDNESDAY", "startTime": "08:00", "endTime": "17:00"},
    {"day": "THURSDAY", "startTime": "08:00", "endTime": "17:00"},
    {"day": "FRIDAY", "startTime": "08:00", "endTime": "17:00"}
  ]
}'

# Get specific business hours
wxcli cc-business-hour show "bh-uuid"

# Delete business hours
wxcli cc-business-hour delete "bh-uuid"
```

### Raw HTTP

```bash
# List business hours (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/business-hours" \
  -H "Authorization: Bearer $TOKEN"

# Create business hours
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/business-hours" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"US East Business Hours","timezone":"America/New_York","businessHours":[{"day":"MONDAY","startTime":"08:00","endTime":"17:00"}]}'
```

---

## 16. Holiday Lists (`cc-holiday-list`)

Holiday lists define dates when the contact center applies holiday treatment instead of normal business hours routing.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/holiday-list` | `list` | List |
| POST | `/organization/{orgid}/holiday-list` | `create` | Create |
| POST | `/organization/{orgid}/holiday-list/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/holiday-list/bulk-export` | `list-bulk-export` | Bulk export |
| GET | `/organization/{orgid}/holiday-list/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/holiday-list/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/holiday-list/{id}` | `update` | Update |
| GET | `/organization/{orgid}/holiday-list/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/holiday-list` | `list-holiday-list` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `holidays` array with `{name, date}` entries
- **Date format:** `YYYY-MM-DD`
- **Recurring:** Some implementations support `recurring: true` for annual holidays

### CLI Examples

```bash
# List holiday lists (v2)
wxcli cc-holiday-list list-holiday-list

# Create a holiday list
wxcli cc-holiday-list create --json-body '{
  "name": "US Federal Holidays 2026",
  "holidays": [
    {"name": "New Year", "date": "2026-01-01"},
    {"name": "MLK Day", "date": "2026-01-19"},
    {"name": "Presidents Day", "date": "2026-02-16"},
    {"name": "Memorial Day", "date": "2026-05-25"},
    {"name": "Independence Day", "date": "2026-07-04"},
    {"name": "Labor Day", "date": "2026-09-07"},
    {"name": "Thanksgiving", "date": "2026-11-26"},
    {"name": "Christmas", "date": "2026-12-25"}
  ]
}'

# Get a specific holiday list
wxcli cc-holiday-list show "hl-uuid"

# Delete a holiday list
wxcli cc-holiday-list delete "hl-uuid"
```

### Raw HTTP

```bash
# List holiday lists (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/holiday-list" \
  -H "Authorization: Bearer $TOKEN"

# Create holiday list
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/holiday-list" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"US Federal Holidays 2026","holidays":[{"name":"New Year","date":"2026-01-01"}]}'
```

---

## 17. Aux Codes (`cc-aux-code`)

Auxiliary (idle/wrap-up) codes categorize agent non-available time. When an agent goes idle or enters wrap-up, they select an aux code to indicate why (e.g., break, lunch, training, after-call work).

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/auxiliary-code` | `list` | List |
| POST | `/organization/{orgid}/auxiliary-code` | `create` | Create |
| POST | `/organization/{orgid}/auxiliary-code/bulk` | `create-bulk` | Bulk save |
| PATCH | `/organization/{orgid}/auxiliary-code/bulk` | `update` | Bulk partial update |
| GET | `/organization/{orgid}/auxiliary-code/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/auxiliary-code/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/auxiliary-code/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/auxiliary-code/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/auxiliary-code/{id}` | `update-auxiliary-code` | Update |
| GET | `/organization/{orgid}/auxiliary-code/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/auxiliary-code` | `list-auxiliary-code` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `defaultCode` (boolean), `active`, `workTypeId`, `workTypeCode` (IDLE_CODE or WRAP_UP_CODE)
- **Bulk partial update:** PATCH with array of partial updates -- only specified fields are changed
- **Default code:** One idle code and one wrap-up code can be marked as default

### CLI Examples

```bash
# List aux codes (v2)
wxcli cc-aux-code list-auxiliary-code

# Create an idle code
wxcli cc-aux-code create --json-body '{
  "name": "Lunch Break",
  "workTypeCode": "IDLE_CODE",
  "workTypeId": "work-type-uuid",
  "defaultCode": false,
  "active": true
}'

# Create a wrap-up code
wxcli cc-aux-code create --json-body '{
  "name": "Follow-up Required",
  "workTypeCode": "WRAP_UP_CODE",
  "workTypeId": "work-type-uuid",
  "defaultCode": false,
  "active": true
}'

# Bulk partial update
wxcli cc-aux-code update --json-body '[
  {"id": "code1-uuid", "isActive": false},
  {"id": "code2-uuid", "name": "Extended Break"}
]'

# Delete an aux code
wxcli cc-aux-code delete "code-uuid"
```

### Raw HTTP

```bash
# List aux codes (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/auxiliary-code" \
  -H "Authorization: Bearer $TOKEN"

# Create idle code
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/auxiliary-code" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Lunch Break","codeType":"IDLE_CODE","defaultCode":false,"isActive":true}'
```

---

## 18. Work Types (`cc-work-types`)

Work types categorize agent activities for reporting. They are referenced in aux codes and wrap-up configurations.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| POST | `/organization/{orgid}/work-type` | `create` | Create |
| POST | `/organization/{orgid}/work-type/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/work-type/bulk-export` | `list` | Bulk export |
| POST | `/organization/{orgid}/work-type/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/work-type/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/work-type/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/work-type/{id}` | `update` | Update |
| GET | `/organization/{orgid}/work-type/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/work-type` | `list-work-type` | List (v2) |

### CLI Examples

```bash
# List work types (v2)
wxcli cc-work-types list-work-type

# Create a work type
wxcli cc-work-types create --json-body '{
  "name": "Outbound Campaign",
  "description": "Outbound dialing work"
}'

# Get a specific work type
wxcli cc-work-types show "wt-uuid"

# Delete a work type
wxcli cc-work-types delete "wt-uuid"
```

### Raw HTTP

```bash
# List work types (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/work-type" \
  -H "Authorization: Bearer $TOKEN"

# Create work type
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/work-type" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Outbound Campaign","description":"Outbound dialing work"}'
```

---

## 19. Sites (`cc-site`)

Sites represent physical or logical locations in the contact center. Teams are assigned to sites, providing geographic grouping for agents and reporting.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/site` | `list` | List Site(s) |
| POST | `/organization/{orgid}/site` | `create` | Create |
| POST | `/organization/{orgid}/site/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/site/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/site/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/site/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/site/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/site/{id}` | `update` | Update |
| GET | `/organization/{orgid}/site/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/site` | `list-site` | List (v2) |

### Key Parameters

- **Create:** Requires `name`
- **Dependencies:** Teams reference sites via `siteId`. Delete all teams from a site before deleting the site.

### CLI Examples

```bash
# List sites (v2)
wxcli cc-site list-site

# Create a site
wxcli cc-site create --json-body '{"name": "US East Coast"}'

# Get a specific site
wxcli cc-site show "site-uuid"

# Check what references this site
wxcli cc-site list-incoming-references "site-uuid"

# Delete a site (must have no team references)
wxcli cc-site delete "site-uuid"
```

### Raw HTTP

```bash
# List sites (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/site" \
  -H "Authorization: Bearer $TOKEN"

# Create site
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/site" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"US East Coast"}'
```

---

## 20. Global Variables (`cc-global-vars`)

Global variables (CAD variables -- Customer Activity Data) store key-value data that flows use for routing decisions, screen pops, and reporting. They are passed through the contact's lifecycle.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| POST | `/organization/{orgid}/cad-variable` | `create` | Create |
| POST | `/organization/{orgid}/cad-variable/bulk` | `create-bulk` | Bulk save |
| GET | `/organization/{orgid}/cad-variable/bulk-export` | `list` | Bulk export |
| POST | `/organization/{orgid}/cad-variable/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/cad-variable/reportable-count` | `list-reportable-count` | Get reportable count |
| GET | `/organization/{orgid}/cad-variable/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/cad-variable/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/cad-variable/{id}` | `update` | Update |
| GET | `/organization/{orgid}/cad-variable/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/cad-variable` | `list-cad-variable` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `type` (STRING, INTEGER, BOOLEAN, DECIMAL, DATE, DATETIME), optional `defaultValue`
- **Reportable:** Variables marked as reportable appear in CC analytics. There is a maximum reportable count -- check with `list-reportable-count`.
- **Agent viewable/editable:** Controls whether agents see and can modify the variable on the desktop

### CLI Examples

```bash
# List global variables (v2)
wxcli cc-global-vars list-cad-variable

# Check how many reportable variables remain
wxcli cc-global-vars list-reportable-count

# Create a global variable
wxcli cc-global-vars create --json-body '{
  "name": "CustomerTier",
  "type": "STRING",
  "defaultValue": "Standard",
  "reportable": true,
  "agentViewable": true,
  "agentEditable": false
}'

# Get a specific variable
wxcli cc-global-vars show "var-uuid"

# Delete a variable
wxcli cc-global-vars delete "var-uuid"
```

### Raw HTTP

```bash
# List global variables (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/cad-variable" \
  -H "Authorization: Bearer $TOKEN"

# Get reportable count
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/cad-variable/reportable-count" \
  -H "Authorization: Bearer $TOKEN"

# Create variable
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/cad-variable" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"CustomerTier","type":"STRING","defaultValue":"Standard","reportable":true}'
```

---

## 21. Call Monitoring Schedules (`cc-monitoring-schedules`)

A call monitoring schedule is a **stored, supervisor-owned plan** for monitoring: a name, a time window (`startTimestamp`/`endTimestamp` in epoch milliseconds, UTC), a `timezone`, an optional weekly `recurrence` on `daysOfWeek`, the teams and contact service queues it covers, which agents it covers (`agentsAccessType` `ALL`, or `SPECIFIC` with an `agents` list), the supervisor who owns it (`userId`), and a `paused` flag. Upstream tags it "Call Monitoring Request"; the paths are `/organization/{orgid}/call-monitoring`.

This is **not** live monitoring. Starting a silent-monitor session on a contact that is in progress, barging in, holding, or ending a session is `cc-call-monitoring` (runtime paths under `/v1/monitor`), documented in [contact-center-analytics.md §7](contact-center-analytics.md#7-call-monitoring). Creating a schedule here does not attach a supervisor to any call, and deleting one does not end a session that is already running. It is also **not** the Webex Calling person-level monitoring (busy-lamp) setting, which belongs to the `manage-call-settings` skill.

**Unverified:** everything in this section is read from `specs/webex-contact-center.json` and the generated module `cc_monitoring_schedules.py`. No live call was made, and the spec does not say how — or whether — a schedule causes the platform to start monitoring sessions on its own.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| POST | `/organization/{orgid}/call-monitoring` | `create` | Create a schedule |
| POST | `/organization/{orgid}/call-monitoring/delete-reference` | `create-delete-reference` | Remove references to a deleted team/agent/queue (destructive, see gotchas) |
| GET | `/organization/{orgid}/call-monitoring/{id}` | `show` | Get one schedule (full record) |
| PUT | `/organization/{orgid}/call-monitoring/{id}` | `update` | Full replace |
| PATCH | `/organization/{orgid}/call-monitoring/{id}` | `update-call-monitoring` | Partial update |
| DELETE | `/organization/{orgid}/call-monitoring/{id}` | `delete` | Delete a schedule |
| GET | `/organization/{orgid}/v2/call-monitoring` | `list` | List schedules (v2 — the only list endpoint) |
| GET | `/organization/{orgid}/user/by-call-monitoring-id/{id}` | `cc-users show` | Users a schedule covers (lives in the `cc-users` group) |

**Which list and which update to use.** The usual CC convention (see `cc-team` in §9) is that bare `list` is the v1 endpoint and `list-<resource>` is v2. That convention does **not** hold here: this resource has no v1 list, so the bare `list` *is* the v2 endpoint and there is no `list-call-monitoring`. For changes, prefer `update-call-monitoring` (PATCH): it changes only the fields you send, so pausing a schedule is one field. `update` (PUT) replaces the record, and the spec marks nine fields required on it — including the `teams` and `contactServiceQueues` arrays — so a PUT that omits them is expected to fail or to clear them.

### Key Parameters

- **Required by the spec on create/PUT:** `name`, `timezone`, `recurrence`, `startTimestamp`, `endTimestamp`, `userId` (the supervisor), `paused`, `teams` (at least one), `contactServiceQueues` (at least one)
- **`teams` / `contactServiceQueues`:** arrays of `{"id": ..., "name": ...}` references. They have no CLI flag — pass them in `--json-body`
- **`agentsAccessType`:** `ALL` or `SPECIFIC`; with `SPECIFIC`, list the agents in `agents` as `[{"id": "AGENT_USER_ID"}]`
- **`daysOfWeek`:** any of `SUN` `MON` `TUE` `WED` `THU` `FRI` `SAT`, used when `recurrence` is true
- **`show --include-filter-details true`:** adds the names of the teams, agents and queues to the response
- **`list --include-user-details true` / `--include-filters-count true`:** adds the supervisor's name/email, and per-schedule counts of specific agents/teams/queues

### CLI Examples

```bash
# List schedules (this bare `list` is the v2 endpoint), with supervisor names
wxcli cc-monitoring-schedules list --include-user-details true --all -o json

# Get one schedule, with team/agent/queue names filled in
wxcli cc-monitoring-schedules show SCHEDULE_ID --include-filter-details true

# Create a weekday schedule covering every agent on one team and one queue
wxcli cc-monitoring-schedules create --json-body '{
  "name": "Morning Shift Monitoring",
  "timezone": "America/New_York",
  "recurrence": true,
  "daysOfWeek": ["MON", "TUE", "WED", "THU", "FRI"],
  "startTimestamp": 1772169240000,
  "endTimestamp": 1772244000000,
  "userId": "SUPERVISOR_USER_ID",
  "paused": false,
  "agentsAccessType": "ALL",
  "teams": [{"id": "TEAM_ID"}],
  "contactServiceQueues": [{"id": "QUEUE_ID"}]
}'

# Pause it without touching anything else (PATCH)
wxcli cc-monitoring-schedules update-call-monitoring SCHEDULE_ID --paused --verify

# Which agents does this schedule actually cover?
wxcli cc-users show SCHEDULE_ID -o json

# Delete it
wxcli cc-monitoring-schedules delete SCHEDULE_ID --force
```

### Raw HTTP

The base URL is region-scoped (`https://api.wxcc-{region}.cisco.com`; `us1` shown) and `$ORG_ID` is the bare UUID form of the org ID (gotcha #19 in §25).

```bash
# List schedules (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/call-monitoring?includeUserDetails=true" \
  -H "Authorization: Bearer $TOKEN"

# Create a schedule
curl -X POST "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/call-monitoring" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Morning Shift Monitoring","timezone":"America/New_York","recurrence":true,"daysOfWeek":["MON","TUE","WED","THU","FRI"],"startTimestamp":1772169240000,"endTimestamp":1772244000000,"userId":"SUPERVISOR_USER_ID","paused":false,"agentsAccessType":"ALL","teams":[{"id":"TEAM_ID"}],"contactServiceQueues":[{"id":"QUEUE_ID"}]}'

# Pause a schedule (partial update)
curl -X PATCH "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/call-monitoring/$SCHEDULE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"paused":true}'

# Users covered by a schedule
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/user/by-call-monitoring-id/$SCHEDULE_ID?page=0&pageSize=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Gotchas

1. **`cc-monitoring-schedules` stores a plan; `cc-call-monitoring` acts on a call that is happening now — picking the wrong one either does nothing yet or does something immediately.** A request like "let the supervisor listen to the support team's calls on weekday mornings" is a schedule; "listen to this call" is a live session (`cc-call-monitoring create`, keyed by `taskId`). The two groups share no IDs: a schedule ID is not a monitoring request ID, and neither is a task ID. **Unverified:** derived from the two groups' paths and request schemas, not from a live call.

2. **A flags-only `create` gets past the CLI and is then expected to be rejected by the server, because two required fields have no flag.** The CLI checks seven required fields locally (`name`, `timezone`, `recurrence`, `startTimestamp`, `endTimestamp`, `userId`, `paused`), but the spec also requires `teams` and `contactServiceQueues` (each with at least one entry), and array fields are never generated as flags. The flag path also sends the timestamps as JSON strings where the spec declares integers. Use `--json-body` for create and PUT, starting from `--generate-json-body`. **Unverified:** the server's reaction to the missing arrays and string timestamps is predicted from the spec, not observed.

3. **The list response is not the whole schedule — read teams, agents and queues from `show`.** The spec states that returning array fields from the list endpoint is deprecated and points to get-by-ID for the complete resource, and the list `--filter`/`--attributes` parameters exclude `teams`, `agents` and `contactServiceQueues`. A list row with no teams is therefore not evidence that the schedule has none. **Unverified:** spec wording; the current list payload was not inspected.

4. **`create-delete-reference` deletes, despite its `create-` prefix, and it does not ask for confirmation.** It is `POST /call-monitoring/delete-reference` with a body like `{"references": {"team": "TEAM_ID"}}`. Its body schema is shared with other resources and describes detaching the named team, site, agent or skill profile from contact service queues across the org, so its exact reach on this path is not documented. Use it only to clean up after a team, agent or queue has been removed, and `show` the affected schedules before and after. **Unverified:** the spec gives this operation no summary or description of its own.

5. **`cc-users show` takes a schedule ID, not a user ID.** Upstream added `GET /organization/{orgid}/user/by-call-monitoring-id/{id}` under the Users tag, and it is generated as `cc-users show`. Passing a user ID to it returns nothing useful; to fetch one user, use `cc-users show-user` (§4). The spec says the result is filtered by the caller's team access ("while enforcing team ACL"), so two admins can get different lists for the same schedule. **Unverified:** command mapping read from `cc_users.py`; the ACL behaviour is spec wording.

---

## 22. Organization Settings (`cc-org-settings`)

The Contact Center tenant's organization-wide settings record (upstream tag "Organization Setting", paths `/organization/{orgid}/organization-setting`). Most of its 94 fields are **entitlements and capacity ceilings** that come from the subscription — `offerCode`, `offerDetails`, `maximumActiveCalls`, `maxChannels`, `maximumSkills`, `numberOfCadVariables`, feature switches such as `campaignManagerEnabled` and `wfoEnabled` — plus a small set of operational settings an admin can change: short- and lost-call thresholds, recording behaviour, purge of inactive entities, WebRTC, sensitive-data masking, and routing back to the same agent.

This is **not** the Webex org-wide `org-settings` group (organization feature settings by key, owned by the `manage-identity` skill), and it is not the Webex org profile (`identity-org`). It is also **not** `cc-tenant-config` (§23), which holds desktop and runtime timers such as RONA timeouts and auto wrap-up. There is no create or delete: you read the existing record and update it.

**Unverified:** read from `specs/webex-contact-center.json` and the generated module `cc_org_settings.py`. No live call was made; in particular, that an org has exactly one settings record is inferred from the absence of create/delete, not observed.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/organization-setting` | `list` | List (v1 — **deprecated** upstream) |
| GET | `/organization/{orgid}/v2/organization-setting` | `list-organization-setting` | List (v2 — use this) |
| GET | `/organization/{orgid}/organization-setting/{id}` | `show` | Get by ID |
| PUT | `/organization/{orgid}/organization-setting/{id}` | `update` | Full replace |
| PATCH | `/organization/{orgid}/organization-setting/{id}` | `update-organization-setting` | Partial update (use this) |

**Which list and which update to use.** This group follows the CC convention: bare `list` is v1 and `list-organization-setting` is v2. The spec marks the v1 list deprecated ("Use GET /v2/organization-setting instead"), so use `list-organization-setting` to find the record's ID. For writes, use `update-organization-setting` (PATCH). `update` (PUT) is a full replace whose schema marks 56 fields required, nearly all of them entitlements a user token is not allowed to change (see gotcha 2).

### Key Parameters

Fields the spec says a **user token** may change ("when authorized by the required scope and User Profile permission"); every other field is marked "User-token updates are not permitted":

| Field | CLI flag | Notes |
|-------|----------|-------|
| `shortCallThreshold` | `--short-call-threshold` | Integer |
| `lostCallThreshold` | `--lost-call-threshold` | Integer |
| `pauseResumeEnabled` | `--pause-resume-enabled` / `--no-pause-resume-enabled` | Recording pause/resume |
| `recordingPauseDuration` | `--recording-pause-duration` | Integer |
| `recordAllCalls` | `--record-all-calls` / `--no-record-all-calls` | |
| `recordingMode` | `--recording-mode` | `AUDIO_ONLY`, `AUDIO_AND_SCREEN`, `DISABLED` |
| `purgeAllowed` | `--purge-allowed` / `--no-purge-allowed` | |
| `purgeInactiveEntitiesInterval` | `--purge-inactive-entities-interval` | Integer |
| `webRtcEnabled` | `--web-rtc-enabled` / `--no-web-rtc-enabled` | |
| `maskSensitiveData` | `--mask-sensitive-data` / `--no-mask-sensitive-data` | |
| `routingToSameAgent` | `--routing-to-same-agent` | `DISABLED`, `ENABLED` |

### CLI Examples

```bash
# Find the settings record and its ID (v2)
wxcli cc-org-settings list-organization-setting -o json

# Read it in full
wxcli cc-org-settings show ORG_SETTING_ID

# Change one admin-modifiable threshold (PATCH) and confirm it took
wxcli cc-org-settings update-organization-setting ORG_SETTING_ID --json-body '{"shortCallThreshold": 10}' --verify

# Turn on routing back to the same agent
wxcli cc-org-settings update-organization-setting ORG_SETTING_ID --routing-to-same-agent ENABLED --verify
```

### Raw HTTP

Region-scoped base URL (`us1` shown); `$ORG_ID` is the bare UUID (gotcha #19 in §25).

```bash
# List (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/organization-setting" \
  -H "Authorization: Bearer $TOKEN"

# Partial update
curl -X PATCH "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/organization-setting/$ORG_SETTING_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shortCallThreshold":10}'
```

### Gotchas

1. **`cc-org-settings` and `org-settings` are different products' settings, and only the `cc-` prefix tells them apart.** `org-settings` reads and writes Webex organization feature settings by key on `webexapis.com`; `cc-org-settings` is the Contact Center tenant record on `api.wxcc-{region}.cisco.com` and needs the CC OAuth scopes (gotcha #2 in §25). A 403 from one says nothing about access to the other. **Unverified:** derived from the two groups' base URLs, not a live comparison.

2. **Only 11 of the 94 fields are writable with a user token, so most "settings" here are read-only to an admin.** The spec marks every entitlement, capacity and licensing field "User-token updates are not permitted"; the writable ones are listed under Key Parameters. Expect a rejection if a body includes a protected field with a changed value — one more reason to send a PATCH carrying only the field you mean to change. **Unverified:** which token types count as "user tokens", and what the server does with an unchanged protected field inside a body, were not tested.

3. **The bare `list` is the deprecated v1 endpoint.** It returns a plain array, while the spec directs callers to the v2 endpoint, which wxcli exposes as `list-organization-setting`. **Unverified:** spec wording; no removal date is given.

4. **Numeric flags are sent as JSON strings.** The generated command sends `--short-call-threshold 10` as `"10"`, while the spec declares an integer. If the server rejects it, pass the value in `--json-body '{"shortCallThreshold": 10}'`, which keeps the number a number. **Unverified:** read from the generated body assembly; server-side coercion not tested.

---

## 23. Tenant Configuration (`cc-tenant-config`)

Tenant-wide Contact Center runtime behaviour (upstream tag "Tenant Configuration", paths `/organization/{orgid}/tenant-configuration`): agent desktop timers (RONA timeouts per channel — telephony, chat, email, social, work item, custom messaging — desktop inactivity timeout, auto wrap-up interval, lost-connection recovery, heartbeat), call-control toggles (`endCallEnabled`, `endConsultEnabled`, `privacyShieldVisible`), outdial (`outdialEnabled`) and dial-number (DN) handling (default/other/target DN regex, prefix, strip characters and descriptions, `rejectDuplicateDn`, `forceDefaultDn`), and log levels.

This is **not** the entitlements record (`cc-org-settings`, §22). It is **not** a desktop profile (`cc-desktop-profile`, §14) or desktop layout (§13), which are assigned to agents — this record applies to the whole tenant. And it is **not** a Webex Calling location or org calling setting. There is no create or delete, and — unlike §21 and §22 — no partial update either.

**Unverified:** read from `specs/webex-contact-center.json` and the generated module `cc_tenant_config.py`. No live call was made; field meanings beyond their names are not stated by the spec.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/tenant-configuration` | `list` | List (v1 — **deprecated** upstream) |
| GET | `/organization/{orgid}/v2/tenant-configuration` | `list-tenant-configuration` | List (v2 — use this) |
| GET | `/organization/{orgid}/tenant-configuration/{id}` | `show` | Get by ID |
| PUT | `/organization/{orgid}/tenant-configuration/{id}` | `update` | Full replace — the only write |

**Which list and which update to use.** Bare `list` is v1 and deprecated by the spec; use `list-tenant-configuration` (v2). Upstream publishes no PATCH for this resource, so `update` (PUT, full replace) is the only way to change anything — see gotcha 1 for how to do that safely.

### Key Parameters

- **Required by the spec on `update`:** `timeoutRonaTelephonySeconds`, `timeoutRonaChatSeconds`, `timeoutRonaEmailSeconds`, `timeoutRonaSocialSeconds`
- **User-token writable** (every other field is marked "User-token updates are not permitted"): `autoWrapUpInterval`, `endCallEnabled`, `endConsultEnabled`, `lostConnectionRecoveryTimeout`, `forceDefaultDn`, `privacyShieldVisible`, `timeoutDesktopInactivityEnabled`, `timeoutDesktopInactivityMins`, and the five `timeoutRona…Seconds` fields for telephony, social, chat, email and work item (`timeoutRonaCustomMessagingSeconds` is not user-writable)
- **`timeoutRonaWorkItemSeconds` / `timeoutRonaCustomMessagingSeconds`:** valid range 1–6000, and only applicable when the tenant has the corresponding work-item or custom-messaging feature flag

### CLI Examples

```bash
# Find the record and its ID (v2)
wxcli cc-tenant-config list-tenant-configuration -o json

# Save the current record to a file before changing it
wxcli cc-tenant-config show TENANT_CONFIG_ID -o json > tenant-config.json

# Edit tenant-config.json (e.g. timeoutRonaTelephonySeconds), then PUT the whole record back
wxcli cc-tenant-config update TENANT_CONFIG_ID --json-body file://tenant-config.json --verify
```

### Raw HTTP

Region-scoped base URL (`us1` shown); `$ORG_ID` is the bare UUID (gotcha #19 in §25).

```bash
# List (v2)
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/v2/tenant-configuration" \
  -H "Authorization: Bearer $TOKEN"

# Read one record
curl "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/tenant-configuration/$TENANT_CONFIG_ID" \
  -H "Authorization: Bearer $TOKEN"

# Full replace — send the whole record you just read, with your edit applied
curl -X PUT "https://api.wxcc-us1.cisco.com/organization/$ORG_ID/tenant-configuration/$TENANT_CONFIG_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @tenant-config.json
```

### Gotchas

1. **There is no partial update: `update` is a PUT, so a call made with one flag sends a one-field body to a full-replace endpoint.** The generated command builds the body from only the flags you pass, and the spec requires the four RONA timeouts on every PUT. Changing just `--auto-wrap-up-interval` with flags is therefore expected to be rejected, or to reset fields you did not send. Read the record with `show -o json`, edit the file, and send it back with `--json-body file://…`. **Unverified:** whether the server rejects or resets omitted fields was not tested; full-replace semantics are the CC convention (Pattern Note 5 in §24).

2. **Units differ from field to field, and the names do not always say which.** The RONA timeouts are in seconds and the desktop inactivity timeout in minutes, as their names state. `autoWrapUpInterval`, `heartBeatInterval`, `lostConnectionRecoveryTimeout` and `notRespondingToAvailableTimeout` carry no unit in the spec; their examples (30000, 30000, 60000, 300000) read as milliseconds. Check the current value with `show` before writing one, so a "30" meant as seconds does not become 30 ms. **Unverified:** the millisecond reading is inferred from the spec's example values.

3. **The bare `list` is the deprecated v1 endpoint.** Use `list-tenant-configuration` (v2). **Unverified:** spec wording; no removal date is given.

---

## 24. Common Patterns

Most CC config entities follow a standard CRUD pattern with these operations:

| Operation | Method | Path Pattern | CLI Pattern | Description |
|-----------|--------|-------------|-------------|-------------|
| **List (v1)** | GET | `/organization/{orgid}/{resource}` | `list` or `list-{resource}-organization` | Basic list |
| **List (v2)** | GET | `/organization/{orgid}/v2/{resource}` | `list-{resource}` or `list-{resource}-v2` | Enhanced filtering, pagination |
| **Create** | POST | `/organization/{orgid}/{resource}` | `create` or `create-{resource}` | Create single entity |
| **Bulk save** | POST | `/organization/{orgid}/{resource}/bulk` | `create-bulk` or `create` | Create/update multiple entities |
| **Bulk export** | GET | `/organization/{orgid}/{resource}/bulk-export` | `list` or `list-bulk-export` | Export all entities (CSV-compatible) |
| **Purge inactive** | POST | `/organization/{orgid}/{resource}/purge-inactive-entities` | `delete-purge-inactive-entities` | Permanently remove deactivated entities |
| **Get by ID** | GET | `/organization/{orgid}/{resource}/{id}` | `show` | Get single entity |
| **Update** | PUT | `/organization/{orgid}/{resource}/{id}` | `update` | Full replace |
| **Delete** | DELETE | `/organization/{orgid}/{resource}/{id}` | `delete` | Remove entity |
| **List references** | GET | `/organization/{orgid}/{resource}/{id}/incoming-references` | `list-incoming-references` | Show what references this entity |

### Pattern Notes

1. **v1 vs v2 vs v3 endpoints:** v2/v3 endpoints generally support better pagination (`page`, `pageSize`), FIQL-style filtering, and field selection (`attributes` parameter). Prefer v2/v3 when available.

2. **Bulk save vs create:** Bulk save (`/bulk`) accepts an array and can create or update multiple entities in one call. Single create returns the created entity.

3. **Purge inactive:** Soft-deleted entities remain in the system until purged. The purge endpoint permanently removes them. This is irreversible.

4. **Incoming references:** Before deleting an entity, check incoming references to see what depends on it. Deleting an entity that is referenced by another entity may fail or cause cascading issues.

5. **PUT is full replace:** All update endpoints use PUT (full replacement). Always GET the entity first, modify the fields you need, and PUT the full object back. The exceptions are the bulk PATCH endpoints on `auxiliary-code` and `user`, and the per-record PATCH commands on call monitoring schedules (`cc-monitoring-schedules update-call-monitoring`, §21) and organization settings (`cc-org-settings update-organization-setting`, §22). Tenant configuration (§23) has no PATCH.

6. **orgId auto-injection:** The `{orgid}` path parameter is automatically injected from your saved config. You never need to pass it manually in CLI commands.

### Entity Dependency Order

When building a CC deployment from scratch, create entities in this order:

```
1. Sites
2. Business Hours + Holiday Lists
3. Skills
4. Skill Profiles (references Skills)
5. Multimedia Profiles
6. Aux Codes (Idle + Wrap-Up)
7. Work Types
8. Global Variables
9. Desktop Layouts
10. Desktop Profiles (references Desktop Layouts)
11. Teams (references Sites)
12. User Profiles (references Queues, Wrap-Up Codes)
13. Queues (references Skill Profiles, Teams)
14. Entry Points (references Queues)
15. Users (references Teams, Skill Profiles, Multimedia Profiles, User Profiles)
```

For teardown, reverse this order.

---

## 25. Gotchas

1. **Different base URL.** The CC API uses `api.wxcc-{region}.cisco.com`, not `webexapis.com`. Set the region with `wxcli set-cc-region <region>` (defaults to `us1`). Using the wrong base URL produces connection errors.

2. **CC-specific OAuth scopes.** CC endpoints require `cjp:config_read` and `cjp:config_write` scopes, not `spark-admin:*` scopes. A standard Webex admin token without CC scopes gets 403 errors. The CLI *may* print a scope tip for these, but do not rely on it: the handler matches on the literal strings `wxcc` and `403` appearing in the error response **body text**, not on the HTTP status code, so the tip only appears when the body happens to spell out both. Treat any 403 from a `cc-*` command as a scope problem whether or not the tip is printed. Note: `cjp:config` (bare, no suffix) also appears in some webhook and subscription API scope requirements — it may be a distinct scope or a legacy alias. Include it when building CC webhook integrations to avoid unexpected 403s.

3. **orgId is auto-injected.** The `{orgid}` path parameter is resolved from your saved config or authenticated user's org. Do not pass it as a CLI flag -- it will be injected automatically.

4. **Multiple API versions.** Many resources have v1, v2, and v3 endpoint variants. The v2/v3 endpoints typically add better filtering, pagination, and additional fields. The v1 endpoints remain for backward compatibility. When in doubt, use the v2/v3 variant.

5. **Bulk operations accept arrays.** Bulk save and bulk partial update endpoints accept JSON arrays of objects. Bulk export returns all entities, sometimes in a CSV-compatible format.

6. **Purge is permanent.** The "purge inactive entities" operation permanently removes all soft-deleted/deactivated resources of that type. There is no undo. Use bulk export first to back up entities before purging.

7. **Agent APIs use runtime paths.** The `cc-agents` group uses `/v1/agents/` and `/v2/agents/` (runtime API), not `/organization/{orgid}/` (config API). These are session-level operations (login, logout, state change) rather than configuration operations.

8. **Agent Wellbeing mixes path families.** The `cc-agent-wellbeing` group has config endpoints at `/organization/{orgid}/agent-burnout/` and runtime endpoints at `/v1/agentburnout/`. The config endpoints manage burnout detection settings; the runtime endpoints handle real-time event subscriptions and actions.

9. **Queue stats are a separate group.** Queue statistics use `cc-queue-stats` (path `/v1/queues/statistics`), which is a separate CLI group from queue configuration (`cc-queue`). Statistics are read-only runtime data.

10. **Desktop Profile API path is "agent-profile".** The `cc-desktop-profile` CLI group maps to the API path `/organization/{orgid}/agent-profile`, not `/organization/{orgid}/desktop-profile`. This naming mismatch is in the API itself.

11. **Global Variables API path is "cad-variable".** The `cc-global-vars` CLI group maps to `/organization/{orgid}/cad-variable`. CAD stands for Customer Activity Data, the legacy term for these variables. The CLI uses the friendlier name `cc-global-vars`.

12. **Incoming references before delete.** Always check `list-incoming-references` before deleting a config entity. Deleting an entity that is referenced by queues, teams, or routing strategies can produce 409 Conflict errors or leave orphaned references.

13. **Skill value types must match.** When creating skill profiles, the `skillValue` must match the skill's `skillType`: integer 0-10 for PROFICIENCY, boolean for BOOLEAN, string for ENUM (must be a defined enum value), or string for TEXT.

14. **Sites must exist before teams.** A team requires a `siteId`. Create sites first, then teams. Similarly, skill profiles require skills, and queues can require skill profiles.

15. **Agent summaries use POST for search.** Both `cc-agent-summaries` endpoints use POST (not GET) because they accept complex filter criteria in the request body. This is a search pattern, not a create pattern, despite the CLI command name `create`.

16. **Auto CSAT has two path families.** The deprecated paths use `/auto-csat/{autoCsatId}/...` and are documented in [contact-center-analytics.md](contact-center-analytics.md). The new non-deprecated paths use `/ai-feature/auto-csat/...` and are available via `wxcli cc-ai-feature` (8 commands). Use the `ai-feature` paths for new integrations.

17. **Internal queue endpoints.** The `by-team-id/.../internal` and `by-user-ci-id/.../internal` queue endpoints are marked as internal-use. They work with CI (Common Identity) user IDs, not CC user IDs. Use the v2 `by-user-id` endpoints for standard integrations.

18. **Reskill uses PATCH, not PUT.** The `/user/{id}/reskill` endpoint uses PATCH (partial update) to modify a user's skill profile and dynamic skills. The `dynamicSkills` field accepts `add` and `remove` arrays for incremental changes rather than full replacement.

19. **CC org ID must be bare UUID.** The CC config API path parameter `{orgid}` requires the raw UUID (e.g., `b8410147-6104-42e8-9b93-639730d983ff`), not the base64-encoded Spark ID returned by `/people/me`. The CLI uses `get_cc_org_id()` in `config.py` to decode automatically. If calling the API directly, decode the base64 orgId to extract the UUID after the last `/` in the URN.

20. **CC v2 list endpoints return `"data"`, not `"items"`.** The v2 endpoints (e.g., `GET /organization/{orgid}/v2/cad-variable`) wrap results in `{"meta": {...}, "data": [...]}`. The v1 bulk-export endpoints use `{"items": [...]}`. The CLI handles both automatically.

21. **Global Variable `variableType` requires title case.** The API rejects `"STRING"` — use `"String"`, `"Integer"`, `"Boolean"`, `"Decimal"`, `"DateTime"`. The OpenAPI spec lists both forms but only title case works at runtime.

22. **`desktopLabel` required when `agentViewable` is true.** Creating or updating a Global Variable with `agentViewable: true` fails unless `desktopLabel` is also provided. This dependency is not documented in the API spec's required fields list.

23. **Personal access tokens lack CC *config* scopes.** PATs from developer.webex.com do NOT carry `cjp:config_read` or `cjp:config_write`, even for full admins on CC-provisioned orgs. **This is about the config surface only — it is not true of the agent runtime.** A PAT *does* carry `cjp:user`, the per-agent runtime scope: verified live on 2026-07-31, an agent's PAT successfully drove `register()`, `stationLogin()` and `setAgentState()` through the `@webex/contact-center` JS SDK against a live tenant. So a PAT works for a custom agent desktop and for `PATCH /v1/tasks/{taskId}`, and does not work for `wxcli cc-*`. See [contact-center-agent-sdk.md](contact-center-agent-sdk.md) §10. Two options for CC config operations: (a) **OAuth integration** — select CC scopes explicitly and complete the OAuth authorization flow; adding scopes to an existing integration does not update previously issued tokens, you must re-authorize; (b) **Service App with CJP scopes** — recommended for production automation and server-to-server use; no interactive login required after the org admin authorizes the app, making it suitable for CI/CD pipelines and backend services. Note: all CC integration scopes work with Service Apps except `spark:applications_token` and `spark:kms`.

24. **Global Variable names are immutable.** The CC API returns 400 `"name: should not be modified"` if you attempt to change the `name` field via PUT update. To rename a variable, delete and recreate it. Note that any flows referencing the old variable ID will need to be updated.

25. **Flow Designer HTTP Connector handles auth and base URL automatically.** The CC HTTP Connector (created in Control Hub → Contact Center → Integrations → Connectors) stores the regional base URL and auth tokens for you. In the Flow Designer HTTP Request node, provide only the **request path**, not the full URL — e.g., `/organization/{orgid}/cad-variable` for Global Variables or `/search` for the Search API. Toggle "Use Authenticated Endpoint" and select the connector; no manual token management is needed in flows. When creating the connector, choose the access level: Read-Only (GET) or Read-Write (POST/PUT/DELETE).

26. **Derive the CC regional base URL from the access token.** The Webex access token has three underscore-separated parts: `token.split('_')` → `[accessToken, ciCluster, orgId]`. The middle segment (`ciCluster`) maps directly to the regional base URL: `https://api.wxcc-{ciCluster}.cisco.com`. Available regions: `us1`, `eu1`, `eu2`, `anz1` (confirmed); `ca1`, `jp1`, `sg1` (plausible but not independently confirmed from public documentation — verify against your org's token cluster value). This is useful for production apps that need to determine the correct CC API endpoint dynamically without hardcoding a region.

---

## 26. See Also

- [Contact Center: Routing](contact-center-routing.md) -- Dial plans, campaigns, flows, audio files, contact lists, dial numbers
- [Contact Center: Analytics](contact-center-analytics.md) -- AI, monitoring, subscriptions, tasks, search
- [Contact Center: Journey](contact-center-journey.md) -- JDS: workspaces, persons, identity, profile views, events
- [Contact Center: Agent Desktop SDK](contact-center-agent-sdk.md) -- The `@webex/contact-center` **JS SDK** for building a custom agent desktop. Note the "desktop" collision: §13 above is *desktop layout* config for **Cisco's own** Agent Desktop; that doc is about replacing that app with your own, which ignores layouts entirely
- [Contact Center: Analytics §7 — Call Monitoring](contact-center-analytics.md#7-call-monitoring) -- Go here when the supervisor needs to listen to, barge into, or end monitoring on a call that is **in progress** (`cc-call-monitoring`). §21 above only stores monitoring *schedules*; it never touches a live call
- [Admin: Org Management](admin-org-management.md) -- Go here when the setting you want is a **Webex** organization setting (`org-settings`, `identity-org`) rather than the Contact Center tenant record in §22. The `cc-` prefix is the only thing that tells the two groups apart, and they live on different hosts with different scopes
- [Authentication](authentication.md) -- CC-specific OAuth scopes, region configuration, and token setup
- [Contact Center Skill](../../.claude/skills/contact-center/SKILL.md) -- Guided workflow for provisioning agents, queues, teams, flows, campaigns via wxcli
- `CLAUDE.md` (project root) -- CC region setup, CLI integration notes
