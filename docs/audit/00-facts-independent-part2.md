# Independent facts — Part 2 (Q8–Q18)

Repo: `/Users/ahobgood/Documents/webexCalling` @ `b578a52` (branch `main`, 2026-08-04).
Produced without reading any other file under `docs/audit/`.

Every answer is labelled `[verified]` (a command was run / source parsed) or `[inferred]`.
`UNKNOWN` is used where no evidence was found.

## Method notes that apply throughout

**Tracked vs on-disk.** All counts below are over **git-tracked** files unless stated.

| Scope | Tracked | On disk | Method |
|---|---|---|---|
| whole repo | 845 | — | `git ls-files \| wc -l` |
| `src/wxcli/**` | 454 | — | `git ls-files 'src/wxcli/**' \| wc -l` |
| `src/wxcli/commands/*.py` | 184 | 195 | `git ls-files` vs `ls -1 src/wxcli/commands/*.py` |
| `tests/**` | 240 | 272 (`.py` only) | `git ls-files 'tests/**'` vs `find tests -name '*.py'` |

The 11 untracked `commands/*.py` files are all gitignored and all prefixed `fs_`
(`fs_connectors.py`, `fs_expression_test.py`, `fs_flow_props.py`, `fs_flow_versions.py`,
`fs_flows_v2.py`, `fs_flows.py`, `fs_projects.py`, `fs_resources.py`, `fs_templates.py`,
`fs_tracing.py`, `fs_user_prefs.py`) — confirmed with `git check-ignore -q` per file. `[verified]`

**Command inventory parse (used for Q8, Q10, Q11).** One `ast` pass over the 184 tracked
`src/wxcli/commands/*.py`. A "command" is a `FunctionDef` carrying a decorator whose unparse
contains `.command(`. For each, the set of called function *names* (last dotted segment) was
collected; HTTP verb is read from membership of `rest_get` / `rest_post` / `rest_put` /
`rest_patch` / `rest_delete`; a gate is `typer.confirm` in that call set. Script written to
scratchpad, results reproduced in each answer below.

Totals from that pass `[verified]`:

- **1,890** typer commands in tracked `commands/`.
- Commands issuing at least one mutating REST call (`POST`/`PUT`/`PATCH`/`DELETE`): **958**.
- Commands issuing `rest_delete`: **179**.
- Commands issuing a write but no delete (`POST`/`PUT`/`PATCH` only): **779**.
- Per-verb call presence (a command can appear under more than one verb):
  `rest_get` 901, `rest_post` 404, `rest_put` 345, `rest_delete` 179, `rest_patch` 30.

This pass covers only generated/hand-written command modules. `cleanup.py` and `cucm.py` route
their deletions and writes through helpers rather than a `rest_*` call inside the command body,
so they are handled separately and named explicitly below.

---

## 8. Commands capable of org-wide mutation or migration-scale change

### 8a. The named org-wide / migration-scale surfaces

| Command | What it does | Is target scope explicitly required? | Evidence |
|---|---|---|---|
| `wxcli cleanup run` | Batch-deletes Webex Calling resources across 13 dependency layers | **Required, enforced.** Either `--scope <names>` or `--all` must be given; neither → `Must specify --scope or --all.` then `typer.Exit(1)`. Org itself is *not* explicit — `org_id = get_org_id()` reads the saved config. | `src/wxcli/commands/cleanup.py:1103-1108` (guard), `:1110-1111` (`get_api`, `get_org_id`), help via `wxcli cleanup run --help` |
| `wxcli cucm execute` | Executes every pending migration operation against the live org, concurrent (default 20, range 1–50) | **No scope flag at all.** Only `-c/--concurrency` and `-p/--project`. Project defaults from config; org comes from the saved token/config. | `wxcli cucm execute --help` (verified subprocess); `src/wxcli/commands/cucm.py` (`execute`) |
| `wxcli organizations delete` | `DELETE /v1/organizations/{orgId}` — deletes the entire organization | **Not required.** Zero positional arguments; `org_id = resolve_org_id(api.session)` is derived, never passed. Gated by `typer.confirm(f"Delete {org_id}?", abort=True)` unless `--force`. | `src/wxcli/commands/organizations.py:64-90`; confirm at `:74-75` |
| `wxcli cucm decide --all --type <t> --choice <c>` | Batch-resolves every migration decision of a type; `--apply-auto` applies all auto-resolvable decisions | Scope is `--type`/`--all`; `-y/--yes` skips the confirm. Mutates local project DB, not the remote org. | `src/wxcli/commands/cucm.py:2149` (`decide`), help verified |
| `wxcli cucm retry-failed` | Resets **all** failed operations to `pending` so the next `execute` re-attempts them | No scope flag beyond `-p/--project`. No confirmation. | `wxcli cucm retry-failed --help` |
| `wxcli cucm config reset` | Resets a config key to default | Key is a required argument; `-y/--yes` skips `typer.confirm`. Local only. | `src/wxcli/commands/cucm.py:928-968` |
| `wxcli scim-bulk create` | SCIM `/Bulk` — arbitrary batch of user create/update/delete in one request | Scope is whatever is in the request body. No confirm. | `wxcli scim-bulk --help`; `src/wxcli/commands/scim_bulk.py` |
| `wxcli init` | Writes/overwrites playbook files into a folder; `--force` overwrites | `-y/--yes` skips confirm. Local filesystem only. | `src/wxcli/commands/init_playbook.py:152` |
| `wxcli update` | Upgrades the installed package, then re-runs `wxcli init --force` | `--yes` skips both confirms. Local only. | `src/wxcli/commands/update.py:166`, `:211`, `:255` |

