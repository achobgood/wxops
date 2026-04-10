# Device API Gap Audit: OpenAPI Specs vs CUCM Migration Pipeline

**Date:** 2026-04-10
**Scope:** webex-device.json + webex-cloud-calling.json device paths vs `src/wxcli/migration/`
**Focus:** Write/mutate endpoints relevant to CUCM migration. Read-only inventory/analytics endpoints excluded.

## Methodology

1. Extracted all device-related paths from `specs/webex-device.json` (87 endpoints) and device paths from `specs/webex-cloud-calling.json` (65+ device endpoints, substantial overlap with device spec).
2. Read all 31 handlers in `handlers.py` HANDLER_REGISTRY, all 4 device-related mappers (`device_mapper.py`, `device_layout_mapper.py`, `softkey_mapper.py`, `button_template_mapper.py`), and the planner expanders.
3. Cross-referenced each write/mutate endpoint against handler URLs and mapper outputs.

## Summary

**Currently handled:** 12 device-related API calls across 6 handler functions.
**Gaps identified:** 24 migration-relevant endpoint groups with no pipeline coverage.
**Not migration-relevant (excluded):** ~40 read-only query, analytics, and inventory endpoints.

---

## Device Creation & Registration

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /devices` (by MAC) | Create device by MAC address, assign to person/workspace | YES | YES | -- | `handle_device_create` uses this. Sends `mac`, `model`, `personId`/`workspaceId`. |
| `POST /devices/activationCode` | Generate activation code for person or workspace | NO | YES | **P1 (HIGH)** | Critical for firmware-convertible phones (8845/8851/8865). After factory reset + MPP firmware load, phone registers via activation code. Comment in `__init__.py` mentions it but handler only does MAC-based POST /devices. |
| `POST /telephony/config/devices/actions/validateMacs/invoke` | Validate a list of MAC addresses before provisioning | NO | YES | **P2 (MEDIUM)** | Pre-flight check: validate MACs are real Cisco MACs and not already claimed. Would prevent provisioning failures. |
| `DELETE /devices/{deviceId}` | Delete a device | NO | YES (teardown) | P3 (LOW) | Handled by `wxcli cleanup` but not by the migration pipeline. Migration creates, doesn't delete. |
| `PATCH /devices/{deviceId}` | Modify device tags | NO | NO | -- | Tags are Webex-native metadata, not sourced from CUCM. |

## Device Settings (Static)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `GET /telephony/config/devices/{deviceId}/settings` | Get device settings | NO (read) | Reference only | -- | Read-only. |
| `PUT /telephony/config/devices/{deviceId}/settings` | Update device settings (static: customLineLabel, SIP transport, etc.) | YES | YES | -- | `handle_device_configure_settings` at tier 5. |
| `GET /telephony/config/devices/settings` | Read org-wide device override settings | NO (read) | Reference only | -- | Read-only. |
| `GET /telephony/config/locations/{locationId}/devices/settings` | Get location-level device settings | NO (read) | Reference only | -- | Read-only. |
| `GET /telephony/config/people/{personId}/devices/settings` | Get person-level device settings | NO (read) | Reference only | -- | Read-only. |
| `PUT /telephony/config/people/{personId}/devices/settings` | Update person-level device settings (line label display, etc.) | NO | YES | **P2 (MEDIUM)** | CUCM has per-user device profile settings (line text label, softkey, etc.). Could carry over user-specific device prefs. |
| `PUT /telephony/config/people/{personId}/devices/settings/hoteling` | Modify hoteling settings for person's primary devices | NO | YES | **P2 (MEDIUM)** | CUCM Extension Mobility maps to Webex hoteling. Workspace mapper sets `hotdeskingStatus` on workspace create, but person-level hoteling host enable is not handled. |
| `GET /telephony/config/workspaces/{workspaceId}/devices/settings` | Get workspace-level device settings | NO (read) | Reference only | -- | Read-only. |
| `PUT /telephony/config/workspaces/{workspaceId}/devices/settings` | Update workspace-level device settings | NO | YES | **P3 (LOW)** | Workspace device settings (line label, etc.). Lower priority since workspace devices are typically simpler. |

## Device Settings (Dynamic / PhoneOS)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `PUT /telephony/config/devices/{deviceId}/dynamicSettings` | Update device dynamic settings (PhoneOS config: wallpaper, ringtone, softkey layout, etc.) | YES | YES | -- | `handle_softkey_config_configure` uses this for PSK settings on 9800/8875. |
| `GET /telephony/config/devices/dynamicSettings/settingsGroups` | Get available settings groups for dynamic config | NO (read) | Reference only | -- | Schema discovery. |
| `GET /telephony/config/devices/dynamicSettings/validationSchema` | Get validation schema for dynamic settings | NO (read) | Reference only | -- | Schema discovery. |
| `POST /telephony/config/lists/devices/{deviceId}/dynamicSettings/actions/getSettings/invoke` | Get device dynamic settings (current values) | NO (read) | Reference only | -- | Read-only. |
| `POST /telephony/config/lists/devices/dynamicSettings/actions/getSettings/invoke` | Get customer-level device dynamic settings | NO (read) | Reference only | -- | Read-only. |
| `POST /telephony/config/lists/locations/{locationId}/devices/dynamicSettings/actions/getSettings/invoke` | Get location-level device dynamic settings | NO (read) | Reference only | -- | Read-only. |

## Device Members & Layout

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `PUT /telephony/config/devices/{deviceId}/members` | Update line members on a device (shared line appearances) | YES | YES | -- | `handle_device_layout_configure` call 1: sets members before layout. |
| `GET /telephony/config/devices/{deviceId}/members` | Get device members | NO (read) | Reference only | -- | Read-only. |
| `PUT /telephony/config/devices/{deviceId}/layout` | Set device layout (line key assignments) | YES | YES | -- | `handle_device_layout_configure` call 2: sets layout after members. |
| `GET /telephony/config/devices/{deviceId}/layout` | Get device layout | NO (read) | Reference only | -- | Read-only. |
| `GET /telephony/config/devices/{deviceId}/availableMembers` | Search available members for a device | NO (read) | Reference only | -- | Discovery helper. |
| `GET /telephony/config/devices/availableMembers/count` | Count available members | NO (read) | Reference only | -- | Discovery helper. |

## Device Actions

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/devices/{deviceId}/actions/applyChanges/invoke` | Apply pending changes to a specific device | YES | YES | -- | Used as call 3 in `handle_device_layout_configure` and call 2 in `handle_softkey_config_configure`. |
| `POST /telephony/config/devices/{deviceId}/actions/backgroundImageUpload/invoke` | Upload a custom background image to device | NO | YES | **P3 (LOW)** | CUCM allows per-phone background images. Only relevant for 9800-series with custom wallpapers. Niche migration scenario. |

