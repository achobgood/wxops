# Cross-Spec Normalization — Execution Summary

**Date:** 2026-03-19
**Phase:** 2 (Fix)
**Findings report:** `docs/superpowers/specs/2026-03-19-cross-spec-audit-findings.md`

## Changes

- **Files modified:** 42
- **Files deleted:** 6 (`_review-*.md`)
- **P0 fixes applied:** 23 across 21 files (14 ref docs + 7 skills)
- **P1 fixes applied:** 26 across 19 files (5 ref docs + 3 skills + 11 files bundled with P0 wave)
- **P2 fixes applied:** 39 across 28 files (9 standalone + 19 bundled with P0/P1 waves)
- **wxcadm limited-scope fixes:** 4 files (Gotchas sections added)
- **Cleanup items resolved:** 6 files deleted, 0 stale cross-references

## Wave Summary

### Wave 1 — P0 Fixes (21 files)

**Skills (7):**
| Skill | Fixes |
|-------|-------|
| manage-call-settings | P0-4 scopes in Step 2, P1-3 9→8 steps, P1-6 plan gate |
| call-control | P0-4 scopes+verification, P1-3 7→8 steps, P1-6 plan gate |
| reporting | P0-4 scope verification gate, P1-3 9→8 steps (6a-6f), P1-6 plan gate |
| wxc-calling-debug | P0-4 scope verification, P1-3 5→8 steps, P1-4 Critical Rules added |
| audit-compliance | P0-4 expanded scopes, P1-3 10→8 steps, P1-6 plan gate |
| manage-licensing | P0-4 scopes moved to Step 2 with verification gate |
| messaging-bots | P0-4 scope verification, P1-3 9→8 steps, P1-6 plan gate |

**Reference Docs (14):**
| Doc | Fixes |
|-----|-------|
| provisioning.md | P0-1 Raw HTTP for Org API, P1-1 inline gotchas (21 distributed), P2-1 Sources |
| admin-identity-scim.md | P0-1 Raw HTTP for SCIM Groups/Schemas, P1-1 inline gotchas, P2-2 ToC |
| messaging-bots.md | P0-1 Raw HTTP (5 sections), P0-2 scopes table, P2-1 Sources, P2-4 cross-cutting gotchas |
| wxc-sdk-patterns.md | P0-2 Required Scopes table, P2-2 ToC, Sources extracted |
| person-call-settings-media.md | P0-2 scopes table, P0-3 CLI (12 sections), P2-1 Sources, P2-4 gotchas |
| reporting-analytics.md | P0-3 CLI Examples (6+ sections) |
| call-features-major.md | P0-3 CLI (AA/CQ/HG/Forwarding), P2-1 Sources, P2-4 gotchas |
| call-features-additional.md | P0-3 CLI (all 11 features), P2-1 Sources, P2-4 gotchas |
| person-call-settings-handling.md | P0-3 CLI (10 sections), P1-1 inline gotchas, P2-1 Sources, P2-4 gotchas |
| person-call-settings-permissions.md | P0-3 CLI (5 sections), P2-4 cross-cutting gotchas |
| person-call-settings-behavior.md | P0-3 CLI (7 sections), P1-1 inline gotchas (4 sections), P2-4 gotchas |
| location-call-settings-core.md | P0-3 CLI (16 subsections), P2-1 Sources |
| location-call-settings-advanced.md | P0-3 CLI (8 sections), P2-1 Sources, P2-4 gotchas |
| emergency-services.md | P0-3 CLI (4 sections), P2-2 ToC, P2-4 gotchas |

### Wave 2 — P1-Only Fixes (8 files)

| File | Fixes |
|------|-------|
| authentication.md | P1-1 inline gotchas (3 sections), P2-1 Sources, P2-4 cross-cutting gotchas |
| call-control.md | P1-1 inline gotchas (3 sections), P2-1 Sources, P2-2 ToC |
| devices-core.md | P1-1 inline gotchas elevated, P2-1 Sources, P2-2 ToC |
| admin-org-management.md | P1-1 gotchas distributed (9 inline, 1 cross-cutting), P2-2 ToC |
| admin-licensing.md | P1-1 gotchas distributed (4 inline, 4 cross-cutting), P2-2 ToC |
| configure-features/SKILL.md | P1-3 merged 9→8 steps, P1-6 plan gate at Step 5 |
| configure-routing/SKILL.md | P1-3 consolidated 12→8 steps |
| manage-devices/SKILL.md | P1-3 consolidated 14→8 steps, P1-6 plan gate moved to Step 5 |

