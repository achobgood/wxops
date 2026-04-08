# Auto-Rule Architecture Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the CUCM migration pipeline's two drifting auto-rule matchers (`apply_auto_rules` vs `_check_auto_apply`) into a single config-driven matcher with cross-decision context enrichment, eliminating a silent CALLING_PERMISSION_MISMATCH data-loss bug (Bug F), and add a `wxcli cucm config reset` CLI subcommand to restore default config keys without clobbering unrelated customizations (Bug G).

**Architecture:**
- **Bug F** — Delete `_check_auto_apply()`. Rewrite `classify_decisions()` as a thin preview wrapper over a new `preview_auto_rules()` that shares matcher logic with `apply_auto_rules()` via a private `_iter_matching_resolutions()` generator. Add an `enrich_cross_decision_context()` pipeline step that writes `is_on_incompatible_device: bool` into non-stale MISSING_DATA decision contexts, so the cross-decision case becomes expressible as a regular config rule. Add a new default `MISSING_DATA` rule that matches that field. Thread `config` through `classify_decisions`, `generate_decision_review`, and the CLI `decide --apply-auto` / `decisions --export-review` branches.
- **Bug G** — Keep `load_config()` literal (no runtime merge). Add a `wxcli cucm config reset <key>` subcommand that replaces a single named key with its `DEFAULT_CONFIG` value, preserving other customizations.

**Tech Stack:** Python 3.11, pytest, Typer CliRunner, the existing `tests/migration/transform/test_rules.py` synthetic-store pattern, the existing `tests/migration/test_decision_cli.py` CliRunner fixture pattern.

**Source-of-truth design spec:** `docs/superpowers/specs/2026-04-07-auto-rule-architecture-unification-design.md`. Where this plan and the spec disagree, the spec wins — stop and ask the user instead of silently reconciling.

---

## Context: what's changing and why

Plan 2 of a 3-plan Wave 3 cleanup track. Plan 1 (separate chat) handles mapper/recommender integration gaps in `feature_mapper.py` and `recommendation_rules.py` — do NOT modify those files here. Plan 3 (separate chat) handles the Wave 3 runbook doc rewrites under `docs/runbooks/cucm-migration/` — do NOT modify those docs here.

**Bug F evidence (from the spec):** `apply_auto_rules()` at `src/wxcli/migration/transform/rules.py:94` is called by `analyze` via `AnalysisPipeline.run()` at `analysis_pipeline.py:144` and is fully config-driven. `_check_auto_apply()` at `src/wxcli/migration/transform/decisions.py:196` is called by `wxcli cucm decide --apply-auto` and `wxcli cucm decisions --export-review` via `classify_decisions()` (same file, line 136) and is a hardcoded 3-case switch that ignores the project's `config.json`. The two paths drift:
- The `CALLING_PERMISSION_MISMATCH` branch in `_check_auto_apply` reads `ctx.get("affected_user_count", len(ctx.get("assigned_users", [])))` but `css_permission.py:128` writes `assigned_users_count` — neither of the keys `_check_auto_apply` reads ever exists, so it always evaluates to `user_count == 0` and silently skips every pending CALLING_PERMISSION_MISMATCH decision.
- `apply_auto_rules` sets `resolved_by="auto_rule"`; `cucm.py:1269` sets `resolved_by="auto_apply"`. Two markers for the same logical action.
- The one case that isn't expressible as a current config rule is "MISSING_DATA on a device that also has DEVICE_INCOMPATIBLE" — it requires looking at *other* decisions, not just the current decision's context.

**Bug G evidence (from the spec):** `load_config()` at `cucm_config.py:49-57` uses `dict.update()` — a shallow replace. `apply_auto_rules()` at `rules.py:130-131` returns 0 immediately if `rules` is falsy. `test_empty_rules_list_returns_zero` at `tests/migration/transform/test_rules.py:74-78` enforces this no-merge contract. Operators who remove a default rule from `config.json` have no documented way to restore it short of hand-editing.

