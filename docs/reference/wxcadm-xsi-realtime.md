# wxcadm XSI & Real-time Call Monitoring

## Why This Matters

XSI (eXtended Services Interface) is the one thing wxcadm can do that wxc_sdk cannot. While wxc_sdk covers the public Webex REST APIs for provisioning, configuration, and admin tasks, it has no access to the real-time call control plane. XSI connects directly to the BroadWorks call control back-end that powers Webex Calling, giving you:

- **Real-time event streams** — every call placed, received, held, transferred, parked, and released fires an event you can consume
- **Programmatic call control** — originate, hold, resume, transfer, conference, park, record, and hang up calls from code
- **Live call state** — query active calls, get call status, see remote party info and endpoint details
- **Directory access** — search Enterprise, Group, and Personal directories directly from the call control platform
- **Service configuration reads** — pull BLF/monitoring, Executive/Assistant, SNR, anonymous call rejection settings live from the platform (not cached admin data)

None of this is available through wxc_sdk or the standard Webex REST APIs.

---

## XSI Architecture Overview

```
Your App (wxcadm)
    |
    |--- XSI-Actions  (REST calls → call control, profile, services, directory)
    |--- XSI-Events   (long-running HTTP streaming → real-time event delivery)
    |
    v
Webex Calling XSP (eXtended Services Platform)
    |
    v
BroadWorks Call Control Back-end
```

XSI exposes two distinct interfaces:

| Interface | Transport | Purpose |
|-----------|-----------|---------|
| **XSI-Actions** | Standard REST (JSON/XML) | Call control commands, profile/service reads, directory search |
| **XSI-Events** | Long-running HTTP stream | Asynchronous event delivery for call state changes |

The XSI endpoints are unique per Org. wxcadm discovers them via the `v1/organizations/{id}?callingData=true` API call, which returns:
- `xsiActionsEndpoint` — base URL for call control and data queries
- `xsiEventsEndpoint` — base URL for event subscription management
- `xsiEventsChannelEndpoint` — base URL for opening streaming channels
- `xsiDomain` — domain used for SRV record lookups to find all XSPs

---

## Setup & Authentication

### Prerequisites

1. **XSI must be enabled on your Webex Org.** This is not on by default. Contact Cisco TAC to request activation.
2. **API token scopes**: Your Integration or access token must include:
   - `spark-admin:xsi` — admin-level XSI access
   - `spark:xsi` — user-level XSI access (if enabled)
   - The 12-hour developer token from developer.webex.com includes all necessary scopes automatically.

### Initializing XSI

Two approaches to get XSI endpoints:

```python
import wxcadm

access_token = "Your API Access Token"

# Option 1: Get XSI endpoints at Webex init time
webex = wxcadm.Webex(access_token, get_xsi=True)

# Option 2: Get XSI endpoints later
webex = wxcadm.Webex(access_token)
webex.org.get_xsi_endpoints()
```

`get_xsi_endpoints()` calls the Org API with `callingData=true` and populates `webex.org.xsi` with the four endpoint URLs. If XSI is not enabled, it returns `None`.

### Starting an XSI Session for a Person

XSI operates per-user. You must start an XSI session for each Person you want to control or query:

```python
person = webex.org.get_person_by_email("user@domain.com")
person.start_xsi()  # Creates person.xsi (an XSI instance)
```

**Signature:**
```python
Person.start_xsi(get_profile: bool = False, cache: bool = False) -> XSI
```

- `get_profile=True` — automatically fetches the XSI profile (phone number, extension, etc.) during init
- `cache=True` — caches XSI data so subsequent property accesses don't re-query the platform. Default is live (uncached).

The `start_xsi()` method creates an `XSI` instance and stores it at `person.xsi`. The XSI instance sets up:
- HTTP headers with `X-BroadWorks-Protocol-Version: 25.0`, JSON accept/content-type, plus the Webex auth token
- Query params with `format=json`
- A user ID derived from the Person's Spark ID (the BroadWorks user identifier)

