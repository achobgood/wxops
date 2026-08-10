# wxops — Architectural Audit

**Completed 2026-08-05.** Eight phases, each run as its own session against
`github.com/achobgood/wxops` (the binary is `wxcli`; source is `src/wxcli/`).
This document is the deliverable. The phase artifacts it draws on live in
`docs/audit/` (tracked as of `9d1c38d`); the prompt that drove them is
`docs/arch/wxops-architecture-audit-prompt_2.md`, which is **not** tracked, so
everything a future reader needs is either here or in `docs/audit/`.

**Two audit targets, because the repository is two bodies of code.**

- **Target A — the generated endpoint layer.** 87,585 LOC in
  `src/wxcli/commands/`, rendered by an in-repo generator (`tools/`) from nine
  git-tracked OpenAPI specs holding 2,053 operations, 154 of them deliberately
  skipped. 1,887 commands across 178 mounted groups (173 generated + 5
  hand-written). It rests on 1,790 lines of shared runtime in `src/wxcli/*.py`.
  The endpoint code is *output*; the real targets are the generator, the
  templates, the specs and that runtime.
- **Target B — the CUCM migration subsystem.** 46,684 LOC in
  `src/wxcli/migration/`, entirely hand-written, plus its driving command
  `src/wxcli/commands/cucm.py`. It runs its own async HTTP stack, its own retry
  policy, its own state machinery and its own SOAP client, and imports the shared
  runtime almost not at all.

**How to read this.** Every claim carries `[verified]` (a phase ran or parsed
something) or `[inferred]`; `UNKNOWN` is used where a question was reached and
not settled. Every finding names its target and cites `path:line`. Counts are
never estimated — where a phase did not measure something, this document says
"not measured" rather than guessing. Section 5 lists the numbers that earlier
artifacts got wrong, because those artifacts remain on disk and a future reader
will hit them.

**Three corrections to the state this report was briefed on**, all `[verified]`
this session:

1. **The working tree is clean.** HEAD is `05739b5`; `git status --porcelain`
   returns nothing. The 28 uncommitted generator files the audit ran against
   were committed as `de9ea55` + `de5bd78`. The code described here **is** the
   code at HEAD.
2. **The four tests pinning the 2026-08-05 fixes are tracked**
   (`git ls-files --error-unmatch`, all four). The "correctly-pinned fix ships
   with its test invisible to CI" item is closed and is not carried forward.
3. **`docs/audit/` is tracked** (21 files); `docs/arch/` is not (0 files).

---

## 1. Verdict

**Target A is structurally sound with localized rot, and its soundness is a
measured result rather than an absence of findings**: all 172 generated modules
regenerate byte-identical to what is committed, regeneration is deterministic
across two Python versions and multiple hash seeds, there are zero hand-edits to
recover, and a 3,899-line 21-check gate blocks CI and passes — the rot is
confined to the generator's six per-verb render paths, where capabilities added
in reaction to one bug on one renderer never reached the other five. **Target B
is sound in construction and compromised in verification**: its architecture is
genuinely better than Target A's in three respects a reader would not predict
(no process exits from library code, testable without a terminal or a network,
AXL failures more legible than Webex ones), but the ~1,000 lines that actually
write to a customer's org carry a retry policy written once in March and never
read again, and *every* failure branch beneath the happy path is executed by no
test. **Neither target's behaviour is pinned by anything CI runs** — proven by
mutation, not inferred: both stacks' retry policies can be gutted simultaneously
and the migration engine can be made to treat every HTTP 4xx/5xx as success,
with 3,580 tests passing and the drift gate reporting PASS in both cases. That
single fact is why this report's remediation begins with characterization rather
than with any of the defects it found, and it is cheaper to fix than the audit
expected, because the tooling is already installed and already used. The
repository is in better shape than an eight-phase audit usually leaves a
codebase; what it lacks is not care but a way for that care to reach the next
person who edits the file.

---

## 2. The three things that matter

**The judgment no phase made.** Each phase ranked severity inside its own scope.
Nobody had yet ranked a generator defect against a migration defect on one
scale. Here is that ranking, with the reasoning shown.

The three are ordered by **what happens if you fix only one**:

- Fix only **#1** and nothing improves today — but the other two become fixable
  in place and *stay* fixed. Leave it unfixed and both of the others are
  reversible in silence, which this repository has already demonstrated twice
  (`02-drift.md` F3, `04-generator.md` §3.2).
- Fix only **#2** and you have repaired the highest-consequence code in the
  repository — irreversible, remote, concurrent, unattended — but by the same
  mechanism that split it in the first place (`08-history.md` §2.5: a one-file
  fix that did not reach the second copy), so it re-diverges.
- Fix only **#3** and you have repaired the highest-*multiplier* code — 1,887
  published commands — but each individual instance is bounded to one resource
  and requires a deliberate write invocation to reach.

So: **#1 is first because it is the precondition, not because it is the worst
defect. #2 outranks #3 on consequence; #3 outranks #2 on reach.** Consequence
wins here for a reason Phase 1 measured rather than assumed: `wxcli cucm
execute` appears **four times in 1,933 recorded invocations across five weeks —
three of them `--help`** (`01-observed.md` §6). The most dangerous code in the
repository is also the least exercised, so ordinary use will not find its
defects. Target A's defects, by contrast, are being exercised constantly and
their observable failure rate on real work calls is **6.8%** and falling
(`01-observed.md` §0.2, §0.6).

---

### #1 — Nothing in CI pins either stack's behaviour, and the cause is a distribution decision made in 25 minutes on 2026-03-23 *(both targets)*

**What's there.**

The proof is a mutation, run in a throwaway clone, not an inference
(`07-testability.md` §2.5) `[verified]`:

| Mutation | Result |
|---|---|
| `RETRY_STATUSES = frozenset()`, `MAX_RETRY_AFTER_SECONDS = 86400`, `DEFAULT_MAX_ATTEMPTS = 1` (`auth.py:158-160`) **and** the engine's 429 branch disabled (`engine.py:199`) | **3,580 passed**, drift gate **PASS** |
| `engine.py:205`'s `if resp_status >= 400:` → `>= 40000`, so a 403/404/409/500 records the op `completed`, takes a `webex_id` from the error body, and cascades dependents forward | **3,580 passed**, drift gate **PASS** |

Target A's side of it: `auth.py:226-260` — the entire retry loop, through which
every HTTP call from all ~1,887 generated commands passes — has **zero statement
coverage**, as do all five `rest_*` methods and `follow_pagination`
(`07-testability.md` §3.3). `follow_pagination` has **173 call sites** and is
covered by nothing, on this disk or in CI (§3.5); it is the walker behind `--all`,
which `CLAUDE.md` instructs the operating LLM to use for every *how many* /
*which ones* / *are there any* question. Target B's side: `engine.py` is the only
module in all of `src/wxcli/migration/` that opens a socket, and it is the
worst-covered file in its own stage — 77% against a stage average of 92%, touched
by 8 of 44 test files. Inside `execute_single_op`, the 429 happy path executes and
**line 206 — the line that builds the error string and returns a failed
`OpResult` — has never run** (§2.4).

The illustrative pair, and it needs no percentage to make its point:
`src/wxcli/migration/rate_limiter.py`, which nothing in `src/` imports, is **96%
covered** by its dedicated unit test; the failure branches of `engine.py`, on the
only path that writes to a customer's org, are at **zero**.

The cause is not carelessness, and Phase 8 measured it rather than assuming it.
On 2026-03-23, in a 25-minute window, six commits reframed the repository as a
distribution artifact: `93bb23f` *"remove tests/ from tracking and gitignore
it"* removed 22 test files with the body *"Tests are dev-only, not needed for
playbook distribution"*, and `522bc69` added `.github/` under the comment *"CI
(no value without tests)"*. `tools/` was restored 14 minutes later and
`migration/` the next day. **`tests/` has been coming back one `!` line at a
time for 4.5 months and is still incomplete** — `.gitignore` is now the joint
highest-churn hand-written file in the repository at 49 commits, 23 of them
spent on which tests CI can see (`08-history.md` §4) `[verified]`.

