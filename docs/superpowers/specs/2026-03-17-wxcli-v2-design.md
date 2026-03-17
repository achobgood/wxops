# wxcli v2 — Core Call Features

**Date:** 2026-03-17
**Status:** Reviewed
**Author:** Adam Hobgood + Claude
**Depends on:** wxcli v0.1.0 (shipped)
**Spec:** Verified against wxc-sdk method signatures (all 9 APIs inspected)

## Problem

wxcli v0.1.0 handles provisioning (locations, users, numbers, licenses) but can't configure call features. After standing up a site, you still need Control Hub to create auto attendants, hunt groups, call queues, schedules, etc. This makes the CLI incomplete for autonomous operation.

## Solution

Add 9 command groups covering core call features. Each group follows the same CRUD + feature-specific pattern established in v1.

## Goals

- 54 commands across 9 groups
- Every write command verified against exact SDK method signatures
- Parallel implementation (9 independent files, 9 subagents)
- Full autonomy: Claude can provision a complete Webex Calling site without Control Hub

## Architecture

Same pattern as v1: one Typer sub-app per command group, registered in `main.py`.

```
src/wxcli/commands/
├── (existing v1 files)
├── schedules.py           # Must come first — AA/HG/CQ reference schedules
├── operating_modes.py     # Business hours, holidays
├── auto_attendants.py     # IVR menus
├── hunt_groups.py         # Ring groups
├── call_queues.py         # ACD queues
├── call_park.py           # Park/retrieve
├── call_pickup.py         # Pickup groups
├── paging.py              # Overhead paging
└── voicemail_groups.py    # Shared voicemail
```

---

## 1. Schedules (`wxcli schedules`)

SDK: `api.telephony.schedules` (`ScheduleApi`)

Note: `obj_id` parameter is the location_id for location-level schedules.

### Commands

```bash
wxcli schedules list --location <id>
wxcli schedules show --location <id> --type <businessHours|holidays> --schedule-id <id>
wxcli schedules create --location <id> --name "..." --type <businessHours|holidays>
wxcli schedules update --location <id> --type <type> --schedule-id <id> --name "..."
wxcli schedules delete --location <id> --type <type> --schedule-id <id>
# Event sub-commands (holidays are events within a holiday schedule)
wxcli schedules add-event --location <id> --type <type> --schedule-id <id> --name "..." --start-date YYYY-MM-DD --end-date YYYY-MM-DD [--all-day]
wxcli schedules show-event --location <id> --type <type> --schedule-id <id> --event-id <id>
wxcli schedules delete-event --location <id> --type <type> --schedule-id <id> --event-id <id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `schedules.list` | `(obj_id: str, schedule_type: ScheduleType = None, name: str = None)` |
| show | `schedules.details` | `(obj_id: str, schedule_type: ScheduleType, schedule_id: str)` |
| create | `schedules.create` | `(obj_id: str, schedule: Schedule)` → returns `str` |
| update | `schedules.update` | `(obj_id: str, schedule: Schedule, schedule_type: ScheduleType, schedule_id: str)` |
| delete | `schedules.delete_schedule` | `(obj_id: str, schedule_type: ScheduleType, schedule_id: str)` |
| add-event | `schedules.event_create` | `(obj_id: str, schedule_type: ScheduleType, schedule_id: str, event: Event)` |
| show-event | `schedules.event_details` | `(obj_id: str, schedule_type: ScheduleType, schedule_id: str, event_id: str)` |
| delete-event | `schedules.event_delete` | `(obj_id: str, schedule_type: ScheduleType, schedule_id: str, event_id: str)` |

### Model: Schedule

Required for create: `name`, `schedule_type` (ScheduleType enum: `businessHours`, `holidays`)

### Model: Event

Required for add-event: `name`, `start_date`, `end_date`. Optional: `start_time`, `end_time`, `all_day_enabled`, `recurrence`.

---

## 2. Operating Modes (`wxcli operating-modes`)

SDK: `api.telephony.operating_modes` (`OperatingModesApi`)

Note: Operating modes are org-level (no location_id on create). But `available_operating_modes` is per-location.

### Commands

```bash
wxcli operating-modes list [--location <id>] [--name "..."]
wxcli operating-modes show <mode-id>
wxcli operating-modes create --name "..." --type <sameHoursDaily|differentHoursDaily>
wxcli operating-modes update <mode-id> --name "..."
wxcli operating-modes available --location <id>
# Holiday sub-commands
wxcli operating-modes add-holiday <mode-id> --name "..." --start-date YYYY-MM-DD --end-date YYYY-MM-DD
wxcli operating-modes delete-holiday <mode-id> --holiday-id <id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `operating_modes.list` | `(limit_to_location_id: str = None, name: str = None)` |
| show | `operating_modes.details` | `(mode_id: str)` |
| create | `operating_modes.create` | `(settings: OperatingMode)` → returns `str` |
| update | `operating_modes.update` | `(mode_id: str, settings: OperatingMode)` |
| available | `operating_modes.available_operating_modes` | `(location_id: str)` |
| add-holiday | `operating_modes.holiday_create` | `(mode_id: str, settings: OperatingModeHoliday)` → returns `str` |
| delete-holiday | `operating_modes.holiday_delete` | `(mode_id: str, holiday_id: str)` |

