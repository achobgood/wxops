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

# Manage Call Settings Workflow

## Step 1: Load references

1. Read `docs/reference/person-call-settings-handling.md` for call handling settings (forwarding, call waiting, DND, sim ring, sequential ring, SNR, selective accept/forward/reject, priority alert)
2. Read `docs/reference/person-call-settings-media.md` for voicemail, caller ID, privacy, barge, recording, intercept, monitoring, push-to-talk, music on hold
3. Read `docs/reference/person-call-settings-permissions.md` for incoming/outgoing permissions, feature access codes, executive/assistant
4. Read `docs/reference/person-call-settings-behavior.md` for calling behavior, app services, shared line, hoteling, receptionist, numbers, preferred answer, MS Teams, mode management, personal assistant, ECBN

## Step 2: Verify authentication

Before any API calls, confirm the user's auth token is working:

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens='<token>')
me = api.people.me()
print(f"Authenticated as: {me.display_name} ({me.emails[0]})")
```

Check the token has the required scopes for the target operation. See the [Scope Quick Reference](#scope-quick-reference) at the bottom of this file.

## Step 3: Identify the target

Confirm with the user:

- **Target type:** Person or Workspace?
- **Target identifier:** Email address (person) or workspace name (workspace)?
- **Scope:** Single target, a list, or all users at a location?

### Look up a person

```python
people = list(api.people.list(email='user@example.com', calling_data=True))
person = people[0]
person_id = person.person_id
print(f"Found: {person.display_name} | Location: {person.location_id}")
```

### Look up a workspace

```python
workspaces = list(api.workspaces.list(display_name='Conference Room A'))
ws = workspaces[0]
workspace_id = ws.workspace_id
```

### For bulk operations (all calling users)

```python
calling_users = [u for u in api.people.list(calling_data=True) if u.location_id]
print(f"Found {len(calling_users)} calling-enabled users")
```

## Step 4: Identify which settings to configure

Present the user with the settings categories. Ask which settings they want to read or change.

### Settings Catalog

#### Category 1: Call Handling

| Setting | SDK Path | read() Returns | Notes |
|---------|----------|---------------|-------|
| Call Forwarding | `api.person_settings.forwarding` | `PersonForwardingSetting` | Always, Busy, No-Answer, Business Continuity |
| Call Waiting | `api.person_settings.call_waiting` | `bool` | Simple on/off toggle |
| Do Not Disturb | `api.person_settings.dnd` | `DND` | Includes ring splash, Webex Go override |
| Simultaneous Ring | `api.person_settings.sim_ring` | `SimRing` | **Admin API may not support person-level; use `api.me.sim_ring` for self-service or `api.workspace_settings` for workspaces** |
| Sequential Ring | `api.person_settings.sequential_ring` | `SequentialRing` | **Same admin limitation as SimRing** |
| Single Number Reach | `api.person_settings.single_number_reach` | `SingleNumberReach` | Uses `telephony_config` scopes, not `people` scopes |
| Selective Accept | `api.person_settings.selective_accept` | `SelectiveAccept` | Criteria managed via separate CRUD methods |
| Selective Forward | `api.person_settings.selective_forward` | `SelectiveForward` | Takes precedence over standard forwarding |
| Selective Reject | `api.person_settings.selective_reject` | `SelectiveReject` | Highest priority of the selective features |
| Priority Alert | `api.person_settings.priority_alert` | `PriorityAlert` | **Same admin limitation as SimRing** |

#### Category 2: Voicemail & Media

| Setting | SDK Path | read() Returns | Notes |
|---------|----------|---------------|-------|
| Voicemail | `api.person_settings.voicemail` | `VoicemailSettings` | Inherits from location; includes greeting uploads, passcode reset |
| Caller ID | `api.person_settings.caller_id` | `CallerId` | Two configure methods: parameter-based and object-based |
| Agent Caller ID | `api.person_settings.agent_caller_id` | `AgentCallerId` | For call queue/hunt group agents only |
| Anonymous Call Rejection | `api.person_settings.anon_calls` | `bool` | Simple on/off |
| Privacy | `api.person_settings.privacy` | `Privacy` | Controls line monitoring, AA extension/name dialing |
| Barge-In | `api.person_settings.barge` | `BargeSettings` | Enables FAC-based barge-in across locations |
| Call Recording | `api.person_settings.call_recording` | `CallRecordingSetting` | **Read scope is `people_read` not `people_write` (SDK doc bug)**; inherits from location recording vendor config |
| Call Intercept | `api.person_settings.call_intercept` | `InterceptSetting` | Takes phone out of service; supports greeting uploads |
| Monitoring | `api.person_settings.monitoring` | `Monitoring` | Max 50 monitored elements (people, places, call park extensions) |
| Push-to-Talk | `api.person_settings.push_to_talk` | `PushToTalkSettings` | One-way or two-way intercom; allow/block member lists |
| Music on Hold | `api.person_settings.moh` | `MusicOnHold` | **Requires location-level MoH enabled first**; uses `telephony_config` scopes |

#### Category 3: Permissions

| Setting | SDK Path | read() Returns | Notes |
|---------|----------|---------------|-------|
| Incoming Permissions | `api.person_settings.permissions_in` | `IncomingPermissions` | External transfer, internal calls, collect calls |
| Outgoing Permissions | `api.person_settings.permissions_out` | `OutgoingPermissions` | Per-call-type (local, toll, international, etc.); sub-APIs for transfer numbers, access codes, digit patterns |
| Feature Access Controls | `api.person_settings.feature_access` | `UserFeatureAccessSettings` | Controls what users can self-modify; org-level defaults available |
| Executive/Assistant Type | `api.person_settings.exec_assistant` | `ExecAssistantType` | UNASSIGNED, EXECUTIVE, or EXECUTIVE_ASSISTANT |
| Executive Settings | `api.person_settings.executive` | (multiple methods) | Alerting, assistants, call filtering, screening |
| Call Policy | `api.person_settings.call_policy` | `PrivacyOnRedirectedCalls` | Connected line ID privacy; **workspace-only (professional license)** |

#### Category 4: Behavior & Devices

| Setting | SDK Path | read() Returns | Notes |
|---------|----------|---------------|-------|
| Calling Behavior | `api.person_settings.calling_behavior` | `CallingBehavior` | Which Webex telephony app handles calls |
| App Services | `api.person_settings.app_services` | `AppServicesSettings` | Client platforms (browser, desktop, tablet, mobile) and ring behavior |
| App Shared Line | `api.person_settings.app_services.shared_line` | `DeviceMembersResponse` | Shared-line appearance on Webex apps |
| Call Bridge | `api.person_settings.call_bridge` | `CallBridgeSetting` | UC-One call bridge warning tone; not for FedRAMP |
| Hoteling | `api.person_settings.hoteling` | `bool` | Simple on/off; workspace-level API has more options |
| Receptionist Client | `api.person_settings.receptionist` | `ReceptionistSettings` | Monitored members list; enabled must be True if members are set |
| Numbers | `api.person_settings.numbers` | `PersonNumbers` | Primary + alternate numbers; distinctive ring patterns |
| Available Numbers | `api.person_settings.available_numbers` | `AvailableNumber` (generator) | Query available numbers for assignment (primary, secondary, ECBN, etc.) |
| Preferred Answer Endpoint | `api.person_settings.preferred_answer` | `PreferredAnswerResponse` | Which device/app answers by default |
| MS Teams | `api.person_settings.ms_teams` | `MSTeamsSettings` | HIDE_WEBEX_APP, PRESENCE_SYNC |
| Mode Management | `api.person_settings.mode_management` | `ModeManagementFeature` | Operating mode assignments (AA, Call Queue, Hunt Group); max 50 features |
| Personal Assistant | `api.person_settings.personal_assistant` | `PersonalAssistant` | Away status, transfer, alerting |
| Emergency Callback Number | `api.person_settings.ecbn` | `PersonECBN` | DIRECT_LINE, LOCATION_ECBN, or LOCATION_MEMBER_NUMBER |

## Step 5: Read current settings — `[Always do this first]`

**CRITICAL: Always read the current value of any setting before proposing a change.** This prevents accidental overwrites and gives the user a clear before/after comparison.

### Pattern for simple settings (bool)

```python
# Call Waiting
is_enabled = api.person_settings.call_waiting.read(entity_id=person_id)
print(f"Call Waiting: {'Enabled' if is_enabled else 'Disabled'}")
```

### Pattern for object settings

```python
# Call Forwarding
fwd = api.person_settings.forwarding.read(entity_id=person_id)
print(f"Always Forward: {fwd.call_forwarding.always.enabled} -> {fwd.call_forwarding.always.destination}")
print(f"Busy Forward: {fwd.call_forwarding.busy.enabled} -> {fwd.call_forwarding.busy.destination}")
print(f"No Answer Forward: {fwd.call_forwarding.no_answer.enabled} (rings: {fwd.call_forwarding.no_answer.number_of_rings})")
print(f"Business Continuity: {fwd.business_continuity.enabled}")
```

### Pattern for settings with sub-components

```python
# Voicemail (many nested fields)
vm = api.person_settings.voicemail.read(entity_id=person_id)
print(f"VM Enabled: {vm.enabled}")
print(f"  Send All Calls: {vm.send_all_calls.enabled}")
print(f"  Send Busy Calls: {vm.send_busy_calls.enabled}")
print(f"  Send Unanswered: {vm.send_unanswered_calls.enabled} (rings: {vm.send_unanswered_calls.number_of_rings})")
print(f"  Notifications: {vm.notifications.enabled}")
print(f"  Email Copy: {vm.email_copy_of_message.enabled}")
```

### Reading multiple settings at once

For a full audit, read all relevant settings and format as a summary table:

```python
settings_summary = {}
settings_summary['Call Waiting'] = api.person_settings.call_waiting.read(entity_id=person_id)
settings_summary['DND'] = api.person_settings.dnd.read(entity_id=person_id)
settings_summary['Hoteling'] = api.person_settings.hoteling.read(person_id=person_id)
settings_summary['Anon Call Reject'] = api.person_settings.anon_calls.read(entity_id=person_id)
# ... continue for each setting of interest
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

