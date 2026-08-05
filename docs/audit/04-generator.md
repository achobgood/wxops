# 04 — The generator *(Target A only)*

Phase 4 (generator half) plus Phase 3 item 4, run as one session per
`docs/audit/PHASE-4-HANDOFF.md`. The spec half is cut and was not re-opened:
`tools/spec_semantics.json` carries no consequence dimension (`00-facts.md` §5c)
and the generator computes one anyway in `classify_real_semantics`
(`tools/postman_parser.py:107`).

Labels: `[verified]` = I ran or parsed something and read the output.
`[inferred]` = reasoned from evidence short of direct observation. `UNKNOWN`
where I could not settle it.

**Tree measured.** Branch `audit/phase-5-safety` at `3e7fa2b`, plus the four
uncommitted files this phase's subject lives in: `tools/command_renderer.py`,
`tools/generate_commands.py`, `tools/field_overrides.yaml`,
`tests/test_field_overrides.py`. `3e7fa2b` touches no `tools/` file and no
generated module `[verified]`, so the target is exactly the working tree.
Every regeneration was run in a throwaway clone
(`git clone --no-hardlinks`, uncommitted `tools/` copied in), never in the
working tree.

**The premise held.** Phase 2 measured that the generated output is reproducible
and matches what is committed. That is coherence, not correctness — and this
phase found the correctness defects it predicted, in the shape it predicted:
one rule, copied, diverging.

---

## 0. Corrections to prior artifacts

Four numbers this phase moves. Each was measured, and the first two are large
enough that carrying the old figure forward would misstate the finding.

### C1 — The array-drop is **696 fields / 394 commands**, not 476 / 142.

`[verified], two independent methods that agree to the field.`

The audit spec states "142 commands / 476 fields" at
`wxops-architecture-audit-prompt_2.md:454` and `:463`, sourced to nothing —
its own text says *"Found by hand, not by a phase."* It is not in
`00-facts.md` `[verified]` — `grep '476' docs/audit/00-facts.md` returns
nothing.

| Method | Fields | Commands | Modules |
|---|---:|---:|---:|
| Spec side — the generator's own parser over the 9 tracked specs, skips and merges applied | **696** | **394** | 98 |
| Artifact side — each command's `_BODY_SKELETON_*` literal vs its declared flags | **696** | **394** | 98 |

Breakdown of the 696: **406 array-typed, 290 object-typed**; 149 required, 547
optional; by method 322 PUT, 314 POST, 55 PATCH, 5 DELETE.

The two methods share no code. The artifact-side one reads only committed
files: every generated command with a request body carries a
`_BODY_SKELETON_<NAME>` string holding **every** body field, dropped ones
included (it is what `--generate-json-body` prints), so comparing the
skeleton's top-level keys against the command's declared `--flags` measures the
user-visible gap without parsing a spec or joining operations to commands.
Script: `scratchpad/probe_dropped.py`.

**The old figure understates the surface by 46%.** Use 696 / 394.

### C2 — **92** commands have zero scalar flags, not 2.

`[verified], three confirmed live by `--help`.`

`05-safety.md` §2.1 names `device-settings update` and `hot-desking-members
update` as "the extreme case … **two** commands are left with zero scalar
flags." The correct count over git-tracked `src/wxcli/commands/` is **92** —
commands whose entire request-body surface is array/object-typed, so the drop
removes 100% of it and the only options left are `--json-body`,
`--generate-json-body`, `-o/--output`, `--fields`, `--debug`, `--help` and
(where applicable) `--verify`/`--force`.

Confirmed live, three of the 92 `[verified]`:

```
wxcli call-park update-settings --help
wxcli announcement-playlists update-playlists --help
wxcli cc-aux-code update --help
```

each render exactly that option set and nothing else. The list of 92 is in
`scratchpad/dropped-shipped.json`. Phase 5's two are in it; the other 90 were
not counted.

This matters because `announcement-playlists update-playlists` is **in Phase
5's own blast-radius table** (`05-safety.md` §2.1, *"which locations a
music-on-hold playlist is assigned to — can span every location"*) and is one
of the 92. The extreme case was not two commands; it is a class.

### C3 — A **fifth** vendor-prose replace case, and it is the most explicit in the corpus.

`[verified], read out of the spec file.`

`05-safety.md` §2.1 lists four operations whose vendor prose states
replace-not-merge. All four state it in the **operation `description`**. A scan
of both levels (`scratchpad/probe_prose.py`) found two more that state it in a
**body field's `description`** — the level the generator actually reads:

| Operation | Field | required | Vendor sentence |
|---|---|---|---|
| `PUT /telephony/config/devices/{deviceId}/members` (`device-settings update`) | `members` | **false** | *"This specifies the new list of device members, **completely replacing the existing device members. If the member's list is omitted then all the users are removed except the primary user.**"* |
| `PUT /telephony/config/operatingModes/{modeId}` (`operating-modes update`) | `holidays` | false | *"Updated holidays. **This will replace the existing holidays.**"* |

The first is the finding of this phase in one row, and §1.3 develops it.

**Two honest limits on that scan.** My regex is narrower than Phase 5's and
missed `hot-desking-members`' operation-level *"The request replaces the hot
desking profile member list"*, so it is **not** a recount of the 42 and I do not
present it as one. And it produced one false positive I checked and excluded:
`PUT /meetingPreferences/schedulingOptions` matched on *"are removed"*, but its
full sentence documents the **safe** semantics — *"If `delegateEmails` is null
or not specified, the user's delegate emails are not changed"* — which is the
inverse of the hazard. It is the one operation in the corpus that says
merge-not-replace out loud.

### C4 — A hypothesis I raised and disproved: `$ref`'d arrays are **not** mistyped.

`[verified], and recorded because the next reader will have the same idea.`

`tools/openapi_parser.py:378-386` emits `field_type="object"` **unconditionally**
for any body property reached through a `$ref` that does not resolve to a
scalar — including, in principle, one that resolves to `type: array`. Any future
rule keying on `"array"` specifically would silently miss those.

Measured over the 9 tracked specs: **115 `$ref`'d non-scalar body properties,
of which 0 resolve to an array.** The resolved `type` distribution is
`{string: 111, object: 115}`, and **0** resolved schemas carry an `items` key at
all, so there is no untyped-array case hiding behind the default either.

**Latent, not live.** The hardcode is correct for today's corpus. It becomes a
defect the moment a spec `$ref`s an array schema, and nothing detects that.
A worker on this phase reported it as a live mislabel; that reading is wrong on
the current tree and is corrected here.

---

## 1. PHASE 3 item 4 — what the array/object drop hides

### 1.1 It is not one branch, and it is not thirteen — it is **fourteen**

`[verified]` The handoff and the operator's note both give 13 sites. A grep for
the majority spelling misses one:

```
$ grep -n 'field_type in ("object", "array")' tools/command_renderer.py     # 13
$ grep -nE 'field_type (in \("object", "array"\)|== "object")' …            # 14
```

`:1511`, inside `_render_create_command`'s flag loop, spells the identical rule
`if bf.field_type == "object" or bf.field_type == "array":`. `field_type` is a
closed five-value enum (`string|number|bool|array|object`,
`tools/openapi_parser.py:162-175`, the only assignment site), so the two
spellings are behaviourally identical today.

**That is the finding in miniature, and it happened to this audit.** Two
successive attempts to enumerate "the same rule copied N times" both undercounted,
because the enumeration method was a grep for one spelling of the rule. A copy
that drifts in *form* while staying correct in *meaning* is invisible to the
instrument used to find copies.

The 14 sites, by what they cost:

| Kind | Sites | Consequence |
|---|---|---|
| Flag/param loop | `:1511, 1613, 1621, 1897, 2010` | field is **invisible in `--help`** |
| Body-build loop | `:1544, 1662, 1677, 1944, 2035` | field **cannot be set** except via `--json-body` |
| Example token loop | `:1041` | field is **absent from the runnable example** |
| Collision detection | `:1122` | field **bypasses `ReservedParamCollisionError`** |
| Collector (inverted) | `:982` | field is **collected** — `_flagless_required_body_fields` |
| Docstring | `:974` | prose describing the other 13 |

**Do they agree?** On the drop itself, yes — every one of the 10 flag/body sites
drops exactly when `field_type in ("object","array") OR param in used_names`,
and `used_names` comes from the one shared `_used_param_names(ep)` helper at
every site, so the sets cannot diverge `[verified]`. `:982`'s inverted collector
uses the identical two-part condition restricted to `bf.required`, so the
disclosure it drives stays in sync **structurally**, not by coincidence.

**Two sites do something no other site does**, and only one is documented:

