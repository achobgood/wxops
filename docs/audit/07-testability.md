# 07 — Boundaries and testability *(both targets, reported separately)*

Phase 7 of `docs/arch/wxops-architecture-audit-prompt_2.md`. Extends
`docs/audit/00-facts.md` Q15 (test inventory), `docs/audit/00-context.md` Q4 (the
stage map), and `docs/audit/06-machinery.md` §0/C2a and §10 item 4 (which handed
this phase the tracked/untracked split and the per-stage decomposition).

Labels: `[verified]` = I ran or parsed something this session. `[inferred]` =
reasoned from evidence short of direct observation. `UNKNOWN` = not established.

**Method.** `wxcli` never imported (hook-blocked — and the hook fired on one of my
own commands this session, §3.2). Tracked-file questions answered with
`git ls-files` / `git check-ignore --no-index`, never the working disk. Coverage
measured with `coverage 7.15.3` in a throwaway venv under the scratchpad; nothing
was installed into the repo or its interpreter. Two mutation experiments were run
in a **throwaway local clone** (`git clone --no-hardlinks . <scratch>`), never in
the working tree — which is unchanged and still carries exactly the 28 modified
files the brief described `[verified]`. Full suite runs were done only in that
clone.

**Target A** = the generated endpoint layer (`src/wxcli/commands/`) + the shared
runtime (`src/wxcli/*.py`) + the generator (`tools/`). **Target B** =
`src/wxcli/migration/` plus `src/wxcli/commands/cucm.py`.

> **Measurement window — added 2026-08-05 after the fact, and it matters.**
> Every measurement in this document was taken between **08:31 and 08:44 on
> 2026-08-05** (coverage artifact mtimes) against a working tree carrying the 28
> modified files the brief described. A **concurrent Phase 5 session then shipped two
> fixes at 09:24–09:27** — D13 (`in_progress` is now written before dispatch:
> `runtime.py:mark_ops_in_progress`, called from `engine.py:924-934`) and the
> preflight bulk-job probe (`checks.py` now returns `INCOMPLETE` instead of `WARN`;
> `cucm.py:1797` widened to `(FAIL, INCOMPLETE)`). See `05-safety.md` §3.1–§3.2.
>
> **The numbers below are unaffected** — they predate those edits by 40 minutes, and
> the mutation experiments (§2.5) ran in a clone of `b578a52`, which is unaffected by
> working-tree state either way. **Two descriptions are now stale**: §2.4's note that
> `preflight/runner.py:325-336` has never executed, and §6 item 5's characterisation
> of the probe. Both described the pre-fix tree accurately and are left as measured
> rather than silently rewritten.
>
> Two new tests pin those fixes — `tests/migration/execute/test_in_progress_written.py`
> and `tests/migration/preflight/test_bulk_job_probe.py`. `[verified]` They are **not
> ignored** (`.gitignore:55`'s `!tests/migration/**` re-include covers them) but are
> **untracked** — never `git add`ed. That is a milder condition than §3.4's 22
> gitignored files: they are one `git add` from CI, not excluded by rule. **Until
> staged, the fixes ship pinned by tests CI cannot see** — which is §3.4's thesis
> reproducing itself within a day of being written.

---

## 0. Four corrections to prior artifacts

Each is argued from a measurement below. Two overturn Phase 6; one overturns
`00-facts.md`; one is a denominator error that has propagated through three
documents.

### C1 — "244 test files, 240 tracked" compares two different denominators. **22 test files are untracked, not 4.**

`[verified]` `06-machinery.md` §0/C2a and the Phase 7 brief both state "240 test
files are tracked, 244 on disk," and name **seven** untracked paths. The 244 is a
count of files matching `test_*.py`; the 240 is a count of **all** `.py` under
`tests/`, including `__init__.py` and `conftest.py`. Comparing them understates
the gap by a factor of five.

Measured, four ways:

| Quantity | Value | Command |
|---|---:|---|
| `test_*.py` on disk under `tests/` | **244** | `find tests -name 'test_*.py' -type f` |
| `test_*.py` **git-tracked** | **222** | `git ls-files tests/ \| grep '(^\|/)test_[^/]*\.py$'` |
| **→ untracked test files** | **22** | difference |
| all `*.py` on disk under `tests/` | 272 | `find tests -name '*.py'` |
| all `*.py` git-tracked | 240 | `git ls-files tests/ \| grep '\.py$'` |
| tracked non-`.py` under `tests/` | **0** | confirms `06-machinery.md` §0/C2 |

The 22, every one gitignored by `.gitignore:53` (`tests/*`), verified individually
with `git check-ignore --no-index -v`:

```
test_auth.py            test_cleanup.py         test_cli_smoke.py
test_command_renderer.py test_common.py         test_config.py
test_config_org.py      test_generate_commands.py test_generator_regression.py
test_init_playbook.py   test_openapi_parser.py  test_org_id_injection.py
test_output.py          test_output_errors.py   test_packaging_metadata.py
test_partner_e2e.py     test_release_workflow.py test_smoke.py
test_update.py          test_update_check.py
tests/tools/test_command_renderer.py  tests/tools/test_openapi_parser.py
```

Plus 5 non-`test_*` files (`__init__.py`, `conftest.py`, `fixtures/expected_output.py`,
`live_test_v2.py`, and `tests/tools/__init__.py`) and 5 CUCM testbed scripts under
`tests/migration/cucm/` ignored by name at `.gitignore:106-111`.

**This matters because `00-facts.md` Q15 (`:428-434`) lists thirteen "top-level
suites bearing on the shared layer and the gate" — and seven of the thirteen are
untracked**: `test_auth.py`, `test_common.py`, `test_config.py`, `test_config_org.py`,
`test_cleanup.py`, `test_cli_smoke.py`, `test_command_renderer.py`. Q15 enumerated
the disk, not the index — the same error it corrected itself for three times.

### C2 — `test_auth.py` is not the only stale untracked test. **Three of the 22 are red, and two commits explain all three.**

Measured by running every one of the 22, one file at a time (§3.4). Phase 6 called
`test_auth.py`'s decay "a mechanism, not an incident" and asked for the count.
The count is **3 files, 26 failing tests**, and the mechanism reproduces exactly.

### C3 — The shared runtime has **8** library-layer process exits, not 6. The two Phase 6 missed are in the one function Target B imports.

`[verified]` `06-machinery.md` §4 lists `errors.py:203`, `:225`, `common.py:32`,
`:252`, `:263`, `config.py:118`. It omits **`auth.py:398` and `auth.py:405`** —
both inside `get_api()`, which is the single symbol `src/wxcli/migration/` imports
from the shared runtime (`preflight/runner.py:312`). Detail and consequence in §2.2.

### C4 — The `pytest.mark.live` filter is neither "dead" nor "mis-selecting". It is **registered and inert**, and what protects CI from the live tests is filename globbing and `.gitignore`, not the marker.

The spec offers two hypotheses (`:328`); the answer is a third. Measured in §4.

---

## 1. The decomposition the phase was called for

HOW TO RUN item 5 asks for the 214 to be decomposed by pipeline stage before it is
quoted, on the hypothesis that a suite **"concentrated on `transform/` (18,517 LOC,
no network) while `execute/` (8,119 LOC, the only stage that writes remotely) is
thin would make the headline reassuring and wrong."**

