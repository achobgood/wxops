# Webex Calling Playbook

Build and configure Webex Calling, admin, device, and messaging APIs programmatically with guided Claude Code assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → `wxcadm` (XSI/E911/CP-API) → raw HTTP (fallback).
The wxcli CLI has 100 command groups covering calling, admin, device, and messaging APIs. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

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

## File Map

### Agent & Skills

| Path | Purpose |
|------|---------|
| `.claude/agents/wxc-calling-builder.md` | Main builder agent — drives the full workflow |
| `.claude/skills/provision-calling/` | Skill: provision users, locations, licenses |
| `.claude/skills/teardown/` | Skill: dependency-safe teardown, `wxcli cleanup`, manual deletion procedure |
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
| `specs/webex-cloud-calling.json` | OpenAPI 3.0 spec — calling APIs |
| `specs/webex-admin.json` | OpenAPI 3.0 spec — admin/org management APIs |
| `specs/webex-device.json` | OpenAPI 3.0 spec — device management APIs |
| `specs/webex-messaging.json` | OpenAPI 3.0 spec — messaging/rooms/teams APIs |
| `src/wxcli/commands/cleanup.py` | Batch cleanup: inventory + parallel layered deletion |

### CUCM→Webex Migration Tool (All 11 phases complete)

The migration tool is at `src/wxcli/migration/` and wired into the CLI as `wxcli cucm <command>`. **1487 tests passing.** See `src/wxcli/migration/CLAUDE.md` for the full file map, architecture, and pipeline commands. Use `/cucm-migrate` to execute a migration after running the pipeline.

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

### CLI test status

100 command groups, all generated from OpenAPI specs, live-tested across 4 batch sweeps (2026-03-19 through 2026-03-21). All found bugs fixed. CUCM pipeline tested against live test bed (10.201.123.107) with 2 test bed expansions. See git history for detailed test logs.

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
3. **my-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The CLI now detects this error and prints a tip.
4. **6 person settings are user-only (no admin path).** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` only exist at `/telephony/config/people/me/settings/{feature}`. Admin tokens get 404. Use user-level OAuth for these. See `docs/reference/self-service-call-settings.md` for the full 138-endpoint /people/me/ surface.
5. **Two path families for person settings.** Classic settings use `/people/{personId}/features/{feature}`. Newer settings use `/telephony/config/people/{personId}/{feature}`. Some names differ between families: `intercept` (not `callIntercept`), `reception` (not `receptionist`), `applications` (not `applicationServicesSettings`), `autoTransferNumbers` (not `transferNumbers`), `pushToTalk` (not `pushToTalkSettings`).
6. **Workspace `/telephony/config/` settings require Professional license.** Most workspace call settings under `/telephony/config/workspaces/{id}/` return 405 "Invalid Professional Place" for Basic-licensed workspaces. Only `musicOnHold` and `doNotDisturb` work on Basic. The `/workspaces/{id}/features/` path family (callForwarding, callWaiting, callerId, intercept, monitoring) works on Basic. The CLI now detects this error and prints a tip.
7. **Settings endpoints now support table output.** Settings-get commands (show-*) now accept `-o table` and auto-detect columns from the response data. List commands with non-standard response shapes (no `id`/`name` fields) also auto-detect columns.
8. **Customer Assist queues are hidden from default `call-queue list`.** Must pass `--has-cx-essentials true` to see them. CX queue creation requires `callPolicies` via `--json-body`. Error 28018 ("CX Essentials is not enabled for this Call center") means the queue isn't a Customer Assist queue. The CLI detects this and prints a tip.
9. **Supervisor delete returns 204 but supervisor persists.** `delete-supervisors-config-1 --has-cx-essentials true` gets 204 from the API but the supervisor remains. Workaround: use `update-supervisors` with `action: DELETE` on each agent — removing the last agent auto-removes the supervisor.
10. **CUCM CallPickupGroup creation with members fails on CUCM 15.0.** The AXL `addCallPickupGroup` operation with `<members>` containing `<directoryNumber>` fails with a null priority foreign key constraint. Workaround: create the pickup group empty, then use `updateLine` with `callPickupGroupName` to assign members at the line level. Affects both wxcadm and raw AXL calls.
11. **Create commands now support `-o json`.** All create commands accept `-o json` to output the full API response as JSON. Default behavior (`-o id`) prints just the created ID.
12. **`virtual-extensions` commands use wrong ID type.** The generated `virtual-extensions` command group maps to the Virtual Extensions API which uses `VIRTUAL_EXTENSION`-encoded IDs. Virtual lines created via `/telephony/config/virtualLines` use `VIRTUAL_LINE` IDs. `virtual-extensions list` returns empty, and `virtual-extensions delete` returns 400. **Workaround:** Use raw REST calls (`DELETE /v1/telephony/config/virtualLines/{id}`). The `wxcli cleanup` command already uses raw REST for this reason. The `virtual-line-settings` group uses the correct path family but only has settings commands, not CRUD.

### Cleanup Command

`wxcli cleanup run` batch-deletes Webex Calling resources in dependency-safe order.

**Flags:**
- `--scope "Name1,Name2"` — limit to specific locations (by name or ID)
- `--all` — clean up entire org (required if --scope not given)
- `--include-users` — also delete users (off by default)
- `--include-locations` — also delete locations (off by default, includes 90s wait for calling disable propagation)
- `--dry-run` — show what would be deleted without deleting
- `--max-concurrent N` — parallel deletions per layer (default 5)
- `--force` — skip confirmation prompt

**Deletion order** (12 layers, reverse of creation): dial plans → route lists → route groups → translation patterns → trunks → call features → schedules/operating modes → virtual lines → devices → workspaces → users → locations.

**Known behaviors:**
- Virtual lines use raw API (not `wxcli virtual-extensions`) due to ID type mismatch bug
- Location deletion requires disabling calling first + 90s propagation wait
- Location delete may still 409 after wait — re-run cleanup to retry
- Call parks and call pickups are enumerated per-location (no org-wide list endpoint)
- Workspaces must be deleted before disable-calling can succeed — API has no location filter, client-side filtering by locationId

### Generator rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
- **Never create new hand-written command files.** 3 legacy hand-written files remain (`locations.py`, `numbers.py`, `licenses.py`) — these are a known drift risk that miss generator improvements. `users.py` was retired and replaced with an alias to the generated `people` command group. All new commands must go through the generator. If a generated command needs custom behavior, use `field_overrides.yaml`.
- **`auto_inject_from_config`** — `field_overrides.yaml` supports an `auto_inject_from_config: ["orgId"]` key per endpoint. Parameters listed here are omitted from `--help` and injected automatically from the saved config at runtime. This replaces the older `omit_query_params` approach for `orgId`.
- **Spec files:** 5 OpenAPI 3.0 specs in `specs/` (`webex-cloud-calling.json`, `webex-admin.json`, `webex-device.json`, `webex-messaging.json`, `webex-wholesale.json`)
- Regenerate one tag: `PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-cloud-calling.json --tag "Tag Name"`
- Regenerate one spec (all tags): `PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all`
- Regenerate all specs:
  ```
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-admin.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-device.json --all
  PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-messaging.json --all
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
- **OpenAPI 3.0 specs** — `specs/webex-cloud-calling.json` (calling), `specs/webex-admin.json` (admin), `specs/webex-device.json` (devices), `specs/webex-messaging.json` (messaging)
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
