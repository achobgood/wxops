# cucm/ — CUCM Extraction Layer (Phase 03)

Connects to CUCM via AXL SOAP and extracts raw configuration into the SQLite store. Output is `DiscoveryResult.raw_data` — a dict of dicts of lists that feeds directly into `transform/pipeline.py:normalize_discovery()`.

## Files

| File | Purpose |
|------|---------|
| `connection.py` | `AXLConnection` — zeep SOAP client with certificate handling and retry |
| `discovery.py` | `run_discovery(store, config)` — orchestrates all extractors in order, writes results to store |
| `unity_connection.py` | `UnityConnectionClient` — REST client for Unity Connection per-user VM settings |
| `extractors/base.py` | `BaseExtractor` ABC + `ExtractionResult` dataclass |
| `extractors/devices.py` | Phones (SEP) and their line appearances |
| `extractors/features.py` | Hunt pilots/lists/groups, call park, pickup groups, CTI route points, paging groups |
| `extractors/locations.py` | CUCM locations, device pools, datetime groups |
| `extractors/routing.py` | Gateways, SIP trunks, route groups, route lists, route patterns, CSS, partitions |
| `extractors/shared_lines.py` | Shared line detection (post-normalization, not an AXL extractor) |
| `extractors/templates.py` | Button templates + softkey templates (via SQL — AXL doesn't expose softkey template list) |
| `extractors/users.py` | EndUsers, lines (DNs), voicemail profiles |
| `extractors/voicemail.py` | Unity Connection voicemail pilot, voicemail profiles |
| `extractors/helpers.py` | `to_list()`, zeep response normalization helpers |
| `extractors/workspaces.py` | Common-area phone workspace classification (post-normalization) |
| `extractors/informational.py` | Tier 3: 20 informational object types (regions, SRST, MRG, app users, etc.) — report only |
| `extractors/tier4.py` | Tier 4 feature gaps: recording profiles, remote destinations, transformation patterns, EM device profiles |
| `extractors/remote_destinations.py` | Remote destinations for SNR |
| `extractors/e911.py` | ELIN groups, geo locations |
| `extractors/device_profiles.py` | Extension Mobility device profiles |
| `extractors/moh.py` | Music on Hold sources |
| `extractors/announcements.py` | Announcements / media resources |

## Extraction Order

```
locations → users → devices → features → routing → templates → voicemail → informational → tier4 → remote_destinations → e911 → device_profiles → moh → announcements
```

Extractors are independent at extraction time — the order is a documentation convention, not a dependency constraint. All raw dicts go into `raw_data` keyed by extractor name.

## raw_data Structure

`raw_data` is a `dict[str, dict[str, list]]`:
- Top key = extractor group (`"devices"`, `"users"`, `"features"`, etc.)
- Inner key = object type (`"phones"`, `"users"`, `"button_templates"`, etc.)
- Value = list of raw CUCM dicts (as returned by zeep, pre-normalized by `to_list()`)

`normalize_discovery()` in `transform/pipeline.py` consumes `raw_data` via `RAW_DATA_MAPPING`.

**Executive/assistant data** is extracted via SQL (no AXL list/get operations exist):
- `raw_data["features"]["executive_assistant_pairs"]` — pair dicts from `executiveassistant` table join
- `raw_data["features"]["executive_settings"]` — user service subscription dicts from `endusersubscribedservice` join

**Intercept candidates** are extracted via SQL heuristics:
- `raw_data["tier4"]["intercept_candidates"]` — heuristically-detected intercept-like configurations (blocked partition DNs, CFA-to-voicemail with no registered device). Uses two SQL queries for partition name pattern matching and call forwarding state detection.

**Standalone extractors** (wired into discovery.py alongside the 9 original extractors):
- `raw_data["remote_destinations"]["remote_destinations"]` — SNR remote destinations
- `raw_data["e911"]["elin_groups"]` — ELIN groups for E911
- `raw_data["e911"]["geo_locations"]` — geo locations for E911
- `raw_data["device_profiles"]["device_profiles"]` — Extension Mobility device profiles
- `raw_data["moh"]["moh_sources"]` — Music on Hold audio sources
- `raw_data["announcements"]["announcements"]` — announcement / media resources

## Key Gotchas

- **Softkey templates require SQL.** `addSoftkeyTemplate`/`listSoftkeyTemplate` don't exist in AXL v15.0. The `TemplateExtractor` uses direct SQL (`executeSQLQuery`) to fetch softkey template data. See `extractors/templates.py`.
- **Button templates use `<buttonNumber>` not `<index>`** in `addPhoneButtonTemplate`. The extractor normalizes this on the way out.
- **BLF name mismatch.** The feature is called "Speed Dial BLF" in `addPhone` but appears as "Busy Lamp Field" in `getPhone` responses. Extractors handle both.
- **Building button templates on a test cluster (AXL 15.0, 2026-03-25).** In `addPhoneButtonTemplate`, list only the **non-fixed** buttons: a position with `isFixedFeature=true` in the base template returns `-201` "syntax error". `updatePhoneButtonTemplate` with `<buttons>` always failed, so buttons are set only when the template is created. `listPhoneButtonTemplate` `returnedTags` accepts only `<name>` and `<isUserModifiable>` (not `<basePhoneTemplateName>`). TypeFeature values: Line 9, Speed Dial 2, Speed Dial BLF 21, Call Park 126, Intercom 23, Service URL 20, Privacy 19, Do Not Disturb 130, None 255. Button counts: 8845 = 10 (none fixed), 7841 = 10 (1 and 5–10 fixed), 9861 = 130 (1 fixed; 11–130 are the KEM), 8875 = 108, 9871 = 32. Softkey templates cannot be created over SQL either (an INSERT is blocked by triggers; use the CUCM admin page); assigning one works through `updatePhone <softkeyTemplateName>`.
- **Speed dials and BLF on a phone.** A speed dial's `<index>` is its button template `<buttonNumber>`. BLF takes `<blfDest>` (target DN) and `<routePartitionName>` on `updatePhone`; `<blfDirn>` always came back empty from `getPhone`, so the partition cannot be read from the BLF entry. BLF in the KEM range (index 12 on a 9861) worked.
- **Raw phones must be preserved.** `normalize_phone()` creates a `CanonicalDevice` but loses the raw dict. `pipeline.py` re-stores each phone as `MigrationObject(canonical_id="phone:{name}", pre_migration_state=phone)` so mappers can read `store.get_objects("phone")` and access `speeddials`, `busyLampFields`, and per-line call forwarding.
- **Unity Connection is optional.** If no Unity Connection config is present, `unity_connection.py` is skipped and `raw_data["voicemail"]["unity_user_settings"]` is absent.
- **Base station MACs require Cisco Bifrost.** DECT base station MAC validation requires the Cisco manufacturing database — fake MACs fail provisioning. Not an extraction issue but affects test beds.
- **CTI Route Points use protocol "CTI Route Point"** in AXL — different from standard phone protocols. Use that exact string in `addCTIRoutePoint`.
- **Pickup group members via `updateLine`**, not `addCallPickupGroup`. Creating a pickup group with `<members>` fails on CUCM 15.0 (null priority FK constraint). The extractor reads the existing members; provisioning test bed uses `updateLine` pattern.
- **`getPhone` now extracts device-settings fields.** `commonPhoneConfigName`, `productSpecificConfiguration`, `userLocale`, `networkLocale`, `dndOption`, `dndStatus`, and `enableExtensionMobility` are all in `PHONE_GET_RETURNED_TAGS` for the DeviceSettingsMapper.
- **InformationalExtractor fetches CPC details.** After listing Common Phone Configs, the extractor calls `getCommonPhoneConfig` per item to retrieve `vendorConfig` (model-specific XML settings).
