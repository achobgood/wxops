---
name: contact-center
description: |
  Provision and manage Webex Contact Center resources using wxcli CLI commands:
  agents, queues, entry points, teams, skills, flows, campaigns, dial plans,
  dial numbers (DN-to-entry-point mapping), desktop profiles, CC sites, CC business hours,
  CC holiday lists, monitoring (live sessions and stored monitoring schedules),
  CC org settings and tenant configuration. Guides the user from prerequisites through
  execution and verification.
  Use for: create, update, delete, list, configure, or troubleshoot any CC resource.
  NOT for: Webex Calling queues/hunt groups (use configure-features), Calling dial plans
  (use configure-routing), or Calling schedules (use configure-features).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [cc-operation]
---

# Contact Center Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What CLI command sets the CC API region? (Answer: `wxcli set-cc-region <region>` — defaults to `us1`. Valid regions: `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1`.)
2. What base URL do CC API calls target? (Answer: `api.wxcc-{region}.cisco.com`, not `webexapis.com`.)
3. How do you verify CC auth is working? (Answer: `wxcli whoami` for token, then `wxcli cc-site list -o json` to confirm CC access.)

If you cannot answer all three, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/contact-center-core.md` for agents, queues, entry points, teams, skills, desktop profiles, sites, aux codes, and configuration data models
2. Read `docs/reference/contact-center-routing.md` for dial plans, campaigns, flows, audio files, contacts, outdial ANI
3. Read `docs/reference/contact-center-analytics.md` for AI features, monitoring, subscriptions, tasks
4. Read `docs/reference/contact-center-journey.md` for JDS: workspaces, persons, identity, profile views, events, WXCC subscription

**Out of scope for this skill:** if the user wants to *build a custom agent desktop* (a browser softphone on the `@webex/contact-center` JS SDK — `webex.cc`, `task.*`, WebRTC audio), that is not a `wxcli` task and this skill has no path for it. Send them to `docs/reference/contact-center-agent-sdk.md`. This skill provisions the agents, queues and profiles such a desktop connects to — including `loginVoiceOptions` on the desktop profile, which is the gate on browser audio.

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli cc-queue create --help` — note the `cc-` prefix is what distinguishes Contact Center commands from Calling, so `cc-queue` ≠ `call-queue`; guessing the wrong one builds the wrong entity). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth token and CC region

Before any API calls, confirm the user has a working auth token and CC region is configured:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

### Set CC region

CC commands target `api.wxcc-{region}.cisco.com`. The region must be set before any `cc-*` command:

```bash
wxcli set-cc-region us1
```

Valid regions: `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1`.

### Verify CC access

After setting the region, confirm the token has CC admin access:

```bash
wxcli cc-site list -o json
```

If this returns 403, the token lacks CC-specific OAuth scopes. Required scopes:
- **Read**: `cjp:config_read`
- **Write**: `cjp:config_write`
- **JDS admin (Journey Data Service)**: `cjds:admin_org_read` and/or `cjds:admin_org_write` — required for `/admin/v1/api/...` JDS endpoints (workspace, person, template management). Standard `cjp:` scopes alone will not grant JDS admin access.

The user may need to re-authenticate with CC scopes enabled.

> **NOTE (verified live 2026-10-13):** A full-admin personal access token (PAT) from developer.webex.com worked for CC config calls on org "the sandbox tenant" — `cc-flow` list/show/export/list-validate/create-validate/create-lock/create-unlock, `cc-queue list`, `cc-entry-point list` and `cc-global-vars list-cad-variable` all returned 200, no 403. An earlier (April 2026) finding that PATs get 403 on global variables on this same org no longer reproduces. Whether a PAT works can still vary by org/token, so try it first.
>
> If you get 403 "Access denied - Client is forbidden access to the resource" with a `ccconfig_` tracking ID, the token lacks `cjp:config_*` scopes. Two options:
>
> **Option A — OAuth Integration** (user-facing apps):
> 1. Create an OAuth integration at developer.webex.com with `cjp:config_read` and `cjp:config_write` scopes selected
> 2. Complete the OAuth authorization flow to get a token
> 3. Run `wxcli configure` with the new token
> 4. If you added scopes to an existing integration, you must re-authorize — old tokens don't pick up new scopes
>
> **Option B — Service App** (production automation, no interactive login):
> 1. Create a Service App at developer.webex.com with `cjp:config_read` and `cjp:config_write` scopes (all CC scopes work except `spark:applications_token` and `spark:kms`)
> 2. Have a Full Admin authorize the app in Control Hub → Management → Apps → Service Apps
> 3. Generate tokens in the developer portal (Access Token: 14-day, Refresh Token: 90-day)
> 4. Run `wxcli configure` with the access token

> **Note:** The CC API requires the bare UUID org ID (e.g., `22222222-...`), not the base64-encoded Spark ID (`Y2lzY29...`). The CLI handles this automatically via `get_cc_org_id()`, which decodes the Spark ID to extract the UUID. No manual conversion is needed.

## Step 3: Identify the operation

Ask the user what they want to configure. Present this decision matrix if they are unsure:

### Agent Management

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| **List the agents / see the agent roster** | Names, emails, team + skill + agent-profile assignments, CC-enabled flag | `cc-users` — **NOT `cc-agents`** |
| Manage agent state (login, logout, state changes) | Agent lifecycle | `cc-agents` |
| See what agents *did* in a time window | Activity/event log, requires `--from`, ≤24h window | `cc-agents list-activities` — an event log, not a roster |
| Configure agent greetings | Upload/assign greeting files | `cc-agent-greetings` |
| View agent summaries | Agent activity summaries | `cc-agent-summaries` |
| Agent wellbeing settings | Burnout/wellness config | `cc-agent-wellbeing` |
| Manage user profiles | Agent desktop/permissions profiles | `cc-user-profiles` |
| Manage CC users | CC user CRUD | `cc-users` |
| Update dynamic skills for users | Bulk update dynamic skill assignments | `cc-users` |
| List users by dynamic skill | Query users with a specific dynamic skill | `cc-users` |
| Reskill users | Reassign skill profiles to users | `cc-users` |

### Queue & Routing

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Configure queues | Create/update/delete contact service queues | `cc-queue` |
| Query queues by skill/team/user | Skill-based routing queue lookups | `cc-queue` |
| Set up entry points | Inbound/outbound entry point CRUD | `cc-entry-point` |
| Configure dial plans | CC dial plan management | `cc-dial-plan` |
| Manage dial numbers | Number-to-entry-point mapping | `cc-dial-number` |
| Queue callbacks | Callback configuration | `cc-callbacks` |
| Estimated wait time | EWT config | `cc-ewt` |
| Queue overrides | Override routing rules | `cc-overrides` |

### Campaign & Contacts

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Run outbound campaigns | Start/stop/update campaigns | `cc-campaign` |
| List campaigns in a group | Look up campaigns by campaign group name | `cc-campaign-group` |
| Manage contact lists | Upload/manage contact lists for campaigns | `cc-contact-list` |
| Manage contact numbers | Contact number validation/management | `cc-contact-number` |
| Do-not-call lists | DNC list management | `cc-dnc` |
| Outdial ANI | Configure outbound caller IDs | `cc-outdial-ani` |
| Capture management | Capture data config | `cc-captures` |

### Configuration

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Manage sites | CC site CRUD | `cc-site` |
| Business hours | Business hours schedules | `cc-business-hour` |
| Holiday lists | Holiday schedule management | `cc-holiday-list` |
| Aux codes | Agent auxiliary/idle codes | `cc-aux-code` |
| Work types | Wrap-up/work type definitions | `cc-work-types` |
| Desktop layouts | Agent desktop UI layouts | `cc-desktop-layout` |
| Desktop profiles | Agent desktop config profiles | `cc-desktop-profile` |
| Multimedia profiles | Channel capacity profiles | `cc-multimedia-profile` |
| Global variables | Global flow variables | `cc-global-vars` |
| Skills | Skill definitions (routing attributes) | `cc-skill` |
| Skill profiles | Skill profile assignments | `cc-skill-profile` |
| Teams | CC team CRUD, agent assignment | `cc-team` |
| Channels | The medium a contact arrives on (telephony/email/chat/social/work-item) + its branding | `channel` |
| Assets | A configured instance of a channel (mailbox, chat widget, custom-messaging endpoint) | `asset` |
| CC org settings | Tenant entitlements/limits (read) + short/lost-call thresholds, recording mode, same-agent routing (write) — **not** Webex `org-settings` | `cc-org-settings` |
| CC tenant configuration | Tenant-wide RONA timeouts, auto wrap-up, desktop inactivity, outdial DN handling | `cc-tenant-config` |

