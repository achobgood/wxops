---
name: manage-call-settings
description: |
  Configure person-level and workspace-level call settings in Webex Calling.
  Covers 39+ settings organized into categories: call handling, voicemail & media,
  permissions, and behavior & devices. Use when the user wants to read, change,
  or audit call settings for one or more users/workspaces.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [person-email-or-workspace-name]
---

<!-- Updated by playbook session 2026-03-19 -->

# Manage Call Settings Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What are the two path families for person call settings, and which is newer? (Answer: `/people/{id}/features/{feature}` is classic; `/telephony/config/people/{id}/{feature}` is newer. Some setting names differ between them.)
2. What happens when you use `/telephony/config/workspaces/{id}/` settings on a Basic-licensed workspace? (Answer: 405 "Invalid Professional Place" — only `musicOnHold` and `doNotDisturb` work on Basic. Use `/workspaces/{id}/features/` path for Basic workspaces.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Quick Recipes — Use These Exact Commands

**These are the authoritative command names. Use them exactly as shown. Do NOT construct command names from reference doc terminology.**

### Recording setup (3-level prerequisite chain)
```bash
wxcli call-recording show -o json                          # 1. Org-level recording vendor
wxcli call-recording list-vendors -o json                  # 2. Per-location vendor assignment
wxcli user-settings show-call-recording PERSON_ID -o json  # 3. Person recording
wxcli user-settings update-call-recording PERSON_ID --json-body '{"enabled": true, "record": "Always"}'
```

### Voicemail transcription (location-scoped — affects ALL users at location)
```bash
wxcli location-voicemail show LOCATION_ID -o json          # Location voicemail policy
wxcli location-voicemail update LOCATION_ID --json-body '{"voiceMessageTranscriptionEnabled": true}'
wxcli user-settings update-voicemail PERSON_ID --json-body '{"enabled": true, "emailCopyOfMessage": {"enabled": true, "emailId": "user@example.com"}}'
```

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
wxcli user-settings update-hoteling PERSON_ID --json-body '{"enabled": true}'  # Person hoteling (simple toggle)
```

### Receptionist client
```bash
wxcli user-settings list-reception PERSON_ID -o json
wxcli user-settings update-reception PERSON_ID --json-body '{"receptionEnabled": true, "monitoredMembers": ["ID1", "ID2"]}'
```
API path is `/features/reception` (NOT `/features/receptionist`). `receptionEnabled` must be `true` if members set.

### SimRing (USER-ONLY — no admin endpoint, use SNR instead)
```bash
wxcli single-number-reach list-single-number-reach PERSON_ID -o json
wxcli single-number-reach create PERSON_ID --phone-number "+15551234567" --enabled --name "Mobile"
```

### Executive-assistant pairing
```bash
wxcli user-settings update-executive-assistant EXEC_ID --json-body '{"type": "EXECUTIVE"}'
wxcli user-settings update-executive-assistant ASST_ID --json-body '{"type": "EXECUTIVE_ASSISTANT"}'
```

### Command group mapping (do NOT guess — use this table)
| Setting domain | wxcli group | NOT this group |
|---------------|-------------|----------------|
| Org call recording | `call-recording` | ~~location-call-settings~~ |
| Location voicemail | `location-voicemail` | ~~location-call-settings~~ |
| Person settings | `user-settings` | — |
| Workspace settings | `workspace-settings` | — |
| Workspace hoteling | `device-settings` | ~~workspace-settings~~ |

---

## Step 1: Load references (only what you need)

Load ONLY the reference docs relevant to the user's specific request. Do NOT load all 4 by default.

| If the request involves... | Load this doc |
|---------------------------|---------------|
| Forwarding, DND, call waiting, sim ring, SNR | `docs/reference/person-call-settings-handling.md` |
| Voicemail, caller ID, recording, intercept, monitoring | `docs/reference/person-call-settings-media.md` |
| Permissions, executive/assistant, feature access | `docs/reference/person-call-settings-permissions.md` |
| Hoteling, receptionist, calling behavior, numbers | `docs/reference/person-call-settings-behavior.md` |

**For recording + voicemail scenarios:** Load `person-call-settings-media.md` only. The location-level recording commands are in the Quick Recipes above — you do NOT need to load any location-call-settings docs.

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

### Scope Verification Logic

1. Determine target type: **Person** needs `people_*` scopes; **Workspace** needs `workspaces_*` scopes
2. Determine operation: **Read** needs `*_read`; **Write** needs `*_write`
3. Check if the setting uses `telephony_config` scopes (see table above) — if so, verify those are present too
4. If `wxcli whoami` does not show the required scopes, stop and tell the user which scopes are missing before proceeding

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

For small batches, use a shell loop. For large batches (50+ users), consider the async Python SDK pattern as a fallback:

```python
from wxc_sdk.as_api import AsWebexSimpleApi
import asyncio

async with AsWebexSimpleApi(tokens='<token>') as api:
    calling_users = [u for u in await api.people.list(calling_data=True)
                     if u.location_id]
```

### Settings Catalog

### Settings Scope Router

**Before attempting any settings command, determine the correct scope.** The same setting often exists at multiple levels with different command groups.

#### Quick router: "Who/what am I configuring?"

| Target | Command group | Scope prefix | Example |
|--------|--------------|-------------|---------|
| A specific **person** | `wxcli user-settings` | `spark-admin:people_read/write` | `wxcli user-settings show-voicemail PERSON_ID` |
| A specific **workspace** | `wxcli workspace-settings` | `spark-admin:workspaces_read/write` | `wxcli workspace-settings show-voicemail WORKSPACE_ID` |
| All people/workspaces at a **location** | `wxcli location-voicemail` / `wxcli location-settings` | `spark-admin:telephony_config_read/write` | `wxcli location-voicemail show LOCATION_ID` |
| **Org-wide** recording vendor | `wxcli call-recording` | `spark-admin:telephony_config_read/write` | `wxcli call-recording show` |

#### Multi-scope settings — which command for what?

| Setting | Person | Workspace | Location | Org |
|---------|--------|-----------|----------|-----|
| **Voicemail** | `user-settings show-voicemail PERSON_ID` | `workspace-settings show-voicemail WS_ID` | `location-voicemail show LOC_ID` (policies) | — |
| **Call Recording** | `user-settings show-call-recording PERSON_ID` | `workspace-settings show-call-recordings WS_ID` | — | `call-recording show` (vendor config) |
| **Music on Hold** | SDK only (telephony_config) | SDK only | `location-settings` (must enable first) | — |
| **Call Intercept** | `user-settings show-intercept PERSON_ID` | `workspace-settings show-intercept WS_ID` | Location defaults apply | — |
| **Call Forwarding** | `user-settings show-call-forwarding PERSON_ID` | `workspace-settings show-call-forwarding WS_ID` | — | — |

#### User-only settings (no admin endpoint — 404 guaranteed)

These 6 settings exist ONLY at `/people/me/settings/{feature}`. Admin tokens **always** get 404. With a **user-level OAuth token**, use `wxcli my-call-settings` (120 commands covering all self-service `/people/me/` endpoints including these 6). Without user-level OAuth, the user must configure these via the Webex app.

| Setting | Self-service path | Workspace equivalent? |
|---------|-------------------|----------------------|
| Simultaneous Ring | `/me/settings/simultaneousRing` | No |
| Sequential Ring | `/me/settings/sequentialRing` | No |
| Priority Alert | `/me/settings/priorityAlert` | No |
| Call Notify | `/me/settings/callNotify` | No |
| Anonymous Call Reject | `/me/settings/anonymousCallReject` | **Yes:** `workspace-settings` has admin endpoint |
| Call Policies | `/me/settings/callPolicies` | **Yes:** workspace-level admin endpoint (Professional license required) |

**If the user asks to configure one of these for a person:** Stop and explain that no admin API exists. Offer the workspace-level alternative if applicable, or inform them the user must self-configure.

Present the user with the settings categories. Ask which settings they want to read or change.

#### Category 1: Call Handling

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Call Forwarding | `show-call-forwarding` | `update-call-forwarding` | Always, Busy, No-Answer, Business Continuity |
| Call Waiting | `show-call-waiting` | `update-call-waiting` | Simple on/off toggle |
| Do Not Disturb | `show-do-not-disturb` | `update-do-not-disturb` | Includes ring splash, Webex Go override |
| Simultaneous Ring | — | — | **USER-ONLY: No admin endpoint. Requires user-level OAuth via `/me/settings/simultaneousRing`** |
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
| Caller ID | `list` | `update-caller-id-features` | |
| Anonymous Call Rejection | — | — | **USER-ONLY: No admin endpoint. Requires user-level OAuth via `/me/settings/anonymousCallReject`; workspace-level uses `workspaces/{id}/anonymousCallReject`** |
| Privacy | `list-privacy` | `update-privacy` | Controls line monitoring, AA extension/name dialing |
| Barge-In | `show-barge-in` | `update-barge-in` | Enables FAC-based barge-in across locations |
| Call Recording | `show-call-recording` | `update-call-recording` | **Read scope is `people_read` not `people_write` (SDK doc bug)**; inherits from location recording vendor config |
| Call Intercept | `show-intercept` | `update-intercept` | Takes phone out of service; greeting upload via `configure-call-intercept` |
| Monitoring | `list-monitoring` | `update-monitoring` | Max 50 monitored elements (people, places, call park extensions) |
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
| Hoteling | `show-hoteling` | `update-hoteling` | Person-level only. **Workspace hoteling:** use `wxcli device-settings update-devices-workspaces WORKSPACE_ID --enabled` |
| Receptionist Client | `list-reception` | `update-reception` | `receptionEnabled` must be `true` if members set. Path: `/features/reception` (NOT receptionist) |
| Numbers | `list-numbers` | — | Primary + alternate numbers; distinctive ring patterns |
| Preferred Answer Endpoint | — | — | Which device/app answers by default (SDK only for now) |
| MS Teams | — | — | HIDE_WEBEX_APP, PRESENCE_SYNC (SDK only for now) |
| Mode Management | — | — | Operating mode assignments (SDK only for now) |
| Personal Assistant | — | — | Away status, transfer, alerting (SDK only for now) |
| Emergency Callback Number | — | — | DIRECT_LINE, LOCATION_ECBN, or LOCATION_MEMBER_NUMBER (SDK only for now) |

All CLI commands above are under `wxcli user-settings`. Run `wxcli user-settings --help` to see the full list.

### Settings without CLI commands ("SDK only")

**6 USER-ONLY settings (no admin endpoint — require user-level OAuth token):**
SimRing, SequentialRing, PriorityAlert, CallNotify, AnonymousCallReject, CallPolicies (person-level).
These ONLY work at `/telephony/config/people/me/settings/{feature}` with a user token. Admin tokens get 404.

For other settings marked "SDK only" above (Music on Hold, Feature Access Controls, Preferred Answer, MS Teams, Mode Management, Personal Assistant, ECBN), use the raw HTTP fallback pattern with an **admin** token:

```bash
# Read the current setting value
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/telephony/config/people/{person_id}/{settingEndpoint}" | python3 -m json.tool

# Update via PUT (read-modify-write)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://webexapis.com/v1/telephony/config/people/{person_id}/{settingEndpoint}" \
  -d '{ ... }'
```

Consult `docs/reference/person-call-settings-handling.md` (SimRing, SeqRing, Priority Alert, Selective features) or `docs/reference/person-call-settings-behavior.md` (ECBN, Mode Management, MS Teams, Personal Assistant, Preferred Answer) for the exact endpoint paths, required fields, and gotchas for each setting.

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

### 4b. Check for location-level dependencies

Use the exact commands from the Quick Recipes section. Key prerequisites:

| Setting | Verify command | Fix command |
|---------|----------------|-------------|
| Call Recording (org) | `wxcli call-recording show -o json` | `wxcli call-recording update --json-body '{...}'` |
| Call Recording (location vendor) | `wxcli call-recording list-vendors -o json` | `wxcli call-recording update-vendor-call-recording LOC_ID --json-body '{...}'` |
| Voicemail transcription | `wxcli location-voicemail show LOC_ID -o json` | `wxcli location-voicemail update LOC_ID --json-body '{...}'` |
| Music on Hold | No wxcli command — use Control Hub or SDK | — |

**Do NOT use `location-call-settings` for recording or voicemail.** That group handles dial patterns only.

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
wxcli user-settings create-events PERSON_ID SCHEDULE_ID --json-body '{
  "name": "Weekdays",
  "startDate": "2026-01-01",
  "endDate": "2026-12-31",
  "startTime": "09:00",
  "endTime": "17:00",
  "recurrence": {"recurWeekly": {"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true}}
}'

# Show schedule detail
wxcli user-settings show-schedules PERSON_ID SCHEDULE_ID --output json

# Delete a schedule event (requires 4 positional args)
wxcli user-settings delete PERSON_ID SCHEDULE_TYPE SCHEDULE_ID EVENT_ID
```

#### Pattern: Reset voicemail PIN

```bash
wxcli user-settings reset-voicemail-pin PERSON_ID
```

### 6b. Bulk changes

#### Shell loop for small batches

```bash
# Disable call waiting for a list of users
for ID in PERSON_ID_1 PERSON_ID_2 PERSON_ID_3; do
  wxcli user-settings update-call-waiting "$ID" --json-body '{"enabled": false}'
done
```

#### Async Python SDK for large batches (50+ users)

```python
from wxc_sdk.as_api import AsWebexSimpleApi
import asyncio

async with AsWebexSimpleApi(tokens='<token>', concurrent_requests=40) as api:
    calling_users = [u for u in await api.people.list(calling_data=True)
                     if u.location_id]

    # Example: disable call waiting for all users
    # The SDK's internal semaphore limits concurrency to concurrent_requests
    await asyncio.gather(*[
        api.person_settings.call_waiting.configure(
            entity_id=u.person_id, enabled=False
        )
        for u in calling_users
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
- **Call Recording read scope bug** — the actual required scope is `people_read`, not `people_write` as some docs state
- **Selective feature precedence** — Selective Reject > Selective Accept > Selective Forward > Standard Forwarding
- **SNR uses telephony_config scopes** — Single Number Reach uses `spark-admin:telephony_config_read/write`, not `people_read/write`
- **MoH requires both location + person enabled** — `moh_location_enabled=true` AND `moh_enabled=true` for MoH to play; if either is false, no music plays
- **Numbers API split endpoints** — read uses `people/{id}/features/numbers`, update uses `telephony/config/people/{id}/numbers` (different paths)
- **Receptionist validation** — `enabled` must be `True` if `monitored_members` is set
- **Use --output json** — always pass `--output json` on show/list commands to get structured data for comparison and scripting
- **Run `wxcli user-settings --help`** — to discover all available commands and their exact names

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

- **404 on person settings (anonymousCallReject, simultaneousRing, sequentialRing, priorityAlert, callNotify, callPolicies):** These 6 settings have NO admin endpoint. Admin tokens always get 404. See the "User-only settings" table in Step 3. Offer the workspace-level alternative if applicable.
- **404 on person settings (all others):** Verify the person has a Webex Calling license. Unlicensed users return 404 on all `/telephony/config/people/{id}/` endpoints.
- **405 "Invalid Professional Place" on workspace settings:** The workspace has a Basic license. Most `/telephony/config/workspaces/{id}/` settings require Professional. Only `musicOnHold` and `doNotDisturb` work on Basic. Use the `/workspaces/{id}/features/` path family for Basic workspaces (callForwarding, callWaiting, callerId, intercept, monitoring).
- **403 on Single Number Reach:** SNR uses `spark-admin:telephony_config_read/write` scopes, not `spark-admin:people_read/write`. Check token scopes.
- **Empty/no-effect on MoH:** Both location-level `moh_location_enabled` AND person-level `moh_enabled` must be `true`. If either is false, no music plays. Check both levels.

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
