# Feature Forwarding + Night Service Migration

**Date:** 2026-04-10
**Priority:** HIGH
**Source:** API audit — calling gaps
**Status:** Spec

---

## Problem Statement

The migration pipeline creates Auto Attendants, Hunt Groups, and Call Queues (tier 4) but
leaves them with default call forwarding and no holiday/night service configuration. In CUCM,
these features have complex overflow, after-hours routing, and holiday behavior wired to time
schedules. After migration, callers hit Webex default behavior (ring forever, no overflow,
no after-hours greeting) instead of the configured routing.

### What Exists Today

1. **Feature creation** (tier 4): `handle_hunt_group_create`, `handle_call_queue_create`,
   `handle_auto_attendant_create` — POST the feature with name, extension, agents, and
   basic call policies. No forwarding body.

2. **Operating modes** (tier 1): `CanonicalOperatingMode` objects are created from CUCM
   time schedules and time periods. The `handle_operating_mode_create` handler POSTs them
   at `/telephony/config/operatingModes`. These are org-level or location-level schedule
   objects.

3. **Location schedules** (tier 1): `CanonicalLocationSchedule` objects created for
   business-hours and holiday schedules referenced by features.

### What Is Missing

**No post-creation configuration calls.** The pipeline has no:
- `hunt_group:configure_forwarding` operation
- `call_queue:configure_forwarding` operation
- `call_queue:configure_holiday_service` operation
- `call_queue:configure_night_service` operation
- `call_queue:configure_forced_forward` operation
- `call_queue:configure_stranded_calls` operation
- `auto_attendant:configure_forwarding` operation

The canonical models (`CanonicalHuntGroup`, `CanonicalCallQueue`, `CanonicalAutoAttendant`)
have no fields for forwarding destinations, overflow numbers, holiday routing, or night
service configuration.

### Impact

| Feature | CUCM Source | Webex State After Migration | What Callers Experience |
|---------|-------------|---------------------------|----------------------|
| Hunt Group overflow | Hunt pilot `forwardHuntNoAnswer` destination | No forwarding configured | Ring-no-answer → nothing |
| Call Queue overflow | `queueFullDestination`, `maxWaitTimeDestination`, `noAgentDestination` | Default (caller waits forever) | Queue full → hold music forever |
| CQ holiday routing | CQ holiday service → schedule + transfer number | No holiday service | Holidays → same as business hours |
| CQ night service | CQ night service → business hours schedule + transfer | No night service | After hours → same as business hours |
| CQ forced forward | CQ forced forward → emergency divert number | Not configured | No emergency overflow capability |
| AA call forwarding | CTI RP forwarding → busy/no-answer destinations | No forwarding | AA unreachable → busy signal |

---

## CUCM Source Data

### Hunt Pilot Overflow (Hunt Group + Call Queue)

The CUCM hunt pilot has forwarding-related fields already extracted by AXL:

```
HuntPilot:
  forwardHuntNoAnswer:            # Forward-on-no-answer destination
    destination: str              # DN or external number
    callingSearchSpaceName: str   # CSS for the forwarded call
  forwardHuntBusy:                # Forward-on-busy destination
    destination: str
    callingSearchSpaceName: str
  queueCalls:                     # Queue configuration (XCallsQueue complex type)
    queueFullDestination: str     # Where to send when queue is full
    maxWaitTimeDestination: str   # Where to send after max wait
    noAgentDestination: str       # Where to send when no agents logged in
    maxCallersInQueue: int        # Queue capacity
    maxWaitTime: int              # Max wait seconds
```

These fields are on the normalized `hunt_pilot` object's `pre_migration_state` but the
`FeatureMapper._map_hunt_pilots()` method only reads `queueCalls.maxCallersInQueue` for
the `queue_size` field. All forwarding destinations are ignored.

### Auto Attendant (CTI Route Point)

CTI Route Points in CUCM have call forwarding via their CSS and partition time schedule
bindings. The `FeatureMapper._map_cti_route_points()` method extracts `business_schedule`
from CSS partition time schedules but does not extract forwarding destinations. CUCM AA
equivalents often use JTAPI scripts for time-of-day routing, which the mapper already flags
as `FEATURE_APPROXIMATION`.

### Time Schedules → Operating Modes/Location Schedules