**The hypothesis is false as stated, and true in a form the spec did not
anticipate.** `execute/` is not thin. It is the second-largest test body in the
subsystem and the *densest*. What is thin is one file inside it — and it is the
only file in all of Target B that opens a socket.

`[verified]` Tracked test files and test LOC by `git ls-files`; tests collected by
`pytest --collect-only -q`; source LOC per stage from `00-context.md` Q4 (not
re-derived — I confirmed `execute/` sums to 8,119 as a spot check); statement
coverage from a `coverage run` over `tests/migration` (3,085 passed, 92.8s).

| Stage | Test files | Test LOC | Tests | Src LOC (Q4) | Tests /kLOC | **Stmt cov** |
|---|---:|---:|---:|---:|---:|---:|
| `transform/` | 73 | 25,059 | 1,079 | 18,517 | 58 | **93%** |
| `execute/` | 45 | 15,758 | **805** | 8,119 | **99** | **92%** |
| *(migration root)* | 17 | 5,870 | 307 | ~907 | — | **96%** |
| `report/` | 23 | 4,589 | 280 | 8,302 | 34 | 90% |
| `advisory/` | 14 | 4,145 | 248 | 3,738 | 66 | 92% |
| `cucm/` | 15 | 3,924 | 208 | 4,611 | 45 | **67%** |
| `preflight/` | 5 | 1,290 | 78 | 1,477 | 53 | 90% |
| `transferability/` | 13 | 1,052 | 34 | *(no source stage)* | — | — |
| `export/` | 4 | 1,036 | 46 | 1,013 | 45 | 98% |
| **migration total** | **209** | **62,723** | **3,085** | 46,684 | — | **89%** |

Two structural notes. `tests/migration/transferability/` has **no corresponding
source stage** — its 34 tests assert on runbook prose, CLI-command citations and
link validity in `.claude/` documents, not on `src/`. And `tests/migration/` holds
**209** tracked files, not 214; the other 5 are the gitignored live-CUCM testbed
scripts (`.gitignore:106-111`).

**So the reassuring headline is real: the migration suite is not hiding behind
`transform/`.** `execute/` carries 99 tests per thousand source lines against
`transform/`'s 58, and its coverage is within a point.

**And it is still wrong, one level down.** §2.4 decomposes `execute/` by file.

---

## 2. TARGET B — `src/wxcli/migration/`

### 2.1 Can core logic run without a terminal, without the CLI framework, without network?

**Yes, and this is Target B's strongest architectural property.** `[verified]`

- **Without the CLI framework.** Three files in 46,684 lines import `typer` or
  `rich`: `cucm/discovery.py`, `cucm/extractors/users.py`,
  `cucm/extractors/devices.py` — the three `Console()` instantiations Phase 6
  found. Every other module is importable and runnable with no Typer, no Rich, no
  Click.
- **Without a network.** Three files import an HTTP or SOAP client:
  `execute/engine.py` (`aiohttp`), `cucm/connection.py` (`zeep`),
  `cucm/unity_connection.py` (`requests`). `transform/` (18,517), `report/` (8,302),
  `advisory/` (3,738) and `export/` (1,013) import none — 31,570 lines with no
  transport dependency at all, confirming `00-context.md` Q4 from the import side.
- **Without a terminal.** 3,085 tests run to completion with no TTY, no token, and
  no socket. Six test files stub `aiohttp` with `aioresponses`; the rest never
  reach a transport.

This is why the subsystem is testable at 89% and why 3,085 tests run in 93
seconds. It is the direct architectural counterpart to Target A's problem (§3.1).

### 2.2 Does anything below the CLI layer print to stdout or call `sys.exit`?

**Exits: no — B is clean, and its one seam into the shared runtime is not.**

Phase 6 established zero `typer.Exit`/`sys.exit`/`SystemExit` across all 46,684
lines. Confirmed. But the single symbol B imports from Target A —
`get_api()` — **exits the process twice** (`auth.py:398`, `:405`), which Phase 6's
list of six omitted (C3).

The migration code knows this and defends against it (`preflight/runner.py:316-321`):

```python
try:
    api = get_api()
except SystemExit:
    # get_api raises typer.Exit when no token is configured
    return None
except Exception:
    return None
```