---

## XSI Profile & Services (XSI-Actions)

Once `person.start_xsi()` has been called, you can read data directly from the call control platform.

### Profile

```python
person.start_xsi(get_profile=True)
print(person.xsi.profile)
```

Returns a dict with:

| Key | Description |
|-----|-------------|
| `country_code` | Country dialing code |
| `number` | Phone number (if assigned) |
| `extension` | Extension (if assigned) |
| `user_id` | BroadWorks user ID |
| `group_id` | BroadWorks group ID (maps to Webex Calling Location) |
| `service_provider` | Service provider identifier |
| `registrations_url` | URL to query device registrations |
| `schedule_url` | URL to query user schedules |
| `fac_url` | URL to query Feature Access Codes |
| `raw` | The complete raw profile response |

### Device Registrations

```python
registrations = person.xsi.registrations
```

Returns the device registrations associated with the person (phones, Webex app, etc.). Requires the profile to have been fetched first (auto-fetches if needed).

### Services

```python
services = person.xsi.get_services()
```

Queries all assigned services and their configurations. Returns a dict keyed by service name with the full service config as the value. Services without configuration data are stored as `True`.

### Individual Service Properties

These are available as properties with lazy loading (fetched on first access, or every access if `cache=False`):

```python
person.xsi.executive              # Executive settings
person.xsi.executive_assistant    # Executive Assistant settings
person.xsi.monitoring             # BLF/Busy Lamp Field settings
person.xsi.single_number_reach    # SNR / Office Anywhere settings
person.xsi.anonymous_call_rejection  # Anonymous Call Rejection settings
person.xsi.alternate_numbers      # Alternate Numbers
```

Each property queries: `GET /v2.0/user/{userId}/services/{ServiceName}`

### Feature Access Codes

```python
fac_list = person.xsi.fac_list
for fac in fac_list:
    print(f"{fac.feature}: {fac.code} (alt: {fac.alternate_code})")
```

Returns a list of `FeatureAccessCode` objects with `.feature`, `.code`, and `.alternate_code` attributes.

### Directory Search

```python
results = person.xsi.directory(
    type='Enterprise',        # or 'Group', 'Personal'
    first_name='John',
    last_name='Smith',
    any_match=False           # True = OR logic across filters
)
```

**Signature:**
```python
XSI.directory(
    type: str = 'Enterprise',
    first_name: str = None,
    last_name: str = None,
    name: str = None,
    user_id: str = None,
    group_id: str = None,
    number: str = None,
    extension: str = None,
    mobile_number: str = None,
    department: str = None,
    email: str = None,
    any_match: bool = False
) -> list[dict]
```

**Filter availability by directory type:**

| Directory Type | Available Filters |
|----------------|-------------------|
| Enterprise | first_name, last_name, name, user_id, group_id, number, extension, mobile_number, department, email |
| Group | first_name, last_name, name, user_id, group_id, number, extension, mobile_number, department, email |
| Personal | name, number |

**Case-insensitive search:** Append `/i` to the search string, e.g. `first_name='John/i'` matches "John", "john", "JOHN".

Handles pagination automatically (fetches 50 records at a time until all results are retrieved).

---

## Call Control via XSI (XSI-Actions)

### Creating and Originating Calls

```python
person.start_xsi()

# Create a call object, then originate
call = person.xsi.new_call()
call.originate("17192662837")

# Or create and originate in one step
call = person.xsi.new_call(address="17192662837")

# One-liner for simple click-to-dial
person.start_xsi().new_call().originate("17192662837")
```

**`XSI.new_call()` signature:**
```python
XSI.new_call(
    address: str = None,        # Phone number to dial
    phone: str = 'All',         # 'All', 'Primary', or 'SharedCallAppearance'
    aor: str = None             # Address-of-record for shared devices
) -> Call
```

