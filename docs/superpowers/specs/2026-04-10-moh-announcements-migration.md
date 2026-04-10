# Music on Hold and Announcement Audio Migration

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM migration pipeline -- MoH audio sources, CUCM announcements, per-feature audio assignments

---

## 1. Problem Statement

Custom Music on Hold (MoH) and call feature announcements are not surfaced prominently in the migration assessment or communicated as action items. The pipeline already detects them (MOH extractor, Announcement extractor, MOH mapper, Announcement mapper) and creates `AUDIO_ASSET_MANUAL` decisions, but three critical gaps remain:

1. **No advisory pattern** flags the aggregate MoH/announcement situation. Individual `AUDIO_ASSET_MANUAL` decisions exist per source/announcement, but there is no cross-cutting advisory that summarizes "you have N custom audio assets requiring manual migration" with a concrete action plan.

2. **No report section** surfaces audio assets. The assessment report has an Appendix H (Voicemail Analysis) but no equivalent for MoH sources or announcements. Custom MoH is high-visibility -- every external caller to every queue and every user placed on hold hears it. Companies spend thousands on professional recordings. Losing custom MoH on migration day is a P1 experience issue.

3. **No per-feature audio cross-referencing.** CUCM hunt pilots reference `networkHoldMohAudioSourceID`, and Auto Attendants reference announcements for greetings. The feature mapper detects `networkHoldMohAudioSourceID` presence (line 422 of `feature_mapper.py`) but doesn't track which MoH source is assigned to which feature. The assessment should tell the admin "these 4 call queues use custom MoH source 'Corporate_Hold_Music'" so they know where to re-assign after upload.

### Business Impact

- **MoH:** Every external caller hears hold music. Default Cisco music is instantly recognizable and signals "cheap." Enterprise customers pay for branded hold music and will reject a migration that reverts to default.
- **AA/CQ Announcements:** Auto Attendant greetings ("Thank you for calling Acme Corp...") and Call Queue comfort messages are customer-facing. Re-recording requires booking voice talent, which has lead time.
- **Scale:** A typical 500-user CUCM deployment has 3-8 custom MoH sources and 10-30 announcements. A 2000-user deployment can have 50+ announcements across locations.

---

## 2. Current State (What Already Exists)

### 2.1 Extraction Layer

| Component | File | Status |
|-----------|------|--------|
| MoH Extractor | `src/wxcli/migration/cucm/extractors/moh.py` | Built. Uses `listMohAudioSource` / `getMohAudioSource`. Extracts name, sourceFileName, isDefault, sourceId. |
| Announcement Extractor | `src/wxcli/migration/cucm/extractors/announcements.py` | Built. Uses `listAnnouncement` / `getAnnouncement`. Extracts name, description, announcementFile. |

### 2.2 Normalization Layer

| Component | File | Status |
|-----------|------|--------|
| MoH normalizer | `normalizers.py` line ~1480 | Built. Produces `moh_source` objects. |
| Announcement normalizer | `normalizers.py` line ~1490 | Built. Produces `announcement` objects. |

### 2.3 Mapper Layer

| Component | File | Status |
|-----------|------|--------|
| MOHMapper | `transform/mappers/moh_mapper.py` | Built. Creates `CanonicalMusicOnHold` per source. Custom sources get `AUDIO_ASSET_MANUAL` decision. |
| AnnouncementMapper | `transform/mappers/announcement_mapper.py` | Built. Creates `CanonicalAnnouncement` per announcement. Every announcement gets `AUDIO_ASSET_MANUAL` decision. |

### 2.4 Models

| Model | File | Status |
|-------|------|--------|
| `CanonicalMusicOnHold` | `models.py:583` | Built. Fields: location_canonical_id, source_name, source_file_name, is_default, cucm_source_id. |
| `CanonicalAnnouncement` | `models.py:592` | Built. Fields: name, location_canonical_id, file_name, media_type, source_system, usage, associated_feature_canonical_id. |
| `DecisionType.AUDIO_ASSET_MANUAL` | `models.py:95` | Built. |

### 2.5 Advisory Layer

| Component | Status |
|-----------|--------|
| Per-decision recommendation for `AUDIO_ASSET_MANUAL` | **NOT BUILT.** No function in `recommendation_rules.py`. |
| Cross-cutting advisory pattern for audio assets | **NOT BUILT.** No pattern in `advisory_patterns.py`. |
| Media resource scope removal (Pattern 15) | Built. Mentions MoH servers in passing but doesn't address custom audio files. |

