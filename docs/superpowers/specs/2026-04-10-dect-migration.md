# DECT Phone Migration for CUCM-to-Webex Pipeline

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline gap -- DECT phone discovery, assessment reporting, and automated provisioning

---

## 1. Problem Statement

DECT phones are completely absent from the migration pipeline. The current device extractor
discovers DECT handsets (Cisco 6823, 6825, 6825ip) via `listPhone` because CUCM registers them
as standard phones. However, the `classify_phone_model()` function in `cross_reference.py` has
no recognition of DECT model strings -- they fall through to `INCOMPATIBLE`, which is technically
wrong. DECT handsets are not desk phones that need hardware replacement; they are wireless
handsets that need a fundamentally different provisioning model on the Webex side.

### Why this matters

Webex Calling uses a **hierarchical DECT model** that has no analog in the CUCM flat-phone world:

```
DECT Network (per-location, named, model-specific)
  +-- Base Station (MAC-addressed, registered to network)
       +-- Handset (assigned to person/workspace/virtual-line, up to 2 lines)
```

CUCM treats DECT handsets as regular phones -- `SEP<MAC>` device names, line appearances on DNs,
device pool assignments. There is no CUCM concept of a "DECT network" or "base station" as a
managed software object. Base stations in CUCM are infrastructure devices managed outside AXL
(via the hardware itself or Cisco Prime Collaboration).

This architectural mismatch means:

1. **Detection gap:** DECT phones are classified `INCOMPATIBLE` and flagged for hardware
   replacement, which is misleading. The 6823/6825 hardware is perfectly valid for Webex DECT.
2. **Report gap:** The assessment report shows DECT handsets as "incompatible devices" without
   explaining that they need a different provisioning approach (DECT networks), not new hardware.
3. **Provisioning gap:** Even if detected correctly, the pipeline has no mapper, planner, or
   handler for the DECT network -> base station -> handset hierarchy.
4. **Decision gap:** No decision types exist for DECT-specific choices (network topology design,
   handset-to-user assignment strategy, multi-cell vs single-cell selection).

### Customer impact

DECT is heavily deployed in mid-market verticals:

- **Healthcare:** Nurses stations, mobile rounding, patient room overflow
- **Retail:** Stockroom, back office, floor coverage
- **Warehousing/Manufacturing:** Pick-pack areas, loading docks, floor supervisors
- **Hospitality:** Front desk coverage areas, housekeeping dispatch

A typical mid-market CUCM with 200-500 phones may have 20-80 DECT handsets (10-15% of the
phone inventory). Misclassifying these as "incompatible hardware" inflates the complexity score
and makes the migration look harder than it is.

---

## 2. CUCM Source Data

### 2a. How DECT appears in AXL

CUCM DECT handsets register as standard phones with specific model names. The `DeviceExtractor`
already discovers them via `listPhone` / `getPhone`. The key fields:

| AXL Field | Typical DECT Value | Notes |
|-----------|-------------------|-------|
| `name` | `SEP<12-hex-MAC>` | Standard phone naming, MAC of the handset |
| `model` | `Cisco 6823`, `Cisco 6825`, `Cisco IP Phone 6825` | Model variants |
| `product` | `Cisco 6823`, `Cisco 6825` | Product string |
| `class` | `Phone` | Same as desk phones |
| `protocol` | `SIP` | Always SIP for DECT |
| `devicePoolName` | `DP-Warehouse-Phones` | Device pool for location resolution |
| `ownerUserName` | `jsmith` or empty | Handset owner (may be unowned for shared) |
| `lines` | Standard line appearances | DN assignments, same as desk phones |
| `description` | Free text | Often contains "DECT" or location hints |

CUCM DECT model strings that need recognition:

```
"Cisco 6823"
"Cisco 6825"
"Cisco 6825ip"
"Cisco IP Phone 6823"
"Cisco IP Phone 6825"
"Cisco IP Phone 6825ip"
```

Note: the 6825ip is the IP-DECT variant (wired IP backhaul to handset). From a migration
standpoint, it is treated identically to the standard 6825.

### 2b. What AXL does NOT contain

CUCM AXL has **no objects** for:

- **DECT base stations** -- These are infrastructure devices managed outside CUCM. Their MACs
  are not stored in the CUCM database. The admin must provide base station MACs separately.
- **DECT network topology** -- CUCM does not know which handsets are associated with which
  base stations or how base stations are grouped into coverage zones.
- **Base station model (DBS-110 vs DBS-210)** -- This is a Webex-side configuration choice
  that depends on coverage requirements, not CUCM data.

### 2c. AXL queries needed

No new AXL queries are required. The existing `DeviceExtractor` already runs `listPhone` and
`getPhone` for all phones, including DECT handsets. The gap is in classification, not extraction.

However, the pipeline should also check for DECT-related device descriptions and device pool
naming patterns (e.g., "DECT", "Wireless", "Warehouse") as heuristics for grouping handsets
into coverage zones for the assessment report.

### 2d. Supplemental data (operator-provided)

For Phase 2 (automated provisioning), the operator must provide data that CUCM does not have:

| Data | Source | Required for |
|------|--------|-------------|
| Base station MAC addresses | Physical inventory / spreadsheet | Base station creation |
| Base station model (DBS-110/DBS-210) | Physical inventory | Network model selection |
| Base station to coverage zone mapping | Site survey / floor plans | Network topology design |
| DECT network naming convention | Operator preference | Network creation |

This data can be provided via a supplemental CSV/JSON file passed to a new `--dect-inventory`
flag on `wxcli cucm discover` or as a separate `wxcli cucm dect-inventory` command.

---

## 3. Webex Target APIs

### 3a. API hierarchy

The Webex DECT API surface lives under `/telephony/config/` and follows a strict hierarchy:

```
Location
  +-- DECT Network (name, model, access code)
       +-- Base Station (MAC address)
       +-- Handset (line 1: person/place, line 2: person/place/virtual_line)
```

**Dependency chain (creation order):**
1. Location must exist
2. DECT Network must be created in the location (returns `dectNetworkId`)
3. Base stations are added to the network by MAC address
4. Handsets are added to the network, referencing person/workspace IDs for line assignment

**Deletion order (reverse):**
1. Delete handsets (or bulk delete all)
2. Delete base stations (or bulk delete all)
3. Delete DECT network

### 3b. Full endpoint inventory

From `specs/webex-cloud-calling.json`, tag "DECT Devices Settings":

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/telephony/config/locations/{locationId}/dectNetworks` | Create DECT network |
| GET | `/telephony/config/dectNetworks` | List all DECT networks (org-wide) |
| GET | `/telephony/config/locations/{locationId}/dectNetworks/{dectNetworkId}` | Get network details |
| PUT | `/telephony/config/locations/{locationId}/dectNetworks/{dectNetworkId}` | Update network |
| DELETE | `/telephony/config/locations/{locationId}/dectNetworks/{dectNetworkId}` | Delete network |
| POST | `.../dectNetworks/{dectNetworkId}/baseStations` | Create base stations (bulk by MAC) |
| GET | `.../dectNetworks/{dectNetworkId}/baseStations` | List base stations |
| GET | `.../dectNetworks/{dectNetworkId}/baseStations/{baseStationId}` | Get base station detail |
| DELETE | `.../dectNetworks/{dectNetworkId}/baseStations/{baseStationId}` | Delete one base station |
| DELETE | `.../dectNetworks/{dectNetworkId}/baseStations` | Delete all base stations |
| POST | `.../dectNetworks/{dectNetworkId}/handsets` | Add single handset |
| POST | `.../dectNetworks/{dectNetworkId}/handsets/bulk` | Add up to 50 handsets |
| GET | `.../dectNetworks/{dectNetworkId}/handsets` | List handsets |
| GET | `.../dectNetworks/{dectNetworkId}/handsets/{handsetId}` | Get handset details |
| PUT | `.../dectNetworks/{dectNetworkId}/handsets/{handsetId}` | Update handset |
| DELETE | `.../dectNetworks/{dectNetworkId}/handsets/{handsetId}` | Delete single handset |
| DELETE | `.../dectNetworks/{dectNetworkId}/handsets` | Delete multiple/all handsets |

**Scopes:** `spark-admin:telephony_config_read` (GET), `spark-admin:telephony_config_write` (POST/PUT/DELETE).

### 3c. Key constraints

| Constraint | Value | Source |
|-----------|-------|--------|
| Max base stations per DBS-210 network | 254 | OpenAPI spec description |
| Max base stations per DBS-110 network | 1 | OpenAPI spec description |
| Max lines per DBS-210 network | 1000 | OpenAPI spec description |
| Max lines per DBS-110 network | 30 | OpenAPI spec description |
| Max handsets per bulk add | 50 | OpenAPI spec `items` array |
| Handset line 1 member types | PEOPLE, PLACE | wxc_sdk source |
| Handset line 2 member types | PEOPLE, PLACE, VIRTUAL_LINE | wxc_sdk source |
| Handset display name length | 1-16 characters | wxc_sdk source |
| Network name length | 1-40 characters | OpenAPI spec |
| Network display name length | max 11 characters | wxc_sdk source |
| Access code | 4 numeric digits, unique per location | wxc_sdk source |
| Base station MAC format | 12 hex characters (no separators) | OpenAPI spec examples |
| Base station MACs must be Cisco-manufactured | Yes | Cisco Bifrost validation |

### 3d. Webex DECT device models

From the Webex API `device_type_list` response (documented in `devices-dect.md`):

| Enum Value | Display Name | Base Stations | Line Ports |
|------------|-------------|---------------|------------|
| `dms_cisco_dbs110` | DMS Cisco DBS110 | 1 | 30 |
| `cisco_dect_110_base` | Cisco DECT 110 Base | 1 | 30 |
| `dms_cisco_dbs210` | DMS Cisco DBS210 | 250 | 1000 |
| `cisco_dect_210_base` | Cisco DECT 210 Base | 250 | 1000 |

---

## 4. Phase 1 -- Detection + Report (P0)

Phase 1 adds DECT detection, correct classification, and a dedicated report appendix section.
No new AXL queries. No new Webex API calls. Pure data classification and reporting.

### 4a. New compatibility tier: DECT

Add a sixth value to `DeviceCompatibilityTier` in `models.py`:

```python
class DeviceCompatibilityTier(str, Enum):
    NATIVE_MPP = "native_mpp"
    CONVERTIBLE = "convertible"
    WEBEX_APP = "webex_app"
    INFRASTRUCTURE = "infrastructure"
    INCOMPATIBLE = "incompatible"
    DECT = "dect"                      # NEW
