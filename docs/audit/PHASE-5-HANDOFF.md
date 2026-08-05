# Handoff prompt — PHASE 5 — ⚠ SUPERSEDED, DO NOT RUN

> **Phase 5 was completed on 2026-08-05 by a concurrent session.** Its artifact is
> `docs/audit/05-safety.md` (90 KB). It also **shipped two fixes** under the
> remediation rule — D13 (`in_progress` now written before dispatch,
> `runtime.py:mark_ops_in_progress` + `engine.py:924-934`) and the preflight
> bulk-job probe (`checks.py` now returns `INCOMPLETE`, `cucm.py:1797` widened to
> `(FAIL, INCOMPLETE)`) — which are the two candidates this handoff deferred *to*
> Phase 5. See `05-safety.md` §3.1 and §3.2.
>
> **Kept for the record only.** Do not paste it into a new chat. The live handoffs
> are `PHASE-4-HANDOFF.md`, `PHASE-8-HANDOFF.md`, `PHASE-1-HANDOFF.md` and
> `FINAL-REPORT-HANDOFF.md`.
>
> **One open item this created:** the two new tests that pin those fixes —
> `tests/migration/execute/test_in_progress_written.py` and
> `tests/migration/preflight/test_bulk_job_probe.py` — are **not ignored** (the
> `!tests/migration/**` re-include at `.gitignore:55` covers them) but are still
> **untracked**, i.e. never `git add`ed `[verified 2026-08-05]`. They are one
> `git add` from CI. Stage them, or the fixes ship pinned by tests CI cannot see.

---

Paste everything below the line into a new Claude Code chat.

---

Continue an architectural audit of the wxops repository at
/Users/ahobgood/Documents/webexCalling. Run PHASE 5 only, then stop.

## Read these first, in this order

1. `docs/arch/wxops-architecture-audit-prompt_2.md` — the audit spec.
   Read STATUS (top), ROLE, KNOWN CONTEXT, HARD CONSTRAINTS, HOW TO RUN,
   and PHASE 5. Skip the other phases.
2. `docs/audit/00-facts.md` — reconnaissance; the NUMERIC AUTHORITY.
   Do not re-derive any count it establishes. `[CORRECTED]` entries are fixes to
   earlier errors; the corrected value is the right one. **Four of its claims
   have been overturned — see *Already settled* below.**
3. `docs/audit/00-context.md` — Phase 0. **Its Q1 is the input Phase 5 needs
   most**: six classes of org-wide-mutation command, with the blast radius of
   each, plus "The bound that does not ship" and "The guard the repository
   already knows how to emit." Q4 is the Target B stage map.
4. `docs/audit/06-machinery.md` — **read in full.** It answers a large share of
   PHASE 5's Target B bullets outright. Do not re-derive anything in it.
5. `docs/audit/07-testability.md` — **read §2.5, §3.1, §3.2 and §6 at minimum.**
   §2.5 changes what a valid Phase 5 remediation looks like (see *The constraint
   Phase 7 puts on every fix you propose*, below).

Consult as needed, do not read cover to cover: `docs/audit/02-drift.md` §6
(the gate's five findings, especially F3), `docs/audit/02-detail-checks-10-20.md`,
`docs/audit/00-facts-independent-part2.md`.

## Your task: PHASE 5

Follow PHASE 5 of the audit spec. Write `docs/audit/05-safety.md`.
Report Target A and Target B in **separate sections** (HARD CONSTRAINT 6). The
spec is explicit that Target B gets *its own section, not a bullet*.

**Do Target B first.** The audit's own ordering (HOW TO RUN item 4) says so, and
it is right: `wxcli cucm execute` is the single highest-consequence command in the
repository and the only one with no gate of any kind. Target A's top question was
answered in Phase 0 and partially fixed; what remains of it is item 1 below.

## Already settled — do NOT re-derive

**From Phase 6 (`06-machinery.md`) — these are PHASE 5 bullets it already
answered.** Cite them; do not re-open them.

- **Preflight does not gate execution.** `execute()` performs **no state,
  preflight, or stage check at all** — no `state`, `preflight`, `_require_stage`
  or `stage` reference anywhere in `cucm.py:3149-3242` (§5). The spec's bullet
  *"can execution run without preflight having passed"* is answered: **yes,
  trivially.**
- **Preflight's own gate is holed twice.** Check 10 of 10 (bulk device job
  support) can never return PASS or FAIL — it calls `api.session.ep()`/`.get()`,
  which `WebexSession` does not define, and `except Exception` at
  `checks.py:875` downgrades the `AttributeError` to `WARN`, which the gate
  treats as passing (§5). Separately, `cucm.py:1797` exits non-zero on `FAIL`
  only, so `INCOMPLETE` — the status this repo invented for "we could not
  check" — **exits 0** (§5.1). The two interlock: fixing `checks.py:875` to
  return `INCOMPLETE` without also widening `cucm.py:1797` moves the failure
  from one silent path to another.
