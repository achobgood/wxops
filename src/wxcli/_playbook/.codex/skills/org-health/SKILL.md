---
name: org-health
description: |
  Run an org health assessment on a live Webex Calling org. Collects state via
  wxcli commands, runs 18 deterministic Python checks across 4 categories, and
  generates an Authority Minimal HTML report. Three phases: collect → analyze → report.
  Use when the user wants to audit their org, run a health check, or see what needs attention.
  NOT for: security/compliance audit logs (use audit-compliance skill), CDR/call analytics
  (use reporting skill), or license auditing (use manage-licensing skill).
---

# Org Health Assessment

## Prerequisites

1. Authenticated session: `wxcli whoami` succeeds
2. Confirm target org with user — show org name from `wxcli whoami` output

## Phase 1 — Collect

Create the output directory and run each wxcli command. Save results as JSON.

**Mandatory --help verification:** Before constructing or running any wxcli command in this skill, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli call-routing --help`, `wxcli call-queue --help`). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

### Setup

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="org-health-output/${TIMESTAMP}/collected"
mkdir -p "${OUTPUT_DIR}/call_queue_details" "${OUTPUT_DIR}/outgoing_permissions"
echo "${TIMESTAMP}" > org-health-output/.current-run
```

Shell state does not survive between tool calls, so every later block re-binds `TIMESTAMP` (and `OUTPUT_DIR`) from `org-health-output/.current-run` — without that, a block run in a fresh shell writes to an empty path. The collection table below assumes the same two bindings: run it in the Setup shell, or re-bind first.

### Collection Commands

Run each command and save the output. If a command fails (e.g., no resources of that type),
save an empty JSON array `[]`.

| # | Command | Output File |
|---|---------|-------------|
| 1 | `wxcli auto-attendant list -o json` | `${OUTPUT_DIR}/auto_attendants.json` |
| 2 | `wxcli call-queue list -o json` | `${OUTPUT_DIR}/call_queues.json` |
| 3 | `wxcli hunt-group list -o json` | `${OUTPUT_DIR}/hunt_groups.json` |
| 4 | `wxcli location-voicemail list --all -o json` | `${OUTPUT_DIR}/voicemail_groups.json` |
| 5 | `wxcli paging-group list -o json` | `${OUTPUT_DIR}/paging_groups.json` |
| 6 | `wxcli call-park list --all -o json` | `${OUTPUT_DIR}/call_parks.json` |
| 7 | `wxcli devices list -o json` | `${OUTPUT_DIR}/devices.json` |
| 8 | `wxcli workspaces list --all -o json` | `${OUTPUT_DIR}/workspaces.json` |
| 9 | `wxcli people list -o json` | `${OUTPUT_DIR}/users.json` |
| 10 | `wxcli call-routing list-dial-plans --all -o json` | `${OUTPUT_DIR}/dial_plans.json` |
| 11 | `wxcli call-routing list-route-groups --all -o json` | `${OUTPUT_DIR}/route_groups.json` |
| 12 | `wxcli call-routing list-route-lists --all -o json` | `${OUTPUT_DIR}/route_lists.json` |
| 13 | `wxcli call-routing list-trunks --all -o json` | `${OUTPUT_DIR}/trunks.json` |
| 14 | `wxcli numbers list --all -o json` | `${OUTPUT_DIR}/numbers.json` |

**Why `--all` is on 8 rows and not all 14.** Every check downstream is a count or a
completeness test, so a collection that stops at page one does not error — it produces a
*clean-looking report that is wrong*. On rows 4, 6, 8, 10-14 a bare `list` issues one
request and discards the rest; `--all` walks the collection. On rows 1, 2, 3, 5, 7 and 9
the default already fetches every page (`--limit` defaults to 0, which walks), so `--all`
would add nothing. If a collection command prints `Note: N records returned and the server
has more pages` on **stderr**, the file you just wrote is partial — re-run it with `--all`
before analyzing. See AGENTS.md's Common Flags section.

### Detail Collection

**Call queue details** — iterate queue IDs from step 2:

```bash
TIMESTAMP=$(cat org-health-output/.current-run)
OUTPUT_DIR="org-health-output/${TIMESTAMP}/collected"

# For each queue ID from call_queues.json:
wxcli call-queue show <QUEUE_ID> -o json > "${OUTPUT_DIR}/call_queue_details/<QUEUE_ID>.json"
```

**Outgoing permissions sample** — select up to 50 user IDs from step 9:

```bash
TIMESTAMP=$(cat org-health-output/.current-run)
OUTPUT_DIR="org-health-output/${TIMESTAMP}/collected"

# For each of the first 50 user IDs from users.json:
wxcli user-settings list-outgoing-permission <USER_ID> -o json > "${OUTPUT_DIR}/outgoing_permissions/<USER_ID>.json"
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
TIMESTAMP=$(cat org-health-output/.current-run)
wxcli org-health analyze \
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
TIMESTAMP=$(cat org-health-output/.current-run)
wxcli org-health report \
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
