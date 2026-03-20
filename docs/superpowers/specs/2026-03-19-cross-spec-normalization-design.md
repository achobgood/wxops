# Cross-Spec Normalization & Completeness Audit

**Date:** 2026-03-19
**Status:** Approved
**Scope:** All 4 OpenAPI spec expansions (Calling, Admin, Device, Messaging) — 39 reference docs, 14 skills, 1 builder agent

## Problem

Each of the 4 OpenAPI spec expansions (Calling, Admin, Device Platform, Messaging) was built in a separate chat session. While all are functional, they diverge in structure, section ordering, gotcha placement, skill workflow patterns, and completeness. This creates inconsistency for both the builder agent (which loads these docs and skills) and for humans reviewing them.

### Observed Asymmetries

1. **Doc header format varies:** Calling docs start with SDK access paths and API class names; admin docs start with Sources and Required Scopes tables; messaging docs lead with a Token Type Matrix.
2. **Gotchas placement varies:** Calling docs have gotchas consolidated at the bottom; messaging docs have per-section inline gotchas; admin docs mix both patterns inconsistently.
3. **Skill workflow structure varies:** Calling skills use numbered sub-steps (4a, 4b, 6a, 6b); admin skills use lettered operations (Operation A, B, C...); messaging-bots uses a recipe-selection pattern.
4. **Raw HTTP coverage varies:** Admin and messaging docs have consistent Raw HTTP per section. Some older calling docs may lack Raw HTTP for certain sections.
5. **Sources/provenance varies:** Admin docs consistently cite their sources. Some calling docs predate this convention and lack a Sources section.
6. **Draft files pollute the directory:** 6 `_review-*.md` files in `docs/reference/` contain 76 NEEDS VERIFICATION tags and serve no active purpose.

### Inventory

| Spec | Reference Docs | Lines | Skills | NEEDS VERIFICATION |
|------|---------------|-------|--------|-------------------|
| Calling (non-wxcadm) | 18 files | ~22,000 | 7 | ~~~85~~ → 0 |
| Device | 4 files | 3,803 | 2 | ~~~8~~ → 0 |
| Admin | 7 files | 3,512 | 3 | ~~~14~~ → 0 |
| Messaging | 2 files | 1,445 | 2 | ~~~6~~ → 2 |
| wxcadm (limited audit) | 8 files | ~8,300 | — | ~~~51~~ → 0 |
| **Total** | **39 files** | **~39,060** | **14** | ~~**~113**~~ → **2** |

> **Updated 2026-03-20:** NEEDS VERIFICATION sweep completed 2026-03-19. 136 tags resolved (122 verified, 27 corrected). Only 2 remain: bot calling scopes (authentication.md) and messaging rate limits (messaging-spaces.md) — both need special tokens to test.

~~Plus 6 `_review-*.md` draft files (76 NEEDS VERIFICATION tags) and 1 builder agent (647 lines).~~ The `_review-*.md` draft files have been deleted.

Note: Device docs (devices-core, devices-dect, devices-workspaces, devices-platform) are broken out as their own spec domain even though some predate the Device Platform expansion — they share the `manage-devices` and `device-platform` skills.

## Approach

**Gap-weighted audit** with **two-phase execution**:
- **Phase 1 (Audit):** Read-only. Every file checked against canonical templates. Findings report produced, grouped by severity.
- **User review gate:** User reviews findings before any files are touched.
- **Phase 2 (Fix):** Executes changes in priority waves (P0 → P1 → P2 → Cleanup), stoppable between waves.

**Blast radius:** Headers, ordering, and gap-fills. No content rewrites, no file splits/merges, no NEEDS VERIFICATION resolution.

**Template strategy:** Hybrid — best patterns cherry-picked from all 4 specs.

## Canonical Reference Doc Template

Every reference doc should follow this structure, top to bottom. Optional sections marked.

