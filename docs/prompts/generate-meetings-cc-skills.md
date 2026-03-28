# Generate Skills: Meetings, Video Mesh, Contact Center

## What This Session Does

Write 3 CLI skills for the Webex Meetings, Video Mesh, and Contact Center API surfaces.
The reference docs, OpenAPI specs, and CLI commands all exist already — this session creates
the guided workflow skills that make them usable through the wxc-calling-builder agent.

**Prerequisites:** The reference docs must exist before running this prompt:
- `docs/reference/meetings-core.md`
- `docs/reference/meetings-content.md`
- `docs/reference/meetings-settings.md`
- `docs/reference/meetings-infrastructure.md`
- `docs/reference/contact-center-core.md`
- `docs/reference/contact-center-routing.md`
- `docs/reference/contact-center-analytics.md`

If any are missing, run these prompts first:
- `docs/prompts/generate-meetings-reference-docs.md`
- `docs/prompts/generate-cc-reference-docs.md`

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

Meetings, Video Mesh, and Contact Center have reference docs and CLI commands but NO skills.

## Key Files

### Patterns (READ THESE FIRST)

| What | Path | Why |
|------|------|-----|
| Skill pattern (features) | `.claude/skills/configure-features/SKILL.md` | Best example (~610 lines): YAML frontmatter, 8-step workflow, decision matrix, prerequisite validation, wxcli examples |
| Skill pattern (reporting) | `.claude/skills/reporting/SKILL.md` | Query/analytics workflow (~578 lines) |
| Skill pattern (messaging) | `.claude/skills/messaging-spaces/SKILL.md` | Simpler skill (~515 lines) |
| Project instructions | `CLAUDE.md` | Full file map, CLI groups, known issues |

### Reference Docs (Skills reference these in Step 1)

| Skill | Reference Docs |
|-------|---------------|
| manage-meetings | `meetings-core.md`, `meetings-content.md`, `meetings-settings.md` |
| video-mesh | `meetings-infrastructure.md` |
| contact-center | `contact-center-core.md`, `contact-center-routing.md`, `contact-center-analytics.md` |

### CLI Groups

**Meetings (17 groups, 139 commands):**
`meetings` (46), `meeting-participants` (7), `meeting-invitees` (6), `meeting-transcripts` (7),
`meeting-preferences` (14), `meeting-tracking-codes` (7), `video-mesh` (30),
`meeting-captions` (3), `meeting-polls` (3), `meeting-summaries` (3), `meeting-session-types` (3),
`meeting-chats` (2), `meeting-qa` (2), `meeting-reports` (2), `meeting-site` (2),
`meeting-slido` (1), `meeting-messages` (1)

**Contact Center (48 groups, 431 commands):**
`cc-agents` (11), `cc-agent-greetings` (13), `cc-agent-summaries` (2), `cc-agent-wellbeing` (5),
`cc-user-profiles` (17), `cc-users` (14), `cc-queue` (23), `cc-queues` (1),
`cc-entry-point` (10), `cc-dial-plan` (9), `cc-dial-number` (12), `cc-callbacks` (5),
`cc-ewt` (1), `cc-overrides` (9), `cc-campaign` (3), `cc-contact-list` (5),
`cc-contact-number` (8), `cc-dnc` (3), `cc-outdial-ani` (16), `cc-captures` (1),
`cc-site` (10), `cc-business-hour` (9), `cc-holiday-list` (9), `cc-aux-code` (11),
`cc-work-types` (9), `cc-desktop-layout` (9), `cc-desktop-profile` (10),
`cc-multimedia-profile` (10), `cc-global-vars` (10), `cc-skill` (10),
`cc-skill-profile` (9), `cc-team` (10), `cc-flow` (4), `cc-data-sources` (7),
`cc-audio-files` (7), `cc-resource-collection` (8), `cc-ai-assistant` (1),
`cc-ai-feature` (3), `cc-auto-csat` (8), `cc-summaries` (3), `cc-journey` (41),
`cc-call-monitoring` (7), `cc-realtime` (1), `cc-subscriptions` (12), `cc-tasks` (24),
`cc-notification` (1), `cc-search` (1), `cc-address-book` (19)

## Guardrails

- **Read the pattern files first.** Do not write any skills until you've read at least
  one existing skill to understand the 8-step structure.
- **Verify reference docs exist.** Check that all 7 reference docs are present before
  starting. If any are missing, stop and tell the user.
- **Use actual wxcli commands.** Run `wxcli <group> --help` and `wxcli <group> <command> --help`
  to verify command names and flags before including them in examples.
- **Break large writes into sections.** Skills are 400-800 lines.
- **Stage specific files only.** Never `git add -A` or `git add .`.
- **Self-review after each skill.** Verify YAML frontmatter parses correctly and all
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
3. Verify all 7 reference docs exist:
   ```bash
   ls docs/reference/meetings-*.md docs/reference/contact-center-*.md
   ```

### Step 2: Write Meetings Skill

#### `.claude/skills/manage-meetings/SKILL.md` (~600-700 lines)

