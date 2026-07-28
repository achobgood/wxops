---
name: manage-call-settings
description: |
  Configure person-level and workspace-level call settings in Webex Calling.
  Covers 39+ settings organized into categories: call handling, voicemail & media,
  permissions, and behavior & devices. Includes phone number add/remove/reassign,
  executive-assistant delegation, hoteling, shared line appearance, simultaneous ring,
  sequential ring, single number reach, receptionist client, and workspace hoteling.
  Also covers virtual line settings (65+ commands), person monitoring/BLF, hot desking
  members, operating mode management (admin assignment + user switching), MS Teams
  client settings (org and per-person), outbound billing plans, and guest issuer tokens.
  Use when the user wants to read, change, or audit call settings for one or more
  users/workspaces/virtual lines.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [person-email-or-workspace-name]
---

<!-- Updated by playbook session 2026-04-23 -->

# Manage Call Settings Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What are the two path families for person call settings, and which is newer? (Answer: `/people/{id}/features/{feature}` is classic; `/telephony/config/people/{id}/{feature}` is newer. Some setting names differ between them.)
2. What happens when you use `/telephony/config/workspaces/{id}/` settings on a Basic-licensed workspace? (Answer: 405 "Invalid Professional Place" — only `musicOnHold` and `doNotDisturb` work on Basic. Use `/workspaces/{id}/features/` path for Basic workspaces.)
3. What wxcli command group handles org/location call recording? (Answer: `call-recording`, NOT `location-settings`. Run `wxcli call-recording --help` to confirm.)

If you cannot answer all three, you skipped reading this skill. Go back and read it.

**MANDATORY: Before including ANY wxcli command in your plan, verify it exists.** Run `wxcli <group> --help` to confirm the command group exists and list its commands. If you cannot run `--help` (e.g., plan-only mode), use ONLY commands listed in the Quick Recipes section below. Do NOT construct command names from reference doc titles or API concepts — the CLI group names often differ from the API concept names (e.g., location recording config uses `wxcli call-recording`, NOT `wxcli location-settings`).

## Quick Recipes — Use These Exact Commands

**These are the authoritative command names. Use them exactly as shown. Do NOT construct command names from reference doc terminology.**

### Recording setup (3-level prerequisite chain)
```bash
wxcli call-recording show -o json                          # 1. Org-level recording vendor
wxcli call-recording list-vendors LOCATION_ID -o json       # 2. Per-location vendor assignment
wxcli user-settings show-call-recording PERSON_ID -o json  # 3. Person recording
wxcli user-settings update-call-recording PERSON_ID --json-body '{"enabled": true, "record": "Always"}'
```

### Voicemail transcription (location-scoped — affects ALL users at location)
```bash
wxcli location-voicemail show LOCATION_ID -o json          # Location voicemail policy
wxcli location-voicemail update LOCATION_ID --json-body '{"voiceMessageTranscriptionEnabled": true}'
wxcli user-settings update-voicemail PERSON_ID --json-body '{"enabled": true, "emailCopyOfMessage": {"enabled": true, "emailId": "user@example.com"}}'
```

### Voicemail self-service (user-level OAuth — Phase 5)
```bash
wxcli call-settings-for-me-phase-5 show -o json            # Show own voicemail settings
wxcli call-settings-for-me-phase-5 update --json-body '{"enabled": true, "sendUnansweredCalls": {"enabled": true, "numberOfRings": 6}}'
wxcli call-settings-for-me-phase-5 show-rules -o json      # Show voicemail PIN rules
wxcli call-settings-for-me-phase-5 update-pin --json-body '{"pin": "123456"}'  # Reset/change voicemail PIN
```
- Requires **user-level OAuth** token (`spark:people_read` / `spark:people_write`). Admin tokens will not work.
- These are `/people/me/` endpoints — the authenticated user configures their own settings.

### Hoteling self-service (user-level OAuth — Phase 5)
```bash
wxcli call-settings-for-me-phase-5 show-guest -o json      # Show own hoteling guest settings
wxcli call-settings-for-me-phase-5 update-guest --json-body '{"enabled": true}'  # Enable self as hoteling guest
wxcli call-settings-for-me-phase-5 list -o json            # List available hoteling hosts
```
- Requires **user-level OAuth** token. Admin tokens will not work.
- The admin path for hoteling guest is `wxcli user-settings update-hoteling PERSON_ID`. Use the self-service path when the user is configuring their own hoteling.

### Call forwarding (PUT replaces entire object — read first, carry ALL blocks)
```bash
wxcli user-settings show-call-forwarding PERSON_ID -o json
wxcli user-settings update-call-forwarding PERSON_ID --json-body '{
  "always": {"enabled": false},
  "busy": {"enabled": true, "destination": "+15551234567", "destinationVoicemailEnabled": false},
  "noAnswer": {"enabled": false, "numberOfRings": 3},
  "businessContinuity": {"enabled": false}
}'
```
Note: 4 blocks (always, busy, noAnswer, businessContinuity). selectiveForward is a SEPARATE API.

### Workspace hoteling
```bash
wxcli device-settings update-devices-workspaces WORKSPACE_ID --enabled  # Enable workspace hoteling host
wxcli user-settings update-hoteling PERSON_ID --json-body '{"enabled": true}'  # Person hoteling guest (simple toggle)
```
- Workspace hoteling host requires **Professional** workspace license (Basic returns 405).
- Supports `--limit-guest-use` + `--guest-hours-limit N` for time-limited guest sessions.
- Guest users must ALSO have person-level hoteling enabled (`user-settings update-hoteling`) to sign in.

### Receptionist client
```bash
wxcli user-settings list-reception PERSON_ID -o json
wxcli user-settings update-reception PERSON_ID --json-body '{"receptionEnabled": true, "monitoredMembers": ["ID1", "ID2"]}'
```
- API path is `/features/reception` (NOT `/features/receptionist`). Person-level only — no workspace equivalent.
- `receptionEnabled` must be `true` if `monitoredMembers` is non-empty.
- Max 50 monitored members. Members can be person or workspace IDs.

### SimRing for persons (admin-configurable)
```bash
wxcli user-settings list-simultaneous-ring PERSON_ID -o json
wxcli user-settings update-simultaneous-ring PERSON_ID --enabled --json-body '{"enabled":true,"phoneNumbers":[{"phoneNumber":"+15551234567"}]}'
wxcli user-settings create-criteria-simultaneous-ring PERSON_ID --json-body '{"name":"After hours","phoneNumbers":["+15551234567"]}'
wxcli user-settings show-criteria-simultaneous-ring PERSON_ID ID -o json
wxcli user-settings update-criteria-simultaneous-ring PERSON_ID ID --json-body '{"enabled":true}'
wxcli user-settings delete-criteria-simultaneous-ring PERSON_ID ID
```
- Person SimRing now has an admin path via `user-settings` — `list-simultaneous-ring` / `update-simultaneous-ring` configure the base setting (enabled, do-not-ring-if-on-call, numbers); the `criteria-simultaneous-ring` commands manage schedule-based ring criteria.
- **Workspace SimRing is also admin-configurable:** `wxcli workspace-settings list-simultaneous-ring WORKSPACE_ID` and `update-simultaneous-ring` exist. Use those for workspaces instead of the `user-settings` commands.
- SNR (`single-number-reach`) remains a valid alternative for the desk + mobile ring-simultaneously use case, but it is no longer the only admin-configurable option for person SimRing:
```bash
wxcli single-number-reach list-single-number-reach PERSON_ID -o json
wxcli single-number-reach create PERSON_ID --phone-number "+15551234567" --enabled --name "Mobile"
```

