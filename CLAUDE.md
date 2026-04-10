# Webex Calling Playbook

Build and configure Webex Calling, admin, device, and messaging APIs programmatically with guided Claude Code assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → `wxcadm` (XSI/E911/CP-API) → raw HTTP (fallback).
The wxcli CLI has 166 command groups covering calling, admin, device, messaging, meetings, and contact center APIs. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

## Quick Start

Use `/agents` and select **wxc-calling-builder**. This is the primary interface for all operations.
The agent walks you through authentication, interviews you about what you want to build, designs
a deployment plan, executes via `wxcli` commands, and verifies the results. **Do not run `wxcli`
commands directly** — the agent handles the full workflow.

**To build or configure Webex Calling:** `/agents` → wxc-calling-builder → describe what you want.

**To migrate from CUCM:** `/agents` → wxc-calling-builder → "Run a CUCM migration" and provide
the CUCM host/credentials. The agent runs the full pipeline: discover → normalize → map → analyze
→ resolve addresses → review decisions → plan → execute → verify. See the CUCM migration section
below for what the pipeline does.

**To debug a failing configuration:** Use `/wxc-calling-debug` (this one is a skill, invoked directly).

### Agent Invocation Pattern

wxc-calling-builder is a **phase-per-invocation** agent. Each major phase runs as a
fresh agent invocation — do not resume agents via `SendMessage` for multi-phase workflows.

**Invocation rules:**
- Always spawn a fresh agent for each phase
- Pass current state in the prompt: project name, current pipeline stage, key context
- The agent reads state from disk on startup and validates against the prompt
- For single-phase work (quick config, one-off query), one invocation is sufficient

**CUCM migration example:**
1. Spawn agent: "Run CUCM discovery for project X against host Y"
2. Agent completes discover + normalize + map + analyze, writes session-state, terminates
3. Spawn fresh agent: "Project X is at ANALYZED. Run decision review and generate report"
4. Agent completes decisions + report, writes session-state, terminates
5. Continue pattern through plan → execute

## File Map

### Agent & Skills

| Path | Purpose |
|------|---------|
| `.claude/agents/wxc-calling-builder.md` | Main builder agent — drives the full workflow |
| `.claude/agents/migration-advisor.md` | Opus-powered CCIE-level migration advisor — architectural reasoning + decision review |
| `.claude/skills/provision-calling/` | Skill: provision users, locations, licenses |
| `.claude/skills/teardown/` | Skill: dependency-safe teardown, `wxcli cleanup`, manual deletion procedure |
| `.claude/skills/configure-features/` | Skill: set up call features (AA, CQ, HG, etc.; CX Essentials → see customer-assist skill) |
| `.claude/skills/customer-assist/`      | Skill: configure Customer Assist (screen pop, wrap-up, recording, supervisors) |
| `.claude/skills/manage-call-settings/` | Skill: configure person/workspace call settings |
| `.claude/skills/configure-routing/` | Skill: configure routing (trunks, dial plans, PSTN) |
| `.claude/skills/manage-devices/` | Skill: manage devices (phones, DECT, workspaces) |
| `.claude/skills/device-platform/` | Skill: manage RoomOS device configs, workspace personalization, xAPI; also 9800-series phones (9811/9821/9841/9851/9861/9871) |
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
| `.claude/skills/cucm-migrate/` | Skill: execute CUCM-to-Webex migration from exported deployment plan |

### Reference Docs — wxc_sdk (Official Cisco SDK)

