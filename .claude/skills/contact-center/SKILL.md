---
name: contact-center
description: |
  Provision and manage Webex Contact Center resources using wxcli CLI commands:
  agents, queues, entry points, teams, skills, flows, campaigns, dial plans,
  desktop profiles, and monitoring. Guides the user from prerequisites through
  execution and verification.
  Use for: create, update, delete, list, configure, or troubleshoot any CC resource.
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
3. Read `docs/reference/contact-center-analytics.md` for AI features, journey analytics, monitoring, subscriptions, tasks

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

The user may need to re-authenticate with CC scopes enabled.

## Step 3: Identify the operation

Ask the user what they want to configure. Present this decision matrix if they are unsure:

### Agent Management

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Manage agent state (login, logout, state changes) | Agent lifecycle | `cc-agents` |
| Configure agent greetings | Upload/assign greeting files | `cc-agent-greetings` |
| View agent summaries | Agent activity summaries | `cc-agent-summaries` |
| Agent wellbeing settings | Burnout/wellness config | `cc-agent-wellbeing` |
| Manage user profiles | Agent desktop/permissions profiles | `cc-user-profiles` |
| Manage CC users | CC user CRUD | `cc-users` |

### Queue & Routing

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Configure queues | Create/update/delete contact service queues | `cc-queue` |
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

### Flows & Automation

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Manage flows | Import/export/publish flows | `cc-flow` |
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
| Call monitoring | Monitor/barge/coach live calls | `cc-call-monitoring` |
| Real-time stats | Real-time queue/agent statistics | `cc-realtime` |
| Event subscriptions | Subscribe to CC events (webhooks) | `cc-subscriptions` |
| Task management | Agent task lifecycle (accept, hold, transfer, wrapup) | `cc-tasks` |
| Notifications | Notification management | `cc-notification` |
| Search | Search CC resources | `cc-search` |
| Address books | Address book management | `cc-address-book` |

### Not Contact Center?

| Need | Redirect To |
|------|-------------|
| Webex Calling features (AA, CQ, HG) | `configure-features` skill |
| Person/workspace call settings | `manage-call-settings` skill |
| Webex Calling reporting (CDR) | `reporting` skill |
| Customer Assist on a Calling queue | `customer-assist` skill |
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
| Entry point exists | `wxcli cc-entry-point list -o json` | Create entry point first |
| Team exists (for team-based routing) | `wxcli cc-team list -o json` | Create team first |
| Skill profiles (for skill-based routing) | `wxcli cc-skill-profile list -o json` | Create skills and skill profiles first |

#### Teams

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Site exists | `wxcli cc-site list -o json` | Create site first |
| Multimedia profile exists | `wxcli cc-multimedia-profile list -o json` | Create multimedia profile first |
| Skill profile (optional) | `wxcli cc-skill-profile list -o json` | Create if using skill-based routing |

#### Campaigns

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Contact list uploaded | `wxcli cc-contact-list list -o json` | Upload contact list first |
| Outdial ANI configured | `wxcli cc-outdial-ani list -o json` | Configure outbound caller ID first |
| Entry point exists (outbound) | `wxcli cc-entry-point list -o json` | Create outbound entry point |

#### Flows

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Audio files uploaded (if used in flow) | `wxcli cc-audio-files list -o json` | Upload audio files first |
| Global variables defined (if used) | `wxcli cc-global-vars list -o json` | Create global variables first |

#### Skill Profiles

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Skills defined | `wxcli cc-skill list -o json` | Create skill definitions first |

#### Desktop Profiles

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Desktop layout exists | `wxcli cc-desktop-layout list -o json` | Create or use default layout |

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

**CLI command (v2 — preferred):**

```bash
wxcli cc-queue create-contact-service-queue-v2 --json-body '{
  "name": "Support Queue",
  "channelType": "telephony",
  "routingType": "LONGEST_AVAILABLE_AGENT"
}'
```

**List queues:**

```bash
wxcli cc-queue list-contact-service-queue-v2 -o json
```

**Show specific queue:**

```bash
wxcli cc-queue show-contact-service-queue-v2 QUEUE_ID -o json
```

---

### Entry Point

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique entry point name |
| Channel type | Yes | `telephony`, `chat`, `email`, `social` |
| Service level threshold | No | Seconds |
| Flow ID | No | Assigned flow for routing |

