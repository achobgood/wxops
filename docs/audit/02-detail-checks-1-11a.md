# Drift gate audit — checks in `tools/drift_check.py` lines 1–1700

Scope read: lines 1–1700 in full (docstring/header 1–213, then continuous read
213→1700). One exception, noted where used: I read lines 3625–3668 and grepped
the whole file for `failed`/`flag_surface`/`regenerat` to establish (a) which
checks feed the `failed` boolean that gates `--enforce`, and (b) whether any
check anywhere compares regenerated vs. committed output. Everything else below
is sourced from 1–1700 and from live `python3.14` execution of the actual
functions against this repo's current tree (never importing `wxcli`, never
running a mutating command).

All findings below marked `[verified]` were confirmed either by reading the
code or by executing the exact function from `tools/drift_check.py` in a
subprocess against the real tree. `[inferred]` marks anything I did not
execute.

---

## `build_flag_surface` (`tools/drift_check.py:554`)

**Method: static source parsing, not the runtime command tree.** `[verified]`
`build_flag_surface` (`tools/drift_check.py:554-565`) calls `parse_module_flags`
(`tools/drift_check.py:518-551`) once per registered group's module. That
function does `ast.parse(path.read_text())` on the `.py` file on disk and walks
`FunctionDef` nodes — it never imports the module, never builds a Click/Typer
`app`, never calls `--help`. It records, per command, only the **set of flag
strings** declared via a `typer.Option(...)` default (plus the literal
`"--help"` typer always adds, `tools/drift_check.py:537`).

**What this method structurally cannot see:**
- **Default values.** Only presence of a flag name is recorded
  (`flags.update(p for p in arg.value.split("/") if p.startswith("-"))`,
  `tools/drift_check.py:549`); the default value passed as `default.args[0]` is
  never read into the surface.
- **Types.** No annotation is captured — the surface is `dict[str, set[str]]`
  (`tools/drift_check.py:554`), flag name only, not `str`/`int`/`bool`/`Path`.
- **Mutual exclusion.** Nothing about which flags can't be combined is
  representable — that logic (if any) lives in a function body, and this
  parser never looks past the decorator-default level.
- **Help text.** The `help=` kwarg is never read.
- **Hidden aliases created by decorator-stacking — verified live, and this is
  a real gap, not a hypothetical one.** See the dedicated section below; it
  affects `build_flag_surface` and three of its siblings.

