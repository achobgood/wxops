# Architecture Documentation — wxcli

Five documents that describe the wxcli project at increasing levels of abstraction. Together they answer: what exists, why it was built that way, how it behaves, how to operate and evolve it, and who it serves.

## Document Summaries

### 01 — Structural Map

What the codebase contains and how the pieces connect. Module inventory (core CLI, 208 generated commands, migration pipeline, org health, code generation tools, test suite, Claude Code agents/skills, reference docs). Data flow diagrams for single commands, the code generation pipeline, the CUCM migration pipeline, and org health assessment. Key abstractions (WebexSession, Endpoint/EndpointField, the migration project store, the NetworkX dependency DAG). Module boundaries and external dependencies.

### 02 — Decisions

Eight architectural decision records (ADRs) capturing the choices that shaped the project:

| ADR | Topic |
|-----|-------|
| 1 | Generated commands from OpenAPI specs vs. hand-written |
| 2 | Raw HTTP via REST client vs. typed SDK methods |
| 3 | SQLite-backed project store for migration |
| 4 | NetworkX DAG for dependency ordering |
| 5 | Async execution engine with configurable concurrency |
| 6 | Pipeline split — normalizers, mappers, analyzers, advisors |
| 7 | The `field_overrides.yaml` pattern |
| 8 | Claude Code playbook structure (builder agent + skills + reference docs) |

Includes a cross-reference matrix showing which ADRs interact and a list of open questions.

### 03 — Behavior

How the system behaves at runtime. Failure modes cataloged by severity (graceful, useful-error, confusing, silent) for the CLI framework, cleanup subsystem, migration pipeline, and org health. Fragility map identifying the most brittle integration points. Performance characteristics (pagination, concurrency, rate limits). State and side effects (config file, migration project store, cleanup state machine). Known issues with workarounds.

### 04 — Operations & Evolution

How to build, test, deploy, debug, and extend the project. Build instructions and test framework (pytest, 2778+ migration tests, 76 org health tests). Deployment model (local pip install, no server). Debugging playbook for common failure scenarios. Areas of active change. Known technical debt. Roadmap implications.

### 05 — Purpose

Who the project serves and why. Primary audience (TSAs, partner engineers, migration practitioners), secondary audience (Webex API developers), and explicit non-audience. Success criteria — what "working well" looks like and how to detect regression. Out-of-scope boundaries. Constraints that aren't technical (product roadmap dependency, license gating, grounding rule).

---

## Quick Reference

If you're trying to understand or modify something, start here:

| If you need to... | Read first | Then |
|---|---|---|
| Understand how a wxcli command flows from invocation to API call | 01 §2a (Data Flow) | 03 §1a (CLI failure modes) |
| Add or modify a generated command | 01 §2b (Code Generation) | 02 ADR-1 (generation design), ADR-7 (field overrides) |
| Write a hand-coded command | 01 §3a (Key Abstractions) | 02 ADR-2 (raw HTTP rationale) |
| Modify the migration pipeline | 01 §2c (Migration Data Flow) | 02 ADR-3/4/5/6 (migration ADRs) |
| Debug a failing API call or command | 03 §1 (Failure Modes) | 04 §3 (Debugging Playbook) |
| Understand why a design choice was made | 02 (Decisions) | 05 (Purpose — constraints and tradeoffs) |
| Add a new skill or modify the builder agent | 02 ADR-8 (Playbook Structure) | 01 §1 (Module Inventory, agents/skills rows) |
| Understand cleanup deletion ordering | 03 §1b (Cleanup Failures) | 01 §3 (Key Abstractions — dependency DAG) |
| Run or modify tests | 04 §1 (Build and Test) | 01 §1 (Module Inventory, tests row) |
| Assess what's technically feasible vs. out of scope | 05 (Purpose — Out of Scope) | 02 (Decisions — Open Questions) |
| Onboard to the project | 05 (Purpose) → 01 (Structure) → 02 (Decisions) | 03 and 04 as needed |

---

## Maintenance Protocol

These docs are load-bearing — they inform Claude Code sessions that modify the codebase. Stale architecture docs produce stale assumptions, wrong code, and rework. Keep them current.

### Update Triggers

| Document | Update when... |
|----------|---------------|
| 01 — Structural Map | A new module, command group, agent, or skill is added or removed. A data flow changes (new pipeline stage, new integration point). Module boundaries shift. |
| 02 — Decisions | A new architectural decision is made (add an ADR). An existing decision is revisited or reversed (update status to "Superseded" or "Revised"). An open question is resolved. |
| 03 — Behavior | A failure mode is discovered, fixed, or reclassified. A new known issue is identified. Performance characteristics change materially (new rate limits, new pagination behavior). A workaround is added or becomes unnecessary. |
| 04 — Operations & Evolution | Build or test infrastructure changes. A new debugging pattern is established. Technical debt is paid down or newly identified. The roadmap shifts. |
| 05 — Purpose | The audience changes. Success criteria are refined. Scope boundaries move (something moves in or out of scope). Non-technical constraints change. |

### Who Updates

Any Claude Code session that makes changes triggering the conditions above. The session that makes the change owns the doc update — don't defer it to a future session.

### How to Update

1. Read the relevant doc section before making your change (to understand current state).
2. Make the code change.
3. Update the corresponding doc section to reflect the new state.
4. If the change affects the cross-reference table in 02 or the quick-reference table above, update those too.
