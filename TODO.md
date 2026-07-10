# Dev-Only Notes (NOT shipped)

Relocated from CLAUDE.md by the playbook-bundling split (spec 2026-07-09 §4.4).
The dev CLAUDE.md is byte-identical to the shipped one; dev-only content lives
here instead. This file is excluded from the customer bundle by
wxcli-dist/assemble.py and does NOT auto-load — read it when doing generator,
spec-sync, drift-gate, or architecture-docs work.

## Architecture Docs Rule

Relocated from the CLAUDE.md `## Architecture Docs Rule` section (was between Mandatory Grounding Rule and Execution Discipline).

**Before making non-trivial changes, read the relevant architecture doc in `docs/architecture/`.** See `docs/architecture/00-index.md` for the quick-reference table mapping tasks to docs. After making changes that affect the structural map, decisions, behavior, or operations, update the corresponding doc in the same session. Treat these docs as load-bearing — stale architecture docs produce wrong code.

## Architecture Docs (File Map table)

Relocated from the CLAUDE.md `### Architecture Docs` section (under `## File Map`).

**These docs are load-bearing.** Before making non-trivial changes, read the relevant architecture doc. After making changes that affect the structural map, decisions, behavior, or operations, update the corresponding doc. The session that makes the change owns the doc update.

| Path | Covers | Read before... |
|------|--------|----------------|
| `docs/architecture/00-index.md` | Index, quick-reference table, maintenance protocol | Any architecture doc work |
| `docs/architecture/01-structural-map.md` | Modules, data flows, abstractions, boundaries | Adding/removing modules, changing data flows |
| `docs/architecture/02-decisions.md` | 10 ADRs, cross-reference, open questions | Making or revisiting architectural decisions |
| `docs/architecture/03-behavior.md` | Failure modes, fragility, performance, state, known issues | Debugging, changing error handling, modifying state |
| `docs/architecture/04-operations-and-evolution.md` | Build, test, deploy, debug, tech debt, roadmap | Changing build/test infra, paying down debt |
| `docs/architecture/05-purpose.md` | Audience, success criteria, scope, constraints | Scope decisions, onboarding |

## Out-of-Skill-Scope Groups (declared)

Relocated from the CLAUDE.md `### Out-of-Skill-Scope Groups (declared)` section (under `## File Map`).

CLI groups intentionally not fronted by any skill — "unreferenced" here is a decision, not drift. The drift gate (`tools/drift_check.py` check 4) fails any group that is neither skill-referenced nor on this list. Claiming one is a product decision: add skill coverage, then remove it from this list.

- Partner/wholesale surfaces (403 for non-partner tokens): `broadworks-billing-reports`, `broadworks-enterprises`, `broadworks-subscribers`, `broadworks-workspaces`, `wholesale-provisioning`, `wholesale-billing-reports`, `partner-admins`, `partner-tags`
- Hybrid/infra: `hybrid-clusters`, `hybrid-connectors`, `data-sources`, `resource-groups`, `resource-group-memberships`, `workspace-locations`
- Admin long tail: `activation-email`, `archive-users`, `classifications`, `guest-management`, `identity-org`, `org-settings`, `roles`, `admin-recordings`
- Calling long tail (disambiguation rows exist above; skill teaching pending): `announcements`, `announcement-playlists`, `cq-playlists`, `emergency-services`, `virtual-line-settings`, `mode-management`, `hot-desking-members`, `caller-reputation`, `calling-service`, `client-settings`, `device-dynamic-settings`, `external-voicemail`, `location-call-handling`, `person-call-settings`, `ucm-profile`
- New at 2026-07-01 spec sync, unclaimed pending review: `cc-legacy-flows`, `meeting-slido`
- Dev-only (untracked): `fs-*`

## CLI (wxcli) — Primary Execution Layer (relocated table rows)

Relocated from the CLAUDE.md `### CLI (wxcli) — Primary Execution Layer` table. Only the three `--help` discovery rows stay in CLAUDE.md; the source-tree, spec, and tooling rows below moved here.