- **`:1544`** (create's body-build) emits `body.setdefault(name, default)` for a
  defaulted array/object before continuing. No other body-build site does.
  **But the mechanism fires on zero commands** — no body field in the 9 tracked
  specs is array/object-typed *and* carries a non-`None` default `[verified]`.
  It is dead code, and reporting the asymmetry without that measurement would
  have overstated it.
- **`:1122`** (`_check_reserved_collisions`) skips array/object fields *before*
  the reserved-name test, so an array-typed body field named `fields`, `output`
  or `all` would never raise. Harmless today — the same field is dropped as a
  flag by 10 other sites, so no duplicate Python parameter can be produced, and
  no tracked spec declares such a field `[verified]`. **But the exemption's
  soundness rests on ten independent copies staying aligned in effect.** Nothing
  ties them together: no shared predicate, no assertion, no test that fails if
  one site changes. `:1511` already proves they can drift in form unnoticed.

### 1.2 The disclosure mitigation covers the safe case and structurally misses the dangerous one

`[verified]` — **this is the sharpest result in the phase.**

The generator is not silent about dropped fields. `_render_example`
(`:1001-1057`) switches the runnable `Example:` line to
`--json-body '<skeleton>'` when a body field is flagless — but only via
`_example_json_body` → `_flagless_required_body_fields`, which is restricted to
**`bf.required`** (`:981`).

**A scope control that defaults to "everything" is by definition optional.** So
the one mitigation that would put the field in front of an operator is gated on
the exact property the dangerous class does not have.

Measured over the 394 commands carrying a dropped field `[verified]`:

| | commands |
|---|---:|
| Runnable `Example:` carries `--json-body` (a required field forced it) | 122 |
| **Runnable `Example:` omits every dropped field** | **272** |

**The 272 was derived twice, from opposite ends, and agrees exactly.** I counted
it forward from the shipped artifact — commands whose emitted `Example:` line
contains no `--json-body`. A worker counted it backward from the spec —
commands for which *every* dropped field is `required: false`, which is
precisely the condition that stops `_example_json_body` returning a skeleton.
Same 272. The predicate and its observable consequence line up with no residue,
which is what makes this a property of the rule rather than an artifact of
either measurement.

The confirmed case is the worked example. `device-settings
create-apply-line-key-template` has `locationIds` optional, so:

```
Example: wxcli device-settings create-apply-line-key-template --action APPLY_TEMPLATE --template-id TEMPLATE_ID
```

**The generator's own copy-pasteable example is the org-wide invocation.** It
gained a hand-written `NOTE:` on 2026-08-04 and a `command_confirms` gate; the
example line beneath the note still teaches the unguarded call.

By contrast `hot-desking-members update`, whose `members` is *required*, gets
`Example: wxcli hot-desking-members update PERSON_ID --json-body '{"members":[…]}'`
`[verified]` — correct, and correct for the reason that cannot generalize.

### 1.3 `device-settings update` — the class in one command

`[verified]` end to end, from spec text to generated source to `--help`.

```
Docstring : "Update Members on the device."
Example   : wxcli device-settings update DEVICE_ID
Options   : --generate-json-body --json-body -o --fields --verify --debug --help
Body build: if json_body: body = load_json_body(json_body)
            else:         body = {}
Call      : api.session.rest_put(url, json=body, params=params)
```

Against a field whose own spec description reads *"completely replacing the
existing device members. If the member's list is omitted then all the users are
removed except the primary user."*

Six independent mechanisms each decline to intervene, and each declines
correctly by its own rule:

1. **Not destructive-classified.** `classify_real_semantics` sees summary
   *"Update Members on the device"* and no delete-shaped field name → `None`.
   So no confirm, no `--force`, no `DESTRUCTIVE:` line.
2. **No flag.** `members` is array-typed → dropped at `:1621` and `:1677`.
3. **No example disclosure.** `members` is optional → §1.2.
4. **No required-field validation.** `_render_update_command` emits none at all
   (§2.2).
5. **No `command_confirms` override.** That mechanism is hand-keyed per command;
   nobody has written this entry.
6. **`--verify` exists but cannot help.** `verify_write` compares scalars with
   `!=` (`common.py:173`), so it would report the array as "changed" without
   naming the members that disappeared — and it runs *after* the write.

`wxcli device-settings update DEVICE_ID`, typed exactly as the tool prints it,
issues `PUT /telephony/config/devices/{deviceId}/members` with body `{}`.
I did not run it — this repo points at a live org — so **what Webex does with an
empty body on that endpoint is `UNKNOWN` to this audit.** The vendor's own
sentence says what omitting the list means; whether `{}` and `{"members": []}`
are the same to the server is not established here and should be settled on a
throwaway device before anyone relies on either answer.

### 1.4 Scope control vs payload — what I can and cannot classify

`[verified]` for the mechanical part; **the full per-field classification is
incomplete and I am reporting it that way rather than estimating.**

A name-shaped filter over the 696 (`locationIds`, `siteIds`, `teamIds`,
`deviceIds`, `tags`, `include/excludeDeviceTags`, …) returns **70 fields across
68 ungated commands**, but it is a poor instrument: most hits are
`phoneNumbers` on selective-call-handling criteria, where the array is the
**payload** (the numbers a rule matches), not a scope control. Name matching
over-includes, exactly as Phase 5 measured for its own vocabulary detector
(§2.1: 53.8% false-positive rate).

What survives as genuine scope control, verified individually:

| Command | Dropped scope field(s) | Example carries it? | Gated? |
|---|---|---|---|
| `device-settings create-apply-line-key-template` | `locationIds`, `includeDeviceTags`, `excludeDeviceTags` | **no** | yes — hand-written 2026-08-04 |
| `device-settings preview-apply-line` | `locationIds`, `includeDeviceTags`, `excludeDeviceTags` | **no** | **no** |
| `announcement-playlists update-playlists` | `locationIds` | yes (required) | no |
| `live-monitoring create` | `siteIds` | no | no |
| `cc-desktop-layout create` / `update` | `teamIds` | no | no |
| `device-dynamic-settings` ×5 | `tags` | 1 of 5 | no |

**`device-settings preview-apply-line` is the finding about the fix.**
`[verified]` It carries the **byte-identical body schema** to
`create-apply-line-key-template` — same `locationIds`, same
`includeDeviceTags`/`excludeDeviceTags`, same `advisoryTypes` — and it received
**neither** the help note nor the confirm. Lower consequence, because it
previews rather than applies. But it establishes that the 2026-08-04 remediation
was applied **per command name**, by hand, via `command_help_notes` /
`command_confirms` keyed on one string. That mechanism scales at one YAML entry
per instance somebody notices, and the instance sitting directly beside the one
that was noticed was missed.

### 1.5 The per-field classification — counted, with its precision stated

`[verified]` for the counts; the rule is stated before the numbers because the
numbers mean nothing without it. Data: `scratchpad/dropped-fields-classified.json`.

Rule as actually applied, per field, in evaluation order:

1. **DELETE-body array → PAYLOAD.** All 5 are `required: true` and are enforced
   client-side by delete's own check (the issue #21 fix), so none can be
   silently omitted.
2. **PUT/PATCH, item schema requires a delta discriminator (`action: ADD|DELETE`)
   → PAYLOAD.** Phase 5's own exclusion (§2.1): omitting a member leaves it
   untouched.
3. **PUT/PATCH array, otherwise → COLLECTION-REPLACE.**
4. **PUT/PATCH object → UNKNOWN.** Whether a whole-object PUT replaces or merges
   an omitted nested bundle is stated by no description in the dataset, so it is
   not guessed.
5. **POST, description explicitly states the field narrows a search over
   locations or devices (omission = "every X") → SCOPE-CONTROL**, sentence
   quoted.
6. **POST, sole array of a `*-bulk` endpoint, or a filter on a non-mutating
   `create-fetch-*` lookup → PAYLOAD** (structural).
7. **Everything else → PAYLOAD**, except a literally empty spec description →
   **UNKNOWN**.

| Class | Fields | Commands |
|---|---:|---:|
| PAYLOAD | 291 | 187 |
| COLLECTION-REPLACE *(shape only — see below)* | 173 | 130 |
| **UNKNOWN** | **224** | **98** |
| **SCOPE-CONTROL** | **8** | **2** |

Three things must be read with these numbers or they will be misused.

**The 130 is not a corrected 42.** Phase 5's 42 is a *triaged operation* count —
91 shape candidates, minus 8 delta-instruction arrays, then a read of every
remaining description. The 130 here is the *untriaged command-level candidate
pool* at the same stage Phase 5 called 83, at Phase 5's own measured 49–54%
precision. Different unit, different stage. **Do not quote 130 as a replacement
for 42.** What it does add: **135 of the 173 fields are optional**, so on most
of them nothing — not the example, not a required-field check, not a confirm —
puts the field in front of the operator.

**The 8 is a floor, not a count.** The rule required the description to state
the narrowing explicitly, which is high-precision and low-recall — exactly the
trade-off Phase 5 measured for its own vocabulary detector. `live-monitoring
create .siteIds`, `cc-desktop-layout .teamIds` and `announcement-playlists
update-playlists .locationIds` are scope controls by inspection and are not in
the 8; they are in UNKNOWN.

**But the 8 lands on two commands, and they are the pair.** The classifier,
working only from spec text and blind to the 2026-08-04 fix, independently
selected `create-apply-line-key-template` **and** `preview-apply-line` — the
command that was fixed and the identical one beside it that was not. That is
independent corroboration of the §1.4 finding from a different direction.

**One field is in two classes at once, and it is the worst command in the
corpus after §1.3.** `announcement-playlists update-playlists`'s `locationIds`
is **both** collection-replace **and** scope-defining: the array is the stored
assignment list *and* it decides which locations a music-on-hold playlist
applies to. It was flagged as both rather than forced into one bucket. It is
also one of the 92 zero-scalar-flag commands (C2) and one of the 11 Phase 5
named. So: a field whose omission both unassigns every location and defines the
scope, on a command with no other flags at all.

**A negative result worth recording, because it closes a lead.** The handoff
sent this hunt at `00-context.md` Q1 classes 3 and 4 first. Class 3 (async job
endpoints) yields exactly the pair above and nothing more. **Class 4
(bulk-array writes — `scim-bulk`, `org-contacts create-delete`, `meetings
create-bulk-delete`, ~30 `cc-*/bulk`) is entirely PAYLOAD**: those arrays are
the target list, so omitting one narrows what is touched rather than widening
it. Class 4 was measuring blast-radius-per-call, which is a different property
from omission-widens-scope, and the distinction holds up. **Do not re-run class
4 looking for scope controls.**

**224 UNKNOWN is itself the finding about the spec.** A third of the dropped
fields carry no statement of whether omitting them removes anything. **198 of
the 224 are object-typed fields on a PUT/PATCH** — whether a whole-object PUT
wipes an omitted nested settings bundle is documented nowhere and verified
nowhere, and it is the single largest unanswered question the drop leaves
behind. **62 have no description at all**, and across all 696 dropped fields
**78 are undescribed**. (§6.2 counts 82 undescribed against a different
denominator —
783 *spec-operation-level* occurrences, before tag skips and merges collapse
them to 696 rendered command-fields. Both are measured; they are not the same
unit.) §6.2 also shows 28 more have a description the parser throws away. A
prose-based classifier — the cheap win Phase 5 proposed — is blind on all of
them, and no amount of care in the detector fixes a field the vendor never
described.

---

## 2. The six render paths — where they disagree, and what each disagreement is worth

`RENDERERS` (`command_renderer.py:2067`) maps 8 `command_type` values onto 6
functions. The multiplier on any per-renderer defect, counted by structural
signature over the 184 git-tracked modules `[verified]`:

| Renderer | Commands |
|---|---:|
| `_render_list_command` | 516 |
| `_render_show_command` (+ `settings-get`) | 386 |
| `_render_update_command` (+ `settings-update`) | 375 |
| `_render_create_command` | 347 |
| `_render_delete_command` | 179 |
| `_render_action_command` | 57 |

`settings-update` is a **dead `command_type`** — `detect_command_type` never
returns it and no `command_type_overrides` entry sets it. Harmless, vestigial.

**They are not one system with six thin dispatches.** They are six
independently-evolved paths sharing several extracted helpers
(`_render_path_arguments`, `_render_query_params`, `_render_error_handler`,
`_render_docstring`, `_render_output_options`, `_check_reserved_collisions`)
and diverging, mostly undocumented, on every capability that was added *in
reaction to a bug on one renderer* rather than designed once. `tools/CLAUDE.md`
names that exact history for `--output`: *"There was no design reason. It grew…
nobody revisited update/delete/action — until this branch."* The same shape is
still present in five more capabilities.

### 2.1 Deliberate divergences (each cites its own record) — not findings

`--output` defaults differ by renderer (`id` on create, `table` on list, `json`
elsewhere) — decided 2026-07-25, recorded in `tools/CLAUDE.md`. `--verify` is
emitted only where `_can_verify` holds. `--all`/`--limit` are list-only.
Delete's `--generate-json-body` guard is `has_body and json_body_example`
rather than `json_body_example` alone, with a seven-line comment at `:1886-1893`
explaining the `NameError` it prevents. `_render_error_handler` is a real shared
function called from 8 sites — the counter-example showing what "one function,
not eight copies" looks like in this file.

### 2.2 Required-body-field validation: two disagreeing copies, two renderers with none

`[verified]` — the strongest render-path finding, and it lands on 432 commands.

One conceptual rule — *tell the operator locally when a required body field is
missing, instead of letting the API 400* — implemented three different ways:

| Renderer | Validation | Scope |
|---|---|---|
| `_render_create_command` (`:1554-1560`) | `_missing = [f for f in […] if f not in body or body[f] is None]` | **inside the `else:` branch**, so `--json-body` bypasses it; and the required list is built *after* the array/object drop, so a **required array is never in it** |
| `_render_delete_command` (`:1947-1959`) | `missing = [f for f in […] if f not in body]` | at function scope, so it applies **with** `--json-body`; required list built from **all** body fields, arrays included |
| `_render_update_command` | **none** | 375 commands |
| `_render_action_command` | **none** | 57 commands |

**The size of the hole, counted at field level:** **144 required object/array
body fields — 73 on create, 64 on update, 7 on action — get no client-side
enforcement of any kind** `[verified]`. Only delete's check (the issue #21 fix)
covers array/object fields at all. Create's `continue` at `:1511` skips them
*before* the required list is built, so its check sees scalars only; update and
action have no check. Verified directly against `src/wxcli/commands/groups.py`'s
`create()`, whose required `schemas` array is in no `_missing` list.

Delete's version carries the argument for why it exists:

> *"Fail HERE, not at the API. A scoped delete whose scope is missing is the one
> shape that must never reach the wire."* (`:1949-1952`)

That argument is verbatim the argument for a collection-replacing PUT, and
update is the renderer that has no check at all. Create's comment at
`:1505-1506` — *"Required fields are validated at runtime when --json-body is
not used"* — is **not true for object/array-typed required fields**, which are
silently excluded from its own required list.

Nothing documents the split as deliberate.

### 2.3 `action` renders boolean body fields as strings

`[verified]` live on two commands.

`_render_action_command`'s flag loop (`:2008-2013`) has no
`if bf.field_type == "bool":` branch, unlike create (`:1519-1522`) and update
(`:1624-1627`). So a boolean body field on an action command renders as
`str = typer.Option(None, "--x")` with no `--no-x`, and `body["x"] = x` sends
the operator's literal text — the JSON **string** `"true"`, not `true`.

```
wxcli domains verify-domain --help
  --claim-domain <str>     A boolean to specify whether the domain needs to be claimed…
  Example --json-body: '{"domain":"…","claimDomain":true,"reserveDomain":true}'
```

The skeleton on the same help screen shows a JSON boolean; the flag beside it
produces a string. Measured: **11 boolean body fields across 9 action-typed
operations**, including `device-settings preview-apply-line
--exclude-devices-with-custom-layout` (`[verified]` — rendered `<str>` on the
live `--help` in §1.4), `mode-management switch-mode
--is-manual-switchback-enabled`, and `location-call-handling
change-announcement-language --agent-enabled`/`--service-enabled`.

### 2.4 A delete reports a different outcome depending only on `--output`

`[verified]` in the generated source.

Known issue #20's fix made the success message follow `real_semantics` rather
than the HTTP verb. It reached `_no_body_result_expr` → `_success_message`,
which is what `-o json`/`-o text`/`--fields` route through. It never reached
`_render_delete_command`'s own prose branch, which hardcodes `echo_line` from
nothing but the presence of a path var (`:1920`, `:1923`).

`src/wxcli/commands/numbers.py:156,158`, one function, two branches:

```python
typer.echo(f"Deleted: {location_id}")                        # -o table | -o id
emit({"status": "removed", "id": location_id}, …)            # -o json  | --fields
```

**9 DELETE-typed operations** have `real_semantics != "delete"` (`remove`,
`revoke`, `unassign`) and therefore report two different outcomes for the same
call. The confirm prompt is derived from the URL's terminal segment rather than
from `real_semantics` too, so 8 of the 9 also prompt with the wrong verb.

This is known issue #20's own defect class, recurring inside the one renderer
the fix was generalized *from*.

### 2.5 Three latent divergences, each measured to zero live instances

Recorded because "0 today" is a different claim from "cannot happen," and this
repository's own rule is that a zero deserves more suspicion than a large number.

- **`--json-body` on commands with no body.** Delete gates it on
  `if has_body:`; create, update and action append it unconditionally. **87
  commands** (45 create, 9 update, 33 action) carry a `--json-body` option that
  can do nothing. Live, but harmless — a useless flag, not a wrong one.
- **`_emits_force_flag` vs delete's `has_spec_force`.** The new helper
  (`:1827-1840`) checks query params **and** body fields for a `force`
  collision; delete's inline guard (`:1908`) checks query params only. The only
  two body fields named `force` in the tracked specs are on POSTs, so delete's
  narrower guard is not reachable today. A future DELETE with a body field
  `force` would emit two `force` parameters — a generation-time `SyntaxError`,
  which is loud.
- **`_expansion_kwargs`** (the `--calling-data` interlock) is wired into
  list/show/create/update and not delete/action. `FIELD_UNLOCKS`
  (`common.py:83-85`) has one entry, and **0** delete- or action-typed
  operations declare `callingData`, so it cannot fire today.

Also live: `_render_action_command` has **no no-body result branch** at all
(`:2062` is an unconditional `emit(result, …)`), so a 204 from an action
endpoint reaches `emit(None, …)`. Update and delete both got that branch in the
2026-07-25 "Finding 9" fix; action was not brought into it. Up to 57 commands.

---

## 3. The 2026-08-04 fix, read as changed code

### 3.1 Is it complete? Yes against today's data, no structurally

`[verified]` `detect_command_type` (`tools/openapi_parser.py:407-456`) derives
`command_type` from the HTTP method: GET yields only `list`/`show`/
`settings-get`, and POST/PUT/PATCH/DELETE yield only
`create`/`update`/`delete`/`action`. So no destructive operation can reach
`_render_list_command` or `_render_show_command`, and all four write-capable
renderers now emit a gate — three via the new
`_render_force_option`/`_render_destructive_gate` pair, delete via its own
pre-existing inline block.

The one escape hatch is `command_type_overrides`
(`tools/postman_parser.py:229-232`), which sets `ep.command_type` to any string
with **no check against the endpoint's HTTP method**. Exactly one entry exists
today and it maps a GET to another GET shape (`"PSTN": {list-connection:
"settings-get"}`, `field_overrides.yaml:386`). Nothing in `drift_check.py`
reads `command_type_overrides` at all `[verified]`.

**So the wiring is four manual call sites, not one rule at the dispatch point.**
That is the same shape as the bug being fixed — the confirm lived in one render
path because someone put it there, and it now lives in four because someone put
it in four.

### 3.2 The guard is pinned by nothing — measured by mutation

`[verified]` in a throwaway clone at `3e7fa2b` + the uncommitted `tools/`.

Removed all six call sites of `_render_force_option` and
`_render_destructive_gate` from `tools/command_renderer.py`, then regenerated
all nine specs:

| | before | after mutation |
|---|---:|---:|
| Generator exit code, all 9 specs | 0 | **0** |
| Gated commands (`typer.confirm`, by AST) | 207 | **183** |
| `if not force:` lines in `src/wxcli/commands/` | 204 | 180 |
| `python -m tools.drift_check --enforce` | PASS | **PASS, exit 0** |
| Tracked artifact-guard tests (23 files) | 415 passed | **415 passed** |

The 24 lost are exactly the 24 added on 2026-08-04 (23 `real_semantics` cases
plus `device-settings create-apply-line-key-template` via `command_confirms`).

**A change that silently removes every confirmation gate this audit added ships
green through the full blocking gate and the entire tracked test suite.** That
is `02-drift.md` F3 measured on the specific fix, not restated.

### 3.3 The check that would pin it — prototyped and proven in both directions

`[verified]` `scratchpad/proto_check21.py`.

The check: every operation `classify_real_semantics` flags destructive must have
a `typer.confirm` in its rendered command body. Two in-repo artifacts, no
network, no fixture.

| Tree | destructive ops | matched | findings | exit |
|---|---:|---:|---:|---:|
| Clean (working tree) | 199 | 191 | **0** | 0 |
| Mutated (gate removed) | 199 | 191 | **22** | 1 |

The 23rd `real_semantics` case and the `command_confirms` scope case are the
two the prototype does not claim — correctly for the second (it is gated on
scope, not destructiveness) and as a residual gap for the first.

**One correction to my own prototype, because it changes the recommendation.**
My first pass caught only **8** of 24, because I hand-rolled the spec↔command
URL join and it dropped every Contact Center path (the base URL is itself
interpolated, `f"{cc_base_url}/organization/…"`, so erasing it to `{}` left a
phantom leading segment). After fixing that, 8 residual operations still fail to
match — five of them because CC spec paths carry a `/v1` prefix the rendered URL
does not.

**So the production form must not reimplement the join.** `check_parity`
(check 1) already consumes `build_cli_surface()` and
`load_spec_ops(skip_tags)`, both keyed `(method, path)`, and check 1 currently
reports `missing_from_cli: 0` — which is proof that pair joins correctly across
all nine specs including CC. The check is those two existing indexes plus one
predicate on each side. That is also the precedent check 19 set:
*"it imports the generator's own resolvers rather than reimplementing them."*

### 3.4 Where the check must live

`.gitignore:53` ignores `tests/*` with individual negations, each carrying the
reason it was promoted (`:58-62`, `:73-76`, `:77-81`, `:86-99`). The convention
is one negation per file that has proven it catches real drift — not a blanket
`!tests/**`. A new `tests/test_drift_check_confirms.py` plus one negation line
follows it exactly, and sits beside the seven `test_drift_check_*.py` guards
already tracked that way.

### 3.5 The generator's own tests: the sequencing precondition

`[verified]` All four are untracked, and `git log` shows when each left:

| File | Tests | Left tracking |
|---|---:|---|
| `tests/test_command_renderer.py` (1,397 LOC) | 134 | `04f6b78`, 2026-03-27 |
| `tests/tools/test_command_renderer.py` (372 LOC) | 20 (**3 failing**) | `93bb23f`, 2026-03-23 |
| `tests/test_generate_commands.py` | 29 | `c5f1021`, 2026-07-06 |
| `tests/test_generator_regression.py` | 4 | **never tracked** — no git history at all |

**"Which of the two same-basename files survives" has a different answer than
the handoff assumes.** They are not duplicates and neither is a superset. Both
directories carry `__init__.py`, so they coexist under pytest — run together:
`151 passed, 3 failed` `[verified]`. The rotting 372-line file holds the only
**dispatch-level** coverage in the repo (`TestRenderCommandFileDispatch::
test_all_command_types_dispatch`, `::test_unknown_type_skipped`,
`TestRenderSettingsGet`) — classes the maintained 1,397-line sibling does not
have. Its 3 failures are all the `short_help=` exact-string assertion Phase 7
identified, pre-existing since `751010c` and unrelated to this audit's change
`[verified]`.

So the answer is **both survive**: repair the three assertions in the smaller
file and track both. Discarding it would delete the only tests that exercise
`render_command_file`'s dispatch — the exact seam §3.1 shows is unguarded.

**No tracked test asserts the destructive gate.** `grep` over `tests/` for
`_render_destructive_gate`, `_render_force_option` and `command_confirms`
returns nothing `[verified]`. `tests/test_field_overrides.py` **is** tracked and
this change did modify it — but only to import `COMMAND_KEYED_OVERRIDES` instead
of re-listing the key names by hand (a real fix: the hand-copy had already
drifted, omitting `command_help_notes`). It validates the YAML's shape, not the
render path.

---

## 4. The spec refresh

### 4.1 Which tool is live, which is vestigial

`[verified]` — imports, doc citations and last-touch dates.

| Tool | LOC | Verdict | Evidence |
|---|---:|---|---|
| `tools/spec_sync.py` | 78 | **LIVE — the entry point** | imported by `command_renderer.py` for `PREFERRED_ORDER`; cited in 9+ docs as *the* regen command; last touched 2026-07-14 |
| `tools/update-specs.py` | 133 | **LIVE — the pull step** | shelled out to by `spec_sync.py`; its 7-spec `SPEC_MAP` matches the documented "first 7 only" claim; its print format matches every `chore(specs)` commit message |
| `tools/spec_overlay.py` | 106 | **LIVE — most embedded of the four** | imported unconditionally in `openapi_parser.py` (every regen) and in `drift_check.py` (check 5) |
| `tools/postman_spec_diff.py` | 157 | **VESTIGIAL** | zero imports repo-wide; last touched 2026-03-28; the only reports it ever produced are dated that same day |

### 4.2 What a `chore(specs)` commit asks a human to review

`[verified]` from `2a89ea4` and `a898c76` — **and the first correction is that
the pair the handoff named is not representative of the label.**

`a898c76` is the thousands-of-lines shape the handoff assumed: **+13,820 /
−8,528, pure `specs/*.json`, zero narrative** beyond path-count bullets.
`2a89ea4` is the opposite: **+24 / −9 across 5 files, containing no spec file at
all**, and extensively hand-narrated by a human who had read the spec. The
actual large regen from that refresh — a 1,089-line new CLI module and a
342-line reference doc — landed in a **third, differently-titled commit between
them** (`2b36011`, `feat(ai-receptionist)`), which neither `chore(specs)` commit
captures.

Across 16 `chore(specs)` commits there are two real patterns: a bare JSON pull
(`a898c76`-shaped) and a single bundled spec+CLI+docs commit (`e1e92c5`,
`649b40b`). **So "read a `chore(specs)` commit to see what a refresh reviews"
does not have one answer** — the CLI consequences of a pull may be in that
commit, in a differently-named sibling, or split across both.

**There is no machine-produced review artifact at the moment of review, and the
one that exists now is ephemeral.**

`tools/spec_semantics.json` — the only field-level artifact that could serve as
one — **did not exist when either commit was made.** `git log` on that path
returns exactly one commit, `b1344a2`, the commit *after* `2a89ea4`, whose own
message says it was written *because* the 2026-08-03 refresh landed 28 new
operations plus edits to four specs, the CLI regenerated, and the gate reported
PASS while three meaning changes went through unseen. The three changes
narrated in `2a89ea4` were found by a human reading the spec.

Going forward, `refresh_spec_snapshot()` (`drift_check.py:3436-3468`) prints
every delta before writing — and the snapshot stores **hashes**, not text. Its
own docstring is explicit: *"this report is the only place the new text
appears."* CI never invokes `--refresh-spec-snapshot` (`ci.yml:128` runs
`--enforce`, which diffs against the snapshot but never regenerates it), and
nothing captures the printed report into a commit message, a docs file or a log
`[verified]`.

