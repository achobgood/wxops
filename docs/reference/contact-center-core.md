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

# Get agent activities — an event log, not the roster.
# --from/--to are EPOCH MILLISECONDS and the window must be <= 24 hours (verified live 2026-10-13:
# ISO strings -> 400 "from should be of type java.lang.Long"; a 27-day window -> 400 "The duration
# between from and to cannot exceed 1 days"; from older than 12 months -> 400). Example = 2026-10-12 UTC.
wxcli cc-agents list-activities --from 1791763200000 --to 1791849600000

# Get agent statistics (same rules: epoch ms, <= 24h — 400 "Querying only supported for 24 hours at a time")
wxcli cc-agents list-statistics --agent-ids "..." --from 1791763200000 --to 1791849600000

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
curl "https://api.wxcc-us1.cisco.com/v1/agents/activities?orgId={orgUuid}&from=1791763200000&to=1791849600000" \
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
  "name": "Burnout events",
  "eventTypes": ["EVENT_TYPE"],
  "destinationUrl": "https://example.com/webhook"
}'

# Record a burnout event action
wxcli cc-agent-wellbeing create-action --json-body '{
  "agentId": "...",
  "interactionId": "...",
  "clientId": "Acme",
  "actionType": "Break Played",
  "actionDateType": 1617536244000
}'
```

> **Unverified:** both bodies are from the spec, not a live call. `create` registers a webhook
> subscription (`name`, `eventTypes` and `destinationUrl` are required; `destinationUrl` must be
> HTTPS) — it does not take an agent. The spec does not list the burnout event-type names (its
> generic example is `agent:login`). `create-action` records what was done about an agent's
> burnout index: `actionType` is free text (spec example: "Break Played, Supervisor Notified,
> etc.") and `actionDateType` is the epoch-ms time it happened.

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

# Bulk assign a dynamic skill to users (verified live 2026-10-13; see the note below this block)
wxcli cc-users update-dynamic-skill "skill-uuid" --json-body '{
  "items": [
    {"itemIdentifier": 1, "requestAction": "SAVE",
     "item": {"organizationId": "cc-org-uuid", "userId": "user1-uuid",
              "skillId": "skill-uuid", "proficiencyValue": 7}},
    {"itemIdentifier": 2, "requestAction": "SAVE",
     "item": {"organizationId": "cc-org-uuid", "userId": "user2-uuid",
              "skillId": "skill-uuid", "proficiencyValue": 7}}
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

**Verified live 2026-10-13** (the sandbox tenant, temporary dynamic skill, removed afterwards): the body above is accepted as written. The response is per item — `{"items":[{"itemIdentifier":1,"status":200,"href":…}]}` — so check each item's `status`, not just the HTTP code. Read back with `wxcli cc-users show-by-dynamic-skill-id SKILL_ID --fields data` (`dynamicSkill.proficiencyValue` comes back as a **string**, e.g. `"7"`). SAVE on a user who already has the skill updates it **without** `id` or `version`. `item.organizationId` and `item.skillId` are both **optional** here (omitting each still returned 200 and changed the value — the path supplies the skill) — the spec's "required for all bulk save operations" and "`id` mandatory when updating" do not hold for this endpoint. Not tested by omission: `userId`, `itemIdentifier`, `requestAction`. Remove an assignment with `{"items":[{"itemIdentifier":1,"item":{"userId":"USER_ID"},"requestAction":"DELETE"}]}` (verified, 200, read-back empty). The skill must be created with `"dynamicSkill": true`; a normal skill returns 400 "is not a dynamic skill". The value field must match the skill's type — `proficiencyValue` (0-10) verified; `booleanValue`, `textValue`, `enumSkillValues` are from the spec, unverified.

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
  "profileType": "STANDARD_AGENT",
  "active": true,
  "permissionAccessLevel": "ALL",
  "resourceAccessLevel": "ALL"
}'

# Get profile ACL (v3) — returns the whole ACL object (JSON); before 2026-10-13 the CLI printed []
wxcli cc-user-profiles list-acl "profile-uuid"

# Delete a user profile (v3)
wxcli cc-user-profiles delete "profile-uuid"
```

> **Unverified:** the `create` body is from the spec, not a live call. `name`, `profileType`,
> `active`, `permissionAccessLevel` and `resourceAccessLevel` are required. There is no
> `accessRights` key: to limit a profile to particular resources, set `resourceAccessLevel` to
> `SPECIFIC` and list `resourceCollections`.

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
- **Single create vs bulk:** `cc-queue create` is the **bulk** endpoint (`/contact-service-queue/bulk`); the single-queue create is `cc-queue create-contact-service-queue`. Its `--help` marks `name`, `queueType`, `checkAgentAvailability`, `channelType`, `serviceLevelThreshold`, `maxActiveContacts`, `maxTimeInQueue` and `active` required; the `--json-body` example also carries `queueRoutingType` and `callDistributionGroups` (see gotcha 27)
- **Read team routing with `show`, not `list`:** `list-contact-service-queue-v2` omits `callDistributionGroups` (gotcha 28)
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
  "add": ["agent1-uuid", "agent2-uuid"],
  "remove": []
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

> **Unverified:** the `create-reassign-agents` body is from the spec, not a live call: it is two
> lists of agent ids, `add` and `remove`, not an `agentIds` list with an action verb.

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
# Get queue statistics. --from/--to are EPOCH MILLISECONDS and the window must be under 24 hours
# (verified live 2026-10-13: ISO strings -> 400 "from should be of type java.lang.Long"; a 27-day
# window -> 400 "Querying only supported for 24 hours at a time"). Example = 2026-10-12 UTC.
wxcli cc-queue-stats list --from 1791763200000 --to 1791849600000