**The comment is wrong and the handler is dead** `[verified]`: `typer.Exit`'s MRO
is `Exit → RuntimeError → Exception → BaseException`; `issubclass(typer.Exit,
SystemExit)` is `False` (typer 0.27.1 / click 8.3.2). The `except SystemExit`
clause can never fire. **Behaviour is nonetheless correct**, because the
`except Exception` fallback on the next line catches it — `typer.Exit` *is* an
`Exception`. So this is a dead branch and a false comment, not a defect. I checked
before asserting one.

It is uncovered either way: `runner.py:313-322` never executes in any test
`[verified]`, so the no-token path through B's only shared-runtime seam has never
run.

**Stdout: yes, and Phase 6 already judged it.** §6.4 there measured `cucm execute`
printing errors to stdout while Target A's convention is stderr. Nothing to add;
I did not re-derive it.

### 2.3 Do raw remote response shapes leak to the CLI surface?

**Yes, and on Target B they leak into persistent storage as well.** `[verified]`

`execute_single_op` builds `error=f"{resp_status}: {error_msg}"` from
`resp_body.get("message") or resp_body.get("errors", str(resp_body))`
(`engine.py:205-210`), where `errors` is a Webex JSON array rendered by Python's
`str()`. That string is written to `plan_operations.error_message`
(`runtime.py:213-216`) and read back by `wxcli cucm execution-status`. Phase 6
§6.1 and §6.5 established the shape (`500: {}`, a Python repr, PII at rest); the
testability consequence is new and is §2.4's: **the line that constructs it has
never executed in a test**, so its format is unpinned in both directions — nothing
would catch a change to it, and nothing documents it as a contract.

`OpResult.body` carries the raw parsed response object unchanged
(`engine.py:207-210`, `:219`).

### 2.4 What the 3,085 tests actually pin — and where `execute/` is thin

`[verified]` Per-file coverage inside `execute/`, and per-file import analysis of
its 44 `test_*.py` files:

| Module | Src LOC | Stmts | **Cov** | Test files importing it |
|---|---:|---:|---:|---:|
| `planner.py` | 2,552 | 846 | 93% | 16 |
| `handlers.py` | 2,403 | 1,003 | 94% | 17 |
| **`engine.py`** | **964** | **424** | **77%** | **8** |
| `runtime.py` | 571 | 136 | 99% | 5 |
| `dependency.py` | 501 | 82 | 100% | 4 |
| `batch.py` | 277 | 97 | 99% | 7 |
| `__init__.py` | 322 | 33 | 100% | — |

**`engine.py` is the only module in Target B that opens a socket, and it is the
worst-covered file in its own stage — 15 points below the stage average and 8 of
44 test files touch it.** The 805 tests are concentrated on plan *construction*
(`planner.py` + `handlers.py` = 4,955 of 8,119 LOC), which is exactly the
`transform/`-vs-`execute/` skew the spec predicted, displaced one level down.

**Line-level, inside `execute_single_op` — the function every Webex write passes
through** `[verified]`:

| Lines | What | Executed? |
|---|---|---|
| 188–192 | retry loop, semaphore, `session.request` | **HIT** |
| 193–194 | `resp_body = await resp.json()` | **HIT** |
| **195–196** | `except Exception: resp_body = {}` — the non-JSON body case | **MISS** |
| 199–203 | the 429 branch: read `Retry-After`, sleep, `continue` | **HIT** |
| 205 | `if resp_status >= 400:` | HIT *(never true)* |
| **206–210** | build the error string, return a failed `OpResult` | **MISS** |
| 217–220 | success: extract id, `break` | **HIT** |
| **222–229** | `except aiohttp.ClientError` — connect retry + exhaustion | **MISS** |
| **231–234** | the `for…else` — `"Max retries exceeded (429)"` | **MISS** |

Line 205 executes and is **only ever evaluated false**. So: the 429 happy path is
pinned; **every failure branch beneath it is unpinned.** That is the fuller version
of the answer Phase 6 gave (`§10` item 4 / lead 3) — not "no test exercises a 5xx"
but "line 206 has never run."

Three more uncovered regions of consequence, all naming Phase 6 findings:

- **`engine.py:625-663, 681-694`** — `_try_find_existing`'s per-resource-type
  search branches, i.e. almost all of the 409 auto-recovery path (D8), including
  the `items[0]`-with-no-name-check return. **`:708-709`**, its
  `except Exception: pass`, is also uncovered.
- **`engine.py:329-341, 368-369`** — the bulk submit error paths and the narrow
  `except TimeoutError` (D5).
- **`preflight/runner.py:325-336`** — the entire body of the broken bulk-job probe
  closure (`api.session.ep`, `api.session.get`, the `requests` catch). Phase 6 §5
  said it is "referenced nowhere in `tests/`"; measured, **those twelve lines have
  never executed.** Coverage confirms the defect lives in code no test constructs.

**And the inverse, which is the cleanest illustration of why the aggregate
misleads:** `src/wxcli/migration/rate_limiter.py` — the module Phase 6 proved
nothing in `src/` imports — is **96% covered** by its dedicated unit test. The repo
pins dead code at 96% and the live-write failure paths at 0%.

### 2.5 Would any test fail if the two stacks drifted further apart? — **Measured by mutation. No.**

The spec asks this directly (`:327`). Rather than infer it from coverage, I ran it,
in the throwaway clone at `b578a52`, whose unmutated baseline is **3,580 passed,
drift gate PASS** `[verified]`.

**Mutation 1 — drive the two retry policies as far apart as the source allows:**

| File:line | From | To |
|---|---|---|
| `auth.py:160` | `RETRY_STATUSES = frozenset({429,500,502,503,504})` | `frozenset()` |
| `auth.py:159` | `MAX_RETRY_AFTER_SECONDS = 30` | `86400` |
| `auth.py:158` | `DEFAULT_MAX_ATTEMPTS = 4` | `1` |
| `engine.py:36` | `MAX_RETRIES = 5` | `1` |
| `engine.py:199` | `if resp_status == 429:` | `if resp_status == 99999:` |