### 8b. The structural org-wide surface (scope defaults, not required)

`[verified]` **312** of the 958 mutating commands take **zero required positional arguments** —
their entire target is options and/or config-derived state. Method: same `ast` pass, checking
each parameter's default for `typer.Argument`; a command with no `typer.Argument` parameter has
no required positional.

Of those 312, **60** call `get_org_id()` directly, i.e. the org they act on comes from the saved
config file rather than the invocation. Method: `'get_org_id' in calls` on the same pass.

Repo-wide, `get_org_id` appears in **63** of the 184 tracked command modules across **917** call
sites (`grep -rl` / `grep -rc` over `src/wxcli/commands/*.py`). Org scope is therefore inherited
by default across most of the CLI; `CLAUDE.md:470` documents this as generator
`auto_inject_from_config` (`tools/generate_commands.py:267`).

Top modules by count of zero-positional mutating commands: `my_call_settings.py` 33,
`call_controls.py` 24, `cc_queue.py` 10, `cc_agents.py` 9, `conference.py` 9,
`call_routing.py` 8, `meeting_preferences.py` 8, `device_settings.py` 7.

**Seven zero-positional commands issue `rest_delete`** — the delete target is entirely
config- or option-derived `[verified]`:

- `src/wxcli/commands/authorizations.py:51` `delete`
- `src/wxcli/commands/call_queue.py:1375` `delete_supervisors_config`
- `src/wxcli/commands/cc_dial_number.py:155` `delete`
- `src/wxcli/commands/conference.py:88` `delete`
- `src/wxcli/commands/device_settings.py:1630` `delete_background_images`
- `src/wxcli/commands/meeting_chats.py:50` `delete`
- `src/wxcli/commands/organizations.py:65` `delete`

---

## 9. Irreversible operations on the remote side

`[verified]` for the enumeration; `[inferred]` for "the Webex API offers no undo" — that claim
rests on the absence of any restore/undelete path in this repo, not on an API document.

**Repo-side evidence that deletes are one-way:** the only confirmation string in the codebase
that names consequence says so — `cleanup.py:1255-1258`:

```
f"\nDelete {total} resources? This cannot be undone"
```

**Categories:**

1. **All 179 `rest_delete` commands.** No compensating create is emitted, no prior state is
   captured before the call. Method: the `ast` pass; no command in the set calls a `rest_get`
   *and* persists the result before deleting.
2. **`wxcli cleanup run`** — up to 13 layers of deletions (`DELETION_LAYERS`,
   `cleanup.py:1262`), including users, workspaces, numbers, and locations when
   `--include-users` / `--include-locations` are passed. Raw deletes at
   `cleanup.py:375`, `:445`, `:710`, and a batched number-delete at `:852`.
3. **`wxcli organizations delete`** — whole-org delete (`organizations.py:78`).
4. **`wxcli cucm execute` create operations** — no automatic rollback exists. The only rollback
   affordance is `wxcli cucm rollback-ops`, which is **read-only**: it *lists* completed create
   ops in reverse dependency order. Its implementation
   (`src/wxcli/migration/execute/runtime.py:303-375`, `get_completed_ops_for_rollback`) issues
   only `SELECT` statements against `plan_operations` and returns dicts. No delete is performed.
   The name is a report, not an action. `[verified]`
5. **`wxcli scim-bulk create`** — a bulk body may contain `DELETE` operations; nothing in the
   command inspects the body.

**Partially reversible:** `PUT`/`PATCH` writes (779 commands) overwrite prior values. No
pre-write snapshot is taken anywhere in `src/wxcli/` — the `--verify` flag re-reads *after* the
write to compare against what was sent (`src/wxcli/common.py:136` `verify_write`), which detects
a discrepancy but does not preserve the old value.

---

## 10. Dry-run, pre-flight validation, confirmation gates — quantified

### 10a. Confirmation gates

Method: the `ast` pass — `typer.confirm` present in the command's call set; `--force`/`--yes`
detected as a parameter named `force` / `yes`.

| Measure | Count | Method |
|---|---|---|
| Commands performing a destructive HTTP call (`DELETE`) | **179** | `rest_delete` in call set |
| …of those carrying a confirmation gate | **179** (100%) | `typer.confirm` in call set |
| …of those carrying a bypass flag | **179** (100%) | `force` in parameter list |
| Commands performing a mutating HTTP call (`POST`/`PUT`/`PATCH`/`DELETE`) | **958** | any of the four |
| …of those carrying a confirmation gate | **179** (18.7%) | identical set to the deletes |
| Write-but-not-delete commands (`POST`/`PUT`/`PATCH` only) | **779** | set difference |
| …of those carrying a confirmation gate | **0** | `typer.confirm` count over that set |
| …of those carrying a `--force` flag | **2** | `force` in parameter list |
| Total commands anywhere in tracked `commands/` with `typer.confirm` | **183** | same pass |