**CLI command (v2 — preferred):**

```bash
wxcli cc-entry-point create-entry-point --json-body '{
  "name": "Main IVR",
  "channelType": "telephony"
}'
```

**List entry points:**

```bash
wxcli cc-entry-point list-entry-point-v2 -o json
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
wxcli cc-skill list -o json
```

**Create a skill profile:**

```bash
wxcli cc-skill-profile create-skill-profile --json-body '{
  "name": "Bilingual Agent",
  "description": "English + Spanish",
  "skills": [
    {"skillId": "SKILL_ID", "skillValue": 8}
  ]
}'
```

**List skill profiles:**

```bash
wxcli cc-skill-profile list-skill-profile-v2 -o json
```

---

### Dial Plan & Dial Number

**Create a dial plan:**

```bash
wxcli cc-dial-plan create-dial-plan --json-body '{
  "name": "US Dial Plan",
  "description": "US domestic dialing rules"
}'
```

**List dial plans:**

```bash
wxcli cc-dial-plan list-dial-plan-v2 -o json
```

**Map a dial number to an entry point:**

```bash
wxcli cc-dial-number create --json-body '{
  "dialNumber": "+18005551234",
  "entryPointId": "ENTRY_POINT_ID"
}'
```

---

### Business Hours & Holidays

**Create business hours:**

```bash
wxcli cc-business-hour create --json-body '{
  "name": "Standard Hours",
  "timezone": "America/New_York",
  "businessHours": [
    {"day": "monday", "startTime": "08:00", "endTime": "17:00"},
    {"day": "tuesday", "startTime": "08:00", "endTime": "17:00"},
    {"day": "wednesday", "startTime": "08:00", "endTime": "17:00"},
    {"day": "thursday", "startTime": "08:00", "endTime": "17:00"},
    {"day": "friday", "startTime": "08:00", "endTime": "17:00"}
  ]
}'
```

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
wxcli cc-desktop-layout list -o json
```

**Create a desktop profile:**

```bash
wxcli cc-desktop-profile create-agent-profile --json-body '{
  "name": "Standard Profile",
  "desktopLayoutId": "LAYOUT_ID"
}'
```

**List desktop profiles:**

```bash
wxcli cc-desktop-profile list -o json
```

---

### Multimedia Profile

**Create a multimedia profile:**

```bash
wxcli cc-multimedia-profile create-multimedia-profile --json-body '{
  "name": "Voice Only",
  "mediaTypes": [
    {"media": "telephony", "maxCount": 1}
  ]
}'
```

**List multimedia profiles:**

```bash
wxcli cc-multimedia-profile list-multimedia-profile-v2 -o json
```

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
wxcli cc-aux-code list -o json
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
wxcli cc-work-types list -o json
```

---

### Global Variables

**Create a global variable:**

```bash
wxcli cc-global-vars create --json-body '{
  "name": "maxRetries",
  "variableType": "INTEGER",
  "defaultValue": "3",
  "description": "Max IVR retry attempts"
}'
```

Variable types: `STRING`, `INTEGER`, `BOOLEAN`, `DECIMAL`, `DATE_TIME`, `JSON`.

**List global variables:**

```bash
wxcli cc-global-vars list -o json
```

---

### Flow Management

**List flows:**

```bash
wxcli cc-flow list -o json
```

**Import a flow:**

```bash
wxcli cc-flow create --json-body '{
  "name": "Main IVR Flow",
  "flowType": "flow"
}'
```

**Export a flow:**

```bash
wxcli cc-flow list-export --flow-id FLOW_ID -o json
```

**Publish a flow:**

```bash
wxcli cc-flow create-export --json-body '{
  "flowId": "FLOW_ID"
}'
```

---

### Call Monitoring

**Create a monitoring session:**

```bash
wxcli cc-call-monitoring create-monitor --json-body '{
  "taskId": "TASK_ID",
  "agentId": "AGENT_ID"
}'
```

**Barge into a call:**

```bash
wxcli cc-call-monitoring create-barge-in --json-body '{
  "taskId": "TASK_ID"
}'
```

**List active monitoring sessions:**

```bash
wxcli cc-call-monitoring list -o json
```