# Get statistics for a specific queue (--from/--to are required on every call)
wxcli cc-queue-stats list --from 1791763200000 --to 1791849600000 --queue-ids "queue-uuid"
```

### Raw HTTP

```bash
curl "https://api.wxcc-us1.cisco.com/v1/queues/statistics?orgId={orgUuid}&from=1791763200000&to=1791849600000" \
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
- **Wiring an entry point to a flow:** set `flowId` (the flow's id) and `flowTagId` (which published-version tag to run). `"Latest"` works; Live, Test and Dev tags also exist. A newly published flow has only the `Latest` tag, so use `"Latest"` until you tag a version otherwise (gotcha 29)

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

# Wire an entry point to a published flow (add these two fields to the create body or an update)
#   "flowId": "<flow id>", "flowTagId": "Latest"
# Verified live 2026-10-13: create with flowId + flowTagId "Latest" saved, and show read both back.

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
  -d '{"name":"Main IVR","entryPointType":"INBOUND","channelType":"TELEPHONY","active":true,"serviceLevelThreshold":60,"maximumActiveContacts":100}'
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
| GET | `/organization/{orgid}/team/bulk-export` | _(no CLI command)_ | Bulk export (the `cc-team` group has no `list-bulk-export` subcommand: "No such command", verified live 2026-10-13) |
| POST | `/organization/{orgid}/team/purge-inactive-entities` | `delete-purge-inactive-entities` | Purge inactive |
| GET | `/organization/{orgid}/team/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/team/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/team/{id}` | `update` | Update |
| GET | `/organization/{orgid}/team/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/team` | `list-team` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `siteId` (team must belong to a site), `active`, `teamType` and `teamStatus`. Verified live 2026-10-13: `{name, siteId}` alone (the old example) → `400 "[active: should be either true or false.]"`; adding `active` but not `teamType` → `500 "Processing failed"` (the CLI retries it three times first); adding `teamType` but not `teamStatus` → `409 "Column 'team_status' cannot be null"`. Enums are UPPER CASE: `teamType` is `AGENT` or `CAPACITY` (`"Agent"` → 400 listing `[CAPACITY, AGENT]`); `teamStatus` is `IN_SERVICE` or `NOT_AVAILABLE`. Optional `description`, `skillProfileId`, `userIds`, `desktopLayoutId`, `multiMediaProfileId` (the last two read back on `show`, verified live 2026-10-13 — **the desktop layout is attached to the team, not to the desktop profile**, see §14).
- **CLI quirk:** `cc-team create` and `cc-team update` mark `--team-dto` required even when `--json-body` is given, so a bare `--json-body` call exits `Missing option '--team-dto'` (verified live 2026-10-13). Pass any placeholder (`--team-dto x`); `--json-body` overrides it.
- **Update:** Can reassign team to different site, rename, change capacity. It is a full replace and the body **must carry `"id"` equal to the URL id** (`400 "Invalid id: id in payload and URL should be same"` otherwise). `--verify` works and reported `all 7 sent field(s) match` (verified live 2026-10-13).
- **List vs show:** `list` / `list-team` omit `userIds`, `skillProfileId`, `desktopLayoutId`, `multiMediaProfileId`, `description` and `queueRankings`; read team membership with `show` (verified live 2026-10-13).
- **References:** Shows which queues, routing strategies, and profiles reference this team

### CLI Examples

```bash
# List all teams (v2)
wxcli cc-team list-team

# Create a team (verified live 2026-10-13; --team-dto is a required-but-ignored placeholder, see Key Parameters)
wxcli cc-team create --team-dto x --json-body '{
  "name": "Sales Team",
  "siteId": "site-uuid",
  "active": true,
  "teamType": "AGENT",
  "teamStatus": "IN_SERVICE"
}'

# Get a specific team
wxcli cc-team show "team-uuid"

# Bulk save multiple teams. The body is {"items":[{"itemIdentifier":N,"item":{...}}]}; the
# earlier bare-array form returns 400 "Bad payload: Cannot deserialize" (verified live 2026-10-13).
# Each item needs the same fields as a single create; `requestAction` was not needed to create.
# (Tested with a single item; a second item uses the same shape.)
wxcli cc-team create-bulk --json-body '{"items":[
  {"itemIdentifier":0,"item":{"name":"Support Team A","siteId":"site-uuid","active":true,"teamType":"AGENT","teamStatus":"IN_SERVICE"}},
  {"itemIdentifier":1,"item":{"name":"Support Team B","siteId":"site-uuid","active":true,"teamType":"AGENT","teamStatus":"IN_SERVICE"}}
]}'

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
  -d '{"name":"Sales Team","siteId":"site-uuid","active":true,"teamType":"AGENT","teamStatus":"IN_SERVICE"}'
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

- **Create:** Requires `name`, `serviceLevelThreshold`, `skillType` and `active`. `skillType` is **UPPER CASE**: `PROFICIENCY`, `BOOLEAN`, `TEXT`, `ENUM`
- **PROFICIENCY type:** Values 0-10, used for competency-based routing
- **BOOLEAN type:** True/false, used for capability flags (e.g., "speaks_spanish")
- **ENUM type:** Requires `enumSkillValues` — one `{"name": …}` object per allowed value
- **TEXT type:** Free-form text value
- **Dynamic skill:** add `"dynamicSkill": true` to create a skill that `cc-users update-dynamic-skill` can assign (a normal skill returns 400 "is not a dynamic skill")

> **Verified live 2026-10-13:** `cc-skill create` with `"skillType":"PROFICIENCY"` and
> `"dynamicSkill":true` succeeded; the spec's title-case spelling (`"Proficiency"`, also the value
> the generated `--help` example shows) was rejected with a 400 listing the valid values as
> `BOOLEAN, ENUM, PROFICIENCY, TEXT`. Note the opposite convention from a sibling field: Global
> Variable `variableType` requires **title** case (gotcha 21). `--help` and the spec are wrong here.
> **Unverified:** the `enumSkillValues` shape (from the spec).

### CLI Examples

```bash
# List all skills (v2)
wxcli cc-skill list-skill

# Create a proficiency skill
wxcli cc-skill create --json-body '{
  "name": "Product Knowledge",
  "skillType": "PROFICIENCY",
  "serviceLevelThreshold": 60,
  "active": true
}'

# Create a boolean skill
wxcli cc-skill create --json-body '{
  "name": "Spanish Speaker",
  "skillType": "BOOLEAN",
  "serviceLevelThreshold": 60,
  "active": true
}'

# Create an enum skill
wxcli cc-skill create --json-body '{
  "name": "Region",
  "skillType": "ENUM",
  "serviceLevelThreshold": 60,
  "active": true,
  "enumSkillValues": [{"name": "EAST"}, {"name": "WEST"}, {"name": "CENTRAL"}]
}'

# Get a specific skill
wxcli cc-skill show "skill-uuid"

# Delete a skill
wxcli cc-skill delete "skill-uuid"

# Deactivate a skill (PUT replaces the resource, so resend name, type and threshold)
wxcli cc-skill update "skill-uuid" --name "Product Knowledge" --skill-type "PROFICIENCY" \
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
  -d '{"name":"Product Knowledge","skillType":"PROFICIENCY","serviceLevelThreshold":60,"active":true}'
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

