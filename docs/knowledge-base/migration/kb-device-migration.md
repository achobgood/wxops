# Device Migration: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

## Decision Framework

### DEVICE_INCOMPATIBLE

**Source:** `recommendation_rules.py` `_DEVICE_REPLACEMENT_MAP` (28 keys, 26 unique models after ATA spacing normalization)

The pipeline looks up the CUCM model in a static replacement map and recommends `replace` with the target model. If the device has `button_count` or `has_sidecar`, the reasoning appends a sidecar/line-key-capacity warning.

#### Replacement Map

| CUCM Model | Recommended Replacement | Notes |
|------------|------------------------|-------|
| **79xx series** | | |
| 7811 | 9841 | Same desk form factor, single-screen. 9841 is RoomOS (device configuration templates, not telephony device settings). |
| 7821 | 9841 | 2-line phone. 9841 supports more lines, same price tier. RoomOS firmware. |
| 7832 | Conference room device | Conference phone. Consider Webex Room device for both calling and meetings. |
| 7905, 7906, 7911, 7912 | 8845 or 9851 | Legacy SCCP/SIP. 8845 = MPP firmware; 9851 = RoomOS (larger screen). Different day-2 config models. |
| 7940, 7941, 7942, 7945 | 8845 or 9851 | Same as above. |
| 7960, 7961, 7962, 7965 | 8845 or 9851 | Same as above. |
| 7970, 7971, 7975 | 8845 or 9851 | Same as above. |
| **69xx series** | | |
| 6901, 6911, 6921, 6941, 6945, 6961 | 8841 or 9841 | No Webex firmware. 8841 = MPP (same line count); 9841 = RoomOS. |
| **ATA** | | |
| ATA 190 / ATA190 | ATA 192 | Analog adapter. ATA 192 supports Webex Calling. |
| ATA 191 / ATA191 | ATA 192 | Analog adapter. ATA 192 supports Webex Calling. |

When the map returns `None` (unknown model), the rule returns `None` and the decision requires human input.

### DEVICE_FIRMWARE_CONVERTIBLE

**Source:** `recommendation_rules.py` `recommend_device_firmware_convertible()`

Always recommends `convert` (convert to native MPP firmware). If `has_srst` is true in context, appends a warning: "Survivable Gateway (SRST) is configured. Verify fallback behavior after conversion -- Webex devices use Webex Edge for survivability."

Key firmware distinction for replacements and conversions:
- **MPP firmware** (68xx, 78xx, 88xx): Configured via Telephony Device Settings API (`device-settings` CLI group). Requires `apply-changes` after updates. <!-- Source: devices-core.md §5a -->
- **RoomOS / PhoneOS** (9800-series, Room/Board/Desk): Configured via Device Configurations API (`device-configurations` CLI group). Uses RoomOS key-value pairs, JSON Patch updates, auto-applies on resync. <!-- Source: devices-core.md §5a -->
- **9800-series is the exception that breaks assumptions.** They are `productType: phone` but run PhoneOS (RoomOS-derived). Treating all phones as `device-settings` targets will fail on 9800-series. <!-- Source: devices-core.md line 1329 -->

### HOTDESK_DN_CONFLICT

**Source:** `recommendation_rules.py` `recommend_hotdesk_dn_conflict()`

Always recommends `keep_primary` -- keep the primary DN and configure Webex hoteling for secondary access. Webex hoteling allows any user to log into the device temporarily.

### AUDIO_ASSET_MANUAL

**Source:** `recommendation_rules.py` `recommend_audio_asset_manual()`

| Usage Context | Recommendation | Reasoning |
|--------------|----------------|-----------|
| `AA_GREETING` | `accept` | Customer-facing audio -- migrate manually |
| `QUEUE_COMFORT` | `accept` | Customer-facing audio -- migrate manually |
| `QUEUE_WHISPER` | `accept` | Customer-facing audio -- migrate manually |
| `MOH` with `location_count <= 2` | `use_default` | Low-usage MOH -- Webex default is sufficient |
| All other | `accept` | Custom audio should be migrated for brand consistency |

### BUTTON_UNMAPPABLE

**Source:** `recommendation_rules.py` `recommend_button_unmappable()`

