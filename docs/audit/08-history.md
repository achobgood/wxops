# 08 — Targeted history

Phase 8 of the wxops architectural audit. Scope: the generator, templates, spec,
the shared runtime, and `src/wxcli/migration/`. Generated command modules are
excluded by construction — churn there measures spec refreshes, not maintenance.

**The one-sentence result.** The premise — *a function modified four or more
times is an unresolved ambiguity* — holds on Target A and is **inverted on
Target B's execute path**: every place the maintainer churned, they left a
tracked characterization test behind, and every place a prior phase found a live
behavioural defect has **exactly one commit**. On this repository, high churn
marks resolved questions and **zero churn marks the unexamined ones**.

---

## 0. Five corrections to this phase's own brief

Each was measured before any analysis was run.

| Claim, and where | Measured |
|---|---|
| "1,038 commits" (`00-facts.md` Q16); "`tools/` has 134" | **1,043** and **136** `[verified]`. The Q16 anchor was taken at `b578a52`; five commits have landed since (`3e7fa2b`, `de9ea55`, `de5bd78`, `9d1c38d`, `872ff5a`). Monthly totals are unaffected except 2026-08: **15 → 20**. |
| "The working tree is NOT at `b578a52` — 28 tracked files are modified and uncommitted… the most recently changed generator code is not in the history this phase analyses" (`PHASE-8-HANDOFF.md:148-150`) | **Stale, and it inverts the caveat.** `git status --porcelain` returns **zero** lines; HEAD is `872ff5a`. Phase 4's remediation was committed as `de9ea55` + `de5bd78`. The newest generator code **is** in the history analysed here. |
| "`docs/audit/` and `docs/arch/` are untracked/gitignored" (`:143`) | **Half wrong.** `docs/audit/` is **tracked** as of `9d1c38d` (19 files). `docs/arch/` is still untracked — 0 files `[verified, git ls-files]`. |
| "19 modules in `src/wxcli/commands/` are not generated" (audit spec HARD CONSTRAINT 5; handoff `:53-55`) | **11 tracked**, of which one — `_registry.py` — is itself generator output (`_registry.py:3`, *"Emitted by tools/generate_commands.py — do NOT edit by hand"*). So **10 hand-written**, plus 11 gitignored `fs_*.py`. The handoff names `org_health.py`; the file is `org_health_cli.py`. 19 is unsourced. |
| The path filter (`:47-57`) omits one exclusion | **`src/wxcli/_playbook/` is generated** and must be excluded too. `wxcli-dist/assemble.py:19,25` builds it; `src/wxcli/_playbook/CLAUDE.md` is **byte-identical** to `CLAUDE.md` `[verified, diff]`. Unfiltered, the three highest-churn files in the repo are `_playbook/AGENTS.md` (93), `CLAUDE.md` (93), `_playbook/CLAUDE.md` (92) — one document counted three times. |

---

## 1. Method, and what it cannot see

File churn is `git log --follow --format=%H -- <path>`, counted. Function churn is
`ast` for each function's current `(start,end)`, then `git log -L start,end:<path>`,
which walks that region backwards through diffs — **862 functions across 34 files**.
Every load-bearing single-function claim is confirmed by two or three independent
methods (`-L` on a range, `-L :funcname:`, `-S` on a literal from the block); none
disagreed.

**What the instrument structurally cannot see.** A function that was wrong when
written and never touched gives the same signal as one that was right when written
and never touched: one commit. Churn ranks *attention*, not *correctness*. That is
not an aside here — it is §3.1's result.

---

## 2. TARGET A — generator, templates, spec, shared runtime

### 2.1 The six per-verb renderers — 71 commits, and this is a real ambiguity

| Function (`tools/command_renderer.py`) | Commits |
|---|---:|
| `_render_list_command` `:1229` | **15** |
| `_render_create_command` `:1495` | **13** |
| `_render_update_command` `:1598` | **13** |
| `_render_delete_command` `:1870` | **12** |
| `_render_action_command` `:1998` | **10** |
| `_render_show_command` `:1393` | **8** |

