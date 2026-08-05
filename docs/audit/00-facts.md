# 00 — Reconnaissance Facts

Produced by `docs/arch/wxops-recon-prompt.md`. Facts only. Every answer labeled
`[verified]` (I ran or parsed something) or `[inferred]` (reasoned from evidence
short of direct observation). No judgment — see *Deferred observations* at the end.

**Method note.** `wxcli` cannot be imported from Python in this repo: a hook blocks
it ("Importing wxcli from Python bypasses this gate, the read-only verb policy, and
the confirm prompt"). All structural counts below therefore come from `ast` parsing
of source, cross-checked where possible against `wxcli --help` subprocess output.
This is the same method `tools/drift_check.py` uses (`drift_check.py:75` CI comment).

---

## Framework and shape

**1. CLI framework and entry point.** `[verified]`

Typer, over Click. Console script `wxcli = "wxcli.main:app"` (`pyproject.toml:56`).
The root app is **not** `typer.Typer` — it is `LazyTyper` (`src/wxcli/main.py:15`),
defined at `src/wxcli/commands/_lazy.py`. `LazyTyper.__call__` is the real entry
point and never reads `registered_groups`; it builds a small Click group from the
root's own commands and merges in one `_LazyGroupProxy` per group, each resolving
its module only on real dispatch or on that group's `--help` (`_lazy.py:9-21`).
Anything reading `app.registered_groups` directly (typer's `CliRunner`, bare
`typer.main.get_command`) falls back to eager `mount_all()` (`_lazy.py:22-28`).

**2. Python floor, dependencies, packaging, published version.** `[verified]`

- Floor: `requires-python = ">=3.11"` (`pyproject.toml:9`). Classifiers list 3.11
  and 3.12 only (`pyproject.toml:50-51`).
- Packaging: setuptools + `setuptools-scm` (`pyproject.toml:2-4`); version is
  `dynamic` (`pyproject.toml:7`), written to `src/wxcli/_version.py` (`pyproject.toml:74`).
- 14 runtime dependencies (`pyproject.toml:23-47`): `typer>=0.20.0`, `click>=8.1`,
  `rich`, `httpx`, `jmespath`, `pyyaml`, `packaging`, `pydantic`, `aiohttp`,
  `networkx`, `phonenumbers`, `requests`, `urllib3`, `zeep`.
  The typer floor carries a 12-line comment recording live verification on
  2026-08-04 that every version 0.9.0–0.19.2 fails at least one of
  `--version` / `--help` / `people list --help` (`pyproject.toml:12-23`).
  **Four HTTP stacks are declared as dependencies** — `httpx`, `aiohttp`,
  `requests`, `urllib3` — plus `zeep` (SOAP) on top of `requests`.
- Distribution: PyPI. `PYPI_JSON_URL = "https://pypi.org/pypi/{PACKAGE}/json"`
  (`src/wxcli/update_check.py:29`), polled once a day from the root callback
  (`src/wxcli/main.py:38-40`).
- Latest tag `v1.4.6`; working tree reports `1.4.7.dev120+g2a89ea4ea.d20260804`
  (`wxcli --version`).

**3. LOC and split.** `[verified]` — `find | xargs wc -l`, excluding `src/wxcli/_playbook/`.

| Layer | LOC | Hand-written? |
|---|---:|---|
| `src/wxcli/commands/` (generated endpoint layer) | 87,585 | mostly no |
| `src/wxcli/migration/` (CUCM pipeline) | 46,684 | **yes, entirely** |
| `src/wxcli/org_health/` | 998 | yes |
| `src/wxcli/*.py` (shared runtime machinery) | **1,790** | yes |
| `tools/` (generator + gate) | 12,036 | yes |
| `tests/` | 80,043 | yes |
| **`src/wxcli` total** | **136,849** | |

Shared machinery, itemized: `auth.py` 407, `common.py` 263, `output.py` 227,
`errors.py` 225, `main.py` 208, `suggest.py` 148, `update_check.py` 145,
`config.py` 139, `_version.py` 24, `__init__.py` 4.

**The shape the audit assumed does not hold.** The split is not "generated
endpoints + shared machinery." It is three roughly independent bodies: a
generated endpoint layer (87.6k), a hand-written CUCM migration subsystem
(46.7k — 34% of `src/wxcli`), and 1,790 lines of shared runtime.

---

## Endpoint origin

**4. Generated, spec-driven, generator in-repo.** `[verified]`

Generated. Evidence, in order of strength:

- `src/wxcli/commands/_registry.py:1-7` — "Registration manifest for generated
  command groups. Emitted by tools/generate_commands.py — do NOT edit by hand."
- Generator: `tools/generate_commands.py` (588 lines), rendering via
  `tools/command_renderer.py` (2,091 lines, single entry `render_command_file`
  at `command_renderer.py:2030`), parsing via `tools/openapi_parser.py` and
  `tools/postman_parser.py`.
- Source of truth: 10 OpenAPI documents in `specs/`.
- Override seams: `tools/field_overrides.yaml` (`omit_query_params`, `skip_tags`,
  `tag_merge`, `cli_name_overrides` — `generate_commands.py:27`) and
  `specs/overlays/` via `tools/spec_overlay.py`.

**Not generated** (19 modules in `src/wxcli/commands/` absent from the registry):
`cleanup`, `configure`, `cucm`, `cucm_config`, `converged_recordings_export`,
`init_playbook`, `org_health_cli`, `update`, and the 11 `fs_*` modules.

**4a. The four counts.** `[verified]` — each with its method.

> **Corrected 2026-08-04 after an independent re-run.** Three errors below were
> found and are fixed in place; each is marked `[CORRECTED]` with what was wrong.
> The common cause: I counted what was on this disk instead of what is
> git-tracked, and this repo gitignores dev-only specs and modules.

| # | Quantity | Count | Method |
|---|---|---:|---|
| a | Operations in the source specs — **git-tracked corpus** | **2,053** | `json.load` each tracked `specs/*.json`, count GET/POST/PUT/PATCH/DELETE keys under `paths` |
| a′ | …including the untracked dev-only spec | 2,142 | same, over all 10 files on disk |
| b | Commands exposed by the CLI | **1,887** | `ast` walk of registered modules, counting `@app.command` decorators |
| c1 | Generated command modules | **173** | `len(GENERATED_GROUPS)`, `_registry.py` |
| c2 | Hand-written mounted modules | **5** | `len(HAND_WRITTEN_GROUPS)`, `_lazy.py:52-58` |
| d | Top-level names at runtime | **197** | `wxcli --help`, count entries under `Commands:` |

Per-spec operation counts (a): `webex-cloud-calling.json` 1087,
`webex-contact-center.json` 448, `webex-meetings.json` 168, `webex-admin.json` 148,
`webex-device.json` 101, `webex-messaging.json` 63, `webex-broadworks.json` 19,
`webex-wholesale.json` 18, `webex-ucm.json` 1 — **nine tracked specs, 2,053 operations.**

**`[CORRECTED]`** A tenth file, `specs/webex-flow-store.json` (89 operations), is
on disk but **gitignored** (`.gitignore:144`, confirmed via `git check-ignore -v`).
`git ls-files specs/` returns nine spec documents plus one overlay. My original
figure of 2,142 silently included a dev-only spec that does not ship.

**154 of the tracked operations are deliberately skipped** — no CLI command, on
purpose, per `skip_tags` in `tools/field_overrides.yaml`. They are enumerated in
`docs/arch/deliberate-gaps.md:8` ("154 skipped operations across 26 spec/tag
pairs"), a file emitted by `tools/drift_check.py --write-gaps` whose header states
the invariant: *"Anything missing from the CLI and not listed here is drift
(drift-gate check 1)."* I missed this file in the original pass despite reading
two other files in the same directory.

Command split (b): **1,857 from the 173 generated modules; 30 from the 5
hand-written ones.**

The 197 runtime top-level names (d) decompose exactly:
173 generated groups + 5 hand-written groups + 3 aliases (`_lazy.py` `ALIASES`)
+ 11 `fs_*` groups (`_lazy.py:68-80` `FS_DEV_GROUPS`) + 5 bare root commands
(`whoami`, `switch-org`, `clear-org`, `set-cc-region`, `init`) = 197.

**`[CORRECTED]` — 197 is this machine's number, not the product's.** The 11 `fs_*`
groups are gitignored (`.gitignore:145`) and mounted purely on file existence
(`_lazy.py:250-251`), so **a fresh clone or the published wheel exposes 186
top-level names.** Any audit statement about what the operator can see must use
186; 197 describes only this working tree.

**Reconciliation with the ~2,000 figure:** a raw `grep -c "@app.command"` over
`src/wxcli/commands/*.py` returns **2,010**, because it sweeps in the 11 `fs_*`
dev modules and the unmounted `cucm_config` / `converged_recordings_export` /
`init_playbook`. 1,887 is the count reachable through a mounted group.

**`[CORRECTED]` — 51 commands are hidden from `--help` but remain dispatchable.**
`grep -c "hidden=True" src/wxcli/commands/*.py`: **50 across 30 generated modules**
(concentrated in `my_call_settings.py` 8, `announcements.py` 4, `dect_devices.py` 4,
`ai_receptionist.py` 3) plus **1 in the hand-written `update.py`**. I missed these
entirely in the original pass.

**This is a material omission for the audit, not a rounding error.** The audit's
premise is that help text is the only specification the operating LLM reads. Fifty
commands that dispatch but never appear in `--help` are, by that premise,
undiscoverable to the operator — and any Phase 3 enumeration built from `--help`
output alone will silently omit them. An enumeration must walk the command tree,
not parse help.

**5. Canonical registry: yes.** `[verified]`

`src/wxcli/commands/_registry.py` holds `GENERATED_GROUPS`, a flat list of
`(module, group)` tuples — the single source of truth for the generated side,
emitted by the generator and parsed (not exec'd) by the gate's
`parse_registrations()` (`_lazy.py:28-31`). Hand-written seams, aliases, and the
`fs_*` block are declared as sibling data structures in `_lazy.py`, deliberately
as literals so the gate can `ast`-parse them too (`_lazy.py:429-432`).
All 173 registry entries have a file on disk; no file-side orphans among them.

---

## Existing coherence enforcement

**5a. A gate exists and is blocking in CI.** `[verified]`

`tools/drift_check.py` — **3,899 lines**. Named check functions found by grep:
`check_parity` (check 1, `:607`), `check_references` (`:783`), `check_counts`
(`:905`), `check_unreferenced` (`:959`), `check_overlays` (`:969`), `check_flags`
(`:1044`), `check_prose_flags` (`:1090`), `check_untracked_modules` (`:1123`),
`check_table_columns` (`:1302`), `check_required_flags` (`:1582`),
`check_positionals` (`:1678`), `check_arg_kinds` (`:1829`), `check_naming`
(`:1952`), `check_generated_help` (`:2337`), `check_registry_counts` (`:2630`),
`check_inert_overrides` (`:2681`), `check_undeclared_paging` (`:2849`),
`check_reference_doc_shape` (`:3010`), `check_spec_semantics` (`:3415`),
`check_reference_doc_coverage` (`:3490`). Numbered references in comments run to
**check 20**, including sub-numbered `11a`/`11b`.

CI: a dedicated job `drift-gate` (`.github/workflows/ci.yml:65`), deliberately
separate from `test` so "a flaky unit test [cannot] mask a docs-drift failure and
vice versa" (`ci.yml:71-73`). Invocation: `python -m tools.drift_check --enforce`
(`ci.yml:128`), run under `set +e` with `pipefail`, treating exit 2 as *crashed,
did not run* rather than *found nothing* (`ci.yml:129-133`), and asserting on the
last check having completed.

**I did not determine whether any check compares regenerated output byte-for-byte
against committed output.** That is Phase 2's job. `[inferred]` from names only:
the battery appears oriented to spec↔CLI↔docs coherence (parity, flags,
positionals, naming, doc shape and coverage), not to output-byte identity.

**5b. The flag surface is computed in-process, not committed.** `[verified]`

`build_flag_surface()` at `drift_check.py:554`, consumed by `check_flags`
(`:1044`) and `check_prose_flags` (`:1090`), and built fresh on each run
(`:3566-3568`). A positional counterpart "mirrors build_flag_surface, adding the
positional side" (`:1449`).

**No committed flag-surface artifact exists anywhere in the repo.**
`find . -name "*surface*"` (excluding `venv/`, `.git/`) returns nothing. The only
committed artifacts under `tools/` are `drift_check_allowlist.txt`,
`field_overrides.yaml`, and `spec_semantics.json`.

**5c. `tools/spec_semantics.json` — what it actually encodes.** `[verified]`

Its own header (`spec_semantics.json:2`): *"Drift gate check 19. Regenerate with
`python -m tools.drift_check --refresh-spec-snapshot`; never hand-edit."*
Captured 2026-08-04.

Per-operation encoding, quoting the header's field key verbatim:
`!` required · `~name`/`~id` the kind its description states · `#` hash of the
description · `%` hash of the rules stated in it · `=` enum values. Each entry
also carries `summary` and `tag`. Example (`DELETE /authorizations`):
`"query:clientId": "!#146aad"`, `"query:orgId": "~id#912bb1"`.

**Every encoded field is shape or change-detection. None expresses consequence.**
There is no destructiveness, scope, reversibility, idempotency, or rate-limit-class
dimension. The file detects *"the meaning of this parameter changed upstream"*;
it cannot tell the generator *"this operation destroys things."*

---

## Systems touched

**6. Two external systems, plus local file mutation.** `[verified]`

- **Webex REST API** — `src/wxcli/auth.py`, class `WebexApi` (`auth.py:370`),
  `rest_get`/`put`/`post`/`patch`/`delete` (`auth.py:272-288`), over `httpx`.
- **CUCM via AXL/SOAP** — `src/wxcli/migration/cucm/connection.py:22-24`,
  `from zeep import Client, Settings` / `zeep.helpers.serialize_object` /
  `zeep.transports.Transport`. This is the only `zeep` usage in `src/`.
- **Local file mutation** — `wxcli init` materializes the bundled playbook into
  the user's folder (`src/wxcli/commands/init_playbook.py`); `wxcli update`
  rewrites `.claude/` and `.codex/` playbook trees, keyed off
  `.claude/.wxops-manifest.json` (`src/wxcli/commands/update.py:158-167`).

No Unity, no Expressway, no other on-prem client found in `src/`.

**7. The two paths do not share auth, retry, or error semantics.** `[verified]`

`src/wxcli/migration/` contains **exactly one** import from the shared runtime:
`from wxcli.auth import get_api` at `src/wxcli/migration/preflight/runner.py:312`.
Across 46,684 lines, that is the entire reuse of `wxcli.auth` and `wxcli.errors`.

- **Webex REST path:** `httpx`, synchronous. `RETRY_STATUSES = frozenset({429,
  500, 502, 503, 504})` (`auth.py:160`); "Retry-After honored on 429, exponential
  backoff otherwise, + one [connect retry]" (`auth.py:224`); connect-error retry
  at `auth.py:242`. Three pagination walkers, all in `auth.py`: `Link: rel="next"`
  (`auth.py:97-100`, `:308`), Contact Center `page`/`pageSize` (`auth.py:314`),
  SCIM `startIndex`/`count` (`auth.py:344`). Tunable via `WXCLI_MAX_ATTEMPTS`,
  `WXCLI_RETRY_MODE`, `WXCLI_NO_RETRY`, `WXCLI_MAX_PAGES`.
- **Migration execute path:** `aiohttp`, asynchronous
  (`src/wxcli/migration/execute/handlers.py`, `execute/engine.py`), with its own
  `src/wxcli/migration/rate_limiter.py` — an independent `RateLimitConfig`
  (`max_concurrent=5`, `base_delay=1.0`, `max_delay=60.0`, `backoff_factor=2.0`,
  `max_retries=5`) whose docstring cites the migration design docs, not `auth.py`.
- **CUCM AXL path:** `zeep` over `requests`, with its own connection module.

Whether the two Webex-facing retry policies actually agree on edge cases is
**not established here** — I compared their declarations, not their behavior.

---

## Migration and destructive surface

**8. Org-wide and migration-scale commands.** `[verified]` for the inventory,
`[inferred]` for the scope-defaulting judgment, which I did not test per-command.

- `wxcli cleanup` (`src/wxcli/commands/cleanup.py`) — the bulk-deletion engine;
  13-layer deletion order per `.claude/rules/cleanup.md`. Contains the only four
  `rest_delete` call sites in the codebase with no adjacent confirm (see Q10).
- `wxcli cucm` (`src/wxcli/commands/cucm.py`) — the full discover → normalize →
  map → analyze → plan → execute → export pipeline.
- `wxcli update` (`src/wxcli/commands/update.py`) — rewrites playbook files in
  the user's working folder.
- 179 tracked `DELETE` commands, plus 779 tracked POST/PUT/PATCH commands that mutate without any confirmation (Q10).

Scope: **`orgId` is auto-injected from config on endpoints that accept it**, per
`CLAUDE.md`'s generator note (`auto_inject_from_config`) and
`src/wxcli/config.py` `get_org_id`. Every generated command file imports
`get_org_id` (visible in the standard header, e.g. `src/wxcli/commands/people.py:9`).
So target org is ambient state, not a required argument, on the generated surface.

**9. Irreversible on the remote side.** `[inferred]` — from HTTP verb and Webex
semantics, not from a documented reversibility field, because none exists (Q5c).

Every `DELETE`-backed command (**179** tracked commands — see the correction in
Q10). No soft-delete, undo, or trash surface
appears in the CLI. `archive_users` is a *read* group (lookup of already-deleted
users, per `CLAUDE.md`), not an undo path. CUCM-side reads are non-mutating; the
migration's Webex-side writes are ordinary creates and updates.

**10. Confirmation, dry-run, and pre-flight all exist — unevenly.** `[verified]`

**`[CORRECTED]` — my original framing here was the most consequential error in
this document.** I measured `rest_delete` against confirmations and reported
"185 of 189 gated," concluding guards were present and near-universal. Two
things were wrong: the denominator counted *functions* in untracked files, not
*commands*; and, far more importantly, **I never asked what fraction of
_mutating_ commands are gated — only what fraction of _deletes_ are.**

*Confirmation.* Re-measured over git-tracked `src/wxcli/commands/`, counting
only `@app.command`-decorated functions:

| | count |
|---|---:|
| Commands issuing a mutating HTTP call (POST/PUT/PATCH/DELETE) | **958** |
| — `DELETE` commands | 179 |
| — `DELETE` commands with a confirm gate | **179 (100%)** |
| — `DELETE` commands with `--force` to bypass it | **179 (100%)** |
| — write-but-not-delete (POST/PUT/PATCH) | **779** |
| — of those, with any confirm gate | **0** |

So the gate is not "near-universal with 4 gaps." It is **total within `DELETE`
and absent everywhere else.** The generator keys destructiveness on the HTTP
verb, so a PUT that overwrites a working configuration, reassigns a number, or
blanks a schedule prompts for nothing. My earlier count of 189 included the 4
non-command helpers inside `cleanup.py` plus deletes in the gitignored `fs_*`
modules.

Note also that the gate and its bypass are emitted together: 100% gate coverage
is simultaneously 100% `--force` coverage.

**`wxcli cucm execute` — the migration executor — has no gate at all.**
`[verified]` by running `--help`: the only options are `-p/--project` and
`-c/--concurrency` (**default 20**). No confirm, no `--force`, no `--yes`, no
`--dry-run` on the command. `wxcli cucm retry-failed` is likewise ungated. The
dry-run is a *separate* command (`wxcli cucm dry-run`) that the help text advises
running first and that nothing enforces. **The CLI prompts before deleting one
room and does not prompt before applying an entire migration plan concurrently.**

The gate is generated and uniform. From `src/wxcli/commands/locations.py:202-210`:

```python
force: bool = typer.Option(False, "--force", help="Skip confirmation"),
...
if not force:
    typer.confirm(f"Delete {location_id}?", abort=True)
```

**`--force` exists on all 179 gated commands** (`"--yes"` on 4 more), help text
"Skip confirmation". The confirm string interpolates the raw ID only.

*Dry-run.* Present in exactly four files: `commands/cucm.py`, `commands/cleanup.py`,
`migration/execute/runtime.py`, `migration/preflight/runner.py`. **No generated
command has a dry-run.**

*Pre-flight.* `src/wxcli/migration/preflight/` — a distinct pass, migration-only.

*Read-back verification.* `--verify` on 328 update commands per `CLAUDE.md`
(claim not independently counted here).

---

## Failure handling

**11. Idempotency, per-command.** `[inferred]`, and thin — I did not execute any
mutating command.

No conditional-request machinery exists in the shared layer: grep for ETag /
If-Match returns nothing in `src/wxcli/auth.py`. Generated `create` commands issue
a bare POST with no natural-key check-then-act, so a re-run after partial success
produces duplicates or a remote 409 depending on the endpoint's own constraints.
`DELETE` is idempotent at the HTTP level (second call 404s). The migration engine
has explicit state (`migration/state.py`, `migration/store.py`,
`migration/decision_state.py`) and a `__stale__` sentinel convention, which is the
only resumability substrate in the repo. **Per-command answers for the Q8 list are
not established.**

**12. Position reporting and resume.** `[verified]` for the split.

Generated commands: none — each is a single request; there is no bulk loop to
report position within. `cleanup` and the migration `execute` engine carry state
(`migration/state.py`, `migration/store.py`) and a `--dry-run`; whether either
emits a resume token I did not confirm.

**13. Error structure and exit codes.** `[verified]`

`src/wxcli/errors.py`, 225 lines. `WebexError(Exception)` carries
`(message, status_code, body)` (`errors.py:17`). `handle_rest_error` (`:169`)
and `handle_network_error` (`:215`) both terminate with **`raise typer.Exit(1)`**
(`errors.py:203`, `errors.py:225`).

The module contains real actionability machinery: `_extract_error_code` (`:63`),
`_truncate_html` (`:76`), `decode_id_kind` (`:90`), `_passed_id_kinds` (`:125`),
`_id_kind_tip` (`:135`), `_invoked_group` (`:145`), `_is_cc_403` (`:157`) — i.e.
it decodes the base64 Spark ID kinds actually passed and tips when they mismatch.

Exit codes across `src/wxcli`: `typer.Exit(0)` × 725, `typer.Exit(1)` × 270,
`typer.Exit(2)` × 5, bare `typer.Exit()` × 1.
**Validation, transient, and remote-rejection failures are not distinguishable by
exit code** — remote errors and network errors both exit 1; Click supplies 2 for
parse errors. Output is prose to stderr with tips, not structured/machine-parseable.
Two tests target this surface: `tests/test_errors_actionability.py`,
`tests/test_errors_id_kind.py`.

**14. Invocation logging: none.** `[verified]`

`logging` is used in exactly one module: `src/wxcli/auth.py:6,23`
(`logger = logging.getLogger("wxcli")`), emitting two `logger.warning` calls on
retry (`auth.py:242`, `:256`), plus `logging.basicConfig(level=DEBUG)` behind a
debug flag (`auth.py:392-393`). No handler, no file, no JSONL, no argv capture,
no exit-code capture. Grep for `.log` / `jsonl` in `auth.py`, `main.py`,
`common.py` returns nothing.

The 11 `WXCLI_*` environment variables are all behavioral, none observational:
`CONNECT_TIMEOUT`, `MAX_ATTEMPTS`, `MAX_PAGES`, `NO_PAGE_WARN`, `NO_RETRY`,
`NO_UPDATE_CHECK`, `PLAIN`, `PLAN_FAIL_ON_UNRESOLVED`, `READ_TIMEOUT`,
`RETRY_MODE`, `UPDATE_INDEX_URL`.

**Phase 1 of the audit prompt has nothing to build on top of. It is greenfield.**

---

## Tests and history

**15. Tests.** `[verified]` for inventory; coverage of shared machinery **not measured**.

244 test files, 80,043 lines. **214 of the 244 are under `tests/migration/`** —
the hand-written CUCM subsystem is where the test mass sits.

Top-level suites bearing on the shared layer and the gate: `test_auth.py`,
`test_common.py`, `test_config.py`, `test_config_org.py`, `test_cleanup.py`,
`test_cli_smoke.py`, `test_command_renderer.py`, `test_command_naming_residue.py`,
`test_errors_actionability.py`, `test_errors_id_kind.py`, `test_field_expansion.py`,
`test_assemble.py`, `test_release_integrity.py`, and eleven `test_drift_check_*.py`
files (columns, doc_shape, exit_codes, inert, naming, paging, positionals,
references, registrations, semantics, untracked).

**Recorded remote responses exist for AXL only** — `tests/fixtures/axl-responses/`.
The other fixtures are `mini-openapi.json` (a generator input) and
`expected_output.py`. **No recorded Webex REST responses.**
`grep -l "pytest.mark.live"` returns **0 files**, though `pytest -m "not live"` is
what CI runs (`ci.yml:63`) and `tests/live_test_v2.py` exists outside the marker system.

I did not run coverage. `.coverage` exists at repo root, dated 2026-03-23 — over
four months stale.

**16. History: 1,038 commits, and churn is not usable as a proxy.** `[verified]`

Authors: Adam Hobgood 1,022, "Claude" 15, achobgood 1.
By month: 2026-03 290, 2026-04 487, 2026-05 30, 2026-06 10, 2026-07 206, 2026-08 15.

**Yes, large portions were committed in bulk machine-generated batches**, and the
prompt's caution is warranted, but the mechanism is spec regeneration rather than
LLM authorship of individual commits. Direct evidence in recent history:
`2a89ea4 chore(specs): regen from the 2026-08-03 refresh…`,
`a898c76 chore(specs): update OpenAPI specs from upstream (2026-08-03)`,
`b578a52 chore(repo): 2,330 dependency files sat one 'git add .' from the repo`.
Commit messages are hand-curated and unusually specific
(`820fe8b test(gate): the read-verb invariant was inspecting 86 of 1961 commands`),
so message quality is **not** a signal that the diff was small or hand-made.

`tools/` has 134 commits of its own — that subtree *is* a valid churn target.

---

## Distribution

**17. Who installs this.** `[verified]` for the mechanism, `UNKNOWN` for the audience.

Published to PyPI as `wxcli`; the root callback polls
`https://pypi.org/pypi/wxcli/json` once a day and nudges on a newer version
(`update_check.py:29,78`; `main.py:38-40`). `wxcli update` self-upgrades and
refreshes an installed playbook, gated on `.claude/.wxops-manifest.json` /
`.codex/.wxops-manifest.json` (`update.py:158-167`), prompting *"This folder holds
a wxops playbook. Refresh it to v{latest}?"* (`update.py:167`).

**No download counts, telemetry, issue history, or user list is observable from
the repo.** Whether the operating LLM is only Adam's or also downstream users' is
`UNKNOWN` — and unanswerable from here, because Q14 established there is no
telemetry of any kind.

**18. Committed public contract.** `[verified]`

Everything a caller can bind to is committed and unversioned-as-contract:
1,887 command names across 197 top-level names; every flag and positional; the
`--fields` / `--output` / `--json-body` / `--all` / `--verify` conventions;
`--force` on 179 commands; exit codes 0/1/2; `table|json|text|id` output shapes;
and the 11 `WXCLI_*` environment variables.

**Nothing is documented as unstable.** `grep -n "unstable|experimental|breaking
change|deprecat" README.md` returns **zero matches**. No SemVer policy, no
stability tiers, no deprecation-window statement was found in `README.md`.
The one deprecation actually in flight is recorded only in `CLAUDE.md` prose
(`licenses-api` as "a deprecated one-release alias for `licenses`").

---

## Counts table

| Quantity | Value | How measured |
|---|---:|---|
| Spec operations, git-tracked (9 docs) | 2,053 | `json.load` + count HTTP-verb keys, over `git ls-files specs/*.json` |
| — of those, deliberately skipped | 154 | `docs/arch/deliberate-gaps.md:8`, emitted by `drift_check.py --write-gaps` |
| Spec operations incl. untracked dev spec | 2,142 | same, all 10 files on disk (`webex-flow-store.json` is gitignored) |
| Commands `hidden=True` (dispatchable, not in `--help`) | 51 | `grep -c "hidden=True" src/wxcli/commands/*.py` — 50 generated + 1 in `update.py` |
| CLI commands reachable via a mounted group | 1,887 | `ast` walk for `@app.command` over registered modules |
| — from generated modules | 1,857 | same, restricted to `GENERATED_GROUPS` |
| — from hand-written modules | 30 | same, restricted to `HAND_WRITTEN_GROUPS` |
| Raw `@app.command` count in `commands/*.py` | 2,010 | `grep -h "@app.command" \| wc -l` (includes unmounted/dev) |
| Generated command modules | 173 | `len(GENERATED_GROUPS)`, `_registry.py` |
| Hand-written mounted modules | 5 | `_lazy.py:52-58` |
| Aliases | 3 | `_lazy.py` `ALIASES` |
| `fs_*` dev modules | 11 | `_lazy.py:68-80` |
| Non-registry `.py` files in `commands/` | 19 | set difference, disk vs registry |
| Top-level names at runtime | 197 | `wxcli --help` |
| Mutating commands, tracked (POST/PUT/PATCH/DELETE) | 958 | `ast` scan of `@app.command` fns over `git ls-files` |
| — `DELETE` commands | 179 | same |
| — `DELETE` with confirm gate | 179 (100%) | same |
| — write-not-delete (POST/PUT/PATCH) | 779 | set difference |
| — write-not-delete with confirm gate | 0 | same |
| Mutating commands with a dry-run | 2 of 958 | `cleanup run`, `cucm preflight` |
| Drift-gate checks (highest numbered) | 20 | comment numbering in `drift_check.py` |
| `drift_check.py` LOC | 3,899 | `wc -l` |
| Test files | 244 | `find tests -name "test_*.py"` |
| — under `tests/migration/` | 214 | `find tests/migration -name "*.py"` |
| Commits | 1,038 | `git log --oneline \| wc -l` |
| — touching `tools/` | 134 | `git log -- tools/ \| wc -l` |

---

## Corrections to repo prose

| Claim | Where | Measured |
|---|---|---|
| "178 generated command-group modules (plus 5 hand-written ones, 3 aliases…)" | `src/wxcli/commands/_lazy.py:3-5` | **173** generated + 5 hand-written = 178 *total*. The docstring's 178 is the total, mislabeled as the generated count; taken literally it implies 183 groups. |
| "178 command groups covering calling, admin, device, messaging, meetings, wholesale, and contact center APIs" | `CLAUDE.md`, *CLI Status & Known Issues* | **Correct** as a total (173 + 5). Does not mention the 3 aliases, the 11 `fs-*` groups, or the 5 bare root commands that also appear in `wxcli --help` — 197 names are visible, not 178. |
| "The wxcli CLI has 178 command groups" | `CLAUDE.md`, opening *Execution pattern* | Same as above. |
| "`--verify` — on **328 update commands**" | `CLAUDE.md` | Not independently verified in this pass. |
| "2535 tests passing" | `docs/CLAUDE.md`, *Key Entry Points* | Not verified — no suite was run (project rule forbids full-suite runs). 244 test *files* exist. |
| ~~11 `fs-*` groups are absent from `CLAUDE.md`~~ | ~~`CLAUDE.md`~~ | **`[CORRECTED]` — this was my error, not the repo's.** `src/wxcli/commands/fs_*.py` is gitignored (`.gitignore:145`, confirmed via `git check-ignore -v`). The 11 `fs-*` groups exist only in this working tree; they are not tracked, do not ship in the wheel, and are mounted purely on file existence (`_lazy.py:250-251`). `CLAUDE.md` is correct to omit them, and the drift gate is correct not to demand a scope declaration. **Retracted.** |

---

## Assumptions I could not confirm

1. **Whether regeneration is deterministic.** I did not run the generator. Byte-identity across two runs is unknown.
2. **Whether the drift gate detects a hand-edit to generated code.** I read check *names*, not check *bodies*. The gate may or may not compare regenerated output to committed output.
3. **What `tools/drift_check_allowlist.txt` currently suppresses,** and whether entries are deliberate exemptions or quieted findings. Not opened.
4. **Per-command idempotency** for the Q8 list. Inferred from the absence of ETag/If-Match machinery, not tested.
5. **Whether `auth.py`'s retry policy and `migration/rate_limiter.py`'s agree behaviorally.** I compared declared parameters only.
6. **Real coverage of the 1,790-line shared machinery.** `.coverage` is from 2026-03-23; I did not re-run it.
7. ~~**Whether the 11 `fs_*` modules ship in the published wheel.**~~ **RESOLVED: they do not.** `src/wxcli/commands/fs_*.py` is gitignored (`.gitignore:145`). They exist only in this working tree. Same for `specs/webex-flow-store.json` (`.gitignore:144`). **I flagged this as unconfirmed and then wrote a finding that assumed the opposite — the assumption should have blocked the finding.**
8. **Who downstream users are, if any.** Unanswerable from the repo.
9. **The `--verify` count (328) and the test count (2535)** stated in `CLAUDE.md`.

---

## Deferred observations

- The endpoint layer is 87.6k LOC of generated code; the shared runtime it sits on is 1,790 LOC.
- `src/wxcli/migration/` is 46.7k hand-written LOC — 34% of `src/wxcli` — and imports the shared runtime exactly once, at `preflight/runner.py:312`.
- Four HTTP client libraries are declared dependencies: `httpx`, `aiohttp`, `requests`, `urllib3`.
- Two independent retry/backoff policies exist for Webex-facing traffic (`auth.py:160,224` and `migration/rate_limiter.py`).
- All 179 `DELETE` commands carry a generated confirm gate; all 779 other mutating commands carry none. The generator keys destructiveness on the HTTP verb alone.
- `--force` ("Skip confirmation") is emitted alongside every gate, so 100% gate coverage is also 100% bypass coverage.
- `wxcli cucm execute` applies a whole migration plan concurrently (default 20) with no confirm, no `--force`, and no `--dry-run` on the command.
- The generated confirm prompt interpolates only a raw opaque ID: `Delete {location_id}?`.
- No generated command has a dry-run; only `cucm`, `cleanup`, and the migration engine do.
- `orgId` is injected from ambient config rather than being a required argument on the generated surface.
- Remote-rejection and network failures both exit 1; validation exits 2 only because Click does it.
- No structured error output anywhere; errors are prose on stderr.
- Zero invocation logging: no argv, no exit code, no duration, no failure layer.
- `tools/spec_semantics.json` encodes requiredness, id-kind, description hashes, and enums — no consequence dimension.
- No committed flag-surface artifact; the surface is rebuilt in-process on both sides of the gate's comparison.
- The drift gate is 3,899 lines with 20 checks; `tools/drift_check_allowlist.txt` exists and was not read.
- Recorded remote responses exist for AXL only; none for Webex REST.
- 214 of 244 test files cover the migration subsystem.
- `grep -l "pytest.mark.live"` returns zero files, yet CI runs `pytest -m "not live"`.
- `.coverage` at repo root is dated 2026-03-23.
- 51 commands are `hidden=True` — dispatchable, absent from `--help`. Any enumeration built by parsing help output will miss them.
- 154 tracked spec operations are deliberately skipped, enumerated in the generated `docs/arch/deliberate-gaps.md`; that file is itself gitignored along with all of `docs/arch/`.
- The 11 `fs-*` groups and `specs/webex-flow-store.json` are gitignored dev-only artifacts present on this machine and absent from the shipped package — a fresh clone sees 186 top-level names, not 197.
- `README.md` contains no stability, SemVer, or deprecation policy for a published CLI whose entire surface is a public contract.
- `_lazy.py:3` states 178 generated modules; the registry holds 173.
