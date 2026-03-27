# Tier 2: Enterprise Migration Expansion

## Context

The CUCM-to-Webex migration pipeline (`src/wxcli/migration/`) has 11 completed phases covering 26 canonical types with 1507 tests passing. Tier 2 extends coverage to enterprise-grade CUCM features that large customers expect migrated. Many canonical types and extractors already exist — the main gaps are mappers, analyzers, and execution handlers.

**Pipeline architecture:**
```
raw_data (from cucm/) → Pass 1: normalizers → Pass 2: cross_refs → mappers → analyzers → decisions
```

**Read these files first:**
- `src/wxcli/migration/transform/CLAUDE.md` — three-pass pipeline architecture, mapper/analyzer contracts
- `src/wxcli/migration/transform/mappers/CLAUDE.md` — all 14 mappers, depends_on chains, patterns
- `src/wxcli/migration/cucm/CLAUDE.md` — extractor architecture, raw_data structure
- `src/wxcli/migration/execute/CLAUDE.md` — execution handler pattern, tier system
- `src/wxcli/migration/models.py` — all canonical types and enums
- `docs/plans/cucm-pipeline/future/expansion-scope.md` — the detailed spec for each item
- `docs/plans/cucm-pipeline/02b-cucm-extraction.md` — extraction patterns and AXL methods

## Scope: 8 Items in 3 Waves

### Wave 1 — Highest Value, Lowest Effort (1-2 sessions)

**§2.1 Call Forwarding** — SMALL
- `CanonicalCallForwarding` already exists in `models.py`
- `CallForwardingMapper` already exists at `src/wxcli/migration/transform/mappers/call_forwarding_mapper.py`
- `handle_call_forwarding_configure` execution handler already exists
- **Gap:** Verify end-to-end coverage. The data flows from `DeviceExtractor` (per-line forwarding in `getPhone` response → `lines.line[].callForwardAll/callForwardBusy/callForwardNoAnswer`) through normalizer → cross-ref → mapper → analyzer → handler. Check if an analyzer exists for lossy forwarding types (CUCM has ~10 types, Webex supports 3 core modes). If missing, add a `ForwardingLossyAnalyzer` that produces `FORWARDING_LOSSY` decisions for CUCM-only types.

**§2.5 Speed Dials + BLF/Monitoring** — SMALL
- `CanonicalMonitoringList` already exists
- `MonitoringMapper` already exists at `src/wxcli/migration/transform/mappers/monitoring_mapper.py`
- `handle_monitoring_list_configure` handler already exists
- **Gap:** Verify speed dial extraction. Raw phone `speeddials` array is preserved via `phone:{name}` MigrationObject. The `DeviceLayoutMapper` reads speed dials and places them in `CanonicalDeviceLayout`. Verify the full chain works for BLF → monitoring list conversion. Check if speed dials that can't map to Webex BLF produce decisions.

**§2.7 Remote Destinations / Single Number Reach (SNR)** — SMALL
- **New extractor needed:** `src/wxcli/migration/cucm/extractors/remote_destinations.py`
  - AXL: `listRemoteDestinationProfile` + `getRemoteDestinationProfile`
  - Returns: profile name, destinations (number, answerTooSoonTimer, answerTooLateTimer, delayBeforeRingingCell)
- **New canonical type:** `CanonicalRemoteDestination` in `models.py`
  - Fields: `user_canonical_id`, `destinations` (list of {number, timers}), `snr_enabled`
- **New normalizer** in `normalizers.py` + entry in `RAW_DATA_MAPPING`
- **New mapper:** `RemoteDestinationMapper` → maps CUCM timers to Webex SNR settings. Produces `SNR_LOSSY` decisions for CUCM timer controls that Webex doesn't support (Webex SNR is simpler — enable/disable + number, no fine-grained timers).
- **Execution:** Maps to `PUT /people/{id}/features/singleNumberReach` (person call settings)

### Wave 2 — Medium Effort (1-2 sessions)

**§2.2 Extension Mobility / Device Profiles** — MEDIUM
- **New extractor:** `src/wxcli/migration/cucm/extractors/extension_mobility.py`
  - AXL: `listDeviceProfile` + `getDeviceProfile`
  - Returns: profile name, lines, speed dials, associated users
