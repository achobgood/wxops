# Messaging Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add messaging API reference docs, skills, and agent integration to the Webex playbook.

**Architecture:** 4 new files (2 reference docs, 2 skills), 3 modified files (webhooks-events.md, wxc-calling-builder.md, CLAUDE.md). All documentation — no code changes. Each task produces one file that can be reviewed independently.

**Tech Stack:** Markdown documentation, YAML frontmatter for skills

**Spec:** `docs/superpowers/specs/2026-03-19-messaging-expansion-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `docs/reference/messaging-spaces.md` | Spaces, messages, memberships, teams, ECM, HDS — the admin/space-manager reference |
| Create | `docs/reference/messaging-bots.md` | Bot fundamentals, adaptive card recipes, attachment actions, room tabs, cross-domain — the developer reference |
| Modify | `docs/reference/webhooks-events.md` | Add sections 4b (messaging resource events) and 6b (bot webhook pattern) |
| Create | `.claude/skills/messaging-spaces/SKILL.md` | Skill: space lifecycle, team management, membership, ECM, HDS |
| Create | `.claude/skills/messaging-bots/SKILL.md` | Skill: bot building, card recipes, webhook setup, cross-domain |
| Modify | `.claude/agents/wxc-calling-builder.md` | 8 additive changes: frontmatter, interview ×3, dispatch, doc loading, setup check, multi-skill mapping |
| Modify | `CLAUDE.md` | Add 2 skills + 2 ref docs to file map, update webhooks-events.md description |

---

### Task 1: Reference Doc — `messaging-spaces.md`

**Files:**
- Create: `docs/reference/messaging-spaces.md`

**Source material to read:**
- Spec sections: "Reference Doc 1" (lines 69-245 of the spec)
- Structural model: `docs/reference/call-features-major.md` (for format/tone)
- CLI help: `wxcli rooms --help`, `wxcli messages --help`, `wxcli memberships --help`, `wxcli teams --help`, `wxcli team-memberships --help`, `wxcli ecm --help`, `wxcli hds --help`
- Generated command files (for exact parameter names): `src/wxcli/commands/rooms.py`, `src/wxcli/commands/messages.py`, `src/wxcli/commands/memberships.py`, `src/wxcli/commands/teams.py`, `src/wxcli/commands/team_memberships.py`, `src/wxcli/commands/ecm.py`, `src/wxcli/commands/hds.py`

**Critical boundary rules (from spec "Scope Boundaries"):**
- This doc covers: plain text/markdown/file messages, message CRUD, direct messages, threading
- This doc does NOT cover: adaptive card payloads (`--json-body` with `attachments`) — that's `messaging-bots.md`
- Token type matrix goes at the TOP of the doc, before any API details
- ECM is here (it's space-scoped admin work)
- HDS is here (read-only monitoring subsection)

- [ ] **Step 1: Read the structural model**

Read `docs/reference/call-features-major.md` to match the established doc format: section headers, CLI command tables, gotchas sections, Raw HTTP patterns, See Also links.

- [ ] **Step 2: Read all 7 CLI command files**

Read the generated Python files to extract exact parameter names, option flags, boolean toggles, and default values. These are the source of truth — not the spec's approximations.

Files: `src/wxcli/commands/rooms.py`, `messages.py`, `memberships.py`, `teams.py`, `team_memberships.py`, `ecm.py`, `hds.py`

- [ ] **Step 3: Write `docs/reference/messaging-spaces.md`**

Follow the spec's 9-section structure exactly:
1. Messaging Model Overview (hierarchy diagram, space vs room terminology)
2. Spaces (rooms — 6 commands)
3. Messages (6 commands, format options, threading)
4. Memberships (5 commands, moderator roles)
5. Teams + Team Memberships (10 commands)
6. ECM (5 commands, admin-only)
7. HDS (7 commands, read-only, admin-only)
8. Common Patterns (bulk recipes, audit patterns)
9. See Also (messaging-bots.md, webhooks-events.md, authentication.md)

Token type matrix at top. Each section has: CLI command table, key parameters, gotchas. Mark unverified info with `<!-- NEEDS VERIFICATION -->`.

- [ ] **Step 4: Verify cross-references**

Confirm all See Also links point to files that exist or will exist. Confirm the message-sending boundary: no adaptive card content in this doc.

- [ ] **Step 5: Commit**

```bash
git add docs/reference/messaging-spaces.md
git commit -m "docs: add messaging-spaces reference doc — spaces, messages, teams, ECM, HDS"
```

---

### Task 2: Reference Doc — `messaging-bots.md`

**Files:**
- Create: `docs/reference/messaging-bots.md`

**Source material to read:**
- Spec sections: "Reference Doc 2" (lines 247-475 of the spec)
- Structural model: `docs/reference/call-control.md` (for runtime/developer doc tone)
- CLI help: `wxcli attachment-actions --help`, `wxcli room-tabs --help`
- Generated command files: `src/wxcli/commands/attachment_actions.py`, `src/wxcli/commands/room_tabs.py`
- Adaptive Cards reference: https://adaptivecards.io/explorer/ (for recipe accuracy)
- Webex cards guide: developer.webex.com/docs/api/guides/cards (for Webex-specific gaps)

**Critical boundary rules:**
- This doc covers: adaptive card payloads, card recipes, attachment actions, room tabs, cross-domain recipes, bot fundamentals
- This doc does NOT cover: plain text/markdown message sending (that's `messaging-spaces.md`), webhook CRUD (that's `webhooks-events.md`)
- Webhook signpost is ONE paragraph pointing to `webhooks-events.md`, not a duplicate
- Room tabs section needs bold callout: requires user token, NOT bot token

- [ ] **Step 1: Read the structural model and CLI files**

Read `docs/reference/call-control.md` for format. Read `src/wxcli/commands/attachment_actions.py` and `src/wxcli/commands/room_tabs.py` for exact parameters.

- [ ] **Step 2: Research adaptive card recipes**

Use web search to verify Webex Adaptive Cards 1.3 support level and identify any rendering gaps. Check:
- Which elements are supported/unsupported
- Card payload size limits
- Known rendering differences between desktop/mobile/web

This informs Section 4 (gaps/gotchas) — mark anything unconfirmed with `<!-- NEEDS VERIFICATION -->`.

- [ ] **Step 3: Write `docs/reference/messaging-bots.md`**

Follow the spec's 9-section structure:
1. Bot Fundamentals (bot vs user vs admin, capabilities, token detection via `wxcli whoami`)
2. Sending Messages (three-tier: text → markdown → card, `--json-body` pattern)
3. Adaptive Card Recipe Catalog (6 recipes, each with complete JSON + wxcli command + response handling)
4. Webex Adaptive Cards Supported Features and Gaps
5. Attachment Actions (2 commands, the Action.Submit response flow)
6. Room Tabs (5 commands, bold user-token-only callout)
7. Cross-Domain Recipes (3 patterns: queue alert, voicemail notification, incident response)
8. Webhook Signpost (one paragraph + `wxcli webhooks create` example)
9. See Also

Each recipe in Section 3 must include: complete JSON payload, `wxcli messages create --json-body` command, and (for interactive recipes) the attachment action response handling.

- [ ] **Step 4: Verify cross-references and boundary compliance**

Confirm: no webhook CRUD content duplicated from `webhooks-events.md`. Confirm: no plain text/markdown message patterns duplicated from `messaging-spaces.md`. Confirm: room tabs section has token callout.

- [ ] **Step 5: Commit**

```bash
git add docs/reference/messaging-bots.md
git commit -m "docs: add messaging-bots reference doc — bot patterns, card recipes, cross-domain"
```

---

### Task 3: Expand `webhooks-events.md`

**Files:**
- Modify: `docs/reference/webhooks-events.md`

**Source material to read:**
- Spec sections: "Reference Doc 3: Expand webhooks-events.md"
- Current file: `docs/reference/webhooks-events.md` (560 lines, sections 1-9)
- Webex webhook documentation for messaging resource payloads

**Critical rules:**
- Do NOT modify existing sections 1-3 or 7-9
- Insert new content as H3 subsections under existing H2s to avoid renumbering
- Use heading style `### 4b. Title` under existing `## 4.`