71 function-commits across **25 distinct commits**. **12 of those 25 (48%) touch
three or more of the six; seven touch all six** `[verified]`:

```
6/6  751010c 2026-07-28  real argument help, runnable examples, 28 renames
6/6  42be213 2026-07-25  emit JSON on no-body update/delete, guard unbound URL placeholders
6/6  765a0bb 2026-07-25  guard reserved-name collisions
6/6  6051165 2026-07-25  add --fields and give every command type a uniform --output
6/6  0472832 2026-03-28  generate CLI from Postman Meetings and Contact Center collections
6/6  3a8f2ac 2026-03-23  renderer auto-injects orgId from config
6/6  7b36ab0 2026-03-23  track tools/ — expose CLI code generator pipeline
3/6  de9ea55 2026-08-05  gate the 24 destructive writes the verb-based confirm missed
```

**The ambiguity, stated:** *is a CLI property a property of the command, or of the
HTTP verb?* The renderer answers "verb" — six parallel emitters — so every
cross-cutting property must be written six times and can be got right in one to
five of them. This is not inferred; it is the recorded cause of two shipped
defects. `CLAUDE.md` records `--output` present on three of six for four months;
`6051165` (2026-07-25) is the commit that closed it, and its subject says so
verbatim. `de9ea55` is the same shape a third time: the confirm gate was emitted
only by `_render_delete_command`, so 23 destructive non-DELETE operations had none.

**Prior phases:** `02-drift.md` F3 found the confirm gap; Phase 4 fixed it and
added check 21; the audit spec `:485` records that "the render paths" are the
deliberately-unstarted step (c) of Phase 4's remediation. History **corroborates**
that sequencing and dates the cost: 12 six-way edits in 4.5 months.

### 2.2 `tools/field_overrides.yaml` — 53 commits, the highest-churn hand-written file

98 lines at birth (`2721859`, 2026-03-17) → **2,729 lines today**, across 53
commits, with **five shrink events**, four of them in the first week
`[verified, git show <rev>:path | wc -l at every revision]`.

**The ambiguity:** *what does the OpenAPI spec fail to say that the generator
needs?* Answered incrementally, 53 times, monotonically since 2026-03-23. No
phase has asked whether entries ever become obsolete — the file has no expiry
mechanism and the gate has no check that an override still matches a live spec
field. Flagged, not fixed; that is a Phase 4 question, not a Phase 8 one.

### 2.3 High churn that is **not** ambiguity — reported so it is not misread

- `tools/drift_check.py:main` **15** and `render_command_file` **14**. `main` is
  the gate's check-registration point; 15 commits is 21 checks added one at a
  time. Growth, not indecision.
- `tools/generate_commands.py:main` **12**, `generate_tag` **10** — same shape.
- `src/wxcli/commands/cucm.py` **46 file commits** is a *file* number for a
  3,620-line module carrying 27 leaf commands. It is not usable and §3.1 does not
  use it.

### 2.4 `specs/` — counted, not attributed

**25 commits**, of which **13** are literally `chore(specs): update OpenAPI specs
from upstream (<date>)`, running roughly weekly from 2026-04-27 to 2026-08-03
`[verified]`. **9 tracked specs + 1 overlay.** That cadence is Cisco's release
cadence. No conclusion is drawn from it, per the brief.

### 2.5 The shared runtime — 74 commits, and one of them matters enormously

| File | Commits |
|---|---:|
| `main.py` | 40 |
| `errors.py` | 14 |
| `auth.py` | 13 |
| `output.py` / `config.py` | 7 / 7 |
| `common.py` | 4 |
| `suggest.py` / `update_check.py` / `__init__.py` | 2 each |

Function level: `main.py:whoami` **7**, `errors.py:handle_rest_error` **7**,
`output.py:print_table` **6**, `auth.py:WebexSession._request` **5**,
`main.py:switch_org` **4**. `auth.py:_backoff_delay` **1**;
`auth.py:follow_pagination` **2** — the function `07-testability.md` §3.5 proved
has 173 call sites and zero coverage has been edited twice, both times before the
call sites existed.

