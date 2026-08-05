# Handoff prompt — FINAL REPORT

Paste everything below the line into a new Claude Code chat. **Run this last**, after
Phases 5, 4+3 and 8 (and Phase 1, if it was run).

---

You are writing the final deliverable of an eight-phase architectural audit of the
wxops repository at /Users/ahobgood/Documents/webexCalling. Write
`docs/ARCHITECTURE_AUDIT.md`. Do not start a new investigation.

## This document ships. Every other audit artifact does not.

`[verified]` `docs/arch/` is gitignored (`.gitignore:45`) and `docs/audit/` is
untracked. **`docs/ARCHITECTURE_AUDIT.md` sits at a tracked path** — it is the only
part of this audit that enters the repository, survives a clone, and is read by
anyone who was not in these sessions. Write it for that reader: a maintainer six
months from now with no memory of the phases.

Confirm the path is not ignored before you finish (`git check-ignore --no-index -v
docs/ARCHITECTURE_AUDIT.md` should report nothing).

## Read these, in this order

1. `docs/arch/wxops-architecture-audit-prompt_2.md` — **STATUS in full** (it records
   what was overturned and what was already remediated), ROLE, KNOWN CONTEXT, HARD
   CONSTRAINTS, and **FINAL REPORT** (the required structure). Skip the phase bodies.
2. `docs/audit/00-facts.md` — the numeric authority.
3. `docs/audit/00-context.md` — Phase 0, especially Q1 (the six classes of org-wide
   mutation) and Q4 (the Target B stage map).
4. `docs/audit/02-drift.md` — Phase 2, especially §6 and F3.
5. `docs/audit/06-machinery.md` — **in full.** The largest single input. §8 is a
   remediation sequence already written; §10 lists its corrections.
6. `docs/audit/07-testability.md` — **in full.** §2.5 constrains every remediation
   step you will write. §8 lists its corrections.
7. `docs/audit/05-safety.md` — Phase 5.
8. `docs/audit/04-generator.md` — Phase 4 + Phase 3 item 4.
9. `docs/audit/08-history.md` — Phase 8, if it was run.
10. `docs/audit/01-observed.md` — Phase 1, if it was run. **If it exists, it
    outranks inference**: it is the only evidence about what actually fails.

Consult as needed: the four `docs/audit/02-detail-*.md` working papers,
`docs/audit/00-facts-independent.md`, `00-facts-independent-part2.md`.

## Required structure — this is not negotiable

From the spec's FINAL REPORT section:

**1. Verdict** — 5 sentences. Structurally sound / sound with localized rot /
compromised. **One verdict per target.** A repo can be sound in its generated half
and compromised in its hand-written half; a single blended verdict would hide exactly
the thing this audit was widened to find.

**2. The three things that matter.** **Exactly three**, and **at least one must
belong to each target.** If all three land on the generator, or all three on the
migration subsystem, you have audited one and glanced at the other. For each: what's
there, why it's expensive *given generation, publication, and an autonomous
operator*, the correct shape, and what it costs. If you cannot reach three, your
severity judgment is wrong — try again.

**3. Sequenced remediation for those three.** Per step: what changes, blast radius,
and **how to pin current behaviour first.** See *The constraint*, below — this section
is where the audit's central result lands.

**4. Leave alone.** Non-standard but correct, plus wrong-but-not-worth-fixing.
**Be generous.** This section is a real deliverable, not a formality: the audit found
several things that look wrong and are right, and a maintainer who "fixes" them makes
the repo worse. Candidates already argued: `cucm execute` exiting 0 (Phase 6 §6.3
agrees with the decision), the `httpx`-sync / `aiohttp`-async split itself (§8 — not
one disagreement is caused by the library choice), the semaphore released across the
429 sleep (D6 — right on the mechanism), `verify_ssl=False` for on-prem CUCM/Unity
(§7.3 — defensible; the defect is the silence, not the default), and the two-`Console`
split in `cucm.py` (§6.4 — the reasoning is right, `execute` is simply not covered).

**5. Appendix: everything else** — table, no narrative.

