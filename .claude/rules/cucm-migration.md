---
paths:
  - "src/wxcli/migration/**"
  - "docs/knowledge-base/migration/**"
  - "docs/runbooks/cucm-migration/**"
  - "docs/reference/migration-spec-template.md"
---

# CUCM Migration Context

## Agent Invocation Example

The builder agent uses phase-per-invocation for migrations:
1. Spawn agent: "Run CUCM discovery for project X against host Y"
2. Agent completes discover + normalize + map + analyze, writes session-state, terminates
3. Spawn fresh agent: "Project X is at ANALYZED. Run decision review and generate report"
4. Agent completes decisions + report, writes session-state, terminates
5. Continue pattern through plan → execute

## Migration Knowledge Base (Opus Advisor)

Structured knowledge base read by the `migration-advisor` agent (Opus) during CUCM migration analysis and decision review. Grounded in the reference docs above + static advisory heuristics. The advisor reads relevant KB docs based on which decision types are present, then applies its own training for edge cases.

| Path | Purpose |
|------|---------|
| `docs/knowledge-base/migration/kb-css-routing.md` | CSS/partition ordering, dial plan decomposition, calling permissions |
| `docs/knowledge-base/migration/kb-device-migration.md` | Device replacement paths, firmware conversion, MPP vs PhoneOS/RoomOS |
| `docs/knowledge-base/migration/kb-trunk-pstn.md` | Trunk topology, LGW vs CCPP, CPN transformation chains |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Hunt Group vs Call Queue depth, AA mapping, shared line semantics |
| `docs/knowledge-base/migration/kb-user-settings.md` | Call forwarding, voicemail, calling permissions, workspace licensing |
| `docs/knowledge-base/migration/kb-location-design.md` | Device pool → location consolidation, E911, numbering plan |
| `docs/knowledge-base/migration/kb-identity-numbering.md` | DN ownership, extension conflicts, duplicate users, number porting |
| `docs/knowledge-base/migration/kb-webex-limits.md` | Platform hard limits, feature gaps, scope requirements (always loaded) |

## Migration Operator Runbooks (Phase 2 Transferability)

Operator-facing reference docs for the CUCM-to-Webex migration tool. Written for a CUCM-literate SE running their first migration. The cucm-migrate skill points operators here for end-to-end pipeline help, per-decision lookups, and tuning recipes.

| Path | Purpose |
|------|---------|
| `docs/runbooks/cucm-migration/operator-runbook.md` | Operator runbook — end-to-end pipeline walkthrough, prerequisites, failure recovery |
| `docs/runbooks/cucm-migration/decision-guide.md` | Decision guide — one entry per DecisionType + advisory pattern, with override criteria |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Tuning reference — config keys, auto-rules, score weights, 5 worked recipes |

**When handling CUCM migration questions:** Read `operator-runbook.md` first for the pipeline walkthrough and `decision-guide.md` for per-decision interpretation. Read `tuning-reference.md` when discussing customer environment shapes (the 5 worked recipes), config tuning, or recurring decision patterns. The `cucm-migrate` skill loads these references automatically when `/cucm-migrate` is invoked; this instruction covers ad-hoc CUCM questions sent to `wxc-calling-builder` or other agents outside the skill flow.

## CUCM→Webex Migration Tool (All 11 phases complete)

The migration tool is at `src/wxcli/migration/` and wired into the CLI as `wxcli cucm <command>`. **2778 tests passing.** See `src/wxcli/migration/CLAUDE.md` for the full file map, architecture, and pipeline commands. Use `/cucm-migrate` to execute a migration after running the pipeline.

**To run a migration:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `decisions` → `plan` → `preflight` → `export` → then invoke `/cucm-migrate`.

**Migration advisory workflow:** During `/cucm-migrate`, the cucm-migrate skill delegates to the `migration-advisor` agent (Opus) at two points: (1) after pipeline verification, it produces a `migration-narrative.md` with cross-decision analysis, dissent flags, and risk assessment; (2) during decision review, it presents advisories and recommendations with CCIE-level contextual explanation, grounded in the knowledge base at `docs/knowledge-base/migration/`. The static heuristics (`recommendation_rules.py`, `advisory_patterns.py`) remain the backbone — the Opus layer adds interpretation and structured dissent when heuristics are likely wrong. Falls back to mechanical presentation if the advisor agent is unavailable.

**To generate an assessment report:** `wxcli cucm init` → `discover` (or `discover --from-file`) → `normalize` → `map` → `analyze` → `report --brand "..." --prepared-by "..."`. Does not require plan/preflight/export — the report reads directly from the post-analyze store.

**To generate a per-user diff:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `user-diff`. Does not require plan/preflight/export.

**To generate a user communication notice:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `user-notice --brand "..." --migration-date "..." --helpdesk "..."`. Does not require plan/preflight/export.

## Migration Spec Template

All migration pipeline spec documents must follow the template at `docs/reference/migration-spec-template.md`. This applies whether the spec is written interactively via brainstorming, by an agent swarm, or manually. The template is rigid — all 9 sections are required. Sections can be brief for simple specs but cannot be omitted.
