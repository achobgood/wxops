# Additional Call Features Reference

## Sources

- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Call Features APIs

Comprehensive reference for Webex Calling Paging Groups, Call Park, Call Park Extensions, Call Pickup, Voicemail Groups, Customer Assist (formerly CX Essentials), Operating Modes, Call Recording, Announcements/Playlists, Single Number Reach, and Virtual Extensions. Each section includes both API signatures and Raw HTTP examples.

---

## Table of Contents

1. [Required Scopes](#required-scopes)
2. [Paging Groups](#paging-groups)
3. [Call Park](#call-park)
4. [Call Park Extensions](#call-park-extensions)
5. [Call Pickup](#call-pickup)
6. [Voicemail Groups](#voicemail-groups)
7. [Customer Assist (CX Essentials)](#customer-assist-cx-essentials)
8. [Operating Modes](#operating-modes)
9. [Call Recording (Org-Level)](#call-recording-org-level)
10. [Announcements & Playlists](#announcements--playlists)
11. [Single Number Reach](#single-number-reach)
12. [Virtual Extensions](#virtual-extensions)
13. [Data Models Quick Reference](#data-models-quick-reference)
14. [Dependencies & Relationships](#dependencies--relationships)

---

## Required Scopes

| Operation | Scope |
|-----------|-------|
| Read paging groups, call parks, call pickups, call park extensions, voicemail groups | `spark-admin:telephony_config_read` |
| Create/update/delete paging groups, call parks, call pickups, call park extensions, voicemail groups | `spark-admin:telephony_config_write` |
| Read Customer Assist queue recording | `spark-admin:people_read` |
| Configure Customer Assist queue recording | `spark-admin:people_write` |
| Read Customer Assist wrap-up reasons, screen pop, available agents | `spark-admin:telephony_config_read` |
| Modify Customer Assist wrap-up reasons, screen pop | `spark-admin:telephony_config_write` |

All APIs accept an optional `org_id` parameter, allowing partner administrators to operate on a customer organization.

---

## Paging Groups

### Overview

Group Paging allows a person to place a **one-way call or group page** to up to **75 people and/or workspaces** by dialing a number or extension assigned to a specific paging group. The paging service makes a simultaneous call to all assigned targets.

Use cases: overhead announcements, warehouse pages, emergency notifications to a group of phones.

### Key Data Models

#### `Paging`

| Field | Type | Required for Create | Notes |
|-------|------|-------------------|-------|
| `paging_id` | `str` (alias: `id`) | -- | Read-only, set by API |
| `enabled` | `bool` | No | Default varies |
| `name` | `str` | **Yes** | Max 30 chars |
| `phone_number` | `str` | **One of phone_number/extension** | Max 23 chars |
| `extension` | `str` | **One of phone_number/extension** | 2-10 chars |
| `toll_free_number` | `bool` | -- | Read-only |
| `language` | `str` | No | Read-only (use `language_code` for write) |
| `language_code` | `str` | No | e.g., `en_us` |
| `originator_caller_id_enabled` | `bool` | **Yes, if originators set** | Shows page originator ID on target caller ID |
| `originators` | `list[PagingAgent]` | No | People/workspaces who can originate pages |
| `targets` | `list[PagingAgent]` | No | People/workspaces/virtual lines who receive pages |
| `first_name` / `last_name` | `str` | No | **Deprecated** -- use `direct_line_caller_id_name` and `dial_by_name` |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | No | Replacement for first/last name |
| `dial_by_name` | `str` | No | Name used for dial-by-name directory |

#### `PagingAgent`

| Field | Type | Notes |
|-------|------|-------|
| `agent_id` (alias: `id`) | `str` | **Only field sent in create/update** |
| `first_name` | `str` | Read-only (returned from details) |
| `last_name` | `str` | Read-only |
| `agent_type` (alias: `type`) | `UserType` | `PEOPLE` or `PLACE` |
| `phone_number` | `str` | Read-only |
| `extension` | `str` | Read-only |
| `routing_prefix` | `str` | Read-only |
| `esn` | `str` | Read-only (routing prefix + extension) |

**Important**: When creating or updating, `originators` and `targets` are serialized as flat lists of IDs only, not full agent objects.

### Phone Number / Extension Assignment

- Either `phone_number` or `extension` is mandatory on create.
- Use the Get Available Phone Numbers endpoint (see Raw HTTP) to find unassigned numbers at a location.
- The `toll_free_number` flag is read-only and reflects whether the assigned number is toll-free.

### Member Management

- **Originators**: People/workspaces who can initiate a page. Set via `originators` field as a list of `PagingAgent` with `agent_id` populated.
- **Targets**: People/workspaces/virtual lines who receive the page broadcast. Set via `targets` field. Up to 75 targets.
- On create/update, pass agent IDs only. On read (details), full agent info is returned.

### Raw HTTP

<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List Paging Groups** (org-wide, filterable by location):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/paging",
    params={"locationId": loc_id, "name": "Warehouse", "max": 1000})
items = result["paging"]  # response key: "paging"
# Each item: {id, name, extension, phoneNumber, enabled, locationId, locationName, routingPrefix, esn, tollFreeNumber}
```

**Get Paging Group Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/paging/{paging_id}")
# Returns full object including originators[], targets[] with firstName, lastName, type, phoneNumber, extension
```

**Create Paging Group** -- required: `name`, one of `phoneNumber`/`extension`:

```python
body = {
    "name": "Warehouse Page",
    "extension": "8100",
    "languageCode": "en_us",
    "originatorCallerIdEnabled": True,  # required if originators are set
    "originators": [person_id],  # Plain string array, NOT [{"id": person_id}]
    "targets": [person_id, workspace_id]  # Plain string array, NOT [{"id": ...}]
}
# IMPORTANT: targets and originators are arrays of ID strings, not objects.
# [{"id": ...}] returns 400 "Invalid field value". Verified via stress test 2026-03-25.
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/paging", json=body)
paging_id = result["id"]
```

**Update Paging Group:**

```python
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/paging/{paging_id}",
    json={"name": "Updated Name", "enabled": True})
```

**Delete Paging Group:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/paging/{paging_id}")
```

**Get Available Phone Numbers:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/paging/availableNumbers",
    params={"max": 1000})
items = result["availableNumbers"]
```

### CLI Examples

```bash
# List all paging groups (org-wide)
wxcli paging-group list

# List paging groups filtered by location
wxcli paging-group list --location-id <loc_id>

# Get details for a specific paging group
wxcli paging-group show <loc_id> <pg_id>

# Create a paging group
wxcli paging-group create <loc_id> --name "Warehouse Page" --extension "8100"

# Update a paging group
wxcli paging-group update <loc_id> <pg_id> --name "Updated Page"

# Delete a paging group
wxcli paging-group delete <loc_id> <pg_id>

# List available phone numbers for paging group assignment
wxcli paging-group list-available-numbers <loc_id>
```

---

## Call Park

### Overview

Call Park allows a call recipient to place a call **on hold at a designated park location** so it can be retrieved from another device. Users park calls against extensions or Call Park Extensions, then other users retrieve them by dialing the park extension.

Use cases: front-desk parks a call, employee picks it up from their desk phone; warehouse environments where users move between stations.

### Key Data Models

#### `CallPark`

| Field | Type | Notes |
|-------|------|-------|
| `callpark_id` (alias: `id`) | `str` | Read-only. **Changes when name is modified.** |
| `name` | `str` | Max 80 chars |
| `location_name` | `str` | Read-only |
| `location_id` | `str` | Read-only |
| `recall` | `RecallHuntGroup` | Recall options (who gets alerted when park times out) |
| `agents` | `list[PersonPlaceAgent]` | People/workspaces eligible to receive parked calls |
| `park_on_agents_enabled` | `bool` | Whether calls can be parked on agents as a destination |
| `call_park_extensions` | `list[CallParkExtension]` | Park extensions assigned to this call park |

**Important**: On create/update, `agents` and `call_park_extensions` are serialized as flat lists of IDs only.

#### `RecallHuntGroup`

| Field | Type | Notes |
|-------|------|-------|
| `hunt_group_id` | `str` | Hunt group ID for recall alternate destination |
| `hunt_group_name` | `str` | Read-only (excluded from create/update) |
| `option` | `CallParkRecall` | Recall behavior enum |

#### `CallParkRecall` (Enum)

| Value | Constant | Description |
|-------|----------|-------------|
| `ALERT_PARKING_USER_ONLY` | `parking_user_only` | Alert only the user who parked the call |
| `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP` | `parking_user_first_then_hunt_group` | Alert parking user first, then hunt group |
| `ALERT_HUNT_GROUP_ONLY` | `hunt_group_only` | Alert hunt group only |

#### `CallParkSettings` (Location-Level)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `ring_pattern` | `RingPattern` | `normal` | Ring pattern when park extension is called |
| `recall_time` | `int` | `45` | Seconds before recall (30-600 range) |
| `hunt_wait_time` | `int` | `45` | Seconds before reverting to hunt group (30-600 range) |

#### `LocationCallParkSettings`

Location-level call park configuration combines the recall setting (`call_park_recall`) and park settings (`call_park_settings`).

### Phone Number / Extension Assignment

Call Parks themselves do not have phone numbers or extensions directly. They are groups of agents and park extensions. Calls are parked **to** a Call Park Extension (see next section) or to an agent's extension.

### Member Management

- **Agents**: People and workspaces eligible to receive parked calls. Added via the `agents` field (list of IDs on create/update).
- **Call Park Extensions**: Dedicated extensions for parking. Added via `call_park_extensions` field (list of IDs on create/update).
- Use the Get Available Agents endpoint (see Raw HTTP) to discover eligible agents at a location.
- Use the Get Available Recall Hunt Groups endpoint (see Raw HTTP) to discover hunt groups eligible as recall destinations.

### Raw HTTP

<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List Call Parks** (location-scoped):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callParks",
    params={"name": "Lobby", "order": "ASC", "max": 1000})
items = result["callParks"]  # response key: "callParks"
# Each item: {id, name}
```

**Get Call Park Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callParks/{park_id}")
# Returns: name, recall, agents[], callParkExtensions[], parkOnAgentsEnabled
```

**Create Call Park** -- required: `name`, `recall` with `option`:

```python
body = {
    "name": "Lobby Park",
    "recall": {"option": "ALERT_PARKING_USER_ONLY"},  # required
    "parkOnAgentsEnabled": True,
    "agents": [{"id": person_id}],
    "callParkExtensions": [{"id": cpe_id}]
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/callParks", json=body)
park_id = result["id"]
```

**Update Call Park** (ID changes when name changes):

```python
result = api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/callParks/{park_id}",
    json={"name": "New Name", "parkOnAgentsEnabled": False})
# New park_id returned if name changed
```

**Delete Call Park:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/callParks/{park_id}")
```

**Get Available Agents:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callParks/availableUsers",
    params={"name": "John", "max": 1000})
items = result["availableUsers"]  # response key: "availableUsers"
```

**Get Available Recall Hunt Groups:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callParks/availableRecallHuntGroups",
    params={"max": 1000})
items = result["availableRecallHuntGroups"]
```

**Get Location Call Park Settings:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callParks/settings")
# Returns: callParkRecall, callParkSettings (ringPattern, recallTime, huntWaitTime)
```

**Update Location Call Park Settings:**

```python
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/callParks/settings",
    json={"callParkSettings": {"recallTime": 60, "huntWaitTime": 60}})
```

### CLI Examples

```bash
# List call parks at a location
wxcli call-park list <loc_id>

# Get details for a call park
wxcli call-park show <loc_id> <park_id>

# Create a call park
wxcli call-park create <loc_id> --name "Lobby Park" --json-body '{"recall": {"option": "ALERT_PARKING_USER_ONLY"}}'

# Update a call park
wxcli call-park update <loc_id> <park_id> --name "New Park Name"

# Delete a call park
wxcli call-park delete <loc_id> <park_id>

# List available agents for call park
wxcli call-park list-available-users <loc_id>

# List available recall hunt groups
wxcli call-park list-available-recall-hunt-groups <loc_id>

# Get location-level call park settings
wxcli call-park show-settings <loc_id>

# Update location-level call park settings
wxcli call-park update-settings <loc_id> --json-body '{"callParkSettings": {"recallTime": 60}}'
```

---

## Call Park Extensions

### Overview

Call Park Extensions are **dedicated extensions defined within the Call Park service** for holding parked calls. A user parks a call to one of these extensions, and another user retrieves it by dialing that extension. Call Park Extensions can also be added as **monitored lines** on Cisco phones, so users can park and retrieve calls by pressing a line key.

The Call Park service is enabled for all users by default.

### Key Data Models

#### `CallParkExtension`

| Field | Type | Notes |
|-------|------|-------|
| `cpe_id` (alias: `id`) | `str` | Unique identifier |
| `name` | `str` | Max 30 chars |
| `extension` | `str` | 2-10 chars, must be unique within location |

This is a lightweight model -- just a name and extension. The `CallParkExtension` model is also used within the `CallPark` model to list assigned park extensions.

### Phone Number / Extension Assignment

- Each Call Park Extension has a **unique extension** within its location.
- No phone number assignment -- these are extension-only entities.
- Extensions are dialed internally to park or retrieve calls.

### Member Management

Call Park Extensions do not have members. They are simple extension holders assigned to Call Park groups (see the `call_park_extensions` field on `CallPark`).

### Raw HTTP

<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List Call Park Extensions** (org-wide, filterable by location):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/callParkExtensions",
    params={"locationId": loc_id, "name": "Park", "max": 1000})
items = result["callParkExtensions"]  # response key: "callParkExtensions"
# Each item: {id, name, extension, locationId, locationName}
```

**Get Call Park Extension Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callParkExtensions/{cpe_id}")
# Returns: name, extension
```

**Create Call Park Extension** -- required: `name`, `extension`:

```python
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/callParkExtensions",
    json={"name": "Park Slot 1", "extension": "7001"})
cpe_id = result["id"]
```

**Update Call Park Extension:**

```python
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/callParkExtensions/{cpe_id}",
    json={"name": "Park Slot A", "extension": "7002"})
```

**Delete Call Park Extension:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/callParkExtensions/{cpe_id}")
```

### CLI Examples

```bash
# List call park extensions
wxcli call-park list-call-park-extensions --location-id <loc_id>

# Get details for a call park extension
wxcli call-park show-call-park-extensions <loc_id> <cpe_id>

# Create a call park extension
wxcli call-park create-call-park-extensions <loc_id> --name "Park Slot 1" --extension "7001"

# Update a call park extension
wxcli call-park update-call-park-extensions <loc_id> <cpe_id> --name "Park Slot A"

# Delete a call park extension
wxcli call-park delete-call-park-extensions <loc_id> <cpe_id>
```

---

## Call Pickup

### Overview

Call Pickup enables a user (agent) to **answer any ringing line within their pickup group**. When a call rings unanswered for a configurable period, all members of the pickup group can be notified via audio, visual, or both.

Use cases: small offices where team members cover each other's calls; receptionist groups.

### Key Data Models

#### `CallPickup`

| Field | Type | Notes |
|-------|------|-------|
| `pickup_id` (alias: `id`) | `str` | Read-only. **Changes when name is modified.** |
| `name` | `str` | Max 80 chars |
| `location_name` | `str` | Read-only |
| `location_id` | `str` | Read-only |
| `notification_type` | `PickupNotificationType` | How members are notified of unanswered calls |
| `notification_delay_timer_seconds` | `int` | Seconds before notification fires |
| `agents` | `list[PersonPlaceAgent]` | People, workspaces, virtual lines in the group |

**Important**: On create/update, `agents` is serialized as a flat list of IDs only.

#### `PickupNotificationType` (Enum)

| Value | Constant | Description |
|-------|----------|-------------|
| `NONE` | `none` | No notification sent |
| `AUDIO_ONLY` | `audio_only` | Audio notification after delay |
| `VISUAL_ONLY` | `visual_only` | Visual notification after delay |
| `AUDIO_AND_VISUAL` | `audio_and_visual` | Both audio and visual after delay |

### Phone Number / Extension Assignment

Call Pickup groups do not have their own phone numbers or extensions. They are groupings of agents -- members pick up ringing calls within the group using the feature access code `*98`.

### Member Management

- **Agents**: People, workspaces, and virtual lines. Set via the `agents` field (list of IDs on create/update).
- Use the Get Available Agents endpoint (see Raw HTTP) to discover eligible agents at a location that are not yet assigned to another pickup group. The API excludes already-assigned agents from the results.
- A user can only belong to **one** call pickup group at a time. Attempting to add an already-assigned user returns error 4471: "User ... is already assigned to pickup group ...".

### Raw HTTP

<!-- Updated by playbook session 2026-03-18 -->

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List Call Pickups** (location-scoped):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callPickups",
    params={"name": "Sales", "order": "ASC", "max": 1000})
items = result["callPickups"]  # response key: "callPickups"
# Each item: {id, name}
```

**Get Call Pickup Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callPickups/{pickup_id}")
# Returns: name, notificationType, notificationDelayTimerSeconds, agents[]
```

**Create Call Pickup** -- required: `name`:

```python
body = {
    "name": "Sales Pickup",
    "notificationType": "AUDIO_AND_VISUAL",
    "notificationDelayTimerSeconds": 6,
    "agents": [person_id]  # Plain string array, NOT [{"id": person_id}]
}
# IMPORTANT: agents is an array of ID strings, not objects. [{"id": ...}] returns 400.
# Verified via stress test 2026-03-25.
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/callPickups", json=body)
pickup_id = result["id"]
```

**Update Call Pickup** (ID changes when name changes):

```python
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/callPickups/{pickup_id}",
    json={"name": "New Name", "notificationType": "NONE"})
```

**Delete Call Pickup:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/callPickups/{pickup_id}")
```

**Get Available Agents:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callPickups/availableUsers",
    params={"name": "Jane", "max": 1000})
items = result["availableUsers"]  # response key: "availableUsers"
```

### CLI Examples

```bash
# List call pickups at a location
wxcli call-pickup list <loc_id>

# Get details for a call pickup group
wxcli call-pickup show <loc_id> <pickup_id>

# Create a call pickup group
wxcli call-pickup create <loc_id> --name "Sales Pickup"

# Update a call pickup group
wxcli call-pickup update <loc_id> <pickup_id> --name "New Name"

# Delete a call pickup group
wxcli call-pickup delete <loc_id> <pickup_id>

# List available agents for call pickup
wxcli call-pickup list-available-users <loc_id>
```

---

## Voicemail Groups

### Overview

Voicemail Groups provide a **shared voicemail box** (and optional inbound fax box) that can be assigned to users or call routing features like auto attendants, call queues, or hunt groups. They are useful for team-level voicemail where multiple people need access to the same messages.

### Key Data Models

#### `VoicemailGroup` (List Model)

| Field | Type | Notes |
|-------|------|-------|
| `group_id` (alias: `id`) | `str` | Unique identifier |
| `name` | `str` | Group name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `extension` | `str` | Extension number |
| `phone_number` | `str` | Phone number |
| `routing_prefix` | `str` | Location routing prefix |
| `esn` | `str` | Routing prefix + extension |
| `enabled` | `bool` | Whether incoming calls are sent to voicemail |
| `toll_free_number` | `bool` | Read-only |

#### `VoicemailGroupDetail` (Detail/Create/Update Model)

| Field | Type | Required for Create | Notes |
|-------|------|-------------------|-------|
| `group_id` (alias: `id`) | `str` | -- | Read-only |
| `name` | `str` | **Yes** | Group name |
| `phone_number` | `str` | No | Voicemail group phone number |
| `extension` | `str` | **Yes** | Extension number |
| `first_name` | `str` | **Yes** | **Deprecated** -- use `direct_line_caller_id_name` |
| `last_name` | `str` | **Yes** | **Deprecated** -- use `direct_line_caller_id_name` |
| `passcode` | `int` | **Yes** | Access passcode |
| `enabled` | `bool` | No | For update only |
| `language_code` | `str` | No | Default `en_us` in factory |
| `greeting` | `Greeting` | No | Greeting type enum |
| `greeting_uploaded` | `bool` | -- | Read-only; `True` if custom greeting uploaded |
| `greeting_description` | `str` | No | Description for custom greeting |
| `message_storage` | `VoicemailMessageStorage` | **Yes** (set by factory) | Storage type config |
| `notifications` | `VoicemailNotifications` | **Yes** (set by factory) | Notification settings |
| `fax_message` | `VoicemailFax` | **Yes** (set by factory) | Fax receive settings |
| `transfer_to_number` | `VoicemailTransferToNumber` | **Yes** (set by factory) | Transfer settings |
| `email_copy_of_message` | `VoicemailCopyOfMessage` | **Yes** (set by factory) | Email copy settings |
| `voice_message_forwarding_enabled` | `bool` | No | Enable/disable voice message forwarding |
| `time_zone` | `str` | No | Undocumented field -- present in API response but absent from OpenAPI spec `GetLocationVoicemailGroupObject` schema.  |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | No | Replaces deprecated first/last name |
| `dial_by_name` | `str` | No | Name for dial-by-name directory |

#### `VoicemailMessageStorage`

| Field | Type | Notes |
|-------|------|-------|
| `storage_type` | `StorageType` | `INTERNAL` (Webex-hosted) or `EXTERNAL` (external server) |
| `external_email` | `str` | Email address for external storage delivery |

#### `VoicemailNotifications`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Whether notifications are sent |
| `destination` | `str` | Email address or phone number for notifications |

#### `VoicemailFax`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Whether fax reception is enabled |
| `phone_number` | `str` | Dedicated fax phone number |

#### `VoicemailTransferToNumber`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Whether transfer-to-number is enabled |
| `destination` | `str` | Number to transfer to when the caller presses 0 |

#### `VoicemailCopyOfMessage`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Whether email copies of voicemail are sent |
| `email_id` | `str` | Email address to receive message copies |

If not explicitly provided on create, these fields default to:
- `message_storage`: `StorageType.internal`
- `notifications`: disabled
- `fax_message`: disabled
- `transfer_to_number`: disabled
- `email_copy_of_message`: disabled

### Phone Number / Extension Assignment

- `extension` is **required** on create.
- `phone_number` is optional.
- Use the Get Available Phone Numbers and Get Fax Message Available Phone Numbers endpoints (see Raw HTTP) to find unassigned numbers at a location.

### Member Management

Voicemail Groups do not have explicit member lists. They are shared voicemail boxes that are **assigned to** other features (auto attendants, call queues, hunt groups) or users through those features' overflow/no-answer settings.

### Raw HTTP

<!-- Updated by playbook session 2026-03-18 -->

The Voicemail Groups API base is `telephony/config/voicemailGroups`. The underlying API URLs are:

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List Voicemail Groups** (org-wide):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/voicemailGroups",
    params={"locationId": loc_id, "name": "Support", "max": 1000})
items = result["voicemailGroups"]  # response key: "voicemailGroups"
# Each item: {id, name, locationName, locationId, extension, phoneNumber, routingPrefix, esn, enabled, tollFreeNumber}
```

**Get Voicemail Group Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/{vg_id}")
# Returns: name, extension, passcode, languageCode, messageStorage, notifications, faxMessage, etc.
```

**Create Voicemail Group** -- requires 7+ fields (name, extension, passcode, languageCode, messageStorage, notifications, faxMessage, transferToNumber, emailCopyOfMessage):

```python
body = {
    "name": "Support VM",
    "extension": "8200",
    "passcode": "740384",         # 6+ digits, no sequential/repeating patterns
    "languageCode": "en_us",
    "messageStorage": {"storageType": "INTERNAL"},
    "notifications": {"enabled": False},
    "faxMessage": {"enabled": False},
    "transferToNumber": {"enabled": False},
    "emailCopyOfMessage": {"enabled": False}
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups", json=body)
vg_id = result["id"]
```

**Gotcha**: The create body must use camelCase keys. Send them explicitly, as the example above does -- or pass `--json-body` via the CLI.

**Update Voicemail Group:**

```python
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/{vg_id}",
    json={"name": "New Name", "enabled": True})
```

**Delete Voicemail Group:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/{vg_id}")
```

**Get Available Phone Numbers:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/availablePhoneNumbers",
    params={"max": 1000})
items = result["phoneNumbers"]
```

**Get Fax Message Available Phone Numbers:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/faxMessage/availablePhoneNumbers",
    params={"max": 1000})
items = result["phoneNumbers"]
```

### CLI Examples

Voicemail Group commands are under the `location-voicemail` command group.

```bash
# List voicemail groups (org-wide or filtered by location)
wxcli location-voicemail list --location-id <loc_id>

# Get details for a voicemail group
wxcli location-voicemail show-voicemail-groups <loc_id> <vg_id>

# Create a voicemail group
wxcli location-voicemail create <loc_id> --name "Support VM" --extension "8200" \
  --json-body '{"passcode": "740384", "languageCode": "en_us", "messageStorage": {"storageType": "INTERNAL"}, "notifications": {"enabled": false}, "faxMessage": {"enabled": false}, "transferToNumber": {"enabled": false}, "emailCopyOfMessage": {"enabled": false}}'

# Update a voicemail group
wxcli location-voicemail update-voicemail-groups <loc_id> <vg_id> \
  --name "New Name"

# Delete a voicemail group
wxcli location-voicemail delete <loc_id> <vg_id>

# List available phone numbers for voicemail group assignment
wxcli location-voicemail list-available-numbers-voicemail-groups <loc_id>

# List available phone numbers for fax message
wxcli location-voicemail list-available-numbers-fax-message <loc_id>
```

---

## Customer Assist (CX Essentials)

> **Not to be confused with Webex Contact Center (WxCC).** Customer Assist (formerly CX Essentials) is a Webex Calling add-on for basic queue supervision and agent experience. Webex Contact Center is a separate product with its own developer portal at `developer.webex-cx.com`, separate APIs, and separate licensing. This playbook covers Customer Assist only.

### Overview

Webex **Customer Assist** (formerly Customer Experience Essentials / CX Essentials) provides enhanced queue capabilities beyond the Customer Experience Basic suite. It adds features such as:

- **Screen Pop**: Pop a URL (CRM, ticketing system) when an agent receives a queued call
- **Queue Call Recording**: Hosted call recording for quality assurance, compliance, and training
- **Wrap-Up Reasons**: Post-call categorization codes that agents select after ending a call
- **Customer Assist Agent Licensing**: Ability to query agents with Customer Assist licenses

These APIs are distinct from Customer Experience Basic and require Customer Assist licensing.

### Screen Pop Configuration

Screen pop lets agents view customer-related info in a pop-up window when receiving a call from a queue.

#### `ScreenPopConfiguration` Model

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Enable/disable screen pop |
| `screen_pop_url` | `str` | URL to pop (CRM, ticketing, etc.) |
| `desktop_label` | `str` | Label for the screen pop config |
| `query_params` | `dict[str, Any]` | Query parameters appended to the screen pop URL |

### Available Agents

- `has_cx_essentials=True`: Returns only agents with Customer Assist (formerly CX Essentials) license.
- `has_cx_essentials=False`: Returns only agents with CX Basic license.
- Omit for all agents.

### Queue Call Recording

Hosted call recording for queues. Records calls placed and received on the platform for replay and archival.

**Note**: A person with a Webex Calling Standard license is eligible for call recording only when the recording vendor is Webex.

#### Raw HTTP

```
GET  /v1/telephony/config/locations/{locationId}/queues/{queueId}/cxEssentials/callRecordings
PUT  /v1/telephony/config/locations/{locationId}/queues/{queueId}/cxEssentials/callRecordings
```

GET response / PUT body fields: `enabled` (bool), `record` (str: Always/Never/OnDemand), `notification` (object: `{enabled, type}`), `repeat` (object: `{enabled, interval}`), `startStopAnnouncement` (object: `{internalCallsEnabled, pstnCallsEnabled}`), `serviceProvider` (str), `externalGroup` (str), `externalIdentifier` (str).

Scope: `spark-admin:people_read` (GET), `spark-admin:people_write` (PUT).

### Wrap-Up Reasons

Wrap-up reasons let agents categorize the outcome of a call after it ends. Admins configure reasons and assign them to queues. A configurable timer (default 60 seconds) dictates how long agents have to select a reason post-call.

#### Update Wrap-Up Reason

Queue assignment is **incremental** -- you can assign and unassign specific queues without replacing the full list.

#### Update Queue Wrap-Up Settings

- `default_wrapup_reason_id`: Set as `''` (empty string) to clear the default.

### Customer Assist Data Models

#### `WrapUpReason` (List Model)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Reason name |
| `description` | `str` | Reason description |
| `number_of_queues_assigned` | `int` | Count of assigned queues |

#### `WrapUpReasonDetails` (Detail Model)

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Reason name |
| `description` | `str` | Reason description |
| `default_wrapup_queues_count` | `int` | Number of queues where this is the default |
| `queues` | `list[WrapupReasonQueue]` | Assigned queues with full details |

#### `WrapupReasonQueue`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Queue ID |
| `name` | `str` | Queue name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `phone_number` | `str` | Queue phone number |
| `extension` | `int` | Queue extension |
| `default_wrapup_enabled` | `bool` | Whether this reason is the default for the queue |

#### `QueueWrapupReasonSettings`

| Field | Type | Notes |
|-------|------|-------|
| `wrapup_timer_enabled` | `bool` | Whether the wrap-up timer is active |
| `wrapup_timer` | `int` | Timer value in seconds |
| `wrapup_reasons` | `list[QueueSettingsReason]` | Reasons assigned to this queue |

#### `QueueSettingsReason`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Wrap-up reason ID |
| `name` | `str` | Reason name |
| `description` | `str` | Reason description |
| `default_enabled` | `bool` | Whether this reason is the default for the queue |

#### `AvailableQueue`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Queue ID |
| `name` | `str` | Queue name |
| `location_name` | `str` | Location name |
| `location_id` | `str` | Location ID |
| `phone_number` | `str` | Queue phone number |
| `extension` | `int` | Queue extension |

### Raw HTTP (Customer Assist)

<!-- Updated by playbook session 2026-03-18 -->

Customer Assist (formerly CX Essentials) APIs operate on call queues. The base URL pattern is `telephony/config/cxEssentials/...` or queue-scoped paths.

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**Note**: Customer Assist operations require Customer Assist licensing. Screen pop, queue recording, and wrap-up reasons are all per-queue settings -- call queues must exist first.

### CLI Examples

```bash
# List all wrap-up reasons (org-level)
wxcli cx-essentials list

# Get details for a wrap-up reason
wxcli cx-essentials show REASON_ID -o json

# Create a wrap-up reason
wxcli cx-essentials create --name "Customer Inquiry"

# Update a wrap-up reason
wxcli cx-essentials update REASON_ID --name "Updated Reason"

# Delete a wrap-up reason
wxcli cx-essentials delete REASON_ID --force

# Validate a wrap-up reason name
wxcli cx-essentials validate-wrap-up --name "New Reason Name"

# List available queues for a wrap-up reason
wxcli cx-essentials list-available-queues REASON_ID

# Get wrap-up reason settings for a queue
wxcli cx-essentials list-settings LOCATION_ID QUEUE_ID -o json

# Update wrap-up reason settings for a queue
wxcli cx-essentials update-settings LOCATION_ID QUEUE_ID \
  --json-body '{"wrapupTimerEnabled": true, "wrapupTimer": 60}'

# Get screen pop configuration for a queue
wxcli cx-essentials show-screen-pop LOCATION_ID QUEUE_ID -o json

# Update screen pop configuration for a queue
wxcli cx-essentials update-screen-pop LOCATION_ID QUEUE_ID \
  --json-body '{"enabled": true, "screenPopUrl": "https://crm.example.com/pop"}'

# List available agents (optionally filter by Customer Assist license)
wxcli cx-essentials list-available-agents LOCATION_ID

# Get queue call recording settings
wxcli cx-essentials show-call-recordings LOCATION_ID QUEUE_ID -o json

# Update queue call recording settings (simple: enable + record mode)
wxcli cx-essentials update-call-recordings LOCATION_ID QUEUE_ID \
  --enabled --record Always

# Update nested recording settings (notification / repeat / announcement) via --json-body
wxcli cx-essentials update-call-recordings LOCATION_ID QUEUE_ID --json-body '{
  "enabled": true,
  "record": "Always",
  "notification": {"type": "Beep", "enabled": true},
  "repeat": {"interval": 30, "enabled": true},
  "startStopAnnouncement": {"internalCallsEnabled": true, "pstnCallsEnabled": true}
}'

# --- Queue Discovery & Creation ---

# List Customer Assist queues (hidden from default call-queue list!)
wxcli call-queue list --has-cx-essentials true -o json

# Create a Customer Assist queue (requires callPolicies via --json-body)
wxcli call-queue create LOCATION_ID --name "Queue Name" --has-cx-essentials true \
  --json-body '{"name":"Queue Name","extension":"XXXX","callPolicies":{"policy":"SIMULTANEOUS"}}'

# --- Supervisor Cleanup ---

# To remove a supervisor, remove all agents via update (not delete endpoint)
wxcli call-queue update-supervisors SUPERVISOR_ID --has-cx-essentials true \
  --json-body '{"agents":[{"id":"AGENT_ID","action":"DELETE"}]}'
# When last agent is removed, supervisor is auto-deleted
```

> **GOTCHA:** Customer Assist queues do not appear in the default `wxcli call-queue list` output. You must pass `--has-cx-essentials true` to see them. Using CX Essentials endpoints on a regular queue returns error 28018 ("CX Essentials is not enabled for this Call center"). The CLI detects this error and prints a tip.

> **GOTCHA:** Creating a Customer Assist queue requires `callPolicies` in the request body via `--json-body`. Omitting `callPolicies` results in a 400 error. Minimum: `{"callPolicies":{"policy":"SIMULTANEOUS"}}`.

> **GOTCHA:** `delete-supervisors-config-1` returns 204 but the supervisor persists. Use `update-supervisors` with `action: DELETE` on each agent instead — removing the last agent auto-removes the supervisor.

### Queue Call Recording — data model

Queue recording lives **only** at `telephony/config/locations/{locationId}/queues/{queueId}/cxEssentials/callRecordings`. It is **not** part of the call queue object: `wxcli call-queue show ... --has-cx-essentials true` returns zero recording-related keys, so `call-queue update --json-body` can never read or write these settings.

Cisco's published OpenAPI spec omits this path (it has never appeared in any revision), so the CLI commands are generated from an additive local spec overlay that re-supplies the missing endpoint after every upstream spec refresh. The endpoint is live and verified, but **unpublished** — Cisco makes no compatibility promise for it, so treat a sudden 404 here as the likely cause. Every field below was proven against the live API on 2026-07-14 by PUT-then-GET read-back.

| Field | Type | Writable | Notes |
|-------|------|:--------:|-------|
| `enabled` | `bool` | yes | Master switch for queue recording. |
| `record` | `str` | yes | When to record. **Only `Always` is live-verified.** Other values are not documented here because they have not been tested. |
| `notification.type` | `str` | yes | Live-verified: `None`, `Beep`. |
| `notification.enabled` | `bool` | yes | |
| `repeat.interval` | `int` | yes | Seconds between notification repeats. Live-verified: `15` (default), `30`. |
| `repeat.enabled` | `bool` | yes | |
| `startStopAnnouncement.internalCallsEnabled` | `bool` | yes | |
| `startStopAnnouncement.pstnCallsEnabled` | `bool` | yes | |
| `serviceProvider` | `str` | no | Read-only. Recording vendor service provider ID (BroadWorks-backed). |
| `externalGroup` | `str` | no | Read-only. |
| `externalIdentifier` | `str` | no | Read-only. |
| `postCallRecordingSettings` | `object` | untested | Only returned once `enabled` is true. Writability not verified — do not assume. |
| `announcements` | `object` | untested | Only returned once `enabled` is true. Writability not verified — do not assume. |

> **GOTCHA:** This endpoint returns **204 for unknown fields and silently discards them**. A PUT of `{"bogusFieldXyz": "nonsense"}` returns 204 exactly like a valid write. A 2xx is therefore *not* evidence a setting applied — always read back with `show-call-recordings` to confirm.

> **GOTCHA:** The PUT is a **partial merge, not a replace**. Fields omitted from the body keep their previous value (verified: `record` stayed `Always` across a PUT that omitted it). You do not need to resend the whole object to change one field.

> **GOTCHA:** The response schema is **conditional on `enabled`**. When recording is off, `record`, `postCallRecordingSettings`, and `announcements` are absent entirely. Do not treat their absence as "unsupported".

> **GOTCHA:** Queue recording uses `spark-admin:people_read` / `spark-admin:people_write` — *different* scopes from every other Customer Assist endpoint (which use `spark-admin:telephony_config_*`). A token that works for screen pop can still 403 here.

> **HISTORY — this section was true when written, and a regen made it false.** Until 2026-07-14 it documented `show-queue-recording` / `update-queue-recording`. Those commands were **real**: hand-written on 2026-03-21 by an author who had correctly diagnosed that the endpoint is live but absent from the OpenAPI spec. They lived **two days**. On 2026-03-23 a routine regeneration ("regenerate all commands with orgId auto-injection") rewrote the module they lived in and silently deleted them — an 85-line deletion inside a 668-endpoint commit. They were never in a released version (the first tag postdates the regen), so no user ever had them; but the docs, accurate on the 21st, were quietly false from the 23rd onward.
>
> **The lesson is about mechanism, not diligence.** The March fix was right in its analysis and wrong in its placement: it put hand-written code inside a file the generator *owns*, so the next regen ate it. That is precisely why hand-written command modules must live in their own file and mount via `register(app)`. The current commands avoid the failure entirely by fixing the layer that was actually broken — the endpoint is supplied to the generator as an additive spec overlay, so a regen now *recreates* these commands instead of destroying them.
>
> Nothing caught the four-month gap because `docs/reference/**` was outside the drift gate's scan scope, even though CLAUDE.md's Mandatory Grounding Rule forces every agent to read these docs. Now fixed: the gate scans `docs/reference/**` and runs on every push and pull request, so a command named here that does not exist fails the build.

---

## Operating Modes

<!-- Updated by playbook session 2026-03-18 -->

> **Not supported for Webex for Government (FedRAMP).** See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

### Overview

Operating Modes define time-of-day schedules (business hours, after hours, holidays) that control call routing behavior for features like auto attendants and call queues. They can be defined at the organization level and assigned to locations.

Types: `SAME_HOURS_DAILY`, `DIFFERENT_HOURS_DAILY`, `HOLIDAY`.

### Raw HTTP

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**List Operating Modes** (org-wide):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/operatingModes",
    params={"name": "Business", "limitToLocationId": loc_id,
            "limitToOrgLevelEnabled": "true", "order": "ASC", "max": 1000})
items = result["operatingModes"]  # response key: "operatingModes"
# Each item: {id, name}
```

**Get Operating Mode Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/operatingModes/{mode_id}")
# Returns full schedule configuration
```

**Create Operating Mode** -- required: `name`, `type`, `level`:

```python
body = {
    "name": "Business Hours",
    "type": "SAME_HOURS_DAILY",       # SAME_HOURS_DAILY | DIFFERENT_HOURS_DAILY | HOLIDAY
    "level": "ORGANIZATION",           # required: must be ORGANIZATION
    "locationId": loc_id               # optional: scope to a location
}
result = api.session.rest_post(f"{BASE}/telephony/config/operatingModes/", json=body)
mode_id = result["id"]
```

**Update Operating Mode:**

```python
api.session.rest_put(f"{BASE}/telephony/config/operatingModes/{mode_id}",
    json={"name": "Updated Hours"})
```

**Delete Operating Mode:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/operatingModes/{mode_id}")
```

**Create Holiday** (HOLIDAY type only) -- required: `name`, `startDate`, `endDate`, `allDayEnabled`:

```python
body = {
    "name": "Christmas 2026",
    "allDayEnabled": True,
    "startDate": "2026-12-25",   # note: startDate/endDate, not date
    "endDate": "2026-12-25"
}
result = api.session.rest_post(f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays", json=body)
holiday_id = result["id"]
```

**Get / Update / Delete Holiday:**

```python
# Get
result = api.session.rest_get(f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}")

# Update
api.session.rest_put(f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}",
    json={"name": "New Year", "startDate": "2027-01-01", "endDate": "2027-01-01", "allDayEnabled": True})

# Delete
api.session.rest_delete(f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}")
```

**List Available Operating Modes for Location:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/operatingModes/availableOperatingModes",
    params={"max": 1000})
items = result["availableOperatingModes"]
```

**Get Operating Mode Call Forward Available Numbers:**

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/operatingModes/callForwarding/availableNumbers",
    params={"max": 1000})
items = result["availableNumbers"]
```

### CLI Examples

```bash
# List operating modes (org-wide)
wxcli operating-modes list

# List operating modes filtered by location
wxcli operating-modes list --limit-to-location-id <loc_id>

# Get details for an operating mode
wxcli operating-modes show <mode_id>

# Create an operating mode
wxcli operating-modes create --name "Business Hours" --type "SAME_HOURS_DAILY" --level "ORGANIZATION"

# Update an operating mode
wxcli operating-modes update <mode_id> --name "Updated Hours"

# Delete an operating mode
wxcli operating-modes delete <mode_id>

# Create a holiday on a HOLIDAY-type operating mode
wxcli operating-modes create-holidays <mode_id> \
  --name "Christmas 2026" --all-day-enabled --start-date "2026-12-25" --end-date "2026-12-25"

# Get holiday details
wxcli operating-modes show-holidays <mode_id> <holiday_id>

# Update a holiday
wxcli operating-modes update-holidays <mode_id> <holiday_id> \
  --name "New Year" --start-date "2027-01-01" --end-date "2027-01-01"

# Delete a holiday
wxcli operating-modes delete-holidays <mode_id> <holiday_id>

# List available operating modes for a location
wxcli operating-modes list-available-operating-modes <loc_id>

# Get available call forward numbers for operating modes
wxcli operating-modes list-available-numbers <loc_id>
```

### Gotchas

- OM create requires `level=ORGANIZATION` -- other values fail.
- `type` must be one of: `SAME_HOURS_DAILY`, `DIFFERENT_HOURS_DAILY`, `HOLIDAY`.
- `sameHoursDaily` needs actual `DaySchedule` hours configured to take effect.
- Holiday create uses `startDate`/`endDate` fields (not `date`), plus `allDayEnabled`.
- Holidays can only be added to `HOLIDAY` type operating modes.

---

## Call Recording (Org-Level)

<!-- Updated by playbook session 2026-03-18 -->

### Overview

Organization-level call recording settings control global recording behavior. Per-queue recording is managed through Customer Assist (see above). Per-person recording is managed through person call settings.

### Raw HTTP

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**Get Org Call Recording Settings:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording")
# Returns: enabled, record, vendor info, etc.
```

**Update Org Call Recording Settings:**

```python
api.session.rest_put(f"{BASE}/telephony/config/callRecording",
    json={"enabled": True})
```

**Get Call Recording Terms of Service:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording/vendors/{vendor_id}/termsOfService")
```

### CLI Examples

```bash
# Get org-level call recording settings
wxcli call-recording show

# Update org-level call recording settings
wxcli call-recording update --json-body '{"enabled": true}'

# Get call recording terms of service
wxcli call-recording show-terms-of-service <vendor_id>

# Update call recording terms of service
wxcli call-recording update-terms-of-service <vendor_id> --json-body '{"termsOfServiceEnabled": true}'

# Get org-level compliance announcement settings
wxcli call-recording show-compliance-announcement-call-recording

# Update org-level compliance announcement settings
wxcli call-recording update-compliance-announcement-call-recording --json-body '{"enabled": true}'

# Get location-level compliance announcement settings
wxcli call-recording show-compliance-announcement-call-recording-1 <loc_id>

# Update location-level compliance announcement settings
wxcli call-recording update-compliance-announcement-call-recording-1 <loc_id> --json-body '{"enabled": true}'

# List call recording regions
wxcli call-recording list

# List call recording vendors for a location
wxcli call-recording list-vendors <loc_id>

# Get org-level call recording vendors
wxcli call-recording show-vendors

# Set call recording vendor for a location
wxcli call-recording update-vendor-call-recording <loc_id> --json-body '{"vendorId": "<vendor_id>"}'

# List call recording jobs
wxcli call-recording list-call-recording

# Get job status of a call recording job
wxcli call-recording show-call-recording <job_id>
```

---

## Announcements & Playlists

<!-- Updated by playbook session 2026-03-18 -->

### Overview

The Announcement Repository stores binary audio greeting files (WAV, WMA) used by auto attendants, call queues, hunt groups, and other features. Announcements can be managed at the organization level or scoped to a location. Playlists group multiple announcements for sequential playback.

### Raw HTTP

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

#### Announcements

**List Announcements** (org-level, filterable by location):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/announcements",
    params={"locationId": loc_id, "fileName": "greeting", "fileType": "WAV",
            "name": "Welcome", "order": "fileName", "max": 1000})
items = result["announcements"]  # response key: "announcements"
# Each item: {id, name, fileName, fileSize, mediaFileType, level, locationId, locationName}
```

**Get Announcement Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/{ann_id}")
# Org-level announcement
```

**Get Location-Level Announcement Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/announcements/{ann_id}")
```

**Update Announcement** (org-level):

```python
api.session.rest_put(f"{BASE}/telephony/config/announcements/{ann_id}", json={...})
```

**Update Announcement** (location-level):

```python
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/announcements/{ann_id}", json={...})
```

**Delete Announcement** (org-level):

```python
api.session.rest_delete(f"{BASE}/telephony/config/announcements/{ann_id}")
```

**Delete Announcement** (location-level):

```python
api.session.rest_delete(f"{BASE}/telephony/config/locations/{loc_id}/announcements/{ann_id}")
```

**Get Repository Usage** (org-level):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/usage")
items = result["usage"]
```

**Get Repository Usage** (location-level):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/announcements/usage")
items = result["usage"]
```

**Note**: Announcement upload (create) is exposed by the CLI -- use `wxcli announcements create` (org level) or `wxcli announcements create-announcements LOCATION_ID` (location level). Both take `--name`, `--file-uri`, `--file-name`, and `--is-text-to-speech`/`--no-is-text-to-speech`.

#### Playlists

**List Playlists:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/playlists",
    params={"max": 1000})
items = result["playlists"]  # response key: "playlists"
```

**Get Playlist Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}")
```

**Create Playlist:**

```python
result = api.session.rest_post(f"{BASE}/telephony/config/announcements/playlists",
    json={"name": "Hold Music"})
playlist_id = result["id"]
```

**Update Playlist:**

```python
api.session.rest_put(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}",
    json={"name": "Updated Playlist"})
```

**Delete Playlist:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}")
```

**List Playlist Locations:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}/locations",
    params={"max": 1000})
items = result["locations"]
```

**Update Playlist Locations:**

```python
api.session.rest_put(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}/locations",
    json={"locationIds": [loc_id_1, loc_id_2]})
```

### CLI Examples

#### Announcements

```bash
# List announcements (org-level, optionally filtered by location)
wxcli announcements list --location-id <loc_id>

# Get org-level announcement details
wxcli announcements show-announcements-config <ann_id>

# Get location-level announcement details
wxcli announcements show-announcements-locations <loc_id> <ann_id>

# Update an org-level announcement
wxcli announcements update <ann_id> --json-body '{"name": "Updated Greeting"}'

# Update a location-level announcement
wxcli announcements update-announcements <loc_id> <ann_id> --json-body '{"name": "Updated"}'

# Delete an org-level announcement
wxcli announcements delete <ann_id>

# Delete a location-level announcement
wxcli announcements delete-announcements <loc_id> <ann_id>

# Get org-level repository usage
wxcli announcements show

# Get location-level repository usage
wxcli announcements show-usage-announcements <loc_id>
```

#### Playlists

```bash
# List announcement playlists
wxcli announcement-playlists list

# Get playlist details
wxcli announcement-playlists show <playlist_id>

# Create a playlist
wxcli announcement-playlists create --name "Hold Music"

# Update a playlist
wxcli announcement-playlists update <playlist_id> --name "Updated Playlist"

# Delete a playlist
wxcli announcement-playlists delete <playlist_id>

# List playlist locations
wxcli announcement-playlists list-playlists <playlist_id>

# Update playlist locations
wxcli announcement-playlists update-playlists <playlist_id> \
  --json-body '{"locationIds": ["<loc_id_1>", "<loc_id_2>"]}'
```

---

## Single Number Reach

<!-- Updated by playbook session 2026-03-18 -->

### Overview

Single Number Reach (Office Anywhere) allows a person to receive calls on alternate phone numbers (mobile, home) when their primary Webex line rings. Calls are forwarded simultaneously or sequentially to the configured numbers.

### Raw HTTP

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

**Get Single Number Reach Settings for a Person:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/people/{person_id}/singleNumberReach")
# Returns: alertAllNumbersForClickToDialCallsEnabled, numbers[]
```

**Update Single Number Reach Settings for a Person:**

```python
api.session.rest_put(f"{BASE}/telephony/config/people/{person_id}/singleNumberReach",
    json={"alertAllNumbersForClickToDialCallsEnabled": True})
```

**Create a Single Number Reach Number:**

```python
body = {
    "phoneNumber": "+14155559999",
    "enabled": True,
    "name": "Mobile",
    "doNotForwardCallsEnabled": False,
    "answerConfirmationEnabled": True
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/people/{person_id}/singleNumberReach/numbers", json=body)
```

**Update a Single Number Reach Number:**

```python
api.session.rest_put(
    f"{BASE}/telephony/config/people/{person_id}/singleNumberReach/numbers/{number_id}",
    json={"enabled": False, "name": "Home"})
```

**Delete a Single Number Reach Number:**

```python
api.session.rest_delete(
    f"{BASE}/telephony/config/people/{person_id}/singleNumberReach/numbers/{number_id}")
```

**Get Available Phone Numbers for Single Number Reach:**

```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/singleNumberReach/availableNumbers",
    params={"max": 1000})
items = result["availableNumbers"]
```

### CLI Examples

```bash
# Get single number reach settings for a person
wxcli single-number-reach list-single-number-reach <person_id>

# Create a single number reach number for a person
wxcli single-number-reach create <person_id> \
  --json-body '{"phoneNumber": "+14155559999", "enabled": true, "name": "Mobile", "answerConfirmationEnabled": true}'

# Update single number reach settings for a person
wxcli single-number-reach update <person_id> \
  --json-body '{"alertAllNumbersForClickToDialCallsEnabled": true}'

# Update a specific single number reach number
wxcli single-number-reach update-numbers <person_id> <number_id> \
  --json-body '{"enabled": false, "name": "Home"}'

# Delete a single number reach number
wxcli single-number-reach delete <person_id> <number_id>

# List available phone numbers for single number reach
wxcli single-number-reach list <loc_id>
```

---

## Virtual Extensions

<!-- Updated by playbook session 2026-03-18 -->

### Overview

Virtual Extensions are directory entries with extensions (and optionally phone numbers) that are not tied to a person, workspace, or device. They appear in the dial-by-name directory and can be used for call routing. Virtual Extension Ranges allow bulk creation with a shared prefix.

### Raw HTTP

```python
from wxcli.auth import get_api
api = get_api()
BASE = "https://webexapis.com/v1"
```

#### Virtual Extensions

**List Virtual Extensions** (org-wide, filterable):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions",
    params={"locationId": loc_id, "name": "Lobby", "extension": "9000",
            "orgLevelOnly": "true", "max": 1000})
items = result["virtualExtensions"]  # response key: "virtualExtensions"
# Each item: {id, displayName, firstName, lastName, extension, phoneNumber, locationId, locationName}
```

**Get Virtual Extension Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions/{ext_id}")
```

**Create Virtual Extension:**

```python
body = {
    "displayName": "Lobby Directory",
    "firstName": "Lobby",
    "lastName": "Directory",
    "extension": "9000",
    "phoneNumber": "+14155551000",   # optional
    "locationId": loc_id             # optional
}
result = api.session.rest_post(f"{BASE}/telephony/config/virtualExtensions", json=body)
ext_id = result["id"]
```

**Update Virtual Extension:**

```python
api.session.rest_put(f"{BASE}/telephony/config/virtualExtensions/{ext_id}",
    json={"displayName": "New Name", "extension": "9001"})
```

**Delete Virtual Extension:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/virtualExtensions/{ext_id}")
```

**Get Virtual Extension Settings** (org-level):

```python
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensions/settings")
# Returns: mode (e.g., "STANDARD")
```

**Update Virtual Extension Settings:**

```python
api.session.rest_put(f"{BASE}/telephony/config/virtualExtensions/settings",
    json={"mode": "STANDARD"})
```

**Validate External Phone Numbers:**

```python
result = api.session.rest_post(
    f"{BASE}/telephony/config/virtualExtensions/actions/validateNumbers/invoke",
    json={"phoneNumbers": ["+14155551234"]})
```

#### Virtual Extension Ranges

**List Virtual Extension Ranges:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensionRanges",
    params={"name": "Sales", "prefix": "90", "locationId": loc_id, "max": 1000})
items = result["virtualExtensionRanges"]  # response key: "virtualExtensionRanges"
```

**Get Virtual Extension Range Details:**

```python
result = api.session.rest_get(f"{BASE}/telephony/config/virtualExtensionRanges/{range_id}")
```

**Create Virtual Extension Range:**

```python
result = api.session.rest_post(f"{BASE}/telephony/config/virtualExtensionRanges",
    json={"name": "Sales Range", "prefix": "90", "locationId": loc_id})
range_id = result["id"]
```

**Update Virtual Extension Range:**

```python
api.session.rest_put(f"{BASE}/telephony/config/virtualExtensionRanges/{range_id}/",
    json={"name": "Updated Range", "prefix": "91", "action": "REPLACE"})
```

**Delete Virtual Extension Range:**

```python
api.session.rest_delete(f"{BASE}/telephony/config/virtualExtensionRanges/{range_id}")
```

**Validate Range Prefix:**

```python
result = api.session.rest_post(
    f"{BASE}/telephony/config/virtualExtensionRanges/actions/validate/invoke",
    json={"locationId": loc_id, "name": "Test Range", "prefix": "90"})
```

### CLI Examples

#### Virtual Extensions

```bash
# List virtual extensions (org-wide, filterable)
wxcli virtual-extensions list --location-id <loc_id>

# Get details for a virtual extension
wxcli virtual-extensions show <ext_id>

# Create a virtual extension
wxcli virtual-extensions create --display-name "Lobby Directory" --extension "9000" --location-id <loc_id>

# Update a virtual extension
wxcli virtual-extensions update <ext_id> --display-name "New Name"

# Delete a virtual extension
wxcli virtual-extensions delete <ext_id>

# Get virtual extension settings (org-level)
wxcli virtual-extensions show-settings

# Update virtual extension settings
wxcli virtual-extensions update-settings --json-body '{"mode": "STANDARD"}'

# Validate external phone numbers
wxcli virtual-extensions validate-an-external --json-body '{"phoneNumbers": ["+14155551234"]}'
```

#### Virtual Extension Ranges

```bash
# List virtual extension ranges
wxcli virtual-extensions list-virtual-extension-ranges --location-id <loc_id>

# Get details for a virtual extension range
wxcli virtual-extensions show-virtual-extension-ranges <range_id>

# Create a virtual extension range
wxcli virtual-extensions create-virtual-extension-ranges --name "Sales Range" --prefix "90" --location-id <loc_id>

# Update a virtual extension range
wxcli virtual-extensions update-virtual-extension-ranges <range_id> \
  --json-body '{"name": "Updated Range", "prefix": "91", "action": "REPLACE"}'

# Delete a virtual extension range
wxcli virtual-extensions delete-virtual-extension-ranges <range_id>

# Validate a range prefix
wxcli virtual-extensions validate-the-prefix --json-body '{"locationId": "<loc_id>", "name": "Test Range", "prefix": "90"}'
```

---

## Data Models Quick Reference

### Shared Models

| Model | Used By | Description |
|-------|---------|-------------|
| `PersonPlaceAgent` | Call Park, Call Pickup | Person/workspace agent with ID, name, phone, extension, type |
| `CallParkExtension` | Call Park, Call Park Extensions | Lightweight model: id, name, extension |
| `RingPattern` | Call Park Settings | Enum: ring pattern (e.g., `normal`) |
| `UserType` | Paging | Enum for person vs. workspace |
| `DirectLineCallerIdName` | Paging, Voicemail Groups | Caller ID name settings (replaces deprecated first/last name) |
| `AvailableNumber` | Paging, Voicemail Groups | Available phone number for assignment |
| `CallRecordingSetting` | Customer Assist (Queue Recording) | Full call recording configuration (see fields below) |

#### `CallRecordingSetting` Fields

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Enable/disable call recording for the queue |
| `record` | `str` | Recording mode: `Always`, `Never`, or `Always with Pause/Resume` |
| `record_voicemail_enabled` | `bool` | Whether voicemail messages are recorded |
| `start_stop_announcement_enabled` | `bool` | Play recording start/stop announcement to parties |
| `notification` | `object` | Notification settings (type, threshold) |
| `repeat` | `object` | Repeat notification settings (enabled, interval) |
| `service_provider` | `str` | Recording vendor/provider name |
| `external_group` | `str` | External group tag for recording categorization |
| `external_identifier` | `str` | External identifier for the recording |

### Feature-Specific Models

| Model | Module | Description |
|-------|--------|-------------|
| `Paging`, `PagingAgent` | `telephony.paging` | Paging group and its members |
| `CallPark`, `CallParkSettings`, `LocationCallParkSettings` | `telephony.callpark` | Call park group and location-level settings |
| `CallParkRecall`, `RecallHuntGroup`, `AvailableRecallHuntGroup` | `telephony.callpark` | Recall behavior when park times out |
| `CallPickup`, `PickupNotificationType` | `telephony.callpickup` | Pickup group and notification enums |
| `VoicemailGroup`, `VoicemailGroupDetail` | `telephony.voicemail_groups` | Voicemail group list/detail models |
| `ScreenPopConfiguration` | `telephony.cx_essentials` | Screen pop settings |
| `WrapUpReason`, `WrapUpReasonDetails`, `QueueWrapupReasonSettings` | `telephony.cx_essentials.wrapup_reasons` | Wrap-up reason models |
| `AvailableQueue`, `WrapupReasonQueue`, `QueueSettingsReason` | `telephony.cx_essentials.wrapup_reasons` | Queue-related models for wrap-up |

---

## Dependencies & Relationships

```
Call Park ──────────── Call Park Extensions (assigned to park groups)
    |
    +──── Agents (PersonPlaceAgent: people, workspaces)
    |
    +──── Recall Hunt Group (optional: fallback when park times out)

Call Pickup ─────────── Agents (PersonPlaceAgent: people, workspaces, virtual lines)

Paging Group ────────── Originators (PagingAgent: who can page)
    |
    +──── Targets (PagingAgent: who receives pages, up to 75)

Voicemail Group ──────── Assigned to auto attendants, call queues, hunt groups
    |
    +──── Available Numbers (for primary and fax)

Customer Assist ─────── Call Queues (screen pop, recording, wrap-up per queue)
    |
    +──── Wrap-Up Reasons (org-level, assigned to queues)
    |
    +──── Available Agents (Customer Assist or Basic licensed)
```

### Key Dependency Notes

1. **Call Park requires Call Park Extensions**: You create Call Park Extensions first, then assign them to Call Park groups.
2. **Call Park recall requires Hunt Groups**: If using `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP` or `ALERT_HUNT_GROUP_ONLY`, a Hunt Group must exist at the location.
3. **Customer Assist requires Call Queues**: Screen pop, queue recording, and wrap-up reasons are all per-queue configurations. Call queues must be created first.
4. **Customer Assist requires licensing**: The `has_cx_essentials` filter on the List Available Agents endpoint distinguishes between Customer Assist and CX Basic licensed agents.
5. **Voicemail Groups are location-scoped**: Created within a location, but listed org-wide.
6. **Paging Groups are location-scoped**: Created within a location, but can be listed org-wide.
7. **ID instability for Call Park and Call Pickup**: The IDs for Call Park and Call Pickup entities change when their names are modified. Always re-fetch the ID after a name change.

---

## Gotchas (Cross-Cutting)

- **ID instability**: Call Park and Call Pickup IDs change when the entity name is modified. Always re-fetch the ID after a name update.
- **Agent format differs by feature type** : Hunt Groups and Call Queues take `agents` as `[{"id": "person_id"}]` (array of objects). Call Pickups take `agents` as `["person_id"]` (plain string array). Paging Groups take `targets` and `originators` as plain string arrays. Using `[{"id": ...}]` for pickup or paging returns 400 "Invalid field value: agents/targets". Reads always return full agent objects regardless.
- **Location-scoped features listed org-wide**: Paging Groups and Voicemail Groups can be listed org-wide (no `locationId` required), but **Call Parks and Call Pickups require `locationId`** for list operations. `wxcli call-park list` without a location argument returns empty. Must enumerate per-location during cleanup.
- **Nested settings require `--json-body`**: Features with complex nested body fields (voicemail group create, call park recall, screen pop, wrap-up settings) need `--json-body` in the CLI because the generator skips deeply nested object/array fields.
- **Voicemail Group create is strict**: Requires 7+ fields (name, extension, passcode, languageCode, messageStorage, notifications, faxMessage, transferToNumber, emailCopyOfMessage). The create body must use camelCase keys; use `--json-body` via the CLI.
- **Customer Assist requires licensing**: Screen pop, queue recording, and wrap-up reasons require Customer Assist licensing. Call queues must exist before configuring these features. Error 28018 ("CX Essentials is not enabled for this Call center") means the target queue is not a Customer Assist queue.
- **CX queue creation requires `callPolicies`**: Creating a Customer Assist queue without `callPolicies` in the request body returns 400. Use `--json-body` with at minimum `{"callPolicies":{"policy":"SIMULTANEOUS"}}`.
- **CX queues hidden from default list**: `wxcli call-queue list` does not show Customer Assist queues. Pass `--has-cx-essentials true` to see them.
- **Supervisor delete returns 204 but persists**: `delete-supervisors-config-1 --has-cx-essentials true` gets 204 from the API but the supervisor remains. Workaround: use `update-supervisors` with `action: DELETE` on each agent — removing the last agent auto-removes the supervisor.
- **Call Park requires recall**: Creating a Call Park without a `recall` option (e.g., `ALERT_PARKING_USER_ONLY`) will be rejected by the API.
- **Announcement upload takes a file URI, not a local file**: `wxcli announcements create` (org) and `wxcli announcements create-announcements LOCATION_ID` (location) send a JSON body with `fileUri`/`fileName` -- the file must already be reachable at a URI. There is no local-file upload flag.
- **CallPickupGroup AXL creation with members fails on CUCM 15.0.** The `addCallPickupGroup` AXL operation with `<members>` containing `<directoryNumber>` elements fails with a null priority foreign key constraint (`pickupgroupmember.priority`). Workaround: create the pickup group empty, then add members via `updateLine` with `callPickupGroupName` on each member DN. Verified on CUCM 15.0.1.13901(2).
- **No native PagingGroup AXL object type.** CUCM does not expose paging groups through AXL (`listPagingGroup`/`getPagingGroup` do not exist). Paging requires third-party systems (InformaCast, Cisco Paging Server). The migration pipeline's `CanonicalPagingGroup` type exists for manual/CSV import but cannot be auto-extracted from CUCM.

---

## See Also

- [Major Call Features](call-features-major.md) -- Auto Attendants, Call Queues, and Hunt Groups (Call Park recall references Hunt Groups; Customer Assist extends Call Queues; Voicemail Groups can be assigned to AA/CQ/HG)
- [Call Routing & PSTN](call-routing.md) -- dial plans, trunks, and routing chain (Paging Groups and Voicemail Groups with phone numbers participate in call routing)
- [Provisioning Reference](provisioning.md) -- creating locations and users (all features in this doc are location-scoped and require existing locations)