- **A half-applied migration is not distinguishable from a not-yet-started one.**
  `in_progress` is declared, transitioned, reset and displayed — and **written by
  nothing** (D13). An op killed after its POST reached Webex stays `pending` and
  is re-issued on the next `execute`. `reset_in_progress` can only ever return 0.
- **Concurrency cannot race the dependency order.** Batches do not overlap;
  `get_next_batch` filters on live DB state (`runtime.py:55-69`). Proven by
  `test_cascade_and_retry.py` (18/18) and `test_bulk_serialization.py`, both run.
  **This spec bullet is answered and the answer is good — say so, don't re-test.**
- **`execute` exits 0 on any outcome**, deliberately and with a design note that
  Phase 6 agrees with; the defect is the undisclosed asymmetry against
  `preflight`, not the choice (§6.3).
- **No ETag / `If-Match` machinery exists in Target B either** (§4).
- **Token is not reachable in error output; PII is, and is persisted** to
  `plan_operations.error_message` and read back by `execution-status` (§6.5).
- The retry policies, the `WXCLI_*` gap, the `500: {}` error string, `orgId`'s
  inline re-read with `except: pass` (D9), `WORKSPACE_LICENSE_ID` never being set
  (D10), and the 62-loggers-no-handler result (D11) are all established in §2–§3.

**From Phase 7 (`07-testability.md`):**

- **Nothing in CI pins the execute path's failure behaviour.** Proven by
  mutation, not inferred: reclassifying every HTTP 4xx/5xx on the migration write
  path as *success* leaves the full suite at **3,580 passed** and the drift gate
  at **PASS**. Gutting both retry policies simultaneously does the same (§2.5).
- `engine.py` is 77% statement-covered — the worst file in `execute/` — and
  lines `206-210` (the error branch), `222-229` (`aiohttp.ClientError`),
  `231-234` (retry exhaustion), `625-694` (409 auto-recovery) and
  `195-196` never execute in any test (§2.4).
- `preflight/runner.py:325-336` — the broken probe's body — has never executed.
- **`dry_run_all_batches` (`runtime.py:375`) is a partial parallel branch**
  `[verified]`: it reuses `get_next_batch`, so batch *ordering* is genuinely the
  same logic, but `grep` for `engine|execute_all_batches|execute_single_op|aiohttp`
  over `runtime.py` returns **nothing**. It simulates by marking ops complete
  inside a SQLite `SAVEPOINT` and rolling back. **This is a partial answer to the
  spec's dry-run-drift bullet — finish it:** establish whether it constructs
  request bodies via `handlers.py` (and so can tell an operator *what will be
  sent*), or only counts operations. That determines whether `dry-run` certifies
  anything about the writes or only about their order.

## Leads that are squarely Phase 5's to judge

1. **The replacement for the DELETE-proxy question.** Of the **755** writes that
   remain ungated and are *not* classified destructive by
   `classify_real_semantics`, which actually destroy state? A PUT that replaces a
   whole collection removes its unlisted members.
   **`migration/execute/handlers.py:2271` documents exactly that hazard for
   membership arrays** — start there, then find the collection-replacing writes on
   the generated surface. This class is invisible to both signals
   `classify_real_semantics` uses, which is why Phase 0's fix did not reach it.
2. **Is the confirm reachable in the operator's actual mode?** `typer.confirm`
   on non-interactive stdin aborts. Establish what the operating LLM actually
   sees when it runs a gated delete with no TTY, and whether that failure is
   legible or looks like an unrelated error the agent "fixes" by adding
   `--force`. This is testable without touching the live org: `--help` is safe,
   and the untracked `tests/test_cli_smoke.py` / `test_partner_e2e.py` show the
   monkeypatch-`get_api` pattern for driving a command offline.
