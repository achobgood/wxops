# Device Settings Template Migration for 9800-Series and PhoneOS Phones

Part of the [CUCM-to-Webex Migration Pipeline](../../plans/cucm-pipeline-architecture.md).

## Problem

9800-series phones (9811/9821/9841/9851/9861/9871) and the 8875 run PhoneOS and expose
a rich set of device settings through the Webex device settings API: wallpaper,
background images, Wi-Fi configuration, Bluetooth, USB port control, network settings
(VLAN, CDP, LLDP), display brightness and screen timeout, ringtones, volume levels,
noise cancellation, HTTP proxy, and more.

Currently the migration pipeline handles:
- **Line key templates** (`ButtonTemplateMapper` + `handle_line_key_template_create`) --
  maps CUCM button templates to Webex line key templates.
- **PSK/softkey configuration** (`SoftkeyMapper` + `handle_softkey_config_configure`) --
  maps CUCM softkey templates to Webex PSK and soft key menu layouts.
- **Device layout** (`DeviceLayoutMapper` + `handle_device_layout_configure`) --
  assigns line appearances, speed dials, and BLF to registered devices.

What is **not** handled: the ~50 device-level settings that CUCM manages through
Enterprise Phone Configuration, Common Phone Configuration profiles, and per-device
overrides. After migration, phones register with Webex defaults -- users lose their
customized display settings, network config, Bluetooth state, volume levels, and
background images.

The existing `handle_device_configure_settings` handler in `handlers.py` accepts a
`device_settings` dict and PUTs it to `/telephony/config/devices/{id}/settings`, but
no mapper populates that dict. It is dead code waiting for a source.

### Why Templates, Not Per-Device Settings

The Webex device settings API operates at three levels: **organization**, **location**,
and **per-device**. Settings cascade: org-level is the default, location-level overrides
org, and per-device overrides location.

A CUCM environment with 200 phones across 5 device pools typically has 2-3 unique
Common Phone Config profiles. Rather than making 200 individual API calls to configure
each phone, we can:

1. Read the CUCM Common Phone Config / Enterprise Phone Config for each model family.
2. Generate a Webex device settings payload per model.
3. Apply it at **org-level** or **location-level** -- one API call covers all matching phones.
4. Apply per-device overrides only where CUCM had per-device exceptions.

This reduces API calls from O(N devices) to O(M models + L locations + E exceptions)
where M is typically 2-4, L is 1-10, and E is a small fraction of N.

---

## Approach

### Two API Surfaces for Device Settings

The Webex platform exposes two distinct APIs for device settings, targeting different
configuration domains:

**1. Static Device Settings API** (`/telephony/config/devices/{id}/settings`)
- Covers: VLAN, CDP, LLDP, audio codec priority, background image selection,
  backlight timer, display name format, line key label format, Wi-Fi network,
  Bluetooth, USB ports, volume settings, HTTP proxy, noise cancellation,
  screen timeout, DND, ACD, multicast, off-hook timer, phone language,
  PoE mode, softkey layout, PSK configuration, call history, contacts source.
- Organized by device family: `mpp`, `ata`, `dect`, `wifi`.
- Supports org-level (`/telephony/config/devices/settings`), location-level
  (`/telephony/config/locations/{id}/devices/settings`), and per-device override.
- PUT body uses `customizations.mpp.{setting}` structure.
- Scope: `spark-admin:telephony_config_write`.

**2. Dynamic Device Settings API** (`/telephony/config/devices/{id}/dynamicSettings`)
- Uses tag-based addressing: `%ENABLE_BLUETOOTH%`, `%DO_UI_MENU_BACKGROUND%`, etc.
- Tags are firmware-dependent -- the validation schema API
  (`/telephony/config/devices/dynamicSettings/validationSchema`) returns available
  tags per device family/model with their data types and valid ranges.
- Supports org-level bulk jobs
  (`/telephony/config/jobs/devices/dynamicDeviceSettings`) that apply tags across
  all devices in an org or location asynchronously.
- Used for settings not exposed in the static API (Poly-specific, 3rd-party).
- Scope: `spark-admin:telephony_config_write`.

**Strategy:** Use the static API as the primary path (covers most MPP/PhoneOS settings).
Use the dynamic API only for settings that exist in CUCM but have no static API
equivalent. The dynamic API bulk job is attractive for org-wide settings but runs
asynchronously and cannot run in parallel with other device jobs.

### Background Image Upload

Background images require a separate multipart upload endpoint:
`POST /telephony/config/devices/{id}/actions/backgroundImageUpload/invoke`