The realized damage, measured by running every excluded file individually
(`07-testability.md` §3.4) `[verified]`: **712 tests exist that CI has never run;
26 are red**, all from two refactor commits, and *neither of those commits touched
any `tests/` file*. That is not two incidents — of the 90 commits since 2026-03-24
touching a module whose only unit test is untracked, **76 (84%) touched no test
file at all**, against 52% for the same author in the same era on subtrees whose
tests *are* tracked (`08-history.md` §5). An untracked test cannot appear in a
commit, so it cannot signal, so it cannot be updated by the person breaking it.

**Why it is expensive, given generation, publication and an autonomous
operator.** Publication is what converts this from a hygiene problem into a
contract problem: exit codes, flag names, output shapes and the eleven `WXCLI_*`
variables are all committed public contract (`00-facts.md` Q18), and nothing
executes the code that implements them. Generation multiplies it: until
2026-08-05, all four of the generator's test files were untracked — 187 tests
over the one component whose defects multiply by the entire surface. And the
autonomous operator is the reason a silent regression is worse here than
elsewhere: a short read from `follow_pagination` produces a confident wrong count
rather than an error, which is precisely the failure mode `CLAUDE.md`'s
`--calling-data` interlock was written to prevent, in a place nothing guards.

**The correct shape.** Not "raise coverage." Two specific things: (a) every test
that exists is either tracked or deleted, with the repair that tracking requires
done first; (b) the behaviours that are *contract* — the retry policy, the page
walker, the engine's notion of failure — are pinned by named characterization
tests that fail if the behaviour moves, in git-tracked files.

**What it costs.** Cheaper than the audit's own brief assumed, because the
premise that brief rested on was false. There are **no recorded remote responses
for any system** — not Webex, not AXL (`06-machinery.md` §0/C2), so there is no
asymmetry to plan around and nothing to record from scratch: `aioresponses` is
already a CI dependency (`ci.yml:35`) and is already used by six migration test
files. Eighteen test files and `conftest.py` remain untracked; two of the
eighteen are red (`test_auth.py` at 18-of-24 failing, `test_partner_e2e.py` at
5-of-21), and both failures are mechanical — stale patch targets and an
exact-string assertion, not live defects. Not measured: the effort to repair
them, beyond "the patch targets re-resolve on every call, so repointing them is
mechanical" (`06-machinery.md` §0/C2a).

---

### #2 — The migration write path's failure semantics were written once in March and have not been read since *(Target B)*

**What's there.**

`wxcli cucm execute` drains an entire migration plan against a live customer
org, 20-way concurrent by default, unattended. Its retry policy is inline in
`migration/execute/engine.py`, and it disagrees with the shared runtime on six
points. Phase 6 measured each with both citations side by side and stated which
side is right; five of six go to Target A (`06-machinery.md` §3) `[verified]`:

| | Target A (`auth.py`) | Target B (`engine.py`) | Right |
|---|---|---|---|
| Retried statuses | `{429,500,502,503,504}` (`:160`) | **429 only** (`:199`); every other `>=400` fails the op at once (`:205-210`) | A |
| `Retry-After` parse | `try/except ValueError`, falls back to backoff (`:249-255`) | bare `int(...)` (`:200`) — the RFC-permitted HTTP-date form raises | A |
| `Retry-After` cap | 30s (`:159`, `:251`) | **uncapped** | A |
| Fallback delay | exponential **with jitter** (`:184-188`) | literal `5`, no jitter | A |
| HTTP timeout | connect 10s / read 60s, env-tunable (`:192-193`) | **unset** — inherits whatever the installed aiohttp defaults to (`:875`) | A |
| `WXCLI_*` tuning vars | 7 read here | **0 of 7 reach the write path** | A |

Two of those compound. The engine releases its semaphore slot across the 429
sleep — correct on the mechanism, and Phase 6 settled it with `ast` rather than
by eye (D6) — which means all 20 rate-limited operations receive the same
`Retry-After`, sleep the identical unjittered duration, and resume in the same
instant, reproducing the burst that caused the throttle. And the entire bulk-job
path — submit, poll, and per-device fallback — has **no 429 handling at all**
(D5), on precisely the operations the planner substitutes at ≥100 devices, i.e.
one op per org-or-location-wide device job.

Beneath the retry policy, the failure surface is thinner than the disagreements
suggest. A non-JSON error body — an HTML gateway page — becomes the literal
string **`500: {}`** (§6.1), because `errors.py` is never imported on this path,
so none of its ID-kind decoding, HTML truncation, error-code tips or status tips
apply. `completed` means "2xx", not "applied": nothing re-reads the resource,
while **332 generated update commands carry `--verify` precisely because, in its
own docstring, a 2xx proves the request was well-formed and not that the
configuration is right** (`05-safety.md` §1.7). A malformed `~/.wxcli/config.json`
takes an `except Exception: pass` branch and every write then goes out without an
`orgId` (D9) — on a partner token, into whichever org the token defaults to. And
the `journal` table, which declares exactly the `request` / `response` /
`pre_state` columns an audit trail needs, is written only by the two read-only
discovery stages and `pre_state` is populated by no caller anywhere (§1.8).

**History dates it, and the date is the finding.** `engine.py` has 21 commits;
**its retry block has one**, from 2026-03-24, confirmed by four independent
methods. The `execute` command body has two. Meanwhile `auth.py`'s policy was
*deliberately widened* on 2026-07-24 by `bcb1330` — one file, 45 insertions, 14
deletions, **no test** — which added the 500/502/503/504 statuses, the jitter and
the `Retry-After` guard. Before that commit the two stacks agreed
(`08-history.md` §2.5) `[verified]`. **Three of the six disagreements are twelve
days old, and were created by a repair that had no mechanism to reach the second
copy of the thing it was repairing.**

That inverts the premise Phase 8 was given. On this repository, high churn marks
*resolved* questions — every place the maintainer churned, they left a tracked
characterization test behind (§3.3) — and **zero churn marks the unexamined
ones**. A ranking built on churn would have put this block near the bottom.