```

This tier means: "hardware is Webex-compatible but requires DECT network provisioning, not
standard phone activation." It is distinct from `NATIVE_MPP` because the provisioning path is
fundamentally different (DECT network hierarchy vs. activation code).

### 4b. Model recognition in `classify_phone_model()`

Add a new pattern set in `cross_reference.py` checked before the `_NATIVE_MPP_PATTERNS` check:

```python
_DECT_PATTERNS = {
    "Cisco 6823", "Cisco 6825", "Cisco 6825ip",
    "Cisco IP Phone 6823", "Cisco IP Phone 6825", "Cisco IP Phone 6825ip",
}
```

In `classify_phone_model()`, add before the `_NATIVE_MPP_PATTERNS` check:

```python
if model in _DECT_PATTERNS:
    return DeviceCompatibilityTier.DECT
```

Also add a keyword fallback for model strings that contain "6823" or "6825" with "dect"
in the description (some CUCM instances use non-standard model names).

### 4c. Normalizer changes

`normalize_phone()` in `normalizers.py` requires no changes -- DECT handsets are already
normalized as `CanonicalDevice` objects with the correct MAC, model, line appearances, and
device pool assignment. The tier classification happens in `CrossReferenceBuilder._classify_phone_models()`,
which already calls `classify_phone_model()` and stores the result.

### 4d. Device mapper changes

`DeviceMapper` in `device_mapper.py` currently handles four tiers. Add a fifth branch for
`DeviceCompatibilityTier.DECT`:

```python
elif compatibility_tier == DeviceCompatibilityTier.DECT:
    # DECT handset -- hardware is compatible but needs DECT network provisioning.
    # Do NOT generate DEVICE_INCOMPATIBLE decision.
    # Mark as needs_dect_network in pre_migration_state for report/planner.
    device_obj.pre_migration_state["needs_dect_network"] = True
    device_obj.status = MigrationStatus.MAPPED
    result.objects_created += 1
```

This prevents the DECT handsets from getting false `DEVICE_INCOMPATIBLE` decisions.

### 4e. Device compatibility analyzer changes

`DeviceCompatibilityAnalyzer` in `analyzers/device_compatibility.py` currently emits
`DEVICE_INCOMPATIBLE` for anything not in the recognized tiers. It must skip `DECT`-tier
devices (no decision needed -- the hardware is fine).

### 4f. Complexity score impact

In `report/score.py`, the device compatibility factor currently counts DECT handsets as
incompatible, which inflates the score. With the `DECT` tier:

- DECT devices should be counted as **compatible with caveats** (similar weight to `CONVERTIBLE`,
  not `INCOMPATIBLE`).
- A new sub-factor "DECT networks required" can add a small fixed penalty (e.g., +3 per
  distinct device pool containing DECT handsets) to reflect the additional provisioning work.

### 4g. Assessment report: new appendix section "W. DECT Networks"

Add section W to `appendix.py` (after V. Extension Mobility):

**Content:**

1. **DECT Handset Inventory Table:**

   | Handset (Device Name) | Model | Owner | Extension | Device Pool | Location |
   |-----------------------|-------|-------|-----------|-------------|----------|

2. **Coverage Zone Analysis:**

   Group DECT handsets by device pool (which maps to location via `device_pool_to_location`).
   Each distinct device pool with DECT handsets represents an implied coverage zone.

   | Coverage Zone (Device Pool) | Location | Handset Count | Owner Count | Unowned Count |
   |---------------------------|----------|---------------|-------------|---------------|

3. **DECT Network Design Inputs:**

   Summary box with operator-facing guidance:
   - Total DECT handsets: N
   - Implied coverage zones: N (from device pool grouping)
   - Recommended: "Provide base station inventory (MAC addresses and model) for each
     coverage zone. See operator runbook section on DECT provisioning."
   - If handset count per zone > 30: "Multi-cell DBS-210 network recommended"
   - If handset count per zone <= 30: "Single-cell DBS-110 or multi-cell DBS-210"

4. **Shared DECT Handset Warning:**

   If any DECT handset has `ownerUserName = None`, flag it:
   "N DECT handsets have no owner. These may be shared/roaming handsets that need
   workspace assignment in Webex."

### 4h. Executive summary changes

In `executive.py`, the "What You Have" section (Page 2) currently shows device tier breakdown.
Add DECT to the device summary:

- Show "N DECT handsets across M coverage zones" as a line item in the Devices subsection.
- Do NOT count DECT handsets in the "incompatible" column.

### 4i. Cleanup command changes

`wxcli cleanup run` (in `commands/cleanup.py`) already handles DECT network deletion in
layer 6 (call features layer). The existing implementation in `_delete_dect_networks()` lists
all DECT networks per location and deletes them. No changes needed for Phase 1.

---

## 5. Phase 2 -- Automated Provisioning (P3)

Phase 2 adds the full DECT provisioning pipeline: new normalizer, mapper, planner expander,
and execution handlers. This is a P3 priority -- it depends on Phase 1 being complete and
on operator-provided base station inventory data.

### 5a. New canonical model: `CanonicalDECTNetwork`

Add to `models.py`:

```python
@dataclass
class CanonicalDECTNetwork:
    canonical_id: str               # "dect_network:{location_name}:{network_name}"
    provenance: Provenance
    status: MigrationStatus
    location_canonical_id: str      # FK to CanonicalLocation
    network_name: str               # 1-40 chars
    display_name: str | None        # max 11 chars, shown on handsets
    model: str                      # "DMS Cisco DBS210" or "DMS Cisco DBS110"
    access_code: str | None         # 4-digit shared code (None = per-handset)
    base_stations: list[dict]       # [{mac: str, zone_name: str}]
    handset_assignments: list[dict] # [{device_canonical_id, owner_canonical_id, line1_member_id, line2_member_id, display_name}]
    pre_migration_state: dict       # coverage zone heuristics, device pool source