## Line Key Templates

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/devices/lineKeyTemplates` | Create a line key template | YES | YES | -- | `handle_line_key_template_create` — full coverage with model remapping, KEM overflow, SPEED_DIAL sanitization. |
| `GET /telephony/config/devices/lineKeyTemplates` | List line key templates | NO (read) | Reference only | -- | Read-only. |
| `GET /telephony/config/devices/lineKeyTemplates/{templateId}` | Get template details | NO (read) | Reference only | -- | Read-only. |
| `PUT /telephony/config/devices/lineKeyTemplates/{templateId}` | Modify a line key template | NO | YES | **P3 (LOW)** | Pipeline creates templates but never updates them. Could be needed for idempotent re-runs if template already exists (409 recovery). |
| `DELETE /telephony/config/devices/lineKeyTemplates/{templateId}` | Delete a line key template | NO | NO | -- | Teardown only. |
| `POST /telephony/config/devices/actions/previewApplyLineKeyTemplate/invoke` | Preview what applying a LKT would change | NO | YES | **P3 (LOW)** | Dry-run preview before bulk apply. Useful for preflight validation but not blocking. |

## Line Key Template Jobs (Bulk Apply)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/jobs/devices/applyLineKeyTemplate` | Bulk-apply a line key template to multiple devices | NO | YES | **P1 (HIGH)** | Currently the pipeline creates LKTs but has NO mechanism to apply them to devices. The per-device `handle_device_layout_configure` sets layout manually, but for environments with 50+ phones on the same template, the bulk job API is far more efficient and is the intended Webex workflow. |
| `GET /telephony/config/jobs/devices/applyLineKeyTemplate` | List apply-LKT jobs | NO | YES (status) | P3 (LOW) | Job status polling for the above. |
| `GET /telephony/config/jobs/devices/applyLineKeyTemplate/{jobId}` | Get job status | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/applyLineKeyTemplate/{jobId}/errors` | Get job errors | NO | YES (status) | P3 (LOW) | Error diagnosis for the above. |

## Device Settings Jobs (Bulk)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/jobs/devices/callDeviceSettings` | Bulk change device settings across org/location | NO | YES | **P2 (MEDIUM)** | Mass-apply device settings (SIP transport, line label display, etc.) to all devices in a location. More efficient than per-device PUTs for large migrations. |
| `GET /telephony/config/jobs/devices/callDeviceSettings` | List change-device-settings jobs | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/callDeviceSettings/{jobId}` | Get job status | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/callDeviceSettings/{jobId}/errors` | List job errors | NO | YES (status) | P3 (LOW) | Error diagnosis. |

