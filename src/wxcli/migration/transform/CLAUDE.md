# transform/ — Normalization, Mapping, and Analysis (Phases 04-06)

Three-pass ELT pipeline that converts raw CUCM dicts into Webex-ready canonical objects with decisions for anything that can't be mapped automatically.

```
raw_data (from cucm/) → Pass 1: normalizers → Pass 2: cross_refs → mappers → analyzers → decisions
```

## Files

| File | Purpose |
|------|---------|
| `pipeline.py` | `normalize_discovery(raw_data, store)` — Phase 04 entry point: runs Pass 1 normalizers + Pass 2 cross-refs |
| `normalizers.py` | 41 Pass 1 normalizer functions + `NORMALIZER_REGISTRY` + `RAW_DATA_MAPPING` |
| `cross_reference.py` | `CrossReferenceBuilder` — Pass 2: builds `cross_refs` table (34 relationships + 3 enrichments) |
| `analysis_pipeline.py` | `AnalysisPipeline` — runs 15 analyzers, merges decisions, applies auto-rules, runs advisor |
| `rules.py` | `apply_auto_rules(store, config)` — auto-resolution rules (simple cases resolved without user input) |
| `decisions.py` | Decision-related helpers and constants |
| `e164.py` | E.164 normalization with site prefix stripping |
| `cucm_pattern.py` | CUCM dial pattern → Webex translation pattern conversion |
| `pattern_converter.py` | Route pattern wildcard conversion |
| `engine.py` | Mapper execution engine — runs mappers in dependency order |
| `mappers/` | 26 mapper classes — see `mappers/CLAUDE.md` |
| `analyzers/` | 15 analyzer classes — see their docstrings |

## Pass 1: Normalizers

`normalizers.py` contains 42 stateless pure functions. Each takes a raw CUCM dict and returns a canonical Pydantic model or `MigrationObject`. They are order-independent and parallel-safe — no cross-object lookups, foreign keys stay as CUCM name strings.

`RAW_DATA_MAPPING` is the routing table: `list[tuple[extractor_key, sub_key, normalizer_key]]` consumed by `normalize_discovery()`.

**Key normalizers:**
- `normalize_user` → `CanonicalUser`
- `normalize_phone` → `CanonicalDevice` (also triggers raw phone preservation — see below)
- `normalize_workspace` → `CanonicalWorkspace` (common-area phones classified post-normalization)
- `normalize_button_template` / `normalize_softkey_template` → `MigrationObject` (raw, for mapper consumption)
- `normalize_intercept_candidate` → `MigrationObject` (Tier 4 informational — intercept-like signals from CUCM)
- `normalize_dect_group` → `MigrationObject` (`dect_network:` prefix) — groups DECT handsets by CUCM device pool; each carries a `handset_assignments` list consumed by `DECTMapper`
- Translation patterns, route patterns, CSSes, partitions, etc. → `MigrationObject`

**Raw phone preservation (critical):** `normalize_phone()` creates a `CanonicalDevice` but discards the raw AXL dict. `pipeline.py` also stores each phone as `MigrationObject(canonical_id="phone:{name}", pre_migration_state=<full_raw_phone>)`. This is required because `MonitoringMapper`, `CallForwardingMapper`, `DeviceLayoutMapper`, `DeviceMapper`, and `WorkspaceMapper` all call `store.get_objects("phone")` to access `speeddials`, `busyLampFields`, and per-line call forwarding that isn't on `CanonicalDevice`.

## Pass 2: CrossReferenceBuilder

`cross_reference.py:CrossReferenceBuilder.build()` sweeps the full normalized inventory to populate the `cross_refs` table. 34 relationships + 3 enrichments across 10 method groups:

| Method | Relationships |
|--------|--------------|
| `_build_device_pool_refs` | device_pool_has_datetime_group, datetime_group_to_timezone |
| `_build_user_refs` | user_has_device, user_has_primary_dn |
| `_build_device_dn_refs` | device_has_dn, dn_in_partition, line_uses_css |
| `_build_device_ownership_refs` | device_owner, device_in_location, common_area_device |
| `_build_css_partition_graph` | css_has_partition, partition_in_css |
| `_build_css_assignment_refs` | user_has_css, device_has_css |
| `_build_routing_refs` | gateway_to_route_group, route_group_to_route_list, etc. |
| `_build_feature_refs` | feature_has_agent, aa_has_schedule, pickup members |
| `_build_voicemail_refs` | user_has_voicemail_profile, unity_user |
| `_build_voicemail_group_refs` | hunt_group_uses_voicemail_group (hunt pilot overflow/fwd dest → VM group extension) |
| `_build_intercept_refs` | user_has_intercept_signal |
| `_build_template_refs` | phone_uses_button_template, phone_uses_softkey_template |
| `_build_audio_refs` | feature_uses_moh_source (hunt pilot networkHoldMohAudioSourceID → music_on_hold canonical ID) |

**`line_assigned_to_user` is written by `LineMapper`, not here.** It is read by
`DeviceLayoutMapper` (line members), `MonitoringMapper` (BLF targets), and
`ReceptionistMapper`. It cannot live in `CrossReferenceBuilder`: that runs before the map
pass, and `line:` objects do not exist until `LineMapper` creates them. Nothing wrote it
until cross-site Phase 2, so all three consumers silently resolved every line to `None` —
which meant `member_canonical_id` was always empty and the device-members PUT was never
emitted at all. Owner resolution is `user_has_primary_dn` first, falling back to the owner
of the device carrying the DN at line index 1.

**Shared lines: `CrossReferenceBuilder._detect_shared_lines()` is the only producer.**
It creates `CanonicalSharedLine` objects from the `device_has_dn` cross-refs during the
enrichment pass. `cucm/extractors/shared_lines.py:SharedLineDetector` is **dead code** —
it has no caller anywhere in the pipeline, and wiring it would build a duplicate producer
of the same objects. Do not wire it. `DeviceLayoutMapper._build_shared_dn_set()` reads the
objects this method creates.

**Note:** `device_pool_to_location` is NOT built here — it's written by `LocationMapper` during the map pass, because the mapping requires decisions about ambiguous device pool → location assignments. Similarly, `voicemail_group_in_location` is written by `VoicemailGroupMapper` after location resolution. `feature_forwards_to_voicemail_group` is written by `FeatureMapper` when a hunt group/call queue forwarding destination matches a voicemail group extension — this powers the dependency graph edge that ensures `voicemail_group:create` runs before `feature:configure_forwarding`.

## Mapper Execution Engine

`engine.py` runs all 26 mapper classes in dependency order (topological sort on `depends_on`). Each mapper reads from the store, produces canonical objects via `store.upsert_object()`, and returns a `MapperResult` with counts and decisions. See `mappers/CLAUDE.md` for the full mapper inventory.

## Analysis Pipeline

`analysis_pipeline.py:AnalysisPipeline.run(store)` runs all 15 analyzers, then advisory, then recommendations:

1. Run 15 analyzers (topological order by `depends_on`) → collect `Decision` objects
2. Convert decisions to store dicts → merge via `store.merge_decisions()` (fingerprint-based, marks stale)
3. Apply auto-resolution rules from config
4. Run `ArchitectureAdvisor` (Phase 2 — reads merged decisions, produces `ARCHITECTURE_ADVISORY` decisions)
5. Populate recommendations on all decisions

**15 Analyzers:**

