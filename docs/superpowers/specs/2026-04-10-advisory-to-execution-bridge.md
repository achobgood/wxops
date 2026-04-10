# Advisory-to-Execution Bridge: 5 Canonical Types

**Status:** Spec  
**Date:** 2026-04-10  
**Scope:** Planner expanders, handlers, engine changes for music_on_hold, announcement, e911_config, device_profile, location_schedule

---

## Problem

Five canonical object types are mapped by the transform layer but are dead ends in the execution layer. Their mappers produce objects in the SQLite store, their analyzers create decisions, and the assessment report displays them — but when `expand_to_operations(store)` runs, these types have **no entry in `_EXPANDERS`**, produce **no `MigrationOp` nodes**, and therefore **never generate API calls**.

The planner logs a warning for each: `No expansion pattern for object type 'X' (id=Y)`.

This creates a false sense of coverage. An operator reviewing the deployment plan sees 0 operations for these types and assumes they were intentionally excluded. In reality, they were never wired up.

### Current state

| Canonical type | Mapper | Model | Planner expander | Handler | Status |
|---|---|---|---|---|---|
| `music_on_hold` | `MOHMapper` | `CanonicalMusicOnHold` | None | None | Advisory only |
| `announcement` | `AnnouncementMapper` | `CanonicalAnnouncement` | None | None | Advisory only |
| `e911_config` | `E911Mapper` | `CanonicalE911Config` | None | None | Advisory only |
| `device_profile` | `DeviceProfileMapper` | `CanonicalDeviceProfile` | None | None | Advisory only |
| `location_schedule` | `FeatureMapper._map_location_schedules` | `CanonicalLocationSchedule` | None (but `schedule` type HAS an expander) | None | Advisory only |

### What exists vs. what is missing

The `_EXPANDERS` dict in `planner.py` (lines 526-552) has 24 entries. None of the 5 types above appear. The `HANDLER_REGISTRY` in `handlers.py` (lines 955-990) has 31 entries. None of the 5 types above appear. The `TIER_ASSIGNMENTS` dict in `__init__.py` (lines 75-119) has entries for 35 `(resource_type, op_type)` pairs. None of the 5 types above appear.

**Note on `location_schedule` vs `schedule`:** The planner already handles `schedule` (canonical_id prefix `schedule:`) via `_expand_schedule` and `handle_schedule_create`. The `location_schedule` type (canonical_id prefix also `schedule:`) uses the same prefix — this means CanonicalLocationSchedule objects produced by FeatureMapper ARE already picked up by the existing `schedule` expander. This type is NOT actually a dead end; it piggybacks on the existing schedule infrastructure. We will verify this during implementation and remove it from scope if confirmed.

---

## Shared Pattern

All 5 types (potentially 4, pending location_schedule verification) follow the same wiring pattern documented in `execute/CLAUDE.md` under "Adding a New Handler":

1. **Expander function** in `planner.py`: `_expand_<type>(obj_data)` returns `list[MigrationOp]`
2. **Entry in `_EXPANDERS`**: `"<type>": lambda obj, _: _expand_<type>(obj)`
3. **Handler function** in `handlers.py`: `handle_<type>_<op>(data, deps, ctx)` returns `HandlerResult`
4. **Entry in `HANDLER_REGISTRY`**: `("<type>", "<op>"): handle_<type>_<op>`
5. **Tier assignment** in `__init__.py`: `("<type>", "<op>"): N`
6. **API call estimate** in `__init__.py`: `"<type>:<op>": N`
7. **Cross-object dependency rules** in `dependency.py` (if the type has dependencies)
8. **Tests** in `tests/migration/execute/test_handlers.py`

The pattern is mechanical. The complexity is in the API details per type.

---

## Engine Limitation: Multipart Upload

Two of the 5 types (music_on_hold and announcement) require `multipart/form-data` uploads when custom audio files are involved. The current engine (`engine.py`) exclusively uses `session.request(method, url, json=body)` — it always sends JSON bodies. There is no code path for multipart form data.

### Impact

