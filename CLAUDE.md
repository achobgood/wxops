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
| `.claude/skills/device-platform/` | Skill: manage RoomOS device configs, workspace personalization, xAPI |
| `.claude/skills/call-control/` | Skill: real-time call control, webhooks, XSI |
| `.claude/skills/reporting/` | Skill: CDR, queue stats, call quality, reports |
| `.claude/skills/wxc-calling-debug/` | Skill: debug failing configurations |
| `.claude/skills/manage-identity/` | Skill: SCIM sync, directory, groups, contacts, domains |
| `.claude/skills/audit-compliance/` | Skill: audit events, security, compliance, authorizations |
| `.claude/skills/manage-licensing/` | Skill: license audit, assignment, reclamation |
| `.claude/skills/messaging-spaces/` | Skill: manage spaces, teams, memberships, ECM, HDS |
| `.claude/skills/messaging-bots/` | Skill: build bots, adaptive cards, webhooks, cross-domain integrations |

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

### Known issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Commands with nested fields now show an example JSON snippet in `--help` output (e.g., `wxcli user-settings update-call-forwarding --help`).
3. **my-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The CLI now detects this error and prints a tip.
4. **6 person settings are user-only (no admin path).** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` only exist at `/telephony/config/people/me/settings/{feature}`. Admin tokens get 404. Use user-level OAuth for these. See `docs/reference/self-service-call-settings.md` for the full 138-endpoint /people/me/ surface.
5. **Two path families for person settings.** Classic settings use `/people/{personId}/features/{feature}`. Newer settings use `/telephony/config/people/{personId}/{feature}`. Some names differ between families: `intercept` (not `callIntercept`), `reception` (not `receptionist`), `applications` (not `applicationServicesSettings`), `autoTransferNumbers` (not `transferNumbers`), `pushToTalk` (not `pushToTalkSettings`).
6. **Workspace `/telephony/config/` settings require Professional license.** Most workspace call settings under `/telephony/config/workspaces/{id}/` return 405 "Invalid Professional Place" for Basic-licensed workspaces. Only `musicOnHold` and `doNotDisturb` work on Basic. The `/workspaces/{id}/features/` path family (callForwarding, callWaiting, callerId, intercept, monitoring) works on Basic. The CLI now detects this error and prints a tip.
7. **Settings endpoints now support table output.** Settings-get commands (show-*) now accept `-o table` and auto-detect columns from the response data. List commands with non-standard response shapes (no `id`/`name` fields) also auto-detect columns.

### Generator rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
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
