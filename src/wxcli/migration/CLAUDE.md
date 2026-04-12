# migration/ — CUCM→Webex Migration Tool

All 11 phases complete. **1642 tests passing.** Wired into the CLI as `wxcli cucm <command>`. Does NOT use the auto-generator.

## File Map

| Path | Purpose |
|------|---------|
| `docs/plans/cucm-migration-roadmap.md` | **Master roadmap** — what's done, what's ready, what's next. Start here. |
| `docs/plans/cucm-pipeline-architecture.md` | Pipeline architecture summary — SQLite store, two-pass ELT, linter-pattern analyzers, NetworkX DAG |
| `docs/plans/cucm-pipeline/01-07 + 03b` | 8 detailed architecture docs |
| `src/wxcli/commands/cucm.py` | Phases 08+10 — CLI: 16 commands (init, discover, normalize, map, analyze, plan, preflight, decisions, decide, export, inventory, status, config, user-diff, user-notice, report) |
| `src/wxcli/commands/cucm_config.py` | Phase 08 — Config management helpers |
| `models.py` | Canonical data models — 28 types, DecisionType (24 values), Decision, MapperResult, TransformResult |
| `store.py` | SQLite-backed store — objects, cross_refs, decisions, journal, merge_log, merge_decisions() |
| `cucm/` | Phase 03 — AXL connection, 9 extractors, discovery pipeline |
| `transform/normalizers.py` | Phase 04 — 41 Pass 1 normalizers |
| `transform/cross_reference.py` | Phase 04 — CrossReferenceBuilder (30 relationships + 3 enrichments) |
| `transform/pipeline.py` | Phase 04 — `normalize_discovery()` entry point |
| `transform/mappers/` | Phase 05 — 24 mappers + base.py (announcement, button_template, call_forwarding, call_settings, css, device, device_layout, device_profile, e911, ecbn, executive_assistant, feature, line, location, moh, monitoring, receptionist, routing, snr, softkey, user, voicemail, voicemail_group, workspace) |
| `transform/analyzers/` | Phase 06 — 13 analyzers (css_permission, css_routing, device_compatibility, dn_ambiguity, duplicate_user, extension_conflict, feature_approximation, layout_overflow, location_ambiguity, missing_data, shared_line, voicemail_compatibility, workspace_license) |
| `transform/analysis_pipeline.py` | Phase 06 — Orchestrator: run analyzers → merge → auto-rules + resolve_and_cascade() |
| `execute/` | Phase 07 — planner.py, dependency.py (NetworkX DAG), batch.py |
| `export/` | Phase 09 — deployment_plan.py, json/csv exports (command_builder.py removed in Phase 12b) |
| `preflight/` | Phase 10 — checks.py (9 preflight checks), runner.py (orchestrator), CLI `wxcli cucm preflight` |
| `advisory/` | Phase 13 — Advisory system: per-decision recommendations (19 rules) + cross-cutting advisor (30 patterns) |
| `report/` | Assessment report generator — complexity score, SVG charts, executive summary + appendix → HTML/PDF. See its CLAUDE.md. |
| `.claude/skills/cucm-migrate/SKILL.md` | Phase 11 — 6-step execution skill: preflight → plan summary → batch execute → delegate → report |

**Where the design spec and pipeline architecture docs conflict, the pipeline architecture docs are authoritative.**

Each subdirectory has its own CLAUDE.md (local context) and TODO.md (outstanding work).
See `docs/plans/cucm-migration-roadmap.md` for the master project status.

## Known Issues

1. **CUCM CallPickupGroup creation with members fails on CUCM 15.0.** The AXL `addCallPickupGroup` operation with `<members>` containing `<directoryNumber>` fails with a null priority foreign key constraint (`pickupgroupmember.priority`). Workaround: create the pickup group empty, then use `updateLine` with `callPickupGroupName` to assign members at the line level. Affects both wxcadm and raw AXL calls. <!-- Verified on CUCM 15.0.1.13901(2), 2026-03-24 -->

## Pipeline Commands

