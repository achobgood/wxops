# Report + Advisory + KB Wiring for Uncovered Features

**Date:** 2026-04-12
**Scope:** Wire 7 gaps into the assessment report, advisory system, and CCIE advisor knowledge base.

## Gap Inventory

| # | Feature | Needs Report Section | Needs Advisory Pattern | Needs KB Routing |
|---|---------|---------------------|----------------------|-----------------|
| 1 | Device Settings Templates | YES — appendix section showing which phone settings migrate vs require manual config | No | No |
| 2 | Feature Forwarding + Night Service | YES — appendix section showing AA/HG/CQ with unconfigured overflow/after-hours routing | YES — flag features with CUCM forwarding that won't migrate | YES — kb-feature-mapping.md |
| 3 | Workspace Call Settings | YES — appendix section showing common-area phones with unconfigured settings | YES — flag workspaces losing call settings | No |
| 4 | DECT (KB only) | Already exists (Section X) | Already exists (detect_dect_deployment) | YES — add to migration-advisor.md routing table → kb-device-migration.md |
| 5 | Route Lists (KB only) | No — internal routing | Already exists (detect_route_list_complexity) | YES — add to migration-advisor.md routing table → kb-trunk-pstn.md |

## Changes Per File

### 1. `src/wxcli/migration/report/appendix.py` — 3 new sections

**Section AC: Device Settings Coverage**
- Read all `device` objects from store, group by model
- For each model family, show: settings the pipeline configures (line keys, PSK, layout) vs settings that need manual Control Hub config (wallpaper, Wi-Fi, Bluetooth, network)
- Summary: "{N} phone models, {M} settings automated, {K} require manual configuration"
- Table: Model | Automated Settings | Manual Settings | Phone Count

**Section AD: Feature Forwarding Status**
- Read `hunt_group`, `call_queue`, `auto_attendant` objects from store
- For each, check if forwarding/overflow config exists in pre_migration_state
- Flag features that have CUCM forwarding configured but no Webex forwarding handler
- Summary: "{N} features with unconfigured forwarding/overflow routing"
- Table: Feature Name | Type | Has CUCM Forwarding? | Webex Forwarding Configured? | Gap

**Section AE: Workspace Settings Coverage**
- Read `workspace` objects from store
- For each, check if `call_settings` dict is populated
- Count workspaces with no configured settings vs those with settings
- Summary: "{N} workspaces, {M} with default settings (unconfigured)"
- Table: Workspace Name | Location | License Tier | Settings Configured?

### 2. `src/wxcli/migration/advisory/advisory_patterns.py` — 2 new patterns

**Pattern 31: detect_feature_forwarding_gaps**
- Read hunt_group, call_queue, auto_attendant objects
- For each, check pre_migration_state for forwarding destinations (forwardHuntNoAnswer, queueFullDestination, etc.)
- If CUCM has forwarding configured but the canonical object has no forwarding fields → gap
- Severity: MEDIUM (features work but overflow/after-hours behavior is wrong)
- Category: rebuild
- Summary: "{N} call features have forwarding/overflow rules in CUCM that won't migrate automatically"

**Pattern 32: detect_workspace_settings_gaps**
- Read workspace objects
- Count workspaces with empty call_settings
- Cross-ref with pre_migration_state to see if CUCM had settings configured
- Severity: LOW (workspaces usually have defaults)
- Category: migrate_as_is
- Summary: "{N} workspaces will use default call settings — review if custom settings were configured in CUCM"

### 3. `.claude/agents/migration-advisor.md` — 2 new KB routing entries

Add to the `By advisory pattern_name` routing table:
- `dect_deployment` → `kb-device-migration.md`
- `route_list_complexity` → `kb-trunk-pstn.md`

### 4. `docs/knowledge-base/migration/kb-device-migration.md` — DECT section

Add a section `## DECT Migration` covering:
- CUCM DECT registers as regular phones; Webex DECT uses network→base station→handset hierarchy
- No 1:1 AXL mapping exists — requires supplemental inventory
- Phase 1 detection is advisory-only; Phase 2 provisioning requires operator input
- Dissent trigger: DT-DEVICE-010 — when DECT count > 20% of phone inventory, flag as HIGH (operator may underestimate DECT migration effort)

### 5. `docs/knowledge-base/migration/kb-trunk-pstn.md` — Route List section

Add a section `## Route Lists` covering:
- Webex HAS route list CRUD (contrary to prior assumption)
- CUCM multi-member route lists need FEATURE_APPROXIMATION decision (Webex route lists bind to one route group)
- Dissent trigger: DT-TRUNK-008 — when route list has 3+ route groups, static "use first" heuristic may pick wrong primary; advisor should recommend manual review

## Test Strategy

- Report sections: verify they render with the existing `populated_store` fixture
- Advisory patterns: 3-4 tests each (positive detection, empty store, no-gap case)
- KB routing: verify advisor.md routing table syntax (grep test)

## Agent Assignment

| Agent | Files | Description |
|-------|-------|-------------|
| A | appendix.py | Add sections AC, AD, AE |
| B | advisory_patterns.py | Add patterns 31-32 + register in ALL_ADVISORY_PATTERNS |
| C | migration-advisor.md + kb-device-migration.md | DECT KB routing + section |
| D | migration-advisor.md + kb-trunk-pstn.md | Route list KB routing + section |

Note: Agents C and D both touch migration-advisor.md but in different table rows — no conflict.