**Why it is expensive.** Consequence, not multiplier. A single 503 from Webex
during a migration fails that operation permanently and cascade-skips every hard
dependent — a 503 while creating a location skips the location's users, their
devices, and every feature hanging off them; the operator is told the operation
*failed*, not that the platform blipped. Recovery exists and is documented, but
**13 of 21 create-capable resource types have no 409 recovery** (`05-safety.md`
§1.6), `execute/` issues no DELETE anywhere, so nothing in the tool can clean up a
duplicate it creates, and whether a re-issued create duplicates or hard-fails is
`UNKNOWN` per type. The autonomous operator makes it worse in a specific way: the
error string carries no tip and the command exits 0 regardless of outcome, so an
LLM cannot distinguish "the platform blipped, retry" from "this is permanently
rejected, stop" — and per Phase 6 §2.2 the documented remedy it will reach for
(`WXCLI_MAX_ATTEMPTS`, named in `errors.py`'s own 429 tip) is inert on this path,
while working on the preflight reads in the *same invocation*, which is the
evidence most likely to convince it the knob is live.

**The correct shape.** Not "merge the stacks." Phase 6 answered that explicitly
and the answer is no: **not one of the six disagreements is caused by the choice
of HTTP library**, and every one is a policy expressible as a pure function of
`(status, attempt, headers, env)` — roughly 40 lines in `auth.py`
(`RETRY_STATUSES`, `MAX_RETRY_AFTER_SECONDS`, `_backoff_delay`, `_retry_enabled`,
`_max_attempts`, `_env_float`) that touch no `httpx` symbol and that both stacks
could import unchanged. The split stands; the *policy* is extracted and shared,
and a gate check asserts both sides read the same constants. Alongside it, three
smaller things with the same root: a request timeout stated as a named constant
(three stacks currently arrive at "no timeout" by three different routes), the
`journal` written on the execute path, and scope disclosed before the first write
rather than only in the post-run summary.

**What it costs.** The 40-line extraction is small; the characterization that has
to precede it is the real work, and Phase 6 §8 already enumerates it as five named
tests, each red today. Not measured: effort in hours. One thing explicitly *not*
on the list — reviving `rate_limiter.py`. It is dead code whose five declared
parameters all contradict what runs; adopting it would be adopting a
specification nobody has validated against the live API. Delete it, and fix
`docs/architecture/04-operations-and-evolution.md:357`, which currently tells the
next contributor to build on it.

---

### #3 — The generator cannot express an array as a flag, cannot classify one as destructive, and prints a runnable example that performs the omission *(Target A)*

**What's there.** One rule, copied fourteen times, with a mitigation gated on the
inverse of the dangerous property.

`tools/command_renderer.py` drops every array- and object-typed request-body
field from the flag surface — `if bf.field_type in ("object", "array"): continue`
— at fourteen sites, one of which spells the identical rule differently
(`:1511`) and was missed by two successive attempts to enumerate them, including
this audit's own (`04-generator.md` §1.1). Measured by two independent methods
that agree to the field: **696 fields across 394 commands in 98 modules**, of
which 406 are arrays and 290 objects. **92 commands are left with zero scalar
flags** — their entire semantic surface is one invisible array — and three were
confirmed live at `--help` (C2).

The consequence is a hazard class that neither of the generator's two
destructiveness signals can see. A PUT that submits a whole collection *replaces*
it, so members not listed are removed; the summary verb is "Update" and no body
field is delete-shaped, so `classify_real_semantics` returns nothing and no
confirm is emitted. Phase 5 triaged **42 confirmed collection-replace operations**
out of 380 ungated PUT/PATCH, reading each description
(`05-safety.md` §2.1) `[verified]`; six state replacement in the vendor's own
words, including:

> *"The PUT API replaces the contents of the user's data … All attributes
> specified in the request body will replace all existing attributes"* —
> `PUT /identity/scim/{orgId}/v2/Users/{userId}`
>
> *"This specifies the new list of device members, completely replacing the
> existing device members. **If the member's list is omitted then all the users
> are removed except the primary user.**"* —
> `PUT /telephony/config/devices/{deviceId}/members`

The highest blast radius among the 42 is an entire SCIM directory-group roster
(`scim-groups update`, `members`, org-wide, no documented cap); also in the set
are a CC permission profile shared by many agents, a route group's local
gateways, hunt-group and call-queue agent rosters, and a music-on-hold playlist's
`locationIds`, which is simultaneously the stored assignment list *and* the scope
control.

**The mitigation exists and is gated backwards.** The generator is not silent
about dropped fields: `_render_example` switches the runnable `Example:` line to
`--json-body '<skeleton>'` when a flagless body field is **required**. A scope
control that defaults to "everything" is by definition *optional*. So of the 394
commands carrying a dropped field, **272 emit a runnable example that omits every
dropped field** — a figure derived twice from opposite ends, forward from the
shipped artifact and backward from the spec predicate, agreeing exactly
(`04-generator.md` §1.2) `[verified]`.

`device-settings update` is the whole class in one command, and six independent
mechanisms each decline to intervene, each correctly by its own rule (§1.3):
not destructive-classified; no flag, because `members` is an array; no example
disclosure, because `members` is optional; no required-field validation, because
`_render_update_command` has none at all (375 update + 57 action commands have
none — §2.2); no hand-keyed `command_confirms` entry; and `--verify` compares
scalars with `!=`, so it would report "the array changed" after the write without
naming who disappeared. The generated docstring says *"Update Members on the
device."* The example the tool prints is:

```
Example: wxcli device-settings update DEVICE_ID
```

which sends `PUT …/devices/{id}/members` with body `{}`. **Whether Webex treats
`{}` the same as `{"members": []}` on that endpoint is `UNKNOWN`** — settling it
needs a live call against a throwaway device, which no phase made, and it is the
one open question that changes this finding's severity.

Two corroborations that this is a class and not a list. The 2026-08-04
remediation that added a scope-aware confirm and help note to
`device-settings create-apply-line-key-template` was applied **per command name**,
by hand, via a YAML key; `device-settings preview-apply-line` carries the
byte-identical body schema — same `locationIds`, same include/exclude tag arrays
— and received neither (§1.4). And a classifier built only from spec text, blind
to that fix, independently selected exactly those two commands (§1.5).

**Why it is expensive.** The multiplier is the point: one `continue` statement
times 696 fields, one example predicate times 272 commands, one missing
validation rule times 432. Publication makes it un-rollbackable by rename — every
flag name is committed contract, so any fix must be additive. And the autonomous
operator turns a documentation gap into an execution gap: with no MCP layer,
`--help` *is* the specification, and Phase 1 measured that **43% of 1,933 recorded
invocations carry `--help`** across 130 groups (`01-observed.md` §1.1). A tool
whose only specification omits the field, and whose copy-pasteable example
demonstrates the omission, is not merely under-documented — it is teaching the
unguarded call to the reader most likely to run it verbatim.

**The correct shape.** In four parts, cheapest first, and none of them requires a
spec change — the audit's own hypothesis that the missing consequence dimension in
`tools/spec_semantics.json` was the root cause is **not what the evidence shows**
(`04-generator.md` §7.5). (a) Extend `_render_example`'s trigger from "required
flagless field" to "any flagless field the classifier calls a scope control", so
the dangerous class reaches the example. (b) Apply one required-body-field rule to
all four write renderers instead of two disagreeing copies and two absences.
(c) Give `classify_real_semantics` the information it needs: it currently receives
the summary string and the body-field list and nothing else, and `EndpointField`
carries no item schema, so the detector Phase 5 recommended — *does this array's
items reference an existing remote object of a known KIND*, reusing the 71 KINDs
`_spark_id_kind` already decodes — **cannot be computed at all.** The item schema
is resolved during parsing and thrown away; that one field on one dataclass is the
ceiling. (d) Emit `--dry-run` on the **328** ungated writes that already carry
`--verify`, which is `_can_verify`'s predicate and `verify_write`'s body run in
the opposite order — and nowhere else, because a preview that silently previews
nothing is worse than no flag, a rule this repository already wrote down and
enforced once.

**What it costs.** (a), (b) and (d) are template changes with no spec and no
parser change. (c) is the only expensive item and the only one that reaches the
class automatically. Two parse-time losses bound the cheap prose alternative and
must be fixed with it: the operation-level `description` is **never read** by the
parser — which is where four of the six vendor sentences live — and 28 body-field
descriptions are discarded by a one-line `$ref`-site read (`04-generator.md` §6.2).
Not measured: LOC or hours for any of it.

---

## 3. Sequenced remediation

Three rules govern this sequence, and each one was earned by a measurement in
this audit rather than assumed:

1. **Pinning is step one of the programme, not a footnote per step.** With
   nothing in CI holding either stack's behaviour, current behaviour is the only
   specification that exists — and §2 #1 proved you cannot tell a refactor from a
   regression here.
2. **A guard ships in the same commit as the check that pins it, and that check
   must live in a git-tracked file** (`02-drift.md` F3, sharpened by
   `07-testability.md` §3.4). A guard pinned by an untracked test is a guard
   pinned by nothing, and this repository has produced three examples.
3. **Never fix a generated file.** Every Target A change below is at the spec,
   the generator or a template, and regenerates.

### 3.0 Already shipped — do not redo this work

Four things landed during the audit, under its remediation rule, each with a
git-tracked test. A maintainer reading the phase artifacts will find them
described in their pre-fix state; **this section is the current state.**

| Shipped | What changed | Where the pre-fix description lives |
|---|---|---|
| 24 destructive non-DELETE commands gated (2026-08-04) | The 23 operations `classify_real_semantics` flags destructive but renders as POST/PUT/PATCH, plus `device-settings create-apply-line-key-template` via a scope override. **The count "779 ungated writes" is 755 everywhere.** | `00-facts.md` Q10 |
| **Drift-gate check 21** (`de5bd78`) | `check_confirm_gates` asserts every operation the classifier flags destructive has a `typer.confirm` in its rendered body. Built on `build_cli_surface()` + `load_spec_ops()`. Mutation-proven in both directions: 0 clean, 23 with the render-path gate removed, 24 with a pre-existing DELETE confirm additionally deleted. Checks 20 → 21. | `02-drift.md` F3 |
| The generator's four test files repaired and tracked | 187 tests that had never run on a PR now do. `tests/tools/test_command_renderer.py` was **renamed** to `tests/test_command_renderer_dispatch.py` — the two same-basename files are not duplicates, and the smaller one holds the only dispatch-level coverage in the repo. Tracked root tests 415 → 612. | `07-testability.md` §3.3 |
| Four Target B safety fixes (2026-08-05) | `in_progress` is written before dispatch, so a half-applied migration is no longer byte-identical to a not-yet-started one; the preflight bulk-job probe actually runs and its failure now stops the gate (`INCOMPLETE`, with `cucm.py:1797` widened to match); `execute` requires a passing preflight; `plan` preserves the execution record and `normalize` refuses to erase it. | `06-machinery.md` D13/§5, `05-safety.md` §1.5/§1.1 |

Check 21's one deliberate limit is worth carrying: it claims only the
`real_semantics` population, so the scope-based gate on
`device-settings create-apply-line-key-template` is **not** pinned by it. That
was the right scoping — a check that asserted more than its name says is the
failure mode this audit named for check 20 — and it means the scope class is
still unguarded until §3.3 lands.

### 3.1 Phase A — pin what exists *(both targets; gates everything below)*

**A1. Repair and track `tests/test_auth.py`, then add the cases it does not
have.**
*What changes:* repoint the ten `patch("wxcli.auth.httpx.request", …)` targets
to survive `auth.py`'s deliberate lazy import (`auth.py:14-21`, `:206`, `:226`) —
patching `httpx.request` itself works, because the method re-resolves it on every
call. Confirm 24/24 green, then add `!tests/test_auth.py` beside the other
re-includes in `.gitignore`. **Then add the two cases Phase 7 measured are still
missing after the repair**: one driving `_request`'s retry loop (`:226-260`) and
one over `follow_pagination` (`:298-311`) — repairing alone leaves both at zero
coverage, so the step is *"repair, track, and add"*, not *"repair and track."*
*Blast radius:* none on shipped code. Tracking before repairing turns CI red.
*How to pin first:* this step **is** the pin — it restores the only executable
proof of the behaviour every later step is measured against. Until it lands,
Target A's retry contract is corroborated only by reading `auth.py:157-260` and by
`docs/reference/authentication.md:566-577`, which is sound evidence and is not
test evidence.

**A2. Characterize the engine with `aioresponses`.**
*What changes:* five tests, all currently absent and all red today, under
`tests/migration/execute/` (re-included wholesale at `.gitignore:56-57`, so they
run on every PR by construction): a 503 is retried; a date-form `Retry-After` does
not become a failed op; a `Retry-After` above the cap is clamped; two concurrent
429s do not wake together; `_try_find_existing` rejects a name that is not an
exact match. **Add a sixth**, from Mutation 2: a 4xx/5xx on the write path is
recorded `failed`, not `completed`.
*Blast radius:* none — tests only.
*How to pin first:* n/a; this is the pin. `aioresponses` is already a CI
dependency and already used by six migration test files, so no tooling is needed.

**A3. Decide the remaining test surface, one file at a time.**
*What changes:* 18 test files and `conftest.py` are still untracked. Two are red.
The existing policy — one `!` line per file, each carrying the reason it was
promoted — is working and should continue; what has not kept pace is the rate.
Also decide `tests/fixtures/axl-responses/`: 18 recorded AXL responses sitting on
one developer's disk, untracked *and* referenced by nothing. **Track and wire them
in, or delete them.** Leaving them is the worst option — this audit's own
reconnaissance mistook them for a safety net and built a remediation plan on it.
*Blast radius:* CI goes red for each red file tracked before repair.
*How to pin first:* run each file individually before tracking it;
`07-testability.md` §3.4 is the current result table.

### 3.2 Phase B — the write path *(Target B; requires A1 + A2)*

**B1. Extract the retry policy into a module both stacks import.**
*What changes:* `RETRY_STATUSES`, `MAX_RETRY_AFTER_SECONDS`, `_backoff_delay`,
`_retry_enabled`, `_max_attempts`, `_env_float` move behind one import; `auth.py`
and `execute/engine.py` both consume it. This closes D1, D2, D3, D4 and D12 at
once, and it restores the published `WXCLI_*` contract on the write path.
*Blast radius:* **large in both directions** — every HTTP call from ~1,887
generated commands, and every write a migration makes. It is also the step that
changes how the engine behaves under real rate limiting, which is unobservable in
a test suite.
*How to pin first:* A1 and A2 in full. Do not start this before both are green;
the five characterization tests are what distinguish "the engine now retries a
503" from "the engine now does something else too."

**B2. Add the gate check that asserts both stacks read the same constants.**
*What changes:* one new drift-gate check, following check 21's shape — two in-repo
artifacts, no network, no fixture. It would be the **first check in the gate that
reads Target B behaviour at all**: the gate's entire current coverage of 46,684
lines is three documentation counts inside check 17.
*Blast radius:* CI only.
*How to pin first:* mutation-prove the check in both directions before landing it,
per this repository's standing rule and check 21's own precedent — a check
reporting zero deserves more suspicion than one reporting many, and check 21
itself reported 15 false findings during development from exactly the mis-keying
`02-drift.md` F1 describes.

**B3. Give every stack a request timeout, stated as a named constant.**
*What changes:* three fixes with one shape. `engine.py:875`'s `ClientSession` sets
none and inherits an unpinned library default; `cucm/connection.py:190` sets
zeep's WSDL-load timeout and leaves `operation_timeout` at `None`, so every AXL
SOAP call is unbounded; `unity_connection.py:49` assigns `session.timeout`, an
attribute `requests` does not consult, so every CUPI call is unbounded and the
constructor advertises a 30s bound it does not enforce.
*Blast radius:* small and one-directional — calls that used to hang now fail.
*How to pin first:* each is testable without a network by asserting the
constructed client's timeout; no characterization needed.

**B4. Write the `journal` on the execute path, and design it once.**
*What changes:* the schema exists (`store.py:120-130`), the writer exists
(`add_journal_entry`), the FK-sentinel pattern exists (`batch.py:185-192`), and
the caller does not. One entry per operation carrying `request` and `response`
unconditionally, and `pre_state` **only for PUT/PATCH** — the verbs where prior
state is otherwise unrecoverable. This is the record that turns the 409
auto-recovery, the re-issue question and the "what did we send" question from
unrecoverable into diagnosable.
*Blast radius:* `pre_state` costs one extra GET per replacing write, at
concurrency 20, on the stack whose 429 handling B1 is fixing — which is why it is
scoped to two verbs and sequenced after B1. Note also that `clear_all` deletes
`journal`, so the protection `normalize` just gained has to extend to it or the
trail evaporates exactly when someone re-runs the pipeline to explain a failure.
*How to pin first:* a test asserting an executed op leaves a journal row;
`tests/migration/execute/` is tracked, so it runs on every PR.
*Design note:* Phase 1 and Phase 5 arrived at this table independently from
opposite directions — audit trail and telemetry — and it is **one record, not
two.** Two schemas would be the worst available outcome.

**B5. Disclose scope before writing.**
*What changes:* `execute` prints only concurrency before the first batch; the
operation count appears only in the post-run summary. Print the pending-op count
and the resolved target `orgId` first, and have `reset_in_progress` name the node
ids it reset rather than a bare count — those ids are precisely the operations
that may have half-applied, and the 2026-08-05 fix is what made that path
reachable at all.
*Blast radius:* output only. It is the cheapest item in this section.
*How to pin first:* nothing; it adds output and changes no behaviour.

### 3.3 Phase C — the render paths *(Target A; its two preconditions are already shipped)*

The ordering constraint here has already been satisfied: the generator's tests
are tracked and check 21 exists (§3.0). That was deliberate — the render paths
were **forbidden until those two landed**, because a renderer change is an
unpinned change to the highest-multiplier file in the repository, and mutation
proved that removing every guard from it regenerates cleanly and reports PASS.

**C1. Extend `_render_example`'s trigger.** *(cheapest, highest value)*
*What changes:* the runnable example switches to `--json-body` for any flagless
field classified as a scope control, not only for required ones. Today 272 of 394
affected commands print an example that omits every dropped field.
*Blast radius:* the emitted example line on up to 272 commands; no behaviour
change, no flag change, no exit-code change.
*How to pin first:* regenerate with a before/after diff over all 173 modules — **a
fix that changes output for commands you did not intend to touch is a finding
about the fix.** Phase 2 established that the generator is a pure function of
(specs, overrides, source) across two Python versions and multiple hash seeds, so
this diff is trustworthy.

**C2. One required-body-field rule for all four write renderers.**
*What changes:* create's check excludes required arrays before building its list;
delete's includes them and argues why in a comment — *"Fail HERE, not at the API.
A scoped delete whose scope is missing is the one shape that must never reach the
wire"* — and update and action have no check at all. That argument is verbatim the
argument for a collection-replacing PUT, and update is the renderer with nothing.
144 required object/array body fields get no client-side enforcement of any kind.
*Blast radius:* 432 commands gain a local error where they previously sent a
request the API rejected. This is a **behaviour change on published commands** —
an invocation that used to reach the wire and 400 now fails locally with exit 2.
Additive in effect, but it must be called out in a release note.
*How to pin first:* the generator's tests, now tracked; plus the regeneration diff.

**C3. Emit `--dry-run` where `--verify` is already emitted — 328 commands.**
*What changes:* `_can_verify` is the emission predicate and `verify_write` is the
body run in the opposite order: GET, diff the body you were about to send, print,
return without writing.
*Blast radius:* one new flag on 328 published commands; additive. One extra GET
per invocation when used.
*How to pin first:* the generator's tests. **Do not emit it where `_can_verify` is
false** — 427 writes have no same-path GET, and a preview that silently previews
nothing converts an unpreviewed write into one that *looks* previewed.

**C4. Then, and only if the class is worth it: the parser change.**
*What changes:* widen `classify_real_semantics`'s signature (its call site already
has `op`, `spec`, `method`, `url_path` and the resolved schema in scope — the call
site is not the constraint) and carry an array's item schema on `EndpointField`,
which is resolved during parsing and thrown away. Then the KIND detector becomes
computable. Recover the 28 discarded `$ref` descriptions and read the
operation-level `description` in the same change — both are nearly free and both
bound any prose-based alternative.
*Blast radius:* the parser is upstream of every renderer; a change here can move
output on all 173 modules.
*How to pin first:* the regeneration diff is the only instrument that sees this,
and it is sufficient because regeneration is deterministic.
*Judgment to make explicitly, not to default:* what "classified" should *emit*. A
`DESTRUCTIVE:`-style docstring line plus a confirm is the conservative answer; the
`--dry-run` from C3 is the better one. Measured alternatives, so the choice is
informed rather than guessed: a curated member-name vocabulary is 0%
false-positive at 62% recall; raw array shape is 53.8% false-positive. Neither
pure signal is good enough alone, which is the argument for the KIND detector.