- [ ] **Step 1: Read the current webhooks-events.md**

Read the full file. Note exact section boundaries and heading styles so insertions are consistent.

- [ ] **Step 2: Add Section 4b — Messaging Resource Events**

Insert after existing Section 4 (Telephony Call Events), before Section 5. Cover 4 messaging webhook resources:

| Resource | Events | Key Data Fields |
|----------|--------|----------------|
| `messages` | created, deleted | id, roomId, roomType, personId, personEmail, created |
| `memberships` | created, updated, deleted | id, roomId, personId, personEmail, isModerator, created |
| `rooms` | created, updated | id, title, type, isLocked, creatorId, created |
| `attachmentActions` | created | id, type, messageId, inputs, personId, roomId, created |

Critical gotcha: `messages` webhook payload does NOT include message text for bots — must call GET /messages/{messageId}.

Mark all payload fields with `<!-- NEEDS VERIFICATION -->` since exact fields need live API confirmation.

- [ ] **Step 3: Add messaging filters to Section 5**

Add messaging filter examples to the existing filter table (currently only has telephony filters). Filters for: `messages` (roomId, personId, mentionedPeople), `memberships` (roomId, personId).

- [ ] **Step 4: Add Section 6b — Bot Webhook Pattern**

Insert after existing Section 6 (Webhook Setup), before Section 7. Document the standard bot interaction loop:
1. Create webhook for `messages` resource
2. User sends message → webhook fires (no text in payload for bots)
3. Bot calls GET /messages/{messageId} to get text
4. Bot processes and responds

