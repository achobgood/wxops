# Playbook Skill Restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make skills the primary operational layer so the builder agent dispatches to them before executing, while keeping reference docs as deep API fallback.

**Architecture:** Enrich 4 existing skills with unique operational knowledge from reference docs. Create 4 new skills for uncovered domains (routing, devices, call-control, reporting). Update the builder agent to actually dispatch to skills during execution. Reference docs stay untouched — they're API reference, not operational guides.

**Tech Stack:** Markdown files only. No CLI code changes. No reference doc changes.

**Scope:**
- 4 existing skills: enrich with cross-referenced gotchas from reference docs
- 4 new skills: create from reference doc content + CLI command mappings
- 1 agent definition: update execute phase with real skill dispatch
- 1 CLAUDE.md: update file map to reflect new structure

**Risk:** Low. CLI code untouched. Reference docs untouched. Skills are additive. Agent routing is the only behavioral change. User took a backup.

---

## File Structure

### Files to modify

| File | Change |
|------|--------|
| `.claude/agents/wxc-calling-builder.md` | Replace SKILLS section with actual dispatch logic; update EXECUTE PHASE to load skill before running commands |
| `.claude/skills/configure-features/SKILL.md` | Add AA menu gotchas discovered this session (5 items from execution report) |
| `.claude/skills/provision-calling/SKILL.md` | Add token configuration pattern (echo pipe to wxcli configure) |
| `.claude/skills/manage-call-settings/SKILL.md` | No content changes needed — already comprehensive |
| `.claude/skills/wxc-calling-debug/SKILL.md` | Already updated with token pipe pattern earlier this session |
| `CLAUDE.md` | Update file map to include new skills |

### Files to create

| File | Purpose |
|------|---------|
| `.claude/skills/configure-routing/SKILL.md` | Trunks, dial plans, route groups, route lists, translation patterns, PSTN |
| `.claude/skills/manage-devices/SKILL.md` | Phones, DECT, workspaces, activation codes, device settings |
| `.claude/skills/call-control/SKILL.md` | Real-time call control, webhooks, XSI events |
| `.claude/skills/reporting/SKILL.md` | CDR, queue/AA stats, call quality, report templates |

---

## Task 1: Enrich configure-features skill with AA gotchas

**Files:**
- Modify: `.claude/skills/configure-features/SKILL.md`
- Reference: `docs/plans/2026-03-18-multi-tier-call-flow-execution-report.md` (source of gotchas)
- Reference: `docs/reference/call-features-major.md` (already has the 5 gotchas added this session)

- [ ] **Step 1: Read the execution report for the 5 AA gotchas**

Read `docs/plans/2026-03-18-multi-tier-call-flow-execution-report.md` and `docs/reference/call-features-major.md` to extract the 5 gotchas added during this session:
1. `wxcli auto-attendants update` only handles basic fields — menu config needs raw HTTP PUT
2. `keyConfigurations.value` is mandatory even for non-transfer actions (use `""`)
3. `TRANSFER_TO_MAILBOX` needs the target extension as `value`
4. No `holidayMenu` field in AA API — `afterHoursMenu` covers both periods
5. After-hours phone numbers get normalized on read-back (`+1-919...`)

- [ ] **Step 2: Add gotchas to configure-features skill**

