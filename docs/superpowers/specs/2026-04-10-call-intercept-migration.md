# Call Intercept Migration

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline gap — call intercept settings

---

## 1. Problem Statement

CUCM call intercept settings are not discovered or migrated by the current pipeline. Call intercept is used to gracefully take a phone out of service — intercepting incoming and outgoing calls with announcements, redirect options, and voicemail fallback. Common use cases:

- **Terminated employees:** Callers hear "This number is no longer in service" with an option to dial the new contact or press 0 for operator.
- **Office relocations:** Callers hear the new number announcement before being redirected.
- **Leave of absence:** Calls route to voicemail or a coverage number while the person is away.
- **Number changes:** Announce the new number to callers for a transition period.

### What the feature does

Call intercept in Webex Calling provides per-person (also per-workspace and per-virtual-line) intercept configuration:

- **Incoming intercept:** `INTERCEPT_ALL` (all calls intercepted) or `ALLOW_ALL` (disabled). When intercepted, callers hear an announcement with optional new number announcement and press-0 transfer.
- **Outgoing intercept:** `INTERCEPT_ALL` (all outgoing blocked) or `ALLOW_LOCAL_ONLY` (only non-local calls blocked). Intercepted outgoing calls can optionally transfer to a destination.
- **Custom greeting:** Upload a `.wav` file for the intercept announcement.

### Current pipeline state

- **Discovery:** No AXL extraction for call intercept settings. CUCM stores intercept via the `CallIntercept` service configuration and the `InterceptDN` table.
- **Normalization:** No normalizer handles intercept data.
- **Mapping:** The `CallSettingsMapper` handles DND, call waiting, caller ID, privacy, and recording but **does not handle intercept**. The `recommendation_rules.py` file references `"intercept"` in the `_PROFESSIONAL_FEATURES` set (line 17), confirming it was anticipated but not implemented.
- **Analysis:** No analyzer checks for intercept configurations.
- **Advisory:** No advisory pattern flags intercept usage.
- **Report:** The assessment report does not mention intercept configurations.
- **Execution:** The `execute/__init__.py` has a comment on line 139 referencing "intercept" as a future person-call-settings handler, confirming it was planned.

### Impact of not migrating

Call intercept is typically applied to a small subset of users at any given time, but the impact of losing it is significant:

1. A terminated employee's line becomes reachable again — callers reach a generic "not available" instead of the configured redirect.
2. An office relocation loses its new-number announcement — callers don't learn the updated number.
3. A person on extended leave starts receiving calls again instead of routing to their coverage.

Unlike most settings that can be bulk-configured post-migration, intercept requires knowing *which* users currently have it enabled and *what* their specific redirect/announcement settings are.

---

## 2. CUCM Source Data

### 2a. AXL Discovery

CUCM call intercept is configured at the line level (directory number). The relevant CUCM tables and AXL access paths:

#### Line-Level Intercept (Primary Source)

CUCM does not have a native "call intercept" feature identical to Webex's. The closest equivalents are:

**1. Call Forward All (CFA) with "Out of Service" pattern:**

Users marked as "out of service" in CUCM typically have Call Forward All set to a voicemail pilot, auto-attendant, or announcement DN. This is already handled by `CallForwardingMapper`.

**2. Intercom/Intercept DN via Partition Blocking:**

CUCM administrators often use partition-based routing to block calls to specific users by placing their DN in a "blocked" or "intercept" partition. This is captured by the CSS/partition analysis.

**3. Translation Patterns for Number Change Announcements:**

When a number changes, CUCM admins create a translation pattern on the old number that routes to an announcement. This is captured by `RoutingMapper`.

**4. Direct Webex-Style Intercept — Not Native to CUCM:**

CUCM does not have a direct equivalent of Webex's `InterceptSetting` (enabled/disabled toggle with incoming/outgoing sub-settings). The Webex intercept feature is a BroadSoft/BroadWorks heritage feature that Webex Calling inherited.

### 2b. Practical Discovery Approach

Since CUCM lacks a direct intercept equivalent, the migration approach is:

**Option A (Recommended): Detect intercept-like configurations and flag for manual Webex intercept setup.**

The extractor identifies users who have intercept-like behavior configured:

```sql
-- Users with Call Forward All set to voicemail or announcement DNs
SELECT n.dnorpattern, n.fkroutepartition, 
       cfwd.cfadestination, cfwd.cfavoicemailenabled
FROM numplan n
JOIN callforwarddynamic cfwd ON cfwd.fknumplan = n.pkid
WHERE cfwd.cfadestination IS NOT NULL 
  AND cfwd.cfadestination != ''
  AND cfwd.cfavoicemailenabled = 't'
```