- Accepts `.jpeg` or `.png`, max 625 KB.
- Returns a `backgroundImageUrl` that can then be referenced in the device settings.
- Org limit: 100 background images.
- The migration tool should upload CUCM custom backgrounds once, then reference
  the URL in the settings payload.

---

## CUCM Source Data

### Enterprise Phone Configuration

CUCM Enterprise Phone Configuration is a global singleton that sets default values
for all phones. It is not exposed as a standalone AXL object -- its values appear as
defaults in device pool and phone-level settings. Key fields:

| CUCM Field | Category | Notes |
|-----------|----------|-------|
| `webAccess` | Network | Enable/disable web admin access |
| `settingsAccess` | UI | Settings button access level |
| `gratuitousArp` | Network | Gratuitous ARP handling |
| `pcPort` | Network | PC port enabled/disabled |
| `cdpSwPort` | Network | CDP on switch port |
| `lldpSwPort` | Network | LLDP on switch port |
| `spanToPCPort` | Network | SPAN to PC port |
| `dot1xAuth` | Network | 802.1x authentication |

### Common Phone Configuration (commonPhoneConfig)

Already extracted by `InformationalExtractor` as `common_phone_config` objects
(via `listCommonPhoneConfig`). These profiles group phone settings shared across
multiple devices.

AXL `listCommonPhoneConfig` returns:
```
name, description
```

To get the full settings, `getCommonPhoneConfig` is needed (not currently called).
The key fields are vendor-specific XML configuration blobs stored as
`vendorConfig` elements.

### Per-Phone Settings

`getPhone` already extracts per-device data but does not capture device-level
settings fields. The following fields are available from `getPhone` but not
currently extracted:

| AXL Field | Maps To | Notes |
|-----------|---------|-------|
| `commonPhoneConfigName` | Profile association | Which common phone config this device uses |
| `networkLocation` | Network | `Use System Default` or explicit |
| `userLocale` | Language | Phone language locale |
| `networkLocale` | Language | Network prompt locale |
| `idleUrl` | Display | XML service URL displayed at idle |
| `idleTimeout` | Display | Idle timer before loading idle URL |
| `alwaysUsePrimeLine` | Behavior | Always use primary line for outgoing |
| `alwaysUsePrimeLineForVoiceMessage` | Behavior | Always use primary line for VM |
| `loginUserId` | Mobility | Extension Mobility login user |
| `dndOption` | Feature | DND mode: Ringer Off or Call Reject |
| `dndStatus` | Feature | DND enabled state |
| `enableExtensionMobility` | Mobility | EM enabled |

### Phone Product Specific Configuration (productSpecificConfiguration)

CUCM stores model-specific settings in `productSpecificConfiguration` XML within the
phone record. This is the richest source of device-level settings but is model-specific
and version-specific. Not currently extracted.

Example fields for 8800-series:
```xml
<productSpecificConfiguration>
  <screenBrightness>15</screenBrightness>
  <backlightTimeout>60</backlightTimeout>
  <BluetoothMode>1</BluetoothMode>
  <WifiEnable>1</WifiEnable>
  <WifiSSID>Corp-WiFi</WifiSSID>
  <WifiSecurityMode>WPA2-Enterprise</WifiSecurityMode>
  <usbPort>Enabled</usbPort>
  <allowIncomingCallToRecordCalls>true</allowIncomingCallToRecordCalls>
</productSpecificConfiguration>
```

---

## Webex Target APIs

### Org-Level Device Settings

```
GET  /telephony/config/devices/settings?orgId={orgId}
PUT  /telephony/config/devices/settings?orgId={orgId}
```

Response/request body structure:
```json
{
  "customizations": {
    "mpp": {
      "backlightTimer": "ONE_MIN",
      "background": { "customUrl": "", "image": "WEBEX_DARK_BLUE" },
      "bluetooth": { "enabled": true, "mode": "PHONE" },
      "cdpEnabled": false,
      "lldpEnabled": false,
      "vlan": { "enabled": false, "value": 1, "pcPort": 1 },
      "wifiNetwork": { "enabled": false, "authenticationMethod": "PSK", "ssidName": "", "userId": "" },
      "usbPorts": { "enabled": true, "sideUsbEnabled": true, "rearUsbEnabled": true },
      "volumeSettings": { "ringerVolume": 9, "speakerVolume": 9, "handsetVolume": 9, "headsetVolume": 9 },
      "screenTimeout": { "enabled": true, "value": 400 },
      "phoneLanguage": "ENGLISH_UNITED_STATES",
      "displayNameFormat": "PERSON_FIRST_THEN_LAST_NAME",
      "noiseCancellation": { "enabled": false, "allowEndUserOverrideEnabled": false },
      "httpProxy": { "mode": "OFF" },
      "backgroundImage8875": "BLUE_LIGHT",
      "softKeyLayout": { "...": "..." }
    },
    "wifi": { "...": "..." }
  },
  "customEnabled": true
}
```

