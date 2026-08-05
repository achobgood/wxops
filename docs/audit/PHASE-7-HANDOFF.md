# Handoff prompt — PHASE 7

Paste everything below the line into a new Claude Code chat.

---

Continue an architectural audit of the wxops repository at
/Users/ahobgood/Documents/webexCalling. Run PHASE 7 only, then stop.

## Read these first, in this order

1. `docs/arch/wxops-architecture-audit-prompt_2.md` — the audit spec.
   Read STATUS (top), ROLE, KNOWN CONTEXT, HARD CONSTRAINTS, HOW TO RUN,
   and PHASE 7. Skip the other phases.
2. `docs/audit/00-facts.md` — reconnaissance; the NUMERIC AUTHORITY.
   Do not re-derive any count it establishes. `[CORRECTED]` entries are
   fixes to earlier errors; the corrected value is the right one. **Two of
   its claims were overturned in Phase 6 — see *What Phase 6 already settled*
   below.**
3. `docs/audit/00-context.md` — Phase 0. Its **Q4 stage map** is the input
   Phase 7 needs most: it gives LOC and remote-write status per migration stage.
4. `docs/audit/06-machinery.md` — **Phase 6, just completed. Read it in full.**
   It is the largest input to this phase and it already answers several of
   Phase 7's questions. Do not re-derive anything in it.

