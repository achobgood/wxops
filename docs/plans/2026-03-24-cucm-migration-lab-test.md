# Deployment Plan: CUCM Migration — lab-test

Created: 2026-03-24
Agent: wxc-calling-builder

---

## 1. Objective

Migrate 10 users, 9 devices, 3 workspaces, 34 call features from CUCM to Webex Calling (project: lab-test).
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
| Call Park | 24 | Create |
| Person | 10 | Create |
| Device | 9 | Create |
| Pickup Group | 7 | Create |
| Shared Line | 4 | Create |
| Translation Pattern | 3 | Create |
| Trunk | 3 | Create |
| Workspace | 3 | Create |
| Hunt Group | 2 | Create |
| Location | 2 | Create |
| Schedule | 2 | Create |
| Route Group | 2 | Create |
| Auto Attendant | 1 | Create |
| Calling Permission | 1 | Create |

## 4. Decisions Made

| ID | Type | Summary | Chosen Option |
|---|------|---------|---------------|
| D0038 | WORKSPACE_LICENSE_TIER | Workspace 'AN0011223344080' needs license tier assignment (no feature indicators detected) | Professional Workspace |
| D0033 | DEVICE_FIRMWARE_CONVERTIBLE | Device Cisco 7841 (SEPBBCCDDEE1122) can be converted to MPP firmware | Upgrade firmware to MPP |
| D0046 | MISSING_DATA | device 'device:SEPBBCCDDEE1122' missing required fields: owner_canonical_id | Skip this object |
| D0032 | DEVICE_FIRMWARE_CONVERTIBLE | Device Cisco 8845 (SEP112233445566) can be converted to MPP firmware | Upgrade firmware to MPP |
| D0039 | WORKSPACE_LICENSE_TIER | Workspace 'Lobby Phone - Building A' needs license tier assignment (no feature indicators detected) | Professional Workspace |
| D0036 | DEVICE_INCOMPATIBLE | Device Cisco Unified Client Services Framework (CSFjsmith) is incompatible with Webex Calling | Skip device |
| D0034 | DEVICE_FIRMWARE_CONVERTIBLE | Device Cisco 8845 (SEPAABBCCDDEEFF) can be converted to MPP firmware | Upgrade firmware to MPP |
| D0050 | MISSING_DATA | location 'location:fd9b9990ac1b' missing required fields: address.address1, address.city, address.postal_code, address.state | Skip this object |
| D0051 | MISSING_DATA | location 'location:DP-Branch-Phones' missing required fields: address.address1, address.city, address.postal_code, address.state | Skip this object |
| D0030 | DEVICE_INCOMPATIBLE | Device Cisco ATA 191 (ATA001144778888) is incompatible with Webex Calling | Skip device |
| D0041 | MISSING_DATA | device 'device:SEP001122334455' missing required fields: owner_canonical_id | Skip this object |
| D0044 | MISSING_DATA | device 'device:SEP74A2E69EE6D0' missing required fields: owner_canonical_id | Skip this object |
| D0048 | MISSING_DATA | device 'device:CSFjdoe' missing required fields: mac, owner_canonical_id | Skip this object |
| D0031 | DEVICE_FIRMWARE_CONVERTIBLE | Device Cisco 8851 (SEP74A2E69EE6D0) can be converted to MPP firmware | Upgrade firmware to MPP |
| D0042 | MISSING_DATA | device 'device:AN0011223344080' missing required fields: mac, owner_canonical_id | Skip this object |
| D0043 | MISSING_DATA | device 'device:ATA001144778888' missing required fields: mac, owner_canonical_id | Skip this object |
| D0045 | MISSING_DATA | device 'device:SEP112233445566' missing required fields: owner_canonical_id | Skip this object |
| D0049 | MISSING_DATA | device 'device:CSFjsmith' missing required fields: mac, owner_canonical_id | Skip this object |
| D0040 | WORKSPACE_LICENSE_TIER | Workspace 'SEP112233445566' needs license tier assignment (no feature indicators detected) | Professional Workspace |
| D0052 | MISSING_DATA | translation_pattern 'translation_pattern:e3b0c44298fc' missing required fields: matching_pattern, name | Skip this object |
| D0029 | DEVICE_INCOMPATIBLE | Device Analog Phone (AN0011223344080) is incompatible with Webex Calling | Skip device |
| D0035 | DEVICE_INCOMPATIBLE | Device Cisco Unified Client Services Framework (CSFjdoe) is incompatible with Webex Calling | Skip device |
| D0047 | MISSING_DATA | device 'device:SEPAABBCCDDEEFF' missing required fields: owner_canonical_id | Skip this object |
| D0028 | DEVICE_FIRMWARE_CONVERTIBLE | Device Cisco 8845 (SEP001122334455) can be converted to MPP firmware | Upgrade firmware to MPP |
| D0037 | LOCATION_AMBIGUOUS | Location 'DP-HQ-Phones' has ambiguous device pool mapping: Location consolidates 3 device pools: DP-HQ-Phones, DP-HQ-Softphones, DP-CommonArea | first |

## 5. Batch Execution Order

| Tier | Batch | Operations | Resource Types |
|------|-------|------------|----------------|
| 1 | org-wide | 7 | Schedule, Route Group, Trunk |
| 2 | location:DP-Branch-Phones | 1 | Person |
| 2 | location:fd9b9990ac1b | 3 | Person |
| 4 | location:fd9b9990ac1b | 2 | Hunt Group |
| 4 | org-wide | 7 | Auto Attendant, Pickup Group |
| 5 | org-wide | 1 | Calling Permission |

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Users added | 10 new Webex Calling users |
| Workspaces added | 3 new workspaces |
| Devices provisioned | 9 devices |
| Licenses consumed | 13 Webex Calling Professional (10 user + 3 workspace) |
| Locations created | 2 new locations |
| Total operations | 21 |
| Estimated API calls | 24 calls (~1 min at 100 req/min) |

## 7. Rollback Strategy

Execution is tracked per-operation in the migration database. Rollback deletes created resources in reverse dependency order. Use `wxcli cucm rollback` to initiate.

## 8. Approval

Review the plan above. The migration skill will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