**`bcb1330`, 2026-07-24 — the commit that created half of Phase 6's finding.**
`git show --stat`: **one file, `src/wxcli/auth.py`, 45 insertions, 14 deletions,
no test, no migration file** `[verified]`. It added `RETRY_STATUSES =
frozenset({429, 500, 502, 503, 504})` (`auth.py:160`), `_backoff_delay`'s jitter
(`:184`), and the `try/except ValueError` around the `Retry-After` parse
(`:250-253`). Immediately before it, `auth.py` retried **429 only**, capped
`Retry-After` at 30s, and had no jitter `[verified, git show bcb1330^]`.

So `06-machinery.md` D1/D2/D4 — *"Target B is the **previously** state"* — is
literally true and now dated. **The two stacks agreed until 2026-07-24.** Three of
the six disagreements are **twelve days old**, and were created by a one-file fix
that did not look at the second copy of the policy it was fixing. That is
corroboration of Phase 6's verdict and a sharpening of it: the defect is not that
someone wrote a bad retry loop in March, it is that the July repair had no
mechanism to reach the copy in `migration/`.

---

## 3. TARGET B — `src/wxcli/migration/`

Ranked by proximity to the execute path, as the spec requires.

### 3.1 The three targets Phase 5 named — all three answered, and all three the same way