| Path | Purpose |
|------|---------|
| `src/wxcli/main.py` | CLI entry point — 178 command groups |
| `src/wxcli/commands/*.py` | All command implementations (raw HTTP pattern) |
| `specs/webex-cloud-calling.json` | OpenAPI 3.0 spec — calling APIs |
| `specs/webex-admin.json` | OpenAPI 3.0 spec — admin/org management APIs |
| `specs/webex-device.json` | OpenAPI 3.0 spec — device management APIs |
| `specs/webex-messaging.json` | OpenAPI 3.0 spec — messaging/rooms/teams APIs |
| `specs/webex-meetings.json` | OpenAPI 3.0 spec — meetings/video mesh/transcripts APIs |
| `specs/webex-contact-center.json` | OpenAPI 3.0 spec — contact center APIs |
| `specs/webex-ucm.json` | OpenAPI 3.0 spec — UCM calling profiles (1 op) |
| `specs/webex-broadworks.json` | OpenAPI 3.0 spec — BroadWorks partner APIs |
| `specs/webex-wholesale.json` | OpenAPI 3.0 spec — wholesale provisioning/billing APIs |
| `src/wxcli/commands/_registry.py` | Generator-emitted registration manifest (do not edit by hand) |
| `tools/spec_sync.py` | Atomic spec sync: update specs → regen all → manifest → drift gate |
| `tools/drift_check.py` | Coherence gate: spec↔CLI parity, skill refs, counts (report-only until S4.5) |
| `docs/arch/deliberate-gaps.md` | Generated list of spec ops deliberately without CLI (skip reasons) |
| `src/wxcli/commands/cleanup.py` | Batch cleanup: inventory + parallel layered deletion |
| `src/wxcli/commands/converged_recordings_export.py` | Hand-written download/export for converged recordings (registered into generated group) |

## Quick Start sentence (relocated)

Relocated from the CLAUDE.md `## Quick Start` section (the "To migrate from CUCM" paragraph). Deleted sentence:

See `src/wxcli/migration/CLAUDE.md` for the full file map and architecture.

## Migration (KB, Runbooks, Tool) — spec-template phrase (relocated)

Relocated from the CLAUDE.md `### Migration (KB, Runbooks, Tool, Spec Template)` section. The heading dropped "Spec Template" and the body list dropped this phrase:

spec template requirements

## Org Health Assessment — test count (relocated)

Relocated from the CLAUDE.md `### Org Health Assessment` section. Deleted phrase:

**76 tests passing.**

## CUCM→Webex Migration Tool — original body (relocated)

Relocated from the CLAUDE.md `### CUCM→Webex Migration Tool (All 11 phases complete)` section. The heading dropped "(All 11 phases complete)" and the body was replaced with a path-free sentence. Original heading and body:

### CUCM→Webex Migration Tool (All 11 phases complete)

The migration tool is at `src/wxcli/migration/` and wired into the CLI as `wxcli cucm <command>`. **2778 tests passing.** See `src/wxcli/migration/CLAUDE.md` for the full file map, architecture, and pipeline commands. Pipeline workflow, report generation, and advisory details are in `.claude/rules/cucm-migration.md`.

## CLI Status & Known Issues — generator sentences (relocated)

Relocated from the CLAUDE.md `## CLI Status & Known Issues` intro paragraph. The paragraph was rewritten to keep only the group-count sentence and the converged-recordings sentence (path-free). Original paragraph:

**178 command groups covering calling, admin, device, messaging, meetings, wholesale, and contact center APIs.** 171 generated modules from 9 tracked OpenAPI 3.0 specs via `tools/generate_commands.py`, registered through the generator-emitted `_registry.py` manifest; spec refresh + regen is one atomic operation (`tools/spec_sync.py`), checked by `tools/drift_check.py`. The `converged-recordings` group combines generated CRUD commands with hand-written `download` and `export` commands (`converged_recordings_export.py`).
