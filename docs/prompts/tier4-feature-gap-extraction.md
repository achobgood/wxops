# Tier 4: Feature Gap Extraction and Flagging

## Context

Tier 4 bridges between Tier 3 (informational-only, no mapping) and Tier 2 (full pipeline with mappers + execution). These are CUCM features that have Webex equivalents (or close approximations) but aren't currently extracted with enough detail to map automatically.

**Two waves:**
- **Wave 1 (this prompt):** Extract + flag in the assessment report. Produces inventory tables and advisory flags. No mappers or execution handlers.
- **Wave 2 (future):** Promote the highest-value items to full Tier 2 mappers with canonical types and execution handlers.

**Read these files first:**
- `docs/plans/cucm-pipeline/future/expansion-scope.md` — Tier 4 section
- `src/wxcli/migration/cucm/extractors/base.py` — extractor pattern
- `src/wxcli/migration/advisory/CLAUDE.md` — advisory system architecture
- `src/wxcli/migration/advisory/advisory_patterns.py` — existing 16 advisory patterns
- `src/wxcli/migration/report/appendix.py` — appendix section pattern
- `src/wxcli/migration/report/CLAUDE.md` — report architecture

## Wave 1: 6 Items — Extract + Flag

### Item 1: Recording Profiles

**What:** CUCM `recordingProfileName` + `recordingFlag` on line appearances control which users have call recording enabled and where recordings are sent.

**Extraction:**
- Expand `DeviceExtractor` (or create a post-processing step) to capture `recordingProfileName` and `recordingFlag` from each `lines.line[]` in the `getPhone` response
- Store as `MigrationObject(object_type="recording_config", canonical_id="recording:{user_cid}")` with fields: `user_canonical_id`, `recording_enabled` (bool), `profile_name`, `recording_type` (automatic/on-demand/never)
- Cross-ref: `user_has_recording_config`

**Report:**
- New appendix section: "Call Recording Inventory"
- Table: User, Profile, Type (Automatic/On-Demand), Status
- Advisory flag: if >0 users have recording enabled, produce `ARCHITECTURE_ADVISORY` with pattern: "Call recording requires Webex call recording license + storage configuration. {count} users currently have recording enabled."

### Item 2: Remote Destinations / SNR Inventory

**What:** CUCM Remote Destination Profiles define Single Number Reach (SNR) configurations — mobile/home numbers that ring simultaneously with the desk phone.

**Extraction:**
- If the Tier 2 `RemoteDestinationExtractor` is already built, this is a no-op — just add the report section
- If not built yet, create a lightweight version that only extracts counts and basic info (no timer details needed for Wave 1)
- AXL: `listRemoteDestinationProfile` with returned_tags `{name, description}`
- Count per user: cross-ref `getRemoteDestinationProfile` for each profile to get destination count

**Report:**
- New appendix section: "Single Number Reach Inventory"
- Table: Profile Name, User, Destination Count
- Summary: "{count} users have SNR configured with {total_destinations} remote destinations"
- Advisory: "Webex SNR is simpler than CUCM — timer controls will not migrate. Manual setup required."

### Item 3: Phone Button Template Usage

**What:** CUCM Phone Button Templates define the line key layout for phone models. The Tier 1 `ButtonTemplateMapper` already handles the full mapping, but the report doesn't show a clear inventory of template → phone model → user count relationships.

**Extraction:**
- No new extraction needed — data already exists in `CanonicalLineKeyTemplate` objects and `phone_uses_button_template` cross-refs
- **Gap:** The report appendix needs a section that aggregates this data

**Report:**
- New appendix section: "Phone Button Template Inventory"
- Table: Template Name, Model, Phones Using, Key Types (LINE/BLF/SPEED_DIAL/OPEN counts)
- Flag templates with >50% OPEN keys (underutilized), templates with BLF (monitoring integration)

### Item 4: Calling Party Transformation Patterns