### Location-Level Device Settings

```
GET  /telephony/config/locations/{locationId}/devices/settings?orgId={orgId}
PUT  /telephony/config/locations/{locationId}/devices/settings?orgId={orgId}
```

Same body structure as org-level. Overrides org-level for devices in that location.

### Per-Device Settings Override

```
GET  /telephony/config/devices/{deviceId}/settings?orgId={orgId}&deviceModel={model}
PUT  /telephony/config/devices/{deviceId}/settings?orgId={orgId}&deviceModel={model}
```

Same body structure. Overrides location-level for a specific device.
Note the `deviceModel` query parameter -- required for the GET to return the correct
schema for that device family.

### Background Image Upload

```
POST /telephony/config/devices/{deviceId}/actions/backgroundImageUpload/invoke?orgId={orgId}
Content-Type: multipart/form-data

(binary image data, .jpeg or .png, max 625 KB)
```

Returns `{ "filename": "...", "backgroundImageUrl": "/dms/Cisco_Phone_Background/...", "count": "2" }`.

### Dynamic Device Settings (Per-Device)

```
PUT /telephony/config/devices/{deviceId}/dynamicSettings?orgId={orgId}
```

Body:
```json
{
  "tags": [
    { "action": "SET", "tag": "%ENABLE_BLUETOOTH%", "value": "0" },
    { "action": "CLEAR", "tag": "%G711A_ORDER%" }
  ]
}
```

### Dynamic Device Settings Bulk Job

```
POST /telephony/config/jobs/devices/dynamicDeviceSettings?orgId={orgId}
```

Body:
```json
{
  "locationId": "",
  "tags": [
    { "familyOrModelDisplayName": "Cisco 9800", "tag": "%ENABLE_BLUETOOTH%", "action": "SET", "value": "1" }
  ]
}
```

Asynchronous. Returns a job ID. Only one such job can run per org at a time, and it
cannot run in parallel with other device jobs (settings push, rebuild phones).

---

## CUCM-to-Webex Field Mapping

### Mappable Settings (Static API)

| CUCM Source | Webex Target (`customizations.mpp.*`) | Notes |
|-------------|---------------------------------------|-------|
| `productSpecificConfiguration.BluetoothMode` | `bluetooth.enabled`, `bluetooth.mode` | CUCM: 0=off, 1=handsfree, 2=phone, 3=both. Webex: `enabled` bool + `mode` enum. |
| `productSpecificConfiguration.WifiEnable` | `wifiNetwork.enabled` | Boolean. |
| `productSpecificConfiguration.WifiSSID` | `wifiNetwork.ssidName` | Direct string. |
| `productSpecificConfiguration.WifiSecurityMode` | `wifiNetwork.authenticationMethod` | Map: WPA2-PSK -> `PSK`, WPA2-Enterprise -> `EAP`. |
| `productSpecificConfiguration.screenBrightness` | `backlightTimer` | CUCM: numeric (0-15). Webex: enum (`ONE_MIN`, `FIVE_MIN`, `THIRTY_MIN`, `ALWAYS_ON`). Lossy mapping -- brightness level has no Webex equivalent, only timer. |
| `productSpecificConfiguration.usbPort` | `usbPorts.enabled` | CUCM: "Enabled"/"Disabled". Webex: bool. |
| `productSpecificConfiguration.backlightTimeout` | `backlightTimer` | CUCM: seconds. Webex: enum values. Needs range mapping. |
| Device pool -> CDP/LLDP settings | `cdpEnabled`, `lldpEnabled` | From device pool or enterprise phone config defaults. |
| Device pool -> VLAN settings | `vlan.enabled`, `vlan.value`, `vlan.pcPort` | VLAN ID from device pool network settings. |
| `userLocale` on phone | `phoneLanguage` | Map CUCM locale name to Webex language enum (e.g., `English_United_States` -> `ENGLISH_UNITED_STATES`). |
| `dndOption` / `dndStatus` | `dndServicesEnabled` | CUCM DND status -> Webex DND bool. DND option (ringer off vs reject) has no Webex equivalent -- always call reject. |
| Enterprise phone config `webAccess` | `mppUserWebAccessEnabled` | Direct bool mapping. |
| Common phone config volume | `volumeSettings.*` | If extractable from vendor config XML. |