Also add the card interaction loop (webhook for `attachmentActions` resource).

- [ ] **Step 5: Verify no existing content was modified**

Diff the file: only new content should appear. Sections 1-3 and 7-9 must be identical to the original.

- [ ] **Step 6: Commit**

```bash
git add docs/reference/webhooks-events.md
git commit -m "docs: expand webhooks-events with messaging resource events and bot patterns"
```

---

### Task 4: Skill — `messaging-spaces`

**Files:**
- Create: `.claude/skills/messaging-spaces/SKILL.md`

**Source material to read:**
- Spec sections: "Skill 1: messaging-spaces"
- Structural model: `.claude/skills/configure-features/SKILL.md` (558 lines, the most detailed existing skill)
- Reference doc: `docs/reference/messaging-spaces.md` (created in Task 1)

**Critical rules:**
- Match the established skill structure exactly: frontmatter → load references → verify auth → decision matrix → prerequisites → CLI catalog → deployment plan template → execute + verify → report → critical rules → compaction recovery
- Frontmatter must have: name, description, allowed-tools (Read, Grep, Glob, Bash), argument-hint

- [ ] **Step 1: Read the structural model**

Read `.claude/skills/configure-features/SKILL.md` in full. Note: frontmatter format, section ordering, how decision matrix works, how CLI commands are cataloged, deployment plan template format, critical rules format.

- [ ] **Step 2: Write `.claude/skills/messaging-spaces/SKILL.md`**

Follow the spec's 10-section structure:
1. Load References (`messaging-spaces.md`, `authentication.md`)
2. Verify Auth Token (detect token type, warn for bot-only ops)
3. Decision Matrix (6-row: space lifecycle, message management, membership, team, ECM, HDS)
4. Prerequisites per Operation (space exists, team exists, admin token for ECM/HDS)
5. CLI Command Catalog (organized by operation type)
6. Deployment Plan Template (adapted for messaging — space names and emails, not locations/extensions)
7. Execute + Verify (read back each resource after creation)
8. Report Results (template format)
9. Critical Rules (10 rules from spec)
10. Context Compaction Recovery

Scopes to document:
- Spaces/messages: `spark:rooms_read/write`, `spark:messages_read/write`
- Memberships: `spark:memberships_read/write`
- Teams: `spark:teams_read/write`, `spark:team_memberships_read/write`
- ECM: `spark-admin:room_linkedFolders_read/write`
- HDS: `spark-admin:hds_read`

- [ ] **Step 3: Verify skill loads the right reference docs**

