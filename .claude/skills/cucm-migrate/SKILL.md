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

   **Auto-apply (clear-cut decisions)** — applied via `--apply-auto`:
   - `DEVICE_INCOMPATIBLE` with no migration path → skip
   - `MISSING_DATA` on devices that are already incompatible → skip
   - `CALLING_PERMISSION_MISMATCH` with 0 affected users → skip (orphaned profile)

   **Needs your input** — decisions requiring admin judgment, grouped by category
   (location, device, workspace, routing, etc.)

3. **Present the needs-input decisions to the admin:**
   Use the `needs_input` array from the JSON output (not the markdown file) to
   present decisions. For each decision show the ID, severity, summary, and
   available options with letter labels.

   Present as a numbered interactive menu:
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

4. **Apply auto-resolvable decisions:**
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

5. **Re-plan and re-export:**
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

### 4b. Main execution loop

```
REPEAT:
  batch_json = wxcli cucm next-batch -o json
  IF batch is empty: BREAK (all done)

  Show: "Batch: [batch name], Tier [N], [count] operations"

  FOR EACH operation in batch:
    1. Show progress:
       "Step [N/M]: [op_type] [resource_type] — [description]"

    2. Read the operation's resource_type and op_type

    3. **Invoke the domain skill using the Skill tool.** Look up the skill name
       from the dispatch table below, then call:
       ```
       Skill("provision-calling")   # for locations, users, workspaces
       Skill("configure-features")  # for HG, CQ, AA, parks, pickups, schedules
       Skill("configure-routing")   # for trunks, route groups, dial plans
       Skill("manage-devices")      # for devices
       Skill("manage-call-settings") # for user/workspace settings
       ```
       The domain skill loads its full execution knowledge — CLI commands,
       gotchas, prerequisites, multi-step sequences. This is NOT optional.
       Do NOT manually construct wxcli commands. The skill handles it.

    4. With the domain skill loaded, tell it what to create using the
       operation data:
       - Pass the canonical data fields as the resource properties
       - Pass resolved_deps for any dependency IDs (e.g., location Webex ID)
       - For user:create, also pass CALLING_LICENSE_ID
       - The domain skill will build and execute the correct CLI command(s)

    5. Capture the Webex resource ID from the domain skill's output

    6. Record the result:
       wxcli cucm mark-complete [node_id] --webex-id [captured_id]
       OR
       wxcli cucm mark-failed [node_id] --error "[error message]"

  After each batch, verify key resources:
    wxcli locations show [id] --output json
    wxcli users show [id] --output json
    [etc.]
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
| schedule | create | configure-features | Must exist before AA references it |
| trunk | create | configure-routing | Type and location immutable after creation. Requires locationId |
| route_group | create | configure-routing | Requires at least one gateway member |
| dial_plan | create | configure-routing | Org-wide. Patterns as array |
| translation_pattern | create | configure-routing | Name and matching_pattern required |
| shared_line | configure | manage-devices | Device member update + apply-changes-for |
| virtual_line | create | manage-call-settings | Extension required, settings applied after creation |
| virtual_line | configure | manage-call-settings | Virtual line settings |
| calling_permission | create | manage-call-settings | Logical grouping — no standalone API |
| calling_permission | assign | manage-call-settings | Per-user outgoing permission PUT |

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
>  - locationId: [resolved_deps → location webex_id]
>  - agents: [list of person Webex IDs from resolved_deps]
>  - policy: [data.callPolicies.policy]
>  The configure-features skill handles agent assignment."

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