### Mappable Settings (Background Image)

| CUCM Source | Webex Target | Notes |
|-------------|-------------|-------|
| `productSpecificConfiguration.backgroundImageAccess` | `background.image` | CUCM: specific file path. Webex: enum (`WEBEX_DARK_BLUE`, `WEBEX_DARK_GREEN`, ...) or `CUSTOM` + `customUrl`. |
| Custom wallpaper TFTP files | Upload -> `backgroundImageUrl` | Extract from CUCM TFTP, upload via multipart API, then reference URL. Requires TFTP access. |
| 8875-specific background | `backgroundImage8875` | Separate field: `BLUE_LIGHT`, `BLUE_DARK`, `PURPLE_LIGHT`, `PURPLE_DARK`. |

### Unmappable Settings (Manual Config Required)

| CUCM Setting | Why Unmappable | Operator Action |
|-------------|---------------|-----------------|
| `idleUrl` / `idleTimeout` | No Webex equivalent (XML services are CUCM-specific) | Note in report as deprecated feature. |
| Extension Mobility (`enableExtensionMobility`) | Webex uses Hot Desking (different mechanism) | Document in report; configure hot desking separately. |
| `gratuitousArp` | Network-level; no Webex phone API equivalent | Network team handles at switch level. |
| `802.1x` (`dot1xAuth`) | Not in Webex device settings API | Configure via Control Hub manually or dynamic tags. |
| `spanToPCPort` | No Webex equivalent | N/A for cloud-managed phones. |
| Custom ring tones (uploaded .raw files) | Webex has built-in ringtone IDs (1-13) only | Map to closest default; note lossy mapping in report. |
| Per-line ringtone (PhoneOS 4.1+ only) | Device Configurations API, not device settings API | Handled separately via JSON Patch if firmware >= 4.1. |
| `alwaysUsePrimeLine` / `alwaysUsePrimeLineForVoiceMessage` | No Webex equivalent | Note in report as behavior change. |

---

## Template Generation Logic

### DeviceSettingsMapper (New Mapper)

New mapper: `src/wxcli/migration/transform/mappers/device_settings_mapper.py`

```python
class DeviceSettingsMapper(Mapper):
    name = "device_settings_mapper"
    depends_on = ["device_mapper", "location_mapper"]
```

**Input:** Raw phone objects (`store.get_objects("phone")`), common phone config objects
(`store.get_objects("common_phone_config")`), location objects.

**Output:** `CanonicalDeviceSettingsTemplate` objects -- one per unique
(model_family, location) combination.

**Algorithm:**

1. Group all NATIVE_MPP and CONVERTIBLE devices by `(model_family, location_canonical_id)`.
   Model families: `9800` (all 9800 models share the same settings schema),
   `8875` (separate background field), `78xx` (legacy MPP), `68xx` (legacy MPP).

2. For each group, read the CUCM settings from:
   a. Enterprise phone config defaults (global).
   b. Common phone config profile assigned to phones in this group.
   c. Per-phone `productSpecificConfiguration` -- compute the **majority value** for
      each setting across all phones in the group.

3. Generate a `CanonicalDeviceSettingsTemplate` with:
   - `canonical_id`: `device_settings_template:{model_family}:{location_id}`
   - `model_family`: string
   - `location_canonical_id`: string
   - `settings`: dict matching the Webex `customizations.mpp` structure
   - `per_device_overrides`: list of `(device_canonical_id, override_settings)` for
     phones that differ from the group majority
   - `unmappable_settings`: list of CUCM settings that have no Webex equivalent
   - `phones_using`: count of phones in this group

4. For each phone that differs from the group template on any setting, create a
   per-device override entry. If >50% of phones in a group differ on a setting,
   promote that setting variation to a second template or flag for decision.

5. Generate `DEVICE_SETTINGS_LOSSY` decisions (new `DecisionType`) when:
   - A CUCM setting maps to Webex with value loss (e.g., brightness level -> timer enum)
   - Custom wallpapers are detected but TFTP extraction is not configured
   - Extension Mobility is enabled (requires hot desking reconfiguration)

### Canonical Model

