# docs/superpowers/ — Design Specs & Implementation Plans

Design documents and implementation plans produced by the brainstorming → writing-plans workflow. These are working artifacts — they drive build sessions and capture design decisions that may not be obvious from the code alone.

## Directory Structure

```
superpowers/
├── specs/    # Design specifications (the "what" and "why")
└── plans/    # Implementation plans (the "how" — task-by-task build instructions)
```

## How These Files Work Together

```
User request → brainstorming skill → spec (specs/) → writing-plans skill → plan (plans/) → implementation
```

- **Specs** are produced by the brainstorming skill. They capture requirements, architecture decisions, trade-offs, and success criteria. They are reviewed by a spec-document-reviewer agent before approval.
- **Plans** are produced by the writing-plans skill from an approved spec. They contain exact file paths, test code, implementation instructions, and commit messages. They are reviewed by a plan-document-reviewer agent.
- Plans may be split into **phases** (e.g., `phase-a.md`, `phase-b.md`) when the full plan exceeds ~400 lines, which is the practical context limit for agent execution.

## Lifecycle

These files are **ephemeral build artifacts**, not permanent documentation. The permanent record is:
1. The code itself (in `src/`)
2. CLAUDE.md files in each module directory (persistent context for future sessions)
3. The main project CLAUDE.md (project-level context)

Specs and plans can be deleted after implementation is complete without losing critical information — as long as the module-level CLAUDE.md captures the key decisions and patterns.

## Naming Convention

```
YYYY-MM-DD-<feature-name>-design.md    # specs/
YYYY-MM-DD-<feature-name>.md           # plans/
YYYY-MM-DD-<feature-name>-phase-X.md   # plans/ (when split into phases)
```

## Active Projects

### CUCM Assessment Report Tool (2026-03-24)

Produces professional HTML/PDF migration assessment reports for Sales Engineers.

| File | Type | Status |
|------|------|--------|
| `specs/2026-03-24-cucm-assess-design.md` | Design spec | Complete |
| `plans/2026-03-24-cucm-assess-report.md` | Master plan (9 tasks) | Complete — split into 3 phases |
| `plans/2026-03-24-cucm-assess-phase-a.md` | Phase A: Foundation (Tasks 1-2) | Complete |
| `plans/2026-03-24-cucm-assess-phase-b.md` | Phase B: Visual Components (Tasks 3-5) | Complete |
| `plans/2026-03-24-cucm-assess-phase-c.md` | Phase C: Report Assembly (Tasks 6-9) | In progress |

Code: `src/wxcli/migration/report/` — see its CLAUDE.md for module documentation.
Future SaaS plan: `docs/plans/cucm-assess-saas-future.md`

### Completed Projects

Earlier specs and plans in this directory built the wxcli CLI, OpenAPI generator, multi-spec expansion, customer assist, partner org-id support, and other features. These are retained for historical reference but the code is the authoritative source for how things work now.

## For New Sessions

If you're starting a new feature:
1. Use the **brainstorming skill** to create a spec in `specs/`
2. Use the **writing-plans skill** to create a plan in `plans/`
3. Split plans into phases if they exceed ~400 lines
4. After implementation, write a **CLAUDE.md** in the module directory capturing key decisions
5. The spec/plan files can be deleted once the module CLAUDE.md exists

If you're continuing existing work:
1. Check the relevant plan file for your current task
2. Read the module's CLAUDE.md for context the plan may reference
3. Phase files include "Notes from Phase X" sections at the top — read these first
