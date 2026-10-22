# Calling build — interview, plan, run and verify

The `wxops` agent reads this on a Webex Calling build (users, locations, features, settings, routing, devices) and on the other org jobs that have no skill of their own. It holds the procedure: what to ask, how to plan, run, verify and report. The values it repeats (commands, flags, limits) are owned by the reference docs it cites, which win any disagreement. Twin: `docs/reference/provisioning.md`.

## Setup

### 1. CLI Environment

Check that wxcli is installed:

```bash
wxcli --help 2>&1 | head -5
```

- If **wxcli** is found: proceed.
- If **wxcli** is missing: install it: `pipx install wxcli` (recommended) or `pip install wxcli` (the wxcli README § Setup, step 1). In a source checkout only: `pip install -e .` from the repo root.

**How to get a token:**
1. **For development/testing**: get a personal access token from developer.webex.com (12-hour expiry)
2. **For production**: set up an OAuth integration or service app (persistent tokens with refresh)
3. Reference: read `docs/reference/authentication.md` for the full guide on token types, scopes, and OAuth flows

### 4. Reference Docs

Check for `docs/reference/` directory:

- If missing: warn the user that platform reference files are not present. The build will require more manual input and web lookups.
- Check for messaging docs (`messaging-spaces.md`, `messaging-bots.md`) if the user's request involves messaging.

## Understand the request

### Query Intent Detection

Before starting the interview, check if the user's request is a **read-only query about current configuration state** rather than a build/config request or a historical data request.

**Configuration state queries → query-live skill:**
- Present-tense questions about what IS configured: "Who **is** in the Sales HG?", "**Does** John **have** voicemail?", "What trunks **are** configured?"
- Inspection verbs: "show me", "check", "look up", "find", "tell me about"
- State references: "current", "right now", "configured", "enabled", "assigned"
- Call flow questions: "what happens when someone calls...", "trace the call path"
- Inventory/audit: "how many call queues **do** we have?", "which users **don't** have voicemail?"

**Historical/analytics queries → reporting skill (via interview, NOT query-live):**
- Past-tense questions about what HAPPENED: "How many calls **did** we get yesterday?", "Show me **missed calls from** this morning"
- Time-bounded data requests with date ranges: "calls **last week**", "**busiest hour**", "call volume **trend**"
- CDR/analytics keywords: "call history", "call log", "call detail", "call quality", "call stats"
- Agent performance: "which agent **handled** the most calls?"

**Build/config intent → normal interview flow:**
- Action verbs: "create", "set up", "enable", "add", "configure", "change", "move", "delete"
- Future intent: "I want to...", "we need to...", "can you make..."

**If the request is a configuration state query:**

Load the query-live skill and follow its workflow. Do not proceed to the interview questions.

```
Skill: query-live
```

The query-live skill handles classification, domain routing, command execution, and response formatting. It will return a natural-language answer to the user's question.

**If the request is a historical/analytics query or a build/config request**, continue to the interview flow below (a CUCM migration goes to the `cucm-migrate` skill instead). The interview will route analytics questions to the reporting skill and build requests to the appropriate domain skill.

## Interview

### Question 1: Objective

> "What do you want to build or configure?"

Get the objective in the user's own words. Listen for the domain:
- **Provisioning**: creating users, assigning licenses, setting up locations
- **Call features**: auto attendants, call queues, hunt groups, paging, call park, pickup groups, voicemail groups
- **Person settings**: call forwarding, DND, caller ID, voicemail, recording, sim ring, sequential ring, executive/assistant
- **Location settings**: internal dialing, voicemail policies, schedules, announcements, access codes, call recording
- **Routing**: dial plans, trunks, route groups, route lists, translation patterns, PSTN connectivity
- **Devices**: phone provisioning, activation codes, DECT networks, workspace devices
- **Device platform**: RoomOS device configuration management, workspace personalization, xAPI device commands and status queries
- **Call control**: real-time call operations (dial, hold, transfer, park, recording control)
- **Monitoring**: real-time call event webhooks, CDR analysis
- **Bulk operations**: CSV-driven mass provisioning, org-wide setting changes, migration
- **Identity/directory**: SCIM sync, user import, group management, domain verification, directory cleanup
- **Audit/compliance**: audit logs, security events, compliance review, authorization management
- **Licensing**: license audit, usage reporting, license assignment, reclamation
- **Org management**: org settings, contacts, roles, domain management
- **Partner operations**: multi-tenant management, partner admin assignment, customer tagging
- **Hybrid monitoring**: hybrid connector health, analytics, meeting quality
- **Recordings/data**: recording management, recycle bin, data sources, resource groups, report templates
- **Messaging spaces**: creating/managing spaces, teams, memberships, sending messages, ECM folder linking, HDS monitoring
- **Messaging bots**: building bots, sending notifications, adaptive cards, interactive card flows, room tabs, cross-domain calling+messaging integrations
- **Meetings**: scheduling meetings, managing registrants, interpreters, breakout sessions, transcripts, recordings, polls, Q&A
- **Video Mesh**: monitoring Video Mesh clusters, nodes, availability, utilization, reachability, event thresholds
- **Contact Center**: CC agents, queues, entry points, teams, skills, flows, campaigns, dial plans, desktop profiles, monitoring, AI features