- **Create:** Requires `name` and at least one entry in `activeSkills` (non-enum skills) or `activeEnumSkills` (enum skills). Verified live 2026-10-13: the body this section showed before that date (`skills:[{skillId, skillValue}]`) returns `400 "Atleast one skill is mandatory."` — `skills` and `skillValue` are not fields. A profile read back with `show` carries `activeSkills[]` (`id`, `skillId`, plus `proficiencyValue` or `booleanValue`) — that is the shape to send.
- **Skill values:** a `PROFICIENCY` skill takes `{"skillId":"…","proficiencyValue":8}`; a `BOOLEAN` skill takes `{"skillId":"…","booleanValue":true}` (both created and read back live 2026-10-13); an `ENUM` skill goes in the separate `activeEnumSkills` array as `{"enumSkillValueId":"<id of one value of the enum skill>"}` (created and read back live 2026-10-13; the ids come from `enumSkillValues[].id` on `cc-skill show`). `TEXT` skills use `textValue` per the spec — **Unverified:** not tested live.
- **CLI quirk:** `cc-skill-profile create` and `update` mark `--skill-profile-dto` required even with `--json-body` (`Missing option '--skill-profile-dto'`); pass a placeholder (`--skill-profile-dto x`). Same pattern as `cc-team` (§9). Verified live 2026-10-13.
- **Update:** full replace with `"id"` in the body. Re-sending `activeSkills` **without each entry's own `id`** returns `409 "Duplicate entry '<org>-<profile>-…' for key 'active_skill.UK…'"`; copy the `activeSkills[].id` values from `show` and the update works (`proficiencyValue` 8 → 5 read back; `--verify` reports `activeSkills` as "differ" only because the server reorders the array). Verified live 2026-10-13.

### CLI Examples

```bash
# List all skill profiles (v2)
wxcli cc-skill-profile list-skill-profile

# Create a skill profile (proficiency + boolean skills; verified live 2026-10-13: created, read back, updated, deleted)
wxcli cc-skill-profile create --skill-profile-dto x --json-body '{
  "name": "Senior Sales Agent",
  "activeSkills": [
    {"skillId": "product-knowledge-uuid", "proficiencyValue": 8},
    {"skillId": "spanish-speaker-uuid", "booleanValue": true}
  ]
}'

# An ENUM skill is attached by the id of one of its values, in a separate array (verified live 2026-10-13)
wxcli cc-skill-profile create --skill-profile-dto x --json-body '{
  "name": "East Region",
  "activeEnumSkills": [{"enumSkillValueId": "east-value-uuid"}]
}'

# Get a specific skill profile
wxcli cc-skill-profile show "profile-uuid"

# List skill profiles (v1 list, GET /skill-profile; there is no bulk-export command, see the table)
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
  -d '{"name":"Senior Sales Agent","activeSkills":[{"skillId":"...","proficiencyValue":8}]}'
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

- **Create:** Requires `name`, channel capacities (`telephony`, `chat`, `email`, `social` counts), `active`, `blendingModeEnabled`, `blendingMode` **and a `manuallyAssignable` object**. Verified live 2026-10-13: without `manuallyAssignable` every create returned `400 "Manually Assignable missing for the multimedia Profile type"` — including the two bodies this section showed before that date; `"manuallyAssignable":{}` was rejected the same way, and `{"telephony":0,"chat":0,"email":0,"social":0}` was accepted (the server fills `workItem` and `customMessaging` with 0). Omitting `active`/`blendingModeEnabled`/`blendingMode` → `400` naming each.
- **`blendingMode` enum (UPPER CASE):** `BLENDED`, `BLENDED_REALTIME`, `EXCLUSIVE` (lower case `blended` → 400 listing exactly these three; verified live 2026-10-13). `EXCLUSIVE` with `blendingModeEnabled:false` created and read back correctly. The system default profiles use `BLENDED` with `blendingModeEnabled:false`.
- **Limits:** `telephony` above 1 → `400 "Maximum limit 1 reached for telephony assigned to multimedia profile."` (verified live 2026-10-13).
- **Update:** full replace, and the body must carry `"id"` equal to the URL id (`400 "Invalid id: id in payload and URL should be same"` without it). A `version` in the body is not enforced (`version:99` accepted; the server increments its own). `show` does not return `version`, so `--verify` always reports `version` and the six-key `manuallyAssignable` expansion as "differ" — server normalisation, not a failed write (verified live 2026-10-13).
- **Delete:** a profile used by a site returns `412 "referred in other entities"` with `"referencedEntities":["site"]`; `list-incoming-references` names the site (verified live 2026-10-13).
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
  "blendingMode": "EXCLUSIVE",
  "manuallyAssignable": {"telephony": 0, "chat": 0, "email": 0, "social": 0}
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
  "blendingMode": "BLENDED",
  "manuallyAssignable": {"telephony": 0, "chat": 0, "email": 0, "social": 0}
}'
# Both bodies above verified live 2026-10-13 (created, read back with `show`, deleted).

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
  -d '{"name":"Voice Only","telephony":1,"chat":0,"email":0,"social":0,"active":true,"blendingModeEnabled":false,"blendingMode":"BLENDED","manuallyAssignable":{"telephony":0,"chat":0,"email":0,"social":0}}'
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
- **Layout JSON:** Defines widget areas, header, navigation panel, and auxiliary info panel. **The server validates it.** Verified live 2026-10-13: the placeholder `{"header":{},"navigation":{},"panel":{}}` this section showed before that date → `400 "Provided layout json is not valid"` with `"layoutJsonErrors":["no 'area' property found"]`; a minimal `{"agent":{"version":"0.1.0","appTitle":"zz","area":{"advancedHeader":[],"panel":{},"navigation":[]}}}` → `layoutJsonErrors":["error in 'agent' layout","panel - property 'comp' is REQUIRED [line: 1]"]`. The real shape is `{"agent":{…,"area":{"advancedHeader":[…],"panel":{"comp":…},"navigation":[…]}},"supervisor":{…},"supervisorAgent":{…}}`. The reliable way to author one is to `show` the system "Global Layout" (`list-desktop-layout`), copy its `jsonFileContent`, and edit that. A copy of it created (`global:false`, `status:true`, `validated:true`), read back, updated with `--verify` (`all 10 sent field(s) match`) and deleted.
- **Update:** PUT replaces the entire layout -- GET first, modify, then PUT back (full body including `jsonFileContent`)

### CLI Examples

```bash
# List desktop layouts (v2)
wxcli cc-desktop-layout list-desktop-layout

# Create a desktop layout. jsonFileContent must be a VALID layout (see Key Parameters) — the
# placeholder below is rejected with 400 "Provided layout json is not valid" (verified live 2026-10-13);
# paste the jsonFileContent string of the system "Global Layout" instead.
wxcli cc-desktop-layout create --json-body '{
  "name": "Custom Sales Layout",
  "editedBy": "admin@example.com",
  "jsonFileName": "sales-layout.json",
  "jsonFileContent": "{\"agent\":{…},\"supervisor\":{…},\"supervisorAgent\":{…}}",
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
  -d '{"name":"Custom Sales Layout","editedBy":"admin@example.com","jsonFileName":"sales-layout.json","jsonFileContent":"<valid layout JSON as a string>","global":false,"status":true,"defaultJsonModified":true,"validated":true}'
```

---

## 14. Desktop Profiles (`cc-desktop-profile`)

Desktop profiles (API path: `agent-profile`) control agent desktop behavior: which login voice options an agent may use, which queues / entry points / idle and wrap-up codes / buddy teams they can access, outdial, auto wrap-up and other feature toggles. (Which layout an agent sees is set on the team, not here — see Key Parameters.)

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