The 4 confirming commands that issue no `rest_delete` are
`cleanup.py:1058 cleanup_run`, `cucm.py:928 config_reset`, `cucm.py:2149 decide`,
`init_playbook.py:152 init`. `[verified]`

The generated gate is uniform, e.g. `src/wxcli/commands/rooms.py:213,220-221`:

```python
force: bool = typer.Option(False, "--force", help="Skip confirmation"),
...
if not force:
    typer.confirm(f"Delete {room_id}?", abort=True)
```

**Not gated:** `wxcli cucm execute` — no `typer.confirm`, no `--force`, no `--yes`; the only
options are `-c/--concurrency` and `-p/--project` (`wxcli cucm execute --help`, verified).
Likewise `wxcli cucm retry-failed`. `[verified]`

### 10b. Dry-run

`[verified]` Exactly **two** commands in tracked `commands/` take a `dry_run` parameter:

- `src/wxcli/commands/cleanup.py:1058` `cleanup_run` → `--dry-run`, "Show what would be deleted
  without actually deleting." Terminates at `cleanup.py:1249` with
  `Dry run complete. No resources were deleted.` before the confirm block.
- `src/wxcli/commands/cucm.py:1715` `preflight` → `--dry-run`.

Plus a separate standalone command `wxcli cucm dry-run` — "Preview the full execution sequence
without making..." — implemented as `dry_run_all_batches` at
`src/wxcli/migration/execute/runtime.py:375`. `[verified]`

No other command in the CLI offers a dry-run. **956 of the 958 mutating commands have no
dry-run path.** `[verified]`

### 10c. Pre-flight validation

Two mechanisms `[verified]`:

1. **`wxcli cucm preflight`** — 10 registered checks imported at
   `src/wxcli/migration/preflight/runner.py:24-32`: `check_bulk_device_job_support`,
   `check_duplicate_users`, `check_e911_readiness`, `check_feature_entitlements`,
   `check_licenses`, `check_locations`, `check_number_conflicts`, `check_rate_limit_budget`,
   `check_trunks`, `check_workspace_licenses`. Dispatch table at `runner.py:163-167`;
   `--check` filter at `runner.py:113`. This validates against the *live Webex org* before
   migration.
2. **`--generate-json-body`** — present **711** times across tracked `commands/*.py`
   (`grep -h '"--generate-json-body"' | wc -l`). It prints a request-body skeleton and exits
   *before authenticating*, so it is a body-shape preview rather than a validation of values.
   Documented caveat at `CLAUDE.md` Known Issue #2: it does not bypass required positionals.

### 10d. Post-write verification (adjacent, not a gate)

`--verify` appears **332** times in tracked `commands/*.py`
(`grep -c '"--verify"' | awk` sum). Implementation `verify_write` at
`src/wxcli/common.py:136-188` re-reads the resource and diffs only the fields sent.
`CLAUDE.md` states 328; the measured tracked figure is **332**. `[verified]`
It runs *after* the write and, per `CLAUDE.md`, never changes the exit code.

---

## 11. Idempotency of mutating bulk operations — per command from the Q8 list

`[verified]` where source was read; `[inferred]` where behaviour follows from the HTTP verb
without a test proving it.

| Command | Idempotent on re-run? | Evidence |
|---|---|---|
| `wxcli cleanup run` | **`[inferred]` Yes, degrading to no-op.** Each run rebuilds an inventory from live `list` calls, then deletes what it found; a second run finds nothing and deletes nothing. But there is **no 404 tolerance in the delete path** — `grep -n "404" src/wxcli/commands/cleanup.py` returns no hits — so a delete losing a race with another actor surfaces as an error rather than a silent success. Failures are collected per resource (`DeleteResult`, `cleanup.py:1262`) and logged (`logger.warning` at `:262`, `:279`, `:290`), not raised. | `src/wxcli/commands/cleanup.py:262,279,290,375,445,710,852,1262` |
| `wxcli cucm execute` | **`[verified]` Yes, by design, via two mechanisms.** (1) State: only ops with status `pending` are picked up (`get_next_batch`, `runtime.py:25`); completed ops are never re-sent. (2) **409 auto-recovery**: on HTTP 409 the engine calls `_try_find_existing` (`engine.py:612-619`), and on success marks the op complete against the pre-existing resource — `logger.info("409 auto-recovered %s -> %s")` at `engine.py:939-951`. Module docstring states "409 auto-recovery (search for existing resource)" at `engine.py:7`. | `src/wxcli/migration/execute/engine.py:7,612,939-951`; `runtime.py:25` |
| `wxcli cucm retry-failed` | **`[verified]` Yes.** Pure state transition `failed → pending`; running it twice with no failures changes nothing. | `wxcli cucm retry-failed --help` |
| `wxcli cucm decide` / `--apply-auto` | **`[verified]` Yes.** Writes decision rows to the local SQLite `decisions` table (`store.py:104`); re-resolving to the same choice is a rewrite of the same value. | `src/wxcli/migration/store.py:104`; `cucm.py:2149` |
| `wxcli cucm config reset` | **`[verified]` Yes.** Sets a key to its `DEFAULT_CONFIG` value. | `src/wxcli/commands/cucm.py:928-968` |
| `wxcli organizations delete` | **`[inferred]` No.** Second invocation targets a now-deleted org; per `src/wxcli/errors.py:_STATUS_TIPS[404]` a 404 is surfaced as an error and `handle_rest_error` exits 1. | `src/wxcli/commands/organizations.py:78`; `src/wxcli/errors.py:169,203` |
| The 179 generated `delete` commands | **`[inferred]` No.** Same 404-on-second-run path; nothing in the generated body swallows 404. | `ast` pass; `src/wxcli/errors.py:203` |
| The 345 `rest_put` commands | **`[inferred]` Yes** — full-representation PUT is idempotent by verb, and the repo relies on that (`verify_write` re-sends nothing, it re-reads). | `src/wxcli/common.py:136` |
| The 404 `rest_post` commands | **`[inferred]` No.** POST-create repeated yields either a duplicate or a 409; only the migration engine has 409 recovery, and it is not reachable from the generated commands. | `src/wxcli/migration/execute/engine.py:939` (recovery lives only there) |
| `wxcli scim-bulk create` | **UNKNOWN.** Idempotency depends entirely on the caller-supplied bulk body; no repo-side handling was found. | `wxcli scim-bulk --help` |