- **Music on Hold** with `greeting: "CUSTOM"` requires an audio file reference. The PUT body accepts an `audioFile.id` field that references a previously-uploaded announcement. The location MoH endpoint itself is JSON (`PUT /telephony/config/locations/{locationId}/musicOnHold`), but the audio file must already exist in the announcement repository.
- **Announcement upload** is inherently multipart: `POST /telephony/config/locations/{locationId}/announcements` requires `multipart/form-data` with a `name` field and a binary `file` field.

### Design decision: Phase this work

**Phase A (this spec):** Wire up the planner expanders and handlers for all 5 types using JSON-only API calls. For MoH, the handler sets `greeting: "SYSTEM"` (default) or references an existing `audioFile.id` if one is provided. For announcements, the handler is a **no-op placeholder** that marks the operation as needing manual upload — the decision was already `AUDIO_ASSET_MANUAL`.

**Phase B (future spec):** Add multipart upload support to the engine. This requires:
- `aiohttp.FormData` construction in `execute_single_op`
- A new handler return type or flag indicating multipart (e.g., a 4th tuple element)
- File path resolution from the canonical object (the CUCM audio file would need to be pre-downloaded to a staging directory)
- `cucm-collect` script integration (the standalone collector script, not yet built)

Phase B is explicitly out of scope for this spec. The advisory decisions (`AUDIO_ASSET_MANUAL`) remain the mechanism for custom audio — the operator must manually download from CUCM and upload to Webex.

---

## Per-Type Design

### 1. music_on_hold

**Mapper output:** `CanonicalMusicOnHold` with fields: `source_name`, `source_file_name`, `is_default`, `cucm_source_id`, `location_canonical_id` (currently None — see below).

**Problem with current mapper:** `MOHMapper` does not set `location_canonical_id`. CUCM MOH audio sources are org-wide, not per-location. But Webex MoH settings are per-location. The mapper needs to be updated to associate MOH sources with locations (via device pool cross-refs or a blanket "apply to all locations" strategy).

**Webex API:**
```
PUT /telephony/config/locations/{locationId}/musicOnHold
Body: {
  "callHoldEnabled": true,
  "callParkEnabled": true,
  "greeting": "SYSTEM" | "CUSTOM",
  "audioFile": { "id": "<announcement_id>" }  // only if CUSTOM
}
```

**Execution strategy:**
- Default MOH sources: One `configure` op per location, setting `greeting: "SYSTEM"`, `callHoldEnabled: true`, `callParkEnabled: true`. This is a confirmation that defaults are acceptable.
- Custom MOH sources: Same op but with `greeting: "CUSTOM"` and `audioFile.id` populated only if the operator has already uploaded the audio and provided the announcement ID via decision resolution. If no ID available, fall back to `greeting: "SYSTEM"` and log a warning.

**Planner:**
```python
_expand_music_on_hold(obj) -> [MigrationOp(
    canonical_id=cid, op_type="configure", resource_type="music_on_hold",
    tier=5, batch=location_id, description="Configure MoH for location X"
)]
```

**Handler:**
```python
handle_music_on_hold_configure(data, deps, ctx) -> [
    ("PUT", _url(f"/telephony/config/locations/{loc_wid}/musicOnHold", ctx), body)
]
```

**Tier:** 5 (settings configuration — depends on location existing + calling enabled)  
**API calls:** 1  
**Dependencies:** location:enable_calling (REQUIRES)  
**Mapper change needed:** Set `location_canonical_id` or produce one object per location.

---

### 2. announcement

**Mapper output:** `CanonicalAnnouncement` with fields: `name`, `file_name`, `media_type`, `source_system`, `location_canonical_id` (currently None), `associated_feature_canonical_id` (currently None).

**Webex API:**
```
POST /telephony/config/locations/{locationId}/announcements
Content-Type: multipart/form-data
Fields: name (string), file (binary WAV)
Response: { "id": "..." }
```

**Execution strategy (Phase A):** The handler returns `[]` (no-op). The announcement mapper already creates `AUDIO_ASSET_MANUAL` decisions for every announcement. These decisions instruct the operator to manually download audio from CUCM and upload to Webex. The planner still creates an op so it appears in the deployment plan as "pending manual upload," but the handler produces no API calls.

When Phase B adds multipart support AND `cucm-collect` pre-downloads the audio files, the handler will be upgraded to actually POST the file.

