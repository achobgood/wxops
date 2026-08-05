# Audit: drift_check.py lines 1700–3899 (checks 10–20 + main())

Scope note: check_positionals's def is actually at line 1678 (before the 1700
boundary) — flagged in the task itself as needing verification. I read it in
full since the task explicitly assigned it to me. All other assigned checks
fall entirely within 1700–3899.

**Canonical check numbers** (settled from `main()`'s `results` dict keys,
`drift_check.py:3594-3630`, not from section-header comments, which are sparser
than the numbering — see the "source hygiene" note at the end):

| Function | Check # | path:line |
|---|---|---|
| `check_positionals` | 10 | `tools/drift_check.py:1678` |
| `check_arg_kinds` (+ `parse_module_arg_kinds:1749`, `build_arg_kind_surface:1793`, `_tokens:1818`) | 11b | `tools/drift_check.py:1829` |
| `check_naming` (+ `build_naming_findings:1930`) | 12 | `tools/drift_check.py:1952` |
| `check_generated_help` | 13 & 14 (one pass) | `tools/drift_check.py:2337` |
| `check_inert_overrides` | 15 | `tools/drift_check.py:2681` |
| `check_undeclared_paging` | 16 | `tools/drift_check.py:2849` |
| `check_registry_counts` | 17 | `tools/drift_check.py:2630` |
| `check_reference_doc_shape` | 18 | `tools/drift_check.py:3010` |
| `check_spec_semantics` (+ `spec_semantics:3248`, `diff_spec_semantics:3350`) | 19 | `tools/drift_check.py:3415` |
| `check_reference_doc_coverage` | 20 | `tools/drift_check.py:3490` |

---

## Check 10 — `check_positionals` (`tools/drift_check.py:1678`, header comment
at `:1356`)

**Name implies:** documented `wxcli` example invocations supply the same
*number* of positional arguments the command actually declares.

**Actually asserts** `[verified]`: for every doc invocation resolved by
`doc_invocations()` (`:1630`, a shared walk also used by check 11b — see
below), it tokenizes the example with `split_doc_positionals()` (a **pre-1700
helper, `:1475`**, read because check 10 depends on it directly), counts
non-flag tokens, and compares against `(need, total)` positional counts pulled
from the AST-derived signature (`positional_surface`). It buckets into
`too_many` / `too_few` / `positional_on_zero_arg`, vs. a separate,
never-failing `bare_count` for zero-argument bare citations outside a fenced
block.

**Is the assertion weaker than the name implies?** Yes, in two verified,
deliberate ways baked into the helper it depends on:

1. `split_doc_positionals` (`:1494-1498`) treats **any token starting with `[`
   or ending with `]`** as usage-synopsis notation and drops it; if a bracket
   is opened but never closed (`unbalanced=True`), `check_positionals`
   (`:1717-1718`) **skips the entire example — not a pass, not a fail, just
   invisible**. A doc author who writes a truncated bracketed synopsis
   (`[--format jsonl|json-per-file]`-style) gets zero coverage from this check,
   silently.
2. `split_doc_positionals` (`:1499-1508`) applies a **guessing heuristic** for
   any flag token it doesn't recognize on the cited command: "an unknown long
   flag takes a value" (`takes = True` at `:1508`) unless the flag is known
   globally boolean. If a doc cites a real but *unlisted-on-this-command*
   boolean flag, the heuristic wrongly consumes the next token as that flag's
   value instead of counting it as a positional — a real `too_many`/`too_few`
   defect could be swallowed as a false negative. This is inherited risk from
   a helper outside my assigned range, but it directly bounds what check 10
   can detect, so I'm flagging it here.

Both are documented behavior (the docstring at `:1479-1483` calls out the
bracket-notation skip explicitly), so this is "check 10 is narrower than its
name suggests" rather than an undocumented bug — but a reader expecting "every
malformed positional-count example fails" should know these two carve-outs
exist.

**Gated or advisory:** Fully gated. `bad_positionals` feeds `failed` at
`:3635`. The separate `bare_count` (bare `wxcli x y` with **zero** args, cited
with single backticks **outside** a fenced block) is explicitly "not a broken
example" and is only ever reported as a count (`10_bare_name_citations`,
`:3607`), never gated — this is a genuine second, softer tier, just not named
"advisory" in the code.

**Allowlist consulted:** `load_allowlist()` (`:776`, pre-1700 helper), keyed
three ways at `:1712-1713`: bare `group`, `"group command"`, or
`"positional {rel} {group} {command}"` (file-scoped). The docstring
(`:1707-1711`) is explicit that this key is a *different claim* from check 2's
`ref` key — sharing one key would let either check silence the other.

---

## Check 11b — `check_arg_kinds` (`tools/drift_check.py:1829`), with
`parse_module_arg_kinds` (`:1749`), `build_arg_kind_surface` (`:1793`),
`_tokens` (`:1818`)

**Name implies:** a documented example's positional placeholder (e.g.
`LOCATION_ID`) names the same kind of Webex object the argument actually is.

**Actually asserts** `[verified]`, three-tier, by design (docstring
`:1831-1848`):
- **Tier 1 (`mismatches`, GATED):** the argument's `--help` text carries an
  explicit `Webex <KIND> id` kind (parsed via `ARG_KIND` regex at `:1744` from
  the rendered help string), the doc placeholder's underscore-split tokens
  (`_tokens`, `:1818-1826`, with `KIND_SYNONYMS` folding at `:1811-1815`)
  positively name a **different**, known kind, and the argument is not in the
  `suspect` set (see below). Anything that doesn't map to a known kind at all
  is dropped as UNDECIDED (`:1892-1894`) — never gated.