---

## 12. Mid-run failure: position reporting and resume

**Migration pipeline — a full resume mechanism exists.** `[verified]`

Position is durable in SQLite (`src/wxcli/migration/store.py:44` `sqlite3.connect`), table
`plan_operations` with `status TEXT DEFAULT 'pending'` (`store.py:145-154`) and `plan_edges`
(`store.py:163`). Per-operation status is written by `update_op_status`
(`src/wxcli/migration/execute/runtime.py:142`).

Resume surface:

- `reset_in_progress(store)` — `UPDATE plan_operations SET status='pending' WHERE status='in_progress'`,
  returns the count reset, logs `"Reset %d in_progress operations to pending"`.
  `src/wxcli/migration/execute/engine.py:148-159`. This is what makes a killed run resumable.
- `wxcli cucm execution-status` — progress report; `get_execution_progress` at `runtime.py:457`.
- `wxcli cucm next-batch` — next ready operations; `get_next_batch` at `runtime.py:25`.
- `wxcli cucm retry-failed` — bulk `failed → pending`.
- `wxcli cucm mark-complete` / `mark-failed` — manual per-op status override.
- `wxcli cucm rollback-ops` — **report only**, see Q9 item 4.
- Cascade handling on failure: `_cascade_skip` (`runtime.py:235`) and `_undo_cascade_skip`
  (`runtime.py:277`) mark dependents of a failed op.

**Everywhere else — no resume, no position.** `[verified]`

- `wxcli cleanup run` has no persisted state. It accumulates `all_results: list[DeleteResult]`
  in memory (`cleanup.py:1262`) and prints at the end. Killed mid-run, nothing records which of
  the 13 layers completed; the only recovery is to re-run and rely on the re-inventory (Q11).
- The 958 generated mutating commands are single-request; there is no multi-step position to
  report. The one bulk-ish exception, number deletion, batches inside a loop at
  `cleanup.py:852` with no per-batch checkpoint.
- `converged-recordings export` writes `recordings.jsonl` incrementally
  (`src/wxcli/commands/converged_recordings_export.py:202`) and logs per-item failures
  (`:78, :244, :266, :283, :286`), but has no resume flag — **UNKNOWN** whether a re-run skips
  already-downloaded items; not determined from the lines read.

---

## 13. Error messages: structure, and error-class distinguishability

### 13a. Structure

`[verified]` Errors are **prose, deliberately and elaborately so**, emitted through one central
module: `src/wxcli/errors.py` (225 lines).

- Typed carrier: `class WebexError(Exception)` with optional `status_code` and parsed `body`
  (`errors.py:11-21`). The docstring states the enrichments exist "so handlers can key off
  status instead of substring matching."
- Three prose tip tables, tried most-specific first:
  - `_ERROR_TIPS` keyed on Webex `errorCode` — 5 entries: 4008, 9601, 25008, 25409, 28018
    (`errors.py:27-33`).
  - `_MESSAGE_TIPS` keyed on message substring — 2 entries: `"Target user not authorized"`,
    `"Unauthorized request:"` (`errors.py:35-45`).
  - `_STATUS_TIPS` keyed on HTTP status — 7 entries: 400, 401, 403, 404, 405, 409, 429
    (`errors.py:48-70`), described in-source as "Last-resort tips … Reached only when no
    errorCode or message tip matched."
  - `_ID_KIND_TIPS` keyed on `(group, decoded id kind)` — an explicit allowlist, with a comment
    (`errors.py:~120`) explaining that broad detection is unsafe because 79 CLI arguments
    declare a kind their own name contradicts.
- `decode_id_kind` (`errors.py:~100`) base64-decodes a Webex id to its `ciscospark://…/KIND/…`
  segment locally, before any call.

