# E911/ECBN Execution — Design Spec

**Date:** 2026-04-10
**Status:** Draft
**Scope:** Move E911 from advisory-only to advisory + execution in the CUCM-to-Webex migration pipeline

---

## 1. Problem Statement

E911 is regulatory. After migration, every user MUST have a valid Emergency Callback Number (ECBN) and every location MUST have a validated emergency address. Failure to configure E911 correctly is a compliance violation of two federal laws:

- **Kari's Law** (U.S. Public Law 115-127): requires notification capability for ALL emergency calls from multi-line telephone systems.
- **RAY BAUM's Act** Section 506: requires dispatchable location information for ALL 911 calls, including from enterprise locations.

### Current State

The pipeline has advisory-only E911 support:

1. **E911 Extractor** (`src/wxcli/migration/cucm/extractors/e911.py`): Pulls ELIN groups and geographic locations from CUCM AXL via `listElinGroup`/`getElinGroup` and `listGeoLocation`/`getGeoLocation`.
2. **E911 Mapper** (`src/wxcli/migration/transform/mappers/e911_mapper.py`): Creates `CanonicalE911Config` objects and produces a single `ARCHITECTURE_ADVISORY` decision flagging E911 as a "separate workstream."
3. **Advisory Pattern 16** (`src/wxcli/migration/advisory/advisory_patterns.py:1066`): `detect_e911_migration_flag()` scans for E911 signals in partitions, route patterns, and translation patterns. Always fires (even on empty stores) because CER data may not be visible via AXL.
4. **Knowledge Base** (`docs/knowledge-base/migration/kb-location-design.md`): Documents E911 requirements per location, ECBN selection options, and cross-pattern interactions with location consolidation.

### What Is Missing

- **No execution handler.** The pipeline produces advisories but never calls any Webex E911 API.
- **No per-user ECBN configuration.** The Webex API at `PUT /telephony/config/people/{personId}/emergencyCallbackNumber` exists and is documented in `docs/reference/emergency-services.md`, but nothing in the pipeline calls it.
- **No location ECBN configuration.** `PUT /telephony/config/locations/{locationId}/features/emergencyCallbackNumber` exists but is uncalled.
- **No emergency call notification setup.** `PUT /telephony/config/emergencyCallNotification` is uncalled.
- **No E911 readiness preflight check.** The preflight system has 8 checks; none verify ECBN readiness.
- **No E911 section in the assessment report.**
- **No new decision types** for ambiguous ECBN scenarios (user with multiple numbers, user in one location with phone in another).

### The Gap

A customer completes migration, all users are provisioned, all features configured. Then someone dials 911 and the PSAP gets no callback number for an extension-only user. Or emergency call notifications are not enabled, violating Kari's Law. The migration tool declared E911 "out of scope" and moved on. This is the gap.

---

## 2. CUCM Source Data

### What Is Discoverable via AXL

The existing E911 extractor pulls:

| AXL Object | What It Contains | Pipeline Object |
|-------------|------------------|-----------------|
| `ElinGroup` | ELIN number pools (E.164 numbers reserved for E911 callback) | `CanonicalE911Config` with `elin_group_name`, `elin_numbers` |
| `GeoLocation` | Geographic locations with country/region (E911 routing) | `CanonicalE911Config` with `geo_location_name`, `geo_country` |
| Route patterns | Patterns matching `911`, `9.911`, `9911`, `.911` in E911 partitions | Detected by mapper, stored in `has_emergency_route_pattern` |
| Translation patterns | ELIN replacement patterns (E911/emergency/ELIN regex match) | Detected by advisory pattern 16 |
| Partitions | Partition names containing E911/emergency/ELIN | Detected by advisory pattern 16 |

### What Is NOT Discoverable via AXL

Cisco Emergency Responder (CER) has its own database. The following require CER API access or manual export:

| CER Object | What It Contains | Why It Matters |
|------------|------------------|----------------|
| ERL (Emergency Response Location) | Physical address mapped to a switch port or IP subnet | Maps to Webex emergency address per location/per-number |
| ERL-to-ELIN mapping | Which ELIN pool serves which ERL | Determines per-number ECBN source |
| Phone-to-ERL tracking | Real-time phone location by CDP/LLDP switch port | Nomadic E911 — maps to RedSky building/floor association |
| PSAP routing rules | How CER routes 911 based on ERL | No direct Webex equivalent; Webex uses civic address → PSAP routing |
| ERL zones/floors | Sub-location granularity (building, floor, zone) | Maps to per-number emergency address overrides in Webex |

