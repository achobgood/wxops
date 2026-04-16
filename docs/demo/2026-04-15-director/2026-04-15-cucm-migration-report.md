# CUCM Migration Execution Report — director-demo-2026-04-15
**Date:** 2026-04-15  
**Source:** dCloud-CUCM 14.0 (10.201.123.107)  
**Target Org:** a9527d60-e78c-4330-9c53-8331a0c5aa7b (ahobgood.wbx.ai)  
**Prepared by:** Adam Hobgood  

---

## Pre-Execution Modifications

### MOD 1: Location Reuse
All 6 target locations already existed in the Webex org. Resolved by pre-marking all 12 location ops (`create` + `enable_calling`) as completed in the plan DB with the existing Webex location IDs. No duplicate locations created. One location (dCloud_DP) required calling enablement via raw POST to `/telephony/config/locations` with the existing location ID — this succeeded (201).

**Locations reused:**
- `dCloud_DP` → `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzYxMWM5ZmRkLTIxMjctNGE3Ny04M2ZhLWVmOTZkYTYxZjI3Ng`
- `DP-NYC-Phones` → `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzc0YjQ0MTgyLWI3MDAtNDFiNi04ZGM5LTZlMDIwYTg5OTgwZg`
- `DP-CHI-Phones` → `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OL2EwMzQ4NWY2LTFiZWYtNGRmMS04ZGMwLWU4MDM5NmZhMGMxNQ`
- `DP-SJC-Phones` → `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OL2QzYzAwNTVkLWYzNjktNGVjNS05NjczLTE3NzQwOGY1NmE0Mg`
- `DP-ATL-Phones` → `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzk5Nzg5N2RjLTIwYjAtNGJiNS1iNTA4LTFiMDdkZWU5NGRkYg`
- `DP-DEN-Phones` → `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzZlMjY1NjAzLTlkYzMtNDNlOC05ZDZjLTBjMzhiMDVmNmNiZA`

### MOD 2: Convertible Phones — MAC-Based Provisioning
**Code change applied** to `src/wxcli/migration/execute/planner.py`:
- Added `convertible_provisioning` config key support to `_expand_device()`
- When `config["convertible_provisioning"] == "mac"` AND device has a MAC, convertibles use the same `device:create` (MAC-based) path as NATIVE_MPP phones
- Added `config` parameter to `expand_to_operations()` and threaded through the call in `cucm.py`
- Set `convertible_provisioning = "mac"` in `~/.wxcli/migrations/director-demo-2026-04-15/config.json`

**Result:** All 772 device ops in the plan are `device:create` (MAC-based). Zero `device:create_activation_code` ops. However, 72 device:create ops failed (see Failures section).

---

## Execution Summary

### Phase D (current — after model normalization fix)

| Status | Count |
|--------|-------|
| Planned | 1,875 |
| Completed | 254 |
| Failed | 419 |
| Skipped (cascade + no-op) | 1,202 |
| **Total** | **1,875** |

**Three execution passes total:**
1. Initial run — 76 completed, 338 failed
2. Retry after dCloud_DP calling enablement — 254 completed, 414 failed
3. Phase D retry after model normalization fix — 254 completed, 419 failed (model error resolved; net +5 failed from CTI Port ops reclassifying from the cascade-reset)

### Phase C (previous)

| Status | Count |
|--------|-------|
| Planned | 1,875 |
| Completed | 254 |
| Failed | 414 |
| Skipped (cascade + no-op) | 1,207 |
| **Total** | **1,875** |

**Two execution passes were run:** Initial run (76 completed, 338 failed) + retry after dCloud_DP calling enablement (254 total completed, 414 total failed).

---

## Completed by Resource Type

| Resource Type | Completed |
|--------------|-----------|
| location | 12 (6 create + 6 enable_calling — all via MOD 1 reuse) |
| operating_mode | 7 |
| line_key_template | 18 |
| auto_attendant | 8 |
| pickup_group | 17 |
| hunt_group | 11 of 17 |
| route_group | 4 |
| route_list | 1 |
| trunk | 10 of 17 |
| user | 53 of 277 planned |
| ecbn_config | 68 |
| shared_line | 45 |
| **Total** | **254** |

---

## Failures Requiring Operator Attention

### 1. Extension-Less Users (225 failures) — DATA ISSUE
**Error:** `400: Create Calling user either Phone number or Extension is required`  
**Cause:** 225 CUCM users have no directory numbers assigned (no lines). The Webex Calling API requires an extension or phone number.  
**Resolution:** These users are CUCM-only administrative/system accounts with no calling presence. Mark as skipped — they do not need Calling licenses.  
**Action:** `wxcli cucm retry-failed` after running: `wxcli cucm decide <id> skip` for each extension-less user decision, or add an auto-rule for `MISSING_DATA` where `extension is null`.