### Flows & Automation

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Manage flows | Export/publish/list flows | `cc-flow` |
| Data sources | External data source config | `cc-data-sources` |
| Audio files | Upload/manage IVR audio | `cc-audio-files` |
| Resource collections | Resource collection management | `cc-resource-collection` |

### AI & Analytics

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| AI assistant | Get AI-powered suggestions | `cc-ai-assistant` |
| AI features | Configure AI capabilities | `cc-ai-feature` |
| Auto CSAT | Automated satisfaction scoring | `cc-auto-csat` |
| Agent summaries (AI) | AI-generated call summaries | `cc-summaries` |
| Customer journey | Journey tracking, profiles, templates | `cc-journey` |

### Monitoring & Events

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Call monitoring | Monitor/barge/coach a call that is in progress now | `cc-call-monitoring` |
| Monitoring schedules | Store a supervisor's monitoring plan (when, which teams/queues/agents, paused) — **not** a live session | `cc-monitoring-schedules` (+ `cc-users show SCHEDULE_ID` for the users it covers) |
| Real-time stats | Real-time queue/agent statistics | `cc-realtime` |
| Queue statistics | Queue performance metrics | `cc-queue-stats` |
| Event subscriptions | Subscribe to CC events (webhooks) | `cc-subscriptions` |
| Task management | Agent task lifecycle (accept, hold, transfer, wrapup) | `cc-tasks` |
| Notifications | Notification management | `cc-notification` |
| Search | Search CC resources | `cc-search` |
| Address books | Address book management | `cc-address-book` |

### External Data Updates

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Correct a finished task's data | Write numeric global-variable values onto ONE task that ended in the last two days | `external-data-updates` |

This is **not** how a live task's variables are set (that is the flow, or
`cc-tasks update`), **not** where a variable is defined (`cc-global-vars` —
it must exist first and be numeric), and **not** a read: there is no GET.
Rules from the spec (**Unverified** — not exercised live): one task per
request; at most 30 variables; numbers only; timestamps are ISO-8601 UTC
strings (`2026-09-22T10:00:00.000Z`), not epoch ms; `orgId` is the bare org
UUID and is not auto-injected. `data[]` has no flag, so `--json-body` is
mandatory — without it the body has no `data` and a 400 is expected. A
`202` means accepted for processing, not applied. The group has no `cc-`
prefix and its `--help` says "Webex Calling", but it calls the CC regional
host. Details: `docs/reference/contact-center-analytics.md` §15.

```bash
wxcli external-data-updates update --generate-json-body

wxcli external-data-updates update --json-body '{"orgId":"ORG_UUID","updateType":"contact","data":[{"id":"TASK_ID","startTimestamp":"2026-09-22T10:00:00.000Z","endTimestamp":"2026-09-22T10:30:00.000Z","globalVariables":[{"name":"UpSell","value":12}]}]}'
```

### Not Contact Center?

| Need | Redirect To |
|------|-------------|
| Webex Calling features (AA, CQ, HG) | `configure-features` skill |
| Person/workspace call settings | `manage-call-settings` skill |
| Webex Calling reporting (CDR) | `reporting` skill |
| Customer Assist on a Calling queue | `customer-assist` skill |
| Webex organization settings (`org-settings`, no `cc-` prefix) | `manage-identity` skill |
| Meetings | `manage-meetings` skill |

## Step 4: Check prerequisites

Before creating any CC resource, verify these conditions:

### 4a. CC tenant is provisioned

The org must have Webex Contact Center provisioned. Confirm with:

```bash
wxcli cc-site list -o json
```

If this returns empty or errors, the CC tenant is not provisioned. The user must provision CC through Control Hub first.

### 4b. At least one site exists

Most CC resources are site-scoped. Confirm a site exists:

```bash
wxcli cc-site list -o json
```

If no sites exist, create one first:

```bash
wxcli cc-site create --json-body '{
  "name": "Main Site",
  "multimediaProfileId": "PROFILE_ID"
}'
```

### 4c. Resource-specific prerequisites

#### Queues

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Entry point exists | `wxcli cc-entry-point list-entry-point -o json` | Create entry point first |
| Team exists (for team-based routing) | `wxcli cc-team list -o json` | Create team first |
| Skill profiles (for skill-based routing) | `wxcli cc-skill-profile list-skill-profile -o json` | Create skills and skill profiles first |

#### Teams

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Site exists | `wxcli cc-site list -o json` | Create site first |
| Multimedia profile exists | `wxcli cc-multimedia-profile list-multimedia-profile -o json` | Create multimedia profile first |
| Skill profile (optional) | `wxcli cc-skill-profile list-skill-profile -o json` | Create if using skill-based routing |

#### Campaigns

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Contact list uploaded | `wxcli cc-contact-list list -o json` | Upload contact list first |
| Outdial ANI configured | `wxcli cc-outdial-ani list -o json` | Configure outbound caller ID first |
| Entry point exists (outbound) | `wxcli cc-entry-point list-entry-point -o json` | Create outbound entry point |

#### Flows

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Audio files uploaded (if used in flow) | `wxcli cc-audio-files list-audio-file -o json` | Upload audio files first |
| Global variables defined (if used) | `wxcli cc-global-vars list-cad-variable -o json` | Create global variables first |

#### Skill Profiles

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Skills defined | `wxcli cc-skill list-skill -o json` | Create skill definitions first |

#### Desktop Profiles

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Desktop layout exists | `wxcli cc-desktop-layout list-desktop-layout -o json` | Create or use default layout (note: `list` takes an ID and lists references for a specific layout — `list-desktop-layout` is the list-all) |

#### Event Subscriptions

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Webhook URL accessible | N/A — verify externally | Set up a webhook endpoint first |

## Step 5: Gather configuration and present deployment plan -- [SHOW BEFORE EXECUTING]

Based on the selected operation, collect the required parameters from the user. **Always present the plan before executing.**

---

### Queue (Contact Service Queue)

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique queue name |
| Channel type | Yes | `telephony`, `chat`, `email`, `social` |
| Routing type | No | `LONGEST_AVAILABLE_AGENT` (default), `SKILLS_BASED`, `BEST_AVAILABLE_AGENT` |
| Service level threshold | No | Seconds (default varies) |
| Max time in queue | No | Seconds before overflow |
| Overflow destination | No | Entry point or number for overflow |

**CLI command (single queue, v2):**

```bash
wxcli cc-queue create-contact-service-queue --json-body '{
  "name": "Support Queue",
  "queueType": "INBOUND",
  "channelType": "TELEPHONY",
  "checkAgentAvailability": false,
  "serviceLevelThreshold": 60,
  "maxActiveContacts": 100,
  "maxTimeInQueue": 3600,
  "active": true,
  "routingType": "LONGEST_AVAILABLE_AGENT",
  "queueRoutingType": "TEAM_BASED",
  "callDistributionGroups": [{"agentGroups": [{"teamId": "TEAM_ID"}], "order": 0, "duration": 0}]
}'
```

> **`cc-queue create` is the BULK endpoint** ("Bulk save Contact Service Queues"), not the single create. Verified live 2026-10-13: `create-contact-service-queue` created four queues. Its `--help` marks `name`, `queueType`, `checkAgentAvailability`, `channelType`, `serviceLevelThreshold`, `maxActiveContacts`, `maxTimeInQueue` and `active` required; the body above follows the `--help` example. Run `wxcli cc-queue create-contact-service-queue --help` for the current list. The earlier example here (`name` + `channelType` only) omitted required fields.

**List queues:**

```bash
wxcli cc-queue list-contact-service-queue-v2 -o json
```

> **`list-contact-service-queue-v2` omits `callDistributionGroups`** (verified live 2026-10-13: team assignment reads null). Read team routing with `show-contact-service-queue-v2` below; a list row with no team does not mean the queue has none.

**Show specific queue:**

```bash
wxcli cc-queue show-contact-service-queue-v2 QUEUE_ID -o json
```

#### Queue Skill-Based Routing Queries

