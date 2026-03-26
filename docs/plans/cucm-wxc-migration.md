Context
Webex Calling customers migrating from on-premises CUCM need a way to extract their existing configuration via AXL (Administrative XML Layer), transform it to Webex Calling API payloads, and execute the migration through the existing wxcli infrastructure. This framework treats migration as a stateful, multi-phase data pipeline — fundamentally different from the stateless CRUD commands that exist today.
Scope decisions:

CUCM versions: 12.5+ only
Scale: Single cluster, 1K–10K users (needs pagination, rate limiting, progress tracking)
PSTN: Config + trunk setup (configure Webex trunks/route groups pointing back to existing gateways, but no number porting)
Coexistence: During migration, CUCM retains PSTN DID routing. Calls to migrated users route via CUCM→Webex trunk (see PSTN Coexistence section).


Architecture Overview
CUCM Cluster (AXL/SOAP)
        │
   ┌────▼─────┐
   │ Discovery │  extractors pull CUCM objects via AXL
   └────┬──────┘
        │ Raw CUCM dicts
   ┌────▼──────┐
   │ Normalize │  CUCM dicts → Canonical Pydantic models
   └────┬──────┘
        │ MigrationInventory (JSON on disk)
   ┌────▼──────┐
   │ Analyze   │  Map to Webex, detect conflicts, generate decisions
   └────┬──────┘
        │
   ┌────▼──────┐
   │ Plan      │  Dependency graph → topological sort → batches
   └────┬──────┘
        │ ExecutionPlan (JSON)
   ┌────▼───────────┐
   │ Preflight      │  Verify Webex org readiness (licenses, PSTN, features)
   └────┬───────────┘
        │
   ┌────▼──────┐
   │ Snapshot   │  Capture pre-migration Webex state for rollback
   └────┬──────┘
        │
   ┌────▼──────┐
   │ Execute   │  Webex REST via existing api.session.rest_*()
   └────┬──────┘
        │
   ┌────▼──────┐
   │ Validate  │  Read-back every object, compare, report
   └──────────┘
State persisted at ~/.wxcli/migrations/<project_id>/ — resumable from any phase.

Module Structure
src/wxcli/
  migration/                          # New package
    __init__.py
    models.py                         # Canonical data models (Pydantic)
    state.py                          # Migration state machine + JSON persistence
    rate_limiter.py                   # Per-endpoint throttling + retry-with-backoff
    cucm/
      __init__.py
      connection.py                   # AXL SOAP client (zeep + requests)
      discovery.py                    # Orchestrates extractors, cross-references
      extractors/
        __init__.py
        users.py                      # EndUser + associated phones/lines
        devices.py                    # Phones, device profiles, line appearances
        features.py                   # Hunt pilots, CTI RPs, call park, pickup, paging
        routing.py                    # Partitions, CSS, route patterns, gateways, trunks
        locations.py                  # Device pools → locations
        voicemail.py                  # Voicemail profiles, pilot numbers
        shared_lines.py               # Shared line appearances across devices
        workspaces.py                 # Conference room phones, common-area devices
    transform/
      __init__.py
      engine.py                       # Orchestrates mappers, detects conflicts
      mappers/
        __init__.py
        location_mapper.py            # DevicePool → Location
        user_mapper.py                # EndUser → Person
        device_mapper.py              # SEP phone → Webex device (with model compat table)
        line_mapper.py                # DN/Line → Number + Extension (E.164 normalization)
        feature_mapper.py             # CTI RP → AA, HuntPilot → HG, etc.
        routing_mapper.py             # RoutePattern → DialPlan, Gateway → Trunk
        css_mapper.py                 # CSS → dial plans + per-user calling permissions
        voicemail_mapper.py           # Unity Connection profile → Webex voicemail settings
        workspace_mapper.py           # CUCM common-area phones → Webex Workspaces
      rules.py                        # Auto-resolution rules for common conflicts
      decisions.py                    # Human decision point tracking
      e164.py                         # E.164 normalization engine (country code, prefix rules)
    execute/
      __init__.py
      executor.py                     # Ordered execution with journaling + rate limiting
      dependency.py                   # DAG + topological sort
      batch.py                        # Site-by-site phased execution
      rollback.py                     # Type-aware rollback (DELETE/PUT/un-assign)
      preflight.py                    # Webex org readiness checks
      snapshot.py                     # Pre-migration Webex state capture
    validate/
      __init__.py
      comparator.py                   # Source vs target comparison
      report.py                       # Markdown migration report
  commands/
    cucm.py                           # NEW: hand-coded CLI command group
    cucm_config.py                    # NEW: CUCM connection configuration

