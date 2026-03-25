---
name: cucm-migrate
description: |
  Execute a CUCM-to-Webex migration using DB-driven skill delegation. Queries the
  migration database for operation metadata, delegates each operation to a domain skill
  (provision-calling, configure-features, etc.), and tracks results per-operation.
  Use after running the CUCM analysis pipeline (wxcli cucm discover/normalize/map/analyze/plan/export).
allowed-tools: Read, Grep, Glob, Bash, Skill, Agent
argument-hint: [project name]
---

# CUCM Migration Execution Workflow

## Step 1: Load and Verify

1. **Check project exists and pipeline is complete:**
   ```bash
   wxcli cucm status -o json
   ```
   Verify stage is `PLANNED` or later. If not, tell the admin which pipeline stages remain.

2. **Check for pending decisions and generate review file:**
   ```bash
   wxcli cucm decisions --status pending -p <project>
   ```
   If pending decisions exist, generate the review file with JSON output:
   ```bash
   wxcli cucm decisions --export-review -o json -p <project>
   ```
   This does two things:
   - **Writes** `<project>/exports/decision-review.md` for admin offline review
   - **Prints JSON** to stdout with structured `auto_apply` and `needs_input` arrays

   The JSON includes `review_file` (path to the markdown file). Tell the admin:
   > "I've generated a decision review at [review_file path]. There are N
   > auto-apply decisions and M that need your input."

### Phase A: Architecture Review

Before per-decision review, present `ARCHITECTURE_ADVISORY` decisions. Pull them:
```bash
wxcli cucm decisions --type advisory -o json -p <project>
```

Group advisories by category and present:
```
=== Architecture Advisory ===

ELIMINATE (CUCM workarounds to remove):
  - <ID> <summary> [REC: accept] <reasoning>
  - ...

REBUILD (use Webex-native patterns):
  - <ID> <summary> [REC: accept] <reasoning>
  - ...

OUT OF SCOPE (separate workstreams):
  - <ID> <summary> [REC: accept] <reasoning>
  - ...

MIGRATE AS-IS (informational):
  - <ID> <summary> [REC: accept] <reasoning>
  - ...

Accept all advisory recommendations? [Y/n] Or review individually? [r]
```

- If **Y** (default): run `wxcli cucm decide <ID> accept -p <project>` for each advisory
- If **n**: skip advisory resolution (admin will handle later)
- If **r**: present each advisory individually with accept/dismiss options

### Phase B: Per-Decision Review

Present remaining (non-advisory) decisions in three groups:

**Group 1: Auto-apply (clear-cut decisions)** — applied via `--apply-auto`:
- `DEVICE_INCOMPATIBLE` with no migration path → skip
- `MISSING_DATA` on devices that are already incompatible → skip
- `CALLING_PERMISSION_MISMATCH` with 0 affected users → skip (orphaned profile)

**Group 2: Recommended** — decisions where `recommendation` is set.
Present with bulk accept option:
```
RECOMMENDED ({n} decisions):

1. <ID> — <summary>
   Recommended: <option> — <reasoning>. Accept? [Y/n]

2. <ID> — <summary>
   Recommended: <option> — <reasoning>. Accept? [Y/n]

Accept all {n} recommended decisions? [Y/a individual/n reject all]
```

- If **Y** (default): run `wxcli cucm decide <ID> <recommended_option> -p <project>` for each
- If **a**: present each individually
- If **n**: leave all unresolved

**Group 3: Needs input** — no recommendation, present options normally:
```
NEEDS YOUR INPUT (N decisions):

1. <ID> — <summary>
   [a] <option 1>  [b] <option 2>  [c] Skip

2. <ID> — <summary>
   [a] <option 1>  [b] <option 2>  [c] Skip

Reply with your choices: "1a, 2b" or "all a"
```

Rules for the interactive menu:
- **Number each decision** sequentially (1, 2, 3...)
- **Letter each option** (a, b, c...) — map to the actual decision option IDs
- **Show what each option means** in plain language, not internal IDs
- **Accept compact responses** like "1a, 2a, 3b" or "all a"
- **Accept natural language** like "accept for 1, workspace for 2 and 3"
- **Confirm what was applied** with a brief summary
- If the admin changes their mind, re-run `wxcli cucm decide <ID> <new_choice>`

**Do NOT auto-resolve needs-input decisions.** Wait for explicit admin choices.
After receiving choices, run `wxcli cucm decide <ID> <choice> -p <project>` for each.