**So the durable artifact is the hash file; the human-readable justification for
writing it exists only on one terminal, once.** That is a reviewability finding,
not a correctness one — but it means the answer to *"what did this refresh
change?"* is unrecoverable after the scrollback is gone.

### 4.3 How would anyone detect a response-shape change? Mostly, nobody would

`[verified]` and it is worse than "check 19 doesn't cover it."

`07-testability.md` §3.6 established there is no intermediate model: Webex's
response schema **is** the CLI's output schema, and `--fields` is a JMESPath
expression over upstream field names. So a response-shape change is a breaking
CLI change with nothing in between.

| Layer | On an upstream response-field rename |
|---|---|
| Check 19 (`spec_semantics.json`) | **Silent.** No response field is encoded — request-side only, and `encode_field` takes no type parameter (`02-drift.md` F5) |
| Check 9, commands using `_derive_default_columns` (the majority of 520 list commands) | **Silent, and self-correcting.** Columns are re-derived from the post-rename schema on the same regen, so both sides of the comparison move together and can never disagree |
| Check 9, commands with a hand-written `table_columns` override (95 per-command entries + 12 tag-level blocks) | **Fails the gate** — the frozen override text no longer matches the derived schema. The only place a rename is genuinely caught |
| `-o json` / `--fields` | **Silent and "correct"** — emits the renamed field. An agent projecting `--fields '[].{name:name}'` gets an empty result, no error |
| show / create / update / delete response bodies | **No check anywhere.** Check 9 is list-item-schema only |

