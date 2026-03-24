# Post-Mortem: CUCM Migration Pipeline — Design-to-Execution Gap

**Date:** 2026-03-23
**Scope:** 22+ bugs found across 3 rounds of live testing after 11 build phases, 1294 tests, 43/43 review checks

---

## Executive Summary

The CUCM migration pipeline's upstream data model (phases 01-07) is solid. The failures concentrate in the export/execution layer (phases 09-11), which generated static CLI commands from design specs while ignoring the domain knowledge already encoded in the playbook's working execution path.

**The central finding:** The day before the migration pipeline failed at creating locations and users, the wxc-calling-builder agent successfully performed those same operations using domain skills. The pipeline's export layer bypassed everything the skills already knew — that locations need a separate calling-enablement step, that users need extensions at creation time, that `--json-body` doesn't bypass required CLI flags. We built a parallel execution path that ignored everything we'd already learned.

**The central recommendation:** Phase 12b's execution layer should delegate to domain skills at runtime, not generate static CLI commands. The migration plan provides WHAT; the skills provide HOW. This is already stated in the cucm-migrate skill (Step 5: "Delegate to domain skills") but the pre-generated commands in the deployment plan make delegation impossible — the commands are baked before the skill runs.

---

## 1. Root Cause Analysis

### Bug Classification by Root Cause

#### Category A: Wrong API Assumptions (5 bugs)

Commands generated from design specs without verifying against real API behavior.

| Bug | What Happened | What Should Have Caught It |
|-----|--------------|---------------------------|
| Location create doesn't enable calling | `POST /v1/locations` creates location but calling requires separate `POST /telephony/config/locations`. Pipeline only generated the first step | **05b-executor-api-mapping.md line 75 already specified `location:enable_calling` as a separate Tier 0 op.** The command_builder.py in Phase 09 didn't implement it. A single manual test would have caught this instantly |
| User create requires extension at creation time | Plan separated user creation (steps 3-6) and extension assignment (steps 12-15). API requires extension in the create body for calling users | The `provision-calling` skill already knows this. 05b says `user:assign_number` is a separate op. **The design spec was wrong** — nobody validated it against the API |
| `wxcli users create` passes `callingData=false` | `users.py` doesn't pass `calling_data=True` to wxc_sdk | CLI was never tested for calling user creation. Live API sweep Batches 1-4 tested read operations and feature configuration, not user provisioning |
| Route group requires at least one gateway | "Standard Local Route Group" created with empty gateway list | `configure-routing` skill knows this. Command builder didn't validate the data |
| Trunk creation requires `locationId` | Command builder omits `locationId` for trunks | `configure-routing` skill includes location in trunk creation. Design spec (05b) shows `locationId` in the trunk create body. Command builder didn't read the spec |

**Pattern:** The command_builder.py was written to map canonical objects to CLI strings. It was not written by someone who had actually created these resources via the CLI or API. The domain skills were written by someone who had.

#### Category B: Mapper Output Not Validated Against API Inputs (5 bugs)

Mappers produce data shapes that can't be consumed by the Webex API.

| Bug | What Happened | What Should Have Caught It |
|-----|--------------|---------------------------|
| Hunt group agents are raw CUCM DNs | Feature mapper stores `dn:1002:PT` references instead of resolving to user canonical IDs | An integration test that feeds mapper output into command_builder would have produced obviously broken `--json-body` payloads |
| Pickup group agents are raw CUCM UUIDs | Same pattern — CUCM UUIDs instead of canonical IDs | Same — the output is visibly wrong if you look at the generated command |
| Call settings `{...}` stubs | Command builder outputs literal `{...}` instead of actual settings JSON | Command builder has no code to serialize settings. Was never tested with real data |
| Empty translation patterns | Mapper creates patterns with empty `name` and `matching_pattern` | Missing data analyzer has no `translation_pattern` entry in `_REQUIRED_FIELDS` |
| User count inflated | 10 "users" in plan but only 4 have emails/locations | Missing data analyzer doesn't check users for email or location_id |

**Pattern:** Mapper output was tested for internal shape correctness (Pydantic validation passes), not for downstream consumability (can a Webex API call be built from this data?).

#### Category C: CLI Not Ready for Programmatic Use (4 bugs)

The CLI was built for interactive human use, not as an execution layer for automated migration.