**End a monitoring session:**

```bash
wxcli cc-call-monitoring create-end --json-body '{
  "taskId": "TASK_ID"
}'
```

---

### Event Subscriptions

**Create a subscription:**

```bash
wxcli cc-subscriptions create --json-body '{
  "name": "Agent Events",
  "eventTypes": ["AgentStateChange", "TaskRouted"],
  "callbackUrl": "https://example.com/webhook"
}'
```

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
wxcli cc-tasks list -o json
```

**Accept a task:**

```bash
wxcli cc-tasks create-accept-tasks --json-body '{
  "taskId": "TASK_ID"
}'
```

**Transfer a task:**

```bash
wxcli cc-tasks create-transfer-tasks --json-body '{
  "taskId": "TASK_ID",
  "destinationId": "QUEUE_OR_AGENT_ID"
}'
```

**Wrap up a task:**

```bash
wxcli cc-tasks create-wrapup --json-body '{
  "taskId": "TASK_ID",
  "auxCodeId": "AUX_CODE_ID"
}'
```

**Hold/unhold a task:**

```bash
wxcli cc-tasks create-hold --json-body '{"taskId": "TASK_ID"}'
wxcli cc-tasks create-unhold --json-body '{"taskId": "TASK_ID"}'
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

- **401/403**: Token expired or insufficient scopes — run `wxcli configure` to re-authenticate. CC requires `cjp:config_read` / `cjp:config_write` scopes.
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
2. **CC requires separate OAuth scopes.** Standard Webex admin tokens don't include CC scopes. The user needs `cjp:config_read` and `cjp:config_write`. The CLI detects 403 and prints a scope tip.
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
14. **Journey API is complex.** `cc-journey` has 41 commands across workspaces, templates, persons, identities, and subscriptions. Read `docs/reference/contact-center-analytics.md` before using.
15. **Cross-skill handoffs:**
    - Webex Calling features (AA, CQ, HG) → `configure-features` skill
    - Customer Assist (CX Essentials on Calling queues) → `customer-assist` skill
    - Webex Calling reporting (CDR, queue stats) → `reporting` skill
    - Person/workspace call settings → `manage-call-settings` skill
    - Routing (Calling trunks, dial plans, PSTN) → `configure-routing` skill
    - Location teardown → `teardown` skill

---

## Common Workflows

### Workflow A: Set up a basic inbound voice queue

1. Verify site exists → `wxcli cc-site list -o json`
2. Create multimedia profile → `wxcli cc-multimedia-profile create-multimedia-profile --json-body '...'`
3. Create team → `wxcli cc-team create --json-body '...'`
4. Create entry point → `wxcli cc-entry-point create-entry-point --json-body '...'`
5. Create queue → `wxcli cc-queue create-contact-service-queue-v2 --json-body '...'`
6. Map dial number → `wxcli cc-dial-number create --json-body '...'`
7. Create/assign flow → `wxcli cc-flow create --json-body '...'`
8. Verify end-to-end → list all resources and confirm IDs are linked

### Workflow B: Add skill-based routing

1. Create skill definitions → `wxcli cc-skill create --json-body '...'` (one per skill)
2. Create skill profiles → `wxcli cc-skill-profile create-skill-profile --json-body '...'`
3. Update queue routing type → `wxcli cc-queue update --json-body '{"routingType": "SKILLS_BASED", ...}'`
4. Assign skill profiles to teams/agents

### Workflow C: Set up outbound campaign

1. Configure outdial ANI → `wxcli cc-outdial-ani create --json-body '...'`
2. Upload contact list → `wxcli cc-contact-list create --json-body '...'`
3. Create outbound entry point → `wxcli cc-entry-point create-entry-point --json-body '...'`
4. Start campaign → `wxcli cc-campaign create --json-body '...'`

### Workflow D: Configure agent monitoring

1. Create event subscription → `wxcli cc-subscriptions create --json-body '...'`
2. Monitor live calls → `wxcli cc-call-monitoring create-monitor --json-body '...'`
3. Barge in if needed → `wxcli cc-call-monitoring create-barge-in --json-body '...'`

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from conversation history to recover what was planned
2. Check what's already been created: run the relevant `list` commands for each resource type
3. Resume from the first incomplete step
