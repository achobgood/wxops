---
name: customer-assist
description: |
  Configure Webex Calling Customer Assist (CX Essentials) using wxcli CLI commands: screen pop,
  wrap-up reasons, queue call recording, supervisors, and available agents.
  Guides the user from prerequisites through configuration and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [feature-type]
---

# Configure Customer Assist Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. How do you list CX Essentials call queues? (Answer: `wxcli call-queue list --has-cx-essentials true` — they are hidden from the default `call-queue list` output.)
2. What is the workaround for the supervisor delete bug? (Answer: `delete-supervisors-config-1` returns 204 but the supervisor persists. Instead, use `update-supervisors` with `action: DELETE` on each agent — removing the last agent auto-removes the supervisor.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/call-features-additional.md` — Customer Assist data models, screen pop, wrap-up reasons, queue recording, available agents
2. Read `docs/reference/location-recording-advanced.md` — Supervisors data models, API methods, key behaviors

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`). Required scopes:

| Operation | Read Scope | Write Scope |
|-----------|-----------|-------------|
| Screen pop, wrap-up, agents, supervisors | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Queue call recording | `spark-admin:people_read` | `spark-admin:people_write` |

## Step 3: Identify which feature(s) to configure

Ask the user which feature they want to configure. Present this decision matrix if they are unsure:

| Need | Feature | CLI Group |
|------|---------|-----------|
| Pop a CRM/ticketing URL when agent receives a queued call | **Screen Pop** | `wxcli cx-essentials` |
| Post-call categorization codes for agents | **Wrap-Up Reasons** | `wxcli cx-essentials` |
| Record calls on a queue for QA/compliance/training | **Queue Call Recording** | `wxcli cx-essentials` |
| Assign supervisors to monitor/coach/barge agents | **Supervisors** | `wxcli call-queue` |
| List agents with or without Customer Assist licensing | **Available Agents** | `wxcli cx-essentials` |

## Step 4: Check prerequisites

Before configuring any feature, verify these exist:

### 4a. Location exists

```bash
wxcli locations list --output json
```

### 4b. Customer Assist queue exists

All Customer Assist features are per-queue configurations. **Customer Assist queues are separate from regular queues** — they do not appear in the default `call-queue list` output.

```bash
# List Customer Assist queues (MUST use --has-cx-essentials true)
wxcli call-queue list --has-cx-essentials true --output json
```

If no Customer Assist queue exists, create one. **Customer Assist queues require `callPolicies` via `--json-body`:**

```bash
wxcli call-queue create LOCATION_ID --name "Queue Name" --has-cx-essentials true \
  --json-body '{"name":"Queue Name","extension":"XXXX","callPolicies":{"policy":"SIMULTANEOUS"}}'
```

> **IMPORTANT:** A regular queue (created without `--has-cx-essentials true`) will return error 28018 on all Customer Assist endpoints. The queue must be created with the `--has-cx-essentials true` flag. The `callPolicies` field is mandatory for Customer Assist queues but not for regular queues.

### 4c. Customer Assist licensing

Confirm agents have CX Essentials licenses:

```bash
wxcli cx-essentials list-available-agents LOCATION_ID --has-cx-essentials true
```

If no agents are returned, CX Essentials licenses must be assigned first (use `manage-licensing` skill).

### 4d. Feature-specific prerequisites

| Feature | Additional Prerequisites |
|---------|------------------------|
| **Screen Pop** | Call queue must exist. No additional requirements. |
| **Wrap-Up Reasons** | Call queue must exist. Org-level reasons must be created before queue assignment. |
| **Queue Call Recording** | Call queue must exist. Recording vendor must be configured at org/location level (see `wxcli call-recording`). Requires `spark-admin:people_read`/`people_write` scopes (different from other Customer Assist features). |
| **Supervisors** | At least one agent must be assigned when creating. Supervisor must be a calling-enabled user. |
| **Available Agents** | Location must exist. |

## Step 5: Gather configuration and present deployment plan -- [SHOW BEFORE EXECUTING]

Based on the selected feature, collect the required parameters from the user. **Always present the plan before executing.**

---

### Screen Pop

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Location ID | Yes | Positional argument |
| Queue ID | Yes | Positional argument |
| Enabled | Yes | `--enabled` / `--no-enabled` |
| Screen pop URL | Yes (if enabling) | CRM or ticketing system URL |
| Desktop label | No | Label for the config |
| Query params | No | Requires `--json-body` (not available as explicit flags) |

CLI commands:

```bash
# View current screen pop config
wxcli cx-essentials show-screen-pop LOCATION_ID QUEUE_ID -o json

# Simple: enable with URL
wxcli cx-essentials update-screen-pop LOCATION_ID QUEUE_ID \
  --enabled --screen-pop-url "https://crm.example.com/lookup"

# Full: enable with URL, label, and query params (requires --json-body)
wxcli cx-essentials update-screen-pop LOCATION_ID QUEUE_ID --json-body '{
  "enabled": true,
  "screenPopUrl": "https://crm.example.com/lookup",
  "desktopLabel": "Customer Lookup",
  "queryParams": {"caller_id": "{{callerNumber}}", "queue": "{{queueName}}"}
}'
```

> **NOTE:** Query parameters (`queryParams`) are only available via `--json-body`. The `--screen-pop-url`, `--enabled`, and `--desktop-label` flags cover the simple case. Use `--json-body` for the full configuration including query params.

---

### Wrap-Up Reasons

Wrap-up reasons are a two-level configuration: org-level reasons, then per-queue assignment.

**Org-level parameter table:**

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Name | Yes | `--name` flag |
| Description | No | `--description` flag |
| Queues | No | List of queue IDs — requires `--json-body` (not available as explicit flag) |
| Assign all queues | No | `--assign-all-queues-enabled` flag |

**Queue-level parameter table:**

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Location ID | Yes | Positional argument |
| Queue ID | Yes | Positional argument |
| Wrap-up timer enabled | No | `--wrapup-timer-enabled` / `--no-wrapup-timer-enabled` |
| Wrap-up timer (seconds) | No | `--wrapup-timer` (default 60) |
| Default wrap-up reason ID | No | `--default-wrapup-reason-id` |
| Wrap-up reasons list | No | List of reason IDs — requires `--json-body` |

CLI commands:

```bash
# --- Org-level reason management ---

# List all wrap-up reasons
wxcli cx-essentials list

# Create a reason (simple — assign to queues later)
wxcli cx-essentials create --name "Issue Resolved" --description "Customer issue resolved on the call"

# Create a reason AND assign to specific queues (requires --json-body)
wxcli cx-essentials create --json-body '{
  "name": "Issue Resolved",
  "description": "Customer issue resolved on the call",
  "queues": ["QUEUE_ID_1", "QUEUE_ID_2"]
}'

# Validate a reason name before creating
wxcli cx-essentials validate-wrap-up --name "Issue Resolved"

# Show reason details (includes assigned queues)
wxcli cx-essentials show REASON_ID -o json

# Update a reason (incremental queue assignment)
wxcli cx-essentials update REASON_ID --json-body '{
  "queuesToAssign": ["QUEUE_ID_3"],
  "queuesToUnassign": ["QUEUE_ID_1"]
}'

# List queues not yet assigned to a reason
wxcli cx-essentials list-available-queues REASON_ID

# Delete a reason
wxcli cx-essentials delete REASON_ID --force

# --- Per-queue wrap-up settings ---

# View queue wrap-up settings
wxcli cx-essentials list-settings LOCATION_ID QUEUE_ID -o json

# Update queue wrap-up timer and assign reasons
wxcli cx-essentials update-settings LOCATION_ID QUEUE_ID --json-body '{
  "wrapupTimerEnabled": true,
  "wrapupTimer": 60,
  "wrapupReasons": ["REASON_ID_1", "REASON_ID_2"],
  "defaultWrapupReasonId": "REASON_ID_1"
}'
```

> **NOTE:** The `queues` array on `create` and the `wrapupReasons` array on `update-settings` require `--json-body`. The CLI flags only cover scalar fields (`--name`, `--description`, `--wrapup-timer-enabled`, `--wrapup-timer`). For queue assignment at creation time, use `--json-body`.

> **NOTE:** Queue assignment on `update` is incremental — use `queuesToAssign` and `queuesToUnassign`, not a full replacement list.

---

### Queue Call Recording

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Location ID | Yes | Positional argument |
| Queue ID | Yes | Positional argument |
| Enabled | No | `--enabled` / `--no-enabled` |
| Record mode | No | `--record` — `Always`, `Never`, or `OnDemand` |
| Notification settings | No | Requires `--json-body` |

CLI commands:

```bash
# View current queue recording settings
wxcli cx-essentials show-queue-recording LOCATION_ID QUEUE_ID -o json

# Enable always-on recording (simple)
wxcli cx-essentials update-queue-recording LOCATION_ID QUEUE_ID \
  --enabled --record Always

# Full recording config with notifications (requires --json-body)
wxcli cx-essentials update-queue-recording LOCATION_ID QUEUE_ID --json-body '{
  "enabled": true,
  "record": "Always",
  "notification": {"enabled": true, "type": "Beep"},
  "repeat": {"enabled": false, "interval": 15},
  "startStopAnnouncement": {"internalCallsEnabled": false, "pstnCallsEnabled": false}
}'
```

> **NOTE:** Queue call recording requires `spark-admin:people_read` / `spark-admin:people_write` scopes — different from all other Customer Assist features which use `spark-admin:telephony_config_read/write`. The recording vendor must be configured at the org or location level first (see `wxcli call-recording`).