### Model: OperatingMode

Fields: `name`, `type` (OperatingModeSchedule), `level` (ScheduleLevel), `location` (IdAndName), `same_hours_daily`, `different_hours_daily`, `holidays`, `call_forwarding`.

---

## 3. Auto Attendants (`wxcli auto-attendants`)

SDK: `api.telephony.auto_attendant` (`AutoAttendantApi`)

### Commands

```bash
wxcli auto-attendants list [--location <id>] [--name "..."]
wxcli auto-attendants show --location <id> <aa-id>
wxcli auto-attendants create --location <id> --name "..." --extension "..." [--phone-number "..."] [--business-schedule "..."] [--holiday-schedule "..."]
wxcli auto-attendants update --location <id> <aa-id> --name "..." [--enabled true|false]
wxcli auto-attendants delete --location <id> <aa-id>
wxcli auto-attendants list-announcements --location <id> <aa-id>
wxcli auto-attendants delete-announcement --location <id> <aa-id> --file-name "..."
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `auto_attendant.list` | `(location_id: str = None, name: str = None, phone_number: str = None)` |
| show | `auto_attendant.details` | `(location_id: str, auto_attendant_id: str)` |
| create | `auto_attendant.create` | `(location_id: str, settings: AutoAttendant)` → returns `str` |
| update | `auto_attendant.update` | `(location_id: str, auto_attendant_id: str, settings: AutoAttendant)` |
| delete | `auto_attendant.delete_auto_attendant` | `(location_id: str, auto_attendant_id: str)` |
| list-announcements | `auto_attendant.list_announcement_files` | `(location_id: str, auto_attendant_id: str)` |
| delete-announcement | `auto_attendant.delete_announcement_file` | `(location_id: str, auto_attendant_id: str, file_name: str)` |

### Model: AutoAttendant

Key fields for create: `name`, `extension`, `phone_number`, `enabled`, `business_schedule`, `holiday_schedule`, `business_hours_menu` (AutoAttendantMenu), `after_hours_menu` (AutoAttendantMenu), `language_code`, `time_zone`.

---

## 4. Hunt Groups (`wxcli hunt-groups`)

SDK: `api.telephony.huntgroup` (`HuntGroupApi`)

### Commands

```bash
wxcli hunt-groups list [--location <id>] [--name "..."]
wxcli hunt-groups show --location <id> <hg-id>
wxcli hunt-groups create --location <id> --name "..." --extension "..." [--phone-number "..."]
wxcli hunt-groups update --location <id> <hg-id> [--name "..."] [--enabled true|false]
wxcli hunt-groups delete --location <id> <hg-id>
wxcli hunt-groups add-agent --location <id> <hg-id> --agent-id <person-id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `huntgroup.list` | `(location_id: str = None, name: str = None, phone_number: str = None)` |
| show | `huntgroup.details` | `(location_id: str, huntgroup_id: str)` |
| create | `huntgroup.create` | `(location_id: str, settings: HuntGroup)` → returns `str` |
| update | `huntgroup.update` | `(location_id: str, huntgroup_id: str, update: HuntGroup)` |
| delete | `huntgroup.delete_huntgroup` | `(location_id: str, huntgroup_id: str)` |
| add-agent | Read-modify-write: `details` → append to `agents` → `update` |

### Model: HuntGroup

Key fields: `name`, `extension`, `phone_number`, `enabled`, `agents` (list[Agent]), `call_policies` (HGCallPolicies), `language_code`, `time_zone`.

Note: `add-agent` is a convenience command — the SDK has no `add_agent` method. Implementation reads current hunt group, appends the agent to the `agents` list, and calls `update`.

---

## 5. Call Queues (`wxcli call-queues`)

SDK: `api.telephony.callqueue` (`CallQueueApi`)

### Commands

