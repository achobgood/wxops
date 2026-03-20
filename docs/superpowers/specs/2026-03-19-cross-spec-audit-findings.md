# Cross-Spec Audit Findings

## Summary
- Files audited: 54 (31 reference docs + 8 wxcadm docs + 14 skills + 1 builder agent)
- P0 findings: 23 across 20 files
- P1 findings: 26 across 19 files
- P2 findings: 39 across 28 files
- wxcadm limited-scope findings: 4 files missing Gotchas sections
- Cleanup items: 6 `_review-*.md` files to delete, 0 stale cross-references in builder agent

### Pattern Summary
- **P0-3 (CLI Examples)** is the most common P0 failure — 10 of 18 calling docs lack `wxcli` command examples (they have SDK/Raw HTTP but not CLI)
- **P2-1 (Sources)** is the most pervasive gap — 18 of 31 reference docs lack a formal Sources section
- **P1-3 (Skill workflow)** affects 9 of 14 skills — step counts range from 5 to 14 instead of canonical 8
- **P2-4 (Cross-cutting Gotchas)** missing in 11 docs — older calling docs consolidated gotchas at bottom without separating inline vs cross-cutting
- Admin docs (built later) are the most compliant; older calling docs have the most gaps

---

## P0 — Blocks Users

### P0-1: Raw HTTP Fallback — Missing in 3 files

- **File:** `docs/reference/provisioning.md`
  - **Current state:** Raw HTTP present for People, Licenses, Locations sections — absent for Organization API section
  - **Fix:** Add Raw HTTP subsection to Organization API section

- **File:** `docs/reference/admin-identity-scim.md`
  - **Current state:** Raw HTTP present for sections 1, 4, 5, 6, 7 — absent for Section 2 (SCIM Groups) and Section 3 (SCIM Schemas)
  - **Fix:** Add Raw HTTP subsections with curl examples for SCIM Groups and SCIM Schemas endpoints

- **File:** `docs/reference/messaging-bots.md`
  - **Current state:** CLI examples present in Sections 2, 3, 5, 6, 7 — no Raw HTTP fallback in any section
  - **Fix:** Add Raw HTTP subsection to Sections 2 (Sending Messages), 3 (Card Recipes), 5 (Attachment Actions), 6 (Room Tabs), 7 (Cross-Domain Recipes)

### P0-2: Required Scopes — Missing in 3 files

- **File:** `docs/reference/wxc-sdk-patterns.md`
  - **Current state:** Section 3 "Authentication Patterns" covers OAuth but no scopes table
  - **Fix:** Add "## Required Scopes" section documenting token type requirements for common SDK operations

- **File:** `docs/reference/person-call-settings-media.md`
  - **Current state:** Scopes documented inline per method, not in consolidated table
  - **Fix:** Add "## Required Scopes" section consolidating all scopes from the 12 feature sections

- **File:** `docs/reference/messaging-bots.md`
  - **Current state:** Bot token scopes listed in Section 1 but no canonical table with token type requirements per command group
  - **Fix:** Add structured scopes table showing bot vs user vs admin token requirements per command group

### P0-3: CLI Examples — Missing in 10 files

- **File:** `docs/reference/call-features-major.md`
  - **Current state:** SDK method examples and Raw HTTP present; no `wxcli` command examples
  - **Fix:** Add CLI Examples subsection to Auto Attendants, Call Queues, Hunt Groups, Shared Forwarding sections

- **File:** `docs/reference/call-features-additional.md`
  - **Current state:** Raw HTTP present; no `wxcli` command examples for any of 11 features
  - **Fix:** Add CLI Examples to all 11 feature sections (Paging, Call Park, Call Park Extensions, Call Pickup, Voicemail Groups, CX Essentials, Operating Modes, Call Recording, Announcements, Single Number Reach, Virtual Extensions)

- **File:** `docs/reference/person-call-settings-handling.md`
  - **Current state:** SDK method examples and Raw HTTP present; no `wxcli` commands
  - **Fix:** Add CLI Examples to all 10 feature sections