---

### Supervisors

Supervisor commands live under `wxcli call-queue`, not `wxcli cx-essentials`. **All commands must include `--has-cx-essentials true` when working with Customer Assist supervisors** (without it, commands default to CX Basic).

Collect from user (for create):

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Supervisor person ID | Yes | `--id` flag — the person's ID (not a separate supervisor entity ID); must be a calling-enabled user |
| Agents | Yes | List of agent IDs — requires `--json-body` |
| Has CX Essentials | Yes (for Customer Assist) | `--has-cx-essentials true` |

CLI commands:

```bash
# --- Discovery ---

# List all Customer Assist supervisors
wxcli call-queue list-supervisors --has-cx-essentials true

# List available supervisors (not yet assigned)
wxcli call-queue list-available-supervisors --has-cx-essentials true

# List available agents for supervisor assignment
wxcli call-queue list-available-agents-supervisors --has-cx-essentials true

# --- Create ---

# Create a supervisor with agents (--id is required AND must be in --json-body)
wxcli call-queue create-supervisors --has-cx-essentials true \
  --id SUPERVISOR_PERSON_ID --json-body '{"id": "SUPERVISOR_PERSON_ID", "agents": [{"id": "AGENT_ID_1"}, {"id": "AGENT_ID_2"}]}'

# --- Read ---

# Show supervisor's assigned agents
wxcli call-queue show-supervisors SUPERVISOR_ID --has-cx-essentials true -o json

# --- Update ---

# Add/remove agents (incremental)
wxcli call-queue update-supervisors SUPERVISOR_ID --has-cx-essentials true --json-body '{
  "agents": [
    {"id": "AGENT_ID_3", "action": "ADD"},
    {"id": "AGENT_ID_1", "action": "DELETE"}
  ]
}'

# --- Delete ---

# Delete a specific supervisor
wxcli call-queue delete-supervisors-config-1 SUPERVISOR_ID --has-cx-essentials true --force

# Delete supervisors in bulk
wxcli call-queue delete-supervisors-config --has-cx-essentials true --force
```

> **WARNING:** `delete-supervisors-config --force` without specifying IDs may remove **all supervisors in the org**. Always confirm scope before executing. Omitting `--force` triggers a confirmation prompt.

> **NOTE:** `SUPERVISOR_ID` in these commands is the supervisor's **person ID**, not a separate supervisor entity ID. Use `wxcli call-queue list-supervisors --has-cx-essentials true` to find supervisor person IDs.

> **NOTE:** Runtime supervisor capabilities (silent monitor, whisper coach, barge in, take over) activate automatically once the supervisor-agent relationship is configured. No additional API setup is needed — these are built into the Webex app.

---

### Available Agents

```bash
# List all agents at a location
wxcli cx-essentials list-available-agents LOCATION_ID

# List only agents with Customer Assist (CX Essentials) license
wxcli cx-essentials list-available-agents LOCATION_ID --has-cx-essentials true

# List only agents with CX Basic license
wxcli cx-essentials list-available-agents LOCATION_ID --has-cx-essentials false
```

---

### Deployment Plan Template

```
DEPLOYMENT PLAN
===============
Feature: Customer Assist — [sub-feature]
Location: [name] ([location_id])
Queue: [queue_name] ([queue_id])

Configuration:
  [Feature-specific settings listed here]

Prerequisites verified:
  ✓ Location exists
  ✓ Call queue exists
  ✓ CX Essentials licenses assigned ([N] agents)
  ✓ [Feature-specific prereqs]

Commands to execute:
  wxcli cx-essentials [command] ...

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

## Step 6: Execute via wxcli

Run commands sequentially. Handle errors explicitly:
- **400 with code 28018**: Customer Assist is not enabled on this queue — create the queue with `--has-cx-essentials true` or use a Customer Assist queue (see Step 4b)
- **401/403**: Token expired or insufficient scopes — run `wxcli configure`
- **409**: Name or resource conflict — ask user for alternate
- **400**: Validation error — read the error message and fix the parameter
- **400 with code 25008**: Missing required field — use `--json-body` for full control
- **400 with code 4003 / "Target user not authorized"**: Endpoint requires user-level OAuth, not admin token
- **404 with code 4008**: Target user needs a Webex Calling license
- **405 with code 25409**: Workspace requires Professional license

## Step 7: Verify creation

After configuration, fetch the details back and confirm:

```bash
# Verify screen pop
wxcli cx-essentials show-screen-pop LOCATION_ID QUEUE_ID -o json

# Verify wrap-up reasons (org-level)
wxcli cx-essentials list -o json
wxcli cx-essentials show REASON_ID -o json

# Verify wrap-up settings (per-queue)
wxcli cx-essentials list-settings LOCATION_ID QUEUE_ID -o json

