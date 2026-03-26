# Deployment Plan: CUCM Migration — test-project

Created: 2026-03-26
Agent: wxc-calling-builder

---

## 1. Objective

Migrate migration objects from CUCM to Webex Calling (project: test-project).
1 locations as routing infrastructure.

## 2. Prerequisites

| # | Prerequisite | Verification Method | Status |
|---|---|---|---|
| 1 | Webex org accessible | `wxcli whoami` | [ ] |
| 3 | Number inventory for 1 location(s) | `wxcli numbers list --location-id ...` | [ ] |
| 4 | All decisions resolved (0 pending) | `wxcli cucm decisions --status pending` | [x] |

**Blockers found:** None

## 3. Resource Summary

| Resource Type | Count | Action |
|--------------|-------|--------|
| Location | 1 | Create |

## 4. Decisions Made

No decisions were required for this migration.

## 5. Batch Execution Order

| Tier | Batch | Operations | Resource Types |
|------|-------|------------|----------------|
| 0 | org-wide | 1 | Location |

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Locations created | 1 new locations |
| Total operations | 1 |
| Estimated API calls | 1 calls (~1 min at 100 req/min) |

## 7. Rollback Strategy

Execution is tracked per-operation in the migration database. Rollback deletes created resources in reverse dependency order. Use `wxcli cucm rollback` to initiate.

## 8. Approval

Review the plan above. The migration skill will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