Already handled. `CanonicalOperatingMode` (business hours, holidays) and
`CanonicalLocationSchedule` objects exist. The gap is connecting them to features.

---

## Webex Target APIs

### Hunt Group Call Forwarding

```
GET/PUT /telephony/config/locations/{locationId}/huntGroups/{huntGroupId}/callForwarding
```

Schema: `CallForwardSettingsGet` — same schema as CQ and person forwarding:
```json
{
  "callForwarding": {
    "always": {
      "enabled": false,
      "destination": "2225551212",
      "ringReminderEnabled": false,
      "destinationVoicemailEnabled": false
    },
    "selective": {
      "enabled": false,
      "destination": "2225551212",
      "ringReminderEnabled": false,
      "destinationVoicemailEnabled": false
    },
    "rules": [],
    "operatingModes": { ... }
  }
}
```

Selective forwarding rules (time-based routing):
```
POST/GET/PUT/DELETE .../callForwarding/selectiveRules/{ruleId}
```

Operating mode switch:
```
POST .../callForwarding/actions/switchMode/invoke
```

### Call Queue Call Forwarding

```
GET/PUT /telephony/config/locations/{locationId}/queues/{queueId}/callForwarding
```

Same `CallForwardSettingsGet` schema as hunt group forwarding.

Plus selective rules and mode switch endpoints (same pattern as HG).

### Call Queue Holiday Service

```
GET/PUT /telephony/config/locations/{locationId}/queues/{queueId}/holidayService
```

Schema: `GetCallQueueHolidayObject`:
```json
{
  "holidayServiceEnabled": true,
  "action": "BUSY|TRANSFER",
  "holidayScheduleLevel": "LOCATION|ORGANIZATION",
  "holidayScheduleName": "2022 Holidays Period",
  "transferPhoneNumber": "1234",
  "playAnnouncementBeforeEnabled": true,
  "audioMessageSelection": "DEFAULT|CUSTOM",
  "audioFiles": [...],
  "holidaySchedules": [
    { "scheduleName": "...", "scheduleLevel": "LOCATION" }
  ]
}
```

### Call Queue Night Service

```
GET/PUT /telephony/config/locations/{locationId}/queues/{queueId}/nightService
```

Schema: `GetCallQueueNightServiceObject`:
```json
{
  "nightServiceEnabled": true,
  "action": "TRANSFER",
  "transferPhoneNumber": "1234",
  "playAnnouncementBeforeEnabled": true,
  "announcementMode": "NORMAL",
  "audioMessageSelection": "DEFAULT",
  "businessHourSchedules": [
    { "scheduleName": "Working Hour", "scheduleLevel": "LOCATION" }
  ],
  "businessHoursLevel": "LOCATION",
  "businessHoursName": "Working Hour",
  "forceNightServiceEnabled": true,
  "manualAudioMessageSelection": "DEFAULT",
  "manualAudioFiles": [...]
}
```

### Call Queue Forced Forward

```
GET/PUT /telephony/config/locations/{locationId}/queues/{queueId}/forcedForward
```

Schema: `GetCallQueueForcedForwardObject`:
```json
{
  "forcedForwardEnabled": true,
  "transferPhoneNumber": "+911235557890",
  "playAnnouncementBeforeEnabled": true,
  "audioMessageSelection": "DEFAULT|CUSTOM"
}
```

### Call Queue Stranded Calls

```
GET/PUT /telephony/config/locations/{locationId}/queues/{queueId}/strandedCalls
```

Handles what happens when no agents are logged in (maps to CUCM `noAgentDestination`).

### Auto Attendant Call Forwarding

```
GET/PUT /telephony/config/locations/{locationId}/autoAttendants/{autoAttendantId}/callForwarding
```

Schema: `GetAutoAttendantCallForwardSettingsObject` — similar to HG/CQ forwarding plus
selective rules endpoints.

### Required Scope

All endpoints: `spark-admin:telephony_config_read` (GET) / `spark-admin:telephony_config_write` (PUT).
Same scope as feature creation — no additional authorization needed.

---

## Pipeline Integration

### 1. Extend Canonical Models

File: `src/wxcli/migration/models.py`

Add forwarding/night/holiday fields to existing models:

```python
class CanonicalHuntGroup(MigrationObject):
    # ... existing fields ...
    # NEW: forwarding configuration
    forward_always_enabled: bool = False
    forward_always_destination: str | None = None
    forward_busy_enabled: bool = False
    forward_busy_destination: str | None = None
    forward_no_answer_enabled: bool = False
    forward_no_answer_destination: str | None = None


class CanonicalCallQueue(MigrationObject):
    # ... existing fields ...
    # NEW: forwarding configuration
    forward_always_enabled: bool = False
    forward_always_destination: str | None = None
    # NEW: overflow destinations (from queueCalls)
    queue_full_destination: str | None = None
    max_wait_time_destination: str | None = None
    max_wait_time: int | None = None
    no_agent_destination: str | None = None
    # NEW: holiday service
    holiday_service_enabled: bool = False
    holiday_schedule_name: str | None = None
    holiday_schedule_level: str = "LOCATION"
    holiday_action: str = "BUSY"
    holiday_transfer_number: str | None = None
    # NEW: night service
    night_service_enabled: bool = False
    night_business_hours_name: str | None = None
    night_business_hours_level: str = "LOCATION"
    night_action: str = "TRANSFER"
    night_transfer_number: str | None = None
    # NEW: forced forward
    forced_forward_enabled: bool = False
    forced_forward_number: str | None = None


class CanonicalAutoAttendant(MigrationObject):
    # ... existing fields ...
    # NEW: forwarding configuration
    forward_always_enabled: bool = False
    forward_always_destination: str | None = None
```

### 2. Enhance FeatureMapper

File: `src/wxcli/migration/transform/mappers/feature_mapper.py`

**Hunt Pilot -> HG/CQ forwarding extraction:**

In `_map_hunt_pilots()`, after the existing agent/policy extraction, read the forwarding
fields from `hp_state`:

```python
# Extract forwarding destinations
fwd_no_answer = hp_state.get("forwardHuntNoAnswer") or {}
fwd_busy = hp_state.get("forwardHuntBusy") or {}

forward_no_answer_dest = fwd_no_answer.get("destination")
forward_busy_dest = fwd_busy.get("destination")
```

For Call Queues, also extract overflow destinations from `queueCalls`:
```python
queue_calls = hp_state.get("queueCalls") or {}
queue_full_dest = queue_calls.get("queueFullDestination")
max_wait_dest = queue_calls.get("maxWaitTimeDestination")
max_wait_time = queue_calls.get("maxWaitTime")
no_agent_dest = queue_calls.get("noAgentDestination")
```

Wire these into the `CanonicalCallQueue` and `CanonicalHuntGroup` constructors.

**Schedule -> holiday/night service binding:**

The FeatureMapper already resolves `aa_has_schedule` cross-refs for AAs. Extend this to
resolve holiday schedule references for Call Queues:

1. Check if the CUCM hunt pilot references a holiday schedule (via time schedule cross-ref)
2. Look up the corresponding `CanonicalOperatingMode` or `CanonicalLocationSchedule` by name
3. Set `holiday_service_enabled`, `holiday_schedule_name`, `holiday_schedule_level`

For night service, the CUCM "normal" operating hours schedule maps to Webex
`businessHoursName`. If the CUCM feature has a time schedule that defines business hours,
set `night_service_enabled=True` and `night_business_hours_name` to the schedule name.

### 3. Add Planner Expanders

File: `src/wxcli/migration/execute/planner.py`

Extend existing feature expanders to produce configure ops when forwarding data exists:

```python
def _expand_hunt_group(obj: dict[str, Any], decisions: list) -> list[MigrationOp]:
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    ops = [_op(cid, "create", "hunt_group", f"Create hunt group {name}")]

    # NEW: add configure_forwarding if any forwarding destination is set
    has_forwarding = any([
        obj.get("forward_always_destination"),
        obj.get("forward_busy_destination"),
        obj.get("forward_no_answer_destination"),
    ])
    if has_forwarding:
        ops.append(_op(cid, "configure_forwarding", "hunt_group",
                       f"Configure forwarding for hunt group {name}",
                       depends_on=[f"{cid}:create"]))
    return ops


def _expand_call_queue(obj: dict[str, Any], decisions: list) -> list[MigrationOp]:
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    ops = [_op(cid, "create", "call_queue", f"Create call queue {name}")]

    # configure_forwarding (overflow destinations)
    has_forwarding = any([
        obj.get("forward_always_destination"),
        obj.get("queue_full_destination"),
        obj.get("max_wait_time_destination"),
    ])
    if has_forwarding:
        ops.append(_op(cid, "configure_forwarding", "call_queue",
                       f"Configure forwarding for call queue {name}",
                       depends_on=[f"{cid}:create"]))

    # configure_holiday_service
    if obj.get("holiday_service_enabled"):
        ops.append(_op(cid, "configure_holiday_service", "call_queue",
                       f"Configure holiday service for call queue {name}",
                       depends_on=[f"{cid}:create"]))

    # configure_night_service
    if obj.get("night_service_enabled"):
        ops.append(_op(cid, "configure_night_service", "call_queue",
                       f"Configure night service for call queue {name}",
                       depends_on=[f"{cid}:create"]))

    # configure_stranded_calls (no-agent destination)
    if obj.get("no_agent_destination"):
        ops.append(_op(cid, "configure_stranded_calls", "call_queue",
                       f"Configure stranded calls for call queue {name}",
                       depends_on=[f"{cid}:create"]))

    return ops
```

### 4. Add Tier Assignments

File: `src/wxcli/migration/execute/__init__.py`

All configure ops are **tier 5** (settings tier), after feature creation at tier 4. They
also depend on operating_mode:create (tier 1) for schedule references, but that dependency
is already satisfied by tier ordering.

```python
TIER_ASSIGNMENTS = {
    ...
    # Feature forwarding/service configuration
    ("hunt_group", "configure_forwarding"): 5,
    ("call_queue", "configure_forwarding"): 5,
    ("call_queue", "configure_holiday_service"): 5,
    ("call_queue", "configure_night_service"): 5,
    ("call_queue", "configure_stranded_calls"): 5,
    ("auto_attendant", "configure_forwarding"): 5,
    ...
}

API_CALL_ESTIMATES = {
    ...
    "hunt_group:configure_forwarding": 1,
    "call_queue:configure_forwarding": 1,
    "call_queue:configure_holiday_service": 1,
    "call_queue:configure_night_service": 1,
    "call_queue:configure_stranded_calls": 1,
    "auto_attendant:configure_forwarding": 1,
    ...
}
```

### 5. Add Handlers

File: `src/wxcli/migration/execute/handlers.py`

