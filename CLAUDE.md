# Webex Calling Playbook

Build and configure Webex Calling, admin, device, and messaging APIs programmatically with guided Claude Code assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → raw HTTP (fallback).
The wxcli CLI has 178 command groups covering calling, admin, device, messaging, meetings, and contact center APIs. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

## Mandatory Grounding Rule

**Never answer any question about Webex Calling from training data alone.**

For every question — capability, configuration, behavior, limits, or anything else — you MUST either:
1. Invoke the relevant skill (`configure-features`, `customer-assist`, `contact-center`, etc.), OR
2. Read the relevant reference doc in `docs/reference/`

The reference docs and skills are the authoritative source for this project. Training data about Cisco/Webex products is unreliable — product tiers get conflated, feature names change, and capabilities vary by license. If the answer isn't in the docs or skills, say so explicitly rather than filling the gap from training data.

## Execution Discipline

- **Verify before claiming done.** Run the command, check the output, confirm the state. Never report success from inference alone. Ask yourself: "Would a staff engineer approve this?"
- **When a plan breaks, stop and re-plan.** Don't push through a failing approach — re-assess, update the plan, then resume.
- **Bug fixes: just fix it.** When the reproduction is clear (logs, errors, failing tests), resolve without asking for hand-holding. For ambiguous or architectural bugs, propose first.
- **Learn from every correction.** After any user correction, save a feedback memory capturing the pattern and why it matters. Write the rule so it prevents the same mistake in future sessions — not just this one.

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

A subagent can die mid-work when a long-running tool call (e.g. a Python polling loop) outlives Bash's ~10-min timeout: the call is killed, the agent loop never resumes to emit a final message, and `SendMessage` pings queue to a dead mailbox. This protocol prevents and recovers from that; it **complements** — does not replace — the phase-per-invocation rule above.

#### For subagents running long-running work (>2 min expected)

1. **Never wrap long-running polling in a single Bash call.** A call that outlives the ~10-min hard timeout is killed mid-run; stdout buffering hides progress and the parent sees silence (see the failure mode above).
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
| `.claude/skills/manage-call-settings/` | Skill: configure person/workspace call settings, phone number add/remove/reassign |
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
| `.claude/skills/contact-center/` | Skill: CC provisioning (agents, queues, entry points, dial numbers, flows, campaigns) |
| `.claude/skills/org-health/` | Skill: org health assessment — collect, analyze 18 checks, HTML report |
| `.claude/skills/cucm-migrate/` | Skill: execute CUCM-to-Webex migration from exported deployment plan |
| `.claude/skills/query-live/` | Skill: read-only natural language queries against live Webex Calling state |

### Skill Disambiguation

When multiple skills could match, use this lookup. (Basic skill-vs-skill routing already lives in each skill's `NOT for:` description, which the session always sees — the rows below cover only what those don't resolve: subtle overlaps, Calling-vs-CC terminology collisions, and undocumented capabilities.)

