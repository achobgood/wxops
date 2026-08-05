# wxops Reconnaissance — Ground Truth (independent run)

Produced by following `docs/arch/wxops-recon-prompt.md`. Facts only; judgment is
deferred to the list at the bottom.

**Repo state at time of measurement:** branch `main`, `HEAD = b578a52`,
`git describe --tags` = `v1.4.6-123-gb578a52`, working tree has 3 untracked
files at root. Measured 2026-08-04.

**Method conventions used throughout.**
- `wxcli` on PATH is `/opt/homebrew/bin/wxcli`; its site-packages entry is
  `__editable__.wxcli-1.3.1.dev20+gfde30d754.d20260714.pth`, whose contents are
  the single line `/Users/ahobgood/Documents/webexCalling/src`. So every
  `wxcli --help` below executes **this repo's source**. `[verified]`
- All `--help` runs used `env COLUMNS=400 TERM=dumb wxcli --no-update-check …`.
  Click caps help at `max_content_width=80`, so output still wrapped at 78
  columns; the parser below therefore treats any line indented ≥2 spaces whose
  column 2 is non-space as a command row, and deeper-indented lines as
  continuation. A naive `^  (\S+)` parser that ends the section on the first
  non-match undercounts badly (it read `call-queue` as 1 command instead of 50).
- Structural counts come from `ast` over source, never from importing `wxcli`.
- "Tracked" means `git ls-files`; several trees here are gitignored and are
  reported separately (see Q4a).

---

## Framework and shape

### 1. CLI framework and entry point — **typer** (on click) `[verified]`

- Console script: `pyproject.toml:66-67` — `[project.scripts]` / `wxcli = "wxcli.main:app"`.
- The installed shim `/opt/homebrew/bin/wxcli` is `from wxcli.main import app`. `[verified]`
- `src/wxcli/main.py:1` `import typer`; `src/wxcli/main.py:15-20` builds the root
  app as `LazyTyper(...)`, **not** `typer.Typer` directly.
- `LazyTyper` is defined at `src/wxcli/commands/_lazy.py:287-355`; it subclasses
  `typer.Typer` (`_lazy.py:287`) and overrides `registered_groups` (property,
  `_lazy.py:300-309`) and `__call__` (`_lazy.py:311-336`) so that the real entry
  path never materializes the group tree. `__call__` delegates to
  `_fast_command()` (`_lazy.py:338-355`), which calls `typer.main.get_command`
  with the group list faked empty, then merges `_LazyGroupProxy` objects
  (`_lazy.py:131-177`) into the resulting `click.Group.commands` dict.
- click is a declared direct dependency (`pyproject.toml:31`), and the repo
  ships its own `click.Group` subclass `SafeSuggestGroup` in
  `src/wxcli/suggest.py` (stamped onto every sub-app at `_lazy.py:180-199`).

So: typer for declaration, click objects for dispatch, with a hand-written lazy
mounting layer between them.

### 2. Python floor, dependencies, packaging, version

- **Python floor:** `requires-python = ">=3.11"` — `pyproject.toml:9`. `[verified]`
  CI matrix is `["3.11", "3.12"]` (`.github/workflows/ci.yml:15-17`); the drift
  gate and release jobs pin 3.12 and 3.11 respectively. `[verified]`
- **Dependencies: 14 runtime deps**, `pyproject.toml:11-43` —
  `typer>=0.20.0`, `click>=8.1`, `rich>=13.0`, `httpx>=0.27.0`, `jmespath>=1.0`,
  `pyyaml>=6.0`, `packaging>=23.0`, `pydantic>=2.0`, `aiohttp>=3.9`,
  `networkx>=3.0`, `phonenumbers>=8.13`, `requests>=2.31`, `urllib3>=2.0`,
  `zeep>=4.2`. `[verified]` — method: read the `dependencies` array and counted
  entries. No `[project.optional-dependencies]` block exists; test-only deps
  (`pytest`, `pytest-asyncio`, `aioresponses`, `aiohttp<3.14`) are installed
  inline by CI (`.github/workflows/ci.yml:28-47`). `[verified]`
- **Packaging:** setuptools + setuptools-scm. `pyproject.toml:1-3`
  (`requires = ["setuptools>=68.0", "setuptools-scm>=8.0"]`,
  `build-backend = "setuptools.build_meta"`); `pyproject.toml:74-75`
  (`[tool.setuptools_scm] write_to = "src/wxcli/_version.py"`); package data at
  `pyproject.toml:70-73` bundles `_playbook/**` including the dot-directories.
  Published to PyPI via OIDC Trusted Publishing on GitHub Release
  (`.github/workflows/release.yml:1-5, 51-52`). `[verified]`