- **Create:** Verified live 2026-10-13 — the body this section showed before that date (`name`, `desktopLayoutId`, `dialNumberSettings`) is rejected, and a body with only `name` is rejected with a `400` listing what is missing. Required: `name`, `parentType` (`ORGANIZATION` or `SITE`; anything else → 400 listing both), `accessQueue`, `accessEntryPoint`, `accessBuddyTeam` (each `ALL`, `SPECIFIC` or `NONE`), `accessIdleCode`, `accessWrapUpCode` (each `ALL` or `SPECIFIC` — no `NONE`), `agentDNValidation` (`PROVISIONED_VALUE`, `SPECIFIC` or `NONE`), `viewableStatistics` (an object, e.g. `{"agentStats":true,"accessQueueStats":"ALL","loggedInTeamStats":true,"accessTeamStats":"ALL"}`) and `loginVoiceOptions` (a non-empty array of `BROWSER`, `AGENT_DN`, `EXTENSION`; `"WEBRTC"` → 400 listing those three). `active` defaults to `false` when omitted — send `"active": true`.
- **No `desktopLayoutId`, `dialNumberSettings` or `agentAvailableOptions` on a profile.** Verified live 2026-10-13: a PUT carrying all three returned 200 and `--verify` reported each `sent … now '<not present in read-back>'` — accepted and silently dropped. The desktop layout is attached to the **team** (`desktopLayoutId` on `cc-team`, §9; read back live), not the profile. Do not infer a layout link from a profile.
- **CLI quirk:** `cc-desktop-profile create` and `update` mark `--agent-profile-dto` required even with `--json-body`; pass a placeholder (`--agent-profile-dto x`) — same pattern as `cc-team` (§9).
- **Update:** full replace; the body must carry `"id"` equal to the URL id (`400 "Invalid id: id in payload and URL should be same"` otherwise). `viewableStatistics` always shows as "differ" under `--verify` because the server adds an `id` and empty arrays to it — normalisation, not a failed write.
- **Outdial:** `outdialEnabled:true` requires `outdialEntryPointId` (`400 "outdialEntryPointId should be specified when outdialEnabled is true"`) and, when `dialPlanEnabled` is false, an `addressBookId` (`400 "addressBookId should be specified when outdialEnabled is true and dialPlanEnabled is false"`). `outdialANIId` points at an Outdial ANI profile (`cc-outdial-ani`, see [contact-center-routing.md](contact-center-routing.md) §3); with it set, the ANI profile's `list-incoming-references` names the desktop profile and deleting the ANI returns `412 "referred in other entities"` with `"referencedEntities":["desktop-profile"]`. Verified live 2026-10-13.
- **List omits `loginVoiceOptions`.** `list`, `list-agent-profile` return `loginVoiceOptions: null` for every profile (the system default "Agent-Profile" really holds `["BROWSER","EXTENSION","AGENT_DN"]`), and `--attributes loginVoiceOptions` → `400 "Invalid requested columns :loginVoiceOptions"`. Read it with `show` per profile (verified live 2026-10-13). The list also omits `dialPlans`, `viewableStatistics`, `wrapUpCodes`, `idleCodes`, `queues`, `entryPoints` and `buddyTeams`.
- **Buddy teams:** Configure which teams an agent can see and consult/transfer to
- **`loginVoiceOptions`** — array of `AGENT_DN` | `EXTENSION` | `BROWSER` (`AgentProfileDTO` in `specs/webex-contact-center.json`). This is the **gate on browser/WebRTC audio**: it is what an agent's `Profile.loginVoiceOptions` reads back as, and `stationLogin({loginOption:'BROWSER'})` fails for an agent whose profile omits `BROWSER` even when everything else is correct. `dialNumberSettings` and `agentAvailableOptions` are *not* this field — do not read either one to decide whether browser audio is available. See [contact-center-agent-sdk.md](contact-center-agent-sdk.md) §1.

### CLI Examples

```bash
# List desktop profiles (v2)
wxcli cc-desktop-profile list-agent-profile

# Create a desktop profile
# (verified live 2026-10-13: created, read back, deleted; `active` defaults to false so it is sent)
wxcli cc-desktop-profile create --agent-profile-dto x --json-body '{
  "name": "Sales Desktop Profile",
  "parentType": "ORGANIZATION",
  "active": true,
  "accessQueue": "ALL",
  "accessEntryPoint": "ALL",
  "accessBuddyTeam": "ALL",
  "accessIdleCode": "ALL",
  "accessWrapUpCode": "ALL",
  "agentDNValidation": "NONE",
  "loginVoiceOptions": ["BROWSER"],
  "viewableStatistics": {"agentStats": true, "accessQueueStats": "ALL", "loggedInTeamStats": true, "accessTeamStats": "ALL"}
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
  -d '{"name":"Sales Desktop Profile","parentType":"ORGANIZATION","active":true,"accessQueue":"ALL","accessEntryPoint":"ALL","accessBuddyTeam":"ALL","accessIdleCode":"ALL","accessWrapUpCode":"ALL","agentDNValidation":"NONE","loginVoiceOptions":["BROWSER"],"viewableStatistics":{"agentStats":true,"accessQueueStats":"ALL","loggedInTeamStats":true,"accessTeamStats":"ALL"}}'
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
| GET | `/organization/{orgid}/business-hours/bulk-export` | _(no CLI command)_ | Bulk export (`cc-business-hour --help` lists no `list-bulk-export`; verified live 2026-10-13) |
| GET | `/organization/{orgid}/business-hours/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/business-hours/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/business-hours/{id}` | `update` | Update |
| GET | `/organization/{orgid}/business-hours/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/business-hours` | `list-business-hours` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `timezone`, `workingHours` (array of `{name, days, startTime, endTime}` entries). Verified live 2026-10-13: `"workingHours":[{"name":"Weekday","days":["MON","TUE","WED","THU","FRI"],"startTime":"07:00","endTime":"19:00"}]` created OK; this matches `cc-business-hour create --help`. An earlier version of this doc and the skill showed `businessHours:[{day:"monday",...}]`, which is not what `--help` shows (gotcha 30)
- **Business hours structure:** Each `workingHours` entry names a block, lists its days as three-letter codes (`MON`..`SUN`), and gives a start and end time
- **Timezone:** Important for multi-region deployments; hours are evaluated in the configured timezone
- **Update and read-back:** the doc's create body (08:00-17:00, `America/New_York`) created and read back, and a PUT with `"id"` in the body changed the hours to 09:00-18:00 (verified live 2026-10-13). The server returns `days` in arbitrary order (`TUE, THU, FRI, MON, WED`), so `--verify` flags `workingHours` as "differ" after an update — a reorder, not a failed write.

### CLI Examples

```bash
# List business hours (v2)
wxcli cc-business-hour list-business-hours