### 2.6 Report Layer

| Component | Status |
|-----------|--------|
| Explainer for `AUDIO_ASSET_MANUAL` | Built. `explainer.py:490` maps to "Audio Asset Migration". |
| Appendix section for audio assets | **NOT BUILT.** No MoH or announcement appendix. |
| Executive summary audio mention | **NOT BUILT.** Audio assets not counted in executive summary. |

### 2.7 Webex Target APIs (Reference)

| API | Endpoint | Purpose |
|-----|----------|---------|
| Location MoH settings | `PUT /telephony/config/locations/{id}/musicOnHold` | Set greeting to CUSTOM, reference uploaded announcement file ID |
| Person MoH settings | `PUT /telephony/config/people/{id}/musicOnHold` | Per-person MoH override |
| Announcement upload (org) | `POST /telephony/config/announcements` | Upload WAV to org-level repo (multipart/form-data) |
| Announcement upload (location) | `POST /telephony/config/locations/{id}/announcements` | Upload WAV to location-level repo |
| Playlist create | `POST /telephony/config/announcements/playlists` | Create playlist from announcement IDs (max 25) |
| Playlist assign locations | `PUT /telephony/config/announcements/playlists/{id}/locations` | Assign playlist as location MoH |
| Person greeting upload (busy) | `POST /people/{id}/features/voicemail/actions/uploadBusyGreeting/invoke` | Upload busy greeting WAV (admin path exists) |
| Person greeting upload (no-answer) | `POST /people/{id}/features/voicemail/actions/uploadNoAnswerGreeting/invoke` | Upload no-answer greeting WAV (admin path exists) |

**Key constraint:** Webex accepts WAV files up to 5 MB for voicemail greetings and 8 MB for announcements. CUCM MoH sources can be larger. The upload is multipart/form-data with `audio/wav` content type.

---

## 3. Proposed Changes

### 3.1 New Advisory Pattern: `detect_custom_audio_assets`

**File:** `src/wxcli/migration/advisory/advisory_patterns.py`

Add Pattern 27 to `ALL_ADVISORY_PATTERNS`. This pattern aggregates all `AUDIO_ASSET_MANUAL` decisions plus all custom MoH sources and announcements to produce a single cross-cutting advisory.

**Logic:**
1. Count custom MoH sources (where `is_default == False`) from `store.get_objects("music_on_hold")`
2. Count announcements from `store.get_objects("announcement")`
3. Count `AUDIO_ASSET_MANUAL` decisions from `store.get_all_decisions()`
4. If total custom audio assets > 0, produce an `AdvisoryFinding`

**Severity mapping:**
- 1-5 custom assets: `MEDIUM`
- 6-20 custom assets: `HIGH`
- 21+ custom assets: `CRITICAL`

**Category:** `"migrate_as_is"` (the assets must be migrated, they just need manual handling)

**Detail template:**
```
This environment has {N} custom audio assets requiring manual migration:
- {moh_count} custom Music on Hold source(s)
- {ann_count} announcement file(s)

CUCM audio files cannot be automatically transferred to Webex. Each must be:
1. Downloaded from CUCM server filesystem (SFTP to /usr/local/cm/tftp/)
2. Converted to WAV format if needed (Webex requires WAV, max 8 MB)
3. Uploaded to Webex announcement repository via API or Control Hub
4. Assigned to the appropriate location (MoH) or feature (AA/CQ greeting)

Action required BEFORE migration day: Download all custom audio files from
CUCM and have them ready for upload. MoH and AA greetings are customer-facing
-- losing them on cutover day is a P1 experience issue.
```

### 3.2 New Recommendation Rule: `recommend_audio_asset_manual`

**File:** `src/wxcli/migration/advisory/recommendation_rules.py`

Add a recommendation function for `AUDIO_ASSET_MANUAL` decisions.

**Logic:**
- If context contains `advisory_type == "audio_asset_manual"` (announcement): recommend `"accept"` with reasoning about downloading from CUCM and uploading to Webex announcement repo.
- If context contains `moh_source_name` (MoH source): recommend `"accept"` with reasoning about downloading from CUCM TFTP and uploading to Webex location MoH.
- Never recommend `"use_default"` -- custom audio was intentional.

### 3.3 Feature-to-Audio Cross-Reference

