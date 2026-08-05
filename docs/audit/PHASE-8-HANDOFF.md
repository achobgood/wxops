# Handoff prompt — PHASE 8

Paste everything below the line into a new Claude Code chat.

**This is the shortest phase in the audit and it should stay short.** Its output is
an input to the final report, not a standalone investigation. If you find yourself
writing more than ~250 lines, you have drifted into re-auditing code that four
earlier phases already covered. If you would rather not run it as its own session,
it can be folded into the final report — but then it *must* actually be done there,
not skipped.

---

Continue an architectural audit of the wxops repository at
/Users/ahobgood/Documents/webexCalling. Run PHASE 8 only, then stop.

## Read these first, in this order

1. `docs/arch/wxops-architecture-audit-prompt_2.md` — the audit spec. Read STATUS
   (top), KNOWN CONTEXT (especially the *"Git churn is not a valid proxy"* bullet),
   HARD CONSTRAINTS, and PHASE 8. Skip the other phases.
2. `docs/audit/00-facts.md` **Q16** — the history anchors. Do not re-derive them.
3. `docs/audit/06-machinery.md` **§3 and §10** — so you know which functions the
   audit already judged, and can weight churn against them.
4. `docs/audit/07-testability.md` **§3.4** — it identifies two commits that each
   broke untracked tests, which is a history pattern this phase should confirm or
   refute.

## Your task

Write `docs/audit/08-history.md`. Report the two targets **separately**
(HARD CONSTRAINT 6).

**The premise:** a function modified four or more times is an **unresolved
ambiguity**, not recurring bad luck. Find those functions, and say what the
ambiguity is.

## The one methodological trap, and it is fatal if you miss it

**Git churn is not a valid proxy for maintenance pain on Target A.** Generated files
change in bulk on every regeneration, and a single `chore(specs)` commit moves
thousands of lines behind a one-line subject. Commit messages in this repo are
hand-curated and unusually specific — e.g.
`820fe8b test(gate): the read-verb invariant was inspecting 86 of 1961 commands` —
so **message quality is not evidence that a diff was small or hand-made.**

**Filter by path, not by subject.** Analyse only:

- `tools/` — the generator, templates, and the drift gate
- `specs/` — but see the caution below
- `src/wxcli/*.py` — the shared runtime (9 files, ~1,766 tracked lines)
- `src/wxcli/migration/` — every line hand-written, so churn *is* meaningful
- `src/wxcli/commands/` **only** the 19 modules that are not generated (check
  `_registry.py` before assuming; `cucm.py`, `cleanup.py`, `configure.py`,
  `update.py`, `init_playbook.py`, `org_health.py`, `_lazy.py` are among them)

**Never** `src/wxcli/commands/<generated>.py`. Churn there measures spec refreshes.

Caution on `specs/`: those files are refreshed wholesale from upstream. Churn there
measures Cisco's release cadence, not this repo's pain. Count the refreshes, do not
attribute them.

## Anchors from `00-facts.md` Q16 — do not re-derive

- **1,038 commits total** across roughly five active months.
- Authors: Adam Hobgood 1,022, "Claude" 15, achobgood 1.
- By month: 2026-03 **290**, 2026-04 **487**, 2026-05 **30**, 2026-06 **10**,
  2026-07 **206**, 2026-08 **15**.
- **`tools/` has 134 commits of its own** — that subtree *is* a valid churn target,
  and it is the highest-leverage one under the severity model.
- Bulk machine-generated batches exist and the mechanism is **spec regeneration, not
  LLM authorship**. Direct evidence: `2a89ea4`, `a898c76`, `b578a52`.

## Three targets Phase 5 named specifically — start with these

`docs/audit/05-safety.md` finished after this handoff was drafted and left three
places where churn history is unexamined and would settle something. Do these first;
they are the highest-value use of this session.

1. **`src/wxcli/migration/execute/batch.py:174-175`** — Phase 5 flagged this
   specifically. Establish how many times it has been touched and by what kind of
   commit. A tight cluster of fixes on two lines is the definition of the
   "unresolved ambiguity" this phase is looking for.
2. **`src/wxcli/commands/cucm.py`'s `execute` region** (`:3149-3242`) — the driving
   command for the highest-consequence path in the repo. Use `git log -L` on the
   function, not on the file: `cucm.py` is 3,500+ lines and 27 leaf commands, so
   file-level churn there measures the whole `cucm` group and tells you nothing.
3. **`src/wxcli/migration/execute/engine.py`** — Phase 6 catalogued six behavioural
   disagreements inside it, Phase 7 proved none is pinned by a test, and Phase 5 just
   modified it. **If its retry block shows repeated churn, that is the single most
   interesting result this phase can produce.**

## For Target B, weight by proximity to the execute path