- **Tier 2 (`advisories`, NEVER GATED):** the argument is a bare `UUID` with no
  stated kind but *does* have a known producer command; if the placeholder
  matches a **sibling** command name in the same group instead of the
  producer, it's reported as a heuristic-only advisory (`:1901-1915`).
- **Tier 3 (`mislabelled_args`):** the `suspect` set itself — arguments whose
  **own parameter name** contradicts their declared kind (e.g. `location_id`
  typed `Webex PEOPLE id`, computed at `:1860-1864`). Reported for visibility
  but **excluded from tier 1** so a doc that correctly used the *parameter
  name's* kind isn't flagged as wrong when the *label* is the actual defect.

**Is the assertion weaker than the name implies?** Two things worth flagging
precisely:
1. **`mislabelled_args` (tier 3) is not gated at all**, despite being a
   genuine, mechanically-detected CLI defect (a help string whose stated kind
   contradicts its own parameter name). It's reported every run
   (`11b_mislabelled_arguments` in `results`, `:3612`) but **absent from the
   `failed` boolean** (`:3631-3641`) — confirmed by its absence from that
   `or`-chain. A reader of the name "check_arg_kinds" would reasonably expect
   a detected CLI-side kind/label contradiction to fail the build; it does
   not, ever. (Tier 1/2 are explicitly documented as differently-gated in the
   docstring; tier 3's exclusion from `failed` is not restated there or in
   `tools/CLAUDE.md`'s "Check 11b" section — it has to be read off `main()`.)
2. Tier 1 only fires when the doc placeholder **positively names a different,
   known kind** (`:1892-1894` — `if not named: continue`). A placeholder using
   an idiosyncratic or unrecognized abbreviation for the *correct* kind, or a
   generic placeholder like `ID`/`UUID`/`RESOURCE_ID`, is silently UNDECIDED
   and never reaches tier 1 or tier 2 — this is by design (documented as
   avoiding false positives on "naming-convention gaps"), but it does mean the
   check's real coverage is bounded by the `known_kinds` vocabulary harvested
   from the CLI's own help strings (`:1850-1851`), not by any independent
   notion of correctness.

**Allowlist/exemption:** general `load_allowlist()` again, keyed
`group` / `"group command"` / `"arg-kind {rel} {group} {command}"`
(`:1874-1875`) — same file-scoping discipline as check 10's positional key.
No YAML ack list backs tier 3 (`mislabelled_args`); it's derived purely from
the `suspect` set computed each run, so it can't rot into a stale allowlist,
but it also can't be formally acknowledged/reviewed — it's a permanent,
always-on, never-gated advisory line.

---

## Check 12 — `check_naming` (`tools/drift_check.py:1952`) with
`build_naming_findings` (`:1930`)

**Name implies:** every generated command's name is a fair/obvious reading of
what it does.

**Actually asserts** `[verified]`: it does not compute naming judgments itself
— `build_naming_findings` calls out to an **external module**,
`verb_naming.parse_module` / `verb_naming.numeric_suffix_findings` /
`verb_naming.resource_mismatch_findings` (`:1946-1949`), which is outside my
assigned range (not read here — flagged as `UNKNOWN` provenance beyond what
the docstring states). `check_naming` itself only does bucketing/ack
validation over whatever `verb_naming` classifies:
- `GATED_SEVERITIES = ("CRITICAL", "HIGH")` (`:1927`) — findings at these
  severities either need an ack (`naming_ack` in `field_overrides.yaml`,
  looked up by key `f"{kind} {op}"`, `:1976-1994`) or land in `unacked`
  (gated). An ack is invalidated (→ `stale`, gated) if the acked `command` no
  longer matches the live citation (renamed) or the acked `severity` no longer
  matches the live classification (reclassified) — `:1988-1994`.
- Anything **not** CRITICAL/HIGH (i.e. MEDIUM) is unconditionally routed to
  `advisory` (`:1978-1980`) and can never fail the build, regardless of what
  `verb_naming` says about it.
- A **numeric-suffix finding always fails regardless of severity** per the
  docstring (`:1964-1965`) — but I could not verify this claim from
  `check_naming`'s own code: the function only branches on
  `f["severity"] not in GATED_SEVERITIES` (`:1978`). If `verb_naming` assigns
  numeric-suffix findings a severity outside CRITICAL/HIGH, this function
  would route them to `advisory`, not fail them — I did not read
  `verb_naming.py` to confirm what severity it assigns them. **This is the one
  place in my range where the docstring's claim outruns what I can verify from
  the code actually in scope; flagged as `UNKNOWN`, not asserted either way.**

**Is the assertion weaker than the name implies?** The MEDIUM-severity
`advisory` tier is the clean instance of the pattern: `check_naming`'s name
suggests it enforces good naming; in fact anything the naming detector itself
rates below HIGH is **never enforced**, only reported (`12_naming_advisory`,
`:3615`, absent from `failed`). The docstring is candid about this being a
deliberate threshold (`:1960-1965`), so it's a documented narrowing, not a
silent one — but the actual gate surface is strictly the CRITICAL+HIGH subset
of whatever `verb_naming` finds, nothing else, and I can't corroborate the
"numeric suffix always fails" claim from code in my range.

**Gated:** `naming_unacked` and `naming_stale` (both gate, `:3636`).
**Advisory:** `naming_advisory` (MEDIUM tier, never gates).

**Ack list:** `naming_ack` (`field_overrides.yaml`, via
`overrides.get("naming_ack")`, main `:3585`), keyed `"<kind> <METHOD /path>"`,
carrying `command` + `severity` — re-validated both directions (an ack for a
finding that's no longer live is itself reported `stale`, `:1995-2002`),
matching the `verb_semantics_ack` pattern the project's own docs hold up as
the model.

---

## Checks 13 & 14 — `check_generated_help` (`tools/drift_check.py:2337`), one
shared pass over `CommandFacts` (`:2163`), `parse_module_facts` (`:2298`),
`skeleton_lies` (`:2309`)

**Name/section implies:** every generated command's printed `Example:` line
(13) and `--generate-json-body` skeleton (14) actually works / doesn't lie
about shape.

**Actually asserts** `[verified]`:
- Both checks are restricted to an operation only when **every spec that
  declares it agrees** on required body/query fields (`:2393-2395`,
  `per_spec` dedup) — if two tracked specs disagree, the operation is
  **silently skipped from both checks**, no finding either way. This mirrors
  check 9's known spec-union defect class but here it's a deliberate "never
  guess" `continue`, not a union — still means a genuinely disagreeing spec
  pair gets **zero coverage** from 13/14 for that operation.
- **Check 14** (`:2400-2435`): only runs if a `_BODY_SKELETON_<CMD>` constant
  exists in the module source *and* the JSON-parses. Reports three finding
  kinds: `skeleton-not-parseable` (the string literal itself doesn't parse as
  JSON — a real defect, deliberately not skipped, `:2409-2419`),
  `nested-object-as-scalar` (an object/array field flattened to a scalar
  placeholder, via `skeleton_lies`), and `required-field-omitted` (a
  spec-required body field simply absent from the skeleton dict). It does
  **not** check optional fields at all, and does not check query-parameter
  skeletons (there's no such artifact for query params) — scope is
  request-body only.
- **Check 13** (`:2437-2483`): only fires when the command has an `Example:`
  line **and** (required body fields **or** required query fields) **and**
  `not cf.opaque_writes` (`:2442`) — a command whose body/query writes the
  parser can't statically resolve to a constant key is **excluded entirely**,
  not flagged. It tokenizes the printed example and checks whether every
  spec-required body field is reachable (`cf.body_from`) or, if the example
  passes an **inline literal** `--json-body '{...}'`, whether that literal
  dict contains every required field (`:2470-2472`). If `--json-body` is used
  but the payload is **not** a bare single-quoted inline JSON literal (e.g. a
  `file://` reference, a shell variable, or `-` for stdin), the check
  `continue`s at `:2463` — **that example is completely unverifiable and
  silently passes**, regardless of whether the referenced file/stdin content
  would actually satisfy the required fields.

**Is the assertion weaker than the name implies?** Yes, precisely at that last
point: "checks that a generated Example works" reads as "verifies the example
is runnable"; in fact any example using `--json-body file://...` or
`--json-body -` (rather than an inline `'{...}'` literal) gets **no
verification at all** — it's treated the same as "nothing to judge"
(`:2463`), not flagged, not counted, not distinguished from a passing case.
Given the docstring's own history lesson two paragraphs above it
(`:2450-2458`, the 2026-07-28 fix for exactly this shape of "escape hatch
wider than the evidence") this specific gap (non-literal `--json-body`
sources) reads as the same category of blind spot that check already got
burned by once, just not yet closed for this sub-case. `[verified]` from the
code; I have not verified whether any *currently shipping* example actually
uses a non-literal `--json-body` form (that would require grepping every
generated `Example:` line, which is beyond this audit's scope) — so the
practical impact is `UNKNOWN`, the code-level gap is `verified`.

**Gated/advisory:** No advisory tier for either check — `bad_examples` (13)
and `bad_skeletons` (14) both gate unconditionally (`:3637`). `fs_audit` is a
reported-always structural self-check (asserting the dev-only `fs_*` module
exclusion actually holds); only its `leaked` key gates (`:3637`,
`fs_audit["leaked"]`), the `declared`/`present_on_disk` counts are pure
reporting.

**Exemption:** none via YAML ack — the "never guess" spec-disagreement skip
(`:2393-2395`) and the opaque-writes skip (`:2442`) are the only escape
hatches, both structural/computed rather than a maintained allowlist.

---

## Check 15 — `check_inert_overrides` (`tools/drift_check.py:2681`)

**Name implies:** every entry in `field_overrides.yaml` actually takes effect
somewhere in the generated CLI.

**Actually asserts** `[verified]`: it re-derives, from the generator's own
imported resolvers (`tools.generate_commands`, `tools.openapi_parser`,
`tools.postman_parser` — imported, not reimplemented, `:2730-2737`), which
tags each spec on disk resolves to after merge/skip, then checks two distinct
things: (a) **TAG-keyed** — a top-level block, a `tag_overrides` entry, or a
`cli_name_overrides` entry naming a tag that resolves to **nothing** in any
spec (`resolves()` returns `False`, `:2760-2766`); (b) **COMMAND-keyed** — a
per-command key (`table_columns`, etc., via `gc.COMMAND_KEYED_OVERRIDES`)
inside a resolved tag block naming a command name that tag's real endpoint set
doesn't actually produce (`:2794-2820`, computed by literally running
`parse_tag` + `apply_endpoint_overrides` in-memory). Also flags a **shallow-
merge clash**: a tag declared both as a top-level block and under
`tag_overrides` for the same keys, where the generator's shallow merge would
silently drop the top-level copy (`:2783-2792`).

**Is the assertion weaker than the name implies?** Narrower in one precise,
documented way: it deliberately does **not** flag `tag_merge` sources or
`tag_op_excludes` keys (`:2698-2701`) — those are "if this tag is present,
correct it" guards that are supposed to be no-ops when the tag is absent, so
flagging them would fight a legitimate defensive pattern. This means an entry
under those two families can be **arbitrarily stale/wrong and this check will
never see it** — that's a stated, deliberate scope line, not a hidden gap.
Also: specs are read from **disk**, not `git ls-files` (unlike almost
everything else in this file) — a per-spec section keyed on an untracked spec
(`webex-flow-store.json`) is `None` (out of scope) rather than "inert"
(`:2760-2766`), so on a machine that happens to have that dev-only spec on
disk, this check's answer for those sections **differs from what a fresh
clone would report** — the opposite direction of check 8's "reproducible from
clone" guarantee elsewhere in this file. I did not find any code compensating
for that (no `tracked_specs()` filter here) — `[verified]` the disk-glob is
`SPECS_DIR.glob("*.json")` at `:2741`, not the tracked-only helper used
elsewhere in the file.

**Gated/advisory:** **No advisory tier at all** — both `findings` (tag +
command + clash kinds all pooled into one list) and `stale` acks gate
unconditionally (`main:3638`, `inert_overrides or stale_inert_acks`). Unusual
among the three-way-split checks (11b, 12, 18, 19) in this range: check 15 is
strictly binary per finding.

**Ack list:** `inert_tag_ack` in `field_overrides.yaml` (`:2740`), keyed by
tag name, holding one entry today (the AI Assistant tag). Re-validated: an
acked tag that resolves again is reported as `stale` and fails (`:2822-2827`).

---

## Check 16 — `check_undeclared_paging` (`tools/drift_check.py:2849`)

**Name implies:** detects list commands whose pagination isn't correctly
declared/handled.

**Actually asserts** `[verified]`, and it is considerably **narrower** than
that name, entirely by explicit design (the docstring says so, `:2861-2866`):
a command is only flagged if **(a)** its rendered source has the `--all`
option string but **no** `if all_pages:` / `and not all_pages:` branch
(`:2900-2903` — i.e. `--all` is structurally inert on this command) **and**
**(b)** the spec's own 200-response schema for that GET operation declares one
of exactly four paging-total field names — `totalResources`, `totalRecords`,
`totalResults`, `total` (`PAGING_TOTALS`, `:2833-2834`) — **and** **(c)** the
path doesn't end in `/count` (`:2923-2924`, deliberately excluded since
`totalCount` there is the answer, not a paging signal).

**Is the assertion weaker than the name implies?** Yes, precisely the class of
"undeclared paging" the name would suggest covering but the code cannot: an
endpoint that genuinely paginates via a **cursor/token scheme, or purely via a
`Link: rel="next"` header with no total-count field at all**, and whose spec
does not declare `paginates`/`pagination_style` either, would be structurally
identical to the flagged case (an inert `--all`) but produces **zero
findings** here, because step (b) has no signal to key on. The check's own
docstring is honest that this is "the signal this check **adds**" (`:2861`),
not a complete detector — but the function name and the `[16]` report line
("list commands whose `--all` is inert on a paging endpoint", `main:3809`)
read as a general claim. In practice this means: a command can have a
genuinely broken `--all` and this check will say nothing, if the endpoint's
response schema simply omits a total field (which is common for cursor-paged
APIs).

**Gated/advisory:** No advisory tier — both `findings` (`inert_paging`) and
`stale` (`stale_paging_acks`) gate unconditionally (`main:3639`).

**Ack list:** `undeclared_paging_ack`, keyed per operation (`GET
<normalized-path>`), re-validated both directions (`:2941-2944`).

---

## Check 17 — `check_registry_counts` (`tools/drift_check.py:2630`)

**Name implies:** prose claims about the size of some registry (e.g. "26
transform mappers") match the registry's real size.

**Actually asserts** `[verified]`: exactly that, and no more — reads a
module-level list/tuple/set literal's length via `ast` (`_list_literal_len`,
`:2592-2610`, never imports) for two hardcoded registries (`MAPPER_ORDER`,
`ALL_ANALYZERS`) plus one dict-literal special case (`_preflight_check_count`,
the `all_checks` dict inside `PreflightRunner.run`, `:2613-2627`), then
regex-matches a **fixed, hand-maintained list of (file, pattern) claim sites**
(`_REGISTRY_CLAIMS` and `_PREFLIGHT_CLAIMS`, `:2553-2589`) against each
registry's true count.

**Is the assertion weaker than the name implies?** Yes, in the most literal
possible sense: this check can **only** ever catch a miscount at a location
someone has already hardcoded into `_REGISTRY_CLAIMS` / `_PREFLIGHT_CLAIMS`.
It is not a general "find every place a number is claimed in prose and verify
it" scanner — it's a **closed, enumerated list of exactly 3 registries and
~10 claim sites**. A new prose claim about mapper/analyzer/preflight counts in
a file not already in those lists (or a claim about the size of some *other*
registry entirely, e.g. command-group counts, which check 3 handles
separately with its own regex machinery) is **completely invisible** to check
17 — there is no fallback scan. This is implicit in the code shape (a literal
Python list of tuples) rather than stated as a limitation in the docstring,
which instead frames the check as solving the general "prose vs. registry"
problem via the F17 anecdote (`:2547-2552`) — the anecdote is about exactly
these 3 registries, so the generalization from "we found this problem here"
to "this check solves this class of problem" is a reasonable but real gap: it
solves it only where it has already been told to look.

**Gated/advisory:** Fully gated, single list, two `kind`s pooled together
(`unreadable_registry` if the registry itself can't be parsed via ast, and
`count_mismatch` for an actual claim/registry number disagreement) — both
included in `results["17_registry_count_claims"]` and both count toward
`failed` (`main:3640`, `registry_counts`). No advisory split.

**Ack/allowlist:** None. No exemption mechanism of any kind — the only way to
silence a finding is to fix the prose or fix the registry, which is the
intended behavior per the docstring's closing clause (`:2669-2670`,
`"— fix the prose or the registry"`).

---

## Check 18 — `check_reference_doc_shape` (`tools/drift_check.py:3010`)

**Name implies:** `docs/reference/*.md` files are structurally sound —
readable as it's stated, "shape", so this one's name is honest about being
narrow. Worth checking anyway whether "shape" itself is checked completely.

**Actually asserts** `[verified]`, two tiers over every `*.md` in
`docs/reference/` except `NON_REFERENCE_DOCS` (`CLAUDE.md`, `TODO.md`,
`migration-spec-template.md`, `:2954`):
- **GATED:** every **in-document** `](#anchor)` link resolves to a real
  heading-derived slug in the *same file* (`_INDOC_LINK` regex `:2958`,
  anchors computed by a hand-rolled GitHub-slugger clone, `heading_slugs`
  `:2985-3007`); the file ends with exactly one trailing newline; a `## See
  Also` section exists somewhere in the doc.
- **ADVISORY (never gated):** `## See Also` exists but isn't the *last*
  section; no `## Sources` section; no heading containing "gotcha"; no
  contents/TOC heading.

**Is the assertion weaker than the name implies?** Yes, in one specific and
verifiable way even for "shape": `_INDOC_LINK = re.compile(r"\]\(#([^)]+)\)")`
(`:2958`) matches **only** links of the literal form `](#anchor)` — a bare
same-document anchor. It does **not** match, and therefore never checks, a
**cross-document** link such as `](call-routing.md#dial-plans)` or a link to a
sibling doc that no longer exists at all. Given that this directory's own
`See Also` sections are explicitly *lists of cross-references to other
reference docs* (per every doc in this repo's `docs/reference/` convention,
and the check's own name-collision handling elsewhere in the file references
"See Also links" as the primary navigation mechanism), the single structural
check this function performs on links entirely **excludes the one link type
the `See Also` sections it enforces the presence of are actually built from**.
A `## See Also` section can exist (satisfying the gated rule), be the last
section, and contain nothing but dead links to renamed/deleted sibling files,
and check 18 will report the doc as shape-clean. I did not find any other
check in my assigned range (nor any hint in `main()`'s printed check
descriptions 1-20) that validates cross-file reference-doc links — this looks
like a genuine, unflagged gap rather than a documented exclusion (contrast
with check 15/16's explicitly-stated scope narrowings above).

**Gated/advisory:** `failures` (dead in-doc anchor, wrong trailing-newline
count, missing `## See Also`) gate via `doc_shape` (`main:3640`). `advisories`
(See-Also-not-last, no Sources, no Gotchas, no TOC) never gate
(`18_reference_doc_advisory`, reported only).

**Exemption:** `NON_REFERENCE_DOCS` (`:2954`), a hardcoded 3-file set — not a
YAML ack, not re-validated against anything (there's no staleness check that
these three files still exist or still deserve the exemption; if one were
deleted or renamed the set would just silently stop matching anything for
that entry, which is harmless, but there's no mechanism analogous to the
YAML-ack staleness pattern used everywhere else in this file).

---

## Check 19 — `check_spec_semantics` (`tools/drift_check.py:3415`), with
`spec_semantics` (`:3248`), `diff_spec_semantics` (`:3350`),
`load_spec_snapshot` (`:3408`), `refresh_spec_snapshot` (`:3436`)

**Name implies:** any upstream OpenAPI spec change that alters what an
operation *means* is caught, not just changes to what commands/fields exist.

**Actually asserts** `[verified]`: diffs a **snapshot file**
(`tools/spec_semantics.json`) against a freshly recomputed
`spec_semantics()` over all tracked specs, scoped to exactly the same
operations `load_spec_ops` renders (untagged / skip_tags / multipart
excluded, `:3277-3282` — matching check 1's scope). For each surviving
operation it records, **per spec file** (never unioned, `:3255-3258`): the
tag, the summary text, and one **encoded field string** per request
parameter/body field (`encode_field`, `:3162-3174`) capturing requiredness,
an extracted `name`/`id` "kind" (only if the description contains the phrase
`<name/id/identifier/uuid> of`, `KIND_PHRASE` `:3092-3093`), a hash of the raw
description, a hash of just the "constraint sentences" (sentences containing
`must`/`cannot`/`only if`/etc., `CONSTRAINT_WORDS` `:3097-3099`), and enum
values. Diffing (`diff_spec_semantics`) buckets into 3 tiers: **structural**
(op/field/required/enum add-remove, GATED), **ID-kind flip** (description
said name, now says id, or reverse, GATED), **prose** (everything else —
wording/summary/constraint-sentence changes, ADVISORY).

**Precisely what it CAN and CANNOT detect** (the task's explicit question):

CAN detect, and gate on:
- An operation appearing/disappearing from a spec (`operation_added` /
  `operation_removed`).
- A request-body or parameter field appearing/disappearing
  (`field_added`/`field_removed`).
- A field's `required` flag flipping either direction
  (`required_added`/`required_removed`).
- An enum's value **set** changing (order-insensitive — values are sorted
  before joining, `:3173`, so reordering alone produces no diff, correctly).
- A description's stated "this is a name" vs "this is an id" flipping, but
  **only** when phrased as `<the> <name(s)|id(s)|identifier(s)|uuid(s)> of`
  (`KIND_PHRASE`) — this is the mechanism that caught the real 2026-08-03
  `cc-dial-number --location` defect, and the docstring documents (and
  `tools/CLAUDE.md` corroborates with 8-refresh measurement) that a looser
  "does the text mention id/name at all" version was tried and rejected as too
  noisy.
- Any operation's tag (first tag only — see below) changing.

CANNOT detect, verified from the code (not merely "not mentioned"):
- **Any change to a response schema.** `spec_semantics()` builds its field set
  from `parameters` and the **request** body schema only
  (`_json_body_schema`, `:3240-3245`, `walk_body` over that, `:3291-3293`) —
  `responses` is never read anywhere in this function. A field silently
  disappearing from, or changing type in, a GET's 200 response is completely
  outside this check's model. (This is a distinct blind spot from check 9,
  which *does* look at response item schemas but only for list-command table
  columns and only compares against what's already rendered — neither check
  covers a general response-schema meaning change on, say, a `show` command.)
- **A field's data TYPE.** `encode_field(required, desc, enum)` (`:3162`) never
  receives or encodes `schema.get("type")` — no `string`/`integer`/`boolean`/
  `array`/`object` discriminator anywhere in the encoding. A field silently
  changing from string to integer (or gaining/losing array-ness) with
  identical description text, requiredness, and enum would produce **zero
  diff of any kind, not even advisory** — invisible to all three tiers.
- **Schema-level validation constraints** not expressed in prose — `pattern`,
  `minLength`/`maxLength`, `minimum`/`maximum`, `format`, `default` are never
  read. Only free-text sentences matching `CONSTRAINT_WORDS` are captured,
  and only as an opaque hash (advisory tier) — the actual rule text is not
  diffable, only "the constraint-sentence set changed" as a boolean-ish
  signal.
- **A field whose meaning-changing phrase doesn't match `KIND_PHRASE`'s exact
  grammar.** E.g. "this field identifies the workspace" or "the workspace this
  belongs to" carries no `<kind> of` phrase, so a real ID/name meaning change
  worded that way is **not even eligible for the ID-kind-flip tier** — at best
  it shows up as a generic `wording_changed` prose delta (advisory, never
  gated). This is a deliberate, measured tradeoff per the docstring/CLAUDE.md
  (anchored phrasing: 0 false positives across 446 other prose deltas vs. 26
  false positives/refresh for the loose form) — but it does mean the "ID-kind
  flip" gate's real coverage is bounded by one specific English idiom.
- **A second/later tag on a multi-tagged operation changing while the first
  tag stays the same.** `tag = (op.get("tags") or ["(untagged)"])[0]`
  (`:3277`) — only `tags[0]` is ever recorded or compared
  (`tag_changed` in `diff_spec_semantics` `:3395-3398` compares only that one
  string). Given the root `CLAUDE.md`'s own documented fact that 27 operations
  across the 9 specs are multi-tagged and render into more than one CLI group,
  a spec revision that adds or changes a **secondary** tag on one of those 27
  — which could change which second CLI group the operation renders into — is
  invisible to this check. `[verified]` from the single-index literal at
  `:3277`; I have not independently re-derived the current multi-tag count to
  confirm it's still 27 (that number is asserted in `tools/CLAUDE.md`, not
  recomputed here).
- **A `oneOf`/`anyOf` schema where two branches declare a field of the same
  name differently.** `walk_body` (`:3211-3237`) flattens `allOf`/`oneOf`/
  `anyOf` by yielding every branch's fields at the *same* dotted path
  (`:3223-3225`); the caller then does `fields[f"body:{name}"] = encode_field(...)`
  in a plain loop (`:3291-3293`), so if two branches yield the same `name`,
  the **second write silently overwrites the first** in the dict — only one
  branch's requiredness/description/enum survives into the snapshot at all.
  `[verified]` as code behavior (last-write-wins on a dict key); `UNKNOWN`
  whether any currently-tracked spec actually has a `oneOf`/`anyOf` with a
  same-named field across branches (I did not grep for this — flagging the
  mechanism, not a confirmed live instance).
- **Anything about operations excluded from `load_spec_ops`'s scope** — same
  skip_tags/untagged/multipart exclusions as check 1, so a meaning change on a
  deliberately-out-of-CLI operation is out of scope by design (consistent with
  the rest of the gate, not a special weakness of check 19).

**Gated/advisory split, precisely:** `spec_structural` and `spec_flips` both
gate (`main:3641`, `spec_structural or spec_flips`). `spec_prose` **never**
gates — explicitly called out in a comment right at the `failed` computation
(`:3642-3646`) as a deliberate, measured decision (267 prose deltas in one
historical refresh; judging which reword a meaning is "not a decision a
machine can make").

**Ack mechanism — explicitly NOT an ack list.** There is no YAML
allow/ack-list for check 19 at all. The snapshot file `tools/spec_semantics.json`
**is** the acknowledgment mechanism — it records every operation's encoded
state, so it's re-validated in both directions for free (an operation upstream
deletes is a finding even though nobody "un-acked" it, `:3419-3424`). The
project's own test suite pins that a second ack mechanism must never be added
on top (`test_check_19_has_no_ack_list`, referenced in `tools/CLAUDE.md`, not
independently verified by me since it's outside `drift_check.py`).

---

## Check 20 — `check_reference_doc_coverage` (`tools/drift_check.py:3490`),
with `command_sets` (`:3473`)

**Name implies:** every command group has a `docs/reference/` document that
actually describes/documents it.

**Actually asserts** `[verified]`, and the docstring is candid about this
being intentionally weak (`:3505`, "It is a weak oracle by design"): for each
module (deduplicated by module, not group — `command_sets`, `:3473-3487` — so
alias groups like `customer-assist`/`cx-essentials` count as covered together)
that isn't matched by the `declared_out_of_scope()` escape hatch (shared with
check 4, `:3524-3525`), the check passes **iff any one of its group names
appears, anywhere, in any `docs/reference/*.md` file, either as a backticked
token `` `group-name` `` or as the literal substring `wxcli group-name`**
(`:3530-3531`). There is no requirement that the mention occur in a heading, a
sentence describing behavior, a command table, or even a *positive* context.

**Is the assertion weaker than the name implies?** Yes, unambiguously, and
this is the clearest instance of the requested pattern in my whole range: the
result key is literally `20_groups_without_a_reference_doc` (`main:3629`) and
the printed line reads "command sets with no docs/reference/ coverage"
(`main:3859`) — both read as "this group is documented." The actual check only
proves the group's **name string** occurs somewhere in the reference-doc
corpus. A doc that says, in a disambiguation table, `"Set up a queue" (Calling)
→ configure-features, NOT contact-center` would make `` `contact-center` ``
match and mark that module "covered" even in a document explaining that
*this* doc is not the place to look for it. Similarly a sentence like "See the
`contact-center` skill instead" would satisfy the check with zero actual
reference content. The docstring justifies this explicitly by pointing at
check 2 ("check 2 already proves every `wxcli <group> <command>` inside those
docs resolves, so this one only has to prove the group is not INVISIBLE
there", `:3505-3507`) — i.e. the check's actual, narrower claim is "not
invisible," and the report line's wording ("no ... coverage") oversells that
by using the word "coverage."

**Gated/advisory:** Single-tier, no split — `undocumented_groups` fully gates
(`main:3641`).

**Exemption:** `declared_out_of_scope()` (pre-1700 helper, `:946`) — reads the
same CLAUDE.md "Out-of-Skill-Scope Command Groups" table check 4 uses, by
explicit design (the whole point of the doc's own note that checks 4 and 20
"cannot disagree about what referenced means").

---

## `main()` (`tools/drift_check.py:3539-3899`)

**Aggregation** `[verified]`: all 20 checks are called as plain sequential
function calls (`:3561-3592`), building local variables, then packed into one
flat `results` dict (`:3594-3630`) keyed `"<N>_<label>"`. There is **no
per-check try/except** anywhere in `main()` — every check call can raise
uncaught.

**Exit code, precisely** (`:3868`, plus the module-level guard at
`:3886-3899`):
- `0` — ran to completion, `failed` is False, or `failed` is True but
  `--enforce` was not passed (report-only mode still exits 0).
- `1` — ran to completion, `failed` is True, **and** `--enforce` was passed.
- `2` — the process **crashed** before `main()` returned at all. This is a
  distinct, separately-installed guard: the `if __name__ == "__main__":` block
  wraps `sys.exit(main())` in `try/except Exception` (`:3887-3899`), prints
  `traceback.print_exc()` **and** a line beginning `result: CRASHED — the gate
  did not run to completion. This is NOT a findings failure...`, then
  `sys.exit(2)`. `KeyboardInterrupt`/`SystemExit` are `BaseException` and
  propagate untouched (stated in the comment at `:3884-3885`, and true because
  `except Exception` never catches `BaseException` subclasses — verified as a
  language fact, not re-tested).

**Can a check crash in a way reported as "found nothing"?** No, not silently
as a *clean pass* — this is the entire point of the documented "Code 2 exists
because of a real 11-day outage" comment block (`:3871-3883`): the gate used
to exit 1 (or presumably some ambiguous state) on a crash, indistinguishable
from "ran and found real problems," and that caused four consecutive red
builds to be misread as known findings for 11 days. The fix makes a crash
**loudly** distinguishable (`exit 2`, an explicit `CRASHED` string on stdout —
deliberately on stdout, not just stderr, "goes to stdout on purpose... so the
crash must speak in the same place the verdict normally does," `:3892-3894`).

**However** — one precise nuance the task's phrasing ("found nothing") is
worth being exact about: because all 20 checks run sequentially *before* any
printing happens (checks: `:3561-3592`; the `[N]` print statements don't start
until `:3651` after the `results`/`failed` computation), **if any single check
raises partway through, none of the earlier-computed check results are
printed either** — the run isn't "checks 1-14 passed, check 15 crashed," it's
"the whole run reports CRASHED, and nothing about checks 1-19's internally-
computed-but-never-printed results is shown at all." That's still correctly
distinguished from "clean" (exit 2 + explicit CRASHED text, not exit 0/1), so
it does not read as "found nothing" to a reader who checks the exit code or
the `result:` line — but a reader who only greps stdout for `[N]` lines and
doesn't reach the end would see a partial, silently-truncated list with no
explanation from the printed lines alone, only from the final `CRASHED`
banner. `[verified]` from the code structure (single linear function, prints
all at the end); this nuance is not called out in the code's own comments,
which frame the fix purely in terms of the exit code / `result:` line.

**One more nuance:** the crash guard only wraps the `if __name__ ==
"__main__"` invocation path (i.e. `python -m tools.drift_check` or `python
tools/drift_check.py`, both of which set `__name__ == "__main__"`). If some
other code imported `drift_check` as a module and called `main()` (or any
individual `check_*` function) directly, no such guard exists — an uncaught
exception would propagate as an ordinary Python exception to that caller, with
no `CRASHED` message and no exit-code-2 convention. `UNKNOWN`/out of scope
whether anything in this repo actually does that (e.g. a test file); not
checked as part of this audit.

---

## Explicit answers requested

**1. Does any check in lines 1700-3899 compare REGENERATED generator output
against COMMITTED output byte-for-byte, or otherwise detect a hand-edit to a
generated command file?**

**No.** `[verified]` by absence: I grepped this whole range for
`render_command_file`, `subprocess`, `generate_commands.py` (as an invoked
script), and `regenerat*` — the only hit is prose in `check_undeclared_paging`'s
docstring ("command regenerated onto a walking branch," `:2879`), not code.
The closest thing is `check_inert_overrides` (`:2681`), which imports
`tools.generate_commands` and calls its **tag/endpoint resolution functions**
(`get_tags`, `parse_tag`, `apply_endpoint_overrides`, `resolve_tag_merge`,
etc., `:2730-2811`) purely to compute *which command names a tag's config
block would claim* — it never calls `render_command_file`, never writes a
file, and never diffs generated source content against `git show HEAD:...` or
any committed copy. No check in this range reads the *content* of a generated
`.py` file and compares it to what regeneration would produce; `CommandFacts`
(`:2163`) and `parse_module_facts` (`:2298`) read the **shipped, on-disk**
source via `ast` to derive facts (URLs, flags, dict-writes) for checks 13/14,
but there is no second "expected" copy anywhere in this range to diff against
— the checks compare shipped-source-derived facts against the **spec**, never
against a regenerated re-render of the same source. (A hand-edit to a
generated file that changed, say, a URL string or a required-field write would
only be caught **indirectly**, if the edit happened to make the shipped
behavior disagree with what the spec says is required — that's what checks
13/14 actually do — not by any direct "this file differs from what the
generator would produce" comparison.)

**2. In `main()`: aggregation, exit code, and crash-as-silent-pass?**

Answered in full in the `main()` section above. Summary: flat dict of the 20
checks' outputs; exit 0 clean or report-only, 1 only with `--enforce` and a
real failure, 2 on any uncaught exception anywhere in the check-running or
result-building code, with an explicit `CRASHED` banner and traceback so it is
never mistaken for a clean or a findings-failure run.

**3. `check_spec_semantics` (check 19) — precisely what it can/cannot
detect?**

Answered in full in the Check 19 section above. Short version: it can detect
request-side (parameters + request body) field add/remove, requiredness
flips, enum-set changes, operation add/remove/first-tag-change, and one
specific "name"⟷"id" description-phrase flip (gated), plus generic
wording/summary/constraint-sentence changes (advisory only). It **cannot**
detect: any response-schema change at all, a field's data type changing, non-
prose schema constraints (pattern/min/max/format/default), a kind-meaning
change phrased outside the exact `<name/id> of` idiom (falls to advisory
prose or nothing), a secondary-tag change on a multi-tagged operation, or
(mechanism-level, unconfirmed live instance) a `oneOf`/`anyOf` branch collision
on a same-named field.

---

## Source-hygiene note (not a "check," but load-bearing for readability)

Section-header comments (`# --- check N`) in my range are **sparser than the
canonical numbering** actually used in `main()`'s `results` dict and report
lines. Grepping every `# --- check N` header in the file: check 10 (`:1356`),
check 11a (`:1520`), check 11b (`:1742`), check 12 (`:1925`), checks 13 & 14
(`:2006`), **check 15 (`:2541`)**, **check 18 (`:2948`)**, check 19 (`:3082`),
check 20 (`:3471`) — `[verified]` via `grep -n "check [0-9]"`. There is **no
header comment anywhere for check 16 or check 17** — both
`check_undeclared_paging` (16, `:2849`) and `check_registry_counts` (17,
`:2630`) live inside the single header block labeled `# --- check 15`
(`:2541-2947`), which also contains the real check 15
(`check_inert_overrides`, `:2681`). A reader navigating by section headers
alone would have no signpost that two more numbered, independently-gated
checks (16, 17) exist between the "check 15" and "check 18" headers, and would
have to notice the `main()` result-dict prefixes (`16_`, `17_`) to find them.
This is purely a navigability/maintainability observation, not a behavioral
weakness of any check — flagging it because the task asked me to be precise
about what each check's *actual* number is, and the file's own comments would
mislead a quick skim into thinking only one check (15) lives in that block.