**Key insight:** The CUCM AXL extraction gives us enough to know E911 WAS configured and what ELIN numbers were used. It does NOT give us the physical address mappings. Those come from CER or from the customer directly.

### New Extraction Enhancement (Phase 1)

Add to the E911 extractor: per-user number inventory cross-reference. The extractor already has ELIN groups. The normalizer already builds `CanonicalUser` with `phone_numbers` (DIDs) and `extension`. What is missing is the mapper connecting these: "for each user, what is their best ECBN candidate?"

This requires no new AXL queries — just cross-referencing existing normalized data.

---

## 3. Webex Target APIs

### 3.1 Per-Person ECBN

```
GET  /telephony/config/people/{personId}/emergencyCallbackNumber
PUT  /telephony/config/people/{personId}/emergencyCallbackNumber
```

**Body (PUT):**
```json
{
  "selected": "DIRECT_LINE"
}
```

Or for extension-only users:
```json
{
  "selected": "LOCATION_ECBN"
}
```

Or for multi-floor/member scenarios:
```json
{
  "selected": "LOCATION_MEMBER_NUMBER",
  "locationMemberId": "<webex_person_id>"
}
```

**Selection options:** `DIRECT_LINE` | `LOCATION_ECBN` | `LOCATION_MEMBER_NUMBER` | `NONE`

**Scopes:** `spark-admin:telephony_config_read` (GET), `spark-admin:telephony_config_write` (PUT)

### 3.2 Per-Workspace ECBN

```
GET  /telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber
PUT  /telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber
```

Same body schema as person ECBN.

### 3.3 Per-Virtual-Line ECBN

```
GET  /telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber
PUT  /telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber
```

Same body schema as person ECBN.

### 3.4 Location ECBN

```
GET  /telephony/config/locations/{locationId}/features/emergencyCallbackNumber
PUT  /telephony/config/locations/{locationId}/features/emergencyCallbackNumber
```

**Body (PUT):**
```json
{
  "selected": "LOCATION_MEMBER_NUMBER",
  "locationMemberId": "<webex_person_id>"
}
```

Sets the location-level default ECBN. Extension-only users at this location who use `LOCATION_ECBN` will inherit this number.

### 3.5 Emergency Call Notifications

```
GET  /telephony/config/emergencyCallNotification
PUT  /telephony/config/emergencyCallNotification
```

**Body (PUT):**
```json
{
  "emergencyCallNotificationEnabled": true,
  "allowEmailNotificationAllLocationEnabled": true,
  "emailAddress": "security@company.com"
}
```

### 3.6 ECBN Available Numbers

```
GET  /telephony/config/people/{personId}/emergencyCallbackNumber/availableNumbers
GET  /telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber/availableNumbers
GET  /telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber/availableNumbers
GET  /telephony/config/locations/{locationId}/emergencyCallbackNumber/availableNumbers
```

Lists valid ECBN candidates. Useful for the handler to verify a number is eligible before attempting to set it.

### 3.7 ECBN Dependencies

```
GET  /telephony/config/people/{personId}/emergencyCallbackNumber/dependencies
GET  /telephony/config/workspaces/{workspaceId}/emergencyCallbackNumber/dependencies
GET  /telephony/config/virtualLines/{virtualLineId}/emergencyCallbackNumber/dependencies
GET  /telephony/config/huntGroups/{huntGroupId}/emergencyCallbackNumber/dependencies
```

Check before changing any ECBN to avoid breaking other entities' callbacks.

### 3.8 RedSky Integration (Phase 2 Only)

| Endpoint | Purpose |
|----------|---------|
| `POST /telephony/config/redSky` | Create RedSky account |
| `PUT /telephony/config/redSky/serviceSettings` | Enable RedSky service |
| `POST /telephony/config/locations/{id}/redSky/building` | Create building address |
| `PUT /telephony/config/locations/{id}/redSky/building` | Update building address |
| `GET /telephony/config/locations/{id}/redSky` | Get location RedSky params |
| `GET/PUT /telephony/config/locations/{id}/redSky/status` | Location compliance status |
| `GET /telephony/config/redSky/complianceStatus` | Org-wide compliance report |