```sql
-- Users with DNs in "intercept" or "blocked" partitions
SELECT n.dnorpattern, rp.name as partition_name
FROM numplan n
JOIN routepartition rp ON rp.pkid = n.fkroutepartition
WHERE LOWER(rp.name) LIKE '%intercept%' 
   OR LOWER(rp.name) LIKE '%block%'
   OR LOWER(rp.name) LIKE '%out_of_service%'
   OR LOWER(rp.name) LIKE '%oos%'
```

**Option B: Post-migration intercept via Webex API only.**

Skip CUCM extraction entirely. Intercept settings are configured fresh in Webex based on HR/IT instructions about which users should be intercepted. The migration pipeline produces an advisory noting that Webex intercept is available but CUCM has no direct equivalent to auto-migrate.

### 2c. Recommended Approach: Option A with Advisory

Extract intercept-like signals from CUCM, normalize them into `intercept_candidate` objects, and produce an advisory that lists users who may need Webex intercept configured. Do NOT auto-configure intercept in Webex — it should be a manual decision because:

1. The CUCM patterns are heuristic (CFA to VM + "blocked" partition naming) — false positives are possible.
2. Intercept is a disruptive setting (blocks calls) — auto-enabling it risks breaking call flow.
3. The specific intercept configuration (announcement text, redirect number, outgoing behavior) must be designed fresh for Webex.

### 2d. Raw Data Shape

```python
raw_data["tier4"]["intercept_candidates"] = [
    {
        "userid": "jsmith",
        "dn": "1234",
        "partition": "Blocked_PT",
        "signal_type": "blocked_partition",  # or "cfa_voicemail", "cfa_announcement"
        "forward_destination": "+14155550000",
        "voicemail_enabled": True,
    },
    ...
]
```

### 2e. Extraction Implementation

Add to `src/wxcli/migration/cucm/extractors/tier4.py` (the `Tier4Extractor` class), alongside the existing recording profiles, remote destinations, transformation patterns, and EM device profiles.

New method: `_extract_intercept_candidates(result)` — SQL queries for CFA-to-voicemail users and blocked-partition DNs.

---

## 3. Webex Target APIs

### 3a. Read Call Intercept Settings

**Endpoint:** `GET /people/{personId}/features/intercept`

```json
{
  "enabled": false,
  "incoming": {
    "type": "INTERCEPT_ALL",
    "voicemailEnabled": false,
    "announcements": {
      "greeting": "DEFAULT",
      "fileName": "",
      "newNumber": {"enabled": false, "destination": ""},
      "zeroTransfer": {"enabled": false, "destination": ""}
    }
  },
  "outgoing": {
    "type": "INTERCEPT_ALL",
    "transferEnabled": false,
    "destination": ""
  }
}
```

**Scope:** `spark-admin:people_read`

### 3b. Configure Call Intercept Settings

**Endpoint:** `PUT /people/{personId}/features/intercept`

```json
{
  "enabled": true,
  "incoming": {
    "type": "INTERCEPT_ALL",
    "voicemailEnabled": true,
    "announcements": {
      "greeting": "DEFAULT",
      "newNumber": {"enabled": true, "destination": "+14155559999"},
      "zeroTransfer": {"enabled": true, "destination": "+14155550000"}
    }
  },
  "outgoing": {
    "type": "ALLOW_LOCAL_ONLY",
    "transferEnabled": false
  }
}
```

**Scope:** `spark-admin:people_write`

### 3c. Upload Custom Intercept Greeting

**Endpoint:** `POST /people/{personId}/features/intercept/actions/announcementUpload/invoke`

Multipart form-data with `audio/wav` content type.

**Scope:** `spark-admin:people_write`

### 3d. Location-Level Intercept

**Endpoint:** `GET/PUT /telephony/config/locations/{locationId}/intercept`

Same structure as person-level but applied to all users in a location. Useful for bulk intercept (e.g., entire office closure).

**Scope:** `spark-admin:telephony_config_read` / `spark-admin:telephony_config_write`

### 3e. Also Available For

- **Virtual Lines:** `GET/PUT /telephony/config/virtualLines/{virtualLineId}/intercept`
- **Workspaces:** `GET/PUT /workspaces/{workspaceId}/features/intercept`

Same data model across all entity types.

---

## 4. Pipeline Integration

### 4a. Normalization (Phase 04)

Add a normalizer function in `transform/normalizers.py`:

```python
def normalize_intercept_candidate(raw: dict) -> MigrationObject:
    """Normalize a CUCM intercept candidate signal."""
```