docs/reference/
  cucm-migration.md                   # AXL overview, object mapping, gotchas
  cucm-axl-mapping.md                 # Complete field-level CUCM↔Webex mapping

.claude/
  agents/cucm-migration-builder.md    # Migration-specific agent (interview→discover→execute)
  skills/cucm-discovery/SKILL.md      # CUCM inventory discovery skill
  skills/cucm-migration/SKILL.md      # Migration execution skill

Canonical Data Model (models.py)
All objects carry provenance (source system, source ID) and migration state. The canonical model decouples CUCM extraction from Webex provisioning.
```python
class MigrationStatus(str, Enum):
    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    NEEDS_DECISION = "needs_decision"
    PLANNED = "planned"
    PREFLIGHT_PASSED = "preflight_passed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"

class Provenance(BaseModel):
    source_system: str          # "cucm" or "webex"
    source_id: str              # CUCM pkid or Webex UUID
    source_name: str
    cluster: str | None = None
    extracted_at: datetime
    cucm_version: str | None = None

class MigrationObject(BaseModel):
    """Base for all migratable objects."""
    canonical_id: str
    provenance: Provenance
    status: MigrationStatus = MigrationStatus.DISCOVERED
    webex_id: str | None = None
    pre_migration_state: dict | None = None  # Webex state before migration (for rollback)
    errors: list[str] = []
    warnings: list[str] = []
    depends_on: list[str] = []      # canonical_ids of prerequisites
    batch: str | None = None

# Concrete types: CanonicalLocation, CanonicalUser, CanonicalDevice,
# CanonicalLine, CanonicalHuntGroup, CanonicalCallQueue,
# CanonicalAutoAttendant, CanonicalTrunk, CanonicalDialPlan,
# CanonicalRouteGroup, CanonicalTranslationPattern,
# CanonicalOperatingMode, CanonicalCallPark, CanonicalPickupGroup,
# CanonicalPagingGroup, CanonicalVoicemailProfile,
# CanonicalSharedLine, CanonicalVirtualLine, CanonicalWorkspace,
# CanonicalCallingPermission
# Each preserves CUCM-specific fields (cucm_device_pool, cucm_css, etc.)
#
# Key mapper-produced fields per type (not exhaustive — see 03b-transform-mappers.md for full details):
#   CanonicalLocation: calling_enabled (bool), routingPrefix, outsideDialDigit
#   CanonicalUser: create_method ("scim"|"people_api"), calling_data (bool), cucm_manager_user_id
#   CanonicalLine: shared (bool), e164 (str|None), classification ("EXTENSION"|"NATIONAL"|"E164"|"AMBIGUOUS")
#   CanonicalDevice: compatibility_tier ("native_mpp"|"convertible"|"incompatible"), cucm_protocol ("SIP"|"SCCP")
#   CanonicalWorkspace: is_common_area (bool, from normalizer), hotdeskingStatus
#   CanonicalCallingPermission: assigned_users[] (list of user canonical_ids sharing this profile)
#   CanonicalRouteGroup: name, localGateways[] (trunk refs with priority)
#   CanonicalTranslationPattern: name, matchingPattern, replacementPattern

class MigrationInventory(BaseModel):
    """Single source of truth for the migration."""
    project_id: str
    cucm_cluster: str
    locations: list[CanonicalLocation] = []
    users: list[CanonicalUser] = []
    devices: list[CanonicalDevice] = []
    lines: list[CanonicalLine] = []
    hunt_groups: list[CanonicalHuntGroup] = []
    call_queues: list[CanonicalCallQueue] = []
    auto_attendants: list[CanonicalAutoAttendant] = []
    trunks: list[CanonicalTrunk] = []
    dial_plans: list[CanonicalDialPlan] = []
    route_groups: list[CanonicalRouteGroup] = []
    translation_patterns: list[CanonicalTranslationPattern] = []
    operating_modes: list[CanonicalOperatingMode] = []
    call_parks: list[CanonicalCallPark] = []
    pickup_groups: list[CanonicalPickupGroup] = []
    paging_groups: list[CanonicalPagingGroup] = []
    voicemail_profiles: list[CanonicalVoicemailProfile] = []
    shared_lines: list[CanonicalSharedLine] = []
    virtual_lines: list[CanonicalVirtualLine] = []
    workspaces: list[CanonicalWorkspace] = []
    calling_permissions: list[CanonicalCallingPermission] = []
    unmapped: list[dict] = []
    pending_decisions: list[dict] = []
```

