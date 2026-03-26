# CUCM Migration Tool — Build Execution Checklist

Copy/paste the prompt for each phase into a new Claude Code chat. Run in order. Phases marked "parallel" can run in separate windows simultaneously.

## Pre-flight

- [ ] All design docs exist:
  - [ ] `docs/plans/cucm-pipeline/01-data-representation.md`
  - [ ] `docs/plans/cucm-pipeline/02-normalization-architecture.md`
  - [ ] `docs/plans/cucm-pipeline/02b-cucm-extraction.md`
  - [ ] `docs/plans/cucm-pipeline/03-conflict-detection-engine.md`
  - [ ] `docs/plans/cucm-pipeline/03b-transform-mappers.md`
  - [ ] `docs/plans/cucm-pipeline/04-css-decomposition.md`
  - [ ] `docs/plans/cucm-pipeline/05-dependency-graph.md`
  - [ ] `docs/plans/cucm-pipeline/05a-preflight-checks.md`
  - [ ] `docs/plans/cucm-pipeline/05b-executor-api-mapping.md`
  - [ ] `docs/plans/cucm-pipeline/06-decision-workflow.md`
  - [ ] `docs/plans/cucm-pipeline/07-idempotency-resumability.md`
- [ ] `docs/prompts/design-guardrails.md` exists
- [ ] `src/wxcli/migration/` directory does NOT exist yet (clean start)

---

## Phase 01: Foundation ⏱ ~1 session

**Can parallel with Phase 02.**

```
Read and execute docs/prompts/phase-01-foundation.md
```

**Produces:**
- `src/wxcli/migration/__init__.py`
- `src/wxcli/migration/models.py`
- `src/wxcli/migration/store.py`
- `src/wxcli/migration/state.py`
- `src/wxcli/migration/rate_limiter.py`
- `tests/migration/test_models.py`
- `tests/migration/test_store.py`
- `tests/migration/test_state.py`
- `tests/migration/test_rate_limiter.py`

**Done when:**
- [ ] All 4 source files + 4 test files exist
- [ ] Tests pass
- [ ] Expansion investigation completed (no blocking gaps found)

---

## Phase 02: Risk Spikes ⏱ ~1 session

**Can parallel with Phase 01.**

```
Read and execute docs/prompts/phase-02-risk-spikes.md
```

**Produces:**
- `src/wxcli/migration/transform/cucm_pattern.py`
- `src/wxcli/migration/transform/e164.py`
- `tests/migration/transform/test_cucm_pattern.py`
- `tests/migration/transform/test_e164.py`

**Done when:**
- [ ] Both source files + both test files exist
- [ ] 10+ cucm_pattern tests pass (including overlap detection)
- [ ] 15+ e164 tests pass (including international formats)
- [ ] Expansion investigation completed

---

## Phase 03: CUCM Extraction ⏱ ~1-2 sessions

**Requires Phase 01 complete.**

```
Read and execute docs/prompts/phase-03-extraction.md
```

**Produces:**
- `src/wxcli/migration/cucm/connection.py`
- `src/wxcli/migration/cucm/discovery.py`
- `src/wxcli/migration/cucm/extractors/` (8 extractor files)
- `tests/migration/cucm/` (test files + fixture dicts)

**Done when:**
- [ ] connection.py + 8 extractors + discovery.py exist
- [ ] Fixture dicts exist for at least: user, phone, CSS, route pattern, device pool
- [ ] Tests pass with mocked zeep (no live CUCM needed)
- [ ] Expansion investigation completed

---

## Phase 04: Normalization ⏱ ~1 session

**Requires Phase 01 + Phase 03 complete.**

```
Read and execute docs/prompts/phase-04-normalization.md
```

**Produces:**
- `src/wxcli/migration/transform/normalizers.py`
- `src/wxcli/migration/transform/cross_reference.py`
- `tests/migration/transform/test_normalizers.py`
- `tests/migration/transform/test_cross_reference.py`