## Dynamic Device Settings Jobs (Bulk)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/jobs/devices/dynamicDeviceSettings` | Bulk update dynamic settings across org/location | NO | YES | **P2 (MEDIUM)** | Mass-apply PSK / wallpaper / ringtone settings. Currently `handle_softkey_config_configure` does per-device PUTs; this bulk API could replace 100+ individual calls with one job. |
| `GET /telephony/config/jobs/devices/dynamicDeviceSettings` | List dynamic-settings jobs | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/dynamicDeviceSettings/{jobId}` | Get job status | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/dynamicDeviceSettings/{jobId}/errors` | List job errors | NO | YES (status) | P3 (LOW) | Error diagnosis. |

## Rebuild Phones Jobs

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/jobs/devices/rebuildPhones` | Rebuild phone configuration (re-sync from cloud) | NO | YES | **P2 (MEDIUM)** | After bulk migration, some phones may need a config rebuild to pick up all changes. This is the API equivalent of "Reset/Restart" in CUCM. Useful as a post-migration verification step. |
| `GET /telephony/config/jobs/devices/rebuildPhones` | List rebuild jobs | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/rebuildPhones/{jobId}` | Get job status | NO | YES (status) | P3 (LOW) | Job status polling. |
| `GET /telephony/config/jobs/devices/rebuildPhones/{jobId}/errors` | Get job errors | NO | YES (status) | P3 (LOW) | Error diagnosis. |

## DECT Networks (Full Stack)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /telephony/config/locations/{loc}/dectNetworks` | Create a DECT network | NO | YES | **P1 (HIGH)** | CUCM DECT environments (792x handsets) require full DECT network provisioning on Webex side. No extractor, normalizer, mapper, or handler exists. Complete gap. |
| `PUT /telephony/config/locations/{loc}/dectNetworks/{id}` | Update DECT network | NO | YES | P3 (LOW) | Modification. |
| `DELETE /telephony/config/locations/{loc}/dectNetworks/{id}` | Delete DECT network | NO | NO | -- | Teardown only. |
| `POST /telephony/config/locations/{loc}/dectNetworks/{id}/baseStations` | Create multiple base stations | NO | YES | **P1 (HIGH)** | Base stations must be provisioned for DECT handsets to register. |
| `POST /telephony/config/locations/{loc}/dectNetworks/{id}/handsets` | Add a handset to DECT network | NO | YES | **P1 (HIGH)** | Individual handset provisioning. |
| `POST /telephony/config/locations/{loc}/dectNetworks/{id}/handsets/bulk` | Bulk-add handsets | NO | YES | **P1 (HIGH)** | Bulk handset provisioning — preferred for migration. |
| `PUT /telephony/config/locations/{loc}/dectNetworks/{id}/handsets/{hid}` | Update handset (assign user/line) | NO | YES | **P2 (MEDIUM)** | Configure handset line assignment after creation. |
| `GET /telephony/config/devices/dectNetworks/supportedDevices` | List supported DECT device types | NO | YES (preflight) | P3 (LOW) | Useful for validating CUCM DECT models map to Webex-supported types. |

## Background Images

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `GET /telephony/config/devices/backgroundImages` | List available background images | NO (read) | Reference only | -- | Read-only. |
| `DELETE /telephony/config/devices/backgroundImages` | Delete device background images | NO | NO | -- | Cleanup only. |
| `POST /telephony/config/devices/{deviceId}/actions/backgroundImageUpload/invoke` | Upload background image to specific device | NO | YES | **P3 (LOW)** | CUCM background image migration. Very niche — most migrations don't preserve custom wallpapers. |

## Supported Devices

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `GET /telephony/config/supportedDevices` | List all Webex-supported device models | NO | YES (preflight) | **P2 (MEDIUM)** | The `classify_phone_model()` function in `cross_reference.py` uses a hardcoded model table. This API could validate that table against live Webex data. Would improve preflight accuracy when Cisco adds new supported models. |

## Third-Party Device Update

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `PUT /telephony/config/devices/{deviceId}` | Update third-party device (SIP URI, proxy, etc.) | NO | YES | **P2 (MEDIUM)** | CUCM third-party SIP phones (Polycom, Yealink, etc.) may need SIP config after initial creation. `handle_device_create` creates the device but doesn't configure third-party SIP parameters. |

## RoomOS / Device Platform (webex-device.json only)

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `PATCH /deviceConfigurations` | Update RoomOS device configurations | NO | YES | **P3 (LOW)** | RoomOS video devices migrating from CUCM (Room Kit, Board, Desk) may need config push. Not typical for calling-focused CUCM migrations. |
| `POST /workspaces/{id}/personalize` | Personalize a workspace (user-to-workspace binding) | NO | YES | **P3 (LOW)** | Maps to CUCM Extension Mobility "login" behavior on RoomOS devices. Niche use case for shared-room video devices. |
| `POST /xapi/command/{commandName}` | Execute xAPI command on RoomOS device | NO | NO | -- | Real-time device control, not provisioning. |
| `GET /xapi/status` | Query RoomOS device status | NO | NO | -- | Real-time status, not provisioning. |