3. **Is `wxcli cucm execute`'s ungated design deliberate?** The spec says a
   defensible answer exists — the plan was approved through a separate decision
   workflow, so the gate lives upstream. **Find the record or report that there
   isn't one.** Then answer the sharper version: does `execute` *verify* that
   approval happened, or merely trust it? `migration/decision_state.py` and the
   `decisions` table (`store.py`) are where to look; note that Phase 6 found
   `plan_operations` has **no `run_id` column**, so two `execute` invocations are
   indistinguishable in the store.
4. **What stops an operator running `execute` without ever running `dry-run`?**
   The help text advises it. Advice is not a gate, and the operating LLM reads
   help text as specification.
5. **`--force` as the agent's default.** Its help string is "Skip confirmation"
   on all 179 gated commands, and says nothing about what is skipped or
   destroyed. The gate and its bypass were generated together, so 100% coverage
   of the gate is 100% coverage of the escape hatch. Judge whether an LLM with
   only `--help` would read `--force` as the normal unattended mode.
6. **The confirm text.** `Delete {room_id}?` names an opaque base64 ID — no
   object type, no display name, no count of dependents. Ask whether the
   generator *could* emit better: the spec carries `summary` and `tag` per
   operation, and `errors.py:90` already has `decode_id_kind`.
7. **The `journal` table is the audit trail that isn't.**
   `migration/store.py:120-130` declares
   `journal(timestamp, entry_type, canonical_id, resource_type, request,
   response, pre_state)` — exactly what a write-path audit log needs. It is
   written at **two** sites, both read-only discovery
   (`commands/cucm.py:1220`, `migration/cucm/discovery.py:251`), and `pre_state`
   is populated by **no caller anywhere**. Nothing in `execute/` writes it.
   This is the natural home for the record that would make D13 and D8
   diagnosable after the fact. → judge it here; Phase 1 also wants it.
