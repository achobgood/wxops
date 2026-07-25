# wxcli Generator & Dev Tooling

This file contains developer/maintainer reference for the wxcli generator pipeline, Postman sync, test status, and doc maintenance protocols. It is intentionally kept out of the root CLAUDE.md to avoid loading into the builder agent's context on every launch.

## Pipeline at a Glance

A wxcli command is not hand-written — it is generated from Cisco's own OpenAPI spec and **is** the code that runs. There is no separate "real" CLI behind the generated files.

1. **Spec** (`specs/*.json`) — Cisco's machine-readable list of every endpoint, its fields, and their descriptions. Pulled by `update-specs.py`.
2. **Parse** — `openapi_parser.py` turns each endpoint into an `Endpoint` object (name, path, query/body fields, enums, descriptions).
3. **Render** — `command_renderer.py` writes one Typer command file per tag into `src/wxcli/commands/`.
4. **Register & run** — `main.py` (~lines 177-183) imports each generated module listed in the `_registry.py` manifest and attaches it with `add_typer`. So `wxcli call-pickup create` executes the `create()` function inside the generated `call_pickup.py`. **The generated files are the CLI; nothing else runs behind them.**
5. **`--help` is not a separate source.** Typer produces it at runtime by reading the docstrings and option `help=` strings *inside those same generated files*. A field's `help=` text is the spec's field description, bounded in exactly one place (see Generator Rules).

Implication: to change what a command *does*, fix the parser / renderer / `field_overrides.yaml` and regenerate — never edit the output. To change what `--help` *says*, change the spec description or the renderer's help logic and regenerate. Both the source and the `--help` output move together because they are the same strings.

## Tools

| Path | Purpose |
|------|---------|
| `tools/postman_parser.py` | Shared dataclasses (`Endpoint`, `EndpointField`) and utilities for the generator pipeline |
| `tools/openapi_parser.py` | Parses OpenAPI 3.0 spec into `Endpoint` objects |
| `tools/command_renderer.py` | Renders `Endpoint` objects into Typer command files (the files that ARE the CLI at runtime) |
| `tools/field_overrides.yaml` | Table columns, display config, and endpoint overrides |
| `tools/generate_commands.py` | Orchestrates OpenAPI parse → render → write pipeline |
| `tools/postman_spec_diff.py` | Offline Postman↔spec gap diff — compares exported collection JSON against local OpenAPI spec |

## Postman↔Spec Sync

Periodic gap reports live in `docs/reports/postman-spec-sync-YYYY-MM-DD.md`. Run the prompt at
`docs/prompts/postman-sync-periodic-report.md` to generate a new one via Postman MCP.

Offline alternative (no MCP needed — export the Postman collection first):
```
python3.14 tools/postman_spec_diff.py \
    --spec specs/webex-cloud-calling.json \
    --postman exported-calling.json \
    --skip-tags tools/field_overrides.yaml
```

Postman fork IDs (wxcli-dev):
- Cloud Calling: `15086833-e014a019-ecc3-4140-ab56-f2e9ccf7f95b`
- Admin: `15086833-5c8bec2d-afcd-4f60-a0ca-cf3bfc798755`
- Device: `15086833-6e026ee0-1f83-4d2b-bba6-b481ab62d0b6`
- Messaging: `15086833-12f8091a-7404-46a7-a1df-61eef3f31435`
- Meetings: `15086833-19910ac6-e687-4b90-b33a-3a02c6f50ce9`
- Contact Center: `15086833-a864a970-27a6-41ad-89d4-cf794012bbcc`

Mock server URLs (public, no auth required — return saved response examples):
- Cloud Calling: `https://f550a728-63cc-4da0-8a6f-e3eda351b9a9.mock.pstmn.io`
- Admin: `https://4ba8e16c-a764-4812-8eb3-e5dc00edcfff.mock.pstmn.io`
- Device: `https://24f543e0-234c-49b6-989d-1627497bf1b0.mock.pstmn.io`
- Messaging: `https://c87534f1-1e5c-477e-a249-333815c03415.mock.pstmn.io`

## CLI Test Status