3. **Apply auto-resolvable decisions:**
   After the admin has resolved all needs-input decisions, show what will be
   auto-applied (read from the Auto-Apply section of the review file):
   ```
   AUTO-APPLYING (N decisions — clear-cut):
     - N incompatible devices → skip (no MPP migration path)
     - N missing data on incompatible devices → skip
     - N orphaned permission profiles → skip
   ```
   Then apply:
   ```bash
   wxcli cucm decide --apply-auto -y -p <project>
   ```

4. **Re-plan and re-export:**
   ```bash
   wxcli cucm plan -p <project> && wxcli cucm export -p <project>
   ```

## Step 2: Auth + Preflight — [MANDATORY, NOT SKIPPABLE]

### 2a. Verify auth token

```bash
wxcli whoami
```

If this fails with 401/403, stop and troubleshoot auth before proceeding.

### 2b. Run preflight checks

```bash
wxcli cucm preflight
```

**Preflight runs 8 checks** against the Webex target org. If ANY check fails, **do NOT proceed to execution.** Show failures with actionable fixes:

| Failure Type | Actionable Fix |
|---|---|
| Number conflicts | "These numbers already exist in Webex. Remove them first, or skip via `wxcli cucm decide`" |
| Duplicate users | "These users already exist. Decide: update in-place or skip" |
| License shortage | "Need N licenses, only M available. Add licenses in Control Hub or reduce scope" |
| Location conflicts | "Location names already exist. Decide: reuse existing or rename" |
| Extension conflicts | "Extensions conflict at target location. Reassign or skip" |
| Missing prerequisites | "Required resources not found in Webex. Provision them first" |

**Preflight failure recovery:**
1. Show failures with specific fix instructions
2. User resolves blockers
3. Re-run: `wxcli cucm preflight` (or `--check <check-name>` for single check)
4. Repeat until all pass

## Step 3: Present Summary and Get Approval

```bash
wxcli cucm export --format deployment-plan
```

Read the generated summary file, then present:

```
=== CUCM Migration Plan Summary ===
Source: [CUCM cluster]
Target: [Webex org]

Resources to migrate:
  Locations:       N to create
  Users:           N to provision
  [etc. — from summary]

Execution:
  Total operations: N in M batches
  [etc.]

Ready to execute? (yes/no)
```

**Wait for explicit "yes" before proceeding.**

## Step 4: Execute via Skill Delegation

This is the core of the workflow. Instead of executing pre-built CLI strings, query the
DB for operation metadata and delegate each operation to a domain skill.

### 4a. Retrieve license ID (once)

```bash
wxcli licenses list --output json
```

Find the license where `name` contains "Calling - Professional" with available capacity.
Store as `CALLING_LICENSE_ID` for user creation operations. If none available, **stop**.

### 4b. Bulk execution

The bulk executor processes all operations concurrently at API throughput (~100 req/min)
instead of one-at-a-time through the conversational loop. Claude is NOT involved during
execution — only for failure diagnosis afterward.

```
1. Preview the execution plan:
   wxcli cucm dry-run

2. Show the admin the dry-run summary (operations, batches, estimated time).
   Get explicit confirmation to proceed.

3. Execute:
   wxcli cucm execute --concurrency 20

   This runs all pending operations using async concurrent API calls.
   Progress is printed per-batch. Failed operations are recorded in the DB.

4. Check results:
   wxcli cucm execution-status -o json

5. IF all completed → proceed to Step 5 (report)

6. IF failures exist:
   Show failure summary to admin.
   FOR EACH failed operation:
     Read the error message from execution-status
     Load the appropriate domain skill (from the dispatch table below)
     Diagnose the failure using the domain skill's knowledge
     Present options: fix+retry | skip | rollback

   After all failures resolved:
     wxcli cucm retry-failed    # resets failed ops to pending
     wxcli cucm execute          # picks up remaining ops

   Repeat until execution-status shows 0 failed, 0 pending.
```

### Skill Dispatch Table

This table is the PRIMARY execution mechanism. The pipeline says WHAT. The domain skills say HOW.