RedSky requires a separate account setup outside the pipeline. Phase 2 only.

---

## 4. Phase 1 — ECBN Execution

Phase 1 covers the straightforward cases that can be automated without CER data or RedSky setup.

### 4.1 Enhanced E911 Mapper Output

The E911 mapper currently produces only `CanonicalE911Config` objects (advisory-only). Enhance it to also produce per-user ECBN mapping data by cross-referencing existing normalized objects.

**New mapper: `EcbnMapper`** (separate from the existing `E911Mapper` to maintain single-responsibility):

- **Name:** `ecbn_mapper`
- **Depends on:** `user_mapper`, `workspace_mapper`, `location_mapper`, `line_mapper`
- **Reads:** `CanonicalUser`, `CanonicalWorkspace`, `CanonicalLine`, cross-refs (`user_has_line`, `user_in_location`)
- **Produces:** `CanonicalEcbnConfig` objects (one per user and one per workspace)

**ECBN classification logic per user:**

1. **User has exactly one DID** (E.164 number on their primary line): ECBN = `DIRECT_LINE`. This is the common case and can be auto-configured.
2. **User has multiple DIDs** (multiple lines with E.164 numbers): ECBN candidate is ambiguous. Produce `E911_ECBN_AMBIGUOUS` decision.
3. **User has no DID** (extension-only): ECBN = `LOCATION_ECBN`. Auto-configure if the location has a valid ECBN set.
4. **User's location has no ECBN configured and user has no DID**: Flag as `E911_ECBN_MISSING` (preflight will also catch this).

**Per workspace:** Same logic but simpler — workspaces typically have one number or none.

### 4.2 New Canonical Model

Add to `models.py`:

```python
class CanonicalEcbnConfig(MigrationObject):
    """Per-entity ECBN configuration for Webex."""
    entity_type: str = ""           # "user", "workspace", "virtual_line"
    entity_canonical_id: str = ""   # canonical_id of the user/workspace/VL
    location_canonical_id: str | None = None
    ecbn_selection: str = ""        # "DIRECT_LINE", "LOCATION_ECBN", "LOCATION_MEMBER_NUMBER"
    did_numbers: list[str] = Field(default_factory=list)  # All DIDs on this entity
    primary_did: str | None = None  # Best candidate DID for ECBN
    needs_location_ecbn: bool = False  # True if extension-only, location ECBN must exist
```

Register in `CANONICAL_TYPE_MAP`: `"ecbn_config": CanonicalEcbnConfig`

### 4.3 New Decision Types

Add to `DecisionType` enum in `models.py`:

```python
E911_ECBN_AMBIGUOUS = "E911_ECBN_AMBIGUOUS"
E911_LOCATION_MISMATCH = "E911_LOCATION_MISMATCH"
```

**`E911_ECBN_AMBIGUOUS`:** User has multiple DIDs — which one should be the ECBN? Options:
- One option per DID number (e.g., `did_+15551234567`, `did_+15559876543`)
- `location_ecbn` — use the location's ECBN instead

**`E911_LOCATION_MISMATCH`:** User is assigned to location A but their phone is physically at location B (detected via device pool cross-ref mismatch). The ECBN must match the user's physical location for accurate PSAP dispatch. Options:
- `use_user_location` — use the user's assigned location ECBN
- `use_device_location` — use the phone's physical location ECBN
- `manual` — operator must verify the correct physical location

### 4.4 Execution Handler

New handler in `handlers.py`:

```python
def handle_ecbn_config_configure(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    """Configure ECBN for a user, workspace, or virtual line."""
```

**Logic:**
1. Resolve entity Webex ID from `deps` using `entity_canonical_id`.
2. Determine entity type (`people`, `workspaces`, `virtualLines`) from `entity_type`.
3. Build PUT body based on `ecbn_selection`:
   - `DIRECT_LINE`: `{"selected": "DIRECT_LINE"}`
   - `LOCATION_ECBN`: `{"selected": "LOCATION_ECBN"}`
   - `LOCATION_MEMBER_NUMBER`: `{"selected": "LOCATION_MEMBER_NUMBER", "locationMemberId": "<resolved_id>"}`
4. Return `[("PUT", url, body)]`.
5. Return `[]` if entity Webex ID not resolved (dep not yet completed).

