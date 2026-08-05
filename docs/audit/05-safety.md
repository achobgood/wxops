# 05 — Safety under agent operation *(both targets, reported separately)*

Phase 5 of `docs/arch/wxops-architecture-audit-prompt_2.md`. Extends
`docs/audit/00-context.md` Q1/Q2 (the six blast-radius classes and the guard the
generator already knows how to emit), `docs/audit/06-machinery.md` §5/§6/D13 (the
execute path's machinery) and `docs/audit/07-testability.md` §2.4/§2.5 (what is
pinned, measured by mutation).

Labels: `[verified]` = I ran or parsed something this session. `[inferred]` =
reasoned from evidence short of direct observation. `UNKNOWN` = not established.

**Target A** = the generated endpoint layer + the shared runtime. **Target B** =
`src/wxcli/migration/` plus its driving command `src/wxcli/commands/cucm.py`.
Reported in separate sections per HARD CONSTRAINT 6. **Target B is first**, per
HOW TO RUN item 4.

**Method.** `wxcli` never imported — the hook fired on one of my own scratch
scripts this session and I re-ran it as a pytest file outside the repo, which is
the sanctioned route (§2.7). `wxcli … --help` run only as a subprocess with
`COLUMNS=400`; **no mutating command was run and no live-org call was made.**
Structural counts are `ast` passes over `git ls-files`, never the working disk.
Two store-level behaviours were proven by executing them against a throwaway
SQLite database in the scratchpad. Targeted test files were run; the full suite
was not (project rule). Read coverage is stated in §5.

**Two fixes shipped this phase** — the two the brief deferred here — with the
tracked tests that pin them. Detail and the scope I extended, with reasons, in
§3. Everything else waits for the report.

---

## 0. What this phase overturns or sharpens

| Claim | Where | Measured here |
|---|---|---|
| `wxcli cucm execute` "has no gate at all" | audit spec KNOWN CONTEXT; `00-facts.md` Q10 | **True but understated.** The repository *has* a working stage-prerequisite gate — `_check_prerequisite` (`commands/cucm.py:272-282`) — and applies it to **six of six read/local stages** and to nothing that writes. `execute` is not absent from a gate that does not exist; it is the one stage **excluded from a gate that does** (§1.1) |
| A half-applied migration is indistinguishable from a not-yet-started one *at the operation level* | `06-machinery.md` D13 | **Worse at the project level, and reversible in the wrong direction.** A fully-applied migration can be *converted into* a not-yet-started one by `wxcli cucm plan` or `wxcli cucm normalize`, neither of which prompts, warns, or is gated. Proven by execution (§1.5) |
| `dry_run_all_batches` is a "partial parallel branch" — ordering genuinely shared, writes unestablished | `07-testability.md` §10 item / Phase 5 brief | **Finished: it certifies ordering and counts only.** It never resolves a handler, so it cannot say what will be sent, and its operation count is not the number of writes that will occur (§1.4) |
| There is no equivalent `wxcli` subcommand that lists bulk device jobs | `preflight/runner.py:302-308` (source comment) | **False since the rename wave.** `wxcli device-settings list-call-device-settings` (`commands/device_settings.py:1093`) hits that exact path. The probe still deviates from the subprocess convention, but for a different and narrower reason — `_run_wxcli` cannot carry an HTTP status (§3) |
| "`--verify` — on **328** update commands" | `CLAUDE.md`, *Common Flags* | **332** `[verified]`, reproducing `00-facts-independent-part2.md`. 328 of the 332 sit on ungated writes; the other 4 are the `accessCodes` PUTs gated on 2026-08-04. The coincidence of 328 in both places is arithmetic, not agreement |
| A `typer.confirm` on non-interactive stdin aborts — "is that failure legible, or does it look like an unrelated error the agent 'fixes' by adding `--force`?" | audit spec PHASE 5 item 2 | **The premise the question carries is wrong in the safe direction.** Measured against the real generated command with the network mocked out: closed stdin, empty stdin and an explicit `n` all abort with **exit 1 and zero API calls**. Click raises the *same* `Abort` for EOF as for "no", so a non-interactive run is treated as a refusal. What is missing is not safety but the **recovery instruction** — the entire output is the prompt echo plus `Aborted!`, naming no flag (§2.2) |
| `device-settings create-apply-line-key-template` is the command carrying `--force-delete` | this document's own Phase 5 brief lead 5 (my briefing of the worker) | **Wrong group.** The inverse-semantics flag is on `location-settings create-delete-calling-location` (`location_settings.py:1218`), which `00-context.md` Q1 class 3 already cited correctly. That command has **no `typer.confirm` at all**, so there is no local prompt for a `force`-named flag to bypass (§2.3) |

One prior claim is **confirmed, not overturned**, and stated here because the
brief asked for it explicitly: **concurrency cannot race the dependency order.**
`06-machinery.md` §4 established it structurally and proved it with
`test_cascade_and_retry.py` (18/18) and
`test_bulk_serialization.py::test_serialized_ops_do_not_overlap`. Both ran again
in this session's `tests/migration` run (3,105 passed). The answer is good and I
did not re-test it.

---

## 1. TARGET B — `wxcli cucm execute`

The single highest-consequence command in the repository: hand-written,
asynchronous, 20-way concurrent by default, writing to a live customer org,
running unattended, and — per `07-testability.md` §2.5 — able to have its entire
notion of failure removed with 3,580 tests and the drift gate both green.

### 1.1 The gate exists. It is applied to every stage except the ones that write.

`[verified]` This is the finding the "no gate at all" framing misses.

`commands/cucm.py` defines a real prerequisite gate:

```python
STAGE_PREREQUISITES: dict[str, str] = {
    "discover": "init",   "normalize": "discover",  "map": "normalize",
    "analyze": "map",     "plan": "analyze",        "preflight": "plan",
}                                                    # cucm.py:67-74

def _check_prerequisite(project_dir: Path, stage: str) -> None:
    """Abort if the prerequisite stage hasn't been completed."""
    ...
    raise typer.Exit(1)                               # cucm.py:272-282
```

Callers, all six of them: `discover` (`:1159`), `normalize` (`:1348`), `map`
(`:1460`), `analyze` (`:1563`), `plan` (`:1612`), `preflight` (`:1727`)
`[verified]`. Three more commands carry a hand-rolled equivalent against
`_completed_stages`: `report` (`:3309`), `user-diff` (`:3437`), `user-notice`
(`:3505`), each refusing to run before `analyze`.

**`execute` (`:3149`) and `retry-failed` (`:3245`) call neither.** There is no
`execute` key in `STAGE_PREREQUISITES`; `PIPELINE_STAGES` (`:64`) ends at
`preflight`; and `grep` for `state`, `preflight`, `_require_stage` or `stage`
inside `cucm.py:3149-3242` returns nothing, reproducing `06-machinery.md` §5.

So the shape is not "this tool has no gates." It is:

> **`wxcli cucm report` — which writes an HTML file — refuses to run until
> `analyze` has completed. `wxcli cucm execute` — which writes to a live
> customer org, concurrently, unattended — refuses to run after nothing.**

Adding `"execute": "preflight"` to `STAGE_PREREQUISITES` and one
`_check_prerequisite(project_dir, "execute")` call is a two-line change that
makes preflight blocking, using machinery already written, already tested, and
already carrying a legible error message. It is **not** shipped here — see §3 for
why (it changes the operator-visible contract of the highest-consequence command,
and `mark-complete`/`retry-failed` recovery flows need to be checked against it
first). It is remediation item 1.

### 1.2 Is the ungated design deliberate? — Partly. The approval record exists, `execute` does not read it.

`[verified]` The brief asks for a design record and says a defensible answer
exists. **Both halves are true, and they are separate records.**

**What is deliberate and recorded.** `migration/execute/CLAUDE.md:374-418`
carries a dated design note (2026-07-29) on `execute` exiting 0 with `Failed: N`
— reasoned, measured over both callers, and correct on its own terms.
`06-machinery.md` §6.3 agrees and so do I. **That note is about the exit code.
There is no design record anywhere for the absence of a confirmation gate or a
prerequisite check.** I looked in `migration/execute/CLAUDE.md`,
`migration/CLAUDE.md`, `docs/architecture/`, `docs/plans/cucm-pipeline*`, and
`.claude/rules/cucm-migration.md`. **Report: there isn't one.**

**Where the approval actually lives.** Two artifacts, both real:

1. **The `decisions` table** (`migration/store.py:104-117`) carries
   `chosen_option`, `resolved_at`, `resolved_by` — a durable, per-decision,
   attributed approval record, written by `store.resolve_decision`
   (`store.py:565-573`) from `wxcli cucm decide` (`cucm.py:2281`) and by
   auto-rules (`transform/rules.py:249-261`, `resolved_by="auto_rule"`).
2. **The `cucm-migrate` skill**, which *does* ship
   (`src/wxcli/_playbook/.claude/skills/cucm-migrate/SKILL.md`, tracked)
   `[verified]`. Its step 4b tells the operator: *"1. Preview the execution plan:
   `wxcli cucm dry-run` … 2. Show the admin the dry-run summary … Get explicit
   confirmation to proceed. 3. Execute."* and its Critical Rules 1 and 2 are
   *"Preflight is mandatory. No override or bypass"* and *"Always show plan
   summary and get approval. Wait for explicit 'yes'."*

**So the defensible answer is available — and `execute` verifies neither record.**

- `grep` for `decision` across `migration/execute/engine.py` and
  `execute/runtime.py` returns **zero hits** `[verified]`. The approval record is
  consumed at `plan` time, by `planner.py:_build_decisions_index` (`:357`) — and
  the plan it produces is then drained by `execute` without re-reading it.
- The one pending-decision block in the planner is **construct-scoped and
  single-type**: an unresolved `CROSS_SITE_DEPENDENCY` suppresses its construct
  (`execute/CLAUDE.md:273-281`). Every other decision type gates only on a
  *resolved* `skip`.
- And the escalation is **opt-in**: `plan --fail-on-unresolved` defaults to
  `False` (`cucm.py:1599-1606`); the default is *"WARN and continue"*, stated in
  its own help text.
- `plan` computes `has_pending` and transitions `ProjectState` to `BLOCKED`
  (`cucm.py:259`) — and then immediately transitions `BLOCKED → PLANNED`
  (`:265-267`), which `state.py:48` permits. **`BLOCKED` is a state the project
  passes through, not one it rests in.**

**The state machine confirms it from the other side.** `ProjectState` declares
`SNAPSHOTTED`, `EXECUTING`, `FAILED`, `VALIDATING`, `COMPLETED`, `ROLLED_BACK`
(`state.py:32-37`) with valid transitions between them (`:52-57`). `grep` over
`src/` for every one of those six names returns **no producer** — the only hits
outside `state.py` are the enum copy in `models.py:39,43` and unrelated prose
`[verified]`. **Nothing in the tool ever advances a project past `PREFLIGHT`.**
So after a complete, successful migration, `wxcli cucm status` still reports
`State: preflight`. `SNAPSHOTTED` is particularly telling: the state machine
names a pre-write snapshot step, and `00-context.md` Q2 established there is no
pre-write snapshot anywhere in the repo.