Confirm `messaging-spaces.md` exists (from Task 1). Confirm `authentication.md` exists.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/messaging-spaces/SKILL.md
git commit -m "feat: add messaging-spaces skill — space lifecycle, teams, ECM, HDS"
```

---

### Task 5: Skill — `messaging-bots`

**Files:**
- Create: `.claude/skills/messaging-bots/SKILL.md`

**Source material to read:**
- Spec sections: "Skill 2: messaging-bots"
- Structural model: `.claude/skills/configure-features/SKILL.md`
- Reference docs: `docs/reference/messaging-bots.md` (Task 2), `docs/reference/webhooks-events.md` (Task 3)

**Critical rules:**
- Same structural pattern as messaging-spaces skill
- Cross-domain dispatch section: when objective involves calling + messaging, instruct to load the relevant calling skill too
- Bot scope limitations must be prominent

- [ ] **Step 1: Read the structural model**

Read `.claude/skills/configure-features/SKILL.md` (same as Task 4, but re-read if in a fresh agent context).

- [ ] **Step 2: Write `.claude/skills/messaging-bots/SKILL.md`**

Follow the spec's 10-section structure:
1. Load References (`messaging-bots.md`, `webhooks-events.md`, `authentication.md`)
2. Verify Auth Token (detect bot token, warn admin can't send messages)
3. Decision Matrix (5-row: send notification, card interaction, webhook setup, room tab, cross-domain)
4. Bot Setup Prerequisites (bot token, bot membership, webhook URL, target space)
5. Card Recipe Selection (guide to right recipe, customize, show wxcli command)
6. Webhook Setup for Bots (messages webhook + attachmentActions webhook, signpost to webhooks-events.md)
7. Cross-Domain Dispatch (load calling skill when both domains involved)
8. Execute + Verify (send test message, verify card render, check webhook)
9. Critical Rules (11 rules from spec)
10. Context Compaction Recovery

- [ ] **Step 3: Verify skill loads the right reference docs**

Confirm `messaging-bots.md` exists (from Task 2). Confirm `webhooks-events.md` exists and has sections 4b and 6b (from Task 3).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/messaging-bots/SKILL.md
git commit -m "feat: add messaging-bots skill — bot patterns, card recipes, cross-domain"
```

---

### Task 6: Agent Updates — `wxc-calling-builder.md`

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md` (616 lines, 8 additive changes)

**Source material to read:**
- Spec sections: "Agent Updates" (all 7 changes with exact line references)
- Current agent file: `.claude/agents/wxc-calling-builder.md`

**Critical rules:**
- ALL changes are additive — no existing content removed or modified
- Match existing formatting exactly (table alignment, heading levels, indentation)
- The agent currently has 12 skills in frontmatter and 12 rows in dispatch table

- [ ] **Step 1: Read the full agent file**

Read `.claude/agents/wxc-calling-builder.md` in full. Note exact current content at each change point.

- [ ] **Step 2: Change 1 — Frontmatter skills (line 10)**

Add `messaging-spaces, messaging-bots` to the end of the skills list.

Current:
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, device-platform, call-control, reporting, wxc-calling-debug, manage-identity, audit-compliance, manage-licensing
```

New:
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, device-platform, call-control, reporting, wxc-calling-debug, manage-identity, audit-compliance, manage-licensing, messaging-spaces, messaging-bots
```

- [ ] **Step 3: Change 2 — Interview Q1 objective recognition (after line ~112)**

Add 2 new domain bullets after the existing list:
```markdown
- **Messaging spaces**: creating/managing spaces, teams, memberships, sending messages, ECM folder linking, HDS monitoring
- **Messaging bots**: building bots, sending notifications, adaptive cards, interactive card flows, room tabs, cross-domain calling+messaging integrations
```

- [ ] **Step 4: Change 3 — Interview Q2 scope (after line ~121)**

Add messaging-specific scope paragraph after the existing scope bullets:
```markdown
For messaging requests, scope is different:
- If space-scoped: which space? Do you have the room ID?
- If team-scoped: which team? Creating new or modifying existing?
- If bot-scoped: is this for a bot or a user integration? Do you have a webhook callback URL?
- If org-wide: org-wide space audit needs admin token + compliance API
```

- [ ] **Step 5: Change 4 — Interview Q5 special requirements (after line ~163)**

Add messaging probes after the existing wxcadm probes (after line ~165):
```markdown
For messaging requests, also probe:
- **Token type**: "Bot token, user token, or admin token?" (explain differences if user is unsure)
- **Card interactions**: "Will users interact with cards (approve/reject/fill forms)?" → triggers card recipe + webhook setup in messaging-bots skill
- **Cross-domain**: "Does this involve both calling and messaging?" → load both domain skills
```

- [ ] **Step 6: Change 5 — Skill dispatch table (after line ~353)**

Add 2 rows to the dispatch table:
```markdown
| Spaces, teams, memberships, messages, ECM, HDS | `.claude/skills/messaging-spaces/SKILL.md` | Space lifecycle, team structure, membership management, token requirements |
| Bot development, notifications, adaptive cards, room tabs, cross-domain | `.claude/skills/messaging-bots/SKILL.md` | Bot patterns, card recipe catalog, webhook setup, cross-domain recipes |
```

- [ ] **Step 7: Change 6 — Reference doc loading (after line ~607, before Cross-Cutting section)**

Add new section (insert after "Apps, Data & Resources" entry, before the "Cross-Cutting" catch-all):
```markdown
### Messaging Spaces (spaces, teams, memberships, messages, ECM, HDS)
\```
docs/reference/messaging-spaces.md
docs/reference/authentication.md
\```

### Messaging Bots (bots, notifications, adaptive cards, cross-domain)
\```
docs/reference/messaging-bots.md
docs/reference/webhooks-events.md
docs/reference/authentication.md
\```
```

