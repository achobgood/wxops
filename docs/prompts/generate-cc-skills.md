# Generate Skill: Contact Center

## What This Session Does

Write 1 CLI skill for the Webex Contact Center API surface (48 CLI groups, 431 commands).
The reference docs, OpenAPI spec, and CLI commands all exist already — this session creates
the guided workflow skill that makes them usable through the wxc-calling-builder agent.

**Prerequisites:** The CC reference docs must exist before running this prompt:
- `docs/reference/contact-center-core.md`
- `docs/reference/contact-center-routing.md`
- `docs/reference/contact-center-analytics.md`

If any are missing, run `docs/prompts/generate-cc-reference-docs.md` first.

## Context (Zero-Context Briefing)

This project is a Webex Calling CLI (`wxcli`) with guided agent assistance. The CLI has
165 command groups generated from 7 OpenAPI specs. Every API surface has **skills**
(`.claude/skills/*/SKILL.md`) — 8-step guided workflows that the builder agent uses to:

1. Load reference docs
2. Verify auth token and scopes
3. Identify the work (decision matrix)
4. Check prerequisites
5. Build and present a deployment plan (SHOW BEFORE EXECUTING)
6. Execute via wxcli commands
7. Verify results
8. Report results

Contact Center has reference docs and CLI commands but NO skill yet.

## Key Files

### Patterns (READ THESE FIRST)

| What | Path | Why |
|------|------|-----|
| Skill pattern (features) | `.claude/skills/configure-features/SKILL.md` | Best example (~610 lines): YAML frontmatter, 8-step workflow, decision matrix, prerequisite validation, wxcli examples |
| Skill pattern (reporting) | `.claude/skills/reporting/SKILL.md` | Query/analytics workflow (~578 lines) |
| Project instructions | `CLAUDE.md` | Full file map, CLI groups, known issues |

### Reference Docs (Skill references these in Step 1)

- `docs/reference/contact-center-core.md` — agents, queues, configuration
- `docs/reference/contact-center-routing.md` — dial plans, campaigns, flows
- `docs/reference/contact-center-analytics.md` — AI, journey, monitoring

### CLI Groups (48 groups, organized by domain)

**Agent Management (62 ops):**
`cc-agents` (11), `cc-agent-greetings` (13), `cc-agent-summaries` (2), `cc-agent-wellbeing` (5), `cc-user-profiles` (17), `cc-users` (14)

**Queue & Routing (73 ops):**
`cc-queue` (23), `cc-queues` (1), `cc-entry-point` (10), `cc-dial-plan` (9), `cc-dial-number` (12), `cc-callbacks` (5), `cc-ewt` (1), `cc-overrides` (9)

**Campaign & Contacts (36 ops):**
`cc-campaign` (3), `cc-contact-list` (5), `cc-contact-number` (8), `cc-dnc` (3), `cc-outdial-ani` (16), `cc-captures` (1)

**Configuration (126 ops):**
`cc-site` (10), `cc-business-hour` (9), `cc-holiday-list` (9), `cc-aux-code` (11), `cc-work-types` (9), `cc-desktop-layout` (9), `cc-desktop-profile` (10), `cc-multimedia-profile` (10), `cc-global-vars` (10), `cc-skill` (10), `cc-skill-profile` (9), `cc-team` (10)

**Flows & Automation (26 ops):**
`cc-flow` (4), `cc-data-sources` (7), `cc-audio-files` (7), `cc-resource-collection` (8)

**AI & Analytics (56 ops):**
`cc-ai-assistant` (1), `cc-ai-feature` (3), `cc-auto-csat` (8), `cc-summaries` (3), `cc-journey` (41)

**Monitoring & Events (56 ops):**
`cc-call-monitoring` (7), `cc-realtime` (1), `cc-subscriptions` (12), `cc-tasks` (24), `cc-notification` (1), `cc-search` (1), `cc-address-book` (19)

## Guardrails

- **Read the pattern files first.** Do not write the skill until you've read at least
  one existing skill to understand the 8-step structure.
- **Verify reference docs exist.** Check that all 3 CC reference docs are present.
  If any are missing, stop and tell the user.
- **Use actual wxcli commands.** Run `wxcli cc-<group> --help` and
  `wxcli cc-<group> <command> --help` to verify command names and flags before including
  them in examples.
- **Break large writes into sections.** This skill will be ~700-800 lines.
- **Stage specific files only.** Never `git add -A` or `git add .`.
- **Self-review after writing.** Verify YAML frontmatter parses correctly and all
  referenced CLI groups/commands exist.

## Step-by-Step Procedure

### Step 1: Read Patterns

