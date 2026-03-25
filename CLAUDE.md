# Webex Calling Playbook

Build and configure Webex Calling, admin, device, and messaging APIs programmatically with guided Claude Code assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → `wxcadm` (XSI/E911/CP-API) → raw HTTP (fallback).
The wxcli CLI has 100 command groups covering calling, admin, device, and messaging APIs. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

## Quick Start

Use `/agents` and select **wxc-calling-builder** to start building. The agent walks you through
authentication, interviews you about what you want to build, designs a deployment plan, executes
via `wxcli` commands, and verifies the results. Covers Webex Calling, admin/org management,
identity/SCIM, licensing, audit/compliance, and partner operations.

## If Debugging

Use `/wxc-calling-debug` to troubleshoot a failing configuration (this one is a skill, invoked directly).

## File Map

### Agent & Skills

| Path | Purpose |
|------|---------|
| `.claude/agents/wxc-calling-builder.md` | Main builder agent — drives the full workflow |
| `.claude/skills/provision-calling/` | Skill: provision users, locations, licenses |
| `.claude/skills/configure-features/` | Skill: set up call features (AA, CQ, HG, etc.; CX Essentials → see customer-assist skill) |
| `.claude/skills/customer-assist/`      | Skill: configure Customer Assist (screen pop, wrap-up, recording, supervisors) |
| `.claude/skills/manage-call-settings/` | Skill: configure person/workspace call settings |
| `.claude/skills/configure-routing/` | Skill: configure routing (trunks, dial plans, PSTN) |
| `.claude/skills/manage-devices/` | Skill: manage devices (phones, DECT, workspaces) |
| `.claude/skills/device-platform/` | Skill: manage RoomOS device configs, workspace personalization, xAPI; also 9800-series phones (9811/9821/9841/9851/9861/9871) |
| `.claude/skills/call-control/` | Skill: real-time call control, webhooks, XSI |
| `.claude/skills/reporting/` | Skill: CDR, queue stats, call quality, reports |
| `.claude/skills/wxc-calling-debug/` | Skill: debug failing configurations |
| `.claude/skills/manage-identity/` | Skill: SCIM sync, directory, groups, contacts, domains |
| `.claude/skills/audit-compliance/` | Skill: audit events, security, compliance, authorizations |
| `.claude/skills/manage-licensing/` | Skill: license audit, assignment, reclamation |
| `.claude/skills/messaging-spaces/` | Skill: manage spaces, teams, memberships, ECM, HDS |
| `.claude/skills/messaging-bots/` | Skill: build bots, adaptive cards, webhooks, cross-domain integrations |
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

### CLI (wxcli) — Primary Execution Layer

| Path | Purpose |
|------|---------|
| `src/wxcli/main.py` | CLI entry point — 100 command groups |
| `src/wxcli/commands/*.py` | All command implementations (raw HTTP pattern) |
| `wxcli --help` | Shows all command groups |
| `wxcli <group> --help` | Shows commands within a group |
| `wxcli <group> <command> --help` | Shows options for a command |
| `webex-cloud-calling.json` | OpenAPI 3.0 spec — calling APIs |
| `webex-admin.json` | OpenAPI 3.0 spec — admin/org management APIs |
| `webex-device.json` | OpenAPI 3.0 spec — device management APIs |
| `webex-messaging.json` | OpenAPI 3.0 spec — messaging/rooms/teams APIs |

### CUCM→Webex Migration Tool (All 11 phases complete)

The migration tool is at `src/wxcli/migration/` and wired into the CLI as `wxcli cucm <command>`. It does NOT use the auto-generator. **1294 tests passing.** Use `/cucm-migrate` to execute a migration after running the pipeline.