| Path | Purpose |
|------|---------|
| `docs/reference/authentication.md` | Auth methods, tokens, scopes, OAuth flows |
| `docs/reference/provisioning.md` | People, licenses, locations, org setup |
| `docs/reference/wxc-sdk-patterns.md` | wxc_sdk setup, auth, async patterns, common recipes |
| `docs/reference/call-features-major.md` | Auto attendants, call queues, hunt groups |
| `docs/reference/call-features-additional.md` | Paging, call park, pickup, voicemail groups, CX Essentials |
| `docs/reference/person-call-settings-handling.md` | Call forwarding, DND, call waiting, sim/sequential ring |
| `docs/reference/person-call-settings-media.md` | Voicemail, caller ID, privacy, barge, recording, intercept |
| `docs/reference/person-call-settings-permissions.md` | Incoming/outgoing permissions, feature access, executive/assistant |
| `docs/reference/person-call-settings-behavior.md` | Calling behavior, app services, hoteling, receptionist, numbers, ECBN |
| `docs/reference/self-service-call-settings.md` | User self-service call settings (/people/me/ endpoints) |
| `docs/reference/location-call-settings-core.md` | Location enablement, internal dialing, voicemail policies, voice portal |
| `docs/reference/location-call-settings-media.md` | Announcements, playlists, schedules, access codes |
| `docs/reference/location-call-settings-advanced.md` | Call recording, caller reputation, conference, supervisor, operating modes |
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

### Reference Docs — wxcadm (Admin Library with XSI/CP-API)

| Path | Purpose |
|------|---------|
| `docs/reference/wxcadm-core.md` | Webex/Org classes, object model, auth, wxcadm vs wxc_sdk comparison |
| `docs/reference/wxcadm-person.md` | Person class (34 call settings methods, 10 unique capabilities) |
| `docs/reference/wxcadm-locations.md` | Location management, features, schedules |
| `docs/reference/wxcadm-features.md` | AA, CQ, HG, pickup, announcements, recording via wxcadm |
| `docs/reference/wxcadm-devices-workspaces.md` | Devices, DECT, workspaces, virtual lines, numbers |
| `docs/reference/wxcadm-xsi-realtime.md` | XSI events, real-time call monitoring (UNIQUE to wxcadm) |
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
| `docs/reference/contact-center-analytics.md` | CC AI, journey, monitoring, subscriptions, tasks |

### Migration Knowledge Base (Opus Advisor)

Structured knowledge base read by the `migration-advisor` agent (Opus) during CUCM migration analysis and decision review. Grounded in the reference docs above + static advisory heuristics. The advisor reads relevant KB docs based on which decision types are present, then applies its own training for edge cases.

| Path | Purpose |
|------|---------|
| `docs/knowledge-base/migration/kb-css-routing.md` | CSS/partition ordering, dial plan decomposition, calling permissions |
| `docs/knowledge-base/migration/kb-device-migration.md` | Device replacement paths, firmware conversion, MPP vs RoomOS |
| `docs/knowledge-base/migration/kb-trunk-pstn.md` | Trunk topology, LGW vs CCPP, CPN transformation chains |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Hunt Group vs Call Queue depth, AA mapping, shared line semantics |
| `docs/knowledge-base/migration/kb-user-settings.md` | Call forwarding, voicemail, calling permissions, workspace licensing |
| `docs/knowledge-base/migration/kb-location-design.md` | Device pool → location consolidation, E911, numbering plan |
| `docs/knowledge-base/migration/kb-identity-numbering.md` | DN ownership, extension conflicts, duplicate users, number porting |
| `docs/knowledge-base/migration/kb-webex-limits.md` | Platform hard limits, feature gaps, scope requirements (always loaded) |

### Migration Operator Runbooks (Phase 2 Transferability)

Operator-facing reference docs for the CUCM-to-Webex migration tool. Written for a CUCM-literate SE running their first migration. The cucm-migrate skill points operators here for end-to-end pipeline help, per-decision lookups, and tuning recipes.

| Path | Purpose |
|------|---------|
| `docs/runbooks/cucm-migration/operator-runbook.md` | Operator runbook — end-to-end pipeline walkthrough, prerequisites, failure recovery |
| `docs/runbooks/cucm-migration/decision-guide.md` | Decision guide — one entry per DecisionType + advisory pattern, with override criteria |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Tuning reference — config keys, auto-rules, score weights, 5 worked recipes |