| Bug | What Happened | What Should Have Caught It |
|-----|--------------|---------------------------|
| `--json-body` doesn't bypass required CLI flags | Click validates required options before command body runs. `--json-body '{"name": "foo"}'` fails without `--name x` | Any programmatic use of `--json-body` on a create command. Never tested |
| `wxcli users create` has no `--extension` flag | Calling user creation requires extension. CLI has no way to pass it | Using the CLI to create a calling user — the primary migration use case |
| Failed user create leaves orphaned resources | People API creates user, then calling setup fails. Retry gets 409 | Any create failure scenario during automated execution |
| Skill falls back to raw HTTP repeatedly | CLI couldn't handle the actual migration workflow, so the skill abandoned it | This is the aggregate symptom of all Category C bugs |

**Pattern:** The CLI was live-tested in Batches 1-4 for read operations, settings queries, and feature configuration. It was never tested for the create-resource-with-all-dependencies workflow that migration requires.

#### Category D: Missing Pipeline Steps / Data (5 bugs)

The pipeline doesn't generate operations or data that the Webex API requires.

| Bug | What Happened | What Should Have Caught It |
|-----|--------------|---------------------------|
| No `location:enable_calling` operation | Planner doesn't generate enable_calling after location create | Design spec (05b) has it. Planner didn't implement it |
| Feature mapper doesn't populate `location_id` | Hunt groups, AAs, pickup groups all have `location_id=None` | Any query that joins features to locations. Integration test with real mapper output |
| User→location cross-refs missing | DAG has no edges from user ops to location create ops | Dependency graph test with real planner output |
| Schedules not stored as `schedule` object type | Store has 0 schedule objects but plan has 2 schedules | Store query for schedules returns empty |
| Duplicate/junk pickup groups | 3 pickup group objects for 1-2 actual groups, one with hash as name | Normalizer creates duplicates with corrupt data |

**Pattern:** These are data-quality bugs in the upstream pipeline that were invisible because no test ever fed real pipeline output into the execution layer.

#### Category E: Architecture Mismatch (3 bugs)

The static deployment plan architecture can't handle the complexity of real execution.

| Bug | What Happened | What Should Have Caught It |
|-----|--------------|---------------------------|
| `{LOCATION_ID}` placeholder not resolved to step reference | Generic placeholder instead of `{STEP_N_ID}` because location_id is null | Placeholder resolution is fragile by design — requires perfect upstream data |
| Resources table includes CUCM source objects | Plan lists partitions, CSSes, device pools as "Create" items | Looking at the generated plan output |
| No-op license assignment steps | 4 comment-only steps cluttering the plan | Looking at the generated plan output |

**Pattern:** The static markdown plan with `{STEP_N_ID}` placeholders is fundamentally fragile. It requires every upstream component to produce perfect data, and there's no runtime validation or recovery.

---

## 2. Process Gaps (ordered by severity)

### Gap 1: No end-to-end spike before building the export layer (would have prevented 18 of 22 bugs)

**What was missing:** Before designing Phase 09 (Export) and Phase 11 (Skill), nobody manually ran the equivalent of the migration workflow: create 1 location → enable calling → create 1 user with extension → create 1 hunt group with that user as agent. This would have taken 30 minutes and would have surfaced:
- Location requires separate calling enablement (Category A)
- User requires extension at creation time (Category A)
- `--json-body` doesn't bypass required flags (Category C)
- `wxcli users create` has no `--extension` flag (Category C)
- Feature agents need resolved person IDs, not CUCM DNs (Category B)

**Why it didn't happen:** The build plan went directly from Phase 07 (Planning) → Phase 08 (CLI) → Phase 09 (Export) → Phase 10 (Preflight) → Phase 11 (Skill). There was no "Phase 08.5: manual execution spike" step. The assumption was that the design specs (especially 05b-executor-api-mapping.md) had already captured the API requirements. They hadn't — 05b was written from reference docs, not from live API experience.

**Contrast with CUCM side:** Phase 03 (Extraction) WAS tested against a live CUCM cluster and found 4 bugs immediately. The Webex side had no equivalent live validation step until after all 11 phases were complete.

### Gap 2: Export layer built without consulting domain skills (would have prevented 12 of 22 bugs)

**What was missing:** The command_builder.py (Phase 09) maps 27 operation types to CLI command strings. It was built by reading the design spec (05b) and the CLI `--help` output. It was NOT built by reading the domain skills that already encode how to create each resource type.

The `provision-calling` skill knows:
- Locations need calling enablement after creation
- Users need extension at creation time
- `announcement_language` must be lowercase
- `location_id` is write-once on users

