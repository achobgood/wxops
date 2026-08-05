# CI Wiring + Gate Blind Spot Audit

Repo: `/Users/ahobgood/Documents/webexCalling`. Only two tracked workflow files exist
(`.github/*` is gitignored except `workflows/ci.yml` and `workflows/release.yml` —
`[verified]` `.gitignore:130-134`: `.github/*` then `!.github/workflows/` /
`.github/workflows/*` then `!.github/workflows/release.yml` / `!.github/workflows/ci.yml`).

---

## PART A — CI WIRING

### A1. How `tools/drift_check.py` is invoked

`[verified]` `.github/workflows/ci.yml:114-147`, job `drift-gate`.

- Trigger: same top-level `on:` block as every job in the file — `push: branches: [main]`
  and `pull_request: branches: [main]` (`ci.yml:3-7`). No `paths:` filter, so it runs on
  every push/PR to main regardless of which files changed.
- Python version: **3.12 only** (`ci.yml:104-107`), a single job, no matrix. Contrast with
  the `test` job, which runs a `fail-fast: false` matrix of `["3.11", "3.12"]`
  (`ci.yml:13-16`). So the gate itself is never verified to import cleanly on 3.11, only
  on the version the `test` job's 3.12 leg also uses.
- Invocation: `pip install -e .` then `python -m tools.drift_check --enforce`
  (`ci.yml:110-112, 128`). The **module form matters and is called out explicitly** in a
  comment (`ci.yml:92-96`): running it as `python tools/drift_check.py` instead puts
  `tools/` on `sys.path` instead of the repo root, breaking `from tools.openapi_parser
  import ...`. Measured and recorded in the comment: "script form exit 1, module form
  exit 0 / result: PASS, same tree, same venv."
- The job is **deliberately separate** from `test` (`ci.yml:68-72`, comment): bundling it
  in would let a flaky unit test mask a docs-drift failure and vice versa.
- **Until 2026-08-04 this job installed nothing** (`ci.yml:74-100`, comment) on the belief
  that the gate is dependency-free static analysis over `git ls-files`. That was false —
  check 15 imports the generator's own resolvers (reaching `tools/command_renderer.py`,
  which imports `wxcli` itself) and checks 15/16 `import yaml` — and the job crashed with
  `ModuleNotFoundError` **before check 1** for **11 days** while reporting a red build
  indistinguishable from a working gate that found problems. Both fixes (`pip install -e .`
  and the module-not-script invocation) are dated in the comment as verified in a clean venv.

### A2. The `set +e` / `pipefail` / exit-2 handling — exact quote and trace

`[verified]` `ci.yml:121-147`, step "Drift gate (enforcing)":

```yaml
run: |
  set -o pipefail
  # `set +e` is required, not stylistic: Actions runs this under
  # `bash -e`, so a non-zero gate would abort the step right here and
  # never reach the branches below — the crash annotation and the
  # completion assertions would silently never run.
  set +e
  python -m tools.drift_check --enforce 2>&1 | tee gate.log
  status=$?
  set -e
  if [ "$status" -eq 2 ]; then
    echo "::error::Drift gate CRASHED — it did not run. This is not a findings failure."
    exit 2
  fi
  # Assert on the LAST check, not on any check. Pin this to whatever
  # the highest-numbered check is; an assertion left on an earlier one
  # passes for a run that died after it, which is the exact blindness
  # the exit-2 work above exists to remove.
  if ! grep -q '^\[20\]' gate.log; then
    echo "::error::Drift gate stopped before check 20 — it did not run to completion."
    exit 2
  fi
  if ! grep -qE '^result: (PASS|FAIL)' gate.log; then
    echo "::error::Drift gate printed no verdict line — it did not run to completion."
    exit 2
  fi
  exit "$status"
```

**Why `set +e` is necessary, precisely:** GitHub Actions runs each `run:` block under
`bash -e` by default. Without `set +e`, a non-zero exit from `python -m tools.drift_check`
inside the pipeline would abort the *step* immediately at that line — the `status=$?`
capture, the exit-2 branch, the check-20 assertion, and the verdict-line assertion would
**never execute**. That would silently regress the whole point of this step: a crash would
just look like Actions' ordinary "command failed" red X with no distinguishing annotation.

