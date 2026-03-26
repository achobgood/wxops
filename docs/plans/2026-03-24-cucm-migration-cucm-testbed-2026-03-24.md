# Deployment Plan: CUCM Migration — cucm-testbed-2026-03-24

Created: 2026-03-24
Agent: wxc-calling-builder

---

## 1. Objective

Migrate 10 users, 11 devices, 5 workspaces, 19 call features from CUCM to Webex Calling (project: cucm-testbed-2026-03-24).
2 locations, 3 trunks as routing infrastructure.

## 2. Prerequisites

| # | Prerequisite | Verification Method | Status |
|---|---|---|---|
| 1 | Webex org accessible | `wxcli whoami` | [ ] |
| 2 | Calling licenses available (10 Professional) | `wxcli licenses list` | [ ] |
| 3 | Number inventory for 2 location(s) | `wxcli numbers list --location-id ...` | [ ] |
| 4 | All decisions resolved (0 pending) | `wxcli cucm decisions --status pending` | [x] |

**Blockers found:** None

## 3. Resource Summary

| Resource Type | Count | Action |
|--------------|-------|--------|
| Device | 11 | Create |
| Person | 10 | Create |
| Call Park | 9 | Create |
| Pickup Group | 6 | Create |
| Workspace | 5 | Create |
| Shared Line | 4 | Create |
| Schedule | 3 | Create |
| Trunk | 3 | Create |
| Auto Attendant | 2 | Create |
| Hunt Group | 2 | Create |
| Location | 2 | Create |
| Route Group | 2 | Create |
| Translation Pattern | 2 | Create |
| Calling Permission | 1 | Create |

## 4. Decisions Made

No decisions were required for this migration.

## 5. Batch Execution Order

| Tier | Batch | Operations | Resource Types |
|------|-------|------------|----------------|
| 0 | org-wide | 4 | Location |
| 1 | org-wide | 8 | Schedule, Route Group, Trunk |
| 2 | location:DP-Branch-Phones | 1 | Person |
| 2 | location:fd9b9990ac1b | 3 | Person |
| 4 | location:fd9b9990ac1b | 2 | Hunt Group |
| 4 | org-wide | 6 | Auto Attendant, Pickup Group |
| 5 | org-wide | 1 | Calling Permission |

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Users added | 10 new Webex Calling users |
| Workspaces added | 5 new workspaces |
| Devices provisioned | 11 devices |
| Licenses consumed | 15 Webex Calling Professional (10 user + 5 workspace) |
| Locations created | 2 new locations |
| Total operations | 25 |
| Estimated API calls | 28 calls (~1 min at 100 req/min) |

## 7. Rollback Strategy

Execution is tracked per-operation in the migration database. Rollback deletes created resources in reverse dependency order. Use `wxcli cucm rollback` to initiate.

## 8. Approval

Review the plan above. The migration skill will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