## Workspace Device Operations

| API Endpoint | What It Does | Currently Handled? | Migration Relevant? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `POST /workspaces` | Create workspace | YES | YES | -- | `handle_workspace_create` — full coverage. |
| `PUT /workspaces/{id}` | Update workspace | YES | YES | -- | `handle_workspace_assign_number` uses this for DID assignment. |
| `PUT /telephony/config/workspaces/{workspaceId}/devices` | Modify workspace devices (add/remove devices from workspace) | NO | YES | **P2 (MEDIUM)** | After creating workspace + device separately, this API binds them. Currently `handle_device_create` sets `workspaceId` at creation time, but if device pre-exists or needs reassignment, this endpoint is needed. |

---

## Priority Summary

### P1 — HIGH (Functional gaps that block common migration scenarios)

1. **Activation Code generation** (`POST /devices/activationCode`) — Required for firmware-convertible phones. The handler comment mentions it but only does MAC-based creation. Phones undergoing Enterprise-to-MPP conversion need activation codes.
2. **DECT Network provisioning** (create network + base stations + handsets) — Complete gap. No extractor, normalizer, mapper, or handler. Any CUCM environment with 792x DECT handsets cannot be migrated.
3. **Bulk Apply Line Key Template job** (`POST /telephony/config/jobs/devices/applyLineKeyTemplate`) — LKTs are created but never applied to devices via the bulk API. The per-device layout handler works but doesn't scale for large deployments and doesn't use the LKT association mechanism.

### P2 — MEDIUM (Efficiency/completeness improvements)

4. **MAC validation** (`POST .../validateMacs/invoke`) — Preflight check to catch invalid/claimed MACs before provisioning failures.
5. **Person-level device settings** (`PUT .../people/{id}/devices/settings`) — CUCM per-user device profile settings.
6. **Person hoteling enable** (`PUT .../people/{id}/devices/settings/hoteling`) — CUCM Extension Mobility host-side enable.
7. **Bulk device settings job** (`POST .../jobs/devices/callDeviceSettings`) — More efficient than per-device PUTs for large migrations.
8. **Bulk dynamic settings job** (`POST .../jobs/devices/dynamicDeviceSettings`) — More efficient than per-device PSK PUTs.
9. **Rebuild phones job** (`POST .../jobs/devices/rebuildPhones`) — Post-migration config rebuild/re-sync.
10. **Supported devices list** (`GET .../supportedDevices`) — Dynamic model validation for preflight.
11. **Third-party device config** (`PUT .../devices/{deviceId}` telephony config) — SIP parameters for non-Cisco phones.
12. **Workspace device binding** (`PUT .../workspaces/{id}/devices`) — Device-to-workspace reassignment.
13. **DECT handset update** (`PUT .../handsets/{id}`) — Line assignment on DECT handsets after creation.

### P3 — LOW (Nice-to-have, niche scenarios)

14. Line key template update (PUT) — Idempotent re-run support.
15. Preview apply LKT — Dry-run validation.
16. Background image upload — Custom wallpaper migration.
17. Workspace device settings update — Workspace-level device prefs.
18. RoomOS device configurations (PATCH /deviceConfigurations) — Video device config push.
19. Workspace personalization — Extension Mobility on RoomOS.
20. All job status/error polling endpoints — Required companions to their POST counterparts.

---

## Recommendations

**Immediate (before next live migration):**
- Add `handle_device_create_activation_code` handler variant that calls `POST /devices/activationCode` when `compatibility_tier == CONVERTIBLE` and no MAC is available. Wire into `_expand_device` with conditional routing.
- Add `handle_rebuild_phones` as a post-execution finalization step — one job per location after all device operations complete.

**Next tier of work:**
- Build DECT pipeline end-to-end: extractor (AXL `listDectNetwork` / `getDectBase` if available, or manual CSV import), normalizer, mapper, handlers for network + base station + handset creation.
- Add bulk job handlers for LKT apply, device settings, and dynamic settings. These replace N individual API calls with 1 job + polling, significantly reducing execution time for 100+ device migrations.
- Add MAC validation to `preflight/checks.py` — call `validateMacs/invoke` with all discovered MACs.

**Low priority / as-needed:**
- Third-party SIP device configuration (depends on whether customer has Polycom/Yealink in CUCM).
- Background image migration (very rarely requested).
- RoomOS device configuration (only for video-heavy CUCM environments).