**Why `pipefail` is necessary:** `python -m tools.drift_check --enforce 2>&1 | tee gate.log`
is a pipeline. Without `pipefail`, `$?` reflects `tee`'s exit code (almost always 0, since
`tee` itself succeeds at copying stdin to the file), not Python's — so `status` would be 0
even when drift_check exited 1 or 2. `pipefail` makes `$?` the rightmost non-zero exit in
the pipe, i.e. Python's real exit code, since `tee` always exits 0 here.

**What exactly makes the job fail vs pass** (drift_check.py's own contract, quoted from
`tools/drift_check.py:3871-3874`):
```
#   0 = ran, clean
#   1 = ran, found problems (with --enforce)
#   2 = DID NOT RUN — crashed before finishing
```
- `status == 2` → step prints a distinct `::error::...CRASHED...` annotation and exits 2.
  This is checked **first**, before the log-content assertions.
- `status != 2` but `gate.log` lacks a line matching `^\[20\]` → treated as "stopped before
  check 20", exits 2 with its own distinct annotation, **even if the raw exit code was 0 or
  1**. This is a second, independent detector of "did not finish" that does not trust the
  process exit code alone.
- `status != 2`, has `[20]`, but lacks a line matching `^result: (PASS|FAIL)` → same
  treatment, exits 2.
- Otherwise: `exit "$status"` — i.e. the job's real pass/fail is `status` itself: `0`
  (clean) or `1` (findings, `--enforce` fails the build).