**File:** `src/wxcli/migration/transform/cross_reference.py`

Add a new cross-reference relationship: `feature_uses_moh_source`

**Logic in `CrossReferenceBuilder`:**
- For each hunt pilot / call queue in the store, check `networkHoldMohAudioSourceID`
- If present, resolve to the `moh_source` canonical_id and write a cross-ref
- This enables the report to show "Call Queue 'Sales' uses MoH source 'Corporate_Hold_Music'"

Also add: `feature_uses_announcement`
- For each Auto Attendant, check for announcement references in greeting config
- Write cross-ref linking AA to announcement canonical_id

### 3.4 Report Appendix: Audio Assets Section

**File:** `src/wxcli/migration/report/appendix.py`

Add a new appendix section (insert as section I, after H. Voicemail Analysis):

**Content:**
- Table of MoH sources: name, file name, is_default, locations using it (via cross-ref)
- Table of announcements: name, file name, media type, features referencing it
- Summary count: "N custom audio assets requiring manual migration"
- Migration checklist callout: "Download these files from CUCM before migration day"

### 3.5 Report Executive Summary: Audio Asset Count

**File:** `src/wxcli/migration/report/executive.py`

Add audio asset counts to the environment inventory section. Something like:
- "Custom MoH Sources: 3 (requires manual upload)"
- "Announcement Files: 12 (requires manual upload)"

### 3.6 Explainer Enhancement

**File:** `src/wxcli/migration/report/explainer.py`

The current explainer for `AUDIO_ASSET_MANUAL` just maps to the string "Audio Asset Migration". Enhance with a proper explanation function similar to `_explain_voicemail_incompatible`:

```
Your CUCM environment uses custom audio files for Music on Hold and/or
feature announcements. These files must be manually downloaded from CUCM
and uploaded to Webex. The Webex announcement repository accepts WAV files
up to 8 MB. Upload via Control Hub (Calling > Service Settings > Announcements)
or via API.
```

---

## 4. CUCM Source Detail

### 4.1 MoH Audio Sources (AXL)

**AXL operations:** `listMohAudioSource`, `getMohAudioSource`

**Key fields:**
| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Source name (e.g., "SampleAudioSource") |
| `sourceFileName` | string | WAV file name on CUCM TFTP |
| `isDefault` | boolean | Whether this is the system default source |
| `sourceId` | string | Numeric source ID |
| `mohAudioSourceFile` | list | Per-codec audio file references |
| `mohAudioSourceProfile` | list | References to MoH audio source profiles |

**Filesystem location:** CUCM stores MoH audio files in `/usr/local/cm/tftp/` on the CUCM publisher. Files are accessible via SFTP or through the CUCM OS Administration page (Cisco Unified OS Administration > Software Upgrades > TFTP File Management).

**Default sources:** CUCM ships with one default source ("SampleAudioSource"). Many deployments keep only the default. The pipeline already correctly identifies default vs. custom.

### 4.2 CUCM Announcements (AXL)

**AXL operations:** `listAnnouncement`, `getAnnouncement`

**Key fields:**
| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Announcement name |
| `description` | string | Admin description |
| `announcementFile` | string | Audio file name |

**Usage:** Announcements are referenced by name from IVR scripts, Auto Attendants, and other features. The AXL API does not expose which features reference a given announcement -- this must be inferred from feature configurations.

### 4.3 Hunt Pilot MoH Reference

The hunt pilot (which maps to Call Queue in Webex) stores `networkHoldMohAudioSourceID` in its configuration. This is the CUCM MoH audio source assigned to callers waiting in queue. The feature mapper already detects this field (line 422) as a signal that the hunt pilot has queue-like behavior, but doesn't track which source it references.

---

## 5. Webex Target API Detail

### 5.1 Location Music on Hold

**Endpoint:** `PUT /telephony/config/locations/{locationId}/musicOnHold`

**Request body (PutMusicOnHoldObject):**
```json
{
  "callHoldEnabled": true,
  "callParkEnabled": true,
  "greeting": "CUSTOM",
  "audioFile": {
    "id": "<announcement_id>",
    "fileName": "custom_hold_music.wav",
    "mediaFileType": "WAV",
    "level": "ORGANIZATION"
  },
  "playlistId": "<playlist_id>"
}
```