**Planner:**
```python
_expand_announcement(obj) -> [MigrationOp(
    canonical_id=cid, op_type="upload", resource_type="announcement",
    tier=1, batch=location_id, description="Upload announcement 'X' (manual)"
)]
```

**Handler:**
```python
handle_announcement_upload(data, deps, ctx) -> []  # Phase A: no-op, manual upload required
```

**Tier:** 1 (routing backbone — announcements must exist before features that reference them)  
**API calls:** 0 (Phase A: manual); 1 (Phase B: multipart upload)  
**Dependencies:** location:enable_calling (REQUIRES)  
**Mapper change needed:** Set `location_canonical_id` from feature cross-refs.  
**Open question:** Should we use tier 1 or tier 4? Announcements are referenced by AAs and CQs (tier 4). If the announcement doesn't exist when the AA is created, the AA create just omits the greeting reference — it's not a hard failure. Tier 1 is safer for future Phase B when uploads actually happen.

---

### 3. e911_config

**Mapper output:** `CanonicalE911Config` with fields: `elin_group_name`, `elin_numbers`, `geo_location_name`, `geo_country`, `has_emergency_route_pattern`, `location_canonical_id` (currently None).

**Architectural note:** CUCM E911 (ELIN-based) and Webex E911 (RedSky civic addresses + ECBN) are fundamentally different systems. There is no automated 1:1 mapping. The E911Mapper already creates `ARCHITECTURE_ADVISORY` decisions flagging this as a separate workstream.

**Webex APIs (two concerns):**
1. **Per-person ECBN:** `PUT /telephony/config/people/{personId}/emergencyCallbackNumber` with body `{"selected": "DIRECT_LINE" | "LOCATION_MEMBER_NUMBER", "locationMemberId": "..."}`. This sets which number is used for the person's 911 callback.
2. **Location emergency settings:** RedSky building addresses via `PUT /telephony/config/locations/{locationId}/e911` — but this requires a separate RedSky account and is genuinely a different workstream.

**Execution strategy:** The handler produces a **no-op** for the e911_config object itself (the architectural advisory stands). However, we add a new concern: during `user:configure_settings`, the handler should check if the user has an ECBN override and apply it. This is NOT a new handler for e911_config — it's an enhancement to the existing `handle_user_configure_settings`.

**Planner:** Add `e911_config` to `_DATA_ONLY_TYPES` instead of creating an expander. The e911_config objects exist for the report and advisory system. The actual ECBN configuration is folded into user settings.

```python
_DATA_ONLY_TYPES = {
    "line": "...",
    "voicemail_profile": "...",
    "e911_config": "Advisory only — ECBN handled via user:configure_settings, RedSky is a separate workstream",
}
```

**Tier:** N/A (data-only)  
**API calls:** 0 (e911_config itself); ECBN is 1 additional call per user within user:configure_settings  
**Dependencies:** N/A  
**Mapper change needed:** None for this spec. ECBN per-user enrichment is a separate concern for the UserMapper or an analyzer.

---

### 4. device_profile

**Mapper output:** `CanonicalDeviceProfile` with fields: `profile_name`, `user_canonical_id`, `model`, `protocol`, `lines`, `device_pool_name`, `speed_dial_count`, `blf_count`.

**Webex APIs (two levels):**
1. **Hoteling (device-level):** `PUT /telephony/config/people/{personId}/devices/settings/hoteling` with body `{"hoteling": {"enabled": true, "limitGuestUse": true, "guestHoursLimit": N}}`. This enables hoteling login on the person's primary device.
2. **Hot Desking (location-level):** `PUT /telephony/config/locations/{locationId}/features/hotDesking` with body `{"voicePortalHotDeskSignInEnabled": true}`. Enables voice portal hot desk sign-in for the location.
3. **Hot Desking (person-level):** `PUT /telephony/config/people/{personId}/features/hotDesking/guest` with body `{"voicePortalHotDeskSignInEnabled": true}`. Per-user hot desking guest settings.

**Execution strategy:** The device_profile mapper already creates `FEATURE_APPROXIMATION` decisions when profiles have multi-line, speed dials, or BLFs that Webex hot desking cannot replicate. The decision options are: "Enable hot desking" (accept), "Don't enable" (skip), or "Manual" (admin configures).