**Registration:**
- `HANDLER_REGISTRY[("ecbn_config", "configure")] = handle_ecbn_config_configure`
- `TIER_ASSIGNMENTS[("ecbn_config", "configure")] = 5` (same tier as other settings — depends on user/workspace existing)
- `API_CALL_ESTIMATES["ecbn_config:configure"] = 1`

### 4.5 Planner Expander

New expander in `planner.py`:

```python
def _expand_ecbn_config(obj: dict[str, Any]) -> list[MigrationOp]:
    cid = obj["canonical_id"]
    entity_cid = obj.get("entity_canonical_id", "")
    entity_create_node = _node_id(entity_cid, "create")

    return [_op(
        canonical_id=cid,
        op_type="configure",
        resource_type="ecbn_config",
        description=f"Configure ECBN for {entity_cid}",
        depends_on=[entity_create_node],
    )]
```

Register in `_EXPANDERS`: `"ecbn_config": lambda obj, _: _expand_ecbn_config(obj)`

### 4.6 Dependency Rules

In `dependency.py`, add cross-object rules:
- `ecbn_config:configure` REQUIRES `user:create` (for person ECBN)
- `ecbn_config:configure` REQUIRES `workspace:create` (for workspace ECBN)
- `ecbn_config:configure` REQUIRES `location:enable_calling` (location must be active)

### 4.7 Emergency Call Notification (Org-Level)

This is a one-shot org-level configuration, not per-entity. Handle it outside the DAG:

- Add a **post-migration step** in the cucm-migrate skill: after all batches complete, prompt the operator for a notification email address and call `PUT /telephony/config/emergencyCallNotification`.
- This is not a DAG operation because it has no dependencies on individual objects and should only run once per migration.
- If the operator declines, log a warning: "Emergency call notifications not configured. Kari's Law compliance requires manual setup."

---

## 5. Phase 2 — RedSky Integration

Phase 2 covers nomadic E911 for users who move between locations. This requires a RedSky account, which is set up outside the pipeline.

### 5.1 Prerequisites (External to Pipeline)

1. Customer must have a RedSky/Intrado account.
2. RedSky service must be enabled in the Webex org via `PUT /telephony/config/redSky/serviceSettings`.
3. RedSky building addresses must be created per location via `POST /telephony/config/locations/{id}/redSky/building`.

These are NOT automated by the pipeline. The pipeline can verify they exist (preflight) and report their absence, but creating RedSky accounts is an out-of-band process.

### 5.2 Pipeline Support for RedSky

Add to the **preflight system** (not execution):

- **RedSky readiness check:** If the migration config has `e911.redsky_enabled: true`, verify:
  - RedSky account exists (`GET /telephony/config/redSky` returns 200)
  - RedSky service is enabled (`GET /telephony/config/redSky/serviceSettings` → `enabled: true`)
  - Each location has a building address (`GET /telephony/config/locations/{id}/redSky` returns building data)
- Report missing building addresses as warnings, not blockers. The migration can proceed without RedSky — it just means nomadic E911 is not yet configured.

### 5.3 Advisory Enhancement

Update Pattern 16 (`detect_e911_migration_flag`) to include a Phase 2 recommendation when E911 signals are detected:

> "Phase 1 (ECBN) can be automated during migration. Phase 2 (RedSky building/floor association) requires RedSky account setup and building address configuration outside the pipeline. Initiate RedSky setup in parallel with migration."

---

## 6. Pipeline Integration

### 6.1 Mapper Registration

Add `EcbnMapper` to the mapper registry in `transform/engine.py`. It runs after `user_mapper`, `workspace_mapper`, and `location_mapper` (Tier 3 in the mapper execution order).

### 6.2 Analyzer Enhancement

No new analyzer needed. The `EcbnMapper` itself produces `E911_ECBN_AMBIGUOUS` and `E911_LOCATION_MISMATCH` decisions during mapping (same pattern as existing mappers that produce decisions).

### 6.3 Auto-Rules

Add auto-resolution rules in `transform/rules.py`:

- **Single-DID users:** If user has exactly one DID, auto-resolve ECBN as `DIRECT_LINE`. No decision needed (this is the default and correct in >90% of cases).
- **Extension-only users:** Auto-resolve ECBN as `LOCATION_ECBN`. No decision needed if the location has a valid ECBN configured.