- **File:** `docs/reference/person-call-settings-media.md`
  - **Current state:** SDK and Raw HTTP examples only; no `wxcli` commands
  - **Fix:** Add CLI Examples to all 12 feature sections

- **File:** `docs/reference/person-call-settings-permissions.md`
  - **Current state:** Raw HTTP Python code present; no `wxcli` commands
  - **Fix:** Add CLI Examples to all 5 sections

- **File:** `docs/reference/person-call-settings-behavior.md`
  - **Current state:** Some scattered CLI commands inline but not structured; sections 1, 5, 9, 10, 12, 15, 16 lack explicit CLI Examples
  - **Fix:** Formalize CLI Examples subsections in sections missing them

- **File:** `docs/reference/location-call-settings-core.md`
  - **Current state:** Raw HTTP examples throughout; no `wxcli` commands
  - **Fix:** Add CLI Examples showing `wxcli location-call-settings` commands

- **File:** `docs/reference/location-call-settings-advanced.md`
  - **Current state:** Raw HTTP code examples present; no `wxcli` commands
  - **Fix:** Add CLI Examples to each section (Call Recording, Caller Reputation, Operating Modes, etc.)

- **File:** `docs/reference/emergency-services.md`
  - **Current state:** SDK code examples; no `wxcli` commands
  - **Fix:** Add CLI Examples for call notification, emergency address, ECBN commands

- **File:** `docs/reference/reporting-analytics.md`
  - **Current state:** SDK and Raw HTTP Python examples; no `wxcli` commands
  - **Fix:** Add CLI Examples for CDR queries, report templates, report creation/download

### P0-4: Auth Verification in Skills — Fails in 7 skills

- **File:** `.claude/skills/manage-call-settings/SKILL.md`
  - **Current state:** Step 2 has only `wxcli whoami` check; scopes table exists at line 458 but not in Step 2
  - **Fix:** Move/copy scopes table into Step 2; add scope verification logic

- **File:** `.claude/skills/call-control/SKILL.md`
  - **Current state:** Step 1 checks `wxcli whoami` only; scopes table at line 36 placed after whoami, not integrated
  - **Fix:** Integrate scopes table into auth verification step with explicit scope checking

- **File:** `.claude/skills/reporting/SKILL.md`
  - **Current state:** Step 1 loads refs and runs `wxcli whoami`; scopes table is reference-only, not verification gate
  - **Fix:** Add scope verification as explicit gate in Step 2

- **File:** `.claude/skills/wxc-calling-debug/SKILL.md`
  - **Current state:** Step 2b has scope reference table but doesn't verify scopes for specific debug operation
  - **Fix:** Add scope verification logic relevant to the debug operation being performed

- **File:** `.claude/skills/audit-compliance/SKILL.md`
  - **Current state:** Step 2 runs `wxcli whoami`; scopes table at lines 29-36 is too brief
  - **Fix:** Expand scopes table with detailed mappings per audit type; integrate into Step 2

- **File:** `.claude/skills/manage-licensing/SKILL.md`
  - **Current state:** Step 2 only checks `wxcli whoami`; scopes table at line 428 (after Critical Rules, not in Step 2)
  - **Fix:** Move scopes table into Step 2; add token type verification

- **File:** `.claude/skills/messaging-bots/SKILL.md`
  - **Current state:** Step 2 lists bot scopes but doesn't verify token against requirements
  - **Fix:** Add verification logic comparing token's actual scopes against required scopes

---

## P1 — Causes Confusion

### P1-1: Inline Gotchas — Inconsistent in 9 files

- **File:** `docs/reference/authentication.md`
  - **Current state:** NEEDS VERIFICATION comments inline but no structured Gotchas subsections
  - **Fix:** Add "### Gotchas" subsections under OAuth, Bot Tokens, Guest Issuer sections

- **File:** `docs/reference/provisioning.md`
  - **Current state:** All 21 gotchas consolidated in "Common Gotchas" at bottom; none inline
  - **Fix:** Move section-specific gotchas inline after their sections; keep cross-cutting ones at bottom

