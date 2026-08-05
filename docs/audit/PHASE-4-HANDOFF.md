# Handoff prompt — PHASE 4 (generator) + PHASE 3 item 4

Paste everything below the line into a new Claude Code chat.

**Why these are one session.** The audit spec compresses PHASE 3 to item 4 only —
"which commands hide a scope control in an array-typed field" — and that is not a
separate question from PHASE 4's central hunt. It is *one instance* of it: the
generator silently drops array-typed body fields, so any scope control that is a
list is unreachable except through `--json-body` and invisible in `--help`. Auditing
the render paths and enumerating the array-field casualties is the same pass over
the same code. Run them together.

---

Continue an architectural audit of the wxops repository at
/Users/ahobgood/Documents/webexCalling. Run PHASE 4 (generator half) and PHASE 3
item 4 as one session, then stop.

## Read these first, in this order

1. `docs/arch/wxops-architecture-audit-prompt_2.md` — the audit spec.
   Read STATUS (top), ROLE, KNOWN CONTEXT, HARD CONSTRAINTS, **HOW TO RUN items 6
   and 7** (they define this session's scope and say what was cut), PHASE 4, and
   PHASE 3 item 4. Skip the other phases.
2. `docs/audit/00-facts.md` — the NUMERIC AUTHORITY. Do not re-derive its counts.
   §5c on `spec_semantics.json` is the one you most need and most must not re-ask.
3. `docs/audit/05-safety.md` **§2.1 and §2.5 — READ THESE BEFORE ANYTHING ELSE IN
   THIS SESSION.** Phase 5 finished after this handoff was drafted and it did not
   leave you leftovers; **it handed you this phase's two best leads, already
   measured.** See *What Phase 5 already found for you*, below. Skipping them means
   re-deriving 42 operations and a `command_renderer.py` line number from scratch.
4. `docs/audit/02-drift.md` — Phase 2, **the direct predecessor.** Read in full,
   especially §6 (the gate's five findings) and F3.
5. `docs/audit/07-testability.md` **§3** — Target A's testability. It establishes
   that this session's subject has no CI coverage at all, and that changes what a
   valid finding looks like here (see *The constraint*, below).

Consult as needed, do not read cover to cover: the four `docs/audit/02-detail-*.md`
working papers, `tools/CLAUDE.md` (1,329 lines — the generator's own design record),
`docs/audit/00-context.md` Q1 and Q2.

## Your task

Write `docs/audit/04-generator.md`. **Target A only** — this session does not touch
`src/wxcli/migration/`.

## The spec half is CUT. Do not re-open it.

`tools/spec_semantics.json` carries **no consequence dimension** — it encodes shape
and change-detection (required-ness, id kind, description drift, enum values), not
"does this destroy something, how much can it touch, can it be undone."
**The generator computes consequence anyway**, in `classify_real_semantics`
(`tools/postman_parser.py:107`). `00-facts.md` §5c settled this. Do **not** re-ask
"does semantic metadata exist" — conflating a change-detection snapshot with
consequence metadata is named in the spec as the worst error available in this audit.

## The premise of this session

Phase 2 measured that the generated output is **reproducible** and **matches what is
committed**. **That is coherence, not correctness.** A generator can deterministically
emit the wrong thing for every endpoint and the drift gate will report PASS the whole
time, because spec, CLI and docs are all downstream of the same generator.

**The evidence says this is where the defects actually are. Both real defects found
so far are generator defects, and neither was found by a generator phase:**

1. **The confirmation gate was emitted only from `_render_delete_command`**, keyed on
   the HTTP verb, while `real_semantics` sat unread beside it — one render path,
   wrong, **× 23 commands**. Found in Phase 0 (scope), not Phase 4. Now fixed.
2. **Array-typed body fields are silently dropped from the flag surface**, so any
   scope control that is a list is unreachable except through `--json-body` and
   invisible in `--help` — **× 142 commands / 476 fields**. Found by hand, not by a
   phase. Not fixed.

**Assume there are more of this shape and go looking deliberately.** That is the
job. Both fit the severity model exactly: one defect in the generator times the whole
generated surface.

## What Phase 5 already found for you — these are leads, not leftovers

Phase 5 ran the "which of the 755 ungated writes actually destroy state" question to
ground and landed both halves of the answer **inside the generator**. Its two Critical
Target A findings (`05-safety.md` §2.8, rows A1 and A2) are this session's starting
point:

- **A1 — 42 ungated PUT/PATCH operations replace a collection by omission**
  `[verified]`. Four of them say so in vendor prose; the hazard is documented in
  `migration/execute/handlers.py:2270` for four migration types **and nowhere on the
  generated surface**. §2.1 shows the classification work — a member-vocabulary /
  id-bearing-items heuristic narrowing 91 candidates to 42 at 49–54% precision.
  **Your job is not to re-derive the 42.** It is the sentence after: this is *a render-
  path gap × 42 operations, and the classifier that would have to change is one
  function.* Name the function, say what it must compute, and say whether the spec
  carries enough to compute it — that is Phase 4's KEY QUESTION applied to a concrete
  class.
- **A2 — the array/object drop has a single line number: `command_renderer.py:1621`**
  `[verified]`. Every one of the 42 hazardous fields, and every array-typed scope
  control, is invisible in `--help` because of it. **Two commands are left with zero
  scalar flags at all.** This is the same defect the audit spec cites at HOW TO RUN
  item 7 (476 fields / 142 commands), now with a confirmed anchor.

Note that `:1621` is *one* of **13 sites** where the same `field_type in ("object",
"array")` idiom appears (list below). Phase 5 anchored the one that matters for A1;
**establishing whether the other twelve agree with it is squarely this session's
work**, and is the shape of defect this phase exists to find.

## The hunt — start here

`[verified 2026-08-05]` `tools/command_renderer.py` is **2,240 lines** and has **six
command-shape render paths**, dispatched by `render_command_file` (`:2178`):

| Renderer | Line |
|---|---:|
| `_render_list_command` | 1229 |
| `_render_show_command` | 1393 |
| `_render_create_command` | 1495 |
| `_render_update_command` | 1598 |
| `_render_delete_command` | 1870 |
| `_render_action_command` | 1998 |

Plus the shared helpers each of them calls: `_render_query_params` (`:1060`),
`_render_path_arguments` (`:944`), `_render_docstring` (`:439`), `_render_example`
(`:1001`), `_render_url_expr` (`:282`), `_render_error_handler` (`:320`),
`_render_output_options` (`:195`), `_render_force_option` (`:1812`),
`_render_destructive_gate` (`:1819`), `_render_auto_inject_params` (`:336`),
`_render_path_inject` (`:346`), `_render_create_id_extraction` (`:1451`).

**For each of the six: what does it silently drop, and what does it emit that the
others do not?** A difference between two renderers is either deliberate (say why)
or it is a defect × the size of that renderer's share of the surface.

**The array/object drop is not one branch — it is a repeated idiom at 13 sites**
`[verified]`: `command_renderer.py:974, 982, 1041, 1122, 1544, 1613, 1621, 1662,
1677, 1897, 1944, 2010, 2035`. It appears in **every one of the six** command
renderers plus the query-param and path-argument helpers. That is the shape to look
for: a rule applied by copy rather than by a single chokepoint. **Ask what else is
implemented as a repeated idiom rather than a single function**, because that is
where two of the thirteen will eventually disagree.

`_render_destructive_gate` (`:1819`) and `_render_force_option` (`:1812`) are the
2026-08-04 fix for defect 1. **They are new, uncommitted, and unaudited.** Read them
as changed code. Confirm they are called from every renderer that can be destructive,
not just from `_render_delete_command` — that was the original bug, and a partial fix
would reproduce it.

## PHASE 3 item 4, folded in

**142 commands / 476 fields** carry a body field the flag surface drops. Enumerate
them, then **judge which are scope controls and which are payloads.** A dropped
`members` array on a create is a payload — annoying, expressible via `--json-body`.
A dropped `locationIds` is a *scope control* whose omission means the entire org, and
that is a different severity.

The confirmed case: `device-settings create-apply-line-key-template` has a
`locationIds` array; omitting it applies the template to every location in the org.
It gained a help note on 2026-08-04. **Find the others.** `00-context.md` Q1 classes
3 and 4 (async job endpoints, bulk-array writes) are where to look first.

Deliverable for this item: a table of every array/object field the generator drops,
classified scope-control vs payload, with the command count per class. Counted, not
estimated.

## The remaining PHASE 4 questions

- **Which spec-refresh tool is live and which is vestigial?** `tools/update-specs.py`
  (133 lines), `tools/spec_sync.py` (78), `tools/postman_spec_diff.py` (157),
  `tools/spec_overlay.py` (106) all exist. Establish which runs, which is dead, and
  what a `chore(specs)` commit actually does — read one (`2a89ea4`, `a898c76`) and
  describe what a human is asked to review.
- **How would anyone detect that Webex changed a response shape?** Note that
  `07-testability.md` §3.6 established there is no intermediate model — Webex's
  response schema *is* the CLI's output schema, and `--fields` is a JMESPath
  expression over upstream field names. So a shape change is a breaking CLI change
  with nothing in between. Does the refresh process surface that, or only parameter
  changes?
- **Is endpoint→renderer selection driven by spec metadata or by pattern-matching on
  names and paths?** Name-based dispatch is fragile and worth flagging. `verb_naming.py`
  (301 lines) is where naming logic may or may not be concentrated — establish whether
  it is one function or scattered.
- **What does the generator do with an endpoint it does not understand?** 154
  operations are deliberately skipped and enumerated in the generated
  `docs/arch/deliberate-gaps.md`. Is the skip loud, and is the enumeration
  trustworthy — i.e. would an accidentally-dropped operation land in that file
  looking deliberate?
- **Is the generator reproducible by a contributor, or does it depend on local
  state?** Phase 2 proved determinism on this machine. `specs/webex-flow-store.json`
  is gitignored, and 11 `src/wxcli/commands/fs_*.py` modules are dev-only — establish
  what a fresh clone can and cannot regenerate.
- **THE KEY QUESTION, and the one the final report needs:** to add scope guards,
  confirmation gates, or dry-run to destructive operations, **what must change — the
  spec, the templates, or both? Give the concrete path.** `_render_destructive_gate`
  is the worked example of "the templates can do it"; say what the ceiling is.

## The constraint Phase 7 puts on every fix you propose

`02-drift.md` F3: **no gate check asserts that a destructive command has a guard**,
so the 24 confirms added on 2026-08-04 are unpinned — a render-path change would drop
them and ship green. Phase 7 measured this one level deeper:

- **All four of the generator's test files are untracked and absent from CI**
  `[verified]`: `tests/test_command_renderer.py` (1,397 LOC, 134 tests),
  `tests/tools/test_command_renderer.py` (372 LOC, 20 tests — **3 currently failing**),
  `tests/test_generate_commands.py` (29 tests), `tests/test_generator_regression.py`
  (4 tests). That is 187 tests over the component whose defects multiply by the whole
  generated surface, **none of which runs on a PR.**
- `tests/tools/test_command_renderer.py` has been red since `751010c` (2026-07-28)
  because the renderer gained `short_help=` and an exact-string assertion was never
  updated. Its 1,397-line sibling *was* updated. **Two files, same basename, one
  maintained, one rotting, neither visible to CI.** Deciding which survives is a
  prerequisite to tracking either.
- The generated command layer is **12% statement-covered** by tracked tests. Per the
  severity model that is the least interesting number available — generated output is
  a shadow. The number that matters is the one above it.

**So: any guard you propose must ship with the check that pins it, and that check
must live in a git-tracked file.** Read `.gitignore:58-100` — the maintainer has been
promoting test files individually as each proves it caught real drift, with the reason
written in a comment. Follow that convention; do not propose a blanket `!tests/**`.

## Repo-specific constraints — these will bite you otherwise

- **The interpreter is `/opt/homebrew/opt/python@3.14/bin/python3.14`.** Bare
  `python3` is the system 3.9 and cannot import `wxcli`. `head -1 "$(which wxcli)"`
  prints the right one.
- **`wxcli` CANNOT be imported from Python.** A hook blocks it, matching on the
  *string* `import wxcli` anywhere in a Bash command — it will fire on an unrelated
  one-liner. Parse with `ast` (the generator's output is designed for it), or run
  `wxcli <cmd> --help` as a subprocess. Set `COLUMNS=400`.
- **Never run a mutating `wxcli` command.** This repo points at a live org and
  `~/.wxcli/config.json` holds a working token.
- **Running the generator is safe and is how this phase gets its evidence** — it reads
  specs and writes files, it makes no network call. Phase 2 ran it twice. **Do it in a
  throwaway clone** (`git clone --no-hardlinks . <scratch>`), never in the working
  tree, which is carrying uncommitted generator changes.
- **Do not run the full pytest suite in the working tree** (project rule). Targeted
  files are fine. Baseline in a clean clone at `b578a52` is **3,580 passed, drift gate
  PASS**.
- **Count git-tracked files, never the working disk** (`git ls-files`,
  `git check-ignore --no-index -v`). This has produced wrong counts in four phases,
  including a denominator error Phase 7 corrected.
- **`docs/audit/` and `docs/arch/` are untracked/gitignored.** Do not assume a prior
  artifact is committed.
- **The working tree is NOT at `b578a52`.** 28 tracked files are modified, and **four
  of them are this session's subject**: `tools/command_renderer.py`,
  `tools/generate_commands.py`, `tools/field_overrides.yaml`,
  `tests/test_field_overrides.py` — plus 23 regenerated command modules. All
  uncommitted, all unaudited. **Read `tools/command_renderer.py` as changed code, not
  as a fixed point**, and `git diff` it before drawing any conclusion about it.
- Subagents work well here and this phase parallelises cleanly (one per render path).
  Use Sonnet or better — never Haiku. Give each agent the constraints above verbatim;
  they do not inherit them.

## Established — do not re-litigate

- **Target A is CLEAN on drift.** All 172 generated modules regenerate
  byte-identical; the generator is deterministic across two full runs; there are
  **zero hand-edits** to generated code. The "fixes reverted by the next
  regeneration" hypothesis is FALSE. Stop looking for it.
- **Nothing detects a hand-edit to generated code.** `check_parity` is the check a
  reader wrongly assumes covers it — it asserts only that every spec operation has a
  command, so an edited function body passes untouched.
- `_registry.py` is the one generated artifact **not reproducible from the specs
  alone** — it retains `cc_ai_assistant`, whose upstream tag Cisco deleted.
  Deliberate, acked at `tools/field_overrides.yaml:1294`, manual by design.
- The 50 `hidden=True` command names are backward-compat **aliases** on functions that
  also carry a visible name. **Zero capabilities are hidden-only.**
- "Is DELETE the right proxy for destructive?" is **ANSWERED: no.** 199 destructive
  operations, 176 DELETE and 23 not; the 23 plus one scope case are now gated, so
  "779 ungated writes" is now **755**. The follow-up — which of the 755 destroy state
  via collection-replacing PUTs — **was answered by Phase 5: 42 operations**
  (`05-safety.md` §2.1). Do not re-derive them; act on them.
- **Phase 5 also measured that a confirm without a TTY fails safe**, overturning the
  spec's premise that it might read as an unrelated error (§2.2), and that **328 of
  the 755 are dry-run-emissible today with machinery already written** (§2.5). Both
  bear directly on the KEY QUESTION below — read them before answering it.
- The drift gate's allowlist is NOT where findings went to die: 214 of ~215
  suppression entries are deliberate with reasons that still hold.
- Gate finding F1: `_command_name` (`drift_check.py:502`) resolves to the HIDDEN
  alias, so checks 6/9/10/11a/11b silently skip 50 renamed commands.

## Rules

Every finding cites `path:line`. Label claims `[verified]` (you ran or parsed
something) or `[inferred]`. `UNKNOWN` is a correct answer. Never report a section
clean unless you read it; state read coverage. Do not estimate LOC, effort, or
percentages unless you counted — say "did not measure." **Never propose a fix to a
generated file** — trace it to the spec, generator, or template (HARD CONSTRAINT 5);
check `_registry.py` first, since 19 modules in `src/wxcli/commands/` are not
generated. **A finding that proposes something the gate already enforces is a false
finding and counts against you.** Disagree where warranted, including with the audit
spec and with prior phases — six of their claims have now been overturned.

Remediation rule: a finding may be fixed immediately ONLY if its root cause is
proven, its fix is in `migration/` or **the generator**, and no later phase would
teach you more. This phase's subject **is** the generator, so more will qualify here
than anywhere else — but every fix must ship with the tracked check that pins it, per
*The constraint* above, and must be recorded in the spec's STATUS block with every
count it moves. Regenerate and diff before and after; a fix that changes output for
commands you did not intend to touch is a finding about the fix.

Stop after writing `docs/audit/04-generator.md`. **Phase 5 is already done**
(`docs/audit/05-safety.md`) — do not re-run it. Do not begin Phase 8 or the final
report.
