# 00 — Phase 0: Scope

Extends `docs/audit/00-facts.md` (the numeric authority) and
`docs/audit/00-facts-independent-part2.md` (Q8–Q18, the closest prior art).
**Nothing already established there is re-derived.** Each section names the row it
extends. Labels: `[verified]` = I ran or parsed something this session;
`[inferred]` = reasoned from evidence short of direct observation.
Target **A** = the generated endpoint layer + shared runtime; target **B** =
`src/wxcli/migration/`.

**Method.** `wxcli` is never imported (`.claude/hooks/wxcli-gate.sh:30-33`). All
structural counts are one `ast` pass over the **184 git-tracked**
`src/wxcli/commands/*.py`, cross-checked against `wxcli <cmd> --help` run as a
subprocess with `COLUMNS=400`. Spec text is read with `json.load` over the nine
tracked `specs/*.json`. No mutating command was run.

**Where the two facts files disagree, and which I used.** Two disagreements found;
both are scope-of-count, not arithmetic:

| Quantity | `00-facts.md` | `part2.md` | Used here |
|---|---|---|---|
| Test files | 244 (`find tests`) | 240 tracked / 272 on disk | **part2** — `00-facts.md` counted the working disk here, against its own corrected rule (`00-facts.md:97`) |
| Commands in `commands/*.py` | 1,887 *reachable via a mounted group* | 1,890 *typer commands in tracked modules* | Both, as stated — different denominators, not a conflict. My own pass finds **1,859** carrying a `rest_*` call, i.e. 31 tracked commands issue no REST call at all |
| `--verify` | 328 (quoted from `CLAUDE.md`, not counted) | **332** counted | **part2** |

My mutating-command counts reproduce both files exactly — 958 mutating / 179
DELETE / 179 confirm / 179 `--force` / 779 write-not-delete / 0 confirm
`[verified]`. That figure is now measured three times by two methods; treat it as
settled.

**Read coverage, stated.** Fully read: both facts files; the audit prompt's
ROLE / KNOWN CONTEXT / HARD CONSTRAINTS / PHASE 0; `.claude/hooks/wxcli-gate.sh`;
`wxcli-dist/settings.bundled.json`; `.claude/settings.json`.
Partially read: `commands/cleanup.py` (lines 60–330, 1058–1310 of 1478);
`migration/execute/engine.py` (840–964, rest grepped);
`migration/preflight/{__init__,runner,checks}.py` (targeted regions);
`migration/store.py` (110–180, 750–840); `tools/postman_parser.py` (86–165);
`tools/command_renderer.py` (1765–1820 + grep); `tools/generate_commands.py`
(200–245); `tools/drift_check.py` (2128–2208 **only** — the gate is Phase 2's job
and I make no claim about the other 3,700 lines). All 184 tracked command modules
were `ast`-parsed, not read. **Not measured:** LOC removed, effort, percentages of
anything I did not count.

---

## Q1 — Commands capable of org-wide mutation or migration-scale change

Extends `00-facts.md` Q8 (which names `cleanup`, `cucm execute`/`retry-failed`,
`update`, 179 DELETEs, 779 ungated writes) and `part2.md` §8a/§8b (which adds
`organizations delete`, `scim-bulk create`, and the 312-zero-positional /
60-`get_org_id()` structural surface). Both stop at the inventory. This section
answers the question they left: **for one invocation, how many remote objects, and
what bounds it.**

Six classes, ordered by blast radius. **Two of them appear in neither facts file**
(classes 3 and 4).

### Class 1 — Whole-org sweep: `wxcli cleanup run` *(target A, hand-written)*