The `configure-features` skill knows:
- Hunt groups need location ID as a positional arg
- Agent assignment requires person IDs
- Call queue routing policy limits

The `configure-routing` skill knows:
- Trunk type and location are immutable after creation
- Route groups require at least one gateway
- Strict dependency chain: trunk → route group → dial plan

**None of this knowledge was consulted when building command_builder.py.**

**Why it didn't happen:** The domain skills are prompt files (SKILL.md) consumed by Claude at runtime. The command builder is Python code. There was no process step that said "before writing the command builder for resource type X, read the skill that creates resource type X." The skills were treated as a downstream consumer of the export, not as a source of truth for how to build commands.

### Gap 3: Testing strategy tested internal consistency, not external correctness (would have prevented 15 of 22 bugs)

**What the 1294 tests verify:**
- Pydantic model round-trips work
- Normalizers produce correct canonical shapes from CUCM dicts
- Mappers produce correct Webex objects from canonical shapes
- Analyzers detect correct conflict patterns
- Planner builds correct DAG structure
- Command builder produces syntactically valid CLI strings
- Preflight checks detect known collision patterns

**What the 1294 tests do NOT verify:**
- Can the command builder's output actually be executed against a Webex org?
- Does the CLI accept the flags and values the command builder generates?
- Are the data values in mapper output valid for the Webex API?
- Does the generated deployment plan contain all necessary steps in the right order?

The build contracts (§4 Testing Strategy) explicitly state: Phase 8 tests use "Mocked Webex API responses." Phase 10 tests are "Human review" with "None" for test fixtures. The testing strategy never planned for live API validation.

### Gap 4: Revised phases had no acceptance criteria (would have caught 8 of 22 bugs)

**What happened:** The original Phases 08-12 had detailed acceptance criteria in `cucm-build-contracts.md` (§2). When the architecture was revised to use the CLI + skill approach instead of a standalone executor, the acceptance criteria were not updated. The revised Phase 09 (Export) had no criteria like "command builder output for location:create must match what `provision-calling` skill produces" or "every generated command must be runnable via `wxcli` without errors."

The 43/43 review checks from `review-build-planning.md` checked: does each phase have acceptance criteria, do contracts match, do fixtures cover edge cases. They did not check: are the acceptance criteria sufficient to catch execution-layer bugs.

### Gap 5: Code reviews checked code quality, not API correctness (would have caught 5 of 22 bugs)

**What the 5-agent code review swarms checked:**
- Code matches the design spec
- Contracts are satisfied
- No regressions from prior phases
- Naming conventions, error handling, test coverage

**What they did not check:**
- Does the design spec match API reality?
- Can the output of this code actually be used to call the Webex API?
- Has anyone run `wxcli <command> --help` to verify the flags exist?

The reviews validated implementation fidelity to the spec. The spec was wrong in several places (user:assign_number as separate op, no location:enable_calling in command builder, etc.). Reviewing code against a wrong spec produces code that faithfully implements the wrong thing.

---

## 3. What Went Right

Not everything failed. These deserve to be preserved:

1. **CUCM extraction (Phase 03) was live-tested immediately** against a real CUCM 15.0 cluster. Found 4 bugs in the first run. This is the model — build it, test it against reality, fix what breaks.

2. **The data model is solid.** Canonical objects, cross-references, the SQLite store, Pydantic validation, fingerprint-based decision merge — all work correctly. The upstream pipeline (phases 01-07) produces correct data shapes.

3. **The decision system works.** Decisions, options, auto-rules, cascading re-evaluation, three-way merge — all function as designed. The 12 analyzers correctly identify conflicts.

4. **The design review process caught internal consistency issues.** Cross-mapper synthesis review found structural inconsistencies. Code review swarms caught real code bugs (wrong field names, wrong types, missing null handling). The reviews work for what they check.

5. **The domain skills encode real API knowledge.** The playbook builder agent successfully provisions resources because the skills were built from live API testing (Batches 1-4). This knowledge exists — it just wasn't consulted when building the migration export layer.

**Why did live-testing work on the CUCM side but not the Webex side?**

Phase 03 (Extraction) was the first phase to touch an external system. The build plan explicitly included "validate against live CUCM" as a step. The Webex side didn't have an equivalent step because:
- The revised architecture assumed the CLI was a proven execution layer (it was — for reads, not writes)
- The export layer produces a plan for a *human-guided skill* to execute, not code. Testing "does the skill work" requires running the whole skill end-to-end, which felt like it should be Phase 11's scope
- Phase 11's acceptance criteria were "Human review" with no test fixtures — the entire execution path was validated by reading the skill, not by running it