- **File:** `docs/reference/call-control.md`
  - **Current state:** Gotchas scattered inline as code comments and notes (lines 236, 397, 539, 595, 655)
  - **Fix:** Consolidate into dedicated "### Gotchas" subsections per major section

- **File:** `docs/reference/person-call-settings-handling.md`
  - **Current state:** Gotchas embedded in comments and notes but not in dedicated subsections
  - **Fix:** Create "### Gotchas" subsections in sections 1, 4, 5, 6, 7, 8, 9, 10

- **File:** `docs/reference/person-call-settings-behavior.md`
  - **Current state:** Inline comments about issues but no structured Gotchas subsections
  - **Fix:** Create "### Gotchas" subsections in sections 6, 8, 10, 14

- **File:** `docs/reference/devices-core.md`
  - **Current state:** "Raw HTTP Gotchas" buried in section 6.8; nothing inline after sections 1-3
  - **Fix:** Move section-specific gotchas inline; elevate "Raw HTTP Gotchas" to standalone section

- **File:** `docs/reference/admin-org-management.md`
  - **Current state:** All gotchas grouped in dedicated section at bottom; none inline
  - **Fix:** Move section-specific gotchas inline after their sections

- **File:** `docs/reference/admin-identity-scim.md`
  - **Current state:** All 8 gotchas at bottom in "Gotchas" section; none inline
  - **Fix:** Move section-specific gotchas inline (e.g., PUT-replaces after SCIM Users section)

- **File:** `docs/reference/admin-licensing.md`
  - **Current state:** All 8 gotchas at bottom; none inline
  - **Fix:** Move gotchas 4, 6, 7, 8 inline to relevant sections; keep 1-3 as cross-cutting

### P1-3: Skill Workflow Consistency — Fails in 9 skills

- **File:** `.claude/skills/configure-features/SKILL.md`
  - **Current state:** 9 steps instead of 8
  - **Fix:** Merge Step 9 (Report) into Step 8; renumber

- **File:** `.claude/skills/manage-call-settings/SKILL.md`
  - **Current state:** 9 steps; plan at Step 6 not Step 5
  - **Fix:** Consolidate to 8 steps; move plan to Step 5

- **File:** `.claude/skills/configure-routing/SKILL.md`
  - **Current state:** 12 steps (Steps 5-8 detail component types separately)
  - **Fix:** Consolidate Steps 5-8 into Step 4 prerequisites with sub-steps; renumber to 8 total

- **File:** `.claude/skills/call-control/SKILL.md`
  - **Current state:** 7 steps with non-standard labels; approach-based rather than workflow-based
  - **Fix:** Restructure to canonical 8-step flow

- **File:** `.claude/skills/reporting/SKILL.md`
  - **Current state:** 9 steps with report-type-based organization (Steps 3-8 are different report types)
  - **Fix:** Restructure so report types are sub-steps within Steps 4/6, not separate top-level steps

- **File:** `.claude/skills/wxc-calling-debug/SKILL.md`
  - **Current state:** 5 steps; diagnostic flow (not deployment-oriented)
  - **Fix:** Restructure to 8 steps; adapt diagnostic flow to canonical structure

- **File:** `.claude/skills/manage-devices/SKILL.md`
  - **Current state:** 14 steps (Steps 5-10 are device type categories)
  - **Fix:** Consolidate device types into Step 4 prerequisites with sub-steps; renumber to 8 total

- **File:** `.claude/skills/audit-compliance/SKILL.md`
  - **Current state:** 10 steps with lettered sub-steps
  - **Fix:** Consolidate to 8 steps with numbered sub-steps

- **File:** `.claude/skills/messaging-bots/SKILL.md`
  - **Current state:** 9 steps; Step 5 is "Select card recipe" not plan gate
  - **Fix:** Restructure to 8 steps; move plan gate to Step 5

### P1-4: Skill Critical Rules — Missing in 1 skill