**6. Read coverage** — read fully / sampled / skipped, and what you extrapolated,
**stated per target.** Target B is 46,684 lines; an honest report says which stages
were actually read and which were inferred from neighbours. `06-machinery.md` §9 and
`07-testability.md` §7 both state theirs — aggregate them, do not re-derive them.
Note explicitly that `transform/`, `report/`, `advisory/` and `export/` — 31,570 of
Target B's lines — were never read by any phase.

## The constraint that reshapes section 3

**The spec's own §3 rests on a premise that is false, and you must not reproduce it.**
It says Target A can be pinned cheaply by regenerating and diffing while Target B has
no recorded Webex responses, "so any Target B remediation must begin by recording
them." Measured:

- **There are no recorded remote responses for any system** — not Webex, not AXL.
  `tests/fixtures/axl-responses/` is gitignored *and* referenced by nothing
  (Phase 6 §0/C2). The asymmetry does not exist.
- **Nothing in CI pins either stack's behaviour.** Proven by mutation, not inferred
  (Phase 7 §2.5): with `RETRY_STATUSES = frozenset()`, a 24-hour `Retry-After` cap,
  and the engine's 429 branch disabled, the full suite reports **3,580 passed** and
  the drift gate reports **PASS**. A second mutation reclassifying every HTTP 4xx/5xx
  on the migration write path as *success* is likewise green on both.
- **22 test files are gitignored**, three are silently red, and **all four of the
  generator's test files are among them** (Phase 7 §0/C1, §3.3, §3.4).

So *"how to pin current behaviour first"* is not a footnote per step — **it is the
first step of the whole sequence**, and it is cheaper than the spec assumes because
`aioresponses` is already installed by CI (`ci.yml:35`) and already used by six
migration test files. Phase 6 §8 wrote the sequence; Phase 7 §5 amended it (repairing
`test_auth.py` is necessary but **not sufficient** — `_request` and
`follow_pagination` stay uncovered unless cases are added for them). Start from those
two, do not re-derive them.

**And apply F3's rule to everything you propose:** no gate check asserts that a
destructive command has a guard, so any guard must ship with the check that pins it —
and per Phase 7, **that check must live in a git-tracked file.** A guard pinned by an
untracked test is a guard pinned by nothing, and this repo has already produced three
examples.

## Corrections to carry into the report

Six claims from earlier artifacts were overturned. The report should reflect the
corrected values silently in its own prose — **and list the corrections in the
appendix**, because `00-facts.md` and `00-context.md` remain on disk and a future
reader will hit them.

| Claim | Where it came from | Corrected to |
|---|---|---|
| Target B's retry policy is `migration/rate_limiter.py` | `00-facts.md` Q7; spec `:264` | **Dead code, imported by nothing.** Policy is inline in `execute/engine.py` and shares no parameter with it |
| Recorded AXL responses exist; Webex has none | `00-facts.md` Q15; spec `:282`, `:326` | **Neither exists.** Zero non-`.py` files tracked under `tests/` |
| Unity is a third external system the pipeline reads | `00-context.md` Q4 (refuting `00-facts.md` Q6) | **Both wrong, oppositely.** Module is real and tracked, but `UnityConnectionClient` is constructed nowhere in `src/` — no command can reach Unity |
| 51 commands are hidden and undiscoverable | spec KNOWN CONTEXT | **RETRACTED.** 50 hidden aliases on functions that also carry a visible name + one hidden *option*; zero capabilities hidden-only |
| "244 test files, 244/240 tracked" — 4 untracked | `06-machinery.md` §0/C2a | **Two denominators.** 244 `test_*.py` on disk vs 222 tracked → **22 untracked** |
| The shared runtime has 6 library-layer exits | `06-machinery.md` §4 | **8** — `auth.py:398`, `:405` are inside `get_api()`, the one symbol Target B imports |

Also already remediated on 2026-08-04 and reflected in current counts: **24
destructive non-DELETE commands now carry a confirm and `--force`**, so "779 ungated
writes" is **755** everywhere.

**And remediated on 2026-08-05 by Phase 5, under the remediation rule** — the report
must describe the *current* behaviour, not the behaviour the earlier phases measured:

- **D13 is fixed.** `in_progress` is now written before dispatch
  (`runtime.py:mark_ops_in_progress`, called from `engine.py:924-934`), so a
  half-applied migration is no longer byte-identical to a not-yet-started one.
  `06-machinery.md` D13 and `07-testability.md` describe the pre-fix state.
