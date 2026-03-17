---
name: configure-features
description: |
  Configure Webex Calling call features: Auto Attendants, Call Queues, Hunt Groups,
  Paging Groups, Call Park, Call Pickup, Voicemail Groups, and CX Essentials.
  Guides the user from prerequisites through creation and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [feature-type]
---

# Configure Call Features Workflow

## Step 1: Load references

1. Read `docs/reference/call-features-major.md` for AA, CQ, HG data models and API signatures
2. Read `docs/reference/call-features-additional.md` for Paging, Call Park, Call Pickup, VM Groups, CX Essentials
3. Read `docs/reference/authentication.md` for auth token conventions
4. Read `docs/reference/wxc-sdk-patterns.md` for SDK usage patterns

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi(tokens='<token>')
me = api.people.me()
print(f"Authenticated as: {me.display_name}")
```

If this fails, stop and resolve authentication first. Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`
- **CX Essentials recording**: `spark-admin:people_read` / `spark-admin:people_write`

## Step 3: Identify which feature(s) to configure

Ask the user which feature they want to create. Present this decision matrix if they are unsure:

| Need | Feature |
|------|---------|
| IVR menu with key-press routing ("Press 1 for Sales...") | **Auto Attendant** |
| Hold callers in queue until an agent is free | **Call Queue** |
| Ring a group of agents directly (no queue hold) | **Hunt Group** |
| One-way broadcast announcements to phones | **Paging Group** |
| Park a call on an extension for someone else to pick up | **Call Park** |
| Let team members answer each other's ringing phones | **Call Pickup** |
| Shared voicemail box for a team or feature | **Voicemail Group** |
| Screen pop, queue recording, or wrap-up reasons on a CQ | **CX Essentials** |

## Step 4: Check prerequisites

Before creating any feature, verify these exist:

### 4a. Location exists

All features are location-scoped. Confirm the target location:

```python
locations = list(api.locations.list(name='<location_name>'))
location = locations[0]
location_id = location.location_id
print(f"Location: {location.name} ({location_id})")
```

If no location matches, the user must create one first (see provisioning skill).

### 4b. Users/agents exist (for features that need members)

For CQ, HG, Paging, Call Park, Call Pickup -- confirm the people who will be agents/members:

```python
people = list(api.people.list(display_name='<name>'))
for p in people:
    print(f"{p.display_name} — {p.person_id}")
```

### 4c. Phone numbers available (for features that need a number)

For AA, CQ, HG, Paging, VM Groups -- check available numbers at the location:

```python
# Example for auto attendant; each feature has its own method
numbers = list(api.telephony.auto_attendant.primary_available_phone_numbers(location_id=location_id))
for n in numbers:
    print(f"{n.phone_number} — {n.extension}")
```

### 4d. Feature-specific prerequisites

| Feature | Additional Prerequisites |
|---------|------------------------|
| **Auto Attendant** | Business hours schedule must exist. Custom greetings must be uploaded via Control Hub (API upload not supported). |
| **Call Queue** | Agents must have Webex Calling Professional license. CX Essentials queue requires CX Essentials license on agents. |
| **Hunt Group** | None beyond location + agents. Can be created with zero agents. |
| **Paging Group** | If originators are set, `originator_caller_id_enabled` is required. |
| **Call Park** | Call Park Extensions should be created first. Recall to hunt group requires an existing HG. |
| **Call Pickup** | A user can only belong to one pickup group at a time. |
| **Voicemail Group** | Extension is required. Passcode is required. |
| **CX Essentials** | Call Queue must exist first. Requires CX Essentials licensing. |

## Step 5: Gather feature-specific configuration

Based on the selected feature, collect the required parameters from the user. **Always present the plan before executing.**

---

### Auto Attendant

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name for the AA |
| Phone number or extension | Yes (one of) | Use `primary_available_phone_numbers()` to find candidates |
| Business hours schedule | Yes | Must already exist at org/location level |
| Holiday schedule | No | Optional |
| Business hours menu | Yes | Key-press actions (see key config below) |
| After hours menu | Yes | Key-press actions |
| Extension dialing | No | `ENTERPRISE` (default) or `GROUP` |
| Name dialing | No | `ENTERPRISE` (default) or `GROUP` |

**Key-press actions** — for each menu, define up to 12 keys (`0`-`9`, `*`, `#`):