**Persistence: recomputed once per run, never persisted, never compared
against a second independently-built surface.** `[verified]` Grepping the
whole file for `flag_surface` (`tools/drift_check.py:554,1044,1064,1090,1107,
1449,3566-3568`) shows exactly one call site, `flag_surface =
build_flag_surface()` at `tools/drift_check.py:3566`, feeding directly into
`check_flags` and `check_prose_flags` in the same `main()` invocation. There is
no on-disk snapshot for it (unlike check 19's `tools/spec_semantics.json`). So
there is only one "side" in play: the flag surface (derived fresh from
`src/wxcli/commands/*.py` on disk) is compared against documentation text also
read fresh from disk in the same run — not against a second, independently
computed CLI surface.

---

## ⚠ Cross-cutting finding: hidden-alias decorator stacking breaks `_command_name`, and it silently blinds checks 6, 9, 10, 11a, 11b on every renamed command's real name

This is not one of the ten named checks but a shared helper (`_command_name`,
`tools/drift_check.py:502-515`) used by every AST-based parser in my range
(`parse_module_flags`, `parse_module_columns`, `parse_module_signatures`,
`parse_module_required_options`). I'm flagging it here because it materially
changes the answer to "is check 6/9/11a weaker than its name implies" for
every one of them, and the team lead's own `build_flag_surface` question asks
exactly what this method can't see.

**The mechanism.** `tools/CLAUDE.md`'s rename entries describe the shipped
pattern: "Typer registers one function under two names by stacking
`@app.command("new")` / `@app.command("old", hidden=True)`" — two `@app.command`
decorators on one function. `_command_name` loops `node.decorator_list` and
`return`s on the **first** matching `command(...)` decorator it finds
(`tools/drift_check.py:504-514`). AST `decorator_list` order matches source
order top-to-bottom, and the shipped convention writes the **hidden alias
first**, the **real/visible name second**:

```python
@app.command("list", hidden=True)
@app.command("list-activities", short_help="Get Agent Activities.")
def list_activities(...):
```
(`src/wxcli/commands/cc_agents.py:247-248`)

So `_command_name` returns `"list"` — the hidden, deprecated alias — and never
reaches `"list-activities"`, the current, documented, correct name.

**Proven live, not inferred.** Ran `_command_name` against the parsed AST of
`cc_agents.py`:
```
_command_name result -> list
```
Then ran the real parsers against the real tree:
```
'list' in flags: True        'list-activities' in flags: False
'list' in sigs:  True        'list-activities' in sigs:  False
column command names containing list: ['list', 'list-statistics']   # no 'list-activities'
```
versus the regex-based `parse_module_commands` (which backs check 1/2's
`surface`, not the AST-based one):
```
'list' in cmds: True []                                  # empty — hidden alias, no body
'list-activities' in cmds: True [('GET', '/agents/activities')]   # real, correct
```
So the CLI-surface used by checks 1/2 correctly holds **both** names (because
it's built by regex-splitting the source per decorator occurrence, which
naturally separates stacked decorators into two blocks); the AST-based
surfaces used by checks 6/7/9/10/11a/11b hold **only the hidden one**.

**Scale: 50 functions, not one.** Counting every `FunctionDef` in every
countable module with ≥2 stacked `@app.command(...)` decorators:
```
Total functions with >=2 stacked @app.command decorators: 50
```
including `ai_receptionist.show` (`show-ai-receptionists`/`show`),
`call_queue.show`/`.update` (`show-queues`/`show`, `update-queues`/`update`),
multiple `cc_*` modules' `delete_purge_inactive_entities`
(`create-purge-inactive-entities`/`delete-purge-inactive-entities`), etc.

**Concrete, live-doc impact — not a constructed example.**
`docs/reference/contact-center-core.md:115` documents exactly this command:
```
wxcli cc-agents list-activities --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z"
```
Running the actual `check_flags` and `check_required_flags` functions against
the real tree:
```
'list-activities' in flag_surface['cc-agents']: False
'list-activities' in required_surface['cc-agents']: False
check_flags findings mentioning cc-agents list-activities: []
check_required_flags findings mentioning list-activities: []
```
Both come back empty **not because the citation is correct**, but because
`flag_surface.get("cc-agents", {}).get("list-activities")` is `None`, which
hits the exact branch `check_flags` (`tools/drift_check.py:1064-1066`) treats
as "a mounted sub-typer, not a leaf command" and skips — and
`check_required_flags` does the identical `required = ... .get(command)` /
`if not required: continue` (`tools/drift_check.py:1605-1607`). **Any flag —
right or wrong — cited against `cc-agents list-activities` (or any of the
other 49 renamed commands) is invisible to check 6 and check 11a.** The same
gap propagates to check 9 (`parse_module_columns` uses the identical
`_command_name`) and to checks 10/11b (`parse_module_signatures`).

**Why this matters more than an ordinary miss:** these are exactly the
commands `tools/CLAUDE.md`'s "Renaming the 30 CRITICAL commands" and the
"Three names that answered a different question" sections describe as
*deliberately renamed to the correct, recommended name*, with the old name
kept only as a back-compat alias. The checks' own blind spot falls precisely
on the name the docs are now supposed to use, not on the deprecated one.

**Read the comment that mis-states its own blind spot:** `check_flags`
(`tools/drift_check.py:1065-1066`) says `if real is None: continue  # a
mounted sub-typer, not a leaf command`. That comment names one cause of
`real is None`; the stacked-decorator case above is a second, unacknowledged
one, and it is the more consequential of the two on this tree (50 functions
vs. however many actual sub-typer mounts exist).

---

## Check 1 — `check_parity` (`tools/drift_check.py:607-629`)

- **Name implies:** every non-skipped spec operation has ≥1 CLI command; every
  CLI command maps to a real spec operation (or an explicit `keep_endpoints`
  exception).
- **Actual predicate:** builds `covered = {(method,path): [group command, ...]}`
  from the CLI `surface` (regex-based `parse_module_commands`, so real). `missing_from_cli`
  = spec ops whose `(method,path)` key isn't in `covered`. `cli_ahead_of_spec` =
  covered ops whose key is in neither `spec_ops` nor `skipped_ops`, whose path
  isn't in `kept`, and whose path doesn't start with `{}` (variable-base
  hand-written modules, e.g. converged-recordings, are chartered exceptions —
  `tools/drift_check.py:625-627`).
- **Gated:** yes — both `missing_from_cli` and `cli_ahead_of_spec` are in the
  `failed` boolean (`tools/drift_check.py:3631`).
- **Exemptions:** `field_overrides.yaml`'s `keep_endpoints` list, plus
  `skip_tags`/multipart/untagged via `skipped_ops` (built in `load_spec_ops`,
  `tools/drift_check.py:390-421`).
- **Weaker than the name implies — verified, live:** `keep_endpoints`'s one
  entry is written `"POST /event"`, clearly method-qualified. But the parser
  (`tools/drift_check.py:619-620`) does `k.split(" ", 1)[1]` and keeps **only
  the path** — the method half is discarded and never reaches the `kept` set:
  ```
  keep_endpoints entries: ['POST /event']
  parsed 'kept' set (method discarded): {'/event'}
  ```
  The actual filter in `ahead` is `p not in kept` (`tools/drift_check.py:624`)
  — path only, no method component at all. So the exemption as *written*
  claims to cover one method on one path; the exemption as *implemented*
  covers **every method** on that path. Today this is inert (only one
  `covered` entry exists at `/event`, and it is the `POST` the entry names),
  so nothing is currently mis-exempted — but the code does not enforce the
  method specificity its own YAML author declared, and a future hand-written
  module adding e.g. a `DELETE /event` would silently inherit the same
  exemption with zero new authorization.

---

## Check 2 — `check_references` (`tools/drift_check.py:783-849`)

- **Name implies:** every `wxcli <group> [<command>]` (and prefixless
  equivalent) cited in the doc corpus resolves to a real registered command.
- **Actual predicate:** for each `.md` file matched by `SCAN_PATTERNS`
  (`tools/drift_check.py:634-635`), extract command heads via
  `command_heads`/`TOKEN`/`PREFIXLESS_HEAD` (`tools/drift_check.py:636-673`),
  then check `group`/`command` against `surface` (the CLI's real command
  sets) and `top_level` (main.py top-level commands). Placeholder-containing
  spans are skipped for the `wxcli`-prefixed form only (`PLACEHOLDER.search`,
  `tools/drift_check.py:813-814`) — prefixless citations use a different guard
  (first token must already be a registered group, `tools/drift_check.py:
  811-812`), so the two forms are filtered by different rules, not the same
  one applied twice.
- **Gated:** yes (`dead_refs` in `failed`, `tools/drift_check.py:3632`).
- **Exemption mechanism — `tools/drift_check_allowlist.txt`, four match
  forms** (`tools/drift_check.py:827-830`): bare `entry` ("group command"),
  bare `group` alone, `ref <file> <group>`, `ref <file> <entry>`.
- **Weaker than implied — verified against the live allowlist file.** The
  code's own comments (`tools/drift_check.py:817-826`) and the allowlist
  file's own header (`tools/drift_check_allowlist.txt:6-12`) describe exactly
  one incident where a **bare, whole-repo group exemption** (`user-call-
  settings`) hid 6 real dead references in an unrelated file, and record the
  fix as moving that one entry to the file-scoped `ref <file> <group>` form.
  But the **general capability to write a bare, all-files group exemption is
  still fully live in the code** (`group in allow`, `tools/drift_check.py:
  827`) and is **still in active use today** for 4 entries:
  `commands`, `locations-api`, `trunk`, `route-group`
  (`tools/drift_check_allowlist.txt:15,23,46-47`). Checked live against the
  real CLI surface:
  ```
  commands -> real group: False | top-level: False
  locations-api -> real group: False | top-level: False
  trunk -> real group: False | top-level: False
  route-group -> real group: False | top-level: False
  ```
  So none of the four currently masks a real finding — but the mechanism the
  project's own history calls out as the cause of a real, 6-reference miss was
  narrowed in **one instance**, not retired. If any of `trunk`/`route-group`
  (plausible future routing/CC group names) is ever registered, every dead
  citation of it in every file becomes silently invisible with no additional
  action.
- Two-word allowlist lines that look similar (`cucm commands`, `call-controls
  accessible`, `users assign-license`) are **not** bare-group forms — they
  match only via the exact-pair `entry in allow` check, so they don't carry
  the same all-groups-in-all-files risk; verified `cucm` and `call-controls`
  are themselves real registered groups, so a bare exemption on either would
  have been dangerous, and appropriately the entries used are pair-scoped, not
  bare.

---

## Check 3 — `check_counts` (`tools/drift_check.py:905-938`)

- **Name implies:** the published "N command groups" / "N OpenAPI specs"
  claims in `CLAUDE.md`/`README.md` match the measured values.
- **Actual predicate:** two independent oracles. (1) `harvest_count_claims`
  (`tools/drift_check.py:883-902`) regex-harvests three claim shapes
  (`GROUP_CLAIM`, `BARE_GROUP_CLAIM` gated on `CLI_CONTEXT` appearing on the
  same line, `SPEC_CLAIM`) and diffs each against `distinct_command_sets()` /
  `len(tracked_specs())`. (2) A same-kind cross-file contradiction check
  (`tools/drift_check.py:920-934`) that does **not** consult the measured
  value at all — it only asks whether `CLAUDE.md` and `README.md` agree with
  each other.
- **Gated:** yes (`count_mismatches` in `failed`).
- **No allowlist/ack** — this is a hard, unconditional string/number match.
- **Is it weaker than implied?** Not found in-range. The header itself
  documents the harvester's known blind spot honestly (`BARE_GROUP_CLAIM`
  requires `CLI_CONTEXT` on the same line, so "The CLI is used by 3 groups of
  users" would false-positive, and a rephrase avoiding that shape would go
  undetected — `tools/drift_check.py:874-879`), and that gap is stated as a
  deliberate, disclosed trade rather than a silent one. I did not find a
  fourth claim-shape gap the header doesn't already own.