---

## 4. Recommended Process Changes

### Change 1: Execution layer delegates to domain skills, not static CLI commands

**This is the architectural fix.** It reframes Phase 12b.

**Current model (broken):**
```
Pipeline DB → command_builder.py → static CLI strings in markdown → skill reads markdown → executes CLI strings
```

The command builder must encode every API quirk for every resource type. It duplicates knowledge that already exists in the domain skills. When it gets something wrong, the skill has no way to recover — it's executing pre-baked strings.

**Proposed model:**
```
Pipeline DB → runtime query (next-batch) → skill reads operation metadata → skill delegates to domain skill → domain skill builds and executes the command
```

The pipeline tells the skill WHAT to create (resource type, canonical data, dependencies). The domain skill decides HOW (which CLI flags, what order, what validation). This is exactly what the cucm-migrate skill's Step 5 ("Delegate to domain skills") was supposed to do, but the pre-generated commands in the deployment plan made delegation impossible.

**What this looks like concretely:**

1. **`wxcli cucm next-batch`** returns a JSON array of operations for the next executable batch:
   ```json
   [
     {"op_id": "op_042", "resource_type": "location", "op_type": "create",
      "canonical_id": "location:dp-abc123", "data": {"name": "HQ-Phones", "timeZone": "America/Chicago", ...},
      "dependencies_met": true}
   ]
   ```

2. **The cucm-migrate skill** reads each operation's `resource_type` and `op_type`, then delegates:
   - `location:create` → reads `provision-calling` skill → executes location creation + calling enablement (the skill already knows the two-step dance)
   - `user:create` → reads `provision-calling` skill → creates user with extension, license, location in one call (the skill already knows extension is required at create time)
   - `hunt_group:create` → reads `configure-features` skill → creates HG with resolved agent person IDs (the skill already knows agents need person IDs)

3. **`wxcli cucm mark-complete <op_id> --webex-id <id>`** records the result. Next call to `next-batch` returns the next tier.

4. **The deployment plan becomes a summary** — resource counts, decision summary, batch overview. Not executable commands. The admin reviews WHAT will happen, not HOW.

**What this prevents:**
- All 5 Category A bugs (wrong API assumptions) — domain skills already know the right API patterns
- All 4 Category C bugs (CLI readiness) — skills adapt to CLI limitations at runtime, use `--json-body` correctly or fall back
- All 3 Category E bugs (architecture mismatch) — no static placeholder resolution, no fragile command strings
- 3 of 5 Category B bugs (call settings stubs, empty patterns, inflated user count would be caught by skills reading real data at runtime)

**What this does NOT prevent:**
- Category D bugs (missing pipeline steps, null location_ids) — these are upstream data-quality issues. Phase 12a fixes these regardless of execution architecture.

**Bugs prevented:** 15 of 22 (all execution-layer bugs). Combined with 12a upstream fixes (7 remaining bugs), this covers 22 of 22.

### Change 2: Spike-first development for any phase that touches external systems

**Rule:** Before designing a phase that generates output consumed by an external system (Webex API, CLI execution, third-party integration), run a manual spike:
1. Manually perform the operation the phase will automate (e.g., create 1 location + 1 user + 1 hunt group via CLI)
2. Document every flag, every gotcha, every multi-step sequence
3. Compare against the design spec — fix discrepancies BEFORE building

**Would have prevented:** 18 of 22 bugs (all of Gap 1). A 30-minute spike before Phase 09 would have found the location enablement issue, user extension requirement, `--json-body` flag conflict, and missing `--extension` flag.

**When to apply:** Any phase that produces commands, API calls, or configuration that will be executed against a live system. Does NOT apply to purely internal phases (normalizers, mappers, analyzers).

### Change 3: Domain skill review gate for export/execution code

**Rule:** Before merging any code that generates commands for a resource type, verify the generated command matches what the corresponding domain skill produces for the same operation. Concretely:

1. Read the domain skill's section for that resource type
2. Compare the CLI command the skill would run vs. what the code generates
3. If they differ, the code is wrong until proven otherwise (the skill was live-tested)

**Would have prevented:** 12 of 22 bugs (all of Gap 2).

### Change 4: Progressive execution testing