**Judgment.** The gate genuinely lives upstream, and upstream is a **prompt
file**. That is a real control when the operator is the `/cucm-migrate` skill,
and it is *no* control when the operator reaches `wxcli cucm execute` any other
way — which the same playbook makes easy, because `CLAUDE.md` documents `wxcli
cucm execute` and `retry-failed` directly. An LLM whose only specification is
`--help` sees a command whose docstring says *"Run 'wxcli cucm dry-run' first to
preview the execution plan"* and nothing that stops it from not doing so. The
approval that *was* recorded — `decisions.resolved_by` — is the one thing
`execute` could cheaply check and does not.

### 1.3 What stops an operator running `execute` without ever running `dry-run`? — Nothing, and dry-run leaves no trace to check.

`[verified]` Two facts compound:

1. **No ordering is enforced.** §1.1: `execute` calls no prerequisite check of
   any kind. The advice lives in the docstring (`cucm.py:3157-3162`) and in the
   skill.
2. **Even a gate could not check it.** `dry_run_all_batches` runs entirely inside
   a SQLite `SAVEPOINT` that is unconditionally rolled back
   (`runtime.py:397, 436-438`), and `dry-run` calls no `_mark_stage_complete`.
   **A dry-run leaves no evidence it ever happened** — not in `state.json`, not
   in `plan_operations`, not in `journal`. Any future "did you dry-run first?"
   check would have to introduce the record as well as the check.

### 1.4 What `dry-run` actually certifies — ordering and counts. Not the writes.

`[verified]`, finishing the question `07-testability.md` handed forward.

The real path and the dry path diverge at the one step that decides what goes on
the wire:

| | `execute_all_batches` (`engine.py:876-964`) | `dry_run_all_batches` (`runtime.py:375-446`) |
|---|---|---|
| Batch selection | `get_next_batch(store)` | `get_next_batch(store)` — **same function** |
| Handler resolution | `HANDLER_REGISTRY.get((resource_type, op_type))` (`:891`) | **never called** |
| Request construction | `calls = handler(op["data"], op["resolved_deps"], ctx)` (`:900`) | **never called** |
| Per-op output | `(method, url, body)` tuples | `{node_id, resource_type, op_type, description, resolved_deps}` — five DB columns (`:411-417`) |
| API-call count | `len(calls)`, computed | `plan_operations.api_calls`, a planner *estimate* from `API_CALL_ESTIMATES` (`:405-410`) |

`grep` for `engine|execute_all_batches|execute_single_op|aiohttp|HANDLER_REGISTRY`
over `runtime.py` returns nothing `[verified]`, confirming and completing Phase
7's partial result.

**So the batch ordering is genuinely the same logic** — that half of Phase 7's
answer holds and is a real strength. **Everything downstream of the handler is
unmodelled**, and three consequences follow that an operator reading the dry-run
output would not expect:

- **The operation count is not the write count.** Three handler outcomes are
  decided by *calling the handler*, and dry-run calls none of them: a
  `SkippedResult` (hard prerequisite missing → op skipped, dependents cascaded),
  an empty `[]` (legitimate no-op → op completed with zero API calls), and a
  missing registry entry (→ op **failed** immediately, `engine.py:893-897`). All
  three appear in the dry-run listing as ordinary operations.
- **`~N API calls` is an estimate, not a measurement**, and so is the
  `~M min at 100 req/min` derived from it (`cucm.py:3136-3143`).
- **It cannot answer "what will you send?"** — the question a human reviewing a
  migration plan is actually being asked to approve. It answers "in what order,
  and roughly how many."

That is not a drift risk in the sense the spec anticipated (the two paths cannot
disagree about ordering, because they share the function). It is a **scope**
gap, and it matters most at exactly the moment the skill uses it: as the artifact
shown to a human for approval before an irreversible bulk write.

### 1.5 The execution record is destroyed by two ungated, unprompted commands *(new, Critical)*

`[verified] by execution` — proven against a throwaway SQLite store in the
scratchpad, not read off the source. Transcript in §5.

`plan_operations` is the only durable record of what the migration wrote to
Webex: `status`, `webex_id`, `error_message`, `completed_at`, `attempts`
(`store.py:145-160`). `execute/` issues **no DELETE anywhere** (`00-context.md`
Q1 class 2), so nothing in this tool can clean up a remote object whose id it has
forgotten.

**Two commands delete that table, unconditionally.**

**(a) `wxcli cucm plan`** → `save_plan_to_store` opens with:

```python
# Clear existing plan (edges first — FK constraint)
conn.execute("DELETE FROM plan_edges")
conn.execute("DELETE FROM plan_operations")     # batch.py:174-175
```

Its docstring calls this *"idempotent re-planning"* (`batch.py:167`). It is
idempotent with respect to the **plan** and destructive with respect to the
**execution record**. There is no guard: `grep` for `already executed`,
`status = 'completed'`, `completed_at IS NOT NULL` or `webex_id IS NOT NULL`
across `cucm.py` and `batch.py` returns nothing `[verified]`. `plan`'s only
prerequisite is `analyze`, which a completed migration satisfies.

Measured:

```
after a successful execute:     status=completed webex_id=Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzEyMw
rollback-ops sees:              1 completed create(s)
after `wxcli cucm plan` re-run: status=pending    webex_id=None
rollback-ops now sees:          0 completed create(s)
```

**(b) `wxcli cucm normalize`** → `store.clear_all()` (`cucm.py:1365`), which is
every table in the database:

```python
for table in ["plan_edges", "plan_operations", "merge_log",
              "decisions", "journal", "cross_refs", "objects"]:
    cursor = self.conn.execute(f"DELETE FROM {table}")   # store.py:446-452
```

Measured:

```
before `normalize`: {'plan_operations': 1, 'decisions': 1, 'objects': 1, 'journal': 0}
after  `normalize`: {'plan_operations': 0, 'decisions': 0, 'objects': 0, 'journal': 0}
clear_all() returned (discarded by the caller): {..., 'plan_operations': 1, 'decisions': 1, ...}
```

`clear_all` returns per-table counts and **the caller discards them**
(`cucm.py:1365` is a bare statement). `normalize` prints
`Normalization complete in N s` and nothing else. Its prerequisite is `discover`,
which every project past stage 2 satisfies, and `_invalidate_downstream` treats
re-running `normalize` as an ordinary operation (`:1349`).

**Why this outranks D13.** D13 says an op killed mid-flight is indistinguishable
from one never attempted — one operation, on a crash. This says **every**
operation of a **completed** migration can be reset to `pending` by a command
that reads as a local transform, with no confirmation, no `--force`, no warning,
and no `--dry-run`. The next `wxcli cucm execute` then re-issues the entire plan
against an org that already has all of it (§1.6 for what happens then), and the
operator decisions with their `resolved_by` attribution are gone too.

**What the operator's only specification says.** Measured with
`COLUMNS=400 wxcli cucm <cmd> --help` `[verified]`:

- `plan` — *"Expand objects to operations, build dependency DAG, partition into
  batches."*
- `normalize` — *"Run pass 1 normalizers + pass 2 cross-reference builder."*

Neither mentions deletion, and `normalize` has no options at all beyond
`--verbose` and `--project`. An LLM reading only `--help` has no way to know
that either command destroys the migration's record of what it wrote to the
customer's org.

**The asymmetry, stated plainly.** `wxcli cleanup run`, which deletes remote
objects, prints the only consequence-bearing confirm string in the codebase —
`Delete {total} resources? This cannot be undone` (`cleanup.py:1255-1258`).
`wxcli cucm normalize`, which deletes the only record of what was created
remotely, prints nothing.

**Bounded, in fairness.** The loss is local. The remote objects survive; what is
destroyed is the mapping to them, and `rollback-ops` — the tool's only rollback
affordance — reads that exact table (`cucm.py:3056` → `runtime.py:333`), so it
silently returns
`No completed create operations to roll back` afterwards. The skill's own re-run
recipe knows the shape of this (step 4b item 0 tells the operator to tear down
the org *first*, then re-`plan`), which is evidence the hazard was understood at
the prompt layer and never expressed in code.

### 1.6 Idempotency and resumability — counted

The brief asks whether a re-issued create actually duplicates, per resource type.
Answered as far as the repository can answer it, and marked `UNKNOWN` where it
cannot.

`[verified]` by `ast` over `HANDLER_REGISTRY` (`handlers.py:2322`) and by reading
`_try_find_existing` (`engine.py:612-712`):

| | count | types |
|---|---:|---|
| Resource types with a `create*` op | **21** | |
| — covered by 409 auto-recovery | **8** | `user`, `location`, `translation_pattern`, `trunk`, `dial_plan`, `operating_mode`, `schedule`, `line_key_template` |
| — recovery **explicitly declined** | **6** | `call_park`, `pickup_group`, `paging_group`, `hunt_group`, `call_queue`, `auto_attendant` — *"Skip recovery — let cascade handle it on next run"* (`engine.py:693-698`) |
| — **no branch at all** | **7** | `dect_network`, `device`, `route_group`, `route_list`, `virtual_line`, `voicemail_group`, `workspace` |

So **13 of 21 create-capable types have no 409 recovery**, and for those a
re-issued create either 409s into a hard failure (with cascade skip of every hard
dependent) or produces a duplicate remote object. **Which of the two, per type,
is `UNKNOWN`** — it depends on per-endpoint uniqueness enforcement in Webex, and
settling it requires a live create against a live org, which this phase did not
and could not do. Two specific notes rather than a blanket:

- `device:create` is keyed on MAC and the platform rejects a MAC already in use
  (error 2011), so a duplicate is `[inferred]` unlikely there — but
  `device:create_activation_code` carries **no MAC** (`execute/CLAUDE.md`, Tier
  2-3), so a re-issue mints a *second* activation code with the first still
  outstanding.
- The eight recovered types are recovered by `items[0]` **with no name-equality
  check** (`engine.py:704-706`, `06-machinery.md` D8), and those branches never
  execute in any test (`07-testability.md` §2.4). So "covered" here means "a
  recovery path exists", not "a recovery path is known correct."

**What the fix shipped this phase does and does not do.** Writing `in_progress`
before dispatch (§3) makes a killed run *visible* — `reset_in_progress` now
returns a non-zero count and the `Reset N in-progress ops to pending` line
becomes reachable for the first time. It does **not** stop the re-issue, and it
should not: with no DELETE available and 13 types unrecoverable, refusing to
proceed would strand the migration. The right behaviour is what now happens —
reset and re-attempt — plus disclosure. The disclosure is currently a **count**,
not the node ids, and those node ids are precisely the operations that may have
half-applied. Remediation item 4.

### 1.7 `completed` means "2xx", not "applied" — there is no read-back anywhere

`[verified]` `plan_operations.status='completed'` is written from
`result.success`, i.e. `200 <= status < 300` (`engine.py:143-145`, `:906`).
Nothing re-reads the resource. `execution-status` (`cucm.py:2937`) and `status`
(`:808`) both read the store only; `grep` for a post-execution Webex read across
`execute/` returns nothing.

The repository knows this is not enough, in two places, and neither applies here:

- `--verify` on **332** generated update commands (§2.5) exists because, in its
  own docstring, *"A 2xx proves the request was WELL-FORMED, not that the
  configuration is right"* (`common.py:139-142`), with the worked case being
  `device-members`, which does no port validation and returns 200 for a
  two-`PRIMARY` layout.