| Action | Description |
|--------|-------------|
| `TRANSFER_WITHOUT_PROMPT` | Transfer immediately to a number/extension |
| `TRANSFER_WITH_PROMPT` | Play prompt then transfer |
| `TRANSFER_TO_OPERATOR` | Transfer to operator |
| `NAME_DIALING` | Dial-by-name directory |
| `EXTENSION_DIALING` | Dial-by-extension |
| `REPEAT_MENU` | Replay the menu |
| `EXIT` | Disconnect |
| `TRANSFER_TO_MAILBOX` | Transfer to voicemail |
| `RETURN_TO_PREVIOUS_MENU` | Go back one level |
| `PLAY_ANNOUNCEMENT` | Play an announcement |

**SDK call:**
```python
from wxc_sdk.telephony.autoattendant import AutoAttendant, AutoAttendantMenu, AutoAttendantKeyConfiguration
from wxc_sdk.telephony.autoattendant import AutoAttendantAction, Greeting, MenuKey

settings = AutoAttendant.create(
    name='Main Menu',
    business_schedule='Business Hours',
    extension='1000'
)
settings.business_hours_menu = AutoAttendantMenu(
    greeting=Greeting.DEFAULT,
    extension_enabled=True,
    key_configurations=[
        AutoAttendantKeyConfiguration(key='1', action=AutoAttendantAction.TRANSFER_WITHOUT_PROMPT, value='2000'),
        AutoAttendantKeyConfiguration(key='0', action=AutoAttendantAction.TRANSFER_TO_OPERATOR, value='1001'),
    ]
)
settings.after_hours_menu = AutoAttendantMenu(
    greeting=Greeting.DEFAULT,
    key_configurations=[
        AutoAttendantKeyConfiguration(key='0', action=AutoAttendantAction.EXIT),
    ]
)
aa_id = api.telephony.auto_attendant.create(location_id=location_id, settings=settings)
```

---

### Call Queue

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name |
| Phone number or extension | Yes (one of) | |
| Routing policy | Yes | `CIRCULAR`, `REGULAR`, `SIMULTANEOUS` (max 50 agents), `UNIFORM`, `WEIGHTED` (max 100 agents) |
| Routing type | No | `PRIORITY_BASED` (default) or `SKILL_BASED` |
| Agents | Yes | List of person IDs (people, workspaces, or virtual lines) |
| Queue size | Yes | Max calls in queue before overflow triggers |
| Overflow action | No | `PERFORM_BUSY_TREATMENT`, `TRANSFER_TO_PHONE_NUMBER`, `PLAY_RINGING_UNTIL_CALLER_HANGS_UP` |
| Overflow transfer number | If overflow=transfer | Destination number |
| Call bounce settings | No | `max_rings` (default 5), `agent_unavailable_enabled` |
| Agent join/unjoin enabled | No | Let agents toggle themselves in/out |

**Announcement chain** (all optional, configure as needed):

1. **Welcome message** — first thing callers hear; can be mandatory even when agent is available
2. **Wait message** — estimated wait time or queue position
3. **Comfort message** — periodic message (promotions, info); interval 10-600 seconds
4. **Comfort message bypass** — short comfort for quickly-answered calls
5. **Music on hold** — normal + alternate source
6. **Whisper message** — plays to agent before connection (identifies which queue)

**SDK call:**
```python
from wxc_sdk.telephony.callqueue import CallQueue, CallQueueCallPolicies, QueueSettings, OverflowSetting
from wxc_sdk.telephony.hg_and_cq import Agent, Policy

settings = CallQueue.create(
    name='Support Queue',
    agents=[Agent(agent_id=pid) for pid in person_ids],
    queue_size=10,
    extension='2000'
)
cq_id = api.telephony.callqueue.create(location_id=location_id, settings=settings)
```

---

### Hunt Group

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Unique name |
| Phone number or extension | Yes (one of) | |
| Ring pattern (policy) | No | `CIRCULAR` (default), `REGULAR`, `SIMULTANEOUS` (max 50), `UNIFORM`, `WEIGHTED` (max 100) |
| Members | No | Can create with zero agents and add later |
| No-answer behavior | No | Advance to next agent, forward after N rings, forward destination |
| Busy redirect | No | Where to send calls when all agents busy |
| Business continuity redirect | No | Fallback when phone system is disconnected |

**Key difference from Call Queue:** Hunt groups ring agents directly -- no queue hold, no announcements chain, no agent join/unjoin.

**SDK call:**
```python
from wxc_sdk.telephony.huntgroup import HuntGroup

settings = HuntGroup.create(
    name='Sales Team',
    extension='3000'
)
hg_id = api.telephony.huntgroup.create(location_id=location_id, settings=settings)
```