# Create business hours
wxcli cc-business-hour create --json-body '{
  "name": "US East Business Hours",
  "timezone": "America/New_York",
  "workingHours": [
    {"name": "Weekday", "days": ["MON", "TUE", "WED", "THU", "FRI"], "startTime": "08:00", "endTime": "17:00"}
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
  -d '{"name":"US East Business Hours","timezone":"America/New_York","workingHours":[{"name":"Weekday","days":["MON","TUE","WED","THU","FRI"],"startTime":"08:00","endTime":"17:00"}]}'
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
| GET | `/organization/{orgid}/holiday-list/bulk-export` | _(no CLI command)_ | Bulk export (`cc-holiday-list --help` lists no `list-bulk-export`; verified live 2026-10-13) |
| GET | `/organization/{orgid}/holiday-list/{id}` | `show` | Get by ID |
| DELETE | `/organization/{orgid}/holiday-list/{id}` | `delete` | Delete |
| PUT | `/organization/{orgid}/holiday-list/{id}` | `update` | Update |
| GET | `/organization/{orgid}/holiday-list/{id}/incoming-references` | `list-incoming-references` | List references |
| GET | `/organization/{orgid}/v2/holiday-list` | `list-holiday-list` | List (v2) |

### Key Parameters

- **Create:** Requires `name`, `holidays` array with `{name, startDate, endDate}` entries. Verified live 2026-10-13: `{name, date}` (the shape this section showed before that date) → `400 "holidays[1].endDate: Format excepted (yyyy-MM-dd)"` (sic); `{"name":"New Year","startDate":"2026-01-01","endDate":"2026-01-01"}` (a one-day holiday repeats the date) created and read back with `show`. Update (`--verify`) is a full replace with `"id"` in the body and reported `all N sent field(s) match`.
- **Date format:** `YYYY-MM-DD`
- **Recurring:** the spec's per-holiday field is `frequency` (example value `DontRepeat`) with an optional `recurrence` object. Verified live 2026-10-13: `"frequency":"DontRepeat"` is accepted and read back; `"DONT_REPEAT"` → `400 "Bad payload: Cannot deserialize"` (no value list in the message). **Unverified:** the other `frequency` values and the `recurrence` fields; `recurring: true` (the earlier claim here) is not a field.

### CLI Examples

```bash
# List holiday lists (v2)
wxcli cc-holiday-list list-holiday-list

# Create a holiday list
wxcli cc-holiday-list create --json-body '{
  "name": "US Federal Holidays 2026",
  "holidays": [
    {"name": "New Year", "startDate": "2026-01-01", "endDate": "2026-01-01"},
    {"name": "MLK Day", "startDate": "2026-01-19", "endDate": "2026-01-19"},
    {"name": "Presidents Day", "startDate": "2026-02-16", "endDate": "2026-02-16"},
    {"name": "Memorial Day", "startDate": "2026-05-25", "endDate": "2026-05-25"},
    {"name": "Independence Day", "startDate": "2026-07-04", "endDate": "2026-07-04"},
    {"name": "Labor Day", "startDate": "2026-09-07", "endDate": "2026-09-07"},
    {"name": "Thanksgiving", "startDate": "2026-11-26", "endDate": "2026-11-26"},
    {"name": "Christmas", "startDate": "2026-12-25", "endDate": "2026-12-25"}
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
  -d '{"name":"US Federal Holidays 2026","holidays":[{"name":"New Year","startDate":"2026-01-01","endDate":"2026-01-01"}]}'
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

- **Create:** Requires `name`, `defaultCode` (boolean), `active`, `workTypeId`, `workTypeCode` (IDLE_CODE or WRAP_UP_CODE). Verified live 2026-10-13: the CLI examples below create correctly when `workTypeId` is a real work-type ID from `cc-work-types list-work-type` (a made-up one → `400 "Given workTypeId does not belong to the organization"`); `{name}` alone → `400 "defaultCode: should be either true or false."`; no `workTypeCode` → `409 "Column 'work_type_code' cannot be null"`; `Idle_Code` (wrong case) → `400 "Bad payload: Cannot deserialize"`. **The server does not check that `workTypeCode` matches the work type's own code** — a `WRAP_UP_CODE` created against the Default Idle Work Type was accepted and read back with that mismatch. The field names are `workTypeCode` and `active`; `codeType` / `isActive` (used in the older Raw HTTP example) are not fields — that body returned `400 "active: should be either true or false."`.
- **Bulk partial update (`cc-aux-code update`, PATCH):** the body is `{"items":[{"itemIdentifier":0,"item":{"id":"…", …changed fields…}}]}`, **not** a bare array — the bare-array form (with `isActive`) shown here before 2026-10-13 returns `400 "Bad payload: Cannot deserialize"`. `name` and `description` changes applied and read back. **`active` is silently ignored:** `{"id":…,"active":false}` returned `status:200, operationType:UPDATE` but `show` still read `active:true`, and the reverse (`active:true` on an inactive code, bare or with `"requestAction":"save"`) also changed nothing; `requestAction` accepts only `save` or `delete`, and upper case `"SAVE"` worked too (a name/description change with it returned `status:200, operationType:UPDATE` and read back; `active` still ignored in 3 of 3 attempts, including a full item with `workTypeId`/`workTypeCode`/`defaultCode`) (`400 "Request action should be valid (save|delete)"`). To deactivate, use the PUT (`update-auxiliary-code`, full body incl. `id`; `--verify` confirmed `active:false`).
- **Default code:** One idle code and one wrap-up code can be marked as default. **Creating a code with `defaultCode:true` silently demotes the current default of the same type** — verified live 2026-10-13: creating a default idle code flipped the org's existing default idle code (`Meeting`) to `defaultCode:false` with no warning; re-setting the old default (`update` with `{"id":…,"defaultCode":true}`, which worked) demoted the new one. (Whether deleting the new default alone would have restored the old one was not tested.) Check `list-auxiliary-code --fields '[?defaultCode].name'` before and after.
- **Bulk export omits system codes:** on this org `list-auxiliary-code --all` and `list --all` returned 21 codes (8 with `isSystemCode:true`: Agent_Busy, RONA, WellbeingBreak, …) while `list-bulk-export --all` returned 13, none of them system codes (verified live 2026-10-13). Count or audit codes from the list, not the export.
- **Delete:** a deleted code returns 404 on `show` afterwards and is gone from the list (hard delete from the API's view). A work type that a code uses cannot be deleted: `412 "referred in other entities"`, `"referencedEntities":["auxiliary-code"]` (§18).

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

# Bulk partial update (verified live 2026-10-13: `name` / `description` / `defaultCode` apply;
# `active` is silently ignored — deactivate with `update-auxiliary-code`, a full PUT)
wxcli cc-aux-code update --json-body '{"items":[
  {"itemIdentifier": 0, "item": {"id": "code2-uuid", "name": "Extended Break"}}
]}'

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
  -d '{"name":"Lunch Break","workTypeCode":"IDLE_CODE","workTypeId":"<idle work type id>","defaultCode":false,"active":true}'
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

# Create a work type. `workTypeCode` (IDLE_CODE or WRAP_UP_CODE) and `active` are required —
# verified live 2026-10-13: without them the old `{name, description}` body returned
# 400 "workTypeCode: Allowed values: [WRAP_UP_CODE, IDLE_CODE]", then 400 "active: should be either true or false."
wxcli cc-work-types create --json-body '{
  "name": "Outbound Campaign",
  "description": "Outbound dialing work",
  "workTypeCode": "IDLE_CODE",
  "active": true
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
  -d '{"name":"Outbound Campaign","description":"Outbound dialing work","workTypeCode":"IDLE_CODE","active":true}'
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

- **Create:** Requires `name`, `active` and `multimediaProfileId` (an existing multimedia profile, §12 — a site cannot be created without one). Verified live 2026-10-13: `{"name": "…"}` alone (the old example) → `400 "[multimediaProfileId: should not be null or blank., active: should be either true or false.]"`; `{name, active:true, multimediaProfileId}` created and `show`/`list-site` read it back.
- **Update:** full replace; the body must carry `"id"` equal to the URL id (`400 "Invalid id: id in payload and URL should be same"` otherwise). `--verify` reported `all 5 sent field(s) match`.
- **Dependencies:** Teams reference sites via `siteId`. Delete all teams from a site before deleting the site: with teams present the delete returns `412 "Entity with id … is referred in other entities."` plus `"referencedEntities":["team"]`, and `list-incoming-references` names the teams (verified live 2026-10-13). A site also pins its multimedia profile — that profile cannot be deleted until the site is gone (`412`, `["site"]`).

### CLI Examples

```bash
# List sites (v2)
wxcli cc-site list-site

# Create a site
wxcli cc-site create --json-body '{"name": "US East Coast", "active": true, "multimediaProfileId": "mm-profile-uuid"}'

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
  -d '{"name":"US East Coast","active":true,"multimediaProfileId":"mm-profile-uuid"}'
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

- **Create:** Requires `name`, `variableType` (`String`, `Integer`, `Boolean`, `Decimal`, `DateTime` — title case, gotcha 21), `defaultValue`, `active`, `reportable`, `agentViewable` and `agentEditable` (spec `required`), plus `desktopLabel` when `agentViewable` is true (gotcha 22)
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
  "variableType": "String",
  "defaultValue": "Standard",
  "active": true,
  "reportable": true,
  "agentViewable": true,
  "desktopLabel": "Customer Tier",
  "agentEditable": false
}'