176 command groups (171 generated modules, manifest-registered). Calling/admin/device/messaging groups live-tested across 4 batch sweeps (2026-03-19 through 2026-03-21). Contact center and meetings groups regenerated at the 2026-07-01 spec sync and not fully live-tested. CUCM pipeline tested against live test bed (10.201.123.107) with 2 test bed expansions. See git history for detailed test logs.

## Generator Rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
- **Never create new hand-written command files** unless adding functionality that the generator cannot produce (e.g., multi-step workflows, file downloads). The legacy trio is fully retired (2026-07-01: `locations.py`/`numbers.py` turned out to be generator output on disk; 2026-07-02: `licenses.py` consolidated into the generated `licenses` group per S3.1, with a one-release `licenses-api` alias). `users.py` was retired and replaced with an alias to the generated `people` command group. `converged_recordings_export.py` is a deliberate hand-written extension that registers `download` and `export` commands onto the generated `converged-recordings` group via a `register(app)` pattern. For simple CRUD commands, use the generator. If a generated command needs custom behavior, use `field_overrides.yaml`.
- **`auto_inject_from_config`** — `field_overrides.yaml` supports an `auto_inject_from_config: ["orgId"]` key per endpoint. Parameters listed here are omitted from `--help` and injected automatically from the saved config at runtime. This replaces the older `omit_query_params` approach for `orgId`.
- **Field `--help` text is truncated in exactly ONE place — do not add a second.** A field's `help=` string is the spec's field description, bounded only by `command_renderer._clean_desc` (collapses whitespace, truncates on a word boundary at a 300-char cap, never mid-token). `openapi_parser.py` must keep the **full** description — it previously sliced to 120 chars mid-word *on top of* the renderer's 60-char slice, so descriptions were double-truncated and routinely lost their trailing `Default: X` clause, and near-identical flags on large groups became indistinguishable (five `call-queue` tone toggles all ended `...plays a tone to agents when a`). Fixed in `chore(generator): keep full field descriptions in --help`. If help lines ever need shortening again, change the cap in `_clean_desc` only.
- **Spec files:** 9 tracked OpenAPI 3.0 specs in `specs/` — all regenerated by `spec_sync.py`: `webex-cloud-calling.json`, `webex-admin.json`, `webex-device.json`, `webex-messaging.json`, `webex-meetings.json`, `webex-contact-center.json`, `webex-ucm.json`, `webex-broadworks.json`, `webex-wholesale.json` (+ untracked dev-only `webex-flow-store.json`). `update-specs.py` pulls upstream refreshes for the first 7 only.
- **Pull updated specs:** `python3.14 tools/update-specs.py` — downloads latest from GitHub, reports diffs. BroadWorks and Wholesale are excluded.
- **Tag collision (retired 2026-07-01):** CC Site/Data Sources collisions are resolved by per-spec `cli_name_overrides`; regen order no longer matters for them (see known issue #17).
- **Multi-tagged ops render into every tag they carry.** Dedup is per-tag, so an op legitimately tagged twice (the 3 `hotDesking/members` ops are both `Features: Hot Desking Members` and `User Call Settings`) appears in both groups. Two guards make that safe — do not remove either without reading known issue #22:
  - **`tag_op_excludes`** (per-spec, `tag -> [path globs]`) drops spurious tag/operation pairings the upstream spec invents. Reach for it when a group fills with operations that plainly belong elsewhere; it is the right fix for a mis-tagged spec, not a dedup change.
  - **Secondary-tag ops cannot claim a bare command name.** `parse_tag` derives names primary-tag-first (`tags[0]`), so an op for which the tag is secondary can never take `create`/`show`/`update` from an op the tag actually owns. This protects the multi-tag case only — two ops in the *same* tag racing for a name still needs pinning per issue #18.
  - Only 27 ops across all 9 specs are multi-tagged. Any regen that moves a command-name count beyond those is a red flag; diff names, not just counts.
- Regenerate one tag: `PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --tag "Tag Name"` (the `_registry.py` manifest upserts automatically)
- Regenerate one spec (all tags): `PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all`
- Regenerate everything (all tracked specs, atomic — pulls specs, regens, updates the manifest, runs the drift gate): `python3.14 tools/spec_sync.py` (`--skip-update` to regen from specs on disk). Land the result as ONE commit. Historical tag-collision order sensitivity is gone (per-spec `cli_name_overrides` for CC Site/Data Sources), but `spec_sync.py` keeps CC-before-admin/meetings order anyway.
- Dev-only specs: `webex-flow-store.json` regens auto-apply `--dev-only` (guarded block in main.py, never enters the manifest).
- **CC response data key:** CC v2 list endpoints return `{"data": [...]}` not `{"items": [...]}`. The renderer adds a `"data"` fallback automatically. If adding a new CC list endpoint manually, use `result.get("items", result.get("data", ...))` for extraction.
- Reinstall after regen: `pip3.14 install -e . -q`

## Decision Record — CLI Surface

Why the generated CLI looks the way it does. Recorded because each of these was
re-derived from scratch at least once after the reasoning was lost to a commit
message. If you are about to change one, read the row first.

### `--output` reaches only three of six command types (defect, being fixed)

**State as of 2026-07-25:** the renderer emits `--output` at exactly three sites —
`command_renderer.py:306` (list, default `table`), `:421` (show, default `json`),
`:549` (create, default `id`). `_render_update_command`, `_render_delete_command`,
and `_render_action_command` emit **no `--output` at all**. Verify on
`src/wxcli/commands/locations.py:139-146`: `update` declares only `--json-body`
and `--debug`, so `wxcli locations update … -o json` fails with `No such option`.
The same gap covers some hand-written commands — `wxcli whoami -o json` fails
(`main.py:38-40`), as do `switch-org`, `clear-org`, and `cleanup run`.

**But `--output` is not simply absent everywhere else — on four hand-written
commands it already means a filesystem path**, and adding a format flag there
would collide two meanings onto one name:

| Command | `--output` means |
|---|---|
| `org_health_cli.py:23` | required `Path` — *"Directory to write results.json into"* |
| `cucm.py:2815, 2935, 2993` | output **filename** for assessment-report / user-diff / user-notice |
| `cucm.py:1448, 1566, 2200, 2342, 2474, 2563, 2620` | already a proper `table\|json` format flag — nothing to do |

Those four path-valued commands keep their path meaning and receive `--fields`
only. Check what an `--output` *means* before assuming a command lacks one.
(Corrected 2026-07-25 after external review: `cucm.py:1566` is the `decisions`
command's *format* flag — `help="Output format: table (default) or json"` —
not a report-writer filename; the writers are three, not four.)

**There is no design reason.** It grew. `--output` originally existed only on the
read commands (list, show). On **2026-03-24, `a795b58`** — *"fix: add -o json to
create commands"* — create was added, because create returns an id you script
against. The word *fix* is the tell: a gap noticed in use and patched, not a
design being implemented. Nobody revisited update/delete/action.

**Do not "explain" this split to a future reader as intentional, and do not
preserve it.** `2026-07-24-cli-ergonomics.md` Task 3 adds the missing three;
Task 6 covers the hand-written commands. An option present on most commands but
not all is worse for an agent than one that does not exist — it teaches a rule
that breaks unpredictably, costing a failed call plus a `--help` round trip each
time.

### The projection flag is `--fields` — not `--query`, not `--filter`

**Decided 2026-07-25.** The generator turns every spec parameter into a CLI
option, so any name we add globally must be free across all 1,872 commands or it
collides with something Cisco already named.

| Candidate | Commands already declaring it | Failure mode if reused |
|---|---|---|
| `--query` | **2** — `cc_search.py:14` (graphQL query string), `fs_flows.py:741` (flow search text, required) | Both bind the Python name `query` → duplicate argument → `SyntaxError`, module fails to import. **Loud.** |
| `--filter` | **65**, across 35 CC modules | Spec ones bind `filter_param`, so a renderer-added `filter` raises no Python error — two Click options share one flag string and silently shadow. **Silent, on 65 commands.** |
| `--project` | 26 | Same class |
| **`--fields`** | **0 commands, 0 doc citations** | — |

`--fields` was chosen because it is free everywhere, so the flag is uniform on
every command with **no per-command suppression logic and no exceptions**. It
also describes what it does.

**If a future spec revision introduces a `fields` parameter**, the fix is the
`_SUPPRESS_SPEC_PAGING_NAMES`-style guard (`command_renderer.py:40`) or a
`cli_name_overrides` entry for that endpoint — *not* renaming `--fields`, which
would break every doc and skill citing it and trip `drift_check` check 6. The
tree-wide duplicate-flag scan in the ergonomics plan's Task 7 step 4 is what
catches it; keep that scan in every future regen.

**One collision already exists in the spec today, not just hypothetically:**
`webex-contact-center.json`'s `GET /v1/{orgId}/functions` (tag `Functions`)
declares a spec parameter literally named `fields`. It is inert only because
that tag is in `skip_tags` for an unrelated reason (colon-action paths,
`tools/field_overrides.yaml:588`) — if `Functions` were ever un-skipped,
`_check_reserved_collisions` (`command_renderer.py:328`) raises
`ReservedParamCollisionError` at generation time instead of silently emitting
a duplicate `fields` function argument. The tree-wide duplicate-flag scan
above is the standing backstop for this and any other case a regen surfaces.

**Note for anyone reading `docs/plans/llm-cli-ergonomics.md`:** it recommends
`--filter` on the grounds that `--query` is taken twice. The observation is
correct and the conclusion is inverted — see the table above. Its `--output`
finding is real and valuable; its token figures are file bytes ÷ 4 and are not
measurements; its claim that request-template generation does not exist is false
(see `locations.py:147`).

### Rich strips colour on a non-TTY but keeps box-drawing

**Verified 2026-07-25.** A common misreading is that constructing `Console()` is
enough for output to degrade gracefully when piped. It is not. Rendering a 1×1
table with stdout redirected produces
`'┏━━━━━━━┓\n┃ Name  ┃\n┡━━━━━━━┩\n│ Sales │\n└───────┘\n'` — no ANSI escapes,
but 24 of 40 characters are box-drawing. Suppressing them requires
`Table(box=None)` explicitly, and for help screens `typer.Typer(rich_markup_mode=None)`
(Typer 0.24.1 declares `None` as a supported value). `print_json`
(`output.py:74-76`) uses builtin `print()` and never involved Rich, so it is
unaffected — any claim of a repo-wide reduction is overcounting.

See `docs/superpowers/plans/2026-07-25-cli-plain-output.md`.

## Known Issues — Generator / Pipeline Only

These were removed from root CLAUDE.md (not needed by the builder agent at runtime):

10. **CUCM CallPickupGroup creation with members fails on CUCM 15.0.** Create empty, then assign via `updateLine`. See `src/wxcli/migration/CLAUDE.md` known issues.
15. **Device settings templates are pipeline-only, not named Webex objects.** The migration pipeline generates "templates" for device settings, but Webex has no named template API object for device settings. Settings are applied directly at org, location, or device level via PUT.
16. **CC spec has duplicate operationIds across paths.** operationIds in `specs/webex-contact-center.json` are reused across different resource paths (e.g., `getConfig_22` on both `/business-hours/{id}` and `/cad-variable/{id}`). The parser deduplicates on `(operationId, path)` to handle this. Verify regen totals against the drift gate (`tools/drift_check.py`) rather than a hardcoded count.
17. ~~CC "Site" tag collides with Meetings "Site" tag.~~ **Retired 2026-07-01:** per-spec `cli_name_overrides` (`webex-contact-center.json: Site -> cc-site, Data Sources -> cc-data-sources`) resolve the collision; `cc_site.py` regenerates normally with `--all` and regen order no longer matters for this.
18. **Spec churn can silently rename commands.** New spec ops can win command-name races within a tag and rename operator-facing commands (happened to `call-queue show/update`, 2026-07-01). Pin load-bearing names with `tag_overrides` -> `command_name_overrides`. Review regen diffs for renames, not just additions.
19. **Query-param/body-field name collisions are skipped, not rendered.** When an endpoint has a body field whose flag name would collide with a path/query param (CC Flows `create-import` flowType), the renderer keeps the query param and drops the body flag — set the body field via `--json-body`.
20. **Command names come from the HTTP verb, so a destructive PUT is named `update-*`.** **FIXED 2026-07-14** — message + `--help` + a generator gate; the misleading *names* were kept on purpose (see below). `_derive_command_name` (`tools/postman_parser.py:59`) maps the verb to the name, but Cisco models some deletes as PUT-with-a-delete-body. The live example is `location-call-handling update-access-codes`: its own `--help` title is *"Delete Outgoing Permission Access Code Location"*, its body is `{"deleteCodes":[...]}`, and on success the renderer printed **"Updated."** An agent asked to "update the access codes" would delete them and be told it updated them.

    **The scope was 6x the first estimate.** Scanning for summaries that *start with* "Delete" found 4 operations. That detector was the wrong shape twice over:

    - **It missed the worst cases.** `PUT .../people/{personId}/outgoingPermission/accessCodes` has the summary *"Modify Access Codes for a Person"* — and `deleteCodes` as its **only** body field. It cannot add or modify; creating is a separate POST on the same path. Same for the virtual-line and workspace twins. Three delete-only operations whose summaries say "Modify" — summary-scanning can never see them. The location one is the *least* camouflaged of the four, because its summary is at least honest.
    - **It was too narrow on verbs.** Widening to Remove/Clear/Purge/Revoke/Unassign/Cancel took the count from 4 to 24 (of 26 candidates; the 2 `reset-voicemail-pin` ops are `action`-typed with truthful names and are correctly not flagged).

    Two independent signals are required, because either alone misses real cases: **(1)** the summary leads with a destructive verb; **(2)** *every* body field is delete-shaped, so the operation cannot do anything but delete. Signal 2 deliberately requires *all* fields — `Modify Dial Patterns` takes `dialPatterns` (add or delete) **plus** `deleteAllDialPatterns` and is a genuine update. Flagging it would have been a false positive that mislabels a real update as destructive.

    **FIXED 2026-07-14.** `classify_real_semantics` (`tools/postman_parser.py`, *not* the renderer — this file used to imply otherwise) computes real semantics at parse time onto `Endpoint.real_semantics`. Then:

    - **The success message follows semantics, not the verb** — `_success_message` in `command_renderer.py`. This was the actively harmful half. All 24 fixed: `update-access-codes` prints "Deleted.", `create-purge-inactive-entities` prints "Purged." A destructive POST also stops printing `Created: <id>`; it creates nothing and has no id to report.
    - **`--help` stops lying** — where the summary itself is misleading, the docstring gains `DESTRUCTIVE: this PUT only deletes despite the summary above. It cannot add or modify.` Applied to exactly the 3 "Modify Access Codes" twins; the location op already says "Delete" and is left alone.
    - **The generator refuses to render a silent mismatch** — `check_verb_semantics` hard-fails (exit 1) on any destructive op whose name carries no hint it destroys. A name that already says it (`create-purge-inactive-entities`) reads oddly but does not mislead, so it passes. 6 ops need an ack; they are declared in `field_overrides.yaml` -> `verb_semantics_ack`, and the generator re-checks each ack against its classification so the YAML cannot rot.

    **Names were deliberately NOT changed** (Adam, 2026-07-14). Renaming is user-facing and breaks anyone scripting `update-access-codes`, and the harm was the message, not the spelling. `verb_semantics_ack` records each kept name as reviewed. To rename later, pin via `tag_overrides` -> `command_name_overrides` (issue #18) and drop the ack — the gate then passes on the truthful name with no ack needed.

    Evidence: regen of all 9 specs → gate `result: PASS`, 176 command sets / 1872 commands (unchanged), **zero `@app.command` name changes**, 22 files touched (messages + 3 docstrings only). Guards proven by mutation: removing an ack exits 1; a stale ack (`delete`→`remove`), an ack naming a dropped path, and a bogus verb each fail `tests/test_field_overrides.py` — which is now tracked, so CI runs them.

    Not covered, deliberately: `reset` is excluded from `DESTRUCTIVE_SEMANTICS`. `video-mesh create-reset` still prints "Created:" after resetting event thresholds. A reset restores defaults rather than removing a resource, and including it risks false positives on legitimate reset actions. Revisit only with a concrete case.

21. **The renderer dropped `requestBody` on DELETE, so the 5 scoped deletes were inert.** **FIXED 2026-07-14** (renderer + `rest_delete`), and the original severity claim here was **WRONG** — corrected below so nobody re-inherits it.

    **What this issue used to say:** that a body-less DELETE "silently becomes delete-everything", e.g. `call-queue delete-supervisors-config` "deletes all supervisors in the org". **That was never tested. It is false.** Live-tested against `/telephony/config/supervisors` with two real supervisors present:

    ```
    DELETE /v1/telephony/config/supervisors   (no body)
    -> HTTP 400, Cisco-Spark-Error-Codes: 25024
       {"errorCode":25024,"message":"Invalid JSON format in request body:
        Required request body is missing: ..."}
    -> supervisors after: 2 of 2 SURVIVED
    ```

    The API **rejects** a body-less scoped delete. It was **inert, not dangerous** — it could never have worked, and could never have deleted anything. Delete-everything is gated behind an explicit `deleteAll: true` (also live-confirmed: with `deleteAll` passed, all supervisors were removed; without it, only the named `supervisorIds` were). An endpoint that wiped everything on an empty body would not need a `deleteAll` flag — that was the tell, and reading the spec's own field description would have settled it without a live call.

    **The real bug** (verified, now fixed): `_render_delete_command` never rendered body fields, and `rest_delete()` had no `json` parameter. 10 tracked spec ops declare a DELETE body; on 5 the body is what *scopes* the delete, so those 5 commands 400'd on every invocation:
    `call-queue delete-supervisors-config` (`supervisorIds`), `call-queue delete-dnis-queues` (`items`), `numbers delete` (`phoneNumbers`), `device-settings delete-background-images` (`backgroundImages`), `dect-devices delete-handsets-dect-networks-1` (`handsetIds`). The other 5 take optional metadata only (`reason`/`comment` on recordings/transcripts) and were unaffected.

    **The fix:** the DELETE branch now renders body fields + `--json-body` exactly as PUT/POST do, and required body fields are enforced **client-side** — a delete with no targets exits 1 locally and never reaches the wire, so the API's behaviour on an empty body stops mattering. `body or None` preserves the no-body wire format when nothing is supplied, so the 5 metadata-body deletes are unchanged.

    Live-proven end-to-end on supervisors: scoped delete removed exactly the named target and left the other in place. **Still unproven: the other 4 scoping deletes were fixed by the same code path but not live-tested** — `numbers delete` most deserves it.

    Lesson (this one cost a session): the claim above was inference stated as fact, in a file whose entire purpose is to be trusted. #20 is still UNFIXED and its claim is *observed* (its own `--help` says "Delete", it prints "Updated.") — do not let this correction cast doubt on that one.

22. **A spurious upstream tag can flood a group and steal its bare command name.** **FIXED 2026-07-14** (`tag_op_excludes` + primary-tag-first name derivation). Read this before touching dedup in `generate_commands.py`.

    **The spec artifact:** upstream tags all 24 `/telephony/calls/*` call-control ops with a second `External Voicemail` tag. They are call control (`dial`, `answer`, `hangup`) and already render into `call-controls`. The only real External Voicemail endpoint is `/telephony/externalVoicemail/mwi`. `dial` is not voicemail — the tag is wrong on those 24 ops.

    **Why it stayed hidden:** dedup was global, so the first tag to claim an op won it. `Call Controls` sorts before `External Voicemail`, so the artifact was masked by iteration order — not by any rule. That accident was the only thing keeping `external-voicemail` at 1 command.

    **What broke, once, in a shipped commit:** dedup was made per-tag to fix a real bug — 3 legitimately dual-tagged `hotDesking/members` ops were being dropped from `user-settings`, which is the name six skills document. Correct intent; the artifact then stopped being masked. All 24 call-control ops rendered into `external-voicemail` (1 -> 25) and `dial` won the bare `create` name.

    **Name the damage precisely — it was a rename, not a deletion.** `_dedup_command_names` disambiguates, so the MWI op survived under an auto-suffixed name (`create-mwi`) rather than disappearing. That is *worse* than deletion and the reason this issue exists: a deleted command errors loudly, whereas `external-voicemail create` silently changed from "set the message-waiting indicator" to "dial a call" while every doc kept citing `create`. When triaging this class, check what a bare name now *points at* — do not stop at "the command still exists".

    **The fix:** `tag_op_excludes` drops the bogus pairing at its source, so `external-voicemail` cannot be flooded regardless of dedup; per-tag dedup then restores the 3 hot-desking commands; and `parse_tag` derives names primary-tag-first so a secondary-tag op can never take a bare name from an op the tag owns. Verified by a name-level per-group diff (all 184 groups, committed vs regenerated): zero groups changed, so the generator now reproduces the tree exactly instead of dropping 3 commands.

    Lesson: the fix for a mis-tagged spec is to fix the tagging, not to loosen dedup. The break shipped because its commit message claimed "drift_check.py runs with no new issues" while the gate was in fact failing — that single unverified claim is the whole reason a command got repurposed. Run the gate, paste the output, and diff command *names* (issue #18), not just counts. Note the trap in how it surfaces: the gate reports "docs cite flags that don't exist", which reads like a docs bug. The docs were right and the CLI was wrong; "fixing" the docs to match would have cemented the break.

## Templates, Examples & Plans

| Path | Purpose |
|------|---------|
| `docs/templates/deployment-plan.md` | Template: what the agent produces before executing |
| `docs/templates/execution-report.md` | Template: what the agent produces after executing |
| `docs/plans/` | Generated design docs (one per customer build) |

## Agent Teams

Two reusable agent team patterns for development workflows. Requires Claude Code v2.1.32+.
Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json`.

| Pattern | Template | When to Use |
|---------|----------|-------------|
| **Spec-to-Ship** | `docs/team-prompts/spec-to-ship.md` | Features touching 2+ of: code, tests, docs. 3 teammates (impl/tests/docs). |
| **Reference Audit** | `docs/team-prompts/reference-audit.md` | Weekly/monthly drift check across 46 reference docs. 4 teammates by doc category. |

**Usage:** Open the template, copy the spawn prompt, fill in the bracketed values, paste into a session.

**Not for:** Quick bug fixes, single-file edits, exploratory research — use normal sessions or subagents.

## Reference Doc Sources

All reference docs are grounded in official API specs and documentation:

- **OpenAPI 3.0 specs** — `specs/webex-cloud-calling.json` (calling), `specs/webex-admin.json` (admin), `specs/webex-device.json` (devices), `specs/webex-messaging.json` (messaging), `specs/webex-meetings.json` (meetings), `specs/webex-contact-center.json` (contact center)
- **Postman collection** (`../postman-webex-collections/webex_cloud_calling.json`) — legacy reference, 22.5MB, 1,079 endpoints
- **developer.webex.com** — Official API docs, guides, and blog posts
- **Cisco Live LTRCOL-2574** — Hands-on provisioning lab

**Execution pattern:** wxcli CLI commands are the primary execution method; reference docs provide Raw HTTP sections for fallback. All Raw HTTP sections were added 2026-03-18.

Maintainers: update reference docs when you discover new gotchas or API changes.

## Reference Doc Sync Protocol

This repo contains authoritative reference docs at `docs/reference/` that document every Webex Calling API surface. These docs serve both the CLI and the playbook agent.

### When you learn something new

Whenever you discover a technical detail through implementation — a gotcha, a correction, an undocumented behavior, a scope requirement, a parameter that works differently than expected — do this:

1. **Check the relevant reference doc first.** Use the See Also links at the bottom of each doc to find related docs. Key docs by area:
   - Provisioning: `docs/reference/provisioning.md`
   - Call features (AA/CQ/HG): `docs/reference/call-features-major.md`, `call-features-additional.md`
   - Person settings: `docs/reference/person-call-settings-*.md` (4 files: handling, media, permissions, behavior) + `self-service-call-settings.md`
   - Location settings: `docs/reference/location-calling-core.md`, `location-calling-media.md`, `location-recording-advanced.md`
   - Devices: `docs/reference/devices-*.md` (4 files: core, dect, workspaces, platform)
   - Routing: `docs/reference/call-routing.md`
   - Auth: `docs/reference/authentication.md`
   - Scopes / raw HTTP: `docs/reference/authentication.md`

2. **If the reference doc is wrong or incomplete**, update it:
   - Fix incorrect method signatures, scopes, or data models
   - Add the gotcha to the doc's Gotchas section (create one if missing)

3. **If the reference doc is right**, move on — no action needed.

4. **If there's no reference doc for what you found**, add it to the closest doc's Gotchas section with a note about which command surfaced it.
