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

## Phase 4: Build Execution — IN PROGRESS

12 build phases with per-phase execution prompts. Run in order (some can parallel as noted).

| Phase | Prompt | Depends On | Can Parallel With | Status |
|-------|--------|-----------|-------------------|--------|
| 01 Foundation | `docs/prompts/phase-01-foundation.md` | nothing | Phase 02 | **Complete** (2026-03-22) — models.py, store.py, state.py, rate_limiter.py |
| 02 Risk Spikes | `docs/prompts/phase-02-risk-spikes.md` | nothing | Phase 01 | **Complete** (2026-03-22) — e164.py, cucm_pattern.py |
| 03 Extraction | `docs/prompts/phase-03-extraction.md` | Phase 01 | — | **Complete** (2026-03-23) — connection.py, 8 extractors, discovery.py. Validated against live CUCM 15.0. See notes below. |
| 04 Normalization | `docs/prompts/phase-04-normalization.md` | Phase 01 + 03 | — | **Complete** (2026-03-23) — normalizers.py (24 normalizers), cross_reference.py (26 relationships + 3 enrichments), pipeline.py (entry point). Reconciled with live CUCM Phase 03 output. 3-agent code review, 357 tests passing. |
| 05 Mappers (4-5 sessions) | `docs/prompts/phase-05-mappers.md` | Phase 01 + 02 + 04 | — | — |
| 06 Analyzers | `docs/prompts/phase-06-analyzers.md` | Phase 01 + 05 | — | — |
| 07 Planning | `docs/prompts/phase-07-planning.md` | Phase 01 + 06 | — | — |
| 08 Preflight | `docs/prompts/phase-08-preflight.md` | Phase 01 + 07 | — | 05a gap design |
| 09 Executor | `docs/prompts/phase-09-executor.md` | Phase 07 + 08 | — | 05b gap design |
| 10 Validate | `docs/prompts/phase-10-validate.md` | Phase 09 | — | — |
| 11 CLI | `docs/prompts/phase-11-cli.md` | All phases | — | — |
| 12 Agent + Skills | `docs/prompts/phase-12-agent-skills.md` | Phase 11 | — | — |

**Gap design dependencies:** Phases 08, 09 are blocked on gap design docs (05a, 05b). Phase 03's gap (02b) is resolved.

**Parallelism:** Phase 01 and 02 can run simultaneously. All other phases are sequential.

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

## Phase 5: Integration Testing — READY (Phase 04 complete)

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
| `phase-06-analyzers.md` | Analyzers: 12 analyzers + analysis_pipeline.py | Ready |
| `phase-07-planning.md` | Planning: planner.py, dependency.py, batch.py | Ready |
| `phase-08-preflight.md` | Preflight + snapshot | Ready (blocked on 05a) |
| `phase-09-executor.md` | Executor + rollback | Ready (blocked on 05b) |
| `phase-10-validate.md` | Validate + report | Ready |
| `phase-11-cli.md` | CLI commands: cucm.py, cucm_config.py | Ready |
| `phase-12-agent-skills.md` | Agent + skills + reference docs | Ready |
| **Mapper Design Prompts (completed)** | | |
| `cucm-mapper-design.md` | Mapper design prompt | Executed |
| `cucm-mapper-design-phase2.md` | Chunked writing instructions | Executed |
| `cucm-mapper-review.md` | Per-mapper review agent swarm | Executed (5+ rounds) |
| `cucm-mapper-synthesis.md` | Cross-mapper synthesis review | Executed |
| **Other** | | |
| `setup-subfolder-docs.md` | Create subfolder CLAUDE.md + TODO.md files | Executed |
| `fix-known-issues.md` | Pre-existing prompt (unrelated) | — |

## What to Do Next

### Immediate (can start now)
1. **Phase 05: Mappers** — `docs/prompts/phase-05-mappers.md` (4-5 sessions, 9 mappers + engine.py)

### Completed
- ~~Phase 3a: Gap designs~~ — **COMPLETE**
- ~~Phase 3b: Build planning~~ — **COMPLETE** (43/43 checks passed)
- ~~Phase 01 + 02~~ — **COMPLETE** (foundation + risk spikes)
- ~~Phase 03: Extraction~~ — **COMPLETE** (validated against live CUCM 15.0)
- ~~Phase 04: Normalization~~ — **COMPLETE** (reconciled with Phase 03, 3-agent code review)

### Remaining build order
Phase 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12