| | |
|---|---|
| **Largest single invocation** | Every resource of **18 types** across 13 layers in the org — dial plans, route lists/groups, translation patterns, trunks, queues, hunt groups, auto attendants, paging groups, call parks, call pickups, operating modes, schedules, virtual lines, devices, workspaces, users, numbers, locations (`cleanup.py:71-201`, `:205-219`) |
| **What bounds the count** | **Nothing in `cleanup.py`.** The inventory is built with `follow_pagination` on every type (`cleanup.py:254`, `:271`, `:286`), so it walks the whole collection. The only ceiling is the shared runtime's `DEFAULT_MAX_PAGES = 1000` (`auth.py:168`), whose own comment puts that at ~200,000 records `[verified]` |
| **What bounds the scope** | `--scope` or `--all` is mandatory (`cleanup.py:1103-1108`); users and locations are opt-in via `--include-users` / `--include-locations` (`cleanup.py:1067-1074`); `--exclude-user-domains` subtracts. The **org** is never an argument — `get_org_id()` (`cleanup.py:1111`) |
| **What the operator is told** | The only consequence-bearing confirm string in the codebase: `Delete {total} resources? This cannot be undone` (`cleanup.py:1255-1258`) — it states the count. `--force` removes it |
| **Concurrency** | 5 per layer, `--max-concurrent` (`cleanup.py:1083`) |

### Class 2 — Migration executor: `wxcli cucm execute` *(target B)*

| | |
|---|---|
| **Largest single invocation** | Every row in `plan_operations` with `status='pending'`. `execute_all_batches` loops `while True: batch = get_next_batch(store)` until empty (`execute/engine.py:876-879`) — **one invocation drains the entire plan**, not one batch |
| **What bounds the count** | **Nothing local.** No cap, no scope flag, no `--limit`. The number is whatever `wxcli cucm plan` expanded from the discovered CUCM cluster. Each op is 1..k HTTP calls (`execute/__init__.py:183` `API_CALL_ESTIMATES`) |
| **Verbs it can issue** | **POST, PUT, GET only.** 29 `("POST"` + 24 `("PUT"` + 1 `("GET"` call tuples in `execute/handlers.py`; 2 PUT + 1 GET in `engine.py`. **Zero DELETE anywhere in `execute/`** — the only `DELETE` statements are SQLite (`execute/batch.py:174-175`) `[verified]`. So its destructive modes are *overwrite* and *duplicate-create*, never remote deletion |
| **The overwrite that deletes** | The tier-9 `reconcile_members` op PUTs a **whole** member array to hunt groups, queues, pickup groups and paging groups; these endpoints replace the array, so a short list removes members — including any an operator added by hand (`execute/handlers.py:2271`, documented at `execute/CLAUDE.md` "Membership Reconcile"). Guarded: an unresolved member returns `skipped(reason)` and writes nothing |
| **Ops that are themselves org-scale** | At ≥100 devices the planner swaps per-device ops for bulk-job submissions — `bulk_device_settings`, `bulk_line_key_template`, `bulk_dynamic_settings`, `bulk_rebuild_phones` (`execute/CLAUDE.md`, "Bulk Job Operations"). One plan op then equals one org-or-location-wide device job (see class 3 for what those jobs touch) |
| **Concurrency** | 20 default, `min=1, max=50` enforced by Typer (`commands/cucm.py:3151-3153`) |
| **What the operator is told before it starts** | Only `Starting migration execution (concurrency: N)` (`commands/cucm.py:3212`). **The operation count is never printed before the writes begin** — it appears only in the post-run summary (`commands/cucm.py:3230-3233`) `[verified]`. `00-facts.md` Q10 established there is no gate; this adds that there is no *disclosure* either |

`wxcli cucm retry-failed` is the re-arming command: one unbounded
`UPDATE plan_operations SET status='pending' WHERE status='failed'`
(`commands/cucm.py:3258-3261`), no confirm, no scope flag, and every reset row
becomes work for the next `execute`.

### Class 3 — Asynchronous job endpoints *(target A)* — **named in neither facts file**

**14 mutating commands POST to a `/jobs/` endpoint. All 14 are POSTs, so all 14
are inside the 779 with no gate** `[verified]`. These are the largest blast radius
on the generated surface, and the scope-widening lives in the request body rather
than in a flag.

