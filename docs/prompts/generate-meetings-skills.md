# Generate Skills: Meetings + Video Mesh

## What This Session Does

Write 2 CLI skills for the Webex Meetings and Video Mesh API surfaces.
The reference docs, OpenAPI specs, and CLI commands all exist already — this session creates
the guided workflow skills that make them usable through the wxc-calling-builder agent.

**Prerequisites:** The meetings reference docs must exist before running this prompt:
- `docs/reference/meetings-core.md`
- `docs/reference/meetings-content.md`
- `docs/reference/meetings-settings.md`
- `docs/reference/meetings-infrastructure.md`

If any are missing, run `docs/prompts/generate-meetings-reference-docs.md` first.

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

Meetings and Video Mesh have reference docs and CLI commands but NO skills yet.

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

### CLI Groups

**Meetings (17 groups, 139 commands):**

| CLI Group | Ops | Domain |
|-----------|-----|--------|
| `meetings` | 46 | Core CRUD, templates, controls, registrants, interpreters, breakouts, surveys |
| `meeting-participants` | 7 | Participant list, details, admit, SIP callout |
| `meeting-invitees` | 6 | Invitee CRUD, batch operations |
| `meeting-transcripts` | 7 | Transcript list, download, snippets, CRUD |
| `meeting-preferences` | 14 | Personal room, audio/video/scheduling, delegates, sites |
| `meeting-tracking-codes` | 7 | Tracking code CRUD, user codes |
| `video-mesh` | 30 | Clusters, nodes, availability, utilization, reachability, health monitoring |
| `meeting-captions` | 3 | Caption list, snippets, download |
| `meeting-polls` | 3 | Poll list, results, respondents |
| `meeting-summaries` | 3 | AI summary get/delete, compliance |
| `meeting-session-types` | 3 | Site/user session types |
| `meeting-chats` | 2 | In-meeting chat list, delete |
| `meeting-qa` | 2 | Q&A list, answer list |
| `meeting-reports` | 2 | Usage reports, attendee reports |
| `meeting-site` | 2 | Site-wide meeting settings |
| `meeting-slido` | 1 | Compliance events |
| `meeting-messages` | 1 | Delete meeting message |

## Guardrails

- **Read the pattern files first.** Do not write any skills until you've read at least
  one existing skill to understand the 8-step structure.
- **Verify reference docs exist.** Check that all 4 meetings reference docs are present
  before starting. If any are missing, stop and tell the user.
- **Use actual wxcli commands.** Run `wxcli <group> --help` and `wxcli <group> <command> --help`
  to verify command names and flags before including them in examples.
- **Break large writes into sections.** Skills are 400-700 lines.
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
3. Verify all 4 meetings reference docs exist:
   ```bash
   ls docs/reference/meetings-*.md
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

**Steps 4-8:** Follow the configure-features pattern. Prerequisites: auth token,
Video Mesh deployed, admin role with `spark-admin:video_mesh_read` scope.

### Step 4: Update CLAUDE.md

Add the 2 new skills to the file map table:

```
| `.claude/skills/manage-meetings/` | Skill: schedule, manage, query meetings + content |
| `.claude/skills/video-mesh/` | Skill: Video Mesh monitoring and threshold configuration |
```

### Step 5: Commit

Stage specific files:
```
.claude/skills/manage-meetings/SKILL.md
.claude/skills/video-mesh/SKILL.md
CLAUDE.md
```

Commit message: `feat(skills): add manage-meetings and video-mesh skills`

## Success Criteria

- [ ] 2 skills exist with correct YAML frontmatter (name, description, allowed-tools, argument-hint)
- [ ] Each skill follows the 8-step workflow pattern
- [ ] Each skill references its corresponding reference docs in Step 1
- [ ] Decision matrices cover all major operations
- [ ] wxcli command examples use actual CLI group and command names (verified via --help)
- [ ] Prerequisites include auth verification with `wxcli whoami`
- [ ] Deployment plans have explicit "SHOW BEFORE EXECUTING" gates
- [ ] CLAUDE.md file map updated
- [ ] Committed with specific file staging
