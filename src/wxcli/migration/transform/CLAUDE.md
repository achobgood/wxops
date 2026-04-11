# transform/ — Normalization, Mapping, and Analysis (Phases 04-06)

Three-pass ELT pipeline that converts raw CUCM dicts into Webex-ready canonical objects with decisions for anything that can't be mapped automatically.

```
raw_data (from cucm/) → Pass 1: normalizers → Pass 2: cross_refs → mappers → analyzers → decisions
```

## Files

| File | Purpose |
|------|---------|
| `pipeline.py` | `normalize_discovery(raw_data, store)` — Phase 04 entry point: runs Pass 1 normalizers + Pass 2 cross-refs |
| `normalizers.py` | 37 Pass 1 normalizer functions + `NORMALIZER_REGISTRY` + `RAW_DATA_MAPPING` |
| `cross_reference.py` | `CrossReferenceBuilder` — Pass 2: builds `cross_refs` table (30 relationships + 3 enrichments) |
| `analysis_pipeline.py` | `AnalysisPipeline` — runs 13 analyzers, merges decisions, applies auto-rules, runs advisor |
| `rules.py` | `apply_auto_rules(store, config)` — auto-resolution rules (simple cases resolved without user input) |
| `decisions.py` | Decision-related helpers and constants |
| `e164.py` | E.164 normalization with site prefix stripping |
| `cucm_pattern.py` | CUCM dial pattern → Webex translation pattern conversion |
| `pattern_converter.py` | Route pattern wildcard conversion |
| `engine.py` | Mapper execution engine — runs mappers in dependency order |
| `mappers/` | 22 mapper classes — see `mappers/CLAUDE.md` |
| `analyzers/` | 13 analyzer classes — see their docstrings |

## Pass 1: Normalizers

`normalizers.py` contains 37 stateless pure functions. Each takes a raw CUCM dict and returns a canonical Pydantic model or `MigrationObject`. They are order-independent and parallel-safe — no cross-object lookups, foreign keys stay as CUCM name strings.

`RAW_DATA_MAPPING` is the routing table: `list[tuple[extractor_key, sub_key, normalizer_key]]` consumed by `normalize_discovery()`.

**Key normalizers:**
- `normalize_user` → `CanonicalUser`
- `normalize_phone` → `CanonicalDevice` (also triggers raw phone preservation — see below)
- `normalize_workspace` → `CanonicalWorkspace` (common-area phones classified post-normalization)
- `normalize_button_template` / `normalize_softkey_template` → `MigrationObject` (raw, for mapper consumption)
- Translation patterns, route patterns, CSSes, partitions, etc. → `MigrationObject`

**Raw phone preservation (critical):** `normalize_phone()` creates a `CanonicalDevice` but discards the raw AXL dict. `pipeline.py` also stores each phone as `MigrationObject(canonical_id="phone:{name}", pre_migration_state=<full_raw_phone>)`. This is required because `MonitoringMapper`, `CallForwardingMapper`, `DeviceLayoutMapper`, `DeviceMapper`, and `WorkspaceMapper` all call `store.get_objects("phone")` to access `speeddials`, `busyLampFields`, and per-line call forwarding that isn't on `CanonicalDevice`.

## Pass 2: CrossReferenceBuilder

`cross_reference.py:CrossReferenceBuilder.build()` sweeps the full normalized inventory to populate the `cross_refs` table. 32 relationships + 3 enrichments across 9 method groups:

| Method | Relationships |
|--------|--------------|
| `_build_device_pool_refs` | device_pool_has_datetime_group, datetime_group_to_timezone |
| `_build_user_refs` | user_in_location, user_has_line |
| `_build_device_dn_refs` | device_has_dn, dn_in_partition, line_uses_css |
| `_build_device_ownership_refs` | device_owner, device_in_location, common_area_device |
| `_build_css_partition_graph` | css_has_partition, partition_in_css |
| `_build_css_assignment_refs` | user_has_css, device_has_css |
| `_build_routing_refs` | gateway_to_route_group, route_group_to_route_list, etc. |
| `_build_feature_refs` | feature_has_agent, aa_has_schedule, pickup members |
| `_build_voicemail_refs` | user_has_voicemail_profile, unity_user |
| `_build_template_refs` | phone_uses_button_template, phone_uses_softkey_template |

**Note:** `device_pool_to_location` is NOT built here — it's written by `LocationMapper` during the map pass, because the mapping requires decisions about ambiguous device pool → location assignments.

## Mapper Execution Engine

`engine.py` runs all 22 mapper classes in dependency order (topological sort on `depends_on`). Each mapper reads from the store, produces canonical objects via `store.upsert_object()`, and returns a `MapperResult` with counts and decisions. See `mappers/CLAUDE.md` for the full mapper inventory.

## Analysis Pipeline

`analysis_pipeline.py:AnalysisPipeline.run(store)` runs all 13 analyzers, then advisory, then recommendations:

1. Run 13 analyzers (topological order by `depends_on`) → collect `Decision` objects
2. Convert decisions to store dicts → merge via `store.merge_decisions()` (fingerprint-based, marks stale)
3. Apply auto-resolution rules from config
4. Run `ArchitectureAdvisor` (Phase 2 — reads merged decisions, produces `ARCHITECTURE_ADVISORY` decisions)
5. Populate recommendations on all decisions

**13 Analyzers:**

| Analyzer | Decision Types |
|----------|---------------|
| `ExtensionConflictAnalyzer` | `EXTENSION_CONFLICT` |
| `DNAmbiguityAnalyzer` | `DN_AMBIGUITY` |
| `DeviceCompatibilityAnalyzer` | `DEVICE_INCOMPATIBLE`, `DEVICE_FIRMWARE_CONVERTIBLE`, `DEVICE_WEBEX_APP` (INFO — transitions to Webex App, no device migration) (DECT-tier devices skipped) |
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

**Cascade re-evaluation:** `resolve_and_cascade(store, decision_id, chosen_option)` resolves one decision and re-runs only the analyzers whose `decision_types` intersect `cascades_to` from the decision's context. Uses `save_decision()` (not `merge_decisions()`) in the cascade path to avoid incorrectly staling decisions from non-cascaded analyzers.

## Key Gotchas

- **Two-pass design is load-bearing.** Pass 1 normalizers must not query the store (they're pure functions). Pass 2 cross-refs depend on all Pass 1 objects being in the store. Mappers depend on cross_refs. Don't mix these layers.
- **Mapper `depends_on` is enforced.** The engine topologically sorts mappers before running them. If mapper B reads objects produced by mapper A, B must list A in `depends_on`.
- **Decision fingerprints are idempotent.** Fingerprint = SHA256(type + context). Re-running the pipeline doesn't create duplicate decisions — `merge_decisions()` updates existing ones and stales missing ones.
- **Multiple decisions per object are normal.** A device can be both `DEVICE_INCOMPATIBLE` and `MISSING_DATA`. Each has a unique fingerprint and is resolved independently.
- **`analyze` status ≠ all decisions resolved.** Objects at `status='analyzed'` may still have unresolved decisions if they're non-blocking (e.g., `FEATURE_APPROXIMATION`). Only objects with blocking decisions stay at `needs_decision`.
- **`productSpecificConfiguration` XML is model-specific and version-dependent.** Each phone model has different PSC fields. The DeviceSettingsMapper handles missing fields gracefully and only maps fields it recognizes.