These are not decisions — the mapper simply sets `ecbn_selection` directly for clear cases. Decisions are only produced for genuinely ambiguous cases.

### 6.4 Recommendation Rules

Add to `recommendation_rules.py`:

```python
def recommend_e911_ecbn_ambiguous(context: dict, options: list[dict]) -> tuple[str, str] | None:
    """Recommend the primary line's DID as ECBN when user has multiple DIDs."""
    primary_did = context.get("primary_did")
    if primary_did:
        option_id = f"did_{primary_did}"
        for opt in options:
            if opt.get("id") == option_id:
                return (option_id, f"Primary line DID {primary_did} is the most common ECBN choice. "
                        f"The PSAP will call back this number if the emergency call is disconnected.")
    return None
```

Register in `RECOMMENDATION_DISPATCH`:
- `"E911_ECBN_AMBIGUOUS": recommend_e911_ecbn_ambiguous`
- `"E911_LOCATION_MISMATCH": recommend_e911_location_mismatch`

### 6.5 Advisory Pattern Update

Modify Pattern 16 to include quantified output:

- Count of users with auto-ECBN (single DID or extension-only): "X users will have ECBN auto-configured"
- Count of ambiguous ECBN decisions: "Y users need ECBN decision (multiple DIDs)"
- Count of location mismatch decisions: "Z users have location mismatch — verify physical location"

This replaces the current generic "E911 requires separate workstream" with actionable specifics.

---

## 7. Preflight Check

### 7.1 E911 Readiness Check

Add as the 9th preflight check in `src/wxcli/migration/preflight/checks.py`:

**Check name:** `e911_readiness`

**What it verifies:**

1. **Every user has an ECBN candidate.** For each `CanonicalUser` with `status='analyzed'`:
   - If user has a DID: ECBN candidate = `DIRECT_LINE` (pass)
   - If user has no DID and location has a main number: ECBN candidate = `LOCATION_ECBN` (pass with info)
   - If user has no DID and location has no main number: FAIL — "User {name} at location {loc} has no ECBN candidate. Configure a location ECBN or assign a DID."
2. **Every workspace has an ECBN candidate.** Same logic as users.
3. **No unresolved E911 decisions.** Check that all `E911_ECBN_AMBIGUOUS` and `E911_LOCATION_MISMATCH` decisions are resolved.

**Severity levels:**
- Missing ECBN candidate: `ERROR` (blocks execution)
- Unresolved E911 decision: `ERROR` (blocks execution)
- Extension-only user relying on location ECBN: `WARNING` (proceeds but logged)
- RedSky not configured (when e911.redsky_enabled): `WARNING`

### 7.2 Registration

Add to `PREFLIGHT_CHECKS` list in `checks.py`. The check reads from the store — no API calls needed at preflight time.

---

## 8. Report Changes

### 8.1 Assessment Report E911 Section

Add an "E911 Readiness" section to the assessment report (`src/wxcli/migration/report/`).

**Content:**

| Metric | Source |
|--------|--------|
| Users with DID (auto-ECBN) | Count of `CanonicalUser` with `phone_numbers` containing E.164 |
| Extension-only users (need location ECBN) | Count of `CanonicalUser` without E.164 numbers |
| Ambiguous ECBN (multi-DID) | Count of `E911_ECBN_AMBIGUOUS` decisions |
| Location mismatch | Count of `E911_LOCATION_MISMATCH` decisions |
| ELIN groups in CUCM | Count from `CanonicalE911Config` |
| E911 route patterns detected | Boolean from existing mapper |
| Locations needing emergency addresses | All locations (Webex requires validated address per location) |

**Placement:** After the "Decision Summary" section, before the "Technical Reference" appendix. E911 is regulatory — it deserves prominent visibility.

**Visual:** A simple readiness table with green/yellow/red status indicators:
- Green: All users have ECBN candidates, no ambiguous decisions
- Yellow: Some extension-only users (location ECBN needed), or some ambiguous decisions
- Red: Users with no ECBN candidate at all

---

## 9. Documentation Updates Required

### Files to Create

| File | Purpose |
|------|---------|
| `src/wxcli/migration/transform/mappers/ecbn_mapper.py` | New ECBN mapper |

### Files to Modify

