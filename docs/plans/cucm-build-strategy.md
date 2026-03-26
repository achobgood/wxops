# CUCM→Webex Migration Pipeline — Build Strategy

Part 1 of 3 in the build planning sequence. This document defines the build order, risk spikes, and anti-patterns that Parts 2 (contracts) and 3 (mapper phases) consume.

**Architecture inputs:** [`cucm-pipeline-architecture.md`](cucm-pipeline-architecture.md) (summary), [`cucm-wxc-migration.md`](cucm-wxc-migration.md) (full spec), detailed pipeline docs in [`cucm-pipeline/01-07`](cucm-pipeline/).

**Existing codebase reviewed:** `src/wxcli/main.py` (Typer CLI, ~100 command groups, `add_typer()` registration pattern), `src/wxcli/commands/hunt_group.py` (command pattern: `get_api()` → `rest_get/post()` → `print_table/print_json()`), `src/wxcli/output.py` (Rich tables, JSON formatting, auto-detect columns).

---

## 1. Recommended Build Order

### Strategy: Bottom-Up with a Location Thin Thread

**Bottom-up**, not vertical slice. Three reasons:

1. **No CUCM lab.** A vertical slice (one object type end-to-end from AXL extraction through Webex provisioning) can't actually execute against a real system. Every test is fixture-driven regardless.
2. **The foundation blocks everything.** models.py is imported by every module. store.py is the inter-layer interface. Building these wrong cascades failure through 40+ files.
3. **The riskiest modules are in the middle of the pipeline** (CSS decomposition, feature mapper classification, E.164 normalization), not at the endpoints. Bottom-up lets us reach them faster.

**However:** pure bottom-up risks building 10 layers before discovering the pipeline integration is broken. The fix: after Phase 1 (foundation), build a **Location thin thread** — one object type through normalize → map → analyze → plan → execute — before building out breadth. This proves the pipeline architecture in ~5 sessions instead of ~25.

### Phase 1: Foundation (Layer 1)

**Goal:** Every other module imports from here. Get it right and tested thoroughly.

| Session | Files | Lines (est.) | What it proves |
|---------|-------|-------------|----------------|
| 1 | `models.py`, `test_models.py` | ~600 | All 20 Pydantic models serialize/deserialize, enums work, field validators catch bad data |
| 2 | `store.py`, `state.py`, `rate_limiter.py`, tests | ~700 | SQLite round-trip for 3+ model types, cross-ref queries with JSON extraction, state machine transitions, rate limiter token bucket |

**Why first:** Everything depends on it. Zero parallelism — this must complete before anything else starts.

**Key verification:** After Session 2, run a test that: (1) creates a CanonicalLocation, (2) upserts it to store, (3) queries it back by type and status, (4) verifies every field survived the SQLite JSON round-trip. If polymorphic deserialization doesn't work (dispatching `object_type` string → correct Pydantic class), fix it here before 40 files depend on it.

**Total: 2 sessions**

### Phase 2: Location Thin Thread

**Goal:** Prove the full pipeline architecture works with one simple object type before committing to 9 mappers × 12 analyzers.

| Session | Files | Lines (est.) | What it proves |
|---------|-------|-------------|----------------|
| 3 | `normalize_location()` (pass 1), `CrossReferenceBuilder` (scaffold: device pool refs only), fixtures, tests | ~650 | Stateless normalizer produces correct canonical model from CUCM dict, cross-ref builder inserts and queries relationships |
| 4 | `engine.py` (scaffold), `location_mapper.py`, `test_location_mapper.py` | ~600 | Mapper reads from store, writes mapped objects back, produces decisions for missing data. Engine orchestrates one mapper. |
| 5 | One simple analyzer (e.g., `LocationAmbiguousAnalyzer`), `planner.py` (scaffold: expand location ops), `dependency.py` (scaffold: build graph for locations only), basic executor path, tests | ~700 | Full pipeline: normalized object → mapped → analyzed → planned → executable DAG node. Proves the inter-layer handoff works. |

**Why second:** Catches pipeline integration bugs early. If the store→normalizer→mapper→analyzer→planner data flow has a design flaw, we learn after 5 sessions, not 20. The location type was chosen because it has the fewest dependencies (tier 0, no incoming cross-refs) and maps cleanly to one Webex API call.

**What this does NOT prove:** Cross-object dependencies, complex cross-references, CSS decomposition, or shared line detection. Those come in the risk spikes.

**Total: 3 sessions** (cumulative: 5)

### Phase 3: Risk Spikes

**Goal:** Retire the 4 highest-risk technical unknowns before committing to full-breadth implementation. See Section 2 for detailed spike descriptions.

| Session | Spike | Files | Lines (est.) |
|---------|-------|-------|-------------|
| 6 | CUCM pattern matching | `cucm_pattern.py`, `test_cucm_pattern.py` | ~500 |
| 7 | E.164 normalization | `e164.py`, line normalizer, `test_e164.py` | ~500 |
| 8-9 | CSS decomposition core | `css_mapper.py` (partition classification + routing scope + restriction profiles), tests | ~800 |
| 10 | Feature mapper classification | `feature_mapper.py` (hunt pilot → HG/CQ/AA classification + simple features), tests | ~600 |

**Why third:** These modules contain the hardest algorithms in the pipeline. CSS decomposition (spike 3-4) is explicitly called out as "the hardest problem" in the architecture. Feature mapper classification (spike 5) involves a non-obvious 3-object-to-1 mapping. If any spike reveals the architecture needs adjustment, it's cheaper to adjust now (5 sessions in) than later (20 sessions in).

