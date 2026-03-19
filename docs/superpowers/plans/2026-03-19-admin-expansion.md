# Admin & Identity API Playbook Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Webex Calling playbook to cover 35 admin CLI groups (~135 commands) with 7 reference docs, 3 skills, agent updates, and CLAUDE.md updates.

**Architecture:** Each reference doc is standalone, covering a cluster of related CLI groups with CLI examples, scopes, raw HTTP fallback, and gotchas. Each skill guides users through a multi-step admin workflow. The builder agent's interview and dispatch phases expand to recognize admin objectives and route to the right skill/doc.

**Tech Stack:** Markdown docs, Claude Code skills (SKILL.md with frontmatter), wxcli CLI (for verification)

**Spec:** `docs/superpowers/specs/2026-03-19-admin-expansion-design.md`

---

## Prerequisite Knowledge

Before implementing any task, the agent MUST read these files for style/pattern reference:

- **Reference doc pattern:** `docs/reference/reporting-analytics.md` — follow this structure (title, sources, scopes table, numbered sections, CLI examples, SDK methods, raw HTTP, gotchas)
- **Skill pattern:** `.claude/skills/provision-calling/SKILL.md` — follow this structure (frontmatter, step-by-step workflow, decision matrix, critical rules, error handling, scope reference)
- **Agent pattern:** `.claude/agents/wxc-calling-builder.md` — understand the interview phase, dispatch table, and reference doc loading sections
- **Spec (authoritative):** `docs/superpowers/specs/2026-03-19-admin-expansion-design.md` — every doc outline, skill design, and agent update is specified here

## How to Write Each Reference Doc

Every reference doc MUST include these sections in order:

1. **Title and subtitle** — `# Admin: [Domain]` with one-line description
2. **Required Scopes table** — scope → purpose mapping (pull from spec's Scope Requirements table)
3. **Per-group sections** — for each CLI group covered:
   - CLI command table: `| Command | Description | HTTP Method | Path |`
   - CLI examples with actual `wxcli` commands (verify each via `wxcli <group> <command> --help`)
   - Raw HTTP fallback pattern (curl or `api.session.rest_*()`)
4. **Common Patterns / Recipes** — 3-5 real-world workflows
5. **Gotchas** — including scope troubleshooting (map 401/403 errors to required scopes)
6. **Cross-reference signposts** — one-line pointers to related calling docs (from spec)

Mark unverified info with `<!-- NEEDS VERIFICATION -->`.

## How to Write Each Skill

Every skill MUST include these sections:

1. **Frontmatter** — name, description, allowed-tools (Read, Grep, Glob, Bash), argument-hint
2. **Step 1: Load references** — list which reference docs to read
3. **Step 2: Verify auth** — `wxcli whoami` check with scope requirements
4. **Step 3: Identify need** — decision matrix table (Need → Operation → CLI Group)
5. **Step 4: Check prerequisites** — what to verify before executing
6. **Step 5: Build plan** — show-before-executing pattern
7. **Step 6: Execute** — CLI commands for each operation
8. **Step 7: Verify** — read-back confirmation
9. **Step 8: Report** — summary template
10. **Critical Rules** — numbered list of non-negotiable rules
11. **Error Handling** — common errors and fixes
12. **Required Scopes Reference** — scope table

---

## Wave 1: Reference Docs (5 + 2)

### Task 1: Write `docs/reference/admin-org-management.md`

**Files:**
- Create: `docs/reference/admin-org-management.md`

**Spec section:** Doc 1 in `docs/superpowers/specs/2026-03-19-admin-expansion-design.md`

**Groups covered:** `organizations` (3), `org-settings` (2), `org-contacts` (7), `roles` (2), `domains` (5) = 19 commands

- [ ] **Step 1: Read the spec's Doc 1 outline** for exact content requirements
- [ ] **Step 2: Read `docs/reference/reporting-analytics.md`** as style template (first 100 lines for structure)
- [ ] **Step 3: Run `wxcli <group> <command> --help`** for all 5 groups to get exact flags, descriptions, and option names. Capture the output — this is the source of truth for CLI examples.
- [ ] **Step 4: Write the doc** following the "How to Write Each Reference Doc" pattern above. Include:
  - Required Scopes table (`identity:organizations_read`, `identity:organizations_rw` for org-settings/domains; standard admin for others)
  - Domain verification workflow recipe (get token → DNS TXT → verify → claim)
  - Org contacts bulk import recipe
  - Gotcha: `org-settings create` is POST-as-upsert (same pattern as `live-monitoring create`)
  - Gotcha: scope troubleshooting for `identity:organizations_rw`
  - Cross-ref signpost: "For Webex Calling locations within an org, see [provisioning.md](provisioning.md)."
- [ ] **Step 5: Verify** all `wxcli` commands referenced in the doc exist by running `--help` on each

### Task 2: Write `docs/reference/admin-identity-scim.md`

**Files:**
- Create: `docs/reference/admin-identity-scim.md`

**Spec section:** Doc 2

**Groups covered:** `scim-users` (7), `scim-groups` (6), `scim-schemas` (3), `scim-bulk` (1), `identity-org` (3), `groups` (6), `people` (6) = 32 commands

- [ ] **Step 1: Read the spec's Doc 2 outline**
- [ ] **Step 2: Read style template** (`docs/reference/reporting-analytics.md`, first 100 lines)
- [ ] **Step 3: Run `wxcli <group> <command> --help`** for all 7 groups
- [ ] **Step 4: Write the doc.** Include:
  - Key concepts: SCIM 2.0 protocol, PUT vs PATCH, filter syntax, `scim-users` vs `people`, `scim-groups` vs `groups`
  - Required Scopes table (`identity:people_rw`, `identity:people_read`, `identity:organizations_rw`)
  - Recipes: SCIM bulk import, user search with filters, bulk deactivate, group membership, OTP generation
  - Gotcha: PUT replaces entire resource (always GET first)
  - Gotcha: `/me` endpoint needs user-level token
  - Gotcha: `--org-id` requirement (mark `<!-- NEEDS VERIFICATION -->`)
  - Cross-ref signpost: "For Webex Calling user provisioning, see [provisioning.md](provisioning.md)."
- [ ] **Step 5: Verify** all commands referenced exist

### Task 3: Write `docs/reference/admin-licensing.md`

**Files:**
- Create: `docs/reference/admin-licensing.md`

**Spec section:** Doc 3

**Groups covered:** `licenses-api` (3) + cross-ref to calling `licenses` (2) = 5 commands

- [ ] **Step 1: Read the spec's Doc 3 outline**
- [ ] **Step 2: Read style template**
- [ ] **Step 3: Run `wxcli licenses-api <command> --help`** for all 3 commands and `wxcli licenses <command> --help` for both calling commands
- [ ] **Step 4: Write the doc.** Include:
  - License types overview (Calling Professional/Basic, Meetings, Messaging, etc.)
  - `licenses-api` vs `licenses` — when to use which
  - PATCH `/licenses/users` payload format (requires `--json-body`)
  - Recipes: audit usage, find unlicensed users, bulk assign, reclaim unused
  - Gotcha: license IDs are org-specific base64
  - Gotcha: removing calling license removes all calling config (destructive)
  - Cross-ref signposts: to `provisioning.md` and to `provision-calling` skill
- [ ] **Step 5: Verify** all commands referenced exist

### Task 4: Write `docs/reference/admin-audit-security.md`

**Files:**
- Create: `docs/reference/admin-audit-security.md`

**Spec section:** Doc 4

**Groups covered:** `audit-events` (2), `security-audit` (1), `events` (2) = 5 commands

- [ ] **Step 1: Read the spec's Doc 4 outline**
- [ ] **Step 2: Read style template**
- [ ] **Step 3: Run `wxcli <group> <command> --help`** for all 3 groups
- [ ] **Step 4: Write the doc.** Include:
  - Key concepts: three different event APIs and when to use each (admin audit vs security audit vs compliance events)
  - Required Scopes table (`audit:events_read` for security-audit; standard admin for others)
  - Recipes: pull audit trail by admin/date, export security events for SIEM, compliance review by user, filter by event category
  - Gotcha: three APIs serve different purposes — don't confuse them
  - Gotcha: date range filtering essential
  - Cross-ref signpost: "For Webex Calling CDR, see [reporting-analytics.md](reporting-analytics.md)."
- [ ] **Step 5: Verify** all commands referenced exist

### Task 5: Write `docs/reference/admin-hybrid.md`

**Files:**
- Create: `docs/reference/admin-hybrid.md`

**Spec section:** Doc 5

**Groups covered:** `hybrid-clusters` (2), `hybrid-connectors` (2), `live-monitoring` (1), `analytics` (3), `meeting-qualities` (1) = 9 commands

- [ ] **Step 1: Read the spec's Doc 5 outline**
- [ ] **Step 2: Read style template**
- [ ] **Step 3: Run `wxcli <group> <command> --help`** for all 5 groups
- [ ] **Step 4: Write the doc.** Include:
  - Required Scopes table (`spark-admin:hybrid_clusters_read`, `spark-admin:hybrid_connectors_read`, `analytics:read_all`)
  - Recipes: monitor hybrid health, pull historical analytics, investigate meeting quality
  - Gotcha: `live-monitoring create` is POST-as-read
  - Gotcha: all groups are read-only
  - **CONFIRMED BUG:** analytics commands have `/v1/v1/` double-path — all 3 will fail at runtime. Document as known issue with fix path (field_overrides.yaml + regen).
  - Gotcha: meeting quality requires specific `meetingId`
- [ ] **Step 5: Verify** all commands referenced exist

### Task 6: Write `docs/reference/admin-partner.md`

**Files:**
- Create: `docs/reference/admin-partner.md`

**Spec section:** Doc 6

**Groups covered:** `partner-admins` (5), `partner-tags` (7), `partner-reports` (5) = 17 commands

- [ ] **Step 1: Read the spec's Doc 6 outline**
- [ ] **Step 2: Read style template**
- [ ] **Step 3: Run `wxcli <group> <command> --help`** for all 3 groups. Use actual CLI help output as source of truth for command names and counts — if they differ from the spec, use the actual count.
- [ ] **Step 4: Write the doc.** Include:
  - Audience note upfront: "This doc serves partner/VAR/MSP organizations. Most single-org admins will never use these commands."
  - Partner/VAR/MSP context explanation
  - Required Scopes table (`spark-admin:reports_read/write` for partner-reports; partner token for others)
  - Recipes: list customer orgs, assign partner admin, tag customers, generate partner reports
  - Gotcha: requires partner-level token
  - Gotcha: generator naming artifacts in `partner-tags`
- [ ] **Step 5: Verify** all commands referenced exist

### Task 7: Write `docs/reference/admin-apps-data.md`

**Files:**
- Create: `docs/reference/admin-apps-data.md`

**Spec section:** Doc 7

**Groups covered:** `service-apps` (1), `authorizations` (4), `activation-email` (3), `archive-users` (1), `guest-management` (2), `data-sources` (7), `classifications` (1), `resource-groups` (2), `resource-group-memberships` (4), `admin-recordings` (12), `report-templates` (1) = 38 commands

- [ ] **Step 1: Read the spec's Doc 7 outline**
- [ ] **Step 2: Read style template**
- [ ] **Step 3: Run `wxcli <group> <command> --help`** for all 11 groups. Use actual CLI help output as source of truth — if counts differ from the spec, use the actual count. Note: `admin-recordings` has a truncated description artifact (`Officer.` from "Compliance Officer") — this is cosmetic, not a command name issue.
- [ ] **Step 4: Write the doc** with 4 clear sub-sections:
  1. **Service Apps & Authorizations** (5 commands) — token lifecycle, OAuth grant management
  2. **User Lifecycle** (6 commands) — activation emails, archive, guests
  3. **Recordings** (12 commands) — admin recording management, recycle bin, sharing, group recordings
  4. **Data & Compliance** (15 commands) — data sources, classifications, resource groups, report templates
  - Required Scopes table (`spark:applications_token`, `spark-admin:datasource_read/write`, standard admin for others)
  - Cross-ref: `admin-recordings` vs `recordings` (calling spec) — explain when to use which
  - Cross-ref: report-templates signpost to `reporting-analytics.md`
  - Gotcha: `admin-recordings` has a truncated description artifact (`Officer.` from "Compliance Officer") — cosmetic, not a command name issue
  - Gotcha: activation-email is async job — poll for completion
- [ ] **Step 5: Verify** all commands referenced exist

---

## Wave 2: Skills (3 tasks)

### Task 8: Write `manage-identity` skill

**Files:**
- Create: `.claude/skills/manage-identity/SKILL.md`

**Spec section:** Skill 1

**Depends on:** Tasks 1-2 (reference docs for domains, org-contacts, identity-scim)

- [ ] **Step 1: Read the spec's Skill 1 outline** for decision matrix, critical rules, scope
- [ ] **Step 2: Read `.claude/skills/provision-calling/SKILL.md`** as style template
- [ ] **Step 3: Read the reference docs written in Wave 1:**
  - `docs/reference/admin-identity-scim.md`
  - `docs/reference/admin-org-management.md` (for domains and org-contacts sections)
- [ ] **Step 4: Write the skill** following "How to Write Each Skill" pattern. Include:
  - Frontmatter: `name: manage-identity`, `allowed-tools: Read, Grep, Glob, Bash`, `argument-hint: [operation]`
  - Decision matrix: 8 rows (SCIM sync, search, CRUD, groups, contacts, domains, cleanup, schemas)
  - Domain verification as prerequisite for SCIM sync workflows
  - CLI groups: scim-users, scim-groups, scim-bulk, scim-schemas, groups, org-contacts, domains
  - Critical rules: PUT vs PATCH, `--org-id`, bulk partial failures, `/me` needs user token, DNS verification, async jobs
  - Error handling: scope errors for `identity:people_rw`, SCIM filter syntax errors, bulk operation partial failures
  - Required Scopes Reference table
- [ ] **Step 5: Verify** the skill file has valid frontmatter and all referenced CLI commands exist

### Task 9: Write `audit-compliance` skill

**Files:**
- Create: `.claude/skills/audit-compliance/SKILL.md`

**Spec section:** Skill 2

**Depends on:** Tasks 4, 7 (reference docs for audit-security, apps-data)

- [ ] **Step 1: Read the spec's Skill 2 outline**
- [ ] **Step 2: Read `.claude/skills/reporting/SKILL.md`** as style template for the decision matrix and query workflow patterns. Follow the step numbering from this plan's "How to Write Each Skill" section, not reporting/SKILL.md's combined steps.
- [ ] **Step 3: Read the reference docs:**
  - `docs/reference/admin-audit-security.md`
  - `docs/reference/admin-apps-data.md` (for authorizations/service-apps sections)
- [ ] **Step 4: Write the skill.** Include:
  - Frontmatter: `name: audit-compliance`, `allowed-tools: Read, Grep, Glob, Bash`, `argument-hint: [audit-type]`
  - Decision matrix: 6 rows (admin audit, security, compliance, authorization review, service app token, categories)
  - CLI groups: audit-events, security-audit, events, authorizations, service-apps
  - Critical rules: different APIs for different purposes, `audit:events_read` scope, date range essential, `authorizations delete` is destructive, service app token is short-lived
  - Error handling: scope errors for `audit:events_read`, empty results (check date range), 403 on authorizations
  - Required Scopes Reference table
- [ ] **Step 5: Verify** frontmatter and CLI commands

### Task 10: Write `manage-licensing` skill

**Files:**
- Create: `.claude/skills/manage-licensing/SKILL.md`

**Spec section:** Skill 3

**Depends on:** Task 3 (admin-licensing reference doc)

- [ ] **Step 1: Read the spec's Skill 3 outline**
- [ ] **Step 2: Read `.claude/skills/provision-calling/SKILL.md`** as style template (similar provisioning workflow)
- [ ] **Step 3: Read `docs/reference/admin-licensing.md`**
- [ ] **Step 4: Write the skill.** Include:
  - Frontmatter: `name: manage-licensing`, `allowed-tools: Read, Grep, Glob, Bash`, `argument-hint: [operation]`
  - Decision matrix: 6 rows (inventory, details, assign, find unused, reclaim, calling licenses)
  - Multi-step workflow recipes:
    1. License audit: `licenses-api list` → parse consumed vs total
    2. Find unlicensed: `people list` → cross-ref with `licenses-api show`
    3. Bulk assign: build JSON → `licenses-api update --json-body` → verify
    4. Reclaim: `people list` → find inactive → remove license → verify
  - CLI groups: licenses-api, licenses (calling spec)
  - Critical rules: PATCH with `--json-body`, `licenses-api` vs `licenses`, license IDs are base64, removing calling license is destructive, verify after assign
  - Cross-ref signpost to `provision-calling` skill for calling-specific license assignment
  - Required Scopes Reference table
- [ ] **Step 5: Verify** frontmatter and CLI commands

---

## Wave 3: Agent & CLAUDE.md Updates (1 task)

### Task 11: Update builder agent and CLAUDE.md

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md`
- Modify: `CLAUDE.md`

**Spec sections:** 3a-3e (agent updates), 4a-4c (CLAUDE.md updates)

**Depends on:** Tasks 8-10 (skills must exist before agent references them)

- [ ] **Step 1: Read the spec's sections 3a-3e and 4a-4c** for exact content to add
- [ ] **Step 2: Read `.claude/agents/wxc-calling-builder.md`** to understand current structure
- [ ] **Step 3: Update agent frontmatter** — add 3 new skills to `skills:` list:
  ```
  skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, device-platform, call-control, reporting, wxc-calling-debug, manage-identity, audit-compliance, manage-licensing
  ```
- [ ] **Step 4: Update INTERVIEW PHASE** — add admin objectives to Question 1 listener:
  - Identity/directory, Audit/compliance, Licensing, Org management, Partner operations, Hybrid monitoring, Recordings/data
- [ ] **Step 5: Update SKILL DISPATCH table** — add 3 rows for manage-identity, audit-compliance, manage-licensing
- [ ] **Step 6: Update REFERENCE DOC LOADING section** — add 7 new doc sections (Organization Management, Identity & SCIM, Licensing, Audit & Security, Hybrid Infrastructure & Analytics, Partner Operations, Apps/Data/Resources)
- [ ] **Step 7: Add no-skill inline handling guidance** — define criteria for when agent handles admin operations directly vs loading a skill (read-only single commands, <5 commands, no destructive ops → inline; destructive ops → load reference doc first)
- [ ] **Step 8: Update CLAUDE.md** — add 3 skill entries to Agent & Skills table, add Reference Docs — Admin & Identity APIs table (7 entries), update Quick Start description to include admin operations. Use the exact Quick Start text from spec section 4c.
- [ ] **Step 9: Add cross-reference signposts to existing docs** — one-line signposts only:
  - In `docs/reference/provisioning.md` **Licenses section**: add signpost to `admin-licensing.md` for org-wide license management
  - In `.claude/skills/provision-calling/SKILL.md` **License Lookup Quick Reference section**: add signpost to `manage-licensing` skill and `licenses-api update` (which now provides CLI-native license assignment)
- [ ] **Step 10: Verify** all file paths in dispatch table and CLAUDE.md point to files that actually exist

---

## Wave 4: Verification (1 task)

### Task 12: Cross-check all deliverables

**Files:**
- Read-only verification of all files created/modified in Tasks 1-11

**Depends on:** All previous tasks

- [ ] **Step 1: Verify all 7 reference docs exist** at correct paths under `docs/reference/`
- [ ] **Step 2: Verify all 3 skill directories exist** with `SKILL.md` files
- [ ] **Step 3: Spot-check CLI commands** — run `wxcli <group> <command> --help` for at least 2 commands from each reference doc (14+ spot checks) to confirm commands match what docs claim
- [ ] **Step 4: Verify cross-reference links** — confirm every signpost link in admin docs points to a real file
- [ ] **Step 5: Verify agent dispatch table** — confirm all 11 skill file paths exist
- [ ] **Step 6: Verify CLAUDE.md** — confirm all new entries in file map point to real files
- [ ] **Step 7: Run `wxcli --help`** and confirm all 35 admin groups appear in the output
- [ ] **Step 8: Report** — produce a verification summary: files created, commands verified, issues found

---

## Execution Notes

### Agent swarm sizing
- Wave 1: launch Tasks 1-5 in parallel (first 5 docs), then Tasks 6-7 (remaining 2 docs)
- Wave 2: launch Tasks 8-10 in parallel (3 skills) — each agent reads its own Wave 1 docs
- Wave 3: Task 11 runs solo (touches shared files)
- Wave 4: Task 12 runs solo (read-only verification)

### Each agent needs
- The spec file path: `docs/superpowers/specs/2026-03-19-admin-expansion-design.md`
- A style template path (specified in each task)
- Access to `wxcli` CLI for command verification
- The "How to Write" instructions from this plan's Prerequisite Knowledge section

### No code changes
This entire plan creates/modifies only markdown files. No Python, no CLI code, no tests. The constraint from the spec: "Do NOT modify any CLI code."