# Get a specific variable
wxcli cc-global-vars show "var-uuid"

# Delete a variable
wxcli cc-global-vars delete "var-uuid"
```

> **Unverified:** the `create` body follows the spec's required keys; `active` was added from the
> spec, not a live call. `variableType` title case and `desktopLabel` come from gotchas 21 and 22.

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

5. **PUT is full replace, and the body must carry `"id"`:** All update endpoints use PUT (full replacement). Always GET the entity first, modify the fields you need, and PUT the full object back. Verified live 2026-10-13 on `cc-site`, `cc-team`, `cc-multimedia-profile`, `cc-desktop-profile`, `cc-aux-code update-auxiliary-code` and `cc-outdial-ani update-entry`: a PUT body without `"id"` equal to the URL id returns `400 "Invalid id: id in payload and URL should be same"`, and a partial body (e.g. `{name, chat}`) returns a 400 listing every missing required field. The exceptions are the bulk PATCH endpoints on `auxiliary-code` and `user`, and the per-record PATCH commands on call monitoring schedules (`cc-monitoring-schedules update-call-monitoring`, §21) and organization settings (`cc-org-settings update-organization-setting`, §22). Tenant configuration (§23) has no PATCH.

6. **orgId auto-injection:** The `{orgid}` path parameter is automatically injected from your saved config. You never need to pass it manually in CLI commands.

### Entity Dependency Order

When building a CC deployment from scratch, create entities in this order:

```
1. Multimedia Profiles (a Site requires one — verified live 2026-10-13; the system default profiles also qualify)
2. Business Hours + Holiday Lists
3. Skills
4. Skill Profiles (references Skills)
5. Sites (references a Multimedia Profile)
6. Aux Codes (Idle + Wrap-Up)
7. Work Types
8. Global Variables
9. Desktop Layouts
10. Desktop Profiles (no layout reference — the layout is set on the Team; verified live 2026-10-13)
11. Teams (references Sites; may reference a Desktop Layout and a Multimedia Profile)
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

12. **Incoming references before delete.** Always check `list-incoming-references` before deleting a config entity. Deleting an entity that is referenced by queues, teams, or routing strategies can produce errors or leave orphaned references. Verified live 2026-10-13: deleting a referenced site, multimedia profile, work type or outdial ANI returns **`412`** (not 409) with `"reason":"Entity with id … is referred in other entities."` and a `referencedEntities` array naming the referencing types (`["team"]`, `["site"]`, `["auxiliary-code"]`, `["desktop-profile"]`). A `409` from these groups instead means a database null-column error (e.g. `Column 'team_status' cannot be null`).

13. **Skill value types must match.** When creating skill profiles there is no generic `skillValue` field (verified live 2026-10-13: `skills:[{skillId, skillValue}]` → `400 "Atleast one skill is mandatory."`). Use `proficiencyValue` (integer 0-10) for `PROFICIENCY`, `booleanValue` for `BOOLEAN` (both under `activeSkills`), and `activeEnumSkills:[{enumSkillValueId}]` for `ENUM` (all three created and read back live 2026-10-13); `TEXT` uses `textValue` per the spec (**Unverified**). `skillType` values are upper case (verified live 2026-10-13). **Unverified:** what the server does when the value field does not match the skill's type — not tested.

14. **Sites must exist before teams.** A team requires a `siteId`. Create sites first, then teams. Similarly, skill profiles require skills, and queues can require skill profiles.

15. **Agent summaries use POST for search.** Both `cc-agent-summaries` endpoints use POST (not GET) because they accept complex filter criteria in the request body. This is a search pattern, not a create pattern, despite the CLI command name `create`.

16. **Auto CSAT has two path families.** The deprecated paths use `/auto-csat/{autoCsatId}/...` and are documented in [contact-center-analytics.md](contact-center-analytics.md). The new non-deprecated paths use `/ai-feature/auto-csat/...` and are available via `wxcli cc-ai-feature` (8 commands). Use the `ai-feature` paths for new integrations.

