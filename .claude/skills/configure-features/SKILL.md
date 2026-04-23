---
name: configure-features
description: |
  Create, modify, or delete Webex Calling call features using wxcli CLI commands: Auto Attendants, Call Queues,
  Hunt Groups, Paging Groups, Call Park, Call Pickup, Voicemail Groups, and Customer Assist.
  Guides the user from prerequisites through creation, modification, deletion, and verification.
  Use for: create, update, delete, remove, list, or troubleshoot any call feature.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [feature-type]
---

<!-- Updated by playbook session 2026-03-18 -->

# Configure Call Features Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What is the argument order for location-scoped feature deletes? (Answer: `--force LOCATION_ID FEATURE_ID` — location comes FIRST, not second.)
2. How do you list CX Essentials call queues? (Answer: `wxcli call-queue list --has-cx-essentials true` — they are hidden from the default list.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/call-features-major.md` for AA, CQ, HG data models and API signatures
2. Read `docs/reference/call-features-additional.md` for Paging, Call Park, Call Pickup, VM Groups, CX Essentials

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`). Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

## Step 3: Identify which feature(s) to configure

Ask the user which feature they want to create. Present this decision matrix if they are unsure:

| Need | Feature |
|------|---------|
| IVR menu with key-press routing ("Press 1 for Sales...") | **Auto Attendant** |
| Hold callers in queue until an agent is free | **Call Queue** |
| Ring a group of agents directly (no queue hold) | **Hunt Group** |
| One-way broadcast announcements to phones | **Paging Group** |
| Park a call on an extension for someone else to pick up | **Call Park** |
| Let team members answer each other's ringing phones | **Call Pickup** |
| Shared voicemail box for a team or feature | **Voicemail Group** |
| Screen pop, recording, wrap-up, supervisors on a CQ | **Customer Assist** (use `customer-assist` skill) |

## Step 4: Check prerequisites

Before creating any feature, verify these exist:

### 4a. Location exists and is calling-enabled

All features are location-scoped. Confirm the target location:

```bash
wxcli locations list --output json
```

Scan the output for the target location name and capture the `location_id`. Then confirm calling is enabled on it — calling features cannot be created at a location where calling is disabled:

```bash
wxcli location-settings list-1
```

The target location must appear in this output. If it does not, calling is not enabled there — run the provision-calling skill to enable it before proceeding.

If no location matches the name at all, the user must create one first (see provision-calling skill).

### 4b. Users/agents exist (for features that need members)

For CQ, HG, Paging, Call Park, Call Pickup -- confirm the people who will be agents/members:

```bash
wxcli users list --calling-data true --output json
```

To filter by location:

```bash
wxcli users list --calling-data true --location-id LOCATION_ID --output json
```

### 4c. Phone numbers available (for features that need a number)

For AA, CQ, HG, Paging, VM Groups -- check available numbers at the location:

```bash
wxcli numbers list --location-id LOCATION_ID --output json
```

### 4d. Feature-specific prerequisites — verify before creating

**Run the verification command for each prerequisite before creating the feature.** Missing prerequisites cause 400 errors that waste an API call and require diagnosis.

#### Auto Attendant

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Business hours schedule | `wxcli location-schedules list LOCATION_ID -o json` — look for a schedule with `type: businessHours` | Create one first: `wxcli location-schedules create LOCATION_ID --name "Business Hours" --type businessHours --json-body '{...}'` |
| Holiday schedule (optional) | Same command — look for `type: holidays` | Create if needed for holiday service routing |
| Custom greetings | Cannot be verified via API | Upload via Control Hub (API upload not supported) |

#### Call Queue

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Agents have Professional license | `wxcli users list -o json` — for each agent, check license type. OR `wxcli licenses list -o json` and cross-reference | Assign Professional license via `manage-licensing` skill before adding as agent |
| CX Essentials license (for CX queues) | Same license check — look for CX Essentials license | Assign via `manage-licensing` skill. Without it, error 28018 on any CX operation |
| `callPolicies` in create body (CX queues) | N/A — CX queues require `callPolicies` in the `--json-body` at creation time | Include `"callPolicies": {...}` in the create body. See `customer-assist` skill for format |

