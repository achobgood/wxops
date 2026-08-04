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

178 command groups (173 generated modules, manifest-registered). Calling/admin/device/messaging groups live-tested across 4 batch sweeps (2026-03-19 through 2026-03-21). Contact center and meetings groups regenerated at the 2026-07-01 spec sync and not fully live-tested. CUCM pipeline tested against live test bed (10.201.123.107) with 2 test bed expansions. See git history for detailed test logs.

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
- **Every gate exemption is scoped to the evidence that justifies it, and carries
  that evidence.** This is the single rule that has been violated most often, and
  each violation cost months of a silently-passing gate. An exemption added for a
  real, narrow reason must not be expressible in a form broader than that reason:
  the gate then reports zero and everyone believes it.

  | Exemption | Was scoped | Hid | Now |
  |---|---|---|---|
  | check 9 item schema | union across every spec declaring the path | `locations list`, 3 blank columns | `spec_authority`, per operation, with `basis: live\|unverified` |
  | check 2 allowlist | bare group name = every file | 6 real dead refs in `person-call-settings-behavior.md` | `ref <file> <group>` — file-scoped |
  | `verb_semantics_ack` | per spec **+** exact method/path | nothing — **this is the pattern to copy** | unchanged |

  Before adding one, answer three questions in the entry itself: *which* artifact
  is exempt (never "this group"), *why* it is legitimately exempt, and *what would
  make it stale*. `verb_semantics_ack` is the model — the generator re-checks each
  ack against its own classification, so the YAML cannot rot. An exemption with no
  staleness check is a permanent blind spot, not an exemption.

  Corollary: a check that reports **0** deserves more suspicion than one reporting
  many. Before trusting a zero, mutate the exemption and confirm the check can
  still fail — check 9 and check 2 both reported a confident 0 while broken.

## When Cisco ships new endpoints — what is automatic, what is gated, what is on you

Read this before running `spec_sync.py` against a refreshed spec. It exists because the
2026-07-28 fix wave closed 15 audit defects, and the honest question afterwards was:
*which of these come straight back with the next batch of endpoints?*

**AUTOMATIC — a new endpoint gets these for free. Do not re-solve them.**