8. **The bound that does not ship.** `.claude/hooks/wxcli-gate.sh` enforces a
   read-only verb policy, but `wxcli-dist/assemble.py:161` substitutes
   `settings.bundled.json`, whose only hook is a `SessionStart` update check plus
   a blanket `Bash(wxcli:*)` allow. **Every bound measured on this machine is
   absent downstream.** Phase 7 §3.2 adds the layering reading — the hook
   compensates for the generated layer having no unit below the CLI entry point
   (2,004 functions in `commands/`, 1,892 of them `@app.command`-decorated) — and
   confirmed the `OptionInfo`-is-truthy trap: `typer.Option(False, "--force")`
   evaluated outside Typer's runtime has `bool() == True`, so `if not force:
   typer.confirm(...)` **inverts**, it does not merely bypass.
9. **Scope containment.** `orgId` is auto-injected from config on the generated
   surface. Determine what an operator would have to do *wrong* for a command to
   hit the unintended org — and note that Phase 6's D9 already established
   Target B's version of this failure (a malformed `~/.wxcli/config.json` sends
   every migration write out unscoped, silently, via `except Exception: pass` at
   `commands/cucm.py:3187-3196`).

## The constraint Phase 7 puts on every fix you propose

`02-drift.md` F3 established that **no gate check asserts a destructive command
has a guard**, so the 24 confirms added on 2026-08-04 are unpinned — a render-path
change would drop them and ship green. **Phase 7 measured the same property one
level deeper and it is worse than F3 states:**

- Both stacks' retry policies and the engine's entire error branch can be
  removed with the suite and the gate both green (§2.5).
- **All four of the generator's test files are untracked** — 187 tests over the
  component whose defects multiply by the whole generated surface, none of which
  runs on a PR (§3.3).
- 22 test files are gitignored; three are silently red; a test that is not
  tracked cannot report its own decay (§0/C2, §3.4).

**So: any guard you propose must ship with the check that pins it, and that check
must live in a git-tracked file.** A guard pinned by an untracked test is a guard
pinned by nothing, and this repository has already produced three examples of
exactly that failure. `.gitignore:58-100` shows the maintainer's own promotion
policy — read those comments before proposing where a new test goes.

## Repo-specific constraints — these will bite you otherwise

- **The interpreter is `/opt/homebrew/opt/python@3.14/bin/python3.14`.** Bare
  `python3` is the system 3.9 and cannot import `wxcli` — you will get a
  misleading `ModuleNotFoundError`. `head -1 "$(which wxcli)"` prints the right one.
- **`wxcli` CANNOT be imported from Python.** A hook blocks it (lead 8), and it
  matches on the *string* `import wxcli` anywhere in a Bash command — it will fire
  on an unrelated verification one-liner. Parse with `ast`, or run
  `wxcli <cmd> --help` as a subprocess (safe). Set `COLUMNS=400`.
- **Never run a mutating `wxcli` command.** This repo points at a live org, and
  `~/.wxcli/config.json` holds a working token.
- **Do not run the full pytest suite in the working tree** (project rule).
  Targeted files are fine. If you need a full-suite or mutation result, do what
  Phase 7 did: `git clone --no-hardlinks . <scratch>` and work in the clone —
  baseline there is **3,580 passed / gate PASS** at `b578a52`.
- **Count git-tracked files, never the working disk** (`git ls-files`,
  `git check-ignore --no-index -v`). This has produced wrong counts in four prior
  phases, including a denominator error Phase 7 corrected.
- **`docs/audit/` and `docs/arch/` are untracked/gitignored.** The audit's own
  output is not in the repo. Do not assume a prior artifact is committed.
- Subagents work well here. Use Sonnet or better — never Haiku. Give each agent
  the constraints above verbatim; they do not inherit them.
- **The working tree is NOT at commit b578a52.** 28 tracked files are modified:
  `tools/{command_renderer,generate_commands}.py`, `tools/field_overrides.yaml`,
  `tests/test_field_overrides.py`, 23 regenerated command modules, and
  `docs/architecture/04-operations-and-evolution.md:357` (Phase 6's one doc fix).
  All uncommitted.

## Established — do not re-litigate

- Target A is CLEAN on drift: all 172 generated modules regenerate
  byte-identical, and the generator is deterministic. The "hand-patches reverted
  by regeneration" hypothesis is FALSE.
- Nothing detects a hand-edit to generated code. `check_parity` is the check a
  reader wrongly assumes covers it.
- The 50 `hidden=True` command names are backward-compat ALIASES on functions
  that also carry a visible name. **Zero capabilities are hidden-only** — the
  "hidden destructive command" cell is empty; do not go looking for it.
- "Is DELETE the right proxy for destructive?" is ANSWERED: no. 199 destructive
  operations, 176 DELETE and 23 not; those 23 plus one scope case are now gated,
  so "779 ungated writes" is now **755**. **Item 1 above is the question that
  replaces it — do not re-ask the original.**
- The drift gate's allowlist is NOT where findings went to die: 214 of ~215
  suppression entries are deliberate with reasons that still hold.
- Gate finding F1: `_command_name` (`drift_check.py:502`) resolves to the HIDDEN
  alias, so checks 6/9/10/11a/11b silently skip 50 renamed commands.
- The gate's **entire** coverage of Target B is three documentation counts
  (check 17, `drift_check.py:2556-2587`). No check reads `execute/`.
- There are **no recorded remote responses for any system** — not Webex, not
  AXL. `tests/fixtures/axl-responses/` is gitignored *and* referenced by nothing.
- `migration/rate_limiter.py` is dead code imported by nothing in `src/`; it is
  also 96% test-covered, which is the cleanest illustration in the repo of why
  the aggregate coverage number misleads.

## Rules

Every finding cites `path:line`. Label claims `[verified]` (you ran or parsed
something) or `[inferred]`. `UNKNOWN` is a correct answer. Never report a section
clean unless you read it; state read coverage per target. Do not estimate LOC,
effort, or percentages unless you counted — say "did not measure." Judge severity
by consequence and reachability for Target B, and by the generated multiplier for
Target A. **A finding that proposes something the gate already enforces is a false
finding and counts against you** — establish what the gate covers before asserting
a gap. Disagree where warranted, including with the audit spec and with prior
phases — six of their claims have now been overturned, four of them since Phase 6.

Remediation rule: a finding may be fixed immediately ONLY if its root cause is
proven, its fix is in `migration/` or the generator, and no later phase would
teach you more. Record it in the spec's STATUS block and update every count it
moves. **Two candidates already qualify on root cause and were deferred to you:**
`checks.py:875` returning `INCOMPLETE` instead of `WARN` (paired with widening
`cucm.py:1797`), and writing `in_progress` before dispatch (D13). Both are in
`migration/`. Both need the tracked test that pins them, per *The constraint*
above. Everything else waits for the report.

Stop after writing `docs/audit/05-safety.md`. Do not begin Phase 3, 4 or 8.
