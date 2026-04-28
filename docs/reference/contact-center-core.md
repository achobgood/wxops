# Contact Center: Agents, Queues, Teams, and Configuration

Reference for Webex Contact Center agent management, queue routing, team assignment, skill-based routing, desktop configuration, and administrative entity management. Covers 21 CLI groups with 211 commands generated from the Contact Center OpenAPI spec.

## Sources

- OpenAPI spec: `specs/webex-contact-center.json`
- [Webex Contact Center API](https://developer.webex.com/docs/api/guides/wxcc-overview) -- Official API docs
- developer.webex.com Contact Center APIs

---

## API Base and Authentication

- **Base URL:** `https://api.wxcc-{region}.cisco.com` (NOT `webexapis.com`)
- **Regions:** `us1` (default), `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1`
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
21. [Common Patterns](#21-common-patterns)
22. [Gotchas](#22-gotchas)
23. [See Also](#23-see-also)

> **Note:** Agent summaries (`cc-agent-summaries`) are documented in [contact-center-analytics.md](contact-center-analytics.md) alongside the related AI and generated summary features.

---

## 1. Agents (`cc-agents`)

Runtime agent operations: login, logout, state changes, reload, buddy lists, activities, and statistics. These use the runtime path family (`/v1/agents/`, `/v2/agents/`), not the config API.

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/v1/agents/activities` | `list` | Get Agent Activities |
| POST | `/v1/agents/buddyList` | `create-buddy-list` | Buddy Agents List |
| POST | `/v1/agents/login` | `create-login-agents-1` | Login (v1) |
| PUT | `/v1/agents/logout` | `update` | Logout |
| POST | `/v1/agents/reload` | `create` | Reload |
| PUT | `/v1/agents/session/state` | `update-state-session` | State Change |
| GET | `/v1/agents/statistics` | `list-statistics` | Get Agent Statistics |
| POST | `/v2/agents/login` | `create-login-agents` | Login (v2) |
| PUT | `/v2/agents/logout` | `update-logout` | Logout (v2) |
| POST | `/v2/agents/reload` | `create-reload` | Reload (v2) |
| PUT | `/v2/agents/session/state` | `update-state-session-1` | State Change (v2) |

### Key Parameters

- **Login:** Requires `teamId`, `channelName`, `agentDn` (dial number)
- **State Change:** Requires `state` (Available, Idle, etc.), `auxCodeId` (for idle codes)
- **Activities:** Supports `from`, `to` date filters, `agentId`, `state`
- **Statistics:** Supports `agentId`, `channelType`, `from`, `to`

### CLI Examples

```bash
# Log in an agent (v2)
wxcli cc-agents create-login-agents --json-body '{
  "agentId": "...",
  "teamId": "...",
  "channelName": "telephony",
  "agentDn": "1001"
}'

# Change agent state to Available
wxcli cc-agents update-state-session-1 --json-body '{
  "agentId": "...",
  "state": "Available"
}'

# Get agent activities for a date range
wxcli cc-agents list --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z"

# Get agent statistics
wxcli cc-agents list-statistics --agent-id "..."

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
| POST | `/organization/{orgid}/agent-personal-greeting` | `create-agent-personal-greeting` | Create (v1) |
| POST | `/organization/{orgid}/agent-personal-greeting/delete-reference` | `create-delete-reference` | Delete References |
| DELETE | `/organization/{orgid}/agent-personal-greeting/{id}` | `delete-agent-personal-greeting` | Delete (v1) |
| GET | `/organization/{orgid}/agent-personal-greeting/{id}` | `show-agent-personal-greeting` | Get by ID (v1) |
| PATCH | `/organization/{orgid}/agent-personal-greeting/{id}` | `update-agent-personal-greeting-organization-1` | Partial update (v1) |
| PUT | `/organization/{orgid}/agent-personal-greeting/{id}` | `update-agent-personal-greeting-organization` | Update (v1) |
| GET | `/organization/{orgid}/v2/agent-personal-greeting` | `list` | List all (v2) |
| POST | `/organization/{orgid}/v2/agent-personal-greeting` | `create` | Create (v2) |
| DELETE | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | `delete` | Delete (v2) |
| GET | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | `show` | Get by ID (v2) |
| PATCH | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | `update-agent-personal-greeting-v2` | Partial update (v2) |
| PUT | `/organization/{orgid}/v2/agent-personal-greeting/{id}` | `update` | Update (v2) |
| GET | `/organization/{orgid}/v3/agent-personal-greeting` | `list-agent-personal-greeting` | List (v3) |

### CLI Examples

```bash
# List all agent greetings (v2)
wxcli cc-agent-greetings list

# Get a specific greeting (v2)
wxcli cc-agent-greetings show --id "greeting-uuid"

# Create a greeting (v2)
wxcli cc-agent-greetings create --json-body '{
  "name": "Welcome Greeting",
  "type": "WELCOME",
  "agentId": "..."
}'

# Delete a greeting (v2)
wxcli cc-agent-greetings delete --id "greeting-uuid"

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

> **Deprecated (April 2026).** The standalone Agent Wellbeing API is deprecated and will be removed in a future release. Use the consolidated `AI Feature` API (`wxcli cc-ai-feature`) instead.

Monitor and manage agent burnout detection. Mixes config paths (`/organization/{orgid}/agent-burnout/`) with runtime paths (`/v1/agentburnout/`).

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/agent-burnout/{id}` | `show` | Get Agent Burnout by ID |
| PUT | `/organization/{orgid}/agent-burnout/{id}` | `update` | Update Agent Burnout by ID |
| GET | `/organization/{orgid}/v2/agent-burnout` | `list` | List Agent Burnout (v2) |
| POST | `/v1/agentburnout/action` | `create-action` | Record realtime burnout events |
| POST | `/v1/agentburnout/subscribe` | `create` | Subscribe for realtime burnout events |

### CLI Examples

```bash
# List agent burnout resources (v2)
wxcli cc-agent-wellbeing list

# Get burnout config for a specific agent
wxcli cc-agent-wellbeing show --id "burnout-uuid"

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
| GET | `/organization/{orgid}/user` | `list-user-organization` | List User(s) (v1) |
| PATCH | `/organization/{orgid}/user/bulk` | `update` | Bulk partial update Users |
| GET | `/organization/{orgid}/user/bulk-export` | `list-bulk-export` | Bulk export User(s) |
| GET | `/organization/{orgid}/user/by-ci-user-id/{id}` | `show-by-ci-user-id-organization` | Get User by CI User ID (v1) |
| POST | `/organization/{orgid}/user/fetch-by-skill-requirements` | `create` | Get agents matching skill requirements |
| POST | `/organization/{orgid}/user/fetch-user-details-by-ids` | `create-fetch-user-details-by-ids` | Get Users by provided IDs |
| GET | `/organization/{orgid}/user/with-user-profile` | `list-with-user-profile` | List Users with profile |
| GET | `/organization/{orgid}/user/with-user-profile/{id}` | `show` | Get User with profile by ID |
| GET | `/organization/{orgid}/user/{id}` | `show-user` | Get User by ID |
| PATCH | `/organization/{orgid}/user/{id}` | `update-user-organization-1` | Partially update User by ID |
| PUT | `/organization/{orgid}/user/{id}` | `update-user-organization` | Update User by ID |
| GET | `/organization/{orgid}/user/{id}/incoming-references` | `list` | List references for User |
| GET | `/organization/{orgid}/v2/user` | `list-user-v2` | List User(s) (v2) |
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
wxcli cc-users list-user-v2

# Get a user with their profile
wxcli cc-users show --id "user-uuid"

# Get a user by their Webex CI User ID
wxcli cc-users show-by-ci-user-id-v2 --id "ci-user-uuid"

# Bulk export all users
wxcli cc-users list-bulk-export

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

User profiles define what a CC agent can do: access to queues, features, and settings. Three API versions available (v1, v2, v3).

### Endpoints

| Method | Path | CLI Command | Description |
|--------|------|-------------|-------------|
| GET | `/organization/{orgid}/user-profile` | `list-user-profile-organization` | List (v1) |
| POST | `/organization/{orgid}/user-profile/bulk` | `create-bulk-user-profile-1` | Bulk save (v1) |
| GET | `/organization/{orgid}/user-profile/bulk-export` | `list-bulk-export-user-profile-1` | Bulk export (v1) |
| POST | `/organization/{orgid}/user-profile/purge-inactive-entities` | `create` | Purge inactive |
| GET | `/organization/{orgid}/user-profile/{id}` | `show` | Get by ID (v1) |
| DELETE | `/organization/{orgid}/user-profile/{id}` | `delete` | Delete (v1) |
| PUT | `/organization/{orgid}/user-profile/{id}` | `update` | Update (v1) |
| GET | `/organization/{orgid}/user-profile/{id}/incoming-references` | `list` | List references |
| GET | `/organization/{orgid}/v2/user-profile` | `list-user-profile-v2` | List (v2) |
| GET | `/organization/{orgid}/v3/user-profile` | `list-user-profile-v3` | List (v3) |
| POST | `/organization/{orgid}/v3/user-profile` | `create-user-profile` | Create (v3) |
| POST | `/organization/{orgid}/v3/user-profile/bulk` | `create-bulk-user-profile` | Bulk save (v3) |
| GET | `/organization/{orgid}/v3/user-profile/bulk-export` | `list-bulk-export-user-profile` | Bulk export (v3) |
| GET | `/organization/{orgid}/v3/user-profile/{id}` | `show-user-profile` | Get by ID (v3) |
| DELETE | `/organization/{orgid}/v3/user-profile/{id}` | `delete-user-profile` | Delete (v3) |
| PUT | `/organization/{orgid}/v3/user-profile/{id}` | `update-user-profile` | Update (v3) |
| GET | `/organization/{orgid}/v3/user-profile/{id}/acl` | `list-acl` | Get ACL (v3) |

### Key Parameters

- **Create (v3):** Requires `name`, optional `description`, `accessRights`, `queues`, `wrapUpCodes`
- **ACL (v3):** Returns access control list for the profile -- which queues and features the profile grants access to
- **Purge:** Removes all soft-deleted/deactivated user profiles permanently

### CLI Examples

```bash
# List user profiles (v3)
wxcli cc-user-profiles list-user-profile-v3

# Get a user profile by ID (v3)
wxcli cc-user-profiles show-user-profile --id "profile-uuid"

# Create a user profile (v3)
wxcli cc-user-profiles create-user-profile --json-body '{
  "name": "Standard Agent Profile",
  "description": "Default profile for voice agents",
  "accessRights": {"queues": ["queue-uuid-1", "queue-uuid-2"]}
}'

# Get profile ACL (v3)
wxcli cc-user-profiles list-acl --id "profile-uuid"

# Bulk export all profiles (v3)
wxcli cc-user-profiles list-bulk-export-user-profile

# Delete a user profile (v3)
wxcli cc-user-profiles delete-user-profile --id "profile-uuid"
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
| GET | `/organization/{orgid}/contact-service-queue` | `list-contact-service-queue-organization` | List (v1) |
| POST | `/organization/{orgid}/contact-service-queue` | `create-contact-service-queue-organization` | Create (v1) |
| POST | `/organization/{orgid}/contact-service-queue/bulk` | `create` | Bulk save |
| PATCH | `/organization/{orgid}/contact-service-queue/bulk` | `update` | Bulk partial update |
| GET | `/organization/{orgid}/contact-service-queue/bulk-export` | `list` | Bulk export |
| GET | `/organization/{orgid}/contact-service-queue/by-skill-profile-id/{id}` | `show` | Get by skill profile ID |
| POST | `/organization/{orgid}/contact-service-queue/delete-reference` | `create-delete-reference` | Delete References |
| POST | `/organization/{orgid}/contact-service-queue/fetch-manually-assignable-queues` | `create-fetch-manually-assignable-queues` | Fetch assignable queues |
| POST | `/organization/{orgid}/contact-service-queue/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| POST | `/organization/{orgid}/contact-service-queue/v2/bulk` | `create-bulk` | Bulk save (v2) |
| GET | `/organization/{orgid}/contact-service-queue/{id}` | `show-contact-service-queue-organization` | Get by ID |
| DELETE | `/organization/{orgid}/contact-service-queue/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/contact-service-queue/{id}` | `update-contact-service-queue-organization` | Update |
| GET | `/organization/{orgid}/contact-service-queue/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/contact-service-queue` | `list-contact-service-queue-v2` | List (v2) |
| POST | `/organization/{orgid}/v2/contact-service-queue` | `create-contact-service-queue-v2` | Create (v2) |
| GET | `/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/agent-based-queues` | `list-agent-based-queues` | Agent-based queues by user |
| GET | `/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/skill-based-queues` | `list-skill-based-queues` | Skill-based queues by user |
| GET | `/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/team-based-queues` | `list-team-based-queues` | Team-based queues by user |
| GET | `/organization/{orgid}/v2/contact-service-queue/{id}` | `show-contact-service-queue-v2` | Get by ID (v2) |
| PUT | `/organization/{orgid}/v2/contact-service-queue/{id}` | `update-contact-service-queue-v2` | Update (v2) |
| POST | `/organization/{orgid}/v2/contact-service-queue/{id}/reassign-agents` | `create-reassign-agents` | Reassign agents |
| GET | `/organization/{orgid}/v3/contact-service-queue` | `list-contact-service-queue-v3` | List (v3) |
| GET | `/organization/{orgid}/contact-service-queue/by-team-id/{id}/internal` | `list-internal-by-team-id` | Team CSQs by team ID (internal) |
| GET | `/organization/{orgid}/contact-service-queue/by-user-ci-id/{ciUserId}/internal` | `list-internal-by-user-ci-id` | Agent CSQs by CI user ID (internal) |
| POST | `/organization/{orgid}/contact-service-queue/fetch-by-dynamic-skills-and-skillProfile` | `create-fetch-by-dynamic-skills-and-skill-profile` | Skill-based CSQs by dynamic skills + profile |
| POST | `/organization/{orgid}/contact-service-queue/fetch-by-userId-skillProfileId` | `create-fetch-by-user-id-skill-profile-id` | Skill-based CSQs by user ID + skill profile ID |
| GET | `/organization/{orgid}/contact-service-queue/skill-based-queues/by-ci-user-id/{id}/internal` | `list-internal-by-ci-user-id` | Skill-based CSQs by CI user ID (internal) |
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
wxcli cc-queue create-contact-service-queue-v2 --json-body '{
  "name": "Sales Queue",
  "channelType": "telephony",
  "routingType": "SKILL_BASED",
  "skillProfileId": "...",
  "distributionType": "LONGEST_AVAILABLE"
}'

# Get a specific queue (v2)
wxcli cc-queue show-contact-service-queue-v2 --id "queue-uuid"

# Get queues where an agent is eligible (agent-based)
wxcli cc-queue list-agent-based-queues --userid "user-uuid"

# Reassign agents to a queue
wxcli cc-queue create-reassign-agents --id "queue-uuid" --json-body '{
  "agentIds": ["agent1-uuid", "agent2-uuid"],
  "action": "ADD"
}'

# Bulk export all queues
wxcli cc-queue list

# Delete a queue
wxcli cc-queue delete --id "queue-uuid"

# List team-based queues for a team (internal)
wxcli cc-queue list-internal-by-team-id "team-uuid"

# List agent-based queues for a CI user (internal)
wxcli cc-queue list-internal-by-user-ci-id "ci-user-uuid"

# List skill-based queues for a CI user (internal)
wxcli cc-queue list-internal-by-ci-user-id "ci-user-uuid"

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

# Get statistics for a specific queue
wxcli cc-queue-stats list --queue-id "queue-uuid"
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
| GET | `/organization/{orgid}/entry-point` | `list-entry-point-organization` | List |
| POST | `/organization/{orgid}/entry-point` | `create-entry-point` | Create |
| POST | `/organization/{orgid}/entry-point/bulk` | `create` | Bulk save |
| GET | `/organization/{orgid}/entry-point/bulk-export` | `list` | Bulk export |
| POST | `/organization/{orgid}/entry-point/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/entry-point/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/entry-point/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/entry-point/{id}` | `update` | Update |
| GET | `/organization/{orgid}/entry-point/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/entry-point` | `list-entry-point-v2` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `channelType` (telephony, chat, email, social), `serviceLevel` threshold
- **v2 list:** Enhanced filtering and pagination support

### CLI Examples

```bash
# List all entry points (v2)
wxcli cc-entry-point list-entry-point-v2

# Create a telephony entry point
wxcli cc-entry-point create-entry-point --json-body '{
  "name": "Main IVR",
  "channelType": "telephony",
  "serviceLevel": 60
}'