```
# {Title}

> {One-line description}

## Sources
- OpenAPI spec, SDK version, API docs this was built from

## Required Scopes
- Table: scope | what it grants | notes
- Token type requirements (admin, user, bot) if the doc covers 3+ token types,
  give this its own sub-section or matrix

## Table of Contents (required for docs with 3+ sections)
- Numbered section links

## {N. Section per CLI group or logical unit}

### Commands
- Table: command | description | key flags

### Key Parameters
- Notable parameters, defaults, gotchas per command

### CLI Examples
- Copy-paste ready examples with realistic values

### Raw HTTP Fallback
- Method, URL, headers, body
- When to use raw HTTP instead of CLI

### Gotchas (inline, per-section)
- Section-specific gotchas immediately after the section they apply to

## Recipes (optional)
- Multi-step workflows combining commands from this doc

## Gotchas (cross-cutting)
- Issues spanning multiple sections — NOT duplicates of inline gotchas
- Generator/CLI bugs affecting this domain

## See Also
- Cross-references to related docs, skills, and external resources
```

**Design decisions:**
1. **Inline + cross-cutting gotchas.** Inline gotchas appear right where the issue bites. Cross-cutting gotchas at the bottom cover issues that span sections. No duplication between the two.
2. **Sources section required.** Establishes provenance — which spec, which SDK version, which docs.
3. **No SDK method signatures in template.** The canonical pattern is CLI-first. The wxcadm-*.md docs are a separate category documenting a different tool and keep their own structure — they are NOT subject to this template.
4. **Token Type Matrix** goes into Required Scopes unless the doc covers 3+ token types, then it gets its own sub-section (as messaging-spaces does).

### wxcadm docs exception

The 8 wxcadm-*.md docs document a different tool (wxcadm library, not wxcli CLI). They follow their own structure centered on Python classes and methods. They are audited only for:
- See Also section exists with cross-references
- Gotchas section exists
- No stale cross-references

They are NOT normalized to the CLI-first template above.

## Canonical Skill Template

Every skill should follow this workflow structure:

```
---
name: {skill-name}
description: {one-line description}
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [{example arguments}]
---

# {Skill Title}

## Step 1: Load references
- List of docs to Read (absolute paths)

## Step 2: Verify auth token
- wxcli whoami
- Required scopes table for this skill's operations
- Token troubleshooting guidance

## Step 3: Identify the operation
- Bulleted list of operation types this skill handles
- "Ask the user if unclear"

## Step 4: Check prerequisites
### 4a. {First prerequisite category}
### 4b. {Second prerequisite category}
### 4c. {Third prerequisite category}
(use numbered sub-steps: 4a, 4b, 4c — not lettered operations)

## Step 5: Build and present deployment plan -- `[SHOW BEFORE EXECUTING]`
- Plan structure
- "DO NOT execute until user approves"

## Step 6: Execute via wxcli
### 6a. {First operation category}
### 6b. {Second operation category}
- CLI commands with realistic examples
- Error handling per operation

## Step 7: Verify
- Read-back commands per operation type

## Step 8: Report results
- Summary format

## Critical Rules
- Numbered list of non-negotiable rules for this domain

## {Domain-specific sections} (optional)
- Scope Quick Reference, CLI Bug Notes, Cross-References, etc.

## Context Compaction Recovery
- How to recover if context resets mid-execution
```

**Design decisions:**
1. **Numbered sub-steps (4a, 4b, 6a, 6b) everywhere.** Not lettered operations (Operation A, B, C). "Resume at Step 6b" is unambiguous.
2. **Step 5 always includes `[SHOW BEFORE EXECUTING]`** — the plan gate marker.
3. **Critical Rules section is mandatory** — even if short. At minimum, every skill's Critical Rules should cover: (a) verify token before write operations, (b) never delete/modify without user confirmation, (c) domain-specific gotchas that cause silent failures. Use existing skills' Critical Rules as reference patterns.
4. **Context Compaction Recovery is mandatory** — every skill needs it.
5. **Domain-specific sections are allowed** after Critical Rules — skills may add Scope Quick Reference, CLI Bug Notes, Cross-References as needed.
6. **Operation → Step conversion requires internal cross-ref updates.** Skills using lettered operations (Operation A, B, C) may have internal references between steps (e.g., "see Operation D for cleanup"). When converting to numbered sub-steps (Step 6a, 6b, 6c), update ALL internal references, not just headers.

