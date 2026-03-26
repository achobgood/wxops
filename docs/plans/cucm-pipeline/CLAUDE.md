# CUCM Pipeline Architecture Specs

This directory contains the 8 authoritative architecture specs for the CUCM-to-Webex migration tool. These docs define the SQLite data store, two-pass ELT normalization, conflict detection (12 linter-pattern analyzers), field-level transform mappers (14 mappers), CSS decomposition algorithm, NetworkX dependency graph, interactive decision workflow, and idempotency/resumability. **Where these docs and the summary in `cucm-pipeline-architecture.md` conflict, these docs are authoritative.**

## Production Sequence

Q1-Q7 architecture docs first, then 03b mapper design (5 review rounds, 1016 lines), then synthesis review.

## Key Cross-References

- **02 -> 03b**: The cross-reference manifest (27 rows) in `02-normalization-architecture.md` feeds the mappers in `03b-transform-mappers.md`. Mappers consume resolved canonical objects post-normalization.
- **04 -> 03b**: The CSS decomposition algorithm in `04-css-decomposition.md` is implemented by `css_mapper` (mapper 8) in `03b-transform-mappers.md`.
- **03 <-> 03b**: Analyzers in `03-conflict-detection-engine.md` run AFTER mappers. Mappers produce per-object decisions; analyzers produce cross-object sweep decisions and skip objects that already have mapper-produced decisions of the same type.
- **05 -> all**: `05-dependency-graph.md` defines the execution order (static tiers + intra-tier DAG) that `engine.py` follows when running mappers and analyzers.

## Gap Design Docs (Phase 3a) — All Complete

- `02b-cucm-extraction.md` -- AXL + CUPI extraction design (8 extractors + Unity Connection REST client, returnedTags, zeep→canonical mappings, 27 cross-ref sources; AXL fields validated against live CUCM 15.0 in Phase 03; 4 CUPI paths remain unverified)
- `05a-preflight-checks.md` -- Preflight check design (7 checks, NUMBER_CONFLICT + DUPLICATE_USER algorithms, decision integration, performance budget)
- `05b-executor-api-mapping.md` -- Executor API mapping design (30+ operations, per-operation request builders, snapshot/rollback spec, PSTN coexistence, dry-run format)

## Verification Status

**02b-cucm-extraction.md:** 24 of 29 items verified against live CUCM 15.0 and WSDL schema (2026-03-23). Spec §6 now reflects all resolutions. Key corrections to original spec:
- `huntTimerCallPick` does NOT exist — use `rnaReversionTimeOut` on LineGroup
- `overflowDestination` does NOT exist — overflow via nested `queueCalls.{queueFullDestination, maxWaitTimeDestination, noAgentDestination}`
- `queueCalls` is complex type `XCallsQueue` with 8 nested fields (not a simple boolean)
- `distributionAlgorithm` is on LineGroup (not HuntList)
- CTI RP has NO schedule field — time-based routing via partition `timeScheduleIdName`
- `enableExtensionMobility` on Phone (not `hotelingEnabled`)
- `calendarPresence` on Phone via getPhone (not listPhone)
- SIP trunk destinations use `destinations.destination[]` array (not flat fields)
- Route pattern destination requires `getRoutePattern` (not available on list)
- VM profile pilot is complex type `{dirn, cssName, uuid}` (not simple ref)

**Remaining:** 4 CUPI endpoint items (blocked on Unity Connection availability). 1 item deferred (incremental timestamps).

4 open questions in `05a-preflight-checks.md` — unchanged. All other docs clean.

## Build Status

All 8 architecture docs have been implemented through the build phases:
- **01 (data representation)**: `store.py` + SQLite schema — Phase 01
- **02 (normalization)**: `normalizers.py` + `cross_reference.py` — Phase 04
- **02b (extraction)**: `extract/` module — Phase 03 (validated against live CUCM 15.0)
- **03 (conflict detection)**: `analyzers/` (12 analyzers) + `analysis_pipeline.py` — Phase 06
- **03b (mappers)**: `mappers/` (14 mappers) + `engine.py` — Phase 05
- **04 (CSS decomposition)**: Implemented in `css_mapper.py` — Phase 05
- **05 (dependency graph)**: `execute/` (planner, dependency, batch) — Phase 07
- **06 (decision workflow)**: CLI in `commands/cucm.py` (decisions/decide) — Phase 08
- **07 (idempotency)**: `store.merge_decisions()` + fingerprint on Analyzer ABC — Phase 06

## Phase 09 Export (2026-03-24)