```python
# Check MoH location status
moh = api.person_settings.moh.read(entity_id=person_id)
if not moh.moh_location_enabled:
    print("WARNING: Music on Hold is disabled at the location level.")
    print("Person-level MoH changes will have no effect until location MoH is enabled.")
```

## Step 7: Execute changes — `[After user confirms plan]`

### Pattern: Simple toggle

```python
# Enable Call Waiting
api.person_settings.call_waiting.configure(entity_id=person_id, enabled=True)
```

### Pattern: Object-based settings (read-modify-write)

```python
# Modify DND
from wxc_sdk.person_settings.dnd import DND

dnd_settings = DND(enabled=True, ring_splash_enabled=True)
api.person_settings.dnd.configure(entity_id=person_id, dnd_settings=dnd_settings)
```

### Pattern: Complex nested settings (read first, modify fields, write back)

```python
# Modify voicemail ring count
vm = api.person_settings.voicemail.read(entity_id=person_id)
vm.send_unanswered_calls.number_of_rings = 6
api.person_settings.voicemail.configure(entity_id=person_id, settings=vm)
```

### Pattern: Settings with criteria (selective features)

Criteria are managed via separate CRUD methods, not through the main configure:

```python
# Enable selective reject and add a criteria
from wxc_sdk.person_settings.selective_reject import SelectiveReject, SelectiveRejectCriteria
from wxc_sdk.common.selective import SelectiveFrom

# Enable the feature
api.person_settings.selective_reject.configure(
    entity_id=person_id,
    settings=SelectiveReject(enabled=True)
)

# Create a criteria (reject calls from specific numbers)
criteria = SelectiveRejectCriteria(
    enabled=True,
    schedule_name=None,  # all hours
    calls_from=SelectiveFrom.select_phone_numbers,
    phone_numbers=['+12025551111', '+12025552222'],
    anonymous_callers_enabled=True,
    unavailable_callers_enabled=False
)
criteria_id = api.person_settings.selective_reject.create_criteria(
    entity_id=person_id,
    settings=criteria
)
```