**(1) `execute/batch.py:174-175`, the unconditional `DELETE FROM plan_operations`.**
Phase 5 asked whether a Critical finding sitting on two lines had been revisited.
**It had not.** `save_plan_to_store` has **3 commits**: `47a9155` (2026-03-26,
birth), `b6289d4` (2026-04-12), `3e7fa2b` (2026-08-05 — the audit's own fix).
`git log -S 'DELETE FROM plan_operations'` returns **exactly two commits**: the
birth commit and the audit's fix `[verified]`. The line was written once and
survived **132 days** untouched. `batch.py` has 5 commits, four of them inside a
17-day window (2026-03-26 → 2026-04-12), then 115 days of silence.

**(2) `commands/cucm.py`'s `execute`, `:3243-3339`.** **Two commits.** `6082b84`
(2026-03-24) and `3e7fa2b` (2026-08-05). Confirmed by both `-L 3242,3339:` and
`-L :execute:` `[verified]`. The single highest-consequence command in the
repository — no confirm, no `--force`, no `--dry-run`, `--concurrency` defaulting
to 20 — **was written once and never revisited in 4.5 months of active work.**

`6082b84` also demonstrates the brief's own warning running the *other* way.
Its subject is `feat(cucm): add report assembler + wxcli cucm report command`.
Its diff adds `@app.command` for **`rollback-ops`, `dry-run`, `execute`, and
`retry-failed`** `[verified]`. The entire execute path shipped behind a subject
line about a report. Hand-curated messages are not evidence of diff *scope*
either — not just of diff size.

**(3) `execute/engine.py`'s retry block — the result the brief said would be the
most interesting one, and it is the opposite of what was expected.**

`engine.py` has **21 commits**. Its retry block has **one**.

```
git log -L 202,214:…/engine.py   →  1c0e520  2026-03-24
git log -L 195,215:…/engine.py   →  1c0e520  2026-03-24
git log -S 'resp_status == 429'  →  1c0e520  2026-03-24
git log -S 'Retry-After' -- migration/ → 1c0e520 + one docs commit
```

Four methods, one answer `[verified]`. `engine.py` has **no commit after
2026-04-16** until the audit's own `3e7fa2b`; the seven July commits under
`execute/` are all planner- and report-facing. The block carrying Phase 6's D1,
D2, D3, D4 and D6 — six catalogued behavioural disagreements, none pinned by a
test per Phase 7 §2.5 — has been read by no one since the day it was typed.

**The premise fails here, and the failure is the finding.** A four-times-modified
function is an unresolved ambiguity. A once-written function on the write path is
not a resolved one — it is an *unexamined* one, and this instrument cannot tell
the two apart. Ranking Target B by churn would have put this block near the bottom.

### 3.2 The functions prior phases judged — churn as corroboration only

| Function | Commits | Date span |
|---|---:|---|
| `_try_find_existing` `engine.py:616` | 5 | 2026-03-24 → **03-30** |
| `run_batch_ops` `engine.py:774` | 5 | 04-11 → **04-16** |
| `execute_all_batches` `engine.py:859` | 5 | 03-24 → 04-16, then 08-05 |
| `execute_single_op` `engine.py:164` | 4 | 03-24 → **04-16** |
| `execute_bulk_op` `engine.py:288` | 4 | 04-11 → **04-16** |
| `update_op_status` `runtime.py:142` | 3 | 03-26 → 04-16 |
| `check_bulk_device_job_support` `checks.py:818` | 3 | 04-16, 04-16, 08-05 |
| `_build_bulk_job_probe` `runner.py:295` | 3 | 04-16, 04-16, 08-05 |
| `poll_job_until_complete` `engine.py:49` | **1** | 04-11 |
| `reset_in_progress` `engine.py:152` | **1** | 03-24 |
| `MigrationStore.clear_all` `store.py:442` | **1** | 03-30 |

Two things fall out. **Every execute-path function's churn ends on 2026-04-16** —
`execute/` has 27 commits in March, 82 in April, then 7 in July (all planner) and
1 in August (the audit). **And `reset_in_progress` — the crash-recovery entry
point Phase 6 D13 proved inert because `in_progress` is never written — has one
commit.** So does `clear_all`, and so does `poll_job_until_complete`. The inert
machinery is inert because nobody returned to it, not because a decision was
reversed.

`migration/rate_limiter.py`: **1 commit** `[verified]`. Phase 6 C1 called it dead
code imported by nothing; a single creating commit and zero maintenance is exactly
the history of an abandoned file. Corroborated, not re-derived.

### 3.3 The one genuine unresolved ambiguity in Target B — and it is already closed

Ranked by count, Target B's leaders are report renderers — `generate_appendix`
**14**, `_page_environment` **11**, `_page_verdict` **9**, and 14 more `appendix.py`
sections at 4–8. The spec calls that noise and it is: every commit adds a new
lettered appendix section. Correctly discarded.

What survives the proximity filter is the **planner's skip-and-warning report**:

| Function | Commits |
|---|---:|
| `planner.py:_expand_device` `:1003` | 11 |
| `planner.py:expand_to_operations` `:2067` | 9 |
| `planner.py:_optimize_for_bulk` `:584` | 8 |
| `planner.py:_log_skip_summary` `:2414` | 7 |

Four commits in **seven days**, each correcting the previous one's count
`[verified]`:

```
36871f3  2026-07-24  cross-site Phase 2 — reassign location, shared-line survival
e4f08b2  2026-07-29  the skip report claimed 766 skips that were planned, and missed 23 that weren't
5d16510  2026-07-30  769 warnings about entities that were provisioned fine, and a skip headline
                     that over-reported the actionable set by 3.8x
3bbeeab  2026-07-30  224 line key templates warned about work that was never owed
```

**The ambiguity:** *what counts as a skip, and does a skip warrant a warning?*
Re-answered four times because the planner had no single definition of "an
operation that was not planned" — some skips were planned work, some warnings
described work that was never owed. Related and concurrent: the `__stale__`
sentinel, a string used as an absence marker, produced `12438ea` (2026-07-29,
*"'__stale__' is truthy, so 405 undecided devices read as auto-resolved"*), then
two refactors on 2026-07-30 to spell it in one module.

**No prior phase identified this.** It is Phase 8's own finding.

**And it is closed.** Each fix shipped its pinning test *in the same commit*
`[verified]`: `e4f08b2` → `tests/migration/execute/test_planner_skip_report_truth.py`;
`5d16510` → `test_planner_skip_honesty.py`; `106f4d1` →
`tests/migration/test_stale_sentinel_is_centralised.py`; `96981b4` →
`tests/migration/report/test_pending_decision_rendering.py`. All four are
**tracked**. This is what a resolved ambiguity looks like in this repository, and
it is the direct contrast to §3.1(3).

### 3.4 A positive result worth recording

`execute/dependency.py` has 5 commits, and **every one of its five functions has
exactly one** `[verified]` — `build_dependency_graph`, `_add_cross_object_edges`,
`validate_tiers`, `detect_and_break_cycles`, `create_fixup_operations`. All the
churn landed in the declarative `_CROSS_OBJECT_RULES` table at `dependency.py:36`.
The DAG that determines execution order and cascade-skip topology was factored so
that new knowledge is a data row, not a code edit. That is the shape §2.1's
renderer does not have.

---

## 4. The cross-cutting finding: the highest-churn decision in the repo is "what is visible"

Ranked over **683 tracked non-generated, non-spec files**, and after excluding the
generated `_playbook/` copies:

| File | Commits |
|---|---:|
| `tools/field_overrides.yaml` | 53 |
| `tools/command_renderer.py` | 49 |
| **`.gitignore`** | **49** |

`.gitignore` went from **25 lines to 183** `[verified]`. **Sixteen** commits edit a
`!tests/…` re-include line; **seven** separate commits delete tests from the index
— including `6c4775a` (2026-04-10) *"untrack test file re-added by mistake"*.
That is **23 commits spent on the question of which tests CI can see.**

It has a single origin, in a 25-minute window on 2026-03-23 `[verified, --date=iso]`:

```
17:20  3fcb316  remove pipeline-visual.html from tracking
17:22  6663656  remove docs/prompts, superpowers, later
17:23  aac6359  remove docs/plans/cucm-pipeline
17:27  93bb23f  remove tests/ from tracking and gitignore it     ← 22 test files
17:30  522bc69  gitignore dev-only files — migration, tools, CI  ← + tools/, migration/, .github/
17:45  7b36ab0  track tools/ — expose CLI code generator pipeline ← reverts tools/ after 14 minutes
```

`93bb23f`'s body reads in full: *"Tests are dev-only, not needed for playbook
distribution."* `522bc69`'s `.gitignore` hunk adds `.github/` under the comment
*"CI (no value without tests)"*. `tools/` was restored in 14 minutes;
`migration/` the next day; **`tests/` has been coming back one `!` line at a time
for 4.5 months and is still incomplete** — 18 test files and `conftest.py` remain
invisible today.

**The ambiguity, stated:** *is this repository a distribution artifact or a
development repository?* It was answered "distribution" in one 25-minute sitting
and has been un-answered incrementally ever since. Every artifact Phase 7 §3.4,
§4 and §5 reports — the 26 rotting tests, the `.github/` blindspot, the
same-basename `test_command_renderer.py` pair — is downstream of those six commits.

---

## 5. Phase 7 §3.4 — pattern or two incidents? **Pattern. Measured.**

Neither `648439f` nor `751010c` touched **any** `tests/` file `[verified,
--name-only]`.

They are not exceptional. Of the **90 distinct commits since 2026-03-24 that
touched a module whose only unit test is untracked**, **76 (84%) touched no
`tests/` file at all** `[verified]`. `648439f` and `751010c` are two of those 76.

**Is the correlation with untracked-ness or with refactors in general?** With
untracked-ness. Same author, same era, same subtree:

| Source | Its covering test | Commits also touching `tests/` |
|---|---|---:|
| `tools/drift_check.py` | 11 files, **tracked** | 11/21 — **52%** |
| `tools/openapi_parser.py` | 2 files, **untracked** | 4/17 — **24%** |
| `tools/command_renderer.py` | tracked only since 2026-08-05 | 9/36 — **25%** |
| `src/wxcli/output.py` | **untracked** | 0/6 — **0%** |
| `src/wxcli/commands/cleanup.py` | **untracked** | 1/20 — **5%** |
| `src/wxcli/migration/` | 214 files, **tracked** | 169/326 — **52%** |
| `src/wxcli/migration/execute/` | **tracked** | 67/117 — **57%** |

By era, the same signal: `migration/` runs 49% during the dark period and **81%**
after 2026-07-06, when its tests were re-included. `tools/` runs 20 → 25 → 29%.

**One honest counter-example.** `errors.py` sits at 20% despite having tracked
tests — because those tests (`test_errors_actionability.py`, `test_errors_id_kind.py`)
were created on 2026-07-29 and 2026-08-01, after 8 of its 10 commits `[verified]`.
Once you condition on a tracked test *existing at the time*, the counter-example
resolves. It is reported because it is the only one, and because the resolution is
a datum, not a rescue: **tracked coverage in this repo is younger than the code it
covers, everywhere except `migration/`.**

The mechanism is not carelessness. It is arithmetic: an untracked test cannot
appear in a commit, so it cannot signal, so it cannot be updated by the person
breaking it. The 76 commits are the exposure; the 26 failures Phase 7 found are
the realized damage, and they are only known because Phase 7 ran files CI never
runs.

---

## 6. Remediation

**Nothing from this phase qualifies**, and the brief predicted that correctly.
Churn identifies where ambiguity lived, not what the resolution is. The two
candidates a reader might reach for both fail the bar:

- *"Give `engine.py` `auth.py`'s retry policy."* The root cause is proven
  (`bcb1330`, §2.5) but the resolution is a design decision — adopt, share, or
  gate — that belongs to `06-machinery.md` §8 and the final report, and it needs
  recorded Webex responses that `07-testability.md` §5 proved do not exist.
- *"Track the remaining 18 test files."* Real, cheap, and **not this phase's to
  make** — three of them are red right now, so tracking them turns CI red, and
  the sequencing of repair-then-track is Phase 4's shipped pattern, not a Phase 8
  finding.

---

## 7. Read coverage

**Function level (`git log -L`), fully measured:** 862 functions across 34 files —
5 of 19 `tools/` files (the 5 with ≥19 commits; the other 14 have ≤6 and cannot
host a ≥4 function), 6 of 9 shared-runtime files (the 3 skipped have 2 commits
each), 5 of 10 hand-written command modules, and **21 of 116** tracked `.py` files
under `migration/`.

**The gap, named:** 32 unscanned `migration/` files have ≥4 file-level commits and
could host a ≥4 function. The largest are `models.py` (31 commits — **0 functions**,
it is dataclasses), `execute/__init__.py` (19 — **0 functions**, re-exports),
`transform/mappers/workspace_mapper.py` (10), `transform/mappers/feature_mapper.py`
(9). **The execute-path gap is closed**: `execute/__init__.py` and
`execute/dependency.py` were both scanned after the fact (§3.4). Everything
unscanned sits in `transform/`, `report/`, `advisory/` and `cucm/` — the stages
`07-testability.md` §2.4 established are the well-tested, no-network ones.

**Not attempted:** blame-level attribution, line-churn totals, and any per-author
analysis. `00-facts.md` Q16 already establishes 1,022 of 1,043 commits carry one
author name, which makes author a constant, not a variable.

---

## 8. Handed forward

1. **§2.5 dates a Phase 6 finding and should be carried into the final report as
   a date, not a diagnosis.** The two retry policies agreed until 2026-07-24. The
   fix that split them (`bcb1330`) touched one file and no test. That is the
   concrete cost of the two-stack split, expressed as one commit.
2. **§3.1(3) is the phase's headline and it contradicts the phase's premise.**
   The retry block with six catalogued disagreements has one commit; the
   `wxcli cucm execute` command body has two. Any "where is the risk" ranking built
   on churn puts both at the bottom. If the final report uses history at all, it
   must say that churn on this repository ranks attention, not correctness.
3. **§4 is a third-item candidate for the final report, on the Target A side of
   the ledger**, and it is the one finding here that is cheap, proven, and
   unowned: 23 commits and 4.5 months of oscillation over which tests CI can see,
   with a 25-minute origin and 18 files still invisible.
4. **`tools/field_overrides.yaml` (§2.2) has no obsolescence check.** 2,729 lines,
   monotonically growing, and nothing in the 21-check gate asks whether an
   override still corresponds to a live spec field. That is a Phase 4 question
   this phase surfaced and did not answer.