- **Current version.** Latest git tag is `v1.4.6` (`git tag --sort=-v:refname |
  head -1`). The working tree is 123 commits past it; the locally generated
  `src/wxcli/_version.py:22` reads `1.4.7.dev120+g2a89ea4ea.d20260804`, and
  `wxcli --version` prints the same. The **published** version is therefore
  `1.4.6` (`[inferred]` — from the tag plus the release workflow's
  tag-equals-wheel-version guard at `release.yml:38-50`; PyPI itself was not
  queried). The tag list holds 8 versions: v1.3.1, v1.4.0 … v1.4.6. `[verified]`

### 3. Total LOC and the shared/per-endpoint split `[verified]`

Method: `git ls-files '*.py'`, then `len(read_text().splitlines())` per file,
bucketed by path prefix. Physical lines, not SLOC; blanks and comments included.

| Bucket | Files | Lines |
|---|---:|---:|
| `src/wxcli/commands/` — endpoint layer (generated + hand-written seams) | 184 | 84,879 |
| `tests/` (tracked only) | 240 | 68,708 |
| `src/wxcli/migration/` — CUCM pipeline | 116 | 46,684 |
| `tools/` — generator + drift gate | 15 | 10,945 |
| `src/wxcli/*.py` — shared machinery, top level | 9 | 1,766 |
| `src/wxcli/org_health/` | 6 | 998 |
| `wxcli-dist/` | 1 | 389 |
| **Total tracked `.py`** | **571** | **214,369** |

Splitting `src/wxcli/commands/` further (`ast` over `_registry.py`/`_lazy.py`
declarations, then line counts):

| Sub-bucket | Files | Lines |
|---|---:|---:|
| 173 generated modules (from `GENERATED_GROUPS`) | 173 | 78,271 |
| 5 hand-written group modules (`update`, `configure`, `cucm`, `cleanup`, `org_health_cli`) | 5 | 5,423 |
| `_lazy.py` 355, `_registry.py` 183, `converged_recordings_export.py` 310, `cucm_config.py` 129, `init_playbook.py` 208, `__init__.py` 0 | 6 | 1,185 |
| 11 `fs_*.py` (gitignored, dev-only, **not** in the 84,879 above) | 11 | 2,706 |

**Shared machinery vs per-endpoint code.** The shared runtime is
`src/wxcli/*.py` = **1,766 tracked lines** (`auth.py` 407, `common.py` 263,
`errors.py` 225, `output.py` 227, `main.py` 208, `suggest.py` 148,
`update_check.py` 145, `config.py` 139, `__init__.py` 4) plus `_lazy.py` (355)
and `_registry.py` (183) — **2,304 lines** — against **78,271 lines** of
generated per-endpoint code. Ratio ≈ **1 : 34**. `[verified]`
(`src/wxcli/_version.py` is generated and untracked, so it is excluded.)

---

## Endpoint origin

### 4. Hand-written, generated, or a mix — **a mix, overwhelmingly generated** `[verified]`

Evidence, in order:

1. **The generator is in-repo:** `tools/generate_commands.py` (588 lines), whose
   module docstring is `"""Generate wxcli command files from OpenAPI spec
   JSON."""` (`tools/generate_commands.py:1`). It imports
   `tools/openapi_parser.py` (843 lines) and `tools/command_renderer.py`
   (2,091 lines), and takes `--spec` defaulting to
   `specs/webex-cloud-calling.json` (`generate_commands.py:18`), with field
   overrides from `tools/field_overrides.yaml` (`generate_commands.py:19`).
2. **The source is OpenAPI JSON on disk:** `specs/*.json` — 9 git-tracked specs
   plus 1 untracked (`specs/webex-flow-store.json`, excluded by
   `.gitignore:144`). Declared `openapi` versions: 3.0.0 for all tracked specs;
   the untracked flow-store spec is 3.1.0. `[verified]`
3. **Additive overlay:** `specs/overlays/webex-cloud-calling.overlay.json`
   supplies 2 operations (GET + PUT on
   `/telephony/config/locations/{locationId}/queues/{queueId}/cxEssentials/callRecordings`)
   that upstream omits; merged by `tools/spec_overlay.py`. `[verified]`
4. **The registration manifest is emitted, not written:** `src/wxcli/commands/_registry.py:1-7`
   says *"Registration manifest for generated command groups. Emitted by
   tools/generate_commands.py — do NOT edit by hand."*; the writer is
   `tools/generate_commands.py:183-189` (`manifest_path = output_dir /
   "_registry.py"`). `[verified]`