# Get a specific entry point
wxcli cc-entry-point show --id "ep-uuid"

# Bulk export all entry points
wxcli cc-entry-point list

# Delete an entry point
wxcli cc-entry-point delete --id "ep-uuid"

# List references (what uses this entry point)
wxcli cc-entry-point list-incoming-references --id "ep-uuid"
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
| POST | `/organization/{orgid}/team/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
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
wxcli cc-team show --id "team-uuid"

# Bulk save multiple teams
wxcli cc-team create-bulk --json-body '[
  {"name": "Support Team A", "siteId": "site-uuid"},
  {"name": "Support Team B", "siteId": "site-uuid"}
]'

# Delete a team
wxcli cc-team delete --id "team-uuid"

# See what references this team
wxcli cc-team list-incoming-references --id "team-uuid"
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
| POST | `/organization/{orgid}/skill/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/skill/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/skill/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/skill/{id}` | `update` | Update |
| GET | `/organization/{orgid}/skill/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/skill` | `list-skill` | List (v2) |
| POST | `/organization/{orgid}/skill/populate-json-attr/{id}` | `create-populate-json-attr` | Populate JSON attributes for a skill |

### Key Parameters

- **Create:** Requires `name`, `serviceLevel`, `skillType` (TEXT, PROFICIENCY, BOOLEAN, ENUM)
- **Populate JSON attributes:** Takes skill ID as path parameter. Populates the `jsonAttr` field for the specified skill. Useful for initializing skill metadata after creation.
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
wxcli cc-skill show --id "skill-uuid"

# Delete a skill
wxcli cc-skill delete --id "skill-uuid"

# Populate JSON attributes for a skill
wxcli cc-skill create-populate-json-attr "skill-uuid"
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
| GET | `/organization/{orgid}/skill-profile` | `list-skill-profile-organization` | List |
| POST | `/organization/{orgid}/skill-profile` | `create-skill-profile` | Create |
| POST | `/organization/{orgid}/skill-profile/bulk` | `create` | Bulk save |
| GET | `/organization/{orgid}/skill-profile/bulk-export` | `list` | Bulk export |
| GET | `/organization/{orgid}/skill-profile/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/skill-profile/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/skill-profile/{id}` | `update` | Update |
| GET | `/organization/{orgid}/skill-profile/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/skill-profile` | `list-skill-profile-v2` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `skills` array with `{skillId, skillValue}` entries
- **Skill values:** Must match the skill's type (0-10 for proficiency, true/false for boolean, enum value for enum, text for text)

### CLI Examples

```bash
# List all skill profiles (v2)
wxcli cc-skill-profile list-skill-profile-v2