---

## CUCM ↔ Webex Object Mapping

| CUCM Object | Webex Equivalent | Mapping Complexity |
|---|---|---|
| Device Pool | Location | Medium — need timezone, address, emergency |
| End User | Person | Medium — email required, license assignment |
| Phone (SEP) | Device | High — model compatibility, firmware conversion, line mapping |
| Common-Area Phone | Workspace + Device | Medium — workspace creation, license tier |
| DN / Line | Phone Number + Extension | Medium — E.164 normalization (see algorithm) |
| Shared Line Appearance | Virtual Line or Shared Line | **High** — multiple devices, primary/secondary ownership |
| Hunt Pilot + Hunt List + Line Group | Hunt Group | High — 3 CUCM objects → 1 Webex object |
| Hunt Pilot (queue-style) | Call Queue | High — depends on CUCM hunt algorithm type |
| CTI Route Point + Script | Auto Attendant | High — IVR logic approximation |
| Gateway / SIP Trunk | Trunk | Medium — SBC address, port, certs |
| Route Pattern | Dial Plan Pattern | Medium — pattern syntax conversion |
| Route Group | Route Group | Low — direct mapping |
| Translation Pattern | Translation Pattern | Medium — digit manipulation rules |
| Call Park | Call Park | Low |
| Pickup Group | Call Pickup | Low |
| Paging Group | Paging Group | Low |
| Time Period + Time Schedule | Schedule | Low — direct mapping |
| Call Forward (CFA/CFB/CFNA) | Person Call Forwarding | Low — per-user settings |
| Voicemail Profile | Person Voicemail Settings | Medium — Unity Connection differences |
| Partition + CSS (routing scope) | Org-wide Dial Plans | **High** — flat model, no per-user routing scope |
| Partition + CSS (call blocking) | Per-user Outgoing Calling Permissions | **High** — must decompose CSS into routing vs restrictions |
| Region / Location (bandwidth) | N/A | Not migratable (cloud-managed) |
| SRST | N/A | Not migratable |
| Phone Button Template | N/A | Different device UX model |
| Speed Dial | N/A | Client-side in Webex |
| Intercom | N/A | Not available in Webex Calling |

---

## State Machine
```
INITIALIZED → CONNECTED → DISCOVERED → ANALYZED
                                           │
                                     ┌─────┴─────┐
                                     ▼           ▼
                                   READY      BLOCKED (pending decisions)
                                     │           │
                                     │     user resolves
                                     │           │
                                     │           ▼
                                     └─────►  PLANNED
                                                │
                                                ▼
                                           PREFLIGHT ──────► PREFLIGHT_FAILED
                                                │                  │
                                                ▼            fix issues, retry
                                           SNAPSHOTTED            │
                                                │◄────────────────┘
                                                ▼
                                           EXECUTING ──────► FAILED → ROLLED_BACK
                                                │
                                                ▼
                                           VALIDATING
                                                │
                                                ▼
                                           COMPLETED
```

BLOCKED → PLANNED: all pending decisions must be resolved before transitioning.
PREFLIGHT: verifies Webex org readiness (licenses, PSTN connections, feature entitlements).
SNAPSHOTTED: pre-migration Webex state captured for rollback.

State persisted to `~/.wxcli/migrations/<project_id>/state.json`. Resumable from any phase.

---

