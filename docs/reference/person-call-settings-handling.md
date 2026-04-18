<!-- Updated by playbook session 2026-03-18 -->
# Person Call Settings — Call Handling Reference

## Sources

- wxc_sdk v1.30.0 (PersonSettingsApi)
- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Person Call Settings APIs

Person-level call handling settings control how incoming calls are routed, filtered, and alerted for individual Webex Calling users. All APIs live under `PersonSettingsApi` (accessed via `api.person_settings.*`) and share a common base class pattern.

> **SDK access path:** `api.person_settings.<feature>`
> **REST base:** `people/{person_id}/features/{feature}` (with some remapped to `telephony/config/people/{person_id}/...`)
> **Also available for:** Workspaces, Virtual Lines (same API classes, different URL selectors)

---

## Admin vs User-Only Access

Not all person call handling endpoints support admin-level access. Four features are **user-only** — they exist only at `/telephony/config/people/me/settings/{feature}` and require user-level OAuth. An admin cannot read or write these settings for another user.

| Feature | Admin Access | Admin REST Path | User REST Path |
|---------|-------------|-----------------|----------------|
| Call Forwarding | **Yes** | `/people/{id}/features/callForwarding` | `/people/me/features/callForwarding` |
| Call Waiting | **Yes** | `/people/{id}/features/callWaiting` | `/people/me/features/callWaiting` |
| Do Not Disturb | **Yes** | `/people/{id}/features/doNotDisturb` | `/people/me/features/doNotDisturb` |
| Simultaneous Ring | **No — user-only** | N/A | `/telephony/config/people/me/settings/simultaneousRing` |
| Sequential Ring | **No — user-only** | N/A | `/telephony/config/people/me/settings/sequentialRing` |
| Single Number Reach | **Yes** | `/telephony/config/people/{id}/singleNumberReach` | `/telephony/config/people/me/singleNumberReach` |
| Selective Accept | **Yes** | `/telephony/config/people/{id}/selectiveAccept` | `/telephony/config/people/me/selectiveAccept` |
| Selective Forward | **Yes** | `/telephony/config/people/{id}/selectiveForward` | `/telephony/config/people/me/selectiveForward` |
| Selective Reject | **Yes** | `/telephony/config/people/{id}/selectiveReject` | `/telephony/config/people/me/selectiveReject` |
| Priority Alert | **No — user-only** | N/A | `/telephony/config/people/me/settings/priorityAlert` |
| Call Notify | **No — user-only** | N/A | `/telephony/config/people/me/settings/callNotify` |

> **Call Notify** (`callNotify`) is a user-only feature not yet documented in this file. It follows the same criteria-based pattern as Priority Alert but sends email/text notifications instead of changing ring patterns.

### Beta: User Self-Service Endpoints

> **Beta API** — These endpoints are tagged as beta and may change without notice.

The following settings are available as user self-service endpoints (`/telephony/config/people/me/settings/...`) but are currently in beta:

| Setting | GET | PUT | Path Suffix |
|---------|-----|-----|-------------|
| Call Policies | Yes | Yes | `callPolicies` |
| Executive Screening | Yes | Yes | `executive/screening` |
| Executive Call Filtering | Yes | Yes | `executive/callFiltering` |
| Call Filtering Criteria | Yes | Yes (+ POST/DELETE) | `executive/callFiltering/criteria/{id}` |
| Do Not Disturb | Yes | Yes | `doNotDisturb` |
| Executive Alert | Yes | Yes | `executive/alert` |
| Country Config | Yes | - | `../countries/{countryCode}` |
| Announcement Languages | Yes | - | `../announcementLanguages` |

These require **user-level OAuth** (not admin tokens). The admin-path equivalents (`/people/{personId}/...`) exist for DND, executive screening/filtering, and executive alert but NOT for call policies.

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
**Admin REST path:** `/people/{person_id}/features/callForwarding`
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

### CLI Examples

