# CUCM→Webex Migration Pipeline — Mapper Build Sessions

Part 3 of 3 in the build planning sequence. Breaks the 9 mappers + engine.py into executable build sessions with self-contained prompts.

**Inputs:** [`cucm-build-strategy.md`](cucm-build-strategy.md) (Part 1: build order), [`cucm-build-contracts.md`](cucm-build-contracts.md) (Part 2: interface contracts, acceptance criteria), [`cucm-pipeline/03b-transform-mappers.md`](cucm-pipeline/03b-transform-mappers.md) (field-level mapper specs).

---

## 1. Mapper Session Breakdown

### Session Summary Table

| Session | Mappers | Why Grouped | Est. Lines | Reference Docs | Prerequisites |
|---------|---------|-------------|-----------|----------------|---------------|
| **D1: Foundational** | `location_mapper`, `user_mapper`, `line_mapper` + **Mapper base class** + `pattern_converter` | Everything references locations and users. Line mapper depends on location for E.164 country code. Mapper protocol must exist before all other sessions. Pattern converter is shared by D2 and D3a. | ~600 | `provisioning.md`, `location-call-settings-core.md`, `person-call-settings-behavior.md`, `virtual-lines.md` | Phase 1 (models, store), Phase 2 (location normalizer, CrossRefBuilder scaffold), Phase 3 Spike 3 (e164.py) |
| **D2: Infrastructure** | `device_mapper`, `workspace_mapper`, `routing_mapper` | Device and workspace share the three-tier compatibility table. Routing is independent but similar complexity. All depend on D1's location output. | ~580 | `devices-core.md`, `devices-workspaces.md`, `call-routing.md`, `person-call-settings-permissions.md` | D1 (Mapper base class, location_mapper output for `device_pool_to_location` cross-ref) |
| **D3a: CSS Decomposition** | `css_mapper` + **`cucm_pattern.py`** (explicit deliverable with test suite) | Hardest mapper — implements the full CSS decomposition algorithm from 04-css-decomposition.md. Gets its own session to avoid quality degradation. `cucm_pattern.py` is built here as a dependency. | ~550 | `call-routing.md`, `person-call-settings-permissions.md` | D1 (Mapper base class), D2 (routing_mapper output for dial plan targets) |
| **D3b: Features + Voicemail** | `feature_mapper`, `voicemail_mapper` | Both depend on users/locations but not on css_mapper. Feature mapper is the second hardest (3-object classification). Voicemail is lower complexity but needs careful gap analysis. | ~500 | `call-features-major.md`, `call-features-additional.md`, `person-call-settings-media.md` | D1 (Mapper base class, user_mapper output) |
| **D4: Engine + Integration** | `engine.py` (completion), `rules.py`, `decisions.py`, full integration test | Engine orchestrates all 9 mappers — needs them all to exist first. Integration test validates cross-mapper consistency. | ~500 | None (reads mapper code from D1-D3b) | D1, D2, D3a, D3b (all mappers must exist) |

### Parallelism

```
D1 (foundational) ─────────┐
                            ├──→ D2 (infrastructure) ──→ D3a (CSS)
                            │                              │
                            ├──→ D3b (features+VM) ────────┤
                            │                              │
                            └──────────────────────────────┴──→ D4 (engine + integration)
```