### Wave 3 — P2-Only Fixes (9 files)

| File | Fix |
|------|-----|
| call-routing.md | P2-1 Sources |
| location-call-settings-media.md | P2-1 Sources |
| devices-dect.md | P2-1 Sources |
| devices-workspaces.md | P2-1 Sources |
| devices-platform.md | P2-1 Sources |
| webhooks-events.md | P2-1 Sources + P2-2 ToC |
| virtual-lines.md | P2-2 ToC |
| admin-apps-data.md | P2-2 ToC |
| messaging-spaces.md | P2-1 Sources + P2-4 cross-cutting Gotchas |

### Wave 4 — Cleanup

**wxcadm Gotchas added (4 files):**
- wxcadm-core.md — 6 gotchas (auth, XSI kwargs, read_only mode, legacy API calls)
- wxcadm-person.md — 6 gotchas (role_names bug, SNR bug, reverse lookups, recording round-trip)
- wxcadm-devices-workspaces.md — 6 gotchas (VirtualLine bugs, DECT access, workspace unassign)
- wxcadm-advanced.md — 6 gotchas (CPAPI, Service Apps, Bifrost, RedSky auth)

**Files deleted (6):**
- `docs/reference/_review-auth-provisioning-sdk.md`
- `docs/reference/_review-coverage-matrix.md`
- `docs/reference/_review-devices-control-other.md`
- `docs/reference/_review-features-routing.md`
- `docs/reference/_review-person-location-settings.md`
- `docs/reference/_review-wxcadm.md`

**Stale cross-references:** 0 found

### Post-Wave: Skill Format Gap Fixes (13 skills + wxc-calling-debug)

A post-Phase 2 recheck (`docs/superpowers/specs/2026-03-19-skill-format-gap-findings.md`) found heading format variations the Phase 1 audit missed. Applied 23 fixes:

| Issue | Count | Skills |
|-------|-------|--------|
| `## CRITICAL RULES` → `## Critical Rules` | 3 | provision-calling, manage-identity, manage-licensing |
| Plan gate missing `[brackets]` | 3 | provision-calling, manage-identity, manage-licensing |
| Plan gate backtick-wrapped | 9 | manage-call-settings, configure-routing, call-control, reporting, manage-devices, device-platform, messaging-spaces, messaging-bots, wxc-calling-debug |
| `## Context Compaction` → `## Context Compaction Recovery` | 8 | provision-calling, configure-features, configure-routing, manage-devices, device-platform, manage-identity, audit-compliance, manage-licensing |

**Verification:** All 3 dimensions grep-clean across all 14 skills after fixes.

## Fixes That Could Not Be Applied

None. All findings from both the main audit and the format gap recheck were addressed.

## Remaining Known Gaps

1. **messaging-spaces/SKILL.md structural issue:** Plan gate at Step 6 (not Step 5). Step 5 is "CLI command catalog" (reference material, should be in Step 4 or domain-specific section). Execute+Verify merged at Step 7 instead of separate Steps 6/7. Missed by both audit rounds.
2. **Reporting skill sub-step naming:** Uses `6a-i`, `6a-ii` style while all other skills use `6a`, `6b`. Minor inconsistency.

## Recommended Follow-Up

1. **NEEDS VERIFICATION backlog:** ~~~113 tags across 37 files remain.~~ Swept 2026-03-19: only 2 remain (bot calling scopes, messaging rate limits).
2. **messaging-spaces skill restructure:** Move CLI catalog to Step 4 sub-step or domain section, shift plan gate to Step 5, split Execute/Verify into Steps 6/7.
3. **Reporting skill sub-step naming:** Normalize `6a-i`/`6a-ii` to `6a`/`6b` style.
4. **CLAUDE.md file map:** No paths changed (no renames/moves), but the 6 deleted `_review-*.md` files were never in the file map, so no update needed.
