# Spec-to-Ship Feature Team

## When to use

Any feature that touches 2+ of: implementation code, tests, reference docs/skills.
Covers new CUCM phases, generator improvements, new skills, cleanup enhancements.

**Don't use for:** Quick bug fixes, single-file edits, exploratory research.

## Usage

Copy the spawn prompt below and fill in the bracketed values:
- `[FEATURE_NAME]` — short name of the feature
- `[SPEC_PATH]` — path to the design spec (e.g., `docs/superpowers/specs/2026-03-28-foo-design.md`)
- `[PLAN_PATH]` — path to the implementation plan (e.g., `docs/superpowers/plans/2026-03-28-foo.md`)

## Spawn Prompt

~~~
I'm implementing [FEATURE_NAME] per the spec at [SPEC_PATH].

Create an agent team with 3 teammates:

1. "impl" (Opus) — Implements the core code changes.
   Owns (writes to): src/wxcli/, tools/, specs/
   Reads: the spec, the plan, project CLAUDE.md
   Requires plan approval before each major step.
   Start with the plan at [PLAN_PATH].
   Do NOT write to tests/, docs/reference/, .claude/skills/, or CLAUDE.md.

2. "tests" (Sonnet) — Writes tests as impl progresses.
   Owns (writes to): tests/
   Reads: the spec, the plan, impl's code in src/
   Watch impl's task list. Message impl directly when a contract or interface is unclear.
   Don't write tests for code that hasn't been implemented yet — wait for impl to mark tasks done.
   Do NOT write to src/wxcli/, tools/, docs/, or .claude/.

3. "docs" (Sonnet) — Updates reference docs and skills.
   Owns (writes to): docs/reference/, .claude/skills/, CLAUDE.md
   Reads: the spec, impl's code in src/
   Update affected reference docs, skill files, and CLAUDE.md sections.
   Message other teammates when you find cross-references that need updating.
   Do NOT write to src/wxcli/, tools/, tests/, or specs/.

File ownership is strict: each teammate only writes to their owned paths.
Read the project CLAUDE.md for file map and conventions.
~~~

## Team Dynamics

- **impl** has plan-approval mode — gets your OK before each major step
- **tests** and **docs** run freely — lower-risk, easier to review after
- **tests** should message **impl** when an interface is unclear rather than guessing
- **impl** should message **tests** when a task is done with the shape/contract of new code
- **docs** should message other teammates when cross-references need updating

## File Ownership Boundaries

| Teammate | Writes to | Reads from |
|----------|-----------|------------|
| impl | `src/wxcli/`, `tools/`, `specs/` | spec, plan |
| tests | `tests/` | spec, plan, impl's code |
| docs | `docs/reference/`, `.claude/skills/`, `CLAUDE.md` | spec, impl's code |
