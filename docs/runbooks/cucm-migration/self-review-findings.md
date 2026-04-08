# Phase 2 — Self-Review Findings

This document collects the drift, self-walkthrough, and external review
findings produced during Phase 2 Wave 4 (integration + verification).
It is committed alongside the runbooks so future readers understand
both what made it into the runbooks AND what was deliberately left
alone.

Sections are appended in execution order: §Spec Drift first (E1),
then §Author Self-Walkthrough (G5), §External Reviewer Pass (G6),
§Assessment Report Drift (G7), and §Drift Outside Phase 2 Scope
(rolling, populated as drift is noticed in passing).

## Spec Drift (frozen — not fixed)

These items diverge from the Phase 2 spec
(`docs/plans/transferability-phase-2.md`) but were intentionally
**not** "fixed" during Wave 4 because fixing them would have broken
other Wave 3 work or contradicted higher-priority spec rules.

### 1. KB doc Dissent Trigger sections pre-existed Phase 2 by 10 days

**What:** All 8 KB docs in `docs/knowledge-base/migration/` already
had `## Dissent Triggers` sections with 3-5 entries each before Phase
2 started. Commits `4baf927` and `1eeb0b2` (both 2026-03-28, 10 days
before Phase 2 kicked off) populated them as part of the
migration-advisor Phase B work.

**Spec implication:** Spec §Artifact 4 was written assuming the KB
docs did NOT have these sections yet. Phase E was scoped as a
"write from scratch" task; in reality it is a backfill + repair
task for dead anchor refs created by Wave 3.

**Why not "fix":** The pre-existing entries are correct, well-cited,
and load-bearing — Wave 3 runbook writing assumed they were the
authoritative source. Rewriting them per the spec's later "from
scratch" instructions would have lost real content.

**Decision:** Phase E was rescoped (per
`docs/plans/transferability-phase-2-plan-wave4-revised.md`) to
backfill, retarget, and repair only — not rewrite.

### 2. KB prefix mismatch: DT-ID/DT-TRUNK/DT-USER vs spec's DT-IDN/DT-TRK/DT-USR

**What:** Spec §Artifact 4 line 207 prescribes a prefix table:
DT-CSS, DT-DEV, DT-FEAT, **DT-IDN**, DT-LOC, **DT-TRK**, **DT-USR**,
DT-LIMITS. Three of these do not match the existing entries on
disk:

| File | Existing prefix | Spec prefix |
|---|---|---|
| `kb-identity-numbering.md` | `DT-ID` | `DT-IDN` |
| `kb-trunk-pstn.md` | `DT-TRUNK` | `DT-TRK` |
| `kb-user-settings.md` | `DT-USER` | `DT-USR` |

**Spec implication:** The spec is internally contradictory. The
same artifact says (a) use these prefixes AND (b) "IDs are stable —
never renumber." The existing IDs are load-bearing — Wave 3
runbooks already forward-reference them.

**Why not "fix":** The "never renumber" rule wins. Renaming
DT-ID/DT-TRUNK/DT-USER to match the spec would break ~30 cross-file
references in the Wave 3 runbooks (and any external readers who
already have these anchors bookmarked).

**Decision:** Keep existing prefixes. Phase E backfills use the
existing prefix per file (DT-USER-004/005/006 not DT-USR-004/005/006,
DT-TRUNK-004/005/006 not DT-TRK-004/005/006). Spec drift recorded
here.

### 3. DT-FEAT-001 content drift

**What:** Spec §Artifact 4 example shows DT-FEAT-001 as "Feature
approximation — Hunt Group vs. Call Queue ambiguity at 5-8 agents."
Actual `kb-feature-mapping.md` line 148 has DT-FEAT-001 as "Queue
indicators fire on default CUCM values" — a different topic
entirely.

**Spec implication:** The spec example was an aspirational sketch
of what *could* be in the slot, not a description of what the file
actually says.