17. **Internal queue endpoints.** The `by-team-id/.../internal` and `by-user-ci-id/.../internal` queue endpoints are marked as internal-use. They work with CI (Common Identity) user IDs, not CC user IDs. Use the v2 `by-user-id` endpoints for standard integrations.

18. **Reskill uses PATCH, not PUT.** The `/user/{id}/reskill` endpoint uses PATCH (partial update) to modify a user's skill profile and dynamic skills. The `dynamicSkills` field accepts `add` and `remove` arrays for incremental changes rather than full replacement.

19. **CC org ID must be bare UUID.** The CC config API path parameter `{orgid}` requires the raw UUID (e.g., `11111111-1111-1111-1111-111111111111`), not the base64-encoded Spark ID returned by `/people/me`. The CLI uses `get_cc_org_id()` in `config.py` to decode automatically. If calling the API directly, decode the base64 orgId to extract the UUID after the last `/` in the URN.

20. **CC v2 list endpoints return `"data"`, not `"items"`.** The v2 endpoints (e.g., `GET /organization/{orgid}/v2/cad-variable`) wrap results in `{"meta": {...}, "data": [...]}`. The v1 bulk-export endpoints use `{"items": [...]}`. The CLI handles both automatically.

21. **Global Variable `variableType` requires title case.** The API rejects `"STRING"` — use `"String"`, `"Integer"`, `"Boolean"`, `"Decimal"`, `"DateTime"`. The OpenAPI spec lists both forms but only title case works at runtime.

22. **`desktopLabel` required when `agentViewable` is true.** Creating or updating a Global Variable with `agentViewable: true` fails unless `desktopLabel` is also provided. This dependency is not documented in the API spec's required fields list.