- The engine's own Fix #18 (`engine.py:172-178`) already treats a 2xx with no
  `id` in the body as a **failure**, *"Some backends return 200/204 without a
  body on server-side hiccups — the resource may not exist."*

So the single-write path has a read-back convention and a documented reason for
it, the bulk write path issues orders of magnitude more writes, and the bulk path
has none. That is the parity gap, not the absence of the idea.

### 1.8 The `journal` table is the audit trail that isn't

`[verified]`, confirming lead 7 from source.

`migration/store.py:120-130` declares
`journal(timestamp, entry_type, canonical_id, resource_type, request, response,
pre_state)` — exactly the shape a write-path audit log needs, including the
pre-write snapshot column `00-context.md` Q2 says does not exist anywhere.

- **Two writers, both read-only discovery**: `entry_type="file_ingestion"`
  (`commands/cucm.py:1217`) and `entry_type="discovery_complete"`
  (`migration/cucm/discovery.py:251`).
- **`pre_state` is passed by no caller.** `add_journal_entry` accepts it
  (`store.py:756`, serialised at `:774`); `grep` over `src/` finds no call site
  that supplies it.
- **Nothing in `execute/` writes it at all.**
- And `clear_all` deletes it (§1.5), so even the discovery entries are not
  durable across a re-normalize.

This is the natural home for the record that would make D13, D8 and §1.5
diagnosable after the fact — `request`/`response` per operation would answer
"what did we send", and `pre_state` on a PUT would answer "what was there
before", which is the missing half of every reversibility question in
`00-context.md` Q2. It is also the substrate Phase 1 asks for, one layer down.
Remediation item 3.

**One structural obstacle worth naming now**, because it changes the cost:
`journal.canonical_id` is a foreign key into `objects` and the connection runs
`PRAGMA foreign_keys = ON` (`store.py:129`, `:732-748` — the repo already
maintains a sentinel-row helper for system-scoped entries). Bulk-job ops carry
synthetic canonical_ids, which `save_plan_to_store` already handles with an
`INSERT OR IGNORE` placeholder (`batch.py:185-192`), so the pattern exists.

### 1.9 Scope containment on the write path

`06-machinery.md` D9 established Target B's version and I did not re-derive it: a
malformed or unreadable `~/.wxcli/config.json` takes the `except Exception: pass`
branch at `commands/cucm.py:3187-3196`, `ctx` has no `orgId`, and **every write
the migration makes goes out unscoped** — resolved server-side to whatever org
the token defaults to. On a partner token that is a first-class supported mode
(`wxcli switch-org`), so it is not a hypothetical.

Phase 5's addition is the comparison with Target A, because it inverts the usual
direction: **Target A fails loudly here and Target B fails silently.**
`config.load_config` (`config.py:7-11`) lets `json.JSONDecodeError` propagate.
Same file, same key path, same failure — one crashes, one writes to the wrong
org. §2.6 has the Target A numbers.

### 1.10 Errors as control surface

Established in `06-machinery.md` §6 and not re-derived. The four answers the
spec asks for, with citations:

- **Do failures name the flag and value that was wrong?** No. Target B never
  imports `errors.py` (§2.3 there), so none of `decode_id_kind`, the five
  errorCode tips, the seven status tips or `_truncate_html` apply. An error is
  `f"{resp_status}: {error_msg}"` (`engine.py:205-210`), and a non-JSON body
  becomes the literal string **`500: {}`**.
- **Are validation / transient / remote-rejection distinguishable?** Not by exit
  code — `execute` exits 0 on every outcome. Within the store they are partly
  distinguishable: `failed` vs `skipped` vs cascade-skipped is a real and useful
  three-way split (`runtime.py:191-232`). What is *not* distinguishable is
  transient from permanent: B retries 429 only, so a single 503 fails the
  operation outright and cascade-skips every hard dependent (D1).
- **Structured or prose?** Prose, on **stdout** (`06-machinery.md` §6.4) — the
  inverse of Target A's convention, on the one command an operator is most likely
  to pipe.
- **Does any error path exit 0?** Yes, by design and with a design note I agree
  with (§6.3 there). The defect is the undisclosed asymmetry against `preflight`
  in the same command group, which `--help` does not mention on either side. This
  phase narrowed that asymmetry from two directions: `preflight` now also exits
  non-zero on `INCOMPLETE` (§3), making it a stricter gate, while `execute` is
  unchanged.

**Token and PII**: the token is not reachable in error output; PII is, and is
persisted to `plan_operations.error_message` and read back by `execution-status`
(`06-machinery.md` §6.5). Not re-derived. One addition from §1.5: that column is
also silently deleted by `plan` and `normalize`, which is the only "retention
policy" the PII currently has.

### 1.11 Target B severity

Severity by consequence and reachability, per the spec's Target B model.

| # | Finding | Severity | Reachable how |
|---|---|---|---|
| B1 | `plan` / `normalize` destroy the execution record with no gate, prompt or warning (§1.5) | **Critical** | Any re-run of two ordinary pipeline stages after a successful execute. Prerequisites already satisfied |
| B2 | `execute` is excluded from the prerequisite gate applied to all six read stages (§1.1) | **Critical** | Every invocation. Preflight is advisory in code and MANDATORY in the prompt |
| B3 | 13 of 21 create types have no 409 recovery; a re-issue duplicates or hard-fails (§1.6) | **High** | Any retry after a crash, a `retry-failed`, or B1 |
| B4 | `completed` means 2xx; no read-back exists on the bulk path while 332 single-write commands have one (§1.7) | **High** | Every completed operation |
| B5 | `dry-run` certifies ordering and counts, not writes — and is the artifact shown to a human for approval (§1.4) | **High** | The documented approval step |
| B6 | The approval record exists (`decisions.resolved_by`) and `execute` never reads it; `BLOCKED` is passed through (§1.2) | **Medium** | Any plan with unresolved decisions and `--fail-on-unresolved` unset (the default) |
| B7 | `journal` is an audit-log schema written only by read-only stages; `pre_state` has no caller (§1.8) | **Medium** | Always — it is an absence |
| B8 | No `run_id` on `plan_operations`, so two `execute` invocations are indistinguishable (`06-machinery.md` §4) | **Medium** | Any multi-pass migration, i.e. the documented normal case |
| B9 | Nothing records that a dry-run happened, so the ordering can never be checked (§1.3) | **Low** | Precondition for any future fix to B5 |

B1 and B2 are the two that change what an operator can recover from. Everything
else is diagnosis quality.

---

## 2. TARGET A — the generated write surface

Starting from the measured shape, per the spec's instruction: **958 mutating
commands, 203 gated, 755 ungated.** I reproduced all three independently by
`ast` over `git ls-files src/wxcli/commands/` this session, detecting the gate as
an `ast.Call` whose `func.attr == "confirm"` rather than by substring — a
substring test over the dumped function (`"typer" in d and "confirm" in d`)
returns **208** gated, over-counting by 5 on commands where the word appears in
help text. The AST figure of 203 (179 DELETE + 24 non-DELETE) matches
`00-context.md` exactly, which is now the fourth independent measurement of the
958/179/755 triple `[verified]`.

### 2.1 The class Phase 0's fix could not reach: writes that destroy by omission

`[verified]` — measured by a worker, **every load-bearing claim re-verified here
against the spec files and against live `--help`** before being written down.

**The question**, replacing the settled DELETE-proxy one: of the 755 ungated
writes, which destroy state? A PUT that submits a whole collection replaces it,
so members not listed are removed. This class is invisible to both signals
`classify_real_semantics` uses — the summary verb is *"Update"* or *"Modify"*,
and no body field is delete-shaped.

**The repository already documents the hazard, for four resource types, in the
hand-written half.** `migration/execute/handlers.py:2270-2273`:

> *"**Never writes a partial list.** These endpoints replace the whole array, so
> a short list would DELETE members rather than add the missing ones, including
> any an operator added by hand."*

That comment covers `hunt_group`, `call_queue`, `pickup_group` and
`paging_group` — the four the migration engine happens to reconcile. The
generated surface has the same hazard on **38 more operations that the migration
code never had to think about**, and no equivalent note anywhere.

**Counted.** Over the nine tracked specs, restricted to PUT/PATCH (a POST cannot
replace a collection that does not exist yet):

| Stage | count |
|---|---:|
| Ungated PUT/PATCH operations examined | 380 |
| — carrying a top-level body array of identifiable items | 91 |
| — minus delta-instruction arrays (item schema **requires** `action: ADD\|DELETE`) | 83 |
| — **confirmed collection-replace hazards** (shape + a read of each description) | **42** |
| — of the 42, **vendor prose explicitly states replace-not-merge** | **4** |

**The four prose-confirmed, quoted verbatim — I read all four out of the spec
files myself** `[verified]`:

| Command | Spec path | Vendor sentence |
|---|---|---|
| `scim-groups update` | `PUT /identity/scim/{orgId}/v2/Groups/{groupId}` | *"Replace the contents of the Group."* |
| `scim-users update` | `PUT /identity/scim/{orgId}/v2/Users/{userId}` | *"The PUT API replaces the contents of the user's data with the data in the request body. All attributes specified in the request body will replace all existing attributes…"* |
| `location-settings update-directories` | `PUT /telephony/config/locations/{locationId}/receptionistContacts/directories/{directoryId}` | *"This modification will replace the existing list of contacts with the new incoming contacts list from the request body. **The API does not support incremental updates.**"* |
| `hot-desking-members update` | `PUT /telephony/config/people/{personId}/features/hotDesking/members` | *"The request replaces the hot desking profile member list with the members supplied in the request body."* |

**The last row is the finding in miniature.** It is the *fifth* instance of
exactly the shape `handlers.py:2270` was written for — vendor prose and all — and
the migration code's careful `skipped(reason)` guard does not cover it, because
that guard was written per-resource-type rather than for the class.

**The eight exclusions are the reason to trust the 42.** Arrays whose item
schema *requires* a delta verb are not replace hazards: omitting an existing
member leaves it untouched. Excluded: `PATCH /groups/{groupId}`, both SCIM
PATCHes, `PUT …/routeLists/{id}/numbers` (`required: [number, action]`),
`PUT …/devices/{id}/dynamicSettings`, `PUT …/supervisors/{id}`
(`required: [id, action]` — the shape `CLAUDE.md` Known Issue #8 already
documents), and `PUT …/{people|workspaces}/{id}/numbers`. Two prose regex hits
were also excluded on reading (`POST …/jobs/person/moveLocation` and
`POST …/personalMeetingRoom/refreshId` are targeted batch jobs, not stored
collections). **The corroborating evidence is the CLI's own help text**:
`call-routing update-numbers` carries `--delete-all-numbers` whose help reads
*"If present, the numbers array is ignored and all numbers in the route list are
deleted"* — the API needed a **separate flag** to get replace-all behaviour,
which is the inverse of the hazard.

**Highest blast radius among the 42**, ordered:

| Command | Array | What one call can unlink |
|---|---|---|
| `scim-groups update` | `members` | An entire SCIM directory-group roster, org-wide, no documented cap |
| `cc-user-profiles update` | `permissions`, `resourceCollections` | One CC permission profile shared by many agents — strips permissions for everyone assigned it |
| `call-routing update-route-groups` | `localGateways` | Which trunks a route group forwards PSTN traffic through |
| `hunt-group update` / `call-queue update` | `agents`, `alternateNumbers` | Full agent roster and assigned DIDs |
| `announcement-playlists update-playlists` | `locationIds` | Which locations a music-on-hold playlist is assigned to — can span every location |
| `device-settings update` | `members` | Shared-line members on a device |
| `location-settings update-directories` | `contacts` | A shared receptionist-client contact directory |
| `cc-queue update-contact-service-queue` | `agents`, `queueSkillRequirements` | CC queue roster plus its skill links |

**Every one of them is invisible in `--help`.** Confirmed live on five
`[verified]`: `tools/command_renderer.py:1621` —
`if bf.field_type in ("object", "array") or param in used_names: continue` —
drops every array and object body field from the flag surface, so the hazardous
field is reachable only through `--json-body`.

**Two commands are the extreme case, and I re-ran both myself** `[verified]`:
`wxcli device-settings update` and `wxcli hot-desking-members update` have
**zero scalar flags**. Their entire option set is `--generate-json-body`,
`--json-body`, `-o`, `--fields`, `--verify`, `--debug`, `--help`. The whole
semantic surface of each command is one array that replaces a collection, and
the docstring says *"Update Members on the device."* An operator reading `--help`
learns the command exists and nothing about what omitting a member does.

**Could the generator detect this?** Counted on the corpus, not guessed:

| Detector | hits | true positives | false-positive rate |
|---|---:|---:|---|
| Array with id-bearing items **or** a member-vocabulary name | 91 | 42 | **53.8%** |
| + exclude delta-verb-required items | 83 | 42 | **49.4%** |
| Curated ~35-word member vocabulary + delta exclusion | 26 | 26 | **0%** — but **62% recall** |

Neither pure signal is good enough: vocabulary is high-precision/low-recall
(misses `localGateways`, `resourceCollections`, `dynamicSkills`, `coHosts`,
`interpreters`, `audioFiles`, `executives`, `queueSkillRequirements`,
`addressBookEntries`, `outdialANIEntries`), shape is the reverse. **The signal
worth building is already half-built in this generator for another purpose**:
`_spark_id_kind` (`tools/command_renderer.py:653-673`) decodes a spec example's
base64 `ciscospark://us/<KIND>/…` URN to name the object kind, and 71 distinct
KINDs are already decoded that way for argument help. *"Does this array's item
schema reference an existing remote object of a known KIND"* is a far better
question than *"is the property called `agents`"*, and it reuses code that
already ships.

The prose scan is the cheaper immediate win and needs no new machinery at all:
four operations state replacement in the vendor's own words, and the generator
already reads `description` (`tools/openapi_parser.py:694`).

**One honest limit.** The worker's independent denominator was **778** ungated
PUT/PATCH/POST *spec operations* against my **755** ungated *commands* — a +23
gap they investigated and left `UNKNOWN` rather than explaining away. Those are
different units (operations vs. rendered commands, before the 154 deliberate
skips and tag merges), so the gap is expected in direction but not reconciled in
size. **Every individual operation above is verified against its spec file and,
for the five checked live, against its generated command.** Read the ratios
(42/380, 53.8%) as operation-level and approximate; read the operations as exact.

### 2.2 Is the gate reachable without a TTY? — Yes, and it fails safe. This overturns the spec's premise.

`[verified]` by experiment, run twice by two methods, and the source claims
re-checked here.

The spec asks *"what actually happens when the operating LLM runs a delete with
no TTY, and whether that failure is legible or looks like an unrelated error the
agent 'fixes' by adding `--force`."* The implied worry — that the abort is a
confusing failure — is **half right, and the important half is wrong**.

**Measured against the real generated command.** `wxcli.main.app` driven through
`typer.testing.CliRunner` with `wxcli.commands.locations.get_api` patched to a
`MagicMock` so no HTTP call is possible, invoking `locations delete loc-123` with
no `--force` (typer 0.27.1 / click 8.3.2):

| stdin | exit | `rest_delete` called | stdout | stderr |
|---|---:|---|---|---|
| none (default) | **1** | **False** | `Delete loc-123? [y/N]: ` | `Aborted!\n` |
| `""` (empty) | **1** | **False** | `Delete loc-123? [y/N]: ` | `Aborted!\n` |
| `"n\n"` | **1** | **False** | `Delete loc-123? [y/N]: n\n` | `Aborted!\n` |
| `"y\n"` | 0 | True | prompt + the JSON result | — |

A standalone Typer app reproducing the generated shape gives identical semantics
under real subprocess conditions (`stdin=DEVNULL`, empty pipe, `y`, `n`).

**So the gate is real in the operator's actual mode.** Closed stdin, empty
stdin, and an explicit `n` all abort with exit 1 and **zero API calls**. The
mechanism is `click/termui.py`: `input()` raises `EOFError` on closed or empty
stdin, which is caught and re-raised as `click.Abort()` — the *same* exception an
explicit `n` produces. **A non-interactive invocation is indistinguishable from a
user who said no, and that is the safe direction.**

**One correction the worker found and I re-verified.** A bare `typer.Typer()`
prints `Aborted.` (Rich-styled); the real CLI prints `Aborted!`. `main.py:19`
sets `rich_markup_mode=None if plain_mode() else "rich"`, and `plain_mode()`
returns `not sys.stdout.isatty()` (`output.py:19-20`) — **true for every
invocation the LLM operator makes**, so typer falls through to Click's plain
`Aborted!`. Semantics identical; only the string differs. Recorded because a
report that quoted the wrong string would be quoting a condition the operator is
never in.

**The legibility judgment, which is where the defect actually is:**

- **Exit code does not discriminate.** Abort exits 1; `handle_rest_error` exits 1
  (`errors.py:203`); `handle_network_error` exits 1 (`errors.py:225`). Three
  different failure classes, one code. A Click *parse* error is distinguishable —
  exit 2 plus a `Usage:` line.
- **Text does discriminate, if you know to look.** Every REST and network failure
  prints `Error: …` as its first stderr line (`errors.py:189`, `:223`, both
  hard-coding the literal prefix) `[verified]`. The abort path never emits the
  word `Error`. So `"Error:" in stderr` is a reliable abort-vs-failure test —
  **and nothing in the abort output tells a reader that test exists.**
- **Nothing names the fix.** The complete output is `Delete loc-123? [y/N]: ` and
  `Aborted!`. Neither string contains `--force`, `force`, `confirmation`, or any
  instruction. Whether a model concludes "add `--force` and retry" is
  **`hypothesis`, not measured** — it would be recognising the `[y/N]:` idiom
  from training, not reading anything the CLI said. No model was tested on this
  transcript.

**Judgment.** The guard works and is safe by default; what is missing is the
recovery instruction. The abort is a *silent* refusal — correct behaviour,
illegible cause. The cheap fix is one line in the generated gate: on abort, print
what was not done and name the flag. That belongs in the same template that
emits the confirm, and §2.4 is the same argument about the prompt itself.

**What I did not establish:** whether anything upstream of the Bash tool can put
`y` on a `wxcli` command's stdin. If something can, the gate is bypassable
without `--force` and nothing would record it. `UNKNOWN`, and worth one question
to whoever owns that wiring.

### 2.3 `--force` as the agent's default — and one command where the idiom is a trap

`[verified]`, AST census over the 184 tracked modules, re-run and confirmed here.

**211 `typer.confirm` calls** exist across tracked `commands/*.py` (203 of them
in mutating commands — §2 — the other 8 in `cleanup.py`, `cucm.py` ×4,
`init_playbook.py` and `update.py` ×2). The bypass census:

| Flag | Help string | Commands |
|---|---|---:|
| `--force` (bool) | **`"Skip confirmation"`** | **202** |
| `--force` (bool) | `"Skip confirmation prompt."` | 1 (`cleanup.py:1058`) |
| `--yes`/`-y` (bool) | `"Skip confirmation"` | 1 (`cucm.py:928`) |
| `--yes`/`-y` (bool) | `"Skip confirmation prompt (for non-interactive use)"` | 1 (`cucm.py:2149`) |
| `--force` (bool) | `"Overwrite collisions / refresh without prompting."` | 1 (`init_playbook.py:152`) |
| `--yes` (bool) | `"Skip the confirmation prompt."` | 2 (`init_playbook.py:152`, `update.py:211`) |
| **`--force` (str)** | *"If 'yes', the flow is deleted even if it is still referenced by other entities. Defaults to 'no'."* | **1 (`cc_flow.py:130`)** |

**Not one of those strings says what is skipped, what is destroyed, or how
many objects are affected.** That is the complete set, quoted verbatim — the
answer to the spec's question is a flat no.

**The structural point stands and is worth restating precisely:** the gate and
its bypass are emitted from the same render path (`command_renderer.py:1812-1816`,
`:1908-1910`), so 100% gate coverage is 100% bypass coverage — and the bypass is
one word an agent already knows. Combined with §2.7 (downstream, `Bash(wxcli:*)`
is blanket-allowed and no hook exists), `--force` is the entire remaining
distance between an autonomous operator and any of the 203 gated commands.

**The trap, which is new and which I verified in full** `[verified]`:

```python
# src/wxcli/commands/cc_flow.py:130, 141-142
force: str = typer.Option(None, "--force",
    help="If 'yes', the flow is deleted even if it is still referenced by "
         "other entities. Defaults to 'no'."),
...
if not force:
    typer.confirm(f"Delete {flow_id}?", abort=True)
...
if force is not None:
    params["force"] = force
```

`wxcli cc-flow delete` is **the only command in the tree whose `force` parameter
is not `bool`** — measured: 206 `force: bool`, 4 `yes: bool`, **1 `force: str`**
`[verified]`. Here `--force` is a *spec query parameter* that collided with the
generator's bypass name, and the collision produces three behaviours the help
text does not mention:

1. **`--force yes`**, used for its documented purpose (delete despite
   references), **also skips the confirmation.**
2. **`--force no`** — the natural way to say *"do not cascade"* — is a non-empty
   string, so `not force` is `False`. It **also skips the confirmation**, while
   telling the server not to force. The operator gets the opposite of both
   intentions.
3. **Bare `--force`**, the idiom that works on 202 other commands, is a **parse
   error** here: `--help` renders it as `--force <str>` `[verified]`, so it
   requires a value.

So on the one command where an agent's learned reflex would fail loudly, it fails
loudly for the wrong reason — and both of the spellings it would try next
silently disable the guard. This is a generator defect of exactly the shape the
severity model names Critical for Target A — a render-path rule (emit `--force`
as the bypass name) meeting a spec that already uses that name. The fix is at the
generator: detect the collision and rename the bypass (e.g. `--yes`, already used
on four commands) when a body or query parameter is called `force`.

**And the collision is not a one-off — the generator shares this name with the
spec on three commands.** Measured `[verified]`: **seven** flags whose name
contains `force` are not the confirm bypass, and **three of them spell the
literal flag `--force`**:

| Command | Flag | What `--force` means there | Has a confirm? |
|---|---|---|---|
| `cc-flow delete` | `--force <str>` | delete despite references | **yes** — and it skips it |
| `cc-notification create` | `--force/--no-force` | *"will drop a random connection and then subscribes if connections for a user exceed maximum limit… drop **all** connections for that user"* | no |
| `cc-realtime create` | `--force/--no-force` | identical text (`cc_realtime.py:21`) | no |

The other four are `--force-agent-unavailable-on-bounced-enabled`,
`--force-night-service-enabled`, `--forced-forward-enabled` (all `call_queue.py`)
and `--force-domain-claim` (`domains.py:91`) — distinct enough in name not to
mislead. **The two `cc-notification`/`cc-realtime` ones are not:** the flag string
is byte-identical to the bypass on 202 commands, and here it drops a user's
live connections. Neither command has a prompt, so nothing is skipped — but a
model that has learned *"`--force` = make this run unattended"* would pass it
freely and get a disconnection instead.

**A second name trap, corrected from my own briefing.** The inverse-semantics
flag is on `location-settings create-delete-calling-location`
(`location_settings.py:1218`), **not** `device-settings` — I gave the worker the
wrong group and they corrected it against `_registry.py` `[verified]`. Its
`--force-delete/--no-force-delete` maps to `body["forceDelete"]`, a **server-side
dependency-check override**: with it set, Webex disables a whole calling location
even though queues, hunt groups, virtual lines or trunks are still attached.
**That command has no `typer.confirm` at all** `[verified]` — the only confirm in
the file is on a different command (`:1112`). So a model pattern-matching
"flag name contains force → this is the skip-confirmation flag" reaches the
opposite conclusion twice over: it is not a bypass, and there is no prompt to
bypass, on a command that disables calling for an entire location.

Its `--help` opens *"Disable a Location for Webex Calling."* `[verified]` — an
accurate summary that reads as a configuration toggle, on the command
`00-context.md` Q1 class 3 identifies as *"a destructive location-scale operation
issued as a POST, hence ungated"*, whose server-side safe-delete checks
(`BATCH-1012004`…`1012011`) are the only thing standing between it and a location
with users, workspaces and trunks still attached — and `--force-delete` removes
exactly those.

### 2.4 The confirm text — 89% of prompts name an opaque token and nothing else

`[verified]`, AST-extracted from the f-strings, not regexed.

**29 distinct prompt shapes across the 211 confirms.** The distribution:

| Shape | count |
|---|---:|
| `Delete {x}?` | **158** |
| `Purge Inactive Entities for {x}?` | 11 |
| `Delete Access Codes for {x}?` | 8 |
| `Delete this resource?` | 5 |
| `Delete Digit Patterns for {x}?` | 4 |
| 24 further shapes | 1–2 each |

**188 of 211 (89%) interpolate exactly one opaque technical token** — a base64
Spark ID, a UUID, or a 24-char hex id — with no object type in words, no display
name and no count.

**15 of those 188 interpolate a value the operator never typed.** They are org
IDs resolved at runtime from `get_cc_org_id(api.session)` or
`resolve_org_id(api.session)`, not CLI parameters — e.g. `cc_aux_code.py:281`
prompts `Purge Inactive Entities for {orgid}?` where `orgid` came from the
session. **The operator is asked to confirm a value it did not supply and cannot
predict from `--help`**, on a purge.

**Twelve prompts interpolate nothing at all**, five of them the fully generic
`Delete this resource?` (`authorizations.py:61`, `call_queue.py:1391`,
`conference.py:98`, `device_settings.py:1647`, `meeting_chats.py:60`) — which
does not even name the kind of object being destroyed.

**The 21 collection-scoped DELETEs** (`00-context.md` Q1 class 5, reproduced
exactly by an independent AST scan this session) are the sharpest case:
`numbers delete` asks `Delete Numbers for {location_id}?` whether the body holds
one number or forty. **None of the 21 discloses count or scope**; five are
`Delete this resource?`. The count is knowable only via a GET the generated
command does not issue.

**What the tree gets right, and it is one command.** `cleanup.py:1255` —
`f"\nDelete {total} resources? This cannot be undone"` — where `total` is summed
from a **prior live listing of every resource type** (`cleanup.py:1249`) and a
dry-run breakdown table is printed first. It is the only confirm in the
repository that states a real count of real objects. Four hand-written prompts
carry more than an ID (`cucm.py:968` names the config key; `:2199` and `:2227`
give counts; `init_playbook.py:190` names the profiles and folder).

**Could the generator emit better? Yes, from three inputs it already holds at
render time**, and a fourth it holds at *run* time:

1. **The operation `summary`** — read at parse time
   (`tools/openapi_parser.py:694`) and already used for the success word and the
   `DESTRUCTIVE:` line. `Purge Inactive Entities for {orgid}?` becomes
   *"Purge ALL inactive **Auxiliary Codes** in this organization?"* from the
   summary *"Purge inactive Auxiliary Code(s)."*
2. **The CLI tag/group** — `_active_cli_name`, set once per file
   (`command_renderer.py:2185`) and readable by every renderer in that pass.
3. **The declared ID kind** — `_spark_id_kind` (`:653-673`) already decodes the
   spec's example to `ciscospark://us/<KIND>/…` and puts *"Webex LOCATION id"*
   into argument help. The same string could go in the prompt:
   `Delete LOCATION {location_id}?` rather than `Delete {location_id}?`.
4. **At run time, `decode_id_kind`** (`errors.py:90-103`) — a **pure function**
   over the token: length check, one regex, a base64 decode, one more regex. No
   I/O, no `api` object, no network `[verified], read in full`. It answers a
   different and better question than (3): not *"what kind does this parameter
   expect"* but *"what kind did the operator just pass"*, computable between
   argument parsing and the confirm, at zero latency, for all 203 gated commands.

Two cases show the current prompt is not merely terse but **wrong**:

- **`cc-tasks delete-preview-task`** (`cc_tasks.py:934`) prompts
  `Remove Preview Task for {campaign_id}?` on a URL of
  `.../campaign/{campaign_id}/preview-task/{task_id}/remove`. **It shows the
  campaign and never the task** — the wrong identifier for the object being
  destroyed.
- **`converged-recordings delete-recordings-recycle`** (`:385`) prompts
  `Purge Converged Recordings?` and carries `--purge-all`, whose help says it
  purges *every* recording owned by the caller or by `--owner-email`. **The
  prompt is identical in both modes** — one deletes what you named, the other
  empties the bin. This is the same danger shape as
  `device-settings create-apply-line-key-template`, which *did* get a
  hand-written scope-aware prompt on 2026-08-04
  (*"Apply line key template to every device in scope (all locations unless
  locationIds was set)?"*, `device_settings.py:898`) — proving the generator can
  carry a scope-aware string, and that it was applied to one command rather than
  to the class.

**What a better confirm still cannot know locally:** the target's display name,
the count of dependents under a collection endpoint, and whether the ID exists at
all. Each needs a GET. **The only read-before-delete precedent in the repo is
`cleanup.py`**, and it is cheap there only because that command already had to
list everything for its dependency-ordered plan. A generic read-before-confirm
would add one GET to every gated command; §2.5 argues the same GET is what a
generated `--dry-run` needs, so the two should be designed as one feature rather
than two.

