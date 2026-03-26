# docs/plans — CUCM-to-Webex Migration Design

This directory contains the design specification and build planning outputs for the CUCM-to-Webex Calling migration tool (`src/wxcli/migration/`). The tool is hand-coded (not auto-generated) and surfaces as `wxcli cucm <command>`. **All 11 phases complete, 1426 tests passing.** Use `/cucm-migrate` to execute after running the pipeline.

## File Dependency Order

1. **`cucm-wxc-migration.md`** — Original design spec. Module structure is STALE; pipeline docs override it.
2. **`cucm-pipeline-architecture.md`** — Pipeline architecture summary (SQLite store, two-pass ELT, linter-pattern analyzers, NetworkX DAG). Sections 3 and 7 marked as BUILT.
3. **`cucm-pipeline/`** — 8 detailed architecture docs (01 through 07 + 03b). These are the AUTHORITATIVE source for pipeline design decisions.
4. **`cucm-build-strategy.md`** — Build planning: strategy, risk assessment, phase ordering.
5. **`cucm-build-contracts.md`** — Build planning: module contracts, acceptance criteria.
6. **`cucm-build-mappers.md`** — Build planning: mapper session breakdown (D1-D4).

Build planning docs (4-6) depend on architecture docs (2-3) and must be consumed in order.

## Precedence Rule

**Where the design spec (`cucm-wxc-migration.md`) and the pipeline architecture docs (`cucm-pipeline/`) conflict, the pipeline docs are authoritative.**

## Unrelated Files

- `2026-03-18-multi-tier-call-flow*.md` — Customer deployment plan (not migration-related).
- `2026-03-20-nova-thornberry-cosmic-comics-queue.md` — Customer deployment plan (not migration-related).

## Project Status

See **[cucm-migration-roadmap.md](cucm-migration-roadmap.md)** for overall status, next steps, and prompt inventory.

Design prompts live in `docs/prompts/`. Design guardrails in `docs/prompts/design-guardrails.md`.