**Parallelism:** Spikes 1-2 (cucm_pattern + E.164) are independent of each other and of Spike 3-4 (CSS mapper uses cucm_pattern, but the spike validates cucm_pattern independently first). Spike 5 (feature mapper) is independent of Spikes 1-4. **Two agent streams can work in parallel here:** one on spikes 1+3-4 (pattern → CSS), one on spikes 2+5 (E.164 → feature mapper).

**Total: 4-5 sessions** (cumulative: 9-10)

### Phase 4: Extraction Layer (Layer 2)

**Goal:** Build the CUCM AXL connection and all 8 extractors.

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 11 | `connection.py`, `extractors/users.py`, `extractors/devices.py`, `extractors/locations.py`, tests with mocked SOAP | ~700 | Core AXL client + the 3 most-referenced extractors |
| 12 | `extractors/features.py`, `extractors/routing.py`, `extractors/voicemail.py`, `extractors/shared_lines.py`, `extractors/workspaces.py`, `discovery.py`, tests | ~700 | Remaining extractors + orchestrator |

**Why here (not earlier):** Extraction produces raw CUCM dicts that normalizers consume — but we can hand-craft fixture dicts without working extractors. The transform pipeline (Phases 2-3) doesn't need extractors to be built. Building extraction now gives us real AXL response shapes for the fixture factory.

**Why not later:** By this point the transform pipeline is well-understood and fixture shapes are stabilized. Building extractors now means the normalizers' fixture dicts match what real AXL calls return.

**Parallelism:** This phase is fully independent of Phases 5-6 (remaining normalizers/mappers). **Can run in parallel with Phase 5.**

**Total: 2 sessions** (cumulative: 11-12)

### Phase 5: Remaining Normalizers + Full CrossReferenceBuilder (Layer 3a)

**Goal:** Complete all pass-1 normalizers and the full cross-reference builder (27 relationship types).

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 13 | Normalizers for: user, device, workspace, routing (partition, CSS, route pattern, gateway/trunk, route group, translation pattern), features (hunt pilot, CTI RP, schedule, call park, pickup, paging), voicemail, shared_lines. Tests. | ~800 | Many are small (50-80 lines each) but there are ~12 of them. Most follow the same pattern as the location normalizer from Phase 2. Tests for stateless normalizers are minimal (input dict → assert output fields), keeping the combined volume manageable. If total exceeds 800, split routing+feature normalizers into a separate session. |
| 14 | Full `CrossReferenceBuilder` (all 27 relationship types from 02-normalization-architecture.md manifest), verification tests | ~700 | This is mechanical but large — each of 27 relationships is a SQL query + insert. The structure was scaffolded in Phase 2; this session fills in the remaining 25 types. |

**Why here:** Mappers (Phase 6) read from the store using cross-references. All 27 relationships must exist before mappers can be built.

**Parallelism:** Can parallel with Phase 4 (extraction). Session 13 (normalizers) and Session 14 (CrossRefBuilder) are sequential — normalizers must exist before cross-ref builder can reference their output types.

**Total: 2 sessions** (cumulative: 13-14)

### Phase 6: Remaining Mappers (Layer 3b)

**Goal:** Build the 7 mappers not yet built (location_mapper from Phase 2, css_mapper core and feature_mapper classification from Phase 3 already exist).

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 15 | `user_mapper.py` + tests | ~500 | Medium complexity: email resolution, create_method flag, manager reference, location via device pool chain |
| 16 | `line_mapper.py` + tests | ~500 | Integrates e164.py from Phase 3. Extension/number classification, shared line tagging, extension conflict detection within CUCM data |
| 17 | `device_mapper.py` + `workspace_mapper.py` + tests | ~700 | Device mapper: 3-tier model compatibility table, MAC extraction, protocol tracking. Workspace mapper: common-area phone detection, license tier decision, hotdesk conflicts. Grouped because workspace_mapper reuses device_mapper's compatibility table. |
| 18 | `routing_mapper.py` + tests | ~650 | Four sub-mappings: trunks, route groups, dial plans (pattern syntax conversion), translation patterns. Medium complexity per sub-mapping. |
| 19 | `voicemail_mapper.py` + `css_mapper.py` completion + tests | ~600 | Voicemail mapper: Unity Connection profile → Webex VM settings (many fields, low algorithmic complexity). CSS mapper completion: integrate css_mapper core from Phase 3 with restriction profiles, full user assignment, ordering conflict integration with cucm_pattern.py. |
| 20 | `feature_mapper.py` completion + tests | ~600 | Extend Phase 3 classification stub into full mapper: HG/CQ/AA field mapping, schedule→OperatingMode mapping, call park/pickup/paging simple features, all decisions and edge cases from 03b spec. |
| 21 | `engine.py` completion, `rules.py`, `decisions.py`, full integration test | ~500 | Extend Phase 2 scaffold to orchestrate all 9 mappers in dependency order. `rules.py` implements auto-resolution rules for common conflicts (e.g., incompatible device → auto-skip). `decisions.py` provides the Decision model helpers used by both mappers and analyzers (fingerprinting, option management). Integration test: load a "messy" fixture set (multiple locations, shared lines, CSS with mixed partitions, hunt pilots) through full normalize → map pipeline. |

**Why here:** Mappers are the bulk of the codebase (~2,800 lines production code). They must follow normalizers (Phase 5) and benefit from the risk spike work (Phase 3) that already proved css_mapper and feature_mapper classification work.

**Parallelism:** Sessions 15-18 (user, line, device/workspace, routing mappers) are independent of each other — each reads different object types from the store and writes different output types. **4-way agent parallelism is possible here**, subject to swarm sizing rules (waves of 5-6, 1-2 files per agent). Sessions 19-21 depend on 15-18 (css_mapper needs routing_mapper output for dial plan references; engine.py integration test needs all mappers).