| | Where it happens |
|---|---|
| Argument help: value shape + which command produces the value | `command_renderer._argument_help` / `build_producer_index` |
| A runnable example per command | `command_renderer` |
| Full group-screen summary (bypasses Click's 45-char cap) | `_command_decorator` emits `short_help` |
| Table columns derived from the 200 response schema | `_derive_default_columns` |
| Confirm prompt names the resource, after its value resolves | `_command_decorator` + emit ordering |
| Old name kept as a hidden alias whenever a rename lands | `original_command_name` |
| List/dict table cells render without dropping data | `output._render_cell` |

**GATED — if it recurs, a check fails and tells you.** Checks 1-16 in `drift_check.py`'s header,
plus `verb_semantics_ack` (hard-fails a destructive op whose name gives no hint) and the
stale-`command_name_overrides` guard. A spec conflict on a shared path fails check 9 until
someone pins `spec_authority` with evidence.

**GATED SINCE 2026-07-28 — d3 is promoted.** Both classes below used to be listed here as
"WILL come back silently". `tools/verb_naming.py` now classifies them and `drift_check.py`
check 12 gates them, so a regen cannot land new naming debt unnoticed.

1. **Numeric-suffix names.** `_dedup_command_names` resolves a name collision by appending
   `-1`, `-2`, which carries no meaning. **42 visible are shipping right now** (48 decorators
   on disk − 2 in gitignored dev-only `fs_*` modules − 4 hidden rename aliases; count
   git-tracked, not local). Every new colliding operation adds one. `aws connect` has 370
   operations and zero numeric suffixes; Phase 1 called this the clearest loss to the rival.
2. **A bare verb whose target is not the group's headline resource.** `hds list` returned
   clusters while `show-database` returned the database; `location-settings list` returns
   dial patterns; `cc-journey delete` deletes a person. The generator names from the HTTP
   method, so whichever operation parses first claims `list`/`delete` regardless of what it
   points at. This is the single most expensive defect shape in the tool — the obvious name
   runs, exits 0, and answers a different question. **156 findings: 129 HIGH, 27 MEDIUM,
   0 CRITICAL.**

**The threshold, and why it is not CRITICAL-only.** CRITICAL+HIGH fails the build; MEDIUM is
reported. Gating on CRITICAL alone was the tempting choice and would have been worthless: the
only CRITICAL findings anywhere are the four `update-access-codes` commands kept by decision
on 2026-07-14, so the gate could never fire, and it would have caught **0 of the 28 renames**
Phase 2 landed. A check that always reports zero is the exact failure this file's Generator
Rules section warns about. Numeric suffixes fail at any severity — a `-N` name carries no
meaning, so it is always a decision the generator could not make.

**The ack list is a debt snapshot, not an argument.** 171 entries (42 + 129) record what
shipped on 2026-07-28 so existing debt does not block every commit while new debt does. It
copies `verb_semantics_ack`'s contract exactly: keyed per OPERATION (`<kind> <METHOD> <path>`),
carrying its evidence as a comment, and re-validated on every run — an ack whose command was
renamed, whose severity changed, or whose operation disappeared is reported STALE and fails.
Deleting a fixed command's ack is part of fixing it. Proven by mutation in all three
directions (drop an ack → fail; rename the acked command → fail; ack a non-existent op →
fail).

The renaming machinery this feeds is already built and proven by 28 renames:
`command_name_overrides` plus an automatic hidden alias. To fix instead of acking, rename
there and delete the ack.

**Reviewing a regen diff — what to actually look at:**
- **Renames, not just additions.** Known issue #18: a new operation can win a name race
  within a tag and silently demote an operator-facing command. Diff `@app.command` names.
- **Any new `-N` suffix.** That is a naming decision the generator could not make; make it.
- **Any new bare `list`/`show`/`delete`/`create`.** Check what its URL actually terminates
  in. If it is not the group's headline resource, name it for what it does.
- **`git diff` on `_registry.py`** for groups appearing or disappearing.

## Decision Record — CLI Surface

Why the generated CLI looks the way it does. Recorded because each of these was
re-derived from scratch at least once after the reasoning was lost to a commit
message. If you are about to change one, read the row first.

### `--output` was missing from three of six command types (fixed 2026-07-25)

**What was found (state before this branch):** the renderer emitted `--output`
from only three of six render paths — `_render_list_command` (list, default
`table`), `_render_show_command` (show, default `json`), and
`_render_create_command` (create, default `id`). `_render_update_command`,
`_render_delete_command`, and `_render_action_command` emitted **no `--output`
at all**. Verified on `locations.py`'s `update`: it declared only `--json-body`
and `--debug`, so `wxcli locations update … -o json` failed with `No such
option`. The same gap covered some hand-written commands — `wxcli whoami -o
json` failed, as did `switch-org`, `clear-org`, and `cleanup run`.

**But `--output` was not simply absent everywhere else — on four hand-written
commands it already meant a filesystem path**, and adding a format flag there
would have collided two meanings onto one name:

| Command | `--output` means |
|---|---|
| `analyze` (`org_health_cli.py:28`) | required `Path` — *"Directory to write results.json into"* |
| `report`, `user_diff`, `user_notice` (`cucm.py:2857, 2991, 3054`) | output **filename** for assessment-report / user-diff / user-notice |
| `preflight`, `decisions`, `inventory`, `next_batch`, `execution_status`, `rollback_ops`, `dry_run` (`cucm.py:1463, 1585, 2224, 2380, 2513, 2603, 2661`) | already a proper `table\|json` format flag — nothing to do |

Those four path-valued commands kept their path meaning and received `--fields`
only — this is still true today; check what an `--output` *means* before
assuming a command lacks one. (Corrected 2026-07-25 after external review:
`decisions`'s `--output` is a *format* flag — `help="Output format: table
(default) or json"` — not a report-writer filename; the writers are three,
not four.)

**There was no design reason. It grew.** `--output` originally existed only on
the read commands (list, show). On **2026-03-24, `a795b58`** — *"fix: add -o
json to create commands"* — create was added, because create returns an id
you script against. The word *fix* is the tell: a gap noticed in use and
patched, not a design being implemented. Nobody revisited update/delete/action
— until this branch.

**The fix, 2026-07-25:** all six render paths now call one shared helper,
`_render_output_options` (`command_renderer.py:84`), from `_render_list_command`
(`:414`), `_render_show_command` (`:524`), `_render_create_command` (`:655`),
`_render_update_command` (`:762`), `_render_delete_command` (`:881`), and
`_render_action_command` (`:989`). Every generated command now carries both
`--output` and `--fields`; the same four hand-written gaps (`whoami`,
`switch-org`, `clear-org`, `cleanup run`) were closed the same way, so
`locations update … -o json` and `whoami -o json` both work now. Measured, not
asserted: commit `60b27b7` regenerated all 9 specs and reported **"Commands
with no --output: was 595, now 0,"** with the drift gate at `result: PASS` /
`gate exit: 0`.

**Lesson:** an option present on most commands but not all is worse for an
agent than one that does not exist — it teaches a rule that breaks
unpredictably, costing a failed call plus a `--help` round trip each time.
That is why this was fixed outright rather than left as a documented quirk.

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

### Upstream refresh, 2026-07-26 — +16 ops, −3 ops, and the first live `--fields` collision

Landed from `stash@{0}` rather than a `tools/update-specs.py` pull: the refresh
had been stashed by the CLI-ergonomics plan because that plan's regen was
flags-only and gated on **zero** command-name changes, while this refresh
legitimately renames one. It was therefore reviewed as a name diff instead.
7 spec files changed (+15,534 / −12,907); only 3 changed semantically.

**Baseline moved — 176 command sets / 1872 commands → 178 / 1886.** Do not treat
the old numbers as current; `drift_check` check 3 enforces the published figure
in `CLAUDE.md` and `README.md`.

**The reviewed name diff — 15 additions, 1 removal, all accounted for:**

| Change | Cause |
|---|---|
| `archive-users show` → `list` | Upstream replaced item `GET /identity/organizations/{orgId}/v1/ArchivedUser/{useruuid}` with collection `GET .../ArchivedUser`. `list` requires `--filter` (SCIM `eq` on `username` or `id`) and takes no positional org ID |
| `announcements` +4 | file-URI and upload-URL operations |
| `data-policies` +5 *(new group)* | new tag `Call Settings Configurable Storage Region` |
| `cc-campaign-group` +1 *(new group)* | new tag `Campaign Group` |
| `cc-contact-list` +2, `cc-flow` +2 | join existing groups |
| `virtual-extensions` — **no name change** | upstream merged the `PUT` onto the correct item path and dropped a stray trailing-slash duplicate; only the URL changed |

The other 2 removals were inert: `POST /v1/{orgId}/functions/{id}:test` is under
the `Functions` tag, already in `skip_tags`; the third was the trailing-slash
path above, not a real removal.

**Group names were chosen BEFORE regenerating** so it only ran once. Neither new
tag had a `cli_name_overrides` entry, so the generator would have auto-derived
`campaign-group` (breaking the `cc-` prefix all 26 other Contact Center groups
use) and `call-settings-configurable-storage-region` (by a wide margin the
longest name in the CLI). Both entries go in `_global`, not a per-spec block —
verified neither tag appears in more than one spec, and the per-spec blocks
exist only to resolve cross-spec tag collisions. `data-policies` is named for
its resource: all 5 ops are `/telephony/config/dataPolicies*`.

**Storage region moved off the call recording vendor endpoints.** Upstream
deleted `storageRegion` and `orgStorageRegionEnabled` from the bodies of both
`PUT /telephony/config/callRecording/vendor` and
`PUT /telephony/config/locations/{locationId}/callRecording/vendor` — verified
by diffing the resolved request-body schemas old vs new, not inferred from the
generated diff. That is what the new `data-policies` group replaces it with.
This surfaced as `drift_check` check 6 ("docs cite flags that don't exist"),
which per known issue #22 can equally mean the CLI regressed — it did not here,
and the spec diff is the evidence. `docs/reference/location-recording-advanced.md` § 1.7 records the move.

### `param_name_overrides` — renaming a spec param's flag without changing the wire (added 2026-07-26)

The `--fields` section above predicted this: *"If a future spec revision
introduces a `fields` parameter, the fix is a guard or an override entry — not
renaming `--fields`."* The 2026-07-26 refresh made it real, and the prediction
held. `ReservedParamCollisionError` fired at generation time and stopped the
regen dead:

```
PATCH v3/campaign-management/campaigns/{campaignId}/contacts/{contactId}
(command 'update-contacts') declares query parameter 'fields' ...
```

**Why neither existing escape hatch worked.** The error message told the reader
to "add a rename for this parameter (field_overrides.yaml / cli_name_overrides)"
— but no such mechanism existed; `cli_name_overrides` maps *tags to group
names*. `omit_query_params` would have worked mechanically but is global and
silent, converting a deliberate loud guard into a silent drop everywhere.

**Why dropping Cisco's parameter was the wrong instinct.** The two are not the
same operation: the spec's `fields` is *server-side* selection of which contact
fields the API returns, while `--fields` is a *client-side* JMESPath post-filter
over whatever already arrived. Dropping the spec one loses a capability
`--fields` cannot supply — and worse, if the endpoint returns a reduced default
set, no client-side filter can recover the missing fields (the `--calling-data`
trap in the root `CLAUDE.md`). They clash only on **spelling**, so the fix is to
spell them differently.

**The mechanism.** `_apply_param_name_overrides` (`command_renderer.py`) runs
once in `render_command_file` before any renderer, so a rename is visible to
every render path *and* to `_check_reserved_collisions`. It rewrites only
`EndpointField.python_name`, which is what the flag string is built from;
request assembly keys the params dict off `qp.name`, so the wire is unchanged.
Shipped entry:

```yaml
"Contact List Management":
  param_name_overrides:
    update-contacts:
      fields: contact-fields
```

Result: `--contact-fields` and `--fields` coexist on one command, and the
request still sends `fields=`.

**It cannot rot** — the same contract `verb_semantics_ack` has. Naming a command
the tag no longer renders, targeting a parameter upstream dropped, or renaming
onto another reserved name each raise `ParamNameOverrideError` at generation
time. Proven by the real before/after (the regen failed, then succeeded
unchanged apart from the entry) and by 6 tests in the tracked
`tests/test_field_overrides.py`, including a control asserting the unrenamed
case still fails loudly, so the others cannot pass for the wrong reason.

### The drift gate skips *gitignored* modules, not merely untracked ones (fixed 2026-07-26)

`drift_check` excluded any command module absent from the git index
(`git ls-files`). The intent was right — `fs_*.py` are gitignored dev-only
modules that exist only on a developer's machine, and counting them would make
the published "N command groups" claim (which check 3 enforces) unreproducible
on CI or a fresh clone. But index membership is the wrong proxy for "gitignored
dev-only": it also swallows a **newly generated module that is legitimately
required and simply has not been `git add`ed yet**.

**Found live during the 2026-07-26 refresh.** With `data_policies.py` and
`cc_campaign_group.py` generated but unstaged, the gate reported
`[1] spec->CLI missing: 6` — naming six endpoints as having no CLI command when
all six existed and were correct — and froze the count at 176 instead of 178.
`git add` alone flipped it to `missing: 0` and 178, with no regeneration.

That failure is worse than wrong, it is *misleading*: "spec->CLI missing" reads
as "the generator failed", which invites adding those endpoints to `skip_tags`
or the out-of-scope table and cementing the opposite of the truth — the same
trap as known issue #22, where the gate blamed the docs and the docs were right.

**The fix:** `module_state()` classifies stems as
`countable = (tracked | on_disk) - ignored` and `untracked = on_disk - ignored -
tracked`, with `ignored` from one batched `git check-ignore --stdin`. Because
`git check-ignore` consults the index, a tracked path is never reported as
ignored — so no tracked module can be dropped by any future pattern change; the
`fs_*` behaviour is structurally preserved, not merely tested. The third state
gets its own **check 8**, which fails `--enforce`: not because a clone always
breaks (it only breaks when `_registry.py` is committed and the module is not,
since `main.py` imports every manifest entry unguarded), but because the gate's
premise is that its numbers are reproducible from a clone, and in that state they
are not. Now that these modules count, leaving it advisory would also let check
3 drift silently.

Guarded by `tests/test_drift_check_untracked.py`, tracked via a `.gitignore`
negation alongside the other artifact guards.

### Table columns come from the response schema, not from ID/Name (2026-07-27)

**The defect.** Every generated `list` renders a Rich table from a hardcoded
`columns=[(header, accessor)]` list, and `command_renderer.py` fell back to
`[("ID", "id"), ("Name", "name")]` whenever a tag had no override. Most Webex
list endpoints return neither — they return `phoneNumber`, `clusterId`,
`displayName`, `campaignId`, `trunkType`. **Measured on the tree before this
change: 215 of 513 list commands named at least one field the API cannot
return.**

It is the quietest possible failure. The command exits 0 and prints a table
that *looks* fine but has blank columns; when every column resolves empty,
`output.py`'s `auto_columns` fallback fires and balloons the table to 40+
auto-detected columns (seen on `cdr`). `-o json` was always correct. Only the
table lied — so nobody scripting against JSON ever hit it, and anyone reading a
table drew conclusions from blanks.

**Three root causes, and what was done about each:**

1. **The generic default was usually wrong** — fixed at the source.
   `_derive_default_columns` picks columns from the endpoint's own resolved 200
   item schema (an identifier, a human-readable label, then scalars in schema
   order, capped at 5). The ID/Name pair survives only as the last resort when
   no schema resolves — still 122 commands, all of which declare no item schema
   at all, so nothing better is knowable from the spec.
2. **The old-style override block leaked to siblings.** A tag's single
   `list: {table_columns: [...]}` entry applies to *every* list-shaped command
   in that tag, so `auto-attendant list-available-numbers-*` inherited the
   parent entity's five columns and rendered all five blank. Migrating a tag to
   the per-command `table_columns: {cmd: [...]}` style fixes it. `Transcripts`
   was migrated here; `Video Mesh` and `Session Types` had their blocks deleted
   outright (both were ID/Name on responses with neither, so the derived
   default is strictly better). **21 tags still use the old style** — that is
   latent, not broken: check 9 catches it the moment it produces a wrong column.
3. **Single-level extraction.** `list_key = ep.response_list_key or "items"`
   then one flat `result.get(list_key)`. Video Mesh nests 2-3 deep
   (`{items: [{orgId, from, to, items: [...real...]}]}`), so the table renders
   the *wrapper*. **Deliberately NOT built (Adam, 2026-07-27).** Measured
   precisely, only 14 commands extract an item with no scalar field at all, and
   they are almost entirely Video Mesh, which is not used here. Nested
   extraction would be built for effectively one other command
   (`call-routing list-usage-route-list`). The video-mesh skill instead tells
   operators to use `-o json`, which was always correct. Careful with the
   measurement if you revisit: a naive "extracted item contains an array" test
   over-counts badly — most of those hits are real records that merely carry a
   sub-array (`user_settings list-privacy` returns `monitoringAgents[]` with
   `displayName`/`email`/`id`/`type` *plus* a `numbers` array) and need a
   column fix, not an extraction fix.

**`emails[0]` never worked.** `wxcli people list` — the most-used list command
in the CLI — shipped an override of `[("Email", "emails[0]")]`.
`output.py:_resolve_accessor` splits on `.` and has no bracket syntax, so that
was a dict lookup for a key of that literal name and every Email cell rendered
blank. The accessor is `emails`: a list-valued accessor already yields its
first element (`output.py:144`). Verified before and after, not inferred.

**The monitoring union was settled live, not by reading.** Three commands
(`person-call-settings list`, `my-call-settings list-monitoring`,
`workspace-settings list-monitoring`) were left unfixed in the first pass
because the spec contradicted itself: `MonitoredElementItem` declares three
*object* properties (`member`/`callparkextension`/`speedDial`), while the
spec's own `example` shows flat records with `id`/`displayName` at the top
level. Guessing either way risked re-creating the exact bug being fixed. A live
configure→read→revert on a real monitored user settled it **2026-07-27: the
schema is right and the example is wrong** — every entry is wrapped
(`{"member": {"displayName": "Dev Patel", ...}}`). Each row populates exactly
one of the three keys, so the override carries one column per kind and lets the
others resolve empty on that row. Before the fix these rendered a single empty
`Value` column (every accessor missed, so `auto_columns` fired and found no
scalar to show). Two further facts from the same run, now in
`docs/reference/person-call-settings-behavior.md`: the API **omits**
`monitoredElements` entirely when nothing is monitored rather than returning
`[]`, and `availableEntriesCount` decrements while a target is monitored.

**A tag override must be keyed on the MERGED tag name.** The first attempt
keyed the `my-call-settings` entry on the spec tag `Call Settings For Me`;
`tag_merges` folds that tag plus three UserHub phase tags into `My Call
Settings`, and overrides resolve by the merged name. The entry parsed, the
YAML-validity tests passed, and the columns never applied — silently inert.
Caught only by diffing the regenerated file for the columns that should have
appeared. Check the `tag_merges` block before adding an override for any
group whose commands come from more than one spec tag.

**Gate check 9 makes it permanent.** `check_table_columns` re-runs the audit
over the *generated* files on every gate run: 215 findings at `HEAD`, 0 after.
Three exclusions, each of which was a real false positive first:
- **dotted accessors** (`owner.type`) — legitimately supported by
  `_resolve_accessor`; 3 of the first 67 triaged findings were exactly this;
- **cross-spec operations** — 151 operations are declared in more than one
  tracked spec (`/telephony/config/jobs/devices/callDeviceSettings/{}/errors`
  is in both `webex-cloud-calling.json` and `webex-device.json`, with a
  different `ItemObject` in each) and the generator rendered from exactly one.
  The check unions all declaring specs, so it under-reports rather than failing
  a correct command. A last-wins lookup produced 3 false positives here before
  this was fixed;
- **wrapper-shaped responses** — the root cause 3 class above. Counted and
  printed separately, never failed, so the decision stays visible.

Guarded by `tests/test_drift_check_columns.py` (tracked via a `.gitignore`
negation). Its harness borrows a registered module name — an earlier draft
borrowed `__init__`, which no group registers, and 6 of its 8 cases passed
without ever reaching the check. Proven by mutation: reverting the union to
last-wins fails the union case *and* the live-tree case.

### Two specs describe one endpoint differently — `spec_authority` (2026-07-27)

Continues the table-columns entry above. That change made check 9 derive columns
from the response schema; this one makes check 9 able to *see* when it is reading
the wrong schema.

**The defect.** `spec_item_fields()` keyed on `(METHOD, normalized_path)` and
**unioned** field names across every spec declaring that path. 60 operations
declare a list-item schema in more than one tracked spec. For 7 of them the specs
**disagree**, and the union meant a column only one spec declared always looked
valid — regardless of which spec the command was actually rendered from.

`GET /locations` is the worked example, and it is the most-run command in the
tool because it produces the IDs everything else needs:

| | `displayName` | `locationId` | `countryCode` | `name` | `address` |
|---|---|---|---|---|---|
| `webex-device.json` claims | ✅ | ✅ | ✅ | ❌ | ✅ |
| `webex-cloud-calling.json` claims | ❌ | ❌ | ❌ | ✅ | ❌ |
| **live response** | ❌ | ❌ | ❌ | ✅ | ✅ (object) |

The device spec is wrong **by invention**; the calling spec is right but wrong
**by omission**. `spec_sync.PREFERRED_ORDER` runs cloud-calling *then* device, so
the device spec wins the file — `locations.py` shipped its three invented columns
blank, and the union told check 9 they were fine.

**The fix.** Provenance is kept, and collapsing is declared, not implicit:
- `spec_authority` in `field_overrides.yaml`, per operation. `spec: <file>` picks
  one; `spec: union` keeps the old permissive behavior *where nothing has been
  verified* — deliberately weaker, and saying so is the point.
- `basis: live | unverified` records why. 1 of the 7 is `live`; the other 6 are
  `unverified` and say so rather than pretending.
- **A conflicting operation with no entry hard-fails.** That is the ratchet: a
  spec refresh introducing a new disagreement cannot land silently.

**`live_fields` — a spec can be wrong by omission too.** The calling spec declares
only `id`/`name`; the live response also carries `orgId`, `address`, `timeZone`,
`preferredLanguage`. Those could **not** go in `specs/overlays/` — overlays are
additive at the PATH level and must never shadow a path upstream already
publishes (`spec_overlay.py` rule 1, enforced by check 5). So they are declared
on the `spec_authority` entry, typed, with the capture date.

**Proven by mutation, not by reading:** removing the pin fails the gate; pinning
to a spec that lacks the operation fails; pinning to `webex-device.json`
reproduces the original 0-finding false negative **exactly**. If you change this,
re-run those three — a passing check 9 is exactly what the bug looked like.

### Renaming the 30 CRITICAL commands: 26, not 30 (2026-07-27)

Recorded **before** the work, because this decision has now been taken twice and
the second time nearly reversed the first.

**Scope: 26.** All 30 commands the `d3-verbs` detector rated CRITICAL, **minus the
four `update-access-codes`** (location, person, virtual-line, workspace).

**Why the four are excluded.** 2026-07-14 (Adam) deliberately kept those names —
see known issue #20. A 2026-07-27 audit rated them CRITICAL again and proposed
renaming. Rather than reverse a deliberate decision on argument alone, the prior
decision was decomposed into its two premises:

1. *"Renaming breaks anyone scripting `update-access-codes`"* — **now obsolete.**
   Every rename in this wave ships a hidden alias, so the old name keeps working.
2. *"The harm was the message, not the spelling"* — **still holds**, and the
   message was fixed in July: `--help` carries `DESTRUCTIVE: this PUT only
   deletes despite the summary above`, and success prints `Deleted.`

One premise expired; the other still supports the decision, so the decision
stands. **A decision is not void because one of its premises expired — re-check
each premise separately.**

**The disagreement was converted into a measurement rather than settled by
argument.** Goal 34 was added to `artifacts/goals-v2.json`, phrased as an admin
asking to *add* an access code, with `create-access-codes` correct and
`update-access-codes` as the trap. If the blind test picks the trap, that is
evidence to revisit July; if it does not, the decision stands on data. Neither
side of the argument knew the answer — that was the actual problem.

**Rejected alternatives, so they are not re-proposed:**
- *30 (rename all)* — reverses a deliberate, already-mitigated decision.
- *10 (only names hiding what they destroy)* — leaves `admin-recordings
  create-purge` reading as a create; 11 of the excluded 16 are cited in zero
  docs, so the sweep cost is near zero. At that price, take them.
- *0 (skip renames)* — leaves the DECT trap live. Not acceptable: `-1` means
  "one" on base stations and "multiple" on handsets, both destructive, and the
  multiple variant's own example body carries `"deleteAll": true`. An agent that
  correctly learns the convention from one resource destroys data on the other.

Mechanism: `tag_overrides -> command_name_overrides`, plus a hidden alias for the
old name. Typer registers one function under two names by stacking
`@app.command("new")` / `@app.command("old", hidden=True)` — verified directly,
not assumed: the new name appears in `--help`, the old name runs and does not.

### A table cell never silently drops data (2026-07-27)

`_resolve_accessor` used to `return current[0]` for any list-valued field, so a
user with three emails rendered as one — no ellipsis, no count, nothing. An agent
reads that table and tells an admin "their email is X", wrongly, with nothing
erroring. It affected every table in the CLI.

Resolution and rendering are now separate concerns. `_resolve_accessor` returns
the raw value; `_render_cell` decides how it looks:
- list → `first (+N more)`; a 3-element list must be visibly distinct from a
  1-element one **by looking at the cell alone**. Empty → `""`.
- dict → `key: value, key: value`, recursing. Previously a raw Python `repr`
  (`locations list` dumped `{'address1': '170 W Tasman Dr', ...}` into a column).
- Both recurse, so a list of dicts and a nested dict stay readable.

`-o json` and `-o text` are untouched and must stay that way — this is a table
presentation rule only, and JSON consumers depend on the full value. The
`auto_columns` fallback (`print_table`, `val is None or val == ""`) is unaffected:
a non-empty list was truthy before and after, and `[] == ""` is False in both.

### Argument help: value shape + which command produces it (2026-07-27)

The largest measured quality gap in the CLI, now closed. An argument used to
render as `LOCATION_ID  locationId  [required]` — the argument's own name echoed
back, in 1,499 of 1,508 cases. The score gap was entirely arguments:
argument-bearing commands averaged 1.36/5, argument-free commands 4.27/5, and all
234 perfect scores had zero arguments.

Now: `LOCATION_ID  Webex LOCATION id, from: wxcli locations list  [required]`.

| | before | after |
|---|---|---|
| carries a value shape | 9 / 1,508 | **88.1%** |
| names a producer command | 8 / 1,187 | **68.7%** |
| runnable example in help | 0 / 1,955 | present |
| median help screen | 180 tok | 203 tok |

Value shape comes from decoding the spec's base64 `example` to
`ciscospark://us/<KIND>/…` — 71 distinct kinds, which catches real traps: on
`locations update-floors` the `locationId` is a **WORKSPACE_LOCATION** id, not a
LOCATION id. The producer is resolved parent-collection-first
(`/locations/{locationId}/…` → the list command on `/locations`), with a
same-resource-shallower-path fallback. A "prefer the bare `list` name" ranking was
measured and REJECTED — it produced false pointers (`team-memberships` →
`memberships list`). Where nothing resolves, the help says nothing: a wrong
pointer is worse than none.

**`build_producer_index` must resolve overrides the way `main()` does.** It loads
the raw YAML, where the `_tag_ovr:*` keys are absent (they are synthesized at
runtime), so a lookup that relies on them alone silently skips everything under
`tag_overrides:` — including all 26 renames. Every producer pointer then cited
PRE-rename names, e.g. 212 arguments pointing at `location-settings list-1`, a
name that is no longer a visible command. Caught only because a rename made it
visible; there is no test that would have failed.

### Startup: lazy mounting, 870ms -> 108ms (2026-07-27)

Measured, interleaved round-robin, 12 samples/scenario, **84 of 84 runs proven to
exit 0 with non-empty stdout**, stdout byte count constant within each scenario:

| | before | after | rival `aws` |
|---|---|---|---|
| `wxcli --version` | 870.4ms | **108.0ms** | 374.4ms |
| `wxcli --help` | 872.7ms | **110.3ms** | — |
| `wxcli locations --help` | 860.2ms | **154.2ms** | — |

wxcli was 2.3x SLOWER than `aws`; it is now 3.5x faster. At 200 calls per agent
session, 174s -> 22s. The 870ms independently corroborates the 0.83s baseline.

`LazyTyper` (`commands/_lazy.py`) mounts groups on demand; `whoami`/`switch_org`
defer the `wxcli.auth` import, and `auth.py` defers `httpx` inside the methods
that make requests, so neither loads for `--version`.

**This blinded the drift gate, and the gate failed LOUD, which is why it was
caught.** `parse_registrations` found the 5 hand-written seams and 3 aliases by
regex-matching `app.add_typer(...)` call sites in main.py. Lazy-loading moved
those calls into `_lazy.py`: command sets read 178 -> 173 and check 2 reported
**274 dead references** while every one of those commands worked perfectly (197
top-level commands, verified by building the click tree directly). The parser now
reads the DECLARATIONS — `HAND_WRITTEN_GROUPS` / `ALIASES` — because a list of
tuples cannot drift from mounting order the way a regex over call syntax can.
Locked in by `tests/test_drift_check_registrations.py`.

### Check 10 — positional arguments, and the two parser bugs it needed (2026-07-27)

Documented examples supply positional arguments the command does not declare.
Checks 2/6/7 cover command names and flags; nothing covered positionals, which is
what makes an example runnable. Positionals are statically declared as
`typer.Argument(...)`, so the check is mechanical.

**Two classes, only one fails the gate.** 85 actionable (`positional_on_zero_arg`
54 + `too_many` 25 + `too_few` 6) are broken runnable examples — copy-paste and
they abort. 77 bare-name citations are prose like "run `wxcli people show`":
incomplete, not wrong, and they fail loudly at runtime. Reporting the combined
162 as one number overstates the work by ~2x; the gate fails on the 85 only.

Two parser bugs surfaced, both of which manufactured phantom positionals:

1. **`code_spans` ended a span at an unterminated quote.** A multi-line
   `--json-body '{ ... }'` block was truncated mid-JSON and the invocation became
   untokenizable — 14 real findings silently dropped. Fixed with
   `join_quotes=True` (opt-in; checks 6/7 keep their tuned behaviour).
2. **`arg_region` kept the file descriptor of a shell redirect.** `2>&1` left a
   bare `2`, which `shlex` reads as its own word and check 10 counted as an extra
   argument. It hit EVERY line ending in a redirect regardless of the real
   arguments — 17 findings in `teardown/SKILL.md` alone, on lines whose
   documented arguments were already correct. Only a LONE digit is stripped, so
   `... SITE2 > out` keeps SITE2.

Bug 2 was found by a subagent that REFUSED its instructions: told to fix 16
findings, it fixed 1, proved the other 15 were a tool bug by calling `arg_region`
directly, and declined to edit correct docs. Had it complied, it would have
corrupted 15 working examples to satisfy a broken check. **When a doc fix requires
contorting the doc — brace-grouping a redirect, reordering prose around an inline
code span — suspect the checker, not the doc.** Two such workarounds were applied
during this session and reverted once the parser was fixed.

### Checks 11a/11b/12, and the blind spot all of them shared (2026-07-28)

**One regex hid three checks' worth of findings.** `TOKEN` (check 2) and `FLAG_CMD`
(checks 6/7/10) both required a literal `wxcli`. Skill quick-reference tables routinely drop
it — `| Get cluster details | `video-mesh show CLUSTER_ID` |` — so every citation in that
form was invisible to every check. Measured: **639** prefixless spans head a registered
group, **14** named a command that does not exist, and check 2 reported **0**. `command_heads`
is now the single reader for checks 2, 10, 11a and 11b, so a citation is either visible to
all of them or to none.

Two guards make the widening safe, and both are load-bearing:
- **Anchored at the span start.** 1232 spans match `<word> <word>`; only 639 head a group.
- **The first token must be a REGISTERED GROUP.** Removing this guard alone takes check 2
  from 0 to **247** findings — ordinary English prose.
- Plus a word boundary after the command token, which is what stops
  `emergency-services show/create/update` (slash-notation prose) reading as a 1-argument
  invocation of `show`. That was the rule's only false positive across the whole doc set.

**Check 11a — a required FLAG is missing.** Check 10 counts positionals only, so an example
can have the right argument count and still abort: `wxcli video-mesh show CLUSTER_ID --output
json` supplies the one positional `show` declares and dies on the missing `--from`/`--to`.
98 commands declare at least one `typer.Option(...)`.

> **Read the RENDERED command, never the spec.** `auto_inject_from_config` supplies orgId
> from saved config, so a parameter the spec marks required is legitimately absent from
> `--help`. Measured: a spec-driven version of this check produces **12 false positives**
> (11 `orgId` + 1 `limitToLocationId`). Also verified: **0 of 158** required options are
> request-body fields — all are query or path parameters — so `--json-body` never substitutes
> for one, and neither does `--generate-json-body`, which Click never reaches until after it
> has enforced them. `tests/test_drift_check_naming.py` pins that 0.

Only FENCED examples fail. An inline single-backtick citation is a reference-table entry
naming a variant, not an invocation — `wxcli xapi list --command` / `--status` sit in a
decision-matrix cell contrasting the two flags, and demanding `--device-id` there would force
a runnable command into a table that is not offering one.

**Check 11b — the doc placeholder names the wrong resource.** Two tiers, deliberately not one
number. Tier 1 (gated) needs the declared kind and the placeholder to both be explicit and
disagree. Tier 2 (advisory, 16 today) is the bare-`UUID` case — `wxcli meetings show
TEMPLATE_ID`, where kind-matching cannot decide and the only signal is the producer command;
that is a heuristic about English and never fails the build.

> **The check found a CLI defect, not a doc defect.** Tier 1's first run reported **240**
> findings. They were overwhelmingly wrong, because **79 of the 1049 kind-carrying arguments
> declare a kind their own parameter name contradicts** — `location_id` help-typed
> "Webex PEOPLE id", `hunt_group_id` typed LOCATION, `call_queue_id` typed HUNT_GROUP. On
> those the doc is right and the help is wrong, so 79 arguments are excluded from tier 1 and
> reported on their own advisory line. Fixing them is generator work in the argument-help
> producer index. With the exclusion plus a small English-synonym set (PERSON/PEOPLE/USER,
> PLACE/PLACES/WORKSPACE), tier 1 goes 240 → 0, and a planted mismatch still fires.

**Validate by mutation, not by a clean run.** Every one of these was proven by making it
fail: check 2 finds 8 with the widening and 0 without, on identical docs; check 10 finds 10
and 0; check 11a fires on 11 when one file is reverted; check 11b tier 1 fires on 2 planted
placeholders. A check reporting 0 deserves more suspicion than one reporting many.

### `--all` is only as good as the spec's paging declaration (2026-07-29)

`--all` ships on **507** generated list commands. Which of three fetch branches a command
gets is decided entirely by what the spec **declares**, in `_pagination_style`
(`openapi_parser.py`) and the `ep.paginates` / `ep.pagination_style` fork in
`_render_list_command`. Measured on the tree, git-tracked modules only:

| Branch | Count | Behaviour |
|---|---|---|
| `paginates` (200 declares a `Link` header) | 53 | default `--limit 0` **already walks**; `--all` only matters once `--limit N` is passed, which otherwise collapses the command to a single fetch |
| `pagination_style` link / page / scim | 211 (110 / 96 / 5) | default is **one fetch**; only `--all` walks |
| neither | 243 | `--all` accepted and **inert**, deliberately — see the renderer comment at the `all_pages` option |

**The residual risk: a spec that under-declares.** The 243 inert commands are inert because
the spec says the endpoint does not page. Nothing verifies that claim. An endpoint that
really pages, described by a spec that declares no paging query parameter and no `Link`
header, renders into the third branch — and `--all` is then a silent no-op on a command
that truncates. "Flag exists ≠ flag works," which is this project's own recurring lesson.

**Partially mitigated at runtime, and that is worth knowing before building anything.**
`rest_get` calls `_warn_if_more_pages` on **every** GET including the inert branch, and
since `1f584d1` that reads both `Link: rel="next"` *and* a declared total in the body
(`totalResources` / `totalRecords` / `totalResults` / `total`, plus the same keys under
`meta`). So an under-declared endpoint that returns either signal still says so on stderr.
What it cannot do is offer a working remedy.

**Two live instances, found by a static scan of the 9 tracked specs** — operations whose
200 schema declares a total while `_pagination_style` returns `none`:

| Command | Response declares | What the CLI actually sends |
|---|---|---|
| `archive-users list` | `totalResults` (the SCIM spelling) | `--limit`→`max`, `--offset`→`start`, `--all` inert. SCIM pages on `startIndex`/`count`, so **all three controls are inert** and the truncation note names two remedies that cannot work on this command |
| `org-contacts list` | `total` | `--limit`→`limit`, `--offset`→`start`, `--all` inert. Whether `start` is the offset name this endpoint reads is **unverified** |

Static evidence only — no live call was made against either. Confirming them needs a
collection larger than one page on each endpoint.

**If you build a detector, the false-positive class is already known.** The same scan
returns 5 more hits, all of them `.../availableMembers/count` operations (3 distinct paths,
2 of them declared in both `webex-cloud-calling.json` and `webex-device.json`). Their
`totalCount` is the answer the endpoint exists to give, not a paging total. Exclude
`/count`-terminating paths or the check reports 7 and means 2.

**DO THIS ON THE NEXT REGEN — `--limit`'s help string is wrong on 211 commands.**
Every list command ships one generic pair, emitted before the renderer picks a branch:

```
--all    Fetch every page, not just the first. Overrides --limit.
--limit  Max results (0=all for paginated endpoints, API default for non-paginated)
```

`0=all for paginated endpoints` is TRUE on the 53 `paginates` commands and FALSE on the
211 that page but were not declared to — there `limit=0` sends no paging parameter and
returns exactly ONE page. So the help makes its strongest promise precisely where it does
not hold, on endpoints that really do paginate. `--all`'s string is not wrong, but it never
says the default is a single fetch, nor that it is a no-op on 243 commands.

`ep.paginates` / `ep.pagination_style` are already in scope where those params are appended
(above the branch fork), so the fix is branch-aware help text, not a new lookup. Deliberately
NOT applied on 2026-07-29: it is inert until a regen, and a renderer that disagrees with the
507 files on disk is a fresh inconsistency rather than a fix. `tests/fixtures/expected_output.py`
must be refreshed in the same commit (see `tests/test_generator_regression.py`'s header).

Until then the truthful version lives in `CLAUDE.md`'s Common Flags section, which is the
surface an agent actually loads. This is worth more than documentation because every skill
has a mandatory `--help` gate — `--help` is the one place every agent looks, and today it
undersells the trap.

### Six override blocks that had never applied, and check 15 (2026-07-29)

Continues the table-columns entry above. That change made columns derive from the
response schema; this one is about override configuration that **cannot reach the
renderer at all**.

**The mechanism.** A tag can be configured in two places: a top-level block keyed on
the tag name, and an entry under `tag_overrides:`. `generate_commands.main()` used to
promote the top-level block **only if** `tag_overrides` did not already name that tag,
so when both existed the whole top-level block was discarded. It parsed, every test
passed, and it did nothing. Measured 2026-07-29: **6 blocks**, `table_columns` on 4
tags plus `add_query_params` and an old-style `list:` block on `Features:  Call Queue`
and another on `Recordings`.

**Merging alone would have been a regression, and was reverted once before this.** It
regenerates with zero command-name changes and then check 9 goes **0 → 15**: `Features:
Call Queue`'s block was the old-style folder-level `list:` form, which applies its four
columns to *every* list-shaped command in the tag — 17 there, and only the bare `list`
declares `extension`/`enabled`. That is root cause #2 above, and the shadowing had been
accidentally shielding the tree from it. So the blocks were fixed first and the merge
landed after.

**What each block turned out to be worth.** Re-verified against each endpoint's real
200-item schema, because a hand-written list is not automatically better than
`_derive_default_columns`:

| Block | Outcome |
|---|---|
| `Features:  Call Queue` `list:` | Migrated to per-command `table_columns: {list:}`. Same four columns as `Features:  Hunt Group` list, so the sibling entities read alike. |
| `Recordings` `list:` | Migrated to per-command form on all three list commands (same recordings resource, all four columns declared on each). Derived was reaching for meetingId / scheduledMeetingId / meetingSeriesId — three near-identical base64 IDs. |
| `DECT Devices Settings` | 5 of 6 entries **deleted** — four were byte-identical to the derived default and `list` was a strict subset. Kept `list-handsets`: derived reaches `accessCode`, the handset pairing code, which a default table should not print. |
| `Location Call Settings` | 6 available-numbers entries **deleted** (2 columns where derived declares the same 2 plus isMainNumber / tollFreeNumber / telephonyType — the shape the applied Hunt Group / Auto Attendant / Paging Group overrides already use). Kept both job lists, whose whole point is `latestExecutionStatus`; `list-delete-calling-location` is what the corrected teardown flow polls. |
| `Location Call Settings: Call Handling` | **Deleted entirely.** `list-access-codes` named no command in the group (the read is `show-access-codes`, not list-shaped), and the other two were strict subsets of derived. |
| `Workspace Call Settings` | `list: [directNumber, extension]` **deleted** — the bare `list` there is GET `/workspaces/{id}/features/callerId`, which extracts `types`; those fields belong to `list-numbers`, where derived already declares both. Kept `list-monitoring`, and this is the one that mattered: the live-verified monitoredElements union was applied to `person-call-settings list` and `my-call-settings list-monitoring` on 2026-07-27 and recorded as covering all three commands — the third never got it, because this block was shadowed, so `workspace-settings list-monitoring` shipped the [ID, Name] fallback, blank on every row and excused by check 9 as wrapper-shaped. |

**`add_query_params` was actively harmful, proven by regen diff.** It injected a
`hasCxEssentials` **query** param onto `delete-supervisors-config`, whose spec declares
`hasCxEssentials` in the **body**. Merged, the injected query param claims the CLI name,
`_used_param_names` then drops the body field as a flag (issue #19), and
`--has-cx-essentials` silently stops reaching the body the API reads — same flag in
`--help`, different wire. Its other half targeted `delete-supervisors-config-1`, where
the spec declares the parameter nowhere and the command is already unreliable (known
issue #8: 204 but the supervisor persists); confirming a query param there needs a
destructive live call. Block deleted.

**The defect is not the six blocks, it is silently inert configuration** — so the guard
is general, and it found eight more instances the moment it existed:

- 3 per-command keys naming commands that do not exist: `table_columns.list-calls` in
  `Call Controls` (the group renders `list-calls-members` / `list-calls-me` — re-pointed
  at both, sharing the bare `list`'s columns since the item schema is identical),
  `list-supported-devices-config` in `Device Call Settings` (deleted; the same rule
  already applies in `device-dynamic-settings`), `list-regions` in `Features: Call
  Recording` (deleted; that endpoint renders as the bare `list`, which already derives
  the same three fields).
- 5 tag keys naming tags nothing declares: a `table_columns` block and a
  `cli_name_overrides` entry both keyed `Features: Customer Experience Essentials`
  after upstream renamed the tag to `Features: Customer Assist` (the group ships as
  `customer-assist` from the derived name, with `cx-essentials` mounted as an alias in
  `_lazy.py` — re-keying would have *renamed* the group and inverted that alias), and
  four `fs-*` blocks keyed on CLI **group** names instead of tags.

**Two guards, each where its oracle is.** The generator hard-fails on a per-command key
that names no rendered command — it already did this for `command_name_overrides`, now
for all nine other command-keyed families — and refuses a family declared in both forms,
since the merge is shallow and would drop the top-level copy. **Check 15** covers what a
single-spec generator run structurally cannot see: a tag key no spec on disk declares.
It reads specs from **disk**, not from git, so a per-spec section for an absent
`webex-flow-store.json` is out of scope rather than inert on a fresh clone, and it
imports the generator's own resolvers rather than reimplementing them.

`inert_tag_ack` declares the one deliberate exception — the `AI Assistant` tag, removed
upstream, whose name mapping is kept so a returning tag rebuilds under the group name
already mounted. Every ack is re-validated: if the tag comes back, the ack fails.

**Mutation-proven in both directions**, which for this check is the whole point: all
four finding kinds fire on a planted defect and return to 0 on revert, and five
mutations of the check body each fail a distinct test in
`tests/test_drift_check_inert.py` (18 cases, tracked via a `.gitignore` negation). That
suite's paired does-not-fire / does-fire cases exist because the check-9 suite once had
6 of 8 cases passing without reaching the check at all.

**Net CLI effect: 10 changed column lines across 6 modules, zero command renames,
check 9 still 0.**

### Three names that answered a different question (2026-07-29)

The last three round-1 audit caveats. All one failure mode: the command runs, exits
0, returns plausible data, and answers something other than what was asked.

**1. `cc-agents list` returned agent ACTIVITIES.** An event log over a required
`--from`/`--to` window of ≤24h, in the group whose name is the one an admin reaches
for. Renamed `list-activities`, hidden alias `list`, so the group now has no bare
`list` to mislead.

Round 1 recorded this as a **capability gap** — *"no command anywhere in the CLI
returns a contact-center agent roster."* **That claim is false**, and it was settled
by a live call because neither `--help` nor the spec could: `cc-users list` IS the
roster (`firstName`, `lastName`, `email`, `ciUserId`, `contactCenterEnabled`,
`siteId`, `teamIds`, `agentProfileId`, `skillProfileId`), and
`cc-users list-with-user-profile` is the same roster with profile permissions
expanded inline. So no `deliberate-gaps.md` entry was filed; the defect was
discoverability, and the fix is the rename plus pointers in
`contact-center-core.md` and the `contact-center` skill. Provenance worth keeping:
no detector found this. It surfaced only because a blind-test model disagreed with
the answer key on goal 17 and was right.

**2. `teams list` and `cc-team list` shipped byte-identical `short_help`.** A Webex
collaboration-space grouping and a Contact Center agent-routing grouping, different
APIs, four identical words. The root `CLAUDE.md` skill table carries two rows for
exactly this collision, which is the admission that the CLI's own output could not
tell them apart.

Fixed at the generator, because `short_help` is the spec's operation summary and
pinning two strings by hand invites the next spec sync to reintroduce it — and it
was never a two-command problem: **17 summaries / 35 command decorators**.
`_summary_qualifier` appends the product (`List Teams. (Messaging)` /
`List Teams. (Contact Center)`), and `SPEC_PRODUCT` derives that from the source
spec FILE rather than guessing from a name prefix.

Two things about the rule are easy to get wrong, both measured:
- **Index on CLI GROUP, not on spec.** 34 of the 51 summaries two specs share are
  ONE operation both declare (`GET /locations` is in cloud-calling and device) that
  renders into ONE group. Per-group they collapse to one entry with one product and
  never qualify. Qualifying them would attach an arbitrary product to a command that
  has only one.
- **Require 2+ PRODUCTS, not 2+ groups.** Same-product collisions
  (`my-call-settings` vs `user-settings`) gain nothing from a product label.
  Dropping this takes 17 → 40. The `len(groups) < 2` line is a redundant early-out,
  not a second condition — a first draft of the docstring claimed otherwise and the
  mutation probe disproved it.

`webex-flow-store.json` maps to `None` on purpose: it is gitignored and dev-only, so
letting it into the index would make generated help differ between a developer's
machine and a fresh clone — drift check 8's premise. A spec on disk with no entry
**raises** rather than being skipped, so a future tracked spec cannot inherit that
exemption silently.

**This is the same root area as findings D07/D08** (the group-help label still reads
`Manage Webex Calling teams` for a messaging group, from the CLI-name-prefix test at
the bottom of `command_renderer.py`). That line was deliberately left alone. When
D07/D08 lands it should READ `SPEC_PRODUCT` instead of the prefix test — not add a
second mapping beside it.

**3. `call-settings-for-me-phase-5` was an internal build-milestone label shipped as
a command path.** 7 real commands behind a name that tells a customer they are
looking at work in progress, and tells an agent reading `wxcli --help` nothing at
all. All 7 ops are `/telephony/config/people/me/*` — the same surface the other four
`Call Settings For Me*` phase tags already fold into `My Call Settings`. Phase 5 was
simply never added to `tag_merge`. **Folded, not renamed: 178 groups → 177.**

**Folding was measured before it was done, and unpinned it was NOT safe.** Merging
into a 123-command tag perturbs name races (known issues #18/#22 — check what a bare
name POINTS AT, not merely that it survived; a name-set diff shows nothing here):

| | unpinned merge | shipped |
|---|---|---|
| `my-call-settings show` | silently moves preferredAnswerEndpoint → personalAssistant | unchanged |
| `my-call-settings update` | same | unchanged |
| `show/update-preferred-answer-endpoint` | renamed to `*-secondary-lines`, no alias | unchanged |

The `command_name_overrides` block is a **SWAP**, the same shape `Features:  Call
Queue` already uses: personalAssistant is named for its resource and the
preferred-answer pair is pinned back to the names it has always had. It works
because `generate_commands.py:278` already suppresses a hidden alias whose name
another command in the tag claims — no generator change was needed, and the
tree-wide invariant (no module registers one name twice) is asserted in
`tests/test_command_naming_residue.py`.

**Rejected: aliasing the old group name.** This is the one decision worth not
re-litigating. `my-call-settings show`/`update`/`list` are the Preferred Answer
Endpoint commands, so `call-settings-for-me-phase-5 show` behind a group alias would
have returned preferredAnswerEndpoint where it used to return personalAssistant —
read-only, exit 0, plausible JSON. That is precisely the failure mode this whole
wave exists to remove, so the old path was left to **fail loudly** instead
(live-verified: exit 2, `Error: No such command 'call-settings-for-me-phase-5'`) and
the 26 skill/doc citations were swept. Renaming the group rather than folding was
also rejected: the 7 ops are three unrelated feature clusters (personal assistant,
voicemail rules/PIN, hoteling guest) with no honest single resource name, so any new
group name would have been as arbitrary as the old one.

**The sweep found a doc defect worse than the naming one.** The
`manage-call-settings` skill documented `show`/`update` as *"own voicemail
settings"* in six places, with a voicemail request body
(`{"enabled", "sendUnansweredCalls"}`) — but that operation is personalAssistant,
whose body is `{enabled, presence, untilDateTime, transferEnabled, transferNumber,
alerting, alertMeFirstNumberOfRings}`. The self-service voicemail commands are
`show-voicemail-settings`/`update-voicemail-settings`, which the skill never cited.
It also documented the PIN field as `pin`; the spec says `passcode`. A doc that
teaches the wrong meaning for the right-looking command is the same defect class as
the name, one layer up — when sweeping citations, re-check what each one *claims the
command does*, not just that the path still resolves.

**Manifest pruning is manual, by design.** `update_manifest` upserts, so the vanished
tag left `call_settings_for_me_phase_5.py` on disk and in `_registry.py` after the
regen; check 12 then reported 3 unacked findings whose acks had just been deleted.
Deleting the module and its manifest line is part of removing a group — see the
docstring at `generate_commands.py:181`.

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

    **Revision, 2026-07-25 (finding 9):** the ack-gated success message described above (`_success_message`) is retained **only for `table`/`id` output** on update and delete. `--output` defaults to `json` on both, and Webex PUT/DELETE mostly return 204 with no body — so the no-body branch was the *common* case, and it always printed this prose line even when `-o json` was requested, which is not valid JSON: `wxcli people delete <id> --force -o json | jq` failed to parse on ~536 commands. `json`/`text` output, and any request that passes `--fields`, now get a small structured result instead — `{"status": "<verb>", "id": "<id>"}` when the endpoint has one, e.g. `{"status": "deleted", "id": "abc123"}` — routed through `emit()` so `--fields` still applies to it. The status word is derived from the exact same `_success_message` semantics as the retained prose line, so a delete-shaped PUT reports `"status": "deleted"`, not `"updated"`. This is a deliberate, documented revision of the table above, not a silent one — the prose wording itself is unchanged and still exactly what table/id output prints.

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

    Live-proven end-to-end on supervisors: scoped delete removed exactly the named target and left the other in place. **Still unproven: the other 4 scoping deletes were fixed by the same code path but not live-tested.**

    `numbers delete` — the one that most deserves it — was attempted on **2026-07-27** against org `ccbcamp0199.wbx.ai` and **could not be tested there**; it remains unproven. The test needs a throwaway number to add and then scope-delete, and that org has no API-managed number lifecycle: its only PSTN location (`Site1`, which holds all 30 inventory records) reports `pstnConnectionType: CISCO_PSTN`, the second location has no PSTN configured at all, and `call-routing list-trunks` returns `[]` — so there is no non-integrated / Local Gateway path, and creating one would mean building routing infrastructure rather than testing numbers. On CCP-integrated orgs number DELETE is refused outright with `ERR.V.TRM.TMN60004` ("DELETE number is supported only for non-integrated CCP"), because number lifecycle is owned by the PSTN portal, not the API (see `docs/reference/provisioning.md`). A run there would therefore have failed on org entitlement and proven nothing either way about whether the body scopes the delete — a false negative, not evidence. **Proving `numbers delete` requires an org with a non-integrated / Local Gateway PSTN location.** No numbers were added or removed during the attempt: inventory was byte-identical before and after.

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