### Pattern: Executive/Assistant pairing

```python
from wxc_sdk.person_settings.exec_assistant import ExecAssistantType

# Assign roles
api.person_settings.exec_assistant.configure(exec_id, ExecAssistantType.executive)
api.person_settings.exec_assistant.configure(asst_id, ExecAssistantType.executive_assistant)

# Link assistant to executive
api.person_settings.executive.update_assigned_assistants(exec_id, assistant_ids=[asst_id])
```

### Pattern: Workspace settings

Workspace settings mirror person settings. Use `api.workspace_settings` instead of `api.person_settings`:

```python
# Workspace call forwarding
ws_fwd = api.workspace_settings.forwarding.read(entity_id=workspace_id)
# ... same models, same patterns
api.workspace_settings.forwarding.configure(entity_id=workspace_id, forwarding=ws_fwd)
```

### Pattern: Reset to defaults

Many settings provide a `.default()` factory:

```python
from wxc_sdk.all_types import PersonForwardingSetting

forwarding = PersonForwardingSetting.default()
api.person_settings.forwarding.configure(entity_id=person_id, forwarding=forwarding)
```

Available `.default()` factories: `PersonForwardingSetting`, `VoicemailSettings`, `CallRecordingSetting`, `InterceptSetting`

### Pattern: Bulk changes (async)