Output is human prose on stderr. No machine-readable error envelope (no JSON error object, no
stable error code emitted by the CLI itself) was found.

### 13b. Distinguishability by exit code

`[verified]` **They are not distinguishable by exit code.** Both handlers converge on 1:

- `handle_rest_error` (`errors.py:169`) → `raise typer.Exit(1)` at `errors.py:203`.
- `handle_network_error` (`errors.py:215`) → `raise typer.Exit(1)` at `errors.py:225`.

So a validation rejection (400), an auth failure (401/403), a not-found (404), a dependency
conflict (409), an exhausted-retry rate limit (429), and a connection failure all exit **1**.
A caller can only separate them by parsing the prose.

Exit-code census across tracked `src/wxcli/**` excluding `_playbook`
(`grep -rhn "typer.Exit(" | grep -o "Exit([^)]*)" | sort | uniq -c`) `[verified]`:

| Code | Sites |
|---|---|
| `Exit(0)` | 725 |
| `Exit(1)` | 270 (+1 `Exit(code=1)`) |
| `Exit(2)` | 5 |
| `Exit()` (bare) | 1 |

Total `raise typer.Exit` / `sys.exit` sites: **999**. Exit 2 is Click/Typer's usage-error code
and the 5 explicit sites are the only third value in the codebase.

**By exception type, they *are* distinguishable in-process** — `WebexError` (remote rejection,
carries `status_code`) versus `httpx.HTTPError` (transient/network) are caught separately in
every generated command, e.g. `organizations.py:79-82`. That distinction is erased at the
process boundary.

### 13c. Transient handling

`[verified]` Retry lives in `src/wxcli/auth.py`: connect-error single retry with
`logger.warning("Connect error on %s %s (%s) — retrying once")` at `auth.py:242`, and a
backoff retry at `auth.py:256` (`"%s on %s %s — retrying in %.1fs"`). Budget is tunable via
`WXCLI_MAX_ATTEMPTS`, per the 429 tip at `errors.py:~68`. The migration engine has its own:
`MAX_RETRIES = 5` with Retry-After backoff (`engine.py:35`, docstring `engine.py:4`).

---

## 14. Logging of invocations

`[verified]` **There is no invocation log.** No audit trail, no history file, no per-run record.

- Logging is stdlib `logging`, imported in **66** tracked modules under `src/wxcli/`
  (`grep -rln "import logging" --include='*.py' src/wxcli/ | grep -v _playbook`).
- **No handler is configured at import time and no file handler exists anywhere.** The only
  configuration call in the tracked tree is inside `get_api`:

  ```python
  def get_api(debug: bool = False, ...):
      if debug:
          logging.basicConfig(level=logging.DEBUG)
          logger.setLevel(logging.DEBUG)
  ```
  `src/wxcli/auth.py:388-393`

  So logging is **opt-in per invocation** via `--debug`, goes to **stderr** (the
  `basicConfig` default), and is **not persisted**.
- `--debug` is a per-command flag on generated commands (e.g. `main.py:49`, `main.py:106`), not
  a global one — `wxcli --debug <cmd>` is not the shape; `--debug` sits after the subcommand.
- The **only** file written by any logging-adjacent code path is
  `src/wxcli/commands/converged_recordings_export.py:202`, which opens
  `<out_path>/recordings.jsonl` — that is exported recording metadata, a product of the command,
  not a log of invocations. `grep -rn "\.jsonl\|audit.log\|\.log'\|\.log\"" src/wxcli/` returns
  that single hit.
- The migration project SQLite DB has a `journal` table (`src/wxcli/migration/store.py:120`) and
  a `merge_log` table (`store.py:133`). These record migration-pipeline state changes within a
  project, not CLI invocations. Their exact contents were not enumerated — **UNKNOWN** beyond
  the fact that they exist.

---

## 15. Tests

### 15a. Inventory

`[verified]` **240 tracked** files under `tests/`, versus **272 `.py` files on disk**. The gap is
gitignored dev-only tests, confirmed per-file with `git check-ignore`.

| Layer | Tracked files | Method |
|---|---|---|
| `tests/` top level | 23 | `git ls-files 'tests/*.py'`, top-level entries only |
| `tests/migration/**` | 209 | `git ls-files 'tests/migration/**' \| wc -l` |
| `tests/org_health/**` | 8 | `git ls-files 'tests/org_health/**'` |

Test functions in tracked test files: **3,060**
(`grep -rh "^def test_\|^    def test_" $(git ls-files 'tests/**/*.py') | wc -l`).

The 23 tracked top-level tests, in full:
`test_assemble.py`, `test_command_naming_residue.py`, `test_drift_check_columns.py`,
`test_drift_check_doc_shape.py`, `test_drift_check_exit_codes.py`, `test_drift_check_inert.py`,
`test_drift_check_naming.py`, `test_drift_check_paging.py`, `test_drift_check_positionals.py`,
`test_drift_check_references.py`, `test_drift_check_registrations.py`,
`test_drift_check_semantics.py`, `test_drift_check_untracked.py`, `test_errors_actionability.py`,
`test_errors_id_kind.py`, `test_field_expansion.py`, `test_field_overrides.py`,
`test_pagination_walkers.py`, `test_readme_distribution.py`, `test_release_integrity.py`,
`test_suggest_and_paging.py`, `test_verify_flag.py`, `test_wxcli_gate.py`.