**Total: 7 sessions** (cumulative: 20-21)

### Phase 7: Analysis Pipeline (Layer 3c)

**Goal:** Build all 12 analyzers and the orchestration pipeline.

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 22 | `analysis_pipeline.py`, `DeviceCompatibilityAnalyzer`, `DuplicateUserAnalyzer`, `MissingDataAnalyzer`, `WorkspaceLicenseAnalyzer`, tests | ~700 | Pipeline orchestration + 4 simple analyzers. These are sweep-and-flag pattern — iterate objects, check conditions, emit decisions. |
| 23 | `SharedLineAnalyzer`, `ExtensionConflictAnalyzer`, `NumberConflictAnalyzer`, tests | ~600 | Medium complexity: shared line detection requires multi-device DN tracking, extension conflicts require cross-location comparison. NumberConflict is offline-only (CUCM-internal); Webex number collisions are deferred to preflight. |
| 24 | `CSSRoutingAnalyzer`, `CallingPermissionAnalyzer`, `FeatureApproximationAnalyzer`, `VoicemailIncompatAnalyzer`, `LocationAmbiguousAnalyzer`, tests | ~700 | CSS analyzers consume css_mapper output and produce user-facing decisions. Feature/voicemail analyzers sweep mapped features for fidelity losses. LocationAmbiguous was scaffolded in Phase 2 — complete it here. |

**Why here:** Analyzers operate on mapped objects (Phase 6 output). They can't run until mappers produce output. By design, analyzers are independent of each other — each sweeps the full inventory for its specific concern.

**Important architectural note:** Mappers produce per-object decisions (e.g., "this device is incompatible"). Analyzers produce cross-object decisions (e.g., "these 15 users share the same CSS routing scope mismatch"). Analyzers skip objects that already have mapper-produced decisions of the same type to avoid duplicates.

**Parallelism:** All 12 analyzers are independent. Sessions 22-24 can run in parallel (3-way agent parallelism). Each session groups analyzers by complexity similarity, not by dependency.

**Total: 3 sessions** (cumulative: 23-24)

### Phase 8: Plan + Execute + Rollback (Layers 3d + 4)

**Goal:** Build the execution pipeline: operation expansion, dependency DAG, batching, preflight, snapshot, executor, and rollback.

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 25 | `planner.py` (full: expand all object types to operations), `dependency.py` (full: DAG construction, cycle detection/breaking, tier validation), `batch.py` (site-based partitioning, rate limit budgeting), tests | ~800 | Planner was scaffolded in Phase 2 (location-only). This session expands to all ~10 object types × 2-5 operations each. dependency.py handles NetworkX graph + the REQUIRES/CONFIGURES/SOFT edge type safety rails. |
| 26 | `preflight.py`, `snapshot.py`, tests | ~600 | Preflight: 7 Webex org readiness checks (licenses, locations, PSTN, features, conflicts, rate budget). Snapshot: capture pre-migration Webex state for rollback targets. Both require mocked Webex API responses in tests. |
| 27 | `executor.py`, `rollback.py`, tests | ~700 | Executor: walk topological order, call `api.session.rest_*()`, record journal entries with type (CREATE/MODIFY/ASSIGN/CONFIGURE). Rollback: walk journal in reverse, apply type-appropriate reversal. Rate limiter integration from Phase 1. |

**Why here:** The planner reads analyzed objects (Phase 7). The executor reads the plan (planner output). Preflight and snapshot must run before execution. This is the natural pipeline sequence.

**Estimate uncertain — depends on mock complexity.** Preflight and executor tests require mocking the Webex REST API for multiple endpoint types. If the mock setup is complex, Sessions 26-27 could each stretch to 1.5 sessions.