```python
@dataclass
class CanonicalDeviceSettingsTemplate:
    canonical_id: str                    # "device_settings_template:{family}:{loc}"
    model_family: str                    # "9800", "8875", "78xx", "68xx"
    location_canonical_id: str           # location this template targets
    settings: dict                       # Webex API-ready customizations.mpp dict
    per_device_overrides: list[dict]     # [{device_canonical_id, settings}]
    unmappable_settings: list[str]       # CUCM setting names with no Webex mapping
    phones_using: int                    # count of phones covered
    custom_backgrounds: list[dict]       # [{filename, source_path}] for upload
```

---

## Pipeline Integration

### Extraction Changes

**DeviceExtractor** (`extractors/devices.py`): Add `productSpecificConfiguration` and
`commonPhoneConfigName` to `PHONE_GET_RETURNED_TAGS`:

```python
PHONE_GET_RETURNED_TAGS = {
    # ... existing tags ...
    'commonPhoneConfigName': '',
    'productSpecificConfiguration': '',
    'userLocale': '',
    'networkLocale': '',
    'dndOption': '',
    'dndStatus': '',
    'enableExtensionMobility': '',
}
```

**InformationalExtractor** already extracts `common_phone_config` via
`listCommonPhoneConfig`, but only gets `name` and `description`. Add a detail
fetch step using `getCommonPhoneConfig` to retrieve `vendorConfig` fields:

```python
# In extractors/informational.py, add detail fetch for common_phone_config
COMMON_PHONE_CONFIG_DETAIL_TAGS = {
    "name": "", "description": "", "vendorConfig": "",
    "dndOption": "", "dndAlertingType": "",
    "unlabelledLineKeyBlinkSpeed": "",
}
```

### Normalizer Changes

Add `normalize_common_phone_config_detail` normalizer that extracts vendor-specific
settings from the `vendorConfig` XML blob into a flat dict of setting values.

Update `normalize_phone` to preserve `productSpecificConfiguration` and
`commonPhoneConfigName` in the raw phone data (they are already available if
extracted -- just need to not be discarded).

### Cross-Reference Changes

Add one new relationship in `CrossReferenceBuilder`:

```python
# In cross_reference.py, _build_template_refs:
"phone_uses_common_phone_config"  # device:{name} -> common_phone_config:{name}
```

### New Mapper: DeviceSettingsMapper

- **Tier:** Tier 3 (depends on `device_mapper` and `location_mapper`).
- **Position:** After `DeviceMapper`, before `DeviceLayoutMapper`.
- **Output types:** `device_settings_template` (new canonical type).

### Planner Changes

New expander `_expand_device_settings_template`:

```python
def _expand_device_settings_template(data, decisions):
    ops = []
    # Location-level settings push (one per template)
    ops.append(MigrationOp(
        canonical_id=data["canonical_id"],
        op_type="apply_location_settings",
        resource_type="device_settings_template",
        data=data,
    ))
    # Per-device overrides (one per device with overrides)
    for override in data.get("per_device_overrides", []):
        ops.append(MigrationOp(
            canonical_id=data["canonical_id"],
            op_type="apply_device_override",
            resource_type="device_settings_template",
            data={**data, "override": override},
        ))
    return ops
```

### Handler Changes

**New handler: `handle_device_settings_template_apply_location_settings`**

```python
def handle_device_settings_template_apply_location_settings(data, deps, ctx):
    loc_cid = data.get("location_canonical_id")
    loc_wid = deps.get(loc_cid)
    if not loc_wid:
        return []
    settings = data.get("settings", {})
    if not settings:
        return []
    body = {"customizations": {"mpp": settings}, "customEnabled": True}
    return [("PUT", _url(f"/telephony/config/locations/{loc_wid}/devices/settings", ctx), body)]
```

**New handler: `handle_device_settings_template_apply_device_override`**

```python
def handle_device_settings_template_apply_device_override(data, deps, ctx):
    override = data.get("override", {})
    device_cid = override.get("device_canonical_id")
    device_wid = deps.get(device_cid)
    if not device_wid:
        return []
    settings = override.get("settings", {})
    if not settings:
        return []
    body = {"customizations": {"mpp": settings}, "customEnabled": True}
    return [("PUT", _url(f"/telephony/config/devices/{device_wid}/settings", ctx), body)]
```

### Tier Assignments

| Operation | Tier | Rationale |
|-----------|------|-----------|
| `(device_settings_template, apply_location_settings)` | 1 | Before devices are created -- location-level settings are infrastructure. |
| `(device_settings_template, apply_device_override)` | 5 | After device:create -- per-device overrides need a registered device. |

### Dependency Graph Changes

New cross-object rules in `dependency.py`:

```python
# device_settings_template:apply_location_settings REQUIRES location:enable_calling
# device_settings_template:apply_device_override REQUIRES device:create (for the target device)
```