Register in `RAW_DATA_MAPPING`:
```python
("tier4", "intercept_candidates", "normalize_intercept_candidate"),
```

Object type in the store: `"intercept_candidate"`.

### 4b. Cross-References (Phase 04)

Add to `CrossReferenceBuilder`:

- `user_has_intercept_signal` — user canonical_id -> intercept_candidate canonical_id

### 4c. Mapping (Phase 05)

**Do NOT create a new mapper.** Instead, extend the existing `CallSettingsMapper` in `src/wxcli/migration/transform/mappers/call_settings_mapper.py`.

Add intercept candidate detection to `_extract_settings()`. When a user has an associated `intercept_candidate` cross-ref:

```python
# In _extract_settings():
intercept_refs = store.find_cross_refs(user_id, "user_has_intercept_signal")
if intercept_refs:
    candidate = store.get_object(intercept_refs[0])
    if candidate:
        pre = candidate.get("pre_migration_state", {})
        settings["intercept"] = {
            "detected": True,
            "signal_type": pre.get("signal_type", "unknown"),
            "forward_destination": pre.get("forward_destination"),
            "voicemail_enabled": pre.get("voicemail_enabled", False),
        }
```

Note: This enriches the user's `call_settings` with intercept metadata but does NOT auto-configure Webex intercept. The advisory pattern (section 6) flags these users for manual review.

### 4d. Analysis (Phase 06)

No new analyzer needed. The intercept candidates are informational — they produce advisory findings (section 6), not blocking decisions. If a user has `call_settings.intercept.detected = True`, this is surfaced in the report and advisory.

### 4e. Execution (Phase 07)

**No auto-execution.** Intercept is too disruptive to auto-configure. The pipeline:

1. Detects intercept-like signals in CUCM
2. Flags them in the assessment report
3. Produces an advisory with the list of affected users
4. The operator manually configures Webex intercept via `wxcli user-settings update-intercept` or via the Webex Control Hub after reviewing the list

If future requirements call for auto-execution, the executor would use:
```
PUT /people/{personId}/features/intercept
```
with the mapped settings. The operation is simple (single API call per user) and can be added later without architectural changes.

---

## 5. Report Changes

### 5a. Assessment Report — Executive Summary (Page 2)

In the "Environment Inventory" section, add a conditional row (only if intercept candidates detected):

| Metric | Value |
|--------|-------|
| Users with Intercept Signals | N |

### 5b. Assessment Report — Technical Appendix

Add a new subsection "Call Intercept Candidates" in the Tier 4 feature gap area:

- Table of users with intercept-like configurations
- Signal type column (blocked partition, CFA to voicemail, CFA to announcement)
- Current forward destination
- Recommendation: "Configure Webex intercept manually post-migration"

### 5c. Implementation

Modify `src/wxcli/migration/report/appendix.py`:
- Add an intercept candidates section in the Tier 4 feature gaps area.
- Query the store for `intercept_candidate` objects and render a summary table.

Modify `src/wxcli/migration/report/executive.py`:
- Add conditional intercept count to the environment inventory (only if > 0).

---

## 6. Advisory Pattern

### 6a. New Cross-Cutting Pattern: Call Intercept Candidates

Add to `advisory_patterns.py`:

**Pattern name:** `call_intercept_candidates`
**Category:** `out_of_scope` (manual Webex configuration required)
**Severity:** `MEDIUM` (when candidates detected), does not fire when none

**Logic:**
1. Count all `intercept_candidate` objects in the store
2. Group by `signal_type` for a structured summary
3. Produce an advisory listing affected users and the signal type

**Finding detail:**
```
N users have intercept-like configurations in CUCM (M via blocked partitions, 
P via CFA-to-voicemail). Webex Calling has a native call intercept feature 
(per-person incoming/outgoing intercept with announcements and redirect options) 
that should be configured manually post-migration for these users. 

The CUCM configurations are heuristic detections — verify each user's intended 
intercept behavior before enabling Webex intercept. Auto-enabling intercept 
would block calls to these users, which may not be the intended post-migration state.
```

**Affected objects:** List of user canonical_ids with intercept signals.

**Recommendation:** `"accept"` (acknowledge and plan manual intercept configuration).

### 6b. Tier 4 Pattern Integration

This pattern fits naturally with the existing Tier 4 advisory patterns (17-20 in the advisory CLAUDE.md): recording, SNR, transformation patterns, extension mobility. Call intercept candidates are the same category — detected CUCM feature usage that requires manual Webex configuration.

### 6c. No Recommendation Rule Needed