**When handling CUCM migration questions:** Read `operator-runbook.md` first for the pipeline walkthrough and `decision-guide.md` for per-decision interpretation. Read `tuning-reference.md` when discussing customer environment shapes (the 5 worked recipes), config tuning, or recurring decision patterns. The `cucm-migrate` skill loads these references automatically when `/cucm-migrate` is invoked; this instruction covers ad-hoc CUCM questions sent to `wxc-calling-builder` or other agents outside the skill flow.

### CLI (wxcli) — Primary Execution Layer

| Path | Purpose |
|------|---------|
| `src/wxcli/main.py` | CLI entry point — 166 command groups |
| `src/wxcli/commands/*.py` | All command implementations (raw HTTP pattern) |
| `wxcli --help` | Shows all command groups |
| `wxcli <group> --help` | Shows commands within a group |
| `wxcli <group> <command> --help` | Shows options for a command |
| `specs/webex-cloud-calling.json` | OpenAPI 3.0 spec — calling APIs |
| `specs/webex-admin.json` | OpenAPI 3.0 spec — admin/org management APIs |
| `specs/webex-device.json` | OpenAPI 3.0 spec — device management APIs |
| `specs/webex-messaging.json` | OpenAPI 3.0 spec — messaging/rooms/teams APIs |
| `specs/webex-meetings.json` | OpenAPI 3.0 spec — meetings/video mesh/transcripts APIs |
| `specs/webex-contact-center.json` | OpenAPI 3.0 spec — contact center APIs (48 groups, 431 commands) |
| `src/wxcli/commands/cleanup.py` | Batch cleanup: inventory + parallel layered deletion |
| `src/wxcli/commands/converged_recordings_export.py` | Hand-written download/export for converged recordings (registered into generated group) |

### CUCM→Webex Migration Tool (All 11 phases complete)

The migration tool is at `src/wxcli/migration/` and wired into the CLI as `wxcli cucm <command>`. **1642 tests passing.** See `src/wxcli/migration/CLAUDE.md` for the full file map, architecture, and pipeline commands. Use `/cucm-migrate` to execute a migration after running the pipeline.

**To run a migration:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `decisions` → `plan` → `preflight` → `export` → then invoke `/cucm-migrate`.

**Migration advisory workflow:** During `/cucm-migrate`, the cucm-migrate skill delegates to the `migration-advisor` agent (Opus) at two points: (1) after pipeline verification, it produces a `migration-narrative.md` with cross-decision analysis, dissent flags, and risk assessment; (2) during decision review, it presents advisories and recommendations with CCIE-level contextual explanation, grounded in the knowledge base at `docs/knowledge-base/migration/`. The static heuristics (`recommendation_rules.py`, `advisory_patterns.py`) remain the backbone — the Opus layer adds interpretation and structured dissent when heuristics are likely wrong. Falls back to mechanical presentation if the advisor agent is unavailable.

**To generate an assessment report:** `wxcli cucm init` → `discover` (or `discover --from-file`) → `normalize` → `map` → `analyze` → `report --brand "..." --prepared-by "..."`. Does not require plan/preflight/export — the report reads directly from the post-analyze store.

### Migration Spec Template

All migration pipeline spec documents must follow the template at `docs/references/migration-spec-template.md`. This applies whether the spec is written interactively via brainstorming, by an agent swarm, or manually. The template is rigid — all 9 sections are required. Sections can be brief for simple specs but cannot be omitted.

### Tools

| Path | Purpose |
|------|---------|
| `tools/postman_parser.py` | Shared dataclasses (`Endpoint`, `EndpointField`) and utilities for the generator pipeline |
| `tools/openapi_parser.py` | Parses OpenAPI 3.0 spec into `Endpoint` objects |
| `tools/command_renderer.py` | Renders `Endpoint` objects into Click command files |
| `tools/field_overrides.yaml` | Table columns, display config, and endpoint overrides |
| `tools/generate_commands.py` | Orchestrates OpenAPI parse → render → write pipeline |
| `tools/postman_spec_diff.py` | Offline Postman↔spec gap diff — compares exported collection JSON against local OpenAPI spec |

### Postman↔Spec Sync