- [ ] **Step 8: Change 7 — First-time setup reference docs check (around line ~75)**

Add messaging reference docs to the existence check list alongside calling docs.

- [ ] **Step 9: Also update "Multiple Skills Per Plan" section (around line ~366)**

Add 2 lines to the domain-to-skill mapping list:
```markdown
- Steps managing spaces, teams, memberships, or messages → read messaging-spaces
- Steps building bots, sending cards, or setting up messaging webhooks → read messaging-bots
```

- [ ] **Step 10: Verify all 7 changes applied correctly**

Read the modified file. Verify:
- Frontmatter has 14 skills
- Dispatch table has 14 rows
- Interview Q1 has messaging domains
- Interview Q2 has messaging scope probes
- Interview Q5 has messaging special requirements
- Reference doc loading has messaging sections
- Multiple Skills Per Plan has messaging lines
- No existing content was removed or modified

- [ ] **Step 11: Commit**

```bash
git add .claude/agents/wxc-calling-builder.md
git commit -m "feat: expand builder agent with messaging interview, dispatch, and doc loading"
```

---

### Task 7: CLAUDE.md Updates

**Files:**
- Modify: `CLAUDE.md`

**Source material to read:**
- Spec sections: "CLAUDE.md Updates"
- Current file: `CLAUDE.md`

- [ ] **Step 1: Read relevant CLAUDE.md sections**

Read lines 21-65 (Agent & Skills table, Reference Docs table).

- [ ] **Step 2: Add skills to Agent & Skills table (after line 37)**

Add 2 rows:
```markdown
| `.claude/skills/messaging-spaces/` | Skill: manage spaces, teams, memberships, ECM, HDS |
| `.claude/skills/messaging-bots/` | Skill: build bots, adaptive cards, webhooks, cross-domain integrations |
```

- [ ] **Step 3: Add reference docs**

Add a new section after the existing reference doc sections (after wxcadm or admin sections):

```markdown
### Reference Docs — Messaging APIs

| Path | Purpose |
|------|---------|
| `docs/reference/messaging-spaces.md` | Spaces, messages, memberships, teams, ECM, HDS |
| `docs/reference/messaging-bots.md` | Bot development, adaptive cards, room tabs, cross-domain recipes |
```

- [ ] **Step 4: Update webhooks-events.md description (line 61)**

Change:
```
| `docs/reference/webhooks-events.md` | Telephony call webhooks, event types, payloads |
```
To:
```
| `docs/reference/webhooks-events.md` | Webhooks: CRUD, telephony + messaging event types, payloads |
```

- [ ] **Step 5: Update docs/later/ reference (line 154)**

Change:
```
| `docs/later/` | Parked: meetings, bots/webhooks (messaging commands now generated) |
```
To:
```
| `docs/later/` | Parked: meetings (messaging now has full reference docs and skills) |
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md file map with messaging reference docs and skills"
```

---

## Task Dependencies

```
Task 1 (messaging-spaces.md) ──┐
                                ├── Task 4 (messaging-spaces skill) ──┐
Task 2 (messaging-bots.md) ────┤                                     ├── Task 6 (agent updates) ── Task 7 (CLAUDE.md)
                                ├── Task 5 (messaging-bots skill) ────┘
Task 3 (webhooks expansion) ───┘
```

**Tasks 1, 2, 3 can run in parallel** — they have no dependencies on each other.
**Tasks 4 and 5 can run in parallel** — but each depends on its reference doc (Task 4 needs Task 1, Task 5 needs Tasks 2+3).
**Task 6 depends on Tasks 4+5** — the agent references skill files that must exist.
**Task 7 depends on Task 6** — CLAUDE.md should reflect the final state.

## Parallelization Strategy

**Wave 1 (3 agents):** Tasks 1, 2, 3 in parallel
**Wave 2 (2 agents):** Tasks 4, 5 in parallel (after Wave 1 completes)
**Wave 3 (1 agent):** Task 6 (after Wave 2 completes)
**Wave 4 (1 agent):** Task 7 (after Wave 3 completes)