Since intercept candidates don't produce decisions (they're advisory-only), no recommendation rule is needed in `recommendation_rules.py`. The advisory pattern itself carries the recommendation reasoning.

---

## 7. Documentation Updates Required

### 7a. CLAUDE.md Files

| File | Section | What to Add |
|------|---------|-------------|
| `src/wxcli/migration/CLAUDE.md` | File Map table | No new files (extends existing mapper + tier4 extractor) |
| `src/wxcli/migration/transform/CLAUDE.md` | Pass 1: Normalizers section | Add `normalize_intercept_candidate` to key normalizers list |
| `src/wxcli/migration/transform/CLAUDE.md` | CrossReferenceBuilder table | Add `user_has_intercept_signal` relationship |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | CallSettingsMapper description | Note that intercept detection was added to the existing mapper |
| `src/wxcli/migration/cucm/CLAUDE.md` | raw_data Structure | Document `intercept_candidates` key under `tier4` |
| `src/wxcli/migration/advisory/CLAUDE.md` | Tier 4 feature gap patterns list | Add Pattern N: Call Intercept Candidates |

### 7b. Reference Docs

| File | Section | What to Add |
|------|---------|-------------|
| `docs/reference/person-call-settings-media.md` | Section 8: Call Intercept | Already fully documented with data models, methods, CLI examples, and raw HTTP. No changes needed. |

### 7c. Knowledge Base

| File | Section | What to Add |
|------|---------|-------------|
| `docs/knowledge-base/migration/kb-user-settings.md` | Call settings mapping table | Add row: "Call Intercept" -> "No CUCM equivalent; detect via CFA/partition heuristics; manual Webex config" |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Feature mapping table | Add row: "Call Intercept" -> "Manual (Webex-native, no CUCM 1:1 source)" with note about detection heuristics |
| `docs/knowledge-base/migration/kb-webex-limits.md` | Feature availability section | Note: Call intercept requires Professional license (same as other person-level telephony settings) |

### 7d. Runbooks

| File | Section | What to Add |
|------|---------|-------------|
| `docs/runbooks/cucm-migration/operator-runbook.md` | Post-migration verification section | Add step: "Review intercept candidates list; configure Webex intercept for terminated/relocated users" |
| `docs/runbooks/cucm-migration/decision-guide.md` | Advisory patterns section | Add entry for `call_intercept_candidates` advisory pattern |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Tier 4 feature gaps section | Mention intercept candidate detection heuristics and how to tune partition name patterns |

### 7e. Skills

| File | Section | What to Add |
|------|---------|-------------|
| `.claude/skills/cucm-migrate/SKILL.md` | No structural change needed | Advisory is auto-discovered |
| `.claude/skills/manage-call-settings/SKILL.md` | If it has a feature list | Mention call intercept as a configurable per-person setting |

### 7f. Models

| File | What to Add |
|------|-------------|
| `src/wxcli/migration/models.py` | No new model needed — uses existing `MigrationObject` for intercept_candidate |

---

## 8. Test Strategy

### 8a. Unit Tests — Extractor

**File:** `tests/migration/cucm/test_intercept_extractor.py`

| Test | Description |
|------|-------------|
| `test_extract_cfa_voicemail_candidates` | Mock SQL returns users with CFA to voicemail, verify raw_data shape |
| `test_extract_blocked_partition_candidates` | Mock SQL returns users in blocked partitions |
| `test_extract_no_candidates` | Clean environment, verify empty list |
| `test_partition_name_matching` | Verify LIKE patterns match "Intercept_PT", "Blocked", "OOS_PT" etc. |

### 8b. Unit Tests — Normalizer

**File:** `tests/migration/transform/test_normalizers_intercept.py`

| Test | Description |
|------|-------------|
| `test_normalize_intercept_candidate` | Raw intercept dict -> MigrationObject with correct canonical_id and pre_migration_state |
| `test_normalize_signal_types` | Each signal type produces correct pre_migration_state |

### 8c. Unit Tests — Mapper Extension

**File:** `tests/migration/transform/mappers/test_call_settings_mapper_intercept.py`

| Test | Description |
|------|-------------|
| `test_intercept_detection_blocked_partition` | User with intercept cross-ref -> `call_settings.intercept` populated |
| `test_intercept_detection_cfa_voicemail` | CFA-to-voicemail signal detected |
| `test_no_intercept_signal` | User without intercept cross-ref -> no intercept in call_settings |
| `test_intercept_does_not_override_other_settings` | Intercept detection coexists with DND, call waiting, etc. |

### 8d. Unit Tests — Advisory Pattern