```bash
# Read call forwarding settings for a person
wxcli user-settings show-call-forwarding Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Enable always-forward to a destination (uses --json-body for nested settings)
wxcli user-settings update-call-forwarding Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --json-body '{"callForwarding":{"always":{"enabled":true,"destination":"+12223334444","ringReminderEnabled":true}}}'

# Enable no-answer forwarding with 5 rings
wxcli user-settings update-call-forwarding Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --json-body '{"callForwarding":{"noAnswer":{"enabled":true,"destination":"+15556667777","numberOfRings":5}}}'

# Enable business continuity forwarding
wxcli user-settings update-call-forwarding Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --json-body '{"businessContinuity":{"enabled":true,"destination":"+18889990000"}}'
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read call forwarding settings
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/callForwarding")
# Returns: {"callForwarding": {"always": {...}, "busy": {...}, "noAnswer": {...}}, "businessContinuity": {...}}

# PUT — update call forwarding settings
body = {
    "callForwarding": {
        "always": {
            "enabled": True,
            "destination": "+12223334444",
            "destinationVoicemailEnabled": True,
            "ringReminderEnabled": True
        },
        "busy": {"enabled": False},
        "noAnswer": {"enabled": True, "destination": "+15556667777", "numberOfRings": 5}
    },
    "businessContinuity": {"enabled": True, "destination": "+18889990000"}
}
api.session.rest_put(f"{BASE}/people/{person_id}/features/callForwarding", json=body)
```

### Gotchas

- `systemMaxNumberOfRings` is read-only; omit it from the PUT body.
- Call forwarding requires `--json-body` in the CLI because the payload has nested objects (`callForwarding.always`, `callForwarding.busy`, etc.).

---

## 2. Call Waiting

Controls whether a user can place an active call on hold to answer a second incoming call. A tone alerts the user of the incoming call.

**SDK path:** `api.person_settings.call_waiting`
**Feature slug:** `callWaiting`
**Admin REST path:** `/people/{person_id}/features/callWaiting`
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

### CLI Examples

```bash
# Read call waiting settings for a person
wxcli user-settings show-call-waiting Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Enable call waiting
wxcli user-settings update-call-waiting Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --enabled

# Disable call waiting
wxcli user-settings update-call-waiting Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --no-enabled
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read call waiting
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/callWaiting")
# Returns: {"enabled": true}

# PUT — update call waiting
api.session.rest_put(f"{BASE}/people/{person_id}/features/callWaiting", json={"enabled": False})
```

---

## 3. Do Not Disturb (DND)

When enabled, all incoming calls receive busy treatment. Optionally plays a ring splash (brief tone) on the desktop phone as a reminder.

**SDK path:** `api.person_settings.dnd`
**Feature slug:** `doNotDisturb`
**Admin REST path:** `/people/{person_id}/features/doNotDisturb`
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

### CLI Examples

```bash
# Read DND settings for a person
wxcli user-settings show-do-not-disturb Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Enable DND with ring splash
wxcli user-settings update-do-not-disturb Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --enabled --ring-splash-enabled

# Disable DND
wxcli user-settings update-do-not-disturb Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --no-enabled

# Enable DND but keep mobile ringing (Webex Go override)
wxcli user-settings update-do-not-disturb Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --enabled --webex-go-override-enabled
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read DND settings
result = api.session.rest_get(f"{BASE}/people/{person_id}/features/doNotDisturb")
# Returns: {"enabled": true, "ringSplashEnabled": true}

# PUT — update DND settings
api.session.rest_put(f"{BASE}/people/{person_id}/features/doNotDisturb", json={
    "enabled": True,
    "ringSplashEnabled": True
})
```

---

## 4. Simultaneous Ring

> **Admin access: Not available.** This endpoint only exists at `/telephony/config/people/me/settings/simultaneousRing` (user-level OAuth). No admin-level path exists — `/telephony/config/people/{personId}/simultaneousRing` returns 404.

Ring the user's office phone and up to 10 additional phone numbers at the same time when an incoming call arrives. Supports schedule-based criteria to control when simultaneous ring is active.

**SDK path:** `api.person_settings.sim_ring`
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

### CLI Examples

No dedicated CLI commands for Simultaneous Ring. Use Raw HTTP or the SDK.

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read simultaneous ring settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/simultaneousRing")
# Returns: {"enabled": true, "doNotRingIfOnCallEnabled": false, "phoneNumbers": [...], "criterias": [...]}

# PUT — update simultaneous ring settings (criteria list excluded)
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/simultaneousRing", json={
    "enabled": True,
    "doNotRingIfOnCallEnabled": True,
    "phoneNumbers": [
        {"phoneNumber": "+12223334444", "answerConfirmationRequiredEnabled": False}
    ]
})