| Path | Purpose |
|------|---------|
| `docs/plans/cucm-migration-roadmap.md` | **Master roadmap** — what's done, what's ready, what's next. Start here. |
| `docs/plans/cucm-pipeline-architecture.md` | Pipeline architecture summary — SQLite store, two-pass ELT, linter-pattern analyzers, NetworkX DAG |
| `docs/plans/cucm-pipeline/01-07 + 03b` | 8 detailed architecture docs |
| `src/wxcli/commands/cucm.py` | Phases 08+10 — CLI: 13 commands (init, discover, normalize, map, analyze, plan, preflight, decisions, decide, export, inventory, status, config) |
| `src/wxcli/commands/cucm_config.py` | Phase 08 — Config management helpers |
| `src/wxcli/migration/models.py` | Canonical data models — 23 types, DecisionType (20 values), Decision, MapperResult, TransformResult |
| `src/wxcli/migration/store.py` | SQLite-backed store — objects, cross_refs, decisions, journal, merge_log, merge_decisions() |
| `src/wxcli/migration/cucm/` | Phase 03 — AXL connection, 8 extractors, discovery pipeline |
| `src/wxcli/migration/transform/normalizers.py` | Phase 04 — 24 Pass 1 normalizers |
| `src/wxcli/migration/transform/cross_reference.py` | Phase 04 — CrossReferenceBuilder (26 relationships + 3 enrichments) |
| `src/wxcli/migration/transform/pipeline.py` | Phase 04 — `normalize_discovery()` entry point |
| `src/wxcli/migration/transform/mappers/` | Phase 05 — 11 mappers + base.py + engine.py (9 original + call_forwarding_mapper + monitoring_mapper) |
| `src/wxcli/migration/transform/analyzers/` | Phase 06 — 12 analyzers (3 analyzer-owned + 9 mapper-owned) |
| `src/wxcli/migration/transform/analysis_pipeline.py` | Phase 06 — Orchestrator: run analyzers → merge → auto-rules + resolve_and_cascade() |
| `src/wxcli/migration/execute/` | Phase 07 — planner.py, dependency.py (NetworkX DAG), batch.py |
| `src/wxcli/migration/export/` | Phase 09 — deployment_plan.py, json/csv exports (command_builder.py removed in Phase 12b) |
| `src/wxcli/migration/preflight/` | Phase 10 — checks.py (8 preflight checks), runner.py (orchestrator), CLI `wxcli cucm preflight` |
| `src/wxcli/migration/advisory/` | Phase 13 — Advisory system: per-decision recommendations (19 rules) + cross-cutting advisor (16 patterns) |
| `src/wxcli/migration/report/` | Assessment report generator — complexity score, SVG charts, executive summary + appendix → HTML/PDF. See its CLAUDE.md. |
| `.claude/skills/cucm-migrate/SKILL.md` | Phase 11 — 6-step execution skill: preflight → plan summary → batch execute → delegate → report |

**Where the design spec and pipeline architecture docs conflict, the pipeline architecture docs are authoritative.**

Each subdirectory has its own CLAUDE.md (local context) and TODO.md (outstanding work).
See `docs/plans/cucm-migration-roadmap.md` for the master project status.

**To run a migration:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `decisions` → `plan` → `preflight` → `export` → then invoke `/cucm-migrate`.

**To generate an assessment report:** `wxcli cucm init` → `discover` (or `discover --from-file`) → `normalize` → `map` → `analyze` → `report --brand "..." --prepared-by "..."`. Does not require plan/preflight/export — the report reads directly from the post-analyze store.

### Tools

| Path | Purpose |
|------|---------|
| `tools/postman_parser.py` | Shared dataclasses (`Endpoint`, `EndpointField`) and utilities for the generator pipeline |
| `tools/openapi_parser.py` | Parses OpenAPI 3.0 spec into `Endpoint` objects |
| `tools/command_renderer.py` | Renders `Endpoint` objects into Click command files |
| `tools/field_overrides.yaml` | Table columns, display config, and endpoint overrides |
| `tools/generate_commands.py` | Orchestrates OpenAPI parse → render → write pipeline |

## CLI Status & Known Issues

**100 command groups covering calling, admin, device, and messaging APIs.** All generated from 4 OpenAPI 3.0 specs via `tools/generate_commands.py`.

### Test status (as of 2026-03-18)