**Rule:** Test execution incrementally, not all-at-once:
1. After building location commands → test: create 1 location, enable calling
2. After building user commands → test: create 1 user at that location with extension
3. After building feature commands → test: create 1 hunt group with that user as agent
4. After building routing commands → test: create 1 trunk, 1 route group, 1 dial plan

Each step validates the prior step's output. Bugs surface at the earliest possible point.

**Would have prevented:** Finding all 22 bugs in Round 3 (after 32 steps) vs. finding them one at a time during development.

---

## 5. Testing Strategy Update

### What exists (keep)

The 1294 unit tests verify internal pipeline correctness and should remain:
- Pydantic round-trip tests (foundation)
- Normalizer shape tests (pass 1)
- Cross-reference relationship tests (pass 2)
- Mapper output tests (canonical object correctness)
- Analyzer decision tests (conflict detection)
- Planner DAG tests (dependency ordering)
- CLI command tests (argument parsing)

### What to add

#### Test Level 1: Command Validity Tests (automated, no API)

For each of the 27 operation types in command_builder.py, verify:
1. The generated CLI command parses without error: `wxcli <group> <command> --help` confirms all flags exist
2. Required flags are present (or correctly handled via `--json-body`)
3. The `--json-body` payload is valid JSON with all required fields

**Implementation:** Parametrized pytest that runs `wxcli <command> --help` via subprocess and checks flag existence. No API call needed. Catches Category C bugs.

**When to run:** After any change to command_builder.py or the CLI generator.

#### Test Level 2: Data Completeness Tests (automated, no API)

End-to-end pipeline test with fixture data through all stages:
1. Seed a CUCM-shaped fixture (use existing test fixtures from Phase 05)
2. Run: normalize → map → analyze → plan → export
3. Assert every generated command has:
   - No `None` or empty string values in required fields
   - No raw CUCM IDs (UUIDs matching `{8-4-4-4-12}` pattern) in Webex-facing fields
   - No `{...}` placeholder stubs in `--json-body`
   - Valid `{STEP_N_ID}` references (each referenced step exists and is a create op)
   - `location_id` populated for all location-scoped resources

**Implementation:** Single integration test that walks the generated deployment plan and validates every command string. Catches Category B and D bugs.

**When to run:** After any change to mappers, planner, or command builder.

#### Test Level 3: Live Smoke Test (manual, requires API — run before declaring any execution phase complete)

Create a minimal set of real resources:
1. Create 1 location + enable calling
2. Create 1 user with extension at that location
3. Create 1 hunt group with that user as agent
4. Create 1 trunk + 1 route group
5. Clean up (delete in reverse order)

**Implementation:** Shell script or manual checklist. Takes ~10 minutes.

**When to run:** Before declaring Phase 12b complete. Before any future phase that changes the execution path. This is the spike from Change 2 codified as a test.

#### Test Level 4: Skill-Command Comparison (automated, no API)

For each resource type, compare:
1. What the domain skill says to do (extracted from SKILL.md)
2. What the command builder generates

This is a documentation-level check, not a code test. Maintained as a checklist in the test directory.

**When to run:** Any time command_builder.py is modified.

### What the testing strategy missed (diagnosis)

The build contracts (§4) defined testing as fixture-driven with mocked APIs. This was appropriate for phases 01-07 (internal pipeline). It was not appropriate for phases 09-11 (execution layer). The gap: **no testing tier was defined for "does the output work against a real system?"**

The original Phase 8 acceptance criteria included "Mocked Webex API responses for: location create, person create, device activation, license assignment, number assignment." Mocking the API means the test passes regardless of whether the real API would accept the request. The mock returns whatever you tell it to return.

**The minimum test that would have caught the majority of these bugs:** Test Level 3 above — create 1 location + 1 user + 1 feature via the generated commands. This single test would have caught 14 of 22 bugs on the first run.

---

## 6. The Architectural Question: What Does the 12b Rewrite Look Like?

This section answers the prompt's key question directly.

### Current State

```
command_builder.py (27 op types → static CLI strings)
    ↓
deployment_plan.py (markdown with embedded commands)
    ↓
cucm-migrate skill (reads markdown, resolves {STEP_N_ID}, executes strings)
    ↓
domain skills (Step 5 — supposed to be consulted, but pre-baked commands bypass them)
```

### Proposed State

```
Pipeline DB (objects, plan_operations, plan_edges — already exists)
    ↓
wxcli cucm next-batch (reads DB, returns JSON of ready operations)
    ↓
cucm-migrate skill (reads operation metadata, delegates by resource_type)
    ↓
domain skills (build and execute the actual commands with full API knowledge)
    ↓
wxcli cucm mark-complete (records webex_id, unlocks dependent ops)
```

