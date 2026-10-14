# Call Features: Auto Attendants, Call Queues, and Hunt Groups

Reference for Webex Calling's three major call-routing features.

## Sources

- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Call Features APIs

---

## Table of Contents

1. [Auto Attendants](#1-auto-attendants)
2. [Call Queues](#2-call-queues)
3. [Hunt Groups](#3-hunt-groups)
4. [Shared Forwarding API](#4-shared-forwarding-api)
5. [Common Data Models (HG/CQ Base)](#5-common-data-models-hgcq-base)
6. [Required Scopes](#6-required-scopes)
7. [Dependencies](#7-dependencies)

---

## 1. Auto Attendants

### Overview

Auto attendants play customized prompts and provide callers with menu options for routing their calls. They support separate menus for business hours and after hours, each configurable with key-press actions (transfer, dial-by-name, extension dialing, repeat menu, exit, etc.).

Use an auto attendant when you need an IVR-style front door: "Press 1 for Sales, 2 for Support..."

### Key Data Models

#### `AutoAttendant`

| Field | Type | Required for Create | Notes |
|-------|------|:-------------------:|-------|
| `name` | `str` | Yes | Unique name |
| `phone_number` | `str` | One of phone_number/extension | |
| `extension` | `str` | One of phone_number/extension | |
| `business_schedule` | `str` | Yes | Name of business hours schedule |
| `holiday_schedule` | `str` | No | Name of holiday schedule |
| `business_hours_menu` | `AutoAttendantMenu` | Yes | No default: create without it is rejected `400 25008 "Missing Mandatory field name:  businessHoursMenu"`, and the CLI does **not** inject one — pass it via `--json-body`. Verified live 2026-10-13. |
| `after_hours_menu` | `AutoAttendantMenu` | Yes | Same as `business_hours_menu`. Verified live 2026-10-13. |
| `extension_dialing` | `Dialing` | No | `ENTERPRISE` or `GROUP` (default: ENTERPRISE) |
| `name_dialing` | `Dialing` | No | `ENTERPRISE` or `GROUP` (default: ENTERPRISE) |
| `language_code` | `str` | No | |
| `time_zone` | `str` | No | |
| `alternate_numbers` | `list[AlternateNumber]` | No | Only in details(), up to 10 |
| `first_name` / `last_name` | `str` | No | **Deprecated** -- use `direct_line_caller_id_name` and `dial_by_name` instead |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | No | Not supported in FedRAMP. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions. |
| `dial_by_name` | `str` | No | Not supported in FedRAMP. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions. |

#### `AutoAttendantMenu`

| Field | Type | Notes |
|-------|------|-------|
| `greeting` | `Greeting` | `DEFAULT` or `CUSTOM` |
| `extension_enabled` | `bool` | Allow extension dialing from this menu |
| `audio_announcement_file` | `AnnAudioFile` | Required when greeting is CUSTOM |
| `key_configurations` | `list[AutoAttendantKeyConfiguration]` | Key-to-action mappings |
| `call_treatment` | `CallTreatment` | What to do when caller gives no input |

#### `AutoAttendantKeyConfiguration`

| Field | Type | Notes |
|-------|------|-------|
| `key` | `MenuKey` | `0`-`9`, `*`, `#` |
| `action` | `AutoAttendantAction` | See enum below |
| `description` | `str` | Optional |
| `value` | `str` | Destination number/extension for transfer actions |

#### Enum: `AutoAttendantAction`

| Value | Description |
|-------|-------------|
| `TRANSFER_WITHOUT_PROMPT` | Transfer immediately |
| `TRANSFER_WITH_PROMPT` | Play prompt then transfer |
| `TRANSFER_TO_OPERATOR` | Transfer to operator |
| `NAME_DIALING` | Dial by name directory |
| `EXTENSION_DIALING` | Dial by extension |
| `REPEAT_MENU` | Replay the menu |
| `EXIT` | Disconnect |
| `TRANSFER_TO_MAILBOX` | Transfer to voicemail |
| `RETURN_TO_PREVIOUS_MENU` | Go back one menu level |
| `PLAY_ANNOUNCEMENT` | Play an announcement |

#### `CallTreatment` (no-input handling)

| Field | Type | Notes |
|-------|------|-------|
| `retry_attempt_for_no_input` | `CallTreatmentRetry` | `NO_REPEAT`, `ONE_TIME`, `TWO_TIMES`, `THREE_TIMES` |
| `no_input_timer` | `int` | Seconds to wait (1-60, default 10) |
| `action_to_be_performed` | `ActionToBePerformed` | What to do after retries exhausted |

#### `ActionToBePerformedAction` (post-retry actions)

`PLAY_MESSAGE_AND_DISCONNECT`, `TRANSFER_WITHOUT_PROMPT`, `TRANSFER_WITH_PROMPT`, `TRANSFER_TO_OPERATOR`, `TRANSFER_TO_MAILBOX`, `DISCONNECT`

### Phone Number/Extension Assignment

- Must provide at least one of `phone_number` or `extension` at creation.

### Announcements

- **Upload is supported via the Announcement Repository API** (`POST /telephony/config/announcements` or `POST /telephony/config/locations/{locationId}/announcements` with multipart/form-data). See [location-calling-media.md](location-calling-media.md) section 1.

### Forwarding

Auto attendants have a `forwarding` sub-resource. See [Shared Forwarding API](#4-shared-forwarding-api).

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List auto attendants:**
```python
params = {"locationId": loc_id, "max": 1000}
result = api.session.rest_get(f"{BASE}/telephony/config/autoAttendants", params=params)
aas = result.get("autoAttendants", [])
# Each item: {"id", "name", "locationId", "locationName", "phoneNumber", "extension", "enabled", ...}
```

**Get details:**
```python
aa = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/autoAttendants/{aa_id}")
```

**Create auto attendant:**
```python
body = {
    "name": "Main Menu",
    "extension": "1000",
    "businessSchedule": "Business Hours",          # must reference existing schedule
    "businessHoursMenu": {
        "greeting": "DEFAULT",
        "extensionEnabled": True,
        "keyConfigurations": [{"key": "0", "action": "EXIT"}]
    },
    "afterHoursMenu": {
        "greeting": "DEFAULT",
        "extensionEnabled": True,
        "keyConfigurations": [{"key": "0", "action": "EXIT"}]
    }
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/autoAttendants", json=body)
new_id = result.get("id")
```

Required fields: `name`, `extension` (or `phoneNumber`), `businessSchedule`, `businessHoursMenu`, `afterHoursMenu`. Both menus need `greeting`, `extensionEnabled`, and at least one `keyConfigurations` entry.

**Update auto attendant:**
```python
body = {"name": "Updated Menu Name"}  # partial update — only changed fields
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/autoAttendants/{aa_id}", json=body)
```

**Delete auto attendant:**
```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/autoAttendants/{aa_id}")
```

**Get call forwarding settings:**
```python
fwd = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/autoAttendants/{aa_id}/callForwarding"
)
```

### CLI Examples

```bash
# List all auto attendants (org-wide)
wxcli auto-attendant list

# List auto attendants at a specific location
wxcli auto-attendant list --location-id Y2lzY29zcGFyazovL...

# Filter by name
wxcli auto-attendant list --name "Main Menu"

# Get details for a specific auto attendant (JSON output)
wxcli auto-attendant show Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_AA_ID

# NOTE: flags alone do NOT work. `auto-attendant create LOC --name ... --extension ... --business-schedule ...`
# fails 400 25008 "Missing Mandatory field name:  businessHoursMenu" (the CLI sends no menus).
# --business-schedule / businessSchedule must be the EXACT NAME of an existing schedule at that location
# (list with `wxcli location-schedules list LOC_ID`). Verified live 2026-10-13.

# Create with the menus (minimum working body) via --json-body
wxcli auto-attendant create Y2lzY29zcGFyazovL_LOC_ID --json-body '{
  "name": "Main Menu",
  "extension": "1000",
  "businessSchedule": "Business Hours",
  "businessHoursMenu": {
    "greeting": "DEFAULT",
    "extensionEnabled": true,
    "keyConfigurations": [
      {"key": "1", "action": "TRANSFER_WITHOUT_PROMPT", "value": "2000"},
      {"key": "2", "action": "TRANSFER_WITHOUT_PROMPT", "value": "3000"},
      {"key": "0", "action": "TRANSFER_TO_OPERATOR", "value": ""}
    ]
  },
  "afterHoursMenu": {
    "greeting": "DEFAULT",
    "extensionEnabled": true,
    "keyConfigurations": [{"key": "0", "action": "EXIT", "value": ""}]
  }
}'

# Update basic fields (name, extension)
wxcli auto-attendant update Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_AA_ID \
  --name "Updated Main Menu"

# Update menu configuration via --json-body (required for menu changes).
# A menu you send REPLACES that whole menu: sending keys 1 and 0 removed a previously
# configured key 2 (verified live 2026-10-13). Resend every key you want to keep.
wxcli auto-attendant update Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_AA_ID --json-body '{
  "businessHoursMenu": {
    "greeting": "DEFAULT",
    "extensionEnabled": true,
    "keyConfigurations": [
      {"key": "1", "action": "TRANSFER_WITHOUT_PROMPT", "value": "2000"},
      {"key": "0", "action": "EXIT", "value": ""}
    ]
  }
}'

# Delete an auto attendant
wxcli auto-attendant delete Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_AA_ID --force

# Get call forwarding settings
wxcli auto-attendant show-call-forwarding Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_AA_ID

# List announcement files
wxcli auto-attendant list-announcements Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_AA_ID
```

---

## 2. Call Queues

### Overview

Call queues temporarily hold calls in the cloud when all assigned agents are unavailable. Queued calls route to agents when they become available. Each queue has a lead number (external phone number) and an internal extension.

Use a call queue when callers should wait on hold until an agent is free (support lines, order lines, etc.).

### Key Data Models

#### `CallQueue` (extends `HGandCQ`)

| Field | Type | Required for Create | Notes |
|-------|------|:-------------------:|-------|
| `name` | `str` | Yes | Unique name |
| `phone_number` | `str` | One of phone_number/extension | |
| `extension` | `str` | One of phone_number/extension | |
| `agents` | `list[Agent]` | No | People, workspaces, or virtual lines. Live: a queue is created fine with no `agents` (verified 2026-10-13). |
| `call_policies` | `CallQueueCallPolicies` | Yes | Only `callPolicies.policy` is required. Omitting `callPolicies` -> `400 25008 "Missing Mandatory field name:  callPolicies"`; `"callPolicies":{}` -> `400 25008 "...callPolicies.policy"`. `routingType` is optional (defaults to `PRIORITY_BASED`). The CLI flags (`--name`, `--extension`) cannot supply it — use `--json-body`. Verified live 2026-10-13. |
| `queue_settings` | `QueueSettings` | No | Queue size, overflow, announcements. Live: omitted on create without error; server fills defaults (`queueSize` 0, overflow `PERFORM_BUSY_TREATMENT`). Verified live 2026-10-13. |
| `enabled` | `bool` | No | |
| `language_code` | `str` | No | |
| `time_zone` | `str` | No | |
| `allow_call_waiting_for_agents_enabled` | `bool` | No | |
| `allow_agent_join_enabled` | `bool` | No | Let agents join/unjoin |
| `phone_number_for_outgoing_calls_enabled` | `bool` | No | Allow queue number for outbound caller ID |
| `department` | `IdAndName` | No | |
| `has_cx_essentials` | `bool` | No | Customer Assist (formerly CX Essentials) license flag |

#### `CallQueueCallPolicies`

| Field | Type | Notes |
|-------|------|-------|
| `routing_type` | `CQRoutingType` | `PRIORITY_BASED` or `SKILL_BASED` |
| `policy` | `Policy` | See Policy enum below |
| `call_bounce` | `CallBounce` | No-answer behavior |
| `distinctive_ring` | `DistinctiveRing` | Optional ring pattern |

#### Enum: `Policy` (shared with Hunt Groups)

| Value | Max Agents | Description |
|-------|:----------:|-------------|
| `CIRCULAR` | 1,000 | Round-robin after last agent that took a call |
| `REGULAR` | 1,000 | Top-down, restart from top each time |
| `SIMULTANEOUS` | 50 | Ring all agents at once |
| `UNIFORM` | 1,000 | Longest-idle agent first |
| `WEIGHTED` | 100 | Percentage-based distribution (up to 100%) |

#### Enum: `CQRoutingType`

| Value | Description |
|-------|-------------|
| `PRIORITY_BASED` | Uses routing policy directly |
| `SKILL_BASED` | Routes by agent skill level; policy is tiebreaker when skill levels match |

#### `CallBounce`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `enabled` (alias: `callBounceEnabled`) | `bool` | `True` | Bounce after max_rings |
| `max_rings` (alias: `callBounceMaxRings`) | `int` | `8` | |
| `agent_unavailable_enabled` | `bool` | `False` | Bounce if agent goes unavailable |
| `alert_agent_enabled` | `bool` | `False` | Alert agent for long-held calls |
| `alert_agent_max_seconds` | `int` | `30` | |
| `on_hold_enabled` | `bool` | `False` | Bounce calls on hold too long |
| `on_hold_max_seconds` | `int` | `60` | |

> **Verified live 2026-10-13:** the defaults above are what a queue created with only `callPolicies.policy` reads back (`callBounceEnabled` true, `callBounceMaxRings` 8, `agentUnavailableEnabled` false, `alertAgentEnabled` false, `alertAgentMaxSeconds` 30, `callBounceOnHoldEnabled` false, `callBounceOnHoldMaxSeconds` 60). An earlier version of this table listed `max_rings` 5 and `agent_unavailable_enabled`/`alert_agent_enabled` True, which came from the SDK model, not the server.

### Overflow Settings

#### `OverflowSetting` (inside `QueueSettings.overflow`)

| Field | Type | Notes |
|-------|------|-------|
| `action` | `OverflowAction` | What happens when queue is full |
| `send_to_voicemail` | `bool` | Forward to voicemail of internal number |
| `transfer_number` | `str` | Destination when action is TRANSFER_TO_PHONE_NUMBER |
| `overflow_after_wait_enabled` | `bool` | Trigger overflow after wait time |
| `overflow_after_wait_time` | `int` | Seconds before overflow triggers (no agent available) |
| `play_overflow_greeting_enabled` | `bool` | Play audio before overflow action |
| `greeting` | `Greeting` | `DEFAULT` or `CUSTOM` |
| `audio_announcement_files` | `list[AnnAudioFile]` | 1-4 files for CUSTOM greeting |

#### Enum: `OverflowAction`

| Value | Description |
|-------|-------------|
| `PERFORM_BUSY_TREATMENT` | Caller hears fast-busy tone |
| `TRANSFER_TO_PHONE_NUMBER` | Transfer to specified number |
| `PLAY_RINGING_UNTIL_CALLER_HANGS_UP` | Caller hears ringing until disconnect |

### Queue Settings and Announcements

`QueueSettings` contains the full queue behavior configuration:

| Field | Type | Notes |
|-------|------|-------|
| `queue_size` | `int` | Maximum calls in queue; overflow triggers when exceeded |
| `call_offer_tone_enabled` | `bool` | Play tone to callers when routed to agent |
| `reset_call_statistics_enabled` | `bool` | Reset stats on queue entry |
| `overflow` | `OverflowSetting` | See above |
| `welcome_message` | `WelcomeMessageSetting` | First message callers hear; can be mandatory |
| `wait_message` | `WaitMessageSetting` | Estimated wait time or position |
| `comfort_message` | `ComfortMessageSetting` | Periodic message (promotions, info) |
| `comfort_message_bypass` | `ComfortMessageBypass` | Short comfort for quickly-answered calls |
| `moh_message` | `MohMessageSetting` | Music on hold (normal + alternate source) |
| `whisper_message` | `AudioSource` | Plays to agent before connection (identifies queue) |

#### `WelcomeMessageSetting` (extends `AudioSource`)

- `enabled`, `greeting` (`DEFAULT`/`CUSTOM`), `audio_announcement_files`
- `always_enabled`: If true, message plays even when agent is immediately available.

#### `WaitMessageSetting`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | |
| `wait_mode` | `WaitMode` | `TIME` or `POSITION` |
| `handling_time` | `int` | Minutes for estimated wait (10-100) |
| `default_handling_time` | `int` | Default handling minutes (1-100) |
| `queue_position` | `int` | Position threshold (10-100) |
| `high_volume_message_enabled` | `bool` | |
| `estimated_waiting_time` | `int` | Seconds (10-600) |
| `callback_option_enabled` | `bool` | Default: false |
| `minimum_estimated_callback_time` | `int` | Minutes; default: 30 |
| `international_callback_enabled` | `bool` | Default: false |
| `play_updated_estimated_wait_message` | `bool` | |

#### `ComfortMessageSetting`

- `enabled`, `greeting`, `audio_announcement_files`
- `time_between_messages`: Interval in seconds (10-600, default 10)

#### `ComfortMessageBypass`

- `enabled`, `greeting`, `audio_announcement_files`
- `call_waiting_age_threshold`: Seconds (default 30)
- `play_announcement_after_ringing`: bool
- `ring_time_before_playing_announcement`: Seconds (default 10)

#### `MohMessageSetting`

- `normal_source`: `AudioSource` -- primary music on hold
- `alternate_source`: `AudioSource` -- alternate music on hold

### Agent/Member Management

Agents can be people, workspaces, or virtual lines. The `Agent` model:

| Field | Type | Notes |
|-------|------|-------|
| `agent_id` (alias: `id`) | `str` | Person/workspace/virtual line ID |
| `weight` | `str` | Only for WEIGHTED policy |
| `skill_level` | `int` | Only for SKILL_BASED routing |
| `join_enabled` | `bool` | Only for call queues -- agent's join status |

**Known SDK note:** The decoded value of the agent's `id` and the `type` returned are always `PEOPLE`, even for workspaces or virtual lines. This is a known platform issue that persists as of 2026-03-19. The OpenAPI spec defines `MemberType` as `["PEOPLE", "PLACE"]` and `GetPersonPlaceVirtualLineCallQueueObject.type` as `["PEOPLE", "PLACE", "VIRTUAL_LINE"]`, but the live API returns `"type": "PEOPLE"` for all agent types in queue detail responses. The `availableUsers` endpoint correctly returns `PLACE` and `VIRTUAL_LINE` types, but once assigned to a queue the type collapses to `PEOPLE`.

### Call Queue Policy Sub-API

These are additional routing policies that sit alongside the main queue configuration:

#### Holiday Service

`HolidayService` fields:
- `holiday_service_enabled`: bool
- `action`: `CPActionType` -- `BUSY` or `TRANSFER`
- `holiday_schedule_name` / `holiday_schedule_level`: Which schedule to use (from `holiday_schedules` list)
- `transfer_phone_number`: Destination when action is TRANSFER
- `play_announcement_before_enabled`: bool
- `audio_message_selection`: `Greeting` (DEFAULT/CUSTOM)
- `audio_files`: `list[AnnAudioFile]`
- `holiday_schedules`: `list[CQHolidaySchedule]` -- read-only list of available schedules

#### Night Service

`NightService` fields:
- `night_service_enabled`: bool
- `action`: `CPActionType` -- `BUSY` or `TRANSFER`
- `transfer_phone_number`: Destination when action is TRANSFER
- `announcement_mode`: `AnnouncementMode` -- `NORMAL` or `MANUAL`
- `business_hours_name` / `business_hours_level`: Schedule reference
- `force_night_service_enabled`: Override business hours
- Separate `audio_message_selection` / `audio_files` for NORMAL mode and `manual_audio_message_selection` / `manual_audio_files` for MANUAL mode
- The PUT always needs `nightServiceEnabled`, and needs `action` when enabling: `update-night-service --night-service-enabled` alone fails `400 25008 "Missing required field: action"`, and `--action TRANSFER --transfer-phone-number ...` without the enabled flag fails `"Missing required field: nightServiceEnabled"`. Verified live 2026-10-13; `--night-service-enabled --action BUSY` and `--no-night-service-enabled` (each with `--verify`) both succeeded. A transfer destination reads back normalised (`+15559876543` -> `+1-5559876543`).

#### Stranded Calls

Handles calls when all agents log off or become unavailable.

`StrandedCallsAction` enum:
| Value | Description |
|-------|-------------|
| `NONE` | Calls remain in queue |
| `BUSY` | Fast-busy tone |
| `TRANSFER` | Transfer to number |
| `NIGHT_SERVICE` | Use night service config |
| `RINGING` | Play ringback until caller hangs up |
| `ANNOUNCEMENT` | Play announcement in loop |

#### Forced Forward

Temporarily diverts all incoming calls to a destination. Calls already in the queue remain queued.

`ForcedForward` fields:
- `forced_forward_enabled`: bool
- `transfer_phone_number`: Destination
- `play_announcement_before_enabled`: bool
- `audio_message_selection`: Greeting
- `audio_files`: list[AnnAudioFile]

### Announcement Files Sub-API

`Announcement` model: `name` (alias: `fileName`), `size` (alias: `fileSize`)

**Upload is supported via the Announcement Repository API** (`POST /telephony/config/announcements` or `POST /telephony/config/locations/{locationId}/announcements` with multipart/form-data). See [location-calling-media.md](location-calling-media.md) section 1.

### Phone Number/Extension Assignment

Same pattern as auto attendants.

### Org-Level Call Queue Settings

`CallQueueSettings` (applies organization-wide):

| Field | Type | Notes |
|-------|------|-------|
| `maintain_queue_position_for_sim_ring_enabled` | `bool` | Optimized simultaneous ring algorithm |
| `force_agent_unavailable_on_bounced_enabled` | `bool` | Set agent unavailable on bounced calls |
| `play_tone_to_agent_for_barge_in_enabled` | `bool` | |
| `play_tone_to_agent_for_silent_monitoring_enabled` | `bool` | |
| `play_tone_to_agent_for_supervisor_coaching_enabled` | `bool` | |

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List call queues:**
```python
params = {"locationId": loc_id, "max": 1000}
result = api.session.rest_get(f"{BASE}/telephony/config/queues", params=params)
queues = result.get("queues", [])
# Each item: {"id", "name", "locationId", "locationName", "phoneNumber", "extension", "enabled", ...}
```

**Get details:**
```python
cq = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}")
```

**Create call queue:**
```python
body = {
    "name": "Support Queue",
    "extension": "2000",
    "callPolicies": {
        "routingType": "PRIORITY_BASED",
        "policy": "CIRCULAR"
    }
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/queues", json=body)
new_id = result.get("id")
```

Required fields: `name`, `extension` (or `phoneNumber`), `callPolicies` (with `routingType` and `policy`).

**Update call queue:**
```python
body = {"name": "Updated Queue Name"}  # partial update — only changed fields
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}", json=body)
```

Gotcha: sending the full details object back on update fails with "Missing callingLineIdPhoneNumber" when `callingLineIdPolicy` is `CUSTOM`. Always use a partial object with only the fields you want to change.

**Delete call queue:**
```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}")
```

**Add/remove agents via raw HTTP:**
```python
# Get current details, modify agents, send partial update
cq = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}")
agents = cq.get("agents", [])
agents.append({"id": person_id})
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}",
    json={"agents": agents}
)
```

**Call queue policy sub-APIs:**
```python
# Holiday service
hs = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/holidayService")
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/holidayService", json=body)

# Night service
ns = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/nightService")
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/nightService", json=body)

# Stranded calls
sc = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/strandedCalls")
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/strandedCalls", json=body)

# Forced forward
ff = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/forcedForward")
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/forcedForward", json=body)
```

**Call forwarding settings:**
```python
fwd = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/queues/{queue_id}/callForwarding"
)
```

### CLI Examples

```bash
# List all call queues (org-wide)
wxcli call-queue list

# List call queues at a specific location
wxcli call-queue list --location-id Y2lzY29zcGFyazovL...

# Filter by name
wxcli call-queue list --name "Support Queue"

# Get details for a specific call queue
wxcli call-queue show Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID

# NOTE: `call-queue create LOC --name "Support Queue" --extension 2000` (flags only) FAILS:
#   Error: 400 25008 "Missing Mandatory field name:  callPolicies"
# The smallest body that works is name + extension + callPolicies.policy:
wxcli call-queue create Y2lzY29zcGFyazovL_LOC_ID \
  --json-body '{"name":"Support Queue","extension":"2000","callPolicies":{"policy":"CIRCULAR"}}'
# (Verified live 2026-10-13.) The CLI auto-injects a default callPolicies for hunt-group, not for call-queue.

# Create a call queue with agents and routing policy via --json-body
wxcli call-queue create Y2lzY29zcGFyazovL_LOC_ID --json-body '{
  "name": "Support Queue",
  "extension": "2000",
  "callPolicies": {
    "routingType": "PRIORITY_BASED",
    "policy": "CIRCULAR"
  },
  "queueSettings": {
    "queueSize": 15,
    "overflow": {
      "action": "PERFORM_BUSY_TREATMENT"
    }
  },
  "agents": [
    {"id": "PERSON_ID_1"},
    {"id": "PERSON_ID_2"}
  ]
}'

# Update basic fields
wxcli call-queue update Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID \
  --name "Renamed Queue" --enabled

# Update agents or complex settings via --json-body (partial update for everything EXCEPT `agents`:
# the `agents` list is a FULL REPLACE -- sending 1 of 2 existing agents removed the other. Verified
# live 2026-10-13. Resend every agent you want to keep; nested `queueSettings`/`callPolicies` merge.)
wxcli call-queue update Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID --json-body '{
  "agents": [
    {"id": "PERSON_ID_1"},
    {"id": "PERSON_ID_2"},
    {"id": "PERSON_ID_3"}
  ]
}'

# Delete a call queue
wxcli call-queue delete Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID --force

# List all call queue agents (org-wide or filtered)
wxcli call-queue list-agents
wxcli call-queue list-agents --queue-id Y2lzY29zcGFyazovL_QUEUE_ID

# Get call forwarding settings
wxcli call-queue show-call-forwarding Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID

# View holiday service settings
# WARNING (CLI bug, verified live 2026-10-13): list-holiday-service, list-night-service,
# list-forced-forward and list-stranded-calls print `[]` even though the API returns 200 with the
# settings (they only look for an `audioFiles` key in a single-object response). `[]` does NOT mean
# the service is off. Until fixed, read the state with raw HTTP (GET .../queues/{id}/nightService etc.);
# `--verify` on the matching `update-*` command only confirms the fields you just sent.
wxcli call-queue list-holiday-service Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID

# View night service, stranded calls, forced forward
wxcli call-queue list-night-service Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID
wxcli call-queue list-stranded-calls Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID
wxcli call-queue list-forced-forward Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_QUEUE_ID

# List available agents for a location
wxcli call-queue list-available-agents-queues --location-id Y2lzY29zcGFyazovL_LOC_ID
```

---

## 3. Hunt Groups

### Overview

Hunt groups route incoming calls to a group of people or workspaces using a configurable ring pattern. Unlike call queues, hunt groups do not hold calls in a queue -- they ring agents directly according to the routing policy, and if no one answers, the call follows no-answer/busy redirect rules.

Use a hunt group when calls should ring agents directly without queuing (small teams, on-call groups).

### Key Data Models

#### `HuntGroup` (extends `HGandCQ`)

| Field | Type | Required for Create | Notes |
|-------|------|:-------------------:|-------|
| `name` | `str` | Yes | Unique name |
| `phone_number` | `str` | One of phone_number/extension | |
| `extension` | `str` | One of phone_number/extension | |
| `agents` | `list[Agent]` | No | Empty by default on creation |
| `call_policies` | `HGCallPolicies` | No (CLI) / **Yes (raw API)** | Auto-defaulted to CIRCULAR if not provided -- **only by `wxcli hunt-group create`** (raw POST without it: `400 25008 "Missing Mandatory field name:  callPolicies"`, verified live 2026-10-13) (the CLI does this with `setdefault('callPolicies', ...)`; the call-queue command does not). Only `policy` is needed inside it: `{"callPolicies":{"policy":"CIRCULAR"}}` created a group live and the server filled in `noAnswer`. Verified live 2026-10-13. |
| `enabled` | `bool` | No | |
| `language_code` | `str` | No | |
| `time_zone` | `str` | No | |
| `alternate_numbers` | `list[AlternateNumber]` | No | Up to 10 |
| `hunt_group_caller_id_for_outgoing_calls_enabled` | `bool` | No | Use hunt group as outbound caller ID |

#### `HGCallPolicies`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `policy` | `Policy` | `CIRCULAR` | Same Policy enum as call queues |
| `waiting_enabled` | `bool` | `False` | If false, acts as "advance when busy" -- skips agents on a call |
| `group_busy_enabled` | `bool` | No default | Set hunt group to busy status; all new calls get busy treatment |
| `allow_members_to_control_group_busy_enabled` | `bool` | No default | Let agents toggle group busy |
| `no_answer` | `NoAnswer` | See below | What happens when no agent answers |
| `busy_redirect` | `BusinessContinuity` | See below | Where to send calls when all agents busy or group is busy |
| `business_continuity_redirect` | `BusinessContinuity` | See below | Fallback when phone disconnected (power outage, etc.) |

#### `NoAnswer`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `next_agent_enabled` | `bool` | `False` | Advance to next agent after rings |
| `next_agent_rings` | `int` | `5` (server) / `3` (`wxcli hunt-group create`) | Rings before advancing. Verified live 2026-10-13: a group created via `--json-body '{"callPolicies":{"policy":"REGULAR"}}'` (CLI default NOT injected) reads back `nextAgentEnabled` false, `nextAgentRings` 5, `numberOfRings` 15; a group created with only name/extension/enabled reads back `nextAgentEnabled` true, `nextAgentRings` 3 because the CLI injects `noAnswer` (`hunt_group.py` `body.setdefault('callPolicies', ...)`). |
| `forward_enabled` | `bool` | `False` | Forward unanswered calls |
| `destination` | `str` | None | Forward-to number |
| `number_of_rings` | `int` | `15` | Rings before forwarding |
| `system_max_number_of_rings` | `int` | `20` | Read-only system maximum |
| `destination_voicemail_enabled` | `bool` | `False` | Send to destination's voicemail (prefixes `*55`) |

#### `BusinessContinuity`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `enabled` | `bool` | `False` | |
| `destination` | `str` | None | Redirect target |
| `destination_voicemail_enabled` | `bool` | `False` | |

### Agent/Member Management

Hunt group agents use the same `Agent` model as call queues. To modify agents, update the hunt group with the new agent list -- see the raw HTTP add/remove agents example further below in this section.

**Key difference from call queues:** Hunt groups do not have a `join_enabled` toggle on agents. All agents in the group receive calls (subject to the `waiting_enabled` setting).

### Forwarding

Hunt groups have a `forwarding` sub-resource. See [Shared Forwarding API](#4-shared-forwarding-api).

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List hunt groups:**
```python
params = {"locationId": loc_id, "max": 1000}
result = api.session.rest_get(f"{BASE}/telephony/config/huntGroups", params=params)
hgs = result.get("huntGroups", [])
# Each item: {"id", "name", "locationId", "locationName", "phoneNumber", "extension", "enabled", ...}
```

**Get details:**
```python
hg = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/huntGroups/{hg_id}")
```

**Create hunt group:**
```python
body = {
    "name": "Sales Team",
    "extension": "3000",
    "callPolicies": {"policy": "CIRCULAR"}      # REQUIRED on the raw API (see below)
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/huntGroups", json=body)
new_id = result.get("id")
```

Required fields: `name`, `extension` (or `phoneNumber`), `callPolicies.policy`. **The raw API does NOT default `callPolicies`:** a POST of `{"name","extension"}` returns `400 25008 "Missing Mandatory field name:  callPolicies"` (Verified live 2026-10-13, direct HTTP POST). The "defaults to CIRCULAR" behaviour belongs to `wxcli hunt-group create`, which injects a `callPolicies` before sending. Agents are optional at creation -- can be added later via update.

**Update hunt group:**
```python
body = {"name": "Updated Team Name"}  # partial update — only changed fields
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/huntGroups/{hg_id}", json=body)
```

**Delete hunt group:**
```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/huntGroups/{hg_id}")
```

**Add/remove agents via raw HTTP:**
```python
hg = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/huntGroups/{hg_id}")
agents = hg.get("agents", [])
agents.append({"id": person_id})
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/huntGroups/{hg_id}",
    json={"agents": agents}
)
```

**Call forwarding settings:**
```python
fwd = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/huntGroups/{hg_id}/callForwarding"
)
```

### CLI Examples

```bash
# List all hunt groups (org-wide)
wxcli hunt-group list

# List hunt groups at a specific location
wxcli hunt-group list --location-id Y2lzY29zcGFyazovL...

# Filter by name
wxcli hunt-group list --name "Sales Team"

# Get details for a specific hunt group
wxcli hunt-group show Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_HG_ID

# Create a basic hunt group
wxcli hunt-group create Y2lzY29zcGFyazovL_LOC_ID \
  --name "Sales Team" \
  --extension "3000" \
  --enabled

# Create with agents and call policies via --json-body
wxcli hunt-group create Y2lzY29zcGFyazovL_LOC_ID --json-body '{
  "name": "Sales Team",
  "extension": "3000",
  "enabled": true,
  "callPolicies": {
    "policy": "SIMULTANEOUS",
    "noAnswer": {
      "nextAgentEnabled": true,
      "nextAgentRings": 3,
      "forwardEnabled": true,
      "destination": "+15551234567",
      "numberOfRings": 10
    }
  },
  "agents": [
    {"id": "PERSON_ID_1"},
    {"id": "PERSON_ID_2"}
  ]
}'

# Update basic fields
wxcli hunt-group update Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_HG_ID \
  --name "Renamed Team" --enabled

# Update agents via --json-body (`agents` is a FULL REPLACE: omitted agents are removed; nested
# `callPolicies` merges. Verified live 2026-10-13.)
wxcli hunt-group update Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_HG_ID --json-body '{
  "agents": [
    {"id": "PERSON_ID_1"},
    {"id": "PERSON_ID_2"},
    {"id": "PERSON_ID_3"}
  ]
}'

# Delete a hunt group
wxcli hunt-group delete Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_HG_ID --force

# Get call forwarding settings
wxcli hunt-group show-call-forwarding Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_HG_ID

# Create a selective call forwarding rule
wxcli hunt-group create-selective-rules Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_HG_ID --json-body '{
  "name": "After Hours Rule",
  "enabled": true,
  "businessSchedule": "Business Hours",
  "forwardTo": {"selection": "FORWARD_TO_SPECIFIED_NUMBER", "phoneNumber": "+15559876543"},
  "callsFrom": {"selection": "ANY"},
  "callsTo": {"selection": "ANY"}
}'
```

---

## 4. Shared Forwarding API

All three features (auto attendants, call queues, hunt groups) use the same call-forwarding endpoint pattern, differing only in the feature path segment.

### API Endpoints

Base: `telephony/config/locations/{locationId}/{feature}/{featureId}/callForwarding`

### Key Data Models

#### `CallForwarding`

| Field | Type | Notes |
|-------|------|-------|
| `always` | `ForwardingSetting` | Forward all calls unconditionally |
| `selective` | `ForwardingSetting` | Forward based on rules |
| `rules` | `list[ForwardingRule]` | Summary list of selective rules |
| `operating_modes` | `ForwardOperatingModes` | Mode-based forwarding |

#### `ForwardingSetting`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | |
| `destination` | `str` | Forward-to number |
| `ring_reminder_enabled` | `bool` | Brief tone on agent's phone |
| `destination_voice_mail_enabled` | `bool` | Send to voicemail if destination is internal with VM |

#### `ForwardingRuleDetails`

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Rule name |
| `id` | `str` | Rule ID (read-only, changes on name update) |
| `enabled` | `bool` | |
| `holiday_schedule` | `str` | Schedule name for holiday-based rules |
| `business_schedule` | `str` | Schedule name for business-hours rules |
| `forward_to` | `ForwardTo` | `FORWARD_TO_DEFAULT_NUMBER`, `FORWARD_TO_SPECIFIED_NUMBER`, or `DO_NOT_FORWARD` |
| `calls_to` | `ForwardCallsTo` | Which incoming numbers trigger the rule |
| `calls_from` | `CallsFrom` | `ANY` or `CUSTOM` with specific numbers |

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

The forwarding URL pattern is the same for all three features -- substitute the feature path segment:

| Feature | Path segment |
|---------|-------------|
| Auto Attendant | `autoAttendants` |
| Call Queue | `queues` |
| Hunt Group | `huntGroups` |

```python
BASE = "https://webexapis.com/v1"
feature = "autoAttendants"  # or "queues" or "huntGroups"
feature_id = aa_id           # or queue_id or hg_id

# Get forwarding settings
fwd = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/{feature}/{feature_id}/callForwarding"
)

# Update forwarding settings
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/{feature}/{feature_id}/callForwarding",
    json={"callForwarding": {"always": {"enabled": True, "destination": "+15551234567"}}}
)
# The "callForwarding" wrapper is REQUIRED. A body of {"always": {...}} returns 200 but is
# silently ignored (verified live 2026-10-13 on auto attendant, call queue and hunt group:
# the read-back stayed enabled=true after {"always": {"enabled": false}}).

# Create selective forwarding rule
rule_body = {
    "name": "After Hours Rule",
    "enabled": True,
    "businessSchedule": "Business Hours",
    "forwardTo": {"selection": "FORWARD_TO_SPECIFIED_NUMBER", "phoneNumber": "+15559876543"},
    "callsFrom": {"selection": "ANY"},
    "callsTo": {"selection": "ANY"}
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/{feature}/{feature_id}/callForwarding/selectiveRules",
    json=rule_body
)
rule_id = result.get("id")

# Get / update / delete a selective rule
rule = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/{feature}/{feature_id}/callForwarding/selectiveRules/{rule_id}"
)
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/{feature}/{feature_id}/callForwarding/selectiveRules/{rule_id}",
    json={"name": rule_name, "enabled": False}   # name is required on update (Verified live 2026-10-13: {"enabled": False} alone -> 400 25008 "Missing Mandatory field name:  name")
)
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/{feature}/{feature_id}/callForwarding/selectiveRules/{rule_id}"
)
```

Gotcha: when you update a selective rule's `name`, the rule ID changes. The update response returns the new ID.

### CLI Examples

The forwarding commands follow the same pattern across all three features. Substitute the feature command group (`auto-attendant`, `call-queue`, or `hunt-group`). The update body nests `always` (and `selective`, `rules`, `operatingModes`) under a top-level `callForwarding` object — the spec requires it on the auto attendant.

```bash
# Get call forwarding settings (same pattern for all three features)
wxcli auto-attendant show-call-forwarding LOC_ID AA_ID
wxcli call-queue show-call-forwarding LOC_ID QUEUE_ID
wxcli hunt-group show-call-forwarding LOC_ID HG_ID

# Update call forwarding — enable always-forward via --json-body
wxcli auto-attendant update-call-forwarding LOC_ID AA_ID --json-body '{
  "callForwarding": {"always": {"enabled": true, "destination": "+15551234567"}}
}'

wxcli call-queue update-call-forwarding LOC_ID QUEUE_ID --json-body '{
  "callForwarding": {"always": {"enabled": true, "destination": "+15551234567"}}
}'

wxcli hunt-group update-call-forwarding LOC_ID HG_ID --json-body '{
  "callForwarding": {"always": {"enabled": true, "destination": "+15551234567"}}
}'

# Create a selective forwarding rule. The flags-only form
#   wxcli auto-attendant create-selective-rules LOC_ID AA_ID --name "After Hours Rule" --enabled --business-schedule "..."
# FAILS 400 25008 "Missing Mandatory field name:  forwardTo" (forwardTo/callsFrom have no flags).
# Use --json-body with forwardTo + callsFrom (Verified live 2026-10-13; schedule must be an existing name):
wxcli auto-attendant create-selective-rules LOC_ID AA_ID --json-body '{
  "name": "After Hours Rule", "enabled": true, "businessSchedule": "Business Hours",
  "forwardTo": {"selection": "FORWARD_TO_SPECIFIED_NUMBER", "phoneNumber": "+15559876543"},
  "callsFrom": {"selection": "ANY"}, "callsTo": {"selection": "ANY"}
}'

# Create a selective rule with full config via --json-body
# (Verified live 2026-10-13 with businessSchedule in place of holidaySchedule. `"callsTo":{"selection":"ANY"}`
# is accepted but reads back as `"callsTo":{"numbers":[]}` -- the server has no `selection` for callsTo.)
wxcli call-queue create-selective-rules LOC_ID QUEUE_ID --json-body '{
  "name": "Holiday Redirect",
  "enabled": true,
  "holidaySchedule": "Company Holidays",
  "forwardTo": {"selection": "FORWARD_TO_SPECIFIED_NUMBER", "phoneNumber": "+15559876543"},
  "callsFrom": {"selection": "ANY"},
  "callsTo": {"selection": "ANY"}
}'

# Get, update, and delete selective rules
wxcli hunt-group show-selective-rules LOC_ID HG_ID RULE_ID
# `name` is required on every update (without it: 400 25008 "Missing Mandatory field name:  name");
# other fields you omit (forwardTo, schedule) are preserved. Verified live 2026-10-13 (call queue).
wxcli hunt-group update-selective-rules LOC_ID HG_ID RULE_ID --json-body '{"name": "After Hours Rule", "enabled": false}'
wxcli hunt-group delete-selective-rules LOC_ID HG_ID RULE_ID --force

# Switch to normal operating mode
wxcli auto-attendant switch-mode-for LOC_ID AA_ID
wxcli call-queue switch-mode-for LOC_ID QUEUE_ID
wxcli hunt-group switch-mode-for LOC_ID HG_ID
```

> **Verified live 2026-10-13** (all three features: auto attendant, call queue, hunt group): the
> `callForwarding` wrapper in the `update-call-forwarding` bodies is required. With the wrapper,
> `{"callForwarding":{"always":{"enabled":true,"destination":"+15559876543"}}}` took effect on the
> read-back (`show-call-forwarding`); without it, `{"always":{"enabled":false}}` returned
> `{"status": "updated"}` and changed nothing. A 2xx here is not evidence the setting applied.

---

## 5. Common Data Models (HG/CQ Base)

`HGandCQ` is the shared base class for both `CallQueue` and `HuntGroup`.

### `HGandCQ` Fields

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | |
| `id` | `str` | Read-only |
| `location_name` | `str` | Only from `list()` |
| `location_id` | `str` | Only from `list()` |
| `phone_number` | `str` | Primary number |
| `extension` | `str` | |
| `routing_prefix` | `str` | Location routing prefix |
| `esn` | `str` | Routing prefix + extension |
| `calling_line_id_policy` | `CallingLineIdPolicy` | `DIRECT_LINE`, `LOCATION_NUMBER`, or `CUSTOM` |
| `calling_line_id_phone_number` | `str` | Shown when policy is CUSTOM |
| `alternate_number_settings` | `AlternateNumberSettings` | Up to 10 alternate numbers with distinctive ring |
| `enabled` | `bool` | |
| `toll_free_number` | `bool` | Read-only |
| `language` / `language_code` | `str` | |
| `first_name` / `last_name` | `str` | Caller ID display names |
| `time_zone` | `str` | |
| `agents` | `list[Agent]` | |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | |
| `dial_by_name` | `str` | |

### `AlternateNumberSettings`

| Field | Type | Notes |
|-------|------|-------|
| `distinctive_ring_enabled` | `bool` | Default: True |
| `alternate_numbers` | `list[AlternateNumber]` | Up to 10 numbers |

### `Agent`

| Field | Type | Notes |
|-------|------|-------|
| `agent_id` (alias: `id`) | `str` | Person, workspace, or virtual line ID |
| `phone_number` | `str` | Read-only in responses |
| `extension` | `str` | Read-only in responses |
| `weight` | `str` | Only for WEIGHTED policy |
| `skill_level` | `int` | Only for SKILL_BASED routing |
| `join_enabled` | `bool` | Call queues only |
| `location` | `IdAndName` | Read-only |
| `has_cx_essentials` | `bool` | Read-only |

When creating/updating, only `agent_id` is required. Set `weight` or `skill_level` as needed for the routing policy.

---

## 6. Required Scopes

| Operation | Scope |
|-----------|-------|
| Read (list, details, settings) | `spark-admin:telephony_config_read` |
| Write (create, update, delete) | `spark-admin:telephony_config_write` |

- **Full administrator** or **read-only administrator** tokens work for read operations.
- **Full administrator** or **location administrator** tokens are required for write operations.
- A **partner administrator** can use the `orgId` query parameter to manage customer organizations.

---

## 7. Dependencies

### Prerequisites for All Three Features

1. **Location must exist** -- all features are scoped to a location (`location_id` is required for create/details/update/delete).
2. **Phone number or extension** -- at least one must be provided at creation. Numbers must be unassigned and associated with the target location. Use the `primary_available_phone_numbers()` method to find candidates.
3. **Schedules** -- auto attendants require a `business_schedule` at creation. Call queue holiday/night service policies reference named schedules that must already exist at the org or location level.

### Call Queue Specific

4. **Agents** -- must be existing people, workspaces, or virtual lines. Users with Webex Calling Standard license are excluded from available agents.
5. **Queue size** -- must be specified either via `queue_size` parameter or a `QueueSettings` object.
6. **Customer Assist** -- if creating a Customer Assist (formerly CX Essentials) queue, agents must have the Customer Assist license.

### Hunt Group Specific

7. **Agents** -- same types as call queues (people, workspaces, virtual lines). A hunt group can be created with no agents and agents added later.

### Auto Attendant Specific

8. **Audio files** -- custom greetings require announcement audio files uploaded via the Announcement Repository API (`POST /telephony/config/announcements` with multipart/form-data). See [location-calling-media.md](location-calling-media.md) section 1 for upload details. WAV and WMA formats supported.
9. **FedRAMP** -- `directLineCallerIdName`, `customName`, and `dialByName` are not available in Webex for Government. Use `firstName`/`lastName` instead. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

### Auto Attendant API Gotchas

10. **`wxcli auto-attendant update` option flags cover only scalar fields** -- the CLI `update` command takes `LOCATION_ID AUTO_ATTENDANT_ID` as positional arguments and accepts `--name`, `--phone-number`, `--extension`, `--first-name`, `--last-name`, `--language-code`, `--business-schedule`, `--holiday-schedule`, `--extension-dialing`, `--name-dialing`, `--time-zone`, `--dial-by-name`. There is no `--enabled` flag. Menu configuration (`businessHoursMenu`, `afterHoursMenu`) has no option flags -- pass it via `--json-body`, which the CLI sends verbatim as the PUT body to `telephony/config/locations/{locationId}/autoAttendants/{aaId}`. Raw HTTP is not required.

11. **`keyConfigurations.value` is optional for actions with no destination** (`TRANSFER_TO_OPERATOR`, `REPEAT_MENU`, `NAME_DIALING`, `EXTENSION_DIALING`, `EXIT`) -- omit it or send `""`; both are accepted (the server drops an empty `value` on read-back). Verified live 2026-10-13: a PUT whose keys 0-3 carried no `value` at all returned 200 and read back correctly. (An earlier version of this entry said `value` was mandatory; that did not reproduce. Sending `null` was not tested.) The error `25008 Missing Mandatory field name:  HoursMenu.keyConfigurations.value` is real, but in the live test it came from `TRANSFER_TO_MAILBOX` with `"value":""` -- see #12.

12. **`TRANSFER_TO_MAILBOX` requires a non-empty `value`** -- empty string `""` is rejected with `25008 Missing Mandatory field name:  HoursMenu.keyConfigurations.value`. Use the target AA's own extension (e.g., `"8000"`) to route to the AA's own voicemail. This is the extension of the auto attendant whose mailbox should receive the call. Verified live 2026-10-13: `""` rejected; the AA's own extension (`9709`) accepted.

13. **There is no `holidayMenu` field in the AA PUT body** -- the `holidayMenu` field is silently ignored by the API (verified live 2026-10-13: PUT returned 200 and the read-back contains no `holiday` key). The `afterHoursMenu` applies to both after-hours and holiday schedule periods. If you need different routing on holidays vs. after-hours, you need two separate auto attendants (one for after-hours, one for holidays).

14. **After-hours phone numbers are normalized on read-back** -- a number sent as `+19195559876` returns as `+1-9195559876` in GET responses. Do not use the GET value as input to a subsequent PUT; use the original format. Verified live 2026-10-13 for an AA menu key `value` (`+19195559876` -> `+1-9195559876`), a CQ `overflow.transferNumber`/forced-forward `transferPhoneNumber` (`+15559876543` -> `+1-5559876543`); a `callForwarding.always.destination` and a hunt-group `noAnswer.destination` were returned as sent.

---

## Appendix: Feature Comparison

| Capability | Auto Attendant | Call Queue | Hunt Group |
|------------|:--------------:|:----------:|:----------:|
| IVR menu with key-press routing | Yes | No | No |
| Hold calls in queue | No | Yes | No |
| Ring agents by policy | No | Yes | Yes |
| Business/after-hours menus | Yes | Via policies | Via `waiting_enabled` / `no_answer` |
| Holiday service | Via schedule | Yes (policy API) | Via forwarding rules (schedule-based) |
| Night service | Via schedule | Yes (policy API) | Via forwarding rules (schedule-based) |
| Stranded calls handling | N/A | Yes (policy API) | N/A |
| Forced forward | N/A | Yes (policy API) | N/A |
| Agent join/unjoin | N/A | Yes | No |
| Agent skill-based routing | N/A | Yes | No |
| Agent weight-based routing | N/A | Yes | Yes |
| Whisper message to agent | N/A | Yes | No |
| Comfort/wait messages | N/A | Yes | No |
| Music on hold | N/A | Yes | No |
| Max agents (simultaneous) | N/A | 50 | 50 |
| Max agents (WEIGHTED) | N/A | 100 | 100 |
| Max agents (CIRCULAR/REGULAR/UNIFORM) | N/A | 1,000 | 1,000 |
| Shared forwarding API | Yes | Yes | Yes |
| Announcement file management | Yes | Yes | No |

---

## Gotchas (Cross-Cutting)

1. **Hunt groups ignore member personal call forwarding.** HG calls route directly to the agent's device and bypass any personal call forwarding the member has configured. Only the hunt group's own no-answer/forwarding settings govern overflow behavior.

2. **DND on a hunt group member skips them, not their voicemail.** If a member has DND enabled, the hunt group skips that member and moves to the next — it does NOT send the call to the member's personal voicemail. The HG's no-answer action only triggers after all members are exhausted.

3. **Partial updates are safer than full-object PUTs.** For all three features (AA, CQ, HG), sending the full GET response back as a PUT body can trigger validation errors on read-only or computed fields (e.g., `callingLineIdPolicy=CUSTOM` without a phone number on CQ). Always send only the fields you want to change. (Live 2026-10-13: a full `call-queue show` object PUT back unchanged succeeded twice, so the failure is not universal; the `callingLineIdPolicy=CUSTOM` 400 itself did not reproduce — `{"callingLineIdPolicy":"CUSTOM","callingLineIdPhoneNumber":"+15559876543"}` returned 200 and the queue still read back `LOCATION_NUMBER`. Partial updates remain the safe default.)

2. **`--json-body` is required for nested settings.** The CLI generator skips deeply nested object/array body fields. Menu configurations (AA), queue settings with announcements (CQ), and call policies with no-answer/bounce config (HG) all require `--json-body '{ ... }'` instead of individual flags.

3. **Phone numbers normalize differently on read-back.** Numbers sent as `+19195559876` may return as `+1-9195559876` in GET responses. Do not round-trip GET values into PUT requests without stripping the dashes.

4. **Agents share the same model but differ in behavior.** The `Agent` object is used by both CQ and HG, but `joinEnabled` only applies to call queues, and `skillLevel` only applies to `SKILL_BASED` routing in CQ. Sending these fields to the wrong feature is silently ignored.

5. **Selective forwarding rule IDs change on name update.** Across all three features, renaming a selective forwarding rule changes its ID. The update response returns the new ID — capture it if you need to reference the rule again.

6. **Audio file upload IS supported via API.** Use the Announcement Repository API (`POST /telephony/config/announcements` or `POST /telephony/config/locations/{locationId}/announcements`) with multipart/form-data encoding. Supports WAV and WMA formats. See [location-calling-media.md](location-calling-media.md) section 1 for full upload details and examples.

---

## Migration Notes — CUCM Forwarding & Night Service

The CUCM-to-Webex migration pipeline writes hunt group and call queue forwarding via these per-feature endpoints:

- `PUT /telephony/config/locations/{locationId}/huntGroups/{huntGroupId}/callForwarding`
- `PUT /telephony/config/locations/{locationId}/queues/{queueId}/callForwarding`
- `PUT /telephony/config/locations/{locationId}/queues/{queueId}/holidayService`
- `PUT /telephony/config/locations/{locationId}/queues/{queueId}/nightService`
- `PUT /telephony/config/locations/{locationId}/queues/{queueId}/strandedCalls`
- `PUT /telephony/config/locations/{locationId}/autoAttendants/{autoAttendantId}/callForwarding`

All endpoints require the same scope as feature creation (`spark-admin:telephony_config_write`). The migration tool only writes these settings when the corresponding CUCM source data is present; features without forwarding configuration are created with Webex defaults.

---

## See Also

- [Provisioning Reference](provisioning.md) -- creating locations and users (prerequisites for all features in this doc)
- [Additional Call Features](call-features-additional.md) -- Paging Groups, Call Park, Call Pickup, Voicemail Groups, and Customer Assist (Call Park recall uses Hunt Groups; Voicemail Groups can serve as overflow destinations for CQ/HG)
- [Call Routing & PSTN](call-routing.md) -- dial plans, trunks, and route lists (AA/CQ/HG phone numbers participate in the call routing chain)
- [Location Call Settings: Media](location-calling-media.md) -- schedule management (business hours and holiday schedules used by AA menus and CQ/HG policies)