Always recommends `accept_loss`. CUCM-specific phone button types that have no Webex line key equivalent:
- **Service URL** -- no Webex equivalent
- **Intercom** -- no Webex equivalent
- **Privacy** -- no Webex equivalent
- Other CUCM-specific button features

Webex Calling line key types are limited to: `PRIMARY_LINE`, `SHARED_LINE`, `MONITOR`, `CALL_PARK_EXTENSION`, `SPEED_DIAL`, `OPEN`, `CLOSED`, `MODE_MANAGEMENT`. <!-- Source: devices-core.md §3.2, LineKeyType enum -->

---

## Edge Cases & Exceptions

### 8845/8865 already on MPP firmware
These models support Webex Calling firmware natively. If already on MPP firmware but registered to CUCM, they are `DEVICE_FIRMWARE_CONVERTIBLE`, not `DEVICE_INCOMPATIBLE`. The conversion is a re-registration, not a hardware replacement.

### 9800-series phones (9811, 9821, 9841, 9851, 9861, 9871)
Native MPP (PhoneOS/RoomOS-derived). No conversion or replacement needed. These use the Device Configurations API (RoomOS keys), not Telephony Device Settings. <!-- Source: devices-core.md §5a, line 1323 -->

### DECT networks
A DECT network is a unit: base station(s) + handsets. Supported Webex DECT models: DBS110 (1 base, 30 lines), DBS210 (250 bases, 1000 lines). Migration requires creating the DECT network in Webex, registering base stations, then assigning handsets. Not supported for FedRAMP. <!-- Source: devices-dect.md §3 -->

### Conference room devices
7832/8832 conference phones map to either a Webex Room device (RoomOS, full meetings + calling) or a 9800-series desk phone depending on use case. RoomOS devices use the Device Configurations API and Workspace Personalization API. <!-- Source: devices-platform.md §1 -->

### Devices with >6 line appearances
Webex line key count depends on model. The `SupportedDevice` catalog includes `number_of_line_ports` and `number_of_line_key_buttons` per model, plus `kem_support_enabled`, `kem_module_count`, and `kem_module_type`. Query via `wxcli device-settings list-supported-devices --output json`. <!-- Source: devices-core.md §3.2 SupportedDevice model -->

### 8851 model classification
8851 is `CONVERTIBLE` (supports MPP firmware conversion to Webex Calling), not `INCOMPATIBLE`. The replacement map does not include 8851. <!-- Source: recommendation_rules.py _DEVICE_REPLACEMENT_MAP does not contain "8851"; CLAUDE.md mentions 8851 as CONVERTIBLE in Phase 12c -->

---

## Real-World Patterns

| Pattern | CUCM Device | Webex Target | License | Notes |
|---------|------------|-------------|---------|-------|
| Hallway phone | 7811/7821 | Workspace + 9841 | Webex Calling Basic | Common area, no user assignment. 9841 is RoomOS. |
| Executive suite | 8865 + 3 sidecars | 9871 + KEM modules | Professional | KEM types: `KEM_14_KEYS`, `KEM_18_KEYS`, `KEM_20_KEYS`. Max modules per model from `kem_module_count` in supported devices catalog. <!-- Source: devices-core.md §3.2 --> |
| Factory floor | 7925/7926 wireless | No direct equivalent | -- | CUCM wireless phones have no Webex hardware equivalent. Webex App on mobile is the nearest substitute. <!-- From training, needs verification --> |
| Conference room | 7832/8832 | Webex Room device or 9800 | Workspace | RoomOS device provides both calling and meetings capability. |
| ATA + fax | ATA 190/191 | ATA 192 | Workspace | ATA 192 supports T.38 fax on Webex Calling. `t38_enabled` field in supported devices catalog. <!-- Source: devices-core.md §3.2 --> |
| Extension Mobility user | Device profile (EM login) | Workspace + hot desking | Hot Desk license | Webex hot desking is simpler: user login/logout with primary line only, no device-profile switching. <!-- Source: advisory_patterns.py detect_extension_mobility_usage() --> |

---

## Webex Constraints

