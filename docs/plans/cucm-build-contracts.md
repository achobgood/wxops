# CUCM→Webex Migration Pipeline — Interface Contracts, Acceptance Criteria, Parallelization

Part 2 of 3 in the build planning sequence. Defines the exact data contracts between pipeline layers, testable acceptance criteria per phase, parallelization map, and testing strategy.

**Inputs:** [`cucm-build-strategy.md`](cucm-build-strategy.md) (Part 1: build order, risk spikes, anti-patterns), [`cucm-pipeline-architecture.md`](cucm-pipeline-architecture.md) (summary), pipeline detail docs [`01-07`](cucm-pipeline/).

---

## 1. Interface Contracts

### Layer 1 → Everything: Canonical Pydantic Models

**Source:** `cucm-wxc-migration.md` lines 112-191 (canonical model definitions), `01-data-representation.md` (SQLite schema)

Every module above Layer 1 imports these types. The canonical models are the lingua franca of the pipeline.

#### MigrationObject (base class)

**Source:** `cucm-wxc-migration.md` lines 133-143

```python
class MigrationObject(BaseModel):
    canonical_id: str                    # "{object_type}:{cucm_pkid}" (from 07-idempotency-resumability.md)
    provenance: Provenance               # source_system, source_id, source_name, cluster, extracted_at, cucm_version
    status: MigrationStatus = "discovered"  # discovered → normalized → analyzed → planned (from 07, "Object Status" section)
    webex_id: str | None = None          # populated after execution
    pre_migration_state: dict | None = None  # Webex state before migration (for rollback)
    errors: list[str] = []
    warnings: list[str] = []
    depends_on: list[str] = []           # canonical_ids of prerequisites
    batch: str | None = None
```

**Key fields other layers depend on:**

| Field | Used by | Purpose |
|-------|---------|---------|
| `canonical_id` | Every layer | Primary key in `objects` table, cross_refs foreign key |
| `provenance.source_id` | Layer 2 (discovery) | CUCM pkid for re-discovery merge identity (from 07-idempotency-resumability.md) |
| `status` | Store queries, state machine | Four-state progression gates pipeline stages |
| `webex_id` | Layer 4 (executor) | Populated after Webex resource creation |
| `batch` | Layer 3d (planner) | Site-based batch assignment for execution ordering |

#### MigrationStatus enum

**Source:** `cucm-wxc-migration.md` lines 113-123

**Architecture note:** The design spec defines 10 statuses. The pipeline architecture (`07-idempotency-resumability.md`, "Object Status" section) simplifies to a 4-state progression for the core pipeline: `discovered → normalized → analyzed → planned`. Additional terminal states (`COMPLETED`, `FAILED`, `SKIPPED`, `ROLLED_BACK`) are used by the executor (Layer 4). `NEEDS_DECISION`, `PREFLIGHT_PASSED`, `EXECUTING` are intermediate states used by the decision workflow (Layer 6) and executor.

**Not specified in architecture docs:** Whether the 4-state vs 10-state discrepancy needs reconciliation, or whether the executor simply uses the full 10-state enum while the core pipeline uses only the first 4. Builder decides — recommend using the full enum from the design spec with the understanding that the core pipeline only transitions through `discovered → normalized → analyzed → planned`.

#### Provenance

**Source:** `cucm-wxc-migration.md` lines 125-131

```python
class Provenance(BaseModel):
    source_system: str          # "cucm" or "webex"
    source_id: str              # CUCM pkid or Webex UUID
    source_name: str            # Human-readable name from source system
    cluster: str | None = None  # CUCM cluster identifier
    extracted_at: datetime
    cucm_version: str | None = None
```

#### Concrete Canonical Types — Key Fields Per Type

**Source:** `cucm-wxc-migration.md` lines 145-161 (type list + mapper-produced fields), `03b-transform-mappers.md` (full field mappings per type)

| Type | Key Fields (depended on by other layers) | Source |
|------|----------------------------------------|--------|
| `CanonicalLocation` | `calling_enabled: bool`, `routingPrefix`, `outsideDialDigit`, `address` (nested), `timeZone` | 03b §1 field mapping |
| `CanonicalUser` | `create_method: "scim"\|"people_api"`, `calling_data: bool`, `cucm_manager_user_id`, `email`, `extension`, `locationId` | 03b §2 field mapping |
| `CanonicalLine` | `shared: bool`, `e164: str\|None`, `classification: "EXTENSION"\|"NATIONAL"\|"E164"\|"AMBIGUOUS"`, `extension`, `partition` | 03b §3 field mapping |
| `CanonicalDevice` | `compatibility_tier: "native_mpp"\|"convertible"\|"incompatible"`, `cucm_protocol: "SIP"\|"SCCP"`, `mac`, `cucm_model`, `lines[]` | 03b §4 field mapping |
| `CanonicalWorkspace` | `is_common_area: bool`, `hotdeskingStatus`, `supportedDevices`, license tier flag | 03b §5 field mapping |
| `CanonicalHuntGroup` | `name`, `extension`, `callPolicies.policy`, `agents[]`, `enabled` | 03b §8 HG field mapping |
| `CanonicalCallQueue` | `name`, `extension`, `callPolicies.policy`, `callPolicies.routingType`, `agents[]`, `queueSettings` | 03b §8 CQ field mapping |
| `CanonicalAutoAttendant` | `name`, `extension`, `businessSchedule`, `businessHoursMenu`, `afterHoursMenu` | 03b §8 AA field mapping |
| `CanonicalTrunk` | `name`, `locationId`, `trunkType`, `address`, `password` | 03b §6 trunk field mapping |
| `CanonicalDialPlan` | `name`, `dialPatterns[]`, `routeId`, `routeType` | 03b §7 + §6 dial plan mapping |
| `CanonicalRouteGroup` | `name`, `localGateways[]` (trunk refs with priority) | 03b §6 route group mapping |
| `CanonicalTranslationPattern` | `name`, `matchingPattern`, `replacementPattern` | 03b §6 translation pattern mapping |
| `CanonicalCallingPermission` | `assigned_users[]`, `callingPermissions[]` (per-category action array) | 03b §7 calling permission mapping |
| `CanonicalVoicemailProfile` | `enabled`, send rules, `notifications`, `messageStorage`, `faxMessage` | 03b §9 field mapping |
| `CanonicalSharedLine` | Created by `CrossReferenceBuilder._detect_shared_lines()` | 02-normalization-architecture.md |
| `CanonicalVirtualLine` | Created when shared line decision resolves to "virtual_line" option | 03-conflict-detection-engine.md SharedLineAnalyzer |
| `CanonicalOperatingMode` | `name`, `level` (must be `ORGANIZATION`), `type`, schedule data | 03b §8 simple features |
| `CanonicalCallPark` | `name`, `extension`, `locationId`, recall config | 03b §8 simple features |
| `CanonicalPickupGroup` | `name`, `agents[]` | 03b §8 simple features |
| `CanonicalPagingGroup` | `name`, `extension`, `targets[]`, `originators[]` | 03b §8 simple features |

#### Decision and DecisionOption models

**Source:** `01-data-representation.md` (decisions table schema), `03-conflict-detection-engine.md` (Analyzer base class + Decision usage), `07-idempotency-resumability.md` (fingerprinting)

```python
class DecisionOption(BaseModel):
    id: str          # "skip", "virtual_line", "convert", etc.
    label: str       # Human-readable: "Virtual Line"
    impact: str      # "1 virtual line + 4 line assignments"

class Decision(BaseModel):
    decision_id: str                    # Auto-incrementing via store.next_decision_id()
    type: DecisionType                  # Enum of 14 decision types (from 03-conflict-detection-engine.md §Concrete Analyzers + 03b §Decision Ownership Table)
    severity: str                       # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    summary: str                        # Human-readable one-liner
    context: dict                       # JSON blob with full details (analyzer/mapper-specific)
    options: list[DecisionOption]       # Available resolution options
    chosen_option: str | None = None    # Set when resolved
    resolved_at: str | None = None
    resolved_by: str | None = None      # "user" or "auto_rule"
    fingerprint: str                    # Hash of causal data (from 07-idempotency-resumability.md)
    run_id: str                         # Analysis run identifier
    affected_objects: list[str] = []    # canonical_ids affected by this decision
```