**Parallelism:** Session 25 (plan) must complete before 26-27. Sessions 26 and 27 are somewhat independent (preflight/snapshot don't depend on executor) but share the mocked Webex API test infrastructure, so building them sequentially avoids duplicate mock setup.

**Total: 3 sessions** (cumulative: 26-27)

### Phase 9: Validate + Report + CLI (Layers 5 + 6)

**Goal:** Build post-execution validation, report generation, and all CLI commands.

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 28 | `comparator.py`, `report.py`, tests | ~600 | Comparator: read-back every Webex resource, compare key fields against canonical model, flag mismatches. Report: generate markdown with migration-specific sections (unmapped objects, decisions, CSS warnings, phone replacements, firmware conversion instructions). |
| 29 | `cucm.py` (all ~20 CLI commands), `cucm_config.py`, tests | ~700 | CLI commands are thin Typer wrappers: connect, test, discover, inventory, analyze, decisions, decide, plan, diff, preflight, execute, validate, rollback, status, report, export, import-decisions, db. Each command calls pipeline functions and formats output via existing `output.py`. |

**Why here:** CLI commands wrap pipeline functions that must exist first. Validation runs after execution.

**Total: 2 sessions** (cumulative: 28-29)

### Phase 10: Agent + Skills + Polish (Layer 7)

**Goal:** Build the migration-specific agent, skills, reference docs, and export/import features.

| Session | Files | Lines (est.) | Notes |
|---------|-------|-------------|-------|
| 30 | `cucm-migration-builder.md` agent, `cucm-discovery/SKILL.md`, `cucm-migration/SKILL.md`, `cucm-migration.md` + `cucm-axl-mapping.md` reference docs | ~800 | Agent follows `wxc-calling-builder.md` pattern. Skills provide guided workflows for discovery and execution. Reference docs document AXL mapping and gotchas found during implementation. |

**Why last:** Agent and skills reference CLI commands and pipeline behaviors. They can only be written accurately after the pipeline is built and its edge cases are known.

**Total: 1 session** (cumulative: 29-30)

### Build Order Summary

Total estimated sessions: **30** (range: 28-33 depending on mock complexity and normalizer/CSS mapper session splits).

Critical path: Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10.

Phase 4 (extraction) runs **off the critical path** — it parallels Phases 5-6.

The first **testable pipeline** (one object type, end-to-end) exists after **Phase 2 (session 5)**. The first **complete pipeline** (all object types, all analyzers) exists after **Phase 8 (session 27)**.

---

## 2. Risk-Ordered Spike List

These are ordered by blast radius — how much rework a failure in each area causes.

### Spike 1: CUCM Digit Pattern Matching (`cucm_pattern.py`)

**Risk:** The CSS decomposition algorithm depends entirely on correctly detecting overlap between CUCM digit patterns. CUCM patterns have unusual semantics (`X` = any digit, `!` = one or more digits, `[1-4]` = range, `.` = access code separator, `@` = national numbering plan macro). If `cucm_patterns_overlap()` produces false negatives, ordering conflicts go undetected — users silently get more or less access than they had in CUCM. If it produces false positives, the system generates spurious decisions that waste admin time and erode trust.

**What it proves:** That we can compile CUCM patterns to a testable form and reliably determine whether two patterns can match the same digit string.

**Smallest implementation:**
- `compile_cucm_pattern(pattern: str) -> re.Pattern` — translate CUCM syntax to regex
- `cucm_pattern_matches(pattern: str, digits: str) -> bool` — test a digit string against a compiled pattern
- `cucm_patterns_overlap(a: str, b: str) -> bool` — enumeration-based overlap detection (generate representative digit strings from each pattern's match space, test against the other)
- 25+ test cases with real CUCM pattern pairs:
  - `9.!` vs `9.011!` (overlapping, broad vs international)
  - `9.1[2-9]XXXXXXXXX` vs `9.1900XXXXXXX` (overlapping, ranges)
  - `9.1[2-9]XXXXXXXXX` vs `9.011!` (non-overlapping, domestic vs international)
  - `9.[2-9]XXXXXX` vs `9.1[2-9]XXXXXXXXX` (non-overlapping, local vs long distance)
  - `+1XXXXXXXXXX` vs `+1900XXXXXXX` (E.164 format overlap)
  - Patterns with `[^5]` negated ranges
  - The `@` macro (even if we just flag it as "requires expansion")

**Duration:** 1 session.

**Blast radius if skipped:** CSS mapper, CSSRoutingAnalyzer, CallingPermissionAnalyzer, and all downstream decisions about routing and permissions are unreliable. This is ~20% of the pipeline's decision-making surface.

### Spike 2: SQLite Store + Pydantic Polymorphic Round-Trip

**Risk:** The entire pipeline stores and retrieves Pydantic models via SQLite JSON blobs in the `data` column. The store must deserialize the right concrete type (`CanonicalUser` vs `CanonicalDevice` vs `CanonicalHuntGroup`) based on the `object_type` column. With 20 model types, some with nested models (e.g., `CanonicalDevice` contains `LineAppearance` objects), optional fields, and list fields, subtle serialization bugs can corrupt data silently — a field that's `None` on round-trip when it should be `""`, a nested model that becomes a plain dict, an enum that deserializes as a string.

**What it proves:** That we can upsert, query, and round-trip all model types through SQLite without data loss. That cross-reference queries using `json_extract()` work against the actual JSON structure Pydantic produces.

**Smallest implementation:** Folded into Phase 1 (sessions 1-2). Explicitly test:
- Round-trip for at least 5 model types including one with nested models (CanonicalDevice)
- `json_extract()` query against a nested field (e.g., `json_extract(data, '$.cucm_model')`)
- Cross-ref insert + query joining objects and cross_refs tables
- Upsert idempotency (upsert same object twice, verify no duplication)

**Duration:** 0 incremental sessions (part of Phase 1), but the test must be EXPLICIT, not implicit.

**Blast radius if broken:** Every module above the store (normalizers, mappers, analyzers, planner, executor) reads from the store. A serialization bug here is a foundation-level failure.

### Spike 3: E.164 Normalization with `phonenumbers` Library

**Risk:** CUCM DNs come in formats that `phonenumbers.parse()` may not handle as expected: 4-digit extensions (not phone numbers at all), 7-digit local numbers (deprecated in US but common in legacy CUCM), 10-digit national with site prefix (e.g., `91234567890` where `9` is the outside line access code), and full E.164 with `+`. The classification logic (EXTENSION / NATIONAL / E164 / AMBIGUOUS) drives number assignment for every user and line in the migration. If it misclassifies, users get wrong numbers or no numbers.

**What it proves:** That `phonenumbers` handles CUCM-style DN formats with correct country-code-specific behavior, and that site prefix stripping works correctly before classification.

**Smallest implementation:**
- `e164.py` with `normalize_dn(dn, country_code, site_prefix_rules) -> E164Result`
- 20+ test cases:
  - US: `1001` → EXTENSION, `5551234567` → NATIONAL (+15551234567), `+15551234567` → E164, `91234567890` with "strip 9" → NATIONAL
  - UK: `2001` → EXTENSION, `02012345678` → NATIONAL (+442012345678), `+442012345678` → E164
  - Edge cases: 1-digit DN → MISSING_DATA, 24-digit DN → AMBIGUOUS, DN that's valid in US but not UK
  - Site prefix rules: multiple prefixes per site, prefix that IS the start of a valid number

**Duration:** 1 session (paired with line normalizer).

**Blast radius if skipped:** Every CanonicalLine, CanonicalUser (primary extension), and CanonicalWorkspace (extension) gets wrong number classifications. Extension conflicts go undetected. User provisioning fails because invalid E.164 numbers are passed to the API.

### Spike 4: Feature Mapper — Hunt Pilot Classification

**Risk:** CUCM uses 3 objects (HuntPilot + HuntList + LineGroup) where Webex uses 1 (HuntGroup or CallQueue). The classification depends on traversing cross-references (hunt_pilot → hunt_list → line_group) and inspecting queue-style indicators. Wrong classification means creating a HG when it should be a CQ (losing queue features: overflow, MoH, announcements) or vice versa (CQ where a simple ring group sufficed, adding unnecessary complexity). Additionally, CTI Route Points → Auto Attendants is a "best effort" mapping with low confidence on complex IVR scripts.

**What it proves:** That cross-reference traversal works for multi-hop lookups (3 objects deep), and that the classification algorithm handles the real-world CUCM hunt configurations documented in the spec's algorithm mapping table.

**Smallest implementation:**
- `classify_hunt_pilot()` function + full field mapping for HG and CQ
- 8 fixture hunt pilots covering:
  - Top Down (no queue) → HG REGULAR
  - Circular (no queue) → HG CIRCULAR
  - Longest Idle → HG UNIFORM
  - Broadcast → HG SIMULTANEOUS (+ test with >50 agents for FEATURE_APPROXIMATION decision)
  - Top Down + queue features → CQ REGULAR
  - Circular + queue features → CQ CIRCULAR
  - CTI Route Point → AA (simple script)
  - CTI Route Point → AA (complex script → FEATURE_APPROXIMATION decision)

**Duration:** 1 session.

**Blast radius if skipped:** Every hunt group, call queue, and auto attendant in the migration could be the wrong type. These are the most visible call features — agents get different ring behavior, callers hear wrong prompts.

### Spike 5: Dependency Graph Cycle Detection

**Risk:** If cycle detection/breaking doesn't work correctly, the executor either deadlocks (trying to create resources that depend on each other) or silently breaks a hard REQUIRES dependency (creating an incomplete resource). The safety rail — all-REQUIRES cycles become hard errors, SOFT/CONFIGURES cycles break to tier 7 fixup — must be correct. NetworkX makes the basics easy, but the edge-type-aware breaking logic is custom.

**What it proves:** That the DAG handles real-world dependency patterns including: (a) all-REQUIRES cycle → hard error, (b) SOFT cycle → broken with fixup, (c) CONFIGURES cycle → broken with fixup, (d) mixed cycle → weakest edge broken, (e) no false cycles in normal acyclic configurations.

**Smallest implementation:**
- `dependency.py` with `build_dependency_graph()` and `detect_and_break_cycles()`
- 6 test cases:
  - Normal acyclic (locations → users → devices) — verify topological sort
  - AA-to-AA mutual transfer (SOFT cycle) — verify break + tier 7 fixup
  - User A monitors User B, B monitors A (SOFT cycle) — verify break
  - All-REQUIRES cycle (artificial) — verify hard error produced
  - Mixed cycle (REQUIRES + SOFT) — verify weakest edge broken
  - Tier validation: verify no edge points from higher tier to lower tier

**Duration:** 1 session (can be folded into Phase 8 session 25 if capacity allows).

**Blast radius if skipped:** Executor hangs or produces incomplete resources. Rollback may not work because resource creation order was wrong. Lower blast radius than spikes 1-3 because cycles are rare in real CUCM data — but when they occur, the failure mode is catastrophic (execution halts).

---

## 3. Anti-Patterns to Avoid

These are specific to **this** project — CUCM→Webex migration with SQLite store, Pydantic models, fixture-driven testing, no CUCM lab.

### Anti-Pattern 1: Mocking the SQLite Store in Mapper/Analyzer Tests

**What it looks like:**
```python
# DON'T DO THIS
mock_store = MagicMock()
mock_store.query_by_type.return_value = [fake_user]
mapper = UserMapper()
result = mapper.map(mock_store)
```

**Why it's wrong for this project:** The store IS the inter-layer interface. Mappers read via `store.get_objects()` + `store.get_cross_refs()` and write via `store.upsert_object()`. If you mock the store, you're testing the mapper's logic in isolation but NOT testing that it reads and writes the correct JSON structure, that cross-ref queries return the right related objects, or that the round-trip through SQLite preserves field types.

**What to do instead:** Use `:memory:` SQLite databases with the real schema. Seed them with fixture objects via `store.upsert_object()`. The store is fast enough (microseconds per query) that there's no performance reason to mock.

```python
# DO THIS
store = MigrationStore(":memory:")
store.upsert_object(make_canonical_user(email="jsmith@acme.com"))
store.add_cross_ref("device:SEP001122", "user:jsmith", "device_owned_by_user")
mapper = UserMapper()
result = mapper.map(store)
# Assert against the REAL store state after mapping
```

### Anti-Pattern 2: One XML Fixture File Per AXL Response Type

**What it looks like:** `tests/fixtures/axl_responses/listPhone_response.xml`, `listEndUser_response.xml`, ... — 50+ static XML files with full CUCM AXL response structure (dozens of fields per object, most irrelevant to the test).

**Why it's wrong for this project:** AXL responses are deeply nested XML with 30-80 fields per object. Maintaining 50+ static fixture files means: (a) changing a normalizer's field access pattern requires updating every fixture that touches that field, (b) new test cases require copying and modifying 200-line XML blobs, (c) it's impossible to tell which fields in a fixture are load-bearing vs. filler.

**What to do instead:** Build a fixture factory that constructs minimal CUCM dicts programmatically:

```python
def make_cucm_phone(name="SEP001122AABBCC", model="Cisco 7841",
                    device_pool="HQ-Phones", dn="1001",
                    partition="Internal-PT", css=None, owner=None):
    """Build a minimal CUCM phone dict matching AXL listPhone output."""
    return {
        "name": name,
        "model": model,
        "devicePoolName": {"_value_1": device_pool},
        "callingSearchSpaceName": {"_value_1": css},
        "ownerUserName": owner,
        "lines": {"line": [
            {"index": 1, "dirn": {"pattern": dn,
             "routePartitionName": {"_value_1": partition}}}
        ]},
    }
```

Each test builds exactly the fields it needs. The factory's defaults cover the common case. Edge case tests override specific fields. No fixture files to maintain.

### Anti-Pattern 3: Testing Mappers With Only Trivial Fixtures

**What it looks like:** Every mapper test uses one user, one phone, one DN, one location. Tests pass. Ship it.

**Why it's wrong for this project:** The bugs in CUCM→Webex mapping hide in the combinatorial cases:
- A user with 5 lines across 2 phones where line 1 is shared with another user
- A CSS with 3 partitions where partition 2 has MIXED routing+blocking patterns
- A hunt pilot with 2 line groups totaling 60 members (exceeds Webex's 50-agent SIMULTANEOUS limit)
- 3 device pools that share one CUCM Location entity (should produce 1 Webex location, not 3)
- A device pool with no CUCM Location reference at all (LOCATION_AMBIGUOUS decision)

**What to do instead:** Each mapper gets at least two test scenarios:
1. **Happy path** — one clean object, direct mapping, no decisions
2. **Messy path** — multiple objects with edge cases from the 03b mapper spec's "Edge Cases" section. This is where you test the decision generation, not just the mapping.

The full integration test (Phase 6, session 21) should load a scenario with ALL edge cases active simultaneously — shared lines + CSS mismatches + incompatible devices + hunt pilots with queue features — to verify mappers don't interfere with each other.

### Anti-Pattern 4: Hardcoding US Dial Rules in CSS Mapper

**What it looks like:**
```python
# DON'T DO THIS
if pattern.startswith("9.011"):
    return "international"
elif pattern.startswith("9.1900"):
    return "premium"
```

**Why it's wrong for this project:** The architecture explicitly requires configurable `country_dial_rules` in migration config. UK uses `00` for international, Germany uses `0` for national, Australia uses `0011` for international. The migration interview is designed to ask "What country?" and load country-specific rules. Hardcoding US patterns means the first non-US migration attempt produces completely wrong restriction profiles.

**What to do instead:** Load category rules from `config.json`'s `country_dial_rules` section. Ship US/Canada defaults. The CSS mapper's `effective_restrictions()` function must accept the rules as a parameter, not import them from a constant.

### Anti-Pattern 5: Building Extractors Before the Transform Pipeline

**What it looks like:** "Let's start with Layer 2 (extraction) since it's the first stage in the pipeline."

**Why it's wrong for this project:** There's no CUCM lab. Extractors can only be tested against mocked SOAP responses. Meanwhile, the transform pipeline (normalize → map → analyze → plan) can be fully tested with hand-crafted fixture dicts. Building extractors first produces code that can't be integration-tested while the pipeline (which CAN be tested) waits.

**What to do instead:** Build extraction in Phase 4 (after the transform pipeline core is proven), or in parallel with Phases 5-6. The fixture factory (Anti-Pattern 2) defines the contract between extraction and normalization — extractors must produce dicts matching the factory's structure.

### Anti-Pattern 6: Putting Business Logic in CLI Commands

**What it looks like:**
```python
@app.command("analyze")
def analyze(project_id: str):
    store = MigrationStore(get_db_path(project_id))
    # 50 lines of analysis logic here...
    for obj in store.query_by_type("user"):
        if not obj.email:
            decisions.append(Decision(...))
    # ... more logic
```

**Why it's wrong for this project:** The CLI layer (`cucm.py`) should be thin Typer wrappers — parse args, call pipeline function, format output. If analysis logic lives in `cucm.py`, it can't be tested without invoking the CLI, can't be called from the agent/skill layer, and can't be reused from the executor.

**What to do instead:** `cucm.py analyze` calls `engine.map(store)` then `pipeline.analyze(store)`. The command handles output formatting, progress bars, and user confirmation — nothing else.

### Anti-Pattern 7: Over-Engineering the AXL Connection Layer

**What it looks like:** Building connection pooling, WSDL caching, automatic reconnection, retry with circuit breaker, AXL version negotiation — all for a connection that can't be tested against a real endpoint.

**Why it's wrong for this project:** Without a CUCM lab, all of this complexity is untestable dead code. The AXL connection layer needs exactly: (a) load WSDL, (b) authenticate, (c) call one method with parameters, (d) return the response dict, (e) paginate. That's ~100-150 lines.

**What to do instead:** Build the minimum viable `connection.py`. Add retry logic, pooling, and version negotiation when there's a live endpoint to test against. The interface (`call_axl(method, **params) -> list[dict]`) should be stable; the implementation can grow later.

### Anti-Pattern 8: Skipping Cross-Reference Verification After Normalization

**What it looks like:** Build all 27 cross-reference types in `CrossReferenceBuilder`, assume they're correct, move on to mappers.

**Why it's wrong for this project:** If a cross-reference is missing (e.g., `user_has_device` wasn't built because the AXL field name was wrong in the normalizer), the user_mapper silently produces users with no location (because it resolves location via user → device → device pool → location). The mapper doesn't error — it generates a `MISSING_DATA` decision for every user, which looks like bad CUCM data rather than a pipeline bug.

**What to do instead:** After `CrossReferenceBuilder.build()` completes, run a verification sweep:
```python
EXPECTED_REFS = {
    "device_has_dn": ("device", "line"),  # (from_type, to_type)
    "user_has_device": ("user", "device"),
    # ... all 27
}
for ref_type, (from_type, to_type) in EXPECTED_REFS.items():
    count = store.count_cross_refs(ref_type)
    if count == 0:
        logger.warning(f"No {ref_type} cross-refs built — {from_type}→{to_type} resolution will fail")
```

This catches the bug in normalization, not in a mapper 3 layers downstream.

### Anti-Pattern 9: Not Encoding Webex API Constraints in Mappers

**What it looks like:** Mapper produces a CanonicalLocation with `announcementLanguage: "en_US"` (mixed case), or a CanonicalUser with `extension: "8001001"` (includes routing prefix), or a CanonicalWorkspace with both `hotdeskingStatus: "on"` and an extension assigned.

**Why it's wrong for this project:** The reference docs and 03b mapper spec document dozens of Webex API constraints — announcement language must be lowercase, extensions exclude routing prefix, hot desk workspaces can't have extensions, locationId is write-once, etc. If mappers don't enforce these constraints, the executor fails with cryptic API errors (400 "Invalid Language Code", 405 "Invalid Professional Place"). The bug is in the mapper's output, but it surfaces in the executor — 2 layers away.

**What to do instead:** Each mapper must validate its output against the Webex constraints documented in the 03b spec's "Edge Cases" section. The CanonicalLocation Pydantic model should have a validator that lowercases `announcementLanguage`. The CanonicalLine model should have a validator that strips routing prefixes. These are data quality checks at the model level, not business logic in the mapper.

### What Will Seem Hard But Is Actually Straightforward

Not everything in this pipeline is as scary as it looks. Three things that appear daunting but are mostly mechanical:

1. **The 12 analyzers.** They look like a lot — 12 classes, each with its own detection logic. But the architecture designed them as independent sweep-and-flag classes. Each follows the same pattern: query objects by type from the store, check a condition, emit a Decision if the condition is true. Most are 80-120 lines. The hard analysis work (CSS decomposition, pattern matching) lives in the mappers and `cucm_pattern.py`, not the analyzers. The analyzers consume that work and present it to the user.

2. **The dependency DAG (NetworkX).** Building a directed acyclic graph with topological sort sounds like an algorithms interview question, but NetworkX does the heavy lifting. `nx.DiGraph()`, `G.add_edge()`, `nx.topological_sort(G)`, `nx.find_cycle(G)` — the library API is 4 calls. The custom work is the edge-type-aware cycle breaking, which is ~50 lines of logic (Spike 5 proves this).

3. **The 8 extractors.** Each one calls one or two AXL `list*` methods with pagination, returns a list of dicts. The extractors are repetitive by design — same pagination pattern, same error handling, same return type. Once `users.py` works, the other 7 follow the template. The hard extraction work is in `connection.py` (WSDL setup, auth), which is one file.

---

## 4. Build Phase Summary Table

| Phase | Name | Files Produced | Sessions (est.) | Dependencies | Can Parallelize? |
|-------|------|---------------|-----------------|-------------|-----------------|
| 1 | Foundation | `models.py`, `store.py`, `state.py`, `rate_limiter.py` + tests | 2 | None | No — blocks everything |
| 2 | Location Thin Thread | Location normalizer, `CrossReferenceBuilder` (scaffold), `engine.py` (scaffold), `location_mapper.py`, one analyzer (scaffold), `planner.py` (scaffold), `dependency.py` (scaffold) + tests | 3 | Phase 1 | No — sequential pipeline proof |
| 3 | Risk Spikes | `cucm_pattern.py`, `e164.py`, `css_mapper.py` (core), `feature_mapper.py` (classification) + tests | 5 | Phase 1-2 | Yes — 2 streams: (patterns + CSS) and (E.164 + feature mapper) |
| 4 | Extraction Layer | `connection.py`, 8 extractors (`users.py`, `devices.py`, `locations.py`, `features.py`, `routing.py`, `voicemail.py`, `shared_lines.py`, `workspaces.py`), `discovery.py` + tests | 2 | Phase 1 | Yes — fully independent of Phases 5-6 |
| 5 | Remaining Normalizers + CrossRef | All remaining pass-1 normalizers (~12), full `CrossReferenceBuilder` (all 27 relationship types) + tests | 2 | Phase 2 (for normalizer patterns), Phase 4 (for AXL response shapes, soft dependency) | Partially — normalizers then CrossRef sequentially, but phase parallels Phase 4 |
| 6 | Remaining Mappers | `user_mapper.py`, `line_mapper.py`, `device_mapper.py`, `workspace_mapper.py`, `routing_mapper.py`, `voicemail_mapper.py`, `css_mapper.py` (completion), `feature_mapper.py` (completion), `engine.py` (completion), `rules.py`, `decisions.py` + tests | 7 | Phase 3 (risk spike outputs), Phase 5 (normalizers + cross-refs) | Yes — sessions 15-18 are 4-way parallelizable (user, line, device/workspace, routing mappers are independent) |
| 7 | Analysis Pipeline | `analysis_pipeline.py`, 12 analyzer classes + tests | 3 | Phase 6 (mappers produce objects analyzers sweep) | Yes — all 3 sessions are parallelizable (analyzers are independent by design) |
| 8 | Plan + Execute | `planner.py` (full), `dependency.py` (full), `batch.py`, `preflight.py`, `snapshot.py`, `executor.py`, `rollback.py` + tests | 3 | Phase 7 (analyzers produce decisions planner reads) | Partially — session 25 (plan) before 26-27. Sessions 26 and 27 share mock infrastructure. |
| 9 | Validate + CLI | `comparator.py`, `report.py`, `cucm.py`, `cucm_config.py` + tests | 2 | Phase 8 (executor must exist for CLI wrappers) | Partially — comparator/report parallel with CLI |
| 10 | Agent + Skills | `cucm-migration-builder.md`, `cucm-discovery/SKILL.md`, `cucm-migration/SKILL.md`, reference docs | 1 | Phase 9 (CLI commands must exist for agent to reference) | No — sequential |
| | **Total** | | **30** | | |

### Parallelism Map

```
Session:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30
Phase 1:  ██ ██
Phase 2:           ██ ██ ██
Phase 3:                       ██ ██ ██ ██ ██
Phase 4:                       ██ ██                              ← parallel with Phase 3/5
Phase 5:                                      ██ ██
Phase 6:                                            ██ ██ ██ ██ ██ ██ ██
Phase 7:                                                              ██ ██ ██  ← 3-way parallel
Phase 8:                                                                       ██ ██ ██
Phase 9:                                                                                ██ ██
Phase 10:                                                                                     ██
```

**Best-case calendar with 2 parallel streams:** ~20-22 sessions elapsed (some phases overlap).
**Serial execution:** 29-30 sessions.

### File Count Per Phase

| Phase | Production Files | Test Files | Total Files |
|-------|-----------------|------------|-------------|
| 1 | 4 | 4 | 8 |
| 2 | 5 (scaffolds) | 3 | 8 |
| 3 | 4 | 4 | 8 |
| 4 | 10 | 4 | 14 |
| 5 | ~14 (normalizers + CrossRef) | 3 | ~17 |
| 6 | 9 (mappers + engine) | 9 | 18 |
| 7 | 13 (pipeline + 12 analyzers) | 6 | 19 |
| 8 | 5 | 5 | 10 |
| 9 | 4 | 3 | 7 |
| 10 | 4 (markdown) | 0 | 4 |
| **Total** | **~72** | **~41** | **~113** |

---

## Self-Review Checklist

- [x] **Every layer from the summary table appears in the build order.** Layers 1-7 all covered. Layer 3 split into 3a (Phase 5), 3b (Phases 3+6), 3c (Phase 7), 3d (Phase 8). Layers 4-5 in Phases 8-9. Layer 6 in Phase 9. Layer 7 in Phase 10.
- [x] **Build order respects the dependency column.** No phase is scheduled before its dependency: Phase 2 after 1, Phase 5 after 2, Phase 6 after 3+5, Phase 7 after 6, Phase 8 after 7, Phase 9 after 8, Phase 10 after 9. Phase 4 (extraction) is correctly shown as independent of Phases 5-6.
- [x] **Session estimates are realistic.** No single session produces more than 4-5 files. Most sessions produce 1-2 production files + 1-2 test files. Line counts per session range 500-800.
- [x] **Spike list includes at least one item from Layer 3b (mappers).** Spikes 1, 3, and 4 are all Layer 3b: cucm_pattern.py (used by css_mapper), css_mapper core, and feature_mapper classification.
- [x] **Anti-patterns are specific to THIS project.** All 9 anti-patterns reference specific project constraints: SQLite store vs mocks, CUCM AXL fixture structure, no CUCM lab, Webex API constraints from the 03b spec, configurable country_dial_rules, cross-reference verification.
- [x] **Build order accounts for no CUCM lab.** Extraction (Layer 2) is deferred to Phase 4 specifically because it can't be integration-tested without a lab. Fixture factory approach (Anti-Pattern 2) is the primary testing strategy. All transform pipeline testing is fixture-driven.
- [x] **Phase summary table is complete and internally consistent.** 10 phases, all with files/sessions/dependencies/parallelism. Session totals in table (2+3+5+2+2+7+3+3+2+1 = 30) match the build order narrative (30). File counts (~74 prod + ~41 test = ~115) are consistent with the module structure in cucm-wxc-migration.md (including `rules.py` and `decisions.py` in Phase 6).

### Final dependency check

For each phase, can a builder start with ONLY the outputs of prior phases and the architecture docs?

- **Phase 1:** Yes — reads architecture docs only, produces foundation modules.
- **Phase 2:** Yes — needs Phase 1 outputs (models, store) + architecture docs for location mapping spec.
- **Phase 3:** Yes — needs Phase 1-2 outputs + 03b mapper spec + 04 CSS decomposition spec.
- **Phase 4:** Yes — needs Phase 1 outputs (models for dict shape) + AXL documentation (in cucm-wxc-migration.md).
- **Phase 5:** Yes — needs Phase 1-2 outputs (models, store, normalizer pattern) + 02 normalization spec for cross-ref manifest.
- **Phase 6:** Yes — needs Phase 3 outputs (spike code), Phase 5 outputs (normalizers, cross-refs) + 03b mapper spec.
- **Phase 7:** Yes — needs Phase 6 outputs (mapped objects in store) + 03 conflict detection engine spec.
- **Phase 8:** Yes — needs Phase 7 outputs (analyzed objects + decisions) + 05 dependency graph spec + 07 idempotency spec.
- **Phase 9:** Yes — needs Phase 8 outputs (executor, rollback) + CLI patterns from existing `hunt_group.py` and `output.py`.
- **Phase 10:** Yes — needs Phase 9 outputs (working CLI commands) + existing agent/skill patterns from `wxc-calling-builder.md`.
