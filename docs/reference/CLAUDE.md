# docs/reference — Webex API Reference Docs

44 reference docs grounded in wxc_sdk (v1.30.0), wxcadm (v4.6.1), and 7 OpenAPI 3.0 specs. Each doc covers SDK method signatures, wxcli CLI examples, and raw HTTP fallback. These docs serve the CLI, the playbook agent, and the CUCM migration tool's mapper/executor designs.

## Doc Families

- **Person call settings** (5): `person-call-settings-{handling,media,permissions,behavior}.md`, `self-service-call-settings.md`
- **Location call settings** (3): `location-call-settings-{core,media,advanced}.md`
- **Devices** (4): `devices-{core,dect,workspaces,platform}.md`
- **wxcadm** (8): `wxcadm-{core,person,locations,features,devices-workspaces,xsi-realtime,routing,advanced}.md`
- **Admin** (7): `admin-{org-management,identity-scim,licensing,audit-security,hybrid,partner,apps-data}.md`
- **Meetings** (4): `meetings-{core,content,settings,infrastructure}.md`
- **Messaging** (2): `messaging-{spaces,bots}.md`
- **Standalone** (11): `authentication.md`, `provisioning.md`, `wxc-sdk-patterns.md`, `call-features-major.md`, `call-features-additional.md`, `call-routing.md`, `call-control.md`, `webhooks-events.md`, `reporting-analytics.md`, `virtual-lines.md`, `emergency-services.md`

## Consumers

- **Mapper design** (pipeline doc 03b) — field-level CUCM-to-Webex mappings
- **Executor design** (pipeline doc 05b) — API call sequences and error handling
- **Build sessions** — implementation reference for CLI and agent work

## Verification Status

All unverified markers have been resolved (0 remaining). 38 items carry `<!-- Verified via CLI implementation -->` comments across 9 files (3 new entries added 2026-03-23 for partner multi-org orgId support).

## Maintenance

Update these docs when you discover new gotchas, API behavior changes, or scope/permission corrections. See the Sync Protocol in the project root `CLAUDE.md` for the full workflow.