**Why not "fix":** Wave 3 runbook references to `dt-feat-001`,
`dt-feat-002`, and `dt-feat-003` all resolve to the existing
entries with legitimate content. The spec example has zero callers
in the runbooks. Renaming the existing entry to match the spec
would break references in `decision-guide.md` and lose the actual
content currently in DT-FEAT-001.

**Decision:** Leave existing DT-FEAT-001 alone. Recorded as drift.

### 4. Wave 3 invented multi-level prefix scheme

**What:** Wave 3 runbook authors invented per-topic prefixes that
contradict the spec's single-prefix-per-file rule:

- `DT-CSS-PERMISSION-001` (decision-guide.md:292)
- `DT-ROUTING-001` (decision-guide.md:343)
- `DT-ROUTING-002` (decision-guide.md:305, 634, 678)
- `DT-CSS-ROUTING-001` (decision-guide.md:412)
- `DT-CSS-ROUTING-003` (decision-guide.md:412)
- `DT-VOICEMAIL-001` (decision-guide.md:330)
- `DT-SHARED-LINE-001` (decision-guide.md:385)
- `DT-SETTINGS-001` (decision-guide.md:591)

These do not exist in any KB doc — Wave 3 forward-referenced 8
unique anchors that nobody had written.

**Spec implication:** Wave 3 didn't realize the KB docs had a
single-prefix-per-file rule (per spec §Artifact 4 prefix table).
The invented multi-level prefixes are a Wave 3 bug.

**Why not "fix" by retarget:** The content distinctions Wave 3 was
trying to express are real (calling permission vs partition
ordering vs E.164 globalization are different topics). Retargeting
all the invented anchors back to the existing 001/002/003 entries
would lose content fidelity in the runbooks.

**Decision:** Backfill new entries under the correct single-prefix
scheme (DT-CSS-004/005/006/007/008, DT-USER-006, DT-FEAT-004/005)
to preserve the topic distinctions. Wave 3's invented prefixes are
then retargeted in Phase E9 to the new canonical IDs.

### 5. Wave 3 over-counted entries per file

**What:** Wave 3 author assumed each KB file had 4-6 dissent
triggers when in reality they have 3 each (kb-webex-limits.md is
the exception with 5). This is why Wave 3 invented prefixes — they
needed slots that didn't exist.

**Spec implication:** Spec §Artifact 4 doesn't prescribe a count
per file. The 3-5-per-file count was a pre-Phase-2 authoring
choice.

**Why not "fix":** Adding more entries solely to match Wave 3's
assumed count would violate Phase E's honesty rule (entries must
cite real evidence; speculation is forbidden). Phase E backfills
add only the entries Wave 3 actually references.

**Decision:** Final per-file counts after Phase E backfills:

| File | Before | After | Net new |
|---|---|---|---|
| `kb-webex-limits.md` | 5 | 5 | 0 |
| `kb-css-routing.md` | 3 | 6-8 | 3-5 |
| `kb-device-migration.md` | 3 | 4 | 1 |
| `kb-feature-mapping.md` | 3 | 4-5 | 1-2 |
| `kb-identity-numbering.md` | 3 | 3 | 0 |
| `kb-location-design.md` | 3 | 6 | 3 |
| `kb-trunk-pstn.md` | 3 | 6 | 3 |
| `kb-user-settings.md` | 3 | 6 | 3 |

(Counts are recorded post-E10 verification.)

## Author Self-Walkthrough

(Populated by G5 — author reads all 3 runbook files end-to-end.)

## External Reviewer Pass

(Populated by G6 — coordinator sends runbooks to a teammate for
review.)

## Assessment Report Drift

(Populated by G7 — controller runs `wxcli cucm report` against a
test project and compares against runbook §Assessment Report
Orientation.)

## Drift Outside Phase 2 Scope

(Rolling — populated as drift is noticed in passing during Wave 4.)