**Two things this sequence deliberately does not do.** It does not add a confirm
to `wxcli cucm execute` — Phase 5 measured that `typer.confirm` on non-interactive
stdin aborts safely with exit 1 and zero API calls, which makes a confirm the
wrong instrument for an operator that has no TTY and that Phase 1 measured writing
`--force` on the *first* invocation 21 times and after a failure 0 times. And it
does not rename anything: every flag, command name, exit code and output shape is
committed public contract, so `--force`'s collision with a spec parameter on
`cc-flow delete` is fixed by emitting the bypass as `--yes` (a spelling four
commands already use), not by moving the published one.

---

## 4. Leave alone

This section is a deliverable, not a formality. The audit found more things that
*look* wrong and are right than it found defects, and a maintainer who "fixes"
any of the following makes the repository worse. Each carries the reasoning, so
that the next person to notice it can stop at the same place.

**Design decisions that are correct and already argued.**

- **`wxcli cucm execute` exits 0 even with `Failed: N`.** Decided and dated
  (`migration/execute/CLAUDE.md:374-418`); Phase 6 §6.3 and Phase 5 both agree.
  Partial failure is the expected mid-migration state, the documented recovery
  loop is `retry-failed` → `execute` repeated, and a non-zero exit would break a
  `set -e` wrapper around exactly that loop. Do not add `--fail-on-failures` —
  the note rejects it correctly as speculative surface. The *one* thing worth
  changing is the `--help` text, which mentions the exit behaviour on neither
  `execute` nor `preflight`, and those two commands now have opposite exit
  semantics inside one group.