# Create a skill profile
wxcli cc-skill-profile create-skill-profile --json-body '{
  "name": "Senior Sales Agent",
  "skills": [
    {"skillId": "product-knowledge-uuid", "skillValue": 8},
    {"skillId": "spanish-speaker-uuid", "skillValue": true},
    {"skillId": "region-uuid", "skillValue": "EAST"}
  ]
}'

# Get a specific skill profile
wxcli cc-skill-profile show --id "profile-uuid"

# Bulk export all skill profiles
wxcli cc-skill-profile list

# Delete a skill profile
wxcli cc-skill-profile delete --id "profile-uuid"
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
| GET | `/organization/{orgid}/multimedia-profile` | `list-multimedia-profile-organization` | List |
| POST | `/organization/{orgid}/multimedia-profile` | `create-multimedia-profile` | Create |
| POST | `/organization/{orgid}/multimedia-profile/bulk` | `create` | Bulk save |
| GET | `/organization/{orgid}/multimedia-profile/bulk-export` | `list` | Bulk export |
| POST | `/organization/{orgid}/multimedia-profile/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/multimedia-profile/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/multimedia-profile/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/multimedia-profile/{id}` | `update` | Update |
| GET | `/organization/{orgid}/multimedia-profile/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/multimedia-profile` | `list-multimedia-profile-v2` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, channel capacities (`telephony`, `chat`, `email`, `social` counts)
- **Blended mode:** When set, agent can handle contacts across multiple channels simultaneously