23. **A full-admin PAT worked against CC config endpoints when tested; a 403 means the token lacks the CC scopes.** An earlier version of this gotcha (2026-04-24, from a 403 on Global Variables on org the sandbox org) claimed PATs from developer.webex.com never carry `cjp:config_read`/`cjp:config_write`. **That claim is disproven.** Verified live 2026-10-13 on the same org (the sandbox tenant, the sandbox org, region us1) with a full-admin PAT from developer.webex.com: HTTP 200 on `cc-flow` list, show, export (`--version latest` and `draft`), list-validate, create-validate, create-lock and create-unlock; `cc-queue list`; `cc-entry-point list`; and `cc-global-vars list-cad-variable` (returned the org's 6 global variables, the same endpoint that returned 403 in April). No 403 on any call. **Not tested:** CC writes other than validate/lock/unlock, PATs from non-full-admin users, and other orgs, so do not assume a PAT works for every `cc-*` command. If a `cc-*` call does return 403 with a `ccconfig_` trackingId, the token lacks the CC scopes; use one of the two options below. **Separately, the agent runtime is a different scope:** a PAT *does* carry `cjp:user`, the per-agent runtime scope: verified live on 2026-07-31, an agent's PAT successfully drove `register()`, `stationLogin()` and `setAgentState()` through the `@webex/contact-center` JS SDK against a live tenant. So a PAT works for a custom agent desktop and for `PATCH /v1/tasks/{taskId}`. See [contact-center-agent-sdk.md](contact-center-agent-sdk.md) §10. Two options for CC config operations when the token lacks the scopes: (a) **OAuth integration** — select CC scopes explicitly and complete the OAuth authorization flow; adding scopes to an existing integration does not update previously issued tokens, you must re-authorize; (b) **Service App with CJP scopes** — recommended for production automation and server-to-server use; no interactive login required after the org admin authorizes the app, making it suitable for CI/CD pipelines and backend services. Note: all CC integration scopes work with Service Apps except `spark:applications_token` and `spark:kms`.

24. **Global Variable names are immutable.** The CC API returns 400 `"name: should not be modified"` if you attempt to change the `name` field via PUT update. To rename a variable, delete and recreate it. Note that any flows referencing the old variable ID will need to be updated.

25. **Flow Designer HTTP Connector handles auth and base URL automatically.** The CC HTTP Connector (created in Control Hub → Contact Center → Integrations → Connectors) stores the regional base URL and auth tokens for you. In the Flow Designer HTTP Request node, provide only the **request path**, not the full URL — e.g., `/organization/{orgid}/cad-variable` for Global Variables or `/search` for the Search API. Toggle "Use Authenticated Endpoint" and select the connector; no manual token management is needed in flows. When creating the connector, choose the access level: Read-Only (GET) or Read-Write (POST/PUT/DELETE).

26. **Derive the CC regional base URL from the access token.** The Webex access token has three underscore-separated parts: `token.split('_')` → `[accessToken, ciCluster, orgId]`. The middle segment (`ciCluster`) maps directly to the regional base URL: `https://api.wxcc-{ciCluster}.cisco.com`. Available regions: `us1`, `eu1`, `eu2`, `anz1` (confirmed); `ca1`, `jp1`, `sg1` (plausible but not independently confirmed from public documentation — verify against your org's token cluster value). This is useful for production apps that need to determine the correct CC API endpoint dynamically without hardcoding a region.

27. **`cc-queue create` is the BULK endpoint; a single queue is `cc-queue create-contact-service-queue`.** `cc-queue create --help` reads "Bulk save Contact Service Queues". Verified live 2026-10-13: four queues were created with `create-contact-service-queue` (SLA 30/60/120 s), and read back. Its `--help` marks `name`, `queueType` (INBOUND/OUTBOUND), `checkAgentAvailability`, `channelType`, `serviceLevelThreshold`, `maxActiveContacts`, `maxTimeInQueue` and `active` required, and its example body also carries `routingType`, `queueRoutingType` (e.g. `TEAM_BASED`) and `callDistributionGroups` (`[{"agentGroups":[{"teamId":"..."}],"order":0,"duration":0}]`). A body with only `name` and `channelType` leaves required fields out.

28. **`list-contact-service-queue-v2` omits `callDistributionGroups`, so team routing reads as null in a list.** Verified live 2026-10-13: a queue whose team assignment was null in the v2 list showed `TEAM_BASED` with its team in `show-contact-service-queue-v2`. Read team routing with `show`; a list row with no team is not evidence the queue has none (a "which queues have no team?" query built on the list would be wrong).

29. **Entry point to flow wiring is `flowId` plus `flowTagId`; new flows publish with only the `Latest` tag.** Verified live 2026-10-13: `cc-entry-point create` with `flowId` set to a just-published flow and `flowTagId: "Latest"` saved, and `show` returned both with the entry point active. Live, Test and Dev tags also exist, but the flow published that day had only `Latest` pointing at its version (Dev/Live/Test unset); pointing an entry point at a tag the flow never received was not tested. Mapping a dial number to the entry point (`cc-dial-number`) is a separate step, without which the flow cannot be called.

30. **CC business hours use `workingHours`, not `businessHours`.** Verified live 2026-10-13: `workingHours:[{"name":"Weekday","days":["MON","TUE","WED","THU","FRI"],"startTime":"07:00","endTime":"19:00"}]` created OK and appeared in the flow-designer choices for the `business-hours` activity. The older `businessHours:[{day:"monday",...}]` shape shown here before 2026-10-13 does not match `--help`. The holiday-list body (§16) was re-tested the same day: it uses `startDate`/`endDate`, not `date`.

31. **A CC-routable Calling number shows a `CONTACT_CENTER_ADAPTER` owner in `numbers list`.** Verified live 2026-10-13 (read-only audit, `wxcli numbers list --all -o json`, three numbers on one location): all three were `ACTIVE`, `PRIMARY`, `PSTN_NUMBER`, no extension, location Site1, and each was owned by its own `CONTACT_CENTER_ADAPTER` named "Contact Center RTMS" (the owner id decodes to a `wcc_…_WCC@<cluster>` address). The two numbers that already took calls and the newly mapped one were structurally identical, so that shape is the comparison target for a new number. **Not established:** whether `cc-dial-number create` is what creates that owner or it already existed, and whether the carrier actually delivers calls to the number (nothing in the API shows delivery). Pass `--all` on `numbers list`; the default is one page. On the CC side the matching record is the dial-number mapping (`cc-dial-number list --all`): the new mapping matched a working one in every field except `entryPointId` and `id` (`defaultAni: true` marked the tenant's default outdial number on a third mapping). Creating the mapping (verified live 2026-10-13): `cc-dial-number create --dialled-number E164 --entry-point-id ID --entry-point-name NAME --location LOC --region-id REG` created it and `show` confirmed. **`--location` and `--region-id` are both required by the API (the spec says optional); since 2026-10-13 `create --help` marks both required.** Observed before that fix: omitting `--location` returns `400 "location: should not be null or blank"`, omitting `--region-id` returns `400 "Telephony regionId should be provided."`; copy both from an existing mapping. In `--json-body` the field is `dialledNumber` (not `dialNumber`). **Warning:** bare `cc-dial-number delete` (no ID) means "Delete all Dialed Number Mapping(s)" and removes every mapping in the org (confirmation unless `--force`); remove one with `cc-dial-number delete-dial-number ID --force` (returned `{"status":"deleted"}`).

32. **Whether an agent is logged in is not in `cc-agents`' roster or in `cc-users`; read it from the activity log or the Search API.** Verified live 2026-10-13: `cc-agents list-activities` is an event log, and its `--from` is epoch milliseconds with a 24 h maximum window per call (verified live 2026-10-13: ISO timestamps → 400 `from should be of type java.lang.Long`; >24 h → 400; §1's examples now use epoch ms). In `cc-search create`, `from`/`to` are GraphQL arguments inside the query and also take unquoted epoch-ms integers (a quoted ISO string → 400 "not a valid 'Long'"). 14 consecutive 24 h windows returned 0 rows, which on its own proves nothing, so the audit cross-checked with `cc-search create` (GraphQL) over the `agentSession` type: a 365-day query returned 66 sessions (proving the query can return data) and the count with `isActive: true` was 0. Use a long-window query that is known to return history as the control, then count the active ones. `cc-search-metadata list` shows what the search surface accepts. The query text itself was not recorded.

33. **A queue with no logged-in agent keeps callers waiting until `maxTimeInQueue` (expected behavior, not observed on a call).** The 2026-10-13 audit found a queue chain with every configuration link correct and zero active agent sessions, and concluded from the queue settings (`maxTimeInQueue: 900`, hold loop in the flow) that a caller would hear menus, then music, and be dropped at 900 s. No test call was placed, so this is inferred from configuration. It is an operations gap, not a configuration gap: a person must sign in to Agent Desktop and set Available.

34. **What makes a user an eligible voice agent (as read, 2026-10-13).** For each of three agents: `cc-users list` showed `contactCenterEnabled` and `agentCapabilitiesEnabled` true and active; `people show <ciUserId> --calling-data true` and `licenses list --all` showed a Contact Center agent license (a Premium Agent SKU, CJPPRM) plus a Webex Calling Professional license (BCSTD). One agent had `invitePending: true` in Webex identity and had never logged in; a user in that state probably cannot sign in (inferred, not tested). Voice also depends on two profiles: the desktop profile (`cc-desktop-profile show`, `loginVoiceOptions` must include the option used, §14) and the multimedia profile (`cc-multimedia-profile show`, telephony slot of 1 or more). An agent with no multimedia profile of its own appeared to inherit from the site (the team had none, the site's profile had telephony 1); this is the audit's reading of the data, not a documented inheritance order.

35. **To validate a new resource, diff it against one that already works.** Verified live 2026-10-13: `cc-entry-point show` on a new entry point vs two working ones differed only in `callbackEnabled` (intended); `cc-flow list` rows showed the same tag pattern (Latest set, Live/Test/Dev unset) and the same `lockedBy` admin as working flows (an editor lock, no runtime effect); four new queues matched an existing queue except for intended values (SLA, recording, `maxTimeInQueue`), but only when read with `show-contact-service-queue-v2` (gotcha 28). For IDs inside a flow, `cc-flow list-activity-choices … --validate true --search ID` is a point lookup; include a negative control (an all-zeros UUID should return no choices) so a hit is distinguishable from a probe that always answers. The command now prints the whole response object (`count`, `source`, `choices`, …), so "no choices" is an empty `choices` array rather than the bare `[]` it printed before (generator fix 2026-10-13, ADR-14; not re-run live for this command). A callback needs no queue-side setting: the queue object had no callback fields, and the flow's `callback` activity drives it.

36. **A global variable record's `agentViewable` does not make it appear on the desktop; the flow's own declaration decides.** Verified live 2026-10-13: two global records were `agentViewable` with labels, but the flow re-declared them with `isCAD:false`, so they would not display; showing them needed `isCAD:true` plus a `desktopLabel` on the flow variable and a republish. Separately, a record with `agentEditable:true` that the flow declares `isAgentEditable:false` is read-only for the agent. The system default "Global Layout" (`cc-desktop-layout list-desktop-layout --all`) displays agent-viewable variables, so no custom layout was needed. Whether the desktop actually renders them is unverified (needs a live call).

37. **Skill `skillType` is UPPER CASE; Global Variable `variableType` is title case — and the spec/`--help` get the first one wrong.** Verified live 2026-10-13: `cc-skill create` accepts `PROFICIENCY`, `BOOLEAN`, `TEXT`, `ENUM` and rejects the spec's (and the generated `--help` example's) `Proficiency` with a 400 that lists the valid values. `variableType` is the opposite: `String`, `Integer`, … (gotcha 21). Do not "normalize" one field's casing to the other's, and do not change either to match the spec without a live call — an automated spec-driven pass on 2026-10-13 regressed the correct `PROFICIENCY` examples in this doc for exactly that reason.

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
