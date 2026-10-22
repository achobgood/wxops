---
paths:
  - "docs/**"
  - ".claude/skills/**"
---

# Documentation Placement — Reference vs. Playbook vs. Skill

Governs **where content goes** and **which directory to read from**, across all
three layers that carry platform content: `docs/reference/`, `docs/playbooks/`,
and `.claude/skills/*/reference.md`. Root `CLAUDE.md` § Answering platform
questions defers to this file for the reference-vs-playbook decision.

Two tests, applied in order:

1. **The Test** — reference vs. playbook: *would this still be true if the
   **user's goal** changed?*
2. **The Second Test** — skill vs. reference: *would this still be true if
   **Cisco** changed the platform?*

## The Test

> **Would this sentence still be true if the user's goal changed?**

- **Yes → `docs/reference/`.** It is a property of the platform.
- **No → `docs/playbooks/`.** It is a step toward a goal.

That is the whole rule. Everything below is elaboration.

| | `docs/reference/` | `docs/playbooks/` |
|---|---|---|
| Answers | "What is X? What are the valid values? What does it return?" | "How do I build X?" |
| Voice | Declarative | Procedural |
| Organized by | Platform object (node, activity, entity, API) | Goal (send an SMS, set up BRE) |
| Owns | Field names, valid values, limits, output variables, ports, error codes, restrictions, syntax | Ordering, decisions, prerequisites, which-UI-next, judgment calls |
| Changes when | The platform changes | The recommended approach changes |

## The Second Test — `.claude/skills/*/reference.md`

There is a **third** layer, and it is a third copy of much of this content.
The Test above cannot place it: a skill's `reference.md` is neither a goal-shaped
procedure nor a platform-object doc, so both answers look wrong. Use this instead:

> **Would this sentence still be true if *Cisco* changed the platform?**

- **Yes → the skill owns it.** It is an authoring convention or a generator asset
  — something this toolkit invented, which Cisco could not invalidate.
- **No → `docs/reference/` owns it.** It is a platform fact, and the skill must
  cite it.

| | `.claude/skills/*/reference.md` | `docs/reference/` |
|---|---|---|
| Owns | Authoring conventions, output-format specs, generator assets, this toolkit's own policies | Platform facts Cisco could change tomorrow |
| Survives a Cisco release? | Yes — it is ours | No — it is theirs |
| Examples **verified present** | Cisco dark HTML theme + section templates and the PPTX spec (`reference.md` of the `build-solution-docs` skill § HTML Theme, § HTML Section Templates, § PPTX Specifications, § Standard 10-Slide Structure); .drawio layout constants, category colours, icon registry, XML templates (`build-spec-diagram/reference.md` § Layout Constants, § Category Constants, § Icon Registry, § XML Templates); the port-name normalization map and its "Include in Connections?" policy (`design-flow/reference.md` § Port Name Canonical Map) | Entity-type lists, activity ports, limits, error codes, output variables, field names |

The "Include in Connections?" column is the clearest case of the split living
inside one table: the **port names** are Cisco's and belong to
`docs/reference/flow-designer-activities/`; the **policy** that Error and
Undefined Error ports are omitted from a Connections table is ours, and stays.

The same three consequences follow as for the playbook↔reference split: a skill
cites platform facts rather than restating them, a value question is never
answered from a skill's `reference.md` alone, and a duplicate found here is
resolved by moving-and-citing, never by deleting.

⚠ Two `reference.md` files are **almost entirely** skill-owned and must not be
reduced to citations: `reference.md` of the `build-solution-docs` skill (742 lines) and most of
`build-spec-diagram/reference.md` (438 lines). Together they are ~1,180 lines of
theme CSS, PPTX spec, .drawio XML templates and SVG icons that exist nowhere
else in the repo. `design-flow/reference.md` **splits** — its Activity Quick
Reference is platform fact and goes; its Blueprint Selection Guide, Composition
Patterns and Common Design Gotchas are authoring judgment and stay.

## The Single-Owner Rule

**Every fact has exactly one *owner*. Where a playbook repeats it, it names that
owner.**

The test above decides who owns a fact. This one decides what happens to every
other copy.

❌ **Wrong — the same fact in two files, neither naming an owner**

```
outbound-sms.md:   Set `Content-Type: application/json` in the Headers section.
connect-sms.md:    | `Content-Type` | `application/json` |
```

Fix one and the other rots, with nothing to say which is right. This is precisely
how "action name must match the Connect event name (case-sensitive)" survived in
`ai-agent-studio.md` for three months after being disproven in the skills.

❌ **Also wrong — stripping the value out of the playbook**

```
outbound-sms.md:   Configure the SMS node headers per `connect-sms.md § Headers`.
connect-sms.md:    | `Content-Type` | `application/json` |
```

Now the builder cannot complete the step without opening a second file. See
"⚠ Single owner means a tiebreak, NOT a deletion" below.

✅ **Right — the value stays, the owner is named**

```
outbound-sms.md:   Set `Content-Type: application/json` [`connect-sms.md` § Headers].
connect-sms.md:    | `Content-Type` | `application/json` |
```

Playbooks own **sequence and judgment**, and may carry values to stay usable.
Reference owns **values** and wins every disagreement.

### ⚠ "Single owner" means a tiebreak, NOT a deletion

**Read this before consolidating anything.** The rule above is about *who
maintains a fact*, not *where it may appear*. Do not strip a value out of a
playbook and replace it with "see `other-file.md`."

Stripping is strictly worse at read time:

| | Files a reader must open to get the answer |
|---|---|
| Duplicated, no citation | **1** — the playbook has it |
| Stripped, replaced by a pointer | **2** — playbook, then the owner |
| **Inline + owner citation** | **1** — the playbook has it |

Inlining costs nothing extra. The citation is a margin note, not a redirect.

**What the citation actually buys.** It does not prevent drift — two copies can
still diverge. It makes divergence *survivable*: when the copies disagree there
is a **tiebreak winner** instead of two equal-authority claims and a coin flip.
That coin flip is exactly how the event-name error survived four correction
passes over three months, and how `7010` came to be called "unverified" in one
skill file and "Cisco-confirmed" in another.

The goal is **not** brevity or token efficiency. It is stopping the toolkit from
confidently stating something false.

### So: inline by default

A playbook **should** carry the values a builder needs to complete a step —
field tables, request bodies, endpoints, exit paths, error codes. Mark the owner
so disagreements resolve:

- Same-line, for a single value:
  ``set `Content-Type: application/json` [`connect-sms.md` § Headers]``
- Block header, for a reproduced table:
  ``> **Owner: `connect-sms.md` § Headers.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.``
- Add a row pairing the two in the doc-maintenance rule (source repository only)

Two things do **not** belong inline: the surrounding *explanation* of a value
(that stays with the owner), and encyclopedic material a builder consults
deliberately rather than needs mid-step.

⚠ **Stripping also breaks internal links.** Removing a table from § 1 silently
broke a later section that said "the domain listed in Section 1." Grep for
in-file back-references before removing anything.

### Only consolidate what actually drifted

Churn on pairs that merely overlap is cost without benefit. Prioritise pairs
where the two copies are **observed to disagree**, or where one has been shown
to strip a hedge in transit. Overlap alone earns a sync-pair row in the
doc-maintenance rule, not surgery.

## Retrieval — which directory to read

1. **Classify the question.**
   - "What / which / how many / is it possible / what does it return" → **a value question** → read `docs/reference/` first.
   - "How do I / build / set up / configure / walk me through" → **a procedure question** → read the `docs/playbooks/` file, **and** every reference doc it cites.
2. **Never answer a value question from a playbook alone.** The playbook may have
   inlined a value under the exception above; the reference doc owns it.
3. **Never answer a procedure question from a reference doc alone.** Reference
   docs deliberately do not carry ordering or cross-UI sequencing.

Root `CLAUDE.md` § Answering platform questions and § Routing Table still dictate
*which* files. This rule dictates *which directory to trust for what*.

## ⚠ Interim: neither directory is reliably authoritative yet

**Do not treat `docs/reference/` as the source of truth until the remediation
backlog is worked.** An audit pass in April 2026 corrected `docs/playbooks/` and
`.claude/skills/` and never swept `docs/reference/` — so for the topics that
audit touched, the *playbook* is currently the more current file. Of 117 priority
fixes: 51 applied, 24 not applied, 42 partially applied.

Until `docs/plans/2026-07-25-documentation-remediation-backlog.md` is closed out:

- **Read both** when they cover the same ground.
- **Treat any disagreement as a finding, not a coin flip.** Do not silently pick
  the more plausible one. Report it, and resolve it against the live API, the
  official vendor documentation, or the platform owner — never from training data.
- Log what you resolve into the backlog document.

This caveat is how the Flow Outcomes and Event Name errors were caught. Delete
this section only when the backlog is closed.

## When you find a duplicate

1. **Check whether the copies disagree.** If they do, that is the actual defect —
   resolve the fact first, against the live API, official vendor docs, or the
   platform owner. Never pick the more plausible one. If they agree, this may
   need nothing more than step 4.
2. Decide the owner with **The Test** (reference vs. playbook) or **The Second
   Test** (skill vs. reference), whichever pair of layers the duplicate spans.
3. Ensure the canonical content exists at the owner, with its full explanation.
4. **Annotate the other copy with the owner — do not delete it.** Leave the value
   where readers need it; add the same-line citation or block header. Deleting
   the value makes the page unusable alone and can break in-file
   back-references.
5. Add a row pairing the two in the doc-maintenance rule (source repository only).

## Never delete a doc to resolve a duplicate

An unreferenced, stale, or duplicated file means the **index is broken**, not that
the content is worthless. A file can be wrong on five lines and still be the only
surviving record of setup detail that never reached the reference layer.

Options are: fix in place, merge-and-cite, or log it in the backlog. Deletion
requires reporting exactly what unique content would be lost and getting explicit
per-file approval. "It's recoverable from git" is not a justification — it makes
the loss quiet, not acceptable.

A subagent recommending "delete it, it's a duplicate" is recommending you
**verify**, not execute.

## Placement of new files

- New file in `docs/reference/` → add a `<!-- ref-tag: <slug>-v1 -->` under the
  title, and add a line to the folder's `INDEX.md`.
- New file in `docs/playbooks/` → add a line to the folder's `INDEX.md` naming its
  reference twin, and a sync-pair row in the doc-maintenance rule (source
  repository only) if a twin exists.
- New `.claude/skills/<name>/reference.md` → it may carry **only** what passes
  The Second Test. Platform facts go to `docs/reference/` and are cited from the
  skill; add the `INDEX.md` line there, not in the skill.
- A file absent from its folder's `INDEX.md` goes unvetted and eventually gets mistaken for
  junk. `docs/playbooks/ai-agent-studio.md` was orphaned exactly this way.