For changing settings across many users, use the async API:

```python
from wxc_sdk.as_api import AsWebexSimpleApi
import asyncio

async with AsWebexSimpleApi(tokens='<token>') as api:
    calling_users = [u for u in await api.people.list(calling_data=True)
                     if u.location_id]

    # Example: disable call waiting for all users
    await asyncio.gather(*[
        api.person_settings.call_waiting.configure(
            entity_id=u.person_id, enabled=False
        )
        for u in calling_users
    ])
```

## Step 8: Verify changes — `[Read back after every configure]`

Always read back the setting after writing to confirm the change took effect:

```python
# After configuring
result = api.person_settings.call_waiting.read(entity_id=person_id)
print(f"Call Waiting is now: {'Enabled' if result else 'Disabled'}")

# For complex settings, compare specific fields
vm_after = api.person_settings.voicemail.read(entity_id=person_id)
print(f"Unanswered rings: {vm_after.send_unanswered_calls.number_of_rings}")  # should show 6
```

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

- **Always read before writing** — never configure a setting without first reading its current value
- **Always show plan before executing** — present the deployment plan and get user confirmation
- **Handle person vs workspace scope differences** — some scopes use `workspaces_read/write` instead of `people_read/write` (outgoing permissions transfer numbers, access codes, call policy)
- **Location-level prerequisites** — voicemail, recording, intercept, and MoH have location-level settings that must be configured first; person-level settings may be overridden or ineffective without them
- **SimRing, SequentialRing, PriorityAlert admin limitation** — these may not be available via `api.person_settings` for admin-level person management; use `api.me.*` for self-service or `api.workspace_settings` for workspaces
- **Call Recording read scope bug** — the SDK docstring says `people_write` for the read method; the actual required scope is `people_read`
- **Read-only fields are auto-excluded** — the SDK strips read-only fields from update payloads automatically; do not manually remove them
- **Selective feature precedence** — Selective Reject > Selective Accept > Selective Forward > Standard Forwarding
- **SNR uses telephony_config scopes** — Single Number Reach uses `spark-admin:telephony_config_read/write`, not `people_read/write`
- **CallRecording notification_type gotcha** — when `notification_type` is the `None` enum value, the SDK converts it to JSON `null` on write (the API returns string `"None"` on read)
- **MoH requires both location + person enabled** — `moh_location_enabled=true` AND `moh_enabled=true` for MoH to play; if either is false, no music plays
- **Numbers API split endpoints** — read uses `people/{id}/features/numbers`, update uses `telephony/config/people/{id}/numbers` (different paths)
- **Receptionist validation** — `enabled` must be `True` if `monitored_members` is set; the SDK enforces this

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