```bash
wxcli call-queues list [--location <id>] [--name "..."]
wxcli call-queues show --location <id> <queue-id>
wxcli call-queues create --location <id> --name "..." --extension "..." [--phone-number "..."]
wxcli call-queues update --location <id> <queue-id> [--name "..."] [--enabled true|false]
wxcli call-queues delete --location <id> <queue-id>
wxcli call-queues add-agent --location <id> <queue-id> --agent-id <person-id>
wxcli call-queues available-agents --location <id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `callqueue.list` | `(location_id: str = None, name: str = None, phone_number: str = None)` |
| show | `callqueue.details` | `(location_id: str, queue_id: str)` |
| create | `callqueue.create` | `(location_id: str, settings: CallQueue)` → returns `str` |
| update | `callqueue.update` | `(location_id: str, queue_id: str, update: CallQueue)` |
| delete | `callqueue.delete_queue` | `(location_id: str, queue_id: str)` |
| add-agent | Read-modify-write: `details` → append to `agents` → `update` |
| available-agents | `callqueue.available_agents` | `(location_id: str, name: str = None)` |

### Model: CallQueue

Key fields: `name`, `extension`, `phone_number`, `enabled`, `agents` (list[Agent]), `call_policies` (CallQueueCallPolicies), `queue_settings` (QueueSettings), `language_code`, `time_zone`, `allow_agent_join_enabled`.

---

## 6. Call Park (`wxcli call-park`)

SDK: `api.telephony.callpark` (`CallParkApi`)

### Commands

```bash
wxcli call-park list --location <id>
wxcli call-park show --location <id> <park-id>
wxcli call-park create --location <id> --name "..."
wxcli call-park update --location <id> <park-id> [--name "..."]
wxcli call-park delete --location <id> <park-id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `callpark.list` | `(location_id: str, name: str = None)` |
| show | `callpark.details` | `(location_id: str, callpark_id: str)` |
| create | `callpark.create` | `(location_id: str, settings: CallPark)` → returns `str` |
| update | `callpark.update` | `(location_id: str, callpark_id: str, settings: CallPark)` |
| delete | `callpark.delete_callpark` | `(location_id: str, callpark_id: str)` |

### Model: CallPark

Fields: `name`, `recall` (RecallHuntGroup), `agents` (list[PersonPlaceAgent]), `park_on_agents_enabled`.

---

## 7. Call Pickup (`wxcli call-pickup`)

SDK: `api.telephony.pickup` (`CallPickupApi`)

### Commands

```bash
wxcli call-pickup list --location <id>
wxcli call-pickup show --location <id> <pickup-id>
wxcli call-pickup create --location <id> --name "..."
wxcli call-pickup update --location <id> <pickup-id> [--name "..."]
wxcli call-pickup delete --location <id> <pickup-id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `pickup.list` | `(location_id: str, name: str = None)` |
| show | `pickup.details` | `(location_id: str, pickup_id: str)` |
| create | `pickup.create` | `(location_id: str, settings: CallPickup)` → returns `str` |
| update | `pickup.update` | `(location_id: str, pickup_id: str, settings: CallPickup)` |
| delete | `pickup.delete_pickup` | `(location_id: str, pickup_id: str)` |

### Model: CallPickup

Fields: `name`, `notification_type` (PickupNotificationType), `notification_delay_timer_seconds`, `agents` (list[PersonPlaceAgent]).

---

## 8. Paging (`wxcli paging`)

SDK: `api.telephony.paging` (`PagingApi`)

### Commands

```bash
wxcli paging list [--location <id>]
wxcli paging show --location <id> <paging-id>
wxcli paging create --location <id> --name "..." --extension "..."
wxcli paging update --location <id> <paging-id> [--name "..."]
wxcli paging delete --location <id> <paging-id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `paging.list` | `(location_id: str = None, name: str = None)` |
| show | `paging.details` | `(location_id: str, paging_id: str)` |
| create | `paging.create` | `(location_id: str, settings: Paging)` → returns `str` |
| update | `paging.update` | `(location_id: str, update: Paging, paging_id: str)` |
| delete | `paging.delete_paging` | `(location_id: str, paging_id: str)` |

### Model: Paging

Key fields: `name`, `extension`, `phone_number`, `enabled`, `originators` (list[PagingAgent]), `targets` (list[PagingAgent]), `language_code`.

Note: `paging.update` has unusual parameter order — `paging_id` comes AFTER `update` (the Paging model). Must match exactly.

---

## 9. Voicemail Groups (`wxcli voicemail-groups`)

SDK: `api.telephony.voicemail_groups` (`VoicemailGroupsApi`)

### Commands

```bash
wxcli voicemail-groups list [--location <id>]
wxcli voicemail-groups show --location <id> <group-id>
wxcli voicemail-groups create --location <id> --name "..." --extension "..."
wxcli voicemail-groups update --location <id> <group-id> [--name "..."]
wxcli voicemail-groups delete --location <id> <group-id>
```

### SDK Method Mapping

| Command | SDK Method | Signature |
|---------|-----------|-----------|
| list | `voicemail_groups.list` | `(location_id: str = None, name: str = None)` |
| show | `voicemail_groups.details` | `(location_id: str, voicemail_group_id: str)` |
| create | `voicemail_groups.create` | `(location_id: str, settings: VoicemailGroupDetail)` → returns `str` |
| update | `voicemail_groups.update` | `(location_id: str, voicemail_group_id: str, settings: VoicemailGroupDetail)` |
| delete | `voicemail_groups.delete` | `(location_id: str, voicemail_group_id: str)` |