---

## 9800-Series Specifics

### Already Handled

| Feature | Handler | Notes |
|---------|---------|-------|
| PSK (Programmable Soft Keys) | `handle_softkey_config_configure` | PSK 1-16 via `dynamicSettings` endpoint. |
| Line key templates | `handle_line_key_template_create` | 9800 models use `"Cisco {model}"` (not `"DMS Cisco {model}"`). Handler remaps. |
| Line key layout | `handle_device_layout_configure` | Members + layout + applyChanges. |
| Device ID surface | `device_mapper.py` | 9800-series uses `"cloud"` surface (`deviceId`, not `callingDeviceId`). |

### New in This Spec

| Feature | Webex API Path | Notes |
|---------|---------------|-------|
| Wallpaper/background | `customizations.mpp.background.image` | Enum selection: `WEBEX_DARK_BLUE`, `WEBEX_DARK_GREEN`, `CISCO_LIGHT_BLUE`, `CUSTOM`. Custom requires prior image upload. |
| Wi-Fi configuration | `customizations.mpp.wifiNetwork.*` | SSID, auth method, enabled state. Wi-Fi-capable 9800 models only (9861, 9871). |
| Bluetooth | `customizations.mpp.bluetooth.*` | Enabled + mode. All 9800 models except 9811. |
| USB ports | `customizations.mpp.usbPorts.*` | Side and rear USB enable/disable. |
| Display/backlight | `customizations.mpp.backlightTimer` | Timeout enum. 9800 uses `backlightTimer` (not `backlightTimer68XX78XX`). |
| Screen timeout | `customizations.mpp.screenTimeout.*` | Enable + value in seconds. |
| Network (VLAN/CDP/LLDP) | `customizations.mpp.vlan.*`, `.cdpEnabled`, `.lldpEnabled` | Network discovery protocol settings. |
| Volume levels | `customizations.mpp.volumeSettings.*` | Ringer, speaker, handset, headset volumes (0-15 scale). |
| Noise cancellation | `customizations.mpp.noiseCancellation.*` | Enabled + allow user override. |
| Phone language | `customizations.mpp.phoneLanguage` | Locale enum. |
| 8875 background | `customizations.mpp.backgroundImage8875` | Separate field for 8875-specific color theme backgrounds. |

### PhoneOS Firmware Version Considerations

The device settings schema is stable across PhoneOS versions for the static API
(the `customizations.mpp` structure is firmware-independent). However:

- **Per-line ringtone** requires PhoneOS 4.1+ and uses the Device Configurations API
  (JSON Patch to `Lines.Line[N].CallFeatureSettings.Ringtone`), not the device
  settings API. Out of scope for this spec -- tracked separately.
- **Dynamic settings tags** (`%ENABLE_BLUETOOTH%` etc.) are firmware-reported. The
  validation schema endpoint returns the available tags per device family. Migration
  should not use dynamic tags for settings available in the static API.
- The static device settings PUT does not require the device to be online -- settings
  are queued and applied on next sync. This is advantageous for migration (bulk apply
  before devices are connected).

---

## Known Limitations

1. **`productSpecificConfiguration` is model-specific XML.** There is no universal
   schema. Each phone model has a different set of fields, and CUCM versions may add
   or remove fields. The mapper must handle missing fields gracefully.

2. **Custom wallpaper extraction requires TFTP access.** CUCM stores custom background
   images on the TFTP server. The migration tool does not currently connect to CUCM
   TFTP. Phase 1 should support Webex built-in backgrounds only; custom image upload
   can be added as a follow-up with TFTP integration or manual image provision.

3. **No Webex "device settings template" object.** Unlike line key templates, Webex
   does not have a named template object for device settings. The settings are applied
   at org, location, or device level directly. The "template" concept exists only in
   our pipeline to group and batch settings -- it does not create a reusable Webex
   object.

4. **Settings push is not atomic.** Applying settings at location level affects all
   devices in that location immediately (on next sync). There is no way to stage
   settings for a subset of devices at a location without using per-device overrides.
   The migration tool should apply location-level settings conservatively (only settings
   that are uniform across all CUCM phones at that location).

5. **Control Hub-only settings.** Some phone settings visible in Control Hub are not
   exposed in the API. Known gaps:
   - Emergency Call settings (handled separately via E911 APIs)
   - Wi-Fi enterprise certificate provisioning
   - Secure phone mode / SRST configuration
   - Device firmware upgrade channel selection