```python
# --- Hunt Group forwarding ---
def handle_hunt_group_configure_forwarding(
    data: dict, deps: dict, ctx: dict
) -> HandlerResult:
    hg_wid = _find_webex_id(data, deps)
    loc_wid = _resolve_location(data, deps)
    if not hg_wid or not loc_wid:
        return []
    body: dict[str, Any] = {"callForwarding": {}}
    cf = body["callForwarding"]
    if data.get("forward_always_destination"):
        cf["always"] = {
            "enabled": True,
            "destination": data["forward_always_destination"],
            "ringReminderEnabled": False,
            "destinationVoicemailEnabled": False,
        }
    if data.get("forward_no_answer_destination"):
        cf["selective"] = {
            "enabled": True,
            "destination": data["forward_no_answer_destination"],
            "ringReminderEnabled": False,
            "destinationVoicemailEnabled": False,
        }
    if not cf:
        return []
    url = f"/telephony/config/locations/{loc_wid}/huntGroups/{hg_wid}/callForwarding"
    return [("PUT", _url(url, ctx), body)]


# --- Call Queue forwarding ---
def handle_call_queue_configure_forwarding(
    data: dict, deps: dict, ctx: dict
) -> HandlerResult:
    cq_wid = _find_webex_id(data, deps)
    loc_wid = _resolve_location(data, deps)
    if not cq_wid or not loc_wid:
        return []
    body: dict[str, Any] = {"callForwarding": {}}
    cf = body["callForwarding"]
    if data.get("forward_always_destination"):
        cf["always"] = {
            "enabled": True,
            "destination": data["forward_always_destination"],
            "ringReminderEnabled": False,
            "destinationVoicemailEnabled": False,
        }
    if not cf:
        return []
    url = f"/telephony/config/locations/{loc_wid}/queues/{cq_wid}/callForwarding"
    return [("PUT", _url(url, ctx), body)]


# --- Call Queue holiday service ---
def handle_call_queue_configure_holiday_service(
    data: dict, deps: dict, ctx: dict
) -> HandlerResult:
    cq_wid = _find_webex_id(data, deps)
    loc_wid = _resolve_location(data, deps)
    if not cq_wid or not loc_wid:
        return []
    body = {
        "holidayServiceEnabled": True,
        "action": data.get("holiday_action", "BUSY"),
        "holidayScheduleLevel": data.get("holiday_schedule_level", "LOCATION"),
        "holidayScheduleName": data.get("holiday_schedule_name"),
        "playAnnouncementBeforeEnabled": True,
        "audioMessageSelection": "DEFAULT",
    }
    if data.get("holiday_transfer_number"):
        body["action"] = "TRANSFER"
        body["transferPhoneNumber"] = data["holiday_transfer_number"]
    url = f"/telephony/config/locations/{loc_wid}/queues/{cq_wid}/holidayService"
    return [("PUT", _url(url, ctx), body)]


# --- Call Queue night service ---
def handle_call_queue_configure_night_service(
    data: dict, deps: dict, ctx: dict
) -> HandlerResult:
    cq_wid = _find_webex_id(data, deps)
    loc_wid = _resolve_location(data, deps)
    if not cq_wid or not loc_wid:
        return []
    body = {
        "nightServiceEnabled": True,
        "action": data.get("night_action", "TRANSFER"),
        "businessHoursLevel": data.get("night_business_hours_level", "LOCATION"),
        "businessHoursName": data.get("night_business_hours_name"),
        "playAnnouncementBeforeEnabled": True,
        "announcementMode": "NORMAL",
        "audioMessageSelection": "DEFAULT",
        "forceNightServiceEnabled": False,
        "manualAudioMessageSelection": "DEFAULT",
    }
    if data.get("night_transfer_number"):
        body["transferPhoneNumber"] = data["night_transfer_number"]
    url = f"/telephony/config/locations/{loc_wid}/queues/{cq_wid}/nightService"
    return [("PUT", _url(url, ctx), body)]


# --- Call Queue stranded calls ---
def handle_call_queue_configure_stranded_calls(
    data: dict, deps: dict, ctx: dict
) -> HandlerResult:
    cq_wid = _find_webex_id(data, deps)
    loc_wid = _resolve_location(data, deps)
    if not cq_wid or not loc_wid:
        return []
    body = {
        "action": "TRANSFER",
        "transferPhoneNumber": data.get("no_agent_destination"),
    }
    url = f"/telephony/config/locations/{loc_wid}/queues/{cq_wid}/strandedCalls"
    return [("PUT", _url(url, ctx), body)]


# --- Auto Attendant forwarding ---
def handle_auto_attendant_configure_forwarding(
    data: dict, deps: dict, ctx: dict
) -> HandlerResult:
    aa_wid = _find_webex_id(data, deps)
    loc_wid = _resolve_location(data, deps)
    if not aa_wid or not loc_wid:
        return []
    body: dict[str, Any] = {"callForwarding": {}}
    cf = body["callForwarding"]
    if data.get("forward_always_destination"):
        cf["always"] = {
            "enabled": True,
            "destination": data["forward_always_destination"],
            "ringReminderEnabled": False,
            "destinationVoicemailEnabled": False,
        }
    if not cf:
        return []
    url = (f"/telephony/config/locations/{loc_wid}"
           f"/autoAttendants/{aa_wid}/callForwarding")
    return [("PUT", _url(url, ctx), body)]
```

Register all in `HANDLER_REGISTRY`:
```python
("hunt_group", "configure_forwarding"): handle_hunt_group_configure_forwarding,
("call_queue", "configure_forwarding"): handle_call_queue_configure_forwarding,
("call_queue", "configure_holiday_service"): handle_call_queue_configure_holiday_service,
("call_queue", "configure_night_service"): handle_call_queue_configure_night_service,
("call_queue", "configure_stranded_calls"): handle_call_queue_configure_stranded_calls,
("auto_attendant", "configure_forwarding"): handle_auto_attendant_configure_forwarding,
```

### 6. Add Dependency Rules

File: `src/wxcli/migration/execute/dependency.py`