#### Hunt Group

No additional prerequisites beyond location + agents. Can be created with zero agents.

#### Paging Group

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Originators/targets exist | `wxcli users list --calling-data true -o json` | Originators and targets are added via `wxcli paging-group update` AFTER creation (not in the create call) |

#### Call Park

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Hunt group exists (for recall) | `wxcli hunt-group list --location-id LOCATION_ID -o json` | Create the hunt group first, then configure call park recall to reference it |

#### Call Pickup

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Users not already in another pickup group | `wxcli call-pickup list LOCATION_ID -o json` — check member lists for the target user | Remove user from existing group before adding to new one |

#### Voicemail Group

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Extension available | `wxcli numbers list --location-id LOCATION_ID -o json` | Choose an unused extension |
| Passcode format | N/A — validate locally | 6+ digits, no repeating sequences (e.g., `111111` is rejected). Use a pattern like `740384` |

#### Customer Assist (CX Essentials)

| Prerequisite | Verification | If missing |
|-------------|-------------|-----------|
| Call queue exists | `wxcli call-queue list --location-id LOCATION_ID -o json` | Create the queue first in this skill, then switch to `customer-assist` skill |
| Queue is CX-enabled | `wxcli call-queue list --has-cx-essentials true -o json` | CX queues are hidden from default list. If queue doesn't appear, it wasn't created as a CX queue |

## Step 5: Gather configuration and present deployment plan -- [SHOW BEFORE EXECUTING]

Based on the selected feature, collect the required parameters from the user. **Always present the plan before executing.**

---

### Auto Attendant

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name for the AA |
| Phone number or extension | Yes (one of) | Use `wxcli numbers list` to find candidates |
| Business hours schedule | Yes | Must already exist at org/location level |
| Holiday schedule | No | Optional |
| Business hours menu | Yes | Key-press actions (see key config below) |
| After hours menu | Yes | Key-press actions |
| Extension dialing | No | `ENTERPRISE` (default) or `GROUP` |
| Name dialing | No | `ENTERPRISE` (default) or `GROUP` |

**Key-press actions** -- for each menu, define up to 12 keys (`0`-`9`, `*`, `#`):

| Action | Description |
|--------|-------------|
| `TRANSFER_WITHOUT_PROMPT` | Transfer immediately to a number/extension |
| `TRANSFER_WITH_PROMPT` | Play prompt then transfer |
| `TRANSFER_TO_OPERATOR` | Transfer to operator |
| `NAME_DIALING` | Dial-by-name directory |
| `EXTENSION_DIALING` | Dial-by-extension |
| `REPEAT_MENU` | Replay the menu |
| `EXIT` | Disconnect |
| `TRANSFER_TO_MAILBOX` | Transfer to voicemail |
| `RETURN_TO_PREVIOUS_MENU` | Go back one level |
| `PLAY_ANNOUNCEMENT` | Play an announcement |

**CLI command:**

> **NOTE:** The CLI automatically provides default menus (key 0 = EXIT, extension dialing enabled, DEFAULT greeting) so the create command succeeds without specifying menu details. To customize menus with specific key-press actions, use `wxcli auto-attendant update` after creation.

```bash
wxcli auto-attendant create LOCATION_ID \
  --name "Main Menu" \
  --extension 1000 \
  --business-schedule "Business Hours"
```

Optional flags: `--phone-number`, `--holiday-schedule`, `--disabled`.

---

### Call Queue

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name |
| Phone number or extension | Yes (one of) | |
| Routing policy | Yes | `CIRCULAR`, `REGULAR`, `SIMULTANEOUS` (max 50 agents), `UNIFORM`, `WEIGHTED` (max 100 agents) |
| Routing type | No | `PRIORITY_BASED` (default) or `SKILL_BASED` |
| Agents | Yes | List of person IDs (people, workspaces, or virtual lines) |
| Queue size | Yes | Max calls in queue before overflow triggers |
| Overflow action | No | `PERFORM_BUSY_TREATMENT`, `TRANSFER_TO_PHONE_NUMBER`, `PLAY_RINGING_UNTIL_CALLER_HANGS_UP` |
| Overflow transfer number | If overflow=transfer | Destination number |
| Call bounce settings | No | `max_rings` (default 5), `agent_unavailable_enabled` |
| Agent join/unjoin enabled | No | Let agents toggle themselves in/out |

