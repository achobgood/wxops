# migration/ — CUCM→Webex Migration Tool

All 11 phases complete. **1487 tests passing.** Wired into the CLI as `wxcli cucm <command>`. Does NOT use the auto-generator.

## File Map

| Path | Purpose |
|------|---------|
| `docs/plans/cucm-migration-roadmap.md` | **Master roadmap** — what's done, what's ready, what's next. Start here. |
| `docs/plans/cucm-pipeline-architecture.md` | Pipeline architecture summary — SQLite store, two-pass ELT, linter-pattern analyzers, NetworkX DAG |
| `docs/plans/cucm-pipeline/01-07 + 03b` | 8 detailed architecture docs |
| `src/wxcli/commands/cucm.py` | Phases 08+10 — CLI: 13 commands (init, discover, normalize, map, analyze, plan, preflight, decisions, decide, export, inventory, status, config) |
| `src/wxcli/commands/cucm_config.py` | Phase 08 — Config management helpers |
| `models.py` | Canonical data models — 26 types, DecisionType (21 values), Decision, MapperResult, TransformResult |
| `store.py` | SQLite-backed store — objects, cross_refs, decisions, journal, merge_log, merge_decisions() |
| `cucm/` | Phase 03 — AXL connection, 9 extractors, discovery pipeline |
| `transform/normalizers.py` | Phase 04 — 27 Pass 1 normalizers |
| `transform/cross_reference.py` | Phase 04 — CrossReferenceBuilder (30 relationships + 3 enrichments) |
| `transform/pipeline.py` | Phase 04 — `normalize_discovery()` entry point |
| `transform/mappers/` | Phase 05 — 14 mappers + base.py + engine.py (9 original + call_forwarding + monitoring + button_template + device_layout + softkey) |
| `transform/analyzers/` | Phase 06 — 12 analyzers (3 analyzer-owned + 9 mapper-owned) |
| `transform/analysis_pipeline.py` | Phase 06 — Orchestrator: run analyzers → merge → auto-rules + resolve_and_cascade() |
| `execute/` | Phase 07 — planner.py, dependency.py (NetworkX DAG), batch.py |
| `export/` | Phase 09 — deployment_plan.py, json/csv exports (command_builder.py removed in Phase 12b) |
| `preflight/` | Phase 10 — checks.py (8 preflight checks), runner.py (orchestrator), CLI `wxcli cucm preflight` |
| `advisory/` | Phase 13 — Advisory system: per-decision recommendations (19 rules) + cross-cutting advisor (16 patterns) |
| `report/` | Assessment report generator — complexity score, SVG charts, executive summary + appendix → HTML/PDF. See its CLAUDE.md. |
| `.claude/skills/cucm-migrate/SKILL.md` | Phase 11 — 6-step execution skill: preflight → plan summary → batch execute → delegate → report |

**Where the design spec and pipeline architecture docs conflict, the pipeline architecture docs are authoritative.**

Each subdirectory has its own CLAUDE.md (local context) and TODO.md (outstanding work).
See `docs/plans/cucm-migration-roadmap.md` for the master project status.

## Pipeline Commands

**To run a migration:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `decisions` → `plan` → `preflight` → `export` → then invoke `/cucm-migrate`.

**To generate an assessment report:** `wxcli cucm init` → `discover` (or `discover --from-file`) → `normalize` → `map` → `analyze` → `report --brand "..." --prepared-by "..."`. Does not require plan/preflight/export — the report reads directly from the post-analyze store.