### CLI Examples

```bash
# List multimedia profiles (v2)
wxcli cc-multimedia-profile list-multimedia-profile-v2

# Create a multimedia profile
wxcli cc-multimedia-profile create-multimedia-profile --json-body '{
  "name": "Voice Only",
  "telephony": 1,
  "chat": 0,
  "email": 0,
  "social": 0
}'

# Create a blended profile (voice + chat)
wxcli cc-multimedia-profile create-multimedia-profile --json-body '{
  "name": "Blended Agent",
  "telephony": 1,
  "chat": 3,
  "email": 5,
  "social": 2
}'

# Get a specific profile
wxcli cc-multimedia-profile show --id "mm-profile-uuid"

# Delete a profile
wxcli cc-multimedia-profile delete --id "mm-profile-uuid"
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
| POST | `/organization/{orgid}/desktop-layout` | `create-desktop-layout` | Create |
| POST | `/organization/{orgid}/desktop-layout/bulk` | `create` | Bulk save |
| GET | `/organization/{orgid}/desktop-layout/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/desktop-layout/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/desktop-layout/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/desktop-layout/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/desktop-layout/{id}` | `update` | Update |
| GET | `/organization/{orgid}/desktop-layout/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/desktop-layout` | `list` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `desktopLayoutJson` (the layout JSON structure as a string)
- **Layout JSON:** Defines widget areas, header, navigation panel, and auxiliary info panel
- **Update:** PUT replaces the entire layout -- GET first, modify, then PUT back

### CLI Examples

```bash
# List desktop layouts (v2)
wxcli cc-desktop-layout list