For profiles where the decision is "accept":
- Produce a `configure` op that enables hoteling on the user's primary device
- The handler calls `PUT /telephony/config/people/{personId}/devices/settings/hoteling`

For simple profiles (no multi-line/extras) that have no decision: produce the configure op by default.

**Planner:**
```python
_expand_device_profile(obj, decisions) -> [MigrationOp(
    canonical_id=cid, op_type="configure", resource_type="device_profile",
    tier=5, batch=location_from_user, description="Enable hoteling for user X"
)]
# Returns [] if user_canonical_id is None (orphan profile)
# Returns [] if FEATURE_APPROXIMATION decision resolved as "skip"
```

**Handler:**
```python
handle_device_profile_configure(data, deps, ctx) -> [
    ("PUT", _url(f"/telephony/config/people/{person_wid}/devices/settings/hoteling", ctx),
     {"hoteling": {"enabled": True}})
]
```

**Tier:** 5 (settings — depends on user being created + licensed)  
**API calls:** 1  
**Dependencies:** user:create (REQUIRES) via user_canonical_id  
**Mapper change needed:** None. The mapper already populates `user_canonical_id`.  
**Cross-object rule needed:**
```python
{
    "source_type": "device_profile",
    "source_op": "configure",
    "relationship": "user_has_device_profile",
    "target_op": "create",
    "dep_type": DependencyType.REQUIRES,
}
```

---

### 5. location_schedule (Verification Required)

**Mapper output:** `CanonicalLocationSchedule` with fields: `name`, `schedule_type`, `location_id`, `events`, `operating_mode_canonical_id`. Canonical ID prefix: `schedule:` (from `f"schedule:{hash_id(om_cid)}"`).

**Key finding:** The `CanonicalLocationSchedule` uses canonical_id prefix `schedule:`, which is the SAME prefix used by `CanonicalSchedule` objects from `RoutingMapper`. The planner's `_expand_schedule` expander checks `obj_type = cid.split(":")[0]` — both resolve to `"schedule"`. The existing `handle_schedule_create` handler produces:
```python
("POST", _url(f"/telephony/config/locations/{loc_wid}/schedules", ctx), body)
```

This means CanonicalLocationSchedule objects produced by FeatureMapper **should already be picked up** by the existing schedule expander and handler. Both have `name`, `schedule_type`, `location_id`, and `events` fields.

**Verification task:** Confirm in a test that CanonicalLocationSchedule objects flow through `expand_to_operations` via the existing `_expand_schedule` path. If confirmed, this type needs NO new code — just a test proving it works.

**If verification fails** (e.g., field name mismatches, missing location_id resolution):
- Add field normalization in the expander
- Add a dedicated `_expand_location_schedule` if the existing one cannot handle both shapes

**Tier:** 1 (same as existing schedule)  
**API calls:** 1  
**Dependencies:** Same as existing schedule (location:enable_calling via schedule_in_location cross-ref)  
**Mapper change needed:** None expected. Verify `location_id` is set correctly.

---

## Summary of Changes

### Files to modify

| File | Changes |
|---|---|
| `src/wxcli/migration/execute/planner.py` | Add `_expand_music_on_hold`, `_expand_announcement`, `_expand_device_profile` to `_EXPANDERS`. Add `e911_config` to `_DATA_ONLY_TYPES`. |
| `src/wxcli/migration/execute/handlers.py` | Add `handle_music_on_hold_configure`, `handle_announcement_upload`, `handle_device_profile_configure` to `HANDLER_REGISTRY`. |
| `src/wxcli/migration/execute/__init__.py` | Add tier assignments and API call estimates for 3 new types. |
| `src/wxcli/migration/execute/dependency.py` | Add cross-object rules: `music_on_hold` depends on `location:enable_calling`, `announcement` depends on `location:enable_calling`, `device_profile` depends on `user:create`. |
| `src/wxcli/migration/transform/mappers/moh_mapper.py` | Set `location_canonical_id` on produced objects (or produce one per location). |
| `src/wxcli/migration/execute/CLAUDE.md` | Document new handlers in the Handler Inventory. |
| `src/wxcli/migration/execute/planner.py` docstring/comments | Update _DATA_ONLY_TYPES comment. |

### Files to create

None. All changes are modifications to existing files.