Target A now retries nothing and will honour a 24-hour `Retry-After`; Target B now
never retries a 429 at all. **Result: `3580 passed`. Drift gate: `result: PASS`,
exit 0.** `[verified]`

**Mutation 2 — reclassify every HTTP error on the migration write path as success:**

`engine.py:205`, `if resp_status >= 400:` → `if resp_status >= 40000:`. A 403, 404,
409 or 500 now falls through to the success branch: `webex_id` is taken from the
error body, the op is recorded `completed`, and dependents cascade forward instead
of being skipped.

**Result: `tests/migration/execute` → `805 passed`. Full suite → `3580 passed`.
Drift gate: `result: PASS`.** `[verified]`

**This is the phase's central finding.** Phase 6 spent an entire session
establishing that the two stacks disagree on six policies and that A is right on
most of them. Nothing in CI would notice if they disagreed on *all* of them, and
nothing in CI would notice if the migration engine stopped recognising failure.
The clone was restored to a clean tree afterwards (`git status --porcelain` → 0
modified) `[verified]`.

### 2.6 Where Target B is genuinely thin

`cucm/` at 67% is the lowest-covered stage, and the thinness is concentrated in the
AXL extractors — the code that reads the customer's cluster and produces the input
every well-tested stage downstream consumes `[verified]`:

| File | Stmts | Cov |
|---|---:|---:|
| `cucm/extractors/e911.py` | 54 | **24%** |
| `cucm/extractors/users.py` | 70 | **24%** |
| `cucm/extractors/device_profiles.py` | 48 | **25%** |
| `cucm/extractors/announcements.py` | 43 | **28%** |
| `cucm/unity_connection.py` | 118 | **35%** |
| `cucm/extractors/voicemail.py` | 87 | **38%** |
| `cucm/extractors/routing.py` | 276 | **46%** |

`transform/` is 93%-covered against fixtures that these extractors produce. A
93%-covered mapper fed by a 24%-covered extractor is well-tested against a data
shape nobody has pinned. `00-context.md` Q4's stage table treats `cucm/` as an
input stage; on this evidence it is also the least-verified one.

`unity_connection.py` at 35% is consistent with Phase 6 §7.3 — its `__init__` is
the one method no test executes, which is where both its defects live.

---

## 3. TARGET A — the generated layer, the shared runtime, and the generator

### 3.1 Can core logic run without a terminal, without the CLI framework, without network? — **No. There is no layer below the CLI.**

`[verified]`, by `ast` over all 184 tracked modules in `src/wxcli/commands/`:

| | Count |
|---|---:|
| Function definitions | 2,004 |
| — carrying `@app.command` / a callback decorator | **1,892 (94%)** |
| — public and undecorated (a testable seam) | **38** |
| — private helpers (`_name`) | 74 |

And the 38 are not in generated code: they are in the hand-written modules —
`_lazy.py` (`build_lazy_commands`, `mount_all`, `registered_groups`) and
`cleanup.py` (`list_resources`, `build_inventory`, `delete_resource`).

**A generated command is one Typer-decorated function that inlines everything:**
`get_api()` → build URL → build `params` → `rest_*`/`follow_pagination` →
`handle_rest_error` → `emit`. Read `call_queue.py:31-66` for the canonical shape.
There is no request-builder to test, no response-mapper to test, and no unit
between the decorator and the socket. Exercising a generated command means either
driving it through `CliRunner` or monkeypatching that module's `get_api` — the two
things the untracked `test_cli_smoke.py` and `test_partner_e2e.py` do, and the two
things CI never runs.

This is the exact inverse of Target B (§2.1), and it is a property of the
*generator*, not of any file — which by the spec's own severity model makes it a
one-defect-times-the-whole-surface observation rather than 1,892 small ones.

### 3.2 The import hook, read as evidence about layering

The spec asks for this (`:323`). The hook (`.claude/hooks/wxcli-gate.sh:33`,
`:41-44`) blocks importing `wxcli` from Python, citing the 2026-07-28 incident:
*"a subagent imported four generated delete functions to see whether they crash;
the OptionInfo-is-truthy trap skipped the confirm prompt and four unconfirmed
DELETEs reached the live org, one of them `DELETE /v1/organizations/{id}`. Only
Cisco refusing them saved it."*

Both halves verified this session:

1. **There is no way to "see whether it crashes" without calling the live API** —
   that is §3.1. The subagent's instinct was correct; the architecture left it no
   safe move.
2. **The `OptionInfo` trap is real** `[verified]`: `typer.Option(False, "--force")`
   evaluated outside Typer's runtime is an `OptionInfo` instance whose `bool()` is
   `True`, so `not force` is `False` and the generated
   `if not force: typer.confirm(..., abort=True)` (e.g. `call_queue.py:370-371`) is
   skipped. The guard is not merely bypassed on direct call — **it inverts.**

**So the hook is a control compensating for an architectural property, not for a
bad habit** — and the repository's own testing story depends on the same
compensation: the only way its untracked tests exercise a command is by
monkeypatching `get_api` in the target module before invoking it, which is the
manual, per-test version of what the hook enforces globally.

The hook's own comment states its limit honestly — *"a hook sees only the command
string, so a `.py` file on disk that imports wxcli is invisible here. That is why
`python tools/drift_check.py` and pytest keep working, and why this is a guard
rail, not a proof."* That is accurate, and it is why running the suite is
sanctioned. **Live evidence from this session:** the hook denied one of my own
Bash calls because the string `import wxcli` appeared inside a `python -c`
verification line that never touched a command module. Fails closed, as designed.

Two bounds worth recording. The hook does **not ship** (`00-context.md`
"The bound that does not ship"; `wxcli-dist/assemble.py:161`), so no downstream
operator has it. And it is `PreToolUse`-only, so it constrains agents, not
`pytest`, not CI, and not a human.

### 3.3 Real coverage of the 1,790-line shared runtime — per target, as the spec asks