5. **Atomic regeneration driver:** `tools/spec_sync.py` runs
   `update-specs.py → generate_commands.py --all` per tracked spec →
   `drift_check.py --write-gaps` (`spec_sync.py:63-75`). `[verified]`

**Files in `src/wxcli/commands/` that are NOT generated** (6 tracked + 5
hand-written group modules): `_lazy.py`, `converged_recordings_export.py`,
`cucm_config.py`, `init_playbook.py`, `__init__.py`, and the five declared in
`HAND_WRITTEN_GROUPS` at `_lazy.py:50-56` — `update.py`, `configure.py`,
`cucm.py`, `cleanup.py`, `org_health_cli.py`. `_registry.py` is generator-emitted
(item 4 above). Outside `commands/`, everything under `src/wxcli/migration/`,
`src/wxcli/org_health/` and `src/wxcli/*.py` is hand-written (no generator writes
there — `DEFAULT_OUTPUT` is `src/wxcli/commands` only, `generate_commands.py:20`).
`[verified]`

**Generated modules carry no marker.** `head -3 src/wxcli/commands/people.py` is
`import json / import httpx / import typer` — no "generated, do not edit" header,
and `grep -n "DO NOT EDIT\|Generated by\|auto-generated" tools/command_renderer.py`
returns nothing. Generated-vs-hand-written is knowable only from
`_registry.py`/`_lazy.py`, not from the file itself. `[verified]`

### 4a. The four counts

Each definition is stated with the exact parse or command that produced it.
None of these is interchangeable with another.

#### (a) Operations in the source spec(s)

Five defensible numbers, depending on the corpus and the de-duplication rule:

| Definition | Value | Method |
|---|---:|---|
| Raw `(path, method)` entries, **all 10 spec files on disk** (incl. untracked flow-store) | **2,142** | `json.load` each `specs/*.json`; count `paths[*][method]` where method ∈ {get,post,put,patch,delete,head,options,trace} |
| Raw entries, **9 git-tracked specs** | **2,053** | same, restricted to `git ls-files -- specs/*.json` minus `*.overlay.json` |
| Distinct `(METHOD, raw path)` across the 9 tracked specs | **1,894** | same parse, into a `set` |
| Distinct `(METHOD, normalized path)` incl. the 2 overlay ops — the gate's universe | **1,896** | `len(set(ops) | set(skipped))` from `tools.drift_check.load_spec_ops(load_overrides()["skip_tags"])` |
| Gate's split of that universe | **1,845 non-skipped / 154 deliberately skipped** | same call, `len(ops)` and `len(skipped)`; printed by `python -m tools.drift_check` header line |

`1,845 + 154 = 1,999 ≠ 1,896` because **103 keys appear in both buckets** — the
same `(METHOD, path)` is skipped under one spec's tag and generated under
another's (`set(ops) & set(skipped)` = 103). `[verified]`

Per-file raw operation counts (9 tracked + 1 untracked):

| Spec | Paths | Operations |
|---|---:|---:|
| `webex-cloud-calling.json` | 687 | 1,087 |
| `webex-contact-center.json` | 327 | 448 |
| `webex-meetings.json` | 128 | 168 |
| `webex-admin.json` | 115 | 148 |
| `webex-device.json` | 67 | 101 |
| `webex-messaging.json` | 36 | 63 |
| `webex-broadworks.json` | 11 | 19 |
| `webex-wholesale.json` | 10 | 18 |
| `webex-ucm.json` | 1 | 1 |
| `webex-flow-store.json` *(untracked, dev-only)* | 63 | 89 |

`docs/arch/deliberate-gaps.md:8` (generated, and itself **gitignored** —
`.gitignore:45` excludes all of `docs/arch/`) states "**154 skipped operations
across 26 spec/tag pairs**", matching the gate. `[verified]`

#### (b) Commands exposed by the CLI at runtime

