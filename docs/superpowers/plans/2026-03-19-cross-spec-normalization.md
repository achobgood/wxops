# Cross-Spec Normalization Implementation Plan

> **For agentic workers:** This plan has two phases that run in **separate sessions**. Phase 1 is read-only (audit). Phase 2 modifies files (fix). Each phase dispatches parallel subagents. Use superpowers:dispatching-parallel-agents for wave management.

**Goal:** Normalize 39 reference docs and 14 skills across 4 OpenAPI spec expansions to consistent canonical templates, filling structural gaps weighted by user impact.

**Architecture:** Two-phase approach — Phase 1 audits all files against canonical templates and produces a findings report; Phase 2 reads that report and executes fixes in priority waves. A user review gate separates the phases.

**Spec:** `docs/superpowers/specs/2026-03-19-cross-spec-normalization-design.md`

---

## Phase 1: Audit (New Session)

### Task 1: Session Setup

- [ ] **Step 1: Read the design spec**

Read `docs/superpowers/specs/2026-03-19-cross-spec-normalization-design.md` in full. This contains:
- Canonical Reference Doc Template (the structure every doc should follow)
- Canonical Skill Template (the 8-step workflow every skill should follow)
- Audit Dimensions & Severity Tiers (P0, P1, P2, Cleanup)
- Complete file inventory with exemptions noted

- [ ] **Step 2: Create the findings report scaffold**

Create `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md` with the report skeleton from the spec (Summary, P0, P1, P2, Cleanup sections). You'll fill this in as subagent results come back.

---

### Task 2: Audit Reference Docs — Calling (18 files)

Dispatch Explore subagents in 3 waves of 6 agents, each assigned 1 file. Each subagent receives:
1. The canonical reference doc template (copy from spec)
2. The P0/P1/P2 dimensions table (copy from spec)
3. Its assigned file path
4. This instruction:

```
Read the file at {path}. Check every dimension from the table below against this file.
For each dimension, return a structured block:

- **Dimension:** {ID} — {name}
- **Result:** PASS / FAIL / N/A
- **Current state:** {quote the relevant section header or note "section absent"}
- **Required state:** {what the template requires}
- **Fix needed:** {specific change, or "none"}

Dimensions marked "exempt" for conceptual docs: if this file is authentication.md
or wxc-sdk-patterns.md, mark P0-1 and P0-3 as N/A.

Do not modify any files. Return only the structured findings.
```

- [ ] **Step 1: Wave 1 — Calling docs 1-6**

Dispatch 6 Explore subagents for:
1. `docs/reference/authentication.md` *(conceptual — P0-1, P0-3 exempt)*
2. `docs/reference/provisioning.md`
3. `docs/reference/wxc-sdk-patterns.md` *(conceptual — P0-1, P0-3 exempt)*
4. `docs/reference/call-features-major.md`
5. `docs/reference/call-features-additional.md`
6. `docs/reference/call-routing.md`

Collect results. Append findings to the report.

- [ ] **Step 2: Wave 2 — Calling docs 7-12**

Dispatch 6 Explore subagents for:
1. `docs/reference/call-control.md`
2. `docs/reference/person-call-settings-handling.md`
3. `docs/reference/person-call-settings-media.md`
4. `docs/reference/person-call-settings-permissions.md`
5. `docs/reference/person-call-settings-behavior.md`
6. `docs/reference/location-call-settings-core.md`

Collect results. Append findings to the report.

- [ ] **Step 3: Wave 3 — Calling docs 13-18**

Dispatch 6 Explore subagents for:
1. `docs/reference/location-call-settings-media.md`
2. `docs/reference/location-call-settings-advanced.md`
3. `docs/reference/emergency-services.md`
4. `docs/reference/virtual-lines.md`
5. `docs/reference/reporting-analytics.md`
6. `docs/reference/webhooks-events.md`

Collect results. Append findings to the report.

---

### Task 3: Audit Reference Docs — Device (4 files)

- [ ] **Step 1: Wave 4 — All 4 device docs**