# Verify queue recording
wxcli cx-essentials show-queue-recording LOCATION_ID QUEUE_ID -o json

# Verify supervisors
wxcli call-queue list-supervisors --has-cx-essentials true -o json
wxcli call-queue show-supervisors SUPERVISOR_ID --has-cx-essentials true -o json
```

## Step 8: Report results

Present the configuration results:

```
CUSTOMER ASSIST CONFIGURED
===========================
Feature: [sub-feature]
Queue: [queue_name]
Location: [location_name]

Configuration applied:
  [Feature-specific summary]

Verification:
  ✓ [Feature] confirmed via read-back

Next steps:
  - [Feature-specific next steps]
  - [e.g., "Assign more agents to supervisor via update-supervisors"]
  - [e.g., "Configure additional queues with the same wrap-up reasons"]
```

---

## Critical Rules

1. **All Customer Assist features require a Customer Assist queue.** Screen pop, queue recording, and wrap-up reasons are per-queue configurations. The queue must be created with `--has-cx-essentials true` — a regular queue returns error 28018. Use `wxcli call-queue list --has-cx-essentials true` to find existing Customer Assist queues (they are hidden from the default `call-queue list`).
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing.
3. **Always pass `--has-cx-essentials true` on supervisor commands.** Without it, commands default to CX Basic supervisors. This applies to `list-supervisors`, `create-supervisors`, `show-supervisors`, `update-supervisors`, `list-available-supervisors`, and `list-available-agents-supervisors`.
4. **Supervisor commands live under `wxcli call-queue`, not `wxcli cx-essentials`.** The supervisor API base path (`/telephony/config/supervisors`) was grouped with call queues in the OpenAPI spec. The `cx-essentials` group handles wrap-up reasons, screen pop, queue recording, and available agents.
5. **A supervisor must have at least one agent** when created via `create-supervisors`.
6. **`delete-supervisors-config --force` can remove ALL supervisors in the org.** The bulk delete endpoint has a `delete_all` option. Always confirm scope before executing.
7. **Queue call recording requires different scopes.** Queue recording uses `spark-admin:people_read` / `spark-admin:people_write`, while all other Customer Assist features use `spark-admin:telephony_config_read` / `spark-admin:telephony_config_write`.
8. **Wrap-up reason queue assignment is incremental.** Use `queuesToAssign` and `queuesToUnassign` on update — not a full replacement list.
9. **`show-supervisors` returns the supervisor's assigned agents, not the supervisor's own details.** The response is a list of agents, not supervisor metadata.
10. **Per-queue features need both `location_id` and `queue_id`.** Screen pop, queue recording, and wrap-up settings are scoped to a specific queue within a specific location.
11. **`queryParams` on screen pop requires `--json-body`.** The `--screen-pop-url`, `--enabled`, and `--desktop-label` flags cover the simple case. For query parameters (passing caller data to the CRM URL), use `--json-body`.
12. **`queues` array on wrap-up reason create requires `--json-body`.** To assign a reason to specific queues on creation, use `--json-body`. Alternatively, create the reason first, then assign queues via `update`.
13. **Runtime supervisor capabilities are automatic.** Silent monitor, whisper coach, barge in, and take over activate once the supervisor-agent relationship is configured. No additional API setup is needed.
14. **Recording vendor must be configured first.** Queue call recording depends on an org-level or location-level recording vendor configuration. Check with `wxcli call-recording show-settings -o json` before enabling queue recording.
15. **Customer Assist queues are hidden from default `call-queue list`.** You must pass `--has-cx-essentials true` to see them. Without the flag, only regular (non-Customer Assist) queues are returned.
16. **Queue recording response uses nested objects.** The API returns `notification: {enabled, type}`, `repeat: {enabled, interval}`, and `startStopAnnouncement: {internalCallsEnabled, pstnCallsEnabled}` — not flat fields. Use the nested structure in `--json-body`.
17. **`create-supervisors` requires `id` in both `--id` flag and `--json-body`.** The `--id` flag is a required CLI option. When using `--json-body`, include `"id"` in the JSON body too, since `--json-body` overrides flag-built body fields.
18. **To remove a Customer Assist supervisor, remove all their agents first.** The DELETE endpoint (`delete-supervisors-config-1`) returns 204 but the supervisor may persist. Instead, use `update-supervisors` with `action: DELETE` on each agent. When the last agent is removed, the supervisor is automatically deleted.
19. **Customer Assist queue creation requires `callPolicies`.** Unlike regular queues, CX queues require the `callPolicies` field (e.g., `{"policy":"SIMULTANEOUS"}`). This must be passed via `--json-body` since it's not available as a CLI flag.

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been configured: run the relevant `show` / `list` commands
3. Resume from the first incomplete step
