# cucm/ — CUCM Extraction Layer (Phase 03)

Connects to CUCM via AXL SOAP and extracts raw configuration into the SQLite store. Output is `DiscoveryResult.raw_data` — a dict of dicts of lists that feeds directly into `transform/pipeline.py:normalize_discovery()`.

## Files

| File | Purpose |
|------|---------|
| `connection.py` | `AXLConnection` — zeep SOAP client with certificate handling and retry |
| `discovery.py` | `run_discovery(store, config)` — orchestrates all extractors in order, writes results to store |
| `unity_connection.py` | `UnityConnectionClient` — REST client for Unity Connection per-user VM settings |
| `extractors/base.py` | `BaseExtractor` ABC + `ExtractionResult` dataclass |
| `extractors/devices.py` | Phones (SEP), device pools, button templates, softkey templates |
| `extractors/features.py` | Hunt pilots/lists/groups, call park, pickup groups, CTI route points, paging groups |
| `extractors/locations.py` | CUCM locations, device pools, datetime groups |
| `extractors/routing.py` | Gateways, SIP trunks, route groups, route lists, route patterns, CSS, partitions |
| `extractors/shared_lines.py` | Shared line detection (post-normalization, not an AXL extractor) |
| `extractors/templates.py` | Button templates + softkey templates (via SQL — AXL doesn't expose softkey template list) |
| `extractors/users.py` | EndUsers, lines (DNs), voicemail profiles |
| `extractors/voicemail.py` | Unity Connection voicemail pilot, voicemail profiles |
| `extractors/helpers.py` | `to_list()`, zeep response normalization helpers |
| `extractors/workspaces.py` | Common-area phone workspace classification (post-normalization) |

## Extraction Order

```
locations → users → devices → features → routing → templates → voicemail
```

Extractors are independent at extraction time — the order is a documentation convention, not a dependency constraint. All raw dicts go into `raw_data` keyed by extractor name.

## raw_data Structure

`raw_data` is a `dict[str, dict[str, list]]`:
- Top key = extractor group (`"devices"`, `"users"`, `"features"`, etc.)
- Inner key = object type (`"phones"`, `"users"`, `"button_templates"`, etc.)
- Value = list of raw CUCM dicts (as returned by zeep, pre-normalized by `to_list()`)

`normalize_discovery()` in `transform/pipeline.py` consumes `raw_data` via `RAW_DATA_MAPPING`.

## Key Gotchas

- **Softkey templates require SQL.** `addSoftkeyTemplate`/`listSoftkeyTemplate` don't exist in AXL v15.0. The `TemplateExtractor` uses direct SQL (`executeSQLQuery`) to fetch softkey template data. See `extractors/templates.py`.
- **Button templates use `<buttonNumber>` not `<index>`** in `addPhoneButtonTemplate`. The extractor normalizes this on the way out.
- **BLF name mismatch.** The feature is called "Speed Dial BLF" in `addPhone` but appears as "Busy Lamp Field" in `getPhone` responses. Extractors handle both.
- **Raw phones must be preserved.** `normalize_phone()` creates a `CanonicalDevice` but loses the raw dict. `pipeline.py` re-stores each phone as `MigrationObject(canonical_id="phone:{name}", pre_migration_state=phone)` so mappers can read `store.get_objects("phone")` and access `speeddials`, `busyLampFields`, and per-line call forwarding.
- **Unity Connection is optional.** If no Unity Connection config is present, `unity_connection.py` is skipped and `raw_data["voicemail"]["unity_user_settings"]` is absent.
- **Base station MACs require Cisco Bifrost.** DECT base station MAC validation requires the Cisco manufacturing database — fake MACs fail provisioning. Not an extraction issue but affects test beds.
- **CTI Route Points use protocol "CTI Route Point"** in AXL — different from standard phone protocols. Use that exact string in `addCTIRoutePoint`.
- **Pickup group members via `updateLine`**, not `addCallPickupGroup`. Creating a pickup group with `<members>` fails on CUCM 15.0 (null priority FK constraint). The extractor reads the existing members; provisioning test bed uses `updateLine` pattern.
