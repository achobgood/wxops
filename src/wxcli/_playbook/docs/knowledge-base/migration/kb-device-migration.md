# Device Migration: Migration Knowledge Base

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for device replacement, firmware conversion, and MPP-vs-PhoneOS decisions.
> **Reading mode:** Reference. Grep by `DT-DEV-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

## Decision Framework

### DEVICE_INCOMPATIBLE

**Source:** `recommendation_rules.py` `_DEVICE_REPLACEMENT_MAP` (28 keys, 26 unique models after ATA spacing normalization)

The pipeline looks up the CUCM model in a static replacement map and recommends `replace` with the target model. If the device has `button_count` or `has_sidecar`, the reasoning appends a sidecar/line-key-capacity warning.

#### Replacement Map

| CUCM Model | Recommended Replacement | Notes |
|------------|------------------------|-------|
| **79xx series** | | |
| 7811 | 9841 | Same desk form factor, single-screen. 9841 runs PhoneOS (device configuration templates, not telephony device settings). |
| 7821 | 9841 | 2-line phone. 9841 supports more lines, same price tier. PhoneOS firmware. |
| 7832 | Conference room device | Conference phone. Consider Webex Room device for both calling and meetings. |
| 7905, 7906, 7911, 7912 | 8845 or 9851 | Legacy SCCP/SIP. 8845 = MPP firmware; 9851 = PhoneOS (larger screen). Different day-2 config models. |
| 7940, 7941, 7942, 7945 | 8845 or 9851 | Same as above. |
| 7960, 7961, 7962, 7965 | 8845 or 9851 | Same as above. |
| 7970, 7971, 7975 | 8845 or 9851 | Same as above. |
| **69xx series** | | |
| 6901, 6911, 6921, 6941, 6945, 6961 | 8841 or 9841 | No Webex firmware. 8841 = MPP (same line count); 9841 = PhoneOS. |
| **ATA** | | |
| ATA 190 / ATA190 | ATA 192 | Analog adapter. ATA 192 supports Webex Calling. |
| ATA 191 / ATA191 | ATA 192 | Analog adapter. ATA 192 supports Webex Calling. |

When the map returns `None` (unknown model), the rule returns `None` and the decision requires human input.

### DEVICE_FIRMWARE_CONVERTIBLE (deprecated 2026-04-15)

Convertible phones no longer produce a decision. `DeviceMapper` classifies the model as `CONVERTIBLE` and the planner unconditionally emits a `create_activation_code` op — if a device is convertible, it converts. There is no operator choice and no skip path at the decision level; the recommendation rule and the `DecisionType` enum value are retained only for backward compatibility with project stores created before 2026-04-15. SRST-dependency concerns surface via the advisor narrative (see `dt-dev-001` below), not as a per-device decision.

Key firmware distinction for replacements and conversions:
- **MPP firmware** (68xx, 78xx, 88xx): Configured via Telephony Device Settings API (`device-settings` CLI group). Requires `apply-changes` after updates. <!-- Source: devices-core.md §5a -->
- **PhoneOS** (9800-series): Configured via Device Configurations API (`device-configurations` CLI group). Uses PhoneOS key-value pairs (e.g., `Phone.LineKeyLabel`, `Lines.Line[N].CallFeatureSettings.*`, `User.Screen.CustomWallpaper.CustomWallpaperDownloadURL[N]`), JSON Patch updates, auto-applies on resync. **PhoneOS is RoomOS-derived but distinct — do not call 9800-series devices "RoomOS devices".** <!-- Source: devices-core.md §5a -->
- **RoomOS** (Room/Board/Desk series): Same Device Configurations API surface, distinct schema (e.g., `Audio.Ultrasound.*`, `Conference.MaxReceiveCallRate`). <!-- Source: devices-core.md §5a -->
- **9800-series straddles both worlds.** They are `productType: phone` but run PhoneOS (not RoomOS). Device-level telephony settings (`GET /telephony/config/devices/{id}/settings`) returns 404 on 9800-series — treating all phones as `device-settings` targets will fail. However, 9800-series phones DO share some telephony infrastructure with MPP:
  - **Line Key Templates** — fully supported. Model string is `"Cisco 98xx"` (not `"DMS Cisco 98xx"` like MPP phones).
  - **Person-level device settings** — returns limited fields (e.g., compression). Not a full device-settings response.
  - **Device Configurations** (PhoneOS keys) — confirmed working for per-device config via JSON Patch.
  - **Device member management** — standard telephony device member APIs work normally.
  The key insight: 9800-series uses PhoneOS config keys for device configuration BUT participates in telephony features like line key templates and person-level settings. Migration code must not assume "PhoneOS = no telephony API surface", and must not conflate PhoneOS with RoomOS. <!-- Source: devices-core.md line 1329; devices-platform.md; live testing 2026-04-15 -->

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

### Webex per-user device limit: 5 (hard)

Webex Calling enforces a **maximum of 5 devices per user**, counting hardware phones (MPP/PhoneOS) and soft clients (Webex App desktop, mobile, tablet, browser) combined. The cap is server-enforced and has no org-level override.

- **Surfaces at execution time** as HTTP 400 from `POST /devices` or `POST /devices/activationCode` with body `"Phones cannot be added to this user"`.
- **CUCM delta:** CUCM's default per-user device cap is 50+, so users with many associated devices (desk phone + backup desk phone + Jabber + mobile + EM profile + tablet + ...) will not fit 1:1. Migration must choose which 5 to carry over.
- **Recommended CUCM→Webex device-selection priority:** (1) primary desk phone, (2) backup/secondary desk phone, (3) softphone (Jabber → Webex App), (4) mobile client, (5) other (tablet, browser, second softphone). Drop extras as `DEVICE_INCOMPATIBLE` with `accept_loss` or `skip`.
- **Orphan devices count against the quota.** Devices left behind by a failed prior migration run still occupy slots — run device cleanup (or `wxcli cleanup`) before retrying a user whose first attempt partially succeeded.
- **Reference:** `docs/reference/devices-core.md` Gotcha #12 for the exact 400 message and endpoint coverage.

## Edge Cases & Exceptions

### 8845/8865 already on MPP firmware
These models support Webex Calling firmware natively. If already on MPP firmware but registered to CUCM, they are classified as `CONVERTIBLE` by `DeviceMapper` (not `INCOMPATIBLE`) and auto-convert at plan time — the "conversion" is a re-registration, not a hardware replacement. No decision is emitted; the planner emits a `create_activation_code` op directly.

### 9800-series phones (9811, 9821, 9841, 9851, 9861, 9871)
Native PhoneOS (RoomOS-derived, but distinct). No conversion or replacement needed. These use the Device Configurations API (PhoneOS keys), not Telephony Device Settings. <!-- Source: devices-core.md §5a, line 1323 -->

### DECT networks

A DECT network is a unit: base station(s) + handsets. Supported Webex DECT models: DBS-110 (1 base, 30 lines) and DBS-210 (up to 250 bases, 1000 lines). Migration requires creating the DECT network in Webex, registering base stations by MAC address, then assigning handsets. Not supported for FedRAMP tenants. <!-- Source: devices-dect.md §3 -->

#### Device Compatibility Tiers

CUCM DECT handsets are classified as `DeviceCompatibilityTier.DECT` by `DeviceMapper` — distinct from `INCOMPATIBLE`, `CONVERTIBLE`, `NATIVE_MPP`, and `WEBEX_APP`. They require DECT network provisioning, not direct device replacement or firmware conversion.

Supported CUCM DECT handset models: **6823, 6825, 6825ip**. Any CUCM device with one of these models is classified as DECT. Other wireless handset models (e.g., 7925, 7926) are `INCOMPATIBLE` and have no equivalent Webex hardware — Webex App on mobile is the closest substitute.

#### Grouping by Device Pool

`normalize_dect_group()` (Pass 1 normalizer) groups all DECT handsets by CUCM device pool into `dect_network:` MigrationObjects. Each MigrationObject carries:
- `coverage_zone` — the CUCM device pool name
- `handset_assignments` — list of handset canonical IDs and owner info
- `handset_count` — total handsets for model auto-selection

One `dect_network` MigrationObject is created per unique device pool that contains DECT handsets. If the CUCM environment uses a single device pool for all DECT handsets across multiple physical locations, the grouping will produce one combined network — see the multi-zone ambiguity issue below.

#### Location Mapping

`DECTMapper` resolves each network's Webex location via the `device_pool_to_location` cross-references built by `CrossReferenceBuilder`. The device pool → location mapping follows the same logic as `DeviceMapper` and `WorkspaceMapper` — if the device pool is unambiguously linked to a single Webex location, the network is assigned to it automatically.

When the device pool maps to multiple candidate locations (ambiguous), or no location at all (unknown device pool), `DECTMapper` raises a `DECT_NETWORK_DESIGN` decision at MEDIUM severity.

#### Auto Model Selection

`DECTMapper` auto-selects the Webex DECT network model based on `handset_count`:
- **≤30 handsets** → `DBS-110` (single base station, 30 lines max)
- **>30 handsets** → `DBS-210` (multi-base, up to 1000 lines)

This selection is stored on the `CanonicalDECTNetwork` object and used by the planner's `create` operation.

#### Handset Owner Resolution

`DECTMapper` enriches each entry in `handset_assignments` by looking up the handset's `ownerUserName` cross-reference:
- **Owned handset** — `owner_canonical_id` is set to the matching `user:` canonical ID
- **Unowned handset** — `owner_status = "unowned"` and a `DECT_HANDSET_ASSIGNMENT` decision is raised at LOW severity

Unowned handsets are common for shared-use devices (warehouse floor, nurse station, lobby). The decision asks the operator to either assign a workspace or mark the handset as unowned in the Webex DECT network.

#### Pipeline Operations

The planner expands each `dect_network` canonical object into 3 sequential ops:

| Op | Handler | What it does |
|----|---------|-------------|
| `dect_network:create` | `handle_dect_network_create` | POST `/telephony/config/locations/{loc}/dectNetworks` — creates the network with model and name |
| `dect_network:create_base_stations` | `handle_dect_base_station_create` | POST `.../baseStations` — registers MAC addresses from `--dect-inventory` CSV. No-op if no inventory supplied. |
| `dect_network:assign_handsets` | `handle_dect_handset_assign` | POST `.../handsets/bulk` — assigns handsets in batches of 50. No-op if no handsets. |

Dependencies enforce: `create` → `create_base_stations` → `assign_handsets`. All three ops must complete before handsets show as registered in Control Hub.

#### Gotchas

1. **FedRAMP not supported.** `DECT_NETWORK_DESIGN` at HIGH severity if the org's `features.dect` is absent. Do not provision DECT on FedRAMP tenants. <!-- Source: devices-dect.md; Webex limits kb -->
2. **Multi-zone ambiguity.** If two CUCM device pools with DECT handsets both resolve to the same Webex location, `DECTMapper` cannot determine whether to create one combined DECT network or two separate ones. This raises `DECT_NETWORK_DESIGN` and requires operator input on the desired network topology.
3. **Base station inventory is not in CUCM AXL.** The CUCM AXL schema does not expose DECT base station MAC addresses. Operators must supply a `--dect-inventory` CSV manually. Without it, base stations are not registered post-migration and handsets cannot associate to the DECT network until an operator registers them in Control Hub.
4. **Handset batch size limit.** The `/handsets/bulk` endpoint accepts max 50 handsets per request. The handler batches automatically — no operator action needed, but large DECT deployments will produce multiple sequential bulk calls.
5. **Model mismatch detection.** If the base station model in the `--dect-inventory` CSV (e.g., `DBS-110-3PC`) does not match the auto-selected network model (`DBS-210`), the discrepancy is surfaced in the `DECT_NETWORK_DESIGN` decision context. Operator must correct either the handset count grouping or the inventory file before proceeding.
6. **DECT classification is additive to device_compatibility_tier.** `DeviceMapper` sets `compatibility_tier = DECT` on `CanonicalDevice` for 6823/6825/6825ip. These devices are still tracked in the device inventory and appear in the assessment report's device table — they are not silently dropped.

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
| Hallway phone | 7811/7821 | Workspace + 9841 | Webex Calling Basic | Common area, no user assignment. 9841 runs PhoneOS. |
| Executive suite | 8865 + 3 sidecars | 9871 + KEM modules | Professional | KEM types: `KEM_14_KEYS`, `KEM_18_KEYS`, `KEM_20_KEYS`. Max modules per model from `kem_module_count` in supported devices catalog. <!-- Source: devices-core.md §3.2 --> |
| Factory floor | 7925/7926 wireless | No direct equivalent | -- | CUCM wireless phones have no Webex hardware equivalent. Webex App on mobile is the nearest substitute.  |
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

### MPP vs PhoneOS/RoomOS config model differences
| Aspect | MPP (68xx/78xx/88xx) | PhoneOS (9800-series) / RoomOS (Room/Board/Desk) |
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

- **Condition:** Device is classified as `CONVERTIBLE` by `DeviceMapper` AND the CUCM device pool has SRST configured AND the site has an unreliable WAN. (As of 2026-04-15 there is no `DEVICE_FIRMWARE_CONVERTIBLE` decision — convertible devices auto-convert unconditionally. This dissent trigger now drives the advisor narrative, not a per-device decision override.)
- **Why the auto-convert path is insufficient on its own:** Convertibility is a pure model check — it does not weigh WAN reliability, SRST dependency depth, or whether the site has an alternative survivability path. Those considerations belong in the advisor narrative rather than at the decision level.
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

- **Condition:** CUCM DECT deployment has multi-cell roaming across base stations AND migration creates a new Webex DECT network
- **Why this matters:** CUCM DECT configurations may have complex roaming chains and handoff patterns between base stations. Webex DECT networks (DBS110: 1 base/30 lines, DBS210: 250 bases/1000 lines) support roaming natively but the specific base-station-to-handset assignments must be manually recreated.
- **What the advisor should do:**
  1. Inventory DECT base station count and handset assignments
  2. Verify the Webex DECT model supports the required base station count
  3. Plan physical base station deployment to match coverage zones
- **Confidence:** MEDIUM -- DECT topology is site-specific and the pipeline does not extract base station placement data

### DT-DEV-004: Legacy gateway conversion recommended but hardware lifecycle not validated

- **Condition:** `detect_legacy_gateway_protocols()` fires (`advisory_patterns.py:1687`) AND the advisory recommends "reconfigure as SIP CUBE" for IOS-XE capable hardware OR "replace with ATA 192" for analog FXS endpoints
- **Why the static advisory is insufficient:** `detect_legacy_gateway_protocols()` (lines 1738-1748) emits a uniform conversion recommendation: IOS-XE hardware → reconfigure as CUBE, analog endpoints → replace with ATA 192. It does not validate:
  1. **IOS-XE hardware lifecycle** — A Cisco 2911 or 2901 router running H.323 may be end-of-sale or running an IOS train that predates SIP CUBE support. IOS-XE CUBE requires a minimum software version (typically 15.3(3)M or later for basic SIP), and the physical platform must support the required feature set license. Converting an EoL 2900-series router to CUBE may not be operationally viable.
  2. **ATA 192 SKU economics** — The advisory recommends ATA 192 at 1-per-analog-endpoint. At scale (a VG224 with 24 FXS ports = 24 ATA 192 units), this is a hardware procurement decision, not a configuration step. The ATA 192 itself is approaching EoL (introduced ~2015); customers may prefer a VG400-series gateway (supports up to 24 FXS ports as a single unit running SIP) for large analog port counts.
  3. **Third-party gateway dependencies** — MGCP-connected door phones, paging adapters, legacy intercoms, and fax machines are often tied to specific signaling protocols. These are not generic endpoints: a Cyberdata VoIP Intercom registering via MGCP cannot simply be swapped for an ATA 192 without vendor support confirmation.
- **What the advisor should do:**
  1. For each MGCP object, ask the operator to confirm the IOS platform and software train before recommending CUBE conversion
  2. Count FXS ports on VG-series gateways; if count > 6, present VG400-series as an alternative to per-port ATA 192 replacement
  3. Flag any non-standard device types (door controllers, paging units, fax adapters) attached to the gateway for manual vendor verification before recommending replacement
  4. For H.323 gateways, confirm the IOS-XE version supports the required SIP feature set before recommending conversion
- **Confidence:** HIGH -- the static advisory's conversion recommendation is architecturally correct but omits hardware lifecycle gating that determines whether the conversion is executable. The three operator confirmation requirements above are non-optional; proceeding without them risks a conversion workstream that cannot be completed.
- **Grounded in:** `advisory_patterns.py:1687-1758` (`detect_legacy_gateway_protocols`), `decision-guide.md` lines 593-605 (`legacy-gateway-protocols` entry), `docs/reference/devices-core.md` (ATA 191/192 device settings, line 1322)

---

## Device Settings Migration

The migration pipeline maps CUCM device-level settings (productSpecificConfiguration, Common Phone Config) to Webex device settings templates.

**Template approach:** Rather than making N API calls for N devices, the mapper groups phones by (model_family, location) and applies settings at the location level. Per-device overrides are generated only for phones that differ from the group majority.

**Field mapping:** Bluetooth, Wi-Fi, backlight, USB, network (CDP/LLDP/VLAN), volume, language, DND, and noise cancellation are mapped from CUCM to Webex. Some mappings are lossy (brightness level → timer enum, DND ringer-off vs reject distinction lost).

**Unmappable settings:** idleUrl, Extension Mobility, gratuitousArp, 802.1x, spanToPCPort, custom ringtones, alwaysUsePrimeLine. These are documented in the assessment report.

**Firmware considerations:** The static device settings API (`customizations.mpp`) is firmware-independent. Per-line ringtone (PhoneOS 4.1+) uses a different API (Device Configurations / JSON Patch) and is handled separately.

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | "42-model replacement map" in `recommend_device_incompatible()` | Partial | `recommendation_rules.py` lines 191-220 | Map has **28 keys** (26 unique models after normalizing ATA spacing variants: `ATA 190`/`ATA190`, `ATA 191`/`ATA191`). Not 42. The map covers 79xx (16 keys), 69xx (6 keys), 7832 (1 key), ATA (4 keys, 2 unique). |
| 2 | Activation code provisioning flow | Verified | `devices-core.md` §1.3, §1.5, §6 | `activation_code()` method documented with workspace/person/model params, `ActivationCodeResponse` model, CLI `create-activation-code` command, and Raw HTTP `POST /devices/activationCode`. |
| 3 | Hot desking requires Professional workspace license | Corrected | `devices-workspaces.md` gotcha #6, #10; `wxcadm-devices-workspaces.md` line 654 | Hot desking uses its own **`hotdesk` license type**, distinct from both Basic (`workspace`) and Professional. However, most `/telephony/config/workspaces/` settings DO require Professional. The claim as stated is imprecise -- hot desking requires a hot desk license, not specifically "Professional". |

---

## DECT Migration

CUCM DECT phones (6823, 6825, 6825ip) register as regular SIP phones via AXL. Webex Calling DECT uses a hierarchical provisioning model:

**CUCM** (flat): Phone → Device Pool → Location
**Webex** (hierarchical): DECT Network → Base Station → Handset → User

There is no 1:1 AXL-to-Webex mapping. The migration pipeline detects DECT handsets by model name during discovery and classifies them separately from desk phones. Base station topology and coverage zones are not discoverable from AXL — they require supplemental operator input via `--dect-inventory` CSV.

**Phase 1 (Detection):** Advisory-only. Reports DECT handset count, model distribution, and estimated base station needs. Does NOT provision anything.

**Phase 2 (Provisioning):** Creates DECT networks, registers base stations (requires physical MAC from supplemental inventory), and binds handsets to users. Handset registration requires the physical device to be powered on and in range of a registered base station.

**Key constraint:** DECT base station MAC addresses are NOT in CUCM AXL. They must be provided separately. Without them, Phase 2 cannot execute.

### Dissent Triggers

| ID | Condition | Recommendation | Confidence |
|----|-----------|---------------|------------|
| DT-DEVICE-010 | DECT handsets > 20% of total phone inventory | Escalate to HIGH — operator may underestimate DECT migration effort. DECT requires physical site survey for base station placement that desk phone migration does not. | 0.85 |
| DT-DEVICE-011 | DECT handsets detected but no supplemental inventory provided | Block execution — cannot provision DECT networks without base station MACs. Advisory should explicitly state this blocker. | 0.95 |