### What Changes in 12b

#### Keep (from current 12b plan)
- `wxcli cucm next-batch` — query DB for next executable batch
- `wxcli cucm mark-complete` / `mark-failed` — record results
- Summary-only deployment plan (resource counts, not commands)
- `plan_operations` status tracking in DB

#### Change (vs. current 12b plan)
- **Delete command_builder.py entirely.** The runtime command builder proposed in 12b's current design still generates CLI strings at runtime. The whole point is to NOT generate CLI strings — let the domain skills do it.
- **The skill becomes a dispatcher, not a command executor.** Instead of:
  ```
  skill reads: "wxcli locations create --json-body '{...}'"
  skill runs: that exact string
  ```
  It becomes:
  ```
  skill reads: {resource_type: "location", op_type: "create", data: {name: "HQ", timeZone: "America/Chicago", address: {...}}}
  skill delegates to provision-calling: "Create a location named HQ in America/Chicago timezone with this address"
  provision-calling runs: wxcli locations create + wxcli location-settings create (two-step dance it already knows)
  ```

#### The Skill Dispatch Table

The cucm-migrate skill already has this table in Step 5. It becomes the primary execution mechanism:

| resource_type | op_type | Delegate To | What Skill Does |
|--------------|---------|-------------|-----------------|
| location | create | provision-calling | Creates location + enables calling (two steps) |
| location | enable_calling | provision-calling | Already handled by create delegation |
| user | create | provision-calling | Creates user with extension, license, location in one call |
| user | assign_number | (merged into create) | Skill knows extension goes in the create call |
| user | assign_license | (merged into create) | Skill knows license goes in the create call |
| user | configure_settings | manage-call-settings | Reads settings from DB data, applies via wxcli |
| user | configure_voicemail | manage-call-settings | Same |
| hunt_group | create | configure-features | Creates HG with agents (resolved person IDs from DB) |
| call_queue | create | configure-features | Creates CQ with agents and policies |
| auto_attendant | create | configure-features | Creates AA with menus |
| trunk | create | configure-routing | Creates trunk with location and type |
| route_group | create | configure-routing | Creates RG with gateway members |
| dial_plan | create | configure-routing | Creates dial plan with patterns |
| translation_pattern | create | configure-routing | Creates pattern |
| device | create | manage-devices | Creates device, generates activation code |
| workspace | create | provision-calling | Creates workspace with license tier |
| pickup_group | create | configure-features | Creates pickup group with agents |
| paging_group | create | configure-features | Creates paging group |
| call_park | create | configure-features | Creates call park |
| operating_mode | create | configure-features | Creates operating mode |
| schedule | create | configure-features | Creates schedule |

#### What the Skill Prompt Looks Like

The revised cucm-migrate skill Step 4 becomes:

```
For each operation in the batch:
1. Run `wxcli cucm next-batch -o json` to get ready operations
2. For each operation:
   a. Read the operation's resource_type and op_type
   b. Load the corresponding domain skill (see dispatch table)
   c. Pass the operation's `data` field to the skill as context:
      "Create a [resource_type] with these properties: [data as key-value pairs]"
   d. The domain skill builds and runs the wxcli command(s)
   e. Capture the Webex resource ID from the result
   f. Run `wxcli cucm mark-complete <op_id> --webex-id <id>`
3. On failure:
   a. Run `wxcli cucm mark-failed <op_id> --error "<message>"`
   b. Present options: fix/skip/rollback (same as current skill)
```

#### What This Eliminates

- `command_builder.py` (580+ lines of brittle CLI string generation) — deleted
- `{STEP_N_ID}` placeholder resolution — eliminated (IDs resolved from DB at runtime via `mark-complete`)
- `{CALLING_LICENSE_ID}` placeholder — eliminated (skill fetches license ID once, passes to provision-calling)
- `deployment_plan.py` command generation — simplified to summary-only
- Category A, C, and E bugs — structurally impossible because domain skills build commands, not the pipeline

#### What This Preserves

- The full upstream pipeline (phases 01-07) — untouched
- The DB schema (plan_operations, plan_edges) — untouched
- `next-batch` / `mark-complete` / `mark-failed` CLI commands — same as 12b plan
- Preflight checks — untouched
- The decision system — untouched
- Batch-by-batch execution with user approval — same pattern
- Rollback capability — domain skills know how to delete resources

