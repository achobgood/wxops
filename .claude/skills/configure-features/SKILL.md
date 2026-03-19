---
name: configure-features
description: |
  Configure Webex Calling call features using wxcli CLI commands: Auto Attendants, Call Queues,
  Hunt Groups, Paging Groups, Call Park, Call Pickup, Voicemail Groups, and CX Essentials.
  Guides the user from prerequisites through creation and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [feature-type]
---

<!-- Updated by playbook session 2026-03-18 -->

# Configure Call Features Workflow

## Step 1: Load references

1. Read `docs/reference/call-features-major.md` for AA, CQ, HG data models and API signatures
2. Read `docs/reference/call-features-additional.md` for Paging, Call Park, Call Pickup, VM Groups, CX Essentials
3. Read `docs/reference/authentication.md` for auth token conventions

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`). Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`
- **CX Essentials recording**: `spark-admin:people_read` / `spark-admin:people_write`

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
| Screen pop, queue recording, or wrap-up reasons on a CQ | **CX Essentials** |

## Step 4: Check prerequisites

Before creating any feature, verify these exist:

### 4a. Location exists

All features are location-scoped. Confirm the target location:

```bash
wxcli locations list --output json
```

Scan the output for the target location name and capture the `location_id`. For details on a specific location:

```bash
wxcli locations show LOCATION_ID
```

If no location matches, the user must create one first (see provisioning skill).

### 4b. Users/agents exist (for features that need members)

For CQ, HG, Paging, Call Park, Call Pickup -- confirm the people who will be agents/members:

```bash
wxcli users list --calling-enabled --output json
```

To filter by location:

```bash
wxcli users list --calling-enabled --location LOCATION_ID --output json
```

### 4c. Phone numbers available (for features that need a number)

For AA, CQ, HG, Paging, VM Groups -- check available numbers at the location:

```bash
wxcli numbers list --location LOCATION_ID --output json
```

### 4d. Feature-specific prerequisites

| Feature | Additional Prerequisites |
|---------|------------------------|
| **Auto Attendant** | Business hours schedule must exist. Custom greetings must be uploaded via Control Hub (API upload not supported). |
| **Call Queue** | Agents must have Webex Calling Professional license. CX Essentials queue requires CX Essentials license on agents. |
| **Hunt Group** | None beyond location + agents. Can be created with zero agents. |
| **Paging Group** | If originators are set, `originator_caller_id_enabled` is required. |
| **Call Park** | Call Park Extensions should be created first. Recall to hunt group requires an existing HG. |
| **Call Pickup** | A user can only belong to one pickup group at a time. |
| **Voicemail Group** | Extension is required. Passcode is required. |
| **CX Essentials** | Call Queue must exist first. Requires CX Essentials licensing. |

## Step 5: Gather feature-specific configuration

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

> **NOTE:** The CLI automatically provides default `callPolicies` (PRIORITY_BASED routing, CIRCULAR policy) so the create succeeds. Agents are added after creation.

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

**CLI command:**

```bash
wxcli hunt-group create LOCATION_ID \
  --name "Sales Team" \
  --extension 3000 \
  --enabled
```

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

### CX Essentials

CX Essentials enhances existing Call Queues. The queue must exist first.

> **CLI commands now available:** Use `wxcli cx-essentials` for wrap-up reasons, screen pop, and settings. <!-- Updated by playbook session 2026-03-18 -->

**Three sub-features:**

#### Screen Pop
Pop a URL when agent receives a queued call:

```bash
# View current screen pop config
wxcli cx-essentials show-screen-pop LOCATION_ID QUEUE_ID --output json

# Update screen pop config
wxcli cx-essentials update-screen-pop LOCATION_ID QUEUE_ID \
  --enabled --screen-pop-url "https://crm.example.com/lookup"
```