Phase 09 added the export layer that bridges the SQLite plan to the wxc-calling-builder agent:
- `src/wxcli/migration/export/command_builder.py` — maps all 27 (resource_type, op_type) combos to wxcli CLI command strings
- `src/wxcli/migration/export/deployment_plan.py` — generates 7-section deployment plan matching `docs/templates/deployment-plan.md`
- `src/wxcli/migration/export/json_export.py` and `csv_export.py` — full data export
- `src/wxcli/commands/cucm.py` updated to delegate to export modules, writes to `<project>/exports/`, copies plan to `docs/plans/`

**Key design decisions:**
- `--json-body` overrides all individual flags in wxcli generated commands. All builders that need JSON body put ALL fields in the body (location with address, trunk with trunkType, workspace always, features with agents/targets, route group, dial plan).
- `wxcli users update` has no `--license` flag. License assignment folded into `user:create` via `--license {CALLING_LICENSE_ID}`. The `user:assign_license` op is a no-op comment.
- wxcli create commands do not support `-o json`. `capture_id` is `"stdout"` (parse ID from text output). Phase 11 skill parses stdout and falls back to `list --name ... -o json` for verification. Adding `-o json` to the generator is a nice-to-have, not a blocker.
- Feature delete commands require `LOCATION_ID RESOURCE_ID` (two positional args). Rollback map includes both.
- `operating_mode` and `translation_pattern` have rollback commands (was missing initially, caught in code review).

## Phase 10 Preflight (2026-03-24)

Phase 10 added preflight checks that verify the Webex org is ready before migration:
- `src/wxcli/migration/preflight/__init__.py` — Data models (CheckStatus, CheckResult, PreflightResult), `_run_wxcli` subprocess helper, `preflight_fingerprint()`
- `src/wxcli/migration/preflight/checks.py` — 8 check functions: licenses, workspace licenses, locations, trunks, feature entitlements, number conflicts (with same-owner dedup), duplicate users (3 scenarios), rate limit budget
- `src/wxcli/migration/preflight/runner.py` — PreflightRunner: fetches shared Webex data once, runs checks, merges decisions scoped to preflight types only
- `src/wxcli/commands/cucm.py` — added `wxcli cucm preflight` with `--check`, `--dry-run`, `-o json`

**Key design decisions:**
- Checks call wxcli via subprocess to reuse auth/pagination/error handling — parse JSON output
- `merge_decisions()` enhanced with `decision_types` param to avoid stale-marking analyzer decisions on preflight re-run
- State machine updated with `PREFLIGHT → PREFLIGHT` and `PREFLIGHT_FAILED → PREFLIGHT` self-transitions for re-runs
- NUMBER_CONFLICT skips same-owner email matches (deferred to DUPLICATE_USER)
- Data fetches gated on `--check` filter to skip unnecessary API calls

## Phase 11 Migrate Skill (2026-03-24)

Phase 11 added the `cucm-migrate` skill that the wxc-calling-builder agent uses to execute a deployment plan:
- `.claude/skills/cucm-migrate/SKILL.md` — 6-step workflow: load plan → auth + preflight → plan summary → batch execute → domain skill delegation → report
- `.claude/agents/wxc-calling-builder.md` — updated with CUCM migration detection in interview phase, `cucm-migrate` added to `skills:` frontmatter and dispatch table

**Key design decisions:**
- Skill is a prompt file, not code. It tells Claude how to execute the deployment plan via wxcli commands.
- Preflight is mandatory and not skippable. 8 checks must all pass before execution begins.
- `{STEP_N_ID}` placeholders resolved by capturing IDs from stdout of create commands. `{CALLING_LICENSE_ID}` resolved once upfront via `wxcli licenses list`.
- Error handling: stop on failure, diagnose, present 4 options (fix/retry, skip, rollback-batch, rollback-all).
- Delegates to 7 domain skills (provision-calling, configure-features, configure-routing, manage-devices, manage-call-settings, customer-assist) for HOW; the plan provides WHAT.
- `-o json` not needed on create commands — skill parses stdout for IDs, with `list --name ... -o json` as verification fallback.

**This completes the full pipeline.** The path from CUCM discovery to Webex execution is: `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `decisions` → `plan` → `preflight` → `export` → `/cucm-migrate`.

## Future Expansion

Two authoritative specs replace the original `expansion-scope.md`:
- `future/tier2-enterprise-expansion.md` — 8 items with full pipeline blueprints (§1 shared infra + §2-§9 per-item). 3 new DecisionTypes, 6 new canonical types, 7 new mappers.
- `future/tier3-informational-extraction.md` — 18 informational types, single extractor, 3 report sections.

All 11 core build phases complete; expansion work is optional. See `future/CLAUDE.md` for build order.
