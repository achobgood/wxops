# TODO — docs/plans

## Ready

- [ ] Phase 11-revised: Migrate Skill — `docs/prompts/phase-11-cucm-migrate-skill.md` (feeds plan to wxc-calling-builder agent). All prerequisites complete.

## Blocked (waiting on dependencies)
- [ ] Phase 5: Integration Testing — end-to-end pipeline tests. Blocked on Phase 11.

## Done

- [x] Phase 1: Architecture Design — 8 pipeline architecture docs complete (01-07 + 03b)
- [x] Phase 2: Mapper Design & Review — 9 mappers designed in 03b, 5+ rounds review, synthesis verified
- [x] Phase 3a: Gap Design — AXL extraction (02b), executor API mapping (05b), preflight checks (05a) all complete
- [x] Phase 3b: Build Planning — strategy, contracts, mapper sessions all complete (43/43 review checks passed)
- [x] Phase 01 Foundation — models.py, store.py, state.py, rate_limiter.py
- [x] Phase 02 Risk Spikes — e164.py, cucm_pattern.py
- [x] Phase 03 Extraction — connection.py, 8 extractors, discovery.py (validated live CUCM 15.0)
- [x] Phase 04 Normalization — 24 normalizers, CrossReferenceBuilder, pipeline.py
- [x] Phase 05 Mappers — 9 mappers + engine.py + rules.py + decisions.py (5 sessions)
- [x] Phase 06 Analyzers — 12 analyzers + analysis_pipeline.py + merge_decisions() (5-agent code review)
- [x] Phase 07 Planning — planner.py, dependency.py, batch.py
- [x] Phase 08-revised CUCM CLI — cucm.py (12 commands), cucm_config.py, 39 CLI tests, 1220 total passing
- [x] Phase 09-revised Export — command_builder.py (27 op builders), deployment_plan.py (7-section), json/csv exports. 66 new tests, 892 total passing.
- [x] Phase 10-revised Preflight — preflight/ module (8 checks), runner.py, CLI `wxcli cucm preflight`. 49 new tests, 892 total passing.