- **New canonical type:** `CanonicalExtensionMobility` — maps to Webex hot desking config
- No direct Webex equivalent for the full EM feature — produces `FEATURE_GAP` decisions with advisory. Hot desking is the closest but loses profile-switching semantics.

**§2.6 E911 / ELIN Configuration** — SMALL-MEDIUM
- `CanonicalE911Config` may already exist in `models.py` — check
- **New extractor:** `src/wxcli/migration/cucm/extractors/e911.py`
  - AXL: ELIN groups, geographic locations
- Always produces `ARCHITECTURE_ADVISORY` decisions — E911 requires a separate workstream with RedSky/Intrado/bandwidth.com integration. The pipeline captures the CUCM config for the assessment report.

**§2.8 SIP/Security Profiles** — SMALL
- Fields already embed in `CanonicalTrunk` (TLS mode, early offer, SRTP)
- **Gap:** Expand `RoutingExtractor` to pull `sipProfile` and `securityProfile` details when processing SIP trunks via `getSipTrunk`. Currently only captures name — needs the profile contents for trunk type inference (TLS vs non-TLS, SRTP required vs optional).

### Wave 3 — Audio File Handling (1-2 sessions)

**§2.3 Music On Hold Sources** — MEDIUM
- **Expand `LocationExtractor`** to pull MOH source references from device pools
- **New canonical type:** `CanonicalMOHSource` — source type (file/streaming), file name, location assignment
- Audio file transfer is a separate problem (SFTP from CUCM MOH server, not via AXL)
- Produces `AUDIO_ASSET_MANUAL` decisions — "Transfer MOH audio files manually"

**§2.4 Announcements / Custom Audio** — MEDIUM-LARGE
- **New extractor** for announcement audio — may need Unity Connection CUPI client expansion
- **New canonical type:** `CanonicalAnnouncement` — greeting type, audio file reference, feature assignments
- Same `AUDIO_ASSET_MANUAL` decision pattern as MOH
- Complexity: multiple audio format conversions may be needed (G.711 → WAV)

## Shared Infrastructure Needed

For all waves:
1. **New DecisionTypes** (add to `models.py` enum): `FORWARDING_LOSSY`, `SNR_LOSSY`, `AUDIO_ASSET_MANUAL` (if not already present — check first)
2. **New recommendation rules** in `src/wxcli/migration/advisory/` for each new decision type
3. **New advisory patterns** for cross-cutting concerns (e.g., "audio asset migration requires manual transfer")
4. **Report expansion** — new appendix sections for each new data type (add `<details>` sections to `src/wxcli/migration/report/appendix.py`)

## Implementation Pattern

For each new object type, follow this exact sequence:

1. **Extractor** (if new AXL data needed): inherit `BaseExtractor`, implement `extract()`, register in `discovery.py`'s `EXTRACTOR_ORDER`
2. **Canonical type** in `models.py`: inherit `MigrationObject`, define fields
3. **Normalizer** in `normalizers.py`: pure function, add to `NORMALIZER_REGISTRY` + `RAW_DATA_MAPPING`
4. **Cross-references** in `cross_reference.py`: add relationships in appropriate `_build_*_refs` method
5. **Mapper** in `mappers/`: inherit `Mapper`, set `depends_on`, implement `map(store) -> MapperResult`
6. **Analyzer** in `analyzers/`: inherit `Analyzer`, set `decision_types`, implement `analyze(store) -> list[Decision]`
7. **Execution handler** in `execute/handlers.py`: pure function `(data, deps, ctx) -> HandlerResult`
8. **Planner expander** in `execute/planner.py`: `_expand_*()` function + `_EXPANDERS` entry
9. **Tests** at each layer: extractor tests, normalizer tests, mapper tests, analyzer tests, handler tests

## Verification

After each wave:
```bash
python3.11 -m pytest tests/migration/ -x -q  # All tests pass
wxcli cucm normalize --verbose  # New types appear in counts
wxcli cucm map --verbose  # New mappers execute
wxcli cucm analyze --verbose  # New analyzers produce decisions
```

## What NOT to Do

- Don't modify existing normalizers/mappers unless fixing a bug — add new ones alongside
- Don't skip the cross-reference step — mappers depend on cross_refs for foreign key resolution
- Don't make normalizers query the store — Pass 1 is pure functions only
- Don't add execution handlers without planner expanders — orphaned handlers never execute
- Don't forget `depends_on` on new mappers — the engine enforces topological sort