The middle row is the sharp one. Check 9's oracle is *derived from the same spec
the rename arrived in*, so a rename is not merely unflagged — it is absorbed and
re-derived by the check that appears to cover it. That is the same structural
blindness the audit spec names for the gate as a whole (spec ↔ CLI ↔ docs are
all downstream of one spec), reappearing inside a single check.

### 4.4 Overlays cannot fix it

`[verified]` `specs/overlays/` is additive **at the path level** and must never
shadow a path upstream publishes — `spec_overlay.py` rule 1, enforced by check 5,
not merely documented. So an overlay can add an operation the vendor omits; it
structurally cannot correct a *wrong response schema* on a path the vendor does
publish. The sanctioned mechanism for that is `spec_authority`'s `live_fields`
(`tools/CLAUDE.md`, the `GET /locations` case), which is per-operation,
hand-written, and carries a capture date — 1 of 7 current entries is `basis:
live`, the other 6 say `unverified`.

---

## 5. Naming, dispatch, and what the generator does with what it does not understand

### 5.1 Renderer selection is pattern-matching, and it is wrong on 4 shipped commands

`[verified]` The HTTP method is real metadata. Everything that turns one verb
into two or three possible `command_type`s is a string test on URL segments or a
shape test on the response schema:

| Branch | Pattern | Fails on |
|---|---|---|
| GET → `show` | last segment is `{param}` or literal `me` | a show-shaped GET not ending on its id |
| GET → `list` vs `settings-get` | 200 schema contains an array | a single-resource GET whose schema nests an array |
| POST → `action` vs `create` | literal segment `actions` or `invoke` | **any other action convention** |

