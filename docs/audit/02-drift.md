# 02 — Drift: regenerate and diff *(Target A only)*

Phase 2 of `docs/arch/wxops-architecture-audit-prompt_2.md`. Extends
`docs/audit/00-facts.md` §5a (which established the gate exists, is 3,899 lines,
and is a blocking CI job) and its *Assumptions I could not confirm* items 1 and 2
(determinism, and whether the gate detects a hand-edit) — **both are now
answered**.

Labels: `[verified]` = I ran it and read the output; `[inferred]` = reasoned from
evidence short of direct observation.

**Baseline.** All measurements in §1–§4 were taken against the working tree at
commit `b578a52`, **before** this session's renderer change. That matters: the
question "has anyone hand-edited generated code?" is a question about the state as
found, not as left. §5 states where the tree stands now.

---

## 1. Regeneration method

`[verified]` The generator writes to `src/wxcli/commands` by default
(`tools/generate_commands.py:20`) but accepts `--output`
(`tools/generate_commands.py:409`), so the full endpoint layer was rendered into a
scratch directory with `src/` untouched:

```
for each spec in PREFERRED_ORDER + the rest:
    PYTHONPATH=. python tools/generate_commands.py --spec specs/<spec> --all --output <tmp>
```

Spec order mirrors `tools/spec_sync.py:25-33` (`PREFERRED_ORDER`), then the two
remaining tracked specs (`webex-broadworks.json`, `webex-wholesale.json`) in the
order `spec_sync` appends them (`spec_sync.py:51-52`). All nine **git-tracked**
specs; the gitignored dev-only `specs/webex-flow-store.json` was excluded, per
`00-facts.md:113`.

Result: **173 generated modules + `_registry.py`**, matching
`len(GENERATED_GROUPS)` = 173 (`00-facts.md` Q4a row c1) exactly. Every spec
exited 0.

## 2. Diff against committed output

`[verified]`

| | count |
|---|---:|
| Generated modules rendered | 173 |
| **Byte-identical to the committed file** | **172** |
| Differ | 1 (`_registry.py` — the manifest, not a command module) |
| Present in regen, absent from `src/` | 0 |
| Present in `src/`, absent from regen | 0 (of the 173 registry entries) |

**No generated command file differs from what the generator produces. There are
zero hand-edits to lose.**

This closes Phase 2's central worry. The audit anticipated "a history of
contradictory flag audits: fixes applied to generated files, reverted by the next
regeneration." **No such fixes are present in the tree.** Whatever caused past
contradictory audits, it was not surviving hand-patches — every correction in this
repo's history appears to have gone through the generator, the overrides file, or
the overlays, as the maintainer rules require (`tools/CLAUDE.md`, *Generator
Rules*).