1. Read `CLAUDE.md` — project structure, file map, known issues.
2. Read `.claude/skills/configure-features/SKILL.md` — the skill pattern. Note:
   - YAML frontmatter (name, description, allowed-tools, argument-hint)
   - 8-step workflow structure
   - Decision matrix format
   - Prerequisite validation with wxcli commands
   - Deployment plan presentation (SHOW BEFORE EXECUTING)
   - wxcli execution examples
   - Verification steps
3. Verify all 3 CC reference docs exist:
   ```bash
   ls docs/reference/contact-center-*.md
   ```

### Step 2: Write Contact Center Skill

#### `.claude/skills/contact-center/SKILL.md` (~700-800 lines)

```yaml
name: contact-center
description: |
  Provision and manage Webex Contact Center resources using wxcli CLI commands:
  agents, queues, entry points, teams, skills, flows, campaigns, dial plans,
  desktop profiles, and monitoring. Guides from prerequisites through execution
  and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [cc-operation]
```

**Step 1 — Load References:** `contact-center-core.md`, `contact-center-routing.md`,
`contact-center-analytics.md`

**Step 2 — Verify Auth:** `wxcli whoami`. Contact Center requires admin token with
appropriate CC admin role.

**Step 3 — Decision Matrix:**

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Manage agents | Create/update/delete agents, state changes | `cc-agents`, `cc-users` |
| Configure agent greetings | Upload, assign, manage greeting files | `cc-agent-greetings` |
| Agent wellbeing | Configure agent wellbeing settings | `cc-agent-wellbeing` |
| Configure queues | Create/update queues, assign agents | `cc-queue` |
| Set up entry points | Create/manage entry points | `cc-entry-point` |
| Create teams | Team CRUD, assign agents | `cc-team` |
| Manage skills | Skill definitions and profiles | `cc-skill`, `cc-skill-profile` |
| Configure dial plans | Dial plan CRUD, number management | `cc-dial-plan`, `cc-dial-number` |
| Set up campaigns | Campaign management, contact lists | `cc-campaign`, `cc-contact-list` |
| Manage outdial ANI | Outdial ANI configuration | `cc-outdial-ani` |
| Configure desktops | Desktop layouts and profiles | `cc-desktop-layout`, `cc-desktop-profile` |
| Manage flows | Flow CRUD | `cc-flow` |
| Configure business hours | Business hours and holidays | `cc-business-hour`, `cc-holiday-list` |
| Manage audio files | Upload and manage audio | `cc-audio-files` |
| Set up aux codes | Auxiliary codes and work types | `cc-aux-code`, `cc-work-types` |
| Configure multimedia | Multimedia profiles | `cc-multimedia-profile` |
| Manage global variables | Global variable CRUD | `cc-global-vars` |
| Monitor calls | Call monitoring, realtime stats | `cc-call-monitoring`, `cc-realtime` |
| Manage subscriptions | Event subscriptions | `cc-subscriptions` |
| View tasks | Task management | `cc-tasks` |
| Journey analytics | Customer journey, identification, insights | `cc-journey` |
| AI features | AI assistant, auto CSAT, summaries | `cc-ai-assistant`, `cc-auto-csat`, `cc-summaries` |
| Not Contact Center? | For Calling features, use `configure-features` skill. For meetings, use `manage-meetings` skill. | — |

**Step 4 — Prerequisites:**
- Auth token verified (`wxcli whoami`)
- Contact Center license provisioned
- CC admin role assigned
- At least one CC site configured (`wxcli cc-site list -o json`)
- For queue operations: entry points and teams must exist first
- For campaign operations: contact lists and outdial ANI must exist first

**Steps 5-8:** Follow the configure-features pattern — deployment plan (SHOW BEFORE
EXECUTING), execution with wxcli examples covering the most common workflows (create agent,
create queue with agents, set up entry point → queue routing, create team), verification
via list commands, results report.

### Step 3: Update CLAUDE.md

Add the new skill to the file map table:

```
| `.claude/skills/contact-center/` | Skill: CC provisioning (agents, queues, flows, campaigns) |
```

### Step 4: Commit

Stage specific files:
```
.claude/skills/contact-center/SKILL.md
CLAUDE.md
```

Commit message: `feat(skills): add contact-center skill`

## Success Criteria

- [ ] Skill exists with correct YAML frontmatter (name, description, allowed-tools, argument-hint)
- [ ] Follows the 8-step workflow pattern
- [ ] References all 3 CC reference docs in Step 1
- [ ] Decision matrix covers all 7 domain areas (agent, queue, campaign, config, flows, AI, monitoring)
- [ ] wxcli command examples use actual CLI group and command names (verified via --help)
- [ ] Prerequisites include auth verification with `wxcli whoami`
- [ ] Deployment plan has explicit "SHOW BEFORE EXECUTING" gate
- [ ] CLAUDE.md file map updated
- [ ] Committed with specific file staging