6. **Dynamic settings bulk job serialization.** Only one dynamic settings job can
   run per org at a time. It also blocks other device jobs (settings push, rebuild
   phones). The migration tool must sequence these jobs carefully if using the dynamic
   API path.

7. **Background image org limit.** Maximum 100 images per org. CUCM environments with
   many custom backgrounds may exceed this limit. The mapper should deduplicate
   identical images and warn when approaching the limit.

8. **`vendorConfig` parsing complexity.** The `vendorConfig` element in
   `getCommonPhoneConfig` contains model-specific XML that varies by CUCM version.
   Parsing must be defensive and tolerate unknown elements.

---

## Report Changes

### New Report Section: Device Settings Coverage

Add a section to the assessment report appendix (after the existing device
compatibility section) showing:

1. **Settings coverage summary table:**
   - Total device settings fields found in CUCM
   - Fields mappable to Webex API (count + percentage)
   - Fields requiring manual configuration (count + list)
   - Fields with lossy mapping (count + detail)

2. **Per-location template summary:**
   - Location name, model family, template settings count, devices covered
   - Per-device override count

3. **Unmappable settings inventory:**
   - Full list of CUCM settings with no Webex API equivalent
   - Operator action required for each

4. **Custom background images:**
   - Count of custom backgrounds detected
   - Upload status (if TFTP integration is available) or manual upload instructions

### Report Score Impact

Add a new score factor `Device Settings Complexity` to
`src/wxcli/migration/report/score.py`:

- 0 points: All phones use default settings (no common phone config customization).
- 1-2 points: 1-3 unique settings profiles, no custom backgrounds.
- 3-4 points: 4+ unique profiles, custom backgrounds, or per-device overrides >20%.
- 5 points: Extension Mobility enabled, custom XML services, or >50% per-device overrides.

---

## Documentation Updates Required

### CLAUDE.md Files

| File | Section | What to Add |
|------|---------|-------------|
| `CLAUDE.md` (project root) | File Map > Migration Knowledge Base | Add `kb-device-settings.md` entry. |
| `CLAUDE.md` (project root) | Known Issues | Add item: "Device settings templates apply at location level, not as named template objects." |
| `src/wxcli/migration/CLAUDE.md` | File Map table | Add `device_settings_mapper.py` entry. |
| `src/wxcli/migration/transform/CLAUDE.md` | Mapper Execution Engine | Add `DeviceSettingsMapper` to mapper inventory. |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Mapper Inventory (Tier 3) | Add `DeviceSettingsMapper` with `name`, `depends_on`, `produces`, `source_objects`. |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Key Gotchas | Add gotcha: "`productSpecificConfiguration` XML parsing is model-specific and version-dependent." |
| `src/wxcli/migration/execute/CLAUDE.md` | Handler Inventory (Tier 1 + Tier 5) | Add `(device_settings_template, apply_location_settings)` at Tier 1 and `(device_settings_template, apply_device_override)` at Tier 5. |
| `src/wxcli/migration/execute/CLAUDE.md` | Tier System | Update tier descriptions to include device settings template operations. |
| `src/wxcli/migration/cucm/CLAUDE.md` | Extraction Order note | Note that `getPhone` now extracts `productSpecificConfiguration`. |
| `src/wxcli/migration/cucm/extractors/CLAUDE.md` (if exists) | Extractor details | Document new `PHONE_GET_RETURNED_TAGS` additions. |
| `src/wxcli/migration/report/CLAUDE.md` (if exists) | Report sections | Document new Device Settings Coverage appendix section. |

### Reference Docs

| File | Section | What to Add |
|------|---------|-------------|
| `docs/reference/devices-core.md` | Section 3 (TelephonyDevicesApi) | Document org-level and location-level device settings GET/PUT. Note that these are separate from per-device settings. |
| `docs/reference/devices-core.md` | Gotchas | Add: "Org/location device settings PUT affects all matching devices on next sync. No rollback." |
| `docs/reference/devices-platform.md` | Gotchas | Add: "Static device settings API (`/telephony/config/devices/{id}/settings`) and dynamic settings API (`/telephony/config/devices/{id}/dynamicSettings`) are separate API surfaces. Do not mix them. Static API uses JSON objects; dynamic API uses tag-based addressing." |

### Runbooks

| File | Section | What to Add |
|------|---------|-------------|
| `docs/runbooks/cucm-migration/decision-guide.md` | New entry | Add `DEVICE_SETTINGS_LOSSY` decision type: severity MEDIUM, override criteria, example scenarios. |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Pipeline walkthrough | Add note about device settings extraction and template generation in the `map` phase. |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Config keys | Add config key for enabling/disabling device settings migration (`enable_device_settings_migration: true`). |