| resource_type | op_type | Delegate To | What the Skill Already Knows |
|--------------|---------|-------------|------------------------------|
| location | create | provision-calling | Two-step: `locations create` + `location-settings create` to enable calling |
| location | enable_calling | provision-calling | Separate API call to enable Webex Calling on the location |
| user | create | provision-calling | Extension required at creation. License via `--license`. Combines create + assign_number + assign_license |
| user | configure_settings | manage-call-settings | Read-before-write. `--json-body` format. Per-setting endpoint paths |
| user | configure_voicemail | manage-call-settings | Same as configure_settings |
| workspace | create | provision-calling | License tier matters. Basic vs Professional determines which settings work |
| workspace | assign_number | provision-calling | Number assignment after workspace creation |
| workspace | configure_settings | manage-call-settings | Workspace settings mirror person settings, Professional license required for some |
| device | create | manage-devices | MAC validation. Activation code generation. `apply-changes-for` after settings |
| device | configure_settings | manage-devices | Device settings, line key templates |
| hunt_group | create | configure-features | Location ID as positional arg. Agents need person IDs. Policy limits |
| call_queue | create | configure-features | Same as HG. Plus routing policy, queue settings |
| auto_attendant | create | configure-features | Menus auto-populated. Schedule must exist first |
| call_park | create | configure-features | Extension required. Location-scoped |
| pickup_group | create | configure-features | Agents need person IDs |
| paging_group | create | configure-features | Targets and originators need person IDs |
| operating_mode | create | configure-features | Schedule — level must be ORGANIZATION |
| schedule | create | configure-features | Location schedule — requires locationId, type (businessHours/holidays), and events with recurWeekly recurrence. Must exist before AA references it |
| trunk | create | configure-routing | Type and location immutable after creation. Requires locationId |
| route_group | create | configure-routing | Requires at least one gateway member |
| dial_plan | create | configure-routing | Org-wide. Patterns as array |
| translation_pattern | create | configure-routing | Name and matching_pattern required |
| shared_line | configure | manage-devices | Device member update + apply-changes-for |
| virtual_line | create | manage-call-settings | Extension required, settings applied after creation |
| virtual_line | configure | manage-call-settings | Virtual line settings |
| calling_permission | create | manage-call-settings | Logical grouping — no standalone API |
| calling_permission | assign | manage-call-settings | Per-user outgoing permission PUT |

### Rollback Dispatch Table

Use `wxcli cucm rollback-ops` (or `--batch <name>` for a single batch) to get the list.
Each entry includes resource_type, webex_id, location_webex_id, and canonical data.

Delete in the order returned (reverse tier: features → devices → users → routing → locations).

| resource_type | Delete Command Pattern | Notes |
|---|---|---|
| paging_group | `wxcli paging-group delete <location_webex_id> <webex_id> --force` | |
| pickup_group | `wxcli call-pickup delete <location_webex_id> <webex_id> --force` | |
| call_park | `wxcli call-park delete <location_webex_id> <webex_id> --force` | |
| auto_attendant | `wxcli auto-attendant delete <location_webex_id> <webex_id> --force` | |
| call_queue | `wxcli call-queue delete <location_webex_id> <webex_id> --force` | |
| hunt_group | `wxcli hunt-group delete <location_webex_id> <webex_id> --force` | |
| schedule | `wxcli location-call-settings-schedules delete <location_webex_id> <schedule_type> <webex_id> --force` | schedule_type from canonical data (businessHours or holidays) |
| operating_mode | `wxcli operating-modes delete <webex_id> --force` | Org-wide |
| device | `wxcli devices delete <webex_id> --force` | No location needed |
| workspace | `wxcli workspaces delete <webex_id> --force` | Deletes associated device too |
| user | `wxcli users delete <webex_id> --force` | Releases number + license |
| translation_pattern | `wxcli call-routing delete-translation-patterns-call-routing <webex_id> --force` | Org-level |
| dial_plan | `wxcli call-routing delete <webex_id> --force` | Remove patterns first |
| route_group | `wxcli call-routing delete-route-groups <webex_id> --force` | Remove from dial plans first |
| trunk | `wxcli call-routing delete-trunks <webex_id> --force` | Remove from route groups first |
| location | `wxcli locations delete <webex_id> --force` | Must be empty first |

**IMPORTANT:** Before deleting locations, verify all users/devices/features at that location
are already deleted. Before deleting trunks, verify no route groups reference them. Before
deleting schedules, verify no auto attendants reference them. The reverse tier ordering
handles this naturally — only override if an op was skipped.

### Delegation examples

**location:create:**
> "Create a Webex Calling location with:
>  - name: [data.name]
>  - timeZone: [data.timeZone]
>  - address: [data.address]
>  The provision-calling skill handles the two-step creation
>  (location create + calling enablement)."

**user:create:**
> "Create a Webex Calling user with:
>  - email: [data.email]
>  - firstName: [data.firstName]
>  - lastName: [data.lastName]
>  - extension: [data.extension]
>  - locationId: [resolved_deps → location webex_id]
>  - license: [CALLING_LICENSE_ID]
>  The provision-calling skill handles extension and license in the create call."

