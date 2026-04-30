# Webex Calling Playbook

Build and configure Webex Calling, admin, device, and messaging APIs programmatically with guided Claude Code assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → raw HTTP (fallback).
The wxcli CLI has 173 command groups covering calling, admin, device, messaging, meetings, and contact center APIs. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

## Mandatory Grounding Rule

**Never answer any question about Webex Calling from training data alone.**

For every question — capability, configuration, behavior, limits, or anything else — you MUST either:
1. Invoke the relevant skill (`configure-features`, `customer-assist`, `contact-center`, etc.), OR
2. Read the relevant reference doc in `docs/reference/`

The reference docs and skills are the authoritative source for this project. Training data about Cisco/Webex products is unreliable — product tiers get conflated, feature names change, and capabilities vary by license. If the answer isn't in the docs or skills, say so explicitly rather than filling the gap from training data.

---

## Quick Start

You MUST use `/agents` and select **wxc-calling-builder**. This is the primary interface for all operations.
The agent walks you through authentication, interviews you about what you want to build, designs
a deployment plan, executes via `wxcli` commands, and verifies the results. **Do not run `wxcli`
commands directly** — the agent handles the full workflow.

**To build or configure Webex Calling:** `/agents` → wxc-calling-builder → describe what you want.

**To migrate from CUCM:** `/agents` → wxc-calling-builder → "Run a CUCM migration" and provide
the CUCM host/credentials. The agent runs the full pipeline: discover → normalize → map → analyze
→ resolve addresses → review decisions → plan → execute → verify. See the CUCM migration section
below for what the pipeline does. Pipeline and tool details in `.claude/rules/cucm-migration.md` (path-scoped). 
See `src/wxcli/migration/CLAUDE.md` for the full file map and architecture.

**To debug a failing configuration:** Use `/wxc-calling-debug` (this one is a skill, invoked directly).

**To query live org state:** Use `/query-live` for read-only questions about the current environment ("who has call forwarding enabled?", "which locations have no users?", "show me all hunt groups").

**To audit org health:** `/agents` → wxc-calling-builder → "audit my org". The `org-health` skill orchestrates collection, analysis, and HTML report generation.

### Agent Invocation Pattern

wxc-calling-builder is a **phase-per-invocation** agent. Each major phase runs as a
fresh agent invocation — do NOT resume agents via `SendMessage` for multi-phase workflows.

**Invocation rules:**
- Always spawn a fresh agent for each phase
- Pass current state in the prompt: project name, current pipeline stage, key context
- The agent reads state from disk on startup and validates against the prompt
- For single-phase work (quick config, one-off query), one invocation is sufficient

**What constitutes a phase boundary:** Any point where the agent writes state to disk and the next step is conceptually independent. Typical boundaries: auth complete → provisioning starts, provisioning complete → feature configuration starts, discovery complete → analysis starts. If the next step needs results from the current step but could be described to a fresh agent in one sentence, it's a new phase.

**When SendMessage IS appropriate:** Simple follow-ups within a single phase — "also add voicemail to that user", "change the extension to 2001 instead". The agent still has the right context. Do NOT use SendMessage across phase boundaries or after long silences; the agent may have lost context or died mid-tool-call.

**Prompt template for fresh phase invocations:**
```
"Project: [name]. Current state: [stage, e.g. 'provisioning complete, 3 users + 2 locations created'].
Next: [what to do]. Key context: [anything the agent needs that isn't on disk]."
```

**CUCM migration invocation example:** See `.claude/rules/cucm-migration.md` for the phase-by-phase spawning pattern.

### Agent Model Selection

The builder agent base context is ~40k tokens. Choose the model to match the task complexity:

| Task type | Model | Why |
|-----------|-------|-----|
| Cleanup, teardown, batch delete | `haiku` | All logic is in `wxcli cleanup run` — agent just picks flags and runs it |
| Simple read-only checks (list users, verify resource) | `sonnet` with minimal prompt (1-2 sentences) | Base context load is unavoidable; keep prompt short to minimize output tokens |
| Standard provisioning, feature config, single-phase builds | `sonnet` (default) | Good balance of capability and cost |
| Multi-phase CUCM migration, complex routing, architectural decisions | `opus` | Needs reasoning about dependencies, cross-feature interactions |
| Batch multiple simple checks into one agent call | `sonnet` | One agent with 3 checks < three separate agent spawns |

