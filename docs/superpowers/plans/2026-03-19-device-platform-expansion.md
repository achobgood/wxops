# Device Platform Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add playbook support for 3 device platform CLI groups (device-configurations, workspace-personalization, xapi) — reference doc, skill, agent routing, and CLAUDE.md updates.

**Architecture:** Standalone reference doc + new skill + wiring into existing builder agent. No CLI code changes. Clean boundary between calling device management (existing) and device platform management (new).

**Tech Stack:** Markdown docs, YAML frontmatter, wxcli CLI

**Spec:** `docs/superpowers/specs/2026-03-19-device-platform-expansion-design.md`

---

### Task 1: Write reference doc `docs/reference/devices-platform.md` [DONE]

**Files:**
- Create: `docs/reference/devices-platform.md`

- [x] **Step 1: Read the spec's Deliverable 1 (Doc Structure section)**

- [x] **Step 2: Read existing doc for style reference**

Read: `docs/reference/devices-core.md` (first 50 lines for heading style, table format, section separators)

- [x] **Step 3: Verify CLI flags against source code**

Read and note all flags/positional args from:
- `src/wxcli/commands/device_configurations.py` — show (--device-id required, --key optional), update (--device-id required, --op, --path, --json-body)
- `src/wxcli/commands/workspace_personalization.py` — create (WORKSPACE_ID positional, --email required), show (WORKSPACE_ID positional)
- `src/wxcli/commands/xapi.py` — show (--device-id required, --name required), create (command_name positional, --device-id required, --json-body optional)

- [x] **Step 4: Write the reference doc**

Sections required (from spec):
1. Title + Overview with signposts to devices-core.md, devices-dect.md, devices-workspaces.md
2. Prerequisites (auth, RoomOS device, workspace, how to get device ID)
3. Scopes table (4 rows) with NEEDS VERIFICATION on xAPI admin token behavior
4. Section 1: Device Configurations (CLI commands with flag tables, key filtering, update pattern with examples, raw HTTP)
5. Section 2: Workspace Personalization (CLI commands, workflow, hot desking comparison, raw HTTP)
6. Section 3: xAPI (CLI commands, status queries table, command execution with examples, common commands table, reference links, raw HTTP)
7. Gotchas (9 items per spec + review findings)
8. See Also links

**Key gotchas to document:**
- device-configurations update --op/--path flags are broken → always use --json-body
- xapi create --json-body does not auto-inject deviceId → must include in body
- PATCH content type is application/json-patch+json
- xAPI only on RoomOS, not MPP

- [x] **Step 5: Verify doc has no calling device content**

Grep for: "line key", "DECT", "activation code", "MAC address", "hot desk" (should only appear in signposts/comparisons, not as instructions)

---

### Task 2: Write skill `.claude/skills/device-platform/SKILL.md` [DONE]

**Files:**
- Create: `.claude/skills/device-platform/SKILL.md`

- [x] **Step 1: Read the spec's Deliverable 2 (Skill section)**

- [x] **Step 2: Read existing skill for format reference**

Read: `.claude/skills/manage-devices/SKILL.md` — note frontmatter format, step numbering, deployment plan template, critical rules style, context compaction section

- [x] **Step 3: Write the skill**

Frontmatter:
```yaml
---
name: device-platform
description: |
  Manage RoomOS device configurations, workspace personalization, and xAPI device control
  using wxcli CLI commands. Covers device software configuration templates, user-to-workspace
  personalization, and programmatic device command execution and status queries.
  Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [device-platform-operation]
---
```

Workflow steps (MUST be in this order):
1. Load references
2. Verify auth token (scope table)
3. Identify operation (decision matrix — 6 rows)
4. Check prerequisites (device exists, workspace exists, xAPI reachability)
5. Build and present deployment plan [SHOW BEFORE EXECUTING]
6. Execute via wxcli (device configs, workspace personalization, xAPI status, xAPI commands)
7. Verify (read-back for each operation type)
8. Report results

Must include:
- All 7 critical rules from spec
- CLI bug notes (--op/--path broken, --json-body deviceId not injected)
- Scope quick reference table
- Cross-references to manage-devices skill
- Context compaction recovery section
- Error handling table

---