Dispatch 4 Explore subagents for:
1. `docs/reference/devices-core.md`
2. `docs/reference/devices-dect.md`
3. `docs/reference/devices-workspaces.md`
4. `docs/reference/devices-platform.md`

Same subagent instruction as Task 2. Collect results. Append findings.

---

### Task 4: Audit Reference Docs — Admin (7 files)

- [ ] **Step 1: Wave 5 — All 7 admin docs**

Dispatch 6 Explore subagents (one agent gets 2 files):
1. `docs/reference/admin-org-management.md`
2. `docs/reference/admin-identity-scim.md`
3. `docs/reference/admin-licensing.md`
4. `docs/reference/admin-audit-security.md`
5. `docs/reference/admin-hybrid.md`
6. `docs/reference/admin-partner.md` + `docs/reference/admin-apps-data.md`

Same subagent instruction as Task 2. Collect results. Append findings.

---

### Task 5: Audit Reference Docs — Messaging (2 files)

- [ ] **Step 1: Wave 6 (combined with wxcadm) — Messaging docs**

Dispatch 2 Explore subagents for:
1. `docs/reference/messaging-spaces.md`
2. `docs/reference/messaging-bots.md`

Same subagent instruction as Task 2. Collect results. Append findings.

---

### Task 6: Audit wxcadm Docs — Limited Scope (8 files)

wxcadm docs are NOT checked against the full template. They are only checked for:
- See Also section exists with valid cross-references
- Gotchas section exists
- No stale cross-references (links to renamed/deleted files)

- [ ] **Step 1: Wave 6 (continued) — All 8 wxcadm docs**

Dispatch 4 Explore subagents (2 files each) for:
1. `docs/reference/wxcadm-core.md` + `docs/reference/wxcadm-person.md`
2. `docs/reference/wxcadm-locations.md` + `docs/reference/wxcadm-features.md`
3. `docs/reference/wxcadm-devices-workspaces.md` + `docs/reference/wxcadm-routing.md`
4. `docs/reference/wxcadm-xsi-realtime.md` + `docs/reference/wxcadm-advanced.md`

Subagent instruction (different from ref docs):
```
Read the files at {path1} and {path2}. These are wxcadm library docs — only check:

1. **See Also:** Does the file end with a See Also section containing cross-references?
   If yes: verify each link target exists (check the file path).
   If no: FAIL — needs See Also section added.

2. **Gotchas:** Does the file have a Gotchas section (at any location)?
   If yes: PASS.
   If no: FAIL — needs Gotchas section.

3. **Stale refs:** Are there any links to files that don't exist?

Return structured findings per file per check. Do not modify any files.
```

Collect results. Append findings.

---

### Task 7: Audit Skills (14 files)

Each subagent receives the canonical skill template from the spec and checks the skill against it.

Subagent instruction for skills:
```
Read the skill at {path}. Check against the canonical skill template:

For each of these dimensions, return PASS/FAIL with current state and fix needed:

- **P0-4 (Auth verification):** Does Step 2 check required scopes (not just wxcli whoami)?
- **P1-3 (Workflow consistency):** Does the skill follow the 8-step template?
  Steps: Load refs → Auth → Identify → Prerequisites (4a/4b) → Plan [SHOW BEFORE EXECUTING] → Execute (6a/6b) → Verify → Report.
  Flag if it uses lettered operations (Operation A/B/C) instead of numbered sub-steps.
- **P1-4 (Critical Rules):** Does the skill have a "Critical Rules" section?
- **P1-5 (Context Compaction):** Does the skill have a "Context Compaction Recovery" section?
- **P1-6 (Plan gate):** Does Step 5 header include `[SHOW BEFORE EXECUTING]`?
- **Frontmatter:** Does it use `allowed-tools:` and `argument-hint:` (not `tools:` or `argument_hint:`)?

Do not modify any files. Return only the structured findings.
```

- [ ] **Step 1: Wave 7 — Calling skills (7 files)**

Dispatch 4 Explore subagents:
1. `.claude/skills/provision-calling/SKILL.md` + `.claude/skills/configure-features/SKILL.md`
2. `.claude/skills/manage-call-settings/SKILL.md` + `.claude/skills/configure-routing/SKILL.md`
3. `.claude/skills/call-control/SKILL.md` + `.claude/skills/reporting/SKILL.md`
4. `.claude/skills/wxc-calling-debug/SKILL.md`