The last one fails on Cisco's own colon-suffix convention. **11 POST operations
in the tracked specs are shaped `…/{id}:publish`, `…/flows:import`,
`…/{id}:lock`** — none matches `actions`/`invoke`, so all fall through to the
POST default, `create`. Five are in the shipped `cc-flow` group, and four still
carry the misnamed result today `[verified]` in
`src/wxcli/commands/cc_flow.py`:

```
create-lock      # "Lock a Flow or Subflow"
create-unlock    # "Unlock a Flow or Subflow"
create-validate  # "Validate a Flow"
create-import    # "Import a Flow"
```

Only `publish` was corrected, by a hand-written `command_name_overrides` entry.
So the boundary was crossed ten times and recovered once, per command, by hand.

### 5.2 Naming is scattered, and `verb_naming.py` grades names it does not produce

`[verified]` Naming decisions live across `postman_parser.py`
(`_derive_command_name`, `_dedup_command_names`, `camel_to_kebab`),
`openapi_parser.py` (tag parsing), `command_renderer.py`
(`folder_name_to_module`, `_safe_param_name`, `_apply_param_name_overrides`)
and a 2,729-line YAML (`cli_name_overrides`, `tag_merges`,
`command_name_overrides`, `param_name_overrides`) — roughly nine naming
functions across three modules plus five override families. **`tools/verb_naming.py`
is a classifier for drift-gate check 12 — it grades names, it does not make
them**; its own docstring says *"nothing here imports or invokes a generated
command."* That distinction matters: the gate can fail a bad name but has no
path to producing a good one, which is why every fix in §5.1 is a hand-written
override.

**And group-name resolution is outright duplicated** `[verified]`:
`generate_commands.py:356-361` and `command_renderer.py:826-861` each
independently resolve `cli_name_overrides` → `folder_name_to_module`. A comment
at `command_renderer.py:780` warns future maintainers not to let the two drift —
which is an accurate description of the hazard and no defence against it. This
is the §1.1 shape again, in a second place: a rule that must agree with itself,
held together by a comment.

The numeric-suffix debt re-measured on the current tree is **42 visible**,
matching `tools/CLAUDE.md`'s claim exactly, all acked, no stale acks.

### 5.3 Skips are silent; `deliberate-gaps.md` is output, not input — and one reason in it is false

`[verified]` by a live generator run in a throwaway clone.

**Silent.** A full `--all` run prints one line per generated module and a
`Total: N tags, M commands` footer. Grepping the full stdout for the four
whole-tag skips in that spec returns **zero matches** — no per-tag message, no
aggregate count, nothing on stderr. The only ways to see a whole-tag skip are
the separate `--list-tags` mode and `drift_check --write-gaps`.

**Trustworthy in the way the handoff worried about.** `check_parity` is called
with `spec_ops`/`skipped_ops` computed fresh from `skip_tags` on every run
(`drift_check.py:3555`) — **not** by reading `docs/arch/deliberate-gaps.md`.
`GAPS_DOC` is referenced twice, both inside `write_gaps_doc`, and nothing reads
it back. So a generator bug that silently dropped an operation whose tag is not
in `skip_tags` would appear in `missing_from_cli` regardless of what the doc
says. **There is no closed loop.**

**The risk is one level up, and one instance is live.** Both the gate's
computation and the human-readable doc read the same `skip_tags` block, so a
tag skipped for a stated reason is simultaneously excused by check 1 and
documented as deliberate — using that same reason, which nothing re-verifies.
The `Functions` entry says:

> *"colon-action paths (`/functions/{id}:publish`) — generator cannot render
> `':'` path segments yet"* (`field_overrides.yaml:884-886`)

That reason is **false on this tree**. The sibling `Flow` tag's five
colon-action operations render today (§5.1), and `_path_to_raw_path`
(`openapi_parser.py:589-614`) splits a `:suffix` into its own segment — which is
what produces the `-lock`/`-unlock` names. "Cannot render" and "chose not to,
and the classifier would misname it exactly like Flow's siblings" call for
different fixes. Five operations are presented as a structural impossibility
when they are an unrevisited editorial choice.

