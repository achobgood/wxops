# Meetings Infrastructure: Video Mesh, Participants, and Invitees

Reference for Webex Meetings infrastructure management. Covers the 43 commands across 3 CLI groups that an IT admin uses to monitor Video Mesh on-premises media processing, manage meeting participants in real time, and configure meeting invitees pre-meeting. Sourced from the Webex Meetings API (OpenAPI spec: `specs/webex-meetings.json`).

## Sources

- OpenAPI spec: `specs/webex-meetings.json`
- [developer.webex.com Video Mesh APIs](https://developer.webex.com/docs/api/v1/video-mesh)
- [developer.webex.com Meeting Participants APIs](https://developer.webex.com/docs/api/v1/meeting-participants)
- [developer.webex.com Meeting Invitees APIs](https://developer.webex.com/docs/api/v1/meeting-invitees)

---

## Table of Contents

1. [Meetings Infrastructure Overview](#1-meetings-infrastructure-overview)
2. [Video Mesh: Clusters and Nodes](#2-video-mesh-clusters-and-nodes)
3. [Video Mesh: Availability](#3-video-mesh-availability)
4. [Video Mesh: Utilization and Overflow](#4-video-mesh-utilization-and-overflow)
5. [Video Mesh: Call Redirects and Client Distribution](#5-video-mesh-call-redirects-and-client-distribution)
6. [Video Mesh: Test Results](#6-video-mesh-test-results)
7. [Video Mesh: On-Demand Tests](#7-video-mesh-on-demand-tests)
8. [Video Mesh: Event Thresholds](#8-video-mesh-event-thresholds)
9. [Meeting Participants](#9-meeting-participants)
10. [Meeting Invitees](#10-meeting-invitees)
11. [Raw HTTP Endpoints](#11-raw-http-endpoints)
12. [Gotchas](#12-gotchas)
13. [See Also](#13-see-also)

---

## 1. Meetings Infrastructure Overview

This doc covers three distinct API surfaces that support the Webex Meetings infrastructure:

- **Video Mesh** (30 commands) -- on-premises media processing nodes that keep meeting traffic local. The API is read-only for monitoring and analytics, plus event threshold configuration. Cluster and node provisioning is done through the Webex Control Hub UI, not via API.
- **Meeting Participants** (7 commands) -- real-time management of who is in a meeting. List, query, admit from lobby, mute/unmute, expel, and call out to SIP devices.
- **Meeting Invitees** (6 commands) -- pre-meeting management of who is invited. CRUD operations on the invitation list before the meeting starts.

```
Video Mesh (on-prem media nodes)
  ├── Clusters (grouping of nodes)
  │    ├── Availability, Utilization, Overflow
  │    ├── Call Redirects, Client Distribution
  │    └── Test Results (network, reachability, media health)
  ├── Nodes (individual media processing servers)
  │    └── Availability, Test Results
  └── Event Thresholds (alert configuration)

Meeting Lifecycle
  ├── Invitees (pre-meeting: who to invite)
  └── Participants (in-meeting: who joined, lobby, mute, expel, SIP callout)
```

**CLI groups in this doc:**

| CLI Group | Resource | Commands |
|-----------|----------|---------|
| `video-mesh` | Video Mesh clusters, nodes, analytics | 30 |
| `meeting-participants` | Meeting participants | 7 |
| `meeting-invitees` | Meeting invitees | 6 |

---

## 2. Video Mesh: Clusters and Nodes

**CLI group:** `video-mesh`
**API base:** `https://webexapis.com/v1/videoMesh`

Video Mesh deploys on-premises media processing nodes that keep real-time media (audio, video, content sharing) local to reduce bandwidth to the cloud. Clusters group multiple nodes for redundancy and load balancing. All cluster and node management (provisioning, registration, decommissioning) is done through the Webex Control Hub -- the API provides monitoring and analytics only.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List clusters | `wxcli video-mesh list-clusters-video-mesh` | GET /videoMesh/clusters | List all Video Mesh clusters in the org |
| Show cluster | `wxcli video-mesh show --cluster-id ID` | GET /videoMesh/clusters/{clusterId} | Get details for a single cluster |

### Key Parameters

#### `list-clusters-video-mesh`

| Option | Description |
|--------|-------------|
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

#### `show`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--cluster-id ID` | Yes | The unique Video Mesh Cluster ID |
| `--org-id ORG_ID` | No | Organization ID (auto-injected from config) |

### Raw HTTP

```python
import requests

BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# List all Video Mesh clusters
resp = requests.get(f"{BASE}/videoMesh/clusters", headers=headers, params={"orgId": org_id})
clusters = resp.json().get("items", [])
# Each item: {"clusterId", "clusterName", "releaseChannel", ...}

# Get a single cluster
resp = requests.get(f"{BASE}/videoMesh/clusters/{cluster_id}", headers=headers, params={"orgId": org_id})
cluster = resp.json()
```

---

## 3. Video Mesh: Availability

Monitor the availability of clusters and individual nodes over time.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List cluster availability | `wxcli video-mesh list-availability-clusters` | GET /videoMesh/clusters/availability | Availability for all clusters in the org |
| Show cluster availability | `wxcli video-mesh show-availability-clusters --cluster-id ID` | GET /videoMesh/clusters/availability/{clusterId} | Availability for a single cluster |
| List node availability | `wxcli video-mesh list-availability-nodes` | GET /videoMesh/nodes/availability | Availability for all nodes in the org |
| Show node availability | `wxcli video-mesh show-availability-nodes --node-id ID` | GET /videoMesh/nodes/availability/{nodeId} | Availability for a single node |

### Key Parameters (shared across availability commands)

| Option | Description |
|--------|-------------|
| `--from DATETIME` | Start of time range (ISO 8601). Required for analytics queries. |
| `--to DATETIME` | End of time range (ISO 8601). Required for analytics queries. |
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List cluster availability over a time range
params = {
    "orgId": org_id,
    "from": "2026-03-01T00:00:00Z",
    "to": "2026-03-28T00:00:00Z"
}
resp = requests.get(f"{BASE}/videoMesh/clusters/availability", headers=headers, params=params)
data = resp.json().get("items", [])
# Each item contains: orgId, from, to, items[{clusterName, clusterId, availabilitySegments[...]}]

# Get availability for a single node
resp = requests.get(f"{BASE}/videoMesh/nodes/availability/{node_id}", headers=headers, params=params)
node_avail = resp.json()
```

---

## 4. Video Mesh: Utilization and Overflow

Monitor resource utilization across clusters and track when calls overflow to the cloud.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List utilization | `wxcli video-mesh list-utilization-video-mesh` | GET /videoMesh/utilization | Utilization for all clusters in the org |
| Cluster utilization | `wxcli video-mesh list-utilization-clusters` | GET /videoMesh/clusters/utilization | Detailed utilization for specific cluster |
| Cloud overflow | `wxcli video-mesh list-cloud-overflow` | GET /videoMesh/cloudOverflow | Overflow to cloud details |

### Key Parameters (shared across utilization and overflow commands)

| Option | Description |
|--------|-------------|
| `--from DATETIME` | Start of time range (ISO 8601). Required. |
| `--to DATETIME` | End of time range (ISO 8601). Required. |
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

#### `list-utilization-clusters` (additional)

| Option | Description |
|--------|-------------|
| `--cluster-id ID` | The unique Video Mesh Cluster ID |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List utilization across all clusters
params = {"orgId": org_id, "from": "2026-03-01T00:00:00Z", "to": "2026-03-28T00:00:00Z"}
resp = requests.get(f"{BASE}/videoMesh/utilization", headers=headers, params=params)
utilization = resp.json().get("items", [])
# Response contains: timestamp, clusters[{utilizationMetrics: {avgCpu, activeCalls, activePrivateCalls, ...}}]

# Cloud overflow details
resp = requests.get(f"{BASE}/videoMesh/cloudOverflow", headers=headers, params=params)
overflow = resp.json().get("items", [])
# Response contains: timestamp, overflowDetails[{overflowReason, overflowCount, possibleRemediation}]
```

---

## 5. Video Mesh: Call Redirects and Client Distribution

Track call redirect patterns across clusters and analyze client type distribution.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List call redirects | `wxcli video-mesh list-call-redirects-video-mesh` | GET /videoMesh/callRedirects | Redirect details for all clusters |
| Cluster call redirects | `wxcli video-mesh list-call-redirects-clusters` | GET /videoMesh/clusters/callRedirects | Redirect details for a specific cluster |
| Client type distribution | `wxcli video-mesh list` | GET /videoMesh/clientTypeDistribution | Client types across all clusters |
| Cluster client distribution | `wxcli video-mesh list-clusters-client-type-distribution` | GET /videoMesh/clientTypeDistribution/clusters | Client types for a specific cluster |

### Key Parameters (shared across these commands)

| Option | Description |
|--------|-------------|
| `--from DATETIME` | Start of time range (ISO 8601). Required. |
| `--to DATETIME` | End of time range (ISO 8601). Required. |
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

#### Cluster-specific commands (additional)

| Option | Description |
|--------|-------------|
| `--cluster-id ID` | The unique Video Mesh Cluster ID |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List call redirects across all clusters
params = {"orgId": org_id, "from": "2026-03-01T00:00:00Z", "to": "2026-03-28T00:00:00Z"}
resp = requests.get(f"{BASE}/videoMesh/callRedirects", headers=headers, params=params)
redirects = resp.json().get("items", [])

# Get client type distribution for a specific cluster
params["clusterId"] = cluster_id
resp = requests.get(f"{BASE}/videoMesh/clientTypeDistribution/clusters", headers=headers, params=params)
distribution = resp.json().get("items", [])
```

---

## 6. Video Mesh: Test Results

Periodic and on-demand test results for network connectivity, reachability, and media health monitoring across clusters and nodes. Test results are available at three levels: org-wide, per-cluster, and per-node.

### Commands

**Network Tests:**

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List network tests | `wxcli video-mesh list-network-test` | GET /videoMesh/testResults/networkTest | Network test results for all clusters |
| Cluster network tests | `wxcli video-mesh list-clusters-network-test` | GET /videoMesh/testResults/networkTest/clusters | Network test results for a cluster |
| Node network tests | `wxcli video-mesh list-nodes-network-test` | GET /videoMesh/testResults/networkTest/nodes | Network test results for a node |

**Reachability Tests (V2):**

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List reachability tests | `wxcli video-mesh list-reachability-test` | GET /videoMesh/testResults/reachabilityTest | Reachability results for all clusters |
| Cluster reachability tests | `wxcli video-mesh list-clusters-reachability-test` | GET /videoMesh/testResults/reachabilityTest/clusters | Reachability results for a cluster |
| Node reachability tests | `wxcli video-mesh list-nodes-reachability-test` | GET /videoMesh/testResults/reachabilityTest/nodes | Reachability results for a node |

**Media Health Monitor Tests (V2):**

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List media health tests | `wxcli video-mesh list-media-health-monitor-test` | GET /videoMesh/testResults/mediaHealthMonitorTest | Media health results for all clusters |
| Cluster media health tests | `wxcli video-mesh list-clusters-media-health-monitor-test` | GET /videoMesh/testResults/mediaHealthMonitorTest/clusters | Media health results for a cluster |
| Node media health tests | `wxcli video-mesh list-nodes-media-health-monitor-test` | GET /videoMesh/testResults/mediaHealthMonitorTest/nodes | Media health results for a node |

### Key Parameters

#### Org-wide test commands

| Option | Description |
|--------|-------------|
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

#### Cluster-level test commands (additional)

| Option | Description |
|--------|-------------|
| `--cluster-id ID` | The unique Video Mesh Cluster ID |

#### Node-level test commands (additional)

| Option | Description |
|--------|-------------|
| `--node-id ID` | The unique Video Mesh Node ID |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List network test results for the org
resp = requests.get(f"{BASE}/videoMesh/testResults/networkTest", headers=headers,
                    params={"orgId": org_id})
results = resp.json().get("items", [])

# Get reachability test results for a specific cluster
resp = requests.get(f"{BASE}/videoMesh/testResults/reachabilityTest/clusters", headers=headers,
                    params={"orgId": org_id, "clusterId": cluster_id})
reach_results = resp.json().get("items", [])

# Get media health test results for a specific node
resp = requests.get(f"{BASE}/videoMesh/testResults/mediaHealthMonitorTest/nodes", headers=headers,
                    params={"orgId": org_id, "nodeId": node_id})
health_results = resp.json().get("items", [])
```

### V2 Changes (Reachability and Media Health)

The V2 endpoints for reachability and media health monitoring include two improvements over V1:
1. On-demand test results are returned alongside periodic test results.
2. The destination IP address of the destination cluster is now included in the JSON response.

---

## 7. Video Mesh: On-Demand Tests

Trigger diagnostic tests on specific nodes or clusters and retrieve results. On-demand tests are asynchronous -- you trigger them, then poll for status and results.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Trigger node test | `wxcli video-mesh create --node-id ID` | POST /videoMesh/triggerTest/nodes/{nodeId} | Trigger on-demand test for a node |
| Trigger cluster test | `wxcli video-mesh create-clusters --cluster-id ID` | POST /videoMesh/triggerTest/clusters/{clusterId} | Trigger on-demand test for a cluster |
| Get test results | `wxcli video-mesh list-test-results` | GET /videoMesh/testResults | Get triggered test results |
| Get test status | `wxcli video-mesh list-test-status` | GET /videoMesh/testStatus | Get triggered test status |

### Key Parameters

#### `create` (trigger node test)

| Option | Required | Description |
|--------|:--------:|-------------|
| `--node-id ID` | Yes | Unique ID of the Video Mesh node to test |
| `--org-id ORG_ID` | No | Organization ID (auto-injected from config) |

#### `create-clusters` (trigger cluster test)

| Option | Required | Description |
|--------|:--------:|-------------|
| `--cluster-id ID` | Yes | Unique ID of the Video Mesh cluster to test |
| `--org-id ORG_ID` | No | Organization ID (auto-injected from config) |

#### `list-test-results` and `list-test-status`

| Option | Description |
|--------|-------------|
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

### Workflow: Run an On-Demand Test

```bash
# 1. Trigger an on-demand test for a node
wxcli video-mesh create --node-id NODE_ID

# 2. Poll test status until complete
wxcli video-mesh list-test-status --output json

# 3. Get the results once complete
wxcli video-mesh list-test-results --output json
```

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Trigger on-demand test for a node
resp = requests.post(f"{BASE}/videoMesh/triggerTest/nodes/{node_id}", headers=headers,
                     params={"orgId": org_id})

# Trigger on-demand test for a cluster
resp = requests.post(f"{BASE}/videoMesh/triggerTest/clusters/{cluster_id}", headers=headers,
                     params={"orgId": org_id})

# Check test status
resp = requests.get(f"{BASE}/videoMesh/testStatus", headers=headers, params={"orgId": org_id})
status = resp.json()

# Get test results
resp = requests.get(f"{BASE}/videoMesh/testResults", headers=headers, params={"orgId": org_id})
results = resp.json()
```

---

## 8. Video Mesh: Event Thresholds

Configure alerting thresholds for Video Mesh events. These thresholds determine when notifications are triggered for cluster and node health events.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List thresholds | `wxcli video-mesh list-event-thresholds` | GET /videoMesh/eventThresholds | List all event threshold configurations |
| Show threshold | `wxcli video-mesh show-event-thresholds --event-threshold-id ID` | GET /videoMesh/eventThresholds/{eventThresholdId} | Get a specific threshold config |
| Update thresholds | `wxcli video-mesh update --json-body JSON` | PATCH /videoMesh/eventThresholds | Update threshold values (partial update) |
| Reset thresholds | `wxcli video-mesh create-reset` | POST /videoMesh/eventThresholds/reset | Reset all thresholds to defaults |

### Key Parameters

#### `list-event-thresholds`

| Option | Description |
|--------|-------------|
| `--org-id ORG_ID` | Organization ID (auto-injected from config) |
| `--output table\|json` | Output format (default: table) |

#### `show-event-thresholds`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--event-threshold-id ID` | Yes | The unique event threshold ID |
| `--org-id ORG_ID` | No | Organization ID (auto-injected from config) |

#### `update` (PATCH)

This command requires `--json-body` because the request body contains nested objects:

```bash
wxcli video-mesh update --json-body '{
  "eventThresholds": [
    {
      "eventThresholdId": "THRESHOLD_ID_1",
      "thresholdConfig": {
        "minThreshold": 80
      }
    }
  ]
}'
```

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List all event thresholds
resp = requests.get(f"{BASE}/videoMesh/eventThresholds", headers=headers, params={"orgId": org_id})
thresholds = resp.json()
# Response: {orgId, eventThresholds: [{entityId, eventScope, eventName, eventThresholdId, thresholdConfig: {minThreshold, defaultMinThreshold}}]}

# Update a threshold (PATCH - partial update)
body = {
    "eventThresholds": [
        {
            "eventThresholdId": threshold_id,
            "thresholdConfig": {"minThreshold": 80}
        }
    ]
}
resp = requests.patch(f"{BASE}/videoMesh/eventThresholds", headers=headers, json=body,
                      params={"orgId": org_id})
result = resp.json()
# Response includes failedEventThresholdIds array for any that failed to update

# Reset all thresholds to defaults
resp = requests.post(f"{BASE}/videoMesh/eventThresholds/reset", headers=headers,
                     params={"orgId": org_id})
```

### Threshold Response Fields

| Field | Description |
|-------|-------------|
| `eventThresholdId` | Unique identifier for the threshold |
| `entityId` | The entity (cluster/node) this threshold applies to |
| `eventScope` | Scope of the event (e.g., cluster-level, node-level) |
| `eventName` | Name of the monitored event |
| `thresholdConfig.minThreshold` | Current threshold value |
| `thresholdConfig.defaultMinThreshold` | Factory default threshold value |

---

## 9. Meeting Participants

**CLI group:** `meeting-participants`
**API base:** `https://webexapis.com/v1/meetingParticipants`

Manage participants during a live meeting or query historical participant data from ended meetings. This API supports listing who joined, admitting from the lobby, muting/unmuting, expelling, and calling out to SIP devices to add them to the meeting.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List participants | `wxcli meeting-participants list --meeting-id ID` | GET /meetingParticipants | List participants for a meeting |
| Show participant | `wxcli meeting-participants show --participant-id ID` | GET /meetingParticipants/{participantId} | Get participant details |
| Update participant | `wxcli meeting-participants update --participant-id ID` | PUT /meetingParticipants/{participantId} | Mute, unmute, admit, or expel a participant |
| Query by email | `wxcli meeting-participants create --json-body JSON` | POST /meetingParticipants/query | Query participants by email addresses |
| Admit participants | `wxcli meeting-participants create-admit --json-body JSON` | POST /meetingParticipants/admit | Admit participants from the lobby |
| Call out SIP | `wxcli meeting-participants create-callout --json-body JSON` | POST /meetingParticipants/callout | Dial a SIP URI to add to meeting |
| Cancel callout | `wxcli meeting-participants create-cancel-callout --json-body JSON` | POST /meetingParticipants/cancelCallout | Cancel a pending SIP callout |

### Key Parameters

#### `list`

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | The unique meeting identifier. Personal room meeting IDs are not supported. |
| `--breakout-session-id ID` | Filter to participants who joined a specific breakout session (ended meetings only) |
| `--meeting-start-time-from DATETIME` | Filter meetings starting after this time (ISO 8601, exclusive). Default: 1 month before `meetingStartTimeTo`. |
| `--meeting-start-time-to DATETIME` | Filter meetings starting before this time (ISO 8601, exclusive) |
| `--host-email EMAIL` | Admin-only: specify a host's email to list their meeting's participants |
| `--join-time-from DATETIME` | Participants who joined after this time (ISO 8601, inclusive). Default: 7 days before `joinTimeTo`. |
| `--join-time-to DATETIME` | Participants who joined before this time (ISO 8601, exclusive). Interval between `joinTimeFrom` and `joinTimeTo` must be within 90 days. |
| `--max N` | Max participants per page, up to 100 |
| `--output table\|json` | Output format (default: table) |

#### `update` (PUT)

| Option | Description |
|--------|-------------|
| `--participant-id ID` | The participant to update (path parameter) |
| `--muted true\|false` | Mute or unmute the participant |
| `--admit true\|false` | Admit the participant from the lobby |
| `--expel true\|false` | Remove the participant from the meeting |

#### `create` (Query by Email -- POST)

This command uses `--json-body` because the request body contains an array of emails:

```bash
wxcli meeting-participants create --meeting-id MEETING_ID --json-body '{
  "emails": ["user1@example.com", "user2@example.com"],
  "joinTimeFrom": "2026-03-01T00:00:00Z",
  "joinTimeTo": "2026-03-28T00:00:00Z"
}'
```

#### `create-admit` (Admit from Lobby -- POST)

Admits up to 100 participants at once. Each `participantId` must share the same meeting prefix as `meetingId`.

```bash
wxcli meeting-participants create-admit --json-body '{
  "items": [
    {"participantId": "PARTICIPANT_ID_1"},
    {"participantId": "PARTICIPANT_ID_2", "breakoutSessionId": "SESSION_ID"}
  ]
}'
```

#### `create-callout` (SIP Callout -- POST)

Dials a SIP address or phone number to add them to the meeting. Useful for bringing room devices into a meeting.

```bash
wxcli meeting-participants create-callout --json-body '{
  "meetingId": "MEETING_ID",
  "address": "roomdevice@example.com",
  "addressType": "sipAddress",
  "displayName": "Conference Room A"
}'
```

| Body Field | Description |
|------------|-------------|
| `meetingId` | The meeting to add the participant to |
| `meetingNumber` | Alternative: use meeting number instead of ID |
| `address` | SIP URI or phone number to dial |
| `addressType` | `sipAddress` (default) |
| `displayName` | Display name for the called participant |
| `invitationCorrelationId` | Optional correlation ID for tracking |

#### `create-cancel-callout` (Cancel Pending Callout -- POST)

```bash
wxcli meeting-participants create-cancel-callout --json-body '{
  "participantId": "PARTICIPANT_ID"
}'
```

### Participant Response Fields

| Field | Description |
|-------|-------------|
| `id` | Unique participant identifier |
| `meetingId` | Meeting the participant is in |
| `hostEmail` | Email of the meeting host |
| `displayName` | Participant display name |
| `email` | Participant email |
| `orgId` | Participant's organization ID |
| `state` | Current state: `lobby`, `joined`, `end` |
| `muted` | Whether participant is muted |
| `host` | Whether participant is the host |
| `coHost` | Whether participant is a co-host |
| `invitee` | Whether participant was an invitee |
| `video` | Video state: `on`, `off` |
| `devices` | Array of devices used: `{joinedTime, leftTime, deviceType, audioType, callType, phoneNumber, correlationId, durationSecond}` |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List participants for a meeting
params = {"meetingId": meeting_id, "max": 50}
resp = requests.get(f"{BASE}/meetingParticipants", headers=headers, params=params)
participants = resp.json().get("items", [])

# Get a specific participant
resp = requests.get(f"{BASE}/meetingParticipants/{participant_id}", headers=headers)
participant = resp.json()

# Mute a participant
body = {"muted": True}
resp = requests.put(f"{BASE}/meetingParticipants/{participant_id}", headers=headers, json=body)

# Expel a participant
body = {"expel": True}
resp = requests.put(f"{BASE}/meetingParticipants/{participant_id}", headers=headers, json=body)

# Admit participants from lobby
body = {"items": [{"participantId": p_id} for p_id in participant_ids]}
resp = requests.post(f"{BASE}/meetingParticipants/admit", headers=headers, json=body)
# Returns 204 No Content on success

# Call out to a SIP device
body = {
    "meetingId": meeting_id,
    "address": "roomdevice@example.com",
    "addressType": "sipAddress",
    "displayName": "Conference Room A"
}
resp = requests.post(f"{BASE}/meetingParticipants/callout", headers=headers, json=body)
# Response: {participantId, address, addressType, state: "pending", meetingId, ...}

# Cancel a pending callout
body = {"participantId": participant_id}
resp = requests.post(f"{BASE}/meetingParticipants/cancelCallout", headers=headers, json=body)
# Returns 204 No Content on success
```

---

## 10. Meeting Invitees

**CLI group:** `meeting-invitees`
**API base:** `https://webexapis.com/v1/meetingInvitees`

Manage who is invited to a meeting before it starts. Invitees are the pre-meeting invitation list -- distinct from participants, who are the people who actually join the meeting. Invitees can be regular attendees, co-hosts, or panelists (for webinars).

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List invitees | `wxcli meeting-invitees list --meeting-id ID` | GET /meetingInvitees | List invitees for a meeting |
| Create invitee | `wxcli meeting-invitees create --meeting-id ID --email user@example.com` | POST /meetingInvitees | Invite a person to a meeting |
| Bulk insert | `wxcli meeting-invitees create-bulk-insert --json-body JSON` | POST /meetingInvitees/bulkInsert | Invite multiple people at once |
| Show invitee | `wxcli meeting-invitees show --meeting-invitee-id ID` | GET /meetingInvitees/{meetingInviteeId} | Get invitee details |
| Update invitee | `wxcli meeting-invitees update --meeting-invitee-id ID` | PUT /meetingInvitees/{meetingInviteeId} | Update invitee role (co-host, panelist) |
| Delete invitee | `wxcli meeting-invitees delete --meeting-invitee-id ID --force` | DELETE /meetingInvitees/{meetingInviteeId} | Remove an invitee |

### Key Parameters

#### `list`

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | The meeting to list invitees for. Supports meeting series, scheduled meetings, and ended/ongoing instances. Personal room meeting IDs are not supported. |
| `--host-email EMAIL` | Admin-only: specify a host's email to list their meeting's invitees |
| `--panelist true\|false\|null` | Webinar filter: `true` = panelists only, `false` = attendees only, `null` (default) = both |
| `--max N` | Max invitees per page, up to 100 |
| `--output table\|json` | Output format (default: table) |

#### `create`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--meeting-id ID` | Yes | The meeting to invite the person to |
| `--email EMAIL` | Yes | Email address of the invitee |
| `--display-name TEXT` | No | Display name for the invitee |
| `--co-host true\|false` | No | Grant co-host role |
| `--panelist true\|false` | No | Set as panelist (webinars only) |
| `--send-email true\|false` | No | Send invitation email (default: `true`) |
| `--host-email EMAIL` | No | Admin-only: specify host email |

#### `create-bulk-insert`

Requires `--json-body` because the request body contains an array of invitees:

```bash
wxcli meeting-invitees create-bulk-insert --json-body '{
  "meetingId": "MEETING_ID",
  "hostEmail": "host@example.com",
  "items": [
    {"email": "user1@example.com", "displayName": "User One", "coHost": false},
    {"email": "user2@example.com", "displayName": "User Two", "coHost": true, "sendEmail": false},
    {"email": "panelist@example.com", "panelist": true}
  ]
}'
```

#### `update`

| Option | Description |
|--------|-------------|
| `--meeting-invitee-id ID` | The invitee to update (path parameter) |
| `--email EMAIL` | Updated email address |
| `--display-name TEXT` | Updated display name |
| `--co-host true\|false` | Grant or revoke co-host role |
| `--panelist true\|false` | Set or remove panelist role (webinars) |
| `--send-email true\|false` | Send update notification email |
| `--host-email EMAIL` | Admin-only: specify host email |

### Invitee Response Fields

| Field | Description |
|-------|-------------|
| `id` | Unique invitee identifier |
| `meetingId` | Meeting the invitee is associated with |
| `email` | Invitee email address |
| `displayName` | Invitee display name |
| `coHost` | Whether invitee is a co-host |
| `panelist` | Whether invitee is a panelist (webinars) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List invitees for a meeting
params = {"meetingId": meeting_id, "max": 100}
resp = requests.get(f"{BASE}/meetingInvitees", headers=headers, params=params)
invitees = resp.json().get("items", [])
# Each item: {id, meetingId, email, displayName, coHost, panelist}

# Invite a person
body = {
    "meetingId": meeting_id,
    "email": "user@example.com",
    "displayName": "Jane Doe",
    "coHost": False,
    "sendEmail": True
}
resp = requests.post(f"{BASE}/meetingInvitees", headers=headers, json=body)
invitee_id = resp.json().get("id")

# Bulk invite multiple people
body = {
    "meetingId": meeting_id,
    "items": [
        {"email": "user1@example.com", "displayName": "User One"},
        {"email": "user2@example.com", "coHost": True, "sendEmail": False}
    ]
}
resp = requests.post(f"{BASE}/meetingInvitees/bulkInsert", headers=headers, json=body)
created = resp.json().get("items", [])

# Update invitee to co-host
body = {"email": "user@example.com", "coHost": True, "sendEmail": False}
resp = requests.put(f"{BASE}/meetingInvitees/{invitee_id}", headers=headers, json=body)

# Delete invitee
resp = requests.delete(f"{BASE}/meetingInvitees/{invitee_id}", headers=headers)
```

---

## 11. Raw HTTP Endpoints

All 43 endpoints across the 3 CLI groups documented in this reference.

### Video Mesh (30 endpoints)

| Endpoint | Method | CLI Command | Category |
|----------|--------|------------|----------|
| `/videoMesh/clusters` | GET | `video-mesh list-clusters-video-mesh` | Clusters |
| `/videoMesh/clusters/{clusterId}` | GET | `video-mesh show` | Clusters |
| `/videoMesh/clusters/availability` | GET | `video-mesh list-availability-clusters` | Availability |
| `/videoMesh/clusters/availability/{clusterId}` | GET | `video-mesh show-availability-clusters` | Availability |
| `/videoMesh/nodes/availability` | GET | `video-mesh list-availability-nodes` | Availability |
| `/videoMesh/nodes/availability/{nodeId}` | GET | `video-mesh show-availability-nodes` | Availability |
| `/videoMesh/utilization` | GET | `video-mesh list-utilization-video-mesh` | Utilization |
| `/videoMesh/clusters/utilization` | GET | `video-mesh list-utilization-clusters` | Utilization |
| `/videoMesh/cloudOverflow` | GET | `video-mesh list-cloud-overflow` | Overflow |
| `/videoMesh/callRedirects` | GET | `video-mesh list-call-redirects-video-mesh` | Redirects |
| `/videoMesh/clusters/callRedirects` | GET | `video-mesh list-call-redirects-clusters` | Redirects |
| `/videoMesh/clientTypeDistribution` | GET | `video-mesh list` | Client Distribution |
| `/videoMesh/clientTypeDistribution/clusters` | GET | `video-mesh list-clusters-client-type-distribution` | Client Distribution |
| `/videoMesh/testResults/networkTest` | GET | `video-mesh list-network-test` | Test Results |
| `/videoMesh/testResults/networkTest/clusters` | GET | `video-mesh list-clusters-network-test` | Test Results |
| `/videoMesh/testResults/networkTest/nodes` | GET | `video-mesh list-nodes-network-test` | Test Results |
| `/videoMesh/testResults/reachabilityTest` | GET | `video-mesh list-reachability-test` | Test Results |
| `/videoMesh/testResults/reachabilityTest/clusters` | GET | `video-mesh list-clusters-reachability-test` | Test Results |
| `/videoMesh/testResults/reachabilityTest/nodes` | GET | `video-mesh list-nodes-reachability-test` | Test Results |
| `/videoMesh/testResults/mediaHealthMonitorTest` | GET | `video-mesh list-media-health-monitor-test` | Test Results |
| `/videoMesh/testResults/mediaHealthMonitorTest/clusters` | GET | `video-mesh list-clusters-media-health-monitor-test` | Test Results |
| `/videoMesh/testResults/mediaHealthMonitorTest/nodes` | GET | `video-mesh list-nodes-media-health-monitor-test` | Test Results |
| `/videoMesh/triggerTest/nodes/{nodeId}` | POST | `video-mesh create` | On-Demand Tests |
| `/videoMesh/triggerTest/clusters/{clusterId}` | POST | `video-mesh create-clusters` | On-Demand Tests |
| `/videoMesh/testResults` | GET | `video-mesh list-test-results` | On-Demand Tests |
| `/videoMesh/testStatus` | GET | `video-mesh list-test-status` | On-Demand Tests |
| `/videoMesh/eventThresholds` | GET | `video-mesh list-event-thresholds` | Event Thresholds |
| `/videoMesh/eventThresholds/{eventThresholdId}` | GET | `video-mesh show-event-thresholds` | Event Thresholds |
| `/videoMesh/eventThresholds` | PATCH | `video-mesh update` | Event Thresholds |
| `/videoMesh/eventThresholds/reset` | POST | `video-mesh create-reset` | Event Thresholds |

### Meeting Participants (7 endpoints)

| Endpoint | Method | CLI Command |
|----------|--------|------------|
| `/meetingParticipants` | GET | `meeting-participants list` |
| `/meetingParticipants/{participantId}` | GET | `meeting-participants show` |
| `/meetingParticipants/{participantId}` | PUT | `meeting-participants update` |
| `/meetingParticipants/query` | POST | `meeting-participants create` |
| `/meetingParticipants/admit` | POST | `meeting-participants create-admit` |
| `/meetingParticipants/callout` | POST | `meeting-participants create-callout` |
| `/meetingParticipants/cancelCallout` | POST | `meeting-participants create-cancel-callout` |

### Meeting Invitees (6 endpoints)

| Endpoint | Method | CLI Command |
|----------|--------|------------|
| `/meetingInvitees` | GET | `meeting-invitees list` |
| `/meetingInvitees` | POST | `meeting-invitees create` |
| `/meetingInvitees/bulkInsert` | POST | `meeting-invitees create-bulk-insert` |
| `/meetingInvitees/{meetingInviteeId}` | GET | `meeting-invitees show` |
| `/meetingInvitees/{meetingInviteeId}` | PUT | `meeting-invitees update` |
| `/meetingInvitees/{meetingInviteeId}` | DELETE | `meeting-invitees delete` |

---

## 12. Gotchas

### Video Mesh

1. **Video Mesh API is read-only for infrastructure.** You cannot create, register, or decommission clusters or nodes via the API. All provisioning is done through the Webex Control Hub UI. The API provides monitoring, analytics, and event threshold configuration only.

2. **All Video Mesh endpoints require an admin token with `spark-admin:video_mesh_read` scope.** User tokens and bot tokens will get 403 Forbidden.

3. **Time-range parameters (`from`, `to`) are required for most analytics endpoints.** Utilization, overflow, call redirects, and client distribution endpoints all require `from` and `to` in ISO 8601 format. Omitting them will result in an error or unexpected empty results.

4. **Event threshold `update` uses PATCH, not PUT.** This means partial update semantics -- you only need to send the thresholds you want to change. The response includes a `failedEventThresholdIds` array listing any threshold IDs that failed to update.

5. **`create-reset` resets all thresholds to factory defaults with no undo.** The only way to restore custom thresholds after a reset is to manually re-apply them via `update`.

6. **On-demand tests are asynchronous.** After triggering a test via `create` or `create-clusters`, you must poll `list-test-status` to check completion, then retrieve results via `list-test-results`. Tests may take several minutes to complete.

7. **The `list` command maps to client type distribution, not a general resource list.** `wxcli video-mesh list` returns client type distribution details (GET /videoMesh/clientTypeDistribution), which may be surprising. Use `list-clusters-video-mesh` to list clusters.

### Meeting Participants

8. **The `create` command is actually "Query by Email" (POST to /meetingParticipants/query).** Despite the CLI name suggesting creation, this command searches for participants by email address. The CLI name follows the generator's convention of mapping POST to `create`.

9. **`update` can mute, unmute, admit, or expel a participant during a live meeting.** Set `muted: true/false` to mute/unmute, `admit: true` to admit from lobby, or `expel: true` to remove. Only one action should be performed per call.

10. **`create-callout` dials a SIP URI to add a device to the meeting.** This is useful for bridging room devices (Webex Room Kit, SIP-registered phones) into a Webex meeting. The callout is asynchronous -- the response returns `state: "pending"` initially.

11. **`create-cancel-callout` cancels a pending SIP callout before the device answers.** Once the device has answered and joined the meeting, use `update` with `expel: true` instead.

12. **`create-admit` has a 100-item limit per request.** Each `participantId` in the `items` array must share the same meeting prefix as the `meetingId`.

13. **Personal room meeting IDs are not supported for the participant list endpoint.** Attempting to use a personal room meeting ID will return an error.

14. **The `joinTimeFrom`/`joinTimeTo` interval must be within 90 days.** Exceeding this range will result in a 400 error.

### Meeting Invitees

15. **Invitees are pre-meeting; participants are in-meeting.** These are separate API surfaces. Invitees represent who was invited (before the meeting). Participants represent who actually joined (during/after the meeting).

16. **`sendEmail` defaults to `true`.** When creating an invitee, the invitation email is sent automatically unless you explicitly set `sendEmail: false`. This is important for bulk operations where you may not want to send hundreds of emails.

17. **`create-bulk-insert` accepts multiple invitees at once** via the `items` array in the JSON body. Each item can have independent `coHost`, `panelist`, and `sendEmail` settings.

18. **The `panelist` filter on `list` is for webinars only.** For regular meetings, this parameter has no effect. Set to `true` for panelists, `false` for attendees, or omit for both.

19. **Invitee `update` uses PUT (full replacement), not PATCH.** You must include all fields you want to keep, not just the ones you are changing.

20. **Duplicate invitee creation returns 409 Conflict.** If the email address is already invited to the meeting, the API returns a 409 error rather than silently updating.

---

## 13. See Also

- [`meetings-core.md`](meetings-core.md) — Meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys
- [`meetings-content.md`](meetings-content.md) — Transcripts, captions, chats, summaries, meeting messages
- [`meetings-settings.md`](meetings-settings.md) — Preferences, session types, tracking codes, site settings, polls, Q&A, reports
- [`admin-hybrid.md`](admin-hybrid.md) -- Hybrid clusters and connectors (Video Mesh nodes are hybrid infrastructure)
- [`reporting-analytics.md`](reporting-analytics.md) -- Meeting quality analytics and CDR reporting
- [`authentication.md`](authentication.md) -- Token types, scopes, OAuth flows