| Definition | Value | Method |
|---|---:|---|
| Top-level names in `wxcli --help` on **this machine** (fs_* present) | **197** | `wxcli --help` → awk from `^Commands:`, count `^  [a-z]` rows |
| …of which render as leaf commands (no subcommands) | **7** | `clear-org`, `configure`, `init`, `set-cc-region`, `switch-org`, `update`, `whoami` — the two Typer sub-apps `configure`/`update` use `@app.callback(invoke_without_command=True)` (`configure.py:52`, `update.py:207`) so they show no `Commands:` block |
| …of which are groups with subcommands | **190** | 197 − 7 |
| Subcommands listed across all 190 groups | **1,982** | ran `wxcli <group> --help` for all 197 names, parsed the `Commands:` block with the indentation-aware parser |
| Subcommands under the **173 generated** groups | **1,859** | same, restricted to `GENERATED_GROUPS` names |
| Subcommands under the 3 aliases (`cx-essentials` 14, `users` 6, `licenses-api` 3) | **23** | same |
| Subcommands under the 11 `fs-*` dev groups | **72** | same |
| Subcommands under `cucm` 25 / `cleanup` 1 / `org-health` 2 | **28** | same |
| **Fresh-clone total, aliases and fs_* excluded** (1,859 + 28 + 7 root leaves) | **1,894** | sum of the rows above |
| **Dispatchable** (adds 50 `hidden=True` commands invisible to `--help`) | **1,944** | `ast` scan for `@app.command(..., hidden=True)` across the 173 generated modules → 50; none elsewhere |
| The drift gate's own figure | **1,963** | `python -m tools.drift_check` header: `sum(len(c) for c in surface.values())` over the 181 registered names — counts alias names as separate commands (+23) and hidden ones (+50), excludes gitignored fs_* and the 7 root leaves |

The gate's 1,963 reconciles exactly: 1,907 generated decorated functions (incl.
50 hidden) + 2 (`converged-recordings download`/`export`, mounted from
`converged_recordings_export.py` at `_lazy.py:118-128`) + 30 hand-written group
commands (`cucm` 27, `org_health_cli` 2, `cleanup` 1) + 23 alias names + 1
(`init_playbook`) = 1,963. `[verified]`

#### (c) Command modules on disk, generated vs hand-written

| Definition | Value | Method |
|---|---:|---|
| `.py` files in `src/wxcli/commands/` on this disk | **195** | `ls src/wxcli/commands/*.py \| wc -l` |
| …git-tracked | **184** | `git ls-files 'src/wxcli/commands/*.py' \| wc -l` |
| …untracked (all gitignored via `.gitignore:145` `src/wxcli/commands/fs_*.py`) | **11** | `comm -13` of the two lists — exactly the 11 `fs_*.py` |
| Generated modules (registry manifest) | **173** | `ast.literal_eval` of `GENERATED_GROUPS` in `_registry.py`; 173 unique modules, 173 unique group names |
| Hand-written group modules | **5** | `ast.literal_eval` of `HAND_WRITTEN_GROUPS` in `_lazy.py:50-56` |
| Non-group support modules | **6** | disk stems minus generated/hand-written/fs: `__init__`, `_lazy`, `_registry`, `converged_recordings_export`, `cucm_config`, `init_playbook` |
| Decorated command functions, all 195 files | **2,012** | `ast.walk` for `FunctionDef` with an `@*.command` decorator |
| …in the 173 generated modules | **1,907** (1,857 visible + 50 hidden) | same, restricted |
| …in `fs_*` | **72** | same |
| …elsewhere | **33** | `cucm` 27, `org_health_cli` 2, `cleanup` 1, `converged_recordings_export` 2, `init_playbook` 1; `update.py` and `configure.py` declare **0** (`@app.callback` only) |

#### (d) Top-level command groups