```python
# All configure_* ops depend on their feature create op (intra-object, via depends_on)
# Additional cross-object dependencies:
#   configure_holiday_service REQUIRES operating_mode:create (the holiday schedule)
#   configure_night_service REQUIRES operating_mode:create (the business hours schedule)
#   configure_night_service REQUIRES schedule:create (location schedule)
```

These dependencies are already satisfied by tier ordering (operating_mode at tier 1,
features at tier 4, configure at tier 5), but explicit edges provide safety against
future tier changes.

### Dependency Chain

```
operating_mode:create           (tier 1)  -- holiday/business schedules
schedule:create                 (tier 1)  -- location schedules
    |
hunt_group:create               (tier 4)
call_queue:create               (tier 4)
auto_attendant:create           (tier 4)
    |
hunt_group:configure_forwarding     (tier 5, depends on create)
call_queue:configure_forwarding     (tier 5, depends on create)
call_queue:configure_holiday_service (tier 5, depends on create + operating_mode)
call_queue:configure_night_service   (tier 5, depends on create + operating_mode)
call_queue:configure_stranded_calls  (tier 5, depends on create)
auto_attendant:configure_forwarding  (tier 5, depends on create)
```

---

## CUCM-to-Webex Field Mapping

### Hunt Group Forwarding

| CUCM Field | Webex API Field | Notes |
|------------|----------------|-------|
| `forwardHuntNoAnswer.destination` | `callForwarding.selective.destination` | Maps no-answer to selective forwarding |
| `forwardHuntBusy.destination` | `callForwarding.always.destination` | Maps busy to always-forward (approximation) |

### Call Queue Overflow

| CUCM Field | Webex API Field | Notes |
|------------|----------------|-------|
| `queueCalls.queueFullDestination` | `callForwarding.always.destination` | Queue full → forward all (when full) |
| `queueCalls.maxWaitTimeDestination` | CQ overflow settings | Map to CQ-specific overflow |
| `queueCalls.maxWaitTime` | CQ `waitMessageTime` | Seconds before overflow |
| `queueCalls.noAgentDestination` | `strandedCalls.transferPhoneNumber` | No agents → stranded calls |

### Call Queue Holiday Service

| CUCM Field | Webex API Field | Notes |
|------------|----------------|-------|
| Schedule (holiday type) `timeScheduleIdName` | `holidayScheduleName` | Schedule name reference |
| Schedule level (org vs location) | `holidayScheduleLevel` | LOCATION or ORGANIZATION |
| Overflow destination during holiday | `transferPhoneNumber` | If action=TRANSFER |
| Default action | `action` | BUSY or TRANSFER |

### Call Queue Night Service

| CUCM Field | Webex API Field | Notes |
|------------|----------------|-------|
| Schedule (business hours) `timeScheduleIdName` | `businessHoursName` | Business hours schedule name |
| Schedule level | `businessHoursLevel` | LOCATION or ORGANIZATION |
| After-hours destination | `transferPhoneNumber` | Where to send after hours |
| Force night service toggle | `forceNightServiceEnabled` | Manual override |

---

## Documentation Updates Required

| File | Change |
|------|--------|
| `src/wxcli/migration/models.py` | Add forwarding/holiday/night fields to CanonicalHuntGroup, CanonicalCallQueue, CanonicalAutoAttendant |
| `src/wxcli/migration/transform/mappers/feature_mapper.py` | Extract forwarding destinations and schedule bindings from hunt_pilot state |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Document new fields on HG/CQ/AA canonical types |
| `src/wxcli/migration/execute/__init__.py` | Add TIER_ASSIGNMENTS and API_CALL_ESTIMATES for 6 new op types |
| `src/wxcli/migration/execute/planner.py` | Extend _expand_hunt_group, _expand_call_queue, _expand_auto_attendant |
| `src/wxcli/migration/execute/handlers.py` | Add 6 new handler functions + HANDLER_REGISTRY entries |
| `src/wxcli/migration/execute/dependency.py` | Add cross-object dependency rules for schedule references |
| `src/wxcli/migration/execute/CLAUDE.md` | Add 6 new handlers to handler inventory (tier 5 section) |
| `src/wxcli/migration/CLAUDE.md` | Update pipeline summary |
| `docs/reference/call-features-major.md` | Add migration mapping notes for forwarding/night/holiday |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Add forwarding/holiday/night mapping guidance |
| `docs/runbooks/cucm-migration/decision-guide.md` | Update HG/CQ entries with forwarding context |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Add post-migration forwarding verification step |