- **The `httpx`-sync / `aiohttp`-async split itself.** Not one of the six
  behavioural disagreements is caused by the library choice
  (`06-machinery.md` §8). Unifying means making `auth.py` async — touching all
  1,857 generated commands and the published surface — or making the engine
  synchronous, which deletes the concurrency that is the entire reason
  `cucm execute` exists. Extract the policy; leave the transports.
- **The semaphore slot is released across the 429 sleep.** Settled with `ast`
  rather than by eye: the `async with semaphore:` block closes before the sleep
  (D6). Under rate limiting the engine does not deadlock its own concurrency
  pool. It is the *right* mechanism, and the resulting thundering herd is fixed
  by jitter, not by holding the slot.
- **`verify_ssl=False` on the CUCM AXL and Unity CUPI clients.** On-prem CUCM and
  Unity routinely run self-signed certificates; this is a defensible engineering
  choice and is not a defect. The defect beside it is the *silence* — a
  module-level `urllib3.disable_warnings` at `cucm/connection.py:27` affects the
  whole process, so nothing ever tells the operator the sessions are unverified.
  Fix the disclosure, keep the default.
- **The two `Console` objects in `commands/cucm.py`.** The stdout/stderr split is
  deliberate and documented at `:44-52` so that `report` / `user-diff` /
  `user-notice` can be piped into `jq`. The reasoning is right; `execute` is
  simply not covered by it, which is a one-line omission and not a design error.
- **Raw Webex response shapes reaching the CLI surface.** There is no intermediate
  model, so Webex's response schema *is* the CLI's output schema and `--fields` is
  a JMESPath expression over upstream field names. That is a legitimate design for
  a thin API wrapper and it is the reason the generator can exist at all. The
  consequence — an upstream shape change is a breaking CLI change with no layer in
  between — is real and belongs in the appendix, not in a refactor.
- **`docs/arch/deliberate-gaps.md` and the suppression surface.** ~214 of ~215
  entries across the allowlist and the five ack families are deliberate, carry a
  stated reason that still holds, and self-revalidate. **The allowlist is not
  where this gate went to die** — a real and unusual result. Do not audit it
  again; audit `_command_name` instead (appendix, F1).
- **The drift gate's CI wiring.** The `drift-gate` job is deliberately separate
  from `test` so a flaky unit test cannot mask a docs-drift failure, runs under
  `set +e` with `pipefail`, and treats **exit 2 as "crashed, did not run"** rather
  than "found nothing", asserting the last check completed. That control was added
  after a crash exit code was indistinguishable from a clean run. It is unusually
  careful and it works.