**Announcement chain** (all optional, configure as needed):

1. **Welcome message** -- first thing callers hear; can be mandatory even when agent is available
2. **Wait message** -- estimated wait time or queue position
3. **Comfort message** -- periodic message (promotions, info); interval 10-600 seconds
4. **Comfort message bypass** -- short comfort for quickly-answered calls
5. **Music on hold** -- normal + alternate source
6. **Whisper message** -- plays to agent before connection (identifies which queue)

**CLI command:**

> **NOTE:** The API may accept call queue creates without `callPolicies` for non-CX queues (using server-side defaults), but the spec marks it required. For CX Essentials queues, `callPolicies` is strictly required — pass via `--json-body`. Agents are added after creation.

```bash
wxcli call-queue create LOCATION_ID \
  --name "Support Queue" \
  --extension 2000
```

Optional flags: `--phone-number`.

To add agents after creation, use the update command with `--json-body`:

```bash
wxcli call-queue update LOCATION_ID QUEUE_ID --json-body '{"agents": [{"id": "AGENT_PERSON_ID"}]}'
```

To find available agents for a location:

```bash
wxcli call-queue list-available-agents-queues LOCATION_ID --output json
```

> **WARNING (CQ Update):** The CLI `update` command uses partial objects to avoid the `callingLineIdPolicy=CUSTOM` 400 error. Only changed fields are sent:
> ```bash
> wxcli call-queue update LOCATION_ID QUEUE_ID --name "New Name"
> ```

---

### Hunt Group

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name |
| Phone number or extension | Yes (one of) | |
| Ring pattern (policy) | No | `CIRCULAR` (default), `REGULAR`, `SIMULTANEOUS` (max 50), `UNIFORM`, `WEIGHTED` (max 100) |
| Members | No | Can create with zero agents and add later |
| No-answer behavior | No | Advance to next agent, forward after N rings, forward destination |
| Busy redirect | No | Where to send calls when all agents busy |
| Business continuity redirect | No | Fallback when phone system is disconnected |

**Key difference from Call Queue:** Hunt groups ring agents directly -- no queue hold, no announcements chain, no agent join/unjoin.

**CLI command (simple — uses CLI defaults for callPolicies):**

```bash
wxcli hunt-group create LOCATION_ID \
  --name "Sales Team" \
  --extension 3000 \
  --enabled
```

> **NOTE:** The CLI auto-injects a default `callPolicies` (CIRCULAR policy, advance to next agent after 3 rings, no forwarding) when not provided. This covers simple creates. For custom policies, use `--json-body`.

**CLI command (full control — custom policy and no-answer behavior):**

```bash
wxcli hunt-group create LOCATION_ID --json-body '{
  "name": "Sales Team",
  "extension": "3000",
  "enabled": true,
  "callPolicies": {
    "policy": "REGULAR",
    "noAnswer": {
      "nextAgentEnabled": true,
      "nextAgentRings": 3,
      "forwardEnabled": false,
      "numberOfRings": 15,
      "destinationVoicemailEnabled": false
    }
  },
  "agents": [{"id": "AGENT_PERSON_ID"}]
}'
```

**callPolicies structure (required by API):**