**Multi-skill workflows:** If the user's goal spans multiple domains (e.g., "offboard a user", "set up call recording for a team", "move a number from a user to a CC entry point"), check the **Multi-Skill Workflows** section in `CLAUDE.md` for the skill sequence. Load and execute skills in the order listed there rather than picking just one.

### Question 2: Scope

> "At what scope? Org-wide, specific location(s), or specific user(s)?"

This determines whether you are doing bulk operations or targeted work. Get specifics:
- If location-scoped: which locations? Do they exist yet?
- If user-scoped: which users? By email, name, or phone number?
- If org-wide: how many users/locations are we talking about? (determines async vs sync approach)

For messaging requests, scope is different:
- If space-scoped: which space? Do you have the room ID?
- If team-scoped: which team? Creating new or modifying existing?
- If bot-scoped: is this for a bot or a user integration? Do you have a webhook callback URL?
- If org-wide: org-wide space audit needs admin token + compliance API

For meetings requests:
- Single meeting or recurring series?
- Webex site URL (if multi-site org)?
- Personal room or scheduled meeting?

For contact center requests:
- Which CC region? (`wxcli set-cc-region` — us1, eu1, eu2, anz1, ca1, jp1, sg1)
- Inbound, outbound campaign, or both?
- Skill-based or team-based routing?

### Question 3: Prerequisites

> "Let me check what's already in place."

Do NOT just ask -- actually check. Run CLI commands to verify:

```bash
# Check calling-enabled locations
wxcli location-settings list-1

# Check licenses
wxcli licenses list

# Check existing users at a location
wxcli users list --location-id LOCATION_ID --output table
```

Report what you find and identify gaps:
- Missing locations that need to be created first
- Insufficient licenses for the planned provisioning
- Users that don't exist yet
- Features that require specific license types (e.g., CX Essentials for supervisor features)

### Question 4: Constraints

> "Any specific requirements I should know about?"

Probe for:
- **Naming conventions**: "All hunt groups must be prefixed with location code"
- **Number ranges**: "Extensions must be 4-digit starting with 3xxx for Sales"
- **Schedule requirements**: business hours, holidays, after-hours routing
- **Compliance**: call recording requirements, E911 requirements
- **Integration**: existing PBX migration, PSTN provider constraints, SBC configuration

### Question 5: Special Requirements

For messaging requests, also probe:
- **Token type**: "Bot token, user token, or admin token?" (explain differences if user is unsure)
- **Card interactions**: "Will users interact with cards (approve/reject/fill forms)?" → triggers card recipe + webhook setup in messaging-bots skill
- **Cross-domain**: "Does this involve both calling and messaging?" → load both domain skills

## Deployment plan

After the interview is complete:

### 1. Load Reference Docs

Based on the user's objective, load the relevant reference docs. Use the mapping in § Reference docs by domain at the bottom of this file.

### 2. Build the Deployment Plan

Read `docs/templates/deployment-plan.md` to get the template. Fill in every section:

- **Objective**: what we are building, in one paragraph
- **Scope**: org-wide, location(s), user(s) -- with specific names/IDs
- **Prerequisites**: what must exist before we start (locations, licenses, users) -- mark each as confirmed or needs-creation
- **Execution Steps**: numbered list of commands in dependency order. For each step:
  - Step number and description
  - Command (e.g., `wxcli users create --json-body '{"emails":["..."],"displayName":"..."}'`)
  - Input parameters (show actual values, not placeholders)
  - Expected result
  - Depends on: which prior steps must complete first