**`Call.originate()` signature:**
```python
Call.originate(
    address: str,               # Phone number or extension to call
    comment: str = "",          # Text comment attached to the call
    phone: str = 'All',         # Device selection
    aor: str = None,            # Address-of-record for shared devices
    executive: str = None       # Extension/number of executive (for assistant calls)
) -> bool
```

On success, the `Call` object gets populated with:
- `call.id` — the XSI call ID
- `call._external_tracking_id` — XSI external tracking ID

### Querying Active Calls

```python
active_calls = person.xsi.calls  # Returns list[Call]
```

The `calls` property queries `GET /v2.0/user/{userId}/calls` and creates fresh `Call` instances for each active call. Previous instances are destroyed on each access.

### Call Status

```python
status = call.status
```

Returns a dict:
```python
{
    'network_call_id': str,     # Unique network-side call ID
    'personality': str,         # 'Originator' or 'Terminator'
    'state': str,               # 'Active', 'Held', 'Alerting', etc.
    'remote_party': {
        'address': str,         # Remote party's address
        'call_type': str        # Call type
    },
    'endpoint': {
        'type': str,            # Endpoint type
        'aor': str              # Address of Record
    },
    'appearance': str,          # Call Appearance number
    'diversion_inhibited': bool,
    'start_time': str,          # UNIX timestamp
    'answer_time': str,         # UNIX timestamp (None if unanswered)
    'status_time': int          # UNIX timestamp of this status query
}
```

### Hold and Resume

```python
call.hold()      # Places the call on hold; sets call.held = True
call.resume()    # Takes the call off hold; sets call.held = False
```

Both return an `XSIResponse` object (truthy on success, falsy on failure).

### Answer an Incoming Call

```python
# Answer the most recent incoming call
answered_call = person.xsi.answer_call()

# Or answer a specific call
answered_call = person.xsi.answer_call(call_id="the-call-id")
```

### Hang Up

```python
call.hangup()              # Normal hangup
call.hangup(decline=True)  # Decline/reject the call
```

### Transfer

```python
# Blind transfer
call.transfer("2345")

# VM transfer (sends directly to target's voicemail)
call.transfer("2345", type="vm")

# Mute transfer
call.transfer("2345", type="mute")

# Attended transfer (puts current call on hold, dials target)
call.transfer("2345", type="attended")
# ... agent and target talk ...
call.finish_transfer()  # Completes the transfer
```

**For Call Queue calls:** the address parameter is sent as `phoneno` instead of `address` (handled automatically).

### Conference

```python
# Conference from an attended transfer (all parties joined)
call.transfer("2345", type="attended")
# ... talk to the target ...
call.conference()          # Bridges all parties
call.finish_transfer()     # Drop the initiator, leave others connected

# Conference with a new party (holds current call, dials, bridges on answer)
conference = call.conference(address="5678")
```

**`Conference` class methods:**

```python
conference.mute(call_id)   # Mute a participant (they can still hear)
conference.deaf(call_id)   # Deaf a participant (they can still be heard)
```

### Call Park

```python
# Group Call Park (auto-assigned extension; user must be in a Park Group)
parked_extension = call.park()

# Park at a specific Call Park Extension
parked_extension = call.park(extension="8001")
```

Returns the extension where the call was parked. Raises `NotAllowed` if the user isn't in a Park Group or the extension is busy.

### Call Recording Control

```python
call.recording("start")    # Start recording
call.recording("stop")     # Stop recording (On Demand mode only)
call.recording("pause")    # Pause recording
call.recording("resume")   # Resume paused recording
```

Requires Call Recording to be enabled for the user. Raises `NotAllowed` if not enabled.

**Known issue in source:** The `recording()` method has a bug where `action="resume"` maps to `PauseRecording` instead of `ResumeRecording` due to a duplicate elif condition. The `"resume"` case on line 1524 (which correctly calls `ResumeRecording`) is reachable, but the duplicate on line 1528 would never execute. <!-- NEEDS VERIFICATION: confirm this bug is still present in latest release -->