### Executive-assistant pairing (3-step process)
```bash
# Step 1: Assign roles
wxcli user-settings update-executive-assistant EXEC_ID --json-body '{"type": "EXECUTIVE"}'
wxcli user-settings update-executive-assistant ASST_ID --json-body '{"type": "EXECUTIVE_ASSISTANT"}'
# Step 2: Link the assistant to the executive
wxcli user-settings update-assigned-assistants EXEC_ID --json-body '{"assistantIds": ["ASST_ID"]}'
# Step 3: Verify both sides
wxcli user-settings show-executive-assistant EXEC_ID -o json
wxcli user-settings list-assigned-assistants EXEC_ID -o json
```
- Both users require **Professional** Calling license (Basic does not support exec-asst).
- Type assignment uses `people_write` scope; assigned-assistants linkage uses `telephony_config_write` scope.
- Rollback: set both to `--type UNASSIGNED` (auto-unlinks).

### Virtual line settings (65+ commands — `virtual-line-settings`)

Virtual lines are person-like calling identities with no user account (shared/fax/hotline lines). They have their **own** command group that mirrors most `user-settings` features. **Do NOT use `user-settings` commands on a virtual line ID.**

**Always discover first — do not guess a command name:**
```bash
wxcli virtual-line-settings --help          # 65+ commands, grouped by theme below
```

| Theme | Representative commands |
|-------|------------------------|
| Lifecycle | `list`, `create`, `show-virtual-lines`, `update-virtual-lines`, `delete` |
| Call handling | `show-call-forwarding`/`update-call-forwarding`, `show-call-waiting`/`update-call-waiting`, `show-do-not-disturb`/`update-do-not-disturb`, `show-intercept`/`update-intercept` |
| Voicemail | `show-voicemail`/`update-voicemail`, `configure-busy-voicemail`, `configure-no-answer`, `reset-voicemail-pin`, `update-passcode` |
| Permissions | `show-incoming-permission`/`update-incoming-permission`, `list-outgoing-permission`/`update-outgoing-permission`, `*-access-codes`, `*-auto-transfer-numbers`, `*-digit-patterns*` |
| Media & privacy | `show-music-on-hold`/`update-music-on-hold`, `list-privacy`/`update-privacy`, `show-barge-in`/`update-barge-in`, `list-push-to-talk`/`update-push-to-talk`, `show-call-bridge`/`update-call-bridge` |
| Caller ID | `list-caller-id`/`update-caller-id-virtual-lines`, `show-caller-id`/`update-caller-id-agent`, `list-available-caller-ids` |
| Devices & numbers | `show-number`, `list-devices`, `list-dect-networks`, `update-directory-search`, `list-available-numbers-*` |
| Billing | `list-outbound-billing-plan`/`update-outbound-billing-plan` |

```bash
wxcli virtual-line-settings list --location-id LOCATION_ID -o json      # find virtual lines
wxcli virtual-line-settings show-virtual-lines VIRTUAL_LINE_ID -o json  # detail (NOT `show`)
wxcli virtual-line-settings create --first-name "Front" --last-name "Desk" --location-id LOCATION_ID --extension 1000
wxcli virtual-line-settings show-call-forwarding VIRTUAL_LINE_ID -o json
wxcli virtual-line-settings update-do-not-disturb VIRTUAL_LINE_ID --enabled --ring-splash-enabled
```
- **Bare-name trap:** `show` / `update` are **Call Recording**, NOT the virtual line detail. Detail is `show-virtual-lines` / `update-virtual-lines`.
- `create` requires `--first-name`, `--last-name`, `--location-id`.
- `delete` prompts for confirmation; pass `--force` to skip.

### Person monitoring / BLF (`person-call-settings` — bare `list`/`update`)

The `person-call-settings` group does **ONLY monitoring** (`/people/{id}/features/monitoring`), which is why its commands are bare-named. **It is the ONLY CLI path to read or write person monitoring** — there is no `user-settings list-monitoring` / `update-monitoring` (verified: those names do not exist).

```bash
wxcli person-call-settings list PERSON_ID -o json                              # read monitoring
wxcli person-call-settings update PERSON_ID --json-body '{"enableCallParkNotification": true, "monitoredElements": ["ID1", "ID2"]}'
wxcli person-call-settings update PERSON_ID --enable-call-park-notification    # flag form

# Helpers live in user-settings (search candidates BEFORE writing the list above)
wxcli user-settings list-available-members-monitoring PERSON_ID -o json
wxcli user-settings list-available-members-speed-dials PERSON_ID -o json
```
- **Do NOT read the bare names as "all person call settings."** `wxcli person-call-settings list` returns monitoring only.
- **Do NOT claim "no CLI exists for person monitoring"** — it exists, under this non-obvious group name. Equally, do not reach for `user-settings list-monitoring`; it is not a real command.
- The read/write pair and the available-member helpers are split across **two different groups** — that split is the reason this feature is easy to miss.
- `update` is a PUT — `monitoredElements` replaces the whole list. Max 50 elements (people, places, call park extensions).

### Hot desking members (person-level line assignment)

Assigns which member lines appear on a person's hot desking device (`/telephony/config/people/{id}/features/hotDesking/members`). This is **separate** from the hoteling guest toggle (`user-settings update-hoteling`) and from workspace hot desking (`device-settings`).

**Two groups hit the identical endpoint — they are aliases. Prefer `user-settings` (clearer names):**

| Endpoint | `user-settings` (preferred) | `hot-desking-members` (alias) |
|----------|----------------------------|------------------------------|
| `.../hotDesking/members` (GET) | `list-members-hot-desking` | `list-members` |
| `.../hotDesking/members` (PUT) | `update-members-hot-desking` | `update` |
| `.../hotDesking/availableMembers` (GET) | `list-available-members-hot-desking` | `list` |