- **File:** `.claude/skills/wxc-calling-debug/SKILL.md`
  - **Current state:** No Critical Rules section
  - **Fix:** Add Critical Rules section with at minimum: verify token before writes, never modify without confirmation, domain-specific debug gotchas

### P1-6: Plan Gate Wording — Fails in 7 skills

- **File:** `.claude/skills/configure-features/SKILL.md`
  - **Current state:** Plan at Step 6 with backtick-wrapped `[SHOW BEFORE EXECUTING]`
  - **Fix:** Move plan to Step 5; remove backticks from marker

- **File:** `.claude/skills/manage-call-settings/SKILL.md`
  - **Current state:** Step 5 says `[Always do this first]`; Step 6 says `[Present to user before executing]`
  - **Fix:** Step 5 header should use `[SHOW BEFORE EXECUTING]`

- **File:** `.claude/skills/call-control/SKILL.md`
  - **Current state:** No plan gate step exists
  - **Fix:** Add Step 5 with `[SHOW BEFORE EXECUTING]` marker

- **File:** `.claude/skills/reporting/SKILL.md`
  - **Current state:** No plan gate step
  - **Fix:** Add Step 5 with `[SHOW BEFORE EXECUTING]` marker

- **File:** `.claude/skills/manage-devices/SKILL.md`
  - **Current state:** Plan gate at Step 11 (should be Step 5)
  - **Fix:** Move plan to Step 5 after restructuring

- **File:** `.claude/skills/audit-compliance/SKILL.md`
  - **Current state:** Step 5 is "Platform events (compliance)" — not a plan gate
  - **Fix:** Add proper plan gate at Step 5 with `[SHOW BEFORE EXECUTING]`

- **File:** `.claude/skills/messaging-bots/SKILL.md`
  - **Current state:** Step 5 is "Select card recipe" — no plan gate
  - **Fix:** Add plan gate at Step 5 with `[SHOW BEFORE EXECUTING]`

---

## P2 — Cosmetic

### P2-1: Sources Section — Missing in 18 files

- `docs/reference/authentication.md`
- `docs/reference/provisioning.md`
- `docs/reference/call-features-major.md`
- `docs/reference/call-features-additional.md`
- `docs/reference/call-routing.md`
- `docs/reference/call-control.md`
- `docs/reference/person-call-settings-handling.md`
- `docs/reference/person-call-settings-media.md`
- `docs/reference/location-call-settings-core.md`
- `docs/reference/location-call-settings-media.md`
- `docs/reference/location-call-settings-advanced.md`
- `docs/reference/webhooks-events.md`
- `docs/reference/devices-core.md`
- `docs/reference/devices-dect.md`
- `docs/reference/devices-workspaces.md`
- `docs/reference/devices-platform.md`
- `docs/reference/messaging-spaces.md`
- `docs/reference/messaging-bots.md`

**Fix for all:** Add `## Sources` section after title listing wxc_sdk version, OpenAPI spec, and developer.webex.com as applicable.

### P2-2: Table of Contents — Missing in 10 files

- `docs/reference/wxc-sdk-patterns.md` — 11 sections, no ToC header
- `docs/reference/call-control.md` — 8 sections, no ToC
- `docs/reference/emergency-services.md` — 5 sections, no explicit ToC
- `docs/reference/virtual-lines.md` — 7 sections, no explicit ToC header
- `docs/reference/webhooks-events.md` — 9 sections, no ToC
- `docs/reference/devices-core.md` — 6 sections, no ToC
- `docs/reference/admin-org-management.md` — 7 sections, no ToC
- `docs/reference/admin-identity-scim.md` — 10+ sections, no ToC
- `docs/reference/admin-licensing.md` — 9 sections, no explicit ToC
- `docs/reference/admin-apps-data.md` — 4 sections, no explicit ToC

**Fix for all:** Add `## Table of Contents` with numbered links to all major sections.

### P2-3: Header Consistency — All files PASS

No findings.

### P2-4: Cross-cutting Gotchas Section — Missing in 11 files