# Create a desktop layout
wxcli cc-desktop-layout create-desktop-layout --json-body '{
  "name": "Custom Sales Layout",
  "desktopLayoutJson": "{\"header\":{},\"navigation\":{},\"panel\":{}}"
}'

# Get a specific layout
wxcli cc-desktop-layout show --id "layout-uuid"

# Bulk export all layouts
wxcli cc-desktop-layout list-bulk-export

# Delete a layout
wxcli cc-desktop-layout delete --id "layout-uuid"
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
| POST | `/organization/{orgid}/agent-profile` | `create-agent-profile` | Create |
| POST | `/organization/{orgid}/agent-profile/bulk` | `create` | Bulk save |
| GET | `/organization/{orgid}/agent-profile/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/agent-profile/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/agent-profile/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/agent-profile/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/agent-profile/{id}` | `update` | Update |
| GET | `/organization/{orgid}/agent-profile/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/agent-profile` | `list-agent-profile` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `desktopLayoutId`, optional `dialNumberSettings`, `agentAvailableOptions`
- **Desktop layout link:** The profile references a desktop layout by ID
- **Buddy teams:** Configure which teams an agent can see and consult/transfer to

### CLI Examples

```bash
# List desktop profiles (v2)
wxcli cc-desktop-profile list-agent-profile

# Create a desktop profile
wxcli cc-desktop-profile create-agent-profile --json-body '{
  "name": "Sales Desktop Profile",
  "desktopLayoutId": "layout-uuid",
  "dialNumberSettings": {"agentDN": true, "otherDN": false}
}'

# Get a specific profile
wxcli cc-desktop-profile show --id "profile-uuid"

# Bulk export all profiles
wxcli cc-desktop-profile list-bulk-export

# Delete a profile
wxcli cc-desktop-profile delete --id "profile-uuid"
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
wxcli cc-business-hour show --id "bh-uuid"

# Delete business hours
wxcli cc-business-hour delete --id "bh-uuid"
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
wxcli cc-holiday-list show --id "hl-uuid"

# Delete a holiday list
wxcli cc-holiday-list delete --id "hl-uuid"
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
| GET | `/organization/{orgid}/auxiliary-code` | `list-auxiliary-code-organization` | List |
| POST | `/organization/{orgid}/auxiliary-code` | `create` | Create |
| POST | `/organization/{orgid}/auxiliary-code/bulk` | `create-bulk` | Bulk save |
| PATCH | `/organization/{orgid}/auxiliary-code/bulk` | `update` | Bulk partial update |
| GET | `/organization/{orgid}/auxiliary-code/bulk-export` | `list-bulk-export` | Bulk export |
| POST | `/organization/{orgid}/auxiliary-code/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/auxiliary-code/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/auxiliary-code/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/auxiliary-code/{id}` | `update-auxiliary-code` | Update |
| GET | `/organization/{orgid}/auxiliary-code/{id}/incoming-references` | `list` | List references |
| GET | `/organization/{orgid}/v2/auxiliary-code` | `list-auxiliary-code-v2` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `defaultCode` (boolean), `isActive`, `codeType` (IDLE_CODE or WRAP_UP_CODE)
- **Bulk partial update:** PATCH with array of partial updates -- only specified fields are changed
- **Default code:** One idle code and one wrap-up code can be marked as default

### CLI Examples

```bash
# List aux codes (v2)
wxcli cc-aux-code list-auxiliary-code-v2