```

### 5b. DECT normalizer

New function in `normalizers.py`: `normalize_dect_group()`.

This is NOT a per-device normalizer. It is a **post-normalization aggregation** that runs
after `normalize_phone()` has processed all phones. It groups DECT-tier devices by device
pool (coverage zone) and produces one `CanonicalDECTNetwork` per coverage zone.

**Input:** All `CanonicalDevice` objects with `compatibility_tier == "dect"` from the store.
**Output:** One `CanonicalDECTNetwork` per distinct device pool containing DECT handsets.

This normalizer must run in `pipeline.py` after the standard phone normalization loop,
similar to how `shared_lines` post-normalization works.

### 5c. DECT mapper

New file: `transform/mappers/dect_mapper.py`

```python
class DECTMapper(Mapper):
    name = "dect_mapper"
    depends_on = ["location_mapper", "device_mapper", "user_mapper"]
```

**What it does:**

1. Reads all `CanonicalDECTNetwork` objects from the store.
2. For each network, resolves the location via `device_pool_to_location` cross-refs.
3. Resolves handset owners via `device_owned_by_user` cross-refs.
4. If operator-provided base station inventory exists (from supplemental data), merges
   base station MACs into the network object.
5. Determines network model:
   - If handset count <= 30 and operator did not specify: default to DBS-110.
   - If handset count > 30 or operator specified DBS-210: use DBS-210.
6. Generates decisions for ambiguous cases (see section 6).

**Decisions generated:**
- `DECT_NETWORK_DESIGN` -- when coverage zone has > 30 handsets but no base station
  inventory was provided, or when multiple device pools map to the same location.
- `DECT_HANDSET_ASSIGNMENT` -- when a DECT handset has no owner and the mapper cannot
  determine whether it should be a person assignment or workspace assignment.

### 5d. Planner expander

New function in `execute/planner.py`: `_expand_dect_network()`

Produces operations in dependency order:

```
1. create_dect_network       (depends on: location exists)
2. create_base_stations      (depends on: dect_network created)
3. assign_handsets            (depends on: base_stations created + users/workspaces created)
```

Each operation maps to a handler function. The planner must enforce the dependency chain --
`create_base_stations` cannot run until `create_dect_network` returns the `dectNetworkId`,
and `assign_handsets` cannot run until both base stations exist and the handset owner
(person or workspace) has been created in Webex.

### 5e. Execution handlers

New handlers in `execute/handlers.py`:

**`handle_dect_network_create`**

```python
async def handle_dect_network_create(op, store, config, session):
    """Create a DECT network in the target location."""
    # POST /telephony/config/locations/{locationId}/dectNetworks
    body = {
        "name": op["network_name"],
        "model": op["model"],
        "defaultAccessCodeEnabled": op.get("access_code") is not None,
        "defaultAccessCode": op.get("access_code"),
        "displayName": op.get("display_name"),
    }
    result = session.post(url, json=body)
    return result["dectNetworkId"]
```

**`handle_dect_base_station_create`**

```python
async def handle_dect_base_station_create(op, store, config, session):
    """Add base stations to a DECT network by MAC address."""
    # POST .../dectNetworks/{dectNetworkId}/baseStations
    body = {"baseStationMacs": op["macs"]}
    result = session.post(url, json=body)
    # Check per-station results for failures
    return result
```

**`handle_dect_handset_assign`**

```python
async def handle_dect_handset_assign(op, store, config, session):
    """Assign handsets to users/workspaces in a DECT network."""
    # POST .../dectNetworks/{dectNetworkId}/handsets/bulk (up to 50)
    items = []
    for assignment in op["assignments"]:
        item = {
            "line1MemberId": assignment["line1_member_id"],
            "customDisplayName": assignment["display_name"],
        }
        if assignment.get("line2_member_id"):
            item["line2MemberId"] = assignment["line2_member_id"]
        items.append(item)
    # Chunk into batches of 50
    for batch in chunks(items, 50):
        body = {"items": batch}
        result = session.post(url, json=body)
        # Check per-item results
    return result