## Feature Forwarding / Holiday / Night Service Migration

The `FeatureMapper` extracts CUCM hunt pilot forwarding destinations
(`forwardHuntNoAnswer`, `forwardHuntBusy`) and queue overflow targets
(`queueCalls.queueFullDestination`, `queueCalls.maxWaitTimeDestination`,
`queueCalls.noAgentDestination`) onto the canonical hunt group / call queue
objects, and CTI Route Point `callForwardAll` onto the canonical auto attendant.
The planner emits 6 tier-5 `configure_*` ops (`hunt_group:configure_forwarding`,
`call_queue:configure_forwarding`, `call_queue:configure_holiday_service`,
`call_queue:configure_night_service`, `call_queue:configure_stranded_calls`,
`auto_attendant:configure_forwarding`) that PUT the new settings via per-feature
endpoints once the feature has been created. Empty / None data short-circuits
the planner so unaffected features produce no extra ops. Schedules referenced
by holiday or night service are resolved by name + level (LOCATION /
ORGANIZATION) — operating modes and location schedules are already created at
tier 1, so no additional dependency edges are needed. Spec at
`docs/superpowers/specs/2026-04-10-feature-forwarding-night-service.md`.

## Hoteling / Hot Desking Migration

The `DeviceProfileMapper` produces execution-ready hoteling data alongside the
existing `FEATURE_APPROXIMATION` decisions. For each CUCM Extension Mobility
device profile it sets `hoteling_guest_enabled=True` (when the user is resolved),
populates `location_canonical_id` (from device_pool → location cross-ref), and
creates a `hoteling_location:{loc_cid}` MigrationObject for each unique location
with EM phones. Three new execution handlers (`enable_hoteling_guest`,
`enable_hoteling_host`, `enable_hotdesking`) configure Webex hoteling guest,
device host, and location-level voice portal sign-in respectively. Advisory
pattern 20 (`detect_extension_mobility_usage`) escalates severity to MEDIUM when
profiles contain multi-line or BLF features that Webex hot desking cannot
replicate, and `recommend_feature_approximation` always recommends "accept" for
EM decisions (no alternative architecture exists). Spec at
`docs/superpowers/specs/2026-04-10-hoteling-migration.md`.

## Voicemail Groups Migration

Unity Connection shared/group mailboxes (department voicemail — sales@, support@,
billing@ — typically reachable via a hunt pilot) are extracted via a new
`UnityConnectionClient.extract_shared_mailboxes()` method and normalized into
`voicemail_group:{name}` MigrationObjects. `VoicemailGroupMapper` (tier 4,
depends on `location_mapper` + `feature_mapper`) resolves each mailbox's
location (user extension match first, then single-location fallback;
multi-location without match → `LOCATION_AMBIGUOUS`),
generates a placeholder passcode (`MISSING_DATA`), flags custom greetings
(`AUDIO_ASSET_MANUAL`), and detects extension conflicts (`EXTENSION_CONFLICT`).
The `handle_voicemail_group_create` handler POSTs to
`/telephony/config/locations/{id}/voicemailGroups`. Overflow linkage from
hunt groups / call queues back to the voicemail group (Phase C in the spec)
is NOT implemented — configure overflow manually post-migration. Spec at
`docs/superpowers/specs/2026-04-10-voicemail-groups.md`.

**To run a migration:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `decisions` → `plan` → `preflight` → `export` → then invoke `/cucm-migrate`.

**To generate an assessment report:** `wxcli cucm init` → `discover` (or `discover --from-file`) → `normalize` → `map` → `analyze` → `report --brand "..." --prepared-by "..."`. Does not require plan/preflight/export — the report reads directly from the post-analyze store.

**To generate a per-user diff:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `user-diff`. Does not require plan/preflight/export.

**To generate a user communication notice:** `wxcli cucm init` → `discover` → `normalize` → `map` → `analyze` → `user-notice --brand "..." --migration-date "..." --helpdesk "..."`. Does not require plan/preflight/export. Generates an email-ready notice covering detected scenarios.