---

### Paging Group

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 30 chars |
| Phone number or extension | Yes (one of) | |
| Originators | No | People/workspaces who can initiate pages |
| Targets | No | People/workspaces/virtual lines who receive pages (up to 75) |
| Originator caller ID enabled | Yes if originators set | Shows originator's caller ID on target phones |

**SDK call:**
```python
from wxc_sdk.telephony.paging import Paging, PagingAgent

settings = Paging.create(name='Warehouse Page', extension='8100')
settings.originator_caller_id_enabled = True
settings.originators = [PagingAgent(agent_id=pid) for pid in originator_ids]
settings.targets = [PagingAgent(agent_id=pid) for pid in target_ids]
paging_id = api.telephony.paging.create(location_id=location_id, settings=settings)
```

---

### Call Park

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 80 chars |
| Agents | No | People/workspaces eligible to receive parked calls |
| Call Park Extensions | No | Dedicated park extensions (create these first) |
| Park on agents enabled | No | Whether calls can be parked directly on agents |
| Recall behavior | No | `ALERT_PARKING_USER_ONLY` (default), `ALERT_PARKING_USER_FIRST_THEN_HUNT_GROUP`, `ALERT_HUNT_GROUP_ONLY` |
| Recall hunt group | If recall uses HG | Must be an existing hunt group at the location |

**Two-step process:**
1. Create Call Park Extensions first (if needed):
```python
cpe_id = api.telephony.callpark_extension.create(
    location_id=location_id, name='Park Slot 1', extension='7001'
)
```
2. Create the Call Park group:
```python
from wxc_sdk.telephony.callpark import CallPark

settings = CallPark.default(name='Lobby Park')
park_id = api.telephony.callpark.create(location_id=location_id, settings=settings)
```

**Location-level settings** (recall timer, ring pattern):
```python
loc_settings = api.telephony.callpark.call_park_settings(location_id=location_id)
# loc_settings.call_park_settings.recall_time = 60  # seconds (30-600)
```

**Gotcha:** Call Park ID changes when name is modified. Always re-fetch after a name change.

---

### Call Pickup

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Max 80 chars |
| Members | No | People, workspaces, virtual lines |
| Notification type | No | `NONE`, `AUDIO_ONLY`, `VISUAL_ONLY`, `AUDIO_AND_VISUAL` |
| Notification delay (seconds) | No | Time before notification fires |

**Constraint:** A user can only belong to one call pickup group at a time.

**SDK call:**
```python
from wxc_sdk.telephony.callpickup import CallPickup, PickupNotificationType

settings = CallPickup(
    name='Front Desk Pickup',
    notification_type=PickupNotificationType.AUDIO_AND_VISUAL,
    notification_delay_timer_seconds=8,
    agents=[PersonPlaceAgent(agent_id=pid) for pid in member_ids]
)
pickup_id = api.telephony.callpickup.create(location_id=location_id, settings=settings)
```

**Gotcha:** Call Pickup ID changes when name is modified. Always re-fetch after a name change.

---

### Voicemail Group

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | Group name |
| Extension | Yes | Required on create |
| Passcode | Yes | Access passcode (integer) |
| First name / Last name | Yes | Caller ID display (deprecated — use `direct_line_caller_id_name` if available) |
| Phone number | No | Optional external number |
| Language code | No | Default `en_us` |
| Message storage | No | `INTERNAL` (default) or `EXTERNAL` with email |
| Notifications enabled | No | Email/phone notification on new message |
| Fax enabled | No | Enable fax reception with dedicated number |
| Transfer to number | No | Caller presses 0 to transfer |
| Email copy of message | No | Send voicemail copies to email |

**SDK call:**
```python
from wxc_sdk.telephony.voicemail_groups import VoicemailGroupDetail

settings = VoicemailGroupDetail.create(
    name='Support VM',
    extension='8200',
    first_name='Support',
    last_name='Team',
    passcode=740384,
    language_code='en_us'
)
vmg_id = api.telephony.voicemail_groups.create(location_id=location_id, settings=settings)
```

---

### CX Essentials

CX Essentials enhances existing Call Queues. The queue must exist first.

**Three sub-features:**

#### Screen Pop
Pop a URL when agent receives a queued call:
```python
from wxc_sdk.telephony.cx_essentials import ScreenPopConfiguration

config = ScreenPopConfiguration(
    enabled=True,
    screen_pop_url='https://crm.example.com/lookup',
    desktop_label='Customer Lookup',
    query_params={'caller_id': '{{callerNumber}}'}
)
api.telephony.cx_essentials.modify_screen_pop_configuration(
    location_id=location_id, queue_id=queue_id, settings=config
)
```

