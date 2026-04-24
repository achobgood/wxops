# wxcli Generator & Dev Tooling

This file contains developer/maintainer reference for the wxcli generator pipeline, Postman sync, test status, and doc maintenance protocols. It is intentionally kept out of the root CLAUDE.md to avoid loading into the builder agent's context on every launch.

## Tools

| Path | Purpose |
|------|---------|
| `tools/postman_parser.py` | Shared dataclasses (`Endpoint`, `EndpointField`) and utilities for the generator pipeline |
| `tools/openapi_parser.py` | Parses OpenAPI 3.0 spec into `Endpoint` objects |
| `tools/command_renderer.py` | Renders `Endpoint` objects into Click command files |
| `tools/field_overrides.yaml` | Table columns, display config, and endpoint overrides |
| `tools/generate_commands.py` | Orchestrates OpenAPI parse → render → write pipeline |
| `tools/postman_spec_diff.py` | Offline Postman↔spec gap diff — compares exported collection JSON against local OpenAPI spec |

## Postman↔Spec Sync

Periodic gap reports live in `docs/reports/postman-spec-sync-YYYY-MM-DD.md`. Run the prompt at
`docs/prompts/postman-sync-periodic-report.md` to generate a new one via Postman MCP.

Offline alternative (no MCP needed — export the Postman collection first):
```
python3.14 tools/postman_spec_diff.py \
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

## CLI Test Status

173 command groups, all generated from OpenAPI specs. Calling/admin/device/messaging groups live-tested across 4 batch sweeps (2026-03-19 through 2026-03-21). Contact center and meetings groups are newly generated and not yet live-tested. CUCM pipeline tested against live test bed (10.201.123.107) with 2 test bed expansions. See git history for detailed test logs.

## Generator Rules

- **Never hand-edit generated files.** Fix bugs by updating `tools/field_overrides.yaml` and regenerating.
- **Never create new hand-written command files** unless adding functionality that the generator cannot produce (e.g., multi-step workflows, file downloads). 3 legacy hand-written files remain (`locations.py`, `numbers.py`, `licenses.py`) — these are a known drift risk that miss generator improvements. `users.py` was retired and replaced with an alias to the generated `people` command group. `converged_recordings_export.py` is a deliberate hand-written extension that registers `download` and `export` commands onto the generated `converged_recordings` group via a `register(app)` pattern. For simple CRUD commands, use the generator. If a generated command needs custom behavior, use `field_overrides.yaml`.
- **`auto_inject_from_config`** — `field_overrides.yaml` supports an `auto_inject_from_config: ["orgId"]` key per endpoint. Parameters listed here are omitted from `--help` and injected automatically from the saved config at runtime. This replaces the older `omit_query_params` approach for `orgId`.
- **Spec files:** 9 OpenAPI 3.0 specs in `specs/` — 7 active (`webex-cloud-calling.json`, `webex-admin.json`, `webex-device.json`, `webex-messaging.json`, `webex-meetings.json`, `webex-contact-center.json`, `webex-ucm.json`) + 2 out-of-scope (`webex-broadworks.json`, `webex-wholesale.json`)
- **Pull updated specs:** `python3.14 tools/update-specs.py` — downloads latest from GitHub, reports diffs. BroadWorks and Wholesale are excluded.
- **Tag collision:** CC spec has "Data Sources" and "Meeting Site" tags that collide with admin/meetings specs. The CC versions are registered as `cc-data-sources` and `cc-site`. Always regenerate admin and meetings specs AFTER contact center to restore the correct `data_sources.py` and `meeting_site.py`.
- Regenerate one tag: `PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --tag "Tag Name"`
- Regenerate one spec (all tags): `PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all`
- Regenerate all specs (order matters — CC before admin/meetings):
  ```
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-device.json --all
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-messaging.json --all
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-ucm.json --all
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-contact-center.json --all
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-admin.json --all
  PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-meetings.json --all
  ```
- **CC response data key:** CC v2 list endpoints return `{"data": [...]}` not `{"items": [...]}`. The renderer adds a `"data"` fallback automatically. If adding a new CC list endpoint manually, use `result.get("items", result.get("data", ...))` for extraction.
- Reinstall after regen: `pip3.14 install -e . -q`

## Known Issues — Generator / Pipeline Only

These were removed from root CLAUDE.md (not needed by the builder agent at runtime):

10. **CUCM CallPickupGroup creation with members fails on CUCM 15.0.** Create empty, then assign via `updateLine`. See `src/wxcli/migration/CLAUDE.md` known issues.
15. **Device settings templates are pipeline-only, not named Webex objects.** The migration pipeline generates "templates" for device settings, but Webex has no named template API object for device settings. Settings are applied directly at org, location, or device level via PUT.
16. **CC spec has duplicate operationIds across paths.** 31 operationIds in `specs/webex-contact-center.json` are reused across different resource paths (e.g., `getConfig_22` on both `/business-hours/{id}` and `/cad-variable/{id}`). The parser deduplicates on `(operationId, path)` to handle this. If regenerating CC commands with `--all`, verify the total is 414 commands — fewer means the dedup regressed.
17. **CC "Site" tag collides with Meetings "Site" tag.** Both specs have a tag named "Site" but for different resources. The `cli_name_overrides` maps "Site" to `meeting-site`, so `cc_site.py` must be maintained separately from the `--all` regen. The `--all` flag generates `meeting_site.py` for this tag.

## Templates, Examples & Plans

| Path | Purpose |
|------|---------|
| `docs/templates/deployment-plan.md` | Template: what the agent produces before executing |
| `docs/templates/execution-report.md` | Template: what the agent produces after executing |
| `docs/plans/` | Generated design docs (one per customer build) |

## Agent Teams

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
   - Location settings: `docs/reference/location-calling-core.md`, `location-calling-media.md`, `location-recording-advanced.md`
   - Devices: `docs/reference/devices-*.md` (4 files: core, dect, workspaces, platform)
   - Routing: `docs/reference/call-routing.md`
   - Auth: `docs/reference/authentication.md`
   - SDK patterns: `docs/reference/wxc-sdk-patterns.md`

2. **If the reference doc is wrong or incomplete**, update it:
   - Fix incorrect method signatures, scopes, or data models
   - Add the gotcha to the doc's Gotchas section (create one if missing)

3. **If the reference doc is right**, move on — no action needed.

4. **If there's no reference doc for what you found**, add it to the closest doc's Gotchas section with a note about which command surfaced it.