| If the user wants to... | Use this skill | NOT this one |
|--------------------------|---------------|-------------|
| Add/remove phone numbers on a user, number reassignment | `manage-call-settings` | `provision-calling` (that's for initial user/license creation; provision-calling owns number *inventory*, not per-user assignment) |
| Update user profile fields (alternate numbers, display name) | `provision-calling` | `manage-call-settings` (profile fields are People API, not telephony config) |
| Configure voicemail groups (shared location mailbox) | `configure-features` | `manage-call-settings` ("voicemail" collides: groups are a location feature, not person voicemail) |
| **Calling vs CC terminology — when the same word means different things:** | | |
| "Create a queue" (Calling call queue) | `configure-features` | `contact-center` (that's CC queues — different API, different entity) |
| "Create a queue" (Contact Center queue) | `contact-center` | `configure-features` (that's Calling queues — no skill-based routing) |
| "Set up a dial plan" (Calling outbound routing) | `configure-routing` | `contact-center` (CC dial plans map DNs to entry points, different API) |
| "Set up a dial plan" (CC DN-to-entry-point mapping) | `contact-center` | `configure-routing` (that's Calling outbound routing) |
| "Create a team" (Messaging spaces) | `messaging-spaces` | `contact-center` (CC teams group agents for routing) |
| "Create a team" (CC agent grouping) | `contact-center` | `messaging-spaces` (that's collaboration spaces) |
| "Set up recording" (per-user call recording) | `manage-call-settings` | `customer-assist` (that's CC queue recording) |
| "Set up recording" (CC queue recording) | `customer-assist` | `manage-call-settings` (that's per-user Calling recording) |
| "Download/export recordings" (converged recordings) | `reporting` | `manage-call-settings` (that's the per-user toggle, not retrieval) |
| "Configure the site" (Calling location) | `provision-calling` | `contact-center` (CC sites are logical agent groupings, not locations) |
| "Configure the site" (CC site for agent teams) | `contact-center` | `provision-calling` (Calling locations have addresses and PSTN) |
| "Create a workspace" (Calling device workspace) | `manage-devices` | `contact-center` (CC JDS workspaces are journey data containers) |
| "Set up business hours / holidays" (Calling schedule) | `configure-features` | `contact-center` (CC business hours are a separate entity type) |
| "Set up business hours / holidays" (CC schedule) | `contact-center` | `configure-features` (Calling schedules attach to AA/CQ/HG) |
| **Undocumented capabilities — user asks, table must route:** | | |
| Set up executive-assistant delegation | `manage-call-settings` | `configure-features` (delegation is a person setting, not a call feature) |
| Configure line keys, BLF, speed dials on phones | `manage-devices` | `manage-call-settings` (line key templates are device config, not call settings) |
| Digit manipulation (strip digits, add country code) | `configure-routing` (translation patterns) | `manage-call-settings` (that's per-person settings, not digit transforms) |
| Bulk import users from CSV | `provision-calling` | `manage-identity` (SCIM is directory sync, not bulk user provisioning) |
| How many licenses are unused / license audit | `manage-licensing` | `reporting` (reporting is CDR/call data, not license inventory) |
| Verify domain for SCIM / DNS setup | `manage-identity` | `provision-calling` (domain verification is identity, not calling provisioning) |
| Enable hoteling on a workspace | `manage-call-settings` | `manage-devices` (hoteling is a workspace calling setting, not device provisioning) |
| Import org contacts / directory entries | `manage-identity` | `provision-calling` (org contacts are directory, not calling users) |
| Reclaim licenses from inactive users | `manage-licensing` | `teardown` (license reclamation ≠ resource deletion) |
| Manage announcement repository files/playlists (AA/CQ greetings), or generate text-to-speech prompts | `configure-features` (groups: `announcements` — incl. `tts-generate`/`tts-usage`/`tts-status`/`tts-voices`; `announcement-playlists`, `cq-playlists`) | `reporting` (that's recordings, not announcements) |
| Configure E911 emergency services/addresses (`emergency-services` group) | `provision-calling` (location addresses) + `manage-call-settings` (per-person ECBN) | `wxc-calling-debug` |
| Virtual line call settings (`virtual-line-settings`) | `manage-call-settings` (virtual lines are person-like settings; see `virtual-lines.md`) | `provision-calling` |
| Operating modes / mode management (`mode-management`, user-token only per Known Issue #3) | `manage-call-settings` | `configure-features` (`operating-modes` location/feature side stays there) |
| Org/admin recordings retrieval (`admin-recordings`) | `reporting` | `manage-meetings` |
| Org profile, settings, roles (`identity-org`, `org-settings`, `roles`) | `manage-identity` | `audit-compliance` |
| Person-level hot-desking members (`hot-desking-members`) | `manage-call-settings` (person settings) | `manage-devices` (workspace/device-level hot-desk stays there) |

### Multi-Skill Workflows

Common admin goals that span multiple skills. When the user states one of these end goals, orchestrate the skills in sequence — don't pick just one.

| User goal | Skills needed (in order) | Why it's multi-skill |
|-----------|------------------------|---------------------|
| Offboard a user | `manage-call-settings` → `manage-devices` → `manage-licensing` → `teardown` → `manage-identity` | Must remove settings, release device, reclaim license, delete user, sync directory |
| Set up call recording for a team | `manage-call-settings` (per-person toggle) + `configure-features` (location recording policy) + `customer-assist` (if CX queue recording) | Recording config lives at person, location, AND queue level |
| E911 compliance for a location | `provision-calling` (emergency address on location) + `manage-call-settings` (per-person ECBN) | Address is location-level, ECBN callback number is per-person |
| Shared line on physical phones | `manage-call-settings` (shared line appearance / exec-assistant) + `manage-devices` (line key assignment on devices) | Pairing is a call setting, line key layout is device config |
| Port numbers and assign to users | `provision-calling` (location number inventory) → `manage-call-settings` (assign to users) → `configure-routing` (update dial plan if needed) | Numbers flow through location inventory before user assignment |
| Convert workspace to licensed user | `teardown` (decommission workspace) → `provision-calling` (create user, assign license) → `manage-call-settings` (voicemail, forwarding) → `manage-devices` (reassign device) | Workspace-to-user is a lifecycle change spanning 4 domains |
| CC overflow to Calling hunt group | `contact-center` (CC queue/entry point config) + `configure-features` (hunt group) + `configure-routing` (dial plan to connect them) | CC and Calling are separate routing worlds joined by PSTN/dial plan |
| Hot desking on conference phones | `manage-devices` (enable hot desking; workspace/device level) + `device-platform` (PhoneOS config keys for hot desk behavior) + `manage-call-settings` (workspace hoteling settings AND person-level hot-desking members via `hot-desking-members`) | Device provisioning, firmware config, and calling settings are three layers; person-level members are person settings |

### Reference Docs — Webex API Surface

| Path | Purpose |
|------|---------|
| `docs/reference/authentication.md` | Auth methods, tokens, scopes, OAuth flows |
| `docs/reference/provisioning.md` | People (profile fields, phoneNumbers array incl. alternate1/alternate2), licenses, locations, org setup |
| `docs/reference/call-features-major.md` | Auto attendants, call queues, hunt groups |
| `docs/reference/call-features-additional.md` | Paging, call park, pickup, voicemail groups, Customer Assist |
| `docs/reference/person-call-settings-handling.md` | Call forwarding, DND, call waiting, sim/sequential ring |
| `docs/reference/person-call-settings-media.md` | Voicemail, caller ID, privacy, barge, recording, intercept |
| `docs/reference/person-call-settings-permissions.md` | Incoming/outgoing permissions, feature access, executive/assistant |
| `docs/reference/person-call-settings-behavior.md` | Calling behavior, app services, hoteling, receptionist, phone number add/remove/reassign, ECBN |
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

### Reference Docs — XSI Real-Time (wxcadm)

| Path | Purpose |
|------|---------|
| `docs/reference/wxcadm-xsi-realtime.md` | XSI events, real-time call monitoring (used by call-control skill) |

Historical SDK object-model docs (wxcadm core/person/locations/features/devices-workspaces/routing/advanced, wxc-sdk-patterns) live in `docs/reference/archive/` — they document Python SDKs this repo does not execute. Resurrect deliberately if a future skill needs RedSky-portal/Meraki/CP-API facts.

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
| `docs/reference/contact-center-routing.md` | CC dial plans, dial number-to-entry-point mapping, campaigns, flows, audio, contacts, outdial |
| `docs/reference/contact-center-analytics.md` | CC AI, monitoring, subscriptions, tasks, search |
| `docs/reference/contact-center-journey.md` | JDS: workspaces, persons, identity, profile views, events, WXCC subscription |

### Migration (KB, Runbooks, Tool)

Detailed migration context lives in `.claude/rules/cucm-migration.md` (auto-loaded when touching migration paths). Contains: knowledge base file map (8 KB docs for the Opus advisor), operator runbooks (3 docs for pipeline walkthrough, decision guide, tuning), migration tool pipeline commands, advisory workflow, report/diff/notice generation commands, and the phase-by-phase agent invocation example.

**Read the rule when:** handling any CUCM migration question, running `/cucm-migrate`, or working with the migration advisor agent — even if not editing migration source files directly.

### CLI (wxcli) — Primary Execution Layer

| Path | Purpose |
|------|---------|
| `wxcli --help` | Shows all command groups |
| `wxcli <group> --help` | Shows commands within a group |
| `wxcli <group> <command> --help` | Shows options for a command |

### Org Health Assessment

Detailed context in `.claude/rules/org-health.md` (auto-loaded when touching org health paths). Contains: file map (models, collector, checks, analyze, report), run instructions, and check category breakdown (Security Posture, Routing Hygiene, Feature Utilization, Device Health).

**Read the rule when:** running an org health audit, modifying checks, or working on the report generator.

### CUCM→Webex Migration Tool

The migration tool is wired into the CLI as `wxcli cucm <command>`. Pipeline workflow, report generation, and advisory details are in `.claude/rules/cucm-migration.md`.

## CLI Status & Known Issues

**178 command groups covering calling, admin, device, messaging, meetings, wholesale, and contact center APIs.** The `converged-recordings` group combines generated CRUD commands with hand-written `download` and `export` commands.

### Partner Multi-Org Support

wxcli supports partner/VAR/MSP admins who manage multiple customer orgs with a single partner token.

- **`wxcli configure`** — detects multi-org tokens automatically and prompts for org selection. The selected `orgId` is saved to the config file.
- **`wxcli switch-org`** — change the active target org at any time.
- **`wxcli clear-org`** — remove the saved `orgId` to revert to single-org behavior.
- **`wxcli whoami`** — shows a "Target:" line when an org is set.
- **Most generated commands** auto-inject `orgId` from config on endpoints that accept it (generator `auto_inject_from_config`). No flag is required — the parameter is injected transparently.
- The former hand-coded trio (licenses, locations, numbers) is retired — all three are generated modules now with the same orgId injection. `users` is an alias for the generated `people` group; `licenses-api` is a deprecated one-release alias for `licenses` (renamed 2026-07-02).
- The builder agent has a blocking org confirmation step at session start (section 2b) when a partner token is detected.

See `docs/reference/authentication.md` (Partner/Multi-Org Tokens section) for full details.

### Error → Known Issue Quick Reference

When you hit one of these errors, jump to the matching known issue:

| Error | Symptom | Known Issue |
|-------|---------|-------------|
| 400 "Target user not authorized" | `call-controls` with admin token | #1 — needs user-level OAuth |
| 404 (error 4008) | `my-call-settings` or `mode-management` | #3 — user needs Calling license |
| 404 on person settings | Admin token on user-only endpoints | #4 — 19 settings have no admin path |
| 405 on workspace settings | Workspace `/telephony/config/` endpoint | #6 — needs Professional license |
| 403 on `cc-*` commands | PAT or wrong OAuth scopes | #11 — needs `cjp:config_*` OAuth scopes |
| 409 on location delete | Resources still assigned | See `.claude/rules/cleanup.md` |
| Unexpected command name | `show-*` vs `list-*`, singular vs plural | #5 — two path families; always run `--help` first |
| `--json-body` needed | Complex nested fields in request body | #2 — check `--help` for JSON example |

### Known issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Commands with nested fields now show an example JSON snippet in `--help` output (e.g., `wxcli user-settings update-call-forwarding --help`).
3. **my-call-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The `my-call-settings` group (120 commands) covers base + UserHub Phase 2/3/4 self-service endpoints. The CLI detects this error and prints a tip.
4. **19 person settings are user-only (no admin path).** Admin tokens get 404. Use `wxcli my-call-settings` with user-level OAuth. Includes core settings (`callBlock`, `callCaptions`, `anonymousCallReject`, `callNotify`, `preferredAnswerEndpoint`, `guestCalling`, `modeManagement`) plus informational/read-only endpoints (`availableCallerIds`, `queues`, `services`, etc.). See `docs/reference/self-service-call-settings.md` gotchas.
5. **Two path families for person settings.** Classic `/people/{id}/features/` vs newer `/telephony/config/people/{id}/`. Some names differ. See `docs/reference/person-call-settings-behavior.md` (lines 36-54) for the full mapping table.
6. **Workspace `/telephony/config/` settings require Professional license.** Basic workspaces get 405. See `docs/reference/devices-workspaces.md` gotcha #10 for the endpoint-by-license matrix.
7. **Customer Assist queues require `--has-cx-essentials true` on `call-queue` commands.** Use `wxcli customer-assist` (alias `cx-essentials`) as the primary CLI group for CX queue management. Standard `call-queue list` omits CX queues unless the flag is passed. See `docs/reference/call-features-additional.md` cross-cutting gotchas.
8. **Supervisor delete returns 204 but supervisor persists.** Workaround: `update-supervisors` with `action: DELETE` on each agent. See `docs/reference/call-features-additional.md` gotchas.
9. **`virtual-extensions` commands use wrong ID type.** Uses `VIRTUAL_EXTENSION`-encoded IDs but virtual lines use `VIRTUAL_LINE` IDs. Still separate path families in the spec (`virtualExtensions/{extensionId}` vs `virtualLines/{virtualLineId}`). `wxcli cleanup` uses raw REST as a workaround. See `docs/reference/virtual-lines.md` Raw HTTP Gotchas #9.
10. **Device config schema is firmware-dependent.** Per-line ringtone was absent on PhoneOS 3.5/3.6 but fixed in 4.1. Offline/expired devices retain a stale schema. See `docs/reference/devices-platform.md` gotchas #10-11.
11. **Contact Center (`cc-*`) commands require CC-scoped OAuth and region config.** PATs do NOT carry `cjp:config` scopes — even full admins on CC orgs get 403. Use an OAuth integration with `cjp:config_read`/`cjp:config_write` explicitly selected, then re-run the OAuth flow. The CC API also requires the bare UUID org ID (not the base64 Spark ID); `get_cc_org_id()` in `config.py` handles decoding. See `docs/reference/contact-center-core.md` gotchas #14 and #18-22.

### Cleanup Command

Detailed context in `.claude/rules/cleanup.md` (auto-loaded when touching `cleanup.py`). Contains: all flags, 13-layer deletion order, and known behaviors (virtual line workaround, location disable propagation, workspace ordering).

**Read the rule when:** running `wxcli cleanup`, modifying cleanup logic, or debugging deletion failures.