## Audit Dimensions & Severity Tiers

### P0 — Blocks Users

| ID | Dimension | What's checked |
|----|-----------|---------------|
| P0-1 | Raw HTTP Fallback | Every CLI group section has a Raw HTTP sub-section. **Exempt:** Conceptual/setup docs (`authentication.md`, `wxc-sdk-patterns.md`) that don't document CLI command groups — mark as N/A. |
| P0-2 | Required Scopes | Doc has a scopes table with token type requirements. **Note:** A Token Type Matrix (as in `messaging-spaces.md`) satisfies this dimension if it covers scope/access requirements per token type. |
| P0-3 | CLI Examples | Every command group has copy-paste examples. **Exempt:** Same conceptual docs as P0-1 — mark as N/A. |
| P0-4 | Auth verification in skills | Skill Step 2 checks scopes (not just `wxcli whoami`) |

### P1 — Causes Confusion

| ID | Dimension | What's checked |
|----|-----------|---------------|
| P1-1 | Inline Gotchas | Section-specific gotchas appear after their section. **Dedup rule:** When adding inline gotchas, check whether the content already exists in the cross-cutting Gotchas section and deduplicate — each gotcha lives in exactly one place. |
| P1-2 | See Also | Every doc ends with cross-references to related docs and skills |
| P1-3 | Skill workflow consistency | Skills follow the 8-step template with numbered sub-steps |
| P1-4 | Skill Critical Rules | Every skill has a Critical Rules section |
| P1-5 | Context Compaction Recovery | Every skill has this section |
| P1-6 | Plan gate wording | Skill Step 5 uses `[SHOW BEFORE EXECUTING]` marker |

### P2 — Cosmetic

| ID | Dimension | What's checked |
|----|-----------|---------------|
| P2-1 | Sources section | Doc states provenance (spec, SDK, docs) |
| P2-2 | Table of Contents | Docs with 3+ sections have a numbered ToC |
| P2-3 | Header consistency | Same heading levels for same concepts across docs |
| P2-4 | Cross-cutting Gotchas | Bottom section exists for issues spanning multiple sections (not duplicating inline) |

### Cleanup (not severity-tiered)

| ID | Item | Action |
|----|------|--------|
| CL-1 | `_review-*.md` files | Flag for deletion |
| CL-2 | Stale cross-references | Flag any See Also link pointing to renamed/deleted file |

## Phase 1: Audit Prompt

### Purpose
Read-only audit of all in-scope files against canonical templates. Produces a findings report.

### In Scope
- All `docs/reference/*.md` (excluding `_review-*.md` and wxcadm-*.md for template compliance — wxcadm docs checked for See Also, Gotchas, and stale refs only)
- All `.claude/skills/*/SKILL.md` (14 skills)
- `.claude/agents/wxc-calling-builder.md` (checked for dispatch table completeness and stale references only)

### Out of Scope
- `CLAUDE.md` (file map, not reference doc)
- `docs/templates/`, `docs/plans/`, `docs/prompts/`
- NEEDS VERIFICATION resolution (requires live API testing)

### Execution Model
1. Session reads the audit prompt (which embeds canonical templates, dimensions, and file inventory)
2. Dispatches parallel Explore subagents in waves of 5-6, each assigned 1-2 files
3. Each subagent returns structured findings per file: dimension ID, pass/fail, current state, required state
4. Main session synthesizes into a single findings report