| Definition | Value | Method |
|---|---:|---|
| Generated groups | **173** | `GENERATED_GROUPS` length |
| + hand-written groups = **command sets** (the gate's own unit) | **178** | `distinct_command_sets()` at `tools/drift_check.py:594-602`; printed as "178 command sets" |
| + 3 aliases = registered names on a fresh clone | **181** | gate header: "(181 registered names incl. aliases)"; `ALIASES` at `_lazy.py:60-64` |
| + 11 dev-only `fs_*` = groups mounted on **this** machine | **192** | `FS_DEV_GROUPS` at `_lazy.py:68-80`, gated by `(_COMMANDS_DIR / f"{module}.py").exists()` at `_lazy.py:251-252` |
| Groups that actually show a `Commands:` block | **190** | 192 − `configure` − `update` |
| + 5 root-level commands (`whoami`, `switch-org`, `clear-org`, `set-cc-region`, `init`) = names in `wxcli --help` here | **197** | measured |
| Same on a fresh clone / wheel (no fs_*) | **186** | 181 + 5 `[inferred]` — arithmetic, not executed against a clean checkout |

### 5. Canonical registry of supported endpoints — **no** `[verified]`

There is a canonical registry of **groups**, not of endpoints:
`src/wxcli/commands/_registry.py` (`GENERATED_GROUPS`, 173 tuples) plus the three
hand-maintained tuple literals in `_lazy.py` (`HAND_WRITTEN_GROUPS`, `ALIASES`,
`FS_DEV_GROUPS`). `_lazy.py:27-30` states this explicitly: *"`GENERATED_GROUPS`
(`_registry.py`) is the single source of truth for the 178 generator-owned
groups"* (the number in that sentence is 173 as measured — see Corrections).

Below group level there is **no registry**. Each command's HTTP verb and URL are
literals inside its own function body (`url = f"https://webexapis.com/v1/…"`
followed by `api.session.rest_get(...)` — e.g. `src/wxcli/commands/roles.py:27-28`).
To recover the endpoint set, `tools/drift_check.py:461-497`
(`parse_module_commands`) **re-derives** it by regex-splitting each module on
`@\w+\.command\(...)` and scanning each block for `url = f"…"` followed by
`rest_(get|put|post|patch|delete)(` or `follow_pagination(`. Flags are recovered
separately by `ast` in `parse_module_flags` (`drift_check.py:518-551`).

So: the endpoint set is **inferred from module structure and decorators at check
time**, and there is no committed list of "(group, command) → (METHOD, path)".

---

## Existing coherence enforcement

### 5a. Drift detection — **yes: `tools/drift_check.py`, 20 checks, CI-blocking** `[verified]`

- **Location:** `tools/drift_check.py`, 3,899 lines. Module docstring
  `drift_check.py:1-215` enumerates the checks; `drift_check.py:3651-3655` prints
  the header; the per-check prints run to `drift_check.py:3859`.
- **Count:** **20 numbered checks**, but check 11 is split into three separately
  reported oracles (11a, 11b-gated, 11b-advisory), and checks 18 and 19 each
  emit an extra ADVISORY line — so a run prints **24 result lines**. Report-only
  by default (always exit 0); `--enforce` exits 1 on findings; exit 2 on crash.
- **Supporting artifacts it reads:** `tools/field_overrides.yaml`,
  `tools/drift_check_allowlist.txt`, `tools/verb_naming.py` (301 lines),
  `tools/spec_overlay.py`, `tools/spec_semantics.json`.

What each check actually asserts (read from the docstring **and** the check
functions, not from the name):

| # | Assertion |
|---|---|
| 1 | Every non-skipped tracked-spec op has ≥1 registered command, and every registered command URL maps to a live spec op or a `keep_endpoints` entry. Implemented `drift_check.py:607-645` by inverting the `{(METHOD,path): [group command]}` map both ways. |
| 2 | Every `wxcli <group> [<command>]` token inside code spans of `.claude/{skills,agents,rules}/**`, `docs/reference/**`, `CLAUDE.md`, `README.md` resolves against the built surface. Also reads the prefixless `<group> <command>` form used in skill tables. |
| 3 | "N command groups" / "N OpenAPI specs" claims in `CLAUDE.md`/`README.md` equal the measured fresh-clone values **and** do not contradict each other. Three phrasings harvested. |
| 4 | Every registered group is referenced by the skills layer or declared on `CLAUDE.md`'s out-of-skill-scope list. |
| 5 | No `specs/overlays/**` path is now published upstream (a stale overlay claim). |
| 6 | Every `--flag` cited after a resolvable `wxcli <group> <command>` is accepted by that command (parsed with `ast`, so `typer.Option` is distinguished from `typer.Argument`). |
| 7 | Every backticked `--flag` anywhere in those files exists on at least one command somewhere. Weaker complement to 6; per-file/flag allowlist. |
| 8 | No `src/wxcli/commands/*.py` is present, non-gitignored, and unstaged. |
| 9 | Every accessor in a generated list command's `columns=` exists on the item schema of the 200 response, resolved through the key the command extracts with. |
| 10 | Every documented `wxcli <group> <command> …` example supplies the exact positional count the command declares. Bare mentions counted separately, never failed. |
| 11a | A documented example supplies every option the command declares required — read off the rendered command, not the spec (because `auto_inject_from_config` legitimately hides 12 spec-required params). |
| 11b | A doc placeholder (`CLUSTER_ID`, `TEMPLATE_ID`) names the resource the positional takes. Gated tier = declared-kind disagreement; advisory tier = bare-UUID heuristics. Arguments whose declared kind contradicts their own name (79) are excluded and reported apart. |
| 12 | No shipping command name whose obvious reading is wrong is unacknowledged (`-N` collision suffixes, bare verbs targeting a non-headline resource). CRITICAL+HIGH gate, MEDIUM reports. Acks in `naming_ack`, re-validated. |
| 13 | The auto-generated `Example:` line in a generated command's docstring names every flag the command has, so a spec-REQUIRED body field with no flag can't produce a complete-looking, unrunnable example. |
| 14 | The `--generate-json-body` skeleton never renders a nested object/array as `"..."` and never omits a spec-required field. |
| 15 | No entry in `field_overrides.yaml` is configuration that cannot apply (tag block / `tag_overrides` / `cli_name_overrides` keyed on a tag no spec generates; a per-command key naming no rendered command; a family declared in both a top-level block and `tag_overrides`). Acks in `inert_tag_ack`. |
| 16 | No list command carries a `--all` that cannot walk on an endpoint whose own 200 schema declares a paging total. Oracle is the rendered module. Acks in `undeclared_paging_ack`. |
| 17 | Prose claiming the size of an in-repo registry (CUCM mappers, analyzers, preflight checks) agrees with the registry read by `ast`. |
| 18 | Every `docs/reference/*.md` satisfies that directory's structural rules: in-document `](#anchor)` links land on a real heading, file ends with exactly one newline, a `## See Also` exists. Convention violations are advisory. |
| 19 | Every rendered operation is recorded in `tools/spec_semantics.json` and recomputed from `specs/*.json` each run. Gated: structural deltas + ID-kind flips. Advisory: all other prose. |
| 20 | Every registered command **set** is cited by ≥1 `docs/reference/*.md` or declared out-of-scope in `CLAUDE.md`. Keyed on the module, so an alias counts for the set it mounts. |

**Measured run (report mode, this tree, 10.5 s wall):** `result: PASS`, every
gated count 0. Header line: `drift-check: 178 command sets (181 registered names
incl. aliases), 1963 commands, 1845 non-skipped spec ops (154 deliberately
skipped)`. Non-zero advisories: 17 bare-UUID placeholder heuristics (11b),
79 arguments whose declared kind contradicts their own name (11b), 27 MEDIUM
naming findings (12). `[verified]`

**CI wiring — blocking. Exact invocation** (`.github/workflows/ci.yml:118-149`):

```yaml
      - name: Drift gate (enforcing)
        run: |
          set -o pipefail
          set +e
          python -m tools.drift_check --enforce 2>&1 | tee gate.log
          status=$?
          set -e
          if [ "$status" -eq 2 ]; then
            echo "::error::Drift gate CRASHED — it did not run. This is not a findings failure."
            exit 2
          fi
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

It is a separate job named `drift-gate` (`ci.yml:66`) from the `test` job, runs
on push-to-main and PRs (`ci.yml:3-6`), and installs the package first
(`pip install -e .`, `ci.yml:114-116`). Three other jobs also gate:
`playbook-freshness` (rebuilds `src/wxcli/_playbook` via `wxcli-dist/assemble.py`
and fails on any diff, `ci.yml:151-176`) and `release-integrity` (builds the
wheel and runs `tools/wheel_playbook_smoke.py`, `ci.yml:178-201`). `[verified]`

### 5b. Persisted CLI flag/argument surface — **no, in-process only** `[verified]`

The flag/argument/kind surfaces are all rebuilt from source on every gate run and
**never written to disk**:

- `build_flag_surface()` — `drift_check.py:554-566` → `{group: {command: {flags}}}`
- `build_positional_surface()` — `drift_check.py:1447-1460`
- `build_required_surface()` — `drift_check.py:1568-1580`
- `build_arg_kind_surface()` — `drift_check.py:1793-1827`
- `build_cli_surface()` — `drift_check.py:568-591` → `{group: {command: [(METHOD, path)]}}`

`grep -n "write_text\|json.dump" tools/drift_check.py` returns exactly **two**
write sites, and neither is the CLI surface:

1. `drift_check.py:3457` writes `tools/spec_semantics.json` (the **spec**
   snapshot — see 5c), only under `--refresh-spec-snapshot`.
2. `drift_check.py:2537` writes `docs/arch/deliberate-gaps.md`, only under
   `--write-gaps` — and `docs/arch/` is gitignored (`.gitignore:45`), so that
   file is **not** a committed artifact either, despite `tools/spec_sync.py:12`
   instructing `git add -u … docs/arch/deliberate-gaps.md`.

So: **the only committed snapshot in this system is of the spec, not of the CLI.**
Nothing on disk records what flags or positionals any command accepts; every
question of that shape is answered by re-parsing `src/wxcli/commands/*.py`.

### 5c. Spec snapshot for change detection — **yes: `tools/spec_semantics.json`** `[verified]`

- File: `tools/spec_semantics.json`, 944,345 bytes, `captured: "2026-08-04"`.
- Top-level keys: `_about`, `captured`, `specs`. `specs` is keyed by the 9
  tracked spec filenames; each value is `{op-key: {fields, summary, tag}}` where
  the op key is `"<METHOD> <normalized path>"`, e.g.
  `"DELETE /admin/recordings/{}"`.
- **1,883 operations** are recorded (sum of per-spec counts:
  cloud-calling 1,053, contact-center 421, meetings 144, admin 129,
  messaging 57, device 41, broadworks 19, wholesale 18, ucm 1). Method:
  `json.load` + `sum(len(v) for v in d["specs"].values())`.
  (1,883 vs the gate's 1,845 non-skipped: the snapshot is per-spec-file, so
  cross-spec duplicates are recorded once each rather than de-duplicated.)

**Exactly what it encodes per operation** — enumerated, not summarized. Per
operation there are three keys: `fields`, `summary`, `tag`. `fields` is a flat
dict whose keys are one of five namespaced forms and whose values are a marker
string. Prefix census across the whole snapshot:

| Field-key prefix | Occurrences | Meaning |
|---|---:|---|
| `body:<dotted.path>` | 7,608 | request-body field, nested paths flattened |
| `query:<name>` | 2,623 | query parameter |
| `(operation)` | 1,883 | the operation itself (one per op) |
| `path:<name>` | 1,872 | path parameter |
| `header:<name>` | 68 | header parameter |
| `?:<name>` | 9 | parameter with no declared `in` |

Marker encoding, quoted verbatim from `_about` and from the writer
(`drift_check.py:3459-3464`): *"Field encoding: `!` required, `~name`/`~id` the
kind its description states, `#hash` of the description, `%hash` of the rules
stated in it, `=enum` values."* Occurrence counts of each marker:
`#` 13,551 · `!` 4,354 · `%` 1,418 · `~` 1,329 · `=` 940.

Worked examples from the file:

```
"DELETE /telephony/config/locations/{}/schedules/{}/{}": {
  "fields": {
    "(operation)":     "#6a1dab",
    "path:locationId": "!#41d6c4",
    "path:scheduleId": "!#b6a1fb",
    "path:type":       "!#694c12=businessHours|holidays",
    "query:orgId":     "#7e0d89" },
  "summary": "Delete a Schedule",
  "tag": "Location Call Settings:  Schedules" }

"DELETE /people/{}/features/schedules/{}/{}": {
  "fields": { …, "query:orgId": "~id#0c01d5" }, … }

"DELETE /convergedRecordings/{}": {
  "fields": { "(operation)": "#d01ec1%98e509",
              "body:comment": "#c68897", "body:reason": "#cdb355",
              "path:recordingId": "!#6acecc" }, … }
```

So, field by field, what IS encoded: **shape** (which body/query/path/header
fields exist, nested body paths flattened), **requiredness** (`!`),
**enum choices** (`=a|b`), **description hash** (`#`), **constraint-rules hash**
(`%`, separate from the description hash so wording changes and rule changes are
distinguishable), **ID-vs-name kind as stated by the description** (`~id` /
`~name`), plus **summary text** and **tag** in the clear.

What is **NOT** encoded — checked by enumerating every per-operation key
(`{'fields','summary','tag'}`) and every field-key prefix: no destructiveness,
no scope (org-wide vs resource-scoped), no reversibility, no idempotency, no
rate-limit class, no auth scope, no response schema, no HTTP status set.

---

## Systems touched

### 6. External systems `[verified]`

Method: `git ls-files 'src/**/*.py' | xargs grep -ohE 'https?://[…]'` for hosts,
plus reading each client module. Four network systems and one local-state system:

| System | Protocol | Client lives at |
|---|---|---|
| **Webex REST API** (`webexapis.com`, 1,445 literal occurrences) | HTTPS/JSON over `httpx` | `src/wxcli/auth.py:203-289` (`WebexSession`, `rest_get/put/post/patch/delete`) — used by every generated command |
| **Webex Contact Center** (`api.wxcc-{us1,eu1,eu2,anz1,ca1,jp1,sg1}.cisco.com`) | HTTPS/JSON, same `WebexSession`, different base URL + bare-UUID org id | base URLs in `src/wxcli/config.py` (`CC_REGIONS`, referenced `main.py:189`); `{cc_base_url}` template in generated `cc_*.py` modules |
| **WxCC Flow Store** (`flow-store.us1.ciscoccservice.com`, `flow-store.intgus1…`) | HTTPS/JSON, `{fs_base_url}` | the 11 gitignored `fs_*.py` modules |
| **Cisco Unified CM — AXL** | **SOAP/WSDL** via `zeep` over `requests` | `src/wxcli/migration/cucm/connection.py` (`AXLConnection`, `connection.py:149-231`) |
| **Cisco Unity Connection — CUPI** | REST/JSON via `requests` | `src/wxcli/migration/cucm/unity_connection.py` (`UnityConnectionClient`, lines 23-56) |
| **PyPI** | HTTPS/JSON via `httpx`, 1 s timeout, 24 h cache | `src/wxcli/update_check.py:29-31` (`https://pypi.org/pypi/wxcli/json`) |
| **Local file mutation** | — | `~/.wxcli/config.json` (`src/wxcli/config.py:5,13-16`); `~/.wxcli/update-check.json` (`update_check.py:30`); per-project SQLite migration DB (`src/wxcli/migration/store.py:34-45`, WAL mode) and project dirs; `wxcli init` materializes the playbook into `./wxcli-playbook` (`src/wxcli/commands/init_playbook.py`); `wxcli cucm report` / `org-health` write HTML/CSV/JSON to disk |

**Not present:** no RIS/RisPort client, no Expressway client, no CUCM CDR/serviceability
client, no SSH/CLI-scraping client. Method: grep for `RisPort`, `risport`,
`expressway`, `paramiko`, `ssh` across `src/` returned no client code. `[verified]`

Two of these are used **only** by the CUCM migration subtree
(`src/wxcli/migration/cucm/`); the rest of the CLI never touches AXL or CUPI.

### 7. Per-system auth, error semantics, retry — **all three are distinct per system** `[verified]`

| | Webex REST (+CC, +Flow Store) | CUCM AXL | Unity CUPI | Migration async engine (Webex) |
|---|---|---|---|---|
| **Auth** | Bearer token; resolved `WEBEX_ACCESS_TOKEN` → `WEBEX_TOKEN` → `~/.wxcli/config.json` (`auth.py:375-386`) | HTTP Basic on a `requests.Session` (`connection.py:186-187`) | HTTP Basic on a `requests.Session` (`unity_connection.py:47`) | same bearer token via `resolve_token()`, passed into `aiohttp` |
| **TLS** | default verification | `session.verify = verify_ssl`, **default `False`**; `urllib3.disable_warnings(InsecureRequestWarning)` at `connection.py:26` | `verify_ssl` default `False` (`unity_connection.py:42,48`) | default |
| **Timeouts** | connect 10 s / read 60 s, env-overridable `WXCLI_CONNECT_TIMEOUT` / `WXCLI_READ_TIMEOUT` (`auth.py:191-192, 208-213`) | `timeout: int = 30` on the zeep `Transport` (`connection.py:174, 188`) | `timeout: int = 30` set on the session (`unity_connection.py:43,49`) | none set explicitly at the call site |
| **Error type** | `WebexError(message, status_code, body)` — `errors.py:10-21` | `AXLConnectionError` — `connection.py:31-32`; plus a regex for zeep's `TypeError("unexpected keyword argument 'x'")` used to drop returnedTags the schema rejects (`connection.py:51-53`, `dropped_tags` at `connection.py:183-185`) | `UnityConnectionError` — `unity_connection.py:20-21` | `OpResult` dataclass with `status`/`error`/`body` (`engine.py:135-146`) |
| **Retry** | bounded, in `WebexSession._request` (`auth.py:220-262`): `RETRY_STATUSES = {429,500,502,503,504}`, `DEFAULT_MAX_ATTEMPTS = 4`, `Retry-After` honored on 429 capped at `MAX_RETRY_AFTER_SECONDS = 30`, otherwise exponential backoff with jitter (`_backoff_delay`, `auth.py:184-188`), plus **one** connect-error retry. Disabled by `WXCLI_RETRY_MODE=off` or `WXCLI_NO_RETRY=1`. | **none** — no retry loop in `connection.py` | **none** — no retry loop in `unity_connection.py` | separate: `MAX_RETRIES = 5` (`engine.py:36`), 429 → `sleep(int(Retry-After or 5))` (`engine.py:199-202`), other failures → `sleep(2 ** attempt)` (`engine.py:224`); plus a per-endpoint `RateLimiter` with `max_concurrent=5`, `base_delay=1.0`, `max_delay=60.0`, `backoff_factor=2.0`, `max_retries=5` (`src/wxcli/migration/rate_limiter.py:17-24`) |
| **Tips / actionability** | rich: `_ERROR_TIPS` (5 Webex errorCodes), `_MESSAGE_TIPS` (2), `_STATUS_TIPS` (7 statuses), `_ID_KIND_TIPS`, `_NETWORK_TIPS` (5) — `errors.py:27-70, 113-121, 208-214` | none | none | log lines only |

So: **shared** for Webex/CC/Flow Store (one `WebexSession`, one error type, one
retry policy — CC and FS differ only in base URL and org-id encoding);
**separate and non-overlapping** for AXL and CUPI (own exception types, own
sessions, no retry); and **a fourth, independent** retry/rate-limit
implementation inside the migration execute engine that does not reuse
`auth.py`'s.

---