---

## Check 4 — `check_unreferenced` (`tools/drift_check.py:959-964`, uses
`declared_out_of_scope` at `tools/drift_check.py:946-956`)

- **Name implies:** every registered group is referenced somewhere in the
  skills/agents/rules layer, or is declared out-of-scope.
- **Actual predicate:** `group_refs` (built inside `check_references`,
  `tools/drift_check.py:801-803`) counts, per group, occurrences of `` `group` ``
  or `wxcli group` in files under `.claude/**`. `check_unreferenced` reports
  any group with count `0` that doesn't fnmatch an entry under `CLAUDE.md`'s
  out-of-skill-scope heading.
- **Gated:** yes (`unreferenced` in `failed`).
- **Weaker than implied?** The reference test is extremely loose by design —
  it is satisfied by the **literal backtick-wrapped group name appearing
  anywhere** in a `.claude/` file, or the string `wxcli <group>` appearing
  anywhere, counted per-file only inside the `if rel.startswith(".claude/")`
  branch (`tools/drift_check.py:798-803`). It does not require the mention to
  be inside a skill's routing table, a "use this for" sentence, or any
  structured location — a single incidental backtick citation of the group
  name in an unrelated skill's prose (e.g., a "NOT for X" disambiguation line)
  satisfies "referenced" exactly as well as a dedicated skill section would.
  This matches the docstring's literal claim ("referenced by the skills layer"
  — it doesn't promise *how well*), but it is a materially weaker bar than
  "this group has a skill that owns it," which is the more natural reading of
  check 4's stated purpose in the file header (`tools/drift_check.py:24-25`,
  "every registered group is referenced by the skills layer"). `[verified]`
  on the code path; the "how a reader would over-read the name" judgment is
  mine.