- **Rollback Plan**: if step N fails, what to undo from steps 1 through N-1
- **Verification Steps**: how to confirm each resource was created correctly
- **Estimated Execution**: sync vs async, approximate time for bulk operations

## Running the plan

### Discovery-First Rule

The rule and its false-negative guard are root `CLAUDE.md` § Discovery-First Rule.

Example of a broad query in this domain: `wxcli device-configurations show --device-id X --key "Lines.*"`

### Progress Reporting

Show real-time progress:

```
Step 1/7: Creating location "Raleigh Office"...
  $ wxcli locations create --json-body '{"name":"Raleigh Office","timeZone":"America/New_York",...,"address":{...}}'
  Created: Y2lz...abc (Raleigh Office)
Step 2/7: Enabling Webex Calling for location...
  $ wxcli location-settings create --json-body '{"id":"Y2lz...abc","name":"Raleigh Office","timeZone":"America/New_York",...,"address":{...}}'
  Done
Step 3/7: Provisioning user alice@example.com...
  $ wxcli users create --json-body '{"emails":["alice@example.com"],"firstName":"Alice","lastName":"Smith"}' ...
  Created: Y2lz...def
Step 4/7: Provisioning user bob@example.com... FAILED
  Error: 409 Conflict — user already has a Calling license
  → Suggested fix: check existing license assignment
  → Pausing execution. Steps 5-7 not started.
```

### Mid-Execution Changes

If the user changes their mind during execution ("actually skip that", "add another queue", "make it a hunt group instead"):

1. **Stop execution immediately** — do not finish the current step
2. **Summarize progress** — list what was completed and what remains
3. **Update the deployment plan** — revise the remaining steps to reflect the change
4. **Re-present for approval** — show the updated plan and wait for confirmation
5. **Offer rollback if needed** — if a completed step conflicts with the new direction (e.g., created a CQ but user now wants a HG), offer to delete the conflicting resource before proceeding

### Common wxcli Commands for Execution

```bash
# Provisioning
# Verified live 2026-10-13: --json-body REPLACES the other flags, so flags + an address-only body fails
# 400 "location name cannot be null or empty". Put name, timeZone, languages AND address all in the body.
wxcli locations create --json-body '{"name":"...","timeZone":"America/Los_Angeles","preferredLanguage":"en_US","announcementLanguage":"en_us","address":{"address1":"123 Main St","city":"...","state":"...","postalCode":"...","country":"US"}}'
# Enable calling (requires location details — fetch first with wxcli locations show LOCATION_ID). Flags-only fails
# 400 "Validation failure" (verified live 2026-10-13); send id, name, timeZone, languages and address in --json-body.
wxcli location-settings create --json-body '{"id":"LOCATION_ID","name":"...","timeZone":"...","preferredLanguage":"en_US","announcementLanguage":"en_us","address":{"address1":"...","city":"...","state":"...","postalCode":"...","country":"US"}}'
wxcli users create --json-body '{"emails":["..."],"displayName":"...","firstName":"...","lastName":"..."}'
# A calling user in ONE call (licenses + locationId + extension in the body) also needs --calling-data true, else 400 "Calling flag not set".

# Features
wxcli location-schedules create LOCATION_ID --name "Business Hours" --type businessHours
# Verified live 2026-10-13: the CLI injects NO defaults for auto-attendant, call-queue or call-park, so their flags-only
# forms fail 400 25008 (missing businessHoursMenu / callPolicies / recall). Use --json-body (it replaces the other flags);
# see .claude/skills/configure-features/SKILL.md for the full bodies. hunt-group flags-only works (the CLI injects a
# default callPolicies for it); the call-pickup form below was not specifically re-tested flags-only.
wxcli auto-attendant create LOCATION_ID --json-body '{...both menus...}'   # businessSchedule = exact schedule NAME
wxcli call-queue create LOCATION_ID --json-body '{"name":"Support","extension":"2000","callPolicies":{"policy":"CIRCULAR"}}'
wxcli hunt-group create LOCATION_ID --name "Sales" --extension 3000 --enabled
wxcli call-park create LOCATION_ID --json-body '{"name":"Lobby Park","recall":{"option":"ALERT_PARKING_USER_ONLY"}}'
wxcli call-pickup create LOCATION_ID --name "Front Desk"

# Settings
wxcli user-settings show-call-forwarding PERSON_ID --output json
wxcli user-settings update-do-not-disturb PERSON_ID --enabled

# Routing
wxcli call-routing list-trunks --all
wxcli pstn list LOCATION_ID
wxcli numbers list --location-id LOCATION_ID --all
```

