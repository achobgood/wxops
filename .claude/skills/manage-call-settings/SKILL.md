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

<!-- Updated by playbook session 2026-03-18 -->

# Manage Call Settings Workflow

## Step 1: Load references

1. Read `docs/reference/person-call-settings-handling.md` for call handling settings (forwarding, call waiting, DND, sim ring, sequential ring, SNR, selective accept/forward/reject, priority alert)
2. Read `docs/reference/person-call-settings-media.md` for voicemail, caller ID, privacy, barge, recording, intercept, monitoring, push-to-talk, music on hold
3. Read `docs/reference/person-call-settings-permissions.md` for incoming/outgoing permissions, feature access codes, executive/assistant
4. Read `docs/reference/person-call-settings-behavior.md` for calling behavior, app services, shared line, hoteling, receptionist, numbers, preferred answer, MS Teams, mode management, personal assistant, ECBN

## Step 2: Verify authentication

Before any API calls, confirm the user's auth token is working:

```bash
wxcli whoami
```

Check the token has the required scopes for the target operation. See the [Scope Quick Reference](#scope-quick-reference) at the bottom of this file.

## Step 3: Identify the target

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

## Step 4: Identify which settings to configure

Present the user with the settings categories. Ask which settings they want to read or change.

### Settings Catalog

#### Category 1: Call Handling

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Call Forwarding | `show-call-forwarding` | `update-call-forwarding` | Always, Busy, No-Answer, Business Continuity |
| Call Waiting | `show-call-waiting` | `update-call-waiting` | Simple on/off toggle |
| Do Not Disturb | `show-do-not-disturb` | `update-do-not-disturb` | Includes ring splash, Webex Go override |
| Simultaneous Ring | — | — | **Admin API may not support person-level; use workspace-level or self-service APIs** |
| Sequential Ring | — | — | **Same admin limitation as SimRing** |
| Single Number Reach | `wxcli single-number-reach` group | `wxcli single-number-reach` group | Uses `telephony_config` scopes, not `people` scopes |
| Selective Accept | — | — | Criteria managed via separate CRUD methods (SDK only) |
| Selective Forward | — | — | Takes precedence over standard forwarding |
| Selective Reject | — | — | Highest priority of the selective features |
| Priority Alert | — | — | **Same admin limitation as SimRing** |

#### Category 2: Voicemail & Media

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Voicemail | `show-voicemail` | `update-voicemail` | Inherits from location; greeting uploads via `configure-busy-voicemail`, `configure-no-answer` |
| Caller ID | `list` | `update-caller-id-features` | |
| Anonymous Call Rejection | — | — | Simple on/off (SDK only for now) |
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
| Call Policy | — | — | Connected line ID privacy; **workspace-only (professional license)** |

#### Category 4: Behavior & Devices

| Setting | CLI Command (show) | CLI Command (update) | Notes |
|---------|-------------------|---------------------|-------|
| Calling Behavior | `show-calling-behavior` | `update-calling-behavior` | Which Webex telephony app handles calls |
| App Services | `show` | `update` | Client platforms (browser, desktop, tablet, mobile) and ring behavior |
| Hoteling | `show-hoteling` | `update-hoteling` | Simple on/off; workspace-level API has more options |
| Receptionist Client | `list-reception` | `update-reception` | Monitored members list; enabled must be True if members are set |
| Numbers | `list-numbers` | — | Primary + alternate numbers; distinctive ring patterns |
| Preferred Answer Endpoint | — | — | Which device/app answers by default (SDK only for now) |
| MS Teams | — | — | HIDE_WEBEX_APP, PRESENCE_SYNC (SDK only for now) |
| Mode Management | — | — | Operating mode assignments (SDK only for now) |
| Personal Assistant | — | — | Away status, transfer, alerting (SDK only for now) |
| Emergency Callback Number | — | — | DIRECT_LINE, LOCATION_ECBN, or LOCATION_MEMBER_NUMBER (SDK only for now) |

All CLI commands above are under `wxcli user-settings`. Run `wxcli user-settings --help` to see the full list.

## Step 5: Read current settings — `[Always do this first]`

**CRITICAL: Always read the current value of any setting before proposing a change.** This prevents accidental overwrites and gives the user a clear before/after comparison.

### Pattern for simple settings

```bash
# Call Waiting
wxcli user-settings show-call-waiting PERSON_ID --output json
```

### Pattern for object settings

```bash
# Call Forwarding (always, busy, no-answer, business continuity)
wxcli user-settings show-call-forwarding PERSON_ID --output json
```

### Pattern for settings with sub-components

```bash
# Voicemail (many nested fields)
wxcli user-settings show-voicemail PERSON_ID --output json

# DND (enabled + ring splash)
wxcli user-settings show-do-not-disturb PERSON_ID --output json
```

### Reading multiple settings at once

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

## Step 6: Build deployment plan — `[Present to user before executing]`

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

### Check for location-level dependencies

Before configuring these settings, verify location-level prerequisites:

| Setting | Location Prerequisite |
|---------|----------------------|
| Music on Hold | `moh_location_enabled` must be `true` at location level |
| Call Recording | Location must have recording vendor configured |
| Call Intercept | Location-level intercept settings serve as defaults |
| Voicemail | Location-level voicemail policies (transcription, expiry) govern person-level behavior |

## Step 7: Execute changes — `[After user confirms plan]`

### Pattern: Simple toggle

```bash
# Enable Call Waiting
wxcli user-settings update-call-waiting PERSON_ID --json-body '{"enabled": true}'
```

### Pattern: Object-based settings

```bash
# Enable DND with ring splash
wxcli user-settings update-do-not-disturb PERSON_ID --json-body '{"enabled": true, "ringSplashEnabled": true}'
```

### Pattern: Complex nested settings (read first, modify fields, write back)

```bash
# 1. Read current forwarding
wxcli user-settings show-call-forwarding PERSON_ID --output json
# 2. Modify and write back — enable always-forward to a destination
wxcli user-settings update-call-forwarding PERSON_ID --json-body '{
  "callForwarding": {
    "always": {
      "enabled": true,
      "destination": "+15551234567"
    }
  }
}'
```

### Pattern: Voicemail configuration

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

### Pattern: Call intercept (take phone out of service)

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

### Pattern: Permissions

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

### Pattern: Executive/Assistant pairing

```bash
# Assign executive role
wxcli user-settings update-executive-assistant EXEC_PERSON_ID --json-body '{"type": "EXECUTIVE"}'

# Assign assistant role
wxcli user-settings update-executive-assistant ASST_PERSON_ID --json-body '{"type": "EXECUTIVE_ASSISTANT"}'
```

### Pattern: Workspace settings

Workspace settings mirror person settings but use the workspace-settings command group. Check available commands:

```bash
wxcli workspace-settings --help
```

### Pattern: Schedules

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

### Pattern: Reset voicemail PIN

```bash
wxcli user-settings reset-voicemail-pin PERSON_ID
```

### Pattern: Bulk changes (shell loop for small batches)

```bash
# Disable call waiting for a list of users
for ID in PERSON_ID_1 PERSON_ID_2 PERSON_ID_3; do
  wxcli user-settings update-call-waiting "$ID" --json-body '{"enabled": false}'
done
```

For large batches (50+ users), use the async Python SDK as a fallback:

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

## Step 8: Verify changes — `[Read back after every update]`

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

## Step 9: Report results

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

## CRITICAL REMINDERS

- **Always read before writing** — never update a setting without first reading its current value via `wxcli user-settings show-*`
- **Always show plan before executing** — present the deployment plan and get user confirmation
- **Handle person vs workspace scope differences** — some scopes use `workspaces_read/write` instead of `people_read/write` (outgoing permissions transfer numbers, access codes, call policy)
- **Location-level prerequisites** — voicemail, recording, intercept, and MoH have location-level settings that must be configured first; person-level settings may be overridden or ineffective without them
- **SimRing, SequentialRing, PriorityAlert admin limitation** — these may not be available via admin-level person management; use self-service APIs or workspace-level commands
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

---

## Scope Quick Reference

### Person Settings — Common Scopes

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
| Anon Call Rejection | Feature Access Controls | |
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

---

## Context Compaction

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