- **The preflight bulk-job probe is fixed and its failure now stops the gate.**
  `checks.py` returns `INCOMPLETE` rather than `WARN`, and `cucm.py:1797` widened to
  `(FAIL, INCOMPLETE)` — the paired change Phase 6 §5.1 said was required, made in
  the same commit. `05-safety.md` §3.1–§3.2 is the record.

**One open item to carry into section 3.** The two tests pinning those fixes —
`tests/migration/execute/test_in_progress_written.py` and
`tests/migration/preflight/test_bulk_job_probe.py` — are **untracked** as of
2026-08-05 `[verified]`. They are not gitignored (the `!tests/migration/**`
re-include covers them); they were simply never `git add`ed. **This is the report's
third finding demonstrating itself in real time**, and it is worth one sentence in
section 2 or 3: the repository's fix workflow does not currently end at "staged," so
a correctly-pinned fix can still reach `main` with its test invisible to CI. The
remedy is one `git add`, which is precisely why it is worth naming — the failure is
procedural, not technical.

Check this before writing: if they have since been staged, say so and drop the item.
`git ls-files --error-unmatch <path>` settles it.

## How to fail at this

The spec's ROLE says it directly: **"a long findings list is a failure mode, not a
deliverable."** Seven phases produced roughly 6,000 lines of findings. The report is
**three things**. Everything else goes in the appendix table with one line each, or
into "Leave alone."

Three more specific traps:

- **Do not quote an aggregate coverage number.** The spec is explicit that the
  aggregate actively misleads here, because 209 of 240 tracked test files are one
  subsystem. Report per-target figures or none. The illustrative case is worth one
  line in the report: `rate_limiter.py`, which nothing imports, is 96% covered, while
  `engine.py`'s failure branches — on the only path that writes to a customer's org —
  are at 0%.
- **Do not blend the verdicts.** Target A is in good shape and that is a *result*.
  Say so plainly and early; an audit that cannot report health is not measuring.
- **Do not re-derive.** Every number in this report should be traceable to a phase
  artifact. If you find yourself running `git ls-files` to check a count, you are
  writing a ninth phase.

## Repo-specific constraints

- **The interpreter is `/opt/homebrew/opt/python@3.14/bin/python3.14`.**
- **`wxcli` CANNOT be imported from Python.** A hook blocks it, matching the string
  `import wxcli` anywhere in a Bash command.
- **Never run a mutating `wxcli` command.** This repo points at a live org.
- **Do not run the full pytest suite in the working tree** (project rule). You should
  not need to run anything — this session reads and synthesises.
- **`docs/arch/` and `docs/audit/` are gitignored/untracked; `docs/ARCHITECTURE_AUDIT.md`
  is not.** That asymmetry is the point of this session.
- **The working tree is NOT at `b578a52`.** 28 tracked files are modified and
  uncommitted: `tools/{command_renderer,generate_commands}.py`,
  `tools/field_overrides.yaml`, `tests/test_field_overrides.py`, 23 regenerated
  command modules, and `docs/architecture/04-operations-and-evolution.md`.
  **Say so in the report** — the code it describes is not the code at HEAD, and a
  reader diffing against HEAD needs to know.

## Rules

Every finding cites `path:line`. Label claims `[verified]` or `[inferred]`;
`UNKNOWN` is a correct answer. Do not estimate LOC, effort, or percentages unless a
phase counted them — say "did not measure." Never propose a fix to a generated file
(HARD CONSTRAINT 5); trace it to the spec, generator, or template. Name the target
for every finding. Be fair: the report's credibility rests on section 4 as much as
section 2.

**One judgment this report must make that no phase made.** Each phase judged severity
within its own scope. Nobody has yet ranked a generator defect against a migration
defect on one scale. That ranking *is* section 2, and it is the reason the audit had
two targets. Make the call explicitly and show the reasoning — do not present three
items in phase order and let the reader infer priority.

Stop after writing `docs/ARCHITECTURE_AUDIT.md`. Do not begin remediation; the
sequence in section 3 is the deliverable, not the work.
