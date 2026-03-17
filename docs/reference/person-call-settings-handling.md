# Person Call Settings — Call Handling Reference

Person-level call handling settings control how incoming calls are routed, filtered, and alerted for individual Webex Calling users. All APIs live under `PersonSettingsApi` (accessed via `api.person_settings.*`) and share a common base class pattern.

> **SDK access path:** `api.person_settings.<feature>`
> **REST base:** `people/{person_id}/features/{feature}` (with some remapped to `telephony/config/people/{person_id}/...`)
> **Also available for:** Workspaces, Virtual Lines (same API classes, different URL selectors)

---

## Required Scopes

| Scope | Grants | Used By |
|-------|--------|---------|
| `spark-admin:people_read` | Read any person's call handling settings | Admin tokens |
| `spark-admin:people_write` | Modify any person's call handling settings | Admin tokens |
| `spark:people_read` | Read own call handling settings | User tokens (personal) |
| `spark:people_write` | Modify own call handling settings | User tokens (personal) |
| `spark-admin:telephony_config_read` | Read telephony config (used by Single Number Reach, some remapped endpoints) | Admin tokens |
| `spark-admin:telephony_config_write` | Modify telephony config (used by Single Number Reach, some remapped endpoints) | Admin tokens |

---

## Common Patterns

All call handling APIs extend `PersonSettingsApiChild`, which builds endpoint URLs from a `feature` string:

```
people/{person_id}/features/{feature}
```

Some features are remapped to `telephony/config/people/{person_id}/{feature}` at the SDK level (selective accept/forward/reject, music on hold, etc.). This is transparent to the caller.

Every feature API follows the same read/configure (or read/update) pattern. All methods accept an optional `org_id` parameter for partner administrators operating across organizations.

---

## 1. Call Forwarding

Controls where incoming calls are sent when the user cannot or does not want to answer. Three forwarding modes plus business continuity.

**SDK path:** `api.person_settings.forwarding`
**Feature slug:** `callForwarding`
**API class:** `PersonForwardingApi`

### Data Models

#### `PersonForwardingSetting`

Top-level container returned by `read()` and accepted by `configure()`.

| Field | Type | Description |
|-------|------|-------------|
| `call_forwarding` | `CallForwardingPerson` | Always / Busy / No-Answer settings |
| `business_continuity` | `CallForwardingCommon` | Forwarding when phone is disconnected from network (power outage, Internet failure) |

#### `CallForwardingPerson`

| Field | Type | Description |
|-------|------|-------------|
| `always` | `CallForwardingAlways` | Forward ALL incoming calls |
| `busy` | `CallForwardingCommon` | Forward when phone is in use |
| `no_answer` | `CallForwardingNoAnswer` | Forward when unanswered |

#### `CallForwardingAlways` (extends `CallForwardingCommon`)

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Enable/disable |
| `destination` | `str` (optional) | Destination number |
| `destination_voicemail_enabled` | `bool` (optional) | Send to destination's voicemail (internal numbers only) |
| `ring_reminder_enabled` | `bool` | Play brief tone on person's phone when a call is forwarded |

#### `CallForwardingNoAnswer` (extends `CallForwardingCommon`)

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Enable/disable |
| `destination` | `str` (optional) | Destination number |
| `destination_voicemail_enabled` | `bool` (optional) | Send to destination's voicemail |
| `number_of_rings` | `int` | Rings before forwarding (default: 3) |
| `system_max_number_of_rings` | `int` (optional, read-only) | System-wide max rings allowed |

#### `CallForwardingCommon` (used for Busy and Business Continuity)

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Enable/disable |
| `destination` | `str` (optional) | Destination number |
| `destination_voicemail_enabled` | `bool` (optional) | Send to destination's voicemail |

### Methods

#### Read

```python
PersonForwardingApi.read(
    entity_id: str,
    org_id: str = None
) -> PersonForwardingSetting
```

**Scopes:** `spark-admin:people_read` or `spark:people_read`

#### Configure

```python
PersonForwardingApi.configure(
    entity_id: str,
    forwarding: PersonForwardingSetting,
    org_id: str = None
) -> None
```

**Scopes:** `spark-admin:people_write` or `spark:people_write`

**Note:** The `system_max_number_of_rings` field is excluded from the update payload automatically.

#### Factory Default

All data models provide a `.default()` static method to generate a reset-to-defaults instance:

```python
forwarding = PersonForwardingSetting.default()
# Sets: always=disabled, busy=disabled, no_answer=disabled (3 rings),
#        business_continuity=disabled
```

### Example: Reset Call Forwarding for All Users

From `examples/reset_call_forwarding.py` — uses the async API to reset forwarding in bulk:

```python
from wxc_sdk.all_types import PersonForwardingSetting
from wxc_sdk.as_api import AsWebexSimpleApi

async with AsWebexSimpleApi() as api:
    calling_users = [user for user in await api.people.list(calling_data=True)
                     if user.location_id]

    forwarding = PersonForwardingSetting.default()
    await asyncio.gather(*[
        api.person_settings.forwarding.configure(
            entity_id=user.person_id,
            forwarding=forwarding
        )
        for user in calling_users
    ])
```

### Example: Enable Always-Forward

```python
settings = api.person_settings.forwarding.read(entity_id=person_id)
settings.call_forwarding.always = CallForwardingAlways(
    enabled=True,
    destination='+12223334444',
    destination_voicemail_enabled=True,
    ring_reminder_enabled=True
)
api.person_settings.forwarding.configure(entity_id=person_id, forwarding=settings)
```

---

## 2. Call Waiting

Controls whether a user can place an active call on hold to answer a second incoming call. A tone alerts the user of the incoming call.

**SDK path:** `api.person_settings.call_waiting`
**Feature slug:** `callWaiting`
**API class:** `CallWaitingApi`

### Data Model

No separate model — returns and accepts a simple `bool`.

### Methods

#### Read

```python
CallWaitingApi.read(
    entity_id: str,
    org_id: str = None
) -> bool
```

Returns `True` if call waiting is enabled.

**Scopes:** `spark-admin:people_read` or `spark:people_read`

#### Configure

```python
CallWaitingApi.configure(
    entity_id: str,
    enabled: bool,
    org_id: str = None
) -> None
```

**Scopes:** `spark-admin:people_write` or `spark:people_write`

### Example

```python
# Check if call waiting is enabled
is_enabled = api.person_settings.call_waiting.read(entity_id=person_id)

# Disable call waiting
api.person_settings.call_waiting.configure(entity_id=person_id, enabled=False)
```

---

## 3. Do Not Disturb (DND)

When enabled, all incoming calls receive busy treatment. Optionally plays a ring splash (brief tone) on the desktop phone as a reminder.

**SDK path:** `api.person_settings.dnd`
**Feature slug:** `doNotDisturb`
**API class:** `DndApi`

### Data Model — `DND`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable DND |
| `ring_splash_enabled` | `bool` (optional) | Play brief ring reminder tone on desktop phone for incoming calls |
| `webex_go_override_enabled` | `bool` (optional) | When `true`, mobile device still rings even if DND is on |

### Methods

#### Read

```python
DndApi.read(
    entity_id: str,
    org_id: str = None
) -> DND
```

**Scopes:** `spark-admin:people_read` or `spark:people_read`

#### Configure

```python
DndApi.configure(
    entity_id: str,
    dnd_settings: DND,
    org_id: str = None
) -> None
```

**Scopes:** `spark-admin:people_write` or `spark:people_write`

### Example

```python
from wxc_sdk.person_settings.dnd import DND

# Enable DND with ring splash
api.person_settings.dnd.configure(
    entity_id=person_id,
    dnd_settings=DND(enabled=True, ring_splash_enabled=True)
)
```

---

## 4. Simultaneous Ring

Ring the user's office phone and up to 10 additional phone numbers at the same time when an incoming call arrives. Supports schedule-based criteria to control when simultaneous ring is active.

**SDK path:** `api.person_settings.sim_ring` <!-- NEEDS VERIFICATION: SimRingApi is not imported into PersonSettingsApi in the SDK source; this feature may only be available via workspace_settings or the "me" API (MeSimRingApi) for person-level access -->
**Feature slug:** `simultaneousRing`
**API class:** `SimRingApi`

### Data Models

#### `SimRing`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable simultaneous ring |
| `do_not_ring_if_on_call_enabled` | `bool` (optional) | Suppress ringing additional numbers when already on a call |
| `phone_numbers` | `list[SimRingNumber]` (optional) | Up to 10 numbers to ring simultaneously |
| `criteria` | `list[SelectiveCrit]` (optional, read-only) | Schedule-based criteria list (managed via criteria sub-endpoints) |
| `criterias_enabled` | `bool` (optional) | Enable/disable schedule-based criteria |