**The generator does fail loudly where it has a rule to fail on.** Six exception
classes, all with live raise sites: `ReservedParamCollisionError`,
`ParamNameOverrideError`, `UnboundUrlPlaceholderError`, `CommandHelpNoteError`,
`CommandConfirmError`, `UnknownSpecProductError`. The pattern is consistent and
good — each guards a configuration that would otherwise be silently inert. What
has no guard is the classification itself: nothing fails when
`detect_command_type` picks the wrong renderer.

---

## 6. Reproducibility by a contributor

Phase 2 proved the generator is deterministic **on this machine**. That is a
different question from whether a fresh clone reproduces the shipped tree.

### 6.1 The generator imports the package it generates, and that import is not clone-local

`[verified]` by a controlled experiment run in both directions.

`tools/command_renderer.py:6` imports `FIELD_UNLOCKS` from `wxcli.common` — a
real top-level import of the runtime package. On this machine that resolves
through an editable-install `.pth` file that hard-codes **the original working
tree's path**:

```
/opt/homebrew/lib/python3.14/site-packages/__editable__.wxcli-….pth
  -> /Users/ahobgood/Documents/webexCalling/src
```

Experiment: edit a clone's own `src/wxcli/common.py` (rename the `FIELD_UNLOCKS`
key), regenerate from the clone with `PYTHONPATH=.` and the mandated
interpreter. **The edit has zero effect** — the output still carries the old
value, because `wxcli.common` was read from the original tree. Repeating with a
genuinely clone-local editable install in an isolated venv makes the same edit
take effect, proving the mechanism is the `.pth` resolution and nothing else.

**Consequence.** A contributor with `wxcli` editable-installed from one checkout
who regenerates in a second checkout silently uses the first checkout's
`wxcli.common`. No error, no warning, exit 0, plausible output. `tools/CLAUDE.md`
documents `pip install -e .` only as a step to run *after* regenerating, never
before.

The fresh-with-nothing case fails **loudly** — `ModuleNotFoundError`, exit 1 —
which is the good failure. The stale-multi-clone case is the silent one, and it
is the case that arises whenever anyone reviews a branch beside `main`.

**Bearing on this phase's own evidence:** the mutation in §3.2 changed
`tools/command_renderer.py`, which loads from the clone via `PYTHONPATH=.`, and
the result is confirmed by direct observation (gated commands moved 207 → 183
in the clone). Only `wxcli.common` came from the original tree, and it was not
modified. The experiment stands.

### 6.2 Two parse-time losses that bound any prose-based detector

`[verified]` over the 9 tracked specs.

- **The operation-level `description` is never read.** `openapi_parser.py` reads
  `description` only from parameters (`:145`, `:243`) and body properties
  (`:375`, `:383`, `:391`); the operation's own `description` is discarded —
  `Endpoint` has no field for it, and `name` comes from `summary` (`:694`).
  **All four of Phase 5's prose-confirmed replace cases state the hazard at that
  level.** So the generator structurally cannot read the sentences Phase 5 found.
- **28 body-field descriptions are discarded by a one-line choice.** For a
  property reached through a `$ref`, `:383` takes `prop.get("description")` —
  the description at the **`$ref` site**, which OpenAPI 3.0 ignores — rather
  than the resolved schema's. Measured: **82 of 783** object/array body-field
  occurrences parse with an empty description, and **28 of those do have one in
  the resolved schema**. Recovering them is a one-line change; the other 54 the
  vendor genuinely never wrote.

### 6.3 Two repo rules that the evidence does not support

`[verified]` — both were assumed by this phase's own brief and both are wrong.

**The Python 3.14 mandate does not hold.** Every `tools/` and `src/` file
byte-compiles cleanly on 3.11, 3.12, 3.13 and 3.14 — no `match` statement, no
PEP 695 syntax, no `itertools.batched`. Going further than compilation: a real
clone-local editable install under **python3.12**, followed by the full nine-spec
regeneration, produced output **byte-identical to the 3.14 run.** The rule is
still fine as a convention (it is what `wxcli` itself installs under), but it is
not a generation-time requirement, and treating it as one has cost at least one
session's worth of "bare `python3` cannot do this" reasoning.

**Determinism is stronger than Phase 2 could claim.** Phase 2 explicitly did not
measure ordering effects, and listed dict/set iteration, locale and dependency
drift as unmeasured risk. Measured here: `PYTHONHASHSEED` is unset everywhere;
a few un-sorted `set()` iterations exist and were traced to output positions
where order does not reach the file; and repeated runs under independently
seeded hashes agree. Combined with the cross-version result above, **the
generator is a pure function of (specs, overrides, generator source) across two
Python versions and multiple hash seeds** — a stronger statement than
`02-drift.md` §3 was able to make, and it strengthens the byte-level-gate
proposal that phase raised.

**One real undeclared dependency, and it is not the generator's.** `flask` is
imported by `tools/webhook_receiver.py` and declared nowhere — but nothing in
the generation path touches it. `PyYAML` is declared and used. `jsonschema` is
used nowhere in the repo, so the suspicion that it was an undeclared generator
dependency does not hold.

---

## 7. THE KEY QUESTION — what must change to add scope guards, confirms or dry-run

The concrete path, per mechanism: what already exists, what is missing, where
the ceiling is.

### 7.1 Confirm on a destructive operation — **templates only, already done, unpinned**

`classify_real_semantics` computes the predicate; `_render_destructive_gate`
emits the gate; the fix shipped 2026-08-04. **No spec change is needed and none
was made.** The gap is not capability — it is that nothing holds it in place
(§3.2). Cost to close: the check in §3.3, one tracked test file, one
`.gitignore` negation.

### 7.2 Guard on a **collection-replacing** write — the classifier's signature is the barrier

The function that must change is named, and so is the reason it cannot do the
job today:

```python
# tools/postman_parser.py:107
def classify_real_semantics(name: str, body_fields: list) -> str | None:
```

It receives **the summary string and the body-field list, and nothing else.** It
cannot see the HTTP method, the URL path, the operation description, or the item
schema of an array. Two consequences, and only the second is expensive:

1. **The call site is not the constraint.** It is invoked at
   `openapi_parser.py:742`, inside `parse_operation`, where `op`, `spec`,
   `method`, `url_path` and the resolved schema are all already in scope.
   Widening the signature is mechanical.
2. **The data model is the constraint.** `EndpointField`
   (`postman_parser.py:14-22`) carries `name, python_name, field_type,
   description, required, default, enum_values` — **and no item schema.** An
   array is `field_type="array"` and nothing else. So Phase 5's recommended
   detector — *"does this array's item schema reference an existing remote
   object of a known KIND",* reusing `_spark_id_kind`
   (`command_renderer.py:653-673`) — **cannot be computed from an
   `EndpointField` as currently modelled.** The item schema is resolved during
   parsing and then thrown away. That is the ceiling: one field on one
   dataclass, plus the code in `parse_request_body` to populate it.

**The cheaper prose scan is bounded by §6.2**: it cannot read the
operation-level sentences where four of the five known cases live, and it is
blind on the 78 undescribed fields. Both halves need a parser change first.
Neither needs a spec change.

### 7.3 Making an array-typed field visible is **not** the fix — and the override file says so

Rendering all 406 dropped arrays as flags would not fix the scope class. The
comment added to `field_overrides.yaml` on 2026-08-04 states it correctly:

> *"Rendering all 476 array body fields as flags would not fix this — the danger
> is the silent default, not the missing flag."*

(The count there is the superseded figure; see C1. The reasoning is right.)

What **would** help, and is cheap, is extending the one mitigation that already
exists. `_render_example` switches to `--json-body` only for *required* flagless
fields (§1.2), which is precisely backwards for scope controls, since a scope
control that defaults to everything is optional by construction. Extending that
trigger to any flagless field the classifier calls a scope control puts the
field into the runnable example for the class that needs it. Templates only,
once §7.2 exists.

### 7.4 Dry-run — 328 commands, no new machinery

Per Phase 5 §2.5: `_can_verify` (`:219-228`) already computes the emission
predicate, and `verify_write` (`common.py:136-183`) already does read-and-diff.
A `--dry-run` is those two operations in the opposite order. Templates only.

**One caveat this phase adds.** `verify_write` compares scalars with `!=`
(`common.py:173`), so on exactly the collection-replacing bodies that matter it
would report "the array changed" without naming the members that disappear. For
the §1.3 class the inversion is necessary and not sufficient.

### 7.5 Summary

| Guard | Spec change? | Parser change? | Template change? |
|---|---|---|---|
| Confirm on a destructive op | no | no | **done, unpinned** |
| Confirm on a collection-replace | no | **yes — signature + item schema on `EndpointField`** | yes |
| Scope control in the runnable example | no | yes (same classifier) | yes |
| `--dry-run` on 328 writes | no | no | yes |
| Response-shape drift detection (§4.3) | no | yes (snapshot the 200 schema) | no |