### Supported device models
Query the live catalog: `wxcli device-settings list-supported-devices --output json`. Each entry includes `model`, `displayName`, `familyDisplayName`, `numberOfLinePorts`, `kemSupportEnabled`, `kemModuleCount`, `kemModuleType`, `onboardingMethod`, and `deviceSettingsConfiguration`. <!-- Source: devices-core.md §3.2-3.3 -->

### Line key limits per model family
From `devices-core.md` model router table:
- MPP 68xx (6821, 6841, 6851, 6861)
- MPP 78xx (7811, 7821, 7832, 7841, 7861)
- MPP 88xx (8811, 8841, 8845, 8851, 8861, 8865)
- 9800-series (9811, 9821, 9841, 9851, 9861, 9871)

Exact line key counts are per-model in the `number_of_line_key_buttons` field of `SupportedDevice`. Line Key Templates (`LineKeyTemplate`) assign key types to each physical key position. <!-- Source: devices-core.md §3.2, §3.3 -->

### KEM/sidecar support by model
`SupportedDevice.kem_support_enabled` (bool), `kem_module_count` (max modules), `kem_module_type` (list of supported KEM types). KEM key types: `KEM_14_KEYS`, `KEM_18_KEYS`, `KEM_20_KEYS`. Each KEM key supports the same `LineKeyType` values as phone line keys. <!-- Source: devices-core.md §3.2 KemModuleType and KemKey -->

### Activation code provisioning flow
Two onboarding methods per the `SupportedDevice` model: `MAC_ADDRESS` and `ACTIVATION_CODE`. <!-- Source: devices-core.md §3.2 OnboardingMethod enum -->

Activation code flow:
1. Generate code via `wxcli devices create-activation-code --workspace-id WS_ID` (RoomOS, no model needed) or `--person-id PID --model "DMS Cisco 8845"` (phones, model required).
2. Code is returned with an expiry timestamp (`ActivationCodeResponse.code`, `.expiry_time`).
3. Enter code on physical device to register it to Webex.
4. For phones, `model` is required -- obtain valid model strings from `telephony.devices.supported_devices()`.
5. Adding a device to a workspace with calling type `none` or `thirdPartySipCalling` resets calling to `freeCalling`.
<!-- Source: devices-core.md §1.3 activation_code() method, §1.5 CLI examples -->

### MPP vs RoomOS config model differences
| Aspect | MPP (68xx/78xx/88xx) | RoomOS (9800/Room/Board/Desk) |
|--------|---------------------|-------------------------------|
| Config API | Telephony Device Settings | Device Configurations (key-value) |
| CLI group | `device-settings` | `device-configurations` |
| Update method | Fixed schema per model | JSON Patch on config keys |
| Apply changes | Required: `apply-changes-for DEVICE_ID` | Auto-applies on resync |
| Content-Type | `application/json` | `application/json-patch+json` |
| Key filtering | N/A (fixed schema) | Wildcard, range, absolute path |
| Scopes | `spark-admin:telephony_config_read/write` | `spark-admin:devices_read/write` |
<!-- Source: devices-core.md §5a, key differences table -->

### Hot desking license requirements
Webex hot desking uses a dedicated `hotdesk` license type (distinct from both Basic `workspace` and `professional`). When creating a hot desk workspace: `phone_number`, `extension`, `device_hosted_meetings`, and `calendar` are not applicable and will cause errors if provided. <!-- Source: devices-workspaces.md gotcha #6; wxcadm-devices-workspaces.md license_type="hotdesk" -->

Most `/telephony/config/workspaces/{id}/` settings require Professional license. Basic workspaces only support `musicOnHold` and `doNotDisturb` at that path. For Basic workspaces, use `/workspaces/{id}/features/` path family (callForwarding, callWaiting, callerId, intercept, monitoring). <!-- Source: devices-workspaces.md gotcha #10 -->

---

## Cross-Cutting Advisory Patterns

### Device Bulk Upgrade Planning (Pattern 4)
**Source:** `advisory_patterns.py` `detect_device_bulk_upgrade()`

Fires when 3+ devices share the same incompatible model. Groups `DEVICE_INCOMPATIBLE` decisions by `cucm_model` from decision context, produces `MEDIUM` severity advisory recommending volume pricing negotiation and streamlined deployment logistics. Category: `migrate_as_is`.