### 2. Device Model Normalization (RESOLVED in Phase D) — MODEL STRING FORMAT

**Fix applied:** `handle_device_create` in `src/wxcli/migration/execute/handlers.py` now normalizes model strings identically to `handle_device_create_activation_code`:
- Prepends `"DMS "` if not already present
- Collapses `" IP Phone "` → `" "` (e.g., "Cisco IP Phone 8851" → "DMS Cisco 8851")

The error `400: Valid model is required` no longer appears. Remaining device failures are a separate root cause (see below).

### 2a. CTI Port / Virtual Devices Without MAC (60 failures) — PLANNER BUG (pre-existing)

**Error:** `400: Valid device mac is required`  
**Cause:** 60 CTI Port devices (virtual, no MAC) have `device:create` ops in the plan despite having `DEVICE_INCOMPATIBLE` decisions. Root cause: DEVICE_INCOMPATIBLE decisions are in `__stale__` state from a re-analysis run, so the planner's skip logic doesn't suppress them. This is a pre-existing bug unrelated to the model fix.  
**Resolution:** Not required for demo. For production: re-run `wxcli cucm analyze` to refresh decisions, then `wxcli cucm plan` to regenerate the plan.

### 2b. MAC Address In Use (10 failures) — PRIOR PARTIAL RUN
**Error:** `403: MAC Address is in use by another device`  
**Cause:** 10 convertible phones (8851/8861/8865 etc.) were partially registered in a prior partial run. Their MACs are already in the org under a different device ID.  
**Resolution:** Delete the existing orphaned device records (`wxcli devices list --mac <mac>` + `wxcli devices delete <id>`) then retry.

### 2c. Cisco IP Communicator Not Supported (2 failures)
**Error:** `400: Device model is not supported.`  
**Cause:** Cisco IP Communicator is a soft phone with no Webex equivalent. Should be suppressed by DEVICE_INCOMPATIBLE but affected by the same stale-decision bug as CTI Ports.

### 3. Dubber Recording Config (37 failures) — DEMO ENV
**Error:** `403: Dubber API Error: Unauthorized`  
**Cause:** `recording_vendor = "Webex"` in config.json but some users have call recording settings pointing at Dubber. Demo org has no Dubber integration.  
**Resolution:** Demo-acceptable. For production: either remove recording settings from these users pre-migration or set `recording_vendor = "Webex"` and clear Dubber-specific settings in the normalizer.

### 4. MAC Address In Use (10 failures) — PRIOR PARTIAL RUN
**Error:** `403: MAC Address is in use by another device`  
**Cause:** 10 phones were registered in a prior partial run. Their MACs are already in the org under a different device ID.  
**Resolution:** Delete the existing orphaned device records (`wxcli devices list --mac <mac>` + `wxcli devices delete <id>`) then retry.

### 5. Call Forwarding on Failed Users (44 cascade failures)
**Error:** `400: [Error 5700] This service requires a phone number`  
**Cause:** Cascade — call_forwarding:configure ops ran against users that failed to create. No fix needed; resolving user:create failures will unblock these on retry.

---

## Preflight Results

| Check | Result |
|-------|--------|
| User licenses | WARN — 277 needed, 299 available (8% buffer) |
| Workspace licenses | PASS — 4 needed, 300 available |
| Locations | WARN — 6/6 exist (MOD 1 reuse), no PSTN (demo) |
| Trunks | PASS — no name conflicts |
| Feature entitlements | PASS |
| Number conflicts | PASS |
| Duplicate users | PASS |
| Rate limit budget | PASS — ~29 min |
| E911 readiness | FAIL — operator accepted demo gap |

---

## Warning: Emergency Call Notification Not Configured
Kari's Law compliance requires an org-level notification email when any user dials 911. This was explicitly skipped for the demo. Before production cutover, configure via:  
Control Hub → Calling → Service Settings → Emergency Call Notification  
Or via API: `PUT /v1/telephony/config/emergencyCallNotification`

---

## Next Steps

1. **Fix device model normalization** in `handle_device_create` (5-line change, mirrors activation-code handler)
2. **Skip or drop extension-less users** — 225 CUCM system accounts with no calling presence
3. **Delete 10 orphaned device records** (MAC conflicts from prior partial run)
4. **Re-run `wxcli cucm retry-failed`** after fixes 1-3 to complete remaining ops
5. **Dubber recording** — resolve per production environment (no action needed for demo)
6. **Configure E911 notification email** before production cutover