**What:** CUCM Calling/Called Party Transformation Patterns manipulate caller ID (ANI/CLI) for outbound calls. Separate from Translation Patterns (which are already extracted in Tier 1).

**Extraction:**
- New AXL calls: `listCallingPartyTransformationPattern`, `listCalledPartyTransformationPattern`
- Store as `MigrationObject(object_type="info_transformation_pattern")` with fields: pattern, description, calling_search_space, partition, transformation_mask, prefix_digits
- These are informational — Webex handles caller ID transformation differently (location-level outbound caller ID settings)

**Report:**
- New appendix section: "Caller ID Transformation Patterns"
- Table: Pattern, Partition, Transformation Mask, Description
- Advisory: "CUCM caller ID transformations map to Webex location-level outbound caller ID settings. {count} patterns require manual review."

### Item 5: Intercom Enhancement

**What:** Tier 3 extracts intercom DN count. This enhancement adds line-level intercom assignments so the report shows which users have intercom configured.

**Extraction:**
- Expand the Tier 3 intercom SQL query to join with `devicenumplanmap` and `device` tables to get per-user intercom assignments
- Store as `MigrationObject(object_type="info_intercom", canonical_id="intercom:{dn}:{device}")` with: dn_pattern, device_name, owner_user

**Report:**
- Enhance existing Tier 3 "Feature Gaps" section with intercom detail: User, DN, Device
- Advisory: "Intercom has no native Webex equivalent. Workaround: speed dial + auto-answer header. {count} users affected."

### Item 6: Extension Mobility Usage

**What:** If Tier 2 Extension Mobility extraction is built, this just adds report aggregation. If not, extract basic usage counts.

**Extraction:**
- AXL: `listDeviceProfile` — just count and names
- Cross-ref with `listEndUser` to count users per profile
- Store as `MigrationObject(object_type="info_extension_mobility")` with: profile_name, user_count, line_count

**Report:**
- New appendix section: "Extension Mobility Usage"
- Table: Profile Name, Users, Lines
- Advisory: "Extension Mobility maps to Webex hot desking but loses profile-switching semantics. {count} users affected."

## Implementation Pattern

For each item:

1. **Check if data already exists** in the store from Tier 1/2 extractors — avoid duplicate extraction
2. **Extract** (if needed): new AXL calls or expand existing extractors
3. **Store** as `MigrationObject` with `object_type="info_{name}"` prefix
4. **Report section:** Add to `appendix.py` as a new `<details>` section with summary badge
5. **Advisory flag:** Add to `advisory_patterns.py` if cross-cutting concern, or produce `ARCHITECTURE_ADVISORY` decisions in a lightweight analyzer
6. **Tests:** Mock AXL data, verify extraction counts, verify report section renders

## Verification

```bash
python3.11 -m pytest tests/migration/ -x -q  # All tests pass
wxcli cucm discover --verbose  # New extraction counts
wxcli cucm analyze --verbose  # New advisory flags if applicable
wxcli cucm report --brand "Test" --prepared-by "Test"  # New sections visible
```

## Wave 2 Promotion Criteria (Future)

An item graduates from Tier 4 to Tier 2 when:
1. Customer demand justifies the mapper/handler complexity
2. The Webex API provides a clear mapping target
3. The extraction data is rich enough for automated mapping (not just counts)

Candidates for Wave 2 promotion:
- **Recording Profiles** → `CanonicalRecordingConfig` + `RecordingMapper` + `handle_recording_configure`
- **Remote Destinations/SNR** → already in Tier 2 spec (§2.7)
- **Calling Party Transformations** → expand `CanonicalTranslationPattern` or new type

## What NOT to Do

- Don't build full mappers or execution handlers — that's Wave 2
- Don't create new `DecisionType` enum values unless producing real decisions (advisory flags use `ARCHITECTURE_ADVISORY`)
- Don't modify existing Tier 1 mappers — Tier 4 adds alongside, not replaces
- Don't skip the "check if data already exists" step — several items may already have partial data from Tier 1/2 work