### DTMF

```python
call.send_dtmf("12345#")       # Send digits
call.send_dtmf("23456#,123")   # Comma = pause between digits
```

### Executive/Assistant Call Handling

```python
# Assistant places a call on behalf of the Executive
assistant = webex.org.get_person_by_email("assistant@company.com")
assistant.start_xsi()
call = assistant.xsi.new_call()
call.originate("7192662837", executive="1234")  # 1234 = exec's extension

# Push the call to the Executive's devices
call.exec_push()
```

### Reconnect

```python
call.reconnect()  # Retrieves call from hold AND releases all other calls
```

### Attach to an Existing Call

When you know a call ID (e.g., from an XSI Event), you can create a `Call` object for it:

```python
# From an XSI instance
call = person.xsi.attach_call(call_id="known-call-id")

# From an XSICallQueue
queue = wxcadm.XSICallQueue(call_queue_id="queue-id", org=webex.org)
call = queue.attach_call(call_id="known-call-id")
```

---

## XSI Response Handling

All call control methods (hold, resume, transfer, hangup, etc.) return an `XSIResponse` object:

```python
response = call.hold()
if response:                  # Truthy when HTTP status is OK
    print("Hold successful")
else:
    print(f"Failed: {response.summary}")

response.success              # bool
response.raw_response         # dict or text
response.summary              # Error summary text (if error)
```

---

## XSI-Events: Real-time Call Monitoring

This is the core differentiator. XSI-Events provides a persistent, streaming connection that delivers every call event in the organization (or for a specific user) as it happens.

### Architecture

```
XSIEvents (org-level)
  └─ XSIEventsChannelSet (groups channels + manages subscriptions)
       ├─ XSIEventsChannel (long-running HTTP stream to XSP #1)
       │    ├─ _channel_daemon thread (reads streaming events)
       │    └─ _heartbeat_daemon thread (sends heartbeats every 15s)
       ├─ XSIEventsChannel (long-running HTTP stream to XSP #2)
       │    ├─ _channel_daemon thread
       │    └─ _heartbeat_daemon thread
       └─ XSIEventsSubscription(s) (what events to receive)
```

Key design decisions in wxcadm:
- **One channel per XSP**: wxcadm does a DNS SRV lookup on the XSI domain (`_xsi-client._tcp.{domain}`) to discover all XSP servers, then opens a streaming channel to each one
- **Daemon threads**: Each channel runs two daemon threads — one reading the stream, one sending heartbeats
- **Python Queue**: All events are delivered into a standard `queue.Queue` you provide, decoupling event production from consumption
- **Automatic ACKs**: wxcadm automatically acknowledges each event to the server (required by the XSI protocol)
- **Auto-refresh**: Channels and subscriptions are refreshed every hour (7200-second expiry) to stay alive

### Basic Event Monitoring Pattern

```python
import queue
import wxcadm

access_token = "Your API Access Token"
webex = wxcadm.Webex(access_token, get_xsi=True)

# Create the XSIEvents instance (org-level)
events = wxcadm.XSIEvents(webex.org)

# Create a queue — set maxsize to prevent unbounded memory growth
events_queue = queue.Queue(maxsize=500)

# Open a channel set (auto-discovers XSPs, creates channels + heartbeat threads)
channel = events.open_channel(events_queue)

# Subscribe to an event package
subscription = channel.subscribe(["Advanced Call"])

# Process events as they arrive
while True:
    event = events_queue.get()
    event_type = event['xsi:Event']['xsi:eventData']['@xsi1:type']
    print(f"Event: {event_type}")
```

### Event Packages

The `subscribe()` method accepts an event package name. The primary package:

| Package | Description |
|---------|-------------|
| `Advanced Call` | All call-related events (originate, ring, answer, hold, transfer, release, hook status, etc.) |