# Criteria CRUD
# POST — create criteria (returns ID in Location header)
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/simultaneousRing/criteria", json={...})
# GET — read single criteria
api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/simultaneousRing/criteria/{criteria_id}")
# PUT — update criteria
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/simultaneousRing/criteria/{criteria_id}", json={...})
# DELETE — delete criteria
api.session.rest_delete(f"{BASE}/telephony/config/people/{person_id}/simultaneousRing/criteria/{criteria_id}")
```

### Gotchas

- **User-only endpoint.** No admin-level path exists. The paths `telephony/config/people/{personId}/simultaneousRing` and `people/{personId}/features/simultaneousRing` both return 404 with an admin token. Only `/telephony/config/people/me/settings/simultaneousRing` works, and it requires user-level OAuth.
- `SimRingApi` may not be imported into `PersonSettingsApi` in some SDK versions.
- The `criteria` list is excluded from the update payload. Criteria are managed via dedicated CRUD methods.

---

## 5. Sequential Ring

> **Admin access: Not available.** This endpoint only exists at `/telephony/config/people/me/settings/sequentialRing` (user-level OAuth). No admin-level path exists — `/telephony/config/people/{personId}/sequentialRing` returns 404.

Ring up to five phone numbers one after another when an incoming call arrives. Configurable ring counts per number, optional primary-line-first behavior, and schedule-based criteria.

**SDK path:** `api.person_settings.sequential_ring`
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

### CLI Examples

No dedicated CLI commands for Sequential Ring. Use Raw HTTP or the SDK.

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read sequential ring settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/sequentialRing")
# Returns: {"enabled": true, "ringBaseLocationFirstEnabled": true, "baseLocationNumberOfRings": 3, ...}

# PUT — update sequential ring settings (criteria list excluded)
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/sequentialRing", json={
    "enabled": True,
    "ringBaseLocationFirstEnabled": True,
    "baseLocationNumberOfRings": 3,
    "continueIfBaseLocationIsBusyEnabled": True,
    "callsToVoicemailEnabled": True,
    "phoneNumbers": [
        {"phoneNumber": "+12223334444", "answerConfirmationRequiredEnabled": False, "numberOfRings": 3}
    ]
})

# Criteria CRUD
# POST — create criteria
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/sequentialRing/criteria", json={...})
# GET — read single criteria
api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/sequentialRing/criteria/{criteria_id}")
# PUT — update criteria
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/sequentialRing/criteria/{criteria_id}", json={...})
# DELETE — delete criteria
api.session.rest_delete(f"{BASE}/telephony/config/people/{person_id}/sequentialRing/criteria/{criteria_id}")
```

### Gotchas

- **User-only endpoint.** No admin-level path exists. The paths `telephony/config/people/{personId}/sequentialRing` and `people/{personId}/features/sequentialRing` both return 404 with an admin token. Only `/telephony/config/people/me/settings/sequentialRing` works, and it requires user-level OAuth.
- `SequentialRingApi` may not be imported into `PersonSettingsApi` in some SDK versions.
- The `criteria` list is excluded from the update payload. Criteria are managed via dedicated CRUD methods.

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

### CLI Examples

```bash
# Read Single Number Reach settings for a person
wxcli single-number-reach list-single-number-reach Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Update top-level SNR settings (alert all numbers for click-to-dial)
wxcli single-number-reach update Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --alert-all-numbers-for-click-to-dial-calls-enabled

# Create an SNR number entry
wxcli single-number-reach create Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --phone-number "+12223334444" --enabled --name "Mobile" \
  --answer-confirmation-enabled

# Update an SNR number entry
wxcli single-number-reach update-numbers Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --json-body '{"enabled": false}'

# Delete an SNR number entry
wxcli single-number-reach delete Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 MTIyMjMzMzQ0NDQ=

# List available phone numbers for SNR at a location
wxcli single-number-reach list Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzU2Nzg=
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read Single Number Reach settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/singleNumberReach")
# Returns: {"enabled": true, "alertAllNumbersForClickToDialCallsEnabled": false, "numbers": [...]}

# PUT — update top-level SNR settings
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/singleNumberReach", json={
    "alertAllNumbersForClickToDialCallsEnabled": True
})

# SNR Number CRUD
# POST — create an SNR number entry
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/singleNumberReach/numbers", json={
    "phoneNumber": "+12223334444",
    "enabled": True,
    "name": "Mobile",
    "doNotForwardCallsEnabled": False,
    "answerConfirmationEnabled": True
})

# PUT — update an SNR number entry
api.session.rest_put(
    f"{BASE}/telephony/config/people/{person_id}/singleNumberReach/numbers/{snr_number_id}",
    json={"enabled": False}
)

# DELETE — delete an SNR number entry
api.session.rest_delete(
    f"{BASE}/telephony/config/people/{person_id}/singleNumberReach/numbers/{snr_number_id}"
)

# GET — list available phone numbers for SNR at a location
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/singleNumberReach/availableNumbers"
)
```