`.coverage` at repo root is dated 2026-03-23 and was not used. **Neither `coverage`
nor `pytest-cov` is installed in the project interpreter, and CI installs neither**
(`ci.yml:35` installs `pytest pytest-asyncio aioresponses` only) — so **no coverage
number has been produced by this project's own tooling in over four months.** I
measured in an isolated venv.

Scope note: I measure the shared runtime at **1,766** tracked lines across 9 files
(`git ls-files 'src/wxcli/*.py'`, depth 1). `00-facts.md` says 1,790. I did not
reconcile the 24-line difference; it does not move any conclusion below.

**Statement coverage of `src/wxcli/*.py`, tracked tests only — this is what CI can
run:**

| Module | Stmts | Miss | **Cov** | +untracked |
|---|---:|---:|---:|---:|
| `errors.py` | 91 | 6 | **93%** | 93% |
| `suggest.py` | 51 | 2 | **96%** | 96% |
| `common.py` | 116 | 40 | 66% | 95% |
| `auth.py` | 236 | 113 | **52%** | 61% |
| `main.py` | 115 | 81 | 30% | 73% |
| `update_check.py` | 82 | 57 | 30% | 87% |
| `output.py` | 125 | 89 | **29%** | 97% |
| `config.py` | 87 | 66 | **24%** | 63% |
| **TOTAL** | **907** | **456** | **50%** | **79%** |

Two readings, and the second is the finding.

**(a) 50% is the honest CI number** — and it is carried by two modules.
`errors.py` (93%) and `suggest.py` (96%) are well pinned, by
`test_errors_actionability.py`, `test_errors_id_kind.py` and
`test_suggest_and_paging.py` — three of the 23 tracked root files. Of 240 tracked
test files, **only six import any shared-runtime module at all**, and `config.py`,
`output.py` and `update_check.py` have **zero tracked importers**.

**(b) 29 percentage points — 269 of 907 statements — exist only on one
developer's disk.** That is the measured price of `.gitignore:53`.

**And the misses are not random.** `auth.py`'s uncovered lines map onto named
functions, and they are precisely the ones Phase 6 spent a session on. Even with
**every** test on this machine — tracked *and* untracked — the following have zero
statement coverage `[verified]`:

| `auth.py` lines | Function | Why it matters |
|---|---|---|
| **226–260** | `WebexSession._request` | **the entire retry loop** — `RETRY_STATUSES`, the `Retry-After` parse, the 30s cap, `time.sleep`. Every HTTP call from all ~1,887 generated commands goes through it |
| 264–269 | `_json_or_raise` | turns a non-2xx into `WebexError` |
| 273–295 | `rest_get`/`put`/`post`/`patch`/`delete` | the whole public surface the generated layer calls |
| **298–311** | `follow_pagination` | see §3.5 |
| 172–181 | `_retry_enabled`, `_max_attempts` | `WXCLI_NO_RETRY`, `WXCLI_RETRY_MODE`, `WXCLI_MAX_ATTEMPTS` |
| 391–407 | `get_api` | including both `typer.Exit` sites (C3) |

`_backoff_delay` (`:186-188`) and `_env_float`/`__init__` (`:197-213`) *are*
covered — but only by the 6 still-passing tests in the untracked `test_auth.py`.
In CI they are uncovered too.

**So Target A's retry policy is unpinned in exactly the same way Target B's is**
(§2.5). The mutation experiment gutted both and neither noticed. The asymmetry
Phase 6 identified — B's stack better pinned than A's — holds at the level of
*files tracked*; at the level of *behaviour pinned*, both are at zero on this axis.

**The generated layer itself:** 55,386 statements, **12% covered by tracked tests**
(14% with everything on disk) `[verified]`. Per the spec's severity model this is
the least interesting number in the phase — generated output is a shadow. The
number that matters is the next one.

**The generator is pinned by nothing in CI.** Its four test files —
`test_command_renderer.py` (1,397 LOC, 134 tests), `tests/tools/test_command_renderer.py`
(372 LOC, 20 tests), `test_generate_commands.py` (29 tests),
`test_generator_regression.py` (4 tests) — are **all four untracked** `[verified]`.
That is 187 tests over the component whose severity model reads *one defect times
the entire generated surface*, none of which runs on a PR. `tools/generate_commands.py`
and `tools/command_renderer.py` are **currently modified in the working tree** by
the audit itself and would ship with no CI test coverage of the renderer at all.

*(I did not measure statement coverage of `tools/` per target — the run was
interrupted. Stated as unmeasured rather than estimated. The tracked/untracked
status of the four files above is measured and is the load-bearing claim.)*

### 3.4 The decay mechanism, measured

Lead 2 asked how many untracked files are stale, and called running them "the
single highest-value thing in the phase." Every one of the 22 was run
individually `[verified]`:

| File | Result |
|---|---|
| **`test_auth.py`** | **18 failed, 6 passed** |
| **`test_partner_e2e.py`** | **5 failed, 16 passed** |
| **`tests/tools/test_command_renderer.py`** | **3 failed, 17 passed** |
| `test_smoke.py` | **no tests ran** — 0 test functions |
| `test_cli_smoke.py` | 122 passed |
| `test_command_renderer.py` | 134 passed |
| `test_openapi_parser.py` | 92 passed |
| `tests/tools/test_openapi_parser.py` | 33 passed, 4 skipped |
| `test_cleanup.py` | 39 passed |
| `test_common.py` | 36 passed |
| `test_output_errors.py` | 33 passed |
| `test_update_check.py` | 33 passed |
| `test_generate_commands.py` | 29 passed |
| `test_update.py` | 26 passed |
| `test_output.py` | 23 passed |
| `test_config.py` | 11 passed |
| `test_init_playbook.py` | 10 passed |
| `test_config_org.py` | 6 passed |
| `test_release_workflow.py` | 6 passed |
| `test_packaging_metadata.py` | 5 passed |
| `test_generator_regression.py` | 4 passed |
| `test_org_id_injection.py` | 1 passed |