**What this plan does NOT fix** (see spec "Out of scope"):
- Wave 3 docs under `docs/runbooks/cucm-migration/` — Plan 3.
- `feature_mapper.py`, `recommendation_rules.py` — Plan 1.
- `DecisionType` enum or `Decision` model schema changes — stable contract.
- Changes to `config.json` on-disk format — backwards compatible.

## File structure

| File | Change | Purpose |
|---|---|---|
| `src/wxcli/migration/store.py` | Add `update_decision_context()` method near `save_decision()` (around line 461-503) | Targeted column update — patch a single decision's context JSON without re-fingerprinting. Prerequisite for enrichment. |
| `src/wxcli/migration/transform/analysis_pipeline.py` | Add module-level helper `enrich_cross_decision_context(store)`; insert step 3.5 in `AnalysisPipeline.run()`; add call to same helper at end of `resolve_and_cascade()` save loop | Cross-decision enrichment step. Writes `is_on_incompatible_device: bool` into every non-stale MISSING_DATA decision's context so a config rule can match it. |
| `src/wxcli/migration/transform/rules.py` | Add `_iter_matching_resolutions()` generator; refactor `apply_auto_rules()` to consume it; add `preview_auto_rules()` public function; add `reason` field support (with non-string fallback) | Unified matcher entry point. Both `apply_auto_rules` (mutates) and `preview_auto_rules` (pure) walk the same rule-match logic. |
| `src/wxcli/migration/transform/decisions.py` | Delete `_check_auto_apply()` entirely; rewrite `classify_decisions(store, config)` as a thin `preview_auto_rules` wrapper; update `generate_decision_review(store, project_id, config)` to accept + thread config | Delete the drifting matcher. `classify_decisions` becomes config-driven via preview. |
| `src/wxcli/commands/cucm_config.py` | Add one entry to `DEFAULT_AUTO_RULES` for `MISSING_DATA` / `is_on_incompatible_device`; optionally backfill `reason` on existing defaults; add documentation comment block | Make the new cross-decision rule a discoverable default for new projects. |
| `src/wxcli/commands/cucm.py` | Rewrite `decide --apply-auto` branch body to use `preview_auto_rules` + `apply_auto_rules` + enrichment; thread `config` through `decisions --export-review`; add new `config_reset` Typer command | CLI surface for the unified flow. `--apply-auto` now re-runs config rules. New `config reset <key>` restores defaults. |
| `.claude/skills/cucm-migrate/SKILL.md` | Rewrite Step 1c-fallback "Group 1: Auto-apply" bullet block and step 3 "Apply auto-resolvable decisions"; add optional `config reset` one-liner | Keep the fallback path honest about config-driven rules. Step 1c's primary agent path is NOT touched. |
| `tests/migration/transform/test_rules.py` | Append TestPreviewAutoRules class (~9 tests) | Cover preview semantics, reason fallbacks, option validation, resolved_by marker, CALLING_PERMISSION_MISMATCH regression. |
| `tests/migration/transform/test_cross_decision_enrichment.py` | **New file** | 7 tests covering `enrich_cross_decision_context()` idempotency, empty store, affected_objects path, stale skip, cascade interaction, MISSING_DATA fingerprint stability. |
| `tests/migration/transform/test_classify_decisions.py` | **New file** (replaces usage of old `test_decision_classify.py` tests that depend on `_check_auto_apply`) | 4 tests covering `classify_decisions(store, config)` auto-apply/needs-input split with custom and empty configs. |
| `tests/migration/transform/test_default_auto_rules_field_alignment.py` | **New file** | Parametrized over `DEFAULT_AUTO_RULES`. Every match key must exist in the producing analyzer's context (catches future analyzer/rule field-name drift). |
| `tests/migration/transform/test_decision_classify.py` | **Delete or rewrite** old tests that assert against `_check_auto_apply` / the old single-arg `classify_decisions(store)` signature | Old contract is gone — either the whole file is deleted (preferred) and replaced by `test_classify_decisions.py`, or the broken tests are updated to pass `config`. |
| `tests/migration/test_decision_cli.py` | Update `TestApplyAuto` tests to assert `resolved_by="auto_rule"` (was `"auto_apply"`); add 4 new tests | CLI integration coverage for the rewritten `--apply-auto` branch, config edits being picked up, existing-project backcompat, custom rule thread-through to `--export-review`. |
| `tests/migration/test_cucm_cli.py` | Append `TestConfigReset` class (~5 tests) | CLI integration coverage for `wxcli cucm config reset`. |