```

### 5f. Supplemental data ingestion

New CLI flag on `wxcli cucm discover`:

```
wxcli cucm discover --host <cucm> --user <user> --dect-inventory <path-to-csv>
```

CSV format:

```csv
coverage_zone,base_station_mac,base_station_model
Warehouse-Floor1,AABBCCDDEEFF,DBS-210
Warehouse-Floor1,112233445566,DBS-210
Lobby,FFEEDDCCBBAA,DBS-110
```

The `coverage_zone` column maps to CUCM device pool names. The pipeline matches each
DECT handset's device pool to the coverage zone to associate base stations with handsets.

If no `--dect-inventory` file is provided, Phase 1 detection and reporting still works.
Phase 2 provisioning generates `DECT_NETWORK_DESIGN` decisions that block execution until
the operator provides the base station data.

---

## 6. Pipeline Integration Summary

### 6a. New files

| File | Phase | Purpose |
|------|-------|---------|
| `transform/mappers/dect_mapper.py` | P2 | DECT network mapper |
| (no new extractor) | -- | Existing `DeviceExtractor` already captures DECT handsets |
| (no new normalizer file) | P1 | `normalize_dect_group()` added to `normalizers.py` |
| (no new analyzer file) | P1 | Changes to `DeviceCompatibilityAnalyzer` only |

### 6b. Modified files (Phase 1)

| File | Change |
|------|--------|
| `models.py` | Add `DECT` to `DeviceCompatibilityTier` enum |
| `transform/cross_reference.py` | Add `_DECT_PATTERNS` set, add DECT branch to `classify_phone_model()` |
| `transform/mappers/device_mapper.py` | Add `DECT` tier branch (skip incompatible decision, mark `needs_dect_network`) |
| `transform/analyzers/device_compatibility.py` | Skip `DECT`-tier devices in incompatible check |
| `report/score.py` | Count DECT as compatible-with-caveats, add DECT sub-factor |
| `report/appendix.py` | Add section W: DECT Networks |
| `report/executive.py` | Add DECT line item to device summary |
| `report/explainer.py` | Add `DECT_NETWORK_DESIGN` and `DECT_HANDSET_ASSIGNMENT` to `DECISION_TYPE_DISPLAY_NAMES` |

### 6c. Modified files (Phase 2)

| File | Change |
|------|--------|
| `models.py` | Add `CanonicalDECTNetwork` dataclass, add `DECT_NETWORK_DESIGN` and `DECT_HANDSET_ASSIGNMENT` to `DecisionType` |
| `transform/normalizers.py` | Add `normalize_dect_group()` post-normalization function |
| `transform/pipeline.py` | Call `normalize_dect_group()` after phone normalization |
| `transform/engine.py` | Register `DECTMapper` in mapper list |
| `execute/planner.py` | Add `_expand_dect_network()` expander |
| `execute/handlers.py` | Add `handle_dect_network_create`, `handle_dect_base_station_create`, `handle_dect_handset_assign` |
| `execute/dependency.py` | Add DECT operation types to DAG builder |
| `commands/cucm.py` | Add `--dect-inventory` option to `discover` command |

### 6d. Tier assignments

| Component | Tier |
|-----------|------|
| DECT model detection + `DeviceCompatibilityTier.DECT` | Tier 1 (core pipeline) |
| Report appendix section W | Tier 1 (assessment report) |
| Complexity score adjustment | Tier 1 (assessment report) |
| `CanonicalDECTNetwork` model + normalizer | Tier 2 (extended pipeline) |
| `DECTMapper` + decisions | Tier 2 (extended pipeline) |
| Planner expander + execution handlers | Tier 3 (execution) |
| Supplemental data ingestion (`--dect-inventory`) | Tier 3 (execution) |

---

## 7. Decision Types

### 7a. `DECT_NETWORK_DESIGN`

**When generated:** The `DECTMapper` generates this decision when it cannot automatically
determine the DECT network configuration for a coverage zone.

**Trigger conditions:**
- Coverage zone has > 30 DECT handsets but no base station inventory was provided
  (cannot determine DBS-110 vs DBS-210 without knowing how many base stations exist).
- Multiple device pools with DECT handsets map to the same Webex location (should they
  be one DECT network or multiple?).
- Operator-provided base station count exceeds the network model limit (e.g., 2 base
  station MACs provided for a DBS-110 network, which only supports 1).

**Severity:** `warning` (blocks execution but not analysis)

**Options:**
- `single_network_dbs210` -- Create one DBS-210 multi-cell network for the location.
  All base stations and handsets in that location go into this network.
- `per_zone_networks` -- Create separate DECT networks per device pool / coverage zone.
  Requires operator to provide zone-to-base-station mapping.
- `manual` -- Operator will design DECT networks manually in Control Hub after migration.

**Context fields:**
- `location_name`: Target Webex location
- `zone_count`: Number of distinct device pools with DECT handsets
- `total_handsets`: Total DECT handset count in the location
- `handsets_per_zone`: Dict of zone_name -> handset count
- `base_stations_provided`: Boolean, whether operator provided inventory

### 7b. `DECT_HANDSET_ASSIGNMENT`

**When generated:** The `DECTMapper` generates this decision when a DECT handset cannot be
automatically assigned to a person or workspace.

**Trigger conditions:**
- DECT handset has no `ownerUserName` in CUCM (unowned handset). Could be a shared/roaming
  handset that should become a workspace assignment, or could be a data quality issue.
- DECT handset owner maps to a user who is being migrated as `DEVICE_WEBEX_APP` (user is
  transitioning to Webex App and won't have a DECT handset in Webex).

**Severity:** `info` (non-blocking, handset can be skipped)

**Options:**
- `assign_workspace` -- Create a Webex workspace for this handset and assign it as a PLACE.
- `assign_person` -- Assign to a specific person (operator provides person ID/email).
- `skip` -- Do not migrate this handset.

**Context fields:**
- `device_name`: CUCM device name (SEP...)
- `model`: Phone model
- `extension`: DN/extension on the handset
- `device_pool`: Source device pool name
- `owner_status`: "unowned" | "owner_transitioning_to_app"

---

## 8. Report Changes

### 8a. Appendix section "W. DECT Networks"

Detailed specification for the new appendix section, rendered as a collapsible `<details>`
element consistent with sections A-V.

**Section structure:**

```html
<details>
  <summary><span class="section-indicator">W</span> DECT Networks</summary>

  <!-- Subsection 1: Inventory -->
  <h4>DECT Handset Inventory</h4>
  <table>...</table>

  <!-- Subsection 2: Coverage zones -->
  <h4>Coverage Zone Analysis</h4>
  <table>...</table>

  <!-- Subsection 3: Design inputs -->
  <h4>DECT Network Design Inputs</h4>
  <div class="callout-box">...</div>

  <!-- Subsection 4: Warnings (conditional) -->
  <h4>Shared Handset Warnings</h4>
  <div class="callout-box warning">...</div>