**Done when:**
- [ ] Pass 1 normalizers handle all fixture dicts from Phase 03
- [ ] CrossReferenceBuilder produces all 27 relationship types
- [ ] Shared line detection works (DN on 2+ devices)
- [ ] CSS partition ordering preserved
- [ ] Expansion investigation completed

---

## Phase 05: Mappers ⏱ ~4-5 sessions

**Requires Phase 01 + Phase 02 + Phase 04 complete.**

```
Read and execute docs/prompts/phase-05-mappers.md
```

This is a dispatcher prompt — it runs 4-5 sub-sessions (05a through 05e). Follow the session groupings in the prompt.

**Produces:**
- `src/wxcli/migration/transform/mapper_base.py`
- `src/wxcli/migration/transform/mappers/` (9 mapper files)
- `src/wxcli/migration/transform/engine.py`
- `tests/migration/transform/mappers/` (9 test files)
- `tests/migration/transform/test_engine.py`
- `tests/migration/transform/test_integration.py`

**Sub-session order:**

### 05a: Foundational mappers + Mapper base class
```
Read and execute docs/prompts/phase-05-mappers.md — run Session 05a only (location_mapper, user_mapper, line_mapper + Mapper protocol)
```
- [ ] mapper_base.py defines Mapper protocol
- [ ] 3 mappers + 3 test files exist and pass

### 05b: Infrastructure mappers
```
Read and execute docs/prompts/phase-05-mappers.md — run Session 05b only (device_mapper, workspace_mapper, routing_mapper)
```
- [ ] 3 mappers + 3 test files exist and pass

### 05c: CSS decomposition mapper (solo)
```
Read and execute docs/prompts/phase-05-mappers.md — run Session 05c only (css_mapper — imports cucm_pattern.py from Phase 02)
```
- [ ] css_mapper produces both CanonicalDialPlan and CanonicalCallingPermission
- [ ] Tests cover ordering conflicts and pattern overlap

### 05d: Feature + voicemail mappers
```
Read and execute docs/prompts/phase-05-mappers.md — run Session 05d only (feature_mapper + voicemail_mapper)
```
- [ ] feature_mapper includes hunt pilot classification algorithm
- [ ] voicemail_mapper handles Unity Connection gap cases

### 05e: Engine + integration
```
Read and execute docs/prompts/phase-05-mappers.md — run Session 05e only (engine.py + integration test)
```
- [ ] engine.py orchestrates all 9 mappers in dependency order
- [ ] Integration test: fixture → normalize → map → verify output
- [ ] Expansion investigation completed

---

## Phase 06: Analyzers ⏱ ~2-3 sessions

**Requires Phase 01 + Phase 05 complete.**

```
Read and execute docs/prompts/phase-06-analyzers.md
```

**Produces:**
- `src/wxcli/migration/transform/analyzers/` (12 analyzer files)
- `src/wxcli/migration/transform/analysis_pipeline.py`
- `tests/migration/transform/analyzers/`
- `tests/migration/transform/test_analysis_pipeline.py`
- `tests/migration/transform/test_decision_merge.py`

**Done when:**
- [ ] All 12 analyzers exist with analyze() + fingerprint() methods
- [ ] analysis_pipeline.py runs all analyzers + applies auto-rules
- [ ] Decision merge test passes (re-analyze preserves resolved decisions)
- [ ] Analyzers check for mapper-produced decisions before duplicating
- [ ] Expansion investigation completed

---

## Phase 07: Planning ⏱ ~1 session

**Requires Phase 01 + Phase 06 complete.**

```
Read and execute docs/prompts/phase-07-planning.md
```

**Produces:**
- `src/wxcli/migration/execute/planner.py`
- `src/wxcli/migration/execute/dependency.py`
- `src/wxcli/migration/execute/batch.py`
- `tests/migration/execute/test_planner.py`
- `tests/migration/execute/test_dependency.py`
- `tests/migration/execute/test_batch.py`