# Create an idle code
wxcli cc-aux-code create --json-body '{
  "name": "Lunch Break",
  "codeType": "IDLE_CODE",
  "defaultCode": false,
  "isActive": true
}'

# Create a wrap-up code
wxcli cc-aux-code create --json-body '{
  "name": "Follow-up Required",
  "codeType": "WRAP_UP_CODE",
  "defaultCode": false,
  "isActive": true
}'

# Bulk partial update
wxcli cc-aux-code update --json-body '[
  {"id": "code1-uuid", "isActive": false},
  {"id": "code2-uuid", "name": "Extended Break"}
]'

# Delete an aux code
wxcli cc-aux-code delete --id "code-uuid"
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
| POST | `/organization/{orgid}/work-type/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
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
wxcli cc-work-types show --id "wt-uuid"

# Delete a work type
wxcli cc-work-types delete --id "wt-uuid"
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
| POST | `/organization/{orgid}/site/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
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
wxcli cc-site show --id "site-uuid"

# Check what references this site
wxcli cc-site list-incoming-references --id "site-uuid"

# Delete a site (must have no team references)
wxcli cc-site delete --id "site-uuid"
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
| POST | `/organization/{orgid}/cad-variable/purge-inactive-entities` | `create-purge-inactive-entities` | Purge inactive |
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
wxcli cc-global-vars show --id "var-uuid"