Consult as needed, do not read cover to cover: `docs/audit/02-drift.md` §6
(the gate's five findings), the four `docs/audit/02-detail-*.md` working papers,
`docs/audit/00-facts-independent-part2.md`.

## Your task: PHASE 7

Follow PHASE 7 of the audit spec. Write `docs/audit/07-testability.md`.
Report Target A and Target B in **separate sections** (HARD CONSTRAINT 6).

The spec's HOW TO RUN item 5 sets the central task: **214 of 244 test files sit
under `tests/migration/`, and nobody has established what they test. Decompose
that number by pipeline stage before quoting it.** A suite concentrated on
`transform/` (18,517 LOC, no network) while `execute/` (8,119 LOC, the only stage
that writes remotely) is thin would make the headline reassuring and wrong.
`00-context.md` Q4 has the stage map.

## What Phase 6 already settled — do NOT re-derive

- **Recorded remote responses: there are none, for any system.** Not Webex, not
  AXL. `tests/fixtures/axl-responses/` holds 18 XML files that are gitignored
  (`.gitignore:53`) *and* referenced by nothing; `git ls-files tests/` returns
  zero non-`.py` files. This overturns `00-facts.md` Q15 and the spec's own
  PHASE 7 bullet. The remaining question is what it *means*, not whether it is so.
- **`tests/test_auth.py` is untracked AND 18-of-24 failing.** It patches
  `wxcli.auth.httpx.request` at ten sites, but `auth.py` imports `httpx` lazily
  inside its two request methods (`auth.py:206`, `:226`), deliberately
  (`auth.py:14-21`). Being gitignored is why nobody noticed. **This is Phase 7's
  hottest lead, not a closed item** — see §5.
- **240 test files are tracked, 244 on disk.** `.gitignore:53` is `tests/*` with
  re-includes for `tests/migration/**`, `tests/org_health/**` and 23 named files
  (`:54-100`). Untracked and therefore absent from CI: `tests/test_auth.py`,
  `test_common.py`, `test_config.py`, `test_cli_smoke.py`, `tests/conftest.py`,
  `tests/live_test_v2.py`, `tests/fixtures/`.
- **`src/wxcli/migration/` contains zero `typer.Exit` / `sys.exit` /
  `SystemExit`** across 46,684 lines (the one grep hit is a comment). The shared
  runtime does the opposite: `errors.py:203`, `:225`; `common.py:32`, `:252`,
  `:263`; `config.py:118` all exit from library code. On this axis **B's layering
  is correct and A's is not.**
- **Eight `Console` instances exist**, three of them inside `migration/`
  (`cucm/discovery.py:41`, `cucm/extractors/users.py:25`,
  `cucm/extractors/devices.py:23`), each file instantiating its own.
- **The drift gate's entire coverage of Target B is three documentation counts**
  (check 17, `drift_check.py:2556-2587`) — mapper, analyzer and preflight-check
  totals cross-checked against prose in CLAUDE.md files. No check reads
  `execute/`.
- Phase 6 executed `tests/migration/execute/test_engine.py` (9/9),
  `test_cascade_and_retry.py` (18/18) and `test_bulk_serialization.py` (passes),
  and established exactly what each pins and does not pin — reuse that, do not
  re-run it.

## Leads from Phase 6 — verified, and squarely Phase 7's to judge

1. **The inversion.** The un-gated hand-written stack is *better* pinned in CI
   than the shared runtime it diverges from. `tests/migration/**` is tracked
   wholesale and CI installs `aioresponses` for it (`ci.yml:35`), while
   `tests/test_auth.py` neither ships nor passes. Establish whether that
   inversion holds once you decompose the 214 by stage, or whether the migration
   mass is concentrated on the no-network stages.
2. **`test_auth.py`'s decay is a mechanism, not an incident.** A tracked test goes
   red when a refactor invalidates it; an untracked one rots silently. Ask how
   many of the other untracked files are also stale — `test_common.py`,
   `test_config.py`, `test_cli_smoke.py`, `tests/conftest.py`. Running them is
   cheap and is the direct measurement. **This is the single highest-value thing
   in the phase**: it converts "coverage of the shared runtime is unmeasured"
   into a number.
3. **Nothing pins either stack's retry policy.** No tracked test asserts
   `auth.py`'s `RETRY_STATUSES` (`git grep RETRY_STATUSES -- tests/` → nothing)
   and no test in `tests/migration/execute/` exercises a 5xx, a date-form
   `Retry-After`, the exhausted-retry branch, or the `aiohttp.ClientError`
   branch. The spec asks directly whether any test would fail if the two stacks
   drifted further apart. Phase 6's answer is no; your job is the fuller version —
   what else has that property.
4. **The `pytest.mark.live` question is still open.** `grep -l "pytest.mark.live"`
   returns zero files, CI runs `pytest -m "not live"` (`ci.yml:63`), and
   `tests/live_test_v2.py` exists outside the marker system *and is untracked*.
   Dead filter, or live tests the marker no longer selects? Settle it.
5. **The import hook is evidence about layering, not just an obstacle.** The spec
   says to read it that way. `.claude/hooks/wxcli-gate.sh` blocks importing
   `wxcli` from Python because command functions make real HTTP calls to a live
   org and a Typer default is a truthy `OptionInfo`. Phase 0 records the incident
   that caused it (`wxcli-gate.sh:41-44`, 2026-07-28: four unconfirmed DELETEs
   reached the live org, one of them `DELETE /v1/organizations/{id}`).
6. **`.coverage` at repo root is dated 2026-03-23** — over four months stale. The
   spec says not to trust it. If you generate a real number, generate it per
   target and say which files it covers.

## Repo-specific constraints — these will bite you otherwise

- **The interpreter is `/opt/homebrew/opt/python@3.14/bin/python3.14`.** Bare
  `python3` on this machine is the system 3.9 and cannot import `wxcli` — you
  will get a misleading `ModuleNotFoundError`. `head -1 "$(which wxcli)"` prints
  the right one.
- **`wxcli` CANNOT be imported from Python.** A hook blocks it (see lead 5).
  Parse with `ast`, or run `wxcli <cmd> --help` as a subprocess (safe). Set
  `COLUMNS=400` when parsing help output.
- **Never run a mutating `wxcli` command.** This repo points at a live org.
- **Do not run the full pytest suite** (project rule, ~2 min). Targeted files are
  fine and are how this phase gets its evidence — run them one file at a time.
- **Count git-tracked files, never the working disk** (`git ls-files`,
  `git check-ignore -v`). This has produced wrong counts in three prior phases.
  Gitignored: all of `docs/arch/` and `docs/plans/`, `specs/webex-flow-store.json`,
  11 `src/wxcli/commands/fs_*.py`, and most of `tests/` (see above).
- **`docs/audit/` is untracked** — 0 tracked files. The audit's own output is not
  in the repo. Do not assume a prior artifact is committed.
- Subagents work well here and this phase parallelises cleanly (one per pipeline
  stage, or one per untracked test file). Use Sonnet or better — never Haiku.
  Give each agent the constraints above verbatim; they do not inherit them.
- **The working tree is NOT at commit b578a52.** An earlier session changed
  `tools/command_renderer.py`, `tools/field_overrides.yaml`,
  `tools/generate_commands.py`, `tests/test_field_overrides.py` and regenerated
  23 command modules. Phase 6 additionally corrected one sentence in
  `docs/architecture/04-operations-and-evolution.md:357`. All uncommitted.

## Established — do not re-litigate

- Target A is CLEAN: all 172 generated modules regenerate byte-identical, and the
  generator is deterministic. The "hand-patches reverted by regeneration"
  hypothesis is FALSE.
- Nothing detects a hand-edit to generated code. `check_parity` is the check a
  reader wrongly assumes covers it.
- The 50 `hidden=True` command names are backward-compat ALIASES on functions
  that also carry a visible name. Zero capabilities are hidden-only.
- "Is DELETE the right proxy for destructive?" is ANSWERED: no. 199 destructive
  operations, 176 DELETE and 23 not; those 23 plus one scope case are now gated,
  so "779 ungated writes" is now 755.
- The drift gate's allowlist is NOT where it went to die: 214 of ~215 suppression
  entries are deliberate with reasons that still hold.
- Gate finding F1: `_command_name` (`drift_check.py:502`) resolves to the HIDDEN
  alias, so checks 6/9/10/11a/11b silently skip 50 renamed commands.
- Gate finding F3: no check asserts that a destructive command has a guard — so
  any guard you propose must ship with the check that pins it.

## Rules

Every finding cites `path:line`. Label claims `[verified]` (you ran or parsed
something) or `[inferred]`. `UNKNOWN` is a correct answer. Never report a section
clean unless you read it; state read coverage per target. Do not estimate LOC,
effort, or percentages unless you counted — say "did not measure." **Do not quote
an aggregate coverage number**; the spec is explicit that the aggregate is
actively misleading here because 214 of 244 test files are one subsystem.
Disagree where warranted, including with the audit spec and with prior phases —
four of their claims have now been overturned, two of them by Phase 6.

Remediation rule: a finding may be fixed immediately ONLY if its root cause is
proven, its fix is in `migration/` or the generator, and no later phase would
teach you more. Record it in the spec's STATUS block and update every count it
moves. Everything else waits for the report.

Stop after writing `docs/audit/07-testability.md`. Do not begin Phase 5 or 8.