| Field | Required | Notes |
|-------|:--------:|-------|
| `policy` | Yes | `CIRCULAR`, `REGULAR`, `SIMULTANEOUS` (max 50 agents), `UNIFORM`, `WEIGHTED` (max 100 agents) |
| `noAnswer.nextAgentEnabled` | Yes | Advance to next agent after rings |
| `noAnswer.nextAgentRings` | Yes | Rings before advancing (when nextAgentEnabled) |
| `noAnswer.forwardEnabled` | Yes | Forward unanswered calls to destination |
| `noAnswer.numberOfRings` | Yes | Rings before forwarding (when forwardEnabled) |
| `noAnswer.destinationVoicemailEnabled` | Yes | Send to destination's voicemail |
| `noAnswer.destination` | No | Forward-to number (required when forwardEnabled=true) |
| `waitingEnabled` | No | false = "advance when busy" |
| `groupBusyEnabled` | No | Set hunt group status to busy |
| `busyRedirect.enabled` | No | Divert calls when all agents busy |
| `busyRedirect.destination` | No | Busy redirect number |
| `businessContinuityRedirect.enabled` | No | Fallback when phones disconnected |
| `businessContinuityRedirect.destination` | No | Business continuity number |

**CUCM migration mapping:** Map `CanonicalHuntGroup.policy` → `callPolicies.policy`, and `CanonicalHuntGroup.no_answer_rings` → `callPolicies.noAnswer.nextAgentRings`.

Optional flags: `--phone-number`.

To add agents after creation, use the update command with `--json-body`:

```bash
wxcli hunt-group update LOCATION_ID HG_ID --json-body '{"agents": [{"id": "AGENT_PERSON_ID"}]}'
```

---

### Paging Group

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 30 chars |
| Phone number or extension | Yes (one of) | |
| Originators | No | People/workspaces who can initiate pages |
| Targets | No | People/workspaces/virtual lines who receive pages (up to 75) |
| Originator caller ID enabled | Yes if originators set | Shows originator's caller ID on target phones |

**CLI command:**

```bash
wxcli paging-group create LOCATION_ID \
  --name "Warehouse Page" \
  --extension 8100
```

Optional flags: `--disabled`.

To list existing paging groups:

```bash
wxcli paging-group list --location-id LOCATION_ID --output json
```

> **NOTE:** Originator and target assignment requires `wxcli paging-group update` after creation. The CLI create command creates the group with name, extension, and enabled status.

---

### Call Park

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 80 chars |
| Agents | No | People/workspaces eligible to receive parked calls |
| Call Park Extensions | No | Dedicated park extensions (create these first) |
| Park on agents enabled | No | Whether calls can be parked directly on agents |
| Recall behavior | No | `ALERT_PARKING_USER_ONLY` (default), `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP`, `ALERT_HUNT_GROUP_ONLY` |
| Recall hunt group | If recall uses HG | Must be an existing hunt group at the location |

**CLI command:**

> **NOTE:** The CLI automatically provides the required `recall` field (defaults to `parking_user_only`), so the create succeeds with just a name.

```bash
wxcli call-park create LOCATION_ID --name "Lobby Park"
```

Note: `LOCATION_ID` is a positional argument for call-park commands.

To list call park groups:

```bash
wxcli call-park list LOCATION_ID --output json
```

**Gotcha:** Call Park ID changes when name is modified. Always re-fetch after a name change.

---

### Call Pickup

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 80 chars |
| Members | No | People, workspaces, virtual lines |
| Notification type | No | `NONE`, `AUDIO_ONLY`, `VISUAL_ONLY`, `AUDIO_AND_VISUAL` |
| Notification delay (seconds) | No | Time before notification fires |

**Constraint:** A user can only belong to one call pickup group at a time.

**CLI command:**

```bash
wxcli call-pickup create LOCATION_ID --name "Front Desk Pickup"
```

Note: `LOCATION_ID` is a positional argument for call-pickup commands.

To list call pickup groups:

```bash
wxcli call-pickup list LOCATION_ID --output json
```

**Gotcha:** Call Pickup ID changes when name is modified. Always re-fetch after a name change.

---

### Voicemail Group

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Group name |
| Extension | Yes | Required on create |
| Passcode | Yes | Access passcode (6+ digits, no repeating) |
| Phone number | No | Optional external number |
| Language code | No | Default `en_us` |

**CLI command:**

> **NOTE:** The CLI handles the known `VoicemailGroupDetail.for_create()` SDK bug (missing `by_alias=True`) internally. It uses `model_dump(by_alias=True)` and raw HTTP under the hood, so the command just works.

