# Tier 3: Informational Extraction for Assessment Report

## Context

The CUCM-to-Webex migration pipeline produces an assessment report (`wxcli cucm report`). Currently the report covers the 26 canonical types that have full extract → normalize → map → analyze pipelines. Tier 3 adds 20 CUCM object types that have **no Webex equivalent** — they're extracted purely to tell the customer what they're losing, what's handled by the cloud, and what needs manual reconfiguration.

**Key difference from Tier 2:** No mappers, analyzers, or execution handlers. Data flows: `extractor → store → report appendix`. One new extractor class handles all 20 types.

**Read these files first:**
- `src/wxcli/migration/cucm/CLAUDE.md` — extractor architecture
- `src/wxcli/migration/cucm/extractors/base.py` — `BaseExtractor` ABC and `ExtractionResult`
- `src/wxcli/migration/report/CLAUDE.md` — report architecture, appendix pattern
- `src/wxcli/migration/report/appendix.py` — how existing appendix sections work
- `docs/plans/cucm-pipeline/future/expansion-scope.md` — Tier 3 section (the spec)
- `src/wxcli/migration/models.py` — `MigrationObject` base class (Tier 3 uses this directly, no new canonical types)

## The 20 Object Types (4 Categories)

### Category 1: Cloud-Managed (7 types)
These CUCM objects are handled automatically by the Webex cloud. Report message: "No migration action needed — Webex manages this automatically."

| AXL Method | Object | Report Note |
|------------|--------|-------------|
| `listRegion` | Regions | Bandwidth management → cloud-managed |
| `listSrst` | SRST References | Survivability → cloud-managed (Survivable Gateway is Webex equivalent) |
| `listMediaResourceGroup` | Media Resource Groups | Transcoding/conferencing → cloud-managed |
| `listMediaResourceList` | Media Resource Lists | MRG ordering → cloud-managed |
| `listAarGroup` | AAR Groups | Automated Alternate Routing → cloud-managed |
| `listDeviceMobilityGroup` | Device Mobility Groups | Device mobility → cloud-managed (Webex uses location-based routing) |
| `listConferenceBridge` | Conference Bridges | Hardware conference bridges → cloud-managed |

### Category 2: Not Migratable / Feature Gaps (3 types)
No Webex equivalent exists. Report message: "This CUCM feature has no Webex equivalent — functionality will be lost."

| AXL Method | Object | Report Note |
|------------|--------|-------------|
| `listSoftkeyTemplate` | Softkey Templates | No equivalent (9800-series uses PSK, covered by Tier 1) |
| `listIpPhoneService` | IP Phone Services | XML services → no equivalent (Webex app replaces most use cases) |
| N/A (SQL: `SELECT * FROM intercom WHERE ...`) | Intercom DNs | No native equivalent (workaround: speed dial + auto-answer) |

### Category 3: Different Architecture (6 types)
Webex has equivalent functionality but configured differently. Report message: "Must be reconfigured manually in Webex Control Hub."

| AXL Method | Object | Report Note |
|------------|--------|-------------|
| `listCommonPhoneConfig` | Common Phone Profiles | → Webex device configuration templates |
| `listPhoneButtonTemplate` | Phone Button Templates | → Webex line key templates (already covered by Tier 1 mapper) |
| `listFeatureControlPolicy` | Feature Control Policies | → Webex calling policies (org/location level) |
| `listCredentialPolicy` | Credential Policies | → Webex SSO/password policies |
| `listRecordingProfile` | Recording Profiles | → Webex call recording settings |
| `listLdapDirectory` | LDAP Directories | → Webex directory sync (Azure AD/Okta/SCIM) |

### Category 4: Migration Planning Input (4 types)
Data that informs migration planning decisions.

| AXL Method | Object | Report Note |
|------------|--------|-------------|
| `listAppUser` | Application Users | Detects JTAPI/TAPI apps, CER presence, recording integrations |
| `listH323Gateway` | H.323 Gateways | ATA migration planning (analog lines) |
| `getEnterprise` (single call) | Enterprise Parameters | Cluster configuration baseline |
| `listProcessConfig` (filtered) | Service Parameters | Telephony service configuration |

## Implementation

### Step 1: Create the Informational Extractor

Create `src/wxcli/migration/cucm/extractors/informational.py`:

```python
"""Tier 3: Informational extraction — CUCM objects with no Webex equivalent.

Extracted for assessment report only. No canonical types, no mappers.
Objects stored as MigrationObject with object_type="info_{type_name}".
"""

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

# Each entry: (object_type_suffix, axl_list_method, search_criteria, returned_tags, category)
INFORMATIONAL_TYPES = [
    # Category 1: Cloud-managed
    ("region", "listRegion", {"name": "%"}, {"name": "", "defaultCodec": ""}, "cloud_managed"),
    ("srst", "listSrst", {"name": "%"}, {"name": "", "ipAddress": "", "port": ""}, "cloud_managed"),
    ("media_resource_group", "listMediaResourceGroup", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("media_resource_list", "listMediaResourceList", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("aar_group", "listAarGroup", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("device_mobility_group", "listDeviceMobilityGroup", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("conference_bridge", "listConferenceBridge", {"name": "%"}, {"name": "", "description": "", "product": ""}, "cloud_managed"),
    # Category 2: Not migratable
    ("ip_phone_service", "listIpPhoneService", {"name": "%"}, {"name": "", "url": "", "serviceType": ""}, "not_migratable"),
    # Category 3: Different architecture
    ("common_phone_config", "listCommonPhoneConfig", {"name": "%"}, {"name": "", "description": ""}, "different_arch"),
    ("feature_control_policy", "listFeatureControlPolicy", {"name": "%"}, {"name": "", "description": ""}, "different_arch"),
    ("credential_policy", "listCredentialPolicy", {"name": "%"}, {"name": "", "description": ""}, "different_arch"),
    ("recording_profile", "listRecordingProfile", {"name": "%"}, {"name": "", "recorderDestination": ""}, "different_arch"),
    ("ldap_directory", "listLdapDirectory", {"name": "%"}, {"name": "", "ldapDn": ""}, "different_arch"),
    # Category 4: Planning input
    ("app_user", "listAppUser", {"userid": "%"}, {"userid": "", "description": "", "associatedDevices": ""}, "planning"),
    ("h323_gateway", "listH323Gateway", {"name": "%"}, {"name": "", "description": "", "product": ""}, "planning"),
]
```

The extractor should:
1. Iterate `INFORMATIONAL_TYPES`, call `paginated_list()` for each
2. Store results as `MigrationObject(canonical_id=f"info_{suffix}:{name}", object_type=f"info_{suffix}", pre_migration_state=raw_dict)`
3. Handle softkey templates separately (SQL, not AXL list — see existing `templates.py` pattern)
4. Handle intercom separately (SQL query for intercom DNs)
5. Handle enterprise params (single `getEnterprise` call, not paginated)
6. Handle service params (`listProcessConfig` filtered to telephony services)
7. Return `ExtractionResult` with total counts per type

### Step 2: Register in Discovery Pipeline

In `src/wxcli/migration/cucm/discovery.py`:
1. Import `InformationalExtractor`
2. Add to `EXTRACTOR_ORDER` (last position — no dependencies)
3. Store results under `raw_data["informational"]` key

### Step 3: Add Normalizer Pass-Through

In `src/wxcli/migration/transform/normalizers.py`:
- Add a simple normalizer that stores informational objects as-is (no transformation needed)
- Add entries to `RAW_DATA_MAPPING` for the `"informational"` extractor key

### Step 4: Add Report Appendix Sections

In `src/wxcli/migration/report/appendix.py`, add 4 new collapsible sections:

**Section O: Cloud-Managed Resources** — Table of resources Webex handles automatically. Columns: Type, Count, Note.

**Section P: Feature Gaps** — Table of CUCM features with no Webex equivalent. Columns: Feature, Count, Impact, Workaround.

**Section Q: Manual Reconfiguration** — Table of features that need manual Webex setup. Columns: Feature, Count, Webex Equivalent.

**Section R: Planning Inputs** — Table of data for migration planning. Subsections for Application Users (flag JTAPI/CER), H.323 Gateways (flag analog lines), Enterprise/Service Parameters.

Each section follows the existing appendix pattern: `<details><summary>` with count badge, table inside.

### Step 5: Update Executive Summary

In `src/wxcli/migration/report/executive.py`:
- Add a "Migration Coverage" callout showing: X types fully mapped, Y types informational-only, Z types not migratable
- Add summary counts for each category to the environment overview

### Step 6: Update Score Algorithm (Optional)

In `src/wxcli/migration/report/score.py`:
- Consider adding a small weight for informational types that indicate complexity (e.g., many application users → integration complexity, H.323 gateways → analog line migration)
- This is optional — the existing 7-factor algorithm may be sufficient

## Tests

- **Extractor tests:** Mock AXL connection, verify each of the 20 types extracts correctly, verify SQL fallback for softkeys/intercom
- **Report tests:** Verify new appendix sections render with mock data, verify counts are correct
- **Integration test:** Run full pipeline with informational data, verify objects appear in store and report

## Verification

```bash
python3.11 -m pytest tests/migration/ -x -q  # All tests pass
wxcli cucm discover --verbose  # Should show informational extraction counts
wxcli cucm normalize --verbose  # info_* objects in store
wxcli cucm report --brand "Test" --prepared-by "Test"  # Sections O-R visible
```

## What NOT to Do

- Don't create canonical types for Tier 3 objects — use `MigrationObject` directly with `object_type="info_{name}"`
- Don't create mappers or analyzers — data goes straight to report
- Don't create execution handlers — nothing to execute
- Don't add to the planner — these objects have no migration operations
- Don't modify existing extractors — create the new `InformationalExtractor` alongside them