### 15b. Coverage of shared machinery

`[verified]` The distribution is lopsided. **209 of 240 tracked test files (87%) test the CUCM
migration module**, which is 125 of 454 tracked `src/wxcli` files.

Shared machinery — `common.py` (263 lines), `output.py` (227), `errors.py` (225),
`auth.py` (407), `config.py` (139), `main.py` (208), `cleanup.py` (1,478) — is covered by
**tracked** tests only obliquely:

| Shared module | Tracked test touching it | Evidence |
|---|---|---|
| `errors.py` | `tests/test_errors_actionability.py`, `tests/test_errors_id_kind.py` | filenames + tracked |
| `common.py` (`apply_fields`, `verify_write`) | `tests/test_field_expansion.py`, `tests/test_verify_flag.py`, `tests/test_field_overrides.py` | tracked |
| pagination (`--all`) | `tests/test_pagination_walkers.py`, `tests/test_suggest_and_paging.py`, `tests/test_drift_check_paging.py` | tracked |
| `suggest.py` | `tests/test_suggest_and_paging.py` | tracked |
| `auth.py` | **none tracked** — `tests/test_auth.py` exists on disk and is **gitignored** | `git check-ignore -q tests/test_auth.py` → ignored |
| `config.py` | **none tracked** — `tests/test_config.py`, `tests/test_config_org.py`, `tests/test_org_id_injection.py` all gitignored | same method |
| `output.py` | **none tracked** — `tests/test_output.py`, `tests/test_output_errors.py` gitignored | same method |
| `cleanup.py` | **none tracked** — `tests/test_cleanup.py` gitignored | same method |
| `common.py` broadly | `tests/test_common.py` gitignored | same method |
| smoke / CLI | `tests/test_smoke.py`, `tests/test_cli_smoke.py` gitignored | same method |
| generator | `tests/test_generate_commands.py`, `tests/test_generator_regression.py`, `tests/test_command_renderer.py`, `tests/test_openapi_parser.py` gitignored | same method |
| `tests/conftest.py` | **gitignored** | same method |

So a fresh clone gets 240 test files but **no `conftest.py`**, and no test for `auth`, `config`,
`output`, or `cleanup`. The tracked top-level tests are dominated by **13 `test_drift_check_*`
modules** testing `tools/drift_check.py` — the coherence gate — rather than runtime behaviour.

### 15c. Recorded/mocked remote responses

`[verified]`

- **No cassettes, no fixture files.** `git ls-files 'tests/**' | grep -iv '\.py$'` returns
  **zero** results — every tracked file under `tests/` is Python. There is no VCR/betamax
  recording, no JSON fixture corpus.
- **33 tracked test files** use in-code stubbing
  (`grep -rln "unittest.mock\|monkeypatch\|responses\|vcr\|respx\|httpx_mock"`).
- `aiohttp` is stubbed with `aioresponses` in **6** tracked `migration/execute` modules — stated
  explicitly in `.github/workflows/ci.yml:~34`: *"aioresponses likewise: 6 tracked
  migration/execute modules import it to stub aiohttp. It is declared nowhere else."*
- CI must install `pytest`, `pytest-asyncio`, and `aioresponses` by hand
  (`.github/workflows/ci.yml`); none are declared in `pyproject.toml`. `aiohttp` is pinned in
  the workflow, not in `pyproject.toml`, with an in-file comment explaining the break is in
  `aioresponses 0.7.9` versus `aiohttp 3.14`, not in the CLI.

CI matrix: Python 3.11 and 3.12, on push to `main` and on PRs to `main`
(`.github/workflows/ci.yml:1-16`). Only two workflow files are tracked: `ci.yml`, `release.yml`.

---

## 16. Commit count and shape of history

`[verified]`

- **1,038 commits** (`git rev-list --count HEAD`).
- First commit `a356052` **2026-03-17** "initial: project scaffold with reference docs and
  skills"; HEAD `b578a52` **2026-08-04**. Roughly **4.6 months**, ~7.4 commits/day average.
- Files changed across the 1,008 commits carrying a shortstat: **7,787**
  (`git log --shortstat`, parsed).

### Bulk machine-generated batches — yes, plainly

**72 commits** mention regeneration (`git log --oneline | grep -ciE "regen|generator|generate"`),
and those commits account for **2,125 files changed** — **27% of all file-changes in the
repository's history** (method: for each matching commit hash, `git show --stat --format=''`,
take the summary line, sum the `N files changed` figure).

The largest commits are overwhelmingly regeneration or bulk-doc events. Top 12 by files changed:

| Files | Commit | Date | Subject |
|---|---|---|---|
| 199 | `e4dfb22` | 2026-04-17 | refactor: drop wxc_sdk dependency, replace with native httpx + Python |
| 182 | `751010c` | 2026-07-28 | feat(cli): real argument help, runnable examples, 28 renames, 8x faster |
| 179 | `37d299c` | 2026-04-29 | docs: add path-scoped rules, skill disambiguation, model selection |
| 170 | `60b27b7` | 2026-07-25 | chore(generator): regenerate with --fields, --generate-json-body, unif… |
| 163 | `1f1e19f` | 2026-04-18 | fix(generator): prioritize required fields in --json-body help examples |
| 153 | `274f52f` | 2026-07-29 | feat(paging): --all fetches every page, on every list command |
| 136 | `f28035b` | 2026-07-21 | chore(generator): keep full field descriptions in --help |
| 136 | `ed50ac5` | 2026-05-06 | chore: update 4 OpenAPI specs from upstream and regenerate |
| 124 | `2cf1883` | 2026-07-25 | chore(generator): regenerate with structured no-body results |
| 122 | `c5f1021` | 2026-07-06 | chore(repo): untrack internal docs/generator tests |
| 122 | `2bfe9f3` | 2026-03-20 | chore: add .gitignore, LICENSE, clean tracked artifacts from index |
| 120 | `e7fd6f3` | 2026-05-27 | fix: resolve 6 project maintenance items from audit |

**Consequence, stated for the record:** because 184 of the 454 tracked `src/wxcli` files are
regenerated wholesale by `tools/generate_commands.py`, **commit churn is not a valid proxy for
maintenance pain in this repo, and a later audit must not weight by it.** A single generator run
rewrites 100–180 files at once regardless of how much thought went into it.

Note on identifying generated files: the command modules carry **no auto-generated banner**
(`grep -l "Auto-generated\|AUTO-GENERATED\|Generated by"` over the 184 tracked modules returns
**1** file, and `head -8 src/wxcli/commands/call_queue.py` shows the file opens directly on
imports with no marker). Generated-ness is inferable only from the commit messages and from
`tools/generate_commands.py`, not from the files themselves. `[verified]`

---

## 17. Distribution and downstream users

`[verified]`

- **Published to PyPI as `wxcli`.** `pyproject.toml:6` `name = "wxcli"`; version is `dynamic`
  via `setuptools-scm` (`pyproject.toml:2-7`).
- Install paths documented at `README.md:57-65`: `pipx install wxcli` (recommended) or
  `pip install wxcli`. macOS, Linux, Windows; Windows instructions include installing
  Python 3.11+ and bootstrapping `pipx`.
- **Self-update path exists in-product**: `wxcli update` (`README.md:116-122`) detects pipx vs
  pip and upgrades accordingly, then deep-links release notes. `WXCLI_UPDATE_INDEX_URL` supports
  an internal mirror behind a firewall. Implementation `src/wxcli/commands/update.py`;
  update-notification logic `src/wxcli/update_check.py`, wired at `src/wxcli/main.py:40`
  (`maybe_notify_update`, suppressible with `--no-update-check`).
- Public repo: `https://github.com/achobgood/wxops` (Homepage, Repository, Issues, Changelog —
  `pyproject.toml` `[project.urls]`).
- License Apache-2.0; author `Adam Hobgood`; classifier
  `Development Status :: 5 - Production/Stable`; `Intended Audience :: System Administrators`
  and `:: Developers` (`pyproject.toml:9-53`).
- Requires Python `>=3.11`; **15 runtime dependencies** including `zeep` (SOAP/AXL),
  `aiohttp`, `networkx`, `phonenumbers`, `pydantic`, `httpx`, `typer>=0.20.0`, `click>=8.1`
  (`pyproject.toml:11-42`).
- A second, non-PyPI distribution channel: `wxcli-dist/` (4 tracked files —
  `assemble.py`, `codex/agents-md-sections.md`, `codex/config.toml`,
  `settings.bundled.json`) assembles the agent playbook bundle, and `src/wxcli/_playbook/`
  ships **129 tracked files** as package data. `wxcli init` writes them into a user folder.

**Signal about actual downstream users: none found in-repo.** No download counts, telemetry,
analytics, issue-tracker export, changelog of user reports, or `CONTRIBUTORS` file. Nothing in
the codebase phones home — the only network egress found is to `webexapis.com` and to PyPI for
the update check. **UNKNOWN** how many people install it. `[verified]` that no such signal is
committed.

---

## 18. Committed public contract, and stability statements

### 18a. What is committed as contract

`[verified]`

**Flags** — documented in `CLAUDE.md` under "Common Flags (`--fields`, `--output`, `--json-body`,
`--all`, `--verify`)" with per-flag semantics, and measured counts in the tracked source:

| Flag | Documented semantics | Occurrences in tracked `commands/*.py` |
|---|---|---|
| `--fields` | JMESPath applied to the response before rendering; on every generated command | present on generated commands (not separately counted) |
| `--output` / `-o` | `table\|json\|text` on every generated command, plus `id` on create | ditto |
| `--all` | fetch every page; overrides `--limit`; bounded at 1000 pages, `WXCLI_MAX_PAGES` | **516** |
| `--generate-json-body` | print body skeleton, exit before authenticating | **711** |
| `--verify` | re-read after write, diff only sent fields, never changes exit code | **332** (CLAUDE.md says 328) |
| `--force` | skip confirmation on delete | **179** |
| `--json-body` | inline JSON, `file://path`, bare path, or `-` | documented in CLAUDE.md |