**712 tests exist on this disk that CI has never run. 682 pass, 26 fail, 4 skip.**

**All 26 failures are one mechanism: an exact-string or patch-target assertion
invalidated by a refactor, in a file CI cannot see.** None is a live defect in
shipping code — I checked each `[verified]`:

| File | Cause | Broken by | Red since |
|---|---|---|---|
| `test_auth.py` | patches `wxcli.auth.httpx.request` at 10 sites; `auth.py` imports `httpx` lazily inside its request methods (`:206`, `:226`), deliberately (`:14-21`) | `751010c` *"real argument help, runnable examples, 28 renames, 8x faster start"* | **2026-07-28** |
| `tests/tools/test_command_renderer.py` | asserts `'@app.command("show")'`; the renderer now emits `@app.command("show", short_help="…")` | `751010c` (same commit) | **2026-07-28** |
| `test_partner_e2e.py` | asserts `"User:  Jane Partner"`; `whoami` now renders a table via `emit()` (`main.py:67-76`) | `648439f` *"give hand-written commands the same --fields surface"* | **2026-07-25** |

`[verified]` `short_help` is **not** part of the audit's uncommitted change to
`tools/command_renderer.py` (`git diff` shows no `short_help` hunk; it is present
in `HEAD`). These are pre-existing.

Two commits produced all 26 failures, and **one commit (`751010c`) broke two files
at once.** The mechanism is not "someone forgot"; it is that an untracked test has
no way to tell anyone. Note also that `tests/tools/test_command_renderer.py` was
last touched 2026-07-01 while its 1,397-line sibling `tests/test_command_renderer.py`
was updated on 2026-07-28 — the maintainer updated the file they were looking at
and had no signal about the other. **Two files with the same basename, one
maintained, one rotting, neither visible.**

**A fragility worth one line:** three tracked test files —
`test_drift_check_positionals.py`, `test_drift_check_references.py`,
`test_drift_check_registrations.py` — match `tests/*` with **no re-include** in
`.gitignore` `[verified, --no-index]`. They survive only because they are already
in the index. They are present in a fresh clone today; anyone who runs
`git rm --cached` on one, or adds an equivalent file, silently gets the untracked
behaviour above.

### 3.5 `follow_pagination`: 173 call sites, zero coverage anywhere

`[verified]` The three page-walkers, by call sites in `src/wxcli/commands/`:

| Walker | Call sites | Covered by tracked tests? |
|---|---:|---|
| **`follow_pagination`** (`Link: rel="next"`) | **173** | **No — `auth.py:298-311` uncovered** |
| `follow_page_param` (CC `page`/`pageSize`) | 96 | Yes — `test_pagination_walkers.py` |
| `follow_scim` (`startIndex`/`count`) | 5 | Yes — `test_pagination_walkers.py` |

`tests/test_pagination_walkers.py` is tracked, and its own docstring line 1 reads
*"The two page-walkers `follow_pagination` could never see…"* — it was written
**deliberately** to cover the two siblings. Nothing covers the third. `test_auth.py`
does not mention it either (`grep` → 0), so `follow_pagination` is uncovered on
this disk, not merely in CI.

That is the walker behind `--all` on the majority of generated list commands, and
`00-facts.md` Q18 lists `--all` as committed public contract. Its `Link`-header
parse (`auth.py:304-310`) — a hand-rolled `split(",")` / `strip("<>")` — is
executed by no test.

### 3.6 Do raw remote response shapes leak to the CLI surface? — **Yes, by design, and it is a published contract.**

`[verified]` A generated command extracts the item list from the raw response
(`call_queue.py:59-62`) and passes it unchanged to `emit(items, …)`. Across
`src/wxcli/commands/` there are **2,506 `emit(` sites, 1,409 of them `emit(result…)`
and 522 `emit(items…)`** — the raw parsed Webex JSON. `emit` applies `--fields`
(`common.py:211`), a **JMESPath expression evaluated against Webex's own field
names**.

There is no intermediate model. So Webex's response schema *is* the CLI's output
schema, and `--fields '[].{name:name,id:id}'` is a user-visible expression over
upstream field names. `00-facts.md` Q18 counts `--fields` among the committed
contract.

This is a legitimate design for a thin API wrapper and I am not calling it a
defect — it is the reason the generator can exist at all. The testability
consequence is the finding: **an upstream response-shape change is a breaking CLI
change with no layer in between and no test that would see it.** The drift gate
compares spec ↔ CLI ↔ docs, all three downstream of the same specs (STATUS,
`:379`), so a Webex field rename that is faithfully reflected in the spec
propagates to the CLI surface and the gate reports PASS throughout.

---

## 4. The `pytest.mark.live` question — settled

The spec offers two hypotheses (`:328`): *"dead filter, or live tests that the
marker no longer selects."* **Neither.** `[verified]`

The marker is **properly registered** — `pyproject.toml:80-82`:

```toml
markers = [
    "live: requires live Webex API access (deselect with '-m not live')",
]
```

So `-m "not live"` is a valid, non-erroring, non-warning filter. It is also inert:

| Measurement | Result |
|---|---|
| `pytest tests/migration tests/org_health -m "live" --collect-only` | `no tests collected (3165 deselected)` |
| `pytest tests/migration --collect-only` | `3085 tests collected` |
| `pytest tests/migration -m "not live" --collect-only` | `3085 tests collected` |

**`-m "not live"` deselects zero tests. Not one file in the repository carries the
marker.**

**What actually keeps live code out of CI is two accidents, neither of them the
marker:**

