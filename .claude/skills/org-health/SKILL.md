---
name: org-health
description: |
  Run an org health assessment on a live Webex Calling org. Collects state via
  wxcli commands, runs 18 deterministic Python checks across 4 categories, and
  generates an Authority Minimal HTML report. Three phases: collect → analyze → report.
  Use when the user wants to audit their org, run a health check, or see what needs attention.
---

# Org Health Assessment

## Prerequisites

1. Authenticated session: `wxcli whoami` succeeds
2. Confirm target org with user — show org name from `wxcli whoami` output

## Phase 1 — Collect

Create the output directory and run each wxcli command. Save results as JSON.

### Setup

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="org-health-output/${TIMESTAMP}/collected"
mkdir -p "${OUTPUT_DIR}/call_queue_details" "${OUTPUT_DIR}/outgoing_permissions"
```

### Collection Commands

Run each command and save the output. If a command fails (e.g., no resources of that type),
save an empty JSON array `[]`.

| # | Command | Output File |
|---|---------|-------------|
| 1 | `wxcli auto-attendant list -o json` | `${OUTPUT_DIR}/auto_attendants.json` |
| 2 | `wxcli call-queue list -o json` | `${OUTPUT_DIR}/call_queues.json` |
| 3 | `wxcli hunt-group list -o json` | `${OUTPUT_DIR}/hunt_groups.json` |
| 4 | `wxcli location-voicemail list -o json` | `${OUTPUT_DIR}/voicemail_groups.json` |
| 5 | `wxcli paging-group list -o json` | `${OUTPUT_DIR}/paging_groups.json` |
| 6 | `wxcli call-park list -o json` | `${OUTPUT_DIR}/call_parks.json` |
| 7 | `wxcli devices list -o json` | `${OUTPUT_DIR}/devices.json` |
| 8 | `wxcli workspaces list -o json` | `${OUTPUT_DIR}/workspaces.json` |
| 9 | `wxcli people list -o json` | `${OUTPUT_DIR}/users.json` |
| 10 | `wxcli call-routing list-dial-plans -o json` | `${OUTPUT_DIR}/dial_plans.json` |
| 11 | `wxcli call-routing list-route-groups -o json` | `${OUTPUT_DIR}/route_groups.json` |
| 12 | `wxcli call-routing list-route-lists -o json` | `${OUTPUT_DIR}/route_lists.json` |
| 13 | `wxcli call-routing list-trunks -o json` | `${OUTPUT_DIR}/trunks.json` |
| 14 | `wxcli numbers list -o json` | `${OUTPUT_DIR}/numbers.json` |

### Detail Collection

**Call queue details** — iterate queue IDs from step 2:

```bash
# For each queue ID from call_queues.json:
wxcli call-queue show <QUEUE_ID> -o json > "${OUTPUT_DIR}/call_queue_details/<QUEUE_ID>.json"
```

**Outgoing permissions sample** — select up to 50 user IDs from step 9:

```bash
# For each of the first 50 user IDs from users.json:
wxcli user-settings show-outgoing-permissions <USER_ID> -o json > "${OUTPUT_DIR}/outgoing_permissions/<USER_ID>.json"
```

### Manifest

After all collection is complete, write `manifest.json`:

```json
{
  "collected_at": "<ISO timestamp>",
  "org_id": "<from wxcli whoami>",
  "org_name": "<from wxcli whoami>",
  "total_users": <count from users.json>,
  "total_devices": <count from devices.json>,
  "sampled_users_for_permissions": <actual number sampled, max 50>,
  "commands_run": ["auto-attendant list", "call-queue list", "..."],
  "wxcli_version": "<from wxcli --version>"
}
```

### Progress Report

After collection, tell the user:
- "Collected X users, Y devices, Z features across N locations"
- "Sampled M users for outgoing permission analysis"

## Phase 2 — Analyze

Run the analyzer:

```bash
python3.14 -m wxcli.org_health.analyze \
  "org-health-output/${TIMESTAMP}/collected" \
  --output "org-health-output/${TIMESTAMP}/results"
```

- If exit code 0: read `results/results.json` and present a summary:
  - Total findings by severity (HIGH/MEDIUM/LOW/INFO)
  - Category breakdown (which categories have findings)
- If exit code 1: report the error to the user and stop

## Phase 3 — Report

Ask the user for:
- **Brand name** (default: org name from manifest)
- **Prepared by** (default: ask the user)

Generate the report:

```bash
python3.14 -m wxcli.org_health.report \
  "org-health-output/${TIMESTAMP}/results" \
  --brand "<brand>" \
  --prepared-by "<name>"
```

### Present Results

Tell the user:
1. Report file path: `org-health-output/${TIMESTAMP}/report/org-health-report.html`
2. Top 3 highest-severity findings (title + recommendation)
3. Total finding counts: X HIGH, Y MEDIUM, Z LOW
4. Any categories with zero issues (positive reinforcement)

## Check Categories

For reference, the 18 checks organized by category:

**Security Posture** (checked first — infrastructure risk):
- Auto attendants allowing external transfers (toll fraud vector)
- Call queues without recording (compliance gap)
- Unrestricted international/premium dialing (toll fraud risk)
- No outgoing permission rules configured (policy gap)

**Routing Hygiene** (infrastructure reliability):
- Dial plans with no route choices (calls will fail)
- Route groups/lists with no trunks/groups (orphaned components)
- Trunks in error/unregistered state (PSTN outage)

**Feature Utilization** (operational efficiency):
- Disabled auto attendants
- Call queues with 0 or 1 agents
- Single-member hunt groups
- Empty voicemail/paging groups
- Call parks with no extensions

**Device Health** (endpoint reliability):
- Offline devices
- Users at 5-device limit
- Unassigned devices
- Calling-enabled workspaces with no device
- Stale activation codes