```bash
wxcli user-settings list-available-members-hot-desking PERSON_ID --location-id LOCATION_ID -o json
wxcli user-settings list-members-hot-desking PERSON_ID -o json
wxcli user-settings update-members-hot-desking PERSON_ID --json-body '{"members":[{"id":"MEMBER_ID","port":1,"primaryOwner":"false","lineType":"SHARED_CALL_APPEARANCE","lineWeight":1}]}'
```
- **Bare-name trap:** `hot-desking-members list` is **search available members**, NOT the assigned list. Assigned list is `list-members`.
- `update` is a PUT — read the current members first and send the complete list.
- Search filters on the available-members command: `--location-id`, `--member-name`, `--phone-number`, `--extension`, `--order`.

### Mode management (admin assigns; user switches)

Operating modes (e.g. holiday/after-hours override on an AA or hunt group) are split across **two groups with two different token types**. Getting this wrong is the #1 mode-management failure.

| Step | Who | Command group | Token |
|------|-----|--------------|-------|
| Assign which features a user may mode-manage | Admin | `user-settings *-mode-management` | Admin token |
| Actually switch/extend the mode | The user | `mode-management` | **User-level OAuth only** |

```bash
# ADMIN side — /telephony/config/people/{id}/modeManagement/... (admin token works)
wxcli user-settings list-available-features PERSON_ID -o json   # mode-manageable features (NOT a generic feature list)
wxcli user-settings list-mode-management PERSON_ID -o json      # features currently assigned
wxcli user-settings update-mode-management PERSON_ID --json-body '{"featureIds":["FEATURE_ID"]}'

# USER side — /telephony/config/people/me/settings/modeManagement/... (user OAuth ONLY)
wxcli mode-management list -o json                              # features the signed-in user can manage
wxcli mode-management show FEATURE_ID -o json
wxcli mode-management list-common-modes --feature-ids "ID1,ID2" -o json
wxcli mode-management switch-mode-for-invoke-1 FEATURE_ID --operating-mode-id MODE_ID --is-manual-switchback-enabled true
wxcli mode-management switch-mode-for-invoke --operating-mode-name "Holiday"   # multiple features at once
wxcli mode-management switch-to-normal FEATURE_ID
wxcli mode-management extend-current-operating FEATURE_ID --operating-mode-id MODE_ID --extension-time 30
```
- **Every `mode-management` command is a `/people/me/` endpoint → admin tokens get 404 (error 4008).** This is Known Issue #3: this group is the *user's own* self-service view and needs user-level OAuth.
- **An admin CAN switch a feature's mode — just not through this group.** Use the per-feature admin commands, which are location-scoped (`POST /telephony/config/locations/{locationId}/<feature>/{id}/callForwarding/actions/switchMode/invoke`): `auto-attendant switch-mode-for`, `call-queue switch-mode-for`, `hunt-group switch-mode-for`. Those live in the `configure-features` skill. Do not conclude from this group's 404 that mode switching has no admin path — it does.
- `--extension-time` must be a multiple of 30 (minutes).
- **Bare-name trap:** `user-settings list-available-features` is mode-management-specific (`modeManagement/availableFeatures`), not a general feature list.
- The location/feature side of operating modes (creating the modes themselves) lives in the `configure-features` skill under `operating-modes`.

### MS Teams settings (org-level vs person-level)

Two groups, two scopes, **different allowed setting names** — verified via `--help`:

```bash
# ORG-wide — /telephony/config/settings/msTeams — supports HIDE_WEBEX_APP *and* PRESENCE_SYNC
wxcli client-settings list -o json
wxcli client-settings update --setting-name HIDE_WEBEX_APP --value
wxcli client-settings update --setting-name PRESENCE_SYNC --no-value

# PERSON — /telephony/config/people/{id}/settings/msTeams — HIDE_WEBEX_APP ONLY
wxcli user-settings list-ms-teams PERSON_ID -o json
wxcli user-settings update-ms-teams PERSON_ID --setting-name HIDE_WEBEX_APP --value
```
- `PRESENCE_SYNC` is **org-level only** — `user-settings update-ms-teams` accepts only `HIDE_WEBEX_APP`. Asking for per-person presence sync is not possible; set it org-wide.
- `client-settings` has no person/workspace argument — it is org-scoped and affects everyone.

### Outbound billing plan (person / workspace / virtual line)

Same setting at three scopes, `/outboundBillingPlan` on each:
```bash
wxcli user-settings list-outbound-billing-plan PERSON_ID -o json
wxcli user-settings update-outbound-billing-plan PERSON_ID --json-body '{...}'
wxcli workspace-settings list-outbound-billing-plan WORKSPACE_ID -o json
wxcli virtual-line-settings list-outbound-billing-plan VIRTUAL_LINE_ID -o json
```
- All three `update-outbound-billing-plan` commands are **`--json-body` only** — no field flags are generated. Read the current plan first and send the modified object back.

### Guest calling tokens (`guest-management`) — read this before using it

`guest-management` is the **Webex Guest Issuer API** (`/v1/guests/token`, `/v1/guests/count`), NOT a per-person call setting. It mints guest identities for guest calling/SDK embedding.

```bash
wxcli guest-management list -o json                                        # guest count for the org
wxcli guest-management create --subject "ext-user-42" --display-name "Jane Guest"
```
- Requires a **Guest Issuer application** (JWT-signed credentials), not a normal admin token. A standard admin/PAT will not mint guest tokens.
- `create` outputs the guest token id by default; use `-o json` for the full token payload. Treat the output as a **credential** — do not echo it into logs or reports.
- **Do NOT confuse with `guestCalling`**, the person setting in Known Issue #4 — that one is user-only (`my-call-settings`) and unrelated to this group.