| Command | Objects one invocation can alter | What bounds it |
|---|---|---|
| `device-settings create-apply-line-key-template` (`device_settings.py:881`) | Every compatible device in the org. Spec: *"apply a line key template or apply factory default Line Key settings to devices in a set of locations **or across all locations in the organization**"*. `--action APPLY_DEFAULT_TEMPLATES` resets phones to factory line keys | `locationIds` **is not a flag** — `--help` exposes only `--action`, `--template-id`, `--exclude-devices-with-custom-layout`; the location filter is reachable only through `--json-body` `[verified]` |
| `device-settings create-call-device-settings` (`device_settings.py:1127`) | Spec: *"will modify the requested device settings **across all the devices**"*; a `locationId` narrows it | `--location-id` is optional. Bounded server-side only by one-job-per-org (409) — a bound on **concurrency, not scope** |
| `device-dynamic-settings create` (`device_dynamic_settings.py:285`) | Same job family (`dynamicDeviceSettings`) | same |
| `device-settings create-rebuild-phones` (`device_settings.py:1350`) | *"Rebuild **all** phone configurations for the specified location"* | `--location-id` is **required** — the only job here whose scope cannot default to the org `[verified]` |
| `numbers create-manage-numbers` (`numbers.py:322`) | Spec: *"Up to **1000** numbers can be given in `MOVE` … per request"* | An explicit upstream cap of 1000, plus 409 if a move job is already running |
| `user-settings create-move-location` (`user_settings.py:2043`) | Spec: *"A maximum of **100** users can be moved at a time"* | 100 per request. **The dry-run is a body field, not a flag**: `validate: true` validates, `validate: false` performs the move. `--help` offers no options at all beyond `--json-body` `[verified]` |
| `location-settings create-delete-calling-location` (`location_settings.py:1215`) | Disables Webex Calling on an entire location — a **destructive location-scale operation issued as a POST**, hence ungated | Bounded by *server-side* safe-delete checks (`BATCH-1012004`…`1012011`: trunks in use, users, workspaces, virtual lines, features attached). **`--force-delete` removes that bound** — and note this flag *adds* force to the server, the inverse of `--force`'s meaning on the 179 deletes |
| `activation-email create` (`activation_email.py:15`) | Sends real activation email to a caller-supplied list of users | The list in the body |
| 6 × `pause`/`resume` job-control commands | 1 job each | job id required |

### Class 4 — Bulk-array writes *(target A)* — **named only as `scim-bulk` in `part2.md` §8a**

**37 mutating commands POST or PATCH to a `/bulk` path** `[verified]`. Each takes an
array (`{"items":[…]}` for the 30 Contact Center ones) and every element is one
remote object created or modified. All are POST/PATCH, so none is gated.