### Extension Mobility Usage (Pattern 20)
**Source:** `advisory_patterns.py` `detect_extension_mobility_usage()`

Fires when `info_device_profile` objects exist in the store. CUCM Extension Mobility lets users log into any EM-enabled phone and load personal line/speed-dial/services config. Webex maps this to hot desking -- simpler model: user login/logout with primary line only, no device-profile switching. Category: `rebuild`. Severity: `LOW`.

---

## Dissent Triggers

### DT-DEV-001: Firmware conversion recommended but device has SRST and site has unreliable WAN

- **Condition:** `DEVICE_FIRMWARE_CONVERTIBLE` recommends `convert` AND `has_srst=True` in context AND location has SRST-configured device pool
- **Why the static rule is insufficient:** `recommend_device_firmware_convertible()` mentions SRST in the reasoning text but always returns `convert` regardless. It does not weigh WAN reliability, SRST dependency depth, or whether the site has an alternative survivability path.
- **What the advisor should do:**
  1. Flag the SRST dependency explicitly
  2. Ask the admin about WAN reliability at this site
  3. If unreliable WAN: recommend Webex Local Survivability Gateway instead of bare conversion
  4. If reliable WAN: proceed with conversion but document SRST removal
- **Confidence:** MEDIUM -- SRST is a real production dependency that the static rule glosses over

### DT-DEV-002: Bulk upgrade grouped but models have different form factors

- **Condition:** `detect_device_bulk_upgrade()` groups 3+ devices of same incompatible model AND the replacement changes form factor (e.g., desk phone model replaced by conference device, or vice versa)
- **Why the static grouping is incorrect:** `detect_device_bulk_upgrade()` groups by source model only (`cucm_model`), not by deployment context or use case. A batch of 7811s might include hallway phones, reception desks, and conference-adjacent units -- all needing different replacements despite sharing the same CUCM model.
- **What the advisor should do:**
  1. Split bulk upgrade groups into sub-groups by deployment context (workspace type, owner presence, location type)
  2. Apply different replacement recommendations per sub-group
  3. Present the split to the admin for confirmation
- **Confidence:** LOW -- the grouping heuristic is useful for volume purchasing but masks deployment diversity

### DT-DEV-003: DECT network migration loses roaming topology
<!-- From training, needs verification -->

- **Condition:** CUCM DECT deployment has multi-cell roaming across base stations AND migration creates a new Webex DECT network
- **Why this matters:** CUCM DECT configurations may have complex roaming chains and handoff patterns between base stations. Webex DECT networks (DBS110: 1 base/30 lines, DBS210: 250 bases/1000 lines) support roaming natively but the specific base-station-to-handset assignments must be manually recreated.
- **What the advisor should do:**
  1. Inventory DECT base station count and handset assignments
  2. Verify the Webex DECT model supports the required base station count
  3. Plan physical base station deployment to match coverage zones
- **Confidence:** MEDIUM -- DECT topology is site-specific and the pipeline does not extract base station placement data

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | "42-model replacement map" in `recommend_device_incompatible()` | Partial | `recommendation_rules.py` lines 191-220 | Map has **28 keys** (26 unique models after normalizing ATA spacing variants: `ATA 190`/`ATA190`, `ATA 191`/`ATA191`). Not 42. The map covers 79xx (16 keys), 69xx (6 keys), 7832 (1 key), ATA (4 keys, 2 unique). |
| 2 | Activation code provisioning flow | Verified | `devices-core.md` §1.3, §1.5, §6 | `activation_code()` method documented with workspace/person/model params, `ActivationCodeResponse` model, CLI `create-activation-code` command, and Raw HTTP `POST /devices/activationCode`. |
| 3 | Hot desking requires Professional workspace license | Corrected | `devices-workspaces.md` gotcha #6, #10; `wxcadm-devices-workspaces.md` line 654 | Hot desking uses its own **`hotdesk` license type**, distinct from both Basic (`workspace`) and Professional. However, most `/telephony/config/workspaces/` settings DO require Professional. The claim as stated is imprecise -- hot desking requires a hot desk license, not specifically "Professional". |