**A residual gap in this design** `[inferred]`: the final branch trusts `status` as the
verdict without cross-checking that the *content* of the `result:` line agrees with it. If
a future bug in `drift_check.py` computed real findings, printed `result: FAIL` to
`gate.log`, but returned `0` from `main()` by mistake, this workflow would report the job
**green** — the two content assertions only check that *a* verdict line exists in the
`PASS|FAIL` alphabet, not that it matches `status`. This is a narrower, hypothetical version
of the exact bug class the exit-2 work was built to close, just one level down (inside
`main()`'s own return-value logic rather than at the import boundary).

### A3. Can the gate fail silently — crash, be skipped, or report success while not
having run? Every path traced

`[verified]` combining `ci.yml` + `tools/drift_check.py:3886-3899`:

1. **Crash before or during any check** (e.g. `ModuleNotFoundError`, any unhandled
   `Exception`): caught by the `try/except Exception` at `drift_check.py:3887-3899`
   (only active because the whole check runs under `if __name__ == "__main__":`, which
   both `python -m tools.drift_check` and `python tools/drift_check.py` satisfy). It
   prints a traceback, then `print("\nresult: CRASHED — the gate did not run to
   completion.")` **to stdout** (deliberately, per the comment at `:3892-3894`, so the
   crash is visible in the same log line every reader and the CI assertion already grep
   for), then `sys.exit(2)`. `KeyboardInterrupt`/`SystemExit` are `BaseException`, not
   `Exception`, so they propagate untouched (not swallowed by this handler).
   → ci.yml catches this at the `status -eq 2` branch. **Cannot fail silently**: two
   independent signals (exit 2, and the "CRASHED" text not matching `PASS|FAIL`) both
   flag it, though only the first is actually consulted since it returns early.
2. **Partial run that exits 0 or 1 anyway** (e.g., an early `return` bug that skips the
   later checks but still reaches the final `return 0/1` in `main()`): caught by the
   `grep -q '^\[20\]'` assertion. This is explicitly designed as **not** trusting the exit
   code — see the comment at `ci.yml:135-138`. Cannot fail silently, **unless** such a bug
   also fabricated a `[20]` line, which no current code path does.
3. **Runs to check 20 but never prints a verdict line** (bug in the final print
   statement): caught by the `result: (PASS|FAIL)` grep.
4. **Skipped entirely**: no `if:` condition gates the `drift-gate` job (`[verified]`,
   grepped the full file — zero `if:`/`continue-on-error:`/`timeout-minutes:` directives
   anywhere in `ci.yml` or `release.yml`), and the triggers have no `paths:` filter. So the
   job always runs on every push/PR to main; it cannot be skipped by the workflow's own
   logic. **What is out of scope of this trace** `[inferred, not verified]`: GitHub branch
   protection settings (whether `drift-gate` is a *required* status check) live in repo
   settings, not in these YAML files, so whether a failing/skipped run can still block a
   merge is `UNKNOWN` from the workflow files alone.
5. **Reports success while not having run, via exit-code/verdict-text mismatch**: see the
   residual gap in A2 — `UNKNOWN`/theoretical, not observed, but structurally possible
   because the final `exit "$status"` branch does not cross-check verdict text against
   exit code.

### A4. Does CI verify committed generated code matches what the generator produces?

**No — proven from the workflow files, not assumed.** `[verified]`

- `grep -n "generate_commands\|spec_sync"` across both `ci.yml` and `release.yml` returns
  **zero matches**. Neither `tools/generate_commands.py` nor `tools/spec_sync.py` (the
  orchestrator that "pulls specs, regens, updates the manifest, runs the drift gate" per
  `tools/CLAUDE.md`) is invoked anywhere in CI.
- The only regeneration step that *does* exist in CI is **`playbook-freshness`**
  (`ci.yml:149-174`) and **`release-integrity`**'s "Rebuild generated Claude and Codex
  playbook" step (`ci.yml:188-189`, `release.yml:22-29`). Both run
  `python wxcli-dist/assemble.py` and `git status --porcelain -- src/wxcli/_playbook` to
  fail on staleness. **This is a completely different artifact**: `src/wxcli/_playbook/`
  is the Claude+Codex playbook bundle assembled from `.claude/` + `docs/`
  (`ci.yml:152-155`), not the 178 command-group Python files under `src/wxcli/commands/`
  that the OpenAPI-spec generator produces.
- So there is **no regen-and-diff CI step** for `src/wxcli/commands/*.py` at all: nothing
  re-runs the generator against the tracked specs and `field_overrides.yaml` and diffs the
  result against the committed tree.
- **Nuance, not a contradiction**: `drift_check.py` itself performs deep *static* analysis
  that reads the **committed generated files directly** and cross-checks them against the
  specs (e.g. check 9's docstring, `tools/drift_check.py:1259-1261`: *"Reads the generated
  file, not the generator: what an operator sees is what this module renders, and check 9
  exists to prove those two agree"*). That catches many *symptoms* of generator/spec
  divergence (missing operations, wrong table columns, inert overrides, naming collisions)
  but is not the same guarantee as "regenerating from the current inputs reproduces the
  committed bytes." A hand-edit to a generated file that happens to still satisfy every
  static rule the gate checks (parity, column derivation, naming, positional counts, etc.)
  would pass `drift_check.py` cleanly despite violating the repo's own "never hand-edit
  generated files" rule (`tools/CLAUDE.md`, Generator Rules section) — nothing in CI
  detects that class of drift.
- Corollary directly relevant to Part B: **`check_verb_semantics`** — the function that
  hard-fails when a destructive operation's name/message doesn't reflect real semantics —
  lives **only** in `tools/generate_commands.py` (`generate_commands.py:201`, called at
  `:341`), **not** in `tools/drift_check.py` (`[verified]`: `grep -n
  "check_verb_semantics|verb_semantics_ack" tools/drift_check.py` returns one hit, a prose
  reference inside check 12's docstring at `:1968` describing it as a model to copy — the
  function itself is never imported or called). Since `generate_commands.py` never runs in
  CI (per this section), **the semantic-naming safety net for destructive commands is a
  generation-time-only guard that CI's drift gate never re-validates against the committed
  tree.** See Part B for the fuller implication.

### A5. What the `test` job runs, and what `-m "not live"` actually excludes

`[verified]` `ci.yml:48-63`: `pytest tests/ -m "not live" -v --tb=short`, with
`TERM=dumb` and `COLUMNS=400` set (the long comment at `:49-58` explains this is because
Rich special-cases GitHub Actions as colour-capable, breaking `--help`-output substring
assertions; `NO_COLOR=1` was measured to not fully suppress bold/dim ANSI codes).

**`-m "not live"` is a no-op — it excludes nothing.** `[verified]`, multiple ways:
- `pyproject.toml:80-82` registers the marker: `"live: requires live Webex API access
  (deselect with '-m not live')"`.
- `grep -rl "pytest.mark.live" tests/` → **zero files, exit code 1** (no match). Re-run
  directly to confirm: exit 1, no output.
- Broader `git grep -n "mark.live" -- '*.py'` over the **entire tracked tree** (not just
  `tests/`) → **zero matches**.
- The only files with "live" in their names are `tests/live_test_v2.py` and
  `tests/migration/cucm/validate_live_cucm.py` — **both are gitignored, not
  tracked** (`[verified]`: `git ls-files` on each returns nothing; `git check-ignore -v`
  confirms both match `.gitignore:53` (`tests/*`) and `.gitignore:111` respectively, an
  explicit named exclusion for the CUCM one). Both are standalone scripts run directly
  (`Usage: python3.11 tests/live_test_v2.py` / `python3.11
  tests/migration/cucm/validate_live_cucm.py`), not pytest modules — no `@pytest.mark`
  decorators, no `test_*` functions in the pytest-discovery sense, just a hand-rolled
  `PASS`/`FAIL` counter with `ok()`/`fail()` helpers.
- Since a fresh `actions/checkout@v4` only materializes **tracked** files, these two
  scripts don't even exist on the CI runner — they can't be collected by pytest whether or
  not `-m "not live"` is passed.

**What this means**: `pytest tests/ -m "not live"` runs the exact same test set as
`pytest tests/` would — the marker filter is dead weight. The comment "Run tests
(excluding live API tests)" (`ci.yml:48`) describes intent that nothing in the tracked
tree currently implements; either the marker was wired up once and its test(s) were later
deleted/gitignored, or it was declared aspirationally and never used. Either way, there is
currently no tracked, pytest-collected test anywhere in this repo that this marker would
ever deselect.

**What actually gets collected**, `[verified]` via `git ls-files tests/ | grep -c
"\.py$"` = **240** tracked test files, broken down as:
- **209** under `tests/migration/` (the CUCM migration subsystem's own suite)
- **8** under `tests/org_health/`
- **23** top-level `tests/test_*.py` files — and critically, `.gitignore:51-52` blanket-
  ignores `tests/*` and then explicitly negates (`!tests/...`) only these 23 files plus
  the two subdirectories above (`[verified]`, full listing at `.gitignore:53-92`). Reading
  the 23 negated names: the large majority are meta-tests about the tool's own tooling —
  `test_assemble.py`, `test_field_overrides.py`, `test_command_naming_residue.py`, nine
  `test_drift_check_*.py` files (columns/doc-shape/exit-codes/inert/naming/paging/
  positionals/references/registrations/semantics/untracked), `test_readme_distribution.py`,
  `test_release_integrity.py` — plus a handful guarding specific runtime behaviors
  (`test_errors_actionability.py`, `test_errors_id_kind.py`, `test_field_expansion.py`,
  `test_verify_flag.py`, `test_pagination_walkers.py`, `test_suggest_and_paging.py`,
  `test_wxcli_gate.py` — the last one guards the **separate** PreToolUse Bash-hook gate
  that stops the main Claude session from directly mutating a live org, not
  `drift_check.py`).
- **Net effect**: outside the CUCM migration and org-health subsystems, CI's pytest suite
  has essentially no committed unit-test coverage of ordinary command-group behavior
  (call queues, person settings, devices, routing, provisioning, etc.) — those tests, if
  they exist on a developer's machine, are gitignored by the blanket `tests/*` rule and
  never reach CI.

### A6. Test dependencies installed by hand, not declared in `pyproject.toml`

`[verified]` `pyproject.toml` has **no** `[project.optional-dependencies]` section at all
(confirmed by `grep -n "optional-dependencies" pyproject.toml` → no output) and no mention
of `pytest`, `pytest-asyncio`, or `aioresponses` anywhere in the file (`grep -n
"pytest|aioresponses|aiohttp" pyproject.toml` → only hit is the runtime dependency
`"aiohttp>=3.9"` at line 35).

Installed only in `ci.yml:26-46`, with extensive justifying comments:
```
pip install -e .
pip install pytest pytest-asyncio aioresponses
pip install 'aiohttp<3.14'
```
- **`pytest-asyncio`** — required because `pyproject.toml` sets `asyncio_mode = "auto"`
  and 7 test modules use `async def test_*`.
- **`aioresponses`** — required because 6 tracked migration/execute test modules import it
  to stub `aiohttp`.
- **`aiohttp<3.14`** pin — deliberately **not** in `pyproject.toml`'s runtime dependency
  (which stays `>=3.9` unbounded) because the break is in the *test double*, not the CLI:
  `aioresponses==0.7.9` hand-builds a `ClientResponse` without the `stream_writer` kwarg
  that `aiohttp>=3.14` made required, so every test stubbing `aiohttp` raises `TypeError`
  at request time. `aioresponses`'s own metadata (`aiohttp<4.0,>=3.8`) doesn't stop pip
  from resolving 3.14, so the pin has to live somewhere, and pinning it in `pyproject.toml`
  would incorrectly constrain end **users**' installs for a test-only defect.

**Why this matters for reproducibility** `[inferred from the above facts]`: `pip install -e
.` alone does not give a developer (or a differently-configured CI runner) a working test
environment — three packages and one version ceiling exist *only* as literal strings in
`ci.yml`. There is no `pip install -e ".[test]"` or `requirements-test.txt` a developer can
run to reproduce CI's test environment; the instructions are readable only by opening the
workflow YAML. A developer who already has `pytest`/`pytest-asyncio`/`aioresponses`
installed globally, on a newer `aiohttp`, sees local test failures CI does not have (or
vice versa) with no single source of truth for "what does CI actually install" other than
this file.

---

## PART B — STRUCTURAL BLIND SPOTS

### B1. Runtime behaviour — the gate never executes a command

**Mechanism** `[verified]`: `tools/drift_check.py` imports only `argparse, ast, datetime,
fnmatch, hashlib, json, re, shlex, subprocess, sys, pathlib` (`:214-224`). Its only two
`subprocess.run` call sites are `git ls-files ...` (`:250`) and `git check-ignore --stdin`
(`:269`) — pure git-metadata queries. There is no `httpx`/`requests` import, no invocation
of `wxcli` as a subprocess, and no `import wxcli.<command_module>` that calls a command
function. Every one of the 20 checks works by **static analysis**: `ast.parse`/`ast.walk`
over generated `.py` source, regex over doc/skill markdown, and `json.loads` over the
tracked OpenAPI specs. Check 9's own docstring states the design directly: it reads "the
generated file, not the generator" (`:1259-1261`) — and by the same logic, reads the file,
never runs it.

**Why this is structural, not incidental**: every one of the 20 checks is a *pure function
of committed text* (source files, spec JSON, markdown). None of them can observe what
happens when a byte actually goes over the wire to `webexapis.com` — a completely disjoint
observation channel from anything `ast`/regex/JSON-diffing can reach.

**Concrete example that slips through** `[verified example, already recorded in this repo's
own docs]`: the `--calling-data` interlock bug — `wxcli people list --fields
'[].extension' --all` returned `[]` on a live org with 15 users holding extensions, because
Webex omits `extension`/`locationId` from the response unless `--calling-data true` is
passed. The command exits 0, returns valid JSON, and silently answers "0" to "how many
users have extensions?" instead of 15. This is a *runtime response-shape* fact that no
static check over the generated `people.py` source or the OpenAPI spec's declared schema
could have caught — the spec doesn't declare that certain fields are conditionally omitted
from the wire response; only a live call revealed it (per root `CLAUDE.md`'s own account,
dated 2026-08-01). Nothing in `drift_check.py`'s 20 checks would flag this class of defect
even today, because none of them make a request.

### B2. The migration subsystem (`src/wxcli/migration/`, ~46-48k lines) — almost entirely
outside the gate

**Grepped directly, as instructed**: `grep -n "migration" tools/drift_check.py` returns
**12 lines** (`[verified]`), and every one of them is inside the doc-shape/prose-count
family of checks, not a check of migration *behavior*:

```
2556: "src/wxcli/migration/transform/engine.py",
2560:     ("src/wxcli/migration/transform/engine.py",
2562:     ("src/wxcli/migration/CLAUDE.md", r"Phase 05 — (\d+) mappers"),
2567: "src/wxcli/migration/transform/analysis_pipeline.py",
2571:     ("src/wxcli/migration/transform/analysis_pipeline.py",
2573:     ("src/wxcli/migration/CLAUDE.md", r"Phase 06 — (\d+) analyzers"),
2581: ("src/wxcli/migration/preflight/runner.py",
2583:     ("src/wxcli/migration/preflight/CLAUDE.md", r"## The (\d+) Checks"),
2584:     ("src/wxcli/migration/preflight/CLAUDE.md", r"\| (\d+) check functions"),
2585:     ("src/wxcli/migration/preflight/CLAUDE.md", r"run (\d+) checks as pure functions"),
2586:     ("src/wxcli/migration/preflight/CLAUDE.md", r"Phase 10 — checks\.py \((\d+) preflight checks\)"),
2587:     ("src/wxcli/migration/CLAUDE.md", r"checks\.py \((\d+) preflight checks\)"),
2615: path = REPO / "src/wxcli/migration/preflight/runner.py"
2952: # migration-spec-template.md" is one of ("migration/preflight/checks.py")
```

**What these actually check**: whether a *documented count* (e.g. "Phase 05 — N mappers",
"N preflight checks") in `migration/CLAUDE.md` / `migration/preflight/CLAUDE.md` matches
the number of functions/mappers found by counting definitions in exactly **3 files**
(`transform/engine.py`, `transform/analysis_pipeline.py`, `preflight/runner.py`) via regex/
count matching. This is a documentation-consistency check, not a correctness check —
it verifies "the docs say 12 mappers and there are 12 mapper functions," never "mapper #7
maps a CUCM field to the correct Webex field," never "the preflight checks actually catch
a bad CUCM config," never anything about `preflight/checks.py`'s logic, the transform
engine's actual output, or execution/rollback correctness.

**Nothing else in the ~46-48k line subsystem is touched by the static gate at all**
`[verified by exhaustive grep above]` — no check reads `migration/execute/`,
`migration/discover/`, `migration/normalize/`, `migration/map/`, `migration/analyze/`, or
any CUCM AXL/zeep interaction code. (Separately, `[verified]` `tests/migration/` *does*
carry 209 tracked pytest files that CI's `test` job runs — so the subsystem is not
completely unverified in CI, but that is pytest unit/integration coverage, a wholly
different mechanism from the static drift gate this audit is about. The gate itself is
blind to essentially the entire migration engine.)

**Concrete example that would slip through**: a CUCM-to-Webex field mapper that has a
logic bug — say it drops a call-forwarding number during transform — would not move any of
the 3 counted numbers (mapper count, analyzer count, preflight-check count) that the gate's
migration-adjacent checks look at. The gate would report `PASS` on a migration engine that
silently corrupts data, so long as the number of mapper/analyzer/check *functions* stays
unchanged from what the CLAUDE.md docs claim.

### B3. Semantic correctness of a spec that is internally consistent but wrong about the
live API

**Mechanism**: `drift_check.py` treats the tracked OpenAPI specs in `specs/*.json` as
ground truth for cross-checking the generated CLI. It has no independent oracle for
whether the **spec itself** is right about what the live API actually returns — nothing in
its 20 checks makes a network call to compare a spec's declared schema against a real
response body.

**Concrete example, already documented in this repo** `[verified via `tools/CLAUDE.md`'s
own "Two specs describe one endpoint differently" section]`: `GET /locations` — three
different pictures of the same endpoint:

| | `displayName` | `locationId` | `countryCode` | `name` | `address` |
|---|---|---|---|---|---|
| `webex-device.json` claims | yes | yes | yes | no | no |
| `webex-cloud-calling.json` claims | no | no | no | yes | no |
| **live response** | no | no | no | yes | yes (object) |

Before the `spec_authority` fix, the gate's check 9 **unioned** field names across both
specs, so the union told the gate the device spec's three invented columns were fine — the
gate reported `PASS`/clean while `locations.py` (the single most-run command in the tool,
since it produces IDs everything else needs) shipped three columns that always rendered
blank. Even now, with `spec_authority` pinning which spec is authoritative per operation,
the pin itself for 6 of 7 known conflicts is recorded with `basis: unverified` — i.e., a
human declared a spec "probably right" without confirming against the live API, and the
gate has no mechanism to independently prove or disprove that declaration; it can only
detect *new*, *undeclared* conflicts between specs on disk, not verify an existing
declaration is actually true.

A second, dated example from the same file: the 2026-08-03 refresh added a whole new
`selectiveCallRecordingSettings` capability (four independent record/don't-record toggles)
to person/virtual-line/workspace call-recording bodies. The gate reported `PASS` because it
only added **body fields**, not new operations — `openapi_parser.py` reads `op.get
("summary")` for the CLI's help text, never `op.get("description")`, and the constraint/
capability is only exposed today as raw `--generate-json-body` skeleton content, documented
nowhere. The spec is internally consistent (it's valid JSON declaring the field); nothing
about it is *wrong*; the gate is simply structurally unable to judge whether an addition
like this is complete, discoverable, or documented enough to be usable — that judgment (per
tools/CLAUDE.md's own check-19 write-up) was deliberately scoped to prose/structural tiers,
with meaning-level completeness left as a judgment call outside any automated check.

### B4. Confirmation gate / destructive guard — no check asserts it exists

**Grepped directly**: `grep -n "confirm\b" tools/drift_check.py` → **zero matches**
`[verified]`. `grep -n "typer.confirm|--force|destructiv|confirm" tools/drift_check.py`
returns exactly 2 lines, both **prose inside other checks' docstrings** describing
unrelated concerns (`:1464`, a comment about an unknown `--force`/`--debug` flag in a doc
example; `:2167`, a comment about a subagent incident with "four unconfirmed" deletes) —
neither is a check that inspects whether a generated command actually renders a
`typer.confirm(...)` call or a `--force` option.

**Where the real logic lives instead**: `_destructive_confirm_line` and `_emits_force_flag`
in `tools/command_renderer.py` (`:1772-1824`) — these are **rendering-time** functions that
decide what confirm/force code to emit into a generated file, not gate-time verifications
that a *committed* file has them. The actual safety-net **check**,
`check_verb_semantics` (which hard-fails when a destructive op's name/success-message don't
reflect its real semantics), lives in `tools/generate_commands.py:201`, called at `:341` —
**not** in `tools/drift_check.py`. Per A4 above, `generate_commands.py` is never invoked in
CI. So the one mechanism that verifies destructive-command safety (confirm prompts wired
correctly, naming/messaging matching real semantics) is a **generation-time-only** gate:
it runs when a maintainer manually regenerates locally, and CI's `--enforce` drift gate
never re-derives or re-checks it against the committed tree.

**Concrete example that would slip through**: if a generated command file were hand-edited
(against the repo's own "never hand-edit generated files" rule) to remove its `typer.
confirm(...)` call from a destructive `delete-*`/`update-*` command — while leaving the
function name, docstring, and success message untouched so every *other* static check
(naming, positional args, table columns, doc citations) still passes — `drift_check.py
--enforce` would report `PASS`. The command would delete a resource with no confirmation
prompt and no `--force` flag gating it, live in production, undetected by CI. (A **separate**
mechanism, the PreToolUse Bash hook + its test `tests/test_wxcli_gate.py`, stops the *main
agent session* from directly invoking mutating `wxcli` commands — but that is an
orthogonal safety net, evaluated in the `test` job, not something `drift_check.py` asserts
about the generated source itself.)

### B5. Gitignored files — what the gate (and CI) structurally cannot see

**The gate's own documented rule** `[verified]`, `tools/CLAUDE.md`, "The drift gate skips
*gitignored* modules, not merely untracked ones" section: `module_state()` classifies
command-module stems as `countable = (tracked | on_disk) - ignored` and `untracked =
on_disk - ignored - tracked`, using one batched `git check-ignore --stdin` call. This is a
**deliberate** design (so a developer's local dev-only `fs_*.py` Flow Store modules don't
inflate the published "178 command groups" count, per check 3), but it is also, by
construction, a blind spot: **anything gitignored is invisible to every one of the 20
checks**, not just the untracked-module check (check 8).

**What this hides, concretely, verified in this repo right now:**

1. **Almost the entire non-migration/non-org-health pytest suite.** `.gitignore:51-52`
   blanket-ignores `tests/*`, negating back in only 23 named files + `tests/migration/**` +
   `tests/org_health/**` (Part A5 above). Any unit test a developer writes locally for,
   say, `configure-features` or `manage-call-settings` behavior is invisible to `git
   ls-files`, never reaches a fresh CI checkout, and is invisible to `drift_check.py` too
   (it doesn't inspect `tests/` at all, but the same gitignore mechanism is why CI's `test`
   job can't run it either — a shared blind spot across both jobs).
2. **Two "live" test scripts** (`tests/live_test_v2.py`,
   `tests/migration/cucm/validate_live_cucm.py`) that exercise real write-cycles against a
   live Webex org / live CUCM testbed. Gitignored specifically because they'd carry lab
   host/credentials info if committed (`.gitignore:106-112` names the CUCM one alongside
   testbed provisioning/teardown scripts explicitly for that reason). Whatever bugs they'd
   catch are only caught when a developer remembers to run them by hand.
3. **The dev-only Flow Store CLI** (`src/wxcli/commands/fs_*.py`,
   `specs/webex-flow-store.json`, `.gitignore:143-145`) — explicitly excluded from the
   "178 command groups" count and from every drift check, by design, because it "regens
   auto-apply `--dev-only`" and never enters the manifest (`tools/CLAUDE.md`).
4. **`docs/prompts/`, `docs/plans/`, `docs/reports/`, `docs/team-prompts/`, `docs/archive/`,
   `docs/arch/`, `docs/references/` (note: plural — distinct from the tracked, singular
   `docs/reference/`, which check 20 reads and which has 44 tracked files)** — all
   gitignored (`.gitignore:33-47`). Any drift-relevant note living in one of these
   directories (e.g., an unfinished design plan describing intended CLI behavior) is
   invisible to the gate and to a fresh clone.

**Why this is structural, not just a policy choice**: `git check-ignore` and `git
ls-files` are the *only* oracle the gate has for "what exists" (per the untracked-modules
docstring, `:1123-1136`: *"A fresh clone still would not have the file"*). The gate's whole
premise is CI reproducibility from a clone — so it is correctly designed to treat
gitignored content as absent. The blind spot is the flip side of that correctness: a real
defect that lives only in a gitignored file (a broken local test, a stale local doc, a
dev-only command module with a bug) is **permanently outside what "the gate passed" can
mean**, by the same design that makes the gate trustworthy about what a fresh clone
actually ships.

**Concrete example that would slip through**: a developer patches a bug in a local (never-
committed) unit test for, say, `manage-call-settings`'s forwarding logic, sees it fail, and
either forgets to fix the underlying code or "fixes" the test instead of the bug — none of
this is visible to CI, to `drift_check.py`, or to any teammate reviewing a PR, because the
test file itself was never tracked to begin with (it isn't in the 23-file allowlist), so
there's no diff to review and no CI signal to contradict a confident "tests pass" claim in
a PR description.

---

## Summary (delivered separately in final message)
