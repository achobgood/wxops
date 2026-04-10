# CUCM→Webex Migration Tool — Master Roadmap

Single source of truth for what's been done, what's ready, and what's next.

## Phase 1: Architecture Design — COMPLETE

Designed the normalize → analyze → plan pipeline. All 7 architecture questions answered.

| Deliverable | File | Status |
|------------|------|--------|
| Full migration design spec | `docs/plans/cucm-wxc-migration.md` | Complete (module structure is stale — pipeline docs are authoritative) |
| Pipeline architecture summary | `docs/plans/cucm-pipeline-architecture.md` | Complete |
| Data representation (SQLite) | `docs/plans/cucm-pipeline/01-data-representation.md` | Complete |
| Normalization architecture | `docs/plans/cucm-pipeline/02-normalization-architecture.md` | Complete + synthesis fixes (27-row cross-ref manifest added) |
| Conflict detection engine | `docs/plans/cucm-pipeline/03-conflict-detection-engine.md` | Complete + synthesis fixes (decision ownership note added) |
| Transform mappers | `docs/plans/cucm-pipeline/03b-transform-mappers.md` | Complete — 5 review rounds + synthesis |
| CSS decomposition | `docs/plans/cucm-pipeline/04-css-decomposition.md` | Complete |
| Dependency graph | `docs/plans/cucm-pipeline/05-dependency-graph.md` | Complete |
| Decision workflow | `docs/plans/cucm-pipeline/06-decision-workflow.md` | Complete |
| Idempotency & resumability | `docs/plans/cucm-pipeline/07-idempotency-resumability.md` | Complete |

## Phase 2: Mapper Design & Review — COMPLETE

Designed field-level CUCM→Webex mappings for all 9 mappers.

| Step | Status | Notes |
|------|--------|-------|
| Mapper design session | Complete | Produced 03b (1,016 lines, 9 mappers) |
| Per-mapper accuracy review | Complete | 5+ rounds of agent swarm review |
| Review in original session | Complete | Final fixes using original session's loaded reference docs |
| Cross-mapper synthesis | Complete | Structural consistency verified, fixes applied to 02, 03, build-3 |

## Phase 3a: Gap Design — COMPLETE

Three design gaps discovered during roadmap review. All three design docs are now complete.

| Gap | Prompt | Produces | Status |
|-----|--------|----------|--------|
| AXL extraction (Phase 2 fields) | `docs/prompts/cucm-extraction-design.md` | `docs/plans/cucm-pipeline/02b-cucm-extraction.md` | **Complete** (21 unverified AXL WSDL fields — validated in Phase 03 live testing) |
| Executor API mapping (Phase 6 fields) | `docs/prompts/cucm-executor-design.md` | `docs/plans/cucm-pipeline/05b-executor-api-mapping.md` | **Complete** |
| Preflight checks (Phase 5 detail) | `docs/prompts/cucm-preflight-design.md` | `docs/plans/cucm-pipeline/05a-preflight-checks.md` | **Complete** (4 open questions deferred — see expansion-scope.md) |