These commands query queues based on skill, team, or user assignments. Useful for verifying routing configuration and debugging skill-based queue assignments.

**List queues assigned to a specific team:**

```bash
wxcli cc-queue list-team-based-queues TEAM_ID -o json
```

**List queues for a CI user:**

```bash
wxcli cc-queue list-agent-based-queues USER_CI_ID -o json
```

**List skill-based queues by CI user:**

```bash
wxcli cc-queue list-agent-based-queues USER_CI_ID -o json
```

**List queues by skill profile:**

```bash
wxcli cc-queue list-skill-based-queues SKILL_PROFILE_ID -o json
```

**Fetch queues by dynamic skill and skill profile (POST):**

```bash
wxcli cc-queue create-fetch-by-dynamic-skills-and-skill-profile --json-body '{
  "dynamicSkills": [{"skillId": "SKILL_ID", "proficiencyValue": 5}],
  "skillProfileId": "SKILL_PROFILE_ID"
}'
```

> **Unverified:** body keys are from the spec, not a live call. Each `dynamicSkills` item
> carries the value in the field matching the skill's type: `proficiencyValue`,
> `booleanValue`, `textValue` or `enumSkillValues`.

**Fetch queues by user ID and skill profile ID (POST):**

```bash
wxcli cc-queue create-fetch-by-user-id-skill-profile-id --json-body '{
  "userId": "USER_ID",
  "skillProfileId": "SKILL_PROFILE_ID"
}'
```

**Fetch queues by grouped assistant skill (v2, POST):**

```bash
wxcli cc-queue create-fetch-by-grouped-assistant-skill --json-body '{
  "assistantSkillIds": ["ASSISTANT_SKILL_ID"]
}'
```

> **Unverified:** the key is from the spec, not a live call. Omit `assistantSkillIds` (or
> send `null`) to get every Assistant Skill's mapping.

---

### Entry Point

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique entry point name |
| Channel type | Yes | `telephony`, `chat`, `email`, `social` |
| Service level threshold | No | Seconds |
| Flow ID | No | Assigned flow for routing (`flowId`) |
| Flow tag ID | No | Which flow version tag to run (`flowTagId`); `"Latest"` works |

**CLI command (v2 — preferred):**

```bash
wxcli cc-entry-point create --json-body '{
  "name": "Main IVR",
  "channelType": "telephony"
}'
```

> **Wiring to a flow (verified live 2026-10-13):** add `"flowId": "<flow id>"` and `"flowTagId": "Latest"` to the body; `show` read both back. A newly published flow has only the `Latest` tag pointing at its version (Live, Test and Dev tags exist but were unset), so use `Latest` until you tag a version otherwise. The entry point is not callable until a dial number is mapped to it (`cc-dial-number`).

**List entry points:**

```bash
wxcli cc-entry-point list-entry-point -o json
```

**Show specific entry point:**

```bash
wxcli cc-entry-point show ENTRY_POINT_ID -o json
```

---

### Team

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique team name |
| Site ID | Yes | From `wxcli cc-site list` |
| Multimedia profile ID | No | Channel capacity assignment |
| Skill profile ID | No | For skill-based routing |
| Desktop profile ID | No | Agent desktop config |

**CLI command:**

```bash
wxcli cc-team create --json-body '{
  "name": "Support Team",
  "siteId": "SITE_ID",
  "multimediaProfileId": "MM_PROFILE_ID"
}'
```

**List teams:**

```bash
wxcli cc-team list -o json
```

**Show specific team:**

```bash
wxcli cc-team show TEAM_ID -o json
```

---

### CC Users

**This is the agent roster.** If someone asks to "list the agents", this is the command — not
anything under `cc-agents`, which holds only runtime session and telemetry operations. Verified
live 2026-07-29: each record carries `firstName`, `lastName`, `email`, `ciUserId`,
`contactCenterEnabled`, `siteId`, `teamIds`, `agentProfileId`, `skillProfileId`. Use
`list-with-user-profile` when you also need each user's profile permissions expanded inline
instead of a bare `userProfileId`.

**List CC users (the agent roster):**

```bash
wxcli cc-users list -o json
```

**List the roster with profile permissions expanded:**

```bash
wxcli cc-users list-with-user-profile -o json
```

**Show a CC user:**

```bash
wxcli cc-users show USER_ID -o json
```

**Bulk update dynamic skill for users:**

```bash
wxcli cc-users update-dynamic-skill SKILL_ID --json-body '{
  "items": [
    {"itemIdentifier": 1, "requestAction": "SAVE",
     "item": {"organizationId": "CC_ORG_UUID", "userId": "USER_ID_1",
              "skillId": "SKILL_ID", "proficiencyValue": 7}},
    {"itemIdentifier": 2, "requestAction": "SAVE",
     "item": {"organizationId": "CC_ORG_UUID", "userId": "USER_ID_2",
              "skillId": "SKILL_ID", "proficiencyValue": 7}}
  ]
}'
```

