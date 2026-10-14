---
name: configure-features
description: |
  Create, modify, or delete Webex Calling call features using wxcli CLI commands: Auto Attendants, Call Queues,
  Hunt Groups, Paging Groups, Call Park, Call Pickup, Voicemail Groups, and Calling schedules
  (business hours, holidays). Also covers the announcement repository (greeting files) and
  text-to-speech prompt generation, announcement playlists (music on hold) and playlist usage,
  location call handling (internal dialing, location intercept, outgoing calling permissions,
  access/authorization codes, outgoing digit patterns), caller reputation (spam/fraud call scoring),
  external voicemail MWI control, and AI Receptionist (an AI that answers calls, with its
  intents and knowledge bases). Guides the user from prerequisites through creation,
  modification, deletion, and verification.
  Use for: create, update, delete, remove, list, or troubleshoot any Calling call feature.
  NOT for: Contact Center queues/teams/flows (use contact-center skill), Customer Assist/CX Essentials
  (use customer-assist skill), or per-person call settings (use manage-call-settings skill).
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
3. Read `docs/reference/location-calling-media.md` for announcements, playlists, and access codes (only when working those groups)
4. Read `docs/reference/location-calling-core.md` for internal dialing and location-level call handling
5. Read `docs/reference/location-recording-advanced.md` for caller reputation
6. Read the "Additional API: External Voicemail MWI" section of `docs/reference/call-control.md` for external voicemail MWI
7. Read `docs/reference/ai-receptionist.md` for AI Receptionist, its intents, and knowledge bases

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli call-queue create --help` reveals the kebab-cased flags like `--has-cx-essentials` and the `--json-body` shape you cannot guess from training data). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

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
| Upload/manage greeting audio files used by AA/CQ; generate a spoken prompt from text | **Announcements** (`announcements`) |
| Group announcements into a music-on-hold rotation and assign to locations | **Announcement Playlists** (`announcement-playlists`) |
| See which queues/locations reference a playlist before changing or deleting it | **Playlist Usage** (`cq-playlists`) |
| Route unknown extensions off-net; block/allow outbound call types; access codes; digit patterns | **Location Call Handling** (`location-call-handling`) |
| Score inbound calls for spam/fraud via an external reputation provider | **Caller Reputation** (`caller-reputation`) |
| Turn a user's or workspace's voicemail waiting light on/off from an external voicemail system | **External Voicemail MWI** (`external-voicemail`) |
| An AI answers the call, understands why the caller rang, and routes or answers from your own documents | **AI Receptionist** (`ai-receptionist`) |

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
| Originators/targets exist | `wxcli users list --calling-data true -o json` | Originators and targets can go in the create body (`--json-body`, plain ID strings) or be added later with `wxcli paging-group update` (both verified live 2026-10-13) |

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

> **NOTE (verified live 2026-10-13):** the CLI does **not** supply default menus. `wxcli auto-attendant create LOCATION_ID --name ... --extension ... --business-schedule ...` (flags only) fails `400 25008 "Missing Mandatory field name:  businessHoursMenu"`. Create needs `--json-body` containing both menus. `businessSchedule` must be the exact **name** of an existing schedule at that location (`wxcli location-schedules list LOCATION_ID`), not a made-up label.

```bash
wxcli auto-attendant create LOCATION_ID --json-body '{
  "name": "Main Menu",
  "extension": "1000",
  "businessSchedule": "EXACT_SCHEDULE_NAME",
  "businessHoursMenu": {"greeting": "DEFAULT", "extensionEnabled": true,
    "keyConfigurations": [{"key": "0", "action": "EXIT"}]},
  "afterHoursMenu": {"greeting": "DEFAULT", "extensionEnabled": true,
    "keyConfigurations": [{"key": "0", "action": "EXIT"}]}
}'
```

To change menus later use `wxcli auto-attendant update LOCATION_ID AA_ID --json-body '{"businessHoursMenu": {...}}'`. A menu you send **replaces** that whole menu (sending keys 1 and 0 removed an existing key 2), so resend every key you want to keep.

Other flags (usable only when you do not pass `--json-body`, which overrides them): `--phone-number`, `--holiday-schedule`, `--extension-dialing`, `--name-dialing`, `--first-name`, `--last-name`, `--language-code`, `--time-zone`.

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
| Call bounce settings | No | `max_rings` (server default 8 when `callBounce` is omitted), `agent_unavailable_enabled` (default false); verified live 2026-10-13 |
| Agent join/unjoin enabled | No | Let agents toggle themselves in/out |

**Announcement chain** (all optional, configure as needed):

1. **Welcome message** -- first thing callers hear; can be mandatory even when agent is available
2. **Wait message** -- estimated wait time or queue position
3. **Comfort message** -- periodic message (promotions, info); interval 10-600 seconds
4. **Comfort message bypass** -- short comfort for quickly-answered calls
5. **Music on hold** -- normal + alternate source
6. **Whisper message** -- plays to agent before connection (identifies which queue)

**CLI command:**

> **NOTE (verified live 2026-10-13):** `callPolicies.policy` is required for EVERY call queue, not just CX Essentials. `wxcli call-queue create LOCATION_ID --name ... --extension ...` (flags only) fails `400 25008 "Missing Mandatory field name:  callPolicies"`; `"callPolicies":{}` fails `"...callPolicies.policy"`. (`hunt-group create` is different: the CLI injects a default `callPolicies` for it; `call-queue create` does not.) Agents, `queueSettings` and `routingType` are optional on create.

```bash
wxcli call-queue create LOCATION_ID \
  --json-body '{"name": "Support Queue", "extension": "2000", "callPolicies": {"policy": "CIRCULAR"}}'