#### Queue Call Recording
```python
recording = api.telephony.cx_essentials.callqueue_recording.read(
    location_id=location_id, queue_id=queue_id
)
recording.enabled = True
recording.record = 'Always'
api.telephony.cx_essentials.callqueue_recording.configure(
    location_id=location_id, queue_id=queue_id, recording=recording
)
```

#### Wrap-Up Reasons
Create org-level reasons, then assign to queues:
```python
# Create a reason
reason_id = api.telephony.cx_essentials.wrapup_reasons.create(
    name='Issue Resolved',
    description='Customer issue was resolved on the call',
    queues=[queue_id]
)

# Configure queue wrap-up settings
api.telephony.cx_essentials.wrapup_reasons.update_queue_settings(
    location_id=location_id,
    queue_id=queue_id,
    wrapup_reasons=[reason_id],
    wrapup_timer_enabled=True,
    wrapup_timer=60
)
```

---

## Step 6: Build and present deployment plan — `[SHOW BEFORE EXECUTING]`

Before executing any API calls, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Feature: [type]
Location: [name] ([location_id])
Name: [feature_name]
Phone/Extension: [number or extension]

Configuration:
  [Feature-specific settings listed here]

Members/Agents:
  - [Person 1] ([person_id])
  - [Person 2] ([person_id])

Prerequisites verified:
  ✓ Location exists
  ✓ [N] agents found
  ✓ Phone number/extension available
  ✓ [Feature-specific prereqs]

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

## Step 7: Execute via wxc_sdk

Run the creation API call. If the feature requires multiple steps (e.g., Call Park Extensions before Call Park), execute them in order.

Handle errors explicitly:
- **401/403**: Token expired or insufficient scopes — re-authenticate
- **409**: Name or extension conflict — ask user for alternate
- **400**: Validation error — read the error message and fix the parameter

## Step 8: Verify creation

After creation, fetch the details back and confirm:

```python
# Example for auto attendant
created = api.telephony.auto_attendant.details(
    location_id=location_id, auto_attendant_id=aa_id
)
print(f"Created: {created.name}")
print(f"Extension: {created.extension}")
print(f"Phone: {created.phone_number}")
```

If phone number assignment is separate (some features), assign it now:
```python
# Check if number needs separate assignment
# This varies by feature — AA, CQ, HG accept number at creation
# Paging and VM Groups also accept number at creation
```

## Step 9: Report results

Present the creation results:

```
FEATURE CREATED
===============
Type: [feature_type]
Name: [name]
ID: [feature_id]
Location: [location_name]
Extension: [extension]
Phone Number: [phone_number or "None assigned"]
Agents/Members: [count]

Next steps:
  - [Feature-specific next steps, e.g., "Upload custom greeting via Control Hub"]
  - [e.g., "Configure holiday service on the queue policy"]
  - [e.g., "Add agents to the hunt group"]
```

---

## Critical Rules

1. **Always verify location exists** before creating any feature. Every feature is location-scoped.
2. **Always show the deployment plan** (Step 6) and wait for user confirmation before executing.
3. **Agent/member assignment requires valid person IDs.** Use `api.people.list()` or the feature-specific `available_agents()` to find them.
4. **Phone number vs. extension** — at least one is required for AA, CQ, HG, Paging, VM Groups. Use `primary_available_phone_numbers()` to find unassigned numbers.
5. **Audio file upload is not supported via API** — custom greetings for AA and CQ must be uploaded through Webex Control Hub.
6. **Call Park and Call Pickup IDs change on name modification.** Always re-fetch after renaming.
7. **CQ routing policy limits** — `SIMULTANEOUS` max 50 agents; `WEIGHTED` max 100 agents; `CIRCULAR`/`REGULAR`/`UNIFORM` max 1,000 agents.
8. **Paging Group validation** — if `originators` are provided, `originator_caller_id_enabled` must be set (raises `TypeError` otherwise).
9. **Call Pickup one-group-per-user constraint** — a user can only belong to one pickup group. Check `available_agents()` to find unassigned users.
10. **CX Essentials requires existing Call Queues** — screen pop, recording, and wrap-up reasons are per-queue configurations.
11. **Hunt Group holiday/night service** uses forwarding rules (schedule-based), not a dedicated policy API like Call Queues have.
12. **Voicemail Group passcode is required** on create — the `VoicemailGroupDetail.create()` factory enforces this.