```bash
wxcli location-voicemail create LOCATION_ID \
  --name "Support VM" \
  --extension 8200 \
  --passcode 740384 \
  --language-code en_us
```

Optional flags: `--phone-number`, `--first-name`, `--last-name`.

---

### CX Essentials (Customer Assist)

Customer Assist (formerly CX Essentials) has its own dedicated skill with full coverage of screen pop, wrap-up reasons, queue call recording, supervisors, and available agents.

> **Use the `customer-assist` skill** for all Customer Assist configuration.

The call queue itself is still created here (see Call Queue section above). Once the queue exists, switch to the `customer-assist` skill to configure Customer Assist features on it.

---

### Deployment Plan Template

Before executing any commands, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Feature: [type]
Location: [name] ([location_id])
Name: [feature_name]
Phone/Extension: [number or extension]

Configuration:
  [Feature-specific settings listed here]

Members/Agents:
  - [Person 1] ([person_id])
  - [Person 2] ([person_id])

Prerequisites verified:
  ✓ Location exists
  ✓ [N] agents found
  ✓ Phone number/extension available
  ✓ [Feature-specific prereqs]

Commands to execute:
  wxcli [feature] create ...
  wxcli [feature] update ... --json-body '{"agents": [...]}' (if applicable)

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

## Step 6: Execute via wxcli

Run the creation command. If the feature requires multiple steps (e.g., agents added after CQ/HG creation), execute them in order.

Handle errors explicitly:

**Generic errors:**
- **401/403**: Token expired or insufficient scopes — run `wxcli configure` to re-authenticate. Required scope: `spark-admin:telephony_config_write`.
- **409**: Name or extension conflict — ask user for alternate name/extension.
- **400**: Validation error — read the error message and fix the parameter.

**Feature-specific errors:**
- **400 on AA create (schedule reference):** The business hours schedule doesn't exist or the schedule ID is wrong. Verify with `wxcli location-schedules list LOCATION_ID -o json`.
- **400 on CQ create (missing callPolicies):** CX Essentials queues require `callPolicies` in the create body. Add via `--json-body`.
- **400 on CQ update (callingLineIdPolicy=CUSTOM):** Sending the full queue object on update triggers this. Use individual flags (`--name`, `--extension`) instead of `--json-body` with the full object. The CLI handles partial updates automatically.
- **28018 on CX operations:** "CX Essentials is not enabled for this Call center" — the queue isn't a CX queue. Must pass `--has-cx-essentials true` on list commands and create with `callPolicies`.
- **400 on VM Group create (passcode):** Passcode doesn't meet requirements: 6+ digits, no repeating sequences, no common patterns.
- **ID changed after rename (Call Park, Call Pickup):** These features generate new IDs when renamed. Always re-fetch the list after a rename: `wxcli call-park list LOCATION_ID -o json`.

## Step 7: Verify creation

After creation, fetch the details back and confirm:

```bash
# Example for auto attendant
wxcli auto-attendant show LOCATION_ID AA_ID --output json

# Example for call queue
wxcli call-queue show LOCATION_ID QUEUE_ID --output json

# Example for hunt group
wxcli hunt-group show LOCATION_ID HG_ID --output json

# Example for paging
wxcli paging-group show LOCATION_ID PAGING_ID --output json

# Example for call park
wxcli call-park show LOCATION_ID CALLPARK_ID --output json

# Example for call pickup
wxcli call-pickup show LOCATION_ID PICKUP_ID --output json

# Example for voicemail group
wxcli location-voicemail show-voicemail-groups LOCATION_ID VMG_ID --output json
```

## Step 8: Report results

Present the creation results:

```
FEATURE CREATED
===============
Type: [feature_type]
Name: [name]
ID: [feature_id]
Location: [location_name]
Extension: [extension]
Phone Number: [phone_number or "None assigned"]
Agents/Members: [count]

Next steps:
  - [Feature-specific next steps, e.g., "Upload custom greeting via Control Hub"]
  - [e.g., "Configure holiday service on the queue policy"]
  - [e.g., "Add agents to the hunt group"]
```

---

## Critical Rules

