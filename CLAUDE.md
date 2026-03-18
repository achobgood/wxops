# Webex Calling Playbook

Build and configure any aspect of Webex Calling programmatically with guided Claude Code assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → `wxcadm` (XSI/E911/CP-API) → raw HTTP (fallback).
The wxcli CLI has 62 command groups covering 1000+ commands. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

## Quick Start

Run `/wxc-calling-builder` to start building. The agent walks you through authentication, interviews you about what you want to build, designs a deployment plan, executes via `wxcli` commands, and verifies the results.

## If Debugging

Run `/wxc-calling-debug` to troubleshoot a failing configuration.

## File Map

### Agent & Skills

| Path | Purpose |
|------|---------|
| `.claude/agents/wxc-calling-builder.md` | Main builder agent — drives the full workflow |
| `.claude/skills/provision-calling/` | Skill: provision users, locations, licenses |
| `.claude/skills/configure-features/` | Skill: set up call features (AA, CQ, HG, etc.) |
| `.claude/skills/manage-call-settings/` | Skill: configure person/workspace call settings |
| `.claude/skills/wxc-calling-debug/` | Skill: debug failing configurations |

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
| `docs/reference/location-call-settings-core.md` | Location enablement, internal dialing, voicemail policies, voice portal |
| `docs/reference/location-call-settings-media.md` | Announcements, playlists, schedules, access codes |
| `docs/reference/location-call-settings-advanced.md` | Call recording, caller reputation, conference, supervisor, operating modes |
| `docs/reference/call-routing.md` | Dial plans, trunks, route groups, route lists, translation patterns, PSTN |
| `docs/reference/devices-core.md` | Device CRUD, activation, device configurations, telephony devices |
| `docs/reference/devices-dect.md` | DECT networks, base stations, handsets, hotdesking |
| `docs/reference/devices-workspaces.md` | Workspaces, workspace settings, workspace locations |
| `docs/reference/call-control.md` | Real-time call control (dial, answer, hold, transfer, park, recording) |
| `docs/reference/webhooks-events.md` | Telephony call webhooks, event types, payloads |
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

### CLI (wxcli) — Primary Execution Layer

| Path | Purpose |
|------|---------|
| `src/wxcli/main.py` | CLI entry point — 62 registered command groups |
| `src/wxcli/commands/*.py` | All command implementations (raw HTTP pattern) |
| `wxcli --help` | Shows all command groups |
| `wxcli <group> --help` | Shows commands within a group |
| `wxcli <group> <command> --help` | Shows options for a command |

### Tools

| Path | Purpose |
|------|---------|
| `tools/postman_parser.py` | Parses Postman collection for endpoint discovery |
| `tools/field_overrides.yaml` | Required fields and defaults for tricky endpoints (read-only, CLI session owns) |
| `tools/generate_commands.py` | Auto-generates CLI commands from Postman collection (read-only) |

## CLI Status & Known Issues

**62 registered command groups, 1000+ commands.** All generated from Postman collection via `tools/generate_commands.py`.

### Test status (as of 2026-03-18)

- **v0.1.0** (14 commands): Fully live-tested, 3 bugs fixed.
- **v2** (55 commands): Fully live-tested, 10 bugs fixed. Schedules, AA, HG, CQ, call-park, call-pickup, paging, voicemail-groups, operating-modes.
- **v3 original 17 groups** (382 commands): All live-tested, 43 response key bugs fixed via `field_overrides.yaml`.
- **v3 extended 31 groups** (~600 commands): Registered but NOT yet live-tested.

### Known issues

1. **~30 singleton-as-list misclassifications.** The generator's `derive_command_type` classifies flat-object GETs as `list` when they should be `settings-get`. Affected groups: emergency-services (12), location-call-handling (4), location-voicemail (3), call-recording (2), announcements (2), PSTN (1), workspaces (1), device-settings (4). These commands output `[]` in table mode but **work correctly with `-o json`**.
2. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". Don't use `wxcli call-controls` with admin/service-app tokens.
3. **Complex nested settings need `--json-body`.** The generator skips object/array body fields. For call forwarding, voicemail, monitoring, and similar nested settings, use `--json-body '{"key": {...}}'`.

### Generator rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
- Regenerate: `PYTHONPATH=. python3.11 tools/generate_commands.py --folder "Folder Name"`
- Regenerate all: `PYTHONPATH=. python3.11 tools/generate_commands.py --all`
- Reinstall after regen: `pip3.11 install -e . -q`

### Templates, Examples & Plans

| Path | Purpose |
|------|---------|
| `docs/templates/deployment-plan.md` | Template: what the agent produces before executing |
| `docs/templates/execution-report.md` | Template: what the agent produces after executing |
| `docs/examples/user-provisioning/` | Working example from Cisco Live lab |
| `docs/plans/` | Generated design docs (one per customer build) |
| `docs/later/` | Parked: messaging, meetings, bots/webhooks (post-calling) |

## Reference Doc Sources

All reference docs are grounded in actual source code and official documentation:

- **wxc_sdk v1.30.0** (github.com/jeokrohn/wxc_sdk) — cloned at `../wxc_sdk_reference/`
- **wxcadm v4.6.1** (github.com/kctrey/wxcadm) — cloned at `../wxcadm_reference/`
- **Postman collection** (`../postman-webex-collections/webex_cloud_calling.json`) — 22.5MB, 1,079 endpoints, 59 folders
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
   - Person settings: `docs/reference/person-call-settings-*.md` (4 files: handling, media, permissions, behavior)
   - Location settings: `docs/reference/location-call-settings-*.md` (3 files: core, media, advanced)
   - Devices: `docs/reference/devices-*.md` (3 files: core, dect, workspaces)
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