Periodic gap reports live in `docs/reports/postman-spec-sync-YYYY-MM-DD.md`. Run the prompt at
`docs/prompts/postman-sync-periodic-report.md` to generate a new one via Postman MCP.

Offline alternative (no MCP needed — export the Postman collection first):
```
python3.11 tools/postman_spec_diff.py \
    --spec specs/webex-cloud-calling.json \
    --postman exported-calling.json \
    --skip-tags tools/field_overrides.yaml
```

Postman fork IDs (wxcli-dev):
- Cloud Calling: `15086833-e014a019-ecc3-4140-ab56-f2e9ccf7f95b`
- Admin: `15086833-5c8bec2d-afcd-4f60-a0ca-cf3bfc798755`
- Device: `15086833-6e026ee0-1f83-4d2b-bba6-b481ab62d0b6`
- Messaging: `15086833-12f8091a-7404-46a7-a1df-61eef3f31435`
- Meetings: `15086833-19910ac6-e687-4b90-b33a-3a02c6f50ce9`
- Contact Center: `15086833-a864a970-27a6-41ad-89d4-cf794012bbcc`

Mock server URLs (public, no auth required — return saved response examples):
- Cloud Calling: `https://f550a728-63cc-4da0-8a6f-e3eda351b9a9.mock.pstmn.io`
- Admin: `https://4ba8e16c-a764-4812-8eb3-e5dc00edcfff.mock.pstmn.io`
- Device: `https://24f543e0-234c-49b6-989d-1627497bf1b0.mock.pstmn.io`
- Messaging: `https://c87534f1-1e5c-477e-a249-333815c03415.mock.pstmn.io`

## CLI Status & Known Issues

**166 command groups covering calling, admin, device, messaging, meetings, and contact center APIs.** Nearly all generated from 7 OpenAPI 3.0 specs via `tools/generate_commands.py`. The `converged-recordings` group combines generated CRUD commands with hand-written `download` and `export` commands (`converged_recordings_export.py`).

### CLI test status

166 command groups, all generated from OpenAPI specs. Calling/admin/device/messaging groups live-tested across 4 batch sweeps (2026-03-19 through 2026-03-21). Contact center and meetings groups are newly generated and not yet live-tested. CUCM pipeline tested against live test bed (10.201.123.107) with 2 test bed expansions. See git history for detailed test logs.

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

### Known issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Commands with nested fields now show an example JSON snippet in `--help` output (e.g., `wxcli user-settings update-call-forwarding --help`).
3. **my-call-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The `my-call-settings` group (120 commands) covers base + UserHub Phase 2/3/4 self-service endpoints. The CLI detects this error and prints a tip.
4. **6 person settings are user-only (no admin path).** Admin tokens get 404. Use `wxcli my-call-settings` with user-level OAuth. See `docs/reference/self-service-call-settings.md` gotchas.
5. **Two path families for person settings.** Classic `/people/{id}/features/` vs newer `/telephony/config/people/{id}/`. Some names differ. See `docs/reference/person-call-settings-behavior.md` (lines 36-54) for the full mapping table.
6. **Workspace `/telephony/config/` settings require Professional license.** Basic workspaces get 405. See `docs/reference/devices-workspaces.md` gotcha #10 for the endpoint-by-license matrix.
7. **Settings endpoints now support table output.** Settings-get commands (show-*) now accept `-o table` and auto-detect columns from the response data. List commands with non-standard response shapes (no `id`/`name` fields) also auto-detect columns.
8. **Customer Assist queues are hidden from default `call-queue list`.** Must pass `--has-cx-essentials true`. See `docs/reference/call-features-additional.md` cross-cutting gotchas.
9. **Supervisor delete returns 204 but supervisor persists.** Workaround: `update-supervisors` with `action: DELETE` on each agent. See `docs/reference/call-features-additional.md` gotchas.
10. **CUCM CallPickupGroup creation with members fails on CUCM 15.0.** Create empty, then assign via `updateLine`. See `src/wxcli/migration/CLAUDE.md` known issues.
11. **Create commands now support `-o json`.** All create commands accept `-o json` to output the full API response as JSON. Default behavior (`-o id`) prints just the created ID.
12. **`virtual-extensions` commands use wrong ID type.** Uses `VIRTUAL_EXTENSION`-encoded IDs but virtual lines use `VIRTUAL_LINE` IDs. `wxcli cleanup` uses raw REST as a workaround. See `docs/reference/virtual-lines.md` Raw HTTP Gotchas #9.
13. **Device config schema is firmware-dependent.** Per-line ringtone was absent on PhoneOS 3.5/3.6 but fixed in 4.1. Offline/expired devices retain a stale schema. See `docs/reference/devices-platform.md` gotchas #10-11.
14. **Contact Center (`cc-*`) commands require CC-scoped OAuth and region config.** See `docs/reference/contact-center-core.md` gotchas #1-3.