**Nothing in this table requires a spec change.** The audit spec's hypothesis —
that the absent consequence dimension in `spec_semantics.json` is the root cause
of the missing guards — is not what the evidence shows. The generator already
computes destructiveness without it, and the one thing genuinely missing, an
array's item schema, is present in the specs today and discarded by the parser.

---

## 8. Severity

Target A's model: a defect in the generator or a template counts once and ships
everywhere. Multipliers are counted, not estimated.

| # | Finding | Severity | Multiplier |
|---|---|---|---|
| **G1** | **The runnable `Example:` teaches the unguarded invocation for every optional dropped field.** `_render_example` switches to `--json-body` only when a *required* body field is flagless (`:995`, `:981`), and a scope control that defaults to everything is optional by construction. **272 of 394** commands emit an example that omits every dropped field — including `create-apply-line-key-template`, whose example is the org-wide call (§1.2) | **Critical** | One predicate × 272 commands. It is the only disclosure mechanism that exists, and it is gated on the inverse of the dangerous property |
| **G2** | **`device-settings update` — vendor prose states the hazard, in text the generator reads, and six mechanisms each decline correctly.** Zero scalar flags, optional array, no confirm, no required-field check, example is `wxcli device-settings update DEVICE_ID` (§1.3). A **fifth** prose case Phase 5 did not have | **Critical** | ×1 command, but it is the worked proof that the whole chain fails together, and **92** commands share its zero-flag shape (C2) |
| **G3** | **The 2026-08-04 confirmation gates are pinned by nothing.** Removing all six call sites regenerates cleanly, drops 24 gates, and reports `drift_check --enforce` **PASS exit 0** with **415/415** tracked tests passing (§3.2) | **Critical** | The audit's own remediation × 24 commands, provably reversible in silence |
| **G4** | **Required-body-field validation: two disagreeing copies, two renderers with none.** create excludes required arrays from its own check; delete includes them and argues why in a comment; update and action have no check at all (§2.2) | **High** | 375 update + 57 action = **432** commands with no local check, on the renderer that owns the collection-replace class |
| **G5** | **Renderer selection is pattern-matching on URL segments.** POST→`action` requires the literal `actions`/`invoke`, so Cisco's `…:publish` convention falls through to `create`. 11 operations, 4 shipped today as `create-lock`/`create-unlock`/`create-validate`/`create-import` (§5.1) | **High** | Every future spec adds more; recovery is one hand-written override per command, and 1 of 10 was recovered |
| **G6** | **A response-shape change is invisible, and the check that appears to cover it absorbs it.** Check 19 is request-side only; check 9 re-derives its own oracle from the post-rename schema, so both sides move together (§4.3) | **High** | The majority of 520 list commands, plus **all** non-list response bodies, which no check reads |
| **G7** | **`action` renders boolean body fields as `str`** — no `--x/--no-x`, and the value reaches the wire as a JSON string while the skeleton on the same help screen shows a boolean (§2.3) | **High** | 11 fields / 9 operations, wrong today |
| **G8** | **A delete reports a different outcome depending only on `--output`.** `-o table` prints `Deleted:`; `-o json` prints `{"status": "removed"}` — same call. Known issue #20's own defect class, inside the renderer the fix generalized from (§2.4) | **Medium** | 9 DELETE operations; 8 also confirm with the wrong verb |
| **G9** | **The generator is not clone-hermetic.** It imports `wxcli.common`, which an editable-install `.pth` resolves to a *different checkout*. A contributor regenerating in a second clone silently uses the first one's source — exit 0, no warning (§6.1) | **Medium** | Every contributor with more than one checkout; proven in both directions |
| **G10** | **`deliberate-gaps.md` is trustworthy; its inputs are not.** No closed loop — check 1 computes skips fresh and never reads the doc. But the `Functions` skip reason (*"generator cannot render ':' path segments"*) is **false**: the sibling `Flow` tag's five colon-action ops render today. 5 operations documented as impossible are an unrevisited choice (§5.3) | **Medium** | 5 operations, and the mechanism — an unverified human reason excusing both the gate and the doc |
| **G11** | **The array/object rule is 14 copies, not one function**, and `:1511` already differs in form. `_check_reserved_collisions`'s exemption is sound *only* because ten other copies stay aligned, with nothing enforcing that (§1.1) | **Medium** | Latent × the whole body-field surface; the mechanism by which G4 and G7 arose |
| **G12** | **The refresh's human-readable review artifact is ephemeral.** `--refresh-spec-snapshot` prints the only place the new description text ever appears, and nothing captures it — not CI, not the commit message (§4.2) | **Medium** | Every refresh |
| **G13** | **87 commands carry a `--json-body` that can do nothing** (no body fields); delete gates it correctly and the other three do not (§2.5). **`action` has no no-body result branch**, so a 204 reaches `emit(None, …)` on up to 57 commands | **Low** | 87 + 57, cosmetic-to-annoying |

**G1 and G2 are the same defect from two sides**, in the way `05-safety.md` §2.8
says A1 and A2 are: the generator cannot express an array as a flag, so it hides
the field; and its one compensating disclosure is triggered by a property the
dangerous class never has, so it hides it *in the example too*. Phase 5 named
the invisibility. This phase's addition is that the tool does not merely stay
silent — **it prints a runnable command that performs the omission.**

**What is not here, deliberately.** The generator's guard-rails against inert
configuration are genuinely good and I am not going to pad this list by
implying otherwise: six exception classes with live raise sites, each failing
generation on a config entry that would otherwise silently do nothing, and
`_render_error_handler` is the worked example of one function instead of eight
copies. The drift gate is strong. The defects above are specific, and they
cluster in exactly one place — capabilities added in reaction to a bug on one
renderer rather than designed once.

---

## 9. Sequenced remediation

The order is not optional, and the reason is G3: **a renderer change proposed
today is an unpinned change to the highest-multiplier file in the repo.**