**Anti-patterns:**
- Never use Haiku for implementation subagents — it misses details and produces rework
- Don't spawn a full builder agent just to run one `wxcli` read command — keep the prompt minimal
- Don't spawn separate agents for each simple check — batch them

### Inline IDs in Commands

Always inline resource IDs directly as arguments. Never use multi-line shell variable assignments before wxcli commands.

```bash
# WRONG — multi-line breaks permission prefix matching
HQ="Y2lz..."
wxcli dect-devices show "$HQ"

# RIGHT — inline the ID
wxcli dect-devices show "Y2lz..."
```

**Why:** Permission rules use prefix matching. A variable assignment line before `wxcli` means the command string doesn't start with `wxcli`, so it won't match `Bash(wxcli:*)` permission patterns, triggering unnecessary prompts.

### Agent Orchestration — Long-Running Work & Silence Detection

Added 2026-04-15 after an org-cleanup subagent died mid-Phase-2 when its Python polling loop exceeded Bash's 10-min timeout. Parent sent two `SendMessage` pings that received no response because the subagent's tool call was still in flight and then terminated; the agent loop never got a chance to resume and handle the messages. Root cause recovery required spawning a fresh agent to verify org state and finish the job. This protocol **complements** — does not replace — the phase-per-invocation rule above.

#### For subagents running long-running work (>2 min expected)

1. **Never wrap long-running polling in a single Bash call.** The Bash tool has a ~10-min hard timeout; if the tool call runs longer, stdout buffering hides progress and the subagent dies silently when the kernel kills the process. The agent loop never resumes to produce a final message, so the parent sees silence.
2. **Split into discrete tool calls.** One Bash call per polling round (not 20 rounds in one call). Between rounds, the agent loop can emit progress messages.
3. **Use `run_in_background: true` on Bash** for genuinely long-running commands (e.g., `wxcli cucm execute` that runs >5 min); monitor the task output file (but do not `tail`/Read large JSONL transcripts — use targeted line ranges only).
4. **Emit progress explicitly.** At minimum every 60s, the subagent should produce a visible message (text output, not a tool call) so observers see aliveness.

#### For parent agents when a subagent goes silent

1. **Wait up to 5 min** of silence before investigating — normal operations can have gaps.
2. **After 5 min silence, read the subagent's transcript directly** at `~/.claude/projects/<project-hash>/subagents/agent-<id>.jsonl`. Check:
   - Last entry type: `tool_use` with no paired `tool_result` → subagent is blocked in a tool call (likely Bash timeout pending).
   - Last entry is `assistant` text → subagent thinking, give it more time.
3. **Do NOT use `SendMessage` to ping a subagent blocked in a tool call.** `SendMessage` cannot interrupt an in-flight tool call; the message queues to a dead mailbox.
4. **If the subagent is dead** (transcript ends on unpaired `tool_use`), spawn a fresh agent to continue the work from current state. Do not wait longer.
5. **Check external state** via a fresh diagnostic agent (e.g., "run `wxcli locations list`") rather than trusting the dead subagent's last self-reported state.

## File Map

### Agent & Skills