1. **Always verify location exists** before creating any feature. Every feature is location-scoped.
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing.
3. **Agent/member assignment requires valid person IDs.** Use `wxcli users list --calling-data true` or the feature-specific `available-agents` subcommand to find them.
4. **Phone number vs. extension** -- at least one is required for AA, CQ, HG, Paging, VM Groups. Use `wxcli numbers list --location-id LOCATION_ID` to find unassigned numbers.
5. **Audio file upload is not supported via API** -- custom greetings for AA and CQ must be uploaded through Webex Control Hub.
6. **Call Park and Call Pickup IDs change on name modification.** Always re-fetch after renaming.
7. **CQ routing policy limits** -- `SIMULTANEOUS` max 50 agents; `WEIGHTED` max 100 agents; `CIRCULAR`/`REGULAR`/`UNIFORM` max 1,000 agents.
8. **Paging Group: originators require update** -- the CLI create command does not accept originator/target lists; use `wxcli paging-group update` after creation.
9. **Call Pickup one-group-per-user constraint** -- a user can only belong to one pickup group.
10. **Customer Assist (CX Essentials) has its own skill.** Use the `customer-assist` skill for screen pop, wrap-up, queue recording, and supervisor configuration. Call queue creation stays in this skill.
11. **Hunt Group holiday/night service** uses forwarding rules (schedule-based), not a dedicated policy API like Call Queues have.
12. **Voicemail Group passcode is required** on create -- the CLI enforces this via `--passcode` (required option).
13. **AA create: menus are auto-populated by the CLI.** The CLI provides default menus (key 0 = EXIT, extension dialing enabled) so the create command succeeds. Customize menus via `wxcli auto-attendant update` after creation.
14. **CQ update uses partial objects.** The CLI `update` command avoids the `callingLineIdPolicy=CUSTOM` 400 error by sending only changed fields.
15. **VM Group SDK bug is handled by the CLI.** The `wxcli location-voicemail create` command works around the `by_alias=True` bug internally.
16. **Before deleting, check for cross-feature references.** Some features are referenced by others and deleting them silently breaks the dependent feature:
    - Hunt Groups may be referenced by Call Park recall configuration. Check: `wxcli call-park list LOCATION_ID -o json` and inspect `recall.huntGroupId`.
    - Auto Attendants may be referenced by Call Queues (overflow destination) or other AAs (key-press routing). Check overflow settings on any CQ at the location.
    - Call Queues may be referenced by AAs as overflow targets.
    Run the relevant checks before executing any delete.

17. **Location-scoped deletes take LOCATION_ID as the FIRST argument** — `wxcli hunt-group delete --force LOCATION_ID HG_ID`, not `wxcli hunt-group delete --force HG_ID`. This applies to all location-scoped features: hunt-group, auto-attendant, call-queue, paging-group, call-park, call-pickup, location-voicemail, location-schedules.
17. **Always use `--force` for programmatic deletes** — Without `--force`, delete commands prompt `[y/N]` which blocks non-interactive execution.
18. **Agent/member format differs by feature type.** Hunt Groups and Call Queues take `agents` as `[{"id": "person_id"}]` (array of objects). Call Pickups take `agents` as `["person_id"]` (plain string array). Paging Groups take `targets`/`originators` as plain string arrays. Using the wrong format returns 400 "Invalid field value". Always check `docs/reference/call-features-additional.md` if unsure.
19. **Call Parks and Call Pickups require location for listing.** `wxcli call-park list` and `wxcli call-pickup list` without a location argument return empty. Must pass `LOCATION_ID` as first positional arg: `wxcli call-park list LOCATION_ID -o json`.
20. **Cross-skill handoffs:**
    - CX Essentials configuration → `customer-assist` skill (screen pop, wrap-up, recording, supervisors)
    - Person/workspace call settings → `manage-call-settings` skill (voicemail, forwarding, DND, etc.)
    - Routing (trunks, dial plans, PSTN) → `configure-routing` skill
    - Device provisioning → `manage-devices` skill
    - Location teardown → `provision-calling` skill (Operation D: Teardown)

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