<!-- NEEDS VERIFICATION: confirm full list of available event packages (e.g., "Basic Call", "Call Center", "Do Not Disturb", etc.) — the source code only demonstrates "Advanced Call" -->

### Subscription Scopes

```python
# Org-wide: monitor ALL calls across the entire organization
subscription = channel.subscribe(["Advanced Call"])

# Per-user: monitor calls for a specific person only
person = webex.org.get_person_by_email("user@domain.com")
subscription = channel.subscribe(["Advanced Call"], person=person)
```

Org-wide subscription uses the `serviceprovider/{enterpriseId}` endpoint. Per-user subscription uses the `user/{userId}` endpoint.

### XSI Event Types

A single outbound call from a Webex Calling desk phone generates **six events**:

| Event Type | When It Fires |
|------------|---------------|
| `xsi:HookStatusEvent` | Phone goes off-hook |
| `xsi:CallOriginatedEvent` | Call is initiated (dialing) |
| `xsi:CallUpdatedEvent` | Call state changes (ringing, etc.) |
| `xsi:CallAnsweredEvent` | Remote party answers |
| `xsi:CallReleasedEvent` | Call ends |
| `xsi:HookStatusEvent` | Phone goes on-hook |

Additional event types you will see in practice:

| Event Type | When It Fires |
|------------|---------------|
| `xsi:CallReceivedEvent` | Incoming call arrives |
| `xsi:CallHeldEvent` | Call placed on hold |
| `xsi:CallRetrievedEvent` | Call taken off hold |
| `xsi:CallTransferredEvent` | Call is transferred |
| `xsi:CallSubscriptionEvent` | Subscription state change |
| `xsi:ChannelTerminatedEvent` | Channel was closed (not queued — handled internally) |

<!-- NEEDS VERIFICATION: confirm the complete event type list from the BroadWorks XSI schema -->

### Event Payload Structure

Events are delivered as Python OrderedDicts (parsed from XML via `xmltodict`). The general structure:

```python
{
    'xsi:Event': {
        '@xsi1:type': 'xsi:CallOriginatedEvent',   # Event type
        'xsi:eventID': '12345-abcde',               # Unique event ID (used for ACK)
        'xsi:sequenceNumber': '42',                 # Sequence number
        'xsi:userId': 'user@domain.com',            # User the event is for
        'xsi:externalApplicationId': 'app-uuid',    # Your application ID
        'xsi:subscriptionId': 'sub-uuid',           # Subscription that matched
        'xsi:channelId': 'channel-uuid',            # Channel it arrived on
        'xsi:eventData': {
            '@xsi1:type': 'xsi:CallEvent',          # Data type
            'xsi:call': {
                'xsi:callId': 'callhalf-123',
                'xsi:extTrackingId': 'tracking-456',
                'xsi:personality': 'Originator',     # or 'Terminator'
                'xsi:state': 'Alerting',             # Call state
                'xsi:remoteParty': {
                    'xsi:address': {
                        'xsi:type': 'E164',
                        '#text': '+17192662837'
                    },
                    'xsi:callType': 'Network'
                },
                'xsi:startTime': '1710000000000',
                'xsi:answerTime': '1710000005000',
                # ... additional fields vary by event type
            }
        }
    }
}
```

<!-- NEEDS VERIFICATION: exact payload field names vary by event type and BroadWorks version — use the actual event data for field discovery -->

### Event Processing Best Practices

**Queue sizing:** A busy org can generate hundreds of events per second. Set `maxsize` large enough to absorb bursts but not so large it consumes all memory. Start with 500-1000 for a small org.

**Threaded consumer:** For production, process the queue in its own thread:

```python
import queue
import threading
import wxcadm

def event_processor(q):
    """Process events in a dedicated thread."""
    while True:
        try:
            event = q.get(timeout=5)
        except queue.Empty:
            continue

        event_data = event['xsi:Event']
        event_type = event_data['xsi:eventData']['@xsi1:type']
        user_id = event_data.get('xsi:userId', 'unknown')

        if event_type == 'xsi:CallOriginatedEvent':
            handle_new_call(event_data)
        elif event_type == 'xsi:CallAnsweredEvent':
            handle_answered(event_data)
        elif event_type == 'xsi:CallReleasedEvent':
            handle_released(event_data)
        # ... etc

        q.task_done()

# Setup
webex = wxcadm.Webex(access_token, get_xsi=True)
events = wxcadm.XSIEvents(webex.org)
events_queue = queue.Queue(maxsize=1000)
channel = events.open_channel(events_queue)
channel.subscribe(["Advanced Call"])

# Start processor thread
processor = threading.Thread(target=event_processor, args=(events_queue,), daemon=True)
processor.start()

# Keep main thread alive
import time
while True:
    time.sleep(60)
```

---

## Channel Management

### Channel Lifecycle

When `open_channel()` is called, wxcadm:

1. Does a DNS SRV lookup: `_xsi-client._tcp.{xsi_domain}`
2. Opens one `XSIEventsChannel` per SRV record (per XSP server)
3. Each channel sends an XML `<Channel>` POST to `{endpoint}/v2.0/channel` with:
   - `channelSetId` — groups channels together
   - `applicationId` — unique per XSIEvents instance
   - `priority=1`, `weight=50`, `expires=7200` (2 hours)
4. The POST is a **streaming request** — the connection stays open and events flow through it
5. A heartbeat thread sends `PUT .../channel/{id}/heartbeat` every 15 seconds
6. Channels auto-refresh every hour (before the 7200s expiry)

### Channel Failure Recovery

wxcadm has built-in resilience:

- If a channel fails to establish (no response within 40 seconds / 20 retries), it is marked inactive and a restart is attempted
- If a heartbeat gets HTTP 404 or 401, the channel is marked inactive and restarted
- If the streaming connection drops, the channel loop ends and triggers `restart_failed_channel()` (with a 60-second backoff)
- `restart_failed_channel()` creates a new channel to the same endpoint and sends a DELETE on the old one

### Checking Active Channels

```python
active = channel.active_channels  # List of XSIEventsChannel with active=True
```

### Closing Everything

```python
channel.close()  # Deletes all subscriptions, then deletes all channels
```

---

## Subscription Management

### Subscribe

```python
# Org-wide
subscription = channel.subscribe(["Advanced Call"])

# Per-user
subscription = channel.subscribe(["Advanced Call"], person=some_person)
```

Returns an `XSIEventsSubscription` instance (or `False` if subscription fails). The subscription has:
- `subscription.id` — server-assigned subscription ID
- `subscription.active` — boolean
- `subscription.event_package` — what was subscribed to

### Unsubscribe

```python
# Unsubscribe a specific subscription
channel.unsubscribe(subscription.id)

# Unsubscribe all
channel.unsubscribe("all")
```

### Subscription Refresh

Subscriptions auto-refresh every hour (checked during heartbeat processing). The refresh sends a PUT with a new 7200-second expiry.

---

## XSICallQueue: Call Queue Call Control

When monitoring XSI Events for a Call Queue, incoming calls have a `targetId` identifying the queue. Use `XSICallQueue` to control those calls:

```python
# Create a Call Queue controller from an event's targetId
call_queue = wxcadm.XSICallQueue(
    call_queue_id="queue-id-from-event",
    org=webex.org
)

# Attach to a specific call (from event's callId)
call = call_queue.attach_call(call_id="call-id-from-event")

# Now you can control the call
call.transfer("2345")   # Transfer to an agent
call.hangup()            # Release the call
```

Call Queue calls support basic call control (transfer, hangup) but not all operations available to regular user calls. <!-- NEEDS VERIFICATION: confirm exact subset of call controls available for Call Queue calls -->

---

## Monitoring Features (REST API)