## CLI Commands
```
wxcli cucm connect                     # Configure CUCM host/user/version
wxcli cucm test                        # Test AXL connectivity
wxcli cucm discover                    # Full inventory extraction
wxcli cucm discover --type users       # Extract only users
wxcli cucm discover --site "Building A"  # One device pool/site
wxcli cucm inventory                   # Show discovery summary
wxcli cucm inventory --type users -o json
wxcli cucm analyze                     # Run transformation analysis
wxcli cucm decisions                   # Show pending human decisions
wxcli cucm decide <id> --choice <val>  # Resolve a decision
wxcli cucm plan                        # Generate execution plan
wxcli cucm plan --batch site-hq        # Plan one batch
wxcli cucm diff                        # Show CUCM→Webex mapping diff
wxcli cucm preflight                   # Verify Webex org readiness
wxcli cucm execute                     # Execute plan (with confirmations)
wxcli cucm execute --batch site-hq     # Execute one batch
wxcli cucm execute --dry-run           # Show what would be done
wxcli cucm validate                    # Verify migration results
wxcli cucm rollback                    # Undo executed steps
wxcli cucm rollback --batch site-hq
wxcli cucm status                      # Overall migration status
wxcli cucm report                      # Generate markdown report
wxcli cucm export                      # Export inventory to CSV
wxcli cucm import-decisions            # Bulk resolve from CSV
```

Registered in main.py following existing pattern:
```python
from wxcli.commands.cucm import app as cucm_app
app.add_typer(cucm_app, name="cucm")
```

---

## CUCM Connection Layer

Uses `zeep` (SOAP client) over HTTPS to CUCM AXL API:

- WSDL: `https://<cucm>:8443/axl/AXLAPIService?wsdl`
- Auth: HTTP Basic Auth (prompted at runtime, stored in system keyring via `keyring` lib)
- Pagination: AXL `first`/`skip` parameters, **200 rows per page** (AXL default max for `list*` operations; some operations have lower limits — page size is configurable per AXL method via `cucm_page_sizes` in config)
- Connection config stored in `~/.wxcli/config.json` under `cucm_profiles` key (no passwords in file)
- Version detection via `getCCMVersion()` AXL call

---

## Key Algorithms

### Dependency Ordering (Topological Sort)
```
Tier 0: Locations, Trunks (no inter-dependencies — trunks are org-level)
Tier 1: Schedules (depend on locations), Route Groups (depend on trunks)
Tier 2: Users, Workspaces, Dial Plans, Route Lists (depend on locations)
Tier 3: Devices, Virtual Lines, Number assignments (depend on users/workspaces)
Tier 4: Hunt Groups, Call Queues, Auto Attendants, Call Park, Pickup, Paging (depend on users + extensions)
Tier 5: User call settings, calling permissions, voicemail, device line assignments, AA menus (depend on features existing)
Tier 6: Forwarding rules, shared line assignments, monitoring lists (depend on extensions + features)
```

### CSS/Partition Decomposition

CUCM's Calling Search Space serves **two distinct purposes** that map to different Webex constructs:

**Purpose 1 — Routing scope** (which patterns a user can dial):
- For each user, trace CSS → partitions → route patterns to find effective routing scope
- Group users by identical effective scope
- If all users have same scope → map to org-wide dial plans
- If different scopes → generate `CSS_ROUTING_MISMATCH` decision explaining that Webex routing is org-wide flat

**Purpose 2 — Call restrictions** (blocking international, premium, etc.):
- For each CSS, identify partitions that contain **blocking** route patterns (e.g., `9.011!` to Block)
- Map blocking rules to **per-user Outgoing Calling Permissions** (incoming/outgoing permission settings)
- Group users by identical restriction profile
- Generate `CanonicalCallingPermission` objects for each unique restriction profile
- If restrictions can't be expressed in Webex permissions model → generate `CALLING_PERMISSION_MISMATCH` decision

The analyzer MUST decompose each CSS into both routing and restriction components separately.

### E.164 Normalization

CUCM DNs can be 4-digit extensions, 7/10-digit national numbers, or full E.164. The line mapper normalizes as follows:

1. **Configuration**: Migration config requires `default_country_code` (e.g., "+1") and optional per-site `site_prefix_rules` (e.g., site "HQ" strips leading "9" for outside line access)
2. **Classification**: Each DN is classified as:
   - `EXTENSION` — 3-6 digits, kept as Webex extension only (no DID)
   - `NATIONAL` — 7-10 digits, prepend country code → E.164
   - `E164` — already starts with "+", validate and pass through
   - `AMBIGUOUS` — doesn't fit above rules → generate `DN_AMBIGUOUS` decision
3. **Overlap detection**: After normalization, check for duplicate extensions across device pools. Same extension in different device pools that map to different locations → generate `EXTENSION_CONFLICT` decision
4. **Site prefix stripping**: Apply `site_prefix_rules` before classification (e.g., DN "91234567890" at site with rule "strip leading 9" → "1234567890" → national → "+11234567890")