Collect results. Append findings.

- [ ] **Step 2: Wave 8 — Device + Admin + Messaging skills (7 files)**

Dispatch 4 Explore subagents:
1. `.claude/skills/manage-devices/SKILL.md` + `.claude/skills/device-platform/SKILL.md`
2. `.claude/skills/manage-identity/SKILL.md` + `.claude/skills/audit-compliance/SKILL.md`
3. `.claude/skills/manage-licensing/SKILL.md` + `.claude/skills/messaging-spaces/SKILL.md`
4. `.claude/skills/messaging-bots/SKILL.md`

Collect results. Append findings.

---

### Task 8: Audit Builder Agent + Cleanup Scan

- [ ] **Step 1: Audit builder agent dispatch table**

Read `.claude/agents/wxc-calling-builder.md`. Check:
- All 14 skills appear in the dispatch table
- All reference doc paths in the REFERENCE DOC LOADING section point to existing files
- No stale cross-references

- [ ] **Step 2: Verify cleanup candidates exist**

Confirm these 6 files exist (they should all be flagged for deletion):
```
docs/reference/_review-auth-provisioning-sdk.md
docs/reference/_review-coverage-matrix.md
docs/reference/_review-devices-control-other.md
docs/reference/_review-features-routing.md
docs/reference/_review-person-location-settings.md
docs/reference/_review-wxcadm.md
```

---

### Task 9: Synthesize Findings Report

- [ ] **Step 1: Compile all findings into the report**

Read back all subagent results (already appended incrementally). Now:
1. Count totals: P0, P1, P2 findings and affected files
2. Fill in the Summary section at the top
3. Verify no duplicate findings (same file + same dimension listed twice)
4. Sort findings within each severity tier by file path for easy scanning

- [ ] **Step 2: Save the final report**

Write the completed findings to `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md`.

- [ ] **Step 3: Present summary to user**

Show the user:
- Total findings per severity tier
- Files with the most findings (likely the older calling docs)
- Any surprises or patterns discovered
- Ask: "Ready to review the full findings report before we proceed to Phase 2?"

---

## User Review Gate

**STOP HERE.** The user reviews `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md` and decides:
- Approve as-is → proceed to Phase 2
- Request changes → update findings, re-present
- Reduce scope → user may choose to skip P2 fixes, or only do P0

---

## Phase 2: Fix (New Session)

### Task 10: Session Setup

- [ ] **Step 1: Read both documents**

Read these files in full:
1. `docs/superpowers/specs/2026-03-19-cross-spec-normalization-design.md` — canonical templates and fix rules
2. `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md` — the findings to fix

- [ ] **Step 2: Group findings by file**

Create a working list: for each file that has findings, list ALL findings (across all severity tiers). An agent editing a file should make all fixes in one pass.

- [ ] **Step 3: Sort files into priority waves**

- **Wave 1 (P0):** Files that have at least one P0 finding
- **Wave 2 (P1):** Files that have P1 findings but no P0 (P0 files already handled in Wave 1 — their P1 fixes were included)
- **Wave 3 (P2):** Files that have only P2 findings
- **Wave 4 (Cleanup):** Delete `_review-*.md` files, fix any stale cross-references

Note: When a file has findings across multiple tiers (e.g., P0 + P1 + P2), ALL its fixes go in Wave 1. This avoids editing the same file multiple times.

---

### Task 11: Execute Wave 1 — P0 Fixes

Each fix subagent receives:
1. The canonical template (reference doc or skill, as appropriate — copy from spec)
2. The file path and its specific findings list
3. This instruction:

For **reference doc** fixes:
```
Read the file at {path}. Apply these fixes:

{list of findings with "Fix needed" field from the report}

Rules:
- Add missing sections with appropriate content (not placeholders)
- When adding Raw HTTP sections: include method, URL, headers, sample body based on
  the CLI commands already documented in the same section
- When adding inline gotchas: check whether the content exists in a consolidated
  Gotchas section at the bottom — deduplicate, don't duplicate
- When reordering sections: match the canonical template order (Sources → Scopes →
  ToC → Numbered sections → Recipes → Cross-cutting Gotchas → See Also)
- Preserve all existing content — only add, reorder, or move. Do not rewrite.
- Do not resolve NEEDS VERIFICATION tags
- Do not rename or move the file
```

For **skill** fixes:
```
Read the skill at {path}. Apply these fixes:

{list of findings with "Fix needed" field from the report}

Rules:
- If converting Operation A/B/C to Step 6a/6b/6c: update ALL internal references
  to these operations throughout the file, not just the headers
- If adding Critical Rules: include at minimum (a) verify token before writes,
  (b) never delete/modify without confirmation, (c) domain-specific gotchas.
  Reference other skills' Critical Rules sections for patterns.
- If adding Context Compaction Recovery: follow the pattern from existing skills
  (read plan file, check completed steps, resume from next pending)
- If fixing plan gate: ensure Step 5 header includes `[SHOW BEFORE EXECUTING]`
- Preserve all existing content — only add, reorder, or restructure. Do not rewrite.
```

- [ ] **Step 1: Dispatch Wave 1 fix agents**

Dispatch 5-6 agents, 1-2 files each, for all files with P0 findings.
Each agent receives the appropriate instruction (ref doc or skill) plus its file's complete findings list.

- [ ] **Step 2: Spot-check 2-3 files**

After Wave 1 completes, read 2-3 modified files and verify:
- Missing sections were added with real content (not TODOs)
- Existing content was preserved
- Section ordering matches template
- No NEEDS VERIFICATION tags were touched

- [ ] **Step 3: Report Wave 1 results to user**

Show: files modified, fixes applied, any fixes that couldn't be applied. Ask: "Continue to Wave 2 (P1 fixes)?"

---

### Task 12: Execute Wave 2 — P1 Fixes

Same pattern as Task 11 but for files with P1-only findings (files that already had P0 fixes are done).

- [ ] **Step 1: Dispatch Wave 2 fix agents**
- [ ] **Step 2: Spot-check 2-3 files**
- [ ] **Step 3: Report Wave 2 results to user**

Ask: "Continue to Wave 3 (P2 cosmetic fixes)?"

---

### Task 13: Execute Wave 3 — P2 Fixes

Same pattern for files with P2-only findings.

- [ ] **Step 1: Dispatch Wave 3 fix agents**
- [ ] **Step 2: Spot-check 2-3 files**
- [ ] **Step 3: Report Wave 3 results to user**

Ask: "Continue to Wave 4 (cleanup)?"

---

### Task 14: Execute Wave 4 — Cleanup

- [ ] **Step 1: Delete `_review-*.md` files**

```bash
rm docs/reference/_review-auth-provisioning-sdk.md
rm docs/reference/_review-coverage-matrix.md
rm docs/reference/_review-devices-control-other.md
rm docs/reference/_review-features-routing.md
rm docs/reference/_review-person-location-settings.md
rm docs/reference/_review-wxcadm.md
```

- [ ] **Step 2: Fix any stale cross-references**

For each stale link found in the audit: update the path or remove the link.

- [ ] **Step 3: Verify no broken references remain**

```bash
# Grep all docs for references to deleted _review files
grep -r "_review-" docs/reference/ .claude/skills/ .claude/agents/
```

Should return zero results.

---

### Task 15: Execution Summary

- [ ] **Step 1: Write the execution summary**

Create or update `docs/superpowers/specs/2026-03-19-cross-spec-normalization-summary.md` with:
- Files modified (with line count deltas)
- Files deleted
- Fixes applied per severity tier
- Any fixes that could not be applied (with reason)
- Recommended follow-up:
  - Update CLAUDE.md file map if any paths changed
  - ~~NEEDS VERIFICATION backlog (~113 tags, requires live API)~~ Swept 2026-03-19: only 2 remain
  - Any new issues discovered during fixes

- [ ] **Step 2: Present final summary to user**

Show the execution summary and ask if any follow-up work should be done now.