#### `SimRingNumber`

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | `str` (optional, E.164) | Phone number to ring |
| `answer_confirmation_required_enabled` | `bool` (optional) | Require called party to press 1 to accept |

#### `SimRingCriteria` (extends `SelectiveCriteria`)

Uses `ringEnabled` as the enabled attribute. See [Shared Criteria Model](#shared-criteria-model-selectivecriteria) below.

### Methods

#### Read Settings

```python
SimRingApi.read(
    entity_id: str,
    org_id: str = None
) -> SimRing
```

#### Configure Settings

```python
SimRingApi.configure(
    entity_id: str,
    settings: SimRing,
    org_id: str = None
) -> None
```

**Note:** The `criteria` list is excluded from the update payload. Criteria are managed via dedicated CRUD methods.

#### Criteria CRUD

```python
SimRingApi.create_criteria(entity_id: str, settings: SimRingCriteria, org_id: str = None) -> str
SimRingApi.read_criteria(entity_id: str, id: str, org_id: str = None) -> SimRingCriteria
SimRingApi.configure_criteria(entity_id: str, id: str, settings: SimRingCriteria, org_id: str = None) -> None
SimRingApi.delete_criteria(entity_id: str, id: str, org_id: str = None) -> None
```

`create_criteria` returns the new criteria ID.

---

## 5. Sequential Ring

Ring up to five phone numbers one after another when an incoming call arrives. Configurable ring counts per number, optional primary-line-first behavior, and schedule-based criteria.

**SDK path:** `api.person_settings.sequential_ring` <!-- NEEDS VERIFICATION: SequentialRingApi is not imported into PersonSettingsApi in the SDK source; may only be available via workspace_settings or MeSequentialRingApi -->
**Feature slug:** `sequentialRing`
**API class:** `SequentialRingApi`

### Data Models

#### `SequentialRing`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable sequential ring |
| `ring_base_location_first_enabled` | `bool` (optional) | Ring primary (Webex Calling) line first |
| `base_location_number_of_rings` | `int` (optional) | Number of rings on primary line before advancing |
| `continue_if_base_location_is_busy_enabled` | `bool` (optional) | If primary line is busy, proceed to sequential numbers |
| `calls_to_voicemail_enabled` | `bool` (optional) | Send to voicemail if no sequential number answers |
| `phone_numbers` | `list[SequentialRingNumber]` (optional) | Up to 5 numbers to ring in sequence |
| `criteria` | `list[SelectiveCrit]` (optional, read-only) | Schedule-based criteria |

#### `SequentialRingNumber`

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | `str` (optional) | Phone number in sequence |
| `answer_confirmation_required_enabled` | `bool` (optional) | Require called party to press 1 to accept |
| `number_of_rings` | `int` (optional) | Rings before advancing to next number |

#### `SequentialRingCriteria` (extends `SelectiveCriteria`)

Uses `ringEnabled` as the enabled attribute. See [Shared Criteria Model](#shared-criteria-model-selectivecriteria) below.

### Methods

#### Read Settings

```python
SequentialRingApi.read(
    entity_id: str,
    org_id: str = None
) -> SequentialRing
```

#### Configure Settings

```python
SequentialRingApi.configure(
    entity_id: str,
    settings: SequentialRing,
    org_id: str = None
) -> None
```

**Note:** The `criteria` list is excluded from the update payload. Criteria are managed separately.

#### Criteria CRUD

```python
SequentialRingApi.create_criteria(entity_id: str, settings: SequentialRingCriteria, org_id: str = None) -> str
SequentialRingApi.read_criteria(entity_id: str, id: str, org_id: str = None) -> SequentialRingCriteria
SequentialRingApi.configure_criteria(entity_id: str, id: str, settings: SequentialRingCriteria, org_id: str = None) -> None
SequentialRingApi.delete_criteria(entity_id: str, id: str, org_id: str = None) -> None
```

---

## 6. Single Number Reach

Ring remote destinations (mobile, home, etc.) alongside or instead of the office phone. Unlike Simultaneous Ring, Single Number Reach operates at the `telephony/config` level and manages individual number entries with their own IDs.

**SDK path:** `api.person_settings.single_number_reach`
**REST base:** `telephony/config/people/{person_id}/singleNumberReach`
**API class:** `SingleNumberReachApi`

### Data Models

#### `SingleNumberReach`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable Single Number Reach |
| `alert_all_numbers_for_click_to_dial_calls_enabled` | `bool` (optional) | Ring SNR numbers for click-to-dial calls |
| `numbers` | `list[SingleNumberReachNumber]` (optional) | Array of SNR number entries |

#### `SingleNumberReachNumber`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` (optional) | SNR entry ID (base64-encoded phone number; changes if number is modified) |
| `phone_number` | `str` (optional) | Phone number in E.164 format |
| `enabled` | `bool` (optional) | Enable/disable this specific number |
| `name` | `str` (optional) | Display name for this entry |
| `do_not_forward_calls_enabled` | `bool` (optional) | Skip call forwarding settings for this number |
| `answer_confirmation_enabled` | `bool` (optional) | Prompt recipient to press a key before connecting |

### Methods

#### Read Settings

```python
SingleNumberReachApi.read(
    person_id: str
) -> SingleNumberReach
```

**Scopes:** `spark-admin:telephony_config_read`

#### Update Settings

```python
SingleNumberReachApi.update(
    person_id: str,
    alert_all_numbers_for_click_to_dial_calls_enabled: bool = None
) -> None
```

**Scopes:** `spark-admin:telephony_config_write`

**Note:** This only updates the top-level `alert_all_numbers_for_click_to_dial_calls_enabled` flag. Individual numbers are managed via the SNR number CRUD methods below.

#### SNR Number CRUD

```python
SingleNumberReachApi.create_snr(person_id: str, settings: SingleNumberReachNumber) -> str
SingleNumberReachApi.update_snr(person_id: str, settings: SingleNumberReachNumber) -> str
SingleNumberReachApi.delete_snr(person_id: str, id: str, org_id: str = None) -> None
```

- `create_snr` returns the new entry ID.
- `update_snr` returns the (possibly changed) entry ID. The `settings.id` field is used to identify the target entry. **Important:** The ID can change if the phone number is modified, since the ID is base64-encoded phone number data.
- The `id` field is excluded from the create/update request body automatically.

#### Available Phone Numbers

```python
SingleNumberReachApi.available_phone_numbers(
    location_id: str,
    phone_number: list[str] = None,
    org_id: str = None
) -> Generator[AvailableNumber, None, None]
```

Lists service and standard PSTN numbers at a location that are available for SNR assignment.

**Scopes:** `spark-admin:telephony_config_read`

---

## 7. Selective Accept

Accept calls only from specific callers or during specific schedules. Calls not matching any enabled criteria are rejected.

**SDK path:** `api.person_settings.selective_accept`
**Feature slug:** `selectiveAccept`
**REST path (remapped):** `telephony/config/people/{person_id}/selectiveAccept`
**API class:** `SelectiveAcceptApi`

### Data Models

#### `SelectiveAccept`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable selective accept |
| `criteria` | `list[SelectiveCrit]` (optional, read-only) | List of criteria summaries |

#### `SelectiveAcceptCriteria` (extends `SelectiveCriteria`)

Uses `acceptEnabled` as the enabled attribute and `phoneNumbers` for the number list. See [Shared Criteria Model](#shared-criteria-model-selectivecriteria) below.

### Methods

#### Read Settings

```python
SelectiveAcceptApi.read(
    entity_id: str,
    org_id: str = None
) -> SelectiveAccept
```

#### Configure Settings

```python
SelectiveAcceptApi.configure(
    entity_id: str,
    settings: SelectiveAccept,
    org_id: str = None
) -> None
```

#### Criteria CRUD

```python
SelectiveAcceptApi.create_criteria(entity_id: str, settings: SelectiveAcceptCriteria, org_id: str = None) -> str
SelectiveAcceptApi.read_criteria(entity_id: str, id: str, org_id: str = None) -> SelectiveAcceptCriteria
SelectiveAcceptApi.configure_criteria(entity_id: str, id: str, settings: SelectiveAcceptCriteria, org_id: str = None) -> None
SelectiveAcceptApi.delete_criteria(entity_id: str, id: str, org_id: str = None) -> None
```

---

## 8. Selective Forward

Forward calls to a specific destination based on caller identity and/or schedule. **Takes precedence over standard call forwarding settings.**

**SDK path:** `api.person_settings.selective_forward`
**Feature slug:** `selectiveForward`
**REST path (remapped):** `telephony/config/people/{person_id}/selectiveForward`
**API class:** `SelectiveForwardApi`

### Data Models

#### `SelectiveForward`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable selective forward |
| `default_phone_number_to_forward` | `str` (optional) | Default forward destination |
| `ring_reminder_enabled` | `bool` (optional) | Play ring reminder tone for forwarded calls |
| `destination_voicemail_enabled` | `bool` (optional) | Forward to destination's voicemail (internal numbers only) |
| `criteria` | `list[SelectiveCrit]` (optional, read-only) | Criteria summaries |

#### `SelectiveForwardCriteria` (extends `SelectiveCriteria`)

Uses `forwardEnabled` as the enabled attribute and `numbers` (not `phoneNumbers`) for the number list.

Additional fields beyond the base `SelectiveCriteria`:

| Field | Type | Description |
|-------|------|-------------|
| `forward_to_phone_number` | `str` (optional) | Per-criteria forward destination (overrides default) |
| `send_to_voicemail_enabled` | `bool` (optional) | Forward to voicemail instead |

### Methods

Same pattern as Selective Accept:

```python
SelectiveForwardApi.read(entity_id: str, org_id: str = None) -> SelectiveForward
SelectiveForwardApi.configure(entity_id: str, settings: SelectiveForward, org_id: str = None) -> None

SelectiveForwardApi.create_criteria(entity_id: str, settings: SelectiveForwardCriteria, org_id: str = None) -> str
SelectiveForwardApi.read_criteria(entity_id: str, id: str, org_id: str = None) -> SelectiveForwardCriteria
SelectiveForwardApi.configure_criteria(entity_id: str, id: str, settings: SelectiveForwardCriteria, org_id: str = None) -> None
SelectiveForwardApi.delete_criteria(entity_id: str, id: str, org_id: str = None) -> None
```

---

## 9. Selective Reject

Reject calls from specific callers or during specific schedules. **Takes precedence over Selective Accept.**

**SDK path:** `api.person_settings.selective_reject`
**Feature slug:** `selectiveReject`
**REST path (remapped):** `telephony/config/people/{person_id}/selectiveReject`
**API class:** `SelectiveRejectApi`

### Data Models

#### `SelectiveReject`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable selective reject |
| `criteria` | `list[SelectiveCrit]` (optional, read-only) | Criteria summaries |

#### `SelectiveRejectCriteria` (extends `SelectiveCriteria`)

Uses `rejectEnabled` as the enabled attribute and `phoneNumbers` for the number list. See [Shared Criteria Model](#shared-criteria-model-selectivecriteria) below.

### Methods

Same pattern:

```python
SelectiveRejectApi.read(entity_id: str, org_id: str = None) -> SelectiveReject
SelectiveRejectApi.configure(entity_id: str, settings: SelectiveReject, org_id: str = None) -> None

SelectiveRejectApi.create_criteria(entity_id: str, settings: SelectiveRejectCriteria, org_id: str = None) -> str
SelectiveRejectApi.read_criteria(entity_id: str, id: str, org_id: str = None) -> SelectiveRejectCriteria
SelectiveRejectApi.configure_criteria(entity_id: str, id: str, settings: SelectiveRejectCriteria, org_id: str = None) -> None
SelectiveRejectApi.delete_criteria(entity_id: str, id: str, org_id: str = None) -> None
```

---

## 10. Priority Alert

Play a distinctive ring pattern for calls matching specific criteria (caller identity, schedule). Useful for VIP caller identification.

**SDK path:** `api.person_settings.priority_alert` <!-- NEEDS VERIFICATION: PriorityAlertApi is not imported into PersonSettingsApi; may only be available via workspace_settings or MePriorityAlertApi -->
**Feature slug:** `priorityAlert`
**API class:** `PriorityAlertApi`

### Data Models

#### `PriorityAlert`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` (optional) | Enable/disable priority alert |
| `criteria` | `list[SelectiveCrit]` (optional, read-only) | Criteria summaries |

#### `PriorityAlertCriteria` (extends `SelectiveCriteria`)

Uses `notificationEnabled` as the enabled attribute. See [Shared Criteria Model](#shared-criteria-model-selectivecriteria) below.

### Methods

Same pattern:

```python
PriorityAlertApi.read(entity_id: str, org_id: str = None) -> PriorityAlert
PriorityAlertApi.configure(entity_id: str, settings: PriorityAlert, org_id: str = None) -> None

PriorityAlertApi.create_criteria(entity_id: str, settings: PriorityAlertCriteria, org_id: str = None) -> str
PriorityAlertApi.read_criteria(entity_id: str, id: str, org_id: str = None) -> PriorityAlertCriteria
PriorityAlertApi.configure_criteria(entity_id: str, id: str, settings: PriorityAlertCriteria, org_id: str = None) -> None
PriorityAlertApi.delete_criteria(entity_id: str, id: str, org_id: str = None) -> None
```

---

## Shared Criteria Model (`SelectiveCriteria`)

All schedule/caller-based features (Simultaneous Ring, Sequential Ring, Selective Accept/Forward/Reject, Priority Alert) share a common criteria model. Each feature subclasses `SelectiveCriteria` with a different `_enabled_attr` value.

### `SelectiveCriteria` Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` (optional) | Unique criteria ID (excluded from create/update payloads) |
| `schedule_name` | `str` (optional) | Name of the schedule. Omit both `schedule_name` and `schedule_type` for all-hours/all-days |
| `schedule_type` | `ScheduleType` (optional) | `businessHours` or `holidays` |
| `schedule_level` | `SelectiveScheduleLevel` (optional) | `GROUP` or `GLOBAL` |
| `calls_from` | `SelectiveFrom` (optional) | Which callers trigger this criteria |
| `anonymous_callers_enabled` | `bool` (optional) | Allow private/anonymous numbers (only when `calls_from=SELECT_PHONE_NUMBERS`) |
| `unavailable_callers_enabled` | `bool` (optional) | Allow unavailable numbers (only when `calls_from=SELECT_PHONE_NUMBERS`) |
| `phone_numbers` | `list[str]` (optional, E.164) | Specific numbers (only when `calls_from=SELECT_PHONE_NUMBERS`) |
| `enabled` | `bool` (optional) | Enable/disable this criteria. Criteria with `enabled=false` take priority |

### `SelectiveFrom` Enum

| Value | Meaning |
|-------|---------|
| `ANY_PHONE_NUMBER` | All incoming numbers |
| `SELECT_PHONE_NUMBERS` | Only specific numbers (use with `phone_numbers`, `anonymous_callers_enabled`, `unavailable_callers_enabled`) |
| `ANY_INTERNAL` | Any internal number |
| `ANY_EXTERNAL` | Any external number |

### `SelectiveCrit` (Summary Model)

Returned in the top-level settings `criteria` list (read-only summaries):

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` (optional) | Criteria ID |
| `schedule_name` | `str` (optional) | Schedule name |
| `source` | `SelectiveSource` (optional) | `ALL_NUMBERS` or `SPECIFIC_NUMBERS` |
| `enabled` | `bool` (optional) | Whether this criteria is active |

### Enabled Attribute Mapping by Feature

The REST API uses different field names for the "enabled" flag on each criteria type. The SDK normalizes this to `enabled` on the Python model.

| Feature | REST API `_enabled_attr` | REST API `_phone_numbers` attr |
|---------|--------------------------|-------------------------------|
| Simultaneous Ring | `ringEnabled` | `phoneNumbers` |
| Sequential Ring | `ringEnabled` | `phoneNumbers` |
| Selective Accept | `acceptEnabled` | `phoneNumbers` |
| Selective Forward | `forwardEnabled` | `numbers` |
| Selective Reject | `rejectEnabled` | `phoneNumbers` |
| Priority Alert | `notificationEnabled` | `phoneNumbers` |

---

## Precedence Order

When multiple selective features are enabled simultaneously, the following precedence applies:

1. **Selective Reject** — highest priority; rejects matching calls outright
2. **Selective Accept** — only accepts calls matching criteria
3. **Selective Forward** — forwards matching calls; takes precedence over standard call forwarding
4. **Standard Call Forwarding** (Always > Busy > No Answer > Business Continuity)

<!-- NEEDS VERIFICATION: exact precedence order between Selective Reject and Selective Accept is stated in SDK docstrings ("Selective Reject takes precedence over Selectively Accept Calls") but full interaction with Priority Alert and ring features is not documented in the SDK source -->

---

## "Me" API Variants

For user-token access (a person managing their own settings), the SDK provides parallel APIs under `api.me.*`:

| Feature | Admin API (`person_settings.*`) | User API (`me.*`) |
|---------|-------------------------------|-------------------|
| Forwarding | `forwarding` | `forwarding` (`MeForwardingApi`) |
| Call Waiting | `call_waiting` | `call_waiting` (`MeCallWaitingApi`) |
| DND | `dnd` | `dnd` (`MeDNDApi`) |
| Simultaneous Ring | N/A (see note) | `sim_ring` (`MeSimRingApi`) |
| Sequential Ring | N/A (see note) | `sequential_ring` (`MeSequentialRingApi`) |
| Single Number Reach | `single_number_reach` | `snr` (`MeSNRApi`) |
| Selective Accept | `selective_accept` | `selective_accept` (`MeSelectiveAcceptApi`) |
| Selective Forward | `selective_forward` | `selective_forward` (`MeSelectiveForwardApi`) |
| Selective Reject | `selective_reject` | `selective_reject` (`MeSelectiveRejectApi`) |
| Priority Alert | N/A (see note) | `priority_alert` (`MePriorityAlertApi`) |

> **Note:** `SimRingApi`, `SequentialRingApi`, and `PriorityAlertApi` are **not** imported into the admin-level `PersonSettingsApi` class. They are available under `workspace_settings` (for workspaces) and the `me` API (for user self-service). For admin-level person management of these features, use the REST API directly or the workspace-settings API if the target is a workspace. <!-- NEEDS VERIFICATION: whether admin-level person endpoints exist for these features in the Webex Calling REST API -->

---

## URL Routing Internals

The `PersonSettingsApiChild` base class builds endpoints based on the `selector` parameter:

| Selector | URL Template |
|----------|-------------|
| `person` (default) | `people/{person_id}/features/{feature}{path}` |
| `workspace` | `workspaces/{person_id}/features/{feature}{path}` |
| `location` | `telephony/config/locations/{person_id}/{feature}{path}` |
| `virtual_line` | `telephony/config/virtualLines/{person_id}/{feature}{path}` |

Some feature/selector combinations are remapped to different URL bases. For persons, the following features use `telephony/config/people/{person_id}/` instead of `people/{person_id}/features/`:

- `selectiveAccept`
- `selectiveForward`
- `selectiveReject`
- `musicOnHold`
- `emergencyCallbackNumber`
- `outgoingPermission/` (and sub-paths)
- `agent`

---

## Source Files

| File | Contents |
|------|----------|
| `wxc_sdk/person_settings/__init__.py` | `PersonSettingsApi` — parent class aggregating all sub-APIs |
| `wxc_sdk/person_settings/common.py` | `PersonSettingsApiChild` base class, `ApiSelector` enum |
| `wxc_sdk/person_settings/forwarding.py` | `PersonForwardingApi`, forwarding data models |
| `wxc_sdk/person_settings/call_waiting.py` | `CallWaitingApi` |
| `wxc_sdk/person_settings/dnd.py` | `DndApi`, `DND` model |
| `wxc_sdk/person_settings/sim_ring.py` | `SimRingApi`, `SimRing`, `SimRingNumber`, `SimRingCriteria` |
| `wxc_sdk/person_settings/sequential_ring.py` | `SequentialRingApi`, `SequentialRing`, `SequentialRingNumber`, `SequentialRingCriteria` |
| `wxc_sdk/person_settings/single_number_reach/__init__.py` | `SingleNumberReachApi`, `SingleNumberReach`, `SingleNumberReachNumber` |
| `wxc_sdk/person_settings/selective_accept.py` | `SelectiveAcceptApi`, `SelectiveAccept`, `SelectiveAcceptCriteria` |
| `wxc_sdk/person_settings/selective_forward.py` | `SelectiveForwardApi`, `SelectiveForward`, `SelectiveForwardCriteria` |
| `wxc_sdk/person_settings/selective_reject.py` | `SelectiveRejectApi`, `SelectiveReject`, `SelectiveRejectCriteria` |
| `wxc_sdk/person_settings/priority_alert.py` | `PriorityAlertApi`, `PriorityAlert`, `PriorityAlertCriteria` |
| `wxc_sdk/common/selective.py` | `SelectiveCriteria` base, `SelectiveCrit`, `SelectiveFrom`, `SelectiveScheduleLevel` |
| `examples/reset_call_forwarding.py` | Bulk reset forwarding example |

---

## See Also

- **[Location Call Settings — Core](location-call-settings-core.md)** — Location-level call forwarding, call intercept, and ECBN settings that serve as defaults for person-level overrides