### Extension Conflict Resolution
Check CUCM extensions against existing Webex extensions. Same-email matches = update-in-place. Different users = generate decision with options: reassign, new extension, or skip.

### Phone Model Compatibility

Three-tier classification of CUCM phone models:

| Category | Models | Action |
|---|---|---|
| **Native MPP** | 68xx, MPP 78xx/88xx (factory MPP) | Direct migration — assign to user in Webex |
| **Firmware Convertible** | Enterprise 78xx (7821/7841/7861), Enterprise 88xx (8845/8865) | Generate `DEVICE_FIRMWARE_CONVERTIBLE` decision with conversion steps: (1) factory reset, (2) load MPP firmware via TFTP/EDOS, (3) register to Webex. User can choose: convert, replace, or skip. |
| **Incompatible** | 79xx, 99xx, 69xx, 39xx, older 78xx (7811) | `DEVICE_INCOMPATIBLE` — user migrated without device. Report lists replacement recommendations. |

### Shared Line Handling

CUCM shared lines (same DN on multiple devices) require special handling:
1. **Identify shared DNs**: DN appears on >1 device with different owners
2. **Primary owner**: User whose device has the DN on line 1
3. **Migration options** (generated as `SHARED_LINE_COMPLEX` decision):
   - Map to Webex **Virtual Line** — shared line assigned to virtual line, appearances on multiple devices
   - Map to Webex **Shared Line** — if only 2 devices, simpler model
   - Convert to **Call Park + Speed Dial** — if shared line was used for monitoring only
   - Skip — handle manually post-migration

### Conflict & Decision System
```python
class DecisionType(str, Enum):
    EXTENSION_CONFLICT = "extension_conflict"
    NUMBER_CONFLICT = "number_conflict"
    DN_AMBIGUOUS = "dn_ambiguous"
    DEVICE_INCOMPATIBLE = "device_incompatible"
    DEVICE_FIRMWARE_CONVERTIBLE = "device_firmware_convertible"
    CSS_ROUTING_MISMATCH = "css_routing_mismatch"
    CALLING_PERMISSION_MISMATCH = "calling_permission_mismatch"
    FEATURE_APPROXIMATION = "feature_approximation"
    SHARED_LINE_COMPLEX = "shared_line_complex"
    LOCATION_AMBIGUOUS = "location_ambiguous"
    MISSING_DATA = "missing_data"
    DUPLICATE_USER = "duplicate_user"
    VOICEMAIL_INCOMPATIBLE = "voicemail_incompatible"
    WORKSPACE_LICENSE_TIER = "workspace_license_tier"
```

Each decision has options with impact descriptions. Resolvable individually (`wxcli cucm decide`), in bulk (CSV import), or auto-resolved by configurable rules.

---

## Webex Org Preflight Checks

Before execution, `wxcli cucm preflight` verifies the Webex org can receive the migration:

1. **Licenses**: Sufficient Webex Calling licenses available for planned user count (Professional vs Basic)
2. **Workspace licenses**: Sufficient workspace licenses for common-area devices
3. **Locations**: Each target location exists and has a PSTN connection configured
4. **PSTN trunks**: Trunk endpoints are reachable (if trunks are in scope)
5. **Feature entitlements**: Org has required features enabled (Call Queue, AA, etc.) for planned feature count
6. **Existing conflicts**: No collisions between planned extensions/numbers and existing Webex config
7. **Rate limit budget**: Estimate API calls needed, warn if migration will take >N hours at current rate limits

Each check produces PASS/WARN/FAIL. FAIL blocks execution. WARN proceeds with acknowledgment.

---

## PSTN Coexistence Strategy

Since number porting is out of scope, PSTN DIDs remain routed to CUCM during migration. Two supported coexistence patterns:

**Pattern A — CUCM forwards to Webex (recommended for phased migration):**
1. Create a SIP trunk from CUCM → Webex Calling
2. For each migrated user, set CFA (Call Forward All) on CUCM to route to their Webex extension via the trunk
3. Incoming PSTN → CUCM → CFA → Webex trunk → Webex user
4. After all users migrated, port numbers to Webex PSTN provider