| Path | Purpose |
|------|---------|
| `.claude/agents/wxc-calling-builder.md` | Main builder agent — drives the full workflow |
| `.claude/agents/migration-advisor.md` | Opus-powered CCIE-level migration advisor — architectural reasoning + decision review |
| `.claude/skills/provision-calling/` | Skill: provision users, locations, licenses |
| `.claude/skills/teardown/` | Skill: dependency-safe teardown, `wxcli cleanup`, manual deletion procedure |
| `.claude/skills/configure-features/` | Skill: set up call features (AA, CQ, HG, etc.; Customer Assist → see customer-assist skill) |
| `.claude/skills/customer-assist/`      | Skill: configure Customer Assist (screen pop, wrap-up, recording, supervisors) |
| `.claude/skills/manage-call-settings/` | Skill: configure person/workspace call settings |
| `.claude/skills/configure-routing/` | Skill: configure routing (trunks, dial plans, PSTN) |
| `.claude/skills/manage-devices/` | Skill: manage devices (phones, DECT, workspaces) |
| `.claude/skills/device-platform/` | Skill: manage PhoneOS/RoomOS device configs, workspace personalization, xAPI; 9800-series phones (9811/9821/9841/9851/9861/9871) use PhoneOS (not RoomOS) |
| `.claude/skills/call-control/` | Skill: real-time call control, webhooks, XSI |
| `.claude/skills/reporting/` | Skill: CDR query engine (75 recipes + composition guide), report templates, recordings |
| `.claude/skills/reporting-cc/` | Skill: Contact Center analytics (queue stats, agent stats, EWT, summaries) |
| `.claude/skills/reporting-meetings/` | Skill: meetings quality, workspace metrics, historical analytics, live monitoring |
| `.claude/skills/wxc-calling-debug/` | Skill: debug failing configurations |
| `.claude/skills/manage-identity/` | Skill: SCIM sync, directory, groups, contacts, domains |
| `.claude/skills/audit-compliance/` | Skill: audit events, security, compliance, authorizations |
| `.claude/skills/manage-licensing/` | Skill: license audit, assignment, reclamation |
| `.claude/skills/messaging-spaces/` | Skill: manage spaces, teams, memberships, ECM, HDS |
| `.claude/skills/messaging-bots/` | Skill: build bots, adaptive cards, webhooks, cross-domain integrations |
| `.claude/skills/manage-meetings/` | Skill: schedule, manage, query meetings + content |
| `.claude/skills/video-mesh/` | Skill: Video Mesh monitoring and threshold configuration |
| `.claude/skills/contact-center/` | Skill: CC provisioning (agents, queues, flows, campaigns) |
| `.claude/skills/org-health/` | Skill: org health assessment — collect, analyze 18 checks, HTML report |
| `.claude/skills/cucm-migrate/` | Skill: execute CUCM-to-Webex migration from exported deployment plan |
| `.claude/skills/query-live/` | Skill: read-only natural language queries against live Webex Calling state |

### Skill Disambiguation

When multiple skills could match, use this lookup:

| If the user wants to... | Use this skill | NOT this one |
|--------------------------|---------------|-------------|
| Configure Customer Assist (screen pop, wrap-up, supervisors) | `customer-assist` | `configure-features` (CX queues are a separate skill) |
| Create a call queue, hunt group, or auto attendant | `configure-features` | `customer-assist` (only for CX Essentials features) |
| Set person call forwarding, DND, voicemail, caller ID | `manage-call-settings` | `configure-features` (person settings ≠ call features) |
| Configure voicemail groups (shared location mailbox) | `configure-features` | `manage-call-settings` (voicemail groups are a location feature) |
| Provision MPP phones, DECT, activation codes | `manage-devices` | `device-platform` (that's for config keys, not provisioning) |
| Set 9800-series PhoneOS config keys, xAPI commands | `device-platform` | `manage-devices` (that's for provisioning, not config) |
| Query Webex Calling CDR, call quality, queue stats | `reporting` | `reporting-cc` (that's Contact Center only) |
| Query Contact Center agent/queue analytics | `reporting-cc` | `reporting` (that's Calling only) |
| Query meeting quality, workspace utilization | `reporting-meetings` | `reporting` (different API domain) |
| Delete/clean up resources | `teardown` | `provision-calling` (that's for creation) |
| Provision users, locations, licenses | `provision-calling` | `teardown` (that's for deletion) |

### Reference Docs — wxc_sdk (Official Cisco SDK)

| Path | Purpose |
|------|---------|
| `docs/reference/authentication.md` | Auth methods, tokens, scopes, OAuth flows |
| `docs/reference/provisioning.md` | People, licenses, locations, org setup |
| `docs/reference/wxc-sdk-patterns.md` | wxc_sdk setup, auth, async patterns, common recipes |
| `docs/reference/call-features-major.md` | Auto attendants, call queues, hunt groups |
| `docs/reference/call-features-additional.md` | Paging, call park, pickup, voicemail groups, Customer Assist |
| `docs/reference/person-call-settings-handling.md` | Call forwarding, DND, call waiting, sim/sequential ring |
| `docs/reference/person-call-settings-media.md` | Voicemail, caller ID, privacy, barge, recording, intercept |
| `docs/reference/person-call-settings-permissions.md` | Incoming/outgoing permissions, feature access, executive/assistant |
| `docs/reference/person-call-settings-behavior.md` | Calling behavior, app services, hoteling, receptionist, numbers, ECBN |
| `docs/reference/self-service-call-settings.md` | User self-service call settings (/people/me/ endpoints) |
| `docs/reference/location-calling-core.md` | Location enablement, internal dialing, voicemail policies, voice portal |
| `docs/reference/location-calling-media.md` | Announcements, playlists, schedules, access codes |
| `docs/reference/location-recording-advanced.md` | Call recording, caller reputation, conference, supervisor, operating modes |
| `docs/reference/call-routing.md` | Dial plans, trunks, route groups, route lists, translation patterns, PSTN |
| `docs/reference/devices-core.md` | Device CRUD, activation, device configurations, telephony devices |
| `docs/reference/devices-dect.md` | DECT networks, base stations, handsets, hotdesking |
| `docs/reference/devices-workspaces.md` | Workspaces, workspace settings, workspace locations |
| `docs/reference/devices-platform.md` | RoomOS device configurations, workspace personalization, xAPI |
| `docs/reference/call-control.md` | Real-time call control (dial, answer, hold, transfer, park, recording) |
| `docs/reference/webhooks-events.md` | Webhooks: CRUD, telephony + messaging event types, payloads |
| `docs/reference/reporting-analytics.md` | CDR, report templates, call quality, queue/AA stats |
| `docs/reference/virtual-lines.md` | Virtual line/extension settings, voicemail, recording |
| `docs/reference/emergency-services.md` | E911, emergency addresses, ECBN |

### Reference Docs — Admin APIs (Core Object Model)

| Path | Purpose |
|------|---------|
| `docs/reference/wxcadm-core.md` | Webex/Org classes, object model, auth patterns |
| `docs/reference/wxcadm-person.md` | Person class (34 call settings methods, 10 unique capabilities) |
| `docs/reference/wxcadm-locations.md` | Location management, features, schedules |
| `docs/reference/wxcadm-features.md` | AA, CQ, HG, pickup, announcements, recording |
| `docs/reference/wxcadm-devices-workspaces.md` | Devices, DECT, workspaces, virtual lines, numbers |
| `docs/reference/wxcadm-xsi-realtime.md` | XSI events, real-time call monitoring |
| `docs/reference/wxcadm-routing.md` | Call routing, PSTN, CDR, reports, jobs, webhooks |
| `docs/reference/wxcadm-advanced.md` | RedSky E911, Meraki integration, CP-API, wholesale, bifrost |

### Reference Docs — Admin & Identity APIs

| Path | Purpose |
|------|---------|
| `docs/reference/admin-org-management.md` | Organizations, org settings, contacts, roles, domains |
| `docs/reference/admin-identity-scim.md` | SCIM users/groups, schemas, bulk ops, identity org, people, groups |
| `docs/reference/admin-licensing.md` | License inventory, assignment, usage auditing |
| `docs/reference/admin-audit-security.md` | Admin audit events, security audit, compliance events |
| `docs/reference/admin-hybrid.md` | Hybrid clusters/connectors, analytics, meeting quality |
| `docs/reference/admin-partner.md` | Partner admins, tags, partner reports |
| `docs/reference/admin-apps-data.md` | Service apps, authorizations, activation emails, data sources, recordings, resource groups |

### Reference Docs — Messaging APIs

| Path | Purpose |
|------|---------|
| `docs/reference/messaging-spaces.md` | Spaces, messages, memberships, teams, ECM, HDS |
| `docs/reference/messaging-bots.md` | Bot development, adaptive cards, room tabs, cross-domain recipes |

### Reference Docs — Meetings APIs

| Path | Purpose |
|------|---------|
| `docs/reference/meetings-core.md` | Meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys |
| `docs/reference/meetings-content.md` | Transcripts, captions, chats, summaries, meeting messages |
| `docs/reference/meetings-settings.md` | Preferences, session types, tracking codes, site settings, polls, Q&A, reports |
| `docs/reference/meetings-infrastructure.md` | Video Mesh (clusters, nodes, health, utilization), participants, invitees |

### Reference Docs — Contact Center APIs

| Path | Purpose |
|------|---------|
| `docs/reference/contact-center-core.md` | CC agents, queues, entry points, teams, skills, desktop, configuration |
| `docs/reference/contact-center-routing.md` | CC dial plans, campaigns, flows, audio, contacts, outdial |
| `docs/reference/contact-center-analytics.md` | CC AI, monitoring, subscriptions, tasks, search |
| `docs/reference/contact-center-journey.md` | JDS: workspaces, persons, identity, profile views, events, WXCC subscription |

### Migration (KB, Runbooks, Tool, Spec Template)

Detailed migration context lives in `.claude/rules/cucm-migration.md` (auto-loaded when touching migration paths). Contains: knowledge base file map (8 KB docs for the Opus advisor), operator runbooks (3 docs for pipeline walkthrough, decision guide, tuning), migration tool pipeline commands, advisory workflow, report/diff/notice generation commands, spec template requirements, and the phase-by-phase agent invocation example.

**Read the rule when:** handling any CUCM migration question, running `/cucm-migrate`, or working with the migration advisor agent — even if not editing migration source files directly.

### CLI (wxcli) — Primary Execution Layer

| Path | Purpose |
|------|---------|
| `src/wxcli/main.py` | CLI entry point — 173 command groups |
| `src/wxcli/commands/*.py` | All command implementations (raw HTTP pattern) |
| `wxcli --help` | Shows all command groups |
| `wxcli <group> --help` | Shows commands within a group |
| `wxcli <group> <command> --help` | Shows options for a command |
| `specs/webex-cloud-calling.json` | OpenAPI 3.0 spec — calling APIs |
| `specs/webex-admin.json` | OpenAPI 3.0 spec — admin/org management APIs |
| `specs/webex-device.json` | OpenAPI 3.0 spec — device management APIs |
| `specs/webex-messaging.json` | OpenAPI 3.0 spec — messaging/rooms/teams APIs |
| `specs/webex-meetings.json` | OpenAPI 3.0 spec — meetings/video mesh/transcripts APIs |
| `specs/webex-contact-center.json` | OpenAPI 3.0 spec — contact center APIs (48 groups, 383 commands) |
| `src/wxcli/commands/cleanup.py` | Batch cleanup: inventory + parallel layered deletion |
| `src/wxcli/commands/converged_recordings_export.py` | Hand-written download/export for converged recordings (registered into generated group) |

### Org Health Assessment

Detailed context in `.claude/rules/org-health.md` (auto-loaded when touching org health paths). Contains: file map (models, collector, checks, analyze, report), run instructions, and check category breakdown (Security Posture, Routing Hygiene, Feature Utilization, Device Health). **76 tests passing.**

**Read the rule when:** running an org health audit, modifying checks, or working on the report generator.

### CUCM→Webex Migration Tool (All 11 phases complete)

The migration tool is at `src/wxcli/migration/` and wired into the CLI as `wxcli cucm <command>`. **2778 tests passing.** See `src/wxcli/migration/CLAUDE.md` for the full file map, architecture, and pipeline commands. Pipeline workflow, report generation, and advisory details are in `.claude/rules/cucm-migration.md`.

## CLI Status & Known Issues

**173 command groups covering calling, admin, device, messaging, meetings, and contact center APIs.** Nearly all generated from 9 OpenAPI 3.0 specs via `tools/generate_commands.py`. The `converged-recordings` group combines generated CRUD commands with hand-written `download` and `export` commands (`converged_recordings_export.py`).

### Partner Multi-Org Support

wxcli supports partner/VAR/MSP admins who manage multiple customer orgs with a single partner token.

- **`wxcli configure`** — detects multi-org tokens automatically and prompts for org selection. The selected `orgId` is saved to the config file.
- **`wxcli switch-org`** — change the active target org at any time.
- **`wxcli clear-org`** — remove the saved `orgId` to revert to single-org behavior.
- **`wxcli whoami`** — shows a "Target:" line when an org is set.
- **668 of 804 generated commands** auto-inject `orgId` from config on endpoints that accept it. No flag is required — the parameter is injected transparently.
- **3 hand-coded command files** (licenses, locations, numbers) also inject `orgId` from config. `users` is now an alias for the generated `people` command group.
- The builder agent has a blocking org confirmation step at session start (section 2b) when a partner token is detected.

See `docs/reference/authentication.md` (Partner/Multi-Org Tokens section) for full details.

### Error → Known Issue Quick Reference

When you hit one of these errors, jump to the matching known issue:

| Error | Symptom | Known Issue |
|-------|---------|-------------|
| 400 "Target user not authorized" | `call-controls` with admin token | #1 — needs user-level OAuth |
| 404 (error 4008) | `my-call-settings` or `mode-management` | #3 — user needs Calling license |
| 404 on person settings | Admin token on user-only endpoints | #4 — 6 settings have no admin path |
| 405 on workspace settings | Workspace `/telephony/config/` endpoint | #6 — needs Professional license |
| 403 on `cc-*` commands | PAT or wrong OAuth scopes | #13 — needs `cjp:config_*` OAuth scopes |
| 409 on location delete | Resources still assigned | See `.claude/rules/cleanup.md` |
| Unexpected command name | `show-*` vs `list-*`, singular vs plural | #5 — two path families; always run `--help` first |
| `--json-body` needed | Complex nested fields in request body | #2 — check `--help` for JSON example |

### Known issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Commands with nested fields now show an example JSON snippet in `--help` output (e.g., `wxcli user-settings update-call-forwarding --help`).
3. **my-call-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The `my-call-settings` group (120 commands) covers base + UserHub Phase 2/3/4 self-service endpoints. The CLI detects this error and prints a tip.
4. **6 person settings are user-only (no admin path).** Admin tokens get 404. Use `wxcli my-call-settings` with user-level OAuth. See `docs/reference/self-service-call-settings.md` gotchas.
5. **Two path families for person settings.** Classic `/people/{id}/features/` vs newer `/telephony/config/people/{id}/`. Some names differ. See `docs/reference/person-call-settings-behavior.md` (lines 36-54) for the full mapping table.
6. **Workspace `/telephony/config/` settings require Professional license.** Basic workspaces get 405. See `docs/reference/devices-workspaces.md` gotcha #10 for the endpoint-by-license matrix.
7. **Settings endpoints now support table output.** Settings-get commands (show-*) now accept `-o table` and auto-detect columns from the response data. List commands with non-standard response shapes (no `id`/`name` fields) also auto-detect columns.
8. **Customer Assist queues are hidden from default `call-queue list`.** Must pass `--has-cx-essentials true`. CLI group is `customer-assist` (alias `cx-essentials`). See `docs/reference/call-features-additional.md` cross-cutting gotchas.
9. **Supervisor delete returns 204 but supervisor persists.** Workaround: `update-supervisors` with `action: DELETE` on each agent. See `docs/reference/call-features-additional.md` gotchas.
10. **Create commands now support `-o json`.** All create commands accept `-o json` to output the full API response as JSON. Default behavior (`-o id`) prints just the created ID.
11. **`virtual-extensions` commands use wrong ID type.** Uses `VIRTUAL_EXTENSION`-encoded IDs but virtual lines use `VIRTUAL_LINE` IDs. `wxcli cleanup` uses raw REST as a workaround. See `docs/reference/virtual-lines.md` Raw HTTP Gotchas #9.
12. **Device config schema is firmware-dependent.** Per-line ringtone was absent on PhoneOS 3.5/3.6 but fixed in 4.1. Offline/expired devices retain a stale schema. See `docs/reference/devices-platform.md` gotchas #10-11.
13. **Contact Center (`cc-*`) commands require CC-scoped OAuth and region config.** PATs do NOT carry `cjp:config` scopes — even full admins on CC orgs get 403. Use an OAuth integration with `cjp:config_read`/`cjp:config_write` explicitly selected, then re-run the OAuth flow. The CC API also requires the bare UUID org ID (not the base64 Spark ID); `get_cc_org_id()` in `config.py` handles decoding. See `docs/reference/contact-center-core.md` gotchas #14 and #18-22.
14. **`wxcli cc-journey show-workspace-id-events` and the stream variant were missing `/v1/` in the URL.** Fixed in `src/wxcli/commands/cc_journey.py` — both commands now correctly hit `/v1/api/events/...`. See `docs/reference/contact-center-journey.md` gotcha #11.

### Cleanup Command

Detailed context in `.claude/rules/cleanup.md` (auto-loaded when touching `cleanup.py`). Contains: all flags, 13-layer deletion order, and known behaviors (virtual line workaround, location disable propagation, workspace ordering).

**Read the rule when:** running `wxcli cleanup`, modifying cleanup logic, or debugging deletion failures.