### Command group mapping (do NOT guess — use this table)
| Setting domain | wxcli group | NOT this group |
|---------------|-------------|----------------|
| Org call recording | `call-recording` | ~~location-settings~~ |
| Location voicemail | `location-voicemail` | ~~location-settings~~ |
| Person settings | `user-settings` | — |
| Workspace settings | `workspace-settings` | — |
| Workspace hoteling | `device-settings` | ~~workspace-settings~~ |
| Self-service voicemail/hoteling (Phase 5) | `call-settings-for-me-phase-5` | ~~my-call-settings~~ |
| **Virtual line settings** (any setting on a virtual line) | `virtual-line-settings` | ~~user-settings~~ |
| **Person monitoring / BLF** | `person-call-settings` (read/write) + `user-settings list-available-members-monitoring` (candidates) | ~~`user-settings list-monitoring`~~ (does not exist) |
| **Person hot desking members** | `user-settings *-hot-desking` (or alias `hot-desking-members`) | ~~device-settings~~ (that's workspace hot desking) |
| **Mode switching (user)** | `mode-management` — user OAuth only | ~~user-settings~~ |
| **Mode feature assignment (admin)** | `user-settings *-mode-management` | ~~mode-management~~ |
| **MS Teams — org-wide** | `client-settings` | ~~user-settings~~ |
| **MS Teams — per person** | `user-settings *-ms-teams` | ~~client-settings~~ |
| **Guest issuer tokens** | `guest-management` (Guest Issuer app required) | ~~user-settings~~ |

---

## Step 1: Load references (only what you need)

Load ONLY the reference docs relevant to the user's specific request. Do NOT load all 4 by default.

| If the request involves... | Load this doc |
|---------------------------|---------------|
| Forwarding, DND, call waiting, sim ring, SNR | `docs/reference/person-call-settings-handling.md` |
| Voicemail, caller ID, recording, intercept, monitoring | `docs/reference/person-call-settings-media.md` |
| Permissions, executive/assistant, feature access | `docs/reference/person-call-settings-permissions.md` |
| Hoteling, receptionist, calling behavior, numbers | `docs/reference/person-call-settings-behavior.md` |
| Self-service settings (user-level OAuth) | `docs/reference/self-service-call-settings.md` |

**For recording + voicemail scenarios:** Load `person-call-settings-media.md` only. The location-level recording commands are in the Quick Recipes above — you do NOT need to load any location-settings docs.

## Step 2: Verify auth token

Before any API calls, confirm the user's auth token is working:

```bash
wxcli whoami
```

Check the token has the required scopes for the target operation.

### Required Scopes by Operation Type

| Scope | Grants |
|-------|--------|
| `spark-admin:people_read` | Read any person's call settings (admin) |
| `spark-admin:people_write` | Modify any person's call settings (admin) |
| `spark:people_read` | Read own call settings (self) |
| `spark:people_write` | Modify own call settings (self) |
| `spark-admin:telephony_config_read` | Read telephony config (SNR, MoH, App Services, ECBN, Numbers, Feature Access, Executive, etc.) |
| `spark-admin:telephony_config_write` | Modify telephony config |
| `spark-admin:workspaces_read` | Read workspace settings (outgoing permissions transfer numbers, access codes, call policy) |
| `spark-admin:workspaces_write` | Modify workspace settings |

### Which Settings Use Which Scopes

| `people_read/write` | `telephony_config_read/write` | `workspaces_read/write` |
|---------------------|-------------------------------|------------------------|
| Forwarding | Single Number Reach | Outgoing Permissions — Transfer Numbers |
| Call Waiting | Music on Hold | Outgoing Permissions — Access Codes |
| DND | Voicemail (passcode only) | Call Policy |
| Voicemail (main) | App Services (read) | |
| Caller ID | App Shared Line | |
| ~~Anon Call Rejection~~ *(user-only)* | Feature Access Controls | |
| Privacy | Executive Settings | |
| Barge-In | Numbers (update) | |
| Call Recording | Available Numbers | |
| Call Intercept | Preferred Answer | |
| Monitoring | MS Teams | |
| Push-to-Talk | Mode Management | |
| Incoming Permissions | Personal Assistant | |
| Outgoing Permissions (main) | ECBN | |
| Exec Assistant Type | Digit Patterns | |
| Calling Behavior | | |
| Call Bridge | | |
| Hoteling | | |
| Receptionist | | |
| Numbers (read) | | |

**Self-service scopes:** `call-settings-for-me-phase-5` commands use `spark:people_read` / `spark:people_write` (user-level, NOT admin). These are the same scopes as `my-call-settings`.

### Scope Verification Logic

1. Determine target type: **Person** needs `people_*` scopes; **Workspace** needs `workspaces_*` scopes
2. Determine operation: **Read** needs `*_read`; **Write** needs `*_write`
3. Check if the setting uses `telephony_config` scopes (see table above) — if so, verify those are present too
4. **Self-service commands** (`call-settings-for-me-phase-5`, `my-call-settings`): require user-level `spark:people_*` scopes, NOT admin scopes
5. If `wxcli whoami` does not show the required scopes, stop and tell the user which scopes are missing before proceeding

## Step 3: Identify the operation

Confirm with the user:

- **Target type:** Person or Workspace?
- **Target identifier:** Email address (person) or workspace name (workspace)?
- **Scope:** Single target, a list, or all users at a location?

### Look up a person

```bash
wxcli users list --email user@example.com --output json
```

Extract the `id` field from the JSON output to use as `PERSON_ID` in subsequent commands.

### Look up a workspace

```bash
wxcli workspaces list --output json
```

Filter by display name in the output. Extract the `id` field to use as `WORKSPACE_ID`.

### For bulk operations (all calling users)

```bash
# List all users, then filter for calling-enabled users (those with a locationId)
wxcli users list --output json
```

For small batches, use a shell loop. For large batches (50+ users), use the migration engine's async pattern which handles concurrency, rate limiting, and retry automatically.

### Settings Catalog

### Settings Scope Router

**Before attempting any settings command, determine the correct scope.** The same setting often exists at multiple levels with different command groups.

#### Quick router: "Who/what am I configuring?"

| Target | Command group | Scope prefix | Example |
|--------|--------------|-------------|---------|
| A specific **person** | `wxcli user-settings` | `spark-admin:people_read/write` | `wxcli user-settings show-voicemail PERSON_ID` |
| A specific **workspace** | `wxcli workspace-settings` | `spark-admin:workspaces_read/write` | `wxcli workspace-settings show-voicemail WORKSPACE_ID` |
| A specific **virtual line** | `wxcli virtual-line-settings` | `spark-admin:telephony_config_read/write` | `wxcli virtual-line-settings show-voicemail VIRTUAL_LINE_ID` |
| All people/workspaces at a **location** | `wxcli location-voicemail` / `wxcli location-settings` | `spark-admin:telephony_config_read/write` | `wxcli location-voicemail show LOCATION_ID` |
| **Org-wide** recording vendor | `wxcli call-recording` | `spark-admin:telephony_config_read/write` | `wxcli call-recording show` |
| **Self** (own settings) | `wxcli my-call-settings` or `wxcli call-settings-for-me-phase-5` | `spark:people_read/write` | `wxcli call-settings-for-me-phase-5 show` |

#### Multi-scope settings — which command for what?

| Setting | Person | Workspace | Location | Org | Self-Service |
|---------|--------|-----------|----------|-----|-------------|
| **Voicemail** | `user-settings show-voicemail PERSON_ID` | `workspace-settings show-voicemail WS_ID` | `location-voicemail show LOC_ID` (policies) | — | `call-settings-for-me-phase-5 show` |
| **Virtual line (any setting)** | — | — | — | — | Use `virtual-line-settings <cmd> VIRTUAL_LINE_ID` — its own group, mirrors most person settings |
| **Outbound Billing Plan** | `user-settings list-outbound-billing-plan PERSON_ID` | `workspace-settings list-outbound-billing-plan WS_ID` | — | — | — |
| **MS Teams** | `user-settings list-ms-teams PERSON_ID` (HIDE_WEBEX_APP only) | — | — | `client-settings list` (adds PRESENCE_SYNC) | — |
| **Mode Management** | `user-settings list-mode-management PERSON_ID` (assign) | — | — | — | `mode-management list` (switch — user OAuth only) |
| **Voicemail PIN** | `user-settings reset-voicemail-pin PERSON_ID` | — | — | — | `call-settings-for-me-phase-5 update-pin` |
| **Voicemail PIN Rules** | — | — | — | — | `call-settings-for-me-phase-5 show-rules` |
| **Call Recording** | `user-settings show-call-recording PERSON_ID` | `workspace-settings show-call-recordings WS_ID` | — | `call-recording show` (vendor config) | — |
| **Music on Hold** | SDK only (telephony_config) | SDK only | `location-settings` (must enable first) | — | — |
| **Call Intercept** | `user-settings show-intercept PERSON_ID` | `workspace-settings show-intercept WS_ID` | Location defaults apply | — | — |
| **Call Forwarding** | `user-settings show-call-forwarding PERSON_ID` | `workspace-settings show-call-forwarding WS_ID` | — | — | — |
| **Hoteling Guest** | `user-settings show-hoteling PERSON_ID` | — | — | — | `call-settings-for-me-phase-5 show-guest` |
| **Hoteling Hosts** | — | — | — | — | `call-settings-for-me-phase-5 list` |

#### User-only settings (no admin endpoint — 404 guaranteed)

These 5 settings exist ONLY at `/people/me/settings/{feature}`. Admin tokens **always** get 404. With a **user-level OAuth token**, use `wxcli my-call-settings` (120 commands covering all self-service `/people/me/` endpoints including these 5). Without user-level OAuth, the user must configure these via the Webex app.

**Simultaneous Ring is no longer in this table** — it now has an admin path via `user-settings list-simultaneous-ring` / `update-simultaneous-ring` (plus `*-criteria-simultaneous-ring` for schedule-based criteria). See the SimRing recipe above.

| Setting | Self-service path | CLI group | Workspace equivalent? |
|---------|-------------------|-----------|----------------------|
| Sequential Ring | `/me/settings/sequentialRing` | `my-call-settings` | No |
| Priority Alert | `/me/settings/priorityAlert` | `my-call-settings` | No |
| Call Notify | `/me/settings/callNotify` | `my-call-settings` | No |
| Anonymous Call Reject | `/me/settings/anonymousCallReject` | `my-call-settings` | **Yes:** `workspace-settings` has admin endpoint |
| Call Policies | `/me/settings/callPolicies` | `my-call-settings` | **Yes:** workspace-level admin endpoint (Professional license required) |

**Phase 5 self-service commands** (`call-settings-for-me-phase-5`): These are NOT user-only — they have admin-path equivalents (`user-settings show-voicemail`, `user-settings update-hoteling`, `user-settings reset-voicemail-pin`). The Phase 5 group provides the self-service path for users to manage their own voicemail and hoteling settings with a user-level token. Route to this group when the user is configuring their own settings rather than an admin configuring someone else's.

**If the user asks to configure one of these for a person:** Stop and explain that no admin API exists. Offer the workspace-level alternative if applicable, or inform them the user must self-configure.

Present the user with the settings categories. Ask which settings they want to read or change.

#### Category 1: Call Handling

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Call Forwarding | `show-call-forwarding` | `update-call-forwarding` | Always, Busy, No-Answer, Business Continuity |
| Call Waiting | `show-call-waiting` | `update-call-waiting` | Simple on/off toggle |
| Do Not Disturb | `show-do-not-disturb` | `update-do-not-disturb` | Includes ring splash, Webex Go override |
| Simultaneous Ring | `list-simultaneous-ring` | `update-simultaneous-ring` | Admin-configurable via `user-settings`; `*-criteria-simultaneous-ring` commands manage schedule-based criteria |
| Sequential Ring | — | — | **USER-ONLY: No admin endpoint. Requires user-level OAuth via `/me/settings/sequentialRing`** |
| Single Number Reach | `wxcli single-number-reach` group | `wxcli single-number-reach` group | Uses `telephony_config` scopes, not `people` scopes |
| Selective Accept | — | — | Criteria managed via separate CRUD methods (SDK only) |
| Selective Forward | — | — | Takes precedence over standard forwarding |
| Selective Reject | — | — | Highest priority of the selective features |
| Priority Alert | — | — | **USER-ONLY: No admin endpoint. Requires user-level OAuth via `/me/settings/priorityAlert`** |
| Call Notify | — | — | **USER-ONLY: No admin endpoint. Requires user-level OAuth via `/me/settings/callNotify`** |

#### Category 2: Voicemail & Media

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Voicemail | `show-voicemail` | `update-voicemail` | Inherits from location; greeting uploads via `configure-busy-voicemail`, `configure-no-answer` |
| Voicemail (self-service) | `call-settings-for-me-phase-5 show` | `call-settings-for-me-phase-5 update` | User-level OAuth only. User manages own voicemail settings |
| Voicemail PIN Rules | `call-settings-for-me-phase-5 show-rules` | — | User-level OAuth only. Read-only PIN policy |
| Voicemail PIN Reset | — | `call-settings-for-me-phase-5 update-pin` | User-level OAuth only. User resets own PIN |
| Caller ID | `list` | `update-caller-id-features` | |
| Anonymous Call Rejection | — | — | **USER-ONLY: No admin endpoint. Requires user-level OAuth via `/me/settings/anonymousCallReject`; workspace-level uses `workspaces/{id}/anonymousCallReject`** |
| Privacy | `list-privacy` | `update-privacy` | Controls line monitoring, AA extension/name dialing |
| Barge-In | `show-barge-in` | `update-barge-in` | Enables FAC-based barge-in across locations |
| Call Recording | `show-call-recording` | `update-call-recording` | **Read scope is `people_read` not `people_write` (SDK doc bug)**; inherits from location recording vendor config |
| Call Intercept | `show-intercept` | `update-intercept` | Takes phone out of service; greeting upload via `configure-call-intercept` |
| Monitoring | `person-call-settings list` | `person-call-settings update` | **NOT in `user-settings`** — `list-monitoring`/`update-monitoring` do not exist. Use the `person-call-settings` group (monitoring ONLY). Candidate lookup: `user-settings list-available-members-monitoring`. Max 50 elements |
| Push-to-Talk | `list-push-to-talk` | `update-push-to-talk` | One-way or two-way intercom; allow/block member lists |
| Music on Hold | — | — | **Requires location-level MoH enabled first**; uses `telephony_config` scopes (SDK only for now) |

#### Category 3: Permissions

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Incoming Permissions | `show-incoming-permission` | `update-incoming-permission` | External transfer, internal calls, collect calls |
| Outgoing Permissions | `list-outgoing-permission` | `update-outgoing-permission` | Per-call-type (local, toll, international, etc.) |
| Feature Access Controls | — | — | Controls what users can self-modify (SDK only for now) |
| Executive/Assistant | `show-executive-assistant` | `update-executive-assistant` | UNASSIGNED, EXECUTIVE, or EXECUTIVE_ASSISTANT |
| Call Policy | — | — | **USER-ONLY for persons (via `/me/settings/callPolicies`); workspace-only at admin level (`workspaces/{id}/features/callPolicies`, professional license required)** |

#### Category 4: Behavior & Devices

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Calling Behavior | `show-calling-behavior` | `update-calling-behavior` | Which Webex telephony app handles calls |
| App Services | `show` | `update` | Client platforms (browser, desktop, tablet, mobile) and ring behavior |
| Hoteling | `show-hoteling` | `update-hoteling` | Person-level only (admin path). **Workspace hoteling:** use `wxcli device-settings update-devices-workspaces WORKSPACE_ID --enabled` |
| Hoteling (self-service) | `call-settings-for-me-phase-5 show-guest` | `call-settings-for-me-phase-5 update-guest` | User-level OAuth only. User manages own hoteling guest settings |
| Available Hoteling Hosts | `call-settings-for-me-phase-5 list` | — | User-level OAuth only. Lists hosts the user can sign into |
| Receptionist Client | `list-reception` | `update-reception` | `receptionEnabled` must be `true` if members set. Path: `/features/reception` (NOT receptionist) |
| Numbers | `list-numbers` | — | Primary + alternate numbers; distinctive ring patterns |
| Preferred Answer Endpoint | — | — | Which device/app answers by default (SDK only for now) |
| MS Teams | `list-ms-teams` | `update-ms-teams` | Person-level accepts **HIDE_WEBEX_APP only**. For PRESENCE_SYNC use org-level `wxcli client-settings update` |
| Mode Management | `list-mode-management` | `update-mode-management` | Admin path assigns *which features* a user may mode-manage (`list-available-features` lists candidates). **Switching** a mode is user-OAuth-only via the `mode-management` group |
| Hot Desking Members | `list-members-hot-desking` | `update-members-hot-desking` | Member lines on the person's hot desk device. `list-available-members-hot-desking` searches candidates. Alias group: `hot-desking-members` |
| Outbound Billing Plan | `list-outbound-billing-plan` | `update-outbound-billing-plan` | `--json-body` only (no field flags). Also exists on `workspace-settings` and `virtual-line-settings` |
| Personal Assistant | — | — | Away status, transfer, alerting (SDK only for now) |
| Emergency Callback Number | — | — | DIRECT_LINE, LOCATION_ECBN, or LOCATION_MEMBER_NUMBER (SDK only for now) |

All CLI commands above are under `wxcli user-settings` unless otherwise noted. Run `wxcli user-settings --help` to see the full list. Self-service commands use `wxcli call-settings-for-me-phase-5` (run `wxcli call-settings-for-me-phase-5 --help` to see all 7 commands).

### Settings without CLI commands ("SDK only")

**6 USER-ONLY settings (no admin endpoint — require user-level OAuth token):**
SimRing, SequentialRing, PriorityAlert, CallNotify, AnonymousCallReject, CallPolicies (person-level).
These ONLY work at `/telephony/config/people/me/settings/{feature}` with a user token. Admin tokens get 404.

**MS Teams and Mode Management are NOT SDK-only** — both have verified CLI commands (`user-settings list-ms-teams`/`update-ms-teams`, `user-settings list-mode-management`/`update-mode-management`, plus org-level `client-settings` and user-level `mode-management`). See the Quick Recipes above. Virtual lines likewise have a full 65-command group (`virtual-line-settings`) — do not fall back to raw HTTP for them.

For settings still marked "SDK only" above (Music on Hold, Feature Access Controls, Preferred Answer, Personal Assistant, ECBN), use the raw HTTP fallback pattern with an **admin** token:

```bash
# Read the current setting value
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/telephony/config/people/{person_id}/{settingEndpoint}" | python3 -m json.tool

# Update via PUT (read-modify-write)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://webexapis.com/v1/telephony/config/people/{person_id}/{settingEndpoint}" \
  -d '{ ... }'
```

Consult `docs/reference/person-call-settings-handling.md` (SimRing, SeqRing, Priority Alert, Selective features) or `docs/reference/person-call-settings-behavior.md` (ECBN, Personal Assistant, Preferred Answer) for the exact endpoint paths, required fields, and gotchas for each setting. Those docs also cover Mode Management and MS Teams — read them for API background only; **use the CLI commands above, not raw HTTP, for those two.**

## Step 4: Check prerequisites

### 4a. Read current settings — always do this first

**CRITICAL: Always read the current value of any setting before proposing a change.** This prevents accidental overwrites and gives the user a clear before/after comparison.

#### Pattern for simple settings

```bash
# Call Waiting
wxcli user-settings show-call-waiting PERSON_ID --output json
```

#### Pattern for object settings

```bash
# Call Forwarding (always, busy, no-answer, business continuity)
wxcli user-settings show-call-forwarding PERSON_ID --output json
```

#### Pattern for settings with sub-components

```bash
# Voicemail (many nested fields)
wxcli user-settings show-voicemail PERSON_ID --output json

# DND (enabled + ring splash)
wxcli user-settings show-do-not-disturb PERSON_ID --output json
```

#### Reading multiple settings at once

For a full audit, read all relevant settings and review the JSON output:

```bash
# Read several settings for the same person
wxcli user-settings show-call-waiting PERSON_ID --output json
wxcli user-settings show-do-not-disturb PERSON_ID --output json
wxcli user-settings show-hoteling PERSON_ID --output json
wxcli user-settings show-call-forwarding PERSON_ID --output json
wxcli user-settings show-voicemail PERSON_ID --output json
wxcli user-settings show-caller-id PERSON_ID --output json
wxcli user-settings list-privacy PERSON_ID --output json
wxcli user-settings show-barge-in PERSON_ID --output json
```

#### Reading self-service settings (user-level OAuth)

```bash
# Read own voicemail settings
wxcli call-settings-for-me-phase-5 show --output json

# Read own hoteling guest settings
wxcli call-settings-for-me-phase-5 show-guest --output json

# Check voicemail PIN rules
wxcli call-settings-for-me-phase-5 show-rules --output json

# List available hoteling hosts
wxcli call-settings-for-me-phase-5 list --output json
```

### 4b. Check for location-level dependencies

Use the exact commands from the Quick Recipes section. Key prerequisites:

| Setting | Verify command | Fix command |
|---------|----------------|-------------|
| Call Recording (org) | `wxcli call-recording show -o json` | `wxcli call-recording update --json-body '{...}'` |
| Call Recording (location vendor) | `wxcli call-recording list-vendors -o json` | `wxcli call-recording update-vendor-call-recording LOC_ID --json-body '{...}'` |
| Voicemail transcription | `wxcli location-voicemail show LOC_ID -o json` | `wxcli location-voicemail update LOC_ID --json-body '{...}'` |
| Music on Hold | No wxcli command — use Control Hub or SDK | — |

**Do NOT use `location-settings` for recording or voicemail.** That group handles dial patterns only.

### 4c. Verify scope coverage

Cross-reference the settings the user wants to change against the scopes table in Step 2. If any required scopes are missing from the token, stop and inform the user before building the plan.

## Step 5: Build and present deployment plan -- [SHOW BEFORE EXECUTING]

**CRITICAL: Always show the plan and get user confirmation before making changes.**

Format the plan as a table:

```
## Deployment Plan for: Jane Smith (jane@company.com)

| Setting | Current Value | New Value | Impact |
|---------|--------------|-----------|--------|
| Call Forwarding (Always) | Disabled | Enabled -> +12025551234 | All calls forwarded |
| DND | Disabled | Enabled (ring splash: on) | All callers get busy |
| Voicemail (rings) | 3 | 6 | More time before VM |

Affected scopes required: spark-admin:people_write

Proceed? (y/n)
```

## Step 6: Execute via wxcli — `[After user confirms plan]`

### 6a. Execute individual changes

#### Pattern: Simple toggle

```bash
# Enable Call Waiting
wxcli user-settings update-call-waiting PERSON_ID --json-body '{"enabled": true}'
```

#### Pattern: Object-based settings

```bash
# Enable DND with ring splash
wxcli user-settings update-do-not-disturb PERSON_ID --json-body '{"enabled": true, "ringSplashEnabled": true}'
```

#### Pattern: Complex nested settings (read first, modify fields, write back)

```bash
# 1. Read current forwarding — capture ALL 4 blocks
wxcli user-settings show-call-forwarding PERSON_ID --output json
# 2. PUT replaces entire object — include ALL blocks, modify only target
wxcli user-settings update-call-forwarding PERSON_ID --json-body '{
  "always": {"enabled": false},
  "busy": {"enabled": true, "destination": "+15551234567", "destinationVoicemailEnabled": false},
  "noAnswer": {"enabled": false, "numberOfRings": 3},
  "businessContinuity": {"enabled": false}
}'
```
Forwarding has 4 blocks: always, busy, noAnswer, businessContinuity. selectiveForward is a SEPARATE API.

#### Pattern: Voicemail configuration

```bash
# Update voicemail settings
wxcli user-settings update-voicemail PERSON_ID --json-body '{
  "enabled": true,
  "sendUnansweredCalls": {
    "enabled": true,
    "numberOfRings": 6
  }
}'

# Upload voicemail greetings (json-body only — no --file flag)
wxcli user-settings configure-busy-voicemail PERSON_ID --json-body '{"type": "CUSTOM", ...}'
wxcli user-settings configure-no-answer PERSON_ID --json-body '{"type": "CUSTOM", ...}'
```

#### Pattern: Call intercept (take phone out of service)

```bash
# Enable call intercept
wxcli user-settings update-intercept PERSON_ID --json-body '{
  "enabled": true,
  "incoming": {
    "type": "INTERCEPT_ALL"
  }
}'

# Upload intercept greeting (json-body only — no --file flag)
wxcli user-settings configure-call-intercept PERSON_ID --json-body '{"type": "CUSTOM", ...}'
```

#### Pattern: Permissions

```bash
# Update incoming permissions
wxcli user-settings update-incoming-permission PERSON_ID --json-body '{
  "externalTransfer": "ALLOW_ALL_EXTERNAL",
  "internalCallsEnabled": true,
  "collectCallsEnabled": false
}'

# Update outgoing permissions
wxcli user-settings update-outgoing-permission PERSON_ID --json-body '{
  "callingPermissions": [
    {"callType": "INTERNATIONAL", "action": "BLOCK"}
  ]
}'
```

#### Pattern: Executive/Assistant pairing

```bash
# Assign executive role
wxcli user-settings update-executive-assistant EXEC_PERSON_ID --json-body '{"type": "EXECUTIVE"}'

# Assign assistant role
wxcli user-settings update-executive-assistant ASST_PERSON_ID --json-body '{"type": "EXECUTIVE_ASSISTANT"}'
```

#### Pattern: Workspace settings

Workspace settings mirror person settings but use the workspace-settings command group. Check available commands:

```bash
wxcli workspace-settings --help
```

#### Pattern: Schedules

Person-level schedules have full CRUD support:

```bash
# List schedules
wxcli user-settings list-schedules PERSON_ID --output json

# Create a schedule
wxcli user-settings create PERSON_ID --json-body '{
  "name": "Business Hours",
  "type": "businessHours",
  "events": []
}'

# Add an event to a schedule
wxcli user-settings create-events PERSON_ID SCHEDULE_TYPE SCHEDULE_ID --json-body '{
  "name": "Weekdays",
  "startDate": "2026-01-01",
  "endDate": "2026-12-31",
  "startTime": "09:00",
  "endTime": "17:00",
  "recurrence": {"recurWeekly": {"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true}}
}'

# Show schedule detail
wxcli user-settings show-schedules PERSON_ID SCHEDULE_TYPE SCHEDULE_ID --output json

# Delete a schedule event (requires 4 positional args)
wxcli user-settings delete-events PERSON_ID SCHEDULE_TYPE SCHEDULE_ID EVENT_ID
```

#### Pattern: Reset voicemail PIN

```bash
wxcli user-settings reset-voicemail-pin PERSON_ID
```

#### Pattern: Self-service voicemail and hoteling (user-level OAuth)

```bash
# User updates own voicemail settings
wxcli call-settings-for-me-phase-5 update --json-body '{"enabled": true, "sendUnansweredCalls": {"enabled": true, "numberOfRings": 6}}'

# User resets own voicemail PIN
wxcli call-settings-for-me-phase-5 update-pin --json-body '{"pin": "123456"}'

# User enables self as hoteling guest
wxcli call-settings-for-me-phase-5 update-guest --json-body '{"enabled": true}'
```

### 6b. Bulk changes

#### Shell loop for small batches

```bash
# Disable call waiting for a list of users
for ID in PERSON_ID_1 PERSON_ID_2 PERSON_ID_3; do
  wxcli user-settings update-call-waiting "$ID" --json-body '{"enabled": false}'
done
```

#### Bulk operations for large batches (50+ users)

For large batches, use shell loops with sleep for rate limiting, or reference the migration engine's async pattern for maximum throughput with concurrency control.

```bash
# Example: disable call waiting for all users via shell loop
for USER_ID in $(wxcli people list --calling-data --output json | python3 -c "
import sys, json
for u in json.load(sys.stdin).get('items', []):
    if u.get('locationId'): print(u['id'])
"); do
    wxcli user-settings update-call-waiting "$USER_ID" --no-enabled
    sleep 1
    ])
```

## Step 7: Verify — `[Read back after every update]`

Always read back the setting after writing to confirm the change took effect:

```bash
# After updating call waiting
wxcli user-settings show-call-waiting PERSON_ID --output json

# After updating forwarding
wxcli user-settings show-call-forwarding PERSON_ID --output json

# After updating voicemail
wxcli user-settings show-voicemail PERSON_ID --output json

# After self-service voicemail update
wxcli call-settings-for-me-phase-5 show --output json

# After self-service hoteling update
wxcli call-settings-for-me-phase-5 show-guest --output json
```

Compare the JSON output to the values you set. Flag any discrepancies.

## Step 8: Report results

Summarize what was changed:

```
## Results for: Jane Smith (jane@company.com)

| Setting | Before | After | Status |
|---------|--------|-------|--------|
| Call Forwarding (Always) | Disabled | Enabled -> +12025551234 | Confirmed |
| DND | Disabled | Enabled (ring splash: on) | Confirmed |
| Voicemail (rings) | 3 | 6 | Confirmed |

All 3 changes applied successfully.
```

---

## Critical Rules

- **Always read before writing** — never update a setting without first reading its current value via `wxcli user-settings show-*`
- **Always show plan before executing** — present the deployment plan (Step 5) and get user confirmation
- **Handle person vs workspace scope differences** — some scopes use `workspaces_read/write` instead of `people_read/write` (outgoing permissions transfer numbers, access codes, call policy)
- **Location-level prerequisites** — voicemail, recording, intercept, and MoH have location-level settings that must be configured first; person-level settings may be overridden or ineffective without them
- **SimRing, SequentialRing, PriorityAlert admin limitation** — these are not available via admin-level person management; use `wxcli my-call-settings` with user-level OAuth, or workspace-level commands where available
- **Self-service vs admin path** — for voicemail and hoteling, both admin (`user-settings`) and self-service (`call-settings-for-me-phase-5`) paths exist. Use admin path when configuring for another user; use self-service path when the user is configuring their own settings with a user-level token
- **Call Recording read scope bug** — the actual required scope is `people_read`, not `people_write` as some docs state
- **Selective feature precedence** — Selective Reject > Selective Accept > Selective Forward > Standard Forwarding
- **SNR uses telephony_config scopes** — Single Number Reach uses `spark-admin:telephony_config_read/write`, not `people_read/write`
- **MoH requires both location + person enabled** — `moh_location_enabled=true` AND `moh_enabled=true` for MoH to play; if either is false, no music plays
- **Numbers API split endpoints** — read uses `people/{id}/features/numbers`, update uses `telephony/config/people/{id}/numbers` (different paths)
- **Receptionist validation** — `enabled` must be `True` if `monitored_members` is set
- **Use --output json** — always pass `--output json` on show/list commands to get structured data for comparison and scripting
- **Virtual lines use their own group** — never run `user-settings` commands against a virtual line ID; use `wxcli virtual-line-settings` (65+ commands mirroring person settings)
- **Beware bare-named commands** — a bare `list`/`update`/`show` rarely means "everything." `person-call-settings list` = monitoring only; `virtual-line-settings show`/`update` = call recording only; `hot-desking-members list` = *available* members, not assigned ones. Always confirm with `--help` before assuming a bare name is generic.
- **Mode management is split by token type** — admin assigns features (`user-settings update-mode-management`); only the user can switch a mode (`mode-management`, user OAuth). Admin tokens get 404 on every `mode-management` command.
- **PRESENCE_SYNC is org-only** — per-person MS Teams settings accept `HIDE_WEBEX_APP` only; use `client-settings` for PRESENCE_SYNC (affects the whole org)
- **`guest-management` is not a call setting** — it is the Guest Issuer token API and needs a Guest Issuer app, not an admin token. Treat its output as a credential.
- **Run `wxcli user-settings --help`** — to discover all available commands and their exact names
- **Run `wxcli virtual-line-settings --help`** — to discover the 65+ virtual line commands rather than guessing
- **Run `wxcli call-settings-for-me-phase-5 --help`** — to discover all 7 self-service commands

---

## Error Handling

When a wxcli command fails:

**A. Fix and retry** — If the error is a missing required field, wrong ID, or format issue:
1. Read the full error message
2. Run `wxcli <group> <command> --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** — If the error is non-blocking (e.g., setting already configured):
1. Verify current state with the corresponding show/list command
2. If already correct, skip and move to next setting

**C. Escalate** — If the error is unclear or persistent:
1. Run with `--debug` to see the raw HTTP request/response
2. Invoke `/wxc-calling-debug` for systematic diagnosis

Common errors:
- 400: Check required fields, verify IDs exist, check `--json-body` format
- 403: Check token scopes — some settings need `spark-admin:people_write`
- 404: Verify person/location ID is correct and has calling license
- 409: Resource already exists — GET current state before retrying

### Settings-specific errors

- **404 on person settings (anonymousCallReject, sequentialRing, priorityAlert, callNotify, callPolicies):** These 5 settings have NO admin endpoint. Admin tokens always get 404. See the "User-only settings" table in Step 3. Offer the workspace-level alternative if applicable. (Simultaneous Ring is no longer in this list — it now has an admin path via `user-settings list-simultaneous-ring` / `update-simultaneous-ring`.)
- **404 on person settings (all others):** Verify the person has a Webex Calling license. Unlicensed users return 404 on all `/telephony/config/people/{id}/` endpoints.
- **405 "Invalid Professional Place" on workspace settings:** The workspace has a Basic license. Most `/telephony/config/workspaces/{id}/` settings require Professional. Only `musicOnHold` and `doNotDisturb` work on Basic. Use the `/workspaces/{id}/features/` path family for Basic workspaces (callForwarding, callWaiting, callerId, intercept, monitoring).
- **403 on Single Number Reach:** SNR uses `spark-admin:telephony_config_read/write` scopes, not `spark-admin:people_read/write`. Check token scopes.
- **Empty/no-effect on MoH:** Both location-level `moh_location_enabled` AND person-level `moh_enabled` must be `true`. If either is false, no music plays. Check both levels.
- **404 (error 4008) on any `mode-management` command:** Every command in that group is a `/telephony/config/people/me/` endpoint — admin tokens always 404 (Known Issue #3). Use a user-level OAuth token. If you only need to assign mode-manageable features, use the admin path `user-settings update-mode-management PERSON_ID` instead.
- **404 on `virtual-line-settings` commands:** Confirm the ID is a `VIRTUAL_LINE` ID from `wxcli virtual-line-settings list`, not a person ID. Note the separate `virtual-extensions` group uses a different ID type entirely (Known Issue #9).
- **`person-call-settings list` returns only monitoring data:** That is correct behavior, not a bug — the group covers `/people/{id}/features/monitoring` only. For other person settings use `user-settings`.
- **`guest-management create` fails with 401/403 on an admin token:** Guest tokens require a Guest Issuer application (JWT-signed credentials). A standard admin token or PAT cannot mint them.
- **404 on `call-settings-for-me-phase-5` commands:** The authenticated user must have a Webex Calling license. These are `/people/me/` endpoints and require user-level OAuth tokens (`spark:people_read` / `spark:people_write`), not admin tokens.

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
