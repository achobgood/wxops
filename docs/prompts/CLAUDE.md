# docs/prompts — CUCM Migration Prompt Library

This directory contains all design, review, build-planning, and execution prompts for the CUCM-to-Webex Calling migration tool. Each prompt is a self-contained session script that produces specific deliverables (design specs, review reports, or build plans) into `docs/plans/`.

## Before Any Design Session

**Read `design-guardrails.md` first.** It contains hallucination prevention rules, citation requirements, checklist-before-writing protocol, and **mandatory code review** (rule 13 — dispatch `superpowers:code-reviewer` agent swarm after self-review, fix Critical/Important findings before declaring complete).

## Execution Order

1. **Design prompts** — produce architecture specs in `docs/plans/cucm-pipeline/` (ALL COMPLETE)
   - `cucm-mapper-design.md` + `cucm-mapper-design-phase2.md` (mapper specs)
   - `cucm-extraction-design.md` (AXL extraction spec)
   - `cucm-executor-design.md` (executor API mapping spec)
   - `cucm-preflight-design.md` (preflight check spec)

2. **Review prompts** — validate design outputs (ALL COMPLETE)
   - `cucm-mapper-review.md` (per-mapper agent swarm)
   - `cucm-mapper-synthesis.md` (cross-mapper synthesis)

3. **Build planning prompts** — produce build plans (ALL COMPLETE)
   - `build-1-strategy.md` (strategy, risk, order)
   - `build-2-contracts.md` (contracts, criteria)
   - `build-3-mappers.md` (mapper session breakdown)
   - `review-build-planning.md` (2-wave review — 43/43 PASS)

4. **Build phase prompts** — ALL 11 PHASES COMPLETE
   - `phase-01-foundation.md` through `phase-11-cucm-migrate-skill.md` — **ALL EXECUTED**
   - Pipeline is fully built. 1294 tests passing. See roadmap for the full kickoff sequence.

5. **Phase 12: Execution architecture + bugfixes** — EVALUATION COMPLETE, IMPLEMENTATION READY
   - `phase-12-execution-architecture.md` — **EXECUTED** (2026-03-23) — chose Hybrid (Option C)
   - `phase-12a-upstream-bugfixes.md` — **READY** (9 upstream data-quality bugs)
   - `phase-12b-execution-layer.md` — **READY** (DB-driven execution, depends on 12a)
   - `phase-12c-model-table-update.md` — **READY** (phone model table, independent)
   - Design spec: `docs/plans/cucm-pipeline/08-execution-architecture.md`

6. **Phase 13: Migration Advisory System** — READY
   - `phase-13a-advisory-foundation.md` — Decision model + store changes (run first)
   - `phase-13b-recommendation-rules.md` — 16 per-decision recommendation functions (parallel with 13c)
   - `phase-13c-advisory-patterns.md` — 16 cross-cutting patterns + ArchitectureAdvisor (parallel with 13b)
   - `phase-13d-advisory-integration.md` — Pipeline two-phase execution + CLI + skill (depends on 13a-c)
   - Design spec: `docs/superpowers/specs/2026-03-24-migration-advisory-design.md`
   - Master plan: `docs/superpowers/plans/2026-03-24-migration-advisory.md`

7. **Assessment Report v2** — READY FOR IMPLEMENTATION
   - `redesign-assessment-report.md` — **SUPERSEDED** by v2 spec (was v1 visual-only redesign)
   - v2 spec: `docs/superpowers/specs/2026-03-25-assessment-report-v2-design.md` — customer-centric redesign with design rationale
   - v2 plan: `docs/superpowers/plans/2026-03-25-assessment-report-v2.md` — 10-task implementation plan

## Superseded

- `cucm-migration-build.md` — superseded by `build-1/2/3`
- `phase-08-preflight.md`, `phase-09-executor.md`, `phase-10-validate.md`, `phase-11-cli.md`, `phase-12-agent-skills.md` — superseded by revised phases 08-11
- `redesign-assessment-report.md` — superseded by v2 spec/plan (see item 7 above)

## Status

See [`docs/plans/cucm-migration-roadmap.md`](../plans/cucm-migration-roadmap.md) for overall migration tool status.

Design prompts live in `docs/prompts/`. Design guardrails in `docs/prompts/design-guardrails.md`.