### Task 3: Update builder agent `.claude/agents/wxc-calling-builder.md` [DONE]

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md`

5 precise edits required:

- [x] **Step 1: (3e) Add device-platform to skills frontmatter**

Line 10 — change:
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, call-control, reporting, wxc-calling-debug
```
To:
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, device-platform, call-control, reporting, wxc-calling-debug
```

- [x] **Step 2: (3a) Add "Device platform" to interview objective list**

After the "Devices" line (~line 101), add:
```
- **Device platform**: RoomOS device configuration management, workspace personalization, xAPI device commands and status queries
```

- [x] **Step 3: (3b) Add dispatch table row**

In the Dispatch Table after the "Phones, DECT, workspaces, activation codes" row, add:
```
| RoomOS device configs, workspace personalization, xAPI | `.claude/skills/device-platform/SKILL.md` | Device config management, xAPI commands, personalization workflow |
```

- [x] **Step 4: (3c) Add to Multiple Skills Per Plan**

After "Steps provisioning devices → read manage-devices", add:
```
- Steps managing RoomOS configs, personalization, or xAPI → read device-platform
```

- [x] **Step 5: (3d) Add Reference Doc Loading section**

After the "Devices (phones, DECT, workspaces)" section, add:
```markdown
### Device Platform (RoomOS configurations, personalization, xAPI)
```​
docs/reference/devices-platform.md     — device configs, workspace personalization, xAPI
```​
```

---

### Task 4: Update CLAUDE.md [DONE]

**Files:**
- Modify: `CLAUDE.md`

3 precise edits:

- [x] **Step 1: Add skill row to Agent & Skills table**

After the manage-devices row, add:
```
| `.claude/skills/device-platform/` | Skill: manage RoomOS device configs, workspace personalization, xAPI |
```

- [x] **Step 2: Add reference doc row to Reference Docs table**

After the devices-workspaces.md row, add:
```
| `docs/reference/devices-platform.md` | RoomOS device configurations, workspace personalization, xAPI |
```

- [x] **Step 3: Update Sync Protocol device file count**

Line 167 — change:
```
- Devices: `docs/reference/devices-*.md` (3 files: core, dect, workspaces)
```
To:
```
- Devices: `docs/reference/devices-*.md` (4 files: core, dect, workspaces, platform)
```

---

### Task 5: Verify all deliverables against spec criteria [TODO]

**Files:**
- Read (verify only): all files created/modified in Tasks 1-4

9 verification criteria from the spec. Each must pass.

- [ ] **Step 1: Criterion 1 — Reference doc exists with all sections**

Read `docs/reference/devices-platform.md` and confirm these sections exist:
- Overview with signposts
- Prerequisites
- Scopes table
- Section 1: Device Configurations (CLI commands, key filtering, update pattern, raw HTTP)
- Section 2: Workspace Personalization (CLI commands, workflow, hot desking comparison, raw HTTP)
- Section 3: xAPI (CLI commands, status queries, command execution, common commands/queries tables, raw HTTP)
- Gotchas
- See Also

- [ ] **Step 2: Criterion 2 — Skill exists with correct workflow**

Read `.claude/skills/device-platform/SKILL.md` and confirm:
- Frontmatter matches spec (name, description, allowed-tools, argument-hint)
- 8 steps in correct order: load refs → auth → identify → prereqs → plan → execute → verify → report
- Step 5 is "Build and present deployment plan" (NOT execute)
- Step 6 is "Execute" (NOT plan)

- [ ] **Step 3: Criterion 3 — All 6 CLI commands with correct flags**

Cross-check reference doc CLI flag tables against source code:
- `device_configurations.py` show: --device-id (required), --key (optional), --output, --debug
- `device_configurations.py` update: --device-id (required), --op, --path, --json-body, --debug
- `workspace_personalization.py` create: WORKSPACE_ID (positional), --email (required), --json-body, --debug
- `workspace_personalization.py` show: WORKSPACE_ID (positional), --output, --debug
- `xapi.py` show: --device-id (required), --name (required), --output, --debug
- `xapi.py` create: command_name (positional), --device-id (required), --json-body, --debug

Run: `wxcli device-configurations show --help`, `wxcli device-configurations update --help`, `wxcli workspace-personalization create --help`, `wxcli workspace-personalization show --help`, `wxcli xapi show --help`, `wxcli xapi create --help`

Compare each flag against the doc. Any mismatch = FAIL.

- [ ] **Step 4: Criterion 4 — Builder agent has all 5 updates**

Read `.claude/agents/wxc-calling-builder.md` and confirm:
- (3a) "Device platform" appears in interview objective list after "Devices"
- (3b) device-platform row in dispatch table
- (3c) "Steps managing RoomOS configs, personalization, or xAPI → read device-platform" in Multiple Skills Per Plan
- (3d) "Device Platform (RoomOS configurations, personalization, xAPI)" section in Reference Doc Loading
- (3e) "device-platform" in skills frontmatter (line 10)

- [ ] **Step 5: Criterion 5 — CLAUDE.md has all 3 updates**

Read `CLAUDE.md` and confirm:
- device-platform skill row in Agent & Skills table
- devices-platform.md row in Reference Docs table
- "(4 files: core, dect, workspaces, platform)" in Sync Protocol

- [ ] **Step 6: Criterion 6 — Signposts point to correct docs**

In `docs/reference/devices-platform.md`, confirm signposts link to:
- devices-core.md
- devices-dect.md
- devices-workspaces.md

- [ ] **Step 7: Criterion 7 — No calling device content leaked**

Grep `docs/reference/devices-platform.md` for calling-specific terms that should NOT appear as instructions:
- "activation code" (should only appear in signpost)
- "DECT" (should only appear in signpost)
- "line key" (should not appear at all)
- "MAC address" (should not appear at all)

Grep `.claude/skills/device-platform/SKILL.md` for the same terms — should only appear in cross-references.

- [ ] **Step 8: Criterion 8 — No existing files modified except agent + CLAUDE.md**

Confirm these files were NOT modified:
- `docs/reference/devices-core.md`
- `docs/reference/devices-dect.md`
- `docs/reference/devices-workspaces.md`
- `.claude/skills/manage-devices/SKILL.md`
- Any file in `src/wxcli/`

Run: `git diff --name-only` and confirm only these modified files appear:
- `.claude/agents/wxc-calling-builder.md`
- `CLAUDE.md`

Plus these new files:
- `docs/reference/devices-platform.md`
- `.claude/skills/device-platform/SKILL.md`

- [ ] **Step 9: Criterion 9 — NEEDS VERIFICATION tags present**

Grep both new files for `NEEDS VERIFICATION`:
- `docs/reference/devices-platform.md` — should have at least 1 (xAPI scope behavior)
- `.claude/skills/device-platform/SKILL.md` — should have at least 1 (xAPI scope behavior)

- [ ] **Step 10: Report results**

Print pass/fail for all 9 criteria. If any fail, describe the fix needed.