# Delete a variable
wxcli cc-global-vars delete --id "var-uuid"
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

## 21. Common Patterns

Most CC config entities follow a standard CRUD pattern with these operations:

| Operation | Method | Path Pattern | CLI Pattern | Description |
|-----------|--------|-------------|-------------|-------------|
| **List (v1)** | GET | `/organization/{orgid}/{resource}` | `list` or `list-{resource}-organization` | Basic list |
| **List (v2)** | GET | `/organization/{orgid}/v2/{resource}` | `list-{resource}` or `list-{resource}-v2` | Enhanced filtering, pagination |
| **Create** | POST | `/organization/{orgid}/{resource}` | `create` or `create-{resource}` | Create single entity |
| **Bulk save** | POST | `/organization/{orgid}/{resource}/bulk` | `create-bulk` or `create` | Create/update multiple entities |
| **Bulk export** | GET | `/organization/{orgid}/{resource}/bulk-export` | `list` or `list-bulk-export` | Export all entities (CSV-compatible) |
| **Purge inactive** | POST | `/organization/{orgid}/{resource}/purge-inactive-entities` | `create-purge-inactive-entities` | Permanently remove deactivated entities |
| **Get by ID** | GET | `/organization/{orgid}/{resource}/{id}` | `show` | Get single entity |
| **Update** | PUT | `/organization/{orgid}/{resource}/{id}` | `update` | Full replace |
| **Delete** | DELETE | `/organization/{orgid}/{resource}/{id}` | `delete` | Remove entity |
| **List references** | GET | `/organization/{orgid}/{resource}/{id}/incoming-references` | `list-incoming-references` | Show what references this entity |