## Bulk operations

wxcli has a proven async bulk execution engine with:
- **Concurrent execution** via `asyncio` + `aiohttp` with configurable concurrency (default 20)
- **Semaphore-based rate limiting** — prevents API throttling
- **Automatic 429 retry** with `Retry-After` backoff (up to 5 retries)
- **409 auto-recovery** — searches for existing resource by name/email and reuses its ID
- **Per-operation status tracking** — every op is logged as pending/in_progress/completed/failed
- **Dependency-aware batching** — NetworkX DAG ensures operations run in correct order

This engine is currently wired into the CUCM migration pipeline (`wxcli cucm execute --concurrency 20`), but the pattern is production-proven with 1486 tests.

**For small batches (< 20 items)**, use a shell loop:

```bash
for email in alice@example.com bob@example.com charlie@example.com; do
  wxcli users create --json-body "{\"emails\":[\"$email\"],\"displayName\":\"...\",\"firstName\":\"...\",\"lastName\":\"...\"}"
done
```

**For medium batches (20-50 items)**, use a shell loop with rate limiting:

```bash
for email in ...; do
  wxcli users create --json-body "{\"emails\":[\"$email\"]}" ...
  sleep 1
done
```

**For large batches (50+ items)**, use the bulk engine. It handles concurrency, 429 retry with backoff, 409 auto-recovery, and cascade failure tracking.

### Use Async for Large Bulk Operations
For operations touching more than 50 items, use the async `aiohttp` pattern from the bulk engine (see Bulk Operations section above). Shell loops over wxcli work for smaller batches (< 50). The proven pattern handles concurrency, rate limiting, retry, and error recovery — use it as the reference implementation.

## Verify and report

### 1. Read Back

For every resource created or modified, read it back and compare to the plan:

```bash
# Verify a user
wxcli users show PERSON_ID

# Verify a location
wxcli locations show LOCATION_ID --output json

# Verify a feature
wxcli auto-attendant show LOCATION_ID AA_ID --output json
wxcli call-queue show LOCATION_ID QUEUE_ID --output json
wxcli hunt-group show LOCATION_ID HG_ID --output json
```

### 3. Execution Report

Read `docs/templates/execution-report.md` to get the template (if it exists). If it does not exist yet, produce a report with:

- **Summary**: what was built, how many resources created/modified
- **Step-by-Step Results**: each step with status (done/failed/skipped), resource IDs, timestamps
- **Discrepancies**: anything that doesn't match the plan
- **Failed Steps**: full error details and suggested remediation
- **Verification Results**: read-back confirmation for each resource
- **Next Steps**: any follow-up work needed

Save the report alongside the deployment plan in `docs/plans/`.

### Session State Protocol

At each phase boundary, write `session-state.md` to the active project directory:
- CUCM migrations: `~/.wxcli/migrations/<project>/session-state.md`
- Standard builds: `docs/plans/session-state.md`

```markdown
## Session State
- **Workflow:** cucm-migration | standard-build
- **Project:** <name>
- **Phase completed:** <phase name>
- **Next phase:** <phase name>
- **Key facts:** <1-2 line summary of inventory/scope>
- **Blocking issues:** <anything that must be resolved before next phase>
```

Overwrite this file at each boundary — it is a cursor, not a log. The migration DB and deployment plans remain the source of truth.

## Skills by domain

Load the skill before running any command in its domain; root `CLAUDE.md` § Routing Table names it, and each skill's checkpoint holds the facts you cannot guess. These facts from the old dispatch table are not yet written in the skill itself:

| Skill | What it contains that you CANNOT guess |
|-------|---------------------------------------|
| `.claude/skills/configure-routing/SKILL.md` | trunk type inference |
| `.claude/skills/manage-call-settings/SKILL.md` | name mismatches between the two path families (`intercept` vs `callIntercept`) |
| `.claude/skills/cucm-migrate/SKILL.md` | ID capture between steps, placeholder resolution |

### Multiple Skills Per Plan

Most builds touch multiple domains. Load each skill as you enter its domain — do NOT batch-read all skills upfront:
- Steps deleting or cleaning up resources → load teardown
- Steps creating locations/users → load provision-calling
- Steps creating features (AA, CQ, HG) → load configure-features
- Steps configuring person settings → load manage-call-settings
- Steps setting up routing → load configure-routing
- Steps provisioning devices → load manage-devices
- Steps managing RoomOS configs, personalization, or xAPI → load device-platform
- Steps managing spaces, teams, memberships, or messages → load messaging-spaces
- Steps building bots, sending cards, or setting up messaging webhooks → load messaging-bots
- Steps scheduling or managing meetings, transcripts, recordings → load manage-meetings
- Steps monitoring Video Mesh clusters, nodes, or thresholds → load video-mesh
- Steps provisioning CC agents, queues, entry points, teams, flows → load contact-center
- On any error → load wxc-calling-debug

### Standalone Skill Use

Users can also invoke skills directly as slash commands (`/configure-features`, `/manage-call-settings`, etc.) for focused work outside the builder workflow. Each skill is self-contained and runs independently.

## Admin operations without skills

For admin operations that do not have a dedicated skill, handle them inline using reference docs:
- Org settings (show/update): reference `admin-org-management.md`
- Hybrid monitoring: reference `admin-hybrid.md`
- Partner operations: reference `admin-partner.md`
- Data/resource operations: reference `admin-apps-data.md`

**Inline handling criteria:** Handle inline when: (a) the operation is a single read-only command, (b) the group has fewer than 5 commands, or (c) there are no destructive operations involved. For groups with destructive operations (delete, purge, revoke), always load the relevant reference doc first and confirm before executing.

## Calling rules

### Source of Truth Precedence

`--help` > skills > reference docs > training data: root `CLAUDE.md` § Source of Truth Precedence.

Example: if a reference doc says `wxcli locations-api list` but the skill says `wxcli locations list`, run `wxcli locations list --help` to see which exists. If `--help` confirms `locations list` works, use that regardless of what the reference doc says.

When you find a conflict, fix the stale source if possible (update the reference doc or flag it to the user). Do not silently use the wrong command.

### Handle Rate Limiting
Webex APIs enforce rate limits. wxcli auto-retries 429s (up to 4 attempts, honoring `Retry-After` up to 30 s) and, for GET/PUT/DELETE only, 5xx; it raises once attempts are exhausted. For shell loops, add `sleep 1` between commands to avoid hitting limits. For bulk async operations, use the semaphore + 429 retry pattern (see Bulk Operations section).

### Check Prerequisites Before Creation
ALWAYS verify that dependencies exist before attempting to create a resource. Examples:
- Location must exist before provisioning a user at that location
- User must exist before configuring their call settings
- License must be available before assigning it
- Schedule must exist before referencing it in an auto attendant

If a prerequisite is missing, stop and inform the user rather than letting the API return a cryptic error.

### Location-Scoped Operations
Many Webex Calling APIs require a `location_id` parameter. ALWAYS verify you have the correct location ID before making location-scoped calls. A wrong location ID silently applies settings to the wrong location.

### Command Verification (Anti-Hallucination)

Run `wxcli <group> <command> --help` before a command's first use in a session.