Item 3 of the Phase 2 brief ("for each difference: what was changed, why someone
probably changed it, what generator or spec deficiency forced a manual fix") is
therefore **vacuous for command modules — there are no differences to explain.**

### The one difference, and why it is not drift

`_registry.py` differs by a single line `[verified]`:

```diff
-    ("cc_ai_assistant", "cc-ai-assistant"),
```

This is an artifact of the method, not a finding. `update_manifest` **upserts**
into an existing manifest (`tools/generate_commands.py:182-197`); rendering into an
empty directory rebuilds it from only what this run emitted. `cc_ai_assistant` is
a **real, tracked, mounted module** carrying one command
(`src/wxcli/commands/cc_ai_assistant.py`, 3,323 bytes) whose upstream tag
`AI Assistant` **is declared by no tracked spec** `[verified]` — so a fresh render
cannot emit it.

It is deliberate and declared: `inert_tag_ack` in `tools/field_overrides.yaml:1294`
records it as *"Dormant by decision, not stale. Upstream REMOVED this tag from the
published CC spec"*, kept so a returning tag rebuilds under the group name already
mounted, and check 15 re-validates the ack. `tools/CLAUDE.md` states the
corresponding rule outright: *"Manifest pruning is manual, by design."*

**Consequence worth carrying forward:** a from-scratch clone + regen produces a
manifest missing one shipping group. That is invisible today because nobody
regenerates into an empty tree — but it means the manifest is the one generated
artifact whose committed state is *not* reproducible from the specs alone.

## 3. Determinism

`[verified]` **Yes — byte-identical.** The full nine-spec render was run twice into
two separate directories and compared with `diff -rq`: **no differences across all
173 files.**

This matters for the audit's own severity model: the Phase 2 brief calls
non-determinism Critical because "you cannot distinguish drift from noise, and no
byte-level gate is possible." That risk does not apply. **A byte-level gate is
possible here** — the generator is a pure function of (specs, overrides, generator
source), at least across two runs in one environment.

Not measured: determinism across Python versions, across machines, or over time
(dict ordering, locale, or a dependency upgrade could each break it). Two runs in
one environment is evidence, not proof.

## 4. Does anything catch a hand-edit to generated code?

**No.** `[verified]` — established two ways, one of them by the checks' own bodies
(see §6, from the check-by-check audit).

The measurement above is itself the demonstration: I had to render into a temp tree
and `cmp` the files by hand, because nothing in the repo does it. Concretely:

- The gate is invoked as `python -m tools.drift_check --enforce`
  (`.github/workflows/ci.yml:128`) and never runs the generator.
- CI has no step that regenerates and diffs (see §6).
- `00-facts.md` §5a inferred this from check names only and correctly declined to
  assert it; it is now confirmed from the bodies.

**Which check a reader might believe covers it, and why it does not:** `check_parity`
(check 1) is the natural candidate — it is the spec↔CLI check, and "parity" reads
like "the CLI matches the spec." It asserts that every non-skipped spec *operation*
has a *command*, i.e. presence at the granularity of a command name. A hand-edited
function *body* — a changed URL, a removed confirm, an inverted default — keeps its
command name and passes check 1 untouched. Several other checks (6, 7, 10, 11a)
compare *docs* against the *built CLI*, which means a hand-edit that changed
behaviour would be treated as the new truth and the docs told to match it.

**So the gate's coverage is: spec ↔ command-name ↔ flag-name ↔ docs. Nothing
anchors the generated function body to the generator.**

---

## 5. State of the tree after this session

`[verified]` This session changed `tools/command_renderer.py`,
`tools/field_overrides.yaml` and `tools/generate_commands.py`, and regenerated 23
command modules from them (documented separately). Re-running the §1 procedure
against the tree as it now stands reproduces **all 173 command modules
byte-identically**, so the property established in §2 still holds: `src/` is
exactly what the generator emits.

---

## 6. What the gate actually asserts, and what it suppresses

Four parallel audits produced the per-check detail, preserved alongside this file:
`02-detail-checks-1-11a.md` (537 lines), `02-detail-checks-10-20.md` (752),
`02-detail-suppressions.md` (285), `02-detail-ci-blindspots.md` (503). **Every
claim below that I label `[verified]` I re-ran myself** — the detail files are the
working papers, not the authority.

**Headline: the gate is strong, actively maintained, and honest about most of its
own limits.** Its 20 checks are mutation-tested, its acks self-revalidate, and
~214 of ~215 suppression entries carry a stated reason that still holds. That is a
real result and it shortens remediation. The findings below are specific defects
in a good instrument, not an indictment of it.

### 6.1 The five findings that matter

**F1 — The gate is blind to 50 commands under the names the docs actually cite.**
`[verified]` — I reproduced this end to end.

Renames ship as two stacked decorators on one function: the hidden legacy alias
first, the visible name second (`src/wxcli/commands/cc_agents.py:247-248`).
`_command_name` (`tools/drift_check.py:502-515`) returns on the **first** decorator
it meets, so it resolves to the **hidden** name. Measured on `cc_agents.list_activities`:

```
decorators      : [('list', hidden=True), ('list-activities', hidden=False)]
_command_name() : 'list'          ← what the surface is keyed on
docs cite       : 'list-activities'
build_flag_surface()['cc-agents']['list-activities'] → None
```

That `None` hits the "skip, not a leaf command" branch, so **checks 6, 9, 10, 11a
and 11b silently pass on all 50 stacked-decorator commands** — not because they are
correct, but because the lookup missed. `check_flags`'s own comment attributes
`real is None` to "a mounted sub-typer"; this is a second, larger, unacknowledged
cause.

**The author knew and fixed it in one place only.** `command_names()`
(`tools/drift_check.py:2133-2160`) returns every name with its hidden flag and
`CommandFacts` explicitly prefers the visible one (`:2177-2179`) — with a docstring
saying `_command_name` is "fine for a resolvable key and wrong for a report an
operator reads." The fix reached checks 13/14 and was never propagated to the five
older callers (`:534, :1270, :1407, :1546, :1766`). This is the repo's own stated
trap: *"a check that reports 0 deserves more suspicion than one reporting many."*

**F2 — A command proven not to work is kept alive by the count check.** `[verified]`

`wxcli cc-ai-assistant create` POSTs to `{cc_base_url}/event`
(`src/wxcli/commands/cc_ai_assistant.py:16,34,52`). The `keep_endpoints` exemption
that shields it (`tools/field_overrides.yaml:1303`) carries, in its own comment, a
live probe **disproving** the endpoint: *"POST .../event -> 404, content-length: 0
… no route is registered upstream for this operation at all,"* recorded in commit
`1ae7eaa` (2026-07-25). The same comment names the correct fix — retire the group —
and states why it was deferred: doing so *"changes the drift baseline from 176
command sets / 1872 commands to 175 / 1871, which this plan's gate is specified to
match exactly."*

Three suppressions hold it in place: `keep_endpoints` (check 1),
`inert_tag_ack: "AI Assistant"` (check 15), and the manual manifest retention this
report found independently in §2. **A coherence gate is the reason a known-dead
command still ships**, because check 3 enforces a published count that removing it
would move. This is the single case in ~215 suppression entries where the record
shows a finding was checked, came back negative, and was quieted rather than acted
on.

**F3 — No check asserts that a destructive command has a guard.** `[verified]` —
grep of `tools/drift_check.py` for `confirm`, `--force`, `rest_delete`, and
`destructive` returns only comments and the hidden-alias helper; no check reads
them.

This has an immediate consequence for the remediation this session landed: **the 24
confirmation gates added on 2026-08-04 are unguarded by the gate.** A future change
to a render path that dropped them would regenerate cleanly, pass all 20 checks, and
ship. The same is true of the 179 pre-existing `DELETE` gates. Any remediation that
adds a guard should add the check that pins it, in the same commit.

**F4 — Check 20 asserts "not invisible", and reports it as "coverage".** `[verified]`

`check_reference_doc_coverage` (`tools/drift_check.py:3530-3531`) passes a group if
`` `<group>` `` **or** `wxcli <group>` appears anywhere in any reference doc text,
with no context requirement. A disambiguation-table row reading "NOT
`contact-center`" therefore satisfies "coverage" for `contact-center`. The
docstring is candid that this is a weak oracle by design; the result key
(`20_groups_without_a_reference_doc`) and the report line ("no docs/reference/
coverage") are not.

**F5 — Check 19 cannot see a field's type change, or any response-schema change.**
`[verified]` — `encode_field(required, desc, enum)` (`tools/drift_check.py:3162`)
takes no type parameter and encodes none.

So a spec revision changing a field from `string` to `integer`, with description,
requiredness and enum unchanged, produces **zero diff — not even the advisory
line.** Check 19 is also request-side only and compares `tags[0]` only, so a
secondary-tag change on a multi-tagged operation is invisible too. Given that check
19 exists precisely because three meaning-changes shipped green on 2026-08-03, the
gap is worth naming rather than assuming covered.

### 6.2 What the gate structurally cannot see

Mechanism, not opinion — from `02-detail-ci-blindspots.md`:

| Blind spot | Why, structurally |
|---|---|
| **Runtime behaviour** | The gate parses source with `ast` and never executes a command. Any defect that only appears when a request is issued is out of reach by construction. |
| **The entire migration subsystem** | `src/wxcli/migration/` is ~46.7k hand-written lines and is almost untouched by any check — the gate's oracles are the specs and the generated modules, and Target B has neither. |
| **A spec that is self-consistent but wrong about the live API** | Every check compares spec ↔ CLI ↔ docs. All three are downstream of the same spec, so a spec that misdescribes reality is coherent with itself and passes. |
| **Whether a destructive command is guarded** | F3. |
| **Gitignored modules** | Deliberately skipped so a fresh clone reproduces the counts — which also means nothing about the 11 `fs_*` dev modules is ever checked. |

### 6.3 The suppression surface

~215 entries audited across `drift_check_allowlist.txt` (31), `naming_ack` (167 —
**not** the 171 `tools/CLAUDE.md` prose claims; 4 were legitimately retired as
commands were fixed), `spec_authority` (7), `verb_semantics_ack` (6),
`undeclared_paging_ack` (2), `inert_tag_ack` (1), `keep_endpoints` (1).

**~214 of ~215 are deliberate, with stated reasons that still hold and a staleness
re-check that would fail if they rotted.** The one exception is F2. Two smaller
notes:

- `verb_semantics_ack`'s re-validation lives in `tests/test_field_overrides.py`,
  while its four imitators self-check inside `drift_check.py` (checks 9, 12, 15,
  16). Both are real and currently green — an architectural split, not a hole, but
  it makes `verb_semantics_ack` the one ack whose guard disappears if someone runs
  the gate without the test suite.
- Two bare, non-file-scoped entries remain in `drift_check_allowlist.txt` (`trunk`,
  `route-group`) — the exact shape whose narrowing to a file-scoped `ref` form the
  file's own header records as a past fix (commit `0cccca8`). Currently harmless
  (neither is a registered group), but the capability that caused that incident was
  narrowed for one instance rather than removed.

### 6.4 CI wiring

`[verified]` by the detail agent, spot-checked here. The `drift-gate` job runs
`python -m tools.drift_check --enforce` under `set +e` with `pipefail`
(`.github/workflows/ci.yml:128-133`), treats **exit 2 as *crashed, did not run***
rather than *found nothing*, and asserts the last check completed — a control added
after a crash exit code was indistinguishable from a clean run. That is unusually
careful and it works.

Two gaps: **nothing in CI regenerates and diffs** (the §4 finding, now confirmed
from the workflow files, not inferred), and `pytest`, `pytest-asyncio` and
`aioresponses` are installed by hand in the workflow because they are declared in
no `pyproject.toml`, so a contributor's local run and CI's are not the same
environment.

### 6.5 Direct answers to Phase 2 items 5 and 6

**Item 5 — does anything catch a hand-edit to generated code?** No. Confirmed from
the bodies of all 20 checks across both detail reports; the closest candidate,
`check_inert_overrides`, resolves tag→command-name sets in memory and never reads
file content. The check a reader would wrongly trust is `check_parity`, for the
reason given in §4.

**Item 6 — is the allowlist where this gate went to die?** **No** — and that is the
most useful thing this phase establishes. One quieted finding in ~215 entries, with
the disproving evidence recorded in the file rather than hidden. The gate's real
weaknesses are not its exemptions; they are **F1 (a shared helper that silently
mis-keys five checks)** and **F3/F5 (dimensions never checked at all)**.