**Step 1 — repair and track the generator's tests.** Fix the three
`short_help=` exact-string assertions in `tests/tools/test_command_renderer.py`
(red since `751010c`, unrelated to this audit's change), then track all four
generator test files with one `.gitignore` negation each, following the
convention at `:58-100`. **Both same-basename files survive** — they are not
duplicates, and the rotting one holds the only dispatch-level coverage in the
repo (§3.5). Cost: three assertions, four negation lines. This is the
precondition for everything below.

**Step 2 — add the check that pins the destructive gate.** Prototyped and
proven in both directions (§3.3): 0 findings clean, 22 on the mutated tree.
Build it from `build_cli_surface()` + `load_spec_ops()` — the pair `check_parity`
already uses, whose join is proven by check 1 reporting 0 — **not** from a
hand-rolled URL match, which is where my prototype lost 16 of 24. Ship with
`tests/test_drift_check_confirms.py` and its negation line, mutation-proven in
both directions per this repo's standing rule.

**Step 3 — only then, the render paths.** In value order: G1 (extend
`_render_example`'s trigger), G4 (one required-field rule applied to all four
write renderers), G7 (the missing `bool` branch in `_render_action_command`),
G8 (route delete's prose line through `_success_message`). Every one is a
template change with no spec change and no parser change. Each must regenerate
with a before/after diff — **a fix that changes output for commands you did not
intend to touch is a finding about the fix.**

**Step 4 — the parser change, and only if the class is worth it.** §7.2: widen
`classify_real_semantics`'s signature and carry an array's item schema on
`EndpointField`. This is the only item here that is not cheap, and it is the
only one that can reach the collection-replace class automatically. The
one-line recovery of the 28 discarded `$ref` descriptions (§6.2) belongs here
and is nearly free.

**Steps 1 and 2 are SHIPPED — see §11.** Step 3 remains unstarted, which
was the point of the ordering. Step 2 found on its first run that the
2026-08-04 guards were never committed (§11.3).

---

## 10. Read coverage, and what I did not measure

**Read in full:** `tools/command_renderer.py` (2,240 lines — every render path,
every helper cited, and the full uncommitted diff), `tools/postman_parser.py`,
the relevant halves of `tools/openapi_parser.py` (`parse_request_body`,
`parse_operation`, `detect_command_type`, `_pagination_style`),
`tools/generate_commands.py`'s override plumbing, `check_parity` and the check
call site in `tools/drift_check.py`, `.gitignore:45-105`, and the prior
artifacts the handoff named.

**Ran:** the generator over all 9 tracked specs, twice, in two throwaway clones;
`drift_check --enforce` in a clone, clean and mutated; the 23 tracked
artifact-guard test files; both generator renderer test files together;
`--help` on 6 commands; four purpose-built probes
(`probe_dropped.py`, `probe_prose.py`, `probe_refarrays.py`,
`proto_check21.py`), all preserved in the session scratchpad.

**Not measured, stated rather than estimated:**

- **Whether Webex treats `PUT …/members` with body `{}` the same as
  `{"members": []}`.** The vendor sentence says what omitting the list means;
  the CLI sends `{}`. Settling it needs a live call against a throwaway device,
  which this session did not make. **`UNKNOWN`, and it is the one open question
  that changes G2's severity.**
- **The 224 UNKNOWN classifications** (§1.5) are unresolved by design — the spec
  does not say. That number is a finding, not a gap in the work.
- **Whether the 130 shape-level collection-replace commands triage to more than
  Phase 5's 42.** Different unit and different stage; I did not re-triage, and I
  explicitly do not present 130 as a corrected 42.
- **Statement coverage of `tools/`.** Phase 7 did not measure it and neither did
  I.
- **The other twelve `-N` numeric-suffix names' semantics.** Counted (42,
  matching `tools/CLAUDE.md`), not individually assessed.

**Handed forward to Phase 8 / the final report:**

1. **G3 is the sequencing constraint for the whole remediation programme**, not
   just for this phase. Any guard any later phase proposes is reversible in
   silence until step 2 lands.
2. **G6 (response-shape blindness) is the one finding here that is not a
   generator defect but a gate-design one**, and it belongs in the final
   report's discussion of what the gate structurally cannot see — beside
   `02-drift.md` F5, which found the request-side half of the same hole.
3. **§5.3's mechanism generalizes**: a human-written reason that excuses both a
   gate check and its human-readable report, with nothing re-verifying the
   reason. That is a different shape from `02-drift.md` F2 (a finding checked,
   disproved, and quieted) and worth naming separately.
4. **Phase 5's 42 collection-replace operations are enumerated nowhere.**
   `05-safety.md` §2.1 names **11** of them in its blast-radius and prose
   tables; a grep of all of `docs/audit/` finds no fuller list. All 11 were
   located in this phase's dataset with the named field and all 11 classify
   COLLECTION-REPLACE — but the remaining 31 cannot be cross-referenced by
   anyone who did not run Phase 5. **The final report should either recover the
   list or stop quoting 42 as a citable set**; it is currently a number without
   an artifact, which is the same failure mode as the 476/142 this phase
   corrected in C1.

---

## 11. Remediation shipped in this phase

Steps 1 and 2 of §9 are **shipped**. Step 3 (the render paths) is deliberately
not started — it was forbidden until 1 and 2 existed, and that constraint was
the point.

### 11.1 The generator's tests are repaired and tracked

`[verified]` Four assertions were rotting in files CI could not see:

| Assertion | Broke on | Fix |
|---|---|---|
| `'@app.command("show")'` ×2, `f'@app.command("{name}")'` ×1 | `751010c` (2026-07-28) added `short_help=` | match the decorator's opening only — an exact-string match on a call the renderer is free to extend is what rotted this file |
| `"print_json(result)" in code` | 2026-07-25, when all six render paths moved onto `_render_output_options` + `emit()` | assert `emit(result` — `emit` **is** the rendering contract now; `print_json` survives only in create's id-extraction branch |

**The same-basename problem is solved by renaming, not by `__init__.py`.**
`tests/tools/test_command_renderer.py` → **`tests/test_command_renderer_dispatch.py`**.
The two files are not duplicates (§3.5): the smaller one holds the only
dispatch-level coverage in the repo, and its new name says so. Adding
`tests/__init__.py` + `tests/tools/__init__.py` would also have worked and was
rejected — it converts `tests/` into a package and changes pytest's module
naming for all 23 previously-tracked root files, which is a large blast radius
to accept for a filename collision.

**Tracked with their fixtures.** `tests/fixtures/mini-openapi.json` (needed by
3 of the 4) and `tests/fixtures/expected_output.py` (needed by
`test_generator_regression.py`) are now tracked too. A tracked test with an
untracked fixture is a red CI job on a fresh clone. This required re-including
`tests/fixtures/` and then re-excluding it — git cannot re-include a file whose
parent directory is excluded — so `tests/fixtures/axl-responses/` stays
ignored, verified in both directions with `git check-ignore --no-index`.

### 11.2 Check 21 — a destructive command carries a confirmation gate

`[verified]` `tools/drift_check.py`, `check_confirm_gates` +
`build_confirm_surface` + `destructive_spec_ops`, wired into the results dict,
the `failed` condition and the report.

Built from `build_cli_surface()` and `load_spec_ops()` — the pair check 1 uses,
whose join is proven by check 1 reporting 0 — and from the generator's own
`classify_real_semantics` and `_request_body_schema`. **No third source of
truth, no re-implemented resolver, no network, no fixture, no import of
`wxcli`.**

**Three design decisions, each with the measurement behind it:**

- **`ast`, not a substring.** A substring test over the dumped function reports
  208 gated commands where the parse tree reports 203 (`05-safety.md` §2),
  over-counting on commands whose *help text* contains the word.
- **Scoped to `real_semantics`.** `device-settings
  create-apply-line-key-template` is gated for **scope**, not destructiveness,
  and the check deliberately does not claim it. Folding the two would make the
  check assert something its name does not say — the failure mode this audit
  named for check 20.
- **Keyed on `command_names`, not `_command_name`.** This is `02-drift.md` F1
  and **it bit this check during development.** `build_cli_surface` emits an
  entry per decorator, so a renamed command appears under both its hidden
  legacy alias and its visible name, while `_command_name` returns only the
  first. Keying on the first left every renamed destructive command looking
  ungated: **the check reported 15 findings on a tree where all 15 were
  correctly gated.** It failed loudly rather than passing silently, which is
  the only reason it was caught. A regression test pins it.

### 11.3 What the check found on day one: the guards were never committed

`[verified]` — and this is the finding, not a footnote.

Check 21 reports **23** findings against `HEAD`. Not because the check is
wrong: because `HEAD` does not contain the gates. The 2026-08-04 remediation —
the renderer change, the overrides and the 23 regenerated command modules —
existed **only in the working tree**. The audit spec's STATUS block recorded it
as *"Remediation already landed (2026-08-04) … the drift gate passes"*. It had
landed on one disk.

`git show HEAD:src/wxcli/commands/cc_aux_code.py | grep -c typer.confirm` → **1**.
The working tree → **2**.

So §3.2's mutation understated the exposure. The gates are not merely
*reversible* in silence — for anyone who cloned this repository at any point in
the last day, they were never there. The renderer and its 23 regenerated
modules are staged with check 21, which is the only way to land the check
green.

### 11.4 Verification

`[verified]` — every row run this session, the last three in a **real fresh
clone** of the staged state (`git clone` + `git archive $(git write-tree)`), not
in the working tree.

| | before | after |
|---|---|---|
| Drift-gate checks | 20 | **21** |
| `drift_check --enforce`, fresh clone | PASS | **PASS**, check 21 = **0** |
| Tracked root test files | 23 | **28** |
| Tracked root tests, fresh clone | 415 passed | **612 passed** |
| Generator tests running in CI | 0 of 187 | **187** |
| Regeneration vs the staged tree | — | **0 of 173 modules differ** |

**Mutation-proven in both directions**, which for a check reporting 0 is the
whole point:

| Tree | check 21 |
|---|---:|
| Staged state | **0** |
| Renderer's `_render_destructive_gate` call sites removed, tree regenerated | **23** |
| …plus one pre-existing DELETE confirm deleted from `call_queue.py` | **24**, naming `call-queue delete` |

The 23 is exactly the `real_semantics` population the 2026-08-04 fix gated; the
24th gate that fix added is the scope case check 21 correctly does not claim.
The third row proves the check also guards the 179 DELETE gates that predate
the audit, per command rather than all-or-nothing.

**And the check body itself is mutation-proven** — three mutations, three
*distinct* failures, control green:

| Mutation of the check | Test that fails |
|---|---|
| key the confirm surface on `_command_name` (the F1 bug) | `TestRenamedCommandsResolveUnderBothNames` (both cases) |
| detect the confirm by substring instead of `ast` | `test_the_word_confirm_in_help_text_is_NOT_a_gate` |
| drop the `real_semantics` scoping (flag every ungated write) | `test_ungated_NON_destructive_op_is_not_a_finding` |

### 11.5 What is staged, and what is not

Staged: `.gitignore`, `tools/drift_check.py`, `tools/command_renderer.py`,
`tools/generate_commands.py`, `tools/field_overrides.yaml`, the 23 regenerated
`src/wxcli/commands/*.py`, `tests/test_field_overrides.py`, the five test files
and the two fixtures.

**Not committed.** The staged set includes another session's uncommitted
generator work, which is the only way check 21 lands green, and that is a call
for the operator rather than for this phase. `docs/architecture/
04-operations-and-evolution.md` is modified and unrelated; it is left alone.