**Workflow to set custom MoH for a location:**
1. Upload audio file to announcement repository (`POST /telephony/config/announcements`)
2. Optionally create a playlist containing the announcement
3. Set location MoH to CUSTOM, referencing the announcement ID or playlist ID

**Key gotcha:** The `greeting` field accepts `"SYSTEM"` (Cisco default) or `"CUSTOM"`. When set to `"CUSTOM"`, either `audioFile.id` or `playlistId` must be provided. You cannot set `CUSTOM` without a pre-uploaded file.

**Scopes:** `spark-admin:telephony_config_write`

### 5.2 Announcement Repository Upload

**Org-level:** `POST /telephony/config/announcements`
**Location-level:** `POST /telephony/config/locations/{locationId}/announcements`

Both use `multipart/form-data` with `audio/wav` content type. The SDK handles this via `api.telephony.announcements_repo.upload_announcement()`. The CLI (`wxcli announcements`) does NOT support file upload (multipart limitation). Upload must use SDK, raw HTTP with curl, or Control Hub.

**Limits (from RepositoryUsage):**
- Max single audio file: 8 MB
- Max single video file: 16 MB
- Total repo capacity: 500 MB per org

### 5.3 Per-Person MoH

**Endpoint:** `PUT /telephony/config/people/{personId}/musicOnHold`

Uses `PutMusicOnHoldObject` same as location-level. Can override location-level MoH per user. CUCM doesn't typically have per-user MoH (it's per-MoH-server/source), so this is rarely needed in migration.

---

## 6. Pipeline Integration

### 6.1 No Changes to Extraction

The existing MOH and Announcement extractors are sufficient. No new AXL calls needed.

### 6.2 No Changes to Normalization

The existing normalizers for `moh_source` and `announcement` are sufficient.

### 6.3 Cross-Reference Additions

**File:** `src/wxcli/migration/transform/cross_reference.py`

Add to `CrossReferenceBuilder`:

```python
def _build_audio_refs(self):
    """Build feature -> MoH source and feature -> announcement cross-refs."""
    # Hunt pilots / call queues -> MoH sources
    for phone_data in self.store.get_objects("phone"):
        # Raw phone data contains hunt pilot references with MOH source IDs
        ...

    # Feature -> announcement references
    # This is limited by what AXL exposes. AA greeting configs don't
    # reference announcement objects directly in all cases.
```

**Realistic scope:** The cross-ref for `networkHoldMohAudioSourceID` -> MoH source is feasible because the field contains a source ID that maps to `moh_source:{name}`. The AA -> announcement cross-ref is harder because CUCM AA greeting configs reference audio files by name within IVR scripts, which are opaque blobs. This may need to be advisory-only (Pattern 27 mentions the count, but per-feature mapping may not be fully automated).

### 6.4 Advisory Pattern Addition

**File:** `src/wxcli/migration/advisory/advisory_patterns.py`

Add `detect_custom_audio_assets` as Pattern 27, registered in `ALL_ADVISORY_PATTERNS`.

### 6.5 Recommendation Rule Addition

**File:** `src/wxcli/migration/advisory/recommendation_rules.py`

Add `recommend_audio_asset_manual` and register in `RECOMMENDATION_DISPATCH` for `AUDIO_ASSET_MANUAL`.

### 6.6 Report Additions

**Files:**
- `src/wxcli/migration/report/appendix.py` -- new section I (Audio Assets)
- `src/wxcli/migration/report/executive.py` -- audio asset counts in inventory
- `src/wxcli/migration/report/explainer.py` -- enhanced explanation for AUDIO_ASSET_MANUAL
- `src/wxcli/migration/report/assembler.py` -- register new appendix section

---

## 7. Documentation Updates Required

| File | Change |
|------|--------|
| `src/wxcli/migration/advisory/CLAUDE.md` | Add Pattern 27 to the pattern list. Add `recommend_audio_asset_manual` to the recommendation rules list. Update pattern count from 26 to 27. |
| `src/wxcli/migration/report/CLAUDE.md` | Document new Appendix I (Audio Assets) section. |
| `src/wxcli/migration/transform/CLAUDE.md` | Document new `feature_uses_moh_source` and `feature_uses_announcement` cross-refs if added. |
| `src/wxcli/migration/CLAUDE.md` | No change needed (already lists announcement_mapper and moh_mapper). |
| `docs/runbooks/cucm-migration/decision-guide.md` | Add entry for `AUDIO_ASSET_MANUAL` decision type with manual download/upload procedure. |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Add "Audio Asset Preparation" section to the pre-migration checklist. |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Add MoH source mapping section (CUCM MoH audio sources -> Webex location MoH + announcement repo). |
| `CLAUDE.md` (project root) | No change needed (announcement and moh mappers already listed). |