These follow the same pattern as the mapper design: design doc → review → synthesis. The extraction and executor designs may need per-section review similar to 03b (they're field-level specifications that must be accurate).

## Phase 3b: Build Planning — COMPLETE

Three planning prompts executed in sequence, then reviewed via 2-wave agent swarm.

| Step | Prompt | Execute With | Produces | Status |
|------|--------|-------------|----------|--------|
| Strategy | `docs/prompts/build-1-strategy.md` | `docs/prompts/execute-build-1.md` | `docs/plans/cucm-build-strategy.md` | **Complete** (2026-03-22) |
| Contracts | `docs/prompts/build-2-contracts.md` | `docs/prompts/execute-build-2.md` | `docs/plans/cucm-build-contracts.md` | **Complete** (2026-03-22) |
| Mapper sessions | `docs/prompts/build-3-mappers.md` | `docs/prompts/execute-build-3.md` | `docs/plans/cucm-build-mappers.md` | **Complete** (2026-03-22) |
| Review | `docs/prompts/review-build-planning.md` | 2-wave agent swarm | — | **Complete** (2026-03-22) — 43/43 checks passed |

## Phase 4: Build Execution — COMPLETE

12 build phases with per-phase execution prompts. Run in order (some can parallel as noted).

| Phase | Prompt | Depends On | Can Parallel With | Status |
|-------|--------|-----------|-------------------|--------|
| 01 Foundation | `docs/prompts/phase-01-foundation.md` | nothing | Phase 02 | **Complete** (2026-03-22) — models.py, store.py, state.py, rate_limiter.py |
| 02 Risk Spikes | `docs/prompts/phase-02-risk-spikes.md` | nothing | Phase 01 | **Complete** (2026-03-22) — e164.py, cucm_pattern.py |
| 03 Extraction | `docs/prompts/phase-03-extraction.md` | Phase 01 | — | **Complete** (2026-03-23) — connection.py, 8 extractors, discovery.py. Validated against live CUCM 15.0. See notes below. |
| 04 Normalization | `docs/prompts/phase-04-normalization.md` | Phase 01 + 03 | — | **Complete** (2026-03-23) — normalizers.py (24 normalizers), cross_reference.py (26 relationships + 3 enrichments), pipeline.py (entry point). Reconciled with live CUCM Phase 03 output. 3-agent code review, 357 tests passing. |
| 05 Mappers (4-5 sessions) | `docs/prompts/phase-05-mappers.md` | Phase 01 + 02 + 04 | — | **Complete** (2026-03-23) — 9 mappers + engine.py + rules.py + decisions.py. 5 sessions (D1-D4). 200 new tests, 557 total passing. See notes below. |
| 06 Analyzers | `docs/prompts/phase-06-analyzers.md` | Phase 01 + 05 | — | **Complete** (2026-03-23) — 12 analyzers + analysis_pipeline.py + merge_decisions(). 97 new tests, 660 total passing. See notes below. |
| 07 Planning | `docs/prompts/phase-07-planning.md` | Phase 01 + 06 | — | **Complete** (2026-03-23) — planner.py, dependency.py, batch.py. 740 total passing. |

### Revised Phases 08-11: Playbook Integration (replaces original 08-12)

The original Phases 08-12 designed a standalone executor with raw HTTP calls. The revised plan reuses the existing wxcli CLI (100 command groups) and wxc-calling-builder agent instead of reimplementing API execution from scratch.

| Phase | Prompt | Depends On | Status |
|-------|--------|-----------|--------|
| 08-revised: CUCM CLI | `docs/prompts/phase-08-cucm-cli.md` | Phase 07 | **Complete** (2026-03-23) — cucm.py (580 lines, 12 commands), cucm_config.py, 39 CLI tests. 1220 total passing. See notes below. |
| 09-revised: Export | `docs/prompts/phase-09-export.md` | Phase 08-revised | **Complete** (2026-03-24) — command_builder.py (27 builders), deployment_plan.py (7-section), json/csv exports. 66 new tests, 892 total passing. See notes below. |
| 10-revised: Preflight | `docs/prompts/phase-10-preflight.md` | Phase 08-revised | **Complete** (2026-03-24) — preflight/ module (8 checks), runner.py, CLI `wxcli cucm preflight`. 49 new tests, 892 total passing. See notes below. |
| 11-revised: Migrate Skill | `docs/prompts/phase-11-cucm-migrate-skill.md` | Phases 09+10 revised | **Complete** (2026-03-24) — cucm-migrate skill (6-step workflow, 7 domain skill delegations), builder agent updated. 1294 total passing. |

**Key architectural change:** Instead of building a new executor (Phase 09-original) that makes raw API calls, the pipeline exports a deployment plan that the wxc-calling-builder agent consumes. The builder agent already handles auth, prerequisites, execution, error handling, verification, and rollback — all via wxcli commands.

**Original Phases 08-12 prompts** (`phase-08-preflight.md`, `phase-09-executor.md`, `phase-10-validate.md`, `phase-11-cli.md`, `phase-12-agent-skills.md`) are **superseded** by the revised prompts above. Do not use the original prompts.

**Parallelism:** Phases 01 and 02 can run simultaneously. Phase 09-revised and 10-revised can run in parallel (both depend on 08-revised).

Each phase prompt includes: design guardrails reference, acceptance criteria, self-review checklist, and an expansion investigation section that checks whether the design docs provide enough detail.

### Phase 03 Extraction — Live CUCM Validation Notes (2026-03-23)

Validated against CUCM 15.0.1.13901(2) at 10.201.123.107 with a provisioned enterprise test bed (80 objects, 21 types).

**Key findings that affect downstream phases:**
- `listEndUser` AXL blocked on this cluster — SQL fallback built and validated. Normalizers must handle `_extracted_via: "sql"` flag (CSS, VM profile, selfService, userLocale will be `None`).
- Empty reference fields from zeep are `{'_value_1': None, 'uuid': None}`, not plain `None`. Use `ref_value()` consistently.
- `index` fields are `int` (not `str`) when using zeep + WSDL.
- AXL list operations have restricted schemas — cannot request nested fields like `members`, `lines`, `destinations`. Extractors use list for discovery, get for detail.
- SIP trunk destinations are `destinations.destination[]` array (not flat fields).
- VM profile `voiceMailPilot` is complex type `{dirn, cssName, uuid}` — normalizer resolves via UUID.
- Call forwarding fields (10 types) now enriched on each phone line entry via getLine.

**Test bed:** `tests/migration/cucm/build-testbed.md` (plan), `testbed-manifest.json` (inventory), `provision_testbed.py` (create), `teardown_testbed.py` (destroy). Shared lines: 4 shared DNs across 2-3 devices. Workspaces: 3 common-area phones.

#### AXL Gotchas Discovered (Test Bed Expansion 2026-03-24)

15 new + 5 modified objects added to fill pipeline coverage gaps. Script: `tests/migration/cucm/provision_testbed_phase9.py`.

**Objects added:** 1 blocking partition (Block-International-PT), 2 blocked route patterns, 3 CSS updates (adding blocking partitions), 2 common-area phones (7841 + 8845, no owner), 2 DNs for workspaces, 1 pickup group (Sales-Pickup), 2 line-level pickup assignments, 1 CTI Route Point (CTIAAAfterHours, SCCP, Branch), 1 DN for AA, 2 holiday time periods, 1 holiday schedule, 2 partition→schedule associations.

**AXL gotchas:**
1. `addCallPickupGroup` with `<members>/<directoryNumber>` fails on CUCM 15.0 — null priority FK constraint. Workaround: create empty, then `updateLine` with `callPickupGroupName`.
2. No native `listPagingGroup`/`getPagingGroup` AXL object. Paging requires InformaCast/Cisco Paging Server. Pipeline gap: `CanonicalPagingGroup` cannot be auto-extracted.
3. CTI Route Points require SCCP on some device pools — SIP fails with "Device Protocol not valid."
4. `TimePeriod.monthOfYear` uses 3-letter abbreviations only (Dec, Jan); `endTime` accepts on-the-hour values only (TypeTimeOfDay enum).

**Pipeline gaps not fixable without infrastructure:**
- No PagingGroup extraction (needs InformaCast)
- No Unity Connection CUPI integration test (needs UC server)

**Scope expansion deferred:** `docs/plans/cucm-pipeline/future/expansion-scope.md` — 8 Tier 2 types, 18 Tier 3 informational types.

### Phase 04 Normalization Notes (2026-03-23)

**Files produced:**
- `src/wxcli/migration/transform/normalizers.py` — 24 Pass 1 normalizers (22 object types + `normalize_unity_vm_settings` + `normalize_voicemail_pilot`)
- `src/wxcli/migration/transform/cross_reference.py` — CrossReferenceBuilder (26 of 27 manifest relationships + shared line detection + phone model classification + E.164 normalization)
- `src/wxcli/migration/transform/pipeline.py` — `normalize_discovery()` entry point connecting `DiscoveryResult.raw_data` → normalizers → store → CrossReferenceBuilder
- `tests/migration/transform/test_normalizers.py` — 56 tests
- `tests/migration/transform/test_cross_reference.py` — 40 tests
- `tests/migration/transform/test_pipeline.py` — 7 tests
- Minor fix to `store.py` (`_object_type_for` extracts type from canonical_id prefix for intermediate MigrationObject instances)

**Reconciliation with Phase 03 (live CUCM):**
- Extractors pre-normalize zeep lists via `to_list()` — normalizers handle both flat lists (extractor format) and nested dicts (raw zeep format) via `_to_list()` helper
- Hunt list members use `userOrDeviceName` (not `lineGroupName`), route group members use `sipTrunkName` (not `deviceName`) — normalizers check both
- `is_common_area_device` uses `_extract_ref()` to handle empty-ref `{'_value_1': None}` format
- Call forwarding fields (10 types) captured per line appearance
- Unity Connection per-user VM settings stored as `unity_vm:{userid}` objects

**Code review findings fixed:**
- `cti_rp` object type (not `cti_route_point`) — canonical_id prefix mismatch caught and fixed
- FK pragma wrapped in try/finally
- `line_group_has_members` extracts real partition instead of hard-coding `<None>`
- MPP model classification excludes known-incompatible models (7811, etc.)
- `provenance.source_name` fallback chain extended for users/gateways/pilots

### Phase 05 Mappers Notes (2026-03-23)

**Files produced (5 sessions: D1-D4):**
- `src/wxcli/migration/transform/mappers/base.py` — Mapper ABC with `_create_decision()`, `_fingerprint()`, `decision_to_store_dict()`, option builders
- `src/wxcli/migration/transform/mappers/location_mapper.py` — Device pools → CanonicalLocation (consolidation, timezone, address, `device_pool_to_location` cross-ref write)
- `src/wxcli/migration/transform/mappers/user_mapper.py` — End users → CanonicalUser (email fallback, location chain, SQL-extracted user detection)
- `src/wxcli/migration/transform/mappers/line_mapper.py` — DNs → CanonicalLine (precomputed e164_result, shared line tagging, extension validation)
- `src/wxcli/migration/transform/mappers/device_mapper.py` — Phones → CanonicalDevice (three-tier compatibility, MAC extraction, SCCP detection)
- `src/wxcli/migration/transform/mappers/workspace_mapper.py` — Common-area phones → CanonicalWorkspace (license tier, hotdesk conflict, type inference)
- `src/wxcli/migration/transform/mappers/routing_mapper.py` — Trunks/routes → CanonicalTrunk/RouteGroup/DialPlan/TranslationPattern (destinations as list, empty cross-ref fallback, 10-trunk split)
- `src/wxcli/migration/transform/mappers/css_mapper.py` — CSS decomposition → CanonicalDialPlan + CanonicalCallingPermission (5-step algorithm, intersection-first, ordering conflict detection)
- `src/wxcli/migration/transform/mappers/feature_mapper.py` — Hunt pilots/CTI RPs → HG/CQ/AA + simple features (classify_hunt_pilot 3-step algorithm, agent limits)
- `src/wxcli/migration/transform/mappers/voicemail_mapper.py` — VM profiles → CanonicalVoicemailProfile (CFNA→rings, 10-row gap analysis, unity_vm join)
- `src/wxcli/migration/transform/pattern_converter.py` — `cucm_to_webex_pattern()` shared by routing_mapper and css_mapper
- `src/wxcli/migration/transform/engine.py` — TransformEngine with MAPPER_ORDER (14 mappers), failure-tolerant execution
- `src/wxcli/migration/transform/rules.py` — Auto-resolution rules engine
- `src/wxcli/migration/transform/decisions.py` — Decision summary, formatting, query helpers
- Decision types added to models.py: DecisionType (15 values), Decision, DecisionOption, MapperResult, MapperError, TransformResult
- 200 new tests across 11 test files, 557 total passing

**AXL field name corrections (applied via `docs/prompts/fix-phase05-field-names.md`):**
- `distributionAlgorithm` on LineGroup (was `huntAlgorithm` on HuntList)
- Queue fields nested in `queueCalls` on HuntPilot (was flat on hp_state)
- `rnaReversionTimeOut` on LineGroup (was `huntTimerCallPick`)
- `enableExtensionMobility` on Phone (was `hotelingEnabled`)
- CTI RP schedule resolved via CSS → partition → `timeScheduleIdName` (CTI RP has no schedule field)

**5-agent comprehensive code review findings fixed:**
- `affected_objects` now preserved in `decision_to_store_dict()` via `context._affected_objects`
- css_mapper restriction profiles now use `user_effective_css` (line/device CSS fallback users get calling permissions)
- css_mapper effective CSS resolution now traces user → device → DN → `line_has_css` (higher priority) then device → `device_has_css` (lower priority) when no direct `user_has_css` exists
- voicemail_mapper `send_unanswered_enabled` respects explicit False from CUCM (removed `or True`)
- `_extract_provenance()` and `_hash_id()` extracted to `base.py` (was duplicated across 7 mappers)
- Unused `datetime` import removed from `rules.py`

**Known simplifications (acceptable):**
- feature_mapper: WEIGHTED agent limit defined but unreachable (no CUCM algorithm maps to it)
- voicemail_mapper: `_READ_ONLY_FIELDS` constant defined but unused (model already excludes these fields)

**Integration test:** `tests/migration/transform/test_integration.py` — 20-test messy fixture covering: 3 device pools, 5 users, 6 phones, 5 DNs, 3 partitions, 2 CSSes, 1 SIP trunk, 1 hunt pilot (queue→CQ), 1 CTI RP (→AA), 1 VM profile, 1 schedule. Verifies location consolidation, shared line tagging, hunt pilot classification, device compatibility tiers, CSS intersection, voicemail gap analysis, E.164 classification, and single-mapper failure resilience. 563 tests passing after review fixes.

### Phase 06 Analyzers Notes (2026-03-23)

**Files produced:**
- `src/wxcli/migration/transform/analyzers/__init__.py` — Analyzer ABC with `analyze()`, `fingerprint()` abstract methods, `_create_decision()`, `_get_existing_decisions_for_type()` helpers, `AnalysisResult` dataclass
- `src/wxcli/migration/transform/analyzers/extension_conflict.py` — ExtensionConflictAnalyzer (analyzer-owned EXTENSION_CONFLICT)
- `src/wxcli/migration/transform/analyzers/dn_ambiguity.py` — DNAmbiguityAnalyzer (mapper-owned DN_AMBIGUOUS)
- `src/wxcli/migration/transform/analyzers/device_compatibility.py` — DeviceCompatibilityAnalyzer (mapper-owned DEVICE_INCOMPATIBLE + DEVICE_FIRMWARE_CONVERTIBLE)
- `src/wxcli/migration/transform/analyzers/shared_line.py` — SharedLineAnalyzer (analyzer-owned SHARED_LINE_COMPLEX)
- `src/wxcli/migration/transform/analyzers/css_routing.py` — CSSRoutingAnalyzer (mapper-owned CSS_ROUTING_MISMATCH, 2 detection passes: pattern-level + scope-level)
- `src/wxcli/migration/transform/analyzers/css_permission.py` — CSSPermissionAnalyzer (mapper-owned CALLING_PERMISSION_MISMATCH)
- `src/wxcli/migration/transform/analyzers/location_ambiguity.py` — LocationAmbiguityAnalyzer (mapper-owned LOCATION_AMBIGUOUS)
- `src/wxcli/migration/transform/analyzers/duplicate_user.py` — DuplicateUserAnalyzer (analyzer-owned DUPLICATE_USER, email + name collision)
- `src/wxcli/migration/transform/analyzers/voicemail_compatibility.py` — VoicemailCompatibilityAnalyzer (mapper-owned VOICEMAIL_INCOMPATIBLE)
- `src/wxcli/migration/transform/analyzers/workspace_license.py` — WorkspaceLicenseAnalyzer (mapper-owned WORKSPACE_LICENSE_TIER)
- `src/wxcli/migration/transform/analyzers/feature_approximation.py` — FeatureApproximationAnalyzer (mapper-owned FEATURE_APPROXIMATION)
- `src/wxcli/migration/transform/analyzers/missing_data.py` — MissingDataAnalyzer (mapper-owned MISSING_DATA, 4 object types + separate line check)
- `src/wxcli/migration/transform/analysis_pipeline.py` — AnalysisPipeline orchestrator (12 analyzers, topological sort, merge, auto-rules) + `resolve_and_cascade()` for cascading re-evaluation
- `store.py` — Added `merge_decisions()` method (fingerprint-based three-way merge with merge_log)
- 105 new tests across 3 test files, 668 total passing

**Decision ownership implemented:**
- 3 analyzer-owned types (EXTENSION_CONFLICT, SHARED_LINE_COMPLEX, DUPLICATE_USER): no mapper produces these, analyzers are sole producers
- 11 mapper-owned types: all 9 remaining analyzers check `_get_existing_decisions_for_type()` before creating decisions, skipping objects already covered by mappers

**Merge algorithm behavior:**
- Re-analysis with identical data: analyzers skip objects that already have decisions → produces 0 new decisions → merge marks all pending as stale. This is by design — the analyzer checks for existing decisions including its own from previous runs.
- Re-analysis after data changes: new fingerprints create new decisions, old fingerprints preserve resolved decisions, missing fingerprints mark stale.
- Resolved decisions in "kept" state now get display-only fields updated (summary, options, context) while preserving chosen_option/resolved_at/resolved_by.

**Code review findings fixed (5-agent swarm):**
- **Critical:** CSSRoutingAnalyzer Pass 1 read `dial_patterns` as `list[dict]` but model is `list[str]` — fixed to read strings + top-level `route_id`. Pass 2 read `location_canonical_id` but field is `location_id` — fixed.
- **Important:** WorkspaceLicense fingerprint now includes `features_detected` so feature changes invalidate stale resolutions. CSSPermission action comparison now case-insensitive (`action.upper() == "BLOCK"`). DNAmbiguity `dn_length` now counts non-wildcard chars instead of fragile `rstrip("X")`. Merge "kept" case now updates display-only fields.
- **Deferred→fixed:** Analyzer ABC uses `__init_subclass__` for safe mutable defaults. SharedLine uses set for O(1) owner dedup. MissingData no longer loads lines twice. VoicemailCompatibility `_has_fax_message` simplified. LocationAmbiguity adds 3+ pool consolidation as second detection signal.

**Expansion investigation prompt:** `docs/prompts/phase-06b-expansion.md` — cascade re-evaluation test, multi-analyzer same-object test, auto-rule `match` field support. Ready for a separate session.

### Phase 09-revised Export Notes (2026-03-24)

**Files produced:**
- `src/wxcli/migration/export/__init__.py` — package init
- `src/wxcli/migration/export/command_builder.py` — maps all 27 (resource_type, op_type) combos to wxcli CLI command strings with {STEP_N_ID} placeholders, capture_id metadata, and rollback commands
- `src/wxcli/migration/export/deployment_plan.py` — generates 7-section deployment plan (Objective, Prerequisites, API Calls, Resources, Rollback, Impact, Approval)
- `src/wxcli/migration/export/json_export.py` — full JSON export
- `src/wxcli/migration/export/csv_export.py` — CSV decisions export
- `tests/migration/export/test_command_builder.py` — 49 tests
- `tests/migration/export/test_deployment_plan.py` — 17 tests
- Updated `src/wxcli/commands/cucm.py` — export functions delegate to new modules, write to `<project>/exports/`, copy plan to `docs/plans/`
- 892 total tests passing

**Key design decisions and gotchas:**
- `--json-body` overrides all individual flags in wxcli generated commands. When `--json-body` is needed, ALL required fields go in the body. Affects: location (with address), trunk (with trunkType), workspace (always), features (with agents/targets/policy), route group, dial plan.
- `wxcli users update` has no `--license` flag. License assignment folded into `users create` via `--license`. The `user:assign_license` op is a no-op comment.
- wxcli create commands do NOT support `-o json`. `capture_id` uses `"stdout"` (parse ID from text). Phase 11 skill was built to work without `-o json` — parses stdout and falls back to `list --name ... -o json` for verification. Adding `-o json` to the generator is a nice-to-have, not a blocker.
- Feature delete commands require `LOCATION_ID RESOURCE_ID` (two positional args). Rollback map includes both.
- Dial plan delete is `wxcli call-routing delete` (not `delete-dial-plans`).

**Phase 09→11 interface (how the skill consumes export output):**
- `build_all_commands()` returns dicts with: `step`, `node_id`, `resource_type`, `op_type`, `description`, `command`, `dependencies`, `capture_id`, `step_ref`
- `capture_id` values: `"stdout"` (create — parse ID from text), `"none"` (configure/assign), `"comment"` (no-op)
- `get_rollback_command()` returns delete command strings with placeholders
- The cucm-migrate skill (Phase 11) parses IDs from stdout and verifies via `list --name ... -o json` when ambiguous

### Phase 08-revised CUCM CLI Notes (2026-03-23)

**Files produced:**
- `src/wxcli/commands/cucm.py` — 580 lines, 12 commands: init, status, config (set/show), discover, normalize, map, analyze, plan, decisions, decide, export, inventory
- `src/wxcli/commands/cucm_config.py` — 60 lines, config management helpers
- `tests/migration/test_cucm_cli.py` — 39 CLI tests
- `src/wxcli/main.py` — registered cucm group
- 1220 total tests passing

**Key design decisions:**
- Pipeline stage tracking via `completed_stages` list in state.json (allows re-runs without resetting)
- `raw_data.json` persists discovery output between discover and normalize invocations
- Current project stored in `~/.wxcli/current_project`, overridable with `--project` on any command
- Password prompts with hidden input (secure by default)
- Cascade re-evaluation on `decide` via `AnalysisPipeline.resolve_and_cascade()`
- Export already generates basic deployment-plan markdown, JSON, and CSV-decisions. Phase 09-revised enhances deployment-plan with actual wxcli command strings.

**What Phase 09-revised needs to know:**
- `_export_deployment_plan()` in cucm.py (line 839) already generates markdown with inventory, decisions, and batch plan. Phase 09 adds `command_builder.py` to produce actual wxcli commands per operation, and enhances the export to include the deployment-plan template sections (Prerequisites, API Calls, Rollback, etc.)
- The export path is `<project_dir>/deployment-plan.md`. Phase 09 should also copy to `docs/plans/` for builder agent discovery.

### Phase 10-revised Preflight Notes (2026-03-24)

**Files produced:**
- `src/wxcli/migration/preflight/__init__.py` — Data models, `_run_wxcli` helper, `preflight_fingerprint()`
- `src/wxcli/migration/preflight/checks.py` — 8 check functions: licenses, workspace licenses, locations, trunks, feature entitlements, number conflicts, duplicate users, rate limit budget
- `src/wxcli/migration/preflight/runner.py` — PreflightRunner orchestrator
- `src/wxcli/commands/cucm.py` — added `wxcli cucm preflight` command with `--check`, `--dry-run`, `-o json`
- `src/wxcli/migration/models.py` — added `NUMBER_CONFLICT` to DecisionType enum
- 49 new tests, 892 total passing

**Key design decisions:**
- Checks run via `subprocess.run(["wxcli", ...])` to reuse CLI auth, pagination, and error handling
- `merge_decisions()` enhanced with `decision_types` and `stage` params so preflight doesn't stale-mark analyzer decisions
- State machine updated with self-transitions for re-runs
- Same-owner email dedup: NUMBER_CONFLICT skips collisions where planned and existing owner share the same email
- Shared data fetched once, gated on `--check` filter

**Known limitations:**
- PSTN connection check not available (no wxcli command for that endpoint)
- `wxcli users list` does not support `callingData=true` without filtering — duplicate users classify as `exists_no_calling`

## Phase 5: Integration Testing — READY (Phase 05 mappers complete, Phase 04 complete)

End-to-end pipeline tests: fixture CUCM data → normalize → map → analyze → plan → mock-execute → validate.

## Prompt Inventory

All prompts live in `docs/prompts/`:

| File | Purpose | Status |
|------|---------|--------|
| **Guardrails** | | |
| `design-guardrails.md` | Shared guardrails for all design/build sessions | Active — reference in every prompt |
| **Gap Design Prompts** | | |
| `cucm-extraction-design.md` | Gap 1: AXL extraction field-level spec | Ready |
| `cucm-executor-design.md` | Gap 2: executor API call mapping | **Complete** (2026-03-22) |
| `cucm-preflight-design.md` | Gap 3: preflight check detail | Ready |
| **Build Planning Prompts** | | |
| `cucm-migration-build.md` | Original monolithic build prompt (SUPERSEDED) | Superseded by build-1/2/3 |
| `build-1-strategy.md` | Build planning Part 1: strategy, risk, order | **Executed** (2026-03-22) |
| `build-2-contracts.md` | Build planning Part 2: contracts, criteria | **Executed** (2026-03-22) |
| `build-3-mappers.md` | Build planning Part 3: mapper session breakdown | **Executed** (2026-03-22) |
| `execute-build-1.md` | Execution wrapper for Part 1 | **Executed** (2026-03-22) |
| `execute-build-2.md` | Execution wrapper for Part 2 | **Executed** (2026-03-22) |
| `execute-build-3.md` | Execution wrapper for Part 3 | **Executed** (2026-03-22) |
| `review-build-planning.md` | 2-wave review swarm for build planning outputs | **Executed** (2026-03-22) — 43/43 PASS |
| **Build Phase Prompts** | | |
| `phase-01-foundation.md` | Foundation: models.py, store.py, state.py, rate_limiter.py | Ready |
| `phase-02-risk-spikes.md` | Risk spikes: cucm_pattern.py, e164.py (TDD) | Ready |
| `phase-03-extraction.md` | CUCM extraction: connection, extractors, discovery | Ready (blocked on 02b) |
| `phase-04-normalization.md` | Normalization: pass 1 normalizers, CrossReferenceBuilder | Ready |
| `phase-05-mappers.md` | Mappers: 9 mappers + engine.py (4-5 sessions) | Ready |
| `phase-06-analyzers.md` | Analyzers: 12 analyzers + analysis_pipeline.py | **Executed** (2026-03-23) — 5-agent code review, all fixes applied |
| `phase-06b-expansion.md` | Expansion: cascade, multi-analyzer, auto-rule match | Ready |
| `phase-07-planning.md` | Planning: planner.py, dependency.py, batch.py | **Executed** (2026-03-23) |
| **Revised Build Prompts (replaces 08-12)** | | |
| `phase-08-cucm-cli.md` | CUCM CLI commands: wxcli cucm subgroup | **Executed** (2026-03-23) |
| `phase-09-export.md` | Export: deployment plan, JSON, CSV for builder agent | **Executed** (2026-03-24) — 4-round code review, all Critical/Important fixed |
| `phase-10-preflight.md` | Preflight: Webex collision checks via wxcli | **Executed** (2026-03-24) |
| `phase-11-cucm-migrate-skill.md` | Migrate skill: feeds plan to builder agent | **Executed** (2026-03-24) — 6-step skill, 7 domain skill delegations |
| **Superseded Build Prompts (do not use)** | | |
| `phase-08-preflight.md` | ~~Original preflight~~ | Superseded by phase-10-preflight.md |
| `phase-09-executor.md` | ~~Original executor~~ | Superseded by phase-09-export.md + cucm-migrate skill |
| `phase-10-validate.md` | ~~Original validate~~ | Superseded — builder agent verifies after each step |
| `phase-11-cli.md` | ~~Original CLI~~ | Superseded by phase-08-cucm-cli.md |
| `phase-12-agent-skills.md` | ~~Original agent/skills~~ | Superseded by phase-11-cucm-migrate-skill.md |
| **Mapper Design Prompts (completed)** | | |
| `cucm-mapper-design.md` | Mapper design prompt | Executed |
| `cucm-mapper-design-phase2.md` | Chunked writing instructions | Executed |
| `cucm-mapper-review.md` | Per-mapper review agent swarm | Executed (5+ rounds) |
| `cucm-mapper-synthesis.md` | Cross-mapper synthesis review | Executed |
| **Phase 12: Execution Architecture (post-live-test fixes)** | | |
| `phase-12-execution-architecture.md` | Architecture evaluation: DB-driven vs markdown vs hybrid | **Executed** (2026-03-23) — chose Hybrid (Option C) |
| `phase-12a-upstream-bugfixes.md` | 9 upstream data-quality bugs (feature mapper, missing data, normalizer, DAG) | **Complete** (2026-03-24) |
| `phase-12b-execution-layer.md` | Skill-delegated execution: delete command_builder, domain skill dispatch, summary plan, CLI execution commands | **Complete** (2026-03-24) — informed by post-mortem |
| `postmortem-cucm-pipeline.md` | Post-mortem: design-to-execution gap analysis, architectural recommendation | **Complete** (2026-03-24) — drives 12b rewrite |
| `phase-12c-model-table-update.md` | Phone model table: 8851 → CONVERTIBLE, 9800 → NATIVE_MPP | **Complete** (2026-03-25) — 64 tests passing |
| **Fix / Patch Prompts** | | |
| `fix-phase05-field-names.md` | AXL field name corrections for Phase 05 mappers | **Executed** (2026-03-23) — 6 fixes + test fixture updates |
| `fix-mapper-wave1.md` | Earlier mapper fix wave | Executed |
| `fix-mapper-wave2.md` | Earlier mapper fix wave | Executed |
| **Other** | | |
| `setup-subfolder-docs.md` | Create subfolder CLAUDE.md + TODO.md files | Executed |
| `fix-known-issues.md` | Pre-existing prompt (unrelated) | — |

## What to Do Next

### Remaining Work

1. **Continue live testing** against CUCM test bed (10.201.123.107) — multiple runs since 12a/12b have found and fixed additional bugs.

### Phase 13: Migration Advisory System — COMPLETE

Advisory system adds practitioner-level recommendations to the pipeline. Two layers:

- **Layer 1 (recommendation_rules.py):** 20 per-decision recommendation functions. Each DecisionType gets an optional `recommendation` + `recommendation_reasoning`. Ambiguous cases return `None`.
- **Layer 2 (advisory_patterns.py + advisor.py):** 20 cross-cutting pattern detectors. `ArchitectureAdvisor` runs after all 12 analyzers, reads merged decisions + full inventory, produces `ARCHITECTURE_ADVISORY` decisions. Categories: eliminate, rebuild, out_of_scope, migrate_as_is.

**Pipeline integration:** Two-phase execution in `analysis_pipeline.py` — Phase 1 (12 analyzers → merge), Phase 2 (ArchitectureAdvisor → merge advisory), Phase 3 (populate_recommendations on all decisions).

**CLI:** `wxcli cucm decisions --type advisory` filters to advisories. `[REC: option]` display on decisions with recommendations. JSON export includes recommendation fields.

**Skill:** cucm-migrate decision review has Phase A (architecture advisory grouped by category with bulk accept) and Phase B (per-decision with recommended/needs-input groups).

| Prompt | Status | Tests |
|--------|--------|-------|
| Phase 13a: Foundation (models, store, tests) | COMPLETE | ~20 |
| Phase 13b: Recommendation rules (20 functions) | COMPLETE | ~25 |
| Phase 13c: Advisory patterns (20 patterns + advisor) | COMPLETE | ~42 |
| Phase 13d: Pipeline + CLI + skill integration | COMPLETE | 9 integration |

Design spec: `docs/superpowers/specs/2026-03-24-migration-advisory-design.md`

### All build phases complete (01-13). Pipeline in active live-testing phase.

**To run a migration (after Phase 12):**
```bash
wxcli cucm init <project-name>
wxcli cucm config set country_code "+1"
wxcli cucm discover --host <cucm-ip> --username <user> --password <pass> --wsdl /path/to/AXLAPI.wsdl --version 15.0
wxcli cucm normalize
wxcli cucm map
wxcli cucm analyze
wxcli cucm decisions                    # review conflicts
wxcli cucm decide <id> <choice>         # resolve each decision
wxcli cucm plan
wxcli cucm preflight                    # check Webex readiness
wxcli cucm export --format deployment-plan
# Then invoke /cucm-migrate skill — Claude reads the plan and executes via wxcli
```

### Live Testing Bugs (2026-03-23)

First run against live CUCM 15.0 test bed (10.201.123.107, 80 objects). Three bugs found and fixed:

| Bug | Root Cause | Fix | Regression Test |
|-----|-----------|-----|-----------------|
| `location_mapper` ValidationError: `outside_dial_digit` int vs str | `cucm_config.py` `coerce_value()` converts `"9"` → `int(9)`, JSON round-trips as int | Coerce to `str()` in `location_mapper.py` before passing to `CanonicalLocation` | `test_outside_dial_digit_int_coerced_to_str` |
| `routing_mapper` TypeError: `startswith` gets int | Same root cause — `outside_dial_digit` as int flows to `pattern_converter.py` | Coerce to `str()` in `pattern_converter.py` and all 3 mapper instantiation sites in `engine.py` | Existing pattern converter tests cover this |
| `feature_mapper` ValidationError: pickup group agents are dicts not strings | CUCM AXL returns pickup members as nested dicts `{'priority': N, 'pickupGroupLineMember': {'_value_1': ..., 'uuid': ...}}` | Extract UUIDs in normalizer `_extract_member_uuids()` + defensive fallback in feature mapper `_extract_agent_ids()` | 3 normalizer tests + 1 feature mapper test |
| `feature_mapper` ValidationError: `CanonicalOperatingMode.different_hours_daily` None key | CUCM time periods have `day_of_week: None` — `dict.get()` returns `None` when key exists with null value | Changed `tp.get("day_of_week", fallback)` to `(tp.get("day_of_week") or fallback)` in feature_mapper.py | Existing feature mapper tests cover this |

**Also discovered:** CUCM 15.0 returns 403 for remote WSDL fetch (`/axl/AXLAPIService?wsdl`). Must use local WSDL via `--wsdl` flag. Added `--version 15.0` recommendation for CUCM 15.x clusters.

### Live Testing Bugs — Round 2 (2026-03-23)

Second round of live testing found 8 data validation bugs. All produce broken deployment plan output that should have been caught earlier in the pipeline.

| Bug | Root Cause | Fix | Status |
|-----|-----------|-----|--------|
| **Hunt group agents are raw CUCM DNs** | **Two bugs:** (1) `cross_reference.py` line 540 didn't unwrap nested `directoryNumber` dicts from AXL — `member.get("directoryNumber")` returns `{"pattern": "1002", "routePartitionName": {...}}` not `"1002"`, producing garbage `to_id` like `dn:{'pattern':...}:<None>`. (2) Feature mapper didn't resolve clean DN refs to canonical user IDs. | (1) Fixed in cross_reference.py: unwrap nested `directoryNumber` dict to extract `pattern` and `routePartitionName` from inside it. (2) Fixed in feature_mapper.py: `_resolve_dn_to_owner()` resolves DN→device→user via cross-ref chain, falls back to raw DN ID when chain unavailable. | **DONE** (Phase 12a) |
| **Location addresses not validated** | Missing data analyzer only checks location `name` — no check for address fields (address1, city, state, postal_code). Locations with all-null addresses pass through to deployment plan. Command builder outputs empty strings. Webex API will reject or create E911-noncompliant location | Added address fields to `_REQUIRED_FIELDS["location"]` in `missing_data.py` with dot-notation support: `address.country`, `address.address1`, `address.city`, `address.state` (HIGH), `address.postal_code` (MEDIUM). | **DONE** (Phase 12a) |
| **Empty translation patterns not caught** | Mapper creates `CanonicalTranslationPattern` with empty `name` and `matching_pattern` when CUCM pattern field is empty string. Analyzer has no `translation_pattern` entry in `_REQUIRED_FIELDS`. Empty pattern reaches deployment plan | Skip empty patterns in routing mapper (`if not cucm_pattern: continue`). Added `translation_pattern` to `_REQUIRED_FIELDS` in `missing_data.py`. | **DONE** (Phase 12a) |
| **`{LOCATION_ID}` placeholder not resolved to step reference** | Command builder emits generic `{LOCATION_ID}` for location-scoped features (hunt groups, pickup groups, schedules, auto attendants) instead of `{STEP_N_ID}` referencing the location creation step. Skill can't resolve which location the feature belongs to | Phase 12b removed command_builder.py. Skill-delegated execution resolves location IDs from the DB at runtime. | **DONE** (Phase 12b) |
| **Pickup group agents contain raw CUCM UUIDs** | Pickup group member UUIDs from AXL are line-level UUIDs that don't match any DN object's provenance `source_id`. | Fixed: `_build_line_uuid_to_dn()` builds UUID→DN lookup from raw phone line data (`phone:{name}` objects in store). `_resolve_pickup_members_to_owners()` uses this to resolve UUID→DN→user. | **DONE** (2026-03-30) |
| **Resources table includes CUCM source objects** | Section 4 (Resources to Create/Modify) lists CUCM-only objects (partitions, CSSes, device_pools, cucm_locations, etc.) as "Create" items. These are source objects, not Webex resources | Phase 12b rewrote deployment_plan.py as summary-only (no CLI commands). Resource summary now filters to Webex types only. | **DONE** (Phase 12b) |
| **User creation steps missing location dependencies** | Steps 1-4 (user create) reference `{STEP_13_ID}` and `{STEP_14_ID}` (locations) but show "Dependencies: None". Location must exist before users can be assigned to it | Fixed: user_mapper writes `user_in_location` cross-ref. dependency.py `_CROSS_OBJECT_RULES` targets `enable_calling` (not just `create`). DAG now has user→location edges. | **DONE** (Phase 12a) |
| **Deployment plan hand-edited instead of re-exported** | Other session directly edited the deployment plan markdown to add addresses instead of updating the store and running `wxcli cucm export`. Store data is now out of sync with the plan file | Add critical rule to cucm-migrate skill: never hand-edit the deployment plan, always update via pipeline and re-export | **DONE** (rule 13 added to skill) |
| **Feature mapper doesn't populate `location_id` on features** | Hunt groups, auto attendants, pickup groups, and schedules all have `location_id=None` in the migration store. This is upstream of the `{LOCATION_ID}` placeholder bug — even if the command builder looked up location_id, it would find None. | Fixed: `_resolve_feature_location()` determines location from agent majority vote. Added `location_id` field to CanonicalHuntGroup, CanonicalCallQueue, CanonicalAutoAttendant, CanonicalPickupGroup models. AAs and schedules remain None (no agents — location resolved at execution time). | **DONE** (Phase 12a) |
| **Duplicate/junk pickup groups in store** | Store contains 3 pickup group objects for what should be 1-2: `pickup_group:Engineering-Pickup` (agents=[CUCM UUID], name=Engineering-Pickup), `pickup_group:f998930ff1b4` (name=f998930ff1b4 which is a hash, agents=[]), and `pickup_group:Engineering-Pickup` again (name=None, agents=None). Normalizer or feature mapper is creating duplicates with corrupt/empty data | Fixed: `normalize_pickup_group()` returns None for empty/blank names. Pipeline skips None normalizer results. Store upsert handles canonical_id conflicts via ON CONFLICT UPDATE. | **DONE** (Phase 12a) |
| **Call settings commands have `{...}` instead of actual JSON** | Steps for call forwarding, voicemail, caller ID, call waiting, DND all output `--json-body '{...}'` — a literal ellipsis placeholder, not the actual settings data from the store. The command builder isn't populating the real settings values | Phase 12b removed command_builder.py. Skill-delegated execution reads settings from DB and passes to domain skills at runtime. | **DONE** (Phase 12b) |

### Live Testing Bugs — Round 3: Execution Layer (2026-03-24)

Attempted full execution of the revised deployment plan against live Webex org. 11 of 32 steps completed before stopping. Found 6 execution-layer issues that Phase 12b must address.

| Bug | Root Cause | Impact | Fix |
|-----|-----------|--------|-----|
| **Location create doesn't enable Webex Calling** | Webex API: `POST /v1/locations` creates a location, but calling requires a separate `POST /v1/telephony/config/locations` with the same location ID + address | Users can't be assigned to location — get "Calling flag not set" error | Execution layer must run `location-settings create` after `locations create`. Two-step location provisioning |
| **User create requires extension at creation time** | Webex API: `POST /v1/people?callingData=true` requires either `phoneNumbers` or `extension` in the body. Can't create a calling user then assign extension separately | Plan had user creation (steps 3-6) and extension assignment (steps 12-15) as separate steps. Fails with "extension is required" | Merge user creation + extension assignment into single API call. Plan should not separate these |
| **`wxcli users create` passes `callingData=false`** | `users.py` line 89: `api.people.create(settings=settings)` doesn't pass `calling_data=True` to wxc_sdk | Users created without calling data, then can't be updated to add calling | Fixed: `calling_data=bool(location_id or license_id)`. But the deeper fix is merging user+extension steps |
| **`--json-body` overrides ALL CLI flags including required ones** | Generated commands use `--json-body` which the CLI parses INSTEAD of individual flags. But Click still requires the flags to be present | Must pass dummy values for required flags when using `--json-body` (e.g., `--name x --json-body '{...}'`) | Phase 12b: execution layer should use raw HTTP or the CLI should allow `--json-body` to satisfy required flags |
| **Route groups require at least one gateway** | Webex API rejects route groups with no `localGateways`. Plan generated "Standard Local Route Group" with empty gateway list | Step 10 failed with 400 "Missing fields: localGateways" | Command builder should validate route groups have gateways. Flag as MISSING_DATA if empty |
| **User create 400 may have created the user (409 on retry)** | First attempt with `callingData=false` returned 400 "Calling flag not set" but the API had already created the user. Retry with `callingData=true` returned 409 Conflict | Execution layer must check for existing resource before retrying a create | Phase 12b: on create failure, always check `list --email/--name` before retry. If 409, capture existing ID and continue |

**Resources created during this test run (need manual cleanup or rollback):**
- 2 locations: DP-HQ-Phones, DP-Branch-Phones (calling enabled)
- 4 users: jdoe@acme.com (ext 1001), jsmith@acme.com (ext 1002), bwilson@acme.com (ext 1003), achen@acme.com (ext 1004)
- 3 trunks: sip-trunk-to-lab-cucm, cisco.com, SKIGW0011223344
- 2 route groups: Standard Local Route Group, RG-PSTN-Primary
- Steps 16-32 NOT executed (hunt groups, AA, pickup, schedules, translation patterns, user settings)
| **License assignment generates no-op comment steps** | Planner creates `user:assign_license` operations that produce `# License assigned at user creation time` comments. These are noise — 4 extra steps that do nothing, cluttering the plan | Planner no longer generates `assign_license` ops — licensing bundled into `user:create` | **DONE** (Phase 12a) |
| **User count inflated — users without emails/locations included** | Plan says "10 users" but only 4 have emails and location assignments. 6 users have no emails or no location_id — they can't be provisioned | Missing data analyzer now checks users for required fields | **DONE** (Phase 12a) |
| **Schedules not stored as `schedule` object type** | Querying the store for `object_type='schedule'` returns 0 results | `CanonicalLocationSchedule` model + planner expansion implemented | **DONE** (Phase 12a) |
| **Location creation doesn't include calling enablement step** | Creating a location via `POST /v1/locations` does NOT enable Webex Calling on it | Planner generates `location:enable_calling` after `location:create`. Skill-delegated execution handles two-step provisioning | **DONE** (Phase 12b) |
| **`wxcli users create` doesn't pass `calling_data=True`** | wxc_sdk defaults to `calling_data=False` | Fixed: `calling_data=bool(location_id or license_id)` | **DONE** |
| **`wxcli users create` has no `--extension` flag** | The Webex API requires an extension at calling user creation time | Generated `people.py` already has `--extension` flag (line 89). Old hand-written `users.py` was replaced | **DONE** — `people.py` regenerated with `--extension` and `--calling-data` |
| **Extension assignment should be combined with user creation** | API requires extension at creation time — can't create then assign separately | Planner combines via `--json-body` with all fields including extension | **DONE** — skill dispatch passes extension in create body |
| **Failed user create leaves orphaned non-calling users** | Create fails on calling setup but People API already created the user. Retry gets 409 | Skill section 4c now has user-specific recovery: find orphaned user → update with calling data → mark complete | **DONE** (2026-03-30) |
| **`--json-body` doesn't bypass required CLI flags** | Click validates required options before command body runs | Generator already makes all body fields optional (`typer.Option(None, ...)`), validates required fields at runtime only when `--json-body` is not used | **DONE** — `_render_create_command()` lines 434-473 |
| **Trunk creation requires `locationId` not in plan** | Trunk mapper populates `location_id` on `CanonicalTrunk` via `trunk_at_location` cross-ref chain | Trunk `location_id` now resolved at runtime | **DONE** (Phase 12a) |
| **Route group requires at least one gateway** | "Standard Local Route Group" created with no `localGateways` array | `MISSING_DATA` analyzer now checks `local_gateways` on route groups | **DONE** (Phase 12a) |
| **Skill falls back to raw HTTP repeatedly** | Root causes: missing flags, broken `--json-body`, missing `calling_data` | All root causes addressed: `--extension` exists, `--json-body` bypass works, `calling_data` handled, user recovery pattern added | **DONE** (2026-03-30) |

### Known Limitations

| Limitation | Impact | Workaround | Future Enhancement |
|-----------|--------|------------|-------------------|
| **Location mapping uses device pools, not per-device Location overrides** | If a single device pool spans multiple physical sites (phones have device-level Location overrides), all phones in that pool map to one Webex location | Use `reassign` decision to manually assign devices to correct locations | Extract device-level `locationName` from phones during discovery; add `phone_at_cucm_location` cross-ref; location mapper checks for divergent per-device Locations within a pool and splits accordingly |
| **~~8851 missing from CONVERTIBLE tier~~** | ~~Cisco 8851 supports MPP firmware conversion but is not in `_CONVERTIBLE_PATTERNS`~~ | N/A | **FIXED (Phase 12c)** — 8851 + full 78xx/88xx lineup added: 7811, 7832, 8811, 8832, 8841, 8851, 8861 all in CONVERTIBLE. 7811 removed from `_INCOMPATIBLE_WITH_MPP`. Sources: Cisco E2M converter, help.webex.com/nl9j09w |
| **~~9800 series phones classified as INCOMPATIBLE~~** | ~~Cisco 9841/9851/9861/9871 run PhoneOS and fall through to `INCOMPATIBLE`~~ | N/A | **FIXED (Phase 12c)** — 9811/9821/9841/9851/9861/9871 + 8875 added to NATIVE_MPP. Source: Cisco 9800 data sheet |
| **Video/room devices not classified** | RoomOS devices (Desk, Desk Pro, Desk Mini, Board series, Room Kit series, Codec Plus/Pro) registered on CUCM can re-register to Webex Calling as workspaces, but `classify_phone_model()` marks them INCOMPATIBLE. DX70/DX80 and legacy TelePresence (SX/MX) are genuinely incompatible | Manually skip decisions and provision workspaces outside pipeline | New device tier or separate classification path for RoomOS video devices. Discovery needs to extract video device model names from CUCM. Workspace mapper needs to handle them as re-registration targets (similar to 9800 native MPP — no firmware change, just re-point registration). See detail below |
| **Third-party/generic SIP phones have a supported Webex Calling path** | Third-party phones on CUCM (Poly, Yealink, AudioCodes, others) all fall to INCOMPATIBLE, but many have a direct migration path to Webex Calling. Cisco publishes a supported device list with two tiers: **Cisco Managed** (Poly VVX/CCX/Edge, Yealink T/W/CP series, AudioCodes 4xxHD — full Control Hub provisioning) and **Customer Managed** (any SIP phone supporting TLS 1.2 via Generic SIP Phone/Gateway profile). The pipeline should recognize these devices and generate appropriate migration guidance instead of dead-ending at INCOMPATIBLE | Admin must research replacement options independently and provision outside pipeline | See detail below. New classification tier `THIRD_PARTY_SUPPORTED` or `THIRD_PARTY_REPLACEABLE`. Discovery identifies vendor/model from CUCM. Classifier checks against Cisco's published supported device list. Deployment plan generates "Device Replacement" section with per-device guidance: keep same hardware (Cisco Managed), use Generic SIP profile (Customer Managed), or replace. Reference: help.webex.com/qkwt4j (supported devices), help.webex.com/njwkamr (Cisco-managed third-party), help.webex.com/nemh93t (customer-managed devices) |
| **DECT handsets not in classification table** | Cisco DECT 6823/6825/6825R handsets and DBS 110/210 base stations are supported on Webex Calling but not in the classification table | Falls through to INCOMPATIBLE | Add DECT models to NATIVE_MPP or a dedicated DECT tier. DECT networks have a different provisioning path (base station → handset pairing) than desk phones |
| **Cisco wireless phones (840/860) not classified** | Cisco 840 and 860 ruggedized wireless phones are supported on Webex Calling but not in any pattern set | Falls through to INCOMPATIBLE | Add to NATIVE_MPP if they appear in CUCM discovery |
| **Deployment plan missing firmware conversion reminder** | Devices with `DEVICE_FIRMWARE_CONVERTIBLE` resolved as "convert" are pre-staged in Webex (correct behavior), but the deployment plan doesn't remind the admin that firmware conversion is needed at cutover | Admin must remember independently | Add informational prerequisite in `deployment_plan.py`: list devices needing firmware conversion and note this is a cutover-time step, not a blocker for pre-staging |
| **Voice gateways (VG) treated as incompatible phones** | VG310/VG350/VG450 are analog infrastructure (FXS/FXO ports for fax, elevator phones, paging, intercoms), not phones. Pipeline classifies them as `INCOMPATIBLE` and stops — doesn't track the analog endpoints behind them or plan their migration path | `skip` decision, handle VG migration manually outside pipeline | New device tier `ANALOG_GATEWAY` + dedicated mapper: discover analog ports/assignments from CUCM, map to analog gateway devices in Control Hub. See detail below |
| **~~Preflight workspace license match string is wrong~~** | ~~`check_workspace_licenses()` matches on "Common Area"~~ | N/A | **FIXED** — Now matches `"calling" + "workspace"` substring, correctly matching `"Webex Calling - Workspaces"` and `"Webex Calling - Professional Workspaces"` |
| **Pipeline assumes all users get Webex Calling Professional licenses** | Webex Calling has a Standard license tier (`BASIC_USER` in the API spec). The pipeline maps all users as Professional — `check_licenses()` only counts "Calling Professional" licenses in preflight. Users who only need Standard are over-licensed, and the license count may incorrectly fail preflight if the org has a mix of Standard and Professional | Admin must manually reassign Standard licenses after migration, or manually adjust the preflight license count | Add user license tier inference (similar to workspace `license_tier` classification): analyze each user's CUCM feature profile to determine whether they need Standard or Professional, tag users with `license_tier`, and split `check_licenses()` to count Standard and Professional pools separately |
| **Pipeline doesn't handle Virtual Line/Profile licenses** | The `UserLicenseType` enum includes `VIRTUAL_PROFILE` ("webex calling virtual profile"). The pipeline has no concept of virtual lines — they are not extracted from CUCM and have no mapper or license counting | Virtual lines must be provisioned manually outside the pipeline | If CUCM virtual lines or shared-line appearances need to migrate as Webex virtual lines, add extraction, mapping, and a `check_virtual_line_licenses()` preflight check |
| **Pipeline doesn't track "Hot desk only" workspace licenses** | The API returns a separate `"Webex Calling - Hot desk only"` license distinct from `"Webex Calling - Workspaces"`. The pipeline doesn't distinguish hot-desk-only workspaces from regular workspaces during license counting | Admin must manually verify hot-desk license allocation | Add hot-desk detection during workspace mapping (workspaces flagged as `hotdesk_only` in CUCM), count separately in preflight |

**Detail on device-pool location mapping:** The pipeline groups device pools by their CUCM Location reference — pools sharing the same CUCM Location consolidate into one Webex location. This handles the 80% case where device pools = site topology. However, CUCM allows per-device Location overrides (a phone can have a different Location than its device pool). Deployments with functional device pools (e.g., "Phones", "Softphones", "CommonArea") spanning multiple physical sites, where the actual site is set via device-level Location overrides, will produce incorrect consolidation. The `LOCATION_AMBIGUOUS` decision surfaces this for admin review, but the `reassign` option requires manual per-device work. The enhancement (3 changes: extractor field, cross-ref, mapper divergence check) would automate the split.

**Detail on 9800 series:** FIXED in Phase 12c. The Cisco 9800 series (9811, 9821, 9841, 9851, 9861, 9871) plus 8875 video phone run PhoneOS and are now classified as `NATIVE_MPP`. The 7811 was moved from `_INCOMPATIBLE_WITH_MPP` to `_CONVERTIBLE_PATTERNS` per Cisco's E2M converter tool listing.

**Detail on video/room device migration:** RoomOS video devices registered on CUCM (Room Kit, Room Kit Mini/Plus/Pro, Desk, Desk Pro, Desk Mini, Board 55/70/85, Codec Plus/Pro, Room 55/70 G2, Room Kit EQ/EQX) can re-register to Webex Calling as workspace devices. They run RoomOS and don't need firmware conversion — just a registration target change, similar to 9800 series phones. However, the migration path differs from phones: they become Webex **workspaces**, not user devices. Legacy video devices (DX70/DX80, TelePresence SX10/SX80, MX200/300/700/800) cannot register to Webex Calling for SIP calling — they are cloud-only. The enhancement would: (1) add RoomOS model patterns to `classify_phone_model()` or a separate `classify_video_device()`, (2) route them through workspace_mapper instead of device_mapper, (3) generate re-registration operations instead of firmware conversion decisions.

**Detail on third-party/generic SIP phone handling:** Third-party phones registered on CUCM (Polycom/Poly, Yealink, AudioCodes, etc.) correctly fall to INCOMPATIBLE since they can't be firmware-converted to Cisco MPP. However, many of these devices have a direct path to Webex Calling via two Cisco-published tiers:

- **Cisco Managed** — Cisco provisions and manages these in Control Hub like native devices. Full list at help.webex.com/njwkamr:
  - Poly: VVX 101-601, CCX 400-700, Edge 100-550, TRIO 8300/8500/8800
  - Yealink: T33G-T58A, W52/W56/W60/W70 DECT, CP920/CP925/CP960/CP965
  - AudioCodes: 425HD, 445HD, C450HD, MP-series gateways
  - Algo, 2N, Grandstream, CyberData, Axis, Singlewire (specialty/paging/intercom)

- **Customer Managed** — Any SIP phone/gateway supporting TLS 1.2 via "Generic SIP Phone" or "Generic SIP Gateway" profiles. Manual provisioning, no Control Hub auto-config. Up to 5 per workspace (Professional license). Reference: help.webex.com/nemh93t

The pipeline enhancement would:
1. Add `THIRD_PARTY_SUPPORTED` to `DeviceCompatibilityTier` — devices that can migrate to Webex Calling without hardware replacement
2. During discovery, extract vendor/model from CUCM phone records (the `model` and `product` fields identify third-party devices)
3. Classify against a lookup table of Cisco Managed device models → `THIRD_PARTY_SUPPORTED` tier
4. For unrecognized third-party models → `INCOMPATIBLE` with annotation: "May work via Generic SIP Profile (Customer Managed) if device supports TLS 1.2"
5. Deployment plan generates a "Device Migration by Vendor" section: Cisco Managed devices get provisioning instructions, Customer Managed devices get Generic SIP setup instructions, truly incompatible devices get replacement recommendations
6. The lookup table should be derived from the published list at help.webex.com/qkwt4j and updated as Cisco adds new supported devices

This touches the classifier, device_mapper, and deployment plan — moderate scope, good candidate for a dedicated build phase.

**Detail on firmware conversion prerequisite:** Pre-staging device configs in Webex before firmware conversion is the correct approach — when the phone is eventually converted to MPP and factory reset, it checks into Webex, finds its MAC already provisioned, and downloads its config. The deployment plan just needs an informational note listing which devices need conversion at cutover time so the admin doesn't forget that manual step.

**Detail on voice gateway and ATA migration:** Voice gateways (VG310, VG350, VG450) and ATAs are analog infrastructure — they connect analog devices (fax machines, elevator phones, overhead paging, door intercoms, alarm panels) to the call platform.

In Webex Calling, analog gateways (VGs and ATAs) are manually added as devices in Control Hub — they register directly to Webex Calling as analog gateway devices. Key constraints:
- **VGs:** Can be re-registered to Webex Calling as analog gateway devices in Control Hub. Same hardware, new registration target.
- **ATA 190:** Incompatible. Must be replaced with ATA 191/192 (MPP firmware, ships from factory).
- **ATA 191/192 replacements:** Cannot be pre-staged — the MAC address isn't known until the hardware is purchased and deployed. These must be flagged for manual follow-up.

The pipeline enhancement would:
1. Add `ANALOG_GATEWAY` to `DeviceCompatibilityTier` — separate from phones
2. During discovery, extract VG/ATA port assignments from CUCM (which analog devices/DNs are on which ports)
3. Generate `ANALOG_MIGRATION_PATH` decisions: "re-register VG to Webex" vs "replace ATA with 191/192" vs "decommission"
4. For replacements (ATA 190 → 191/192): flag in deployment plan as **manual follow-up** — admin must purchase hardware, then manually add device in Control Hub with the new MAC
5. Deployment plan includes an "Analog Devices — Manual Follow-Up" section listing all flagged endpoints with their current DN assignments, port mappings, and physical function (fax, elevator, etc.) so the admin has a punch list

This is a meaningful scope expansion — it touches discovery, normalization, a new mapper, and the planner. Good candidate for a dedicated build phase after the current pipeline stabilizes.

**Detail on Webex Calling license types — verified from OpenAPI spec and live API (2026-03-23):**

The `UserLicenseType` enum from the Webex Calling OpenAPI spec (`webex-cloud-calling.json`) defines 5 license types:

| Enum Value | Description | Notes |
|-----------|-------------|-------|
| `BASIC_USER` | "webex calling standard user" | Standard/Basic user license. Not present in trial sandbox org — likely only appears in production orgs with mixed licensing |
| `PROFESSIONAL_USER` | "webex calling professional user" | Full-feature user license |
| `WORKSPACE` | "webex calling common area workspace" | Standard workspace license |
| `PROFESSIONAL_WORKSPACE` | "webex calling professional workspace" | Workspace with advanced features (call recording, etc.) |
| `VIRTUAL_PROFILE` | "webex calling virtual profile" | Virtual line/extension license — pipeline does not handle this type |

Actual license name strings from the live API (`GET /licenses`, via `wxcli licenses list`):

| API License Name | Type |
|-----------------|------|
| `"Webex Calling - Professional"` | User (maps to `PROFESSIONAL_USER`) |
| `"Webex Calling - Workspaces"` | Workspace (maps to `WORKSPACE`) |
| `"Webex Calling - Hot desk only"` | Workspace variant — separate license, not tracked by pipeline |

Note: `"Webex Calling - Standard"` (for `BASIC_USER`) and the Professional Workspace license name were not present in this sandbox org. The Standard license likely appears as `"Webex Calling - Standard"` in production orgs but this has not been confirmed against a live API response.

**Preflight impact:** `check_workspace_licenses()` currently matches on `"Common Area"` which does not match the actual API name `"Webex Calling - Workspaces"` — the match string must be fixed. `check_licenses()` matches on `"Calling Professional"` which is a substring of `"Webex Calling - Professional"` — this works if the match is substring-based, but should be verified.

**Detail on Standard vs Professional user license tier:** The pipeline currently treats every user as needing Webex Calling Professional because the mappers and preflight checks don't analyze which CUCM features each user actually uses. The `BASIC_USER` enum value exists in the spec (described as "webex calling standard user"), confirming that a Standard tier exists. The enhancement would mirror the workspace license tier pattern: during mapping, examine each user's CUCM feature profile and classify them as Standard or Professional. The preflight check would then count each tier separately and verify the org has enough of each license type. The exact Standard vs Professional feature boundary should be verified against current Cisco documentation before implementing tier inference.

**Detail on Workspace vs Professional Workspace license tier:** The workspace mapper and analyzer use "Workspace" and "Professional Workspace" as tier names, which align with the `WORKSPACE` and `PROFESSIONAL_WORKSPACE` enum values in the spec. The actual API license name for standard workspaces is `"Webex Calling - Workspaces"` (not "Common Area"). The preflight match string needs to be updated accordingly. The Professional Workspace license name was not observed in the sandbox org and should be confirmed before implementing tier-aware preflight.

### Architecture Decision: Hybrid (Summary Plan + DB-Driven Execution) — DECIDED (2026-03-23)

**Decision: Option C (Hybrid)** — summary markdown for admin review + DB-driven runtime execution.

The current model (static deployment-plan.md with every CLI command) breaks at scale
(10k users → 30k+ operations), has fragile `{STEP_N_ID}` placeholder resolution, and
caused 6 of 15 Round 2 bugs. The DB already has the right schema. The skill now queries
the DB directly: `next-batch → build command → execute → mark-complete → next-batch`.
The markdown plan becomes a summary-only artifact for admin approval.

**Design spec:** `docs/plans/cucm-pipeline/08-execution-architecture.md`

**Implementation prompts (all complete):**

| Prompt | Scope | Status |
|--------|-------|--------|
| `docs/prompts/phase-12a-upstream-bugfixes.md` | 9 upstream data-quality bugs | **COMPLETE** (2026-03-24) |
| `docs/prompts/phase-12b-execution-layer.md` | Skill-delegated execution, command_builder deleted | **COMPLETE** (2026-03-24) |
| `docs/prompts/phase-12c-model-table-update.md` | Phone model table: full 78xx/88xx/9800/8875 lineup | **COMPLETE** (2026-03-25) — 64 tests |

**All Round 2+3 bugs are fixed** (12a/12b/12c, generator fix, skill recovery pattern, UUID resolution).

### Platform Corner Cases — Execution-Time Failures (2026-03-26)

Discovered during phase10-verify and phase10-clean live execution. These are org-wide → location-scoped mismatches, silent data loss, and handler gaps that cause cascading failures or incorrect Webex configurations.

**Priority 1 — Cause execution failures:**

| # | Corner Case | Impact | Current Behavior | Fix |
|---|-------------|--------|-----------------|-----|
| 1 | **Route group location inference** | Route groups in CUCM are org-wide, but member trunks now auto-assign to locations. If trunks land in different locations, route group creation may fail or pick arbitrary location | No location logic in route group handler | Route group handler should infer location from its trunk members; if trunks span locations, create a `LOCATION_AMBIGUOUS` decision |
| 2 | **Cross-location hunt group/call queue agents** | CUCM hunt lists can have agents from any partition. Webex hunt groups are location-scoped. If agents span locations, the feature goes to the first agent's location | FeatureMapper picks first agent's location silently | FeatureMapper should detect cross-location agents and create a decision: split into per-location groups, or assign all to one location with admin confirmation |
| 3 | **Max members per feature** | Webex hunt groups cap at 50 agents, call queues at 50. CUCM has no practical limit | No validation — large groups get 400 errors at execution time | Add member count validation in FeatureMapper or preflight. Truncate with warning, or split into multiple groups with admin decision |
| 4 | **Certificate-based trunk handler** | Cert-based trunks need certificate exchange with Webex, not registration passwords | Handler generates a password for all trunks regardless of type | Handler should check `trunk_type == "CERTIFICATE_BASED"` and either skip password generation or create a `MANUAL_STEP` decision for cert exchange |

**Priority 2 — Silent data loss during transformation:**

| # | Corner Case | Impact | Current Behavior | Fix |
|---|-------------|--------|-----------------|-----|
| 5 | **CSS→Calling Permission is lossy** | CUCM partition/CSS model is far more granular than Webex outgoing permissions (international/national/local). Complex CSSes with blocking partitions, time-of-day routing via partitions, and per-line CSS overrides all collapse into coarse permissions | CSSMapper does best-effort classification. No warning about fidelity loss | Add `FEATURE_APPROXIMATION` decision when CSS complexity exceeds what Webex permissions can represent. Include before/after comparison in decision context |
| 6 | **SIP Normalization scripts disappear** | CUCM Lua scripts for SIP header manipulation have no Webex equivalent. Could break carrier interop | Scripts are not extracted or flagged | Discovery should extract SIP normalization script assignments from trunks. Mapper should create `FEATURE_APPROXIMATION` decision listing affected trunks and script names. Assessment report should include a "SIP Normalization — Manual Review Required" section |
| 7 | **Custom MoH audio not migrated** | Music on Hold audio files can't be auto-migrated. Webex requires manual upload | Not flagged anywhere in pipeline | Discovery should detect custom MoH audio sources in CUCM. Create informational decision or add to deployment plan as manual follow-up |

**Priority 3 — Edge cases that degrade configuration quality:**

| # | Corner Case | Impact | Current Behavior | Fix |
|---|-------------|--------|-----------------|-----|
| 8 | **BLF targets across locations** | BLF monitoring targets in different locations may not resolve if cross-location monitoring is disabled | Device layout handler silently converts unresolved BLF to OPEN | Handler should log a warning when BLF target is unresolved. DeviceLayoutMapper should create informational decision listing cross-location BLF targets that may not work |
| 9 | **Shared lines across locations** | CUCM shared lines can span any two phones regardless of location. Webex has cross-location shared line restrictions | SharedLineAnalyzer may not catch all cross-location cases | SharedLineAnalyzer should check whether shared line members are in different Webex locations and flag with `SHARED_LINE_COMPLEX` if cross-location restrictions apply |
| 10 | **E911/emergency services gap** | CUCM ELIN/ERL emergency routing → Webex RedSky integration is a completely different model. No automated migration path | Not addressed in pipeline | At minimum: flag in assessment report as "Emergency Services — Complete Redesign Required". E911 configuration should never be silently skipped |

### Optional future work
- **BLOCKING: Replace hand-written command files with generated versions** — 4 files (`users.py`, `locations.py`, `numbers.py`, `licenses.py`) were hand-coded before the generator existed. **These files do NOT receive generator fixes** — any improvement to `command_renderer.py` (--json-body bypass, orgId auto-injection, output format, error handling, new features) only applies to the 96 generated files, not these 4. This is a drift risk that grows with every generator change. Replace with generated commands + `field_overrides.yaml` customizations. The only non-trivial blocker is `users create` which needs `--extension` + `calling_data=True` + wxc_sdk `Person` model logic — handle via a generator post-processing hook, `field_overrides.yaml` custom code block, or a thin wrapper that calls the generated command. **Do not add more hand-written command files.** If a generated command needs custom behavior, use `field_overrides.yaml` to customize it.
- ~~**Scope expansion**~~ — **MOSTLY COMPLETE.** Tier 2 (8/8), Tier 3 (20/20), Tier 4 (6/11). See `docs/plans/cucm-pipeline/future/CLAUDE.md` for remaining Tier 4 items
- **End-to-end test against live CUCM test bed** — 80 objects at 10.201.123.107

### All phases completed
- ~~Phase 3a: Gap designs~~ — **COMPLETE**
- ~~Phase 3b: Build planning~~ — **COMPLETE** (43/43 checks passed)
- ~~Phase 01 + 02~~ — **COMPLETE** (foundation + risk spikes)
- ~~Phase 03: Extraction~~ — **COMPLETE** (validated against live CUCM 15.0)
- ~~Phase 04: Normalization~~ — **COMPLETE** (reconciled with Phase 03, 3-agent code review)
- ~~Phase 05: Mappers~~ — **COMPLETE** (9 mappers + engine, 557 tests)
- ~~Phase 06: Analyzers~~ — **COMPLETE** (12 analyzers + pipeline + merge, 668 tests, 5-agent code review)
- ~~Phase 07: Planning~~ — **COMPLETE** (planner, dependency DAG, batch partitioning, 740 tests)
- ~~Phase 08-revised: CUCM CLI~~ — **COMPLETE** (13 commands, 39 CLI tests, 1220 total)
- ~~Phase 09-revised: Export~~ — **COMPLETE** (27 builders, 7-section deployment plan, 66 new tests, 892 total)
- ~~Phase 10-revised: Preflight~~ — **COMPLETE** (8 checks, runner, CLI command, 49 new tests)
- ~~Phase 11-revised: Migrate Skill~~ — **COMPLETE** (6-step skill, 7 domain skill delegations, 1294 total tests)
- ~~Phase 12: Execution Architecture Evaluation~~ — **COMPLETE** (2026-03-23) — chose Hybrid (Option C). Design spec, 3 implementation prompts written.
- ~~Phase 12a: Upstream Bugfixes~~ — **COMPLETE** (2026-03-24) — 9 data-quality bugfixes
- ~~Phase 12b: Execution Layer~~ — **COMPLETE** (2026-03-24) — skill-delegated execution rewrite, command_builder deleted
- ~~Phase 12c: Model Table Update~~ — **COMPLETE** (2026-03-25) — 8851 → CONVERTIBLE, 9800 → NATIVE_MPP
- ~~Phase 06b: Expansion~~ — **COMPLETE** (2026-03-25) — cascade re-evaluation, auto-rule match field (4 operators), multi-analyzer coexistence. 14 tests.
- ~~Phase 13: Migration Advisory System~~ — **COMPLETE** (2026-03-25) — 20 recommendation rules + 20 cross-cutting patterns + ArchitectureAdvisor + two-phase pipeline + CLI + skill integration
- ~~Tier 2 Wave 1: Shared Infrastructure~~ — **COMPLETE** (2026-03-25) — 3 new DecisionTypes, 2 new canonical types (CanonicalCallForwarding, CanonicalMonitoringList), 3 recommendation rules, 2 new mappers (CallForwardingMapper, MonitoringMapper), SIP/security profile detail in routing extractor, 2 new report sections. 1350 tests.
- ~~Fix Missing Migration Operations~~ — **COMPLETE** (2026-03-30) — 6 data-flow fixes: cross-ref phone mirror, shared_line status transition, is_common_area flag injection, voicemail enrichment, new CallSettingsMapper, diagnostic logging. Pipeline went from 383 → 984 operations on dCloud data. 1640 tests.
- ~~Tier 3: Informational Extraction~~ — **COMPLETE** — InformationalExtractor (20 types, 4 categories), normalizers, 4-section report appendix
- ~~Tier 2: Enterprise Expansion (all 3 waves)~~ — **COMPLETE** — 8 items: Call Forwarding, Speed Dials/BLF/Monitoring, Extension Mobility, MOH, Announcements, E911, SNR, SIP Profiles. 4 new DecisionTypes, 10 canonical types, 9 mappers, 5 extractors
- ~~Tier 4 Wave 1: Feature Gap Extraction~~ — **MOSTLY COMPLETE** — 6/11 items built (Recording, SNR, Button Templates, Transformation Patterns, Extension Mobility, partial User Locale). Tier4Extractor, 4 advisory patterns (P17-P20), 4 report appendix sections (S/T/U/V). 5 items remaining: Intercom enhancement, shared line behavior, Jabber inventory, firmware versions, voicemail PIN management

### Upstream Data Gaps (discovered 2026-03-30 via diagnostic logging — all code-fixed)

Three operation types were absent from the dCloud execution plan. All three have code fixes applied. Voicemail and SNR gaps are dCloud-specific data quality issues (code works when CUCM data has the assignments). Route pattern extraction and normalization were genuine code bugs, now fixed.

| Missing Type | Diagnostic Output | Root Cause | Status |
|---|---|---|---|
| `user:configure_voicemail` | VoicemailMapper: 0 created, 0 updated. All 52 users have `voicemail_profile_id=None` | Code is correct: `_build_voicemail_refs()` builds cross-refs, `VoicemailMapper` enriches users via `enrich_user()`. dCloud users simply don't have `voiceMailProfile` assignments in CUCM AXL data | **CODE FIXED** — works when CUCM data has voicemail profile assignments. dCloud data gap, not a code bug |
| `dial_plan:create` | "29 route patterns processed=0, skipped (@macro)=0, skipped (no target)=29, dial plans created=0" | Two bugs: (1) Extractor used list-only, missing destination data. (2) Normalizer omitted `target_type`/`target_name`. | **FIXED** (2026-03-30) — Extractor now does list+get (`getRoutePattern` per pattern). Normalizer extracts `gatewayName`/`routeListName` into `target_type`/`target_name`. 3 new tests. dCloud may still show 0 if route patterns have no destinations in CUCM |
| `single_number_reach:configure` | "25 remote_destination objects, 0 unique owners" | Code is correct: `_build_remote_destination_refs()` exists and runs in CrossReferenceBuilder. dCloud remote_destination objects don't have populated `ownerUserId` fields in AXL data | **CODE FIXED** — works when CUCM data has owner assignments. dCloud data gap, not a code bug |