### Files requiring tests

| Test file | Coverage |
|---|---|
| `tests/migration/execute/test_handlers.py` | Handler unit tests for `handle_music_on_hold_configure`, `handle_announcement_upload`, `handle_device_profile_configure`. |
| `tests/migration/execute/test_planner.py` | Verify `expand_to_operations` produces ops for music_on_hold, announcement, device_profile. Verify e911_config is skipped as data-only. Verify location_schedule flows through existing schedule expander. |

---

## Tier Assignment Summary

| Type | Op | Tier | API Calls | Rationale |
|---|---|---|---|---|
| `music_on_hold` | `configure` | 5 | 1 | Settings tier — location must exist and have calling enabled |
| `announcement` | `upload` | 1 | 0 (Phase A) | Routing backbone — announcements needed before features. No-op until multipart support. |
| `e911_config` | (data-only) | N/A | 0 | Advisory only. ECBN is part of user:configure_settings. |
| `device_profile` | `configure` | 5 | 1 | Settings tier — user must exist and be licensed |
| `location_schedule` | (existing `schedule:create`) | 1 | 1 | Already handled — verification only |

---

## Dependency Edges

### New cross-object rules for `dependency.py`

```python
# Music on hold depends on location having Calling enabled
{
    "source_type": "music_on_hold",
    "source_op": "configure",
    "relationship": "moh_in_location",
    "target_op": "enable_calling",
    "dep_type": DependencyType.REQUIRES,
},
# Announcement depends on location having Calling enabled
{
    "source_type": "announcement",
    "source_op": "upload",
    "relationship": "announcement_in_location",
    "target_op": "enable_calling",
    "dep_type": DependencyType.REQUIRES,
},
# Device profile hoteling depends on owner user being created
{
    "source_type": "device_profile",
    "source_op": "configure",
    "relationship": "user_has_device_profile",
    "target_op": "create",
    "dep_type": DependencyType.REQUIRES,
},
```

### New cross-ref relationships needed

| Relationship | Source | Target | Where built |
|---|---|---|---|
| `moh_in_location` | `music_on_hold:X` | `location:Y` | MOHMapper (after location_canonical_id is set) |
| `announcement_in_location` | `announcement:X` | `location:Y` | AnnouncementMapper (after location_canonical_id is set) |
| `user_has_device_profile` | `user:X` | `device_profile:Y` | Already built by DeviceProfileMapper (line 90) |

**Note:** `user_has_device_profile` cross-ref is already built by `DeviceProfileMapper._find_profile_owner` (line 90: `store.add_cross_ref(user_cid, dp.canonical_id, "user_has_device_profile")`). The dependency rule references it correctly — the direction is source=device_profile, target=user, matching the cross-ref from user to device_profile.

Wait — the cross-ref is `add_cross_ref(user_cid, dp.canonical_id, "user_has_device_profile")` which means source=user, target=device_profile. The dependency engine walks from source_type (device_profile) and looks up cross-refs where the device_profile canonical_id appears. We need to verify the direction: `find_cross_refs(device_profile_cid, "user_has_device_profile")` should return the user. If the cross-ref is stored as (user, device_profile), the lookup direction may need to be reversed. This is an implementation detail to resolve during coding.

---

## Open Questions

1. **MOH per-location association:** CUCM MOH audio sources are org-wide. How should they map to per-location Webex MoH settings? Options:
   - (a) Produce one music_on_hold configure op per location, all pointing to the same source
   - (b) Only produce ops for locations that have devices referencing non-default MOH
   - **Recommendation:** Option (a) for default sources, option (b) for custom sources

2. **Announcement location resolution:** Announcements in CUCM are org-wide. How to determine which Webex location(s) they belong to? Options:
   - (a) Use the location of the feature (AA/CQ) that references the announcement
   - (b) Upload to all locations
   - **Recommendation:** Option (a) — use the `associated_feature_canonical_id` to look up the feature's location

3. **location_schedule verification:** Does the existing schedule expander correctly handle CanonicalLocationSchedule objects? This must be verified with a test before deciding whether new code is needed.

4. **Cross-ref direction for device_profile:** The dependency engine needs to resolve user_canonical_id from a device_profile's cross-refs. Verify that `find_cross_refs` handles the stored direction correctly.