- **D2 and D3b can run in parallel** after D1 completes (they don't depend on each other)
- **D3a requires D2** (css_mapper uses routing_mapper output for dial plan targets)
- **D4 requires all others** (engine orchestrates all 9 mappers)

### Per-Mapper Line Estimates

| Mapper | Production Lines | Test Lines | Total | Session |
|--------|-----------------|------------|-------|---------|
| Mapper base class + helpers | ~80 | ~30 | ~110 | D1 |
| `location_mapper` | ~120 | ~80 | ~200 | D1 |
| `user_mapper` | ~100 | ~80 | ~180 | D1 |
| `line_mapper` | ~90 | ~70 | ~160 | D1 |
| `pattern_converter` | ~40 | ~40 | ~80 | D1 |
| `device_mapper` | ~110 | ~80 | ~190 | D2 |
| `workspace_mapper` | ~100 | ~80 | ~180 | D2 |
| `routing_mapper` | ~130 | ~80 | ~210 | D2 |
| `cucm_pattern.py` | ~120 | ~100 | ~220 | D3a |
| `css_mapper` | ~200 | ~120 | ~320 | D3a |
| `feature_mapper` | ~180 | ~120 | ~300 | D3b |
| `voicemail_mapper` | ~100 | ~80 | ~180 | D3b |
| `engine.py` + `rules.py` + `decisions.py` | ~200 | ~150 | ~350 | D4 |
| Integration test | — | ~150 | ~150 | D4 |
| **Total** | **~1,570** | **~1,260** | **~2,830** | |

---

## 2. Per-Session Execution Prompts

---

### Session D1: Foundational Mappers (location, user, line) + Mapper Base Class

#### Read these files

**Design docs (read thoroughly):**
- `docs/plans/cucm-pipeline/03b-transform-mappers.md` §1 (location_mapper), §2 (user_mapper), §3 (line_mapper), §13 (Shared Patterns — Mapper base class, MapperResult, canonical ID convention, decision option builders, MigrationStore query helpers, unit test pattern)
- `docs/plans/cucm-pipeline/02-normalization-architecture.md` — Cross-Reference Manifest rows 1-6 (device_pool_has_datetime_group, device_pool_at_cucm_location, user_has_device, user_has_primary_dn, device_has_dn, dn_in_partition)
- `docs/plans/cucm-pipeline/03-conflict-detection-engine.md` — §Decision Ownership design note: mappers produce per-object decisions, analyzers produce cross-object decisions. Analyzers check the decisions table before creating duplicates.

**Prerequisite code (read to understand interfaces):**
- `src/wxcli/migration/models.py` — canonical Pydantic types (CanonicalLocation, CanonicalUser, CanonicalLine, MigrationObject base, Decision, DecisionOption, DecisionType, MapperResult, Provenance, MigrationStatus)
- `src/wxcli/migration/store.py` — MigrationStore API (upsert_object, query_by_type, get_object, add_cross_ref, find_cross_refs, get_cross_ref_targets, resolve_chain, save_decision, next_decision_id, current_run_id)
- `src/wxcli/migration/transform/e164.py` — E164Result, normalize_dn() (already built in Phase 3 Spike 3)

**Webex API reference (for verifying field names):**
- `docs/reference/provisioning.md` — Webex Locations API fields (address, timeZone, routingPrefix, outsideDialDigit), People API fields (emails, firstName, lastName, displayName, locationId, extension, phoneNumbers, callingData, department, title, manager, licenses)
- `docs/reference/location-call-settings-core.md` — Location enablement fields (announcementLanguage must be lowercase, calling-enabled PUT endpoint)
- `docs/reference/person-call-settings-behavior.md` — Calling behavior, numbers (extension vs work_extension routing prefix asymmetry)
- `docs/reference/virtual-lines.md` — Virtual line extension/number assignment (for shared line tagging context)

#### Produce these files

**Production code:**
- `src/wxcli/migration/transform/mappers/__init__.py` — package init, exports Mapper base class
- `src/wxcli/migration/transform/mappers/base.py` — Mapper ABC, MapperResult import, `_create_decision()` helper, `_fingerprint()` helper, decision option builders (`skip_option`, `manual_option`, `accept_option`)
- `src/wxcli/migration/transform/mappers/location_mapper.py`
- `src/wxcli/migration/transform/mappers/user_mapper.py`
- `src/wxcli/migration/transform/mappers/line_mapper.py`
- `src/wxcli/migration/transform/pattern_converter.py` — `cucm_to_webex_pattern()` shared between routing_mapper (D2) and css_mapper (D3a)

**Test code:**
- `tests/migration/transform/test_location_mapper.py`
- `tests/migration/transform/test_user_mapper.py`
- `tests/migration/transform/test_line_mapper.py`
- `tests/migration/transform/test_pattern_converter.py`

#### Mapper base class — define here (all subsequent sessions implement it)

```python
from abc import ABC, abstractmethod
from migration.models import MapperResult, Decision, DecisionOption, DecisionType, MigrationStore
import hashlib, json

class Mapper(ABC):
    """Base class for all transform mappers."""
    name: str
    depends_on: list[str] = []  # Names of mappers that must run before this one

    @abstractmethod
    def map(self, store: MigrationStore) -> MapperResult:
        """Read CUCM canonical objects, produce Webex canonical objects + decisions."""
        ...

    def _create_decision(
        self, store, decision_type, severity, summary, context, options, affected_objects
    ) -> Decision:
        """Helper to create a well-formed Decision with auto-generated ID and fingerprint."""
        return Decision(
            decision_id=store.next_decision_id(),
            type=decision_type, severity=severity, summary=summary,
            context=context, options=options, affected_objects=affected_objects,
            fingerprint=self._fingerprint(decision_type, context),
            run_id=store.current_run_id,
        )

    def _fingerprint(self, decision_type, context) -> str:
        key_data = json.dumps({"type": decision_type.value, **context}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

def skip_option(impact="Object not migrated") -> DecisionOption:
    return DecisionOption(id="skip", label="Skip", impact=impact)

def manual_option(impact="Requires manual configuration post-migration") -> DecisionOption:
    return DecisionOption(id="manual", label="Manual", impact=impact)

def accept_option(impact: str) -> DecisionOption:
    return DecisionOption(id="accept", label="Accept fidelity loss", impact=impact)
```

Source: `03b-transform-mappers.md` §13 Shared Patterns.

#### For each mapper, use checklist-before-writing

Before writing each mapper:
1. List every field mapping from 03b's field mapping table for that mapper
2. List every cross-ref read (from the Cross-Reference Dependencies table)
3. List every decision the mapper owns (from the Decisions Generated table + §13 Decision Ownership Table)
4. List every edge case from the Edge Cases section
5. Write the mapper
6. Verify against your checklist — every item accounted for

#### Acceptance criteria

**location_mapper:**
- Given a DevicePool with cross-refs to DateTimeGroup (timezone="America/New_York") and CUCM Location entity (address fields populated), produces `CanonicalLocation` with `timeZone="America/New_York"`, `address.city` populated, `announcementLanguage="en_us"` (lowercase), `calling_enabled=True`. Source: 03b §1 field mapping table.
- Given 2 device pools ("HQ-Phones", "HQ-Softphones") both referencing the same CUCM Location entity, produces exactly 1 `CanonicalLocation` (consolidated), not 2. Source: 03b §1 Edge Cases "Device pool consolidation".
- Given a device pool with no `device_pool_at_cucm_location` cross-ref, produces `LOCATION_AMBIGUOUS` decision with severity="HIGH" and options including "Create new location" and "Skip". Source: 03b §1 Decisions Generated.
- After mapping, writes `device_pool_to_location` cross-ref from each source DevicePool to the new location's canonical_id. Source: 02-normalization-architecture.md note.
- Location name truncated to 80 chars with warning if CUCM name was longer. Source: 03b §1 Edge Cases.

**user_mapper:**
- Given user with `mailid="jsmith@acme.com"`, produces `email="jsmith@acme.com"`. Given user with `mailid=""` and `userid="jdoe@acme.com"`, uses userid as fallback. Given neither, produces `MISSING_DATA` decision. Source: 03b §2 field mapping.
- Resolves `locationId` by following cross-ref chain: user → `user_has_device` → phone → `device_in_pool` → device pool → `device_pool_to_location` → location (via `store.resolve_chain()`). Source: 03b §2 Cross-Reference Dependencies.
- Sets `create_method` from migration config ("scim" or "people_api"). Source: 03b §2 Execution strategy note.
- Stores bare extension (no routing prefix) from primary DN via `user_has_primary_dn` cross-ref. Source: 03b §2 Edge Cases.
- Does NOT produce `DUPLICATE_USER` decisions — that type is owned by `DuplicateUserAnalyzer`. Source: 03b §13 Decision Ownership Table.
- Does NOT produce `EXTENSION_CONFLICT` decisions — that type is owned by `ExtensionConflictAnalyzer`. Source: 03b §13 Decision Ownership Table.

**line_mapper:**
- Given DN "5551234567" at a US location, produces `CanonicalLine(e164="+15551234567", classification="NATIONAL", extension="5551234567")`. Given DN "1001", produces `CanonicalLine(extension="1001", classification="EXTENSION", e164=None)`. Source: 03b §3 E.164 Normalization Algorithm.
- Resolves location's country code by chain: DN → `device_has_dn` → device → `device_in_pool` → device pool → `device_pool_to_location` → location (via `store.resolve_chain()`). Source: 03b §3 Cross-Reference Dependencies.
- Given DN that can't be classified, produces `DN_AMBIGUOUS` decision (mapper-owned). Source: 03b §13 Decision Ownership Table.
- Tags `shared: true` on CanonicalLine when `device_has_dn` cross-ref shows multiple devices reference the same DN. Source: 03b §3 Edge Cases.
- Does NOT produce `EXTENSION_CONFLICT` decisions — that type is owned by `ExtensionConflictAnalyzer`. Source: 03b §13 Decision Ownership Table.
- Extensions outside 2-10 chars produce `MISSING_DATA` decision. Source: 03b §3 Edge Cases.

**pattern_converter:**
- `cucm_to_webex_pattern("9.1[2-9]XXXXXXXXX", "+1", "9")` returns `"+1[2-9]XXXXXXXXX"`. Source: 03b §6 Pattern Syntax Conversion table.
- `cucm_to_webex_pattern("9.011!", "+1", "9")` returns `"+!"`. Source: 03b §6.
- Strips access code prefix (everything before `.`), preserves wildcards (X, !, ranges). Source: 03b §6.

#### Testing rules

- **Real store, not mocks.** Use `:memory:` SQLite with real schema. No `MagicMock()` on MigrationStore. Source: Part 1 Anti-Pattern 1.
- **Fixture factories, not static files.** Build CUCM dicts programmatically. Source: Part 1 Anti-Pattern 2.
- **Each mapper gets at least 2 test scenarios:** (1) happy path — one clean object, (2) messy path — edge cases from 03b. Source: Part 1 Anti-Pattern 3.
- **Seed the store with normalized objects and cross-refs before running mappers.** Mappers read from the store, not from raw dicts.

#### Self-review checklist

- [ ] Mapper base class defined in `base.py` with `map()` abstract method, `_create_decision()`, `_fingerprint()`, decision option builders
- [ ] All three mappers inherit from Mapper base class and implement `map(self, store) -> MapperResult`
- [ ] location_mapper reads `device_pool_has_datetime_group` cross-ref (manifest row 1) for timezone
- [ ] location_mapper reads `device_pool_at_cucm_location` cross-ref (manifest row 2) for address
- [ ] location_mapper writes `device_pool_to_location` cross-ref (the only mapper-produced cross-ref)
- [ ] location_mapper consolidates multiple device pools sharing a CUCM Location into one CanonicalLocation
- [ ] location_mapper lowercases `announcementLanguage` (edge case from 03b §1)
- [ ] user_mapper reads `user_has_device` (manifest row 3) and `user_has_primary_dn` (manifest row 4)
- [ ] user_mapper resolves locationId via cross-ref chain (user → device → device pool → location)
- [ ] user_mapper stores bare extension without routing prefix
- [ ] user_mapper does NOT produce DUPLICATE_USER or EXTENSION_CONFLICT decisions (analyzer-owned)
- [ ] line_mapper reads `device_has_dn` (manifest row 5) and `dn_in_partition` (manifest row 6)
- [ ] line_mapper calls `e164.normalize_dn()` with country code resolved from location chain
- [ ] line_mapper tags `shared: true` when multiple devices reference same DN
- [ ] line_mapper does NOT produce EXTENSION_CONFLICT decisions (analyzer-owned)
- [ ] pattern_converter strips access code prefix (before `.`) and converts to E.164 format
- [ ] No field names invented — every Webex field comes from the reference docs
- [ ] No decision types produced that are owned by analyzers (per §13 Decision Ownership Table)
- [ ] Tests use real `:memory:` store, not MagicMock

---

### Session D2: Infrastructure Mappers (device, workspace, routing)

#### Read these files

**Design docs (read thoroughly):**
- `docs/plans/cucm-pipeline/03b-transform-mappers.md` §4 (device_mapper), §5 (workspace_mapper), §6 (routing_mapper — trunks, route groups, dial plans, translation patterns, pattern syntax conversion), §13 (Shared Patterns — Mapper base class, canonical ID convention)
- `docs/plans/cucm-pipeline/02-normalization-architecture.md` — Cross-Reference Manifest rows 7-15 (device_in_pool, device_owned_by_user, common_area_device_in_pool, route_pattern_in_partition, route_pattern_uses_gateway, route_pattern_uses_route_list, route_group_has_trunk, trunk_at_location, translation_pattern_in_partition)
- `docs/plans/cucm-pipeline/03-conflict-detection-engine.md` — §Decision Ownership design note: device_mapper owns DEVICE_INCOMPATIBLE and DEVICE_FIRMWARE_CONVERTIBLE. workspace_mapper owns WORKSPACE_LICENSE_TIER, WORKSPACE_TYPE_UNCERTAIN, HOTDESK_DN_CONFLICT. routing_mapper owns FEATURE_APPROXIMATION for `@` macro patterns.

**Prerequisite code (read to understand interfaces):**
- `src/wxcli/migration/transform/mappers/base.py` — Mapper ABC, decision helpers (from Session D1)
- `src/wxcli/migration/transform/pattern_converter.py` — `cucm_to_webex_pattern()` (from Session D1, routing_mapper reuses this)
- `src/wxcli/migration/models.py` — CanonicalDevice, CanonicalWorkspace, CanonicalTrunk, CanonicalRouteGroup, CanonicalDialPlan, CanonicalTranslationPattern
- `src/wxcli/migration/store.py` — MigrationStore API

**Webex API reference (for verifying field names):**
- `docs/reference/devices-core.md` — Device CRUD, activation codes, MAC format, model compatibility, `supportedDevices()` model strings, TelephonyDevicesApi vs DevicesApi distinction, `apply_changes` requirement
- `docs/reference/devices-workspaces.md` — Workspace creation (displayName, locationId, supportedDevices, calling.type, calling.webexCalling, hotdeskingStatus, type), immutable fields, Basic vs Professional license tiers, `/features/` vs `/telephony/config/` path families
- `docs/reference/call-routing.md` — Trunks (name, locationId, trunkType, address, password, deviceType immutability), Route Groups (localGateways, max 10 trunks), Dial Plans (dialPatterns, routeId, routeType), Translation Patterns (matchingPattern, replacementPattern)
- `docs/reference/person-call-settings-permissions.md` — Outgoing calling permissions context for routing_mapper's pattern classification (routing_mapper produces patterns that css_mapper later classifies against permission categories)

#### Produce these files

**Production code:**
- `src/wxcli/migration/transform/mappers/device_mapper.py`
- `src/wxcli/migration/transform/mappers/workspace_mapper.py`
- `src/wxcli/migration/transform/mappers/routing_mapper.py`

**Test code:**
- `tests/migration/transform/test_device_mapper.py`
- `tests/migration/transform/test_workspace_mapper.py`
- `tests/migration/transform/test_routing_mapper.py`

#### For each mapper, use checklist-before-writing

Before writing each mapper:
1. List every field mapping from 03b's field mapping table for that mapper
2. List every cross-ref read (from the Cross-Reference Dependencies table)
3. List every decision the mapper owns (from the Decisions Generated table + §13 Decision Ownership Table)
4. List every edge case from the Edge Cases section
5. Write the mapper
6. Verify against your checklist — every item accounted for

#### Acceptance criteria

**device_mapper:**
- Given phones with models "Cisco 6841" (native MPP), "Cisco 7841" (convertible), "Cisco 7911" (incompatible), produces `compatibility_tier="native_mpp"`, `"convertible"`, `"incompatible"` respectively. The 7911 gets a `DEVICE_INCOMPATIBLE` decision; the 7841 gets a `DEVICE_FIRMWARE_CONVERTIBLE` decision. Source: 03b §4 Phone Model Compatibility Table + Decisions Generated.
- Given phone with `name="SEP001122AABBCC"`, produces `mac="001122AABBCC"` (strip "SEP" prefix). Source: 03b §4 field mapping.
- Resolves location via `device_in_pool` (manifest row 7) → `device_pool_to_location` cross-ref. Source: 03b §4 Cross-Reference Dependencies.
- Resolves person association via `device_owned_by_user` (manifest row 8). Source: 03b §4.
- Stores `cucm_protocol` ("SIP" or "SCCP") — SCCP-only phones are classified as Incompatible. Source: 03b §4 field mapping.
- Does NOT process common-area phones (those go to workspace_mapper). Source: 03b §5 Edge Cases.

**workspace_mapper:**
- Given a common-area phone (`is_common_area=True`), produces `CanonicalWorkspace` with `locationId` from `common_area_device_in_pool` (manifest row 9). Source: 03b §5 field mapping.
- Given a common-area phone with both a DN and hoteling enabled, produces `HOTDESK_DN_CONFLICT` decision. Source: 03b §5 Decisions Generated.
- Determines Basic vs Professional license tier based on required settings, produces `WORKSPACE_LICENSE_TIER` decision. Source: 03b §5 Decisions Generated.
- Given ambiguous device pool classification, produces `WORKSPACE_TYPE_UNCERTAIN` decision. Source: 03b §5 Decisions Generated.
- Sets `calling.type = "webexCalling"` for migration targets. Source: 03b §5 field mapping.
- Infers `supportedDevices` ("phones" for MPP, "collaborationDevices" for Room/Board/Desk). Source: 03b §5 field mapping.

**routing_mapper:**
- Given CUCM pattern `"9.1[2-9]XXXXXXXXX"` with `country_code="+1"`, uses `cucm_to_webex_pattern()` (from D1) to produce `"+1[2-9]XXXXXXXXX"`. Source: 03b §6 Pattern Syntax Conversion table.
- Given a CUCM SIP trunk, produces `CanonicalTrunk(name=<name>, trunkType="REGISTERING", locationId=<resolved>)`. Source: 03b §6 Trunk field mapping.
- Trunk password can't be extracted — generates temporary placeholder and `MISSING_DATA` decision. Source: 03b §6 Decisions Generated.
- Given CUCM route group with 12 trunks, splits into multiple Webex route groups (max 10 per group). Source: 03b §6 Edge Cases.
- Given pattern with `@` macro, produces `FEATURE_APPROXIMATION` decision. Source: 03b §6 Decisions Generated.
- Given translation pattern with E.164 `replacementPattern` containing `X` wildcards, flags as invalid. Source: 03b §6 Edge Cases.
- Route patterns grouped by target into CanonicalDialPlan objects with `routeId` + `routeType`. Source: 03b §6 Dial Plan field mapping.

#### Testing rules

- **Real store, not mocks.** Use `:memory:` SQLite with real schema. Source: Part 1 Anti-Pattern 1.
- **Fixture factories, not static files.** Source: Part 1 Anti-Pattern 2.
- **Each mapper gets 2+ test scenarios.** Source: Part 1 Anti-Pattern 3.
- **device_mapper and workspace_mapper share the three-tier compatibility table.** Put it in a shared constant or utility, not duplicated.

#### Self-review checklist

- [ ] All three mappers inherit from Mapper base class (from D1's `base.py`) and implement `map(self, store) -> MapperResult`
- [ ] device_mapper reads `device_in_pool` (manifest row 7), `device_has_dn` (manifest row 5), `device_owned_by_user` (manifest row 8)
- [ ] device_mapper implements three-tier compatibility table: native_mpp (68xx, MPP 78xx/88xx), convertible (Enterprise 78xx/88xx), incompatible (79xx, 99xx, 69xx, 39xx, 7811, SCCP-only, non-MPP ATAs)
- [ ] device_mapper produces DEVICE_INCOMPATIBLE and DEVICE_FIRMWARE_CONVERTIBLE decisions (mapper-owned per §13)
- [ ] device_mapper stores `cucm_protocol` and classifies SCCP-only as incompatible
- [ ] device_mapper extracts MAC by stripping "SEP" prefix from device name
- [ ] workspace_mapper reads `common_area_device_in_pool` (manifest row 9) and `device_has_dn` (manifest row 5)
- [ ] workspace_mapper produces WORKSPACE_LICENSE_TIER, WORKSPACE_TYPE_UNCERTAIN, HOTDESK_DN_CONFLICT decisions (all mapper-owned)
- [ ] workspace_mapper sets `calling.type = "webexCalling"` and infers `supportedDevices`
- [ ] workspace_mapper detects hot desk + DN conflict (can't have extension when hotdeskingStatus=on)
- [ ] routing_mapper reads manifest rows 10-15 (route_pattern_in_partition, route_pattern_uses_gateway, route_pattern_uses_route_list, route_group_has_trunk, trunk_at_location, translation_pattern_in_partition)
- [ ] routing_mapper uses `cucm_to_webex_pattern()` from pattern_converter.py (D1 deliverable)
- [ ] routing_mapper splits route groups exceeding 10-trunk Webex limit
- [ ] routing_mapper generates temporary trunk passwords and MISSING_DATA decisions
- [ ] routing_mapper flags `@` macro patterns as FEATURE_APPROXIMATION
- [ ] No field names invented — every Webex field comes from the reference docs
- [ ] Tests use real `:memory:` store, not MagicMock

---

### Session D3a: CSS Decomposition (css_mapper + cucm_pattern.py)

**This is the hardest mapper session.** css_mapper implements the full CSS decomposition algorithm from `04-css-decomposition.md`. `cucm_pattern.py` is an **explicit deliverable** of this session — it is built here, not imported as a prerequisite.

#### Read these files

**Design docs (read thoroughly):**
- `docs/plans/cucm-pipeline/03b-transform-mappers.md` §7 (css_mapper — canonical objects produced, field mappings for CanonicalDialPlan and CanonicalCallingPermission, CSS decomposition flow, cross-ref queries, ordering conflict detection, edge cases), §12 (CSS Mapper Integration — module dependencies, cucm_pattern.py interface, data flow summary, relationship to routing_mapper), §13 (Decision Ownership: css_mapper owns CSS_ROUTING_MISMATCH and CALLING_PERMISSION_MISMATCH)
- `docs/plans/cucm-pipeline/04-css-decomposition.md` — The full algorithm: Step 1 (build CSS→Partition→Pattern graph), Step 2 (classify partitions: DIRECTORY/ROUTING/BLOCKING/MIXED), Step 3 (compute routing scope, group by identical scope, intersection-first baseline), Step 4 (compute restriction profiles, classify block patterns into Webex categories), Step 5 (detect ordering conflicts via pattern overlap)
- `docs/plans/cucm-pipeline/02-normalization-architecture.md` — Cross-Reference Manifest rows 16-20 (css_contains_partition with ordinal, partition_has_pattern, user_has_css, device_has_css, line_has_css)
- `docs/plans/cucm-pipeline/03-conflict-detection-engine.md` — §Decision Ownership: css_mapper produces per-CSS decisions. CSSRoutingAnalyzer and CallingPermissionAnalyzer consume css_mapper output but should check for existing mapper decisions before creating duplicates.

**Prerequisite code (read to understand interfaces):**
- `src/wxcli/migration/transform/mappers/base.py` — Mapper ABC (from D1)
- `src/wxcli/migration/transform/pattern_converter.py` — `cucm_to_webex_pattern()` (from D1, css_mapper reuses for pattern conversion)
- `src/wxcli/migration/transform/mappers/routing_mapper.py` — routing_mapper output (from D2, css_mapper reads trunk/route group IDs for dial plan targets)
- `src/wxcli/migration/models.py` — CanonicalDialPlan, CanonicalCallingPermission, DecisionType (CSS_ROUTING_MISMATCH, CALLING_PERMISSION_MISMATCH)
- `src/wxcli/migration/store.py` — MigrationStore API (especially cross-ref queries with ordinal for CSS partition priority)

**Webex API reference (for verifying field names):**
- `docs/reference/call-routing.md` — Dial Plans (dialPatterns, routeId, routeType), digit pattern constraints
- `docs/reference/person-call-settings-permissions.md` — Outgoing calling permissions: `callingPermissions[]` array structure (`callType`, `action`, `transferEnabled`), `useCustomEnabled`, `useCustomPermissions`, `OutgoingPermissionCallType` enum values (INTERNAL_CALL, TOLL_FREE, NATIONAL, INTERNATIONAL, PREMIUM_SERVICES_I, PREMIUM_SERVICES_II, OPERATOR_ASSISTED, CHARGEABLE_DIRECTORY_ASSISTED, SPECIAL_SERVICES_I, SPECIAL_SERVICES_II)

#### Produce these files

**Production code:**
- `src/wxcli/migration/transform/cucm_pattern.py` — **Explicit deliverable with its own test suite.** Contains: `cucm_pattern_to_regex()`, `cucm_patterns_overlap()`, `classify_block_pattern()`
- `src/wxcli/migration/transform/mappers/css_mapper.py`

**Test code:**
- `tests/migration/transform/test_cucm_pattern.py` — 25+ test cases for pattern compilation, overlap detection, block pattern classification
- `tests/migration/transform/test_css_mapper.py`

#### cucm_pattern.py interface (build this FIRST)

```python
# migration/transform/cucm_pattern.py

def cucm_pattern_to_regex(pattern: str) -> str:
    """Convert a CUCM digit pattern to a Python regex.
    X → [0-9], ! → [0-9]+, [1-4] → [1-4], [^5] → [^5]
    . → '' (stripped — separator only), + → \\+, @ → flagged for expansion
    """

def cucm_patterns_overlap(pattern_a: str, pattern_b: str) -> bool:
    """Return True if two CUCM patterns can match any common digit string.
    Uses enumeration: generate representative digit strings from each pattern's
    match space at lengths (4, 7, 10, 11, 15) and test against the other.
    """

def classify_block_pattern(pattern: str, category_rules: list[dict]) -> str | None:
    """Classify a CUCM blocking pattern into a Webex permission category.
    Returns category string ('international', 'premium', etc.) or None if
    unclassifiable. Uses configurable rules from migration config — NOT hardcoded US patterns.
    """
```

Source: 03b §12 cucm_pattern.py Interface.

**Critical anti-pattern:** Do NOT hardcode US dial rules. Load category rules from `config.json`'s `country_dial_rules`. Ship US/Canada defaults but accept rules as a parameter. Source: Part 1 Anti-Pattern 4.

#### For each deliverable, use checklist-before-writing

Before writing cucm_pattern.py:
1. List all pattern syntax elements from 03b §6 Pattern Syntax Conversion table
2. List all test pattern pairs from Part 1 Spike 1 (25+ cases)
3. Write the module
4. Verify all test cases pass

Before writing css_mapper:
1. List all 7 steps of the CSS decomposition flow from 03b §7
2. List all cross-ref queries (css_contains_partition, partition_has_pattern, user_has_css, device_has_css, line_has_css)
3. List both canonical types produced (CanonicalDialPlan, CanonicalCallingPermission)
4. List all decision types (CSS_ROUTING_MISMATCH, CALLING_PERMISSION_MISMATCH)
5. List all edge cases from 03b §7
6. Write the mapper
7. Verify against your checklist

#### Acceptance criteria

**cucm_pattern.py:**
- `cucm_pattern_to_regex("9.1[2-9]XXXXXXXXX")` produces regex matching `"912125551234"` but not `"911"`. Source: Part 2 acceptance #1.
- `cucm_patterns_overlap("9.!", "9.011!")` returns `True` (broad subsumes international). Source: Part 2 acceptance #2.
- `cucm_patterns_overlap("9.[2-9]XXXXXX", "9.1[2-9]XXXXXXXXX")` returns `False` (7-digit local vs 10-digit long distance). Source: Part 2 acceptance #3.
- `cucm_patterns_overlap("+1XXXXXXXXXX", "+1900XXXXXXX")` returns `True`. Source: Part 2 acceptance #4.
- `classify_block_pattern("9.011!", us_rules)` returns `"international"`. Source: 03b §7.
- `classify_block_pattern("9.1408XXXXXXX", us_rules)` returns `None` (area-code-specific, unclassifiable). Source: 03b §7.
- Tests include patterns with `[^5]` negated ranges and the `@` macro (flagged as requiring expansion). Source: Part 1 Spike 1.

**css_mapper:**
- Given a CSS with 3 partitions where partition 1 has only DNs, partition 2 has ROUTE-action patterns, partition 3 has BLOCK-action patterns, classifies as DIRECTORY, ROUTING, BLOCKING. Source: Part 2 acceptance #9.
- Given 2 CSSes with identical routing partitions (single scope group), produces org-wide dial plans with NO `CSS_ROUTING_MISMATCH` decisions. Source: Part 2 acceptance #10.
- Given 2 CSSes with different routing partitions (multiple scope groups), uses intersection as baseline, produces `CSS_ROUTING_MISMATCH` decisions for delta patterns. Source: Part 2 acceptance #11.
- Groups users by identical restriction profile (frozenset of blocked Webex categories), produces one `CanonicalCallingPermission` per group with `assigned_users[]` listing affected canonical_ids. Source: 03b §7 field mapping.
- Given a block pattern that can't be classified into any Webex category, produces `CALLING_PERMISSION_MISMATCH` decision. Source: 03b §7 Decisions Generated.
- Given a MIXED partition (both ROUTE and BLOCK patterns), splits into virtual ROUTING + BLOCKING partitions and produces `CSS_ROUTING_MISMATCH` decision. Source: 03b §7 Edge Cases.
- Calls `cucm_patterns_overlap()` for ordering conflict detection (route-shadows-block or block-shadows-route), produces decisions with risk assessment ("Webex MORE restrictive" or "Webex LESS restrictive"). Source: 03b §7 CSS Decomposition Flow step 7.
- Builds combined CSS by concatenating Line CSS (higher priority) then Device CSS (lower priority) for effective CSS computation. Source: 03b §7 Edge Cases "CSS on devices vs. users".

#### Testing rules

- **Real store, not mocks.** Source: Part 1 Anti-Pattern 1.
- **Configurable country rules, not hardcoded US patterns.** Source: Part 1 Anti-Pattern 4.
- **cucm_pattern.py gets 25+ test cases.** Source: Part 1 Spike 1.
- **css_mapper gets at least 4 test scenarios:** (1) single routing scope happy path, (2) multiple routing scopes with intersection, (3) MIXED partition, (4) ordering conflict. Source: Part 2 High-Risk Area Coverage §1.

#### Self-review checklist

- [ ] `cucm_pattern.py` is a standalone module with its own test suite (not embedded in css_mapper)
- [ ] `cucm_pattern_to_regex()` handles all CUCM syntax: X, !, [ranges], [^negation], `.` (strip), `+` (escape), `@` (flag)
- [ ] `cucm_patterns_overlap()` uses enumeration at representative lengths (4, 7, 10, 11, 15 digits)
- [ ] `classify_block_pattern()` accepts configurable `category_rules` parameter — no hardcoded US patterns
- [ ] css_mapper inherits from Mapper base class and implements `map(self, store) -> MapperResult`
- [ ] css_mapper reads `css_contains_partition` with ordinal (manifest row 16) preserving priority order
- [ ] css_mapper reads `partition_has_pattern` (manifest row 17) with action (ROUTE/BLOCK) per pattern
- [ ] css_mapper reads `user_has_css` (manifest row 18), `device_has_css` (manifest row 19), `line_has_css` (manifest row 20)
- [ ] css_mapper builds combined CSS: Line CSS (higher priority) + Device CSS (lower priority)
- [ ] css_mapper classifies partitions: DIRECTORY / ROUTING / BLOCKING / MIXED
- [ ] css_mapper splits MIXED partitions into virtual ROUTING + BLOCKING with a decision
- [ ] css_mapper computes routing scope per CSS as frozenset of ROUTE-action patterns
- [ ] css_mapper uses intersection-first baseline (not union — union would grant access users didn't have)
- [ ] css_mapper computes restriction profile per CSS as frozenset of blocked Webex categories
- [ ] css_mapper groups users by identical restriction profile → one CanonicalCallingPermission per group
- [ ] css_mapper detects ordering conflicts via `cucm_patterns_overlap()` with risk assessment
- [ ] css_mapper produces CanonicalDialPlan and CanonicalCallingPermission (two canonical types)
- [ ] css_mapper owns CSS_ROUTING_MISMATCH and CALLING_PERMISSION_MISMATCH (per §13 Decision Ownership)
- [ ] css_mapper reads routing_mapper output for trunk/route group IDs (dial plan targets)
- [ ] Tests use real `:memory:` store, not MagicMock

---

### Session D3b: Features + Voicemail (feature_mapper + voicemail_mapper)

#### Read these files

**Design docs (read thoroughly):**
- `docs/plans/cucm-pipeline/03b-transform-mappers.md` §8 (feature_mapper — HG/CQ/AA field mappings, simple features: Call Park, Pickup, Paging, OperatingMode), §10 (Feature Mapper Algorithm — classify_hunt_pilot(), Algorithm Mapping Table, queue-style detection heuristics), §9 (voicemail_mapper — field mapping, Unity Connection vs Webex), §11 (Voicemail Gap Analysis — 13-row gap table), §13 (Decision Ownership: feature_mapper and voicemail_mapper own FEATURE_APPROXIMATION, VOICEMAIL_INCOMPATIBLE, MISSING_DATA respectively)
- `docs/plans/cucm-pipeline/02-normalization-architecture.md` — Cross-Reference Manifest rows 21-27 (hunt_pilot_has_hunt_list, hunt_list_has_line_group, line_group_has_members, cti_rp_has_script, schedule_has_time_period, user_has_voicemail_profile, voicemail_profile_settings)
- `docs/plans/cucm-pipeline/03-conflict-detection-engine.md` — §Decision Ownership: FeatureApproximationAnalyzer consumes feature_mapper output. VoicemailIncompatAnalyzer consumes voicemail_mapper output. Both should check for existing mapper decisions before creating duplicates.

**Prerequisite code (read to understand interfaces):**
- `src/wxcli/migration/transform/mappers/base.py` — Mapper ABC (from D1)
- `src/wxcli/migration/models.py` — CanonicalHuntGroup, CanonicalCallQueue, CanonicalAutoAttendant, CanonicalCallPark, CanonicalPickupGroup, CanonicalPagingGroup, CanonicalOperatingMode, CanonicalVoicemailProfile
- `src/wxcli/migration/store.py` — MigrationStore API

**Webex API reference (for verifying field names):**
- `docs/reference/call-features-major.md` — Hunt Groups (name, extension, callPolicies.policy [REGULAR/CIRCULAR/SIMULTANEOUS/UNIFORM/WEIGHTED], agents[], callPolicies.noAnswer), Call Queues (name, extension, callPolicies.policy, callPolicies.routingType, agents[], queueSettings [queueSize, overflow, mohMessage]), Auto Attendants (name, extension, businessSchedule, businessHoursMenu, afterHoursMenu [both required, with greeting/extensionEnabled/keyConfigurations])
- `docs/reference/call-features-additional.md` — Call Park (name, extension, locationId, recall config required), Pickup Groups (name, agents[], one-per-user limit error 4471), Paging Groups (name, extension, targets[max 75], originators[]), Operating Modes (name, level=ORGANIZATION required, type SAME_HOURS_DAILY/DIFFERENT_HOURS_DAILY/HOLIDAY, limits: 100/org 100/location 150 holidays/mode)
- `docs/reference/person-call-settings-media.md` — Voicemail settings (enabled, sendAllCalls, sendBusyCalls, sendUnansweredCalls [numberOfRings, greeting], notifications, emailCopyOfMessage, messageStorage [storageType, externalEmail, mwiEnabled], faxMessage, transferToNumber), separate passcode API path, greeting upload via multipart/form-data, read-only fields to strip (voiceMessageForwardingEnabled, greetingUploaded, systemMaxNumberOfRings)

#### Produce these files

**Production code:**
- `src/wxcli/migration/transform/mappers/feature_mapper.py`
- `src/wxcli/migration/transform/mappers/voicemail_mapper.py`

**Test code:**
- `tests/migration/transform/test_feature_mapper.py`
- `tests/migration/transform/test_voicemail_mapper.py`

#### For each mapper, use checklist-before-writing

Before writing feature_mapper:
1. List the classify_hunt_pilot() algorithm from §10 (3 steps + algorithm mapping table)
2. List queue-style detection heuristics (5 indicators from §10)
3. List all field mappings for HG, CQ, AA, and simple features from §8
4. List all cross-ref reads (manifest rows 21-25)
5. List all decisions (FEATURE_APPROXIMATION, MISSING_DATA)
6. List all edge cases from §8 (schedule required for AA, CQ requires callPolicies, agent limits, etc.)
7. Write the mapper
8. Verify against your checklist

Before writing voicemail_mapper:
1. List all field mappings from §9 (15+ fields)
2. List the 13-row gap analysis table from §11 (which UC features have no Webex equivalent)
3. List cross-ref reads (manifest rows 26-27)
4. List decisions (VOICEMAIL_INCOMPATIBLE, MISSING_DATA)
5. List edge cases from §9
6. Write the mapper
7. Verify against your checklist

#### Acceptance criteria

**feature_mapper — Hunt Pilot Classification:**
- Given hunt pilot with `huntAlgorithm="Top Down"` and no queue features, `classify_hunt_pilot()` returns `"HUNT_GROUP"`. Mapper produces `CanonicalHuntGroup` with `callPolicies.policy="REGULAR"`. Source: 03b §10 Algorithm Mapping Table.
- Given hunt pilot with `huntAlgorithm="Circular"` and `queueCalls.enabled=True`, returns `"CALL_QUEUE"`. Mapper produces `CanonicalCallQueue` with `callPolicies.policy="CIRCULAR"`. Source: 03b §10.
- Given CTI Route Point (`isCtiRp=True`) with complex script, returns `"AUTO_ATTENDANT"` and produces `FEATURE_APPROXIMATION` decision. Source: 03b §10.
- Given hunt pilot with `huntAlgorithm="Broadcast"` and 60 line group members, produces `FEATURE_APPROXIMATION` decision noting 50-agent SIMULTANEOUS limit. Source: 03b §8 Edge Cases.
- Traverses 3-object cross-ref chain: hunt_pilot → `hunt_pilot_has_hunt_list` → hunt_list → `hunt_list_has_line_group` → line_group → `line_group_has_members` → DN/agent members. Source: 03b §8 Cross-Reference Dependencies.

**feature_mapper — Full Field Mapping:**
- Given HG classification, produces `CanonicalHuntGroup` with `name`, `extension` (bare), `callPolicies.policy`, `agents[]`, `enabled`. Source: 03b §8 HG field mapping.
- Given CQ classification, produces `CanonicalCallQueue` with `callPolicies.routingType="PRIORITY_BASED"`, `queueSettings.queueSize` (default 25). Source: 03b §8 CQ field mapping.
- Given AA classification, produces `CanonicalAutoAttendant` with `businessSchedule` (required), `businessHoursMenu`, `afterHoursMenu` (both required with greeting + extensionEnabled + keyConfigurations). Source: 03b §8 AA field mapping.

**feature_mapper — Simple Features:**
- Maps CUCM Call Park Number → `CanonicalCallPark` with `extension`, `locationId`, recall config. Source: 03b §8 Simple Features.
- Maps CUCM Time Period + Time Schedule → `CanonicalOperatingMode` with `level="ORGANIZATION"` (required), type, schedule data. Source: 03b §8 Simple Features.

**voicemail_mapper:**
- Given CUCM user with CFNA enabled and ring count=18 seconds, produces `sendUnansweredCalls.enabled=True`, `sendUnansweredCalls.numberOfRings=3` (18÷6=3). Source: 03b §9 field mapping.
- Given Unity Connection profile with `callerInputRules` configured (no Webex equivalent), produces `VOICEMAIL_INCOMPATIBLE` decision listing "caller input rules" as lost feature. Source: 03b §11 Gap Analysis.
- Given profile with pager/SMS notification active, produces `VOICEMAIL_INCOMPATIBLE` decision. Source: 03b §11 "Message notification (pager/SMS)".
- Given profile with fax enabled but migration targeting internal storage, notes fax is lost (requires external storage). Source: 03b §9 Edge Cases.
- Does NOT include read-only fields (voiceMessageForwardingEnabled, greetingUploaded, systemMaxNumberOfRings) in output. Source: 03b §9 Edge Cases.
- Custom greetings produce `MISSING_DATA` decision if audio files can't be extracted. Source: 03b §9 Decisions Generated.

#### Testing rules

- **Real store, not mocks.** Source: Part 1 Anti-Pattern 1.
- **feature_mapper gets at least 8 test scenarios** covering all rows of the Algorithm Mapping Table: Top Down→HG, Circular→HG, Longest Idle→HG, Broadcast→HG, Top Down+queue→CQ, Circular+queue→CQ, CTI RP simple→AA, CTI RP complex→FEATURE_APPROXIMATION. Source: Part 1 Spike 4.
- **voicemail_mapper gets happy path + gap detection scenarios.** Source: Part 1 Anti-Pattern 3.

#### Self-review checklist

- [ ] Both mappers inherit from Mapper base class and implement `map(self, store) -> MapperResult`
- [ ] feature_mapper implements `classify_hunt_pilot()` with 3 steps: (1) check CTI RP, (2) check queue features, (3) classify by algorithm
- [ ] feature_mapper checks all 5 queue-style indicators: queueCalls.enabled, maxCallersInQueue>0, mohSourceId not null, overflowDestination not null, voiceMailUsage != "NONE"
- [ ] feature_mapper traverses hunt_pilot → hunt_list → line_group → members (manifest rows 21-23)
- [ ] feature_mapper reads `cti_rp_has_script` (manifest row 24) for AA approximation
- [ ] feature_mapper reads `schedule_has_time_period` (manifest row 25) for OperatingMode
- [ ] feature_mapper handles agent limits: SIMULTANEOUS max 50, WEIGHTED max 100, others max 1000
- [ ] feature_mapper produces both HG and CQ with correct `callPolicies.policy` values
- [ ] feature_mapper produces AA with both `businessHoursMenu` and `afterHoursMenu` (both required)
- [ ] feature_mapper maps schedules to OperatingMode with `level="ORGANIZATION"` (required)
- [ ] feature_mapper maps Call Park with recall config (required by API)
- [ ] voicemail_mapper reads `user_has_voicemail_profile` (manifest row 26) and `voicemail_profile_settings` (manifest row 27)
- [ ] voicemail_mapper converts CFNA timeout seconds to ring count (÷6, clamped to [1, systemMaxNumberOfRings])
- [ ] voicemail_mapper checks all 13 rows of the gap analysis table (§11)
- [ ] voicemail_mapper produces single `VOICEMAIL_INCOMPATIBLE` decision per user listing ALL gaps
- [ ] voicemail_mapper strips read-only fields from output
- [ ] voicemail_mapper notes fax requires external storage
- [ ] No field names invented — every Webex field comes from the reference docs
- [ ] Tests use real `:memory:` store, not MagicMock

---

### Session D4: Engine + Integration Test (engine.py, rules.py, decisions.py)

#### Read these files

**Design docs (read thoroughly):**
- `docs/plans/cucm-pipeline/03b-transform-mappers.md` §13 (Shared Patterns — TransformEngine, MAPPER_ORDER, MapperError, TransformResult, Mapper registry and execution order, decision ownership table, unit test pattern, pre-existing Webex objects boundary)
- `docs/plans/cucm-pipeline/03-conflict-detection-engine.md` — §Auto-Resolution Rules: configurable rules that auto-resolve common decisions (e.g., DEVICE_INCOMPATIBLE → skip). Analyzer-owned decision types vs mapper-owned types.
- `docs/plans/cucm-pipeline/07-idempotency-resumability.md` — Decision fingerprinting (deterministic hash from causal data), merge_decisions() (three-way merge on re-analysis), decision staleness tracking
- `docs/plans/cucm-build-strategy.md` — Anti-Pattern 3: messy path test with ALL edge cases active simultaneously (shared lines + CSS mismatches + incompatible devices + hunt pilots with queue features)
- `docs/plans/cucm-build-contracts.md` — Phase 6 acceptance criteria #16 (TransformEngine orchestration), #17 (auto-resolution rules), #18 (full integration test with messy fixture set)

**Prerequisite code (read all mapper implementations):**
- `src/wxcli/migration/transform/mappers/base.py` — Mapper ABC (from D1)
- `src/wxcli/migration/transform/mappers/location_mapper.py` (D1)
- `src/wxcli/migration/transform/mappers/user_mapper.py` (D1)
- `src/wxcli/migration/transform/mappers/line_mapper.py` (D1)
- `src/wxcli/migration/transform/mappers/device_mapper.py` (D2)
- `src/wxcli/migration/transform/mappers/workspace_mapper.py` (D2)
- `src/wxcli/migration/transform/mappers/routing_mapper.py` (D2)
- `src/wxcli/migration/transform/mappers/css_mapper.py` (D3a)
- `src/wxcli/migration/transform/mappers/feature_mapper.py` (D3b)
- `src/wxcli/migration/transform/mappers/voicemail_mapper.py` (D3b)
- `src/wxcli/migration/models.py` — all canonical types, Decision, DecisionType
- `src/wxcli/migration/store.py` — MigrationStore API

**No Webex API reference docs needed.** This session orchestrates mappers (which already verified their own field names) and tests the full pipeline.

#### Produce these files

**Production code:**
- `src/wxcli/migration/transform/engine.py` — TransformEngine class with `run()` method, MAPPER_ORDER registry, failure handling (continue on mapper error)
- `src/wxcli/migration/transform/rules.py` — Auto-resolution rules engine: load rules from config, apply to decisions after analysis
- `src/wxcli/migration/transform/decisions.py` — Decision model helpers: fingerprinting, option management, decision summary formatting

**Test code:**
- `tests/migration/transform/test_engine.py` — Engine orchestration tests
- `tests/migration/transform/test_rules.py` — Auto-resolution tests
- `tests/migration/transform/test_integration.py` — Full messy fixture integration test

#### TransformEngine specification

```python
MAPPER_ORDER = [
    LocationMapper,       # Tier 0 — produces locations
    RoutingMapper,        # Tier 0 (trunks) / Tier 1 (route groups) / Tier 2 (dial plans)
    UserMapper,           # Tier 2 (depends on locations)
    LineMapper,           # Tier 2 (depends on locations for country code)
    WorkspaceMapper,      # Tier 2 (depends on locations)
    DeviceMapper,         # Tier 3 (depends on users, lines)
    FeatureMapper,        # Tier 4 (depends on users, lines, locations)
    CSSMapper,            # Tier 5 (depends on routing_mapper output)
    VoicemailMapper,      # Tier 5 (depends on users)
]

class TransformEngine:
    def run(self, store: MigrationStore) -> TransformResult:
        """Run all 9 mappers in dependency order.

        Failure handling: if a mapper raises an exception, log the error,
        record a MapperError, and continue to the next mapper. Downstream
        mappers that depend on the failed mapper's output will find no objects
        and produce MISSING_DATA decisions naturally.

        Returns TransformResult with aggregated decisions and any mapper errors.
        """
```

Source: 03b §13 TransformEngine class.

#### Auto-Resolution Rules specification

```python
# rules.py
def apply_auto_rules(store: MigrationStore, config: dict) -> int:
    """Apply auto-resolution rules from config to pending decisions.

    Config format:
    {"auto_rules": [
        {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
        {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert"},
    ]}

    Returns count of decisions auto-resolved.
    Each resolved decision gets: chosen_option=<choice>, resolved_by="auto_rule".
    """
```

Source: 03-conflict-detection-engine.md Auto-Resolution Rules.

#### For each deliverable, use checklist-before-writing

Before writing engine.py:
1. List the MAPPER_ORDER from 03b §13 (all 9 in dependency order)
2. List the failure handling strategy (continue on error, downstream sees no objects)
3. List the TransformResult structure (decisions + errors)
4. Write engine.py
5. Verify all 9 mappers are registered in correct order

Before writing the integration test:
1. List ALL edge cases to include (from Part 1 Anti-Pattern 3 + Part 2 acceptance #18)
2. Build the fixture set covering all edge cases
3. Define expected outputs (object counts, decision types)
4. Write the test
5. Verify every edge case is exercised

#### Acceptance criteria

**TransformEngine:**
- Given all 9 mappers registered in MAPPER_ORDER, `engine.run(store)` executes them in dependency order: location → routing → user → line → workspace → device → feature → css → voicemail. Source: 03b §13 MAPPER_ORDER.
- Returns `TransformResult` with aggregated decisions from all mappers and any MapperError entries. Source: 03b §13.
- If one mapper raises an exception (e.g., RoutingMapper), the engine logs the error, records a MapperError, and continues to UserMapper. Downstream mappers that depend on routing output produce MISSING_DATA decisions. Source: 03b §13 TransformEngine failure handling.

**Auto-resolution rules:**
- Given config with `auto_rules: [{type: "DEVICE_INCOMPATIBLE", choice: "skip"}]`, after analysis the DEVICE_INCOMPATIBLE decisions are auto-resolved with `chosen_option="skip"`, `resolved_by="auto_rule"`. Source: Part 2 acceptance #17.
- Rules only apply to pending (unresolved) decisions. Already-resolved decisions are not overwritten. Source: 07-idempotency-resumability.md.

**Full integration test — messy fixture set:**
- Fixture set contains: 2 locations (2 device pools, 1 consolidated), 5 users (1 with shared line, 1 with no email), 6 phones (2 sharing DN "1001", 1 incompatible 7911, 1 convertible 7841, 1 common-area), 2 CSSes with different routing scopes, 2 route patterns, 1 SIP trunk, 1 hunt pilot with queue features (→ CQ), 1 CTI Route Point (→ AA), 1 voicemail profile with caller input rules. Source: Part 2 acceptance #18.
- After full normalize → map pipeline, the store contains:
  - 2 CanonicalLocations (1 consolidated from 2 device pools sharing CUCM Location)
  - 4 CanonicalUsers mapped + 1 MISSING_DATA decision (no email user)
  - CanonicalDevices with correct compatibility tiers (native_mpp, convertible, incompatible)
  - CanonicalDialPlans from CSS intersection
  - CanonicalCallingPermissions grouped by restriction profile
  - 1 CanonicalCallQueue (from queue-style hunt pilot)
  - 1 CanonicalAutoAttendant (from CTI RP)
  - Decisions for: shared line (tagged), incompatible device, convertible device, CSS routing mismatch, voicemail incompatible (caller input rules)
- Source: Part 1 Anti-Pattern 3 + Part 2 acceptance #18.

#### Testing rules

- **Real store, not mocks.** Source: Part 1 Anti-Pattern 1.
- **The messy fixture set is the main deliverable of this session's tests.** It should exercise ALL edge cases simultaneously. Source: Part 1 Anti-Pattern 3.
- **Verify mappers don't interfere with each other.** Each mapper reads its own object types and writes its own output types. The integration test checks that running all 9 together produces correct results (no clobbering, no missed objects).

#### Self-review checklist

- [ ] engine.py registers all 9 mappers in MAPPER_ORDER in correct dependency order
- [ ] engine.py `run()` returns TransformResult with aggregated decisions and errors
- [ ] engine.py continues on mapper failure — does NOT abort the pipeline
- [ ] engine.py is idempotent — re-running produces the same output
- [ ] rules.py loads auto_rules from config and applies to pending decisions
- [ ] rules.py sets `resolved_by="auto_rule"` on auto-resolved decisions
- [ ] rules.py does not overwrite already-resolved decisions
- [ ] decisions.py provides fingerprinting, option management, summary formatting
- [ ] Integration test fixture set includes ALL edge cases from Part 2 acceptance #18
- [ ] Integration test verifies correct object counts by type
- [ ] Integration test verifies correct decision types are produced
- [ ] Integration test verifies shared line tagging flows through line_mapper
- [ ] Integration test verifies CSS intersection produces dial plans (not union)
- [ ] Integration test verifies hunt pilot with queue features → CanonicalCallQueue (not HG)
- [ ] Integration test verifies mappers don't interfere with each other
- [ ] Tests use real `:memory:` store, not MagicMock

---

## 3. Integration Test Plan

### Purpose

After all mapper sessions (D1-D3b) complete, the integration test (built in D4) verifies that the 9 mappers work correctly together. This is distinct from per-mapper unit tests — the integration test runs ALL mappers on a single shared fixture set and validates cross-mapper consistency.

### Integration Test Fixture Set

The "messy" fixture set simulates a real-world CUCM environment with common complexities:

| Object Type | Count | Edge Cases Included |
|------------|-------|---------------------|
| Device Pools | 3 | "HQ-Phones" and "HQ-Softphones" share CUCM Location "Headquarters" (consolidation test). "Branch-A-Phones" references a separate CUCM Location. |
| CUCM Location entities | 2 | "Headquarters" (address populated), "Branch-A" (address populated) |
| DateTimeGroups | 2 | "US-Eastern" (America/New_York), "US-Pacific" (America/Los_Angeles) |
| End Users | 5 | User 1: normal (email, phone, device). User 2: shared line (DN "1001" on 2 devices). User 3: no email (`mailid=""`, `userid` not email-format) → MISSING_DATA. User 4: normal at Branch-A. User 5: manager reference to User 1. |
| Phones | 6 | Phone 1: Cisco 6841 (native_mpp), owner=User1. Phone 2: Cisco 6841, owner=User2, shares DN "1001" with Phone 3. Phone 3: Cisco 7841 (convertible), owner=User2 (shared line). Phone 4: Cisco 7911 (incompatible), owner=User4. Phone 5: common-area phone (no owner, `is_common_area=True`). Phone 6: Cisco 6841, owner=User5 at Branch-A. |
| DNs | 5 | "1001" (shared by phones 2+3), "1002", "1003", "1004", "5551234567" (national number for User 1) |
| Partitions | 3 | "Internal-PT" (directory), "PSTN-PT" (routing), "Block-PT" (blocking) |
| CSSes | 2 | "Employee-CSS" (Internal-PT + PSTN-PT), "Restricted-CSS" (Internal-PT + PSTN-PT + Block-PT) — different routing scopes |
| Route Patterns | 2 | `"9.1[2-9]XXXXXXXXX"` in PSTN-PT (ROUTE), `"9.1900XXXXXXX"` in Block-PT (BLOCK) |
| SIP Trunk | 1 | "CUBE-GW-01" at HQ device pool |
| Hunt Pilot | 1 | Algorithm="Circular", `queueCalls.enabled=True` → should produce CQ, not HG |
| Hunt List | 1 | With line group containing 3 agents |
| CTI Route Point | 1 | Simple script → AA approximation with FEATURE_APPROXIMATION decision |
| Voicemail Profile | 1 | User 1: CFNA enabled (18 seconds), callerInputRules configured (→ VOICEMAIL_INCOMPATIBLE) |
| Time Schedule | 1 | "Business Hours" with time periods → OperatingMode |

### Expected Outputs

After `TransformEngine.run(store)`:

| Output Type | Expected Count | Key Verifications |
|------------|---------------|-------------------|
| CanonicalLocation | 2 | HQ consolidated from 2 device pools. Branch-A from 1 pool. Both have timezone, address, `announcementLanguage` lowercase. |
| CanonicalUser | 4 mapped + 1 decision | Users 1,2,4,5 mapped. User 3 gets MISSING_DATA (no email). User 5 stores `cucm_manager_user_id` referencing User 1. |
| CanonicalLine | 5 | DN "1001" tagged `shared: true` (appears on 2 devices). DN "5551234567" classified NATIONAL with `e164="+15551234567"`. |
| CanonicalDevice | 4 | Phone 1: native_mpp. Phone 3: convertible + DEVICE_FIRMWARE_CONVERTIBLE decision. Phone 4: incompatible + DEVICE_INCOMPATIBLE decision. Phone 6: native_mpp. |
| CanonicalWorkspace | 1 | From common-area phone 5. |
| CanonicalTrunk | 1 | "CUBE-GW-01" with generated password + MISSING_DATA decision. |
| CanonicalDialPlan | 1+ | From route patterns via routing_mapper + CSS intersection via css_mapper. |
| CanonicalCallingPermission | 1+ | Users grouped by restriction profile (Employee vs Restricted). |
| CanonicalCallQueue | 1 | From queue-style hunt pilot (not HG — queue features detected). |
| CanonicalAutoAttendant | 1 | From CTI RP with FEATURE_APPROXIMATION decision. |
| CanonicalOperatingMode | 1 | From time schedule with `level="ORGANIZATION"`. |
| CanonicalVoicemailProfile | 1 | User 1: `numberOfRings=3` (18÷6). VOICEMAIL_INCOMPATIBLE for callerInputRules. |

### Expected Decisions

| DecisionType | Count | Source |
|-------------|-------|--------|
| MISSING_DATA | 2+ | User 3 (no email), trunk (password) |
| DEVICE_INCOMPATIBLE | 1 | Phone 4 (Cisco 7911) |
| DEVICE_FIRMWARE_CONVERTIBLE | 1 | Phone 3 (Cisco 7841) |
| FEATURE_APPROXIMATION | 1 | CTI RP → AA approximation |
| VOICEMAIL_INCOMPATIBLE | 1 | User 1 (callerInputRules) |
| CSS_ROUTING_MISMATCH | 1+ | Different routing scopes between Employee-CSS and Restricted-CSS |

### Cross-Mapper Consistency Checks

These verify that mapper outputs are consistent with each other:

1. **Shared line detection flows through line_mapper.** DN "1001" has `shared: true` because `device_has_dn` cross-ref shows 2 devices.
2. **CSS decomposition uses routing_mapper output.** css_mapper's CanonicalDialPlan objects reference trunk/route group IDs produced by routing_mapper.
3. **Hunt pilot classification respects queue features.** The hunt pilot with `queueCalls.enabled=True` produces a CanonicalCallQueue, NOT a CanonicalHuntGroup. Changing this to `enabled=False` should produce a HG.
4. **Location consolidation propagates to downstream mappers.** Users at "HQ-Phones" and "HQ-Softphones" both resolve to the same consolidated CanonicalLocation.
5. **Device pool → location cross-ref written by location_mapper.** user_mapper, device_mapper, workspace_mapper all read `device_pool_to_location` written by location_mapper.
6. **Voicemail mapper finds the right user.** voicemail_mapper reads `user_has_voicemail_profile` and produces settings for the correct user.

---

## 4. Engine.py Build Plan

### Mapper Protocol

The `Mapper` base class/protocol is defined in **Session D1** so that D2, D3a, and D3b all implement the same interface. The protocol is:

```python
class Mapper(ABC):
    name: str
    depends_on: list[str] = []

    @abstractmethod
    def map(self, store: MigrationStore) -> MapperResult:
        ...
```

All 9 mappers import from `migration.transform.mappers.base` and implement this interface. This is non-negotiable — if the base class isn't defined in D1, the subsequent sessions will each invent incompatible interfaces.

### Engine.py `run()` Signature

```python
class TransformEngine:
    def run(self, store: MigrationStore) -> TransformResult:
        """Execute all 9 mappers in MAPPER_ORDER.

        Returns:
            TransformResult containing:
            - decisions: list[Decision] — aggregated from all mappers
            - errors: list[MapperError] — any mapper that raised an exception
        """
```

### Failure Handling

When a mapper throws an exception:

1. **Log the error** with full traceback
2. **Record a MapperError** (mapper_name, error message, traceback)
3. **Continue to the next mapper** — do NOT abort the pipeline
4. **Downstream mappers** that depend on the failed mapper's output will find no objects in the store for that type. They'll produce `MISSING_DATA` decisions naturally, which is the correct behavior — the admin sees "5 users couldn't resolve locations" rather than "pipeline crashed."

This strategy means a CSS mapper failure doesn't prevent user/device/feature mapping from completing. The admin gets partial results with clear error reporting.

### Stub-in-D1, Complete-in-D4 Strategy

- **D1:** Defines `Mapper` ABC in `base.py`. Does NOT create `engine.py` — the engine needs all 9 mappers to exist.
- **D2, D3a, D3b:** Each session imports `Mapper` from `base.py` and implements it. Each session tests its own mappers independently (seed store, run mapper, assert output).
- **D4:** Creates `engine.py` that imports all 9 mapper classes and registers them in `MAPPER_ORDER`. Also creates `rules.py` (auto-resolution) and `decisions.py` (helpers). Runs the full integration test.

### MAPPER_ORDER (dependency rationale)

| Order | Mapper | Why This Position |
|-------|--------|-------------------|
| 1 | LocationMapper | Tier 0 — everything depends on locations. Writes `device_pool_to_location` cross-ref used by all downstream mappers. |
| 2 | RoutingMapper | Tier 0-2 — trunks/route groups must exist before css_mapper references them as dial plan targets. Independent of users. |
| 3 | UserMapper | Tier 2 — depends on LocationMapper (resolves locationId via device pool chain). |
| 4 | LineMapper | Tier 2 — depends on LocationMapper (resolves country code for E.164). Can run after UserMapper since they're independent. |
| 5 | WorkspaceMapper | Tier 2 — depends on LocationMapper. Independent of users/lines. |
| 6 | DeviceMapper | Tier 3 — depends on UserMapper (resolves personId) and LineMapper (line appearances). |
| 7 | FeatureMapper | Tier 4 — depends on users and lines for agent resolution. |
| 8 | CSSMapper | Tier 5 — depends on RoutingMapper output for trunk/route group IDs. Runs after all user-related mappers to have user assignments. |
| 9 | VoicemailMapper | Tier 5 — depends on UserMapper for user canonical_ids. Independent of CSS. |

---

## 5. Self-Review

### All 9 mappers appear in exactly one session

| Mapper | Session | Verified |
|--------|---------|----------|
| location_mapper | D1 | Yes |
| user_mapper | D1 | Yes |
| line_mapper | D1 | Yes |
| device_mapper | D2 | Yes |
| workspace_mapper | D2 | Yes |
| routing_mapper | D2 | Yes |
| css_mapper | D3a | Yes |
| feature_mapper | D3b | Yes |
| voicemail_mapper | D3b | Yes |

None missing. None duplicated.

### Session ordering respects mapper dependencies

- D1 (location, user, line) has no mapper dependencies — these are foundational
- D2 (device, workspace, routing) depends on D1 — device/workspace resolve location via `device_pool_to_location` written by location_mapper
- D3a (css) depends on D1 (Mapper base class) and D2 (routing_mapper output for dial plan targets)
- D3b (feature, voicemail) depends on D1 (Mapper base class, user_mapper output) — independent of D2 and D3a
- D4 (engine) depends on D1, D2, D3a, D3b — all mappers must exist

### Reference doc count per session

| Session | Ref Doc Count | Docs |
|---------|--------------|------|
| D1 | 4 | provisioning.md, location-call-settings-core.md, person-call-settings-behavior.md, virtual-lines.md |
| D2 | 4 | devices-core.md, devices-workspaces.md, call-routing.md, person-call-settings-permissions.md |
| D3a | 2 | call-routing.md, person-call-settings-permissions.md |
| D3b | 3 | call-features-major.md, call-features-additional.md, person-call-settings-media.md |
| D4 | 0 | None needed — orchestration only |

All sessions ≤ 4 reference docs. Constraint satisfied.

### Code output per session

| Session | Est. Total Lines |
|---------|-----------------|
| D1 | ~730 (Mapper base ~110, location ~200, user ~180, line ~160, pattern_converter ~80). **Exceeds 600-line target.** Mitigation: base class is mostly boilerplate (code block provided in prompt), and pattern_converter is a thin utility. If quality degrades, split pattern_converter into its own micro-session. |
| D2 | ~580 (device ~190, workspace ~180, routing ~210) |
| D3a | ~540 (cucm_pattern ~220, css_mapper ~320) |
| D3b | ~480 (feature ~300, voicemail ~180) |
| D4 | ~500 (engine ~150, rules ~80, decisions ~120, integration test ~150) |

D2-D4 are under 600. D1 exceeds at ~730 due to the Mapper base class + pattern_converter. This is flagged above with mitigation options.

### Other checklist items

- [x] Each execution prompt includes the checklist-before-writing instruction
- [x] Each execution prompt has a session-specific self-review checklist
- [x] Integration test plan covers: shared line detection flowing through line_mapper, CSS decomposition flowing through css_mapper, hunt pilot classification flowing through feature_mapper
- [x] Engine.py plan defines the Mapper base class/protocol that all 9 mappers implement
- [x] css_mapper gets its own session (D3a) with cucm_pattern.py as an explicit deliverable with its own test suite
- [x] No session reads more than 4 reference docs