```yaml
name: manage-meetings
description: |
  Schedule, manage, and query Webex meetings, registrants, interpreters,
  breakout sessions, transcripts, recordings, and polls using wxcli CLI commands.
  Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [meeting-operation]
```

**Step 1 — Load References:** `meetings-core.md`, `meetings-content.md`, `meetings-settings.md`

**Step 2 — Verify Auth:** `wxcli whoami`. Scopes: `meeting:admin_schedule_write`,
`meeting:admin_preferences_write`, `meeting:admin_participants_read`, etc.

**Step 3 — Decision Matrix:**

| Need | Operation | CLI Group(s) |
|------|-----------|-------------|
| Schedule a meeting | Create/update/delete meetings | `meetings` |
| Manage registrants | Register, approve, reject, batch ops | `meetings` |
| Set up interpreters | Add/manage simultaneous interpretation | `meetings` |
| Configure breakout sessions | Create/update session assignments | `meetings` |
| Pull transcripts | List, download, manage snippets | `meeting-transcripts` |
| Manage captions | List captions, download snippets | `meeting-captions` |
| Configure preferences | Personal room, audio/video, scheduling, delegates | `meeting-preferences` |
| Manage tracking codes | CRUD tracking codes, assign to users | `meeting-tracking-codes` |
| Query meeting reports | Usage reports, attendee reports | `meeting-reports` |
| Review polls/Q&A | List polls, results, Q&A answers | `meeting-polls`, `meeting-qa` |
| Get AI summaries | Retrieve/delete meeting summaries | `meeting-summaries` |
| Configure site settings | Security, telephony, scheduling defaults | `meeting-site` |
| Manage participants | List, admit, SIP callout | `meeting-participants` |
| Manage invitees | Invite, batch invite, update, remove | `meeting-invitees` |
| Not a meeting operation? | For Video Mesh, use `video-mesh` skill. For call features, use `configure-features` skill. | — |

**Steps 4-8:** Follow the configure-features pattern — prerequisites (auth, site, licenses),
deployment plan, execution with wxcli examples, verification, results report.

### Step 3: Write Video Mesh Skill

#### `.claude/skills/video-mesh/SKILL.md` (~400-500 lines)

```yaml
name: video-mesh
description: |
  Monitor and configure Webex Video Mesh clusters, nodes, availability,
  utilization, reachability, and event thresholds using wxcli CLI commands.
  Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [mesh-operation]
```

**Step 1 — Load References:** `meetings-infrastructure.md`

**Step 3 — Decision Matrix:**

| Need | Operation | Commands |
|------|-----------|----------|
| Check cluster health | List clusters, get details | `video-mesh list`, `video-mesh show` |
| Monitor availability | Cluster/node availability | `video-mesh list-availability-clusters` |
| Run reachability tests | Test cluster/node reachability | `video-mesh list-reachability-test` |
| View utilization | Cluster utilization stats | `video-mesh list-utilization-video-mesh` |
| Check media health | Media health monitoring results | `video-mesh list-media-health-monitor-test` |
| Trigger on-demand tests | Run tests on cluster/node | `video-mesh create`, `video-mesh create-clusters` |
| Configure thresholds | Event threshold configuration | `video-mesh list-event-thresholds`, `video-mesh update` |
| View overflow stats | Cloud overflow details | `video-mesh list-cloud-overflow` |
| View call redirects | Redirect details per cluster | `video-mesh list-call-redirects-video-mesh` |
| Not Video Mesh? | For meetings, use `manage-meetings` skill | — |

### Step 4: Write Contact Center Skill

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
| Not Contact Center? | For Calling features, use `configure-features` skill | — |

**Steps 4-8:** Follow the configure-features pattern. Prerequisites: auth token,
Contact Center license, CC admin role, sites configured (`cc-site list`).

### Step 5: Update CLAUDE.md

Add the 3 new skills to the file map table:

```
| `.claude/skills/manage-meetings/` | Skill: schedule, manage, query meetings + content |
| `.claude/skills/video-mesh/` | Skill: Video Mesh monitoring and threshold configuration |
| `.claude/skills/contact-center/` | Skill: CC provisioning (agents, queues, flows, campaigns) |
```

### Step 6: Commit

Stage specific files:
```
.claude/skills/manage-meetings/SKILL.md
.claude/skills/video-mesh/SKILL.md
.claude/skills/contact-center/SKILL.md
CLAUDE.md
```

Commit message: `feat(skills): add manage-meetings, video-mesh, and contact-center skills`

## Success Criteria

- [ ] 3 skills exist with correct YAML frontmatter (name, description, allowed-tools, argument-hint)
- [ ] Each skill follows the 8-step workflow pattern
- [ ] Each skill references its corresponding reference docs in Step 1
- [ ] Decision matrices cover all major operations for each API surface
- [ ] wxcli command examples use actual CLI group and command names (verified via --help)
- [ ] Prerequisites include auth verification with `wxcli whoami`
- [ ] Deployment plans have explicit "SHOW BEFORE EXECUTING" gates
- [ ] CLAUDE.md file map updated
- [ ] Committed with specific file staging