**Output formats** — `table`, `json`, `text`, and `id` (create only). Rendering in
`src/wxcli/output.py` (227 lines) and `emit()` in `src/wxcli/common.py:189`.

**Stderr contract** — three documented behaviours in `CLAUDE.md`, all measured statements:
(1) a truncated single-page read prints `Note: N records returned and the server has more
pages. Re-run with --all…`, suppressible with `WXCLI_NO_PAGE_WARN=1`; (2) `--fields` reducing a
non-empty response to empty prints the unfiltered record count; (3) the `--calling-data`
interlock warns on stderr when `extension`/`locationId` is requested without it.

**Environment variables** as contract: `WEBEX_ACCESS_TOKEN`, `WXCLI_MAX_PAGES`,
`WXCLI_NO_PAGE_WARN`, `WXCLI_MAX_ATTEMPTS`, `WXCLI_UPDATE_INDEX_URL`.

**Command-group count** — `178 command groups` is published in both `README.md:16` and
`CLAUDE.md`, and is *machine-enforced*: `tools/drift_check.py` check 3 harvests three phrasings
(`N command groups`, `N CLI command groups`, bare `N groups`) from both files, compares against
a measured fresh-clone value, and independently flags the two files contradicting each other
(`tools/drift_check.py:17-25`).

**A mechanical contract gate exists.** `tools/drift_check.py` — "Drift gate — mechanical
coherence checks between specs, CLI, skills, and docs. Report-only by default (always exits 0);
`--enforce` exits 1 on any failure" (`tools/drift_check.py:1-4`). At least 20 numbered checks
(`CLAUDE.md` references checks 4, 19, 20). Checks read include: 1 spec↔CLI parity, 2 reference
existence (every `wxcli <group> <command>` token in skills/agents/rules/docs/README/CLAUDE.md
must resolve against the built CLI), 3 published counts, 4 unreferenced groups, 5 stale
overlays, 6 **flag existence** — every `--flag` cited after a resolvable command must be
accepted by that command. 13 tracked test modules test the gate itself.

**Exit codes are NOT documented as contract.** `grep -rn "exit code\|exit status\|Exit code"
README.md docs/*.md` returns **zero hits**, yet `tests/test_drift_check_exit_codes.py` is tracked
— the gate's own exit codes are tested, the CLI's are not published. `[verified]`

### 18b. Stability statements

`[verified]` **Nothing in `README.md` or `CLAUDE.md` is marked unstable or experimental.**
`grep -rn "unstable\|experimental\|deprecated\|breaking change" README.md CLAUDE.md` returns
exactly **one** hit, and it is a deprecation notice rather than an instability warning —
`CLAUDE.md:476`:

> The former hand-coded trio (licenses, locations, numbers) is retired — all three are generated
> modules now with the same orgId injection. `users` is an alias for the generated `people`
> group; `licenses-api` is a deprecated one-release alias for `licenses` (renamed 2026-07-02).

That establishes the project's observed deprecation policy: **a renamed group keeps an alias for
one release**. `[inferred]` from that single instance — it is not stated as a policy anywhere.

Counter-signal on stability: `pyproject.toml` classifies the project
`Development Status :: 5 - Production/Stable`, and version is `dynamic` from `setuptools-scm`
(git tags), so there is no hand-written semver commitment in the repo. No `CHANGELOG.md` is
tracked — the changelog URL points at GitHub Releases (`pyproject.toml` `[project.urls]`).

`CLAUDE.md` does record one *renaming* event with an explicit stability decision: the Phase 5
self-service group was folded into `my-call-settings` on 2026-07-29 and the old group name
`call-settings-for-me-phase-5` was **deliberately not aliased**, because an alias "would have
answered a different question with exit 0" (Known Issue #3). That is a documented, reasoned
break.

---

## Deferred observations

- 779 of 958 mutating commands have no confirmation gate; the gate is delete-only.
- `wxcli cucm execute` — the single largest-blast-radius command — has no confirmation, no
  `--force`, no `--dry-run` flag of its own, and no scope flag.
- `wxcli organizations delete` takes no argument; the org comes from resolved config.
- 956 of 958 mutating commands have no dry-run.
- Every error class exits 1; validation, auth, conflict, rate-limit, and network are
  indistinguishable to a script.
- No invocation log exists; `--debug` writes to stderr only and is per-command, not global.
- `tests/conftest.py`, `test_auth.py`, `test_config.py`, `test_output.py`, `test_cleanup.py`,
  and every generator test are gitignored — a fresh clone cannot exercise them.
- Zero tracked fixture/cassette files; all remote stubbing is in-code.
- CI installs `pytest-asyncio` and `aioresponses` by hand because they are declared nowhere.
- Generated command files carry no auto-generated banner, so a reader cannot tell hand-written
  from regenerated code without consulting the generator or git history.
- CLAUDE.md's `--verify` count (328) is 4 below the measured tracked figure (332).
- `wxcli cucm rollback-ops` performs no rollback; it only lists.
- `cleanup.py` has no 404 tolerance in its delete path.
- Exit codes are tested for the drift gate but published nowhere for the CLI.