- **`_registry.py`'s manual manifest pruning.** It is the one generated artifact
  not reproducible from the specs alone, because it retains `cc_ai_assistant`
  whose upstream tag Cisco deleted. Deliberate, acked at
  `tools/field_overrides.yaml:1294`, and stated as a rule in `tools/CLAUDE.md`.

**Things Target B does better than the shared runtime, which should not be
"unified away."**

- **No process exit from library code.** `typer.Exit`, `sys.exit` and
  `SystemExit` appear **zero** times across all 46,684 lines of
  `src/wxcli/migration/`; the shared runtime terminates the process from library
  modules at eight sites, two of them inside `get_api()` — the one symbol Target B
  imports. On layering, **B is right and A is wrong.** Any "adopt the shared
  runtime" instinct must not travel in that direction.
- **Testability without a terminal or a network.** Three files in 46,684 import
  Typer or Rich; three import an HTTP or SOAP client. 31,570 lines have no
  transport dependency at all. That is why 3,122 tests run in ~90 seconds, and it
  is the direct architectural counterpart to Target A's problem (a generated
  command is one decorated function with no unit between the decorator and the
  socket).
- **AXL failure handling.** Per-extractor typed status
  (`ok`/`partial`/`failed`/`unsupported`), an accumulated record of what a schema
  mismatch dropped, hand-written remediation for the two common connect failures,
  and a hard abort when nothing was extracted. It is *more* legible than the Webex
  write path in the same subsystem. Leave it; copy from it.
- **`execute/dependency.py`.** Five commits, and every one of its five functions
  has exactly one — all the churn landed in a declarative `_CROSS_OBJECT_RULES`
  table. The DAG that determines execution order and cascade-skip topology was
  factored so that new knowledge is a data row, not a code edit. That is the shape
  the six render paths do not have.
- **`wxcli init`'s write path.** It computes collisions up front, refuses rather
  than clobbers, skips rewriting files whose bytes already match, and its deletions
  are manifest-scoped — it never deletes a file it did not create. The most
  careful write path in the repository. (`--uninstall`'s missing confirm is a real
  gap and is in the appendix; the rest is exemplary.)
- **The dry-run's shared batch ordering.** `dry_run_all_batches` and
  `execute_all_batches` call the *same* `get_next_batch`, so the two paths cannot
  disagree about ordering — the drift risk the audit anticipated does not exist.
  What dry-run does not model is everything downstream of the handler, which is a
  scope gap and is in the appendix.

**Claims that were retracted, so nobody goes looking again.**

- **"51 commands are hidden and undiscoverable."** Retracted. Fifty hidden
  `@app.command` decorators are backward-compatibility aliases on functions that
  *also* carry a visible name, plus one hidden *option* (`--hook` on
  `wxcli update`, which exists for the bundled `SessionStart` hook and is
  correctly hidden). **Zero capabilities are reachable only by a hidden name.**
  The "hidden destructive command" cell is empty.
- **"Fixes applied to generated files, reverted by the next regeneration."**
  False. 172 of 172 modules regenerate byte-identical; there are zero hand-edits.
  Every correction in this repository's history went through the generator, the
  overrides file or the overlays.
- **"The confirm gate is unreachable or confusing without a TTY."** The opposite:
  closed stdin, empty stdin and an explicit `n` all abort with exit 1 and **zero
  API calls**, because Click raises the same `Abort` for EOF as for "no". The
  guard fails safe. What is missing is only the recovery instruction — the entire
  output is the prompt echo plus `Aborted!`, naming no flag.
- **"`migration/rate_limiter.py` is Target B's retry policy."** It is dead code
  imported by nothing in `src/`, and none of its five declared parameters is in
  force. **Delete it** rather than reviving it, and fix
  `docs/architecture/04-operations-and-evolution.md:357`, which points the next
  contributor at it.
- **"Unity is a third external system the pipeline reads."** A complete, tested,
  correctly-degrading CUPI client exists and **has no caller** — nothing
  constructs it, and no CLI option supplies credentials. Its two defects are
  latent, not live.
- **"`pytest.mark.live` is a dead filter or mis-selects."** Neither: the marker is
  correctly registered and carried by zero tests, so `-m "not live"` deselects
  nothing. What keeps live code out of CI is pytest's filename glob and
  `.gitignore`. Do not "fix" the marker; understand that it guards nothing.

**High churn that is growth, not indecision.** `tools/drift_check.py:main` at 15
commits is 21 checks added one at a time. `tools/field_overrides.yaml` at 53
commits is the answer to *"what does the OpenAPI spec fail to say?"*, answered
incrementally and monotonically. `appendix.py`'s report renderers at 4–14 commits
each are new lettered sections. None of these is an unresolved ambiguity, and
`08-history.md` is explicit that on this repository **churn ranks attention, not
correctness** — the code with the fewest commits on the write path is the code
nobody has read.

---

## 5. Appendix

### 5.1 Corrections — claims in `docs/audit/` that are wrong

The phase artifacts remain on disk and are read in phase order, so a future
reader will hit the superseded values. Each was overturned by a later
measurement.

| Claim | Where it came from | Corrected to |
|---|---|---|
| Target B's retry policy is `migration/rate_limiter.py` (`max_concurrent=5`, `base_delay=1.0`, …) | `00-facts.md` Q7 | **Dead code, imported by nothing in `src/`.** The policy in force is inline in `execute/engine.py` and shares no parameter with it |
| Recorded AXL responses exist; Webex has none, so Target A can be pinned cheaply and Target B cannot | `00-facts.md` Q15 | **Neither exists.** Zero non-`.py` files are tracked under `tests/`; the AXL fixtures are gitignored *and* referenced by nothing. The asymmetry the remediation was planned around is not real |
| Unity is a third external system the pipeline reads | `00-context.md` Q4, refuting `00-facts.md` Q6 | **Both wrong, oppositely.** The module is real and tracked, but `UnityConnectionClient` is constructed nowhere in `src/` — no `wxcli` command can reach Unity |
| 51 commands are hidden and undiscoverable | audit spec KNOWN CONTEXT; `00-facts.md` Q4a | **Retracted.** 50 hidden aliases on functions that also carry a visible name, plus one hidden *option*; zero capabilities are hidden-only |
| "244 test files, 240 tracked" — 4 untracked | `06-machinery.md` §0/C2a | **Two denominators.** 244 `test_*.py` on disk vs 222 tracked → **22 untracked** at the time of measurement; **18** today |
| The shared runtime has 6 library-layer process exits | `06-machinery.md` §4 | **8** — `auth.py:398` and `:405` are inside `get_api()`, the one symbol Target B imports |
| The array/object flag drop is 476 fields / 142 commands | audit spec `:454`, `:463` (unsourced) | **696 fields / 394 commands**, by two independent methods that agree to the field |
| Two commands are left with zero scalar flags | `05-safety.md` §2.1 | **92**, three confirmed live at `--help` |
| CUCM AXL calls have a 30s timeout | `06-machinery.md` §7.1, first draft | **Unbounded.** `Transport(timeout=…)` governs WSDL loading; SOAP calls use `operation_timeout`, never set |
| 409 auto-recovery covers 7 resource types | `migration/execute/CLAUDE.md` | **8** — `line_key_template` is uncounted |
| "132 transcripts, 157 `wxcli` invocations" | audit spec STATUS; `PHASE-1-HANDOFF.md` | **569 transcripts, 2,062 invoking Bash calls.** 88% come from *subagent* transcripts, which both prior counts omitted entirely |
| The `wxcli-gate.sh` header: "four unconfirmed DELETEs reached the live org" | `.claude/hooks/wxcli-gate.sh:41-44` | **Three reached the network**; the fourth was stopped by a local config guard. Two of the four are dev-only modules absent from the wheel |
| "779 ungated POST/PUT/PATCH commands" | `00-facts.md` Q10 | **755** since 2026-08-04 |
| "`--verify` on 328 update commands" | `CLAUDE.md` | **332**, counted twice independently. 328 of them sit on ungated writes — the coincidence is arithmetic, not agreement |
| The working tree carries 28 uncommitted files / `docs/audit/` is untracked | `FINAL-REPORT-HANDOFF.md`; `PHASE-8-HANDOFF.md` | **Stale.** Tree is clean at `05739b5`; `docs/audit/` is tracked (21 files); `docs/arch/` is not (0 files) |
| The two tests pinning the 2026-08-05 fixes are untracked | `07-testability.md` measurement window note | **Tracked**, along with the two pinning the `plan`/`normalize` and preflight-gate fixes `[verified this session]` |