Separate from XSI-Events, wxcadm provides a `MonitoringList` class for managing BLF (Busy Lamp Field) monitoring configurations through the Webex REST API:

```python
# Get a person's monitoring list
monitoring = person.monitoring  # Returns MonitoringList

# Monitored elements (resolved to Person, Workspace, VirtualLine, or CallParkExtension)
for element in monitoring.monitored_elements:
    print(element)

# Add a monitored element
monitoring.add(another_person)

# Remove a monitored element
monitoring.remove(another_person)

# Copy monitoring config to another user
monitoring.copy_to(other_person)

# Copy from another user
monitoring.copy_from(source_person)

# Replace entire monitoring config
monitoring.replace(other_monitoring_list)

# Clear all monitoring
monitoring.clear()
```

The `MonitoringList` resolves monitored element IDs to actual wxcadm objects (Person, Workspace, VirtualLine, CallParkExtension) automatically.

**Note:** This is the REST API `MonitoringList` class, not the XSI `monitoring` property. The XSI `person.xsi.monitoring` property reads BLF settings directly from the call control platform via XSI.

---

## Use Cases

### 1. Real-time Agent Dashboard

Monitor all call events org-wide, track which agents are on calls, display live call states:

```python
import queue
import wxcadm

webex = wxcadm.Webex(token, get_xsi=True)
events = wxcadm.XSIEvents(webex.org)
q = queue.Queue(maxsize=1000)
channel = events.open_channel(q)
channel.subscribe(["Advanced Call"])

active_calls = {}   # Track calls by user

while True:
    event = q.get()
    evt = event['xsi:Event']
    evt_type = evt['xsi:eventData']['@xsi1:type']
    user = evt.get('xsi:userId', '')

    if 'Originated' in evt_type or 'Received' in evt_type:
        active_calls[user] = evt['xsi:eventData']
    elif 'Released' in evt_type:
        active_calls.pop(user, None)

    # Push active_calls to your dashboard via WebSocket, SSE, etc.
    update_dashboard(active_calls)
```

### 2. CRM Screen Pop

When a call comes in, look up the caller in your CRM and pop the record:

```python
while True:
    event = q.get()
    evt = event['xsi:Event']
    if evt['xsi:eventData']['@xsi1:type'] == 'xsi:CallReceivedEvent':
        caller = evt['xsi:eventData']['xsi:call']['xsi:remoteParty']
        phone = caller['xsi:address'].get('#text', '')
        agent = evt.get('xsi:userId', '')
        crm_record = lookup_crm(phone)
        send_screen_pop(agent, crm_record)
```

### 3. Call Center Queue Management

Monitor Call Queue events and programmatically route calls:

```python
while True:
    event = q.get()
    evt = event['xsi:Event']
    target_id = evt.get('xsi:targetId', '')

    if is_call_queue(target_id):
        call_id = evt['xsi:eventData']['xsi:call']['xsi:callId']
        cq = wxcadm.XSICallQueue(target_id, webex.org)
        call = cq.attach_call(call_id)

        # Route based on business logic
        best_agent = find_available_agent()
        call.transfer(best_agent.extension)
```

### 4. Compliance / Call Logging

Capture every call event for audit:

```python
import json
from datetime import datetime

while True:
    event = q.get()
    evt = event['xsi:Event']
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': evt['xsi:eventData']['@xsi1:type'],
        'user': evt.get('xsi:userId', ''),
        'event_id': evt.get('xsi:eventID', ''),
        'raw': json.dumps(event, default=str)
    }
    write_to_audit_log(log_entry)
```

### 5. Click-to-Dial Integration

Embed calling into any web app or tool:

```python
def click_to_dial(agent_email: str, destination: str):
    person = webex.org.get_person_by_email(agent_email)
    person.start_xsi()
    call = person.xsi.new_call(address=destination)
    return call.id  # Return call ID for tracking/control
```

### 6. Automated Call Recording Control