- `docs/reference/authentication.md`
- `docs/reference/call-features-major.md`
- `docs/reference/call-features-additional.md`
- `docs/reference/person-call-settings-handling.md`
- `docs/reference/person-call-settings-media.md`
- `docs/reference/person-call-settings-permissions.md`
- `docs/reference/person-call-settings-behavior.md`
- `docs/reference/location-call-settings-advanced.md`
- `docs/reference/emergency-services.md`
- `docs/reference/messaging-spaces.md`
- `docs/reference/messaging-bots.md`

**Fix for all:** Add `## Gotchas (Cross-Cutting)` section before `## See Also` for issues spanning multiple sections.

---

## wxcadm Limited-Scope Findings

### Gotchas Section Missing — 4 files

- `docs/reference/wxcadm-core.md` — No Gotchas section; See Also PASS, no stale refs
- `docs/reference/wxcadm-person.md` — No Gotchas section; has NEEDS VERIFICATION tags but no formal section; See Also PASS
- `docs/reference/wxcadm-devices-workspaces.md` — No Gotchas section; has NEEDS VERIFICATION tags; See Also PASS
- `docs/reference/wxcadm-advanced.md` — No Gotchas section; has NEEDS VERIFICATION tags at lines 547, 601, 802; See Also PASS

**Fix for all:** Add `## Gotchas` section consolidating known issues and NEEDS VERIFICATION items.

### All Checks Pass — 4 files

- `docs/reference/wxcadm-locations.md` — See Also PASS, Gotchas PASS, no stale refs
- `docs/reference/wxcadm-features.md` — See Also PASS, Gotchas PASS (via bug notes), no stale refs
- `docs/reference/wxcadm-routing.md` — See Also PASS, Gotchas PASS (via NEEDS VERIFICATION), no stale refs
- `docs/reference/wxcadm-xsi-realtime.md` — See Also PASS, Gotchas PASS (12 gotchas), no stale refs

---

## Cleanup

### _review-*.md files to delete

- `docs/reference/_review-auth-provisioning-sdk.md`
- `docs/reference/_review-coverage-matrix.md`
- `docs/reference/_review-devices-control-other.md`
- `docs/reference/_review-features-routing.md`
- `docs/reference/_review-person-location-settings.md`
- `docs/reference/_review-wxcadm.md`

### Builder Agent

- Dispatch table: All 14 skills present — PASS
- Reference doc paths: All 39 paths valid — PASS
- Stale cross-references: None found — PASS

### Stale cross-references

No stale cross-references found in any audited file.

---

## Files With Most Findings

| File | P0 | P1 | P2 | Total |
|------|----|----|-----|-------|
| `messaging-bots.md` (ref doc) | 3 | 0 | 2 | 5 |
| `person-call-settings-media.md` | 2 | 0 | 2 | 4 |
| `person-call-settings-handling.md` | 1 | 1 | 2 | 4 |
| `person-call-settings-behavior.md` | 1 | 1 | 1 | 3 |
| `call-features-major.md` | 1 | 0 | 2 | 3 |
| `call-features-additional.md` | 1 | 0 | 2 | 3 |
| `call-control.md` | 0 | 1 | 2 | 3 |
| `emergency-services.md` | 1 | 0 | 2 | 3 |
| `call-control/SKILL.md` | 1 | 2 | 0 | 3 |
| `reporting/SKILL.md` | 1 | 2 | 0 | 3 |
| `audit-compliance/SKILL.md` | 1 | 2 | 0 | 3 |
| `wxc-calling-debug/SKILL.md` | 1 | 2 | 0 | 3 |
| `manage-devices/SKILL.md` | 0 | 2 | 0 | 2 |

## Fully Compliant Files (0 findings)

### Reference Docs
- `docs/reference/admin-audit-security.md`
- `docs/reference/admin-hybrid.md`
- `docs/reference/admin-partner.md`

### Skills
- `.claude/skills/provision-calling/SKILL.md`
- `.claude/skills/device-platform/SKILL.md`
- `.claude/skills/manage-identity/SKILL.md`
- `.claude/skills/messaging-spaces/SKILL.md`