### Cleanup Command

`wxcli cleanup run` batch-deletes Webex Calling resources in dependency-safe order.

**Flags:**
- `--scope "Name1,Name2"` — limit to specific locations (by name or ID)
- `--all` — clean up entire org (required if --scope not given)
- `--include-users` — also delete users (off by default)
- `--include-locations` — also delete locations (off by default, includes 90s wait for calling disable propagation)
- `--exclude-user-domains "wbx.ai,corp.com"` — keep users matching these email domains (use with `--include-users`)
- `--dry-run` — show what would be deleted without deleting
- `--max-concurrent N` — parallel deletions per layer (default 5)
- `--force` — skip confirmation prompt

**Deletion order** (13 layers, reverse of creation): dial plans → route lists → route groups → translation patterns → trunks → call features → schedules/operating modes → virtual lines → devices → workspaces → users → numbers → locations.

**Known behaviors:**
- Virtual lines use raw API (not `wxcli virtual-extensions`) due to ID type mismatch bug
- Location deletion requires disabling calling first + 90s propagation wait
- Location delete may still 409 after wait — re-run cleanup to retry
- Calling disable is best-effort — locations where calling is already off are still attempted for deletion
- Phone numbers are removed before location deletion (max 5 per API request, main numbers skipped)
- Call parks and call pickups are enumerated per-location (no org-wide list endpoint)
- Workspaces must be deleted before disable-calling can succeed — API has no location filter, client-side filtering by locationId

### Generator rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
- **Never create new hand-written command files** unless adding functionality that the generator cannot produce (e.g., multi-step workflows, file downloads). 3 legacy hand-written files remain (`locations.py`, `numbers.py`, `licenses.py`) — these are a known drift risk that miss generator improvements. `users.py` was retired and replaced with an alias to the generated `people` command group. `converged_recordings_export.py` is a deliberate hand-written extension that registers `download` and `export` commands onto the generated `converged_recordings` group via a `register(app)` pattern. For simple CRUD commands, use the generator. If a generated command needs custom behavior, use `field_overrides.yaml`.
- **`auto_inject_from_config`** — `field_overrides.yaml` supports an `auto_inject_from_config: ["orgId"]` key per endpoint. Parameters listed here are omitted from `--help` and injected automatically from the saved config at runtime. This replaces the older `omit_query_params` approach for `orgId`.
- **Spec files:** 7 OpenAPI 3.0 specs in `specs/` (`webex-cloud-calling.json`, `webex-admin.json`, `webex-device.json`, `webex-messaging.json`, `webex-meetings.json`, `webex-contact-center.json`, `webex-wholesale.json`)
- Regenerate one tag: `PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-cloud-calling.json --tag "Tag Name"`
- Regenerate one spec (all tags): `PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all`
- Regenerate all specs:
  ```
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-admin.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-device.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-messaging.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-meetings.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-contact-center.json --all
  ```
- Reinstall after regen: `pip3.11 install -e . -q`

### Templates, Examples & Plans