**Raw HTTP alternative** (if CLI doesn't cover all fields):
```python
from wxc_sdk.telephony.cx_essentials import ScreenPopConfiguration

config = ScreenPopConfiguration(
    enabled=True,
    screen_pop_url='https://crm.example.com/lookup',
    desktop_label='Customer Lookup',
    query_params={'caller_id': '{{callerNumber}}'}
)
api.telephony.cx_essentials.modify_screen_pop_configuration(
    location_id=location_id, queue_id=queue_id, settings=config
)
```

#### Queue Call Recording
```python
recording = api.telephony.cx_essentials.callqueue_recording.read(
    location_id=location_id, queue_id=queue_id
)
recording.enabled = True
recording.record = 'Always'
api.telephony.cx_essentials.callqueue_recording.configure(
    location_id=location_id, queue_id=queue_id, recording=recording
)
```

#### Wrap-Up Reasons
Create org-level reasons, then assign to queues:
```python
# Create a reason
reason_id = api.telephony.cx_essentials.wrapup_reasons.create(
    name='Issue Resolved',
    description='Customer issue was resolved on the call',
    queues=[queue_id]
)

# Configure queue wrap-up settings
api.telephony.cx_essentials.wrapup_reasons.update_queue_settings(
    location_id=location_id,
    queue_id=queue_id,
    wrapup_reasons=[reason_id],
    wrapup_timer_enabled=True,
    wrapup_timer=60
)
```

---

## Step 6: Build and present deployment plan -- `[SHOW BEFORE EXECUTING]`

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

## Step 7: Execute via wxcli

Run the creation command. If the feature requires multiple steps (e.g., agents added after CQ/HG creation), execute them in order.

Handle errors explicitly:
- **401/403**: Token expired or insufficient scopes -- run `wxcli configure` to re-authenticate
- **409**: Name or extension conflict -- ask user for alternate
- **400**: Validation error -- read the error message and fix the parameter

## Step 8: Verify creation

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

## Step 9: Report results

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
2. **Always show the deployment plan** (Step 6) and wait for user confirmation before executing.
3. **Agent/member assignment requires valid person IDs.** Use `wxcli users list --calling-enabled` or the feature-specific `available-agents` subcommand to find them.
4. **Phone number vs. extension** -- at least one is required for AA, CQ, HG, Paging, VM Groups. Use `wxcli numbers list --location LOCATION_ID` to find unassigned numbers.
5. **Audio file upload is not supported via API** -- custom greetings for AA and CQ must be uploaded through Webex Control Hub.
6. **Call Park and Call Pickup IDs change on name modification.** Always re-fetch after renaming.
7. **CQ routing policy limits** -- `SIMULTANEOUS` max 50 agents; `WEIGHTED` max 100 agents; `CIRCULAR`/`REGULAR`/`UNIFORM` max 1,000 agents.
8. **Paging Group: originators require update** -- the CLI create command does not accept originator/target lists; use `wxcli paging-group update` after creation.
9. **Call Pickup one-group-per-user constraint** -- a user can only belong to one pickup group.
10. **CX Essentials requires existing Call Queues** -- screen pop, recording, and wrap-up reasons are per-queue configurations. Use `wxcli cx-essentials` commands.
11. **Hunt Group holiday/night service** uses forwarding rules (schedule-based), not a dedicated policy API like Call Queues have.
12. **Voicemail Group passcode is required** on create -- the CLI enforces this via `--passcode` (required option).
13. **AA create: menus are auto-populated by the CLI.** The CLI provides default menus (key 0 = EXIT, extension dialing enabled) so the create command succeeds. Customize menus via `wxcli auto-attendant update` after creation.
14. **CQ update uses partial objects.** The CLI `update` command avoids the `callingLineIdPolicy=CUSTOM` 400 error by sending only changed fields.
15. **VM Group SDK bug is handled by the CLI.** The `wxcli location-voicemail create` command works around the `by_alias=True` bug internally.

---

## Context Compaction

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