**Not specified in architecture docs:** Whether `affected_objects` is stored in the `decisions` table (it's not in the 01-data-representation.md schema) or derived from `context`. Builder decides — recommend adding it as a JSON column to the schema, since `merge_decisions()` in 07 references `old.affected_objects = new.affected_objects`.

#### DecisionType enum — complete list

**Source:** `03-conflict-detection-engine.md` (12 analyzers producing 14 types), `03b-transform-mappers.md` §13 Decision Ownership Table

```python
class DecisionType(str, Enum):
    EXTENSION_CONFLICT = "EXTENSION_CONFLICT"
    DN_AMBIGUOUS = "DN_AMBIGUOUS"
    DEVICE_INCOMPATIBLE = "DEVICE_INCOMPATIBLE"
    DEVICE_FIRMWARE_CONVERTIBLE = "DEVICE_FIRMWARE_CONVERTIBLE"
    SHARED_LINE_COMPLEX = "SHARED_LINE_COMPLEX"
    CSS_ROUTING_MISMATCH = "CSS_ROUTING_MISMATCH"
    CALLING_PERMISSION_MISMATCH = "CALLING_PERMISSION_MISMATCH"
    LOCATION_AMBIGUOUS = "LOCATION_AMBIGUOUS"
    DUPLICATE_USER = "DUPLICATE_USER"
    VOICEMAIL_INCOMPATIBLE = "VOICEMAIL_INCOMPATIBLE"
    WORKSPACE_LICENSE_TIER = "WORKSPACE_LICENSE_TIER"
    WORKSPACE_TYPE_UNCERTAIN = "WORKSPACE_TYPE_UNCERTAIN"        # from 03b §5
    HOTDESK_DN_CONFLICT = "HOTDESK_DN_CONFLICT"                  # from 03b §5
    FEATURE_APPROXIMATION = "FEATURE_APPROXIMATION"
    MISSING_DATA = "MISSING_DATA"                                 # from 03b (multiple mappers)
```

**Note:** `WORKSPACE_TYPE_UNCERTAIN`, `HOTDESK_DN_CONFLICT`, and `MISSING_DATA` appear in the mapper spec (03b) but not in the analyzer list (03). They are mapper-owned decision types, not produced by analyzers. The 03-conflict-detection-engine.md lists 12 analyzers producing 14 types. The full enum has 15 types when including mapper-only types.

---

### Layer 2 → Layer 3a: Raw CUCM Dicts (Discovery → Normalization)

**Source:** `02-normalization-architecture.md` (pass 1 normalizer examples), `cucm-build-strategy.md` Anti-Pattern 2 (fixture factory pattern)

Discovery (Layer 2) produces raw CUCM dicts matching AXL `list*` response structure. Normalizers (Layer 3a, pass 1) consume these dicts. The contract between them is the dict shape — normalizers access specific keys with specific nesting patterns.

**Contract:** Each extractor produces a `list[dict]` where each dict matches the AXL response structure for that object type. The fixture factory (Anti-Pattern 2 from Part 1) defines the minimum required fields. Normalizers MUST NOT assume any field beyond those in the fixture factory exists.

#### Fixture 1: CUCM EndUser dict

**Source:** `02-normalization-architecture.md` does not include a user normalizer example. Field names derived from `03b-transform-mappers.md` §2 user_mapper field mapping table (CUCM Field column).

```python
def make_cucm_user(
    pkid="uuid-user-001",
    userid="jsmith",
    mailid="jsmith@acme.com",
    firstName="John",
    lastName="Smith",
    department="Engineering",
    title="Engineer",
    manager=None,
    directoryUri="jsmith@cucm.acme.com",
    userLocale="English United States",
    selfService="8000",
    associatedDevices=None,
):
    """Build a minimal CUCM EndUser dict matching AXL listUser output.

    Source: 03b-transform-mappers.md §2 field mapping (CUCM Field column)
    """
    return {
        "pkid": pkid,
        "userid": userid,
        "mailid": mailid,
        "firstName": firstName,
        "lastName": lastName,
        "department": department,
        "title": title,
        "manager": manager,
        "directoryUri": directoryUri,
        "userLocale": userLocale,
        "selfService": selfService,
        "associatedDevices": associatedDevices or {
            "device": ["SEP001122AABBCC"]
        },
    }
```

**Load-bearing fields** (normalizer and mapper access these):
- `pkid` → becomes `provenance.source_id` and part of `canonical_id` (from 07-idempotency-resumability.md `canonical_id_for()`)
- `mailid` → becomes `email` on CanonicalUser (03b §2)
- `userid` → fallback for `email` if `mailid` is empty (03b §2)
- `firstName`, `lastName` → direct copy to CanonicalUser (03b §2)
- `associatedDevices.device[]` → list of device names for `user_has_device` cross-ref (02 cross-ref manifest #3)
- `manager` → stored as `cucm_manager_user_id` on CanonicalUser (03b §2)
- `selfService` → consumed by voicemail_mapper (03b §9)

**Not specified in architecture docs:** Exact AXL response nesting for `associatedDevices`. The fixture above uses `{"device": ["SEP..."]}` based on standard AXL list response patterns. Builder should verify against real AXL output when extractors are built (Phase 4).

#### Fixture 2: CUCM Phone dict

**Source:** `02-normalization-architecture.md` pass 1 example (`normalize_phone()` function)

```python
def make_cucm_phone(
    pkid="uuid-phone-001",
    name="SEP001122AABBCC",
    model="Cisco 7841",
    devicePoolName="HQ-Phones",
    callingSearchSpaceName=None,
    ownerUserName="jsmith",
    protocol="SIP",
    lines=None,
):
    """Build a minimal CUCM Phone dict matching AXL listPhone output.

    Source: 02-normalization-architecture.md normalize_phone() example
    """
    return {
        "pkid": pkid,
        "name": name,
        "model": model,
        "protocol": protocol,
        "devicePoolName": {"_value_1": devicePoolName},
        "callingSearchSpaceName": {"_value_1": callingSearchSpaceName},
        "ownerUserName": ownerUserName,
        "lines": lines or {"line": [
            {
                "index": 1,
                "dirn": {
                    "pattern": "1001",
                    "routePartitionName": {"_value_1": "Internal-PT"},
                },
            }
        ]},
    }
```

**Load-bearing fields** (from 02-normalization-architecture.md normalize_phone() example):
- `name` → `canonical_id` = `"device:{name}"` and MAC extraction (strip "SEP" prefix, 03b §4)
- `model` → three-tier compatibility classification (03b §4 Phone Model Compatibility Table)
- `devicePoolName._value_1` → unresolved string stored as `cucm_device_pool` (02 pass 1 example)
- `callingSearchSpaceName._value_1` → stored as `cucm_css` (02 pass 1 example)
- `ownerUserName` → `device_owned_by_user` cross-ref (02 cross-ref manifest #8)
- `lines.line[].index` → line appearance order (02 pass 1 example)
- `lines.line[].dirn.pattern` → DN digits (02 pass 1 example)
- `lines.line[].dirn.routePartitionName._value_1` → partition name for DN scoping (02 pass 1 example)
- `protocol` → stored as `cucm_protocol` on CanonicalDevice (03b §4)

**AXL nesting pattern:** CUCM AXL uses `{"_value_1": "actual_value"}` wrappers for foreign key reference fields (device pool, CSS, partition). This is a zeep/Suds serialization artifact from SOAP XML. All normalizers must access `.get("_value_1")` on these fields.

#### Fixture 3: CUCM RoutePattern dict

**Source:** `03b-transform-mappers.md` §6 routing_mapper field mapping (CUCM Field column) + §6 Pattern Syntax Conversion table

```python
def make_cucm_route_pattern(
    pkid="uuid-rp-001",
    pattern="9.1[2-9]XXXXXXXXX",
    routePartitionName="PSTN-PT",
    description="US Long Distance",
    destination_type="gateway",
    destination_name="CUBE-GW-01",
    destination_id="uuid-gw-001",
    routeListName=None,
):
    """Build a minimal CUCM RoutePattern dict matching AXL listRoutePattern output.

    Source: 03b-transform-mappers.md §6 routing_mapper field mapping
    """
    return {
        "pkid": pkid,
        "pattern": pattern,
        "routePartitionName": {"_value_1": routePartitionName},
        "description": description,
        "destination": {
            "type": destination_type,
            "name": destination_name,
            "id": destination_id,
        },
        "routeListName": {"_value_1": routeListName},
        "blockEnable": False,
    }
```

**Load-bearing fields:**
- `pattern` → CUCM digit pattern, converted to Webex syntax by routing_mapper (03b §6 Pattern Syntax Conversion table)
- `routePartitionName._value_1` → `route_pattern_in_partition` cross-ref (02 cross-ref manifest #10)
- `destination.type` + `destination.name` → `route_pattern_uses_gateway` cross-ref (02 manifest #11)
- `routeListName._value_1` → `route_pattern_uses_route_list` cross-ref (02 manifest #12)
- `blockEnable` → partition classification: `True` = BLOCKING action, `False` = ROUTE action (04-css-decomposition.md Step 2)

**Not specified in architecture docs:** Whether `blockEnable` is the actual AXL field name for route/block action classification. The 04-css-decomposition.md references `action: ROUTE` vs `action: BLOCK` on patterns but doesn't specify the AXL field. Builder should verify against AXL schema. 

#### Additional fixture shapes (reference only)

These follow the same `_value_1` nesting pattern. Builders can derive them from the normalizer pass 1 pattern and cross-ref manifest:

- **DevicePool**: `{pkid, name, dateTimeSettingName: {_value_1}, locationName: {_value_1}, ...}` — fields from 02 cross-ref manifest #1-2
- **CSS**: `{pkid, name, members: {member: [{routePartitionName: {_value_1}, index: N}, ...]}}` — feeds `css_contains_partition` cross-ref (02 manifest #16)
- **Partition**: `{pkid, name}` — container for DNs and route patterns
- **HuntPilot**: `{pkid, name, huntListName: {_value_1}, dn: {pattern, routePartitionName: {_value_1}}, ...}` — feeds feature_mapper classification (03b §10)
- **CTIRoutePoint**: `{pkid, name, script: {...}, dn: {pattern, ...}}` — feeds feature_mapper AA mapping (03b §8)

---

### Layer 3a → Layer 3b: Normalizer + CrossReferenceBuilder Output → Mapper Input

**Source:** `02-normalization-architecture.md` (two-pass design), `01-data-representation.md` (objects + cross_refs tables)

After pass 1 (stateless normalization) and pass 2 (CrossReferenceBuilder), the `objects` table contains canonical Pydantic models with status=`normalized` and the `cross_refs` table contains all 27 relationship types. Mappers read from both.

#### Objects table contract (what mappers read)

**Source:** `01-data-representation.md` schema

```sql
-- Mappers query objects by type and status:
SELECT canonical_id, object_type, data FROM objects
WHERE object_type = ? AND status = 'normalized';
```

The `data` column contains a JSON-serialized Pydantic model. After pass 1, objects have CUCM-sourced fields populated but NOT Webex-mapped fields. For example, a CanonicalDevice after normalization has:
- `cucm_device_pool = "HQ-Phones"` (unresolved string from pass 1, per 02 normalize_phone() example)
- `cucm_css = "Standard-Employee"` (unresolved string from pass 1)
- `lines = [LineAppearance(dn="1001", partition="Internal-PT", line_index=1)]` (from pass 1)
- `compatibility_tier` = populated by pass 2 (`_classify_phone_models()`, per 02)
- `location_id` = populated by pass 2 (`_resolve_device_pools_to_locations()`, per 02)

After pass 2, the object is enriched with resolved references and classifications.

#### cross_refs table contract (what mappers query)

**Source:** `01-data-representation.md` schema, `02-normalization-architecture.md` Complete Cross-Reference Manifest (27 rows)

```sql
CREATE TABLE cross_refs (
    from_id        TEXT NOT NULL,
    to_id          TEXT NOT NULL,
    relationship   TEXT NOT NULL,
    ordinal        INTEGER,        -- for ordered relationships (CSS partition priority)
    PRIMARY KEY (from_id, to_id, relationship)
);
```

**The 27 relationship types mappers depend on** (from 02-normalization-architecture.md manifest):

| # | Relationship | From type → To type | Consuming mapper(s) |
|---|-------------|---------------------|---------------------|
| 1 | `device_pool_has_datetime_group` | DevicePool → DateTimeGroup | location_mapper |
| 2 | `device_pool_at_cucm_location` | DevicePool → CUCM Location entity | location_mapper |
| 3 | `user_has_device` | EndUser → Phone | user_mapper |
| 4 | `user_has_primary_dn` | EndUser → DN (line 1 of primary phone) | user_mapper |
| 5 | `device_has_dn` | Device → DN | line_mapper, device_mapper, workspace_mapper, SharedLineAnalyzer |
| 6 | `dn_in_partition` | DN → Partition | line_mapper |
| 7 | `device_in_pool` | Device → DevicePool | device_mapper |
| 8 | `device_owned_by_user` | Device → EndUser | device_mapper |
| 9 | `common_area_device_in_pool` | Common-area device → DevicePool | workspace_mapper |
| 10 | `route_pattern_in_partition` | RoutePattern → Partition | routing_mapper |
| 11 | `route_pattern_uses_gateway` | RoutePattern → Gateway/Trunk | routing_mapper |
| 12 | `route_pattern_uses_route_list` | RoutePattern → RouteList → RouteGroup chain | routing_mapper |
| 13 | `route_group_has_trunk` | RouteGroup → Gateway/Trunk | routing_mapper |
| 14 | `trunk_at_location` | Gateway/Trunk → DevicePool → Location chain | routing_mapper |
| 15 | `translation_pattern_in_partition` | TranslationPattern → Partition | routing_mapper |
| 16 | `css_contains_partition` | CSS → Partition (with ordinal) | css_mapper |
| 17 | `partition_has_pattern` | Partition → RoutePattern/DN | css_mapper |
| 18 | `user_has_css` | User → CSS | css_mapper |
| 19 | `device_has_css` | Device → CSS | css_mapper |
| 20 | `line_has_css` | DN/Line → CSS | css_mapper |
| 21 | `hunt_pilot_has_hunt_list` | HuntPilot → HuntList | feature_mapper |
| 22 | `hunt_list_has_line_group` | HuntList → LineGroup | feature_mapper |
| 23 | `line_group_has_members` | LineGroup → DN/Line | feature_mapper |
| 24 | `cti_rp_has_script` | CTI Route Point → Script | feature_mapper |
| 25 | `schedule_has_time_period` | Schedule → TimePeriod | feature_mapper |
| 26 | `user_has_voicemail_profile` | EndUser → VoicemailProfile | voicemail_mapper |
| 27 | `voicemail_profile_settings` | VoicemailProfile → settings | voicemail_mapper |

**Note from 02-normalization-architecture.md:** `device_pool_to_location` is NOT built by CrossReferenceBuilder — it is written by `location_mapper` during the transform pass. This is the only mapper-produced cross-ref.

**Contract verification:** After `CrossReferenceBuilder.build()` completes, run the verification sweep from Anti-Pattern 8 (Part 1): for each of the 27 relationship types, confirm `count > 0` (warn if zero). This catches normalizer bugs before they cascade to mappers.

---

### Layer 3b → Layer 3c: Mapper Output → Analyzer Input

**Source:** `03b-transform-mappers.md` §13 (Mapper base class, MapperResult, TransformEngine), `03-conflict-detection-engine.md` (Analyzer base class)

Mappers write objects to the `objects` table with status=`analyzed` (note: architecture says "analyzed" even though logically the object has been "mapped" — the status reflects that analysis can now proceed). Mappers also write decisions to the `decisions` table.

#### What mappers produce (TransformEngine output)

**Source:** `03b-transform-mappers.md` §13 TransformEngine class

```python
class MapperResult(BaseModel):
    objects_created: int
    objects_updated: int
    decisions: list[Decision]

class TransformResult(BaseModel):
    decisions: list[Decision]
    errors: list[MapperError]
```

After all 9 mappers run (in dependency order per MAPPER_ORDER from 03b §13), the `objects` table contains:
1. **CUCM-sourced objects** (from normalization) — updated with Webex-mapped fields (e.g., `locationId`, `e164`, `compatibility_tier`)
2. **New mapper-produced objects** — `CanonicalDialPlan`, `CanonicalCallingPermission`, `CanonicalOperatingMode` (created by css_mapper, feature_mapper)

The `decisions` table contains mapper-owned decisions (per 03b §13 Decision Ownership Table).

#### What analyzers expect to read

**Source:** `03-conflict-detection-engine.md` Analyzer base class

```python
class Analyzer(ABC):
    name: str
    decision_types: list[DecisionType]
    depends_on: list[str] = []

    @abstractmethod
    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep the inventory, return decisions found."""
        ...

    @abstractmethod
    def fingerprint(self, decision_type: DecisionType, context: dict) -> str:
        """Compute deterministic fingerprint from causal data."""
        ...
```

Analyzers read from the store using:
- `store.query_by_type(object_type)` — get all objects of a given type
- `store.conn.execute(SQL)` — direct SQL for complex cross-object queries (e.g., SharedLineAnalyzer's GROUP BY query from 03 example)
- `store.find_cross_refs(canonical_id, relationship)` — follow cross-references

**Critical contract:** Analyzers check the `decisions` table for mapper-produced decisions before creating duplicates (from 03-conflict-detection-engine.md "Design note — Mapper-produced decisions" and 03b §13 Decision Ownership Table). If a mapper already produced `DEVICE_INCOMPATIBLE` for device X, `DeviceCompatibilityAnalyzer` skips device X.

#### Mapper → Analyzer field expectations

| Analyzer | Reads from objects | Expected mapper-produced fields |
|----------|-------------------|-------------------------------|
| `ExtensionConflictAnalyzer` | Lines grouped by extension+location | `extension`, `location_id` (from line_mapper, user_mapper) |
| `DNAmbiguityAnalyzer` | Lines where classification=AMBIGUOUS | `classification` (from line_mapper via e164.py) |
| `DeviceCompatibilityAnalyzer` | Devices with compatibility_tier | `compatibility_tier` (from device_mapper) |
| `SharedLineAnalyzer` | cross_refs `device_has_dn` with COUNT > 1 | Cross-refs from CrossReferenceBuilder, device owner info from device_mapper |
| `CSSRoutingAnalyzer` | CSS graph + user assignments | css_mapper output (`CanonicalDialPlan`, routing scope groups) |
| `CSSPermissionAnalyzer` | CSS restriction profiles | css_mapper output (`CanonicalCallingPermission`, blocked categories) |
| `LocationAmbiguityAnalyzer` | Device pools that can't resolve to one location | `location_id` resolution results from location_mapper |
| `DuplicateUserAnalyzer` | Users with matching email/name | `email` from user_mapper |
| `VoicemailCompatibilityAnalyzer` | Voicemail profiles with unsupported features | voicemail_mapper classifications |
| `WorkspaceLicenseAnalyzer` | Workspaces needing license tier decision | workspace_mapper license tier flags |
| `FeatureApproximationAnalyzer` | CTI RPs, hunt pilots with non-standard config | feature_mapper classification results |
| `MissingDataAnalyzer` | Objects where required fields are null/empty | All mapper outputs — checks for missing email, address, extension, etc. |

**Source for analyzer queries:** `03-conflict-detection-engine.md` "The Concrete Analyzers" table (columns: Queries, Produces).

---

### Layer 3c → Layer 3d: Analyzer Output → Planner Input

**Source:** `03-conflict-detection-engine.md` (AnalysisPipeline, AnalysisResult), `05-dependency-graph.md` (expand_to_operations)

After all 12 analyzers run, the pipeline produces:

```python
class AnalysisResult(BaseModel):
    decisions: list[Decision]    # All analyzer-produced decisions
    stats: dict[str, int]        # Per-analyzer decision counts
    run_id: str
```

**Source:** `03-conflict-detection-engine.md` AnalysisPipeline.run() method

The planner reads:
1. **Objects with status=`analyzed`** — all objects that have survived normalization + mapping + analysis
2. **All decisions** (both mapper-owned and analyzer-owned) from the `decisions` table — the planner needs to know about unresolved decisions to block execution of affected objects
3. **Cross-refs** — for building cross-object dependency edges

#### Contract between analysis and planning

The planner's `expand_to_operations()` function (from `05-dependency-graph.md`) reads objects by status:

```python
for obj in store.query_by_status("analyzed"):
    if obj.object_type == "user":
        ops.extend([...])  # Expand to create, assign_license, assign_number, etc.
```

**Source:** `05-dependency-graph.md` expand_to_operations() example

**Critical contract:** Objects with unresolved `CRITICAL` or `HIGH` decisions should NOT be expanded to operations. The planner must check `store.get_decisions_for_object(canonical_id)` and skip objects whose decisions are unresolved. **Not specified in architecture docs:** The exact blocking logic — whether ALL unresolved decisions block planning, or only HIGH/CRITICAL ones. Builder decides.

---

### Layer 3d → Layer 4: Planner Output → Executor Input

**Source:** `05-dependency-graph.md` (MigrationOp, plan_operations, plan_edges tables, batch partitioning)

The planner writes to two SQLite tables that the executor reads:

#### plan_operations table

**Source:** `05-dependency-graph.md` serialization section

```sql
CREATE TABLE plan_operations (
    node_id        TEXT PRIMARY KEY,     -- "{canonical_id}:{op_type}" e.g. "user:jsmith:create"
    canonical_id   TEXT NOT NULL,
    op_type        TEXT NOT NULL,        -- "create", "configure", "assign", "assign_license", "assign_number", "configure_settings", "configure_voicemail"
    resource_type  TEXT NOT NULL,        -- "location", "user", "device", etc.
    tier           INTEGER NOT NULL,     -- 0-7 (0=locations, 7=fixup)
    batch          TEXT,                 -- "org-wide", "site-hq", "site-branch-a", etc.
    api_calls      INTEGER DEFAULT 1,   -- estimated API call count
    description    TEXT,                 -- human-readable
    status         TEXT DEFAULT 'pending',  -- pending, executing, completed, failed, fixup
    FOREIGN KEY (canonical_id) REFERENCES objects(canonical_id)
);
```

#### plan_edges table

**Source:** `05-dependency-graph.md` serialization section

```sql
CREATE TABLE plan_edges (
    from_node      TEXT NOT NULL,
    to_node        TEXT NOT NULL,
    dep_type       TEXT NOT NULL,  -- "requires", "configures", "soft"
    broken         INTEGER DEFAULT 0,  -- 1 if cycle-broken, deferred to fixup pass
    PRIMARY KEY (from_node, to_node)
);
```

#### What the executor reads

**Source:** `05-dependency-graph.md` batch partitioning section

The executor:
1. Reconstructs the NetworkX DiGraph from `plan_operations` + `plan_edges`
2. Processes batches in order: org-wide (tiers 0-2) → site batches (tiers 2-6) → fixups (tier 7)
3. Within each batch+tier, executes operations in topological order
4. Reads the canonical object's `data` column for API payload construction
5. Writes results to the `journal` table (append-only)

**Source for tier system:** `05-dependency-graph.md` "The Tier System + DAG" section

| Tier | Resource Types | Batch |
|------|---------------|-------|
| 0 | Locations, Trunks | org-wide |
| 1 | Route Groups, Schedules/OperatingModes | org-wide |
| 2 | Users, Workspaces, Lines, Dial Plans, Route Lists | org-wide (dial plans) + per-site (users) |
| 3 | Devices, License assignments, Number assignments | per-site |
| 4 | Hunt Groups, Call Queues, Auto Attendants, Call Park, Pickup, Paging | per-site |
| 5 | Call Settings (forwarding, voicemail, permissions), CSS-derived permissions | per-site |
| 6 | Cross-feature references (AA menu → HG transfer, monitoring) | per-site |
| 7 | Fixup pass (broken cycle edges) | global |

**Not specified in architecture docs:** The exact tier assignments for all resource types. The table above is derived from `05-dependency-graph.md` expand_to_operations() examples and batch partitioning section. The tier 0-2 range is explicit; tiers 3-7 are inferred from the dependency structure. Builder should finalize tier assignments during Phase 8 implementation.

#### Edge type contract

**Source:** `05-dependency-graph.md` DependencyType enum

```python
class DependencyType(str, Enum):
    REQUIRES = "requires"       # hard: A must exist before B can be created
    CONFIGURES = "configures"   # hard: A must be created before settings applied
    SOFT = "soft"               # breakable: nice-to-have ordering
```

**Cycle-breaking safety rails** (from 05-dependency-graph.md):
- All-REQUIRES cycles → hard error, becomes a Decision for the user
- SOFT/CONFIGURES cycles → break weakest edge, deferred operation goes to tier 7 fixup
- Mixed cycles → weakest edge broken (SOFT priority 0, CONFIGURES priority 1, REQUIRES priority 2)

---

### MigrationStore API — The Central Contract

**Source:** `01-data-representation.md` (MigrationStore class example + schema), `03b-transform-mappers.md` §13 (MigrationStore Query Helpers), `07-idempotency-resumability.md` (merge_decisions, merge on re-discover)

This is the single most critical contract. Every layer calls MigrationStore. If its API changes, everything breaks.

#### Constructor

**Source:** `01-data-representation.md` MigrationStore class example

```python
def __init__(self, db_path: Path | str):
    """Initialize store with SQLite database.

    Args:
        db_path: Path to SQLite file, or ":memory:" for tests.

    Sets PRAGMA journal_mode=WAL and foreign_keys=ON.
    Calls _ensure_schema() to CREATE TABLE IF NOT EXISTS for all tables.
    """
```

**Behavior:** Creates the database file if it doesn't exist. Sets WAL mode for concurrent reads. Creates all tables (`objects`, `cross_refs`, `decisions`, `journal`, `plan_operations`, `plan_edges`, `merge_log`) via `_ensure_schema()`.

**Not specified in architecture docs:** Whether `_ensure_schema()` is a migration-style approach (version tracking) or simple `CREATE TABLE IF NOT EXISTS`. Builder decides — recommend `CREATE TABLE IF NOT EXISTS` for simplicity since the schema is defined once and doesn't evolve during a migration project's lifecycle.

#### Object CRUD

##### upsert_object()

**Source:** `01-data-representation.md` MigrationStore class example

```python
def upsert_object(self, obj: MigrationObject) -> None:
    """INSERT OR REPLACE into objects table.

    Serializes the Pydantic model via obj.model_dump_json() into the data column.
    Denormalizes object_type, status, location_id into indexed columns.

    Args:
        obj: Any MigrationObject subclass (CanonicalUser, CanonicalDevice, etc.)
    """
```

**Behavior:** Uses `INSERT ... ON CONFLICT(canonical_id) DO UPDATE SET status=excluded.status, data=excluded.data, updated_at=excluded.updated_at` (from 01 example). The `object_type` is derived from the class name or a type discriminator field.

**Not specified in architecture docs:** Whether `upsert_object` auto-commits or requires explicit `store.conn.commit()`. Builder decides. Also: how `object_type` is derived — whether from `obj.__class__.__name__` lowercased, or from a `type` field on the model.

##### query_by_type()

**Source:** `01-data-representation.md` MigrationStore class example

```python
def query_by_type(
    self, object_type: str, status: str = None
) -> list[MigrationObject]:
    """Query objects by type, optionally filtered by status.

    Returns deserialized Pydantic models (correct concrete type).

    Args:
        object_type: e.g., "user", "device", "line"
        status: Optional filter, e.g., "normalized", "analyzed"
    """
```

**Critical deserialization contract:** Must return the correct concrete Pydantic subclass based on `object_type`. A query for `"user"` returns `list[CanonicalUser]`, not `list[MigrationObject]`. This requires a type registry mapping `object_type` strings to Pydantic classes. (This is the polymorphic round-trip from Spike 2 in Part 1.)

##### query_by_status()

**Source:** `05-dependency-graph.md` expand_to_operations() example

```python
def query_by_status(self, status: str) -> list[MigrationObject]:
    """Query all objects with a given status, regardless of type.

    Returns deserialized Pydantic models (correct concrete types).
    """
```

##### get_object()

**Source:** `03b-transform-mappers.md` §13 MigrationStore Query Helpers

```python
def get_object(self, canonical_id: str) -> MigrationObject | None:
    """Get a single object by canonical_id.

    Returns deserialized Pydantic model or None if not found.
    """
```

##### get_objects()

**Source:** `03b-transform-mappers.md` §13 MigrationStore Query Helpers

```python
def get_objects(self, object_type: str) -> list[dict]:
    """Get all objects of a given type.

    Note: 03b shows this returning list[dict], while 01 shows query_by_type
    returning list[MigrationObject]. These may be two different methods or
    the same method with different return type documentation.
    """
```

**Architecture doc conflict:** `03b-transform-mappers.md` §13 shows `get_objects()` returning `list[dict]`, while `01-data-representation.md` shows `query_by_type()` returning `list[MigrationObject]`. Builder should reconcile — recommend `query_by_type()` as the primary API returning Pydantic models, with `get_objects()` as an alias or a raw-dict variant for SQL-heavy operations.

#### Cross-Reference Methods

##### add_cross_ref()

**Source:** Implied by `01-data-representation.md` cross_refs schema + `02-normalization-architecture.md` CrossReferenceBuilder

```python
def add_cross_ref(
    self, from_id: str, to_id: str, relationship: str, ordinal: int = None
) -> None:
    """Insert a cross-reference between two objects.

    Uses INSERT OR REPLACE (idempotent).
    Ordinal is required for ordered relationships (e.g., css_contains_partition).
    """
```

**Not specified in architecture docs:** The exact method name. The 01 schema defines the table; the 02 CrossReferenceBuilder shows direct SQL inserts. Builder decides the API wrapping.

##### find_cross_refs()

**Source:** `01-data-representation.md` MigrationStore class example

```python
def find_cross_refs(
    self, canonical_id: str, relationship: str
) -> list[str]:
    """Find all objects related to this one by relationship type.

    Returns list of target canonical_ids.
    """
```

##### get_cross_refs()

**Source:** `03b-transform-mappers.md` §13 MigrationStore Query Helpers

```python
def get_cross_refs(
    self,
    from_id: str = None,
    to_id: str = None,
    relationship: str = None,
) -> list[dict]:
    """Query cross-reference relationships with flexible filtering.

    Returns list of dicts with keys: from_id, to_id, relationship, ordinal.
    At least one filter parameter should be provided.
    """
```

##### get_cross_ref_targets()

**Source:** `03b-transform-mappers.md` §13 MigrationStore Query Helpers

```python
def get_cross_ref_targets(
    self, from_id: str, relationship: str
) -> list[str]:
    """Get all target IDs for a given source and relationship type.

    Convenience wrapper over get_cross_refs().
    """
```

##### resolve_chain()

**Source:** `03b-transform-mappers.md` §13 MigrationStore Query Helpers

```python
def resolve_chain(
    self, start_id: str, *relationships: str
) -> str | None:
    """Follow a chain of cross-refs: start → rel1 → rel2 → ... → final target.

    Returns the final target canonical_id or None if chain breaks at any step.

    Example: resolve_chain(dn_id, 'device_has_dn', 'device_in_pool', 'device_pool_to_location')
    follows DN → Device → DevicePool → Location.
    """
```

##### count_cross_refs()

**Source:** `cucm-build-strategy.md` Anti-Pattern 8 (verification sweep)

```python
def count_cross_refs(self, relationship: str) -> int:
    """Count cross-references of a given type. Used for post-normalization verification."""
```

##### clear_cross_refs()

**Source:** `07-idempotency-resumability.md` "Cross-Refs: Deliberate Rebuild" section

```python
def clear_cross_refs(self) -> None:
    """DELETE all cross_refs. Called before CrossReferenceBuilder.build() on re-normalization.

    Deliberate rebuild strategy: simpler code, guaranteed consistency, no diff logic needed.
    """
```

#### Decision Methods

##### save_decision()

**Source:** `07-idempotency-resumability.md` merge_decisions() example

```python
def save_decision(self, decision: Decision) -> None:
    """Insert or update a decision. Uses fingerprint as unique key.

    INSERT ... ON CONFLICT(fingerprint) DO UPDATE SET context, options, run_id, etc.
    """
```

##### get_all_decisions()

**Source:** `07-idempotency-resumability.md` merge_decisions() example

```python
def get_all_decisions(self) -> list[Decision]:
    """Get all non-stale decisions."""
```

##### next_decision_id()

**Source:** `03b-transform-mappers.md` §13 Mapper base class _create_decision() helper

```python
def next_decision_id(self) -> str:
    """Auto-incrementing decision ID. Returns 'D001', 'D002', etc."""
```

##### get_decisions_for_object()

**Source:** Implied by `03b-transform-mappers.md` §13 Decision Ownership ("Analyzers should check the decisions table for mapper-produced decisions before creating duplicates") and Layer 3c→3d contract (planner must check unresolved decisions before expanding operations).

```python
def get_decisions_for_object(
    self, canonical_id: str
) -> list[Decision]:
    """Get all decisions affecting a specific object.

    Queries decisions table where canonical_id appears in affected_objects
    or in the context JSON. Used by:
    - Analyzers: to skip objects with existing mapper-produced decisions
    - Planner: to block expansion of objects with unresolved HIGH/CRITICAL decisions
    """
```

**Not specified in architecture docs:** The exact query mechanism — whether `affected_objects` is a stored column (recommended in Layer 1 contract above) or parsed from `context` JSON. Builder decides.

#### Run Tracking

##### current_run_id property

**Source:** `03b-transform-mappers.md` §13 MigrationStore Query Helpers

```python
@property
def current_run_id(self) -> str:
    """Current analysis run ID for decision tracking.

    Set when an analysis run begins. Format not specified — recommend ISO timestamp.
    """
```

**Not specified in architecture docs:** How `current_run_id` is set. Builder decides — likely a setter called by AnalysisPipeline/TransformEngine before running.

#### Journal Methods (Layer 4)

##### append_journal()

**Source:** `01-data-representation.md` journal table schema

```python
def append_journal(
    self,
    entry_type: str,        # "CREATE", "MODIFY", "ASSIGN", "CONFIGURE"
    canonical_id: str,
    resource_type: str,
    request: dict,           # {method, url, payload}
    response: dict = None,   # {status, body}
    pre_state: dict = None,  # Webex state before (for rollback)
) -> None:
    """Append an execution journal entry. Journal is append-only."""
```

#### Merge Methods (Idempotency)

##### merge_decisions()

**Source:** `07-idempotency-resumability.md` merge_decisions() function

```python
def merge_decisions(
    self, new_decisions: list[Decision]
) -> MergeResult:
    """Three-way merge of new analysis results with existing decisions.

    Uses fingerprint as merge key:
    - Same fingerprint, resolved → keep resolution (result.kept++)
    - Same fingerprint, pending → update context (result.updated++)
    - New fingerprint → insert (result.new++)
    - Old fingerprint missing from new → mark stale (result.stale++)
    - Old fingerprint resolved but new fingerprint changed → invalidate (result.invalidated++)
    """
```

**Note:** `merge_decisions` may be a standalone function rather than a store method. The 07 doc shows it as a free function taking `store` as a parameter. Builder decides placement.

#### Complete MigrationStore Method Summary

| Method | Layer(s) that call it | Source doc |
|--------|----------------------|-----------|
| `__init__(db_path)` | All | 01 |
| `upsert_object(obj)` | 2 (discovery), 3a (normalizers), 3b (mappers) | 01 |
| `query_by_type(object_type, status)` | 3a, 3b, 3c, 3d | 01 |
| `query_by_status(status)` | 3d (planner) | 05 |
| `get_object(canonical_id)` | 3b (mappers), 3c (analyzers) | 03b §13 |
| `get_objects(object_type)` | 3b (mappers) | 03b §13 — **see note below** |
| `add_cross_ref(from_id, to_id, relationship, ordinal)` | 3a (CrossReferenceBuilder), 3b (location_mapper) | 01 schema, 02 |
| `find_cross_refs(canonical_id, relationship)` | 3b, 3c | 01 |
| `get_cross_refs(from_id, to_id, relationship)` | 3b (mappers) | 03b §13 |
| `get_cross_ref_targets(from_id, relationship)` | 3b (mappers) | 03b §13 |
| `resolve_chain(start_id, *relationships)` | 3b (line_mapper chain resolution) | 03b §13 |
| `count_cross_refs(relationship)` | 3a (verification sweep) | Part 1 Anti-Pattern 8 |
| `clear_cross_refs()` | 3a (re-normalization) | 07 |
| `save_decision(decision)` | 3b (mappers), 3c (analyzers), merge | 07 |
| `get_all_decisions()` | 3c (analyzers), merge, CLI | 07 |
| `next_decision_id()` | 3b, 3c | 03b §13 |
| `current_run_id` (property) | 3b, 3c | 03b §13 |
| `get_decisions_for_object(canonical_id)` | 3d (planner), CLI | Implied by 03b §13 Decision Ownership + Layer 3c→3d contract |
| `append_journal(...)` | 4 (executor) | 01 |
| `merge_decisions(new_decisions)` | Pipeline re-run | 07 |

**Reconciliation: `get_objects()` vs `query_by_type()`** — `03b-transform-mappers.md` §13 shows `get_objects(object_type) -> list[dict]`; `01-data-representation.md` shows `query_by_type(object_type, status) -> list[MigrationObject]`. **Decision:** `query_by_type()` is the canonical API (returns deserialized Pydantic models, supports status filter). `get_objects()` is an alias that calls `query_by_type(object_type)` without a status filter. Both return `list[MigrationObject]`, not `list[dict]` — the 03b signature showing `list[dict]` is a spec shorthand, not a literal return type. Builders should implement one method and alias the other.

---

## 2. Phase Acceptance Criteria

Each phase uses Part 1's exact names and ordering from `cucm-build-strategy.md`.

### Phase 1: Foundation (Layer 1)

**Files:** `models.py`, `store.py`, `state.py`, `rate_limiter.py` + tests
**Sessions:** 1-2

**Acceptance:**

1. **Pydantic model serialization round-trip.** Given a `CanonicalUser` with all fields populated (including nested `Provenance`, list fields `errors`, `warnings`, `depends_on`, optional fields `webex_id=None`), calling `obj.model_dump_json()` then `CanonicalUser.model_validate_json(json_str)` produces an identical object. Repeat for at least 5 types: `CanonicalUser`, `CanonicalDevice` (contains nested `LineAppearance` list), `CanonicalLocation`, `CanonicalHuntGroup`, `CanonicalDialPlan`.
    - **Source:** Part 1, Spike 2 ("SQLite Store + Pydantic Polymorphic Round-Trip")

2. **Polymorphic deserialization from object_type string.** Given `object_type="user"` and a JSON blob, the type registry dispatches to `CanonicalUser.model_validate_json()`. Given `object_type="device"`, dispatches to `CanonicalDevice`. Test with all 20 concrete types.
    - **Source:** Part 1, Phase 1 "Key verification"

3. **SQLite upsert idempotency.** Given a `CanonicalLocation`, calling `store.upsert_object(loc)` twice with the same `canonical_id` results in exactly one row in the `objects` table. The second upsert updates `data` and `updated_at` without creating a duplicate.
    - **Source:** Part 1, Spike 2 ("Upsert idempotency")

4. **SQLite JSON round-trip preserves types.** Given a `CanonicalDevice` with `compatibility_tier="native_mpp"` (string enum), `lines=[LineAppearance(dn="1001", partition="Internal-PT", line_index=1)]` (nested list), and `webex_id=None` (optional), after upsert + query_by_type: the returned object has `compatibility_tier` as a string (not None), `lines` as a list of `LineAppearance` objects (not plain dicts), and `webex_id` as None (not empty string).
    - **Source:** Part 1, Spike 2 ("subtle serialization bugs can corrupt data silently")

5. **Cross-ref query with JSON extraction.** Given two objects (a device and a user) with a `device_owned_by_user` cross-ref, `store.find_cross_refs("device:SEP001", "device_owned_by_user")` returns `["user:jsmith"]`. Additionally, a SQL query using `json_extract(data, '$.cucm_model')` against the objects table returns the correct value.
    - **Source:** Part 1, Spike 2 ("json_extract() query against a nested field")

6. **State machine transitions.** Given `state.json` with `current_stage="DISCOVERED"`, calling `state.advance_to("NORMALIZED")` succeeds. Calling `state.advance_to("ANALYZED")` from `DISCOVERED` raises an error (skipping a stage). Valid progression: `INIT → DISCOVERED → NORMALIZED → ANALYZED → PLANNED → EXECUTING → COMPLETED`.
    - **Source:** `07-idempotency-resumability.md` "Object Status" section + `cucm-pipeline-architecture.md` on-disk layout (state.json)

7. **Rate limiter token bucket.** Given a rate limiter configured at 100 requests/minute, 100 rapid `acquire()` calls succeed. The 101st call blocks or returns a wait duration > 0. After waiting 600ms, one more call succeeds.
    - **Source:** `05-dependency-graph.md` Rate Limit Budgeting section

**Test fixtures needed:**
- Factory functions for at least 5 canonical model types with all field combinations (required, optional, nested, list)
- `:memory:` SQLite store instance

### Phase 2: Location Thin Thread

**Files:** Location normalizer, `CrossReferenceBuilder` (scaffold), `engine.py` (scaffold), `location_mapper.py`, `LocationAmbiguousAnalyzer` (scaffold), `planner.py` (scaffold), `dependency.py` (scaffold) + tests
**Sessions:** 3-5

**Acceptance:**

1. **Location normalizer pass 1.** Given `make_cucm_phone(devicePoolName="HQ-Phones")` and a device pool dict `{name: "HQ-Phones", dateTimeSettingName: {_value_1: "CMLocal"}, locationName: {_value_1: "Headquarters"}}`, the normalizer produces a CanonicalLocation with `canonical_id="location:dp-{pkid}"`, `provenance.source_system="cucm"`, and unresolved `cucm_device_pool="HQ-Phones"`.
    - **Source:** `02-normalization-architecture.md` pass 1 properties ("Testable in isolation")

2. **CrossReferenceBuilder scaffold.** Given 2 device pools and 3 phones in the store, `CrossReferenceBuilder(store).build()` inserts `device_in_pool` cross-refs linking each phone to its device pool. `store.find_cross_refs("device:SEP001", "device_in_pool")` returns `["devicepool:HQ-Phones"]`.
    - **Source:** `02-normalization-architecture.md` cross-ref manifest #7

3. **Location mapper field mapping.** Given a normalized DevicePool with cross-refs to a DateTimeGroup (timezone="America/Los_Angeles") and a CUCM Location entity (address fields populated), `location_mapper.map(store)` produces a `CanonicalLocation` with `timeZone="America/Los_Angeles"`, `address.city` populated, `announcementLanguage="en_us"` (lowercase), and `calling_enabled=True`.
    - **Source:** `03b-transform-mappers.md` §1 field mapping table

4. **Location mapper device pool consolidation.** Given 2 device pools ("HQ-Phones", "HQ-Softphones") both referencing the same CUCM Location entity, the mapper produces exactly 1 `CanonicalLocation` (consolidated), not 2.
    - **Source:** `03b-transform-mappers.md` §1 Edge Cases "Device pool consolidation"

5. **Location mapper LOCATION_AMBIGUOUS decision.** Given a device pool with no CUCM Location cross-ref (`device_pool_at_cucm_location` missing), the mapper produces a `Decision` with `type=LOCATION_AMBIGUOUS`, `severity="HIGH"`, and options including "Create new location" and "Skip".
    - **Source:** `03b-transform-mappers.md` §1 Decisions Generated table

6. **Location mapper writes device_pool_to_location cross-ref.** After mapping, `store.find_cross_refs("devicepool:HQ-Phones", "device_pool_to_location")` returns the new location's canonical_id.
    - **Source:** `02-normalization-architecture.md` note: "device_pool_to_location is NOT built by CrossReferenceBuilder — it is written by location_mapper"

7. **Planner scaffold expands location to operations.** Given one analyzed `CanonicalLocation`, `expand_to_operations(store)` produces one `MigrationOp` with `op_type="create"`, `resource_type="location"`, `tier=0`.
    - **Source:** `05-dependency-graph.md` expand_to_operations() example

8. **End-to-end thin thread.** Given fixture CUCM dicts (device pool + CUCM location + datetime group), the pipeline: normalize → cross-ref → map → analyze → plan produces a `plan_operations` row with a valid node_id, tier=0, batch="org-wide", status="pending".
    - **Source:** Part 1, Phase 2 "What it proves"

**Test fixtures needed:**
- `make_cucm_device_pool()`, `make_cucm_location_entity()`, `make_cucm_datetime_group()` factory functions
- `:memory:` store pre-seeded with device pool + location + datetime group objects

### Phase 3: Risk Spikes

**Files:** `cucm_pattern.py`, `e164.py`, `css_mapper.py` (core), `feature_mapper.py` (classification) + tests
**Sessions:** 6-10

**Acceptance:**

1. **CUCM pattern compilation.** Given pattern `"9.1[2-9]XXXXXXXXX"`, `cucm_pattern_to_regex()` returns a regex that matches `"912125551234"` and does not match `"911"` or `"9011441234567"`.
    - **Source:** `03b-transform-mappers.md` §12 cucm_pattern.py interface

2. **Pattern overlap detection — overlapping pair.** Given `"9.!"` and `"9.011!"`, `cucm_patterns_overlap()` returns `True` (broad pattern subsumes international prefix).
    - **Source:** Part 1, Spike 1 test cases

3. **Pattern overlap detection — non-overlapping pair.** Given `"9.[2-9]XXXXXX"` (7-digit local) and `"9.1[2-9]XXXXXXXXX"` (10-digit long distance), `cucm_patterns_overlap()` returns `False`.
    - **Source:** Part 1, Spike 1 test cases

4. **Pattern overlap — E.164 format.** Given `"+1XXXXXXXXXX"` and `"+1900XXXXXXX"`, `cucm_patterns_overlap()` returns `True`.
    - **Source:** Part 1, Spike 1 test cases

5. **E.164 normalization — US extension.** Given `normalize_dn("1001", "US", [])`, returns `E164Result(extension="1001", classification="EXTENSION")`.
    - **Source:** `02-normalization-architecture.md` normalize_dn() example, Part 1 Spike 3 test cases

6. **E.164 normalization — US national with prefix strip.** Given `normalize_dn("91234567890", "US", [{"prefix": "9", "action": "strip"}])`, returns `E164Result(e164="+11234567890", classification="NATIONAL")`.
    - **Source:** Part 1, Spike 3 test cases

7. **E.164 normalization — UK national.** Given `normalize_dn("02012345678", "GB", [])`, returns `E164Result(e164="+442012345678", classification="NATIONAL")`.
    - **Source:** Part 1, Spike 3 test cases

8. **E.164 normalization — ambiguous.** Given a 24-digit DN, returns `E164Result(classification="AMBIGUOUS")`.
    - **Source:** Part 1, Spike 3 test cases

9. **CSS mapper partition classification.** Given a CSS with 3 partitions where partition 1 has only DNs, partition 2 has route patterns with `action=ROUTE`, and partition 3 has route patterns with `action=BLOCK`, the mapper classifies them as `DIRECTORY`, `ROUTING`, `BLOCKING` respectively.
    - **Source:** `04-css-decomposition.md` Step 2 classification table

10. **CSS mapper routing scope — single group (happy path).** Given 2 CSSes that share identical routing partitions, `effective_routing_scope()` returns the same `frozenset` for both. The mapper produces org-wide dial plans with no `CSS_ROUTING_MISMATCH` decisions.
    - **Source:** `04-css-decomposition.md` Step 3 "If there's only one scope group"

11. **CSS mapper routing scope — multiple groups.** Given 2 CSSes with different routing partitions, the mapper uses intersection as the baseline and produces `CSS_ROUTING_MISMATCH` decisions for the delta patterns.
    - **Source:** `04-css-decomposition.md` Step 3 "If there are multiple scope groups"

12. **Feature mapper — Top Down hunt pilot → Hunt Group.** Given a hunt pilot dict with `huntAlgorithm="Top Down"` and no queue features, `classify_hunt_pilot()` returns `"HUNT_GROUP"` and the mapper produces a `CanonicalHuntGroup` with `callPolicies.policy="REGULAR"`.
    - **Source:** `03b-transform-mappers.md` §10 Algorithm Mapping Table

13. **Feature mapper — Circular + queue features → Call Queue.** Given a hunt pilot with `huntAlgorithm="Circular"` and `queueCalls.enabled=True`, `classify_hunt_pilot()` returns `"CALL_QUEUE"` and the mapper produces a `CanonicalCallQueue` with `callPolicies.policy="CIRCULAR"`.
    - **Source:** `03b-transform-mappers.md` §10 Algorithm Mapping Table

14. **Feature mapper — CTI Route Point → Auto Attendant.** Given a CTI Route Point dict (`isCtiRp=True`), `classify_hunt_pilot()` returns `"AUTO_ATTENDANT"`. If the script is complex, a `FEATURE_APPROXIMATION` decision is produced.
    - **Source:** `03b-transform-mappers.md` §10 Algorithm Mapping Table

15. **Feature mapper — Broadcast >50 agents.** Given a hunt pilot with `huntAlgorithm="Broadcast"` and a line group with 60 members, the mapper produces a `FEATURE_APPROXIMATION` decision noting the 50-agent SIMULTANEOUS limit.
    - **Source:** `03b-transform-mappers.md` §8 Edge Cases "Agent limits"

**Test fixtures needed:**
- CUCM pattern pairs (25+ from Spike 1 in Part 1)
- DN strings with country codes (20+ from Spike 3)
- CSS fixtures with partition ordinals, patterns with actions
- Hunt pilot + hunt list + line group fixture chains (8 from Spike 4)

### Phase 4: Extraction Layer (Layer 2)

**Files:** `connection.py`, 8 extractors, `discovery.py` + tests
**Sessions:** 11-12

**Acceptance:**

1. **AXL connection initialization.** Given a CUCM hostname, username, and password, `CUCMConnection(host, user, password)` loads the WSDL and authenticates. Test with mocked SOAP endpoint.
    - **Source:** Part 1, Phase 4 description

2. **User extractor pagination.** Given a mocked `listUser` AXL response with 2 pages (returnedTags shows 1000+500), `extractors.users.extract_users(conn)` returns a list of 1500 user dicts. Each dict has the fields from `make_cucm_user()`.
    - **Source:** Part 1, Anti-Pattern 7 "paginate"

3. **Phone extractor line nesting.** Given a mocked `listPhone` response, the returned dicts have `lines.line[]` with `dirn.pattern` and `dirn.routePartitionName._value_1` matching the `make_cucm_phone()` fixture structure.
    - **Source:** `02-normalization-architecture.md` normalize_phone() example structure

4. **Discovery orchestrator.** Given all 8 extractors, `discovery.run(conn, store)` calls each extractor, passes results through pass-1 normalizers, and upserts into the store. After completion, `store.query_by_type("user")` returns normalized users.
    - **Source:** Part 1, Phase 4

5. **Re-discovery merge.** Given existing objects in the store, re-running discovery with modified CUCM data updates changed objects (status reset to `discovered`), inserts new objects, and marks deleted objects as `stale`.
    - **Source:** `07-idempotency-resumability.md` "Re-Discovery Merge" section

**Test fixtures needed:**
- Mocked SOAP/AXL response XMLs for each extractor (paginated)
- Or: mocked Python dicts matching AXL response structure (lighter-weight)

### Phase 5: Remaining Normalizers + Full CrossReferenceBuilder (Layer 3a)

**Files:** ~12 normalizers, full `CrossReferenceBuilder` (all 27 relationship types) + tests
**Sessions:** 13-14

**Acceptance:**

1. **Each normalizer is stateless.** For each of the ~12 normalizers (user, device, workspace, partition, CSS, route pattern, gateway, trunk, route group, translation pattern, hunt pilot, CTI RP, schedule, call park, pickup, paging, voicemail profile): given a CUCM dict, the normalizer returns a canonical Pydantic model without accessing the store, database, or any global state.
    - **Source:** `02-normalization-architecture.md` pass 1 properties ("Pure function. No side effects. No index lookups.")

2. **User normalizer field extraction.** Given `make_cucm_user(mailid="jsmith@acme.com", firstName="John", lastName="Smith")`, the normalizer produces `CanonicalUser(canonical_id="user:{pkid}", email="jsmith@acme.com", ...)` with provenance populated.
    - **Source:** `03b-transform-mappers.md` §2 field mapping

3. **CrossReferenceBuilder produces all 27 relationship types.** After loading a comprehensive fixture set (users, phones, device pools, CSSes, partitions, route patterns, hunt pilots) and running `CrossReferenceBuilder(store).build()`, `store.count_cross_refs(rel_type)` returns > 0 for all 27 relationship names from the manifest.
    - **Source:** `02-normalization-architecture.md` Complete Cross-Reference Manifest

4. **Shared line detection.** Given 2 phones with the same DN "1001" in partition "Internal-PT", after CrossReferenceBuilder runs, the shared line detection query (from `02-normalization-architecture.md` `_detect_shared_lines()`) returns DN 1001 with device_count=2.
    - **Source:** `02-normalization-architecture.md` _detect_shared_lines() SQL query

5. **E.164 normalization in pass 2.** Given a DN "5551234567" on a phone in device pool "HQ-Phones" → location with country_code="US", after CrossReferenceBuilder runs `_normalize_dns_to_e164()`, the DN object's `e164` field is `"+15551234567"` and `classification` is `"NATIONAL"`.
    - **Source:** `02-normalization-architecture.md` pass 2 step 5

6. **CSS graph construction.** Given a CSS "Standard-Employee" with 3 partitions (ordered by priority), after CrossReferenceBuilder runs, `store.get_cross_refs(from_id="css:std-emp", relationship="css_contains_partition")` returns 3 rows with ordinal values 1, 2, 3 preserving priority.
    - **Source:** `02-normalization-architecture.md` pass 2 step 6, `04-css-decomposition.md` Step 1

7. **Verification sweep passes.** After CrossReferenceBuilder completes, the verification sweep (Anti-Pattern 8) logs no warnings for any of the 27 relationship types that have corresponding fixture data.
    - **Source:** Part 1, Anti-Pattern 8

**Test fixtures needed:**
- Comprehensive fixture set covering all object types: 3+ users, 4+ phones (including shared line pair), 2+ device pools, 2+ CSSes with partitions, route patterns, a hunt pilot chain, a voicemail profile
- Factory functions for each CUCM object type

### Phase 6: Remaining Mappers (Layer 3b)

**Files:** `user_mapper.py`, `line_mapper.py`, `device_mapper.py`, `workspace_mapper.py`, `routing_mapper.py`, `voicemail_mapper.py`, `css_mapper.py` (completion), `feature_mapper.py` (completion), `engine.py` (completion), `rules.py`, `decisions.py` + tests
**Sessions:** 15-21

**Acceptance:**

1. **User mapper email resolution.** Given a CUCM user with `mailid="jsmith@acme.com"`, the mapper produces `CanonicalUser(email="jsmith@acme.com")`. Given a user with `mailid=""` and `userid="jdoe@acme.com"`, the mapper uses `userid` as fallback. Given a user with neither, the mapper produces a `MISSING_DATA` decision.
    - **Source:** `03b-transform-mappers.md` §2 field mapping (mailid → emails[], userid fallback)

2. **User mapper location resolution.** Given a user with `user_has_device` cross-ref → phone → `device_in_pool` → device pool → `device_pool_to_location` → location, the mapper resolves `locationId` by following this cross-ref chain via `store.resolve_chain()`.
    - **Source:** `03b-transform-mappers.md` §2 Cross-Reference Dependencies table

3. **User mapper create_method flag.** Given migration config with `create_method="scim"`, the mapper sets `create_method="scim"` on the CanonicalUser.
    - **Source:** `03b-transform-mappers.md` §2 "Execution strategy note"

4. **Line mapper E.164 classification.** Given a DN "5551234567" at a US location, the mapper produces `CanonicalLine(e164="+15551234567", classification="NATIONAL", extension="5551234567")`. Given a DN "1001", produces `CanonicalLine(extension="1001", classification="EXTENSION", e164=None)`.
    - **Source:** `03b-transform-mappers.md` §3 E.164 Normalization Algorithm

5. **Line mapper extension conflict detection.** Given 2 DNs with `extension="1001"` at different locations (different partitions → different locations), the mapper produces an `EXTENSION_CONFLICT` decision. **Correction:** Per Decision Ownership Table (03b §13), `EXTENSION_CONFLICT` is owned by `ExtensionConflictAnalyzer`, not line_mapper. The line_mapper sets the `extension` and `location_id` fields that the analyzer later sweeps. No decision from the mapper for this case.
    - **Source:** `03b-transform-mappers.md` §13 Decision Ownership Table

6. **Device mapper three-tier classification.** Given phones with models "Cisco 6841" (native MPP), "Cisco 7841" (convertible), and "Cisco 7911" (incompatible), the mapper produces `compatibility_tier="native_mpp"`, `"convertible"`, and `"incompatible"` respectively. The 7911 gets a `DEVICE_INCOMPATIBLE` decision; the 7841 gets a `DEVICE_FIRMWARE_CONVERTIBLE` decision.
    - **Source:** `03b-transform-mappers.md` §4 Phone Model Compatibility Table + Decisions Generated

7. **Device mapper MAC extraction.** Given a phone with `name="SEP001122AABBCC"`, the mapper produces `mac="001122AABBCC"` (strip "SEP" prefix).
    - **Source:** `03b-transform-mappers.md` §4 field mapping (name → mac)

8. **Workspace mapper common-area detection.** Given a phone flagged as `is_common_area=True` by the normalizer, the workspace_mapper (not device_mapper) processes it and produces a `CanonicalWorkspace` with `locationId` from `common_area_device_in_pool` cross-ref.
    - **Source:** `03b-transform-mappers.md` §5 field mapping + Edge Cases "Common-area phones vs. shared lines"

9. **Workspace mapper hot desk conflict.** Given a common-area phone with both a DN and hoteling enabled, the mapper produces a `HOTDESK_DN_CONFLICT` decision.
    - **Source:** `03b-transform-mappers.md` §5 Decisions Generated

10. **Routing mapper pattern syntax conversion.** Given CUCM pattern `"9.1[2-9]XXXXXXXXX"` with `country_code="+1"`, `cucm_to_webex_pattern()` returns `"+1[2-9]XXXXXXXXX"`. Given `"9.011!"`, returns `"+!"`.
    - **Source:** `03b-transform-mappers.md` §6 Pattern Syntax Conversion table

11. **Routing mapper trunk creation.** Given a CUCM SIP trunk with `name="CUBE-GW-01"`, the mapper produces `CanonicalTrunk(name="CUBE-GW-01", trunkType="REGISTERING", locationId=<resolved>)`.
    - **Source:** `03b-transform-mappers.md` §6 Trunk field mapping

12. **Voicemail mapper basic settings.** Given a CUCM user with voicemail profile (CFNA enabled, ring count=18 seconds), the mapper produces voicemail settings with `sendUnansweredCalls.enabled=True`, `sendUnansweredCalls.numberOfRings=3` (18÷6=3).
    - **Source:** `03b-transform-mappers.md` §9 field mapping (CFNA ring count)

13. **Voicemail mapper gap detection.** Given a Unity Connection profile with `callerInputRules` configured (no Webex equivalent), the mapper produces a `VOICEMAIL_INCOMPATIBLE` decision listing "caller input rules" as a lost feature.
    - **Source:** `03b-transform-mappers.md` §11 Voicemail Gap Analysis table

14. **CSS mapper full decomposition.** Given 3 CSSes with different routing scopes, the mapper: (a) computes intersection of routing scopes → org-wide dial plans, (b) computes restriction profiles → `CanonicalCallingPermission` objects, (c) produces `CSS_ROUTING_MISMATCH` decisions for delta patterns.
    - **Source:** `03b-transform-mappers.md` §12 Data Flow Summary

15. **Feature mapper full field mapping.** Given a hunt pilot classified as HUNT_GROUP REGULAR, the mapper produces a `CanonicalHuntGroup` with `name`, `extension`, `callPolicies.policy="REGULAR"`, and `agents[]` populated from line group members.
    - **Source:** `03b-transform-mappers.md` §8 HG field mapping table

16. **TransformEngine orchestration.** Given all 9 mappers registered in MAPPER_ORDER, `engine.run(store)` executes them in dependency order (location → routing → user → line → workspace → device → feature → css → voicemail) and returns a `TransformResult` with aggregated decisions and any mapper errors.
    - **Source:** `03b-transform-mappers.md` §13 TransformEngine class

17. **Auto-resolution rules.** Given `config.json` with auto_rules `[{type: "DEVICE_INCOMPATIBLE", choice: "skip"}]`, after analysis the `DEVICE_INCOMPATIBLE` decisions are auto-resolved with `chosen_option="skip"` and `resolved_by="auto_rule"`.
    - **Source:** `03-conflict-detection-engine.md` Auto-Resolution Rules section

18. **Full integration test — messy fixture set.** Given a fixture set with: 2 locations, 5 users (1 with shared line, 1 with no email), 6 phones (2 sharing DN 1001, 1 incompatible 7911, 1 convertible 7841), 2 CSSes with different routing scopes, 1 hunt pilot with queue features, 1 CTI RP — the full normalize → map pipeline produces: CanonicalLocations (2), CanonicalUsers (4 mapped + 1 MISSING_DATA decision), CanonicalDevices (correct tiers), CanonicalDialPlans (from CSS intersection), CanonicalCallingPermissions (grouped by restriction profile), CanonicalCallQueue (from queue hunt pilot), decisions for shared line, incompatible device, convertible device, CSS mismatch.
    - **Source:** Part 1, Anti-Pattern 3 + Phase 6 session 21

**Test fixtures needed:**
- Extended fixture set from Phase 5 plus: CUCM user with no email, phone with model "Cisco 7911", hot desk workspace, SIP trunk, route patterns with different targets, hunt pilot with queue features, CTI RP with simple script, voicemail profile with Unity Connection features
- `:memory:` store pre-seeded with normalized objects and all 27 cross-ref types

### Phase 7: Analysis Pipeline (Layer 3c)

**Files:** `analysis_pipeline.py`, 12 analyzer classes + tests
**Sessions:** 22-24

**Acceptance:**

1. **AnalysisPipeline orchestration.** Given 12 registered analyzers, `pipeline.run(store)` calls each analyzer's `analyze(store)` method and returns an `AnalysisResult` with all decisions aggregated and per-analyzer stats.
    - **Source:** `03-conflict-detection-engine.md` AnalysisPipeline.run() method

2. **Analyzer independence.** All 12 analyzers have `depends_on=[]` (from 03-conflict-detection-engine.md "No inter-analyzer dependencies exist in the current set"). Running them in any order produces identical decisions.
    - **Source:** `03-conflict-detection-engine.md` "Ordering Between Analyzers"

3. **SharedLineAnalyzer — 2-device simple case.** Given DN "1001" shared across 2 devices with 1 owner, the analyzer produces a `SHARED_LINE_COMPLEX` decision with `severity="MEDIUM"` and options including "Webex Shared Line" (available for ≤2 devices).
    - **Source:** `03-conflict-detection-engine.md` SharedLineAnalyzer example code

4. **SharedLineAnalyzer — 4-device multi-owner case.** Given DN "1001" shared across 4 devices with 3 owners, the analyzer produces `severity="HIGH"` and does NOT include "Webex Shared Line" option (only available for ≤2 devices). Options include "Virtual Line" and "Call Park + BLF".
    - **Source:** `03-conflict-detection-engine.md` SharedLineAnalyzer example (condition: `device_count <= 2` for shared_line option)

5. **DeviceCompatibilityAnalyzer skips mapper-decided objects.** Given a device with an existing `DEVICE_INCOMPATIBLE` decision (written by device_mapper), the analyzer does NOT produce a duplicate decision for that device.
    - **Source:** `03-conflict-detection-engine.md` "Design note — Mapper-produced decisions" + `03b-transform-mappers.md` §13 Decision Ownership

6. **ExtensionConflictAnalyzer.** Given 2 users at different locations with the same extension "1001", the analyzer produces an `EXTENSION_CONFLICT` decision.
    - **Source:** `03-conflict-detection-engine.md` Concrete Analyzers table (#1)

7. **MissingDataAnalyzer.** Given a user with `email=None` and no `MISSING_DATA` decision already present (from user_mapper), the analyzer produces a `MISSING_DATA` decision.
    - **Source:** `03-conflict-detection-engine.md` Concrete Analyzers table (#12)

8. **Fingerprint determinism.** Given the same CUCM data, re-running the analyzer produces decisions with identical fingerprints. Given a shared line with 3 owners, changing to 4 owners produces a different fingerprint.
    - **Source:** `07-idempotency-resumability.md` Decision Fingerprinting section + SharedLineAnalyzer fingerprint() example

**Test fixtures needed:**
- Store pre-seeded with mapped objects (Phase 6 output): shared line pair, incompatible devices (with existing mapper decisions), users with missing email, duplicate email users, CSS-mapped objects
- Fixture covering each of the 12 analyzer trigger conditions

### Phase 8: Plan + Execute + Rollback (Layers 3d + 4)

**Files:** `planner.py` (full), `dependency.py` (full), `batch.py`, `preflight.py`, `snapshot.py`, `executor.py`, `rollback.py` + tests
**Sessions:** 25-27

**Acceptance:**

1. **Planner expands all object types.** Given analyzed objects of types: location, user, device, hunt_group, call_queue, auto_attendant, trunk, dial_plan, the planner produces `MigrationOp` entries for each. A user expands to 5 ops: create, assign_license, assign_number, configure_settings, configure_voicemail (from 05-dependency-graph.md example).
    - **Source:** `05-dependency-graph.md` expand_to_operations() example

2. **DAG construction.** Given expanded operations, `build_dependency_graph(ops)` produces a NetworkX DiGraph. Verify: location:create has no incoming edges, user:create depends on location:create (cross-object REQUIRES edge), user:assign_license depends on user:create (intra-object CONFIGURES edge).
    - **Source:** `05-dependency-graph.md` Building the Graph section

3. **Tier validation.** Given a valid DAG, `validate_tiers(G)` returns no violations (no edge from higher tier to lower tier). Given a manually inserted violation (tier 3 → tier 2 edge), returns the violation.
    - **Source:** `05-dependency-graph.md` validate_tiers() function

4. **Cycle detection — SOFT cycle broken.** Given two AAs where AA1 transfers to AA2 and AA2 transfers to AA1 (SOFT edges), `detect_and_break_cycles(G)` breaks one edge and returns a `BrokenCycle` with the deferred operation moved to tier 7 fixup.
    - **Source:** `05-dependency-graph.md` Cycle Detection and Breaking section

5. **Cycle detection — all-REQUIRES cycle → hard error.** Given an artificial all-REQUIRES cycle, `detect_and_break_cycles(G)` returns an error string (not a broken cycle).
    - **Source:** `05-dependency-graph.md` "Key safety" paragraph

6. **Batch partitioning.** Given ops with batch assignments, `partition_into_batches(G)` produces batches in order: org-wide (tiers 0-2) → site-hq (tiers 2-6) → site-branch-a → fixups (tier 7).
    - **Source:** `05-dependency-graph.md` Batch Partitioning section

7. **Preflight checks.** Given a mocked Webex API, `preflight.run(store, api)` checks: license availability, location existence, PSTN readiness, number conflicts (between planned E.164 and existing Webex numbers), and returns a pass/fail report.
    - **Source:** Part 1, Phase 8 session 26 description

8. **Snapshot capture.** Given existing Webex resources at risk of modification, `snapshot.capture(store, api)` saves their current state to `snapshots/` directory for rollback reference.
    - **Source:** `cucm-pipeline-architecture.md` on-disk layout (snapshots/)

9. **Executor walks topological order.** Given a plan with 3 tiers, the executor processes tier 0 ops before tier 1, tier 1 before tier 2. Within a tier, independent ops can run concurrently. Each completed op writes a journal entry.
    - **Source:** `05-dependency-graph.md` batch execution + `01-data-representation.md` journal table

10. **Executor skips completed operations on re-run.** Given a journal showing op "user:jsmith:create" as completed, re-running the executor skips that op.
    - **Source:** `07-idempotency-resumability.md` "Execute" row in Full Idempotency Guarantee table

11. **Rollback walks journal in reverse.** Given a journal with CREATE entries, `rollback.run(store, api)` processes them in reverse order, applying type-appropriate reversal (DELETE for CREATE, PUT pre_state for MODIFY).
    - **Source:** Part 1, Phase 8 session 27 description

**Test fixtures needed:**
- Analyzed objects covering all major types (location, user, device, HG, CQ, AA, trunk, dial plan)
- Mocked Webex API responses for: location create, person create, device activation, license assignment, number assignment
- Pre-built DAG with known cycle patterns

### Phase 9: Validate + Report + CLI (Layers 5 + 6)

**Files:** `comparator.py`, `report.py`, `cucm.py`, `cucm_config.py` + tests
**Sessions:** 28-29

**Acceptance:**

1. **Comparator read-back validation.** Given a completed migration, `comparator.validate(store, api)` reads back every Webex resource, compares key fields against the canonical model, and flags mismatches. For a user: compare email, extension, locationId. For a location: compare name, timeZone, address.
    - **Source:** Part 1, Phase 9 session 28 description

2. **Report generation.** Given a completed migration with decisions (5 resolved, 2 skipped, 1 failed), `report.generate(store)` produces a markdown report with sections: migration summary, unmapped objects, decisions and their resolutions, CSS warnings, phone replacement list (incompatible devices), firmware conversion instructions (convertible devices).
    - **Source:** Part 1, Phase 9 session 28 description

3. **CLI `cucm analyze` command.** Given a store with normalized objects, `wxcli cucm analyze` calls `engine.map(store)` then `pipeline.analyze(store)`, prints a summary (N decisions by type/severity), and exits.
    - **Source:** Part 1, Anti-Pattern 6 ("cucm.py analyze calls engine.map(store) then pipeline.analyze(store)")

4. **CLI `cucm decisions` command.** Given a store with pending decisions, `wxcli cucm decisions` displays a Rich table with columns: ID, Type, Severity, Status, Summary. Supports `--type`, `--severity`, `--status` filters.
    - **Source:** `06-decision-workflow.md` browsing decisions CLI output

5. **CLI commands are thin wrappers.** Each CLI command in `cucm.py` is ≤20 lines of Typer glue: parse args, call pipeline function, format output via `output.py`. No business logic in CLI commands.
    - **Source:** Part 1, Anti-Pattern 6

**Test fixtures needed:**
- Completed migration store with journal entries, decisions at various states
- Mocked Webex API for comparator read-back

### Phase 10: Agent + Skills + Polish (Layer 7)

**Files:** `cucm-migration-builder.md` agent, `cucm-discovery/SKILL.md`, `cucm-migration/SKILL.md`, reference docs
**Sessions:** 30

**Acceptance:**

1. **Agent follows wxc-calling-builder.md pattern.** The migration agent: interviews the user (CUCM cluster, target org, migration scope), generates a deployment plan, executes CLI commands, and verifies results.
    - **Source:** Part 1, Phase 10 description

2. **Skills provide guided workflows.** `cucm-discovery/SKILL.md` guides through `wxcli cucm connect` → `wxcli cucm discover` → `wxcli cucm inventory`. `cucm-migration/SKILL.md` guides through analyze → decisions → plan → preflight → execute → validate.
    - **Source:** Part 1, Phase 10 description

3. **Reference docs cover AXL mapping and implementation gotchas.** `cucm-migration.md` documents the AXL object mapping and known gotchas discovered during implementation. `cucm-axl-mapping.md` provides field-level CUCM↔Webex mapping.
    - **Source:** Part 1, Phase 10 description, `cucm-wxc-migration.md` file map

**Test fixtures needed:**
- None (markdown files, tested by human review)

---

## 3. Parallelization Map

**Source:** `cucm-build-strategy.md` §4 Build Phase Summary Table + Parallelism Map

### Session Schedule

```
Stream A (main)          Stream B (parallel)       Notes
─────────────────────    ─────────────────────     ──────────────────────
Session 1: Phase 1                                 models.py, tests
  models.py, tests
Session 2: Phase 1                                 store.py, state.py, rate_limiter.py
  store.py + tests
                         ─── GATE: Phase 1 complete ───
Session 3: Phase 2                                 Location normalizer, CrossRefBuilder scaffold
  Normalize + CrossRef
Session 4: Phase 2                                 engine.py scaffold, location_mapper
  Mapper + engine
Session 5: Phase 2                                 Analyzer scaffold, planner scaffold, thin thread test
  Analyzer + planner
                         ─── GATE: Phase 2 complete ───
Session 6: Phase 3       Session 6: Phase 3        Spikes 1+3 and 2+5 are independent
  Spike 1: cucm_pattern    Spike 2: e164.py
Session 7: Phase 3       Session 7: Phase 3
  (cucm_pattern cont.)    Spike 5: feature_mapper classification
Session 8: Phase 3       Session 8: Phase 4
  Spike 3: css_mapper      Extraction: connection.py + 3 extractors
Session 9: Phase 3       Session 9: Phase 4
  Spike 3-4: css cont.     Extraction: remaining extractors + discovery.py
Session 10: Phase 3
  Spike 3-4 completion
                         ─── GATE: Phase 3 spikes complete ───
Session 11: Phase 5      (Phase 4 already done)
  ~12 normalizers
Session 12: Phase 5
  Full CrossRefBuilder
                         ─── GATE: Phase 5 complete ───
Session 13: Phase 6      Session 13: Phase 6       4-way parallelism possible
  user_mapper              line_mapper              (sessions 13-16 are independent)
Session 14: Phase 6      Session 14: Phase 6
  device_mapper +          routing_mapper
  workspace_mapper
                         ─── GATE: sessions 13-14 mappers complete ───
Session 15: Phase 6                                voicemail_mapper + css_mapper completion
  vm + css_mapper
Session 16: Phase 6                                feature_mapper completion
  feature_mapper
Session 17: Phase 6                                engine.py completion, rules.py, integration test
  engine + integration
                         ─── GATE: Phase 6 complete ───
Session 18: Phase 7      Session 18: Phase 7       3-way parallelism
  Pipeline + simple        SharedLine + Extension
  analyzers (4)            + Number analyzers (3)
Session 19: Phase 7
  CSS + Feature + VM +
  Location analyzers (5)
                         ─── GATE: Phase 7 complete ───
Session 20: Phase 8                                planner full + dependency full + batch
  Plan layer
Session 21: Phase 8                                preflight + snapshot (mocked Webex API)
  Preflight + snapshot
Session 22: Phase 8                                executor + rollback
  Execute + rollback
                         ─── GATE: Phase 8 complete ───
Session 23: Phase 9                                comparator + report
  Validate + report
Session 24: Phase 9                                CLI commands (cucm.py, cucm_config.py)
  CLI layer
                         ─── GATE: Phase 9 complete ───
Session 25: Phase 10                               Agent, skills, reference docs
  Agent + skills
```

### Dependency Arrows

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 5 ──→ Phase 6 ──→ Phase 7 ──→ Phase 8 ──→ Phase 9 ──→ Phase 10
                    └──→ Phase 4 (parallel, off critical path) ──┘
                                                                  │
                              Phase 3 spikes feed into ───────────┘
```

**Explicit dependencies:**

| Phase | Depends on | Reason |
|-------|-----------|--------|
| Phase 2 | Phase 1 | Imports models.py, store.py |
| Phase 3 | Phase 1-2 | Uses store, normalizer pattern from Phase 2 |
| Phase 4 | Phase 1 | Imports models for dict shape. Soft dependency on Phase 5 (normalizer fixture shapes) |
| Phase 5 | Phase 2 | Follows normalizer pattern. Soft dependency on Phase 4 (AXL response shapes) |
| Phase 6 sessions 13-16 | Phase 3 (spike outputs), Phase 5 (normalizers + cross-refs) | Mappers use spike code (cucm_pattern, e164, css core, feature classification) and read from normalized store |
| Phase 6 sessions 17-19 | Phase 6 sessions 13-16 | css_mapper needs routing_mapper output; engine.py integration test needs all mappers |
| Phase 7 | Phase 6 | Analyzers sweep mapped objects |
| Phase 8 | Phase 7 | Planner reads analyzed objects + decisions |
| Phase 9 | Phase 8 | CLI wraps executor, comparator needs execution output |
| Phase 10 | Phase 9 | Agent references CLI commands |

**Best-case elapsed with 2 streams:** ~22-24 sessions (from Part 1: "Best-case calendar with 2 parallel streams: ~20-22 sessions elapsed").

**Serial execution:** 29-30 sessions.

---

## 4. Testing Strategy

**Source:** `cucm-build-strategy.md` Anti-Patterns 1-3 (testing approach), architecture docs (test boundaries)

### Testing Approach Per Phase

| Phase | Primary Approach | Secondary | Fixture Type |
|-------|-----------------|-----------|-------------|
| 1: Foundation | **Contract tests** — Pydantic round-trip, SQLite schema validation | Unit tests for state machine, rate limiter | Programmatic model construction |
| 2: Location Thread | **Fixture-driven** — hand-crafted CUCM dicts through normalizer→mapper→analyzer→planner | Integration test (end-to-end thin thread) | `make_cucm_device_pool()` + `make_cucm_location_entity()` factories |
| 3: Risk Spikes | **Fixture-driven** — pattern pairs, DN strings, CSS graphs, hunt pilot chains | Edge case unit tests (25+ patterns, 20+ DNs) | Inline test data (no factory needed for strings) |
| 4: Extraction | **Contract tests** — extractor output matches fixture factory dict shape | Mocked SOAP tests | Mocked AXL XML responses |
| 5: Normalizers + CrossRef | **Fixture-driven** — each normalizer gets input dict → assert output model | Verification sweep (27 cross-ref types exist) | Factory functions per CUCM type |
| 6: Mappers | **Fixture-driven** — `:memory:` store seeded with normalized objects | Integration test (messy multi-object scenario) | Pre-seeded store with cross-refs |
| 7: Analyzers | **Fixture-driven** — store seeded with mapped objects | Contract test (analyzer-mapper decision ownership) | Pre-seeded store with mapped objects + some existing decisions |
| 8: Plan + Execute | **Contract tests** — DAG structure, tier validation, cycle detection | **Golden file tests** — plan output for known input snapshot | Mocked Webex API responses |
| 9: Validate + CLI | **Integration tests** — CLI end-to-end with `:memory:` store | Golden file tests for report output | Completed migration store |
| 10: Agent + Skills | **Human review** | N/A | N/A |

### Anti-Pattern 1 Enforcement: Real Store, Not Mocks

**Source:** Part 1, Anti-Pattern 1

**Rule:** All mapper and analyzer tests use `:memory:` SQLite databases with the real schema. No `MagicMock()` on `MigrationStore`. The store is fast enough (microseconds per query) that there's no performance reason to mock.

```python
# Every mapper/analyzer test follows this pattern:
def test_user_mapper_email_resolution():
    store = MigrationStore(":memory:")
    store.upsert_object(make_canonical_user(email="jsmith@acme.com"))
    store.add_cross_ref("device:SEP001", "user:jsmith", "device_owned_by_user")
    # ... seed more fixtures
    mapper = UserMapper()
    result = mapper.map(store)
    # Assert against REAL store state after mapping
    users = store.query_by_type("user")
    assert users[0].email == "jsmith@acme.com"
```

### Anti-Pattern 2 Enforcement: Fixture Factories, Not Static Files

**Source:** Part 1, Anti-Pattern 2

**Rule:** No static XML fixture files. All CUCM dicts are built programmatically via factory functions (`make_cucm_phone()`, `make_cucm_user()`, `make_cucm_route_pattern()`, etc.). Each test builds only the fields it needs. Factory defaults cover the common case.

### Anti-Pattern 3 Enforcement: Messy Paths Required

**Source:** Part 1, Anti-Pattern 3

**Rule:** Each mapper gets at least two test scenarios: (1) happy path — one clean object, (2) messy path — multiple objects with edge cases from 03b spec. The Phase 6 integration test (session 21) loads ALL edge cases simultaneously.

### High-Risk Area Coverage

#### 1. CSS Decomposition

**Source:** `04-css-decomposition.md`, `03b-transform-mappers.md` §7 + §12

**Test scenarios:**

| Scenario | Input | Expected Output |
|----------|-------|-----------------|
| Single routing scope (happy path) | 2 CSSes with identical ROUTING partitions | Org-wide dial plans, no CSS_ROUTING_MISMATCH |
| Multiple routing scopes | 2 CSSes with different ROUTING partitions | Intersection → baseline dial plans, delta → CSS_ROUTING_MISMATCH decisions |
| MIXED partition | CSS with partition containing both ROUTE and BLOCK patterns | Virtual split into ROUTING + BLOCKING, CSS_ROUTING_MISMATCH decision |
| Ordering conflict — route shadows block | ROUTE pattern at priority 1, overlapping BLOCK pattern at priority 2 | CSS_ROUTING_MISMATCH with "Webex LESS restrictive" risk assessment |
| Ordering conflict — block shadows route | BLOCK pattern at priority 1, overlapping ROUTE pattern at priority 2 | CSS_ROUTING_MISMATCH with "Webex MORE restrictive" risk assessment |
| Unclassifiable block pattern | Block pattern `"9.1408XXXXXXX"` (specific area code) not matching any Webex category | CALLING_PERMISSION_MISMATCH decision |
| Empty restriction profile | CSS with no BLOCKING partitions | Allow-all in Webex (INFO, not a decision) |

**Pattern overlap tests** (from cucm_pattern.py):
- `"9.!"` vs `"9.011!"` → overlap (broad vs international)
- `"9.1[2-9]XXXXXXXXX"` vs `"9.1900XXXXXXX"` → overlap (ranges)
- `"9.1[2-9]XXXXXXXXX"` vs `"9.011!"` → no overlap (domestic vs international)
- `"9.[2-9]XXXXXX"` vs `"9.1[2-9]XXXXXXXXX"` → no overlap (local vs long distance)
- `"+1XXXXXXXXXX"` vs `"+1900XXXXXXX"` → overlap (E.164 format)
- Patterns with `[^5]` negated ranges
- `@` macro → flagged as requiring expansion

#### 2. E.164 Normalization

**Source:** `02-normalization-architecture.md` normalize_dn(), Part 1 Spike 3

**Test scenarios:**

| Input DN | Country | Prefix Rules | Expected Classification | Expected E.164 |
|----------|---------|-------------|------------------------|----------------|
| `1001` | US | none | EXTENSION | — (extension only) |
| `5551234567` | US | none | NATIONAL | +15551234567 |
| `+15551234567` | US | none | E164 | +15551234567 |
| `91234567890` | US | strip "9" | NATIONAL | +11234567890 |
| `2001` | GB | none | EXTENSION | — |
| `02012345678` | GB | none | NATIONAL | +442012345678 |
| `+442012345678` | GB | none | E164 | +442012345678 |
| `5` (1-digit) | US | none | AMBIGUOUS (or MISSING_DATA) | — |
| `123456789012345678901234` (24-digit) | US | none | AMBIGUOUS | — |
| `5551234567` | GB | none | Different classification than US | Depends on GB rules |
| `91234567890` | US | strip "9" (prefix IS start of valid number) | NATIONAL after strip | +11234567890 |

#### 3. Shared Line Detection

**Source:** `02-normalization-architecture.md` _detect_shared_lines(), `03-conflict-detection-engine.md` SharedLineAnalyzer

**Test scenarios:**

| Scenario | Devices | Owners | Expected |
|----------|---------|--------|----------|
| 2-device, 1 owner, same user | SEP001, SEP002 — both owned by jsmith | 1 (jsmith) | SHARED_LINE_COMPLEX, severity MEDIUM, "Shared Line" option available |
| 2-device, 2 owners | SEP001 (jsmith), SEP002 (jdoe) | 2 | SHARED_LINE_COMPLEX, severity MEDIUM, "Shared Line" option available |
| 4-device, 3 owners | SEP001 (jsmith), SEP002 (jdoe), SEP003 (mbrown), SEP004 (mbrown) | 3 | SHARED_LINE_COMPLEX, severity HIGH, NO "Shared Line" option (>2 devices) |
| Same user, multiple devices, same DN | jsmith has desk + softphone sharing DN 1001 | 1 | SHARED_LINE_COMPLEX, severity MEDIUM |
| DN on single device | SEP001 only | 1 | No decision (not shared) |

#### 4. Dependency Graph

**Source:** `05-dependency-graph.md`

**Test scenarios:**

| Scenario | Graph Structure | Expected |
|----------|----------------|----------|
| Normal acyclic | locations(T0) → users(T2) → devices(T3) | Valid topological sort, no violations |
| Tier validation pass | All edges from lower/equal tier to higher/equal tier | `validate_tiers()` returns empty list |
| Tier validation fail | Artificial edge from T3 → T2 | `validate_tiers()` returns 1 violation |
| SOFT cycle — AA mutual transfer | AA1 →(SOFT) AA2 →(SOFT) AA1 | One edge broken, fixup op in tier 7 |
| SOFT cycle — mutual monitoring | User A →(SOFT) User B →(SOFT) User A | One edge broken, fixup op in tier 7 |
| All-REQUIRES cycle | A →(REQ) B →(REQ) A | Hard error, NOT broken silently |
| Mixed cycle | A →(REQ) B →(SOFT) C →(REQ) A | SOFT edge broken (weakest) |
| No false cycles | Large acyclic graph (50+ nodes) | `detect_and_break_cycles()` returns empty lists |

#### 5. Decision Merge (Re-Analyze)

**Source:** `07-idempotency-resumability.md`

**Test scenarios:**

| Scenario | Before Re-Analyze | After Re-Analyze | Expected Merge |
|----------|-------------------|------------------|----------------|
| Resolved, same fingerprint | D001 resolved as "skip" | Same condition → same fingerprint | `kept=1` — resolution preserved |
| Pending, same fingerprint | D002 pending | Same condition, updated context | `updated=1` — context updated |
| New decision | No D003 | New condition detected | `new=1` — inserted |
| Stale pending | D004 pending | Condition no longer exists | `stale=1` — marked stale |
| Invalidated resolved | D005 resolved as "virtual_line" | Condition changed (4th device added → fingerprint changed) | `invalidated=1` — moved back to PENDING |
| Cascade trigger | D006 resolved, depends on D007 | D007 invalidated | D006 should be re-evaluated (cascade) |

**Fingerprint stability test:** Given identical CUCM data, `analyzer.fingerprint(type, context)` produces the same hash on every call. Changing one causal field (e.g., adding an owner to a shared line) produces a different hash.

---

## Self-Review Checklist

- [x] **Every phase from Part 1's build order has acceptance criteria.** Phases 1-10 all covered (10 sections in §2).
- [x] **Every layer boundary has an interface contract.** 6 boundary contracts + MigrationStore API defined in §1: Layer 1→everything, Layer 2→3a, Layer 3a→3b, Layer 3b→3c, Layer 3c→3d, Layer 3d→4.
- [x] **MigrationStore API is fully defined.** 18 methods with signatures, source citations, and cross-layer usage matrix (§1 "Complete MigrationStore Method Summary").
- [x] **Parallelization map doesn't schedule anything before its dependency.** All GATE points in the session schedule correspond to dependency arrows. Phase 4 runs parallel only with Phases 3/5 (depends only on Phase 1). Phase 6 sessions 13-16 parallelize only mappers that are independent of each other.
- [x] **Acceptance criteria are specific enough to write tests from.** All criteria use "Given X input, Y produces Z output" format. No "works correctly" — each criterion specifies concrete inputs, function names, and expected outputs.
- [x] **At least 3 CUCM fixture dict examples included.** 3 full fixture factories: EndUser (§1 Layer 2→3a Fixture 1), Phone (Fixture 2), RoutePattern (Fixture 3), plus summary shapes for DevicePool, CSS, Partition, HuntPilot, CTIRoutePoint.
- [x] **Testing strategy covers 5 specific high-risk areas.** §4 includes detailed test scenario tables for: CSS decomposition (7 scenarios + 7 pattern overlap tests), E.164 normalization (11 test cases), shared line detection (5 scenarios), dependency graph (8 scenarios), decision merge (6 scenarios + fingerprint stability test).

### Final Verification: Both Sides Defined for Every Contract

| Contract | Producer side defined? | Consumer side defined? | Match? |
|----------|----------------------|----------------------|--------|
| Layer 1 → everything | Yes (Pydantic models, fields, enums) | Yes (every consumer listed per field) | Yes — types and fields are explicit |
| Layer 2 → Layer 3a | Yes (3 fixture dicts with load-bearing fields) | Yes (normalizer pass 1 accesses documented fields) | Yes — `_value_1` nesting pattern explicit |
| Layer 3a → Layer 3b | Yes (objects table + 27 cross-ref types) | Yes (mapper cross-ref dependency tables from 03b) | Yes — all 27 relationships have named consumers |
| Layer 3b → Layer 3c | Yes (MapperResult, TransformResult, status=analyzed) | Yes (Analyzer base class, query patterns) | Yes — analyzer reads exactly what mappers write |
| Layer 3c → Layer 3d | Yes (AnalysisResult, decisions table, status=analyzed) | Yes (expand_to_operations reads by status) | Yes — planner reads analyzed objects + decisions |
| Layer 3d → Layer 4 | Yes (plan_operations + plan_edges tables) | Yes (executor reconstructs DAG, walks topo order) | Yes — table schemas match on both sides |
| MigrationStore | Yes (18 methods with signatures) | Yes (per-method consumer list) | Yes — method summary table maps methods to layers |

### Citation Audit

Every field name, method signature, and column name in this document cites its source architecture doc. Fields without a source are explicitly marked `` or "Not specified in architecture docs — builder decides." A grep for unmarked fields found:

- `affected_objects` on Decision: referenced in 07-idempotency-resumability.md merge_decisions() but not in 01-data-representation.md schema → flagged as "Not specified in architecture docs"
- `blockEnable` on route pattern: referenced as the action classification field but not confirmed as the AXL field name → flagged as ``
- `associatedDevices.device[]` nesting: standard AXL pattern but not shown in any architecture doc → flagged as "Builder should verify"

All other field names, method signatures, and column names trace to their source doc.