### Subagent Prompt Template
Each audit subagent receives:
- The canonical template (reference doc or skill, as appropriate)
- The severity dimensions table
- 1-2 file paths to audit
- Instruction: "For each file, check every applicable dimension. Return a structured block per dimension: dimension ID, pass/fail/N/A, current state (quote the relevant section or note its absence), required state. Mark dimensions as N/A with a reason when they don't apply to the file type (e.g., P0-1 Raw HTTP is N/A for conceptual docs like authentication.md). Do not modify any files."

### Findings Report
Saved to `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md`:

```markdown
# Cross-Spec Audit Findings

## Summary
- Files audited: N
- P0 findings: N across M files
- P1 findings: N across M files
- P2 findings: N across M files
- Cleanup items: N

## P0 — Blocks Users

### P0-{id}: {finding title}
- **File:** {path}
- **Dimension:** {P0-N — dimension name}
- **Current state:** {what's there now, quoted}
- **Required state:** {what the template requires}
- **Fix:** {specific change needed}

(repeat per finding)

## P1 — Causes Confusion
(same format)

## P2 — Cosmetic
(same format)

## Cleanup

### _review-*.md files to delete
- {list of file paths}

### Stale cross-references
- **File:** {path} → **Broken link:** {target} → **Fix:** {update or remove}
```

## Phase 2: Fix Prompt

### Purpose
Execute fixes from the findings report. Files are modified.

### Inputs
- Findings report: `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md`
- Canonical templates (embedded in prompt — cannot rely on Phase 1 context)

### Execution Model
1. Session reads the findings report
2. Groups findings by file (an agent editing a file makes ALL fixes to that file in one pass)
3. Executes in priority waves, stoppable between waves:
   - **Wave 1:** P0 fixes
   - **Wave 2:** P1 fixes
   - **Wave 3:** P2 fixes
   - **Wave 4:** Cleanup (delete `_review-*.md`, fix stale cross-references)
4. Each wave dispatches fix agents (5-6 per wave, 1-2 files per agent)
5. After each wave: main session spot-checks 2-3 files to verify correctness
6. Between waves: report progress and ask user whether to continue to next wave

### Fix Types

| Finding type | Fix action |
|-------------|-----------|
| Missing section (Raw HTTP, Gotchas, See Also, Sources, ToC) | Add section with appropriate content — not placeholders |
| Wrong section ordering | Reorder to match template — no content changes |
| Missing inline gotchas | Move relevant items from consolidated gotchas to inline, or write new based on doc content |
| Skill workflow conversion (lettered → numbered) | Rename Operation A/B/C to Step 6a/6b/6c, adjust numbering, add missing steps |
| Missing plan gate wording | Add `[SHOW BEFORE EXECUTING]` to Step 5 header |
| Missing Critical Rules / Context Compaction | Add section based on skill's domain and patterns from other skills |
| `_review-*.md` files | Delete |
| Stale cross-references | Update path or remove link |

### What Fixes Don't Include
- No content rewrites (structural changes and gap-fills only)
- No file splits, merges, renames, or moves
- No CLAUDE.md updates (separate follow-up after fixes land)
- No NEEDS VERIFICATION resolution
- No wxcadm-*.md template normalization (only See Also, Gotchas, stale refs)

### Output
After all waves, the session produces an execution summary saved alongside the findings:

```markdown
# Cross-Spec Normalization — Execution Summary

## Changes
- Files modified: N (with line count deltas)
- Files deleted: N (_review-*.md)
- P0 fixes applied: N
- P1 fixes applied: N
- P2 fixes applied: N
- Cleanup items resolved: N

## Fixes That Could Not Be Applied
- {file}: {reason}

## Recommended Follow-Up
- Update CLAUDE.md file map if any docs were renamed/deleted
- ~~NEEDS VERIFICATION backlog: ~113 tags across 37 files (requires live API)~~ Swept 2026-03-19: only 2 remain
- {any other follow-up discovered during fixes}
```

## File Inventory for Audit