### Model: VoicemailGroupDetail (for create/update — different from VoicemailGroup list model)

Fields: `name`, `extension`, `phone_number`, `enabled`.

---

## Implementation Notes

### Shared Patterns

All 9 command files follow the identical v1 pattern:
- Import `typer`, `get_api`, `print_table`, `print_json`
- Create `app = typer.Typer(help="...")`
- Each command: get API, call SDK method, format output
- `--output table|json`, `--limit N`, `--debug` on every list/show command
- `--force` on delete commands

### Agent Management (add-agent pattern)

Hunt groups, call queues, call park, call pickup, and paging all have member/agent lists. The SDK has no `add_agent` method — it's always read-modify-write:
1. `details()` to get current state
2. Append new agent to the `agents` list
3. `update()` with modified object

**CRITICAL — Agent class imports differ per command group:**
- Hunt Groups + Call Queues: `from wxc_sdk.telephony.hg_and_cq import Agent`
- Call Park + Call Pickup: `from wxc_sdk.common import PersonPlaceAgent`
- Paging originators/targets: `from wxc_sdk.telephony.paging import PagingAgent`

Do NOT try `from wxc_sdk.telephony.huntgroup import Agent` — it will fail.

### Delete Method Names — Use Named Methods, Not Generic `.delete()`

Call Park, Call Pickup, Paging, and Voicemail Groups all have a generic inherited `.delete()` method that accepts anything silently. **Always use the named delete method:**
- `callpark.delete_callpark(location_id, callpark_id)`
- `pickup.delete_pickup(location_id, pickup_id)`
- `paging.delete_paging(location_id, paging_id)`
- `voicemail_groups.delete(location_id, voicemail_group_id)`
- `huntgroup.delete_huntgroup(location_id, huntgroup_id)`
- `callqueue.delete_queue(location_id, queue_id)`
- `auto_attendant.delete_auto_attendant(location_id, auto_attendant_id)`
- `schedules.delete_schedule(obj_id, schedule_type, schedule_id)`

### Paging Update — Unusual Parameter Order

`PagingApi.update` has `paging_id` AFTER the model object:
```python
paging.update(location_id=loc_id, update=paging_obj, paging_id=pg_id)
```
**Always use keyword arguments** for this call. Positional args will silently swap the model and ID.

### Schedule Import Path

`ScheduleApi` lives at `wxc_sdk.common.schedules`, NOT `wxc_sdk.telephony.schedules`:
```python
from wxc_sdk.common.schedules import Schedule, Event, ScheduleType
```

### Operating Modes Delete

`OperatingModesApi` has a `delete` method but it was omitted from v2 scope intentionally — operating mode deletion can cascade and break auto-attendant/hunt-group routing. Add in v2.1 after testing impact.

### Error Handling

Same as v1: stack traces suppressed, API errors printed cleanly. The `RestError` catch pattern from locations should be extracted into a shared decorator or context manager for v2.

### Registration in main.py

9 new lines in main.py:
```python
from wxcli.commands.schedules import app as schedules_app
from wxcli.commands.operating_modes import app as operating_modes_app
from wxcli.commands.auto_attendants import app as auto_attendants_app
from wxcli.commands.hunt_groups import app as hunt_groups_app
from wxcli.commands.call_queues import app as call_queues_app
from wxcli.commands.call_park import app as call_park_app
from wxcli.commands.call_pickup import app as call_pickup_app
from wxcli.commands.paging import app as paging_app
from wxcli.commands.voicemail_groups import app as voicemail_groups_app

app.add_typer(schedules_app, name="schedules")
app.add_typer(operating_modes_app, name="operating-modes")
app.add_typer(auto_attendants_app, name="auto-attendants")
app.add_typer(hunt_groups_app, name="hunt-groups")
app.add_typer(call_queues_app, name="call-queues")
app.add_typer(call_park_app, name="call-park")
app.add_typer(call_pickup_app, name="call-pickup")
app.add_typer(paging_app, name="paging")
app.add_typer(voicemail_groups_app, name="voicemail-groups")
```

## Testing Strategy

- Unit tests for any shared utilities (error handler, agent management pattern)
- Live testing of every write command against the Webex API (same as v1)
- Smoke test script updated to cover all 9 new command groups

## Success Criteria

1. All 54 commands registered and showing help
2. All list/show commands work against live API
3. All create/update/delete commands verified against live API
4. add-agent works for hunt-groups and call-queues
5. Schedule creation works and auto-attendants can reference them
6. Error messages are clear (no stack traces)