### Gotchas

- SNR number IDs are base64-encoded phone numbers. The ID changes if the phone number is modified.
- The `update` method only updates the top-level `alertAllNumbersForClickToDialCallsEnabled` flag. Individual numbers are managed via the SNR number CRUD methods (`create`, `update-numbers`, `delete`).
- The `id` field is excluded from the create/update request body automatically.

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

### CLI Examples

```bash
# List selective accept criteria for a person
wxcli user-settings list-selective-accept Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Enable selective accept
wxcli user-settings update-selective-accept Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --enabled

# Disable selective accept
wxcli user-settings update-selective-accept Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --no-enabled

# Create a selective accept criteria
wxcli user-settings create-criteria-selective-accept Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --accept-enabled --schedule-name "Business Hours" \
  --anonymous-callers-enabled --no-unavailable-callers-enabled

# Read a specific criteria
wxcli user-settings show-criteria-selective-accept Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 CRITERIA_ID

# Delete a criteria
wxcli user-settings delete-criteria-selective-accept Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 CRITERIA_ID
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read selective accept settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/selectiveAccept")
# Returns: {"enabled": true, "criterias": [...]}

# PUT — update selective accept (enable/disable only; criteria managed separately)
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/selectiveAccept", json={
    "enabled": True
})

# Criteria CRUD
# POST — create criteria (returns ID in Location header)
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/selectiveAccept/criteria", json={
    "acceptEnabled": True,
    "scheduleName": "Business Hours",
    "scheduleType": "businessHours",
    "callsFrom": "SELECT_PHONE_NUMBERS",
    "phoneNumbers": ["+12223334444"],
    "anonymousCallersEnabled": False,
    "unavailableCallersEnabled": False
})
# GET — read single criteria
api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/selectiveAccept/criteria/{criteria_id}")
# PUT — update criteria
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/selectiveAccept/criteria/{criteria_id}", json={...})
# DELETE — delete criteria
api.session.rest_delete(f"{BASE}/telephony/config/people/{person_id}/selectiveAccept/criteria/{criteria_id}")
```

### Gotchas

- The REST endpoint is remapped to `telephony/config/people/{person_id}/selectiveAccept` (not `people/{person_id}/features/selectiveAccept`).
- Criteria use `acceptEnabled` (not `enabled`) as the REST API field name for the criteria-level enable flag. The SDK normalizes this to `enabled`.
- The `criteria` list in the top-level settings is read-only. Criteria are managed via dedicated CRUD commands/methods.

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

### CLI Examples

```bash
# List selective forward settings and criteria for a person
wxcli user-settings list-selective-forward Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Enable selective forward with a default destination
wxcli user-settings update-selective-forward Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --enabled --default-phone-number-to-forward "+15556667777" --ring-reminder-enabled

# Disable selective forward
wxcli user-settings update-selective-forward Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --no-enabled

# Create a selective forward criteria (forward external calls to voicemail)
wxcli user-settings create-criteria-selective-forward Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --forward-to-phone-number "+18889990000" --send-to-voicemail-enabled \
  --forward-enabled

# Read a specific criteria
wxcli user-settings show-criteria-selective-forward Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 CRITERIA_ID

# Delete a criteria
wxcli user-settings delete-criteria-selective-forward Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 CRITERIA_ID
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read selective forward settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/selectiveForward")
# Returns: {"enabled": true, "defaultPhoneNumberToForward": "+1...", "ringReminderEnabled": false, ...}

# PUT — update selective forward settings (criteria managed separately)
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/selectiveForward", json={
    "enabled": True,
    "defaultPhoneNumberToForward": "+15556667777",
    "ringReminderEnabled": True,
    "destinationVoicemailEnabled": False
})

# Criteria CRUD
# POST — create criteria
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/selectiveForward/criteria", json={
    "forwardEnabled": True,
    "forwardToPhoneNumber": "+18889990000",
    "sendToVoicemailEnabled": False,
    "callsFrom": "ANY_EXTERNAL"
})
# GET — read single criteria
api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/selectiveForward/criteria/{criteria_id}")
# PUT — update criteria
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/selectiveForward/criteria/{criteria_id}", json={...})
# DELETE — delete criteria
api.session.rest_delete(f"{BASE}/telephony/config/people/{person_id}/selectiveForward/criteria/{criteria_id}")
```