**Pattern B — Webex trunk back to CUCM (recommended for single-cutover):**
1. Create Webex Calling trunk pointing to CUCM/gateway
2. Route patterns on Webex side send unrecognized DIDs back to CUCM
3. Migrated users get calls via Webex; non-migrated users still on CUCM

The migration config stores `coexistence_strategy: "cucm_forwards" | "webex_trunk_back"` and the executor sets up the appropriate forwarding rules in the relevant system.

---

## Execution & Rollback

### Execution
- **Executor**: Walks the topological order, calls `api.session.rest_post/put()` (same pattern as existing wxcli commands), records every action in an execution journal
- **Rate limiting**: Per-endpoint throttle with exponential backoff on 429 responses. Max 5 concurrent requests. Progress bar shows estimated time remaining. Configurable via `rate_limit_config` in migration settings.
- **Batch execution**: Site-by-site with user confirmation between batches

### Journal Entry Types
Each journal entry records the operation type, which determines rollback behavior:
```python
class JournalEntryType(str, Enum):
    CREATE = "create"       # New resource created → rollback = DELETE
    MODIFY = "modify"       # Existing resource updated → rollback = PUT pre_migration_state
    ASSIGN = "assign"       # License/feature assigned → rollback = un-assign via PUT
    CONFIGURE = "configure" # Settings changed → rollback = PUT pre_migration_state
```

Each entry records: entry_type, resource_type, resource_id, request (method + URL + payload), response, pre_migration_state (for MODIFY/ASSIGN/CONFIGURE).

### Snapshot Phase
Before execution begins, the snapshot phase captures current Webex state for any resource that will be modified:
- For users already in Webex: GET current person record, call settings, license assignments
- For locations that will be modified: GET current location config
- Stored in `snapshots/` directory, indexed by Webex resource ID
- Snapshot is required — execution will not proceed without it

### Rollback
Walks journal in reverse, applies type-appropriate reversal:
- `CREATE` → DELETE the created resource
- `MODIFY` → PUT the `pre_migration_state` to restore original config
- `ASSIGN` → PUT to un-assign license (remove from license array)
- `CONFIGURE` → PUT the `pre_migration_state` to restore original settings

If a rollback step fails, it's logged and the next step proceeds (best-effort). Final rollback report shows what was restored vs what needs manual attention.

### Dry-run
Prints planned API calls without executing. Shows: method, URL, payload summary, expected journal entry type.

---

## Validation & Reporting

Post-execution: read back every created Webex resource, compare key fields against canonical model, generate a markdown report following `docs/templates/execution-report.md` format with migration-specific sections (unmapped objects, decisions made, CSS decomposition warnings, calling permission mappings, phone model replacements needed, firmware conversion instructions).

---

## State Persistence
```
~/.wxcli/migrations/<project_id>/
  state.json              # State machine position + stats
  inventory.json          # Full MigrationInventory
  decisions.json          # Pending + resolved decisions
  execution_journal.json  # Step-by-step execution log (with entry types)
  batches/                # Per-batch execution plans
  reports/                # Generated reports
  snapshots/              # Webex state before migration (keyed by resource ID)
  config.json             # Migration config (country code, coexistence strategy, rate limits)
```

### New Dependencies
```toml
# Add to pyproject.toml
"zeep>=4.2.0",           # SOAP/WSDL client for AXL
"keyring>=24.0.0",       # Secure credential storage

[project.optional-dependencies]
migration = ["openpyxl>=3.1.0"]  # Excel export for inventory/decisions
```

---

## Agent & Skill Integration

**New agent** `cucm-migration-builder.md` — follows the `wxc-calling-builder.md` pattern:
1. Setup: verify wxcli auth + CUCM connectivity
2. Interview: cluster details, migration scope, phasing strategy, PSTN coexistence approach, default country code
3. Discovery: run `wxcli cucm discover`, present inventory
4. Analysis: run `wxcli cucm analyze`, present conflicts and decisions (including CSS decomposition and firmware conversion options)
5. Decision walkthrough: guide user through each pending decision
6. Planning: generate batch execution plan
7. Preflight: run `wxcli cucm preflight`, resolve any failures
8. Execution: run batches with user confirmation between each
9. Validation: verify and report

Delegates to existing skills (`provision-calling`, `configure-features`, `configure-routing`, `manage-call-settings`, `manage-devices`) for domain-specific execution.