| Path | Purpose |
|------|---------|
| `docs/templates/deployment-plan.md` | Template: what the agent produces before executing |
| `docs/templates/execution-report.md` | Template: what the agent produces after executing |
| `docs/plans/` | Generated design docs (one per customer build) |
| `docs/later/` | Parked: meetings (messaging now has full reference docs and skills) |

### Agent Teams

Two reusable agent team patterns for development workflows. Requires Claude Code v2.1.32+.
Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json`.

| Pattern | Template | When to Use |
|---------|----------|-------------|
| **Spec-to-Ship** | `docs/team-prompts/spec-to-ship.md` | Features touching 2+ of: code, tests, docs. 3 teammates (impl/tests/docs). |
| **Reference Audit** | `docs/team-prompts/reference-audit.md` | Weekly/monthly drift check across 46 reference docs. 4 teammates by doc category. |

**Usage:** Open the template, copy the spawn prompt, fill in the bracketed values, paste into a session.

**Not for:** Quick bug fixes, single-file edits, exploratory research — use normal sessions or subagents.

## Reference Doc Sources

All reference docs are grounded in actual source code and official documentation:

- **wxc_sdk v1.30.0** (github.com/jeokrohn/wxc_sdk) — cloned at `../wxc_sdk_reference/`
- **wxcadm v4.6.1** (github.com/kctrey/wxcadm) — cloned at `../wxcadm_reference/`
- **OpenAPI 3.0 specs** — `specs/webex-cloud-calling.json` (calling), `specs/webex-admin.json` (admin), `specs/webex-device.json` (devices), `specs/webex-messaging.json` (messaging), `specs/webex-meetings.json` (meetings), `specs/webex-contact-center.json` (contact center)
- **Postman collection** (`../postman-webex-collections/webex_cloud_calling.json`) — legacy reference, 22.5MB, 1,079 endpoints
- **developer.webex.com** — Official API docs, guides, and blog posts
- **Cisco Live LTRCOL-2574** — Hands-on provisioning lab

**Execution pattern:** wxcli CLI commands are the primary execution method. Reference docs contain both SDK method signatures (for understanding) and Raw HTTP sections (for fallback). All Raw HTTP sections were added 2026-03-18.

Items marked `<!-- NEEDS VERIFICATION -->` need confirmation against live API behavior.
Known bugs found in wxcadm source are documented in the reference docs.

Maintainers: update reference docs when you discover new gotchas or API changes.

## Reference Doc Sync Protocol

This repo contains authoritative reference docs at `docs/reference/` that document every Webex Calling API surface. These docs were built from wxc_sdk and wxcadm source code and serve both the CLI and the playbook agent.

### When you learn something new

Whenever you discover a technical detail through implementation — a gotcha, a correction, an undocumented behavior, a scope requirement, a parameter that works differently than expected — do this:

1. **Check the relevant reference doc first.** Use the See Also links at the bottom of each doc to find related docs. Key docs by area:
   - Provisioning: `docs/reference/provisioning.md`
   - Call features (AA/CQ/HG): `docs/reference/call-features-major.md`, `call-features-additional.md`
   - Person settings: `docs/reference/person-call-settings-*.md` (4 files: handling, media, permissions, behavior) + `self-service-call-settings.md`
   - Location settings: `docs/reference/location-call-settings-*.md` (3 files: core, media, advanced)
   - Devices: `docs/reference/devices-*.md` (4 files: core, dect, workspaces, platform)
   - Routing: `docs/reference/call-routing.md`
   - Auth: `docs/reference/authentication.md`
   - SDK patterns: `docs/reference/wxc-sdk-patterns.md`

2. **If the reference doc is wrong or incomplete**, update it:
   - Fix incorrect method signatures, scopes, or data models
   - Add the gotcha to the doc's Gotchas section (create one if missing)
   - If you resolved a `<!-- NEEDS VERIFICATION -->` tag, remove it and replace with the verified info
   - Add a comment: `<!-- Verified via CLI implementation YYYY-MM-DD -->`

3. **If the reference doc is right**, move on — no action needed.

4. **If there's no reference doc for what you found**, add it to the closest doc's Gotchas section with a note about which command surfaced it.