### 5.2 Everything else

One line each. Nothing here reached the top three; several are cheap and worth
doing anyway. `T` = target.

| T | Finding | Cite |
|---|---|---|
| A | `_command_name` resolves to the **hidden** alias, so checks 6/9/10/11a/11b silently skip 50 renamed commands under the names the docs cite. Fixed in `command_names()` for checks 13/14 and never propagated | `02-drift.md` F1 |
| A | `cc-ai-assistant create` calls an endpoint a recorded probe proved returns 404; three suppressions hold it alive because removing it would move the published count check 3 enforces. The one quieted finding in ~215 entries | `02-drift.md` F2 |
| A | Check 20 asserts a group name appears *somewhere* in *some* doc and reports it as "coverage" — a "NOT `contact-center`" table row satisfies it | `02-drift.md` F4 |
| A | Check 19 encodes no field **type**, so `string`→`integer` with unchanged prose produces zero diff; it is request-side only | `02-drift.md` F5 |
| A | A response-shape change is invisible, and check 9 — the check a reader would trust — **re-derives its oracle from the post-rename schema**, so both sides move together | `04-generator.md` §4.3 |
| A | Renderer selection pattern-matches URL segments: POST→`action` needs a literal `actions`/`invoke`, so Cisco's `…:publish` convention falls through to `create`. 11 operations; 4 ship today as `create-lock`/`create-unlock`/`create-validate`/`create-import` | `04-generator.md` §5.1 |
| A | `_render_action_command` renders boolean body fields as `str` — no `--x/--no-x`, and the value reaches the wire as the JSON *string* `"true"` while the skeleton on the same help screen shows a boolean. 11 fields / 9 operations | `04-generator.md` §2.3 |
| A | A delete reports a different outcome depending only on `--output`: `-o table` prints `Deleted:`, `-o json` prints `{"status":"removed"}`. 9 operations; 8 also confirm with the wrong verb | `04-generator.md` §2.4 |
| A | The generator imports `wxcli.common`, which an editable-install `.pth` resolves to a **different checkout**. Regenerating in a second clone silently uses the first one's source — exit 0, no warning | `04-generator.md` §6.1 |
| A | The `Functions` skip reason (*"generator cannot render ':' path segments"*) is **false** — the sibling `Flow` tag's colon-action operations render today. 5 operations documented as impossible are an unrevisited choice | `04-generator.md` §5.3 |
| A | The spec refresh's only human-readable review artifact is printed once to a terminal and captured nowhere — not CI, not the commit message. The durable file stores hashes | `04-generator.md` §4.2 |
| A | `tools/field_overrides.yaml` is 2,729 lines, monotonically growing, with **no obsolescence check** — nothing asks whether an override still matches a live spec field | `08-history.md` §8 item 4 |
| A | 87 commands carry a `--json-body` that can do nothing (no body fields); `_render_action_command` has no no-body result branch, so a 204 reaches `emit(None, …)` on up to 57 | `04-generator.md` §2.5 |
| A | `--force` collides with a **spec** parameter on `cc-flow delete` (typed `str`): `--force yes` *and* `--force no` both skip the confirm, and bare `--force` — the idiom that works on 202 other commands — is a parse error. `cc-notification`/`cc-realtime` spell `--force` meaning "drop this user's live connections" | `05-safety.md` §2.3 |
| A | 89% of confirm prompts interpolate one opaque token and nothing else; 15 name a value the operator never typed (a session-resolved org id, on a purge); 5 say only `Delete this resource?`; `cc-tasks delete-preview-task` names the **wrong** id | `05-safety.md` §2.4 |
| A | The abort prints the prompt echo and `Aborted!` and names no flag; exit 1 collides with REST and network failure. `"Error:" in stderr` distinguishes them and nothing says so | `05-safety.md` §2.2 |
| A | 423 of 958 mutating commands resolve their target org from ambient config; `switch-org` **saves an unvalidated orgId** whose only failure signal is the word `Unknown`; no mutating command or confirm string ever prints the target org | `05-safety.md` §2.6 |
| A | `location-settings create-delete-calling-location` disables calling for an entire location, has **no confirm at all**, and its `--force-delete` flag removes the *server-side* safe-delete checks — the inverse of `--force`'s meaning on 202 commands | `05-safety.md` §2.3 |
| A | 21 collection-scoped DELETEs prompt naming the container and never the count or the members: `numbers delete` asks `Delete Numbers for {location_id}?` whether the body holds one number or forty | `00-context.md` Q1 class 5 |
| A | 14 mutating commands POST to a `/jobs/` endpoint — the largest generated blast radius — and all 14 are POSTs, hence ungated; 37 more POST/PATCH to a `/bulk` path, of which the ~30 CC ones have no discoverable array-size limit | `00-context.md` Q1 classes 3–4 |
| A | A required positional accepts the **empty string**, and the resulting malformed URL is sent to the live API; the operator gets a *resource* error for an *argument* error. Observed twice in real transcripts. Fixable at the generator, upstream of 1,887 commands | `01-observed.md` §1.3a |
| A | The output envelope varies by endpoint and nothing at the CLI surface declares which shape a command returns; the only failure mode that repeats verbatim across commands and sessions is `AttributeError: 'list' object has no attribute 'get'` | `01-observed.md` §1.5 |
| A | 40 of 81 observed failures name **no next action**; 17 are raw remote JSON carrying a `trackingId` and nothing actionable. 63 of 81 exit 1, so validation, transient and remote rejection are indistinguishable by exit code | `01-observed.md` §1.2–1.3 |
| A | 43% of 1,933 recorded invocations carry `--help`, across 130 groups — the intended design working, and the price of not having a machine-readable command index (~837 subprocess launches). Token/wall-clock cost not measured | `01-observed.md` §1.1 |
| A | 224 of the 696 dropped body fields are `UNKNOWN` — the spec never states whether omitting them removes anything. 198 are object-typed on a PUT/PATCH; 78 have no description at all, and 28 more have one the parser discards | `04-generator.md` §1.5, §6.2 |
| A | `wxcli init --uninstall` deletes files with **no confirmation**: it returns before the `--force`/`--yes`/`confirm` logic is reached, and `do_uninstall` has none of its own. Bounded by the manifest | `06-machinery.md` §7.4 |
| B | `_try_find_existing` returns `items[0]` from an un-paginated search with **no name-equality check**, so a 409 on creating `HQ` can bind the operation to `HQ-Backup`, mark it completed, and point every dependent at the wrong object. Whether Webex's `name=` filters are exact-match is **`UNKNOWN`**; the one-line check makes the question moot | `06-machinery.md` D8 |
| B | `WORKSPACE_LICENSE_ID` is read by the workspace handler and **set by nothing**, so every `workspace:create` omits the license; `CALLING_LICENSE_ID`'s "no matching license" case is announced by nothing and creates **unlicensed users**; the license lookup is a single fetch, not `follow_pagination` | `06-machinery.md` D10 |
| B | 62 loggers, no handler configured on the execute path — the two events an operator most needs from an unattended run (*we were rate-limited*, *we adopted a resource we did not create*) are DEBUG and INFO and therefore unobservable, while five WARNING calls reach stderr with no logger name, level or timestamp | `06-machinery.md` D11 |
| B | `execute` prints errors to **stdout**, inverting the tool's own convention on the one command an operator is most likely to pipe; 17 of 27 `cucm` leaf commands carry neither `-o/--output` nor `--fields`, including `execute` and `retry-failed` | `06-machinery.md` §6.4 |
| B | Webex error bodies containing an `errors` array are stored as a Python `repr` in `plan_operations.error_message` and read back by `execution-status` — routinely including submitted emails and DIDs. **PII at rest in a file nobody has declared as holding PII** | `06-machinery.md` §6.5 |
| B | `plan_operations` has **no `run_id` column**, so two `execute` invocations of the same project are indistinguishable in the store and in every log line — which is why "was this op attempted in the run that died?" cannot be answered after the fact | `06-machinery.md` §4 |
| B | `dry-run` certifies **ordering and counts only** — it never resolves a handler, so it cannot say what will be sent, and its `~N API calls` is a planner estimate. It is the artifact the skill shows a human for approval before an irreversible bulk write. It also **leaves no trace it ran**, so no future check can require it | `05-safety.md` §1.3–1.4 |
| B | The approval record exists — `decisions.resolved_by`, durable and attributed — and `execute` never reads it; `plan --fail-on-unresolved` defaults to false; `BLOCKED` is a state the project passes *through*; and nothing in the tool ever advances a project past `PREFLIGHT`, so `status` reports `preflight` after a completed migration | `05-safety.md` §1.2 |
| B | 13 of 21 create-capable resource types have no 409 recovery (6 decline it deliberately, 7 have no branch). Whether a re-issue duplicates or hard-fails is **`UNKNOWN` per type** and needs a live create to settle | `05-safety.md` §1.6 |
| B | `cucm/` is the lowest-covered stage at 67%, concentrated in the AXL extractors (24–46%) — which produce the input the 93%-covered `transform/` stage consumes. A well-tested mapper fed by a shape nobody has pinned | `07-testability.md` §2.6 |
| B | AXL *detail* faults lose their text entirely: `get_detail` logs a warning, returns `None`, and the extractor records a bare `"getPhone failed for {name}"`. The faultcode is never read anywhere, and the `ok/partial/failed` label is persisted but not shown live | `06-machinery.md` §7.2 |
| both | The `PreToolUse` hook that enforces the read-only verb policy and blocks importing `wxcli` from Python **does not ship**; what ships in its place blanket-allows `Bash(wxcli:*)` while the shipped `CLAUDE.md` says "do not run `wxcli` commands directly". Rule shipped, enforcement dropped. **Phase 5 and Phase 1 disagree on whether it should ship** — Phase 5 argues a deny-gate would break the agent it routes to; Phase 1 measured that 28 of 126 blocks were the main session trying to run `wxcli` directly, that the script has no machine-specific paths, and that the routing target already ships. **Open decision, and the disagreement is deliberate — Phase 1's evidence is measured, Phase 5's is reasoned** | `05-safety.md` §2.7; `01-observed.md` §7.1 |
| both | **412 Bash calls across 108 transcripts import the CLI package from Python** — ~20% the size of the `wxcli`-command class, with full capability and **no argv**. Any instrumentation attached at the argv layer inherits that blind spot, including for the one near-miss in this repository's history | `01-observed.md` §5 |
| both | Whether a single fetch that left pages behind is *noticed* by the operator is **`UNKNOWN` and unanswerable by mining** — the note appears in 2 of 1,933 results, because the sandbox org has ~16 people. A counter on the paging path would answer it in a week on any real org, adds no remote requests, and unlike the hook it would ship | `01-observed.md` §3.3, §7.3 |