1. **`pyproject.toml` sets no `python_files`**, so pytest's default `test_*.py` /
   `*_test.py` glob applies. `tests/live_test_v2.py` contains **8 `def test_`
   functions** that run real create→verify→update→delete cycles — and its filename
   does not match, so `pytest tests/` never reaches it. Named explicitly it
   collects all 8 `[verified]`. The same glob accident protects
   `tests/migration/cucm/validate_live_cucm.py`, `provision_testbed*.py` and
   `teardown_testbed.py`.
2. **`.gitignore`**, which keeps all six of those files out of a clone entirely.

The one file that *does* match the glob is `tests/test_smoke.py` — and it is safe
only because it has **zero test functions**; its `wxcli whoami / locations list /
users list …` subprocess calls sit under `if __name__ == "__main__"`. Adding a
single `def test_x()` to that file would make CI call a live Webex org, and
`-m "not live"` would not deselect it.

**One more reason `live_test_v2.py` could not run even if collected:** it imports
`wxc_sdk` (`:9-16`), which is **not a dependency** — `grep wxc_sdk pyproject.toml`
returns nothing, and Phase 6 §5 established the same for `WebexSimpleApi`. It was
dropped in `e4dfb22` (2026-04-17, *"drop wxc_sdk dependency, replace with native
httpx"*) and survives only because it is still installed on this machine. The file
has been un-runnable in a clean environment for **three and a half months**, and
being untracked is why nobody found out — the same mechanism as §3.4.

**Verdict.** The marker system is *correctly configured and entirely unused*. It
reads, to anyone inspecting `ci.yml:63`, as an active safety control. It selects
nothing, guards nothing, and the protection it appears to provide is being
supplied by a filename convention nobody wrote down.

---

## 5. Recorded remote responses — confirming C2, and what it means

`06-machinery.md` §0/C2 established there are none, for any system, overturning
`00-facts.md` Q15 and the spec's own Phase 7 bullet (`:326`). Re-confirmed from a
different angle this session: **`git ls-files tests/ | grep -v '\.py$'` returns
zero, and a fresh checkout of `HEAD` contains exactly 240 `.py` files under
`tests/` and nothing else** `[verified]`. There is no fixture data of any kind in
the repository.

The spec asks what that means for changing either stack safely. Combined with §2.5
and §3.3:

- **Target A.** The retry loop, the five `rest_*` methods and `follow_pagination`
  are covered by nothing and pinned by nothing. `errors.py` is the exception at
  93% — it is pure functions over already-parsed dicts, which is exactly why it
  could be tested without recorded responses. **The dividing line is not
  importance, it is whether the code needs a transport.**
- **Target B.** Six test files stub `aiohttp` with `aioresponses`, so the
  mechanism to record responses is *already installed and already used* — CI
  installs it deliberately (`ci.yml:35`) and pins `aiohttp<3.14` for it. The
  missing thing is not tooling. It is the five tests Phase 6 §8 step 2 names, none
  of which exists.
- **Consequence for sequencing.** Phase 6 §8 step 1 (repair and track
  `test_auth.py`) is now measured to be **necessary but not sufficient**: even with
  it fully green, `_request` (`:226-260`) stays uncovered unless the 18 repaired
  tests actually drive the retry loop, and `follow_pagination` stays uncovered
  regardless (§3.5). The step should be stated as *"repair, track, and add the
  `follow_pagination` and `_request` cases,"* not just *"repair and track."*

---

## 6. What can break in production with a green suite?

The spec's closing question. Everything below is `[verified]` above; this section
only assembles it. A "green suite" means: fresh clone at `b578a52`,
`pytest tests/ -m "not live"` → **3,580 passed**, `python -m tools.drift_check
--enforce` → **PASS** — both measured this session.

**Target B — on the one path that writes to a customer's org:**

1. **Every failure branch of `execute_single_op`.** A 403/404/409/500 can be
   reclassified as success and 3,580 tests still pass (§2.5, Mutation 2). Today
   that branch is correct; nothing holds it there.
2. **Both retry policies, in any direction.** Gutted simultaneously, suite and gate
   both green (§2.5, Mutation 1). Every disagreement Phase 6 catalogued (D1–D4,
   D7, D12) can widen without a signal, and every one of them can be *introduced*
   into a stack that does not have it yet.
3. **The 409 auto-recovery search** (`engine.py:625-694`) — the code that can bind
   a migration operation to a pre-existing remote object it did not create. Its
   per-type branches never execute in a test (§2.4). D8's missing name-equality
   check would be added, or removed, invisibly.
4. **The bulk-job path's error handling** (`:329-341`, `:368-369`) — the ops that
   act on every device in a location or org.
5. **The preflight bulk-job probe** (`runner.py:325-336`) is structurally broken
   *and* has never executed in a test. The eight tests that cover
   `check_bulk_device_job_support` all inject a lambda; the factory that builds the
   broken closure is constructed by no test. **A check can be thoroughly tested and
   still be incapable of running.**
6. **The AXL extractors at 24–46%** feed the 93%-covered `transform/` stage. A
   change in what CUCM returns surfaces as a mapper working perfectly on a shape
   that no longer arrives.

**Target A — across ~1,887 published commands:**

7. **The retry loop** (`auth.py:226-260`) and **all five `rest_*` methods** —
   zero coverage. Every HTTP call the generated surface makes passes through code
   no test executes.
8. **`follow_pagination`** — 173 call sites, no coverage anywhere (§3.5). A
   regression in its `Link`-header parse silently truncates `--all` on the majority
   of list commands. `00-facts.md` Q18 lists `--all` as committed contract, and
   `CLAUDE.md` instructs the operating LLM that any *how many* / *which ones* / *are
   there any* question requires it. **A silent short-read here produces a confident
   wrong count** — the exact failure mode `CLAUDE.md`'s `--calling-data` note was
   written to prevent, in a place nothing guards.
9. **The generator.** All four of its test files are untracked (§3.3), so the
   component the severity model multiplies by the whole surface has **no CI
   coverage** — and `tools/command_renderer.py` and `tools/generate_commands.py`
   are modified in the working tree right now. This compounds `02-drift.md` F3
   (nothing asserts a destructive command has a guard) and the STATUS finding that
   nothing detects a hand-edit to generated code: there is no check on the input,
   no check on the transform, and no check on the output.
10. **`config.py` at 24%** — the lowest-covered shared module, and the one that
    resolves which org every auto-injected `orgId` points at.

**The cross-cutting one:** a Webex response-shape change propagates spec → CLI →
docs with the gate green at every step, because all three sides are downstream of
the same spec (§3.6).

---

## 7. Read coverage

**Read in full:** `.gitignore` (`:45-119`), `.claude/hooks/wxcli-gate.sh:1-70`,
`.github/workflows/ci.yml:25-75`, `pyproject.toml:70-95`, `tests/test_smoke.py`,
`tests/test_org_id_injection.py`, `src/wxcli/auth.py:262-296` and `:388-407`,
`src/wxcli/migration/preflight/runner.py:145-170`, `:288-340`,
`src/wxcli/migration/execute/engine.py:180-235`.

**Read in the regions that matter:** `tests/test_partner_e2e.py` (fixtures and the
5 failures), `tests/test_cli_smoke.py` (`:340-420`, the cleanup mocks),
`src/wxcli/commands/call_queue.py:25-80`, `:365-380`, `src/wxcli/common.py:189-214`,
`src/wxcli/main.py:60-85`.

**Parsed, not read:** all 184 tracked modules in `src/wxcli/commands/` (`ast`, for
the decorator census in §3.1). All 209 tracked migration test files (import
analysis and LOC).

**Executed:** all 22 untracked test files, individually. `tests/migration` under
coverage (3,085 passed). `tests/org_health` under coverage (80 passed). The 23
tracked root files under coverage (415 passed). The full tracked suite **three
times in a throwaway clone** — baseline, Mutation 1, Mutation 2 (3,580 each).
`tools.drift_check --enforce` three times in the same clone. The working tree's own
suite was never run in full (project rule); every full run was in the clone.

**Not measured, stated as such:** statement coverage of `tools/` per target (run
interrupted; the tracked/untracked status of the generator's four test files is
measured and is what the §3.3 claim rests on). The 24-line discrepancy between my
1,766 and `00-facts.md`'s 1,790 for the shared runtime. Branch coverage anywhere —
every figure here is **statement** coverage, which is the weaker measure and
therefore makes every gap reported above a floor, not a ceiling.

**Claims I am explicitly not making:** that the 682 passing untracked tests assert
anything *useful* — I ran them, I did not read them. That the 93%-covered
`transform/` stage is *correct* — coverage is not correctness, and §2.6 is the
reason to doubt its inputs. That `errors.py`'s 93% means its tips are right. That
the mutations I chose are the worst available; they are the two the prior phases
pointed at.

---

## 8. Handed forward

**Corrections this phase makes** — each argued in §0:

| Claim | Where | Measured |
|---|---|---|
| "244 test files, 240 tracked" — 4 untracked | `06-machinery.md` §0/C2a; Phase 7 brief | **Two denominators.** 244 `test_*.py` on disk vs 222 tracked → **22 untracked**, all gitignored |
| 13 named top-level suites cover the shared layer | `00-facts.md` Q15 `:428-434` | **7 of the 13 are untracked** and absent from CI |
| `tests/migration/**` is tracked wholesale | `06-machinery.md` §0/C2a | **209 of 214**; 5 live-CUCM testbed scripts are ignored by name (`.gitignore:106-111`) |
| The shared runtime has 6 library-layer exits | `06-machinery.md` §4 | **8.** `auth.py:398`, `:405` are in `get_api()` — the one symbol Target B imports |
| `pytest.mark.live` is a dead filter *or* mis-selects | audit spec `:328` | **Neither.** Registered (`pyproject.toml:80-82`) and inert; filename globbing + `.gitignore` do the protecting |
| Target B's suite might be concentrated on `transform/` | audit spec HOW TO RUN item 5 | **False at stage level** (`execute/` 99 tests/kLOC vs 58, 92% vs 93%); **true one level down** — `engine.py` 77%, 8 of 44 files |

**Open, and belonging to later phases:**

1. **Nothing here proposes a fix.** Under the remediation rule, the two candidates
   in `migration/` — writing `in_progress` before dispatch (Phase 6 D13) and the
   name-equality check in `_try_find_existing` (D8) — both fail the *"no later
   phase would teach you more"* test: Phase 5 owns the execute path's safety model
   and Phase 8 owns whether these functions are repeat-churn sites. The
   `.gitignore` items sit outside `migration/` and the generator. **Sequencing
   stays in `06-machinery.md` §8, amended by §5 above.**
2. **`tests/tools/` is a duplicate tree.** `test_command_renderer.py` and
   `test_openapi_parser.py` exist in both `tests/` and `tests/tools/`, with
   different content and different maintenance dates. Deciding which survives is a
   prerequisite to tracking either. → whoever executes §8 step 1.
3. **33 tracked tests shell out to `git`** (`git ls-files`, `git check-ignore`) and
   fail without a `.git` directory `[verified]` — they pass in a real clone and in
   CI's `actions/checkout`. Recorded because it constrains how the suite can be
   packaged or vendored, not because it is broken.
4. **Whether the 682 passing untracked tests are worth tracking** is unestablished
   — I measured that they pass, not that they assert anything load-bearing. The
   `.gitignore:58-100` comments show the author has been promoting files
   individually as each proves it caught real drift; that policy is working and the
   question is only whether it is keeping pace.
5. **Branch coverage.** Every number here is statement coverage. `engine.py:200`'s
   unguarded `int(Retry-After)` — Phase 6's D2, a real latent defect — sits on a
   line that reports as **covered**. A branch-coverage run would sharpen §2.4 and
   §3.3 and would likely widen both gaps.