</details>
```

**Data access pattern:**

```python
def _dect_networks_group(store: MigrationStore) -> str:
    devices = store.get_objects("device")
    dect_devices = [d for d in devices if d.get("compatibility_tier") == "dect"]
    if not dect_devices:
        return ""
    # Group by device pool (coverage zone)
    # Build inventory table, zone analysis, design inputs
```

### 8b. Executive summary device chart

The stacked bar chart in appendix section D (Device Inventory) and the donut chart in
the executive summary must include DECT as a distinct segment:

- **Color:** Use a distinct color (not teal/gray/amber) -- suggest blue-400 (#42A5F5) to
  differentiate from the teal-primary palette.
- **Label:** "DECT" in the legend.
- **Tooltip:** "N DECT handsets -- compatible hardware, requires DECT network provisioning."

### 8c. Sidebar navigation

Add "W" to the lettered sidebar nav in `assembler.py`. The section shows as "W. DECT Networks"
in the step-list nav panel.

---

## 9. Documentation Updates Required

Every file that needs updating after implementation, with the specific section and content.

### 9a. CLAUDE.md files

| File | Section | What to add |
|------|---------|-------------|
| `/CLAUDE.md` (project root) | Known Issues | Add item 15: "DECT handsets classified as separate tier. Provisioning requires operator-provided base station inventory." |
| `/CLAUDE.md` (project root) | File Map > Migration Knowledge Base | Add `kb-dect-migration.md` entry if a KB doc is created |
| `src/wxcli/migration/CLAUDE.md` | File Map table | Add `dect_mapper.py` entry, update normalizer count (37 -> 38), update model count |
| `src/wxcli/migration/CLAUDE.md` | Known Issues | Add: "DECT base station MACs must be Cisco-manufactured (Bifrost validation). Fake MACs fail provisioning." |
| `src/wxcli/migration/transform/CLAUDE.md` | Pass 1: Normalizers | Update normalizer count, add `normalize_dect_group()` description |
| `src/wxcli/migration/transform/CLAUDE.md` | Key Gotchas | Add: "DECT normalizer is post-normalization (like shared_lines), not per-device." |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Mapper Inventory | Add `DECTMapper` to Tier 3 table (depends on location/device/user mappers) |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Key Gotchas | Add DECT base station MAC gotcha (Bifrost validation) |
| `src/wxcli/migration/cucm/CLAUDE.md` | Key Gotchas | Already has the Bifrost note -- verify it is still accurate |
| `src/wxcli/migration/report/CLAUDE.md` | appendix.py line | Update section count "22 lettered sections A-V" -> "23 lettered sections A-W" |
| `src/wxcli/migration/report/CLAUDE.md` | Device Compatibility | Add `"dect"` to the tier list |
| `src/wxcli/migration/execute/CLAUDE.md` | Handler list | Add 3 new DECT handlers |

### 9b. Reference docs

| File | Section | What to add |
|------|---------|-------------|
| `docs/reference/devices-dect.md` | Common Gotchas | Add: "CUCM DECT handsets (6823/6825) register as standard phones in AXL. Migration pipeline classifies them as DECT tier and provisions via DECT network hierarchy." |
| `docs/reference/devices-dect.md` | (new section) | Add "Migration from CUCM" section referencing the pipeline's DECT handling |

### 9c. Runbooks

| File | Section | What to add |
|------|---------|-------------|
| `docs/runbooks/cucm-migration/operator-runbook.md` | Prerequisites | Add: "If CUCM has DECT handsets, prepare a base station inventory CSV." |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Pipeline Steps > Discover | Document `--dect-inventory` flag |
| `docs/runbooks/cucm-migration/decision-guide.md` | Decision Types | Add entries for `DECT_NETWORK_DESIGN` and `DECT_HANDSET_ASSIGNMENT` |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Config Keys | Add any DECT-related config keys (e.g., `dect.default_model`, `dect.default_access_code`) |

### 9d. Knowledge base

| File | Section | What to add |
|------|---------|-------------|
| `docs/knowledge-base/migration/kb-device-migration.md` | Device replacement paths | Add DECT section: 6823/6825 are compatible, need DECT network provisioning |
| `docs/knowledge-base/migration/kb-webex-limits.md` | Platform hard limits | Add DECT limits: 254 base stations per DBS-210, 1000 lines, 30 lines per DBS-110 |

### 9e. Skills

| File | Section | What to add |
|------|---------|-------------|
| `.claude/skills/cucm-migrate/SKILL.md` | Step 1 (preflight) or Step 2 (plan summary) | Add DECT network provisioning to the plan summary template |
| `.claude/skills/manage-devices/SKILL.md` | DECT section | Verify DECT provisioning guidance is up to date |

### 9f. Advisory system

| File | Section | What to add |
|------|---------|-------------|
| `src/wxcli/migration/advisory/recommendation_rules.py` | Rule list | Add rule for `DECT_NETWORK_DESIGN` and `DECT_HANDSET_ASSIGNMENT` |
| `src/wxcli/migration/advisory/advisory_patterns.py` | Pattern list | Add cross-cutting pattern: "DECT deployment detected" with guidance on base station inventory |
| `src/wxcli/migration/report/explainer.py` | `DECISION_TYPE_DISPLAY_NAMES` | Add "DECT Network Design" and "DECT Handset Assignment" |

---

## 10. Test Strategy

### 10a. Phase 1 tests (detection + report)

**Model classification tests** (`tests/migration/transform/test_cross_reference.py`):

```python
# New DECT model recognition
def test_classify_dect_6823():
    assert classify_phone_model("Cisco 6823") == DeviceCompatibilityTier.DECT