- **v0.1.0** (14 commands): Fully live-tested, 3 bugs fixed.
- **v3 original 17 groups** (382 commands): All live-tested, 43 response key bugs fixed via `field_overrides.yaml`.
- **v3 extended 31 groups** (~600 commands): Registered. Most now live-tested via Batches 1-3.
- **OpenAPI migration**: All commands regenerated from OpenAPI spec. Singleton/list classification, response keys, and body field parsing all derived from schema.
- **Live API sweep Batch 1 (2026-03-19):** Tested ~60 CLI commands and ~36 person endpoints. Found 9 CLI bugs (5 response key, 2 SCIM URL, 2 missing params) and 6 user-only person endpoints. All documented in reference docs.
- **Live API sweep Batch 2 (2026-03-19):** Tested user-settings (~12 cmds), workspace-settings (~12 cmds), virtual-line-settings (~6 cmds), device-settings (~4 cmds), device-dynamic-settings, call-routing (5 list cmds), calling-service, caller-reputation, client-settings, hot-desking-portal, report-templates, CDR, admin-recordings, resource-groups, resource-group-memberships, hybrid-clusters/connectors, and workspace endpoint existence via curl. Found 3 CLI bugs (CDR wrong base URL, null result traceback, report-templates misclassified as singleton). Fixed in generator: analytics base URL support, null result guard, direct-array-response list classification. Mapped workspace endpoint access by license tier (Basic vs Professional).
- **Live API sweep Batch 3 (2026-03-20):** Tested location-settings (~15 cmds), location-schedules, location-voicemail (~10 cmds), emergency-services (~15 cmds), dect-devices full CRUD lifecycle (create network → add handsets with 2 lines → update → bulk add → delete), call-recording (~10 cmds), organizations, roles, org-contacts, device-configurations, xapi, workspace-personalization. No new CLI bugs found. Full DECT create/read/update/delete cycle verified. Base station MACs require Cisco manufacturing database (Bifrost) — can't use fake MACs.
- **Live API sweep Batch 4 (2026-03-21):** Customer Assist (cx-essentials) end-to-end: screen pop, wrap-up reasons, queue call recording (2 new commands), supervisors, available agents. Found 6 CLI bugs (list table column, validate output, list-settings response shape, missing error 28018 handling, wrong queue recording JSON example, update-settings missing 28018). Found 2 generator issues (supervisor delete missing hasCxEssentials param, create output for empty dict). Found 3 API behaviors: CX queues hidden from default `call-queue list`, CX queue creation requires `callPolicies`, supervisor delete returns 204 but supervisor persists (workaround: remove agents via update). All CLI bugs fixed, generator enhanced with `add_query_params` override.
- **Test bed expansion (2026-03-24):** Added 15 new + 5 modified objects to CUCM test bed (10.201.123.107) for pipeline coverage gaps: 2 blocking partitions in CSSes (CSSMapper CallingPermission), 2 common-area phones (WorkspaceMapper), 2nd pickup group, 2nd CTI Route Point, 2 holiday time periods (HOLIDAY OperatingMode), time schedule→partition wiring. Script: `tests/migration/cucm/provision_testbed_phase9.py`. Discovered 4 AXL gotchas (pickup group members, CTI RP protocol, TimePeriod enums). Pipeline gaps: no PagingGroup AXL object (needs InformaCast), no Unity Connection for CUPI voicemail extraction.

### Partner Multi-Org Support

wxcli supports partner/VAR/MSP admins who manage multiple customer orgs with a single partner token.

- **`wxcli configure`** — detects multi-org tokens automatically and prompts for org selection. The selected `orgId` is saved to the config file.
- **`wxcli switch-org`** — change the active target org at any time.
- **`wxcli clear-org`** — remove the saved `orgId` to revert to single-org behavior.
- **`wxcli whoami`** — shows a "Target:" line when an org is set.
- **668 of 804 generated commands** auto-inject `orgId` from config on endpoints that accept it. No flag is required — the parameter is injected transparently.
- **4 hand-coded command files** (users, licenses, locations, numbers) also inject `orgId` from config.
- The builder agent has a blocking org confirmation step at session start (section 2b) when a partner token is detected.

See `docs/reference/authentication.md` (Partner/Multi-Org Tokens section) for full details.