### Gotchas

- Selective Forward uses `forwardEnabled` (not `enabled`) and `numbers` (not `phoneNumbers`) for its criteria enabled attr and number list, respectively. This differs from Selective Accept and Selective Reject.
- Selective Forward takes precedence over standard call forwarding settings.
- The REST endpoint is remapped to `telephony/config/people/{person_id}/selectiveForward`.
- Each criteria can override the default forward destination via `forwardToPhoneNumber`.

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

### CLI Examples

```bash
# List selective reject criteria for a person
wxcli user-settings list-selective-reject Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0

# Enable selective reject
wxcli user-settings update-selective-reject Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --enabled

# Disable selective reject
wxcli user-settings update-selective-reject Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 --no-enabled

# Create a selective reject criteria (reject anonymous callers)
wxcli user-settings create-criteria-selective-reject Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 \
  --reject-enabled --anonymous-callers-enabled --no-unavailable-callers-enabled

# Read a specific criteria
wxcli user-settings show-criteria-selective-reject Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 CRITERIA_ID

# Delete a criteria
wxcli user-settings delete-criteria-selective-reject Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0 CRITERIA_ID
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read selective reject settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/selectiveReject")
# Returns: {"enabled": true, "criterias": [...]}

# PUT — update selective reject (enable/disable only; criteria managed separately)
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/selectiveReject", json={
    "enabled": True
})

# Criteria CRUD
# POST — create criteria
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/selectiveReject/criteria", json={
    "rejectEnabled": True,
    "callsFrom": "SELECT_PHONE_NUMBERS",
    "phoneNumbers": ["+15551234567"],
    "anonymousCallersEnabled": True,
    "unavailableCallersEnabled": False
})
# GET — read single criteria
api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/selectiveReject/criteria/{criteria_id}")
# PUT — update criteria
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/selectiveReject/criteria/{criteria_id}", json={...})
# DELETE — delete criteria
api.session.rest_delete(f"{BASE}/telephony/config/people/{person_id}/selectiveReject/criteria/{criteria_id}")
```

### Gotchas

- Selective Reject takes precedence over Selective Accept. If both are enabled with overlapping criteria, the reject rule wins.
- The REST endpoint is remapped to `telephony/config/people/{person_id}/selectiveReject`.
- Criteria use `rejectEnabled` (not `enabled`) as the REST API field name.

---

## 10. Priority Alert

> **Admin access: Not available.** This endpoint only exists at `/telephony/config/people/me/settings/priorityAlert` (user-level OAuth). No admin-level path exists — `/telephony/config/people/{personId}/priorityAlert` returns 404.

Play a distinctive ring pattern for calls matching specific criteria (caller identity, schedule). Useful for VIP caller identification.

**SDK path:** `api.person_settings.priority_alert`
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

### CLI Examples

No dedicated CLI commands for Priority Alert. Use Raw HTTP or the SDK.

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# GET — read priority alert settings
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/priorityAlert")
# Returns: {"enabled": true, "criterias": [...]}

# PUT — update priority alert (enable/disable only; criteria managed separately)
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/priorityAlert", json={
    "enabled": True
})