```

`--json-body` overrides the other flags, so put `name`/`extension` (or `phoneNumber`) inside it.

To add agents after creation, use the update command with `--json-body`:

```bash
wxcli call-queue update LOCATION_ID QUEUE_ID --json-body '{"agents": [{"id": "AGENT_PERSON_ID"}]}'
```

To find available agents for a location:

```bash
wxcli call-queue list-available-agents-queues --location-id LOCATION_ID --output json
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

**callPolicies structure.** Verified live 2026-10-13: only `policy` is required inside it -- `{"callPolicies":{"policy":"CIRCULAR"}}` created a hunt group and the server filled in `noAnswer` (server defaults: nextAgentEnabled **false**, nextAgentRings 5, forwardEnabled false, numberOfRings 15 — read back from a `{"callPolicies":{"policy":"REGULAR"}}` create; the "nextAgentEnabled true, rings 3" you see after a plain `hunt-group create` comes from the CLI's own injected default, not the server). The **raw API requires `callPolicies`**: a direct POST without it returns `400 25008 "Missing Mandatory field name:  callPolicies"`. A `noAnswer` object that omits `destinationVoicemailEnabled` is also accepted. The `Yes` marks on the `noAnswer.*` rows below are what the spec says, not what the API enforces. If you pass no `callPolicies` at all, `wxcli hunt-group create` injects one.

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

Optional flags: `--phone-number`, `--first-name`, `--last-name`, `--language-code`, `--originator-caller-id-enabled`.

To list existing paging groups:

```bash
wxcli paging-group list --location-id LOCATION_ID --output json
```

> **NOTE (verified live 2026-10-13):** the create flags only cover name/extension/etc., but `--json-body` accepts `originators`, `targets` and `originatorCallerIdEnabled` in the same create call, as **plain ID strings** -- `wxcli paging-group create LOCATION_ID --json-body '{"name":"Warehouse Page","extension":"8100","originatorCallerIdEnabled":true,"originators":["PERSON_ID"],"targets":["PERSON_ID"]}'`. `[{"id": ...}]` objects fail `400 25024 "Invalid field value: targets"`. `wxcli paging-group update` can change them later.

---

### Call Park

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 80 chars |
| Agents | No | People/workspaces eligible to receive parked calls |
| Call Park Extensions | No | Dedicated park extensions (create these first) |
| Park on agents enabled | No | Whether calls can be parked directly on agents |
| Recall behavior | No | `recall.option` is **required** on create (no server default): `ALERT_PARKING_USER_ONLY`, `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP`, `ALERT_HUNT_GROUP_ONLY` |
| Recall hunt group | If recall uses HG | Must be an existing hunt group at the location |

**CLI command:**

> **NOTE (verified live 2026-10-13):** the CLI does **not** supply `recall`. `wxcli call-park create LOCATION_ID --name "Lobby Park"` fails `400 25008 "message=Missing required field(s)."`. Pass `name` AND `recall.option` in `--json-body` (it overrides the flags, so `--name` plus a body without `name` fails too).

```bash
wxcli call-park create LOCATION_ID --json-body '{"name": "Lobby Park", "recall": {"option": "ALERT_PARKING_USER_ONLY"}}'
```

`agents` and `callParkExtensions` in the body are plain ID strings, not `{"id":...}` objects (objects fail `400 25024 "Invalid field value: agents"`).

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

> **NOTE (verified live 2026-10-13):** the flags-only form does **not** work. `wxcli location-voicemail create LOCATION_ID --name ... --extension ... --passcode ... --language-code en_us` fails `400 25008 "...Missing Mandatory field name:  messageStorageType"`: the CLI does not fill in `messageStorage`, `notifications`, `faxMessage`, `transferToNumber` or `emailCopyOfMessage`. Use `--json-body` with every field in it (the body overrides the flags, so `name`/`extension` must be inside it too -- a body without `name` fails `"Missing Mandatory field name:  name"`). `passcode` as a string (`"740384"`) is accepted.

```bash
wxcli location-voicemail create LOCATION_ID --json-body '{
  "name": "Support VM", "extension": "8200", "passcode": "740384", "languageCode": "en_us",
  "messageStorage": {"storageType": "INTERNAL"},
  "notifications": {"enabled": false},
  "faxMessage": {"enabled": false},
  "transferToNumber": {"enabled": false},
  "emailCopyOfMessage": {"enabled": false}
}'
```

Optional body fields: `phoneNumber`, `firstName`, `lastName`, `dialByName`.

---

### Announcements (greeting repository + text-to-speech)

The announcement repository holds the audio files that AAs, CQs, and playlists play to callers. Every announcement lives at **one of two scopes**: org-level (available to all locations) or location-level (that location only). Each scope has its own set of commands — this is the main source of confusion in this group.

| Scope | List | Create | Show details | Update | Delete | Repo usage |
|-------|------|--------|--------------|--------|--------|------------|
| Org | `list` | `create` | `show-announcements-config` | `update` | `delete` | `show` |
| Location | `list --location-id LOC_ID` | `create-announcements LOC_ID` | `show-announcements-locations LOC_ID ANN_ID` | `update-announcements LOC_ID ANN_ID` | `delete-announcements LOC_ID ANN_ID` | `show-usage-announcements LOC_ID` |

> **NAMING TRAP:** `wxcli announcements show` does **not** show an announcement — it returns org repository usage (space used, size limits). To fetch one announcement's details use `show-announcements-config ANNOUNCEMENT_ID` (org) or `show-announcements-locations LOCATION_ID ANNOUNCEMENT_ID` (location).

**Discovery — start here:**

```bash
# List org-level announcements
wxcli announcements list --output json

# List announcements for one location, or across all locations
wxcli announcements list --location-id LOCATION_ID --output json
wxcli announcements list --location-id all --output json

# Check repository space before uploading
wxcli announcements show --output json
```

`list` also filters with `--name`, `--file-name`, `--file-type`, `--media-file-type`, and sorts with `--order`.

**Create an announcement.** `create` (org) and `create-announcements LOCATION_ID` take a file **URI**, not a local file path — all four flags are required. **The URI must be a Calling Media File Service reference (`cmf://customers/<org>/media/tmp/<id>`), not an open-web URL.** Verified live 2026-10-13: `--file-uri https://example.com/welcome.wav` and a real, reachable public WAV (`https://www.kozco.com/tech/piano2.wav`, HTTP 200) both fail `400 27917 "Error retrieving announcement file from Calling Media File Service"`. The only way found to obtain a valid `cmf://` URI through the CLI is the TTS flow below (`tts-status` returns it as `fileUri`):

```bash
wxcli announcements create \
  --name "Welcome Greeting" \
  --file-uri "cmf://customers/ORG_UUID/media/tmp/TTS_FILE_ID" \
  --file-name "welcome.wav" \
  --is-text-to-speech
```

Use `--no-is-text-to-speech` only for a non-TTS file; `update` / `update-announcements` need `name`, `fileName` AND `fileUri` together (a name-only body fails `400 25008 "Missing Mandatory field name:  fileName"`, then `"... fileUri"`), and omitting `--is-text-to-speech` on update drops the TTS metadata. Verified live 2026-10-13.

**Delete (both scopes need `--force` for non-interactive runs):**

```bash
wxcli announcements delete ANNOUNCEMENT_ID --force
wxcli announcements delete-announcements LOCATION_ID ANNOUNCEMENT_ID --force
```

**Before deleting, check what references the announcement.** The details command returns `featureReferenceCount` and `playlists` (`[{id,name}]`; verified live 2026-10-13 — the skill's earlier `featureReferences` name was not observed, an announcement with no feature references shows `featureReferenceCount: 0`). A delete of an announcement that sits in a playlist is refused (`400 6575 "cannot be deleted because it is being used by a group or user"`), so delete the playlist first; an AA/CQ greeting reference was not tested:

```bash
wxcli announcements show-announcements-config ANNOUNCEMENT_ID --output json
```

#### Text-to-Speech prompts

Generate spoken audio from text instead of recording and uploading a WAV. The flow is: pick a voice → generate → poll status.

```bash
# 1. List available voices (get the voice ID and language code)
wxcli announcements tts-voices --output json

# 2. Generate the prompt
wxcli announcements tts-generate --voice VOICE_ID --text "Thank you for calling. Please hold." --language-code en_us

# 3. Check generation status (tts-status requires the ttsId that tts-generate returned as {"id": ...})
#    -> {id, voice, text, languageCode, status: "SUCCESS", promptUrl, kmsKeyUri, fileUri: "cmf://..."}
wxcli announcements tts-status TTS_ID --output json

# 4. Check TTS quota/consumption for the org
wxcli announcements tts-usage --output json
```

All four flags on `tts-generate` (`--voice`, `--text`, `--language-code`, plus `--json-body`) are optional per `--help`, but voice and text are needed for a usable prompt. Use `tts-voices` to get a valid `--voice` ID and `--language-code` rather than guessing.

> **Verified live 2026-10-13:** `tts-generate --voice calvin --text "..." --language-code en_us` returned `{"id": "<ttsId>"}`; `tts-status <ttsId>` returned `status: "SUCCESS"` on the first poll (short text) with a `fileUri` of the form `cmf://customers/<org>/media/tmp/<uuid>`; passing that `fileUri` to `announcements create --is-text-to-speech` (org) and `create-announcements LOCATION_ID` (location) created announcements; `tts-usage` went from `noOfApiCalls` 0 to 2 of `maxAllowedApiCalls` 150. **`--language-code` must be lower-case as `tts-voices` returns it (`en_us`); `en_US` fails `400 1014 "The requested language is not supported for this customer"`.** A prompt shorter than 5 s cannot go into a playlist (`400 6536 "Duration is too short for use with Music On Hold. The file must be 5 seconds or longer"`).

---

### Announcement Playlists (music on hold)

A playlist groups announcement files into a rotation (typically music on hold) and is then assigned to locations. **Playlists are org-level objects** — you create one playlist and assign it to many locations.

**Order of operations:** upload announcements first → create the playlist referencing those announcement IDs → assign the playlist to locations.

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name for the playlist |
| Announcement IDs | **Yes (on create)** | Array of announcement IDs (`announcementIds`) — `--json-body` only, no flag exists. `create --name X` alone fails `400 25008 "Missing Mandatory field name:  announcements"` (verified live 2026-10-13) |
| Location IDs | No | Assigned separately via `update-playlists` |

```bash
# List playlists in the org
wxcli announcement-playlists list --output json

# Get one playlist (includes its announcement list)
wxcli announcement-playlists show PLAYLIST_ID --output json

# Create a playlist — announcement IDs require --json-body
wxcli announcement-playlists create --json-body '{"name":"Lobby MOH","announcementIds":["ANN_ID_1","ANN_ID_2"]}'

# Rename (flag) or change its announcements (--json-body)
wxcli announcement-playlists update PLAYLIST_ID --name "Lobby MOH v2"
wxcli announcement-playlists update PLAYLIST_ID --json-body '{"name":"Lobby MOH v2","announcementIds":["ANN_ID_1"]}'

# Delete
wxcli announcement-playlists delete PLAYLIST_ID --force
```

**Location assignment:**

```bash
# Which locations use this playlist
wxcli announcement-playlists list-playlists PLAYLIST_ID --output json

# Assign locations — FULL REPLACE, not incremental
wxcli announcement-playlists update-playlists PLAYLIST_ID --json-body '{"locationIds":["LOC_ID_1","LOC_ID_2"]}'
```

> **WARNING (full replace):** `update-playlists` replaces the entire location assignment list. Always read the current list with `list-playlists` first and include every location you want to keep — omitting one un-assigns it.

> **NAMING TRAP:** `list-playlists` and `update-playlists` operate on a playlist's **locations**, not on playlists. To list playlists themselves, use plain `list`.

#### Playlist usage (`cq-playlists`)

Before changing or deleting a playlist, check what references it. This is the only command in the `cq-playlists` group.

```bash
# Everything referencing this playlist
wxcli cq-playlists list PLAYLIST_ID --output json

# Narrow to feature references (call queues, auto attendants) or location assignments
wxcli cq-playlists list PLAYLIST_ID --playlist-usage-type feature --output json
wxcli cq-playlists list PLAYLIST_ID --playlist-usage-type location --output json
```

`--playlist-usage-type` accepts only `feature` or `location`.

---

### CX Essentials (Customer Assist)

Customer Assist (formerly CX Essentials) has its own dedicated skill with full coverage of screen pop, wrap-up reasons, queue call recording, supervisors, and available agents.

> **Use the `customer-assist` skill** for all Customer Assist configuration.

The call queue itself is still created here (see Call Queue section above). Once the queue exists, switch to the `customer-assist` skill to configure Customer Assist features on it.

---

### Location Call Handling

19 commands covering location-wide call handling: where unknown extensions route, whether the location is intercepted, what call types users may dial out, and the access codes / digit patterns that override those rules. **Every command takes `LOCATION_ID` as the first positional argument.**

> **THIS GROUP HAS THE WORST NAMING IN THE CLI.** The generic verbs do not mean what they look like. Read this table before running anything:
>
> | Command | What it ACTUALLY does |
> |---------|----------------------|
> | `show` / `update` | Internal **dialing** config — not a generic show/update |
> | `list` | Gets the location's **outgoing permission** — prints a JSON **array** of per-call-type entries (13 live, each `{callType, action, transferEnabled, isCallTypeRestrictionEnabled}`; verified 2026-10-13) |
> | `create` | Creates an **access code** |
> | `update-access-codes` | **DELETES** specific access codes (body is `deleteCodes`) — it does not update anything |
> | `delete` | **DELETES ALL** access codes for the location |
> | `delete-digit-patterns-outgoing-permission` | **DELETES ALL** digit patterns for the location |
> | `delete-digit-patterns-outgoing-permission-1` | Deletes **one** digit pattern (the `-1` suffix is the single-item variant) |

**Discovery — read current state before changing anything:**

```bash
wxcli location-call-handling show LOCATION_ID --output json                  # internal dialing
wxcli location-call-handling list LOCATION_ID --output json                  # outgoing permissions
wxcli location-call-handling show-intercept LOCATION_ID --output json        # intercept
wxcli location-call-handling show-access-codes LOCATION_ID --output json     # access codes
wxcli location-call-handling list-digit-patterns LOCATION_ID --output json   # digit patterns
```

#### Internal dialing (`show`, `update`)

Controls whether calls to an unknown extension are routed off-net to a trunk or route group.

```bash
wxcli location-call-handling update LOCATION_ID --json-body '{"enableUnknownExtensionRoutePolicy":true,"unknownExtensionRouteIdentity":{"id":"ROUTE_GROUP_ID","type":"ROUTE_GROUP"}}'
```

`--enable-unknown-extension-route-policy` / `--no-enable-unknown-extension-route-policy` toggles the policy alone, but **enabling it without a route target fails** `400 27344 "Unknown extension premises route identity need to be configured..."` (verified live 2026-10-13); setting the route target requires `--json-body`. The trunk or route group must already exist — create it with the `configure-routing` skill first.

#### Location intercept (`show-intercept`, `update-intercept`)

Overrides all inbound and/or outbound calling at the location, sending callers to an announcement instead. Used during cutovers and closures.

```bash
wxcli location-call-handling update-intercept LOCATION_ID --json-body '{"enabled":true,"incoming":{"type":"INTERCEPT_ALL","voicemailEnabled":true,"announcements":{"greeting":"DEFAULT"}},"outgoing":{"type":"INTERCEPT_ALL","transferEnabled":false}}'
```

`--enabled` / `--no-enabled` toggles intercept alone.

> **BLAST RADIUS:** Enabling intercept silently overrides call handling for the **whole location**. Confirm with the user before enabling.

#### Outgoing permissions (`list`, `update-outgoing-permission`)

Allow/block outbound call types (international, premium, toll-free, etc.) for the location.

```bash
wxcli location-call-handling update-outgoing-permission LOCATION_ID --json-body '{"callingPermissions":[{"callType":"INTERNATIONAL","action":"BLOCK","transferEnabled":false}]}'
```

#### Auto transfer numbers (`show-auto-transfer-numbers`, `update-auto-transfer-numbers`)

The destinations that outbound rules with a `TRANSFER_NUMBER_1/2/3` action send calls to.

```bash
wxcli location-call-handling show-auto-transfer-numbers LOCATION_ID --output json
wxcli location-call-handling update-auto-transfer-numbers LOCATION_ID --auto-transfer-number1 "+15551234567"
```

Flags: `--auto-transfer-number1`, `--auto-transfer-number2`, `--auto-transfer-number3`. Numbers read back normalised (`+15551234567` -> `+1-5551234567`); to clear one send `--json-body '{"autoTransferNumber1":""}'` (verified live 2026-10-13: read-back returned to `{}`).

#### Access codes (`show-access-codes`, `create`, `update-access-codes`, `delete`)

Authorization codes that let a caller bypass an outgoing permission restriction.

```bash
# Add an access code
wxcli location-call-handling create LOCATION_ID --json-body '{"accessCodes":{"code":"123456","description":"Front desk override"}}'

# Delete SPECIFIC codes (yes, the command is named "update-access-codes")
wxcli location-call-handling update-access-codes LOCATION_ID --json-body '{"deleteCodes":["123456"]}' --force   # without --force: "[y/N]" prompt -> "Aborted!", nothing deleted (verified live 2026-10-13)

# Delete ALL access codes at the location
wxcli location-call-handling delete-access-codes-all LOCATION_ID --force
```

#### Digit patterns (6 commands)

Per-pattern outbound rules — match a dialed pattern and allow, block, require an auth code, or force a transfer number.

```bash
# Create a pattern (all four flags required)
wxcli location-call-handling create-digit-patterns LOCATION_ID \
  --name "Block 900" --pattern "1900XXXXXXX" --action BLOCK --no-transfer-enabled

# Read one / update one
wxcli location-call-handling show-digit-patterns LOCATION_ID DIGIT_PATTERN_ID --output json
wxcli location-call-handling update-digit-patterns LOCATION_ID DIGIT_PATTERN_ID --action ALLOW

# Delete ONE pattern
wxcli location-call-handling delete-digit-patterns-outgoing-permission-1 LOCATION_ID DIGIT_PATTERN_ID --force

# Delete ALL patterns at the location
wxcli location-call-handling delete-digit-patterns-outgoing-permission LOCATION_ID --force
```

`--action` accepts: `ALLOW`, `BLOCK`, `AUTH_CODE`, `TRANSFER_NUMBER_1`, `TRANSFER_NUMBER_2`, `TRANSFER_NUMBER_3`.

> **Digit patterns here are permission rules (allow/block a dialed pattern), not digit manipulation.** To strip or prepend digits, use translation patterns in the `configure-routing` skill.

#### Example password (`generate-example-password`)

Generates a compliant example password for the location's SIP device credentials.

```bash
wxcli location-call-handling generate-example-password LOCATION_ID --json-body '{"generate":["sip"]}'
```

---

### Caller Reputation

Connects an external reputation provider that scores inbound calls for spam/fraud. **Org-level, not location-level** — there is no `LOCATION_ID` argument in this group.

```bash
# What providers are available
wxcli caller-reputation list --output json

# Current service settings and connection status
wxcli caller-reputation show --output json
wxcli caller-reputation show-status --output json

# Enable a provider and set scoring thresholds
wxcli caller-reputation update --enabled --id PROVIDER_ID --name "Provider Name" \
  --client-id CLIENT_ID --client-secret CLIENT_SECRET \
  --call-block-score-threshold "80" --call-allow-score-threshold "20"

# Recover a provider locked out after repeated auth failures
wxcli caller-reputation unlock-caller-reputation --id PROVIDER_ID
```

**Gotchas (both confirmed in `--help`):**
- **Score thresholds are strings, not integers** — `--call-block-score-threshold "80"`. Quote them.
- **This group uses `--organization-id`, not the usual `--orgId`/`orgId` injection.** Every command accepts `--organization-id`; omit it to use the token's own org.
- `show-status` returns provider state: `NOT_CONNECTED`, `CONNECTING`, `CONNECTED`, `ACTIVE`, `EXPIRED`, `AUTH_FAILED`, `PROVIDER_DISABLED`. An `AUTH_FAILED` or `EXPIRED` provider is why scoring silently stops.
- `client_secret` is write-only — it is never returned by `show`.

---

### External Voicemail (MWI)

Two commands, same action. Turns the message-waiting indicator (the voicemail light/badge) on or off — used when an **external** voicemail system, not Webex voicemail, holds the messages.

```bash
# Light the voicemail indicator (target as --id: person or workspace)
wxcli external-voicemail create --id PERSON_OR_WORKSPACE_ID --action SET

# Turn it off
wxcli external-voicemail create --id PERSON_OR_WORKSPACE_ID --action CLEAR

# Member-path form — target in the path; the spec also allows a virtual line here
wxcli external-voicemail create-mwi MEMBER_ID --action SET
```

`create` needs `--id` and `--action`; `create-mwi` needs the `MEMBER_ID` positional and `--action`. `--action` accepts `SET` or `CLEAR` only. Use `create-mwi` for a virtual line — the spec lists its `memberId` as "person, workspace, or virtual line" (`--help` calls it a PEOPLE id; the spec is right on ID kinds). **Unverified:** `create-mwi` has not been run live.

> **Requires a Service App token** with the `spark-admin:calls_write` scope — an ordinary admin token or PAT will not work here. See the "Additional API: External Voicemail MWI" section of `docs/reference/call-control.md` for both endpoint forms and their gotchas. These commands only drive the indicator; they do not create or store voicemail. To read or delete *Webex* voicemail messages, that is `user-call-settings-members` in the manage-call-settings skill.

---

### AI Receptionist

An AI answers the call instead of an IVR menu: it hears why the caller rang, answers from
documents you upload (a **knowledge base**), and hands off to a person when an **intent**
matches. Three separate resources, created in this order:

| Resource | Scope | Command family |
|----------|-------|----------------|
| Knowledge base + its documents | **Org-wide** — build once, reuse at every location | `*-knowledge-bases`, `*-documents` |
| AI Receptionist | **Per location** | bare `list`/`show`/`create`/`update`/`delete` |
| Intents (route "I need billing" to a person) | Per receptionist | `*-intents` |

**Read the bare verbs carefully — they act on the receptionist, and the template read is
separate.** `show` returns an AI Receptionist; `show-template` returns a starter template
from the org catalogue (`list-templates`). These were pinned deliberately, because the
generator's derived names had `show` returning a *template* while `update` and `delete` acted
on the *receptionist* — same group, three verbs, two different resources.

```bash
# Knowledge base first — org-wide, plain flags work
wxcli ai-receptionist create-knowledge-bases --name "Store FAQ" --description "Hours, returns, parking"
wxcli ai-receptionist list-knowledge-bases

# What voices and numbers are available at this location
wxcli ai-receptionist list-voices LOCATION_ID
wxcli ai-receptionist list-available-numbers LOCATION_ID

# Check the country is supported before building anything
wxcli ai-receptionist validate-country --country-code US

# Create the receptionist — see the --json-body note below
wxcli ai-receptionist create LOCATION_ID --generate-json-body

# Read it back, and list every receptionist in the org
wxcli ai-receptionist show LOCATION_ID AI_RECEPTIONIST_ID
wxcli ai-receptionist list --all
```

> **`create` and `create-intents` need `--json-body`, not flags.** Both declare required
> fields that are nested objects — `--default-action` and `--ai-agent` on `create`,
> `transferTo` on `create-intents` — and the generator renders a nested object as a plain
> TEXT option, so passing a JSON string to those flags sends a string where the API expects
> an object (Known Issue #2). Run the command with `--generate-json-body` first, fill in the
> skeleton, then pass it back with `--json-body`. `create-knowledge-bases` has no nested
> required field and works with plain flags.

**Document upload is not in the CLI.** `POST .../documents/actions/upload/invoke` is a
`multipart/form-data` endpoint, which the generator structurally skips — that is why this
group has 27 commands and not 28. Add document *content* with
`wxcli ai-receptionist create-documents KNOWLEDGE_BASE_ID --name "Returns" --content "..."`,
or upload a file with raw HTTP. `download-documents` downloads one document (not the whole
knowledge base, despite the container in the path).

Deleting: work inwards-out — intents, then the receptionist, then its knowledge base. That
order follows the containment in the paths; **the API's behaviour when you delete out of
order has not been tested here**, so do not promise the user it will be refused cleanly.

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
- **400 25008 on CQ create (missing callPolicies):** every call queue (CX or not) needs `callPolicies.policy` in the create body; the call-queue flags cannot supply it. Add via `--json-body`.
- **400 on CQ update (callingLineIdPolicy=CUSTOM):** Sending the full queue object on update triggers this. Use individual flags (`--name`, `--extension`) instead of `--json-body` with the full object. The CLI handles partial updates automatically. (Live 2026-10-13: this 400 did NOT reproduce — a queue with `callingLineIdPolicy` CUSTOM + `callingLineIdPhoneNumber` was read with `call-queue show` and the whole object PUT back via `--json-body file://` returned 2xx. Partial updates are still the safe default.)
- **28018 on CX operations:** "CX Essentials is not enabled for this Call center" — the queue isn't a CX queue. Must pass `--has-cx-essentials true` on list commands and create with `callPolicies`.
- **400 on VM Group create (passcode):** error `5432 "Invalid portal passcode."`. Passcode doesn't meet requirements: 6+ digits, no repeating sequences, no common patterns. Verified live 2026-10-13: `111111` (repeating), `12345` (too short) and `123456` (sequential) were each rejected with 5432; `740384` was accepted.
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

# Example for announcement (org-level vs location-level)
wxcli announcements show-announcements-config ANNOUNCEMENT_ID --output json
wxcli announcements show-announcements-locations LOCATION_ID ANNOUNCEMENT_ID --output json

# Example for announcement playlist (plus its location assignments)
wxcli announcement-playlists show PLAYLIST_ID --output json
wxcli announcement-playlists list-playlists PLAYLIST_ID --output json

# Example for location call handling (each theme reads back separately)
wxcli location-call-handling show LOCATION_ID --output json
wxcli location-call-handling list LOCATION_ID --output json
wxcli location-call-handling show-access-codes LOCATION_ID --output json
wxcli location-call-handling list-digit-patterns LOCATION_ID --output json

# Example for caller reputation (settings + live connection state)
wxcli caller-reputation show --output json
wxcli caller-reputation show-status --output json
```

> **External voicemail MWI has no read-back command** — the `external-voicemail` group only has `create` and `create-mwi`, both write-only. Verify by checking the physical device indicator, not via API.

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
8. **Paging Group: originators/targets via `--json-body`.** The create *flags* do not cover originator/target lists, but `--json-body` accepts `originators`/`targets` (plain ID strings) on create, and `wxcli paging-group update` changes them later. Both verified live 2026-10-13.
9. **Call Pickup one-group-per-user constraint** -- a user can only belong to one pickup group.
10. **Customer Assist (CX Essentials) has its own skill.** Use the `customer-assist` skill for screen pop, wrap-up, queue recording, and supervisor configuration. Call queue creation stays in this skill.
11. **Hunt Group holiday/night service** uses forwarding rules (schedule-based), not a dedicated policy API like Call Queues have.
12. **Voicemail Group passcode is required** on create -- the CLI enforces this via `--passcode` (required option).
13. **AA create needs both menus in `--json-body`.** The CLI does NOT auto-populate menus: flags-only create fails `400 25008 "Missing Mandatory field name:  businessHoursMenu"` (verified live 2026-10-13). An `auto-attendant update` menu replaces that whole menu.
14. **CQ update uses partial objects.** The CLI `update` command avoids the `callingLineIdPolicy=CUSTOM` 400 error by sending only changed fields.
15. **VM Group create needs the full body.** `wxcli location-voicemail create` with flags only fails `400 25008 "...Missing Mandatory field name:  messageStorageType"`; use `--json-body` with name, extension, passcode, languageCode, messageStorage, notifications, faxMessage, transferToNumber and emailCopyOfMessage (verified live 2026-10-13).
16. **Before deleting, check for cross-feature references.** Some features are referenced by others and deleting them silently breaks the dependent feature:
    - Hunt Groups may be referenced by Call Park recall configuration. Check: `wxcli call-park show LOCATION_ID PARK_ID -o json` for each park and compare `recall.huntGroupName` (NOT `recall.huntGroupId` -- the server returns that in a different encoding from the hunt group's own `id`, so an ID comparison never matches; `call-park list` returns no `recall` field, so you must `show` each park). Verified live 2026-10-13: deleting a hunt group that a call park used succeeded and reset that park's recall to `ALERT_PARKING_USER_ONLY`, so the effect is a silent downgrade rather than a dangling reference.
    - Auto Attendants may be referenced by Call Queues (overflow destination) or other AAs (key-press routing). Check overflow settings on any CQ at the location.
    - Call Queues may be referenced by AAs as overflow targets.
    Run the relevant checks before executing any delete.

17. **Location-scoped deletes take LOCATION_ID as the FIRST argument** — `wxcli hunt-group delete --force LOCATION_ID HG_ID`, not `hunt-group delete --force HG_ID`. This applies to all location-scoped features: hunt-group, auto-attendant, call-queue, paging-group, call-park, call-pickup, location-voicemail, location-schedules. Exception in shape: `location-schedules delete` takes THREE arguments, `LOCATION_ID TYPE SCHEDULE_ID` (`wxcli location-schedules delete --force LOCATION_ID businessHours SCHEDULE_ID`); passing two fails `Missing argument 'schedule_id'`. Delete with `--force` verified live 2026-10-13 for hunt-group, call-queue, auto-attendant, paging-group, call-pickup, location-voicemail and location-schedules.
17. **Always use `--force` for programmatic deletes** — Without `--force`, delete commands prompt `[y/N]` which blocks non-interactive execution.
18. **Agent/member format differs by feature type.** Hunt Groups and Call Queues take `agents` as `[{"id": "person_id"}]` (array of objects). Call Pickups take `agents` as `["person_id"]` (plain string array). Paging Groups take `targets`/`originators` as plain string arrays. Call Parks take `agents` and `callParkExtensions` as plain string arrays. Using the wrong format returns 400 25024 "Invalid field value: agents" (re-verified live 2026-10-13 for pickup, paging and call park). **A call-pickup update that omits `agents` empties the group** -- always resend the full list. Always check `docs/reference/call-features-additional.md` if unsure.
19. **Call Parks and Call Pickups require location for listing.** `wxcli call-park list` and `wxcli call-pickup list` without a location argument exit 1 with `Error: Missing argument 'location_id'.` (verified live 2026-10-13). Must pass `LOCATION_ID` as first positional arg: `wxcli call-park list LOCATION_ID -o json`.
20. **Cross-skill handoffs:**
    - CX Essentials configuration → `customer-assist` skill (screen pop, wrap-up, recording, supervisors)
    - Person/workspace call settings → `manage-call-settings` skill (voicemail, forwarding, DND, etc.)
    - Routing (trunks, dial plans, PSTN) → `configure-routing` skill
    - Device provisioning → `manage-devices` skill
    - Location teardown → `provision-calling` skill (Operation D: Teardown)
21. **`location-call-handling` verbs lie — never infer meaning from the command name.** `show`/`update` are internal dialing; `list` returns outgoing permissions (a settings object, not a list); `create` makes an access code; `update-access-codes` **deletes** codes; `delete-access-codes-all` wipes **all** access codes. Re-read the trap table in the Location Call Handling section before running any of them.
22. **Three commands in `location-call-handling` delete everything at a location** — `delete-access-codes-all` (all access codes), `delete-digit-patterns-outgoing-permission` (all digit patterns), and enabling `update-intercept` (overrides all call handling). The single-item digit pattern delete is the `-1` suffixed variant. Confirm scope with the user first.
23. **`announcements show` is repository usage, not announcement details.** Use `show-announcements-config ANN_ID` (org) or `show-announcements-locations LOC_ID ANN_ID` (location).
24. **Announcements are scoped org-level OR location-level, with different commands for each.** Location-level commands are the `*-announcements`/`*-announcements-locations` variants and take `LOCATION_ID` first. Passing a location announcement ID to an org command returns 404.
25. **Check references before deleting an announcement or playlist.** `wxcli announcements show-announcements-config ANN_ID -o json` returns `featureReferenceCount` and `playlists`; `wxcli cq-playlists list PLAYLIST_ID -o json` shows which queues/locations use a playlist. Verified live 2026-10-13: an announcement inside a playlist cannot be deleted (`400 6575`), so it is not silently broken; AA/CQ greeting references were not tested.
26. **Playlist location assignment is a full replace.** `announcement-playlists update-playlists` overwrites the whole list — read `list-playlists PLAYLIST_ID` first and re-include every location you want to keep.
27. **`caller-reputation` is org-level and uses `--organization-id`**, not the standard orgId injection. Score thresholds are **strings** — quote them (`--call-block-score-threshold "80"`).
28. **`external-voicemail create` and `create-mwi` require a Service App token** with `spark-admin:calls_write`. Neither has a read-back command. (Observed 2026-10-13: with the admin PAT, `create --id <person> --action CLEAR` was NOT rejected as 401/403 — it reached business validation and failed `112130 "External MWI Control not allowed for user with an internal mailbox"`. So "PATs fail" is not confirmed for the auth layer; a success case could not be produced because every user in the sandbox has an internal mailbox.) **Unverified** for `create-mwi`: the Service App requirement is the spec's own text for that endpoint, not observed.
29. **Announcement `create` takes a `cmf://` media-service URI, not a local path or an open-web URL.** `--file-uri`, `--file-name`, `--name`, and the `--is-text-to-speech`/`--no-is-text-to-speech` flag are all required. Public https URLs fail `400 27917` (verified live 2026-10-13); use the `fileUri` that `tts-status` returns.
30. **The TTS flow is live-verified (2026-10-13).** `tts-generate` → `{"id"}` → `tts-status` → `fileUri` → `announcements create`. `--language-code` is lower-case (`en_us`).
31. **`location-call-handling update-access-codes` needs `--force`** (it is a delete under a misleading name); without it, non-interactive runs print `Aborted!` and delete nothing. Enabling the internal-dialing unknown-extension policy alone (`update --enable-unknown-extension-route-policy`) fails `400 27344` until a route target is in the body (no route group/trunk existed to test the target form). `update-auto-transfer-numbers` stores numbers normalised (`+1-5551234567`); `{"autoTransferNumber1":""}` clears one (verified live 2026-10-13). `location-call-handling list` returns a JSON **array** of per-call-type entries, not a single object.
32. **Delete order and gaps verified live 2026-10-13.** `location-schedules delete` takes `LOCATION_ID TYPE SCHEDULE_ID` (`businessHours`|`holidays` is the second argument). Deleting a hunt group still named in a call park's recall succeeded and the park's recall reset itself to `ALERT_PARKING_USER_ONLY`. Deleting an AI Receptionist knowledge base that still held a document succeeded (the document went with it); the receptionist-first ordering could not be tested because the org lacks the `callingAiReceptionist` entitlement (`403 BIFROST-B10005` on `ai-receptionist create`; the CLI tip wrongly blamed the token — since 2026-10-13 it keys on `BIFROST-B10005` and says the org is usually not entitled to the service; unit-tested, not re-run live).

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