- **Exemption:** `declared_out_of_scope()` reads backticked names under
  `CLAUDE.md`'s out-of-skill-scope heading, via a heading-boundary state
  machine keyed on `OUT_OF_SCOPE_HEADING` regex matching any line starting
  with `#`. `fnmatch` is used for comparison, so a glob pattern in that table
  (none currently use one, as far as this range shows) would work as a
  wildcard exemption too.

---

## Check 5 — `check_overlays` (`tools/drift_check.py:969-982`)

- **Name implies:** no `specs/overlays/**` entry claims a path that upstream
  has since published for real (a stale "the live API serves this, the spec
  omits it" claim).
- **Actual predicate:** for every tracked spec, call `superseded_paths(raw,
  load_overlay(...))` (imported from `tools/spec_overlay.py`, outside my
  range) and report every path returned. I did not read `spec_overlay.py`, so
  I cannot verify `superseded_paths`'s own logic — that function is out of my
  assigned range and I have not followed it. **This is the one check in my
  range whose true strength depends on a helper I have not inspected. Flag as
  `UNKNOWN`: whether `superseded_paths` does an exact path+method match or
  something looser (e.g. path-only, mirroring check 1's `keep_endpoints`
  weakness) is not established by anything in lines 1-1700.**
- **Gated:** yes (`stale_overlays` in `failed`).
- **No ack list observed in my range** — the check has no per-entry
  acknowledgment mechanism visible here; it reports every superseded path
  unconditionally.

---

## Check 6 — `check_flags` (`tools/drift_check.py:1044-1077`)

- **Name implies:** every `--flag` cited immediately after a resolvable
  `wxcli <group> <command>` is one that command actually accepts.
- **Actual predicate:** for each `FLAG_CMD` match in a joined-continuation code
  span, resolve `group`/`command` against `surface` (skip if unresolved — "check
  2 owns names that don't resolve"), look up `real = flag_surface.get(group,
  {}).get(command)`, skip if `None` ("a mounted sub-typer"), then scan
  `arg_region(...)` for `FLAG_CITE` tokens and report any not in `real`.
- **Gated:** yes (`dead_flags` in `failed`).
- **Exemption:** `tools/drift_check_allowlist.txt`, three forms: bare `group`,
  `"{group} {command}"`, `"{group} {command} {flag}"`.
- **THE key weakness, verified live (see the dedicated section above):** the
  `real is None: continue` branch is not only hit by genuine sub-typer mounts.
  It is also hit by **every command that is the visible half of a
  stacked-decorator rename** (50 functions across the tree), because
  `flag_surface` is keyed by `_command_name`, which resolves to the hidden
  alias, not the visible name. For those ~50 commands, check 6 does not
  validate flags at all — not "validates loosely," **does not run.** Verified
  concretely against `docs/reference/contact-center-core.md:115`'s real,
  fenced `wxcli cc-agents list-activities --from ... --to ...` citation:
  `check_flags` produces zero findings for it, and tracing why shows `real is
  None`, not "flags matched."
- Deliberately **not** blind to placeholder-shaped flags (`--location-id
  <loc_id>`) the way check 2 is — the docstring states this is intentional
  (`tools/drift_check.py:1047-1050`), and I found nothing in-range that
  contradicts that stated design choice.

---

## Check 7 — `check_prose_flags` (`tools/drift_check.py:1090-1118`)

- **Name implies:** every backticked `` `--flag` `` in the doc corpus is a
  flag that exists somewhere in the CLI.
- **Actual predicate:** `real = {every flag string in flag_surface, unioned
  across ALL groups and commands}` (`tools/drift_check.py:1107`); a
  `PROSE_FLAG` match fails only if the flag string is in **no command
  anywhere**.
- **Gated:** yes (`prose_flags` in `failed`).
- **Is it weaker than the name implies?** Yes, and uniquely among my checks
  **the file's own docstring already says so, explicitly and by name**
  (`tools/drift_check.py:1090-1105`, and the file header lines 34-43): it can
  only ever prove "this flag string exists on *some* command," never "on the
  command actually named nearby." The worked example given in the source
  itself is `--media-type` on `cc-ewt show` — real only on `cc-tasks create`
  — and the docstring states plainly that this passes and always will. I am
  not the one surfacing this weakness; the code already discloses it. Because
  of the `real` set's construction (union over `flag_surface`, which — per the
  cross-cutting finding above — is itself missing every stacked-decorator
  rename's own flags under its visible name), a flag that exists **only** on
  one of those 50 renamed commands' visible identity is still fine here (the
  flag string itself is still present in the union, just filed under the
  hidden alias's entry) — so check 7's already-disclosed weakness does not
  compound with the hidden-alias bug the way checks 6/9/10/11a do.
- **Exemption:** `prose-flag <path> <flag>` allowlist entries, file-scoped (not
  line-scoped — `tools/drift_check_allowlist.txt:125-126` notes this
  explicitly, "so an unrelated edit above the line does not rot the entry").

---

## Check 8 — `check_untracked_modules` (`tools/drift_check.py:1123-1135`)

- **Name implies:** a command module exists on disk, isn't gitignored, but was
  never `git add`ed.
- **Actual predicate:** exactly that — `module_state()["untracked"]` (`=
  on_disk - ignored - tracked`, computed in `module_state`,
  `tools/drift_check.py:281-305`), reported with whether it's already named in
  `_registry.py` (`"registered": m in registered`).
- **Gated:** yes (`untracked_mods` in `failed`).
- **No allowlist/ack.** This is purely structural set arithmetic; I found no
  gap between what the name claims and what the code does. `ignored_files`
  (`tools/drift_check.py:258-275`) is a single batched `git check-ignore
  --stdin` call, consulting the index so a tracked path is provably never
  reported as ignored — this is asserted, not merely hoped, per the comment
  and matches `tools/CLAUDE.md`'s account of the 2026-07-26 fix.

---

## Check 9 — `check_table_columns` (`tools/drift_check.py:1302-1353`, using
`spec_item_fields` at 1168-1208, `resolve_item_fields` at 1211-1242,
`parse_module_columns` at 1255-1299)

- **Name implies:** every accessor in a generated list command's `columns=`
  exists on the actual 200-response item schema.
- **Actual predicate:** for each command with a static `columns=` literal
  passed to `emit(...)` (found via `ast.literal_eval` on the keyword,
  `tools/drift_check.py:1274-1283`), resolve the declaring operation's item
  schema (`spec_item_fields`, unioned **only when specs agree** — provenance
  is otherwise kept per-spec and requires a `spec_authority` pin,
  `resolve_item_fields`), and flag any non-dotted column accessor absent from
  that resolved schema.
- **Gated:** yes, for the primary `findings` list (`bad_columns` in `failed`)
  and for `unpinned_specs` (operations where two specs disagree with no
  `spec_authority` entry — also in `failed`). `wrapper_only` (nested/wrapper
  responses with no scalar field at all) is explicitly **not** gated —
  returned as a third, separate list and never added to `failed`.
- **Exemption:** `spec_authority` block in `field_overrides.yaml`, keyed per
  operation (`spec: <file>` or `spec: union`, plus a `basis: live|unverified`
  and optional `live_fields`). This is the one exemption in my range that is
  fully evidenced per-entry rather than a flat allowlist string.
- **Deliberate, disclosed non-failures:** dotted accessors (`owner.type`) are
  excluded because `_resolve_accessor` legitimately supports them and this
  check can't follow the dot (`tools/drift_check.py:1311-1313,1344-1345`);
  wrapper-shaped responses are excluded because no column list could fix them
  (`1314-1317`). Both are counted and returned, never silently dropped.
- **Same hidden-alias gap as check 6, and it's the same root cause, not a new
  one:** `parse_module_columns` calls `_command_name(node)`
  (`tools/drift_check.py:1270`) exactly like `parse_module_flags`. Verified
  live: `cc_agents`'s column list for `list-activities` is filed under `list`
  instead; `check_table_columns` dedupes on `(group, cmd)` per module
  (`tools/drift_check.py:1328-1332`), so the **first** decorator's name wins
  the `seen` set the same way it wins `_command_name`, and the visible
  rename's own columns are never checked under its real name. I did not
  re-run check_table_columns end-to-end against a deliberately-bad column on
  a renamed command (that would require injecting a fixture, out of scope for
  a read-only audit), but the mechanism is identical to the check-6 case I did
  prove end-to-end, and the `'list-activities'` absence from
  `parse_module_columns("cc_agents", ...)` output is itself `[verified]` (see
  the cross-cutting section).

---

## Check 11a — `check_required_flags` (`tools/drift_check.py:1582-1627`, using
`doc_invocations` at 1630-1676 and `build_required_surface` at 1568-1579 /
`parse_module_required_options` at 1522-1565)

- **Name implies:** a documented example supplies every option the command
  declares `typer.Option(...)` with `...` (Ellipsis) as its default, i.e.
  every REQUIRED option.
- **Actual predicate:** for each real invocation yielded by `doc_invocations`
  (which already filters to invocations resolving to a real leaf command with
  a known signature), compute `missing = [required option group not
  represented among cited flag tokens]`. **Only fenced-block invocations
  (`in_code=True`) fail**; bare single-backtick citations are counted
  separately as `bare_count` and never gate the build
  (`tools/drift_check.py:1620-1622`).
- **Gated:** yes for `findings` (`missing_flags` in `failed`); `bare_count` is
  explicitly excluded from `failed` (advisory only, per the docstring's own
  "Inline hits are counted and printed, never failed," `tools/drift_check.py:
  1598`).
- **Correctly reads the RENDERED command, not the spec** — the docstring is
  explicit that a spec-driven version would produce 12 false positives (11
  `orgId` + 1 `limitToLocationId` via `auto_inject_from_config`), and this is
  structurally guaranteed since `parse_module_required_options` parses the
  actual `.py` file's `typer.Option(...)` calls, which is post-injection.
  `[verified]` — this part of the check's own claim about itself holds up.
- **Exemption:** `tools/drift_check_allowlist.txt`, three forms — bare
  `group`, `"{group} {command}"`, and file-scoped `"required-flag {rel}
  {group} {command}"`.
- **Same hidden-alias gap propagates here too, verified live:**
  `required_surface.get("cc-agents", {}).get("list-activities")` is `None`
  (the required-options dict is also keyed by `_command_name`,
  `parse_module_required_options` line 1546), and `check_required_flags`'s own
  logic (`tools/drift_check.py:1605-1607`) is `if not required: continue` —
  the exact same silent skip as check 6. Verified against the live
  `contact-center-core.md:115` citation: zero findings, for the same
  structural reason (not because the citation supplies `--from` correctly,
  though it happens to).
- One more real, narrower gap worth naming precisely: `doc_invocations` builds
  `sig = positional_surface.get(group, {}).get(command)` and skips if `sig is
  None` (`tools/drift_check.py:1653-1655`) **before** `check_required_flags`
  ever gets a chance to look anything up — so for a hidden-alias-affected
  command the skip actually happens one layer earlier than I described above,
  in the shared `doc_invocations` generator itself (also keyed through
  `_command_name` via `build_positional_surface`), rather than inside
  `check_required_flags`'s own body. Net effect is identical (zero findings,
  for the same root cause), but the precise code location is
  `doc_invocations`, and since checks 10/11a/11b all consume `doc_invocations`,
  **all three are blinded at one shared choke point**, not independently.