| Analyzer | Decision Types |
|----------|---------------|
| `ExtensionConflictAnalyzer` | `EXTENSION_CONFLICT` |
| `DNAmbiguityAnalyzer` | `DN_AMBIGUITY` |
| `DeviceCompatibilityAnalyzer` | `DEVICE_INCOMPATIBLE`, `DEVICE_WEBEX_APP` (INFO — transitions to Webex App, no device migration) (DECT-tier devices skipped; CONVERTIBLE-tier devices auto-convert at plan time — no decision emitted as of 2026-04-15) |
| `SharedLineAnalyzer` | `SHARED_LINE_COMPLEX` |
| `CSSRoutingAnalyzer` | `CSS_ROUTING_COMPLEX` |
| `CSSPermissionAnalyzer` | `CALLING_PERMISSION` |
| `LocationAmbiguityAnalyzer` | `LOCATION_AMBIGUOUS` |
| `DuplicateUserAnalyzer` | `DUPLICATE_USER` |
| `VoicemailCompatibilityAnalyzer` | `VOICEMAIL_INCOMPATIBLE` |
| `WorkspaceLicenseAnalyzer` | `WORKSPACE_LICENSE_TIER` |
| `FeatureApproximationAnalyzer` | `FEATURE_APPROXIMATION` |
| `MissingDataAnalyzer` | `MISSING_DATA` |
| `LayoutOverflowAnalyzer` | `LAYOUT_OVERFLOW` |
| `SelectiveCallHandlingAnalyzer` | `FEATURE_APPROXIMATION` (with `selective_call_handling_pattern` context key) |
| `CrossSiteAnalyzer` | `CROSS_SITE_DEPENDENCY` (table-driven: 18 rules over membership / monitoring / delegation / destination / device_placement / line_appearance) |

**CrossSiteAnalyzer is table-driven — add a row, not a branch.** `CROSS_SITE_RULES` in
`analyzers/cross_site.py` is the single source of truth for what counts as cross-site. Each
row names the object type, the member field, a collector kind (`_COLLECTORS` registry), and
how the construct's own location is determined (`field:` / `owner:` / `vote`). The sweep has
no per-type branching; new constructs are one-line additions. `resolve_entity_location()` in
the same module is the only correct way to get an entity's location — the field name is
`location_id` on some canonical types, `location_canonical_id` on others, and absent (inherit
from the owner) on the rest.

Two behaviours are unique to `CROSS_SITE_DEPENDENCY`: it is excluded from auto-resolution
(`_NEVER_AUTO_RESOLVE` in `rules.py`) and an *unresolved* one blocks plan expansion of its
construct. See `execute/CLAUDE.md` for the gate.

**Cascade re-evaluation:** `resolve_and_cascade(store, decision_id, chosen_option)` resolves one decision and re-runs only the analyzers whose `decision_types` intersect `cascades_to` from the decision's context. Uses `save_decision()` (not `merge_decisions()`) in the cascade path to avoid incorrectly staling decisions from non-cascaded analyzers.

## Key Gotchas

- **Two-pass design is load-bearing.** Pass 1 normalizers must not query the store (they're pure functions). Pass 2 cross-refs depend on all Pass 1 objects being in the store. Mappers depend on cross_refs. Don't mix these layers.
- **Mapper `depends_on` is enforced.** The engine topologically sorts mappers before running them. If mapper B reads objects produced by mapper A, B must list A in `depends_on`.
- **Decision fingerprints are idempotent.** Fingerprint = SHA256(type + context). Re-running the pipeline doesn't create duplicate decisions — `merge_decisions()` updates existing ones and stales missing ones.
- **Multiple decisions per object are normal.** A device can be both `DEVICE_INCOMPATIBLE` and `MISSING_DATA`. Each has a unique fingerprint and is resolved independently.
- **`analyze` status ≠ all decisions resolved.** Objects at `status='analyzed'` may still have unresolved decisions if they're non-blocking (e.g., `FEATURE_APPROXIMATION`). Only objects with blocking decisions stay at `needs_decision`.
- **`productSpecificConfiguration` XML is model-specific and version-dependent.** Each phone model has different PSC fields. The DeviceSettingsMapper handles missing fields gracefully and only maps fields it recognizes.