**New skills**: `cucm-discovery` (AXL extraction guidance) and `cucm-migration` (execution flow guidance).

---

## Implementation Phases

| Phase | Deliverables | Depends On |
|---|---|---|
| 1. Foundation | `models.py`, `state.py`, `rate_limiter.py`, `connection.py`, `cucm.py` (connect/test/status) | — |
| 2. Discovery | All extractors (including shared_lines, workspaces), `discovery.py`, `cucm discover` + `cucm inventory` | Phase 1 |
| 3. Transform | All mappers (including css_mapper, voicemail_mapper, workspace_mapper, e164), `engine.py`, `rules.py`, `decisions.py`, `cucm analyze` + `cucm decisions` | Phase 2 |
| 4. Planning | `dependency.py`, `batch.py`, `cucm plan` + `cucm diff` | Phase 3 |
| 5. Preflight + Snapshot | `preflight.py`, `snapshot.py`, `cucm preflight` | Phase 4 |
| 6. Execution | `executor.py`, `rollback.py` (type-aware), `cucm execute` + `cucm rollback` | Phase 5 |
| 7. Validation | `comparator.py`, `report.py`, `cucm validate` + `cucm report` | Phase 6 |
| 8. Agent/Skills | `cucm-migration-builder.md`, skill files, reference docs | Phase 7 |
| 9. Polish | CSV/Excel export, bulk decision import, dry-run, `cucm-migration.md` + `cucm-axl-mapping.md` | Phase 8 |

---

## Testing Strategy

- **Unit tests** (no connectivity): model serialization, mapper logic (including E.164 normalization, CSS decomposition, firmware classification), dependency graph, conflict detection, phone model mapping, state machine transitions, rate limiter behavior
- **Integration tests** (mocked): mock AXL via recorded SOAP responses, mock Webex API via `responses` library, end-to-end pipeline tests, rollback type verification (CREATE→DELETE, MODIFY→PUT restore, ASSIGN→un-assign)
- **Live tests** (`@pytest.mark.cucm_live`): requires a CUCM 12.5+ lab environment. Options:
  - **Cisco dCloud**: reserve a CUCM collaboration lab (free with partner/customer account, 2-5 day sessions)
  - **CML (Cisco Modeling Labs)**: self-hosted, requires CML license
  - **Recorded fixtures**: for CI, use recorded AXL SOAP responses in `cucm/fixtures/` — live tests are manual/optional
  - Scope: discovery smoke test, small migration (2-3 users + hunt group + shared line), rollback verification, firmware model classification
```
tests/migration/
  test_models.py, test_state_machine.py
  cucm/test_connection.py, test_extractors.py, test_discovery.py
  cucm/fixtures/axl_responses/*.xml
  transform/test_engine.py, test_mappers.py, test_rules.py
  transform/test_css_decomposition.py, test_e164.py, test_firmware_compat.py
  execute/test_dependency_graph.py, test_executor.py, test_rollback.py, test_batch.py
  execute/test_preflight.py, test_snapshot.py, test_rate_limiter.py
  validate/test_comparator.py, test_report.py
```

---

## Critical Files to Modify

| File | Change |
|---|---|
| `src/wxcli/main.py` | Register cucm command group via `add_typer()` |
| `src/wxcli/auth.py` | Pattern to follow for CUCM auth (parallel `resolve_cucm_creds()`) |
| `src/wxcli/config.py` | Add `cucm_profiles` and `migration` sections to config schema |
| `pyproject.toml` | Add `zeep`, `keyring` dependencies |
| `CLAUDE.md` | Add migration section to file map |

---

## Verification

- `wxcli cucm test` connects to a CUCM 12.5+ cluster and returns version
- `wxcli cucm discover` extracts full inventory to `~/.wxcli/migrations/`
- `wxcli cucm analyze` identifies conflicts including CSS decomposition and firmware classification
- `wxcli cucm preflight` checks Webex org readiness and reports PASS/WARN/FAIL per check
- `wxcli cucm execute --dry-run` prints planned API calls with journal entry types
- `wxcli cucm execute --batch <site>` provisions objects, respects rate limits, records typed journal
- `wxcli cucm validate` reads back all created objects and confirms match
- `wxcli cucm rollback --batch <site>` applies type-appropriate reversal (DELETE/PUT-restore/un-assign)