# Criteria CRUD
# POST — create criteria
api.session.rest_post(f"{BASE}/telephony/config/people/{person_id}/priorityAlert/criteria", json={
    "notificationEnabled": True,
    "callsFrom": "SELECT_PHONE_NUMBERS",
    "phoneNumbers": ["+12223334444"],
    "anonymousCallersEnabled": False,
    "unavailableCallersEnabled": False
})
# GET — read single criteria
api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/priorityAlert/criteria/{criteria_id}")
# PUT — update criteria
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/priorityAlert/criteria/{criteria_id}", json={...})
# DELETE — delete criteria
api.session.rest_delete(f"{BASE}/telephony/config/people/{person_id}/priorityAlert/criteria/{criteria_id}")
```

### Gotchas

- **User-only endpoint.** No admin-level path exists. The path `telephony/config/people/{personId}/priorityAlert` returns 404 with an admin token. Only `/telephony/config/people/me/settings/priorityAlert` works, and it requires user-level OAuth.
- `PriorityAlertApi` may not be imported into `PersonSettingsApi` in some SDK versions.
- Criteria use `notificationEnabled` (not `enabled`) as the REST API field name.
- Priority Alert only changes the ring pattern; it does not affect call routing or acceptance.

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

<!-- Verified via wxc_sdk source (selective_reject.py) and OpenAPI spec 2026-03-19: Both sources confirm "This setting [Selective Reject] takes precedence over Selectively Accept Calls." The precedence order Selective Reject > Selective Accept > Selective Forward > Standard Forwarding is confirmed. Full interaction with Priority Alert and ring features remains undocumented in source. -->

---

## "Me" API Variants

For user-token access (a person managing their own settings), the SDK provides parallel APIs under `api.me.*`:

| Feature | Admin API (`person_settings.*`) | User API (`me.*`) |
|---------|-------------------------------|-------------------|
| Forwarding | `forwarding` | `forwarding` (`MeForwardingApi`) |
| Call Waiting | `call_waiting` | `call_waiting` (`MeCallWaitingApi`) |
| DND | `dnd` | `dnd` (`MeDNDApi`) |
| Simultaneous Ring | N/A in SDK¹ | `sim_ring` (`MeSimRingApi`) |
| Sequential Ring | N/A in SDK¹ | `sequential_ring` (`MeSequentialRingApi`) |
| Single Number Reach | `single_number_reach` | `snr` (`MeSNRApi`) |
| Selective Accept | `selective_accept` | `selective_accept` (`MeSelectiveAcceptApi`) |
| Selective Forward | `selective_forward` | `selective_forward` (`MeSelectiveForwardApi`) |
| Selective Reject | `selective_reject` | `selective_reject` (`MeSelectiveRejectApi`) |
| Priority Alert | N/A in SDK¹ | `priority_alert` (`MePriorityAlertApi`) |

> **¹ "N/A in SDK" means the SDK class is not wired to `PersonSettingsApi`** — and **no admin-level REST endpoint exists** for these features. Simultaneous Ring, Sequential Ring, and Priority Alert are user-only: they only work at `/telephony/config/people/me/settings/{feature}` with user-level OAuth. An admin cannot read or write these settings for another user. The Raw HTTP examples in sections 4, 5, and 10 above show the `{person_id}` path pattern used by the SDK internally, but these paths return 404 when called with an admin token against another user.

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

## Gotchas (Cross-Cutting)

- **Four features are user-only (no admin access):** Simultaneous Ring, Sequential Ring, Priority Alert, and Call Notify only exist at `/telephony/config/people/me/settings/{feature}` and require user-level OAuth. There is no admin-level path — an admin cannot read or write these settings for another user. All other call handling features in this doc support admin-level access.
- **Selective features remapped URLs:** Selective Accept, Selective Forward, and Selective Reject all use `telephony/config/people/{person_id}/` instead of `people/{person_id}/features/`. This remapping is transparent in the SDK but matters for raw HTTP and CLI usage.
- **Enabled attribute naming varies by feature:** Each criteria-based feature uses a different REST field name for its enabled flag (`ringEnabled`, `acceptEnabled`, `forwardEnabled`, `rejectEnabled`, `notificationEnabled`). The SDK normalizes all of these to `enabled` on the Python model, but CLI `--json-body` and raw HTTP payloads must use the REST field names.
- **Criteria are managed separately:** For all criteria-based features (Sim Ring, Sequential Ring, Selective Accept/Forward/Reject, Priority Alert), the `criteria` list in the top-level settings response is read-only. Create, update, and delete criteria via their dedicated CRUD endpoints.
- **SDK import gaps:** `SimRingApi`, `SequentialRingApi`, and `PriorityAlertApi` may not be wired into `PersonSettingsApi` in some SDK versions. These are also user-only features with no admin-level REST endpoints (see above).
- **No CLI for Sim Ring, Sequential Ring, or Priority Alert:** These features do not have wxcli command groups. Use Raw HTTP or the SDK.
- **Selective Forward uses `numbers` not `phoneNumbers`:** Unlike all other criteria-based features that use `phoneNumbers` for their number list, Selective Forward criteria use `numbers`.
- **Nested settings require `--json-body` in CLI:** Call forwarding and other nested payloads cannot be expressed with simple CLI flags. Use `--json-body '{"key": {...}}'` for these.

---

## See Also

- **[Location Call Settings — Core](location-calling-core.md)** — Location-level call forwarding, call intercept, and ECBN settings that serve as defaults for person-level overrides
- **[self-service-call-settings.md](self-service-call-settings.md)** -- User-level `/people/me/` endpoints for self-service call settings, including 6 user-only settings with no admin path.