def test_classify_dect_6825():
    assert classify_phone_model("Cisco 6825") == DeviceCompatibilityTier.DECT

def test_classify_dect_6825ip():
    assert classify_phone_model("Cisco 6825ip") == DeviceCompatibilityTier.DECT

def test_classify_dect_ip_phone_6825():
    assert classify_phone_model("Cisco IP Phone 6825") == DeviceCompatibilityTier.DECT

# Ensure DECT does NOT match native MPP (6821/6841/6851 are desk phones, not DECT)
def test_6821_is_not_dect():
    assert classify_phone_model("Cisco 6821") == DeviceCompatibilityTier.NATIVE_MPP

def test_6841_is_not_dect():
    assert classify_phone_model("Cisco 6841") == DeviceCompatibilityTier.NATIVE_MPP
```

**Device mapper tests** (`tests/migration/transform/mappers/test_device_mapper.py`):

```python
def test_dect_handset_not_flagged_incompatible():
    """DECT handsets should NOT generate DEVICE_INCOMPATIBLE decisions."""
    # Setup: phone with model "Cisco 6825", DECT tier
    # Assert: no DEVICE_INCOMPATIBLE decision
    # Assert: device.pre_migration_state["needs_dect_network"] is True

def test_dect_handset_mapped_status():
    """DECT handsets should reach MAPPED status, not NEEDS_DECISION."""
    # Assert: device.status == MigrationStatus.MAPPED
```

**Device compatibility analyzer tests** (`tests/migration/transform/analyzers/test_device_compatibility.py`):

```python
def test_dect_devices_skipped_by_analyzer():
    """DECT-tier devices should not appear in analyzer output."""
    # Setup: mix of incompatible + DECT devices
    # Assert: only incompatible devices generate decisions
```

**Report appendix tests** (`tests/migration/report/test_appendix.py` or new file):

```python
def test_appendix_section_w_present_with_dect():
    """Section W appears when DECT devices exist in the store."""
    # Setup: store with DECT-tier devices
    # Assert: "DECT Networks" in appendix HTML

def test_appendix_section_w_absent_without_dect():
    """Section W is omitted when no DECT devices exist."""
    # Setup: store with only desk phones
    # Assert: "DECT Networks" not in appendix HTML

def test_appendix_section_w_coverage_zones():
    """Coverage zones are grouped by device pool."""
    # Setup: 10 DECT handsets across 3 device pools
    # Assert: 3 rows in coverage zone table

def test_appendix_section_w_unowned_warning():
    """Shared handset warning appears when unowned DECT devices exist."""
    # Setup: DECT handset with no ownerUserName
    # Assert: warning text present
```

**Complexity score tests** (`tests/migration/report/test_score.py`):

```python
def test_dect_not_counted_as_incompatible():
    """DECT devices should not inflate the incompatible device count."""
    # Setup: 10 desk phones (native_mpp) + 5 DECT handsets + 2 incompatible
    # Assert: incompatible count == 2, not 7

def test_dect_adds_small_penalty():
    """DECT presence adds a small complexity penalty, not a large one."""
    # Setup: environment with DECT handsets
    # Assert: penalty is proportional to zone count, not handset count