### Estimated Wave Count
- Phase 1 (audit): ~54 files at 1-2 per agent, 5-6 agents per wave = approximately 5-6 waves
- Phase 2 (fix): depends on findings, but expect 3-4 waves per priority tier

### Reference Docs — Full Template Audit (31 files)

#### Calling (18 files)
- `docs/reference/authentication.md` *(conceptual — exempt from P0-1, P0-3)*
- `docs/reference/provisioning.md`
- `docs/reference/wxc-sdk-patterns.md` *(conceptual — exempt from P0-1, P0-3)*
- `docs/reference/call-features-major.md`
- `docs/reference/call-features-additional.md`
- `docs/reference/call-routing.md`
- `docs/reference/call-control.md`
- `docs/reference/person-call-settings-handling.md`
- `docs/reference/person-call-settings-media.md`
- `docs/reference/person-call-settings-permissions.md`
- `docs/reference/person-call-settings-behavior.md`
- `docs/reference/location-call-settings-core.md`
- `docs/reference/location-call-settings-media.md`
- `docs/reference/location-call-settings-advanced.md`
- `docs/reference/emergency-services.md`
- `docs/reference/virtual-lines.md`
- `docs/reference/reporting-analytics.md`
- `docs/reference/webhooks-events.md`

#### Device (4 files)
- `docs/reference/devices-core.md`
- `docs/reference/devices-dect.md`
- `docs/reference/devices-workspaces.md`
- `docs/reference/devices-platform.md`

#### Admin (7 files)
- `docs/reference/admin-org-management.md`
- `docs/reference/admin-identity-scim.md`
- `docs/reference/admin-licensing.md`
- `docs/reference/admin-audit-security.md`
- `docs/reference/admin-hybrid.md`
- `docs/reference/admin-partner.md`
- `docs/reference/admin-apps-data.md`

#### Messaging (2 files)
- `docs/reference/messaging-spaces.md`
- `docs/reference/messaging-bots.md`

### Reference Docs — Limited Audit (8 wxcadm files, See Also + Gotchas + stale refs only)
- `docs/reference/wxcadm-core.md`
- `docs/reference/wxcadm-person.md`
- `docs/reference/wxcadm-locations.md`
- `docs/reference/wxcadm-features.md`
- `docs/reference/wxcadm-devices-workspaces.md`
- `docs/reference/wxcadm-routing.md`
- `docs/reference/wxcadm-xsi-realtime.md`
- `docs/reference/wxcadm-advanced.md`

### Skills — Full Template Audit (14 files)

#### Calling (7 skills)
- `.claude/skills/provision-calling/SKILL.md`
- `.claude/skills/configure-features/SKILL.md`
- `.claude/skills/manage-call-settings/SKILL.md`
- `.claude/skills/configure-routing/SKILL.md`
- `.claude/skills/call-control/SKILL.md`
- `.claude/skills/reporting/SKILL.md`
- `.claude/skills/wxc-calling-debug/SKILL.md`

#### Device (2 skills)
- `.claude/skills/manage-devices/SKILL.md`
- `.claude/skills/device-platform/SKILL.md`

#### Admin (3 skills)
- `.claude/skills/manage-identity/SKILL.md`
- `.claude/skills/audit-compliance/SKILL.md`
- `.claude/skills/manage-licensing/SKILL.md`

#### Messaging (2 skills)
- `.claude/skills/messaging-spaces/SKILL.md`
- `.claude/skills/messaging-bots/SKILL.md`

### Builder Agent — Dispatch Table & Stale Reference Audit
- `.claude/agents/wxc-calling-builder.md`

### Cleanup Candidates (6 files)
- `docs/reference/_review-auth-provisioning-sdk.md`
- `docs/reference/_review-coverage-matrix.md`
- `docs/reference/_review-devices-control-other.md`
- `docs/reference/_review-features-routing.md`
- `docs/reference/_review-person-location-settings.md`
- `docs/reference/_review-wxcadm.md`