| File | Change |
|------|--------|
| `src/wxcli/migration/models.py` | Add `CanonicalEcbnConfig`, `E911_ECBN_AMBIGUOUS`, `E911_LOCATION_MISMATCH` to `DecisionType` |
| `src/wxcli/migration/transform/engine.py` | Register `EcbnMapper` |
| `src/wxcli/migration/execute/handlers.py` | Add `handle_ecbn_config_configure` |
| `src/wxcli/migration/execute/planner.py` | Add `_expand_ecbn_config`, register in `_EXPANDERS` |
| `src/wxcli/migration/execute/__init__.py` | Add tier assignment + API call estimate for `ecbn_config:configure` |
| `src/wxcli/migration/execute/dependency.py` | Add cross-object rules for `ecbn_config` |
| `src/wxcli/migration/preflight/checks.py` | Add `e911_readiness` check |
| `src/wxcli/migration/advisory/recommendation_rules.py` | Add `recommend_e911_ecbn_ambiguous`, `recommend_e911_location_mismatch` |
| `src/wxcli/migration/advisory/advisory_patterns.py` | Update Pattern 16 with quantified output |
| `src/wxcli/migration/report/` | Add E911 readiness section to assessment report |
| `src/wxcli/migration/CLAUDE.md` | Update file map with new mapper, decision types |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Add EcbnMapper to inventory |
| `src/wxcli/migration/execute/CLAUDE.md` | Add handler, tier, dependency documentation |
| `src/wxcli/migration/advisory/CLAUDE.md` | Update recommendation rule count and pattern 16 description |
| `src/wxcli/migration/preflight/CLAUDE.md` | Add 9th check documentation |
| `docs/knowledge-base/migration/kb-location-design.md` | Add ECBN execution guidance (currently advisory-only) |
| `docs/runbooks/cucm-migration/decision-guide.md` | Add entries for `E911_ECBN_AMBIGUOUS` and `E911_LOCATION_MISMATCH` |
| `CLAUDE.md` (root) | Update DecisionType count (21 -> 23), preflight check count (8 -> 9) |
| `.claude/skills/cucm-migrate/SKILL.md` | Add E911 notification post-migration step |

---

## 10. Test Strategy

### 10.1 Unit Tests — ECBN Mapper

| Test | What It Verifies |
|------|------------------|
| `test_user_single_did_direct_line` | User with one DID → `ecbn_selection="DIRECT_LINE"` |
| `test_user_multiple_dids_ambiguous` | User with 2+ DIDs → `E911_ECBN_AMBIGUOUS` decision |
| `test_user_no_did_location_ecbn` | Extension-only user → `ecbn_selection="LOCATION_ECBN"` |
| `test_workspace_with_did` | Workspace with DID → `ecbn_selection="DIRECT_LINE"` |
| `test_workspace_no_did` | Workspace without DID → `ecbn_selection="LOCATION_ECBN"` |
| `test_location_mismatch_detection` | User location differs from device pool location → `E911_LOCATION_MISMATCH` decision |
| `test_no_users_no_output` | Empty store → no ECBN configs produced |
| `test_skipped_users_excluded` | Users with skip decisions are not processed |

### 10.2 Unit Tests — Handler

| Test | What It Verifies |
|------|------------------|
| `test_handle_ecbn_direct_line` | Produces correct PUT body for `DIRECT_LINE` |
| `test_handle_ecbn_location_ecbn` | Produces correct PUT body for `LOCATION_ECBN` |
| `test_handle_ecbn_location_member` | Produces correct PUT body with `locationMemberId` |
| `test_handle_ecbn_workspace` | Uses `/workspaces/` URL path |
| `test_handle_ecbn_virtual_line` | Uses `/virtualLines/` URL path |
| `test_handle_ecbn_no_deps` | Returns `[]` when entity not yet created |

### 10.3 Unit Tests — Planner

| Test | What It Verifies |
|------|------------------|
| `test_expand_ecbn_config` | Produces `configure` op with correct depends_on |
| `test_expand_ecbn_in_full_plan` | ECBN ops appear at tier 5, after user/workspace create |

### 10.4 Unit Tests — Preflight

| Test | What It Verifies |
|------|------------------|
| `test_e911_readiness_all_users_have_did` | All users with DID → pass |
| `test_e911_readiness_extension_only_with_location` | Extension-only user at location with main number → warning |
| `test_e911_readiness_extension_only_no_location_number` | Extension-only user, location has no number → error |
| `test_e911_readiness_unresolved_decisions` | Unresolved E911 decisions → error |