---

## Test Strategy

### Unit Tests — Mapper

1. **HG forwarding extraction** — hunt pilot with `forwardHuntNoAnswer` → CanonicalHuntGroup
   has `forward_no_answer_destination` set
2. **CQ overflow extraction** — hunt pilot with `queueCalls.queueFullDestination` → CanonicalCallQueue
   has `queue_full_destination` set
3. **CQ holiday schedule binding** — hunt pilot referencing a holiday time schedule → CanonicalCallQueue
   has `holiday_service_enabled=True` and `holiday_schedule_name` set
4. **CQ night service binding** — hunt pilot with business hours schedule → CanonicalCallQueue
   has `night_service_enabled=True` and `night_business_hours_name` set
5. **No forwarding** — hunt pilot with no forwarding fields → canonical model has all forwarding
   fields at default (False/None), no configure ops produced
6. **AA forwarding** — CTI RP with forwarding destination → CanonicalAutoAttendant has
   `forward_always_destination` set

### Unit Tests — Planner

7. **HG with forwarding** — produces `[create, configure_forwarding]` ops
8. **CQ with all services** — produces `[create, configure_forwarding, configure_holiday_service,
   configure_night_service, configure_stranded_calls]` ops
9. **CQ without services** — produces `[create]` only (no configure ops)
10. **Op dependencies** — all configure ops depend on their create op

### Unit Tests — Handlers

11. **HG configure_forwarding** — correct PUT body with callForwarding.always/selective
12. **CQ configure_forwarding** — correct PUT body
13. **CQ configure_holiday_service** — correct PUT body with schedule name, action, transfer number
14. **CQ configure_night_service** — correct PUT body with business hours schedule
15. **CQ configure_stranded_calls** — correct PUT body with action=TRANSFER and phone number
16. **AA configure_forwarding** — correct PUT body
17. **Missing deps** — all handlers return [] when feature or location Webex ID not resolved
18. **No forwarding data** — handlers return [] when forwarding fields are None/empty

### Integration Tests

19. **Full pipeline** — discover -> normalize -> map -> analyze -> plan with hunt pilot that has
    forwarding + queue overflow → plan contains both create and configure ops in correct tiers
20. **Tier ordering** — configure ops at tier 5, create ops at tier 4, schedule at tier 1
21. **Schedule dependency** — configure_holiday_service depends on operating_mode:create

### Acceptance Criteria

- Hunt groups with CUCM forwarding destinations produce configure_forwarding ops
- Call queues with overflow/holiday/night configuration produce all relevant configure ops
- No configure ops produced when source data has no forwarding/holiday/night configuration
- All configure ops are tier 5 with dependency on their feature's create op
- Handler PUT bodies match the Webex API schema for each endpoint
- End-to-end: features appear in plan with both create and configure operations

---

## Open Questions

1. **CUCM hunt pilot forwarding field extraction.** Verify that `forwardHuntNoAnswer` and
   `forwardHuntBusy` are in the AXL `returnedTags` for `listHuntPilot` / `getHuntPilot`.
   If not, the extractor needs updating to request these fields.

2. **Holiday schedule matching.** CUCM time schedules are generic (not typed as "holiday" vs
   "business hours"). The classifier must distinguish holiday schedules from business-hours
   schedules. Heuristic: schedules with `timeScheduleCategory=Holiday` or schedules whose
   time periods define specific calendar dates (not recurring weekday patterns).

3. **Destination resolution.** CUCM forwarding destinations are raw DNs or external numbers.
   These need E.164 normalization before writing to Webex. The existing `e164.py` module
   handles this, but the forwarding destinations must pass through it.

4. **Forced forward.** CUCM doesn't have a direct equivalent to Webex forced forward. The
   `queueFullDestination` is the closest match. Decide whether to wire this or leave
   forced forward as a manual post-migration configuration.

5. **Audio announcements.** The Webex holiday/night/stranded APIs accept custom audio files,
   but CUCM MoH and announcements are a separate migration topic (covered in
   `2026-04-10-moh-announcements-migration.md`). This spec uses `"audioMessageSelection": "DEFAULT"`
   for all handlers. Custom audio is out of scope.