**Unverified:** this body is built from the spec's `UpdateDynamicSkillsDTO`, not from a live call. Per the spec: `userId` is the user whose skill is set; `organizationId` (the bare CC org UUID) is "required for all bulk save operations"; the value goes in the field that matches the skill's type — `proficiencyValue` (0-10), `booleanValue`, `textValue`, or `enumSkillValues`; `requestAction` is `SAVE` or `DELETE`; and `id` (the assignment's own resource id) is "mandatory when updating a resource", so include it when changing an existing assignment. Run the command with `--generate-json-body` to see the full item shape.

**List users with a specific dynamic skill:**

```bash
wxcli cc-users show-by-dynamic-skill-id DYNAMIC_SKILL_ID -o json
```

**Reassign skill profiles to a user (reskill):**

```bash
wxcli cc-users update-reskill USER_ID --json-body '{
  "skillProfileId": "NEW_SKILL_PROFILE_ID"
}'
```

---

### Skill & Skill Profile

**Create a skill definition:**

```bash
wxcli cc-skill create --json-body '{
  "name": "Spanish",
  "skillType": "PROFICIENCY",
  "description": "Spanish language proficiency"
}'
```

Skill types: `PROFICIENCY` (1-10 scale), `BOOLEAN` (true/false), `TEXT` (string match), `ENUM` (set of values).

**List skills:**

```bash
wxcli cc-skill list-skill -o json
```

**Create a skill profile:**

```bash
wxcli cc-skill-profile create --json-body '{
  "name": "Bilingual Agent",
  "description": "English + Spanish",
  "skills": [
    {"skillId": "SKILL_ID", "skillValue": 8}
  ]
}'
```

**List skill profiles:**

```bash
wxcli cc-skill-profile list-skill-profile -o json
```

---

### Dial Plan & Dial Number

**Create a dial plan:**

```bash
wxcli cc-dial-plan create --json-body '{
  "name": "US Dial Plan",
  "description": "US domestic dialing rules"
}'
```

**List dial plans:**

```bash
wxcli cc-dial-plan list-dial-plan -o json
```

> **NOTE:** `cc-dial-plan list` is a references endpoint (shows what references a specific dial plan), not a list-all. Always use `list-dial-plan-v2` to list all dial plans.

**Map a dial number to an entry point:**

```bash
wxcli cc-dial-number create --dialled-number "+18005551234" --entry-point-id "ENTRY_POINT_ID" --entry-point-name "ENTRY_POINT_NAME" --location "LOCATION_ID" --region-id "REGION_ID"
```

> **Dial-number create (verified live 2026-10-13):** the flags form above created the mapping and `show` confirmed it. **`--location` and `--region-id` are both required by the API (the spec says optional); since 2026-10-13 `--help` marks both required and the CLI refuses locally without them.** Before that fix: omit `--location` and it returns `400 "location: should not be null or blank"`; omit `--region-id` and it returns `400 "Telephony regionId should be provided."`. Copy both from a mapping that already works (`wxcli cc-dial-number list --all -o json` or `show ID -o json`), using the same values for a number on the same Calling location. In `--json-body` the field is `dialledNumber` (two L's, not `dialNumber`, which the earlier example here used), with `entryPointId`, `entryPointName`, `location`, `regionId`. After mapping, check the Calling side of the number too (see "Readiness checklist" in Flow Management).
>
> **WARNING: bare `wxcli cc-dial-number delete` (no ID) is "Delete all Dialed Number Mapping(s)" and removes EVERY mapping in the org** (it asks for confirmation unless `--force` is passed). To remove one mapping use `wxcli cc-dial-number delete-dial-number MAPPING_ID --force` (verified live 2026-10-13: returned `{"status":"deleted"}`).

---

### Campaign Group Lookup

`cc-campaign-group list` looks up campaigns by campaign group name. There is no CLI command to enumerate campaign group names themselves — get the name from Control Hub or wherever the campaign group was created.

```bash
wxcli cc-campaign-group list CAMPAIGN_GROUP_NAME -o json
```

Takes one required argument, `CAMPAIGN_GROUP_NAME`. Optional `--page`, `--page-size` (1-100), and `--campaign-status` (`Draft`, `Running`, `Pending`, `Paused`, `Completed`, `Ended`) filter/paginate the result.

The response is `{"outcome", "statusCode", "pagination", "campaigns": [...]}`; the CLI extracts `campaigns`. Each campaign carries `campaignId`, `campaignName`, `status`, `campaignDialingMode`, `campaignType`, `channel`, `outdialANI`, `scheduleInfo` and more — note there is **no** `id` or `name` field, so project on the real names: `--fields '[].{id:campaignId,name:campaignName}'`.

> **Verified live:** an unknown or nonexistent campaign group name does not 404 — the API returns `500 {"code":"InternalServerError","message":"An unexpected error occurred"}` after the CLI's automatic retry. A 500 here means the group name is wrong, not that the CLI is broken.

---

### Business Hours & Holidays

**Create business hours:**

```bash
wxcli cc-business-hour create --json-body '{
  "name": "Standard Hours",
  "timezone": "America/New_York",
  "workingHours": [
    {"name": "Weekday", "days": ["MON", "TUE", "WED", "THU", "FRI"], "startTime": "08:00", "endTime": "17:00"}
  ]
}'
```

> **Body shape (verified live 2026-10-13):** the array is `workingHours: [{name, days:["MON",...], startTime, endTime}]`, matching `cc-business-hour create --help`. An earlier version of this example used `businessHours:[{day:"monday",...}]`, which does not match `--help`. The holiday-list example below was not re-tested.

**List business hours:**

```bash
wxcli cc-business-hour list -o json
```

**Create a holiday list:**

```bash
wxcli cc-holiday-list create --json-body '{
  "name": "US Holidays 2026",
  "holidays": [
    {"name": "New Year", "startDate": "2026-01-01", "endDate": "2026-01-01"},
    {"name": "Memorial Day", "startDate": "2026-05-25", "endDate": "2026-05-25"}
  ]
}'
```

---

### Desktop Layout & Desktop Profile

**Create a desktop layout:**

```bash
wxcli cc-desktop-layout create --json-body '{
  "name": "Standard Layout",
  "description": "Default agent desktop"
}'
```

**List desktop layouts:**

```bash
wxcli cc-desktop-layout list-desktop-layout -o json
```

**Create a desktop profile:**

```bash
wxcli cc-desktop-profile create --json-body '{
  "name": "Standard Profile",
  "desktopLayoutId": "LAYOUT_ID"
}'
```

**List desktop profiles:**

```bash
wxcli cc-desktop-profile list-agent-profile -o json
```

---

### Multimedia Profile

**Create a multimedia profile:**

```bash
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
```

Each channel is its own integer limit (`telephony` 0–1, `chat`/`email`/`social` 0–5); all
eight keys above are required by the spec.

**List multimedia profiles:**

```bash
wxcli cc-multimedia-profile list-multimedia-profile -o json
```

---

### Channels & Assets

A **channel** is the medium a contact arrives on; an **asset** is one configured instance of a
channel. Create the channel first — an asset must name an existing `channelId`. Neither group is
prefixed `cc-`: they register as `channel` and `asset`.

**List channels and assets:**

```bash
wxcli channel list-channel --all --fields '[].{id:id,name:name}' -o json
wxcli asset list-asset --all --include-channel-name true -o json
```

**Create a channel — `create` is the BULK endpoint, so the body needs an `items` array:**

```bash
wxcli channel create --json-body '{"items":[{"requestAction":"CREATE","name":"Web Chat","description":"Public website chat","channelType":"CHAT"}]}'
```

**Create an asset against that channel:**

```bash
wxcli asset create --name "Tier 2 Work Items" --channel-type WORK_ITEM --channel-id CHANNEL_ID --business-address "600 Congress Ave, Austin TX"
```

**Before changing or deleting either, check what references it:**

```bash
wxcli channel list-incoming-references CHANNEL_ID
wxcli asset list-incoming-references ASSET_ID
```

Two traps, both in `docs/reference/contact-center-routing.md` §§ 15-16: `asset update` (PUT) is for
**WORK_ITEM** assets and `asset update-asset` (PATCH) is for **CUSTOM_MESSAGING** assets — the
wrong one is a 4xx, so check `channelType` with `asset show` first. And single channel create /
full channel update are multipart (logo upload) and have **no** CLI command; use raw HTTP for those.

---

### Aux Codes & Work Types

**Create an aux code (idle/wrap-up code):**

```bash
wxcli cc-aux-code create --json-body '{
  "name": "Break",
  "description": "Agent on break",
  "isSystemCode": false
}'
```

**List aux codes:**

```bash
wxcli cc-aux-code list-auxiliary-code -o json
```

**Create a work type:**

```bash
wxcli cc-work-types create --json-body '{
  "name": "Follow-up Call",
  "description": "Post-call follow-up"
}'
```

**List work types:**

```bash
wxcli cc-work-types list-work-type -o json
```

---

### Global Variables

**Create a global variable:**

```bash
wxcli cc-global-vars create --json-body '{
  "name": "maxRetries",
  "variableType": "Integer",
  "defaultValue": "3",
  "description": "Max IVR retry attempts"
}'
```

Variable types use **title case**: `--help` lists `String`, `Integer`, `Boolean`, `Decimal`, `DateTime`, `DATE_TIME`. Verified live 2026-10-13: `"variableType":"STRING"` fails with a misleading `400` ("validDefaultValueForVariabelType: defaultValue invalid value...", trackingId `ccconfig_39babbad-89a7-46b0-839f-ed942256433e`), while `"String"` succeeds and the API returns `"String"`. Only `String` was tested live; the other types' casing follows `--help` and `contact-center-core.md` gotcha 21 and is unverified. An `agentViewable` variable also needs `desktopLabel` (gotcha 22).

**List global variables:**

```bash
wxcli cc-global-vars list-cad-variable -o json
```

---

### CC Org Settings & Tenant Configuration

Two tenant-wide records with no create or delete — find the record ID with the v2 list, then
update it. Neither is the Webex `org-settings` group (that is `manage-identity`). Most fields are
marked "User-token updates are not permitted" in the spec; only a few are admin-writable
(**Unverified** — spec-derived, see `docs/reference/contact-center-core.md` §22–§23).

- `cc-org-settings` — entitlements and limits (mostly read-only) plus short/lost-call thresholds,
  recording mode, pause/resume, WebRTC, data masking, routing to same agent. Bare `list` is the
  deprecated v1 endpoint: use `list-organization-setting`. Write with `update-organization-setting`
  (PATCH, partial), not `update` (PUT, 56 required fields).
- `cc-tenant-config` — RONA timeouts per channel, auto wrap-up interval, desktop inactivity, outdial
  DN handling. Bare `list` is deprecated v1: use `list-tenant-configuration`. There is **no PATCH**:
  `update` is a full-replace PUT, so read → edit → send the whole record back.

```bash
wxcli cc-org-settings list-organization-setting -o json
wxcli cc-org-settings update-organization-setting ORG_SETTING_ID --json-body '{"shortCallThreshold": 10}' --verify

wxcli cc-tenant-config list-tenant-configuration -o json
wxcli cc-tenant-config show TENANT_CONFIG_ID -o json > tenant-config.json
wxcli cc-tenant-config update TENANT_CONFIG_ID --json-body file://tenant-config.json --verify
```

---

### Flow Management

**List flows:**

```bash
wxcli cc-flow list PROJECT_ID -o json
```

> **Paging (fixed 2026-10-13):** `cc-flow list --all` returns every flow (56 of 56 live). The default fetch returns 10 and prints a "more pages … `--offset 10`" note. `--offset N` works (translated to `page`/`size`, record-exact; ADR-12), and so does `--page`.

> **Argument order (verified via `--help` and live 2026-10-13):** `show`, `export`, `list-validate`, `delete` take `PROJECT_ID` then `FLOW_ID`. `publish`, `create-lock`, `create-unlock` take `FLOW_ID` then `PROJECT_ID`. The wrong order on `export` returns 404 "Flow … not found".
>
> **Finding the project ID:** no `cc-*` command lists projects. Get a flow id from `cc-entry-point show <id>` (field `flowId`), then read `projectId` from `cc-flow show PROJECT_ID FLOW_ID` (reads do not enforce the project in the path, so any value returns the flow). If you already know a project id, `cc-flow list PROJECT_ID` gives flow ids.

**Show a flow (full definition):**

```bash
wxcli cc-flow show PROJECT_ID FLOW_ID -o json
```

Returns the full flow definition (FlowIr schema 2.0), including `projectId`.

**Export a flow:**

```bash
wxcli cc-flow export PROJECT_ID FLOW_ID -o json
```

Use `--version` to specify a version: `draft`, `latest`, or a specific version ID.

```bash
wxcli cc-flow export PROJECT_ID FLOW_ID --version draft -o json
```

> **NOTE:** `cc-flow export` emits the full export envelope (15 keys incl. `schemaVersion`, `id`, `name`, `nodes`, `edges`, `variables`, `eventFlows`, `preferences`), verified 2026-10-13. (An earlier CLI build printed only `nodes`; fixed.) `show -o json` returns the full flow definition.

**Publish a flow:**

```bash
wxcli cc-flow publish FLOW_ID PROJECT_ID --comment "Initial publish"
```

Use `--json-body` for additional publish options (e.g., tag IDs):

```bash
wxcli cc-flow publish FLOW_ID PROJECT_ID --json-body '{
  "comment": "Production release",
  "tagIds": ["TAG_ID"]
}'
```

**Validate, lock, import:**

```bash
wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json
wxcli cc-flow list-validate PROJECT_ID FLOW_ID   # returns {valid, results}
wxcli cc-flow create-lock FLOW_ID PROJECT_ID
wxcli cc-flow create-unlock FLOW_ID PROJECT_ID
wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json
```

> **NOTE:** Lock/unlock return 200 "OK" but no command exposes lock state for read-back.

**Activity catalog (read-only, added 2026-10-13, all returned 200 live):**

```bash
wxcli cc-flow list-activities PROJECT_ID
wxcli cc-flow show-activity PROJECT_ID ACTIVITY_NAME
wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY_NAME INPUT_NAME
wxcli cc-flow list-event-specifications PROJECT_ID
```

> A dependent input (e.g. `queue-contact` `destination`) returns 400 "requires a parent value" unless you also pass `--parent-input-name channelType --parent-value TELEPHONY`. Use these to look up activity names, inputs and choice values when hand-writing a FlowIr body; raw `GET /v2/activities` is the fallback. `cc-flow list-search` is not routed on us1: the API gateway returns an empty-body 404 (`GTWY_` trackingId) for every path and parameter variant while `…/flows` returns 200 (verified 2026-10-13). Search by name with `cc-flow list PROJECT_ID --all --fields "[?contains(name, 'X')].name"`.
>
> **`create-validate` is safe to run but not authoritative.** It is a POST that changes nothing, but `valid:false` can be a false positive. Two are proven (verified live 2026-10-13, against Designer-built flows): `ivr-collectdigits` has no accepted success-edge condition (`default`, `out`, `done`, `success` all rejected, yet Designer writes `default`), and `FC1038 Variable 'X' is referenced but not declared` fires on every `{{Node.Output}}` reference except the start node's (`{{NewContact.ANI}}` passes). It also reports only **one** edge-condition error per call, and edge checks gate the FC checks, so errors appear one layer at a time. `cc-flow publish` (without `--skip-validation`) succeeded on a draft that `list-validate` reported as `ERROR FC1038`, so neither validate endpoint is the publish gate. Treat validate as a way to find real errors (FC1015, FC1024, missing start-node fields), not a pass/fail verdict.
>
> **Import works (verified live 2026-10-13; supersedes the earlier "HTTP 500 / not demonstrated" note).** `cc-flow create-import` (POST `/{orgId}/project/{projectId}/v2/flows:import`) created a 43-node flow on the first try from a well-formed FlowIr 2.0 body; `show` read back identical. It is a **full create**: a name clash returns `409 FLOW_ALREADY_EXISTS` unless `--overwrite true`. The response can carry non-fatal preflight warnings (`preflightWarningsCount`) that dry-run validate does not report. The earlier 500s (trackingIds `<trackingId-1>`, `<trackingId-2>`) were on export-derived bodies, cause unproven. **Hypothesis (not re-tested):** the incomplete start-node `flowType`.
>
> **Exports do not round-trip (as observed):** `create-validate` on export-derived bodies returned `valid:false` with errors such as "key not found: eventSourceName" and "Condition 'default' is not valid for activity 'bridged-transfer'". Likely cause (not proven): the start node's incomplete `flowType` plus the validator false positives above.

**Building a flow from scratch (condensed; full detail, port table and example body in `docs/reference/contact-center-routing.md` §11, "Building a flow from scratch"):**

1. **Use FlowIr 2.0, not the shape in `--help` or the spec.** The `--help`/FlowV2 example (nodes `{name, activityName, inputs, outputs, position}`, edges `{key, from_node, from_port, to_node, condition}`, `flowName`, `eventFlows: []`) fails `create-validate` with `400 main flow edge from must not be empty.; main flow edge to must not be empty.` and `No start node found. Add one node with activityType='start'`. The server reads: top level `{schemaVersion:"2.0", name, flowType:"FLOW", description, variables:[], nodes:[], edges:[], eventFlows:{nodes:[],edges:[]}, preferences:[]}` (`eventFlows` is an object); node `{name, activityType:"start"|"action"|"end", properties:{activityName, <inputs flat>}}`; edge `{from, to, condition}`. No `position`.
2. **Start node.** Must be activity `NewContact` (`NewPhoneContact` gives `FC1024`) with all six `flowType` fields (omitting the `*Name` ones gives `FC0000 ... key not found: eventSourceName`):
   `{"name":"NewContact","activityType":"start","properties":{"name":"NewContact","activityName":"NewContact","activityId":"start","event":"NewContact","flowType":{"eventSourceId":"5eff0e2eb10162499bc9f932","eventSourceName":"WebexContactCenter","eventClassificationId":"5f10475cf021306e89e1692c","eventClassificationName":"VoiceInteractions","eventSpecificationId":"5f2d02144332507e39cc8a7f","eventSpecificationName":"ContactStartWorkflow"}}}`
3. **Edge `condition` names seen in the published body:** start and `set-variable` use `out` (+ `error`); `play-message`, `play-music`, `queue-contact`, `callback` use `default` (queue-contact and callback also `failure`); `ivr-menu` uses the digit plus `timeout`/`invalid`/`error`; `ivr-collectdigits` uses `default` (validator rejects it, see above) plus `timeout`/`invalid`/`error`; `condition-activity` uses `true`/`false`/`error`; `business-hours` uses `workingHours`/`holidays`/`override`/`default`/`error`. `queue-contact` `failure` draws a non-fatal import WARNING ("Use one of: default").
4. **Variables.** A global variable in FlowIr is `{name, type, value, source:"GLOBAL", id:"<global var id>", ...}`; a flow-local one has `source:""`, `id:""`. An `isCAD:true` (agent-viewable) variable needs a non-empty `desktopLabel` or validate returns `FC1015` (also for globals re-declared in the flow).
5. **Sequence that worked (verified live 2026-10-13):** create queues, business hours and globals first and take their ids from the read-back, then `create-import` the flow, `show` it to compare, `publish FLOW_ID PROJECT_ID`, then create the entry point with `flowId` + `flowTagId` (see Entry Point). No test call was placed, so none of it is runtime-verified.
6. **Recipe notes, not runtime-tested.** *Callback:* `callback` with `toggleCallbackDestination: false` calls back into the queue the contact is already in, which avoids a `{{QueueNode.QueueId}}` reference (and its FC1038 false positive). *Bilingual prompts:* with the built-in "Cisco Cloud Text-to-Speech" connector the voice follows the `Global_Language` / `Global_VoiceName` globals; a language-specific `set-variable` node sets them (`es-US` / `es-US-Alonso` for Spanish) plus prompt-text variables, and one set of nodes speaks `{{msgX}}`.
7. **Demo data in global variables is not live data.** A value such as a static restoration time ("9:30 PM tonight") or area name stored in a global variable is spoken on every call until someone edits the variable, whether or not it is still true. That is acceptable for a demo only if everyone knows it. A real deployment would fetch it per call (for example an HTTP Request node against the outage system, via an HTTP Connector). **The HTTP Request alternative was not built or tested here;** for HTTP Request node mechanics in flows, see `docs/reference/contact-center-routing.md` gotchas #16-17 and `docs/reference/contact-center-core.md` gotcha #25, which were written for other calls (JDS events, CC APIs), not an outage system.

#### Readiness checklist — before the first test call (new inbound voice flow)

Source: a read-only audit run live on 2026-10-13 against a new number → entry point → flow → 4 queues → team → agents chain (no writes made). Every row is an API read; none of it replaces a test call. Compare each new resource against one that already takes calls: same fields except the ones you meant to change.

| # | Check | Command(s) | What "ready" looked like |
|---|---|---|---|
| 1 | Calling side of the number | `wxcli numbers list --all -o json` (filter to the number) | ACTIVE, PRIMARY, PSTN_NUMBER, same location as a working number, **owned by a `CONTACT_CENTER_ADAPTER`** ("Contact Center RTMS"). Same location means the same PSTN connection. Whether the carrier delivers calls is not visible here |
| 2 | DN mapping | `wxcli cc-dial-number list --all -o json` | Mapping points at your entry point; `location`/`regionId` match a working mapping; only the entry point and `id` differ (`defaultAni: true` marks the tenant's default outdial number, leave it alone) |
| 3 | Entry point → flow | `wxcli cc-entry-point show ID -o json` vs a working one | INBOUND, TELEPHONY, active, `flowId` set, `flowTagId` set (`Latest`), music file set. Differences from a working entry point should be intended ones (e.g. `callbackEnabled`) |
| 4 | Published version | `wxcli cc-flow list PROJECT_ID --partial-name-search NAME --all` | Status `Published`, a version number, and the tag the entry point uses (`Latest`) pointing at it. A later publish moves `Latest` immediately, so do not publish edits mid-test |
| 5 | Every ID in the flow is a valid choice | `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY --validate true --search QUEUE_ID` (also `business-hours businessHoursId`, `play-music prompt`, `play-message connector`) | The ID resolves. Run one negative control (an all-zeros UUID) and confirm it returns `[]`, otherwise a hit proves nothing |
| 6 | Global variables the flow reads | `wxcli cc-global-vars show ID` per variable | Each exists and is active |
| 7 | Queues route to a team | `wxcli cc-queue show-contact-service-queue-v2 ID` (not the list, which omits `callDistributionGroups`) | active, INBOUND, TELEPHONY, `callDistributionGroups` → your team, music set, `maxTimeInQueue` as intended |
| 8 | Team has agents | `wxcli cc-team show ID` | active, `userIds` non-empty, site set |
| 9 | Agents are licensed and enabled | `wxcli cc-users list --all -o json`; `wxcli people show PERSON_ID --calling-data true`; `wxcli licenses list --all` | `contactCenterEnabled` and `agentCapabilitiesEnabled` true; a Contact Center agent license and a Webex Calling license; check `invitePending` (an agent who never accepted the invite probably cannot sign in: inferred, not tested) |
| 10 | Profile allows voice | `wxcli cc-desktop-profile show ID` (`loginVoiceOptions` includes the option the agent will use, e.g. `BROWSER`); `wxcli cc-multimedia-profile show ID` (telephony slot ≥ 1). A user with no multimedia profile of their own inherits the team's, else the site's: `wxcli cc-site show ID` | Voice allowed on the profile the agent actually inherits |
| 11 | **Someone is logged in and Available** | See "Agent session state" below | At least one active agent session in a team the queue routes to. **A queue with zero active sessions holds callers on music until `maxTimeInQueue`, then drops them.** This is an operations step, not configuration |
| 12 | Business hours + timezone | `wxcli cc-business-hour show ID` | Timezone correct, hours cover the test time, holiday list/override as intended |
| 13 | Agent-viewable variables | Flow export `variables`; `wxcli cc-desktop-layout list-desktop-layout --all` | Each agent-viewable variable has a `desktopLabel`, and the flow declares it `isCAD:true` (a global record marked agentViewable but declared `isCAD:false` in the flow will not show). The system default layout shows these variables, so a custom layout is not required |
| 14 | Wrap-up codes | `wxcli cc-aux-code list --all` | Active `WRAP_UP_CODE` entries exist so the agent can finish the call |

**Agent session state.** `wxcli cc-agents list-activities --from EPOCH_MS` is an event log (24 h window max per call, see `--help`); zero rows prove nothing by themselves. The audit cross-checked with `wxcli cc-search create` (GraphQL, `--help` shows the body) against the `agentSession` type: a 365-day query returned the real session history (so the probe works), and the sessions with `isActive: true` were counted. The query text was not saved, so build it from `wxcli cc-search-metadata list` and `wxcli cc-search create --generate-json-body`. If the count is 0, a person must sign in to Agent Desktop and go **Available** before the test call.

**Only a live test call can prove** (no API read can):
- That the carrier delivers the number to Contact Center.
- The TTS voices (English `Automatic`, Spanish voices driven by the `Global_Language` / `Global_VoiceName` globals).
- collect-digits behavior: the `default` success edge firing and `{{Node.DigitsEntered}}` landing in the variable (the validator rejects both; see above).
- Expressions and nested `{{variable}}` references inside set-variable values resolving at runtime.
- The business-hours port names (`workingHours`/`holidays`/`override`/`default`) at runtime.
- The callback path (offer to the agent, which ANI is used when `callbackAni` is unset).
- The `queue-contact` `failure` edges, which only fire when a queue fails.
- That Agent Desktop shows the agent-viewable variables.

---

### JDS (Journey Data Service) — Flow Designer Integration

JDS tracks customer journey events. The two most common flow patterns are:

**1. Detect returning caller at flow entry**

Query JDS by CallerANI at the start of the flow using an HTTP Request node:

```
Method: GET
URL: https://api.wxcc-{region}.cisco.com/admin/v1/api/person/workspace-id/{{CJDS_Workspace_ID}}/aliases/{{CallerANI}}
Authorization: Bearer {{cc_oauth_token}}
```

- **200 + data array** → caller exists in JDS; check event history to determine if returning
- **NOT_FOUND** → first-time caller (no prior contacts)
- CallerANI must be E.164 with `+1` prefix — WXCC writes ANI that way, so `+19105551234`, not `9105551234`

**2. Post a custom event from a flow**

Use an HTTP Request node to record a business event (e.g., store verified, order looked up):

```
Method: POST
URL: https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId={{CJDS_Workspace_ID}}
Authorization: Bearer {{cc_oauth_token}}
Content-Type: application/json
```

Body:
```json
{
  "id": "{{DialedDNIS}}-{{CallerANI}}",
  "specversion": "1.0",
  "type": "custom:your_event_type",
  "source": "wxcc_flow",
  "identity": "{{CallerANI}}",
  "identitytype": "phone",
  "datacontenttype": "application/json",
  "data": {
    "event": "your_event_type"
  }
}
```

> `workspaceId` goes on the query string — the body schema has no `workspaceId` field.
> The URL must be a full absolute URL — relative paths return HTTP 500.
> `id` must be unique per event (use a combination of flow variables to ensure uniqueness).
> A successful post returns `"Accepted for processing"` — JDS ingests asynchronously.

**Query events for a person (wxcli):**

```bash
wxcli cc-journey show-workspace-id-events WORKSPACE_ID --identity "+19105551234" --filter "type=='custom:your_event_type'" -o json
```

Filter uses RSQL syntax. Omit `--filter` to return all events for that identity.

---

### SCIM User Lookup from Flow Designer

Use this pattern to look up a Webex user's identity data (e.g. alternate phone number, userName, ID) from within a WxCC flow using HTTP Request nodes.

**Authentication:** The SCIM API (`/identity/scim/`) requires `identity:people_read` scope — separate from `spark-admin:people_read`. PATs expire after 12 hours. For production use an OAuth Integration or Service App with `identity:people_read` explicitly selected at developer.webex.com.

**Phone number types:** `work`, `mobile`, `fax`, `work_extension`, `alternate1`, `alternate2`

---

**Node 1 — Search by alternate1 phone number (DNIS)**

Before this node, add a Set Variable node to strip the `+` from DNIS:

```
Variable: DNIS
Expression: {{NewContact.DNIS | slice(1)}}
```

> `| slice(1)` works in WxCC Flow Designer. `| replace("+", "%2B")` does NOT — `+` is a regex special character and fails silently. `.substring(1)` also does not work.

HTTP Request node config:
- **Method:** GET
- **URL:** `https://webexapis.com/identity/scim/{orgId}/v2/Users`
- **Header:** `Authorization: Bearer {token}`
- **Query param key:** `filter`
- **Query param value:** `phoneNumbers%5Btype%20eq%20%22alternate1%22%20and%20value%20eq%20%22%2B{{DNIS}}%22%5D`
- **Output variable:** `StoreUserPersonId` ← JSONPath: `$.Resources[0].id`

Decoded filter: `phoneNumbers[type eq "alternate1" and value eq "+19197010928"]`

Key syntax rules:
- No space before `[` — `phoneNumbers[...]` not `phoneNumbers [...]`
- `+` must be hardcoded as `%2B` in the filter — the SCIM server decodes bare `+` as a space, returning zero results
- `phoneNumbers.value eq "..."` dot notation returns 400 and is not implemented despite being documented

---

**Node 2 — Get full user profile by ID**

HTTP Request node config:
- **Method:** GET
- **URL:** `https://webexapis.com/identity/scim/{orgId}/v2/Users/{{StoreUserPersonId}}`
- **Header:** `Authorization: Bearer {token}`
- **Query param:** `attributes=id,userName,phoneNumbers` (optional — trims response)
- **Output variable:** `StoreExtension` ← JSONPath: `$.phoneNumbers[?(@.type=='alternate1')].value`

Response is the raw user object (no `Resources` wrapper), so JSONPath starts at `$.phoneNumbers` not `$.Resources[0].phoneNumbers`.

The `[?(@.type=='alternate1')]` filter expression is supported in WxCC Flow Designer's JSONPath parser.

---

### Auto CSAT

**Show Auto CSAT configuration:**

```bash
wxcli cc-auto-csat show-auto-csat AUTO_CSAT_ID -o json
```

**Update Auto CSAT settings:**

```bash
wxcli cc-auto-csat update AUTO_CSAT_ID --json-body '{...}'
```

**List Auto CSAT entries:**

```bash
wxcli cc-auto-csat list -o json
```

**List Auto CSAT questions:**

```bash
wxcli cc-auto-csat list-question AUTO_CSAT_ID -o json
```

---

### Call Monitoring

**Create a monitoring session:**

```bash
wxcli cc-call-monitoring create --json-body '{
  "id": "REQUEST_ID",
  "monitorType": "midcall",
  "taskId": "TASK_ID"
}'
```

> **Unverified:** body keys are from the spec, not a live call. `id` (your own request id,
> ≤36 chars) and `monitorType` (`midcall`, `adhoc` or `continuous`) are required; `taskId` is
> mandatory for `midcall`. To monitor an agent's calls rather than one task, send
> `"agents": ["AGENT_ID"]` (or `queueIds`/`teams`/`sites`) instead of `taskId`.

**Barge into a call:**

```bash
wxcli cc-call-monitoring create-barge-in TASK_ID
```

**List active monitoring sessions:**

```bash
wxcli cc-call-monitoring list -o json
```

**End a monitoring session:**

```bash
wxcli cc-call-monitoring create-end TASK_ID
```

**Monitoring schedules (`cc-monitoring-schedules`) — a stored plan, not a live session.** Use this
group when the ask is "supervisor X monitors team Y on weekday mornings"; use `cc-call-monitoring`
above when the ask is "listen to this call now". A schedule never attaches anyone to a call by
itself being created (**Unverified** — spec-derived). Bare `list` here is the **v2** endpoint (there
is no v1 list, unlike `cc-team`); prefer `update-call-monitoring` (PATCH, partial) over `update`
(PUT, full replace). `teams` and `contactServiceQueues` are required (at least one each) and have
no flags, so create needs `--json-body`. Timestamps are epoch milliseconds (integers).

```bash
wxcli cc-monitoring-schedules create --json-body '{"name":"Morning Shift Monitoring","timezone":"America/New_York","recurrence":true,"daysOfWeek":["MON","TUE","WED","THU","FRI"],"startTimestamp":1772169240000,"endTimestamp":1772244000000,"userId":"SUPERVISOR_USER_ID","paused":false,"agentsAccessType":"ALL","teams":[{"id":"TEAM_ID"}],"contactServiceQueues":[{"id":"QUEUE_ID"}]}'

wxcli cc-monitoring-schedules update-call-monitoring SCHEDULE_ID --paused --verify

# Users a schedule covers — note `cc-users show` takes a SCHEDULE id, not a user id
wxcli cc-users show SCHEDULE_ID -o json
```

Details and gotchas: `docs/reference/contact-center-core.md` §21.

---

### Event Subscriptions

**Create a subscription:**

```bash
wxcli cc-subscriptions create --json-body '{
  "name": "Agent Events",
  "eventTypes": ["AgentStateChange", "TaskRouted"],
  "destinationUrl": "https://example.com/webhook"
}'
```

The webhook target is `destinationUrl` (HTTPS); `name`, `eventTypes` and `destinationUrl`
are required by the spec.

**List subscriptions:**

```bash
wxcli cc-subscriptions list -o json
```

**List available event types:**

```bash
wxcli cc-subscriptions list-event-types-v2 -o json
```

---

### Task Management

**List tasks:**

```bash
wxcli cc-tasks list --from 1784592000000 -o json
```

**Accept a task:**

```bash
wxcli cc-tasks create-accept-tasks TASK_ID
```

**Transfer a task:**

```bash
wxcli cc-tasks create-transfer-tasks TASK_ID --to QUEUE_OR_AGENT_ID --destination-type queue
```

**Wrap up a task:**

```bash
wxcli cc-tasks create-wrapup TASK_ID --aux-code-id AUX_CODE_ID --wrap-up-reason "Resolved"
```

**Hold/unhold a task:**

```bash
wxcli cc-tasks create-hold TASK_ID --media-resource-id MEDIA_RESOURCE_ID
wxcli cc-tasks create-unhold TASK_ID --media-resource-id MEDIA_RESOURCE_ID
```

---

### Deployment Plan Template

Before executing any commands, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Resource type: [queue / entry point / team / skill / flow / ...]
Operation:     [create / update / delete]
Region:        [us1 / eu1 / ...]

Configuration:
  Name: [resource_name]
  [Resource-specific settings listed here]

Dependencies:
  ✓ Site exists: [site_name] ([site_id])
  ✓ [Prerequisite 1]: [name] ([id])
  ✓ [Prerequisite 2]: [name] ([id])

Commands to execute:
  wxcli cc-[group] [command] --json-body '{...}'

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

## Step 6: Execute via wxcli

Run the command(s) from the approved deployment plan. If the operation requires multiple steps (e.g., create team then assign agents), execute them in order.

Handle errors explicitly:

### Generic errors

- **401/403**: Token expired or insufficient scopes — run `wxcli configure` to re-authenticate. A 403 with a `ccconfig_` trackingId means the token lacks `cjp:config_read` / `cjp:config_write`; use an OAuth integration or Service App with those scopes selected and re-authorize after adding scopes.
- **403 with scope hint**: The CLI detects CC 403 errors and prints a scope tip. Follow the guidance.
- **409**: Name conflict — ask user for alternate name.
- **400**: Validation error — read the error message and fix the parameter.
- **404**: Resource not found — verify the ID and region are correct.

### CC-specific errors

- **Region mismatch**: If calls fail with connection errors, verify the region is correct: `wxcli set-cc-region <region>`. The CC API base URL is `api.wxcc-{region}.cisco.com`.
- **orgId injection**: The CLI auto-injects `orgId` from the authenticated user's org. If operating on a partner-managed org, ensure `wxcli configure` has the correct org selected.
- **v1 vs v2 endpoints**: Some CC groups have both v1 (bulk) and v2 (CRUD) endpoints. Prefer v2 commands (e.g., `list-contact-service-queue-v2` over `list`).
- **Bulk operations**: v1 bulk endpoints (`create`, `list`) handle multiple resources at once. Use these for migrations or large-scale provisioning.

## Step 7: Verify creation

After execution, fetch the resource back and confirm:

```bash
# Queue
wxcli cc-queue show-contact-service-queue-v2 QUEUE_ID -o json

# Entry point
wxcli cc-entry-point show ENTRY_POINT_ID -o json

# Team
wxcli cc-team show TEAM_ID -o json

# Skill
wxcli cc-skill show SKILL_ID -o json

# Skill profile
wxcli cc-skill-profile show SKILL_PROFILE_ID -o json

# Site
wxcli cc-site show SITE_ID -o json

# Dial plan
wxcli cc-dial-plan show DIAL_PLAN_ID -o json

# Business hours
wxcli cc-business-hour show BH_ID -o json

# Desktop profile
wxcli cc-desktop-profile show PROFILE_ID -o json

# Multimedia profile
wxcli cc-multimedia-profile show MM_PROFILE_ID -o json

# Global variable
wxcli cc-global-vars show VAR_ID -o json

# Aux code
wxcli cc-aux-code show AUX_ID -o json

# Subscription
wxcli cc-subscriptions show SUBSCRIPTION_ID -o json

# CC user (show-user, not show — `cc-users show` takes a monitoring schedule ID)
wxcli cc-users show-user USER_ID -o json

# Auto CSAT
wxcli cc-auto-csat show-auto-csat AUTO_CSAT_ID -o json
```

## Step 8: Report results

Present the results:

```
CC RESOURCE CONFIGURED
======================
Type: [resource_type]
Name: [name]
ID: [resource_id]
Region: [cc_region]

Configuration:
  [Key settings confirmed]

Next steps:
  - [Resource-specific next steps]
  - [e.g., "Assign flow to entry point"]
  - [e.g., "Add agents to team"]
  - [e.g., "Map dial number to entry point"]
```

---

## Critical Rules

1. **Always set CC region first.** Before any `cc-*` command, ensure the region is set: `wxcli set-cc-region <region>`. CC API calls go to `api.wxcc-{region}.cisco.com`, not `webexapis.com`.
2. **CC config calls need `cjp:config_read` / `cjp:config_write` on the token.** A full-admin PAT worked for CC config reads and flow writes on one org (verified live 2026-10-13), so try the current token first. On a 403 (`ccconfig_` trackingId) the token lacks those scopes — use an OAuth integration or Service App with them selected. The CLI detects 403 and prints a scope tip.
3. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing.
4. **Prefer v2 commands over v1.** v2 endpoints are CRUD-oriented (single resource). v1 endpoints are bulk-oriented (arrays). For individual creates/updates, use the v2 variant (e.g., `create-contact-service-queue-v2`, `list-entry-point-v2`).
5. **orgId is auto-injected.** The CLI resolves `orgId` from the authenticated user's org. No need to pass it manually.
6. **Most CC creates use `--json-body`.** CC resources have complex nested structures. Use `--json-body '{...}'` for creates and updates.
7. **Dependency order matters.** Create resources in this order: sites → skills → skill profiles → multimedia profiles → desktop layouts → desktop profiles → teams → entry points → queues → dial plans → dial numbers → flows.
8. **Delete in reverse dependency order.** When tearing down: flows → dial numbers → dial plans → queues → entry points → teams → desktop profiles → desktop layouts → multimedia profiles → skill profiles → skills → sites.
9. **Bulk operations for migrations.** For large-scale provisioning, use the v1 bulk endpoints (`cc-team create-bulk`, `cc-skill create-bulk`, `cc-site create-bulk`). These accept arrays of resources.
10. **Audio files must be uploaded before flow references.** If a flow references an audio prompt, upload it via `cc-audio-files` first.
11. **Campaign prerequisites are strict.** Campaigns require: contact list, outdial ANI, outbound entry point. Verify all three exist before starting a campaign.
12. **Task commands are real-time agent operations.** `cc-tasks` commands (accept, hold, transfer, wrapup) operate on live calls. Confirm with the user before executing.
13. **Monitoring is supervisor-only.** `cc-call-monitoring` commands require supervisor privileges. The authenticated user must have the CC supervisor role.
14. **Journey API is complex.** `cc-journey` has 41 commands across workspaces, templates, persons, identities, and subscriptions. Read `docs/reference/contact-center-journey.md` before using. Key gotchas: alias lookup is exact after stripping `+` (no country-code normalization); WXCC writes ANI in E.164 so lookups must use `+1` prefix; events are immutable (no delete); event filter uses RSQL syntax (`type=='custom:event_name'`); Publish API requires `workspaceId` as a query param not in the body. For posting events from Flow Designer, see `docs/reference/contact-center-routing.md` gotchas #16–18.
15. **Cross-skill handoffs:**
    - Webex Calling features (AA, CQ, HG) → `configure-features` skill
    - Customer Assist (CX Essentials on Calling queues) → `customer-assist` skill
    - Webex Calling reporting (CDR, queue stats) → `reporting` skill
    - Person/workspace call settings → `manage-call-settings` skill
    - Webex Calling routing (trunks, route groups, PSTN) → `configure-routing` skill (CC dial plans stay in this skill)
    - Location teardown → `teardown` skill

---

## Common Workflows

### Workflow A: Set up a basic inbound voice queue

1. Verify site exists → `wxcli cc-site list -o json`
2. Create multimedia profile → `wxcli cc-multimedia-profile create --json-body '...'`
3. Create team → `wxcli cc-team create --json-body '...'`
4. Create entry point → `wxcli cc-entry-point create --json-body '...'`
5. Create queue → `wxcli cc-queue create-contact-service-queue --json-body '...'` (`cc-queue create` is the bulk endpoint)
6. Map dial number → `wxcli cc-dial-number create --json-body '...'`
7. Create/assign flow → `wxcli cc-flow publish FLOW_ID PROJECT_ID --comment "..."`
8. Verify end-to-end → list all resources and confirm IDs are linked

### Workflow B: Add skill-based routing

1. Create skill definitions → `wxcli cc-skill create --json-body '...'` (one per skill)
2. Create skill profiles → `wxcli cc-skill-profile create --json-body '...'`
3. Update queue routing type → `wxcli cc-queue update --json-body '{"routingType": "SKILLS_BASED", ...}'`
4. Assign skill profiles to teams/agents
5. Verify queue-to-skill mapping → `wxcli cc-queue list-skill-based-queues SKILL_PROFILE_ID -o json`
6. Verify user queue assignments → `wxcli cc-queue list-agent-based-queues USER_CI_ID -o json`

### Workflow C: Set up outbound campaign

1. Configure outdial ANI → `wxcli cc-outdial-ani create --json-body '...'`
2. Upload contact list → `wxcli cc-contact-list create --json-body '...'`
3. Create outbound entry point → `wxcli cc-entry-point create --json-body '...'`
4. Start campaign → `wxcli cc-campaign create --json-body '...'`
5. Verify it joined its group → `wxcli cc-campaign-group list "GROUP_NAME" -o json`

### Workflow D: Configure agent monitoring

1. Create event subscription → `wxcli cc-subscriptions create --json-body '...'`
2. Monitor live calls → `wxcli cc-call-monitoring create --json-body '...'`
3. Barge in if needed → `wxcli cc-call-monitoring create-barge-in TASK_ID --json-body '...'`

### Workflow E: Reskill agents

1. List current user skill assignments → `wxcli cc-users show-user USER_ID -o json`
2. List users by dynamic skill → `wxcli cc-users show-by-dynamic-skill-id SKILL_ID -o json`
3. Bulk update dynamic skills → `wxcli cc-users update-dynamic-skill SKILL_ID --json-body '...'`
4. Reassign skill profile → `wxcli cc-users update-reskill USER_ID --json-body '...'`
5. Verify updated queues → `wxcli cc-queue list-agent-based-queues USER_CI_ID -o json`

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from conversation history to recover what was planned
2. Check what's already been created: run the relevant `list` commands for each resource type
3. Resume from the first incomplete step