```

### 10b. Phase 2 tests (provisioning)

**DECT normalizer tests** (`tests/migration/transform/test_normalizers.py`):

```python
def test_normalize_dect_group_creates_networks():
    """Post-normalization groups DECT devices by device pool into networks."""
    # Setup: 5 DECT devices in DP-Warehouse, 3 in DP-Lobby
    # Assert: 2 CanonicalDECTNetwork objects created

def test_normalize_dect_group_empty_when_no_dect():
    """No networks created when no DECT devices exist."""

def test_normalize_dect_group_handset_assignments():
    """Each network's handset_assignments contains the correct devices."""
```

**DECT mapper tests** (`tests/migration/transform/mappers/test_dect_mapper.py`):

```python
def test_dect_mapper_resolves_locations():
    """Mapper resolves device pool to location for each DECT network."""

def test_dect_mapper_design_decision_no_inventory():
    """DECT_NETWORK_DESIGN generated when no base station inventory provided."""

def test_dect_mapper_design_decision_multi_zone():
    """DECT_NETWORK_DESIGN generated when multiple zones map to same location."""

def test_dect_mapper_handset_decision_unowned():
    """DECT_HANDSET_ASSIGNMENT generated for unowned handsets."""

def test_dect_mapper_auto_selects_dbs110_small_zone():
    """Zones with <= 30 handsets default to DBS-110."""

def test_dect_mapper_auto_selects_dbs210_large_zone():
    """Zones with > 30 handsets require DBS-210."""
```

**Planner tests** (`tests/migration/execute/test_planner.py`):

```python
def test_expand_dect_network_dependency_order():
    """DECT operations follow create_network -> create_base_stations -> assign_handsets."""

def test_expand_dect_network_handset_batching():
    """Handset assignments are batched into groups of 50."""
```

**Handler tests** (`tests/migration/execute/test_handlers.py`):

```python
def test_handle_dect_network_create():
    """Creates DECT network via POST and returns dectNetworkId."""

def test_handle_dect_base_station_create():
    """Adds base stations by MAC address."""

def test_handle_dect_handset_assign_bulk():
    """Assigns handsets in bulk batches of 50."""

def test_handle_dect_handset_assign_with_line2():
    """Handset with line 2 (virtual line) is included in payload."""
```

### 10c. Integration / end-to-end test scenarios

**Scenario 1: Pure desk phone environment (regression)**

- 50 desk phones (mix of 7800/8800/9800 series), zero DECT.
- Assert: no section W in report, no DECT-related decisions, same complexity score as before.

**Scenario 2: Mixed DECT + desk phone environment**

- 40 desk phones + 15 DECT handsets (6825) across 2 device pools.
- Assert: section W present with 2 coverage zones, DECT handsets not counted as incompatible,
  complexity score reflects DECT presence with small penalty.

**Scenario 3: Large DECT deployment**

- 200 DECT handsets across 5 device pools, some with > 30 handsets.
- Assert: `DECT_NETWORK_DESIGN` decisions for large zones, DBS-210 recommended where
  handset count exceeds 30.

**Scenario 4: Unowned DECT handsets**

- 10 DECT handsets, 3 without owners.
- Assert: 3 `DECT_HANDSET_ASSIGNMENT` decisions generated, warning in appendix section W.

**Scenario 5: DECT with supplemental base station inventory**

- 20 DECT handsets + operator CSV with 4 base station MACs across 2 zones.
- Assert: base station MACs merged into `CanonicalDECTNetwork`, no `DECT_NETWORK_DESIGN`
  decision (sufficient data), planner produces create_network -> create_base_stations ->
  assign_handsets operations.

---

## 11. Open Questions

1. **6825ip handling:** Should the 6825ip (IP-DECT with wired IP backhaul) be treated
   identically to the wireless 6825, or does it need a separate provisioning path? Current
   assumption: identical treatment, but this needs verification against the Webex DECT API
   (does Webex support IP-DECT mode, or is it wireless-only?).

2. **CUCM DECT integration pages:** Some CUCM versions have a "DECT" section in the
   administration UI that is not exposed via AXL. If there is useful data there (e.g., base
   station registrations, coverage maps), it would need a separate extraction method. Current
   assumption: this data is not available via AXL and is not needed for Phase 1.

3. **Multi-cell repeater support:** The DBS-210 supports repeater base stations for extended
   coverage. The Webex API does not distinguish between primary and repeater base stations --
   all are registered by MAC. Confirm that repeater stations are treated identically in the
   API.

4. **Access code strategy:** When migrating from CUCM (which has no per-handset access codes),
   should the pipeline default to shared access codes (simpler) or per-handset auto-generated
   codes (more secure)? This may warrant a config key (`dect.access_code_mode: shared|per_handset`).

5. **Handset MAC preservation:** CUCM stores the handset MAC in the device name (`SEP<MAC>`).
   Webex assigns handset MACs when they pair with base stations. Confirm that there is no need
   to pre-register handset MACs in Webex -- the handset-to-user assignment is the mapping, not
   the MAC.

6. **Cleanup ordering:** The existing `wxcli cleanup` deletes DECT networks in the call features
   layer (layer 6). With the new DECT tier classification, verify that cleanup still correctly
   discovers and deletes DECT networks, even though the devices are now classified differently
   in the migration store.