---

## Answering the two explicit cross-cutting questions

**1. Does any check in lines 1–1700 compare regenerated generator output
against committed output byte-for-byte, or otherwise detect a hand-edit to a
generated command file?**

**No.** `[verified]` Every check in my range that touches generated command
files (`check_table_columns` via `parse_module_columns`, checks 6/7/8/9/10/11a
via the various `parse_module_*` functions) reads the **currently-committed
on-disk file** exactly once and validates its content against the **spec**
(schema, requiredness) or against **documentation text** — never against a
freshly-regenerated copy of the same file. I grepped the whole 3899-line file
for `regenerat`/`byte-for-byte`/`hand-edit` and found three hits, all outside
my range (`tools/drift_check.py:2879,3181,3460`) and none describing an
automated regenerate-and-diff step; the closest thing to that idea
(`tools/CLAUDE.md`'s "a name-level per-group diff (all 184 groups, committed
vs regenerated)") is documented there as a **one-time manual verification**
Adam ran once during a specific fix, not a standing, automated
`drift_check.py` check. So a hand-edit to a generated `.py` file that
preserves matching flag/column/positional shapes (or one that regenerates
identically) would not be caught by anything in my range; if the generator
and the file on disk disagree, no check here would know, because none of them
ever re-invoke the generator.

**2. `build_flag_surface` — runtime tree or static parsing? What can't it
see? Is it persisted?**

Answered in full above (see the dedicated section). Short version: **static
AST parsing of the committed `.py` source**, never the runtime Click/Typer
tree; it cannot see default values, types, mutual exclusion, or help text,
and — the one non-obvious, verified finding — it **cannot see the visible
name of any command created via stacked `@app.command` decorators**, because
the shared `_command_name` helper returns only the first-listed decorator's
name. It is recomputed fresh every run from disk and fed directly into
checks 6/7 in the same invocation; there is no persisted snapshot and no
second independently-built surface it's reconciled against.