- **Bounded by the spec:** `scim-bulk create` — *"The maximum number of operations
  in a request is **100**"*, with `failOnErrors` between 1 and 100 (`webex-admin.json`,
  `POST /identity/scim/{orgId}/v2/Bulk`). Its operations may be `POST`/`PATCH`/**`DELETE`**,
  so this is the one command in class 4 that can delete.
- **Bounded by nothing found:** the 30 `cc-*` `/bulk` endpoints (`cc_queue`,
  `cc_team`, `cc_site`, `cc_skill`, `cc_entry_point`, `cc_aux_code`, …). I found no
  array-size limit in `webex-contact-center.json` `[verified — searched the operation
  descriptions]`; whether the service enforces one is `UNKNOWN`.
- **Deletion disguised as POST:** `org-contacts create-delete` → `POST
  contacts/organizations/{org_id}/contacts/bulk/delete` (`org_contacts.py`), and
  `meetings create-bulk-delete` → `POST meetings/{id}/registrants/bulkDelete`
  (`meetings.py`). Both destroy N objects per call with no gate.

### Class 5 — Collection-scoped DELETEs *(target A)*

**21 of the 179 DELETE commands target a collection, not an item** — their URL ends
in a literal segment, so one invocation destroys every member `[verified]`:

`authorizations delete` · `call-queue delete-supervisors-config` ·
`call-queue delete-dnis-queues` · `cc-dial-number delete` · `conference delete` ·
`dect-devices delete-base-stations-dect-networks-bulk` ·
`dect-devices delete-handsets-dect-networks-bulk` ·
`device-settings delete-background-images` ·
`location-call-handling delete-access-codes-all` ·
`location-call-handling delete-digit-patterns-outgoing-permission` ·
`meeting-chats delete` · `meetings delete-breakout-sessions` ·
`meetings delete-registration` · `numbers delete` · `partner-admins delete` ·
`user-settings delete-access-codes` ·
`user-settings delete-digit-patterns-outgoing-permission` ·
`virtual-line-settings delete-access-codes` ·
`virtual-line-settings delete-digit-patterns-outgoing-permission` ·
`workspace-settings delete-access-codes-all` ·
`workspace-settings delete-digit-patterns-outgoing-permission`

All 21 carry the generated confirm. **The prompt names the container, never the
count or the members** — `numbers delete` asks `Delete Numbers for {location_id}?`
(`numbers.py:137`) whether the body holds one number or forty. Five of these are
body-scoped (known issue #21): the body is what limits the delete, and the confirm
string cannot see it.

### Class 6 — Item DELETEs *(target A)*

The remaining **158** DELETE commands remove one object each. The exception that
matters is scope, not count: `organizations delete` removes one object whose
contents are the entire org, takes **zero arguments**, and derives the target from
resolved config (`part2.md` §8a, `organizations.py:65-90`).

### The bound that does not ship

`00-facts.md` and `part2.md` both stop at "no confirmation gate." There is a
second control, and it is **local to this repository, not to the product**
`[verified]`:

- `.claude/settings.json` registers a `PreToolUse` hook, `.claude/hooks/wxcli-gate.sh`,
  which denies any non-`list*`/`show*` `wxcli` invocation outside the
  `wxc-calling-builder` / `migration-advisor` agents (`wxcli-gate.sh:64-67`, `:121-124`).
- It **does not ship.** `wxcli-dist/assemble.py:20,161` substitutes
  `wxcli-dist/settings.bundled.json`, whose entire hook block is one `SessionStart`
  entry running `wxcli --no-update-check update --hook`, plus a blanket
  `"Bash(wxcli:*)"` allow. **No PreToolUse gate, no read-only verb policy.**
- So for every downstream installation, the bounds enumerated above are the *only*
  bounds. The read-only policy an auditor might assume exists is a property of one
  developer's machine.

The hook's own header also records the one time class 6's worst case was actually
exercised: on 2026-07-28 a subagent imported four generated delete functions,
`OptionInfo`-is-truthy skipped the confirm, and four unconfirmed DELETEs reached the
live org, one of them `DELETE /v1/organizations/{id}` — *"Only Cisco refusing them
saved it"* (`wxcli-gate.sh:41-44`). **What bounded that blast radius was the remote
API, not any local control.**

### The guard the repository already knows how to emit

This is the highest-value fact in Phase 0, and it changes what a Phase 5 finding
should say.

`00-facts.md` Q10 concludes *"the generator keys destructiveness on the HTTP verb."*
That is true of the **guard** and false of the **classification**. `tools/postman_parser.py:107`
defines `classify_real_semantics(name, body_fields)`, which returns a destructive
verb from two verb-independent signals: the summary's leading verb
(`DESTRUCTIVE_SEMANTICS` at `:86-94` — delete/remove/purge/clear/revoke/unassign/cancel),
or *every* body field being delete-shaped (`:98`, `:128`). It is attached to every
endpoint at parse time (`tools/openapi_parser.py:742`).

Measured by running that classifier over the nine tracked specs `[verified]`:

| | distinct `(method, path)` operations |
|---|---:|
| Classified destructive by the generator's own rule | **199** |
| — rendered as `DELETE` (confirm emitted) | 176 |
| — **rendered as POST / PUT / PATCH (no confirm emitted)** | **23** (18 POST, 4 PUT, 1 PATCH) |

The 23 include all 11 CC `purge-inactive-entities` operations, both recording-recycle-bin
purges, the four `accessCodes` PUTs whose only body field is `deleteCodes`, and
`meeting-preferences delete-delegate-emails`.

`real_semantics` is consumed at three renderer sites — the success word, the
`DESTRUCTIVE:` docstring warning, and a docstring branch
(`tools/command_renderer.py:408`, `:461`, `:1458`) — and by a **build-failing** gate
on misleading names (`tools/generate_commands.py:216-240`, acked in
`tools/field_overrides.yaml:910`). It is **not** consulted where the confirm is
decided: `typer.confirm` is emitted from exactly one place,
`_render_delete_command` (`tools/command_renderer.py:1814`, `:1817`), selected on
`command_type`, which comes from the HTTP method.

So the correct framing for later phases is not *"the generator cannot tell which
operations destroy"*. It is: **the generator does tell, on 23 operations it renders
without a guard, and the guard is emitted by a different code path that never asks.**
A Phase 5 finding that proposes "teach the generator about destructiveness" would be
a false finding — that already exists and is CI-enforced for naming.

### Correction to KNOWN CONTEXT: the 51 hidden commands

The audit prompt states *"51 commands are `hidden=True` — dispatchable but absent
from `--help` … by that premise those 50 are undiscoverable"*, and `00-facts.md:145`
records the same. **Measured, this does not hold** `[verified]`:

- 51 `hidden=True` occurrences in tracked `commands/*.py`, of which **50 are on
  `@app.command` decorators and 1 is a hidden *option*** — `--hook` on `wxcli update`
  (`commands/update.py:215-216`).
- All **50 hidden command names sit on functions that also carry a visible name.
  Zero functions are reachable only by a hidden name.** They are backward-compatibility
  aliases from the 28-command rename wave: `admin_recordings` `create-purge` (hidden)
  → `delete-recordings-recycle` (visible); `announcements` `generate-a-text` → `tts-generate`;
  `call_queue` `show-queues` → `show`.
- Confirmed live: `wxcli admin-recordings --help` **does** list `delete-recordings-recycle`.
- The drift gate already documents this exact mechanism (`tools/drift_check.py:2136-2140`).

**The "hidden destructive command — no discoverability, full capability" cell the
prompt calls the worst in the matrix is empty.** Every hidden name is a second
spelling of a command that appears in `--help`. The residual issue is different and
smaller: an enumeration built by parsing help output will miss 50 *dispatchable
strings*, which matters for Phase 3's completeness, not for operator discoverability.

---

## Q2 — Which remote operations are irreversible, and can we do better than verb inference?

Extends `00-facts.md` Q9 (*"`[inferred]` — from HTTP verb and Webex semantics …
because no reversibility field exists"*) and `part2.md` §9 (which adds the
`rollback-ops`-is-a-report finding and the no-pre-write-snapshot point).

**Yes — better is available, in three ways, none complete. Verb inference is not
the ceiling; the absence of a *machine-readable* field is.**

### 1. Upstream prose states permanence on 15 operations `[verified]`

Searching every operation `summary` + `description` across the nine tracked specs
for permanence language returns 15 hits — all `DELETE`, so verb inference *agrees*,
but these are upgraded from inferred to stated by the vendor:

`DELETE /organizations/{orgId}` (*"permanently"*) ·
`DELETE /telephony/config/virtualExtensions/{extensionId}` (*"permanently"*) ·
`DELETE /{orgId}/project/{projectId}/flows/{flowId}` (*"Permanently"*) ·
`DELETE /rooms/{roomId}` · `DELETE /meetings/{meetingId}` ·
`DELETE /meetings/{meetingId}/breakoutSessions` ·
`DELETE /meetings/{meetingId}/interpreters/{interpreterId}` ·
`DELETE /meetingInvitees/{meetingInviteeId}` · `DELETE /meetingSummaries/{summaryId}` ·
`DELETE /meetingTranscripts/{transcriptId}` · `DELETE /recordings/{recordingId}` ·
`DELETE /admin/recordings/{recordingId}` · `DELETE /convergedRecordings/{recordingId}`
(*"cannot be recovered"*).

### 2. A soft-delete / restore surface exists — this refutes a claim in `00-facts.md`

`00-facts.md` Q9 states: *"No soft-delete, undo, or trash surface appears in the CLI."*
**Refuted** `[verified]`. Both the spec and the shipped CLI carry a recycle-bin triad
for recordings:

| Stage | Spec | Command |
|---|---|---|
| Soft delete | `POST /recordings/softDelete`, `POST /convergedRecordings/softDelete` | `admin-recordings create-soft-delete`, `converged-recordings create-soft-delete` |
| **Restore** | `POST /recordings/restore`, `POST /convergedRecordings/restore` | `admin-recordings create-restore` |
| Purge (irreversible) | `POST /recordings/purge`, `POST /convergedRecordings/purge` | `admin-recordings delete-recordings-recycle`, `converged-recordings delete-recordings-recycle` |

Verified live in `wxcli admin-recordings --help`: `create-soft-delete`,
`create-restore` and `delete-recordings-recycle` are all listed.

This inverts the verb heuristic twice over. The **reversible** step is a POST; the
**irreversible** step is also a POST — and it carries `--purge-all`, which empties
the entire recycle bin (`admin_recordings.py:474-477`). A reversibility model built
on the HTTP verb classifies both as "write, probably fine."

### 3. The generator's own `real_semantics` — the best signal in the repo

Already described under Q1. It is verb-independent, computed for every operation,
and identifies 23 destructive non-DELETE operations. It answers *"does this destroy"*
— not *"can it be undone"* — but it is strictly better than verb inference and it
already exists.

### The ceiling, stated

- **No machine-readable reversibility field exists anywhere** — confirming
  `00-facts.md` Q5c. I checked the specs for vendor extensions: the only `x-` key on
  any operation across all nine specs is `x-codegen-request-body-name` `[verified]`.
- `tools/spec_semantics.json` hashes each field description (`#`) and the rules
  stated in it (`%`). So if Cisco ever *edits* "cannot be recovered", drift-gate check 19
  reports a hash delta — **the change is detected, the meaning is never extracted.**
  That is exactly the distinction `00-facts.md` Q5c draws, and it holds.
- **PUT/PATCH remain practically irreversible** for the reason `part2.md` §9 gives —
  no pre-write snapshot; `--verify` re-reads *after* the write (`common.py:136`).
  Extension: **the schema for a snapshot exists and is unused.** The migration store's
  `journal` table declares `request`, `response` and **`pre_state`** columns
  (`migration/store.py:120-130`), and `pre_state` is never populated by any caller —
  the only two writers omit it (see Q3).

**Conclusion.** For the 179 DELETE commands, verb inference and the evidence agree,
and 15 operations have vendor prose confirming it. For the 779 writes, verb inference
is *wrong in both directions*: it misses 23 destructive POST/PUT/PATCH operations the
repo itself classifies, and it flags as risky two POSTs (`softDelete`, `restore`) that
are the reversible half of a documented recycle-bin flow. **Do not carry
"DELETE = destructive" into Phase 5 as a settled proxy — the prompt is right to call
it a live question, and the measurement above answers it: no.**

---

## Q3 — Invocation logging, shell history, CI record

**Confirmed, not refuted.** `00-facts.md` Q14 (one logger, two retry warnings, no
argv or exit-code capture) and `part2.md` §14 (`logging` imported in 66 modules,
no handler configured except `basicConfig` under `--debug`, nothing persisted) both
hold; I found nothing that contradicts either. Four extensions:

**1. A hook sees every invocation and records none.** `[verified]`
`.claude/settings.json` registers a `PreToolUse` hook on `Bash` running
`.claude/hooks/wxcli-gate.sh`. That script receives the full command string on stdin
(`wxcli-gate.sh:35-37`) — the one place in the whole system where argv is already in
hand — and contains **zero** log, `tee`, redirect or JSONL writes. It decides
allow/deny and exits. This is the cheapest possible Phase 1 attachment point and it
is presently a pure gate.

**2. The gate is dev-only, so there is nothing to log downstream either.** `[verified]`
`wxcli-dist/assemble.py:161` writes `wxcli-dist/settings.bundled.json` over
`.claude/settings.json` in the shipped bundle; that file's only hook is a
`SessionStart` `wxcli --no-update-check update --hook`. Downstream agent sessions
have no PreToolUse hook at all.

**3. The migration `journal` table is an audit-log schema that the write path never
uses.** `[verified]` `part2.md` §14 flagged `journal` and `merge_log` as `UNKNOWN`
beyond existence. Enumerated:

- `journal` (`migration/store.py:120-130`) — `timestamp, entry_type, canonical_id,
  resource_type, request, response, pre_state`. That is precisely the shape Phase 1
  asks for, one layer down.
- It is written at **two** sites, **both in the read-only discovery stage**:
  `entry_type="file_ingestion"` (`commands/cucm.py:1220-1225`) and
  `entry_type="discovery_complete"` (`migration/cucm/discovery.py:251-256`).
  **Nothing in `migration/execute/` writes it**, and `pre_state` is passed by no
  caller anywhere in `src/wxcli/`.
- `merge_log` (`store.py:133-142`) records pipeline merge actions
  (`store.py:657-718`), i.e. local store reconciliation, not remote calls.
- The only durable record of what was written remotely is `plan_operations`:
  `status`, `webex_id`, `error_message`, `completed_at`, `attempts`
  (`store.py:145-159`). **Per-operation outcome only** — no argv, no request body, no
  response body, no prior state. It answers "did op X succeed" and cannot answer
  "what did we send" or "what was there before."

**4. No CI record of agent runs.** `[verified]` `.github/workflows/ci.yml` runs
`pytest` and the drift gate; the gate's output goes to `gate.log` and is `grep`ped
in-job (`ci.yml:128-143`). No `upload-artifact`, no retention, no `wxcli` invocation
anywhere in either tracked workflow.

**So Phase 1 is greenfield, as `00-facts.md:417` says — but not from zero.** Two
substrates already exist and are unused: the hook (has argv, logs nothing) and
`journal` (has the schema, is written only by the read-only stage).

---

## Q4 — Target B scope: which migration stages write remotely

New work; neither facts file breaks the migration subsystem down by stage.
LOC are `wc -l` over git-tracked files per subpackage `[verified]`.

| Stage | LOC | Reads CUCM | Reads Unity | Reads Webex | **Writes Webex** | Writes CUCM | Local only | Evidence |
|---|---:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| `cucm/` | 4,611 | ✅ | ✅ | — | **no** | **no** | store | `cucm/connection.py:22-24` (`zeep`); `cucm/unity_connection.py:14` (`requests`) |
| `transform/` | 18,517 | — | — | — | **no** | — | ✅ | no HTTP client imported anywhere in the subtree |
| `preflight/` | 1,477 | — | — | ✅ | **no** | — | ✅ | `preflight/__init__.py:70-77` (`subprocess` → `wxcli … -o json`); `preflight/runner.py:311-336` (one direct GET) |
| `execute/` | 8,119 | — | — | ✅ | **YES** | — | store | `execute/engine.py:17` (`aiohttp`), `:875` session, `:191`/`:326`/`:582` `session.request(method, …)` |
| `export/` | 1,013 | — | — | — | **no** | — | ✅ | no HTTP client imported |
| `report/` | 8,302 | — | — | — | **no** | — | ✅ | no HTTP client imported |
| `advisory/` | 3,738 | — | — | — | **no** | — | ✅ | no HTTP client imported |

### The blast radius Phases 5 and 6 must cover in full

**`src/wxcli/migration/execute/` — 8,119 tracked LOC — plus the two commands that
drive it, `execute` (`commands/cucm.py:3150`) and `retry-failed` (`:3245`).**
That is the entire remote-write surface of target B. Everything else in the 46,684
lines reads, or writes SQLite and files.

Four scope facts about that surface:

- **It cannot delete on Webex.** POST/PUT/GET only (Q1, class 2) `[verified]`.
- **CUCM is read-only, verified not assumed.** Every AXL operation invoked is
  `list*`, `get*`, or `executeSQLQuery` (`cucm/connection.py:275`, `:342`, `:363-370`);
  no `add*`/`update*`/`remove*`/`do*` AXL verb appears anywhere in `src/wxcli/`, and
  `executeSQLUpdate` — AXL's write path — appears **zero** times `[verified]`.
- **Unity Connection is read-only and is a third external system.** `00-facts.md` Q6
  states *"No Unity, no Expressway, no other on-prem client found in `src/`."*
  **Refuted** `[verified]`: `migration/cucm/unity_connection.py` is a tracked CUPI
  REST client over `requests` (`:14-15`, base `https://{host}/vmrest` at `:46`). All
  eight call sites are `session.get` (`:68`, `:235`, `:276`). It adds a fourth HTTP
  stack usage to the four `00-facts.md` Q2 counted as dependencies, and a third
  external system to Q6's two.
- **The "imports the shared runtime exactly once" framing understates the coupling.**
  The single import at `preflight/runner.py:312` is real, but the migration path
  touches the shared runtime three ways: (1) that import; (2) `commands/cucm.py`
  — the driving command — calls `resolve_token()` (`:3164`) and `get_api()` +
  `rest_get` for the license lookup (`:3199-3202`) before handing the raw token to
  `aiohttp`; (3) `preflight` shells out to the `wxcli` binary
  (`preflight/__init__.py:74-77`), which re-enters the *entire* shared runtime in a
  child process. Only the writes bypass it. For Phase 5 that matters: the two retry
  policies `00-facts.md` Q7 flags do not merely coexist — they run in the same
  invocation, `auth.py`'s for the token and license read, `rate_limiter.py`/`engine.py`'s
  for every write.

### One observation, deferred

`preflight`'s bulk-device-job probe cannot reach the network. It calls
`api.session.ep(...)` and `api.session.get(...)` (`preflight/runner.py:329`, `:334`),
but `WebexSession` defines neither method — its full method set is `_headers`,
`_request`, `_json_or_raise`, `rest_get`, `rest_put`, `rest_post`, `rest_patch`,
`rest_delete`, `follow_pagination`, `follow_page_param`, `follow_scim`
(`src/wxcli/auth.py:203-368`) `[verified]`. The probe also catches
`requests.RequestException` (`runner.py:333`) while the session is `httpx`-based
(`auth.py:206`). The resulting `AttributeError` is swallowed by
`except Exception` in the caller, which downgrades the check to
`WARN "Bulk device job probe failed"` (`preflight/checks.py:873-880`) rather than
`PASS`/`FAIL` `[verified]`. Recorded here because it changes the Q4 row —
`preflight` reads Webex by subprocess, not by this path. **Severity is a Phase 5
call, not a Phase 0 one.**

---

## Open items handed to later phases

1. Whether the 30 Contact Center `/bulk` endpoints enforce any array-size limit —
   `UNKNOWN`; nothing in `webex-contact-center.json` states one.
2. Whether `execute`'s bulk-job ops and the generated `/jobs/` commands collide on
   Webex's one-job-per-org constraint during a migration. Not investigated.
3. `tools/drift_check.py` beyond lines 2128–2208 — deliberately untouched; Phase 2.
4. The `preflight` probe defect above.