**hunt_group:create:**
> "Create a hunt group with:
>  - name: [data.name]
>  - extension: [data.extension]
>  - enabled: [data.enabled]
>  - locationId: [resolved_deps → location webex_id]
>  - agents: [list of person Webex IDs from resolved_deps as {"id": "WEBEX_ID"}]
>  - callPolicies.policy: [data.policy] (CIRCULAR, REGULAR, SIMULTANEOUS, UNIFORM, WEIGHTED)
>  - callPolicies.noAnswer.nextAgentEnabled: true
>  - callPolicies.noAnswer.nextAgentRings: [data.no_answer_rings or 3]
>  - callPolicies.noAnswer.forwardEnabled: false
>  - callPolicies.noAnswer.numberOfRings: 15
>  - callPolicies.noAnswer.destinationVoicemailEnabled: false
>  The configure-features skill handles the full callPolicies structure.
>  The CLI auto-injects a default callPolicies if omitted, but always pass
>  the canonical policy to preserve the CUCM source configuration."

**trunk:create:**
> "Create a trunk with:
>  - name: [data.name]
>  - locationId: [resolved_deps → location webex_id]
>  - trunkType: [data.trunk_type]  ← REQUIRED, always pass from metadata
>  - password: [data.password]     ← REQUIRED for REGISTERING type
>  - address: [data.address]       ← only for CERTIFICATE_BASED
>  The configure-routing skill handles trunk type and authentication."

**schedule:create:**
> "Create a location schedule with:
>  - locationId: [data.location_id]
>  - name: [data.name]
>  - type: [data.schedule_type] (businessHours or holidays)
>  - events: [data.events] — must use recurWeekly recurrence, NOT recurForEver
>  The configure-features skill handles location schedule creation."

### 4c. Error handling

On any failure:

**IF 409 Conflict (resource already exists):**
→ Search for existing resource: `wxcli [resource] list --name/--email "..." -o json`
→ If found and matches: `wxcli cucm mark-complete [node_id] --webex-id [existing_id]` — continue
→ If found but different: present to admin for decision

**IF 400/500 (may have partially created):**
→ Search for existing resource (same as 409 flow)
→ If found: resource was created despite error, mark-complete
→ If not found: genuine failure, present options

**ALL OTHER errors:**
→ `wxcli cucm mark-failed [node_id] --error "[message]"`
→ Present options:
  (A) Fix and retry — domain skill diagnoses and suggests fix
  (B) Skip this step — `wxcli cucm mark-failed [node_id] --error "..." --skip`
  (C) Rollback this batch
  (D) Rollback all

**NEVER fall back to raw HTTP.** If a wxcli command fails, diagnose the CLI issue.
The `--json-body` bypass fix means all create commands accept JSON body without
needing individual flags. If a CLI command is genuinely broken, flag it for a
generator fix.

## Step 5: Report Results

```bash
wxcli cucm execution-status -o json
```

Generate report from the JSON:

```
=== CUCM Migration Execution Report ===
Source: [CUCM cluster]
Target: [Webex org]
Date: [timestamp]

Summary:
  Planned:    N operations
  Succeeded:  M
  Failed:     K
  Skipped:    J

Resources created:
  [from execution-status by_resource_type breakdown]

Failed operations:
  [list failures with error messages]

Next steps:
  [manual post-migration tasks]
```

Save to `docs/plans/YYYY-MM-DD-cucm-migration-report.md`.

---

## Critical Rules

1. **Preflight is mandatory.** No override or bypass.
2. **Always show plan summary and get approval.** Wait for explicit "yes".
3. **Execute via domain skill delegation.** Read the dispatch table. Load the skill. Pass the data. Let the skill build the commands.
4. **Always use `mark-complete` and `mark-failed`.** Never update the migration database directly.
5. **On any create failure, always check for existing resource before retry.** Partial creates leave orphaned resources that cause 409 on retry.
6. **Never fall back to raw HTTP.** Fix the CLI command. Don't work around it.
7. **If `next-batch` returns empty but `execution-status` shows pending ops, there's a dependency deadlock.** Show the failed/skipped dependencies and let the admin decide.
8. **Rollback in reverse dependency order.** Feature deletes need location ID + resource ID.
9. **The deployment plan is a summary for admin review.** Not executable commands. Never hand-edit it.
10. **License ID must be retrieved before user creation.** Fetch once, use for all user:create ops.

---

## Context Compaction Recovery

Simplified — no markdown plan to re-parse:

1. `wxcli cucm execution-status -o json` → see what's done
2. `wxcli cucm next-batch -o json` → see what's next
3. Resume from Step 4b
