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
# 4. Record only some DIRECTIONS — inbound/outbound x internal/external, four
#    independent toggles. Nested object, so no flag exists; --json-body only.
#    All four are required when sent; applies on "Always" / "Always with Pause/Resume".
wxcli user-settings update-call-recording PERSON_ID --verify --json-body '{"enabled":true,"record":"Always","selectiveCallRecordingSettings":{"recordInboundInternalCallsEnabled":false,"recordInboundExternalCallsEnabled":true,"recordOutboundInternalCallsEnabled":false,"recordOutboundExternalCallsEnabled":true}}'
```

### Voicemail transcription (location-scoped — affects ALL users at location)
```bash
wxcli location-voicemail show LOCATION_ID -o json          # Location voicemail policy
wxcli location-voicemail update LOCATION_ID --json-body '{"voicemailTranscriptionEnabled": true}'
wxcli user-settings update-voicemail PERSON_ID --json-body '{"enabled": true, "emailCopyOfMessage": {"enabled": true, "emailId": "user@example.com"}}'
```
Verified live 2026-10-13: the location key is `voicemailTranscriptionEnabled` — `show` read
`{"voicemailTranscriptionEnabled": true}`, an `update ... --verify` to `false` matched, and it was
restored to `true` with a matching read-back. (The `emailCopyOfMessage` person body on the third
line was not exercised.)

### Voicemail self-service (user-level OAuth)
```bash
wxcli my-call-settings show-voicemail-settings -o json     # Show own voicemail settings
wxcli my-call-settings update-voicemail-settings --json-body '{"enabled": true, "sendUnansweredCalls": {"enabled": true, "numberOfRings": 6}}'
wxcli my-call-settings show-voicemail-rules -o json        # Show voicemail PIN rules
wxcli my-call-settings update-voicemail-pin --json-body '{"passcode": "123456"}'  # Reset/change voicemail PIN
```
- The `123456` above is a placeholder: the admin passcode endpoint (`user-settings update-passcode`) rejected `123456`, `111111` and `12345678` with `[Error 5432] Invalid portal passcode` and accepted `135790` (Verified live 2026-10-13). The self-service endpoint is user-OAuth only and was not run, but expect the same strength rules.
- Requires **user-level OAuth** token (`spark:people_read` / `spark:people_write`). Admin tokens will not work.
- These are `/people/me/` endpoints — the authenticated user configures their own settings.
- The PIN body field is `passcode`, not `pin`.

### Personal assistant self-service (user-level OAuth)
```bash
wxcli my-call-settings show-personal-assistant -o json     # Show own personal-assistant settings
wxcli my-call-settings update-personal-assistant --json-body '{"enabled": true, "presence": "OUT_OF_OFFICE", "transferEnabled": true, "transferNumber": "+14085551234"}'
```
- Personal assistant is the "I am away — route my calls" feature (presence + optional transfer + ring reminder). It is **not** voicemail; the voicemail commands are the block above.

### Hoteling self-service (user-level OAuth)
```bash
wxcli my-call-settings show-hoteling-guest -o json         # Show own hoteling guest settings
wxcli my-call-settings update-hoteling-guest --json-body '{"enabled": true}'  # Enable self as hoteling guest
wxcli my-call-settings list-available-hosts -o json        # List available hoteling hosts
```
- Requires **user-level OAuth** token. Admin tokens will not work.
- The admin path for hoteling guest is `wxcli user-settings update-hoteling PERSON_ID`. Use the self-service path when the user is configuring their own hoteling.

### Call forwarding (read first and send the full object to be safe)
```bash
wxcli user-settings show-call-forwarding PERSON_ID -o json
wxcli user-settings update-call-forwarding PERSON_ID --json-body '{
  "callForwarding": {
    "always": {"enabled": false},
    "busy": {"enabled": true, "destination": "+15551234567", "destinationVoicemailEnabled": false},
    "noAnswer": {"enabled": false, "numberOfRings": 3}
  },
  "businessContinuity": {"enabled": false}
}'
```
Note: 4 blocks — `always`, `busy` and `noAnswer` nest under `callForwarding`; `businessContinuity` is its sibling at the top level. selectiveForward is a SEPARATE API.

Verified live 2026-10-13 (person, admin token): the `callForwarding` wrapper is correct. The PUT is a **block-level merge**, not a full replace — a body containing only `callForwarding.noAnswer` left an already-enabled `always` block untouched, and `businessContinuity` can be sent alone. Inside a block, however, an omitted boolean is reset (`always.ringReminderEnabled` went `true` -> `false` when only `{"enabled":false}` was sent) while an omitted `destination` is kept. To clear a destination send `"destination":""` (read-back then omits the field). Sending the full object is still the safe habit.

### Workspace hoteling
```bash
wxcli device-settings update-devices-workspaces WORKSPACE_ID --enabled  # Enable workspace hoteling host
wxcli user-settings update-hoteling PERSON_ID --json-body '{"enabled": true}'  # Person hoteling guest (simple toggle)
```
- Workspace hoteling host requires **Professional** workspace license (Basic returns 405) — **not reproduced for this command:** on a Basic workspace (created with the `Webex Calling - Workspaces` license) `device-settings update-devices-workspaces WORKSPACE_ID --enabled` and `--no-enabled` also returned 2xx (Verified live 2026-10-13; effect unreadable, see below). The 405 / `25409 Invalid Professional Place` error is what the other `/telephony/config/workspaces/{id}/...` settings return on Basic.
- Making a **Professional** workspace (Verified live 2026-10-13): create it with the org's `Webex Calling - Professional` license in `calling.webexCalling.licenses`; a workspace created with the `Webex Calling - Workspaces` license is Basic and `workspace-settings show-voicemail|list-simultaneous-ring|list-sequential-ring|list-priority-alert|show-anonymous-call-reject|show-call-policies|show-barge-in|show-call-bridge|list-privacy|list-push-to-talk|list-selective-*` all returned `25409` (HTTP 405) on it, while `show` (forwarding), `show-call-waiting`, `show-do-not-disturb`, `show-intercept`, `list-numbers`, `show-music-on-hold` and `list-monitoring` worked. On the Professional one all of those read 200.
- Verified live 2026-10-13 (Professional desk workspace): `device-settings update-devices-workspaces WORKSPACE_ID --enabled` returns 200 but the write cannot be read back — `--verify` reports `enabled` as `<not present in read-back>` (its re-read is `GET /telephony/config/workspaces/{id}/devices`, which returns only `devices`/`maxDeviceCount`), and `GET .../workspaces/{id}/features/hoteling` and `.../telephony/config/workspaces/{id}/hoteling` both 404. Treat the result as unconfirmed.
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
- **Not reproduced (2026-10-13):** `update-reception` with `{"receptionEnabled": true}` — with or without `monitoredMembers` — returned HTTP 400 with an **empty body** for a fresh Professional user (the CLI prints a bare `Error: `); `receptionEnabled: false` returned 204. The cause was not found, so treat the enable recipe above as unconfirmed. `list-reception` printed `[]` (it dropped `receptionEnabled`); it now prints the whole response object (generator fix 2026-10-13, ADR-14; not re-run live for this command).

### SimRing for persons (admin-configurable)
```bash
wxcli user-settings list-simultaneous-ring PERSON_ID -o json
wxcli user-settings update-simultaneous-ring PERSON_ID --json-body '{"enabled":true,"phoneNumbers":[{"phoneNumber":"+15551234567","answerConfirmationRequiredEnabled":false}]}'
wxcli user-settings create-criteria-simultaneous-ring PERSON_ID --json-body '{"scheduleName":"After hours","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"SELECT_PHONE_NUMBERS","phoneNumbers":["+15551234567"],"anonymousCallersEnabled":false,"unavailableCallersEnabled":false,"ringEnabled":true}'
wxcli user-settings show-criteria-simultaneous-ring PERSON_ID ID -o json
wxcli user-settings update-criteria-simultaneous-ring PERSON_ID ID --json-body '{"ringEnabled":true}'
wxcli user-settings delete-criteria-simultaneous-ring PERSON_ID ID --force
```

Verified live 2026-10-13 (person, admin token): the base update body needs `answerConfirmationRequiredEnabled` on **every** phone number or it fails with 400 `{"errorCode":25008,"message":"Missing Mandatory field name:  numbers.answerConfirmationEnabled"}` (the message names the field wrong). The recipe body above (`{"phoneNumber":"+15551234567"}` only) fails for that reason; use `{"phoneNumber":"+15551234567","answerConfirmationRequiredEnabled":false}`. Criteria: `callsFrom` and `ringEnabled` are required; `scheduleName` must name an existing schedule (an unknown name returned 400 `[Error 4167] The time schedule cannot be found`, so the recipe's `"After hours"`/`PEOPLE` example only works if a person schedule of that name exists). A location schedule worked with `"scheduleName":"openHours","scheduleLevel":"LOCATION"` (and also `GROUP`, which reads back as `LOCATION`), `callsFrom: ANY_PHONE_NUMBER`. `show-` / `update-` (`{"ringEnabled":false}`) / `delete-criteria-simultaneous-ring` (needs `--force` to skip the prompt) all worked. `user-settings list-simultaneous-ring` used to print `[]` although the object existed; it now prints the whole object (Verified live 2026-10-13 after the generator fix — see the read-command note below).

- Person SimRing now has an admin path via `user-settings` — `list-simultaneous-ring` / `update-simultaneous-ring` configure the base setting (enabled, do-not-ring-if-on-call, numbers); the `criteria-simultaneous-ring` commands manage schedule-based ring criteria.
- **Workspace SimRing is also admin-configurable:** `wxcli workspace-settings list-simultaneous-ring WORKSPACE_ID` and `update-simultaneous-ring` exist. Use those for workspaces instead of the `user-settings` commands.
- SNR (`single-number-reach`) remains a valid alternative for the desk + mobile ring-simultaneously use case, but it is no longer the only admin-configurable option for person SimRing:
```bash
wxcli single-number-reach list-single-number-reach PERSON_ID -o json
wxcli single-number-reach create PERSON_ID --phone-number "+14085551234" --enabled --name "Mobile"
# Verified live 2026-10-13: use a number with a real area code. +12223334444 (non-existent area code 222) was ACCEPTED on create and
# then made every GET of that person's singleNumberReach fail with 400 25105 "The number is not E.164 format" until deleted.
# +15551234567 (area code 555) was not tried. `list-single-number-reach` printed only the numbers array ([] when none), hiding
# `enabled`; it now prints the whole response object (generator fix 2026-10-13, ADR-14; not re-run live for this command).
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
| Answering | `show-answer-settings`/`update-answer-settings`, `list-available-preferred-answer-endpoints` (preferred endpoint + auto answer) |

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
- Verified live 2026-10-13 (create → settings → delete round trip on a temp virtual line): `update-call-forwarding` needs BOTH `callForwarding` and `businessContinuity` in the body (400 `25008` otherwise); `update-virtual-lines --announcement-language` takes the language NAME as read back (`"English"`), not `en_us` (400 `25046 Invalid Language`); `update-caller-id-virtual-lines` needs `--selected`; `list-caller-id` printed only `types` (it now prints the whole response object — generator fix 2026-10-13, ADR-14; not re-run live for this command); `update --enabled --record "Always"` returns the recording vendor's terms-of-service body (not accepted in the sandbox); `update-directory-search` has no `--verify`.

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
- `update` is a PUT — a `monitoredElements` list you send replaces the whole list (`[]` clears it); **omitting `monitoredElements` keeps the existing list** (Verified live 2026-10-13: the `--enable-call-park-notification`-only form left the monitored person in place). Max 50 elements (people, places, call park extensions). The read key is `callParkNotificationEnabled`, the write key `enableCallParkNotification`, so `--verify` reports the flag as "not present in read-back" even when it applied.

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
wxcli user-settings update-members-hot-desking PERSON_ID --verify --json-body '{"members":[{"id":"PERSON_ID","port":1,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":1,"allowCallDeclineEnabled":true},{"id":"MEMBER_ID","port":2,"primaryOwner":false,"lineType":"SHARED_CALL_APPEARANCE","lineWeight":1}]}'
# Verified live 2026-10-13: the body must re-send the person's own primary-owner entry (read list-members first);
# omitting it returns 400 {"errorCode":25486,"message":"Only one member can be the primary owner."}. lineWeight must be 1-16.
# A second member with lineType HOTDESKING_GUEST returns 200 but is silently dropped; SHARED_CALL_APPEARANCE persists.
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
wxcli user-settings update-outbound-billing-plan PERSON_ID --json-body '{"enabled": true}'   # body is {"enabled": bool} — Verified live 2026-10-13 (person: true then false, --verify matched)
wxcli workspace-settings list-outbound-billing-plan WORKSPACE_ID -o json
wxcli virtual-line-settings list-outbound-billing-plan VIRTUAL_LINE_ID -o json
```
- All three `update-outbound-billing-plan` commands are **`--json-body` only** — no field flags are generated. Read the current plan first and send the modified object back.
- The three `list-outbound-billing-plan` commands return **one object** (e.g. `{"enabled": true}`), not a list, and take no `--limit`/`--offset`/`--all`. Before 2026-10-13 they printed `[]` for every person (verified live 2026-10-13; ADR-13).

### Guest calling tokens (`guest-management`) — read this before using it

`guest-management` is the **Webex Guest Issuer API** (`/v1/guests/token`, `/v1/guests/count`), NOT a per-person call setting. It mints guest identities for guest calling/SDK embedding.

```bash
wxcli guest-management list -o json                                        # guest count for the org (one object, not a list; printed [] before 2026-10-13)
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
| Self-service voicemail / hoteling / personal assistant | `my-call-settings` | ~~call-settings-for-me-phase-5~~ (group removed 2026-07-29 — folded into `my-call-settings`) |
| **Virtual line settings** (any setting on a virtual line) | `virtual-line-settings` | ~~user-settings~~ |
| **Person monitoring / BLF** | `person-call-settings` (read/write) + `user-settings list-available-members-monitoring` (candidates) | ~~`user-settings list-monitoring`~~ (does not exist) |
| **Person hot desking members** | `user-settings *-hot-desking` (or alias `hot-desking-members`) | ~~device-settings~~ (that's workspace hot desking) |
| **Mode switching (user)** | `mode-management` — user OAuth only | ~~user-settings~~ |
| **Mode feature assignment (admin)** | `user-settings *-mode-management` | ~~mode-management~~ |
| **MS Teams — org-wide** | `client-settings` | ~~user-settings~~ |
| **MS Teams — per person** | `user-settings *-ms-teams` | ~~client-settings~~ |
| **Guest issuer tokens** | `guest-management` (Guest Issuer app required) | ~~user-settings~~ |
| **Voicemail messages** (list/read/delete a mailbox's messages) | `user-call-settings-members` (by member) · `user-call-settings-members-me` (self) | ~~`user-settings show-voicemail`/`update-voicemail`~~ (that's voicemail *config* — enable, forward, greeting) |
| **Answer settings** (preferred answer endpoint + auto answer) | `user-settings` / `virtual-line-settings` / `workspace-settings` `*-answer-settings` | ~~`my-call-settings show`/`update`~~ (self-service preferred endpoint only, user OAuth) |

### Voicemail messages (the messages, not the settings)

`user-settings show-voicemail`/`update-voicemail` *configure* voicemail. These
two groups act on the **messages in the mailbox**: the unread/read summary, the
message list, mark read/unread, and delete. `user-call-settings-members` takes a
positional member ID — a person, workspace, virtual line, hunt group, call queue
or auto attendant per the spec (`--help` types it "PEOPLE id"; on ID kinds the
doc wins). `user-call-settings-members-me` is the self-scoped twin: no
positional, user token, optional `--line-owner-id` for a secondary/shared line.
Neither retrieves audio — metadata and state only. Full detail:
`docs/reference/person-call-settings-media.md` §13.

```bash
# Unread/read counts, then the messages (a list endpoint — use --all to count)
wxcli user-call-settings-members show-summary MEMBER_ID
wxcli user-call-settings-members list-voice-messages MEMBER_ID --all -o json

# Mark ONE message read — without --message-id EVERY message is marked read
wxcli user-call-settings-members create-mark-as-read MEMBER_ID --message-id MESSAGE_ID

# Delete one message (no undo; prompts unless --force)
wxcli user-call-settings-members delete-voice-messages MEMBER_ID MESSAGE_ID

# Self-scoped twin (user token)
wxcli user-call-settings-members-me show-summary
```

- `list-memberships` (either group) does NOT list messages — it lists the call
  queue / hunt group / auto attendant **shared mailboxes** the member can reach.
  `list-voice-messages` is the message list.
- `user-settings list-memberships` (new) answers that same question for the
  **token holder** — the spec says "for the authenticated user" — through the
  older `/telephony/voiceMessages/memberships` path. It is not org-wide and takes
  no person ID. `user-settings` also still wraps the older self-scoped message
  path (`show-summary`, `list-voice-messages`, … with no positional).
- Verified live 2026-10-13 (admin PAT, empty mailboxes): `show-summary`, `list-voice-messages`, `list-memberships`
  and `create-mark-as-read` all ran against a person and (summary) a virtual line with 2xx; an empty mailbox returns
  204 (CLI prints `{}`/`[]`), and the `-me` twin returns `400 Target user not authorized (9601)` for an admin token.
  `user-settings list-memberships` / `-me list-memberships` failed `9000 Feature Toggle not enabled` on this org.
  Populated-mailbox shapes and a real delete were NOT exercised (no voicemail in the sandbox).

### Answer settings — preferred answer endpoint + auto answer (person / workspace / virtual line)

"Answer settings" is the admin-side object that picks **which of an entity's
devices or apps answers** (`preferredAnswerEndpointId`) and whether calls are
**auto-answered** (`autoAnswerEnabled`). It is not call forwarding and not ring
or alerting settings. The same three commands exist on all three groups; only
the positional changes.

```bash
wxcli user-settings list-available-preferred-answer-endpoints PERSON_ID   # candidate endpoint IDs
wxcli user-settings show-answer-settings PERSON_ID -o json
wxcli user-settings update-answer-settings PERSON_ID --preferred-answer-endpoint-id ENDPOINT_ID --auto-answer-enabled --verify

wxcli virtual-line-settings show-answer-settings VIRTUAL_LINE_ID -o json
wxcli workspace-settings update-answer-settings WORKSPACE_ID --no-auto-answer-enabled --verify

# CLEAR the preferred endpoint: the API wants JSON null, which the flag cannot send
wxcli user-settings update-answer-settings PERSON_ID --json-body '{"preferredAnswerEndpointId": null}'
```

- `--is-preferred-endpoint-clearable-by-person` exists on person and virtual
  line only — the workspace body has no such field.
- The older `user-settings list-preferred-answer-endpoint` /
  `update-preferred-answer-endpoint` (`/preferredAnswerEndpoint`) set the
  endpoint only; `my-call-settings show`/`update` are the user-OAuth
  self-service equivalent. Reach for `*-answer-settings` when auto answer is
  involved, or for a workspace or virtual line. Detail:
  `docs/reference/person-call-settings-behavior.md` §10.
- Verified live 2026-10-13 (person): set endpoint + `--auto-answer-enabled` with `--verify` matched; clearing with `--json-body '{"preferredAnswerEndpointId": null}'` works. The flag form `--preferred-answer-endpoint-id null` sends the string `"null"` and the server answered 502 — always clear with `--json-body`. Workspace and virtual-line variants (Verified live 2026-10-13): on a Professional workspace `workspace-settings update-answer-settings --no-auto-answer-enabled --verify` matched and `--no-is-preferred-endpoint-clearable-by-person` is rejected as an unknown option (workspace has no such flag); on a virtual line `--auto-answer-enabled` and `--no-is-preferred-endpoint-clearable-by-person` both matched under `--verify`. A set preferred endpoint is one value shared with the older `*-preferred-answer-endpoint` commands.


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

**Self-service scopes:** `my-call-settings` commands use `spark:people_read` / `spark:people_write` (user-level, NOT admin).

### Scope Verification Logic

1. Determine target type: **Person** needs `people_*` scopes; **Workspace** needs `workspaces_*` scopes
2. Determine operation: **Read** needs `*_read`; **Write** needs `*_write`
3. Check if the setting uses `telephony_config` scopes (see table above) — if so, verify those are present too
4. **Self-service commands** (`my-call-settings`): require user-level `spark:people_*` scopes, NOT admin scopes
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
# --calling-data true is REQUIRED — without it Webex omits locationId and extension,
# so every user reads as not calling-enabled and the filter silently returns nothing.
wxcli users list --calling-data true --output json
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
| **Self** (own settings) | `wxcli my-call-settings` | `spark:people_read/write` | `wxcli my-call-settings show-voicemail-settings` |

#### Multi-scope settings — which command for what?

| Setting | Person | Workspace | Location | Org | Self-Service |
|---------|--------|-----------|----------|-----|-------------|
| **Voicemail** | `user-settings show-voicemail PERSON_ID` | `workspace-settings show-voicemail WS_ID` | `location-voicemail show LOC_ID` (policies) | — | `my-call-settings show-voicemail-settings` |
| **Virtual line (any setting)** | — | — | — | — | Use `virtual-line-settings <cmd> VIRTUAL_LINE_ID` — its own group, mirrors most person settings |
| **Outbound Billing Plan** | `user-settings list-outbound-billing-plan PERSON_ID` | `workspace-settings list-outbound-billing-plan WS_ID` | — | — | — |
| **MS Teams** | `user-settings list-ms-teams PERSON_ID` (HIDE_WEBEX_APP only) | — | — | `client-settings list` (adds PRESENCE_SYNC) | — |
| **Mode Management** | `user-settings list-mode-management PERSON_ID` (assign) | — | — | — | `mode-management list` (switch — user OAuth only) |
| **Voicemail PIN** | `user-settings reset-voicemail-pin PERSON_ID` | — | — | — | `my-call-settings update-voicemail-pin` |
| **Voicemail PIN Rules** | — | — | — | — | `my-call-settings show-voicemail-rules` |
| **Call Recording** | `user-settings show-call-recording PERSON_ID` | `workspace-settings show-call-recordings WS_ID` | — | `call-recording show` (vendor config) | — |
| **Music on Hold** | `user-settings show-music-on-hold PERSON_ID` / `update-music-on-hold` (Verified live 2026-10-13) | SDK only (untested) | `location-settings` (must enable first) | — | — |
| **Call Intercept** | `user-settings show-intercept PERSON_ID` | `workspace-settings show-intercept WS_ID` | Location defaults apply | — | — |
| **Call Forwarding** | `user-settings show-call-forwarding PERSON_ID` | `workspace-settings show WS_ID` (bare `show` **is** call forwarding) | — | — | — |
| **Hoteling Guest** | `user-settings show-hoteling PERSON_ID` | — | — | — | `my-call-settings show-hoteling-guest` |
| **Hoteling Hosts** | — | — | — | — | `my-call-settings list-available-hosts` |

#### User-only settings (no admin endpoint — 404 guaranteed)

These settings exist ONLY at `/people/me/settings/{feature}` (Verified live 2026-10-13 for sequentialRing, priorityAlert, callNotify, callPolicies: admin path returns 404). Anonymous Call Reject is NOT one of them — it has an admin path (see below). With a **user-level OAuth token**, use `wxcli my-call-settings` (120 commands covering all self-service `/people/me/` endpoints including these 5). Without user-level OAuth, the user must configure these via the Webex app.

**Simultaneous Ring is no longer in this table** — it now has an admin path via `user-settings list-simultaneous-ring` / `update-simultaneous-ring` (plus `*-criteria-simultaneous-ring` for schedule-based criteria). See the SimRing recipe above.

| Setting | Self-service path | CLI group | Workspace equivalent? |
|---------|-------------------|-----------|----------------------|
| Sequential Ring | `/me/settings/sequentialRing` | `my-call-settings` | **Yes** (Professional workspace, Verified live 2026-10-13): `workspace-settings list-sequential-ring` / `update-sequential-ring` / `*-criteria-sequential-ring` |
| Priority Alert | `/me/settings/priorityAlert` | `my-call-settings` | **Yes** (Professional workspace, Verified live 2026-10-13): `workspace-settings list-priority-alert` / `update-priority-alert` / `*-criteria-priority-alert` |
| Call Notify | `/me/settings/callNotify` | `my-call-settings` | No |
| Call Policies | `/me/settings/callPolicies` | `my-call-settings` | **Yes:** workspace-level admin endpoint (Professional license required) |

**Self-service voicemail / hoteling commands** (`my-call-settings show-voicemail-settings`, `show-hoteling-guest`, `update-voicemail-pin`, `show-voicemail-rules`, `list-available-hosts`): These are NOT user-only — they have admin-path equivalents (`user-settings show-voicemail`, `user-settings update-hoteling`, `user-settings reset-voicemail-pin`). They provide the self-service path for users to manage their own voicemail and hoteling settings with a user-level token. Route to them when the user is configuring their own settings rather than an admin configuring someone else's. `my-call-settings show-personal-assistant` / `update-personal-assistant` are the user-OAuth versions; **an admin path exists too** (Verified live 2026-10-13: `GET`/`PUT /telephony/config/people/{id}/features/personalAssistant` returned 200/204 with an admin token, and `wxcli user-settings show-personal-assistant PERSON_ID` read an existing user). The earlier "self-service only" wording was wrong.

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
| Voicemail (self-service) | `my-call-settings show-voicemail-settings` | `my-call-settings update-voicemail-settings` | User-level OAuth only. User manages own voicemail settings |
| Voicemail PIN Rules | `my-call-settings show-voicemail-rules` | — | User-level OAuth only. Read-only PIN policy |
| Voicemail PIN Reset | — | `my-call-settings update-voicemail-pin` | User-level OAuth only. User resets own PIN |
| Caller ID | `list` | `update-caller-id-features` | |
| Anonymous Call Rejection | `show-anonymous-call-reject` | `update-anonymous-call-reject` | **Admin path exists** (`/telephony/config/people/{id}/anonymousCallReject`; Verified live 2026-10-13, `--verify` matched). Workspaces: `workspace-settings show/update-anonymous-call-reject` (Professional only) |
| Privacy | `list-privacy` | `update-privacy` | Controls line monitoring, AA extension/name dialing |
| Barge-In | `show-barge-in` | `update-barge-in` | Enables FAC-based barge-in across locations |
| Call Recording | `show-call-recording` | `update-call-recording` | **Read scope is `people_read` not `people_write` (SDK doc bug)**; inherits from location recording vendor config. `selectiveCallRecordingSettings` (4 direction toggles, added 2026-08-03) has **no flag** — `--json-body` only; same object on virtual lines and workspaces |
| Call Intercept | `show-intercept` | `update-intercept` | Takes phone out of service; greeting upload via `configure-call-intercept` |
| Monitoring | `person-call-settings list` | `person-call-settings update` | **NOT in `user-settings`** — `list-monitoring`/`update-monitoring` do not exist. Use the `person-call-settings` group (monitoring ONLY). Candidate lookup: `user-settings list-available-members-monitoring`. Max 50 elements |
| Push-to-Talk | `list-push-to-talk` | `update-push-to-talk` | One-way or two-way intercom; allow/block member lists |
| Music on Hold | `show-music-on-hold` | `update-music-on-hold` | Verified live 2026-10-13 (`--moh-enabled`/`--no-moh-enabled`, `--greeting DEFAULT`; read shows `mohLocationEnabled`). Location-level MoH must be enabled first; uses `telephony_config` scopes |

> **Read-command trap — fixed by the generator 2026-10-13 (ADR-14).** Before the fix (verified live 2026-10-13, person, admin token), `user-settings list` (caller ID) printed only the `types` array, and `list-privacy`, `list-push-to-talk`, `list-simultaneous-ring` and `person-call-settings list` (monitoring) printed `[]` or just the inner array although the server returned a full object. Now: `list-privacy` and `list-simultaneous-ring` print the whole object (Verified live 2026-10-13 after the fix). `user-settings list`, `list-push-to-talk` and `person-call-settings list` now print the whole response object (generator fix 2026-10-13, ADR-14; not re-run live for these commands) — until they are, the live-verified read is `api.session.rest_get` on `/people/{id}/features/callerId|pushToTalk|monitoring`. The writes (`update-*`) are unaffected.

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
| Hoteling (self-service) | `my-call-settings show-hoteling-guest` | `my-call-settings update-hoteling-guest` | User-level OAuth only. User manages own hoteling guest settings |
| Available Hoteling Hosts | `my-call-settings list-available-hosts` | — | User-level OAuth only. Lists hosts the user can sign into |
| Receptionist Client | `list-reception` | `update-reception` | `receptionEnabled` must be `true` if members set. Path: `/features/reception` (NOT receptionist) |
| Numbers | `list-numbers` | `update-numbers` | Primary + alternate numbers; distinctive ring patterns. Verified live 2026-10-13: `update-numbers PERSON_ID --json-body '{"phoneNumbers":[{"primary":false,"action":"ADD","directNumber":"+1..."}]}'` added an alternate number and `action: DELETE` removed it (`external` is accepted as a synonym of `directNumber`). Candidates: `list-available-numbers-secondary`. `list-numbers` printed only the phoneNumbers array (dropped `distinctiveRingEnabled`); it now prints the whole response object (generator fix 2026-10-13, ADR-14; not re-run live for this command) |
| Preferred Answer Endpoint | `list-preferred-answer-endpoint` | `update-preferred-answer-endpoint` | Which device/app answers by default. Self-service: `my-call-settings show`/`update` |
| Answer Settings | `show-answer-settings` | `update-answer-settings` | Preferred endpoint **plus** auto answer; candidates via `list-available-preferred-answer-endpoints`. Same three on `workspace-settings`/`virtual-line-settings`. See the Answer settings recipe above |
| MS Teams | `list-ms-teams` | `update-ms-teams` | Person-level accepts **HIDE_WEBEX_APP only**. For PRESENCE_SYNC use org-level `wxcli client-settings update` |
| Mode Management | `list-mode-management` | `update-mode-management` | Admin path assigns *which features* a user may mode-manage (`list-available-features` lists candidates). **Switching** a mode is user-OAuth-only via the `mode-management` group |
| Hot Desking Members | `list-members-hot-desking` | `update-members-hot-desking` | Member lines on the person's hot desk device. `list-available-members-hot-desking` searches candidates. Alias group: `hot-desking-members` |
| Outbound Billing Plan | `list-outbound-billing-plan` | `update-outbound-billing-plan` | `--json-body` only (no field flags). Also exists on `workspace-settings` and `virtual-line-settings` |
| Personal Assistant | `show-personal-assistant` | `update-personal-assistant` | Away status, transfer, alerting. Verified live 2026-10-13 (admin token, `--verify`). Clear `transferNumber` with `--json-body '{"transferNumber":null}'` (`--transfer-number ""` is rejected with 400 6004) |
| Emergency Callback Number | `emergency-services show-emergency-callback-number-people` | `emergency-services update-emergency-callback-number-people` | `--selected` DIRECT_LINE, LOCATION_ECBN, or LOCATION_MEMBER_NUMBER (+ `--location-member-id`); `--elin-enabled`/`--elin-for-webex-app-enabled`. Verified live 2026-10-13 (LOCATION_ECBN + ELIN flag, `--verify` matched). LOCATION_MEMBER_NUMBER with an extension-only member returned 400 `[Error 27402] ... does not have a valid phone number` |

All CLI commands above are under `wxcli user-settings` unless otherwise noted. Run `wxcli user-settings --help` to see the full list. Self-service commands are under `wxcli my-call-settings` (run `wxcli my-call-settings --help`).

### Settings without CLI commands ("SDK only")

**4 USER-ONLY settings (no admin endpoint — require user-level OAuth token):**
SequentialRing, PriorityAlert, CallNotify, CallPolicies (person-level). (SimRing and AnonymousCallReject have admin paths — Verified live 2026-10-13.)
These ONLY work at `/telephony/config/people/me/settings/{feature}` with a user token. Admin tokens get 404.

**MS Teams and Mode Management are NOT SDK-only** — both have verified CLI commands (`user-settings list-ms-teams`/`update-ms-teams`, `user-settings list-mode-management`/`update-mode-management`, plus org-level `client-settings` and user-level `mode-management`). See the Quick Recipes above. Virtual lines likewise have a full 65-command group (`virtual-line-settings`) — do not fall back to raw HTTP for them.

For settings still marked "SDK only" above (Feature Access Controls — whose documented endpoints returned 404 live on 2026-10-13), use the raw HTTP fallback pattern with an **admin** token:

```bash
# Read the current setting value
curl -s -H "Authorization: Bearer $WEBEX_ACCESS_TOKEN" \
  "https://webexapis.com/v1/telephony/config/people/{person_id}/{settingEndpoint}" | python3 -m json.tool

# Update via PUT (read-modify-write)
curl -s -X PUT -H "Authorization: Bearer $WEBEX_ACCESS_TOKEN" -H "Content-Type: application/json" \
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
wxcli user-settings list PERSON_ID --output json        # person caller ID — whole object since the 2026-10-13 generator fix (not re-run live; it printed ONLY `types` before); see the read-command note
# NOT `show-caller-id`: that is AGENT caller ID (read {"selectedCallerId": {}} for a non-agent; Verified live 2026-10-13)
wxcli user-settings list-privacy PERSON_ID --output json   # prints the whole privacy object (Verified live 2026-10-13 after the generator fix; it printed [] before)
wxcli user-settings show-barge-in PERSON_ID --output json
```

#### Reading self-service settings (user-level OAuth)

```bash
# Read own voicemail settings
wxcli my-call-settings show-voicemail-settings --output json

# Read own hoteling guest settings
wxcli my-call-settings show-hoteling-guest --output json

# Check voicemail PIN rules
wxcli my-call-settings show-voicemail-rules --output json

# List available hoteling hosts
wxcli my-call-settings list-available-hosts --output json
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
  "callForwarding": {
    "always": {"enabled": false},
    "busy": {"enabled": true, "destination": "+15551234567", "destinationVoicemailEnabled": false},
    "noAnswer": {"enabled": false, "numberOfRings": 3}
  },
  "businessContinuity": {"enabled": false}
}'
```
Forwarding has 4 blocks: always, busy and noAnswer under `callForwarding`, plus top-level businessContinuity. selectiveForward is a SEPARATE API.
Verified live 2026-10-13 (see the recipe at the top of this skill): the wrapper is right and the person PUT merges. **Virtual lines are different** — `virtual-line-settings update-call-forwarding` requires BOTH `callForwarding` and `businessContinuity` in every body (400 `25008 Missing Mandatory field name: businessContinuity` / `callForwarding` otherwise), so for a virtual line the "read first, send everything" advice above is mandatory, not just safe.

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

# Upload voicemail greetings — DOES NOT WORK from the CLI (Verified live 2026-10-13): both commands, bare or with
# --json-body '{"type":"CUSTOM"}', return 400 "Current request is not a multipart request" (no file option exists).
# Upload the .wav with a multipart POST to .../voicemail/actions/uploadBusyGreeting|uploadNoAnswerGreeting/invoke instead.
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

# Upload intercept greeting — same limitation: 400 "not a multipart request" (Verified live 2026-10-13); multipart POST needed
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
  "startDate": "2026-10-14",
  "endDate": "2026-10-14",
  "startTime": "09:00",
  "endTime": "17:00",
  "recurrence": {"recurWeekly": {"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true}}
}'
# Verified live 2026-10-13: startDate/endDate are the FIRST OCCURRENCE (same day), not the recurrence window. The old
# example (startDate 2026-01-01, endDate 2026-12-31) failed with 400 [Error 4194] "The event recurrence is invalid. The
# duration must be shorter than how frequently it occurs." "recurForEver": true inside recurrence (capital E, as the server
# stores it) was accepted and read back; a weekly rule without it was accepted too.

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
wxcli my-call-settings update-voicemail-settings --json-body '{"enabled": true, "sendUnansweredCalls": {"enabled": true, "numberOfRings": 6}}'

# User resets own voicemail PIN
wxcli my-call-settings update-voicemail-pin --json-body '{"passcode": "123456"}'

# User enables self as hoteling guest
wxcli my-call-settings update-hoteling-guest --json-body '{"enabled": true}'
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
# Verified live 2026-10-13: the previous version of this loop could not run — `--calling-data` takes a value
# (`--calling-data --output json` fails with "Got unexpected extra argument(s) (json)"), `people list -o json` returns a
# bare JSON array (so `.get('items')` raises AttributeError), and it ended in a stray `])` with no `done`.
# This form returned the 16 calling-enabled users of the test org, one id per line:
wxcli people list --calling-data true --all --fields '[?locationId].id' -o text | while read -r USER_ID; do
    wxcli user-settings update-call-waiting "$USER_ID" --no-enabled
    sleep 1
done
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
wxcli my-call-settings show-voicemail-settings --output json

# After self-service hoteling update
wxcli my-call-settings show-hoteling-guest --output json
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
- **Self-service vs admin path** — for voicemail and hoteling, both admin (`user-settings`) and self-service (`my-call-settings`) paths exist. Use admin path when configuring for another user; use self-service path when the user is configuring their own settings with a user-level token
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
- **Run `wxcli my-call-settings --help`** — to discover the self-service (`/people/me/`) commands rather than guessing

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
2. Invoke `the `wxc-calling-debug` skill` for systematic diagnosis

Common errors:
- 400: Check required fields, verify IDs exist, check `--json-body` format
- 403: Check token scopes — some settings need `spark-admin:people_write`
- 404: Verify person/location ID is correct and has calling license
- 409: Resource already exists — GET current state before retrying

### Settings-specific errors

- **404 on person settings (sequentialRing, priorityAlert, callNotify, callPolicies):** These settings have NO admin endpoint (Verified live 2026-10-13). anonymousCallReject is NOT in this list — it has an admin path via `user-settings show/update-anonymous-call-reject`. Admin tokens always get 404. See the "User-only settings" table in Step 3. Offer the workspace-level alternative if applicable. (Simultaneous Ring is no longer in this list — it now has an admin path via `user-settings list-simultaneous-ring` / `update-simultaneous-ring`.)
- **404 on person settings (all others):** Verify the person has a Webex Calling license. Unlicensed users return 404 on all `/telephony/config/people/{id}/` endpoints.
- **405 "Invalid Professional Place" on workspace settings:** The workspace has a Basic license. Most `/telephony/config/workspaces/{id}/` settings require Professional. Only `musicOnHold` and `doNotDisturb` work on Basic. Use the `/workspaces/{id}/features/` path family for Basic workspaces (callForwarding, callWaiting, callerId, intercept, monitoring).
- **403 on Single Number Reach:** SNR uses `spark-admin:telephony_config_read/write` scopes, not `spark-admin:people_read/write`. Check token scopes.
- **Empty/no-effect on MoH:** Both location-level `moh_location_enabled` AND person-level `moh_enabled` must be `true`. If either is false, no music plays. Check both levels.
- **404 (error 4008) on any `mode-management` command:** Every command in that group is a `/telephony/config/people/me/` endpoint — admin tokens always 404 (Known Issue #3). Use a user-level OAuth token. If you only need to assign mode-manageable features, use the admin path `user-settings update-mode-management PERSON_ID` instead.
- **404 on `virtual-line-settings` commands:** Confirm the ID is a `VIRTUAL_LINE` ID from `wxcli virtual-line-settings list`, not a person ID. Note the separate `virtual-extensions` group uses a different ID type entirely (Known Issue #9).
- **`person-call-settings list` returns only monitoring data:** That is correct behavior, not a bug — the group covers `/people/{id}/features/monitoring` only. For other person settings use `user-settings`.
- **`guest-management create` fails with 401/403 on an admin token:** Guest tokens require a Guest Issuer application (JWT-signed credentials). A standard admin token or PAT cannot mint them.
- **404 on `my-call-settings` commands:** The authenticated user must have a Webex Calling license. These are `/people/me/` endpoints and require user-level OAuth tokens (`spark:people_read` / `spark:people_write`), not admin tokens.
- **`call-settings-for-me-phase-5` no longer exists:** the group was removed on 2026-07-29 and its 7 commands folded into `my-call-settings` under names that say what they touch — `show`/`update` became `show-personal-assistant`/`update-personal-assistant`, `show-rules` became `show-voicemail-rules`, `update-pin` became `update-voicemail-pin`, `show-guest`/`update-guest` became `show-hoteling-guest`/`update-hoteling-guest`, and `list` became `list-available-hosts`. There is deliberately **no alias for the old group name**: `my-call-settings show`/`update`/`list` are the Preferred Answer Endpoint commands, so an alias would have answered a different question with exit 0.

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