**File:** `tests/migration/advisory/test_advisory_intercept.py`

| Test | Description |
|------|-------------|
| `test_pattern_fires_with_candidates` | Store has intercept candidates -> advisory produced |
| `test_pattern_silent_no_candidates` | No candidates -> empty findings |
| `test_pattern_groups_by_signal_type` | Multiple signal types in detail string |
| `test_pattern_severity_medium` | Verify severity is MEDIUM |
| `test_pattern_category_out_of_scope` | Verify category is out_of_scope |

### 8e. Integration Tests

**File:** `tests/migration/transform/test_intercept_integration.py`

| Test | Description |
|------|-------------|
| `test_full_pipeline_with_intercept` | Discover -> normalize -> map -> analyze with intercept candidates |
| `test_report_includes_intercept` | Assessment report includes intercept candidates section |

### Estimated test count: 14-17 tests

---

## 9. Risks and Open Questions

### 9a. Heuristic False Positives

The blocked-partition detection relies on partition naming conventions (`%intercept%`, `%block%`, `%oos%`). Administrators who use "block" in partition names for other purposes (e.g., "BlockInternational_PT") will produce false positives.

**Mitigation:** Make the partition name patterns configurable via migration config. Document the default patterns and how to customize them in the tuning reference. The advisory explicitly warns that detections are heuristic and should be verified.

### 9b. CFA-to-Voicemail Ambiguity

Many users have CFA to voicemail as a normal setting (e.g., "send all calls to voicemail during meetings"), not as an intercept. The heuristic should look for CFA combined with other signals:
- CFA enabled + user has no registered device
- CFA enabled + user in a "terminated" or "disabled" state
- CFA destination is a shared announcement DN (not personal voicemail)

**Mitigation:** Weight the signal types. CFA-to-voicemail alone is a weak signal (LOW). CFA + blocked partition is a strong signal (MEDIUM). The advisory groups by confidence level.

### 9c. No CUCM-to-Webex Settings Mapping

Since CUCM has no native call intercept feature, there is no field-level mapping table. The migration pipeline detects intercept-like behavior and flags it, but the actual Webex intercept configuration (announcement text, new number, zero-transfer destination, outgoing behavior) must be designed fresh.

**Mitigation:** The advisory includes a "what to configure" section listing the Webex intercept options and pointing the operator to `wxcli user-settings update-intercept` or the Control Hub intercept page.

### 9d. Volume Expectations

Intercept candidates are typically a small fraction of users (< 5%). The advisory and report should handle both small (1-5 users) and moderate (20-50 users) volumes gracefully.

### 9e. Location-Level Intercept

If the CUCM source has an entire location (device pool) with all DNs in a blocked partition, this should be flagged as a location-level intercept candidate rather than individual user-level. Webex supports `PUT /telephony/config/locations/{locationId}/intercept` for bulk intercept.

**Mitigation:** The advisory pattern groups candidates by location. If > 80% of users in a location have intercept signals, recommend location-level intercept instead of per-user.

---

## 10. Effort Estimate

| Component | Estimated Lines | Effort |
|-----------|----------------|--------|
| Extractor (SQL queries in tier4.py) | ~60 | Small |
| Normalizer (1 function) | ~25 | Small |
| Cross-reference addition | ~15 | Small |
| CallSettingsMapper extension | ~30 | Small |
| Advisory pattern | ~70 | Small |
| Report changes | ~40 | Small |
| Tests (14-17) | ~400 | Medium |
| Doc updates (6 files) | ~150 | Small |
| **Total** | **~790** | **Small-Medium** |

Estimated implementation time: 1 session.

---

## 11. Comparison: Executive/Assistant vs. Call Intercept

| Dimension | Executive/Assistant | Call Intercept |
|-----------|-------------------|---------------|
| CUCM source | Direct SQL table (`executiveassistant`) | Heuristic detection (CFA + partition naming) |
| Webex target | Rich API (6 endpoints, type/assign/alert/filter/screen/assist) | Single API (`PUT /people/{id}/features/intercept`) |
| Auto-migration | Yes (direct field mapping possible) | No (heuristic source, manual Webex config) |
| Pipeline output | New mapper + canonical object + execution ops | Mapper extension + advisory (informational) |
| Decision types | `MISSING_DATA` for broken pairs | None (advisory only) |
| Typical volume | 5-50 executives per org | 1-20 intercepted users per org |
| Risk of error | Low (direct mapping) | Medium (heuristic false positives) |
| Day-1 impact | HIGH (executives notice immediately) | MEDIUM (mostly terminated/relocated users) |