Add these 5 items to the CRITICAL RULES section of `configure-features/SKILL.md`. Format them as numbered rules consistent with the existing style (rules #1-12 already exist, so these become #13-17).

- [ ] **Step 3: Add raw HTTP AA menu update pattern to skill**

Add a new section "AA Menu Configuration via Raw HTTP" to the Auto Attendant section of the skill. Include the JSON structure for `businessHoursMenu` and `afterHoursMenu` with `keyConfigurations` array, since wxcli can't handle this and the skill should show the fallback pattern.

- [ ] **Step 4: Verify skill is valid markdown**

Read the full skill file and confirm it renders correctly, no broken tables or formatting.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/configure-features/SKILL.md
git commit -m "feat(skills): add 5 AA menu gotchas to configure-features from live testing"
```

---

## Task 2: Add token configuration pattern to provision-calling skill

**Files:**
- Modify: `.claude/skills/provision-calling/SKILL.md`

- [ ] **Step 1: Read current auth section of provision-calling skill**

Find the authentication/token setup section in the skill.

- [ ] **Step 2: Replace export pattern with pipe pattern**

Replace any `export WEBEX_ACCESS_TOKEN=...` instructions with:
```bash
echo "<TOKEN>" | wxcli configure
```

Add note: "Do NOT use `export WEBEX_ACCESS_TOKEN=...` — environment variables do not persist across Bash tool calls in Claude Code. The pipe pattern saves the token to `~/.wxcli/config.json`."

- [ ] **Step 3: Verify skill is valid markdown**

Read the full skill file and confirm formatting.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/provision-calling/SKILL.md
git commit -m "fix(skills): use wxcli configure pipe pattern instead of export in provision-calling"
```

---

## Task 3: Create configure-routing skill

**Files:**
- Create: `.claude/skills/configure-routing/SKILL.md`
- Reference: `docs/reference/call-routing.md` (source of API knowledge)

- [ ] **Step 1: Read call-routing reference doc**

Read `docs/reference/call-routing.md` to extract:
- CLI command mappings (wxcli call-routing, wxcli pstn, etc.)
- Prerequisite chains (trunk → route group → route list → dial plan)
- Known gotchas

- [ ] **Step 2: Read existing skill for structure template**

Read `configure-features/SKILL.md` to follow the same structure pattern:
- Frontmatter (name, description, allowed-tools)
- When to use
- Prerequisites
- Decision matrix
- Step-by-step workflow
- CLI commands with examples
- Critical rules / gotchas
- Verification steps

- [ ] **Step 3: Write the skill**

Create `.claude/skills/configure-routing/SKILL.md` with:
- **Scope:** Dial plans, trunks (premise, cloud), route groups, route lists, translation patterns, PSTN connection types
- **Decision matrix:** "What routing do you need?" → maps to trunk type, dial plan pattern, etc.
- **Dependency chain:** Trunk must exist → route group references trunk → route list references route group → dial plan references route list
- **CLI commands:** Map each operation to wxcli commands (`wxcli call-routing list-dial-plans`, `wxcli pstn list`, etc.)
- **Gotchas:** From reference doc gotchas section + any known CLI issues
- **Verification:** How to confirm routing is working (test call, CDR check)

- [ ] **Step 4: Verify skill renders correctly**

Read the file back and check formatting.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/configure-routing/SKILL.md
git commit -m "feat(skills): create configure-routing skill for dial plans, trunks, PSTN"
```

---

## Task 4: Create manage-devices skill

**Files:**
- Create: `.claude/skills/manage-devices/SKILL.md`
- Reference: `docs/reference/devices-core.md`, `docs/reference/devices-dect.md`, `docs/reference/devices-workspaces.md`

- [ ] **Step 1: Read device reference docs**

Read all 3 device reference docs to extract CLI mappings, gotchas, and workflows.

- [ ] **Step 2: Write the skill**

Create `.claude/skills/manage-devices/SKILL.md` with:
- **Scope:** Phone CRUD, activation codes, DECT networks/base stations/handsets, workspace devices, device settings, hot desking
- **Decision matrix:** "What device operation?" → maps to device type and workflow
- **CLI commands:** `wxcli devices list`, `wxcli device-settings`, `wxcli workspaces`, etc.
- **DECT workflow:** Network → base station → handset (strict dependency order)
- **Activation codes:** Generate, apply, lifecycle
- **Gotchas:** From reference docs
- **Verification:** How to confirm device is registered and functional

- [ ] **Step 3: Verify and commit**

```bash
git add .claude/skills/manage-devices/SKILL.md
git commit -m "feat(skills): create manage-devices skill for phones, DECT, workspaces"
```

---

## Task 5: Create call-control skill

**Files:**
- Create: `.claude/skills/call-control/SKILL.md`
- Reference: `docs/reference/call-control.md`, `docs/reference/webhooks-events.md`, `docs/reference/wxcadm-xsi-realtime.md`

- [ ] **Step 1: Read call-control and webhook reference docs**

Extract: API operations, token requirements (user-level OAuth), webhook event types, XSI event model.

- [ ] **Step 2: Write the skill**

Create `.claude/skills/call-control/SKILL.md` with:
- **Scope:** Real-time call operations (dial, answer, hold, transfer, park, recording control), webhooks, XSI events
- **Critical warning:** Call control requires user-level OAuth token — admin tokens get 400 "Target user not authorized". This is the #1 gotcha.
- **CLI commands:** `wxcli call-controls` (with the user-token caveat)
- **Webhook setup:** Event types, payload structure, subscription management
- **XSI section:** When to use wxcadm for real-time event monitoring (this is wxcadm's unique capability)
- **Gotchas:** User token requirement, webhook retry behavior, XSI connection management

- [ ] **Step 3: Verify and commit**

```bash
git add .claude/skills/call-control/SKILL.md
git commit -m "feat(skills): create call-control skill for real-time ops, webhooks, XSI"
```

---

## Task 6: Create reporting skill

**Files:**
- Create: `.claude/skills/reporting/SKILL.md`
- Reference: `docs/reference/reporting-analytics.md`

- [ ] **Step 1: Read reporting reference doc**

Extract: CDR fields, report templates, queue/AA stats, call quality metrics, required scopes.

- [ ] **Step 2: Write the skill**

Create `.claude/skills/reporting/SKILL.md` with:
- **Scope:** Call detail records (CDR), queue statistics, AA statistics, call quality, report templates
- **CLI commands:** `wxcli reports`, `wxcli recording-report`, `wxcli reports-detailed-call-history`, `wxcli partner-reports-templates`
- **CDR query patterns:** Date ranges, filtering by user/location, common analysis queries
- **Required scopes:** `spark-admin:calling_cdr_read` and others
- **Gotchas:** CDR availability delay, report generation async behavior, data retention limits

- [ ] **Step 3: Verify and commit**

```bash
git add .claude/skills/reporting/SKILL.md
git commit -m "feat(skills): create reporting skill for CDR, queue stats, call quality"
```

---

## Task 7: Update builder agent with real skill dispatch

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md`

This is the key behavioral change. The agent's EXECUTE PHASE must load the relevant skill BEFORE running commands.

- [ ] **Step 1: Read current agent SKILLS and EXECUTE sections**

Read lines 188-365 of the agent definition (EXECUTE PHASE through SKILLS section).

- [ ] **Step 2: Rewrite the SKILLS section**

Replace the current "Invoke skills when..." section with explicit dispatch logic:

```markdown
## SKILL DISPATCH

Before executing commands for any domain, load the relevant skill. The skill contains
CLI command mappings, gotchas, and prerequisites that prevent trial-and-error failures.

### Dispatch Table

| Task Domain | Skill to Load | What It Provides |
|-------------|---------------|------------------|
| Users, locations, licenses | provision-calling | License methods, location gotchas, bulk patterns |
| AA, CQ, HG, paging, park, pickup, VM groups | configure-features | Feature CRUD, agent assignment, AA menu raw HTTP pattern |
| Person/workspace call settings | manage-call-settings | 39-setting CLI command catalog, scope mapping, edge cases |
| Trunks, dial plans, route groups, PSTN | configure-routing | Dependency chain, trunk types, translation patterns |
| Phones, DECT, workspaces, activation codes | manage-devices | Device lifecycle, DECT workflow, activation codes |
| Real-time call ops, webhooks, XSI | call-control | User token requirement, webhook setup, XSI via wxcadm |
| CDR, queue stats, call quality | reporting | CDR query patterns, report templates, scopes |
| Any error during execution | wxc-calling-debug | Symptom-to-fix mapping, --debug flag, token diagnostics |

### How Dispatch Works

1. After the deployment plan is approved, identify which skills cover the plan's steps
2. Read each relevant skill file BEFORE executing its domain's commands
3. Follow the skill's prerequisites, CLI commands, and gotchas
4. If a command fails, load wxc-calling-debug for diagnosis
5. If the skill references a raw HTTP pattern, check `docs/reference/wxc-sdk-patterns.md`

### Multiple Skills Per Plan

Most builds touch multiple domains. Load skills as you enter each domain's steps:
- Steps creating locations/users → load provision-calling
- Steps creating features → load configure-features
- Steps configuring settings → load manage-call-settings
- On any error → load wxc-calling-debug
```

- [ ] **Step 3: Update EXECUTE PHASE to reference dispatch**

Add to the beginning of the EXECUTE PHASE section:

```markdown
Before executing, load the relevant skill(s) per the SKILL DISPATCH table above.
The skill tells you which CLI commands to use and what gotchas to watch for.
```

- [ ] **Step 4: Verify agent definition is coherent**

Read the full agent file and confirm the dispatch table, execute phase, and critical rules are consistent.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/wxc-calling-builder.md
git commit -m "feat(agent): add real skill dispatch to builder execute phase"
```

---

## Task 8: Update CLAUDE.md file map

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Read current CLAUDE.md Agent & Skills section**

Find the file map table.

- [ ] **Step 2: Add new skills to file map**

Add 4 rows to the Agent & Skills table:

```markdown
| `.claude/skills/configure-routing/` | Skill: configure routing (trunks, dial plans, PSTN) |
| `.claude/skills/manage-devices/` | Skill: manage devices (phones, DECT, workspaces) |
| `.claude/skills/call-control/` | Skill: real-time call control, webhooks, XSI |
| `.claude/skills/reporting/` | Skill: CDR, queue stats, call quality, reports |
```

- [ ] **Step 3: Update Quick Start to mention skills**

If the Quick Start section doesn't mention that skills are loaded automatically by the agent, add a note.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add 4 new skills to CLAUDE.md file map"
```

---

## Execution Order & Dependencies

```
Task 1: Enrich configure-features     (independent)
Task 2: Fix provision-calling auth     (independent)
Task 3: Create configure-routing       (independent)
Task 4: Create manage-devices          (independent)
Task 5: Create call-control            (independent)
Task 6: Create reporting               (independent)
Task 7: Update agent dispatch          (depends on Tasks 1-6 — all skills must exist)
Task 8: Update CLAUDE.md               (depends on Tasks 3-6 — new skills must exist)
```

Tasks 1-6 are fully independent and can run in parallel.
Tasks 7-8 depend on 1-6 and can run in parallel with each other.

---

## Verification

After all tasks complete:

1. Run the builder agent with a test prompt ("set up a hunt group at HQ") and confirm it loads the configure-features skill before executing
2. Run `/configure-routing` directly and confirm the skill loads and provides useful guidance
3. Run `/manage-devices` directly and confirm it loads
4. Confirm CLAUDE.md file map is accurate
5. Confirm no reference docs were modified