The plan is split into **three phases** to stay under the ~400-line per-phase guidance from `docs/superpowers/CLAUDE.md`. Phase files are force-added with `git add -f` because `docs/plans/` is gitignored (per the Plan 1 precedent at `docs/plans/2026-04-07-recommender-mapper-gap-hotfix.md`).

## Exit criteria

- `_check_auto_apply()` is deleted from `src/wxcli/migration/transform/decisions.py`.
- No file in `src/wxcli/migration/` or `src/wxcli/commands/` still writes `resolved_by="auto_apply"`.
- `apply_auto_rules()` is the only matcher function — `preview_auto_rules()` is a pure-read wrapper that shares `_iter_matching_resolutions()` with it.
- `wxcli cucm decide --apply-auto` reads `config.json`, runs `enrich_cross_decision_context`, previews what would resolve, prompts, then calls `apply_auto_rules`. Edits to `config.json` are picked up without re-running `analyze`.
- `wxcli cucm decisions --export-review` loads config once and threads it through `classify_decisions` and `generate_decision_review`. The markdown review file's "Auto-Apply" section reflects the project's actual config rules.
- `DEFAULT_AUTO_RULES` contains a new entry matching `MISSING_DATA` with `is_on_incompatible_device: True` → `skip`.
- `wxcli cucm config reset auto_rules` restores defaults for that single key, preserving other config keys, and refuses unknown keys with a helpful message.
- The silent CALLING_PERMISSION_MISMATCH skip regression is guarded by `test_calling_permission_mismatch_with_users_not_silently_skipped`.
- The full `tests/migration/` suite passes (1642 pre-Plan-2 tests + the ~25 new tests from this plan).
- SKILL.md Step 1c-fallback Group 1 and step 3 no longer reference the hardcoded 3 cases.
- Manual smoke test on a test project: edits to `config.json` are picked up by the next `decide --apply-auto`; `config reset auto_rules` restores defaults without clobbering `country_code`.

## Cross-plan coordination

- **Plan 1** modifies `src/wxcli/migration/transform/mappers/feature_mapper.py` and `src/wxcli/migration/advisory/recommendation_rules.py`. This plan does NOT touch either file. If a task in this plan surprises you by needing to edit one of those files, STOP — something is wrong with the scope boundary; ask the user before proceeding.
- **Plan 3** rewrites `docs/runbooks/cucm-migration/*.md`. This plan only touches `.claude/skills/cucm-migrate/SKILL.md` (Step 1c-fallback section only). If a task in this plan asks you to edit a `docs/runbooks/cucm-migration/` file, STOP — that's Plan 3's scope.
- Both Plan 1 and Plan 3 ship independently. No cross-plan dependencies from this plan's tasks.

## In-flight project upgrade procedure (document in user-facing docs)

Existing projects created via `wxcli cucm init` before this work shipped have a `config.json` seeded with the OLD 7 default auto-rules (no `MISSING_DATA` / `is_on_incompatible_device` rule). When this work ships, their MISSING_DATA decisions on incompatible devices will NOT auto-resolve by default. The operator has two options:

1. **Preserve customizations, add the rule by hand:** Open `<project>/config.json` in an editor and append to the `auto_rules` array:
   ```json
   {"type": "MISSING_DATA",
    "match": {"is_on_incompatible_device": true},
    "choice": "skip"}
   ```
2. **Reset defaults (clobbers custom rules in `auto_rules`):**
   ```bash
   wxcli cucm config reset auto_rules -p <project>
   ```

The new SKILL.md text (Task 13 in Phase C) documents this. The plan's smoke-test task (Task 15) verifies the upgrade procedure works.

## Phases

The rest of this plan is split into three phase files that must be executed in order:

1. **[Phase A — Foundations (Tasks 1-8)](2026-04-07-auto-rule-architecture-unification-plan-phase-a.md)**
   Store `update_decision_context` method (Task 1), `enrich_cross_decision_context` helper (Task 2), pipeline wiring in `AnalysisPipeline.run()` + `resolve_and_cascade()` (Task 3), `rules.py` refactor with `_iter_matching_resolutions` + `preview_auto_rules` (Task 4), new `MISSING_DATA` default rule + doc comment (Task 5), `decisions.py` rewrite deleting `_check_auto_apply` and giving `classify_decisions` a `config` parameter (Task 6), new `test_classify_decisions.py` + retire old `test_decision_classify.py` (Task 7), field-alignment parametrized test (Task 8). No CLI changes yet — the existing CLI callers of `classify_decisions(store)` break at the end of Phase A and are fixed in Phase B.

2. **[Phase B — CLI integration (Tasks 9-11)](2026-04-07-auto-rule-architecture-unification-plan-phase-b.md)**
   Thread `config` through the `decisions --export-review` branch + new integration tests (Task 9), rewrite the `decide --apply-auto` branch to use preview + enrichment + apply and update legacy `resolved_by="auto_apply"` tests to `"auto_rule"` + add 5 new CLI integration tests (Task 10), add the `wxcli cucm config reset` subcommand + 5 `TestConfigReset` tests (Task 11). At the end of Phase B, the full `tests/migration/` suite must pass.

3. **[Phase C — Cleanup + docs + smoke test (Tasks 12-15)](2026-04-07-auto-rule-architecture-unification-plan-phase-c.md)**
   Spec-mandated grep audit for stray `auto_apply` / `_check_auto_apply` references (Task 12), SKILL.md Step 1c-fallback Group 1 and numbered-step-3 rewrites (Task 13), final full-suite regression verification (Task 14), manual smoke test on a scratch `phase2-smoke` test project to verify config-edit pickup and `config reset` behavior end-to-end (Task 15).

Each phase file is self-contained: an executor with no prior context can open the phase file and work through it. Phase boundaries are also natural commit checkpoints — do not merge tasks across phases.

## Self-review checklist (run before asking for user approval)

- [x] Every task in every phase cites exact file paths; function names are stable anchors where line numbers drift (e.g., `cucm.py decide` branch is anchored by function name, not line).
- [x] Every task has TDD ordering: failing test written first, run to confirm failure, implementation, run to confirm pass, commit.
- [x] Every test in the spec's Tests section maps to a task or subtask in one of the three phase files. Cross-check the spec-test inventory at the top of Phase A.
- [x] The grep audit from the spec is an explicit task in Phase C (Task 12). Note that `_check_auto_apply` is actually deleted in Phase A Task 6 before the Phase C audit — that's safe because the deletion is covered by its own tests at the moment it happens; the Phase C audit is a final-sweep check that no stray references survived. The `resolved_by="auto_apply"` marker is replaced inside Phase A's rules.py refactor (Task 4) for production writes and updated in Phase B Task 10 for the CLI; Phase C Task 12 sweeps for anything remaining.
- [x] The smoke test is an explicit task in Phase C (Task 15) that runs on a real test project, not just in pytest.
- [x] No task in this plan touches `feature_mapper.py` or `recommendation_rules.py` (Plan 1 territory).
- [x] No task in this plan touches `docs/runbooks/cucm-migration/` (Plan 3 territory).
- [x] The `--apply-auto` branch in Phase B still prints a "no pending" line when the store is empty (spec's empty-store edge case).
- [x] The cascade-path enrichment (spec: "Cascade-path enrichment" subsection) is covered in Phase A (Task 3) as the final step of `resolve_and_cascade`.
- [x] Commit messages are provided inline for each task (HEREDOC format, Co-Authored-By line per repo convention).
- [x] The plan cites the spec as source of truth and explicitly tells the executor to stop and ask rather than reconcile conflicts silently.

## Execution handoff

After the phase files are written and committed, the executor (a separate chat) starts from Phase A, works task-by-task, and moves to Phase B only after all Phase A tasks are committed and passing. Phase C only starts after Phase B tests pass.

Recommended execution mode: **subagent-driven-development**. Each task fits a single subagent dispatch; the task boundaries are natural review checkpoints.