**Done when:**
- [ ] expand_to_operations() handles all object types
- [ ] DAG builds correctly with NetworkX
- [ ] Cycle detection: SOFT cycles break, all-REQUIRES cycles error
- [ ] Batch partitioning: org-wide first, then per-site
- [ ] Expansion investigation completed

---

## Phase 08: Preflight + Snapshot ⏱ ~1 session

**Requires Phase 01 + Phase 07 complete.**

```
Read and execute docs/prompts/phase-08-preflight.md
```

**Produces:**
- `src/wxcli/migration/execute/preflight.py`
- `src/wxcli/migration/execute/snapshot.py`
- `tests/migration/execute/test_preflight.py`
- `tests/migration/execute/test_snapshot.py`

**Done when:**
- [ ] All 7 preflight checks produce PASS/WARN/FAIL
- [ ] NUMBER_CONFLICT + DUPLICATE_USER decisions generated correctly
- [ ] Snapshot captures pre-migration Webex state
- [ ] Expansion investigation completed

---

## Phase 09: Executor + Rollback ⏱ ~1-2 sessions

**Requires Phase 07 + Phase 08 complete.**

```
Read and execute docs/prompts/phase-09-executor.md
```

**Produces:**
- `src/wxcli/migration/execute/executor.py`
- `src/wxcli/migration/execute/rollback.py`
- `tests/migration/execute/test_executor.py`
- `tests/migration/execute/test_rollback.py`

**Done when:**
- [ ] Executor walks DAG in tier order with mocked API calls
- [ ] Journal entries recorded for all 4 types
- [ ] Dry-run produces formatted output without API calls
- [ ] Rollback reverses all 4 journal types correctly
- [ ] Expansion investigation completed

---

## Phase 10: Validate + Report ⏱ ~1 session

**Requires Phase 09 complete.**

```
Read and execute docs/prompts/phase-10-validate.md
```

**Produces:**
- `src/wxcli/migration/validate/comparator.py`
- `src/wxcli/migration/validate/report.py`
- `tests/migration/validate/test_comparator.py`
- `tests/migration/validate/test_report.py`

**Done when:**
- [ ] Comparator reads journal, GETs resources, compares fields
- [ ] Report generates markdown with provenance trail
- [ ] Expansion investigation completed

---

## Phase 11: CLI Commands ⏱ ~1-2 sessions

**Requires ALL previous phases complete.**

```
Read and execute docs/prompts/phase-11-cli.md
```

**Produces:**
- `src/wxcli/commands/cucm.py`
- `src/wxcli/commands/cucm_config.py`
- Update to `src/wxcli/main.py` (register cucm group)
- `tests/commands/test_cucm.py`

**Done when:**
- [ ] `wxcli cucm --help` shows all ~20 commands
- [ ] `wxcli cucm status` reads state.json correctly
- [ ] `wxcli cucm decisions` shows Rich table with severity colors
- [ ] `wxcli cucm execute --dry-run` produces formatted output
- [ ] Expansion investigation completed

---

## Phase 12: Agent + Skills ⏱ ~1 session

**Requires Phase 11 complete.**

```
Read and execute docs/prompts/phase-12-agent-skills.md
```

**Produces:**
- `.claude/agents/cucm-migration-builder.md`
- `.claude/skills/cucm-discovery/SKILL.md`
- `.claude/skills/cucm-migration/SKILL.md`
- `docs/reference/cucm-migration.md`
- `docs/reference/cucm-axl-mapping.md`

**Done when:**
- [ ] Agent follows 9-step workflow (interview → validate)
- [ ] Skills registered and invocable
- [ ] Reference docs grounded in 03b and 02b
- [ ] CLAUDE.md file map updated
- [ ] Expansion investigation completed

---

## Post-Build

- [ ] Full integration test: fixture CUCM data → normalize → map → analyze → plan → mock-execute → validate
- [ ] `wxcli cucm` end-to-end smoke test with fixture data
- [ ] Update `docs/plans/cucm-migration-roadmap.md` to mark Phase 4 complete
- [ ] Commit all files

## Estimated Total: ~16-20 sessions