### Known issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Commands with nested fields now show an example JSON snippet in `--help` output (e.g., `wxcli user-settings update-call-forwarding --help`).
3. **my-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The CLI now detects this error and prints a tip.
4. **6 person settings are user-only (no admin path).** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` only exist at `/telephony/config/people/me/settings/{feature}`. Admin tokens get 404. Use user-level OAuth for these. See `docs/reference/self-service-call-settings.md` for the full 138-endpoint /people/me/ surface.
5. **Two path families for person settings.** Classic settings use `/people/{personId}/features/{feature}`. Newer settings use `/telephony/config/people/{personId}/{feature}`. Some names differ between families: `intercept` (not `callIntercept`), `reception` (not `receptionist`), `applications` (not `applicationServicesSettings`), `autoTransferNumbers` (not `transferNumbers`), `pushToTalk` (not `pushToTalkSettings`).
6. **Workspace `/telephony/config/` settings require Professional license.** Most workspace call settings under `/telephony/config/workspaces/{id}/` return 405 "Invalid Professional Place" for Basic-licensed workspaces. Only `musicOnHold` and `doNotDisturb` work on Basic. The `/workspaces/{id}/features/` path family (callForwarding, callWaiting, callerId, intercept, monitoring) works on Basic. The CLI now detects this error and prints a tip.
7. **Settings endpoints now support table output.** Settings-get commands (show-*) now accept `-o table` and auto-detect columns from the response data. List commands with non-standard response shapes (no `id`/`name` fields) also auto-detect columns.
8. **Customer Assist queues are hidden from default `call-queue list`.** Must pass `--has-cx-essentials true` to see them. CX queue creation requires `callPolicies` via `--json-body`. Error 28018 ("CX Essentials is not enabled for this Call center") means the queue isn't a Customer Assist queue. The CLI detects this and prints a tip.
9. **Supervisor delete returns 204 but supervisor persists.** `delete-supervisors-config-1 --has-cx-essentials true` gets 204 from the API but the supervisor remains. Workaround: use `update-supervisors` with `action: DELETE` on each agent — removing the last agent auto-removes the supervisor.
10. **CUCM CallPickupGroup creation with members fails on CUCM 15.0.** The AXL `addCallPickupGroup` operation with `<members>` containing `<directoryNumber>` fails with a null priority foreign key constraint. Workaround: create the pickup group empty, then use `updateLine` with `callPickupGroupName` to assign members at the line level. Affects both wxcadm and raw AXL calls.
11. **Create commands now support `-o json`.** All create commands accept `-o json` to output the full API response as JSON. Default behavior (`-o id`) prints just the created ID.

### Generator rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
- **Never create new hand-written command files.** 4 legacy hand-written files exist (`users.py`, `locations.py`, `numbers.py`, `licenses.py`) — these are a known drift risk that miss generator improvements. All new commands must go through the generator. If a generated command needs custom behavior, use `field_overrides.yaml`. These 4 files are queued for replacement (see roadmap).
- **`auto_inject_from_config`** — `field_overrides.yaml` supports an `auto_inject_from_config: ["orgId"]` key per endpoint. Parameters listed here are omitted from `--help` and injected automatically from the saved config at runtime. This replaces the older `omit_query_params` approach for `orgId`.
- **Spec files:** 4 OpenAPI 3.0 specs in project root (`webex-cloud-calling.json`, `webex-admin.json`, `webex-device.json`, `webex-messaging.json`)
- Regenerate one tag: `PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-cloud-calling.json --tag "Tag Name"`
- Regenerate one spec (all tags): `PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-cloud-calling.json --all`
- Regenerate all specs:
  ```
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-cloud-calling.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-admin.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-device.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-messaging.json --all
  ```
- Reinstall after regen: `pip3.11 install -e . -q`

### Templates, Examples & Plans

| Path | Purpose |
|------|---------|
| `docs/templates/deployment-plan.md` | Template: what the agent produces before executing |
| `docs/templates/execution-report.md` | Template: what the agent produces after executing |
| `docs/plans/` | Generated design docs (one per customer build) |
| `docs/later/` | Parked: meetings (messaging now has full reference docs and skills) |

## Reference Doc Sources

All reference docs are grounded in actual source code and official documentation:

- **wxc_sdk v1.30.0** (github.com/jeokrohn/wxc_sdk) — cloned at `../wxc_sdk_reference/`
- **wxcadm v4.6.1** (github.com/kctrey/wxcadm) — cloned at `../wxcadm_reference/`
- **OpenAPI 3.0 specs** — `webex-cloud-calling.json` (calling), `webex-admin.json` (admin), `webex-device.json` (devices), `webex-messaging.json` (messaging)
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