The spec is explicit: **four fixes to a report renderer is noise; four fixes to
`execute/engine.py` or `runtime.py` is the audit telling you where the ambiguity
lives.** Rank by consequence, not by count.

Two corrections to carry in, both from Phase 6:

- **`migration/rate_limiter.py` is dead code** — imported by nothing in `src/`.
  Churn there is meaningless regardless of volume, and the file should be read as
  abandoned, not as maintained.
- The retry policy actually in force is inline in `execute/engine.py`. If
  `engine.py`'s retry block shows repeated churn, that is the single most
  interesting result this phase can produce, because Phase 6 catalogued six
  behavioural disagreements in it and Phase 7 proved none is pinned by a test.

Functions Phases 6 and 7 already judged, so churn on them is *corroboration* and
should be reported as such rather than re-derived: `execute_single_op`,
`execute_bulk_op`, `poll_job_until_complete`, `_try_find_existing`,
`run_batch_ops`, `execute_all_batches`, `update_op_status`, `reset_in_progress`,
`_build_bulk_job_probe`, `check_bulk_device_job_support`, and `auth.py`'s
`_request` / `_backoff_delay` / `follow_pagination`.

## One pattern Phase 7 found that this phase can confirm or refute

`07-testability.md` §3.4 established that **two commits each broke a test nobody
could see**:

| Commit | Date | Broke |
|---|---|---|
| `648439f` *"give hand-written commands the same --fields surface"* | 2026-07-25 | `tests/test_partner_e2e.py` (5 tests, still red) |
| `751010c` *"real argument help, runnable examples, 28 renames, 8x faster start"* | 2026-07-28 | `tests/test_auth.py` (18 tests) **and** `tests/tools/test_command_renderer.py` (3 tests) |

Both are untracked files, so neither refactor got a signal.

**The question for this phase: is that a pattern or two incidents?** Specifically —
do refactor commits in this repo systematically land without touching the tests that
cover them, and is the correlation with *untracked* test files or with refactors in
general? A cheap way in: for each commit that touched `src/wxcli/*.py` or `tools/`,
check whether the same commit touched any `tests/` file, and split the result by
whether those test files are tracked. That is a real, countable answer and it feeds
the final report's third item directly.

## Repo-specific constraints

- **The interpreter is `/opt/homebrew/opt/python@3.14/bin/python3.14`.** Bare
  `python3` is the system 3.9.
- **`wxcli` CANNOT be imported from Python.** A hook blocks it, matching the string
  `import wxcli` anywhere in a Bash command. This phase should not need to.
- **Never run a mutating `wxcli` command.** This repo points at a live org.
- **Count git-tracked files, never the working disk** (`git ls-files`,
  `git check-ignore --no-index -v`). Four phases have got this wrong.
- **`docs/audit/` and `docs/arch/` are untracked/gitignored.** Do not assume a prior
  artifact is committed.
- **The working tree is NOT at `b578a52`** — 28 tracked files are modified and
  uncommitted (generator work plus one doc fix). Those changes have **no commit**, so
  they are invisible to every `git log` you run. Say so where it matters: the most
  recently changed generator code is not in the history this phase analyses.
- `git log --follow -L` and `git log -S` are the right tools here. `git log --format`
  with `--` path filters is how you avoid the generated-file trap.

## Established — do not re-litigate

- Target A is CLEAN on drift: 172 generated modules regenerate byte-identical, the
  generator is deterministic, and there are **zero hand-edits** to generated code.
- Nothing detects a hand-edit to generated code; `check_parity` does not cover it.
- The 50 `hidden=True` names are backward-compat aliases; zero capabilities are
  hidden-only.
- "Is DELETE the right proxy for destructive?" is ANSWERED: no. 199 destructive
  operations; the 23 non-DELETE ones are now gated, so 779 ungated writes is now 755.
- There are **no recorded remote responses for any system**, and 22 test files are
  gitignored — including all four of the generator's.
- Nothing in CI pins either stack's retry policy or the migration engine's error
  branch; proven by mutation in Phase 7 §2.5.

## Rules

Every finding cites `path:line` (or `commit:path`). Label claims `[verified]` or
`[inferred]`. `UNKNOWN` is a correct answer. **Do not estimate counts — count them.**
Report the two targets separately. A ranked list of churn with no interpretation is
not a deliverable: for each function you name, say **what the ambiguity is** and
whether a prior phase already identified it. Disagree where warranted — six claims
from earlier phases have now been overturned.

Remediation rule: this phase is unlikely to produce a fix that qualifies, because
churn identifies *where* ambiguity lives, not what the resolution is. If you think
one qualifies, it still must be in `migration/` or the generator, with a proven root
cause and a tracked test that pins it.

Stop after writing `docs/audit/08-history.md`. Do not begin the final report.
