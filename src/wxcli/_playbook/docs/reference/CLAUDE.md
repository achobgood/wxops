# docs/reference — Webex API Reference Docs

Webex API reference docs grounded in the Webex OpenAPI specs and live API behavior. Each doc covers wxcli CLI examples and raw HTTP fallback. These docs serve the CLI, the playbook agent, and the CUCM migration tool's mapper/executor designs.

## Doc Families

- **Person call settings** (5): `person-call-settings-{handling,media,permissions,behavior}.md`, `self-service-call-settings.md`
- **Location calling** (3): `location-calling-core.md`, `location-calling-media.md`, `location-recording-advanced.md`
- **Devices** (4): `devices-{core,dect,workspaces,platform}.md`
- **Admin** (7): `admin-{org-management,identity-scim,licensing,audit-security,hybrid,partner,apps-data}.md`
- **Meetings** (4): `meetings-{core,content,settings,infrastructure}.md`
- **Messaging** (2): `messaging-{spaces,bots}.md`
- **Contact Center** (4): `contact-center-{core,routing,analytics,journey}.md`
- **Standalone** (10): `authentication.md`, `provisioning.md`, `call-features-major.md`, `call-features-additional.md`, `call-routing.md`, `call-control.md`, `webhooks-events.md`, `reporting-analytics.md`, `virtual-lines.md`, `emergency-services.md`

## Consumers

- **Mapper design** (pipeline doc 03b) — field-level CUCM-to-Webex mappings
- **Executor design** (pipeline doc 05b) — API call sequences and error handling
- **Build sessions** — implementation reference for CLI and agent work

## Maintenance

Update these docs when you discover new gotchas, API behavior changes, or scope/permission corrections. See the Sync Protocol in the project root `CLAUDE.md` for the full workflow.