**One thing the generator already does right, verified live.** The
`DESTRUCTIVE:` docstring line **does** reach `--help`
(`COLUMNS=400 wxcli user-settings update-access-codes --help` prints
*"DESTRUCTIVE: this PUT only deletes despite the summary above. It cannot add or
modify."*) `[verified]`. It is emitted by `_render_docstring`
(`command_renderer.py:461-469`) only when the summary does **not** already lead
with a destructive verb — i.e. it is reserved for genuinely misleading names, and
lands on exactly 3 commands. That is correct scoping for what it is, and it is
**not** a destructiveness disclosure for the other 199 destructive operations.

### 2.5 Dry-run: 328 of the 755 are emissible today, with machinery already written

`[verified]` The spec asks whether a generated dry-run is even possible and what
it would cost. **The generator already computes the predicate, and the shared
runtime already implements both halves of the operation.**

`--verify` is emitted by exactly one rule (`tools/command_renderer.py:219-228`):

```python
def _can_verify(ep) -> bool:
    """True when this write has a same-path GET to read back from. ..."""
    return ep.method.upper() in ("PUT", "PATCH") and ep.url_path in _active_get_paths
```

and it calls `verify_write(api, url, params, body)` (`common.py:136-183`), which
does `rest_get(url, params)` and diffs **only the fields that were sent** against
what came back.

A generated `--dry-run` on those same commands is the same two operations in the
opposite order: GET first, diff the body you were about to send, print, return
without writing. No new spec field, no new consequence metadata, no new HTTP
machinery — `_can_verify` is the emission predicate and `verify_write`'s diff
loop (`common.py:169-174`) is the body.

Measured over git-tracked `src/wxcli/commands/`, by `ast` `[verified]`:

| | count |
|---|---:|
| Commands carrying `--verify` | **332** |
| — of those, gated (the four `accessCodes` PUTs) | 4 |
| — of those, **ungated writes** | **328** |
| Ungated writes total | 755 |

**So 328 of the 755 ungated writes — 43% — already carry the read-back endpoint a
dry-run needs, proven by the generator having already decided so.** The
remaining 427 are POSTs and PUT/PATCHes with no same-path GET, and for those the
honest answer is the one `_can_verify`'s own docstring gives about `--verify`: a
dry-run that silently previews nothing is worse than no flag, because it converts
an unpreviewed write into one that *looks* previewed. Emit it where it can do its
job and nowhere else — which is the rule this repository already wrote down and
enforced once.

Two caveats I did not measure away:

- `verify_write` compares scalars with `!=` (`common.py:173`). A dry-run diff over
  a collection-replacing body (§2.1) would report the array as "changed" without
  saying *which members disappear*, which is the thing that matters. Making the
  preview useful for that class is more than an inversion.
- A dry-run costs one extra GET per invocation. On a single command that is
  nothing; the audit did not measure whether any caller loops.

### 2.6 Scope containment: 423 mutating commands take their target org from ambient state

`[verified]` by `ast` over the 184 git-tracked modules in `src/wxcli/commands/`:

| | count |
|---|---:|
| `@app.command`/callback functions | **1,892** |
| — calling `get_org_id()` | **852** across 62 modules |
| — mutating (POST/PUT/PATCH/DELETE) | 958 |
| — **mutating AND resolving org from config** | **423** |
| — mutating, org from a path parameter or the token's implicit org | 535 |

The 1,892 reproduces `07-testability.md` §3.1 exactly and the 958 reproduces the
three prior measurements, which is the cross-check on the method.

The generated shape is uniform (`device_settings.py:1075-1077` is
representative):

```python
org_id = get_org_id()
if org_id is not None:
    params["orgId"] = org_id
```

**So "no org saved" is not an error — it is a silent widening.** The parameter is
omitted and the server resolves the call against whatever org the token defaults
to. The spec asks what an operator would have to do *wrong*. Three answers,
all `[verified]`, and none of them requires a mistake that looks like one:

1. **Mistype an orgId in `switch-org`.** `wxcli switch-org <orgId>` resolves the
   org name for display and **saves the id regardless of whether the lookup
   succeeded** (`main.py:116-124`):

   ```python
   try:
       org = api.session.rest_get(f"https://webexapis.com/v1/organizations/{org_id}")
       org_name = org.get("displayName", "Unknown")
   except Exception:
       org_name = "Unknown"
   save_org(org_id, org_name)
   ```

   The one command whose entire purpose is setting scope does not validate the
   scope it sets. Its only signal is the word `Unknown` in an output field, and
   an org the token genuinely cannot see produces the same string as a transient
   network blip. Every one of the 423 then injects that id.
2. **Run `clear-org` while holding a partner token.** Its help reads *"Clear
   target organization — commands will target your own org"* and its output is
   *"Commands will now target your own organization"* (`main.py:169-180`). Both
   are accurate and neither says that "your own org" is a *different* org from
   the customer org just being administered, nor names either one.
3. **Run `switch-org` with no argument in an agent.** It falls through to
   `typer.prompt` (`main.py:161`), which on a multi-org token blocks a
   non-interactive caller — the behaviour `CLAUDE.md` already documents and the
   same class of trap as §2.2.

**The disclosure that exists, and where it does not reach.** `wxcli whoami` adds
a `targetOrgId` field when an org is set (`main.py:69-74`). That is the only
place the ambient target is surfaced. **No mutating command prints it, and no
confirm string contains it** — including the 179 delete prompts (§2.4). So the
answer to "which org is this delete about to hit?" is available from a different
command than the one doing the deleting.

**Contrast with Target B, which fails the same way but louder in one direction
and quieter in the other** (§1.9): Target A crashes on a malformed config
(`config.py:7-11` lets `json.JSONDecodeError` propagate) and silently widens on a
missing `org_id`; Target B silently widens on both.

### 2.7 The bound that does not ship

`[verified]` Phase 0 established the mechanism and Phase 7 §3.2 added the
layering reading. Phase 5 owns the judgment, so here it is with the evidence
re-confirmed from source this session.

- `.claude/hooks/wxcli-gate.sh` enforces a read-only verb policy — `list*` /
  `show*` / `whoami` / help outside the two playbook agents, unknown verbs deny
  (`wxcli-gate.sh:5-11`) — and separately blocks importing `wxcli` from Python,
  which is what stops the `OptionInfo`-is-truthy inversion (`:31-33`, `:41-52`).
- `wxcli-dist/assemble.py:158-161` copies `wxcli-dist/settings.bundled.json` over
  `.claude/settings.json` in the shipped bundle.
- **`src/wxcli/_playbook/.claude/` contains `agents`, `rules`, `settings.json`
  and `skills` — and no `hooks` directory at all** `[verified]`. The hook is not
  merely unreferenced downstream; it is not shipped, which its own header states
  plainly (`wxcli-gate.sh:2-3`).
- The shipped `settings.json` is four lines of substance: a `SessionStart` update
  check, plus `"permissions": {"allow": ["Bash(wxcli:*)", "Bash(which:*)"]}`
  `[verified], read in full`.

**The judgment.** This is not "a safety control is missing downstream." It is
sharper than that, and it is a coherence defect rather than an omission:

> The bundle ships the **rule** and drops the **enforcement**, then adds a
> blanket allow in the permissive direction. `src/wxcli/_playbook/CLAUDE.md:118-119`
> — which every `wxcli init` writes into the customer's folder — says **"Do not
> run `wxcli` commands directly"**. The shipped `settings.json` says
> `Bash(wxcli:*)` is allowed without a prompt. One of those is prose an LLM may
> follow; the other is machine-enforced.

Two consequences that belong to Phase 5 specifically:

1. **The import block is the control that the 2026-07-28 incident produced, and
   it is the one that does not travel.** The hook's own header records the
   incident: *"a subagent imported four generated delete functions to see whether
   they crash; the OptionInfo-is-truthy trap skipped the confirm prompt and four
   unconfirmed DELETEs reached the live org, one of them
   `DELETE /v1/organizations/{id}`. Only Cisco refusing them saved it."*
   Phase 7 §3.2 confirmed the trap is real and that the guard **inverts** rather
   than merely being bypassed. Downstream there is no hook, so the mechanism is
   live and the only thing that stopped it last time was the remote API.
2. **It compounds §2.2 and §2.3.** For a downstream operator the complete local
   bounding on 958 mutating commands is: the confirm prompt on 203 of them, and
   nothing else. Whatever §2.2 concludes about that prompt's behaviour without a
   TTY is therefore not a partial answer — it is the whole answer.

I am **not** proposing that the hook ship. A `PreToolUse` hook that denies
non-read verbs would break the builder agent it exists to route work *to*, and
the shipped playbook's routing is prose for a reason. The finding is the
mismatch: a shipped instruction that says "never run this directly" paired with a
shipped permission that says "run it without asking," with no third artifact
reconciling them.

### 2.8 Target A severity

Severity by the generated multiplier, per the spec's Target A model: a defect in
the generator or a template counts once and ships everywhere.

| # | Finding | Severity | Multiplier |
|---|---|---|---|
| A1 | **42 ungated PUT/PATCH operations replace a collection by omission**; 4 say so in vendor prose; the hazard is documented in `handlers.py:2270` for 4 migration types and nowhere on the generated surface (§2.1) | **Critical** | A render-path gap × 42 operations, and the classifier that would have to change is one function |
| A2 | **Array and object body fields are dropped from the flag surface** (`command_renderer.py:1621`), so every one of the 42 hazardous fields — and every array-typed scope control — is invisible in `--help` (§2.1) | **Critical** | One `continue` × 476 fields / 142 commands (`00-facts.md`, HOW TO RUN item 6). Two commands are left with **zero** scalar flags |
| A3 | **The generator emits `--force` as the bypass without checking whether the spec already uses that name.** On `cc-flow delete` it collides: `--force yes` *and* `--force no` both skip the confirm, bare `--force` is a parse error. Two more commands spell `--force` meaning "drop this user's live connections" (§2.3) | **High** | 3 commands today where the literal flag means something else — and it is a **generator** rule, so every spec refresh can add more |
| A4 | **89% of confirms name only an opaque token**; 15 name a value the operator never typed; 5 say only `Delete this resource?`; `cc-tasks delete-preview-task` names the **wrong** id (§2.4) | **High** | One template × 203 gated commands. All four inputs for a better string already exist in the generator or in `errors.py:90` |
| A5 | **The abort gives no recovery instruction.** The gate fails safe (exit 1, no HTTP call) but its entire output is the prompt echo plus `Aborted!` — no mention of `--force`, and exit 1 collides with REST and network failure (§2.2) | **Medium** | One template × 203. Note this is *less* severe than the spec assumed: the guard holds |
| A6 | **423 of 958 mutating commands take their target org from ambient config**, `switch-org` saves an unvalidated orgId, and no mutating command or confirm string ever prints the target org (§2.6) | **Medium** | Uniform generator behaviour × 423, plus one hand-written command (`main.py:116-124`) |
| A7 | **`location-settings create-delete-calling-location` disables calling for an entire location, has no confirm, and its only `force`-named flag removes a *server-side* safety check** (§2.3) | **Medium** | ×1, but it is one of the 14 job-endpoint commands `00-context.md` Q1 class 3 identifies as the largest generated blast radius |
| A8 | **Dry-run is emissible on 328 of the 755 ungated writes** using `_can_verify` and an inversion of `verify_write`, and is emitted on none (§2.5) | **Medium** | An absence × 328. Cheap because both halves already exist |
| A9 | **The shipped bundle keeps the rule and drops the enforcement**, then blanket-allows `Bash(wxcli:*)` (§2.7) | **Medium** | Every downstream install |

**A1 and A2 are the same defect seen from two sides**, which is why they are both
Critical: the generator cannot express an array as a flag, so it renders the
hazardous field invisible; and it cannot classify an array as destructive, so it
renders the command ungated. Fixing either alone leaves a real gap — a visible
flag with no guard, or a guard on a field nobody can see.

**What is *not* here, deliberately.** The DELETE gate itself is in good shape:
179 of 179 carry it, it fires correctly without a TTY, and it makes no API call
when it aborts (§2.2). `02-drift.md` F3 remains the reason that is fragile —
**no gate check asserts a destructive command has a guard** — and §6 item 5
proposes the check.

---

## 3. Remediation shipped in this phase

Under the revised remediation rule (`wxops-architecture-audit-prompt_2.md:425`),
the brief deferred two candidates here. **Both are shipped, each with a
git-tracked test that pins it**, per the constraint Phase 7 imposes: a guard
pinned by an untracked test is a guard pinned by nothing, and this repository has
produced three examples of exactly that failure (`07-testability.md` §3.4).

`tests/migration/**` is re-included wholesale at `.gitignore:56-57`, so a new
file under `tests/migration/execute/` or `tests/migration/preflight/` is tracked
and runs on every PR by construction. That is the cheapest correct home and it is
where both tests went.

**Verification, run this session** `[verified]`:

| | before | after |
|---|---|---|
| `pytest tests/migration -q` | 3,085 passed | **3,105 passed** (+20: 6 + 11 new, 1 replaced by 4) |
| `pytest tests/migration/execute -q` | 805 passed | **811 passed** |
| `pytest tests/migration/preflight -q` | 78 passed | **92 passed** |
| `python -m tools.drift_check --enforce` | PASS | **PASS**, exit 0 |
| tracked artifact guards (7 files) | — | 100 passed |

### 3.1 D13 — `in_progress` is now written before dispatch

**Root cause** (`06-machinery.md` D13, re-verified): `plan_operations` carries an
`in_progress` status, `OpStatus.IN_PROGRESS` is declared, `update_op_status`
implements the transition, `reset_in_progress` exists to recover from it and
`commands/cucm.py:3180` calls it at the top of every run — and **nothing wrote
it**. `execute_all_batches` set `completed`, `failed` or `skipped` only.

**Change:**

- `migration/execute/runtime.py` — new `mark_ops_in_progress(store, node_ids)`:
  one guarded `UPDATE … WHERE status = 'pending' AND node_id IN (…)` and one
  commit for the whole batch. A bulk statement rather than a loop over
  `update_op_status(..., "in_progress")` because that path commits per call,
  which at batch sizes in the hundreds is hundreds of fsyncs before any useful
  work. Guarded on `pending` so a re-entrant call cannot resurrect a terminal op.
- `migration/execute/engine.py` — called immediately after the `tasks` list is
  built and **before** `run_batch_ops`, i.e. before the first request can leave
  the process. Ops that resolve to `SkippedResult`, to `[]`, or to a missing
  handler `continue` before `tasks.append` and are correctly never marked.

**Why this is safe against the existing machinery**, checked rather than assumed:
`get_next_batch` selects `status = 'pending'` only (`runtime.py:57`), so an
in-flight batch cannot be re-selected; its dependency filter is
`dep.status NOT IN ('completed','skipped')` (`:66`), so an `in_progress`
dependency still blocks, which is correct; and `_cascade_skip` already matched
`status IN ('pending','in_progress')` (`:258`, `:269`) — the defensive clause
Phase 6 found had no producer now has one.

**What it does and does not fix.** It makes a killed run *visible*:
`reset_in_progress` can now return non-zero and the
`Reset N in-progress ops to pending` line (`cucm.py:3182`) is reachable for the
first time. It does **not** stop the re-issue, and it should not — with no DELETE
available and 13 of 21 create types unrecoverable (§1.6), refusing to proceed
would strand the migration. Disclosure, not refusal, is the right behaviour here.

**Pinned by** `tests/migration/execute/test_in_progress_written.py` (6 tests,
tracked). The load-bearing one reads the database *from inside* a patched
`run_batch_ops` and asserts the status observed there is `in_progress` — if that
read returns `pending`, a kill at that instant is indistinguishable from never
having started, which is the whole finding in one assertion. A second test
simulates the kill by raising out of `run_batch_ops` and asserts
`reset_in_progress` finds the op.

### 3.2 The preflight bulk-job probe — repaired, and its failure now stops the gate

**I extended this beyond what the brief named, and the reason is a hazard the
brief's version would have created.** Stated plainly because it is a scope
decision, not a detail.

The brief authorised *"`checks.py:875` returning `INCOMPLETE` instead of `WARN`
(paired with widening `cucm.py:1797`)."* Shipping only that pair would have been
**worse than shipping nothing**: the probe is structurally incapable of running
(`06-machinery.md` §5), so it raises on *every* invocation. Turning that raise
from `WARN` into `INCOMPLETE` and making `INCOMPLETE` exit non-zero converts a
silent pass into a **hard block on every migration whose plan contains a bulk op**
— i.e. every org with ≥100 devices, which is where real migrations live. The
authorised fix is only correct if the probe can actually return a verdict, so the
probe repair is part of the same change.

**Three changes, all in `migration/` or its driving command:**

1. **`preflight/runner.py` — the probe now runs.** `api.session.ep(...)` /
   `api.session.get(...)` (`wxc_sdk`'s `WebexSimpleApi`, dropped as a dependency
   in `e4dfb22`, 2026-04-17) replaced with `api.session.rest_get(url, params)`
   against `https://webexapis.com/v1/telephony/config/jobs/devices/callDeviceSettings`
   — a path present as a `GET` in both `webex-cloud-calling.json` and
   `webex-device.json` `[verified]` and served by
   `wxcli device-settings list-call-device-settings`. `WebexError` is caught to
   read `status_code` (`errors.py:17`), because the check branches on the HTTP
   status; any other exception returns the `0` transport sentinel. The
   `except requests.RequestException` residue is gone — `WebexSession` is
   `httpx`.
   Also: the `orgId` now falls back to `wxcli.config.get_org_id()` when the
   project config carries none, matching the generated surface. Unscoped, the
   probe answers about whatever org the token defaults to, which on a partner
   token is not the migration target (§2.6).
2. **`preflight/checks.py` — three outcomes now return `INCOMPLETE`**: the probe
   raising (the authorised change), the `0` transport sentinel, and `401`. All
   three mean *"we could not ask"*, which is what `INCOMPLETE` was invented for
   (`preflight/__init__.py:26-32`). **`403` and `404` deliberately stay `FAIL`**
   with their existing remedy — a token authorised for the rest of the plan being
   refused *here* is a statement about the org, and the message already names
   `bulk_device_threshold=999999` as the way out, so a hard block is actionable
   rather than a dead end.
3. **`commands/cucm.py:1797` — widened to `in (FAIL, INCOMPLETE)`.** Phase 6 §5.1
   established the interlock. The two consumers of one verdict disagreed:
   `gate_ok` (`:1771-1774`) already refused to mark the stage on `INCOMPLETE`
   while the exit branch returned 0, so a run that printed "we could not check"
   and left `ProjectState` un-advanced still told `$?` it had succeeded — on a
   gate the skill calls MANDATORY, NOT SKIPPABLE.

**Corrected while doing it:** the source comment at `runner.py:302-308` said
*"there is no equivalent `wxcli` subcommand that lists bulk device jobs"* and
promised to re-route through `_run_wxcli` if one appeared. One exists
(`commands/device_settings.py:1093`). The probe still calls the session directly,
but for a narrower and now-recorded reason: `_run_wxcli` surfaces a process exit
code and stderr text, not an HTTP status, and collapsing 403/404 into "non-zero"
would destroy the distinction the check is built on.

**Pinned by** `tests/migration/preflight/test_bulk_job_probe.py` (11 tests,
tracked), plus four rewritten cases in the existing tracked
`tests/migration/preflight/test_checks.py`. The important one constructs
**`_build_bulk_job_probe` itself** — the factory that
`07-testability.md` §2.4 measured as never having executed in any test, and which
all eight existing tests bypass by injecting a lambda. Its fake session exposes
only the methods `WebexSession` really has, so an `ep`/`get` regression fails
there loudly instead of being swallowed into a WARN.

**Confirmed red-before-green** `[verified]`: the pre-fix probe body, run against
that same fake session in the scratchpad, raises
`AttributeError: 'FakeSession' object has no attribute 'ep'`. The new test would
have failed before the change; it is not a test written to the implementation.

### 3.3 B1 and B2 — shipped on the operator's decision (2026-08-05)

Both were written up in §4 as items 1 and 2 and held back for a decision. The
decision came back *ship them*, with the design choices below made explicitly.

**B2 — `execute` now requires a passing preflight.** `"execute": "preflight"`
added to `STAGE_PREREQUISITES` (`cucm.py:67-88`) and one
`_check_prerequisite(project_dir, "execute")` call at the top of `execute()`,
**before** `_open_store` and before `resolve_token` — so a refusal costs no
socket and no store handle. `--help` now opens *"Requires a passing 'wxcli cucm
preflight'."*

*The recovery loop was traced before enabling, not assumed:* `execute` and
`retry-failed` read and write `completed_stages` at **no** point `[verified]`, so
`execute → retry-failed → execute` — the loop the runbook tells operators to
repeat until zero failures — never disturbs the gate. The only thing that clears
`preflight` is `_invalidate_downstream` from re-running an earlier stage, and a
re-plan *should* demand a fresh preflight. A partial `preflight --check <one>`
still cannot open it, because finding F07's fix already refuses to mark the stage
on a partial run — the two guards compose.

**B1 — `plan` preserves; `normalize` refuses.** The two commands needed different
answers, and the reason is structural rather than a matter of taste.

*`plan` can preserve, so it does.* `save_plan_to_store` (`batch.py:160`) now
snapshots `status`, `webex_id`, `error_message`, `completed_at` and `attempts`
before the rebuild and restores them for every `node_id` present in the new
graph. `node_id` is `canonical_id:op_type`, stable across re-plans for the same
object, which is what makes the carry-forward well-defined. The graph stays the
source of truth for everything the *planner* decides — tier, batch, description,
dependencies all rebuild — and only the columns recording what happened
*remotely* survive. **This is strictly better than the old behaviour in both
directions**: a re-plan no longer destroys the record, and the next `execute` no
longer re-issues work that is already done.

*The orphan case is the one a human still has to resolve*, and it is now
disclosed rather than swallowed: a completed op carrying a `webex_id` whose
`node_id` is **absent** from the new graph names a real object in the customer's
org that the new plan no longer references. `save_plan_to_store` returns those,
and `plan` prints them with their resource type, description and `webex_id`,
pointing at the teardown procedure. Nothing in this tool can delete them.

*`normalize` cannot preserve, so it refuses.* It rebuilds `objects` from
`raw_data.json` and every other table hangs off it by foreign key, so there is no
coherent record to carry. It now counts executed operations before
`store.clear_all()` and, if any exist, aborts with the count, the number of
resolved decisions that would go with them, and three ways forward —
`execution-status` to see what exists, `rollback-ops` to list what to remove, and
`wxcli cucm plan` as the non-destructive alternative. `--force` overrides, and
**its help text names what it destroys** (*"ERASES the record of what was created
in Webex — including every webexId and every resolved decision"*) rather than the
`"Skip confirmation"` that §2.3 measures on 202 generated commands.

**Pinned by two tracked files, 17 tests:**
`tests/migration/execute/test_plan_preserves_execution_record.py` (7) and
`tests/migration/test_write_path_gates.py` (10). Both live under
`tests/migration/**`, re-included at `.gitignore:56-57`, so they run on every PR.

**One defect found in my own test while writing it, recorded because it is the
same class this audit keeps finding.** The positive-case gate test — "with
preflight complete, does `execute` proceed?" — originally let the command run on
past the gate. With the gate open it reached `get_api()` and issued a real
`GET /v1/licenses` against whatever org the developer's or CI's token points at.
It passed, silently, in 1.32s. Forcing `resolve_token` to `None` so the command
stops at its own no-token guard proves the same thing and takes 0.41s
`[verified]` — the ~0.9s delta was the live round-trip. **A test in
`tests/migration/**` runs on every PR, so a live call there is a live call for
everyone**, and nothing in the suite would have reported it. `07-testability.md`
§4 found the same shape in `tests/test_smoke.py`, which is safe only because it
has zero test functions.

**Verification after both changes** `[verified]`: `pytest tests/migration` →
**3,122 passed** (3,105 + 17); drift gate → **PASS**; the seven tracked
artifact-guard files → 100 passed. No mutating command was run and no live-org
call was made.

### 3.4 What I did not ship, and why

- ~~**`"execute": "preflight"`**~~ and ~~**a guard on `plan` / `normalize`**~~ —
  **both shipped**, see §3.3. They were held for a decision and the decision
  came back. The retry-loop trace they were waiting on is in §3.3.

- **A confirm or a scope disclosure on `execute`.** Same reason, plus §2.2's
  answer about what `typer.confirm` does without a TTY bears directly on whether a
  confirm is even the right instrument here.
- **`_try_find_existing`'s missing name-equality check** (`06-machinery.md` D8).
  Root cause is proven and the fix is one line, but its severity turns on whether
  Webex's `name=` filters are exact-match, which is `UNKNOWN` and settleable by
  one live read. It belongs with that read, not ahead of it.

---

## 4. Sequenced remediation

Ordered by consequence × cheapness, with what pins each. Items 1–4 are Target B,
5–8 Target A. Nothing here was shipped; §3 is what was.

**1. Make preflight blocking. Target B, two lines.**
Add `"execute": "preflight"` to `STAGE_PREREQUISITES` (`cucm.py:67-74`) and one
`_check_prerequisite(project_dir, "execute")` call in `execute()`. Uses machinery
already written, already exercised by six commands, and already emitting a
legible error naming the missing stage. **Blast radius: it can make a
mid-migration `execute` refuse to run** — so walk `retry-failed` → `execute` and
the `mark-complete` recovery flow against it first, and decide whether
`retry-failed` needs the same gate or is deliberately exempt. **Pinned by** a
test under `tests/migration/preflight/` in the shape of
`test_gate_requires_full_run.py`, which already drives `cucm` commands through
`CliRunner` against a seeded `state.json`.

**2. Stop `plan` and `normalize` destroying the execution record. Target B.**
The shape is a decision, not a finding: refuse when completed ops exist, prompt
with a count in the `cleanup.py:1255` style, or snapshot into `journal` first.
`save_plan_to_store` (`batch.py:174-175`) and `clear_all` (`store.py:446-452`)
are four lines each. **Blast radius: it can make a legitimate re-plan refuse**,
which is a normal operation the skill's own re-run recipe uses. My
recommendation, stated as one: **refuse by default when
`SELECT COUNT(*) FROM plan_operations WHERE status='completed'` is non-zero**,
with a `--force` that prints the count first — the one prompt in this repository
that already does this well is the model. **Pinned by** a test asserting a
completed op survives a re-plan without the flag and does not survive with it;
the probe in §1.5 is already most of that test.

**3. Write the `journal` on the execute path. Target B.**
The schema exists (`store.py:120-130`), the writer exists
(`add_journal_entry`, `:749-777`), the FK sentinel pattern exists (`:732-748`),
and the caller does not. One entry per operation carrying `request`, `response`
and — on a PUT — `pre_state` from the read `_try_find_existing` is already
capable of making. This is what turns D13, D8 and §1.5 from "unrecoverable" into
"diagnosable", and it is the substrate Phase 1 asks for, so **design it once**.
Cost: the `pre_state` read is an extra GET per replacing write, which is the same
GET item 7 needs. **Pinned by** a test asserting an executed op leaves a journal
row; `tests/migration/execute/` is tracked, so it runs on every PR.

**4. Disclose scope before writing, and name the ops a crash left behind.**
Two small Target B changes with no behaviour risk: print the pending-operation
count and the target `orgId` before the first batch (today `execute` prints only
concurrency, `cucm.py:3212`, and the count only afterwards); and have
`reset_in_progress` surface the node ids it reset rather than a bare count
(`engine.py:148-157`, `cucm.py:3182`) — those ids are precisely the operations
that may have half-applied. §3.1 made that path reachable; this makes it useful.

**5. Add the gate check that pins every guard. Target A — do this before 6 or 7.**
`02-drift.md` F3 established that **no check asserts a destructive command has a
guard**, so the 179 DELETE gates and the 24 added on 2026-08-04 are unpinned: a
render-path change drops them and ships green. The check is a pure comparison of
two in-repo artifacts — run `classify_real_semantics` over the nine specs, `ast`
the rendered `commands/*.py`, assert every flagged operation's command contains a
`typer.confirm`. No network, no fixture, no new metadata. It would have caught
the 23-command gap Phase 0 found by hand, and **it is the prerequisite for items
6 and 7 being durable.** It is also the first drift-gate check that would read a
*guard* rather than a name — the gate's Target B coverage is currently three
documentation counts (`06-machinery.md` §1).

**6. Teach the generator the collection-replace class. Target A.**
Two stages, cheap first: (a) **the prose signal** — the generator already reads
`description` (`openapi_parser.py:694`); four operations state replacement in the
vendor's own words and can be classified today, including the fifth hot-desking
instance the migration guard misses. (b) **the KIND signal** — reuse
`_spark_id_kind`'s base64 URN decoding (`command_renderer.py:653-673`, 71 KINDs
already decoded) to ask whether an array's *items* reference existing remote
objects, excluding items that require a delta verb. §2.1 measures the
alternatives: name-vocabulary is 0% false-positive at 62% recall; raw shape is
53.8% false-positive. **What "classified" should emit is a judgment to make
explicitly** — a `DESTRUCTIVE:`-style docstring line and a confirm is the
conservative answer; a `--dry-run` (item 7) is the better one.

**7. Emit `--dry-run` where `--verify` is already emitted. Target A, 328 commands.**
`_can_verify` (`command_renderer.py:219-228`) is the emission predicate;
`verify_write` (`common.py:136-183`) is the body, run in the opposite order.
Pair it with item 6 so the diff over a collection-replacing array reports *which
members disappear* rather than "the array changed" — that is the case
`verify_write`'s scalar `!=` does not serve, and it is the whole reason the class
is dangerous. **Do not emit it where `_can_verify` is false**: a preview that
silently previews nothing is worse than none, which is the rule this repository
already wrote down and enforced once.

**8. Fix the `--force` collision at the generator, and improve the confirm string.**
(a) When a spec parameter is named `force`, emit the bypass as `--yes` — four
commands already use that spelling, so it is additive, not a rename of published
surface. `cc-flow delete` is the only current instance (§2.3) and the next spec
refresh can add more. (b) Splice `decode_id_kind(the_id)` — a pure function,
`errors.py:90-103` — plus the operation summary's object noun into the generated
prompt: `Delete LOCATION {id}?` rather than `Delete {id}?`. (c) On abort, print
one line naming the flag that would proceed. All three are the same template.

**What pins Target A first, and it is not optional.** `07-testability.md` §3.3
measured that **all four of the generator's test files are untracked** — 187
tests over the component whose defects multiply by the whole surface, none of
which runs on a PR — and `tools/command_renderer.py` is modified in the working
tree right now. **Items 6, 7 and 8 all change that file.** So the real step zero
is `06-machinery.md` §8's: repair and track the generator's tests, then item 5's
gate check, then touch the renderer. Changing the renderer with no CI coverage of
the renderer is how a defect ×1,857 commands ships green.


---

## 5. Read coverage

**Read in full:** `docs/audit/00-facts.md`, `00-context.md`, `06-machinery.md`,
`07-testability.md`, `PHASE-5-HANDOFF.md`, and the audit spec's STATUS / ROLE /
KNOWN CONTEXT / HARD CONSTRAINTS / PHASE 5 / HOW TO RUN.
`src/wxcli/migration/state.py` (139), `migration/preflight/__init__.py` (96),
`migration/execute/CLAUDE.md`, `migration/preflight/CLAUDE.md`,
`wxcli-dist/settings.bundled.json`, `src/wxcli/_playbook/.claude/settings.json`,
`.gitignore:45-120`, `.claude/hooks/wxcli-gate.sh:1-75`.

**Read in the regions that matter, grepped elsewhere:**
`src/wxcli/commands/cucm.py` (3,525 lines — read `:60-300`, `:1337-1380`,
`:1595-1715`, `:1755-1805`, `:2330-2370`, `:2856-2940`, `:3026-3160`,
`:3140-3280`; the rest grepped for stage checks, `_check_prerequisite`,
`clear_all`, `journal`, `resolved_by`);
`migration/execute/engine.py` (`:1-45`, `:140-240`, `:620-715`, `:780-970`);
`migration/execute/runtime.py` (`:25-80`, `:160-300`, `:333-460`);
`migration/execute/batch.py` (`:160-210`);
`migration/store.py` (`:100-215`, `:438-470`, `:740-810`);
`migration/preflight/{runner,checks}.py` (`:1-130`, `:285-345`; `:840-915`);
`.claude/skills/cucm-migrate/SKILL.md` (`:400-450`, `:805-830`);
`src/wxcli/main.py` (`:96-190`); `src/wxcli/config.py` (`:1-45`);
`src/wxcli/auth.py` (`:203-300`); `src/wxcli/errors.py` (`:10-30`);
`src/wxcli/common.py` (`:136-183`);
`tools/command_renderer.py` (`:210-250` + grep for the confirm and `--verify`
emission sites); `src/wxcli/commands/{init_playbook,device_settings}.py`
(the write/confirm and bulk-job regions).

**Parsed, not read:** all **184** git-tracked modules in `src/wxcli/commands/`
(`ast`, for every count in §2). All nine tracked `specs/*.json` (`json.load`, for
the bulk-job endpoint check and §2.1).

**Executed this session** `[verified]`: `pytest tests/migration` (3,105 passed,
91s), `tests/migration/execute` (811), `tests/migration/preflight` (92), seven
tracked artifact-guard files (100), `python -m tools.drift_check --enforce`
(PASS, exit 0), and two throwaway probes in the scratchpad — the store-wipe
reproduction (§1.5) and the pre-fix probe body (§3.2). **No mutating `wxcli`
command was run; no live-org call was made.** The full suite was not run
(project rule); every full-suite figure in this document is Phase 7's, cited.

**Parallel work.** Three workers covered one Target A measurement each (§2.1,
§2.2, §2.3–2.4). Their method constraints were given verbatim. **Every claim of
theirs reproduced above was re-verified against source or re-run here before
being written down** — what survived that check is marked `[verified]`; what did
not is either absent or marked as theirs and unconfirmed.

**Not read at all.** `transform/` (18,517), `report/` (8,302), `advisory/`
(3,738), `export/` (1,013) — 31,570 lines that `00-context.md` Q4 establishes
make no remote call, which is why a phase scoped to the write path does not cover
them. Also not read: `execute/handlers.py` beyond `_url`, the reconcile-members
region and the `HANDLER_REGISTRY` literal; `execute/planner.py`;
`execute/dependency.py`; the 13 AXL extractors; `tools/drift_check.py` (I ran it,
I did not read it).

**Claims I am explicitly not making:**

- That the 755 ungated writes are individually safe. §2.1 characterises one class
  within them; the rest are uncharacterised.
- That Webex enforces uniqueness on any resource type. §1.6 counts the recovery
  coverage and marks the per-type outcome `UNKNOWN` — settling it needs a live
  create, which this phase did not do.
- That the eight 409-recoverable types are correctly recovered. `06-machinery.md`
  D8's missing name-equality check stands, and those branches execute in no test.
- That `transform/`, `report/`, `advisory/` or `export/` are clean.
- That the repaired preflight probe returns 200 against any particular org. It
  returns whatever the org returns; what is verified is that it now *reaches* the
  endpoint and preserves the status, and that the four branches downstream are
  reachable.

---

## 6. Handed forward

**Open, and belonging to later phases or to a live read:**

1. **Are the Webex `name=` filters exact-match?** `06-machinery.md` D8's severity
   turns on it; still `UNKNOWN`. One live read settles it. The one-line equality
   check is worth adding regardless.
2. **Does a re-issued create duplicate, per resource type?** §1.6 counts the
   coverage (8 recovered / 6 declined / 7 unbranched) and cannot answer the
   per-type outcome without a live create.
3. **Phase 8 should weight `commands/cucm.py`, `execute/engine.py` and
   `execute/batch.py` by proximity to the write path.** Three of this phase's
   findings (B1, B2, D13) live in code whose churn history was not examined.
   `batch.py:174-175` — the unconditional `DELETE FROM plan_operations` — is a
   four-line region carrying a Critical finding; whether it has been revisited is
   exactly the Phase 8 question.
4. **The `journal` table** (§1.8) is Phase 1's substrate as well as Phase 5's
   audit trail. Phase 1 is deferred; when it runs, the request/response/pre_state
   record and the invocation log are one design, not two.
5. **`tools/drift_check.py` has no check that reads Target B behaviour.**
   `06-machinery.md` §8 step 4 proposes the first one. Phase 5 adds a second
   candidate that is cheaper and answers `02-drift.md` F3 directly: **a check that
   asserts every operation `classify_real_semantics` flags destructive has a
   `typer.confirm` in its rendered body.** That is a pure comparison of two
   in-repo artifacts — the classifier's output and an `ast` scan of
   `src/wxcli/commands/` — needing no network and no fixture, and it would have
   caught the 23-command gap Phase 0 found by hand. It is the check that makes
   every guard in §2 durable.

**One thing a later phase should not re-open:** whether `execute` exiting 0 is
correct. It is, the reasoning is recorded and dated
(`execute/CLAUDE.md:374-418`), and both Phase 6 and this phase agree with it. The
defect beside it — the undisclosed asymmetry against `preflight`, which this
phase made *stricter* — is a `--help` text problem, not an exit-code problem.