### Knowledge Base

| File | What to Add |
|------|-------------|
| `docs/knowledge-base/migration/kb-device-migration.md` | New section: "Device Settings Migration" covering the template approach, field mapping table, and firmware version considerations. |
| `docs/knowledge-base/migration/kb-webex-limits.md` | Add: "Background image limit: 100 per org. Dynamic settings job: 1 concurrent per org." |

### Skills

| File | Section | What to Add |
|------|---------|-------------|
| `.claude/skills/cucm-migrate/SKILL.md` | Execution flow | Note that device settings templates are applied at location level during Tier 1 and per-device overrides at Tier 5. |
| `.claude/skills/manage-devices/SKILL.md` | Device settings section | Document the three-level settings hierarchy (org -> location -> device) and how to read/modify at each level. |
| `.claude/skills/device-platform/SKILL.md` | Gotchas or reference | Cross-reference to devices-core.md for the static device settings API (distinct from RoomOS device configurations). |

---

## Test Strategy

### Unit Tests

**Mapper tests** (`tests/migration/transform/mappers/test_device_settings_mapper.py`):

1. **Empty environment:** No phones with device settings -> mapper produces no templates.
2. **Single model, single location:** 10 phones with identical settings -> one template, zero overrides.
3. **Single model, multiple locations:** Same model across 3 locations -> 3 templates.
4. **Multiple models, single location:** 9861 + 8875 at one location -> 2 templates (different families).
5. **Per-device override detection:** 10 phones, 2 with different Bluetooth settings -> 1 template + 2 overrides.
6. **Majority vote:** 10 phones, 6 with Bluetooth on, 4 with off -> template has `bluetooth.enabled: true`.
7. **CUCM field mapping:** Each individual field mapping produces correct Webex API value.
8. **Missing `productSpecificConfiguration`:** Phone without PSC -> no settings mapped, no error.
9. **Unknown CUCM fields:** PSC with unknown XML elements -> ignored gracefully.
10. **`DEVICE_SETTINGS_LOSSY` decision:** Phone with custom wallpaper -> decision generated.
11. **INCOMPATIBLE devices excluded:** Incompatible phones do not contribute to any template.
12. **WEBEX_APP devices excluded:** Software phones do not contribute to any template.

**Handler tests** (`tests/migration/execute/test_device_settings_handlers.py`):

1. **Location settings apply:** Correct URL and body for location-level PUT.
2. **Device override apply:** Correct URL and body for per-device PUT.
3. **No settings -> empty result:** Template with empty `settings` returns `[]`.
4. **No location dep -> empty result:** Missing location dependency returns `[]`.
5. **No device dep -> empty result:** Override with unresolved device returns `[]`.

**Planner tests:**

1. **Expansion produces correct op types:** Template -> `apply_location_settings` + N `apply_device_override` ops.
2. **Skip on zero phones_using:** Template with `phones_using=0` produces no ops.

### Integration Tests

1. **Full pipeline with device settings:** Run discover -> normalize -> map -> analyze
   with a store that includes phones with `productSpecificConfiguration` data.
   Verify templates are generated and decisions are created for lossy mappings.

2. **Handler integration:** Feed template data through `handle_device_settings_template_apply_location_settings`
   and verify the URL and body match the Webex API contract.

### Live Validation (Manual)

1. Read org-level device settings before migration: `GET /telephony/config/devices/settings`.
2. Apply location-level settings via the handler.
3. Verify a 9800-series phone at that location picks up the new settings on next sync.
4. Apply a per-device override to one phone; verify it overrides the location setting.
5. Verify phones at other locations are unaffected.

---

## Open Questions

1. **Should org-level settings be used instead of location-level?** If all locations
   share the same CUCM Enterprise Phone Config, one org-level PUT would suffice.
   Location-level is more conservative but requires more API calls.

2. **Should custom background image upload be in Phase 1?** It requires TFTP access
   to the CUCM server, which the pipeline does not currently support. Deferring to
   Phase 2 simplifies the initial implementation.

3. **How to handle Extension Mobility to Hot Desking mapping?** EM is a fundamentally
   different architecture. Should the migration tool generate hot desking configuration
   automatically, or just flag it in the report as a manual task?

4. **Should the dynamic settings API be used at all?** The static API covers all
   standard MPP/PhoneOS settings. Dynamic settings are primarily for Poly/third-party
   devices. If we limit scope to Cisco 9800/8875/78xx/68xx, the static API may be
   sufficient.