Start/stop recording based on business rules:

```python
while True:
    event = q.get()
    evt = event['xsi:Event']
    if evt['xsi:eventData']['@xsi1:type'] == 'xsi:CallAnsweredEvent':
        user_id = evt.get('xsi:userId', '')
        call_id = evt['xsi:eventData']['xsi:call']['xsi:callId']

        if should_record(user_id):
            person = webex.org.get_person_by_email(user_id)
            person.start_xsi()
            call = person.xsi.attach_call(call_id)
            call.recording("start")
```

---

## Class Reference Summary

| Class | Purpose | Key Methods/Properties |
|-------|---------|----------------------|
| `XSI` | Per-user XSI session | `new_call()`, `answer_call()`, `calls`, `profile`, `directory()`, `get_services()`, `attach_call()` |
| `XSIEvents` | Org-level event manager | `open_channel(queue)` |
| `XSIEventsChannelSet` | Channel group + subscriptions | `subscribe()`, `unsubscribe()`, `close()`, `active_channels` |
| `XSIEventsChannel` | Single streaming connection | Managed automatically; `active`, `delete()` |
| `XSIEventsSubscription` | Event subscription | `id`, `active`, `delete()` |
| `XSICallQueue` | Call Queue call control | `attach_call(call_id)` |
| `Call` | Individual call control | `originate()`, `hold()`, `resume()`, `transfer()`, `finish_transfer()`, `conference()`, `park()`, `hangup()`, `status`, `recording()`, `send_dtmf()`, `exec_push()`, `answer()`, `reconnect()` |
| `Conference` | Multi-party conference | `mute(call_id)`, `deaf(call_id)` |
| `XSIResponse` | API response wrapper | `success`, `summary`, `raw_response`, truthy/falsy |
| `FeatureAccessCode` | FAC definition | `feature`, `code`, `alternate_code` |
| `MonitoringList` | BLF monitoring config (REST) | `add()`, `remove()`, `replace()`, `copy_to()`, `copy_from()`, `clear()` |

---

## Gotchas & Tips

1. **XSI must be enabled by Cisco TAC** before any of this works. There is no self-service toggle.

2. **Events volume is high.** A single call generates 6 events. A busy org with 100 concurrent calls can produce hundreds of events per second. Size your queue and process events quickly.

3. **Events are XML, not JSON.** wxcadm parses them with `xmltodict` into OrderedDicts. The `$` key holds text content (e.g., `config['code']['$']`). The `@` prefix denotes attributes.

4. **ChannelTerminatedEvent is NOT queued.** wxcadm filters this out before putting events in your queue, since it's an infrastructure event, not a business event.

5. **Channel auto-recovery is built in** but not instant. A failed channel waits 60 seconds before restarting. During that window, events for that XSP are lost.

6. **Heartbeats every 15 seconds.** If a heartbeat fails, the retry interval drops to 10 seconds. If it gets a 404/401, the channel restarts.

7. **7200-second expiry.** Both channels and subscriptions expire after 2 hours. wxcadm auto-refreshes them hourly.

8. **XSI profile vs. REST profile.** The XSI profile comes from the call control back-end and may differ from the REST API profile (which comes from Common Identity / Active Directory).

9. **Call IDs are transient.** They only exist while the call is active. Use `attach_call()` promptly after receiving an event.

10. **The `recording()` method has a bug.** The `"pause"` action case is unreachable because it shares an `elif action.lower() == "resume"` condition with the actual resume case. If you need to pause recording, call the XSI API directly. <!-- NEEDS VERIFICATION -->

11. **SRV lookup dependency.** wxcadm uses the `srvlookup` library to find XSP servers. If DNS SRV records are unreachable, channel creation will fail.

12. **Session cookies.** Each channel uses a `requests.Session` and preserves cookies from the initial streaming POST. This ensures subsequent heartbeats and ACKs hit the correct server instance behind load balancers.