### Pattern Notes

1. **v1 vs v2 vs v3 endpoints:** v2/v3 endpoints generally support better pagination (`page`, `pageSize`), FIQL-style filtering, and field selection (`attributes` parameter). Prefer v2/v3 when available.

2. **Bulk save vs create:** Bulk save (`/bulk`) accepts an array and can create or update multiple entities in one call. Single create returns the created entity.

3. **Purge inactive:** Soft-deleted entities remain in the system until purged. The purge endpoint permanently removes them. This is irreversible.

4. **Incoming references:** Before deleting an entity, check incoming references to see what depends on it. Deleting an entity that is referenced by another entity may fail or cause cascading issues.

5. **PUT is full replace:** All update endpoints use PUT (full replacement). Always GET the entity first, modify the fields you need, and PUT the full object back. The only exceptions are the bulk PATCH endpoints on `auxiliary-code` and `user`.

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

## 22. Gotchas

1. **Different base URL.** The CC API uses `api.wxcc-{region}.cisco.com`, not `webexapis.com`. Set the region with `wxcli set-cc-region <region>` (defaults to `us1`). Using the wrong base URL produces connection errors.

2. **CC-specific OAuth scopes.** CC endpoints require `cjp:config_read` and `cjp:config_write` scopes, not `spark-admin:*` scopes. A standard Webex admin token without CC scopes gets 403 errors. The CLI detects this and prints a scope tip.

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

23. **Personal access tokens lack CC scopes.** PATs from developer.webex.com do NOT carry `cjp:config_read` or `cjp:config_write`, even for full admins on CC-provisioned orgs. Two options for CC config operations: (a) **OAuth integration** — select CC scopes explicitly and complete the OAuth authorization flow; adding scopes to an existing integration does not update previously issued tokens, you must re-authorize; (b) **Service App with CJP scopes** — recommended for production automation and server-to-server use; no interactive login required after the org admin authorizes the app, making it suitable for CI/CD pipelines and backend services. Note: all CC integration scopes work with Service Apps except `spark:applications_token` and `spark:kms`.

24. **Global Variable names are immutable.** The CC API returns 400 `"name: should not be modified"` if you attempt to change the `name` field via PUT update. To rename a variable, delete and recreate it. Note that any flows referencing the old variable ID will need to be updated.

25. **Flow Designer HTTP Connector handles auth and base URL automatically.** The CC HTTP Connector (created in Control Hub → Contact Center → Integrations → Connectors) stores the regional base URL and auth tokens for you. In the Flow Designer HTTP Request node, provide only the **request path**, not the full URL — e.g., `/organization/{orgid}/cad-variable` for Global Variables or `/search` for the Search API. Toggle "Use Authenticated Endpoint" and select the connector; no manual token management is needed in flows. When creating the connector, choose the access level: Read-Only (GET) or Read-Write (POST/PUT/DELETE).

26. **Derive the CC regional base URL from the access token.** The Webex access token has three underscore-separated parts: `token.split('_')` → `[accessToken, ciCluster, orgId]`. The middle segment (`ciCluster`) maps directly to the regional base URL: `https://api.wxcc-{ciCluster}.cisco.com`. Available regions: `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1`. This is useful for production apps that need to determine the correct CC API endpoint dynamically without hardcoding a region.

---

## 23. See Also

- [Contact Center: Routing](contact-center-routing.md) -- Dial plans, campaigns, flows, audio files, contact lists, dial numbers
- [Contact Center: Analytics](contact-center-analytics.md) -- AI, monitoring, subscriptions, tasks, search
- [Contact Center: Journey](contact-center-journey.md) -- JDS: workspaces, persons, identity, profile views, events
- [Authentication](authentication.md) -- CC-specific OAuth scopes, region configuration, and token setup
- [Contact Center Skill](../../.claude/skills/contact-center/SKILL.md) -- Guided workflow for provisioning agents, queues, teams, flows, campaigns via wxcli
- `CLAUDE.md` (project root) -- CC region setup, CLI integration notes
