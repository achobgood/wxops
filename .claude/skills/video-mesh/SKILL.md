---
name: video-mesh
description: |
  Monitor and configure Webex Video Mesh clusters, nodes, availability,
  utilization, reachability, and event thresholds using wxcli CLI commands.
  Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [mesh-operation]
---

<!-- Created by playbook session 2026-03-28 -->

# Video Mesh Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What is the command to list all Video Mesh clusters? (Answer: `wxcli video-mesh list-clusters-video-mesh` — not `wxcli video-mesh list`, which shows client type distribution.)
2. How do you trigger an on-demand test for a single node? (Answer: `wxcli video-mesh create NODE_ID` — not `create-clusters`, which targets a cluster.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/meetings-infrastructure.md` for Video Mesh clusters, nodes, availability, utilization, reachability, health monitoring, and event thresholds

---

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

**Required scopes:**
- **Read**: `spark-admin:video_mesh_read`
- **Write**: `spark-admin:video_mesh_write` (for threshold configuration and on-demand tests)

**Token type:** Admin token required. User tokens will return 403.

---

## Step 3: Identify the operation type

Ask the user what they want to accomplish. Present this decision matrix if they are unsure:

| User Wants To | Operation | CLI Commands |
|--------------|-----------|-------------|
| List all clusters | Cluster inventory | `video-mesh list-clusters-video-mesh` |
| Get cluster details | Cluster inspection | `video-mesh show CLUSTER_ID` |
| Check cluster health/availability | Availability monitoring | `video-mesh list-availability-clusters`, `video-mesh show-availability-clusters CLUSTER_ID` |
| Check node health/availability | Node monitoring | `video-mesh list-availability-nodes`, `video-mesh show-availability-nodes NODE_ID` |
| View cluster utilization stats | Utilization analysis | `video-mesh list-utilization-video-mesh`, `video-mesh list-utilization-clusters CLUSTER_ID` |
| Run reachability tests | Connectivity verification | `video-mesh list-reachability-test`, `video-mesh list-clusters-reachability-test CLUSTER_ID`, `video-mesh list-nodes-reachability-test NODE_ID` |
| View media health results | Media quality monitoring | `video-mesh list-media-health-monitor-test`, `video-mesh list-clusters-media-health-monitor-test CLUSTER_ID`, `video-mesh list-nodes-media-health-monitor-test NODE_ID` |
| Run network tests | Network diagnostics | `video-mesh list-network-test`, `video-mesh list-clusters-network-test CLUSTER_ID`, `video-mesh list-nodes-network-test NODE_ID` |
| Trigger on-demand test (node) | Manual testing | `video-mesh create NODE_ID` |
| Trigger on-demand test (cluster) | Manual testing | `video-mesh create-clusters CLUSTER_ID` |
| Check triggered test status/results | Test follow-up | `video-mesh list-test-status`, `video-mesh list-test-results` |
| View cloud overflow stats | Overflow analysis | `video-mesh list-cloud-overflow` |
| View call redirect details | Redirect analysis | `video-mesh list-call-redirects-video-mesh`, `video-mesh list-call-redirects-clusters CLUSTER_ID` |
| View client type distribution | Client analytics | `video-mesh list`, `video-mesh list-clusters-client-type-distribution CLUSTER_ID` |
| View/update event thresholds | Threshold configuration | `video-mesh list-event-thresholds`, `video-mesh show-event-thresholds THRESHOLD_ID`, `video-mesh update THRESHOLD_ID` |
| Reset event thresholds to defaults | Threshold reset | `video-mesh create-reset` |
| Not Video Mesh? | For meetings → `manage-meetings` skill. For call features → `configure-features` skill. | — |

---

## Step 4: Check prerequisites

### 4a. Admin token with Video Mesh scopes

```bash
wxcli whoami
```

Verify the output shows admin-level access. If Video Mesh commands return 403, the token is missing `spark-admin:video_mesh_read` or `spark-admin:video_mesh_write` scopes.

### 4b. Video Mesh deployed

Verify the org has Video Mesh clusters registered:

```bash
wxcli video-mesh list-clusters-video-mesh --output json
```

If this returns empty, Video Mesh is not deployed in this org. Video Mesh requires on-premises nodes registered to the Webex cloud. This skill cannot deploy Video Mesh — that is a network infrastructure task done via the Video Mesh Node OVA.

### 4c. Cluster and node IDs

For most operations, you need a cluster ID or node ID. Get them from the cluster list:

```bash
# List clusters (get cluster IDs)
wxcli video-mesh list-clusters-video-mesh --output json

# Get cluster details (includes node IDs)
wxcli video-mesh show CLUSTER_ID --output json
```

---

## Step 5: Gather configuration and present deployment plan — [SHOW BEFORE EXECUTING]

Most Video Mesh operations are read-only queries. For write operations (threshold configuration, on-demand tests), present the plan before executing.

---

### Monitoring Queries (Read-Only)

For read-only operations, present a brief query plan:

```
QUERY PLAN
==========
Operation: [type — e.g., "Check availability for all clusters over last 7 days"]
Scope: [all clusters / specific cluster / specific node]
Time Range: [if applicable]

Commands to execute:
  1. wxcli video-mesh list-availability-clusters --from ... --to ... --output json

Proceed? (yes/no)
```

---

### Cluster Health Check (Comprehensive)

For a comprehensive health check of a cluster:

```bash
# 1. Cluster details
wxcli video-mesh show CLUSTER_ID --output json

# 2. Availability
wxcli video-mesh show-availability-clusters CLUSTER_ID --output json

# 3. Utilization
wxcli video-mesh list-utilization-clusters CLUSTER_ID --output json

# 4. Reachability
wxcli video-mesh list-clusters-reachability-test CLUSTER_ID --output json

# 5. Media health
wxcli video-mesh list-clusters-media-health-monitor-test CLUSTER_ID --output json

# 6. Network test results
wxcli video-mesh list-clusters-network-test CLUSTER_ID --output json

# 7. Call redirects (overflow)
wxcli video-mesh list-call-redirects-clusters CLUSTER_ID --output json

# 8. Client type distribution
wxcli video-mesh list-clusters-client-type-distribution CLUSTER_ID --output json
```

---

### Node Health Check

For a single node:

```bash
# Node availability
wxcli video-mesh show-availability-nodes NODE_ID --output json

# Node reachability
wxcli video-mesh list-nodes-reachability-test NODE_ID --output json

# Node media health
wxcli video-mesh list-nodes-media-health-monitor-test NODE_ID --output json

# Node network test
wxcli video-mesh list-nodes-network-test NODE_ID --output json
```

---

### On-Demand Tests

```bash
# Trigger test for a specific node
wxcli video-mesh create NODE_ID

# Trigger test for all nodes in a cluster
wxcli video-mesh create-clusters CLUSTER_ID

# Check test status
wxcli video-mesh list-test-status --output json

# Get test results
wxcli video-mesh list-test-results --output json
```

---

### Event Threshold Configuration

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Threshold ID | Yes | Get from `list-event-thresholds` |
| New threshold value | Yes | Depends on threshold type |

```bash
# List current thresholds
wxcli video-mesh list-event-thresholds --output json

# Get a specific threshold
wxcli video-mesh show-event-thresholds THRESHOLD_ID --output json

# Update a threshold
wxcli video-mesh update THRESHOLD_ID --json-body '{"value": 80}'

# Reset all thresholds to defaults
wxcli video-mesh create-reset
```

---

### Overflow and Redirect Analysis

```bash
# List cloud overflow details
wxcli video-mesh list-cloud-overflow --output json

# List call redirect details (org-wide)
wxcli video-mesh list-call-redirects-video-mesh --output json

# Get redirect details for a specific cluster
wxcli video-mesh list-call-redirects-clusters CLUSTER_ID --output json
```

---

### Deployment Plan Template (Write Operations)

For write operations (threshold updates, on-demand tests):

```
DEPLOYMENT PLAN
===============
Operation: [type — e.g., "Update CPU utilization threshold to 80%"]
Target: [threshold ID / node ID / cluster ID]

Current State:
  [Current threshold value / current test status]

Changes:
  [What will be changed]

Commands to execute:
  1. wxcli video-mesh update THRESHOLD_ID --json-body '{"value": 80}'

Proceed? (yes/no)
```

**Wait for user confirmation before executing write operations.**

---

## Step 6: Execute via wxcli

Run the commands in plan order.

Handle errors explicitly:

- **401/403**: Token expired or insufficient scopes — run `wxcli configure` to re-authenticate. Required scope: `spark-admin:video_mesh_read` (read) or `spark-admin:video_mesh_write` (write).
- **404**: Cluster or node not found — verify the ID with `wxcli video-mesh list-clusters-video-mesh`.
- **400**: Validation error — read the error message and fix the parameter (e.g., invalid threshold value).
- **Empty results on availability/utilization queries:** The time range may be too narrow or the cluster may be newly deployed. Try expanding the time range.

---

## Step 7: Verify

After write operations, verify the change took effect:

```bash
# Verify threshold update
wxcli video-mesh show-event-thresholds THRESHOLD_ID --output json

# Verify on-demand test was triggered
wxcli video-mesh list-test-status --output json

# Verify test completed and get results
wxcli video-mesh list-test-results --output json
```

For read-only operations, verification is inherent — the query results are the verification.

---

## Step 8: Report results

Present the operation results:

### For monitoring queries:

```
VIDEO MESH STATUS
=================
Clusters: [N]
Total Nodes: [N]

Cluster: [cluster_name]
  ID: [cluster_id]
  Nodes: [N]
  Availability: [percentage]
  Utilization: [percentage]
  Reachability: [pass/fail]
  Media Health: [pass/fail]
  Cloud Overflow: [count] calls redirected

[Repeat for each cluster]

Issues Found:
  - [e.g., "Node X reachability test failed"]
  - [e.g., "Cluster Y utilization at 92% (above threshold)"]

Recommendations:
  - [e.g., "Investigate node X network connectivity"]
  - [e.g., "Consider adding nodes to cluster Y"]
```

### For write operations:

```
OPERATION COMPLETE
==================
Operation: [type]
Status: Success

Changes Applied:
  - [e.g., "CPU threshold updated from 70% to 80%"]
  - [e.g., "On-demand test triggered for node X"]

Next steps:
  - [e.g., "Monitor test results: wxcli video-mesh list-test-results"]
  - [e.g., "Check cluster health in 5 minutes after test completes"]
```

---

## Critical Rules

1. **Always verify admin token and Video Mesh scopes** before any operation. User tokens return 403 for all Video Mesh endpoints.
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing write operations (threshold changes, on-demand tests).
3. **`video-mesh list` is NOT the cluster list command.** `list` shows client type distribution. Use `list-clusters-video-mesh` to list clusters.
4. **On-demand tests are `create` (node) and `create-clusters` (cluster).** The command names follow the generator pattern where POST endpoints become `create`.
5. **Threshold reset (`create-reset`) resets ALL thresholds** to factory defaults. This is a destructive operation — confirm with the user before executing.
6. **Video Mesh is read-heavy.** Most operations are monitoring queries. Only threshold configuration and on-demand test triggers are write operations.
7. **Time-range queries default to recent data.** If availability/utilization commands return empty, the time range may need to be specified with `--from` and `--to` flags (where supported).
8. **Node IDs come from cluster details.** You cannot list all nodes directly — get them from `wxcli video-mesh show CLUSTER_ID --output json` which includes the node list.
9. **Cross-skill handoffs:**
    - Meeting scheduling/management → `manage-meetings` skill
    - CDR and call quality reports → `reporting` skill
    - Network infrastructure/PSTN → `configure-routing` skill

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. List clusters to recover the environment state:
   ```bash
   wxcli video-mesh list-clusters-video-mesh --output json
   ```
2. Check if any on-demand tests are pending:
   ```bash
   wxcli video-mesh list-test-status --output json
   ```
3. Resume from the first incomplete step in the plan