**Common hallucination patterns to avoid:**
- Inventing flags: `--location` (wrong) vs `--location-id` (right)
- Singular vs plural: `delete-route-group` (wrong) vs `delete-route-groups` (right)
- Assuming `-o json` works on all commands (action/POST commands don't support it)
- Guessing `--json-body` structure instead of reading the example in `--help`
- Inventing commands like `wxcli users assign-license` (doesn't exist — licenses are assigned via `wxcli licenses update`)

**When a skill provides exact command examples, trust the skill.** Skills are verified against live APIs. When operating without a skill (ad-hoc requests), always check `--help` first.

## Reference docs by domain

Based on the user's request, load the relevant reference docs. Do not load everything -- load only what the current task requires.

### Provisioning (users, locations, licenses)
```
docs/reference/provisioning.md
```

### Call Features (AA, CQ, HG, paging, park, pickup, voicemail groups)
```
docs/reference/call-features-major.md        — AA, CQ, HG
docs/reference/call-features-additional.md   — paging, park, pickup, voicemail groups, CX Essentials
```

### Person Call Settings
```
docs/reference/person-call-settings-handling.md     — forwarding, DND, call waiting, sim/sequential ring
docs/reference/person-call-settings-media.md        — voicemail, caller ID, privacy, barge, recording, intercept
docs/reference/person-call-settings-permissions.md  — incoming/outgoing permissions, feature access, exec/assistant
docs/reference/person-call-settings-behavior.md     — calling behavior, app services, hoteling, receptionist, numbers, ECBN
```

### Location Call Settings
```
docs/reference/location-calling-core.md       — enablement, internal dialing, voicemail policies, voice portal
docs/reference/location-calling-media.md      — announcements, playlists, schedules, access codes
docs/reference/location-recording-advanced.md   — call recording, caller reputation, conference, supervisor, operating modes
```

### Call Routing (dial plans, trunks, route groups, PSTN)
```
docs/reference/call-routing.md
```

### Devices (phones, DECT, workspaces)
```
docs/reference/devices-core.md          — device CRUD, activation codes, configurations
docs/reference/devices-dect.md          — DECT networks, base stations, handsets
docs/reference/devices-workspaces.md    — workspaces, workspace settings, workspace locations
```

### Device Platform (RoomOS configurations, personalization, xAPI)
```
docs/reference/devices-platform.md     — device configs, workspace personalization, xAPI
```

### Call Control (real-time call operations)
```
docs/reference/call-control.md
docs/reference/webhooks-events.md
```

### Monitoring and Reporting
```
docs/reference/reporting-analytics.md
docs/reference/webhooks-events.md
```

### Emergency Services
```
docs/reference/emergency-services.md
```

### Virtual Lines
```
docs/reference/virtual-lines.md
```

### Organization Management
```
docs/reference/admin-org-management.md
```

### Identity & SCIM
```
docs/reference/admin-identity-scim.md
```

### Licensing
```
docs/reference/admin-licensing.md
```

### Audit & Security
```
docs/reference/admin-audit-security.md
```

### Hybrid Infrastructure & Analytics
```
docs/reference/admin-hybrid.md
```

### Partner Operations
```
docs/reference/admin-partner.md
```

### Apps, Data & Resources
```
docs/reference/admin-apps-data.md
```

### Messaging Spaces (spaces, teams, memberships, messages, ECM, HDS)
```
docs/reference/messaging-spaces.md
```

### Messaging Bots (bots, notifications, adaptive cards, cross-domain)
```
docs/reference/messaging-bots.md
docs/reference/webhooks-events.md
```

### Meetings (schedule, manage, transcripts, recordings, polls)
```
docs/reference/meetings-core.md              — meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys
docs/reference/meetings-content.md           — transcripts, captions, chats, summaries, meeting messages
docs/reference/meetings-settings.md          — preferences, session types, tracking codes, site settings, polls, Q&A, reports
docs/reference/meetings-infrastructure.md    — Video Mesh clusters, nodes, health, utilization, participants, invitees
```

### Video Mesh (monitoring, clusters, nodes, thresholds)
```
docs/reference/meetings-infrastructure.md    — Video Mesh clusters, nodes, health, utilization
```

### Contact Center (agents, queues, flows, campaigns, monitoring)
```
docs/reference/contact-center-core.md        — agents, queues, entry points, teams, skills, desktop, configuration
docs/reference/contact-center-routing.md     — dial plans, campaigns, flows, audio, contacts, outdial
docs/reference/contact-center-analytics.md   — AI, monitoring, subscriptions, tasks, search
docs/reference/contact-center-journey.md     — JDS: workspaces, persons, identity, profile views, events
```

### Cross-Cutting (on-demand only — load when debugging or using raw HTTP)
```
docs/reference/authentication.md        — token issues, scope questions (loaded by wxc-calling-debug skill)
docs/reference/authentication.md        — scopes, token types, raw HTTP pattern, auth errors
```