---

## Test Strategy

### Unit tests (per handler)

1. **test_handle_music_on_hold_configure_default** — Default MOH source produces PUT with `greeting: "SYSTEM"`
2. **test_handle_music_on_hold_configure_custom_with_id** — Custom source with audioFile.id produces PUT with `greeting: "CUSTOM"` and audioFile reference
3. **test_handle_music_on_hold_configure_custom_no_id** — Custom source without audioFile.id falls back to `greeting: "SYSTEM"` with warning
4. **test_handle_announcement_upload_noop** — Returns `[]` (Phase A no-op)
5. **test_handle_device_profile_configure** — Produces PUT hoteling with `enabled: true`
6. **test_handle_device_profile_configure_no_user** — Returns `[]` when user_canonical_id is None
7. **test_handle_device_profile_configure_skip_decision** — Planner returns `[]` when FEATURE_APPROXIMATION decision is "skip"

### Integration tests (planner)

8. **test_expand_music_on_hold** — Store with CanonicalMusicOnHold produces 1 configure op at tier 5
9. **test_expand_announcement** — Store with CanonicalAnnouncement produces 1 upload op at tier 1
10. **test_expand_device_profile** — Store with CanonicalDeviceProfile produces 1 configure op at tier 5
11. **test_e911_config_is_data_only** — Store with CanonicalE911Config produces 0 ops (data-only)
12. **test_location_schedule_uses_existing_schedule_expander** — Store with CanonicalLocationSchedule flows through `_expand_schedule` and produces 1 create op at tier 1

### Registry completeness test

13. **test_handler_registry_covers_tier_assignments** — Every `(resource_type, op_type)` in `TIER_ASSIGNMENTS` (except `calling_permission:create` which has 0 API calls) has a corresponding entry in `HANDLER_REGISTRY`. This test already exists — verify it passes after adding new entries.

---

## Implementation Order

1. **Verify location_schedule** (test only — no code if it works)
2. **Add e911_config to _DATA_ONLY_TYPES** (smallest change, immediate value)
3. **Wire up device_profile** (clearest 1:1 mapping, no multipart concerns)
4. **Wire up music_on_hold** (requires mapper change for location association)
5. **Wire up announcement** (no-op handler, but needs mapper change for location)
6. **Update CLAUDE.md** docs
7. **Run full test suite** to verify no regressions

Estimated effort: 4-6 hours for all 5 types including tests and doc updates.

---

## Documentation Updates Required

| File | Update needed |
|---|---|
| `src/wxcli/migration/execute/CLAUDE.md` | Add music_on_hold, announcement, device_profile to Handler Inventory tables. Update Tier System table. Update "Adding a New Handler" section if the pattern has changed. |
| `src/wxcli/migration/execute/__init__.py` | Inline comments for new TIER_ASSIGNMENTS and API_CALL_ESTIMATES entries. |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Note that MOHMapper and AnnouncementMapper now set location_canonical_id for execution wiring. |
| `src/wxcli/migration/CLAUDE.md` | Update "Migration Operator Runbooks" or pipeline summary if the 5 types change the operator workflow. |
| `CLAUDE.md` (root) | No change needed — the file map already lists all mappers. |
| `docs/runbooks/cucm-migration/decision-guide.md` | Update AUDIO_ASSET_MANUAL and ARCHITECTURE_ADVISORY entries to note that Phase A produces no-op ops (announcements) and data-only handling (e911). |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| MOH mapper produces objects without location_canonical_id | Handler cannot resolve location Webex ID | Mapper change is prerequisite — fail the handler with `[]` if no location |
| Announcement multipart upload deferred to Phase B | Custom audio still requires manual upload | AUDIO_ASSET_MANUAL decisions already communicate this to operators |
| E911 is a genuinely separate workstream | Operators may expect automated E911 setup | ARCHITECTURE_ADVISORY decision already communicates this; adding e911_config to DATA_ONLY_TYPES makes the intent explicit |
| Cross-ref direction mismatch for device_profile | Dependency engine can't find user from device_profile | Verify during implementation; add reverse cross-ref if needed |
| location_schedule already works via schedule prefix | Adding a second expander would create duplicate ops | Verify before coding; test proves no new code needed |