---

## 6. Read coverage

Stated per target, aggregated from `06-machinery.md` §9 and `07-testability.md`
§7 rather than re-derived. Where a phase said "not measured", this says so too.

**Target A — the generator, the templates, the specs, the shared runtime.**

- **Read in full:** `tools/command_renderer.py` (2,240 lines — every render path,
  every helper cited, and the full uncommitted diff at the time),
  `tools/postman_parser.py`, `src/wxcli/auth.py`, `errors.py`, `config.py`; the
  relevant halves of `tools/openapi_parser.py`; `.gitignore`; `ci.yml`'s test and
  gate jobs; `.claude/hooks/wxcli-gate.sh`.
- **Read in the regions that matter:** `tools/generate_commands.py`'s override
  plumbing; `check_parity` and the check call site in `tools/drift_check.py`;
  `src/wxcli/common.py`'s `emit`/`verify_write`; `main.py`'s org commands;
  `commands/{init_playbook,update,device_settings,call_queue}.py` in their
  write/confirm regions.
- **Parsed, not read:** all 184 tracked modules in `src/wxcli/commands/` (`ast`,
  for every structural count in this report) and all nine tracked `specs/*.json`
  (`json.load`).
- **Executed:** the generator over all nine specs, four times across two throwaway
  clones and two Python versions; `drift_check --enforce` clean and mutated; all
  22 then-untracked test files individually; the tracked root suite under
  coverage; the full tracked suite three times in a clone.
- **Sampled or skipped, and extrapolated:** `tools/drift_check.py` was read
  check-by-check by four parallel workers producing the four
  `02-detail-*.md` working papers, with every load-bearing claim re-run — but no
  single reader read all 3,899 lines. **Statement coverage of `tools/` was not
  measured** (the run was interrupted); the tracked/untracked status of the
  generator's test files is measured and is what the coverage claim rests on. The
  generated command modules were read only as samples — the claim that they are
  correct rests on regeneration byte-identity, not on reading them.

**Target B — `src/wxcli/migration/` (46,684 lines) and `commands/cucm.py`.**

- **Read in full:** `execute/engine.py` (964), `execute/runtime.py` (571),
  `cucm/unity_connection.py` (304), `preflight/__init__.py` (96),
  `migration/state.py` (139), `rate_limiter.py` (145), and
  `migration/execute/CLAUDE.md` + `preflight/CLAUDE.md`.
- **Read in the regions that matter, grepped elsewhere:** `commands/cucm.py`
  (3,525 lines — roughly 900 lines read across the stage-gate, discovery,
  preflight, execution-status and execute regions; the rest grepped);
  `execute/handlers.py` (2,403 — three of 67 handlers read); `execute/batch.py`;
  `migration/store.py`; `cucm/connection.py`; `preflight/{runner,checks}.py`.
- **Parsed, not read:** all 209 tracked migration test files (import analysis and
  LOC).
- **Executed:** `tests/migration` under coverage (3,085 → 3,122 after the
  2026-08-05 fixes), plus targeted files in `execute/` and `preflight/`. Two
  store-level behaviours were proven against a throwaway SQLite database rather
  than read off the source.
- **Never read by any phase — and this is the honest limit of this report:**
  **`transform/` (18,517), `report/` (8,302), `advisory/` (3,738) and `export/`
  (1,013) — 31,570 of Target B's 46,684 lines, 68% of the subsystem.** The
  justification is that `00-context.md` Q4 establishes none of them makes any
  remote call and `07-testability.md` §2.1 confirms it from the import side (they
  import no HTTP or SOAP client at all), so a programme scoped to safety, the two
  stacks and the remote-write path does not reach them. It is a justification, not
  a substitute. Also unread: `execute/planner.py` (2,552), `execute/dependency.py`
  beyond its churn profile, `migration/models.py`, `decision_state.py`, and the 13
  AXL extractors.

**Claims this report is explicitly not making.** That `transform/`, `report/`,
`advisory/` or `export/` are clean — nobody read them. That the 67 handlers in
`execute/handlers.py` are correct — three were read. That the 755 ungated writes
are individually safe — one class within them was characterized and the rest are
uncharacterized. That the 682 passing previously-untracked tests assert anything
useful — they were run, not read. That coverage is correctness anywhere. And that
the two mutations in `07-testability.md` §2.5 are the worst available — they are
the two the prior phases pointed at.

**One methodological note worth carrying.** Every figure of coverage in this
report is **statement** coverage, which is the weaker measure, so every gap named
here is a floor rather than a ceiling. The worked example is `engine.py:200`'s
unguarded `int(Retry-After)` — a real latent defect on a line that reports as
covered.