### 10.5 Unit Tests — Recommendation Rules

| Test | What It Verifies |
|------|------------------|
| `test_recommend_ecbn_ambiguous_primary_did` | Recommends primary line DID |
| `test_recommend_ecbn_ambiguous_no_primary` | Returns None when no clear primary |
| `test_recommend_location_mismatch` | Recommends based on device count at each location |

### 10.6 Integration Test

One end-to-end test that runs the full pipeline (normalize → map → analyze → plan) on a fixture with:
- 3 users with single DID (auto-ECBN)
- 1 user with multiple DIDs (ambiguous decision)
- 1 extension-only user (location ECBN)
- 1 workspace with DID
- 1 workspace without DID

Verify: correct ECBN configs produced, correct decisions generated, planner produces correct ops at tier 5, preflight passes for auto-cases and flags the ambiguous one.

**Estimated test count:** ~25 tests across 5 test files.

---

## 11. Migration Config

Add E911 configuration to the migration config (`wxcli cucm config`):

```yaml
e911:
  auto_configure_ecbn: true          # Auto-set ECBN for clear cases (single DID / extension-only)
  notification_email: null            # Email for emergency call notifications (prompted post-migration)
  redsky_enabled: false               # Whether to check RedSky readiness in preflight
  primary_did_strategy: "first_line"  # How to pick primary DID: "first_line" or "lowest_number"
```

When `auto_configure_ecbn: false`, the mapper still produces `CanonicalEcbnConfig` objects but they are all `status='needs_decision'` — the operator must explicitly approve each ECBN assignment. Default is `true` because single-DID and extension-only cases are unambiguous.

---

## 12. Scope Boundaries

### In Scope (This Spec)

- Per-user/workspace ECBN auto-configuration for clear cases
- New decision types for ambiguous cases
- Execution handler calling Webex ECBN API
- Preflight E911 readiness check
- Assessment report E911 section
- Emergency call notification prompt (post-migration)
- Recommendation rules for E911 decisions
- Enhanced advisory pattern 16

### Out of Scope (Separate Work)

- CER data extraction (requires CER API client, not AXL)
- Emergency address validation and creation (requires customer-provided physical addresses)
- RedSky account creation and building address configuration (external process)
- Per-number emergency address overrides (requires CER ERL-to-address mapping)
- PSAP routing verification (no programmatic way to verify)
- cucm-collect standalone script integration (see MEMORY.md priorities)

### Phase Boundary

- **Phase 1 (this spec):** ECBN execution, decisions, preflight, report. Can be built and tested without any external dependencies.
- **Phase 2 (future):** RedSky integration, building/floor association. Requires RedSky account and is additive to Phase 1.
- **Phase 3 (future):** CER extraction, ERL-to-address mapping. Requires CER API access and customer address data.

---

## 13. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| ECBN API rejects `DIRECT_LINE` for users whose DID is not yet active | MEDIUM | Handler must run after user create + number assignment. Tier 5 ordering handles this. |
| Location has no main number, extension-only users cannot get ECBN | HIGH | Preflight check catches this. Operator must add a number to the location before migration. |
| Multi-DID users get wrong ECBN auto-picked | LOW | These produce decisions — operator must choose. Never auto-pick for ambiguous cases. |
| CER data missing entirely, no E911 signals in AXL | MEDIUM | Pattern 16 already fires a "verify with CUCM admin" warning. Enhanced pattern will quantify ECBN readiness regardless. |
| Emergency call notification email address not provided | LOW | Post-migration prompt. Warning logged if declined. Not a blocker. |

---

## 14. Success Criteria

1. Every user with a single DID has ECBN auto-configured as `DIRECT_LINE` after migration execution.
2. Every extension-only user has ECBN set to `LOCATION_ECBN` after migration execution.
3. Multi-DID users produce `E911_ECBN_AMBIGUOUS` decisions with one option per DID.
4. Location mismatch scenarios produce `E911_LOCATION_MISMATCH` decisions.
5. Preflight blocks execution if any user has no ECBN candidate.
6. Assessment report shows E911 readiness breakdown.
7. Emergency call notifications are prompted post-migration.
8. All existing tests continue to pass (no regressions).
9. ~25 new tests covering mapper, handler, planner, preflight, and recommendation rules.