---

## 8. Test Strategy

### 8.1 Advisory Pattern Tests

**File:** `tests/migration/advisory/test_advisory_patterns.py`

| Test | Description |
|------|-------------|
| `test_custom_audio_assets_no_custom` | Store with only default MoH source, no announcements -> no finding |
| `test_custom_audio_assets_moh_only` | 2 custom MoH sources -> MEDIUM finding with counts |
| `test_custom_audio_assets_announcements_only` | 5 announcements -> MEDIUM finding |
| `test_custom_audio_assets_mixed` | 3 MoH + 10 announcements -> HIGH finding |
| `test_custom_audio_assets_large_scale` | 5 MoH + 20 announcements -> CRITICAL finding |
| `test_custom_audio_assets_detail_text` | Verify detail includes download instructions and file counts |

### 8.2 Recommendation Rule Tests

**File:** `tests/migration/advisory/test_recommendation_rules.py`

| Test | Description |
|------|-------------|
| `test_recommend_audio_asset_announcement` | Announcement context -> recommend "accept" |
| `test_recommend_audio_asset_moh` | MoH context -> recommend "accept" |
| `test_recommend_audio_asset_never_default` | Verify "use_default" is never recommended |

### 8.3 Cross-Reference Tests (if cross-refs are added)

**File:** `tests/migration/transform/test_cross_reference.py`

| Test | Description |
|------|-------------|
| `test_feature_uses_moh_source` | Hunt pilot with `networkHoldMohAudioSourceID` -> cross-ref to MoH source |
| `test_feature_no_moh_source` | Hunt pilot without MoH source ID -> no cross-ref |

### 8.4 Report Tests

**File:** `tests/migration/report/test_appendix.py` (or new test file)

| Test | Description |
|------|-------------|
| `test_audio_assets_appendix_with_data` | Store with MoH + announcements -> section renders with tables |
| `test_audio_assets_appendix_empty` | No audio assets -> section renders with "no custom audio" message |
| `test_executive_audio_counts` | Verify executive summary includes audio asset counts |
| `test_explainer_audio_asset_manual` | Verify enhanced explainer text for AUDIO_ASSET_MANUAL |

**Estimated test count:** 12-15 tests.

---

## 9. Implementation Order

1. **Advisory pattern + recommendation rule** (advisory_patterns.py, recommendation_rules.py) -- highest value, lowest risk
2. **Report appendix section** (appendix.py, assembler.py) -- surfaces data already in the store
3. **Report executive summary counts** (executive.py) -- small addition
4. **Explainer enhancement** (explainer.py) -- small addition
5. **Cross-reference additions** (cross_reference.py) -- moderate complexity, may be deferred if AXL data is insufficient
6. **Documentation updates** -- after implementation

### Estimated Effort

- Advisory pattern + recommendation rule: 1 hour
- Report sections: 2 hours
- Cross-references: 1-2 hours (depends on AXL data quality)
- Tests: 2 hours
- Documentation: 1 hour
- **Total: 7-8 hours**

---

## 10. Open Questions

1. **Should we attempt automated audio file download?** CUCM stores MoH files in `/usr/local/cm/tftp/`. If the `cucm-collect` script (not yet built) gains SFTP access, it could automatically download MoH WAV files. This would upgrade the advisory from "manual download required" to "files downloaded, ready for upload." This is a stretch goal dependent on `cucm-collect` implementation.

2. **Should we attempt automated upload to Webex?** If the audio files are available locally, the SDK's `upload_announcement()` method can upload them programmatically. This could be an execution handler. However, the upload requires the file to be WAV format and under 8 MB. CUCM MoH sources can be in other formats. Format conversion adds complexity.

3. **Per-queue MoH assignment.** Webex Call Queues don't have a per-queue MoH setting in the same way CUCM hunt pilots do. Webex MoH is set at the location level or person level. If different queues in the same location use different MoH sources, this is a feature gap that should be called out in the advisory.

4. **Announcement repository capacity.** A large deployment with 50+ announcements could approach the 500 MB org limit. Should the advisory calculate estimated storage usage from CUCM file sizes?
